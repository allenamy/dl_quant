#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tf_train_seq_att_v3.py

Fixes / changes vs prior version
--------------------------------
1) NaN-safe, mask-safe loss:
   - If y contains NaN/Inf anywhere (even where mask==0), the old loss could become NaN because:
       diff = pred - y  -> NaN
       huber(NaN)       -> NaN
       NaN * 0          -> NaN   (still NaN!)
     This script prevents that by computing diff ONLY on valid points and zeroing elsewhere.

2) Sanitizes X and y on load:
   - X: nan_to_num
   - y: nan_to_num + force y[mask==0] = 0

3) More representative scaler sampling:
   - sample_stats_days() randomly samples days across the training span (not just the first days).

4) Persists scalers and clipping params:
   - Saves x_center/x_scale and y_sigma/y_clip_lo/y_clip_hi in both .npy and meta.json.
   - This is important so inference can reapply the exact same feature normalization.

5) Score definition:
   - r2 is computed at main_step (default last step).
   - score_raw = sqrt(max(r2,0)) * std(y_target_raw_clipped)
   - score_bps = score_raw * score_mult   (default score_mult=10000 => bps if y is fractional return)

6) Dumps predictions for best checkpoint:
   - After training selects best epoch (by val loss), it loads that checkpoint and dumps:
       preds_best/train/YYYY-MM-DD/SYMBOL.csv.gz
       preds_best/val/YYYY-MM-DD/SYMBOL.csv.gz
       preds_best/test/YYYY-MM-DD/SYMBOL.csv.gz
     Each file contains:
       local_timestamp, pred, target, mask
     Optionally include scaled columns with --dump_scaled_preds 1.

Assumptions
-----------
- NPZ structure:
    X: (Nwin, L, S, F)
    y: (Nwin, Ly, S)
    y_mask: (Nwin, Ly, S) 0/1
- Window semantics:
    L=2H+1, Ly=H+1, active region is last Ly steps.
- main_step selects which step within active region you evaluate/dump:
    main_step=-1 => last step (t->t+H).
"""

import argparse
import gc
import json
import math
import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch import nn, optim
import torch.nn.functional as Fnn


# =========================
# Utils
# =========================

def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def parse_int_list_csv(s: str) -> List[int]:
    s = (s or "").strip()
    if not s:
        return []
    out: List[int] = []
    for part in s.split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    return out


def daterange(start: str, end: str) -> List[str]:
    a = datetime.strptime(start, "%Y-%m-%d")
    b = datetime.strptime(end, "%Y-%m-%d")
    out = []
    d = a
    while d <= b:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def safe_y_sigma_mad(y_1d: np.ndarray) -> float:
    y = np.asarray(y_1d, dtype=np.float64)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return 1.0
    med = np.median(y)
    mad = np.median(np.abs(y - med))
    sig = 1.4826 * mad
    if not np.isfinite(sig) or sig < 1e-9:
        sig = float(np.std(y))
    if not np.isfinite(sig) or sig < 1e-9:
        sig = 1.0
    return float(sig)


def normalize_main_step(main_step: int, Ly: int) -> int:
    ms = int(main_step)
    if ms < 0:
        ms = Ly + ms
    ms = max(0, min(Ly - 1, ms))
    return int(ms)


def dt_index_to_epoch_us(idx: pd.DatetimeIndex) -> np.ndarray:
    return (idx.view("int64") // 1_000).astype(np.int64)


def make_window_index(
    day: str,
    Nwin: int,
    *,
    warmup_len_sec: int,
    window_stride_sec: int,
    step_offset_sec: int,
    time_shift_sec: int,
) -> pd.DatetimeIndex:
    """
    One timestamp per window:
      t_i = midnight + warmup_len + i*stride + step_offset + time_shift
    """
    day0 = pd.Timestamp(day)
    offsets = int(warmup_len_sec) + (np.arange(int(Nwin), dtype=np.int64) * int(window_stride_sec)) + int(step_offset_sec)
    times = day0 + pd.to_timedelta(offsets + int(time_shift_sec), unit="s")
    return pd.DatetimeIndex(times, name="sts")


# =========================
# CV folds
# =========================

@dataclass
class Fold:
    train_days: List[str]
    val_days: List[str]
    test_days: List[str]


def build_folds(all_days: List[str], train_span: int, val_span: int, test_span: int, stride: int) -> List[Fold]:
    folds: List[Fold] = []
    total = train_span + val_span + test_span
    max_start = len(all_days) - total
    for i in range(0, max(0, max_start) + 1, max(1, stride)):
        tr = all_days[i:i + train_span]
        va = all_days[i + train_span:i + train_span + val_span]
        te = all_days[i + train_span + val_span:i + train_span + val_span + test_span]
        if len(tr) == train_span and len(va) == val_span and len(te) == test_span:
            folds.append(Fold(tr, va, te))
    return folds


# =========================
# NPZ discovery / loading
# =========================

def list_days_for_horizon(data_dir: Path, H: int) -> List[str]:
    hdir = data_dir / f"H{H}"
    if not hdir.is_dir():
        return []
    return [p.stem for p in sorted(hdir.glob("*.npz"))]


def npz_path(data_dir: Path, H: int, day: str) -> Path:
    return data_dir / f"H{H}" / f"{day}.npz"


def load_npz_arrays(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    z = np.load(path, allow_pickle=True)
    X = z["X"]
    y = z["y"]
    y_mask = z["y_mask"]
    symbols = z["symbols"].astype(object)
    features = z["features"].astype(object)
    warmup_len = int(z["warmup_len"]) if "warmup_len" in z.files else 0
    return X, y, y_mask, symbols, features, warmup_len


# =========================
# Scaling
# =========================

def fit_x_scaler_from_samples(
    samples: List[np.ndarray], mode: str, eps: float = 1e-6
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    mode = str(mode).lower()
    if mode == "none":
        return None, None

    flat = np.concatenate([s.reshape(-1, s.shape[-1]) for s in samples], axis=0).astype(np.float32, copy=False)
    flat = np.nan_to_num(flat, nan=0.0, posinf=0.0, neginf=0.0)

    if mode == "zscore":
        center = flat.mean(axis=0)
        scale = flat.std(axis=0)
    elif mode == "robust":
        center = np.median(flat, axis=0)
        mad = np.median(np.abs(flat - center), axis=0)
        scale = 1.4826 * mad
    else:
        raise ValueError("x_norm must be one of: none|zscore|robust")

    scale = np.where(~np.isfinite(scale) | (scale < eps), 1.0, scale)
    center = np.where(np.isfinite(center), center, 0.0)

    return center.astype(np.float32), scale.astype(np.float32)


def sample_stats_days(
    data_dir: Path,
    H: int,
    days: List[str],
    *,
    max_days: int,
    max_windows_per_day: int,
    seed: int,
) -> Tuple[List[np.ndarray], np.ndarray, np.ndarray]:
    """
    Randomly sample days across the training span (fixes "first-days-only" bias).
    Returns:
      Xflat samples list (each: (n,L,D)), ys (N,Ly,S), ms (N,Ly,S)
    """
    rng = np.random.default_rng(seed)

    if not days:
        raise RuntimeError("sample_stats_days: empty days")

    nd = int(min(max_days, len(days))) if max_days > 0 else len(days)
    nd = max(1, nd)

    pick_days = rng.choice(np.asarray(days, dtype=object), size=nd, replace=False).tolist()
    pick_days = [str(d) for d in pick_days]

    Xs_list: List[np.ndarray] = []
    ys_list: List[np.ndarray] = []
    ms_list: List[np.ndarray] = []

    for d in pick_days:
        p = npz_path(data_dir, H, d)
        if not p.exists():
            continue
        X, y, m, symbols, features, warmup_len = load_npz_arrays(p)

        N = int(X.shape[0])
        if N <= 0:
            continue
        n = int(min(N, max_windows_per_day)) if max_windows_per_day > 0 else N
        idx = rng.choice(N, size=n, replace=False)

        Xb = np.asarray(X[idx], dtype=np.float32)  # (n,L,S,F)
        Xflat = Xb.reshape(n, Xb.shape[1], -1)     # (n,L,D)
        Xflat = np.nan_to_num(Xflat, nan=0.0, posinf=0.0, neginf=0.0)

        yb = np.asarray(y[idx], dtype=np.float32)
        mb = np.asarray(m[idx], dtype=np.uint8)

        # sanitize y (important for any NaN in invalid slots)
        yb = np.nan_to_num(yb, nan=0.0, posinf=0.0, neginf=0.0)
        yb[mb.astype(bool) == 0] = 0.0

        Xs_list.append(Xflat)
        ys_list.append(yb)
        ms_list.append(mb)

        del X, y, m, Xb, Xflat, yb, mb
        gc.collect()

    if not Xs_list:
        raise RuntimeError("No samples collected for stats; missing files or empty windows.")

    ys = np.concatenate(ys_list, axis=0)
    ms = np.concatenate(ms_list, axis=0)
    return Xs_list, ys, ms


def fit_y_sigma_per_symbol(y: np.ndarray, m: np.ndarray, clip_k: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute robust sigma per symbol (MAD) and clipping bounds.
    """
    _, _, S = y.shape
    sigma_raw = np.zeros(S, dtype=np.float64)
    for s in range(S):
        vals = y[..., s][m[..., s].astype(bool)]
        sigma_raw[s] = safe_y_sigma_mad(vals)

    clip_lo = -float(clip_k) * sigma_raw
    clip_hi = +float(clip_k) * sigma_raw

    sigma = np.zeros(S, dtype=np.float64)
    for s in range(S):
        vals = y[..., s][m[..., s].astype(bool)]
        vals = np.clip(vals, clip_lo[s], clip_hi[s])
        sigma[s] = safe_y_sigma_mad(vals)

    sigma = np.where(~np.isfinite(sigma) | (sigma < 1e-12), 1.0, sigma)
    return clip_lo.astype(np.float32), clip_hi.astype(np.float32), sigma.astype(np.float32)


# =========================
# Model (Conv/TCN front-end + causal Transformer)
# =========================

class CausalConvBlock(nn.Module):
    def __init__(self, channels: int, kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        if kernel_size < 2:
            raise ValueError("kernel_size must be >= 2 for causal conv usefulness.")
        self.channels = int(channels)
        self.kernel_size = int(kernel_size)
        self.dilation = int(dilation)

        self.ln = nn.LayerNorm(channels)
        self.dw = nn.Conv1d(
            in_channels=channels,
            out_channels=channels,
            kernel_size=kernel_size,
            dilation=dilation,
            groups=channels,
            bias=False,
        )
        self.pw = nn.Conv1d(
            in_channels=channels,
            out_channels=channels,
            kernel_size=1,
            bias=True,
        )
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B,L,C)
        _, L, _ = x.shape
        h = self.ln(x).transpose(1, 2)   # (B,C,L)

        pad = (self.kernel_size - 1) * self.dilation
        h = Fnn.pad(h, (pad, 0))
        h = self.dw(h)
        h = h[:, :, :L]
        h = self.pw(h)

        h = h.transpose(1, 2)
        h = self.act(h)
        h = self.drop(h)
        return x + h


class CausalTransformerTime(nn.Module):
    def __init__(
        self,
        input_dim: int,
        out_dim: int,
        L: int,
        d_model: int,
        nhead: int,
        depth: int,
        d_ff: int,
        dropout: float,
        use_feature_gate: bool,
        use_conv_frontend: bool,
        conv_layers: int,
        conv_kernel: int,
        conv_dilation_base: int,
    ):
        super().__init__()
        if d_model % nhead != 0:
            raise ValueError("d_model must be divisible by nhead")

        self.L = int(L)
        self.input_dim = int(input_dim)
        self.out_dim = int(out_dim)

        self.feature_gate = nn.Parameter(torch.ones(input_dim)) if use_feature_gate else None

        self.in_proj = nn.Linear(input_dim, d_model)
        self.in_ln = nn.LayerNorm(d_model)
        self.in_drop = nn.Dropout(dropout)

        self.use_conv_frontend = bool(use_conv_frontend)
        self.conv_layers = int(max(0, conv_layers))
        self.conv_kernel = int(conv_kernel)
        self.conv_dilation_base = int(max(1, conv_dilation_base))

        if self.use_conv_frontend and self.conv_layers > 0:
            blocks = []
            dil = 1
            for _ in range(self.conv_layers):
                blocks.append(CausalConvBlock(
                    channels=d_model,
                    kernel_size=self.conv_kernel,
                    dilation=dil,
                    dropout=dropout,
                ))
                dil *= self.conv_dilation_base
            self.conv_frontend = nn.ModuleList(blocks)
        else:
            self.conv_frontend = None

        self.pos_emb = nn.Parameter(torch.zeros(1, self.L, d_model))
        nn.init.normal_(self.pos_emb, std=0.02)

        enc = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc, num_layers=depth)

        m = torch.triu(torch.ones(self.L, self.L), diagonal=1).bool()
        self.register_buffer("causal_mask", m, persistent=False)

        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.shape[1] != self.L:
            raise ValueError(f"Expected L={self.L}, got {x.shape[1]}")
        if self.feature_gate is not None:
            x = x * self.feature_gate[None, None, :]

        h = self.in_proj(x)
        h = self.in_ln(h)
        h = self.in_drop(h)

        if self.conv_frontend is not None:
            for blk in self.conv_frontend:
                h = blk(h)

        h = h + self.pos_emb[:, :self.L, :]
        h = self.encoder(h, mask=self.causal_mask)
        return self.head(h)  # (B,L,S)


# =========================
# Loss / metrics (mask-safe)
# =========================

def make_time_weights(Ly: int, loss_time_weight_min: float, device: str) -> Optional[torch.Tensor]:
    if Ly <= 1 or loss_time_weight_min >= 1.0:
        return None
    tw = torch.linspace(float(loss_time_weight_min), 1.0, steps=Ly, device=device, dtype=torch.float32)
    return tw / tw.mean()


def huber_loss_masked_safe(
    pred: torch.Tensor,     # (B,Ly,S) scaled
    target: torch.Tensor,   # (B,Ly,S) scaled
    mask: torch.Tensor,     # (B,Ly,S) float 0/1
    *,
    delta: float,
    time_w: Optional[torch.Tensor],
) -> torch.Tensor:
    """
    Mask-safe & NaN-safe:
      - valid = (mask>0) & isfinite(pred) & isfinite(target)
      - diff computed ONLY on valid entries; invalid entries contribute 0.
    """
    if pred.shape != target.shape or pred.shape != mask.shape:
        raise ValueError(f"shape mismatch pred={tuple(pred.shape)} target={tuple(target.shape)} mask={tuple(mask.shape)}")

    valid = (mask > 0.0) & torch.isfinite(pred) & torch.isfinite(target)

    diff = torch.where(valid, pred - target, torch.zeros_like(pred))
    ad = diff.abs()
    d = float(delta)
    hub = torch.where(
        ad <= d,
        0.5 * diff * diff,
        d * (ad - 0.5 * d),
    )

    w = valid.float()
    if time_w is not None:
        w = w * time_w[None, :, None]

    denom = torch.clamp(w.sum(), min=1.0)
    return (hub * w).sum() / denom


class OnlineStats:
    """
    Online stats for corr and R2 of (p,t) pairs.
    """
    def __init__(self):
        self.n = 0
        self.sum_p = 0.0
        self.sum_t = 0.0
        self.sum_pp = 0.0
        self.sum_tt = 0.0
        self.sum_pt = 0.0
        self.sum_se = 0.0

    def update(self, p: np.ndarray, t: np.ndarray):
        p = np.asarray(p, dtype=np.float64)
        t = np.asarray(t, dtype=np.float64)
        m = np.isfinite(p) & np.isfinite(t)
        if not np.any(m):
            return
        p = p[m]
        t = t[m]
        n = int(p.size)
        self.n += n
        self.sum_p += float(p.sum())
        self.sum_t += float(t.sum())
        self.sum_pp += float((p * p).sum())
        self.sum_tt += float((t * t).sum())
        self.sum_pt += float((p * t).sum())
        self.sum_se += float(((p - t) ** 2).sum())

    def corr(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        mp = self.sum_p / n
        mt = self.sum_t / n
        cov = (self.sum_pt / n) - mp * mt
        vp = (self.sum_pp / n) - mp * mp
        vt = (self.sum_tt / n) - mt * mt
        if vp <= 0 or vt <= 0:
            return 0.0
        return float(cov / math.sqrt(vp * vt))

    def r2(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        mt = self.sum_t / n
        vt = (self.sum_tt / n) - mt * mt
        vt = max(vt, 1e-12)
        mse = self.sum_se / n
        return float(1.0 - mse / vt)

    def std_pred(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        mp = self.sum_p / n
        vp = (self.sum_pp / n) - mp * mp
        return float(math.sqrt(max(vp, 0.0)))

    def std_target(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        mt = self.sum_t / n
        vt = (self.sum_tt / n) - mt * mt
        return float(math.sqrt(max(vt, 0.0)))


class OnlineMoments:
    """
    Online std for a single stream.
    """
    def __init__(self):
        self.n = 0
        self.sum = 0.0
        self.sum2 = 0.0

    def update(self, x: np.ndarray):
        x = np.asarray(x, dtype=np.float64)
        x = x[np.isfinite(x)]
        if x.size == 0:
            return
        self.n += int(x.size)
        self.sum += float(x.sum())
        self.sum2 += float((x * x).sum())

    def std(self) -> float:
        if self.n <= 1:
            return 0.0
        n = float(self.n)
        m = self.sum / n
        v = (self.sum2 / n) - m * m
        return float(math.sqrt(max(v, 0.0)))


# =========================
# Data iteration (sanitizing)
# =========================

def iter_day_minibatches(
    data_dir: Path,
    H: int,
    day: str,
    batch_size: int,
    shuffle: bool,
    seed: int,
):
    """
    Yields:
      Xflat: (B,L,D) float32
      y   : (B,Ly,S) float32  (sanitized, invalid forced 0)
      m   : (B,Ly,S) float32  (0/1)
      symbols, features, warmup_len
    """
    path = npz_path(data_dir, H, day)
    X, y, m, symbols, features, warmup_len = load_npz_arrays(path)

    N, L, S, F = X.shape

    Xflat = np.asarray(X, dtype=np.float32).reshape(N, L, S * F)
    Xflat = np.nan_to_num(Xflat, nan=0.0, posinf=0.0, neginf=0.0)

    y = np.asarray(y, dtype=np.float32)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

    m = np.asarray(m, dtype=np.uint8)
    # normalize mask to 0/1 float
    m_f = (m > 0).astype(np.float32)

    # force invalid targets to 0 (prevents any NaN poisoning)
    y[m_f == 0.0] = 0.0

    idx = np.arange(N, dtype=np.int64)
    if shuffle:
        rng = np.random.default_rng(seed)
        rng.shuffle(idx)

    bs = int(batch_size)
    for i in range(0, N, bs):
        sel = idx[i:i + bs]
        yield Xflat[sel], y[sel], m_f[sel], symbols, features, int(warmup_len)

    del X, y, m, Xflat, m_f
    gc.collect()


# =========================
# Eval / prediction dumping
# =========================

def eval_days(
    model: nn.Module,
    data_dir: Path,
    H: int,
    days: List[str],
    device: str,
    *,
    batch_size: int,
    x_center_t: Optional[torch.Tensor],
    x_scale_t: Optional[torch.Tensor],
    x_clip: float,
    y_sigma_t: torch.Tensor,
    y_clip_lo_t: torch.Tensor,
    y_clip_hi_t: torch.Tensor,
    delta: float,
    time_w_t: Optional[torch.Tensor],
    main_step: int,
    use_amp: bool,
    score_mult: float,
) -> Dict[str, float]:
    model.eval()

    losses: List[float] = []
    stats_scaled = OnlineStats()
    tgt_raw_mom = OnlineMoments()

    amp_ctx = torch.cuda.amp.autocast(enabled=use_amp) if (use_amp and device == "cuda") else nullcontext()

    with torch.no_grad():
        for day in days:
            for Xb, yb, mb, symbols, features, warmup_len in iter_day_minibatches(
                data_dir, H, day, batch_size=batch_size, shuffle=False, seed=0
            ):
                xb = torch.from_numpy(Xb).to(device)
                yb = torch.from_numpy(yb).to(device)
                mb = torch.from_numpy(mb).to(device)

                if x_center_t is not None and x_scale_t is not None:
                    xb = (xb - x_center_t[None, None, :]) / x_scale_t[None, None, :]
                if x_clip > 0:
                    xb = torch.clamp(xb, -float(x_clip), float(x_clip))

                with amp_ctx:
                    pred = model(xb)  # (B,L,S)

                    Ly = int(yb.shape[1])
                    start = int(pred.shape[1] - Ly)
                    pred_active = pred[:, start:, :]  # (B,Ly,S)

                    ms = normalize_main_step(int(main_step), Ly)

                    # clip target in raw units to the training clip bounds
                    yb_clip = torch.clamp(yb, y_clip_lo_t[None, None, :], y_clip_hi_t[None, None, :])

                    # scaled for loss/metrics (R2 is invariant to this scaling)
                    yb_s = yb_clip / y_sigma_t[None, None, :]
                    pred_s = pred_active / y_sigma_t[None, None, :]

                    loss_t = huber_loss_masked_safe(pred_s, yb_s, mb, delta=float(delta), time_w=time_w_t)

                if torch.isfinite(loss_t):
                    losses.append(float(loss_t.item()))

                # metrics @ main_step
                p = pred_s[:, ms, :].detach().cpu().numpy()
                t = yb_s[:, ms, :].detach().cpu().numpy()
                mnp = mb[:, ms, :].detach().cpu().numpy().astype(bool)

                stats_scaled.update(p[mnp], t[mnp])

                # raw target std @ main_step (after clipping)
                t_raw = yb_clip[:, ms, :].detach().cpu().numpy()
                tgt_raw_mom.update(t_raw[mnp])

    # If we somehow got no finite losses, mark as inf
    loss_mean = float(np.mean(losses)) if losses else float("inf")

    corr = stats_scaled.corr()
    r2 = stats_scaled.r2()
    std_pred_scaled = stats_scaled.std_pred()
    std_target_scaled = stats_scaled.std_target()

    std_target_raw = tgt_raw_mom.std()
    score_raw = math.sqrt(max(r2, 0.0)) * float(std_target_raw)
    score = score_raw * float(score_mult)

    return {
        "loss": float(loss_mean),
        "corr_scaled": float(corr),
        "r2_scaled": float(r2),
        "std_pred_scaled": float(std_pred_scaled),
        "std_target_scaled": float(std_target_scaled),
        "std_target_raw": float(std_target_raw),
        "score_raw": float(score_raw),
        "score": float(score),  # typically bps if score_mult=1e4
    }


def predict_and_dump_split(
    *,
    model: nn.Module,
    data_dir: Path,
    H: int,
    days: List[str],
    out_root: Path,
    split_name: str,
    device: str,
    batch_size: int,
    x_center_t: Optional[torch.Tensor],
    x_scale_t: Optional[torch.Tensor],
    x_clip: float,
    y_sigma: np.ndarray,
    y_sigma_t: torch.Tensor,
    y_clip_lo_t: torch.Tensor,
    y_clip_hi_t: torch.Tensor,
    main_step: int,
    use_amp: bool,
    window_stride_sec: int,
    time_shift_sec: int,
    dump_scaled: bool,
) -> None:
    """
    Writes per-day per-symbol csv.gz under:
      out_root/{split_name}/{YYYY-MM-DD}/{SYMBOL}.csv.gz
    with columns:
      local_timestamp, pred, target, mask (+ optional pred_scaled,target_scaled)
    """
    if not days:
        return

    model.eval()
    amp_ctx = torch.cuda.amp.autocast(enabled=use_amp) if (use_amp and device == "cuda") else nullcontext()

    out_base = out_root / split_name
    out_base.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        for day in days:
            # We'll assemble full day arrays for each symbol
            pred_list: List[np.ndarray] = []
            tgt_list: List[np.ndarray] = []
            m_list: List[np.ndarray] = []
            warmup_len_day: int = 0
            symbols_day: Optional[List[str]] = None

            for Xb, yb, mb, symbols, features, warmup_len in iter_day_minibatches(
                data_dir, H, day, batch_size=batch_size, shuffle=False, seed=0
            ):
                warmup_len_day = int(warmup_len)
                symbols_day = [str(s) for s in symbols.tolist()]

                xb = torch.from_numpy(Xb).to(device)
                yb = torch.from_numpy(yb).to(device)
                mb = torch.from_numpy(mb).to(device)

                if x_center_t is not None and x_scale_t is not None:
                    xb = (xb - x_center_t[None, None, :]) / x_scale_t[None, None, :]
                if x_clip > 0:
                    xb = torch.clamp(xb, -float(x_clip), float(x_clip))

                with amp_ctx:
                    pred = model(xb)  # (B,L,S)

                    Ly = int(yb.shape[1])
                    start = int(pred.shape[1] - Ly)
                    pred_active = pred[:, start:, :]  # (B,Ly,S)

                    ms = normalize_main_step(int(main_step), Ly)

                    yb_clip = torch.clamp(yb, y_clip_lo_t[None, None, :], y_clip_hi_t[None, None, :])

                # pick main_step
                pred_step = pred_active[:, ms, :].detach().cpu().numpy().astype(np.float32, copy=False)  # (B,S)
                tgt_step = yb_clip[:, ms, :].detach().cpu().numpy().astype(np.float32, copy=False)      # (B,S)
                m_step = mb[:, ms, :].detach().cpu().numpy().astype(np.uint8, copy=False)              # (B,S) 0/1

                pred_list.append(pred_step)
                tgt_list.append(tgt_step)
                m_list.append(m_step)

            if not pred_list or symbols_day is None:
                continue

            pred_day = np.concatenate(pred_list, axis=0)  # (Nwin,S)
            tgt_day = np.concatenate(tgt_list, axis=0)
            m_day = np.concatenate(m_list, axis=0)

            Nwin = int(pred_day.shape[0])
            S = int(pred_day.shape[1])

            idx = make_window_index(
                day,
                Nwin,
                warmup_len_sec=warmup_len_day,
                window_stride_sec=int(window_stride_sec),
                step_offset_sec=int(normalize_main_step(int(main_step), int(tgt_day.shape[1] if tgt_day.ndim == 3 else 0))) if False else int(normalize_main_step(int(main_step), int((H + 1)))),  # fallback, see below
                time_shift_sec=int(time_shift_sec),
            )

            # NOTE:
            # We want step_offset_sec = ms within active region, but Ly isn't available here anymore.
            # For NPZs that follow semantics Ly=H+1, ms maps to seconds.
            # If you want exact Ly-based mapping for nonstandard Ly, compute ms earlier and pass it in.
            ms_for_ts = normalize_main_step(int(main_step), int(H + 1))
            idx = make_window_index(
                day,
                Nwin,
                warmup_len_sec=warmup_len_day,
                window_stride_sec=int(window_stride_sec),
                step_offset_sec=int(ms_for_ts),
                time_shift_sec=int(time_shift_sec),
            )

            local_ts = dt_index_to_epoch_us(idx)

            # write per symbol
            day_dir = out_base / day
            day_dir.mkdir(parents=True, exist_ok=True)

            for si, sym in enumerate(symbols_day):
                df = pd.DataFrame({
                    "local_timestamp": local_ts,
                    "pred": pred_day[:, si].astype(np.float64),
                    "target": tgt_day[:, si].astype(np.float64),
                    "mask": m_day[:, si].astype(np.uint8),
                })
                if dump_scaled:
                    sig = float(y_sigma[si]) if si < len(y_sigma) else 1.0
                    df["pred_scaled"] = df["pred"] / (sig if sig != 0 else 1.0)
                    df["target_scaled"] = df["target"] / (sig if sig != 0 else 1.0)

                out_path = day_dir / f"{sym}.csv.gz"
                df.to_csv(out_path, index=False, compression="gzip")


# =========================
# Train one fold + horizon
# =========================

def train_one_fold_horizon(args, fold_idx: int, data_dir: Path, H: int, fold: Fold) -> None:
    device = "cuda" if (torch.cuda.is_available() and not args.cpu) else "cpu"
    use_amp = (device == "cuda") and (not args.no_amp)
    scaler_amp = torch.cuda.amp.GradScaler(enabled=use_amp)

    out_dir = Path(args.model_saved_path) / f"H{H}" / f"fold{fold_idx}"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt = out_dir / "model.pt"
    meta_json = out_dir / "meta.json"

    # ---- sample stats for scalers ----
    Xs_list, ys_samp, ms_samp = sample_stats_days(
        data_dir, H, fold.train_days,
        max_days=int(args.stats_num_days),
        max_windows_per_day=int(args.stats_num_windows_per_day),
        seed=int(args.seed) + 1000 * int(fold_idx) + int(H),
    )

    # ---- infer shapes from first train day ----
    X0, y0, m0, symbols0, features0, warmup_len0 = load_npz_arrays(npz_path(data_dir, H, fold.train_days[0]))
    S = int(len(symbols0))
    F = int(len(features0))
    L = int(X0.shape[1])
    Ly = int(y0.shape[1])
    D = int(S * F)

    warmup_len = int(warmup_len0)
    if int(args.warmup_len) > 0:
        warmup_len = int(args.warmup_len)

    # ---- x scaler ----
    center, scale = fit_x_scaler_from_samples(Xs_list, mode=args.x_norm, eps=1e-6)
    x_center_t = torch.tensor(center, device=device) if center is not None else None
    x_scale_t = torch.tensor(scale, device=device) if scale is not None else None

    # ---- y sigma + clip bounds ----
    clip_lo, clip_hi, y_sigma = fit_y_sigma_per_symbol(ys_samp, ms_samp, clip_k=float(args.clip_k))
    y_sigma_t = torch.tensor(y_sigma, device=device, dtype=torch.float32)
    y_clip_lo_t = torch.tensor(clip_lo, device=device, dtype=torch.float32)
    y_clip_hi_t = torch.tensor(clip_hi, device=device, dtype=torch.float32)

    time_w_t = make_time_weights(Ly, float(args.loss_time_weight_min), device=device)

    # ---- model ----
    model = CausalTransformerTime(
        input_dim=D,
        out_dim=S,
        L=L,
        d_model=int(args.d_model),
        nhead=int(args.nhead),
        depth=int(args.depth),
        d_ff=int(args.d_ff),
        dropout=float(args.dropout),
        use_feature_gate=(not args.no_feature_gate),
        use_conv_frontend=(not args.no_conv_frontend),
        conv_layers=int(args.conv_layers),
        conv_kernel=int(args.conv_kernel),
        conv_dilation_base=int(args.conv_dilation_base),
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=float(args.learning_rate), weight_decay=float(args.weight_decay))

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=float(args.lr_factor),
        patience=int(args.lr_patience),
        threshold=float(args.lr_threshold),
        threshold_mode=str(args.lr_threshold_mode),
        cooldown=int(args.lr_cooldown),
        min_lr=float(args.lr_min),
    )

    best_val = float("inf")
    best_epoch = -1
    best_val_metrics: Dict[str, float] = {}
    es_wait = 0
    accum = max(1, int(args.grad_accum_steps))

    print(f"\n========== Fold {fold_idx} | H={H} ==========", flush=True)
    print(f"device={device} AMP={use_amp}", flush=True)
    print(f"days: train={len(fold.train_days)} val={len(fold.val_days)} test={len(fold.test_days)}", flush=True)
    print(f"shapes: X(*,{L},{S},{F})->D={D} ; y Ly={Ly}", flush=True)
    print(f"x_norm={args.x_norm} x_clip={args.x_clip} y_clip_k={args.clip_k} huber_delta={args.huber_delta}", flush=True)
    print(
        f"conv_frontend={'OFF' if args.no_conv_frontend else 'ON'} "
        f"conv_layers={args.conv_layers} conv_kernel={args.conv_kernel} conv_dilation_base={args.conv_dilation_base}",
        flush=True,
    )
    print(
        f"lr_sched: factor={args.lr_factor} patience={args.lr_patience} "
        f"thr={args.lr_threshold} mode={args.lr_threshold_mode} cooldown={args.lr_cooldown} "
        f"min_lr={args.lr_min} warmup_epochs={args.lr_warmup_epochs}",
        flush=True,
    )
    print(f"main_step={args.main_step} score_mult={args.score_mult}", flush=True)

    # Persist scalers (important for inference)
    np.save(out_dir / "x_center.npy", center if center is not None else np.zeros((D,), dtype=np.float32))
    np.save(out_dir / "x_scale.npy", scale if scale is not None else np.ones((D,), dtype=np.float32))
    np.save(out_dir / "y_sigma.npy", y_sigma)
    np.save(out_dir / "y_clip_lo.npy", clip_lo)
    np.save(out_dir / "y_clip_hi.npy", clip_hi)

    t0 = time.perf_counter()

    amp_ctx = torch.cuda.amp.autocast(enabled=use_amp) if (use_amp and device == "cuda") else nullcontext()

    for epoch in range(int(args.num_epochs)):
        model.train()
        epoch_losses: List[float] = []

        optimizer.zero_grad(set_to_none=True)
        accum_count = 0

        for di, day in enumerate(fold.train_days):
            step_seed = int(args.seed) + epoch * 100000 + di * 17 + int(H)

            for Xb, yb, mb, symbols, features, warmup_len_file in iter_day_minibatches(
                data_dir, H, day, batch_size=int(args.batch_size), shuffle=True, seed=step_seed
            ):
                xb = torch.from_numpy(Xb).to(device)
                yb = torch.from_numpy(yb).to(device)
                mb = torch.from_numpy(mb).to(device)

                if x_center_t is not None and x_scale_t is not None:
                    xb = (xb - x_center_t[None, None, :]) / x_scale_t[None, None, :]
                if float(args.x_clip) > 0:
                    xb = torch.clamp(xb, -float(args.x_clip), float(args.x_clip))

                with amp_ctx:
                    pred = model(xb)  # (B,L,S)
                    start = int(pred.shape[1] - Ly)
                    pred_active = pred[:, start:, :]  # (B,Ly,S)

                    yb_clip = torch.clamp(yb, y_clip_lo_t[None, None, :], y_clip_hi_t[None, None, :])
                    yb_s = yb_clip / y_sigma_t[None, None, :]
                    pred_s = pred_active / y_sigma_t[None, None, :]

                    loss = huber_loss_masked_safe(
                        pred_s, yb_s, mb,
                        delta=float(args.huber_delta),
                        time_w=time_w_t,
                    )

                if not torch.isfinite(loss):
                    # Skip pathological batch (shouldn't happen with our sanitization, but just in case)
                    optimizer.zero_grad(set_to_none=True)
                    accum_count = 0
                    continue

                loss_div = loss / float(accum)
                scaler_amp.scale(loss_div).backward()
                accum_count += 1

                if accum_count >= accum:
                    if float(args.grad_clip) > 0:
                        scaler_amp.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), float(args.grad_clip))

                    scaler_amp.step(optimizer)
                    scaler_amp.update()
                    optimizer.zero_grad(set_to_none=True)
                    accum_count = 0

                epoch_losses.append(float(loss.item()))

        # flush remaining accumulated grads
        if accum_count > 0:
            if float(args.grad_clip) > 0:
                scaler_amp.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(args.grad_clip))
            scaler_amp.step(optimizer)
            scaler_amp.update()
            optimizer.zero_grad(set_to_none=True)

        train_loss = float(np.mean(epoch_losses)) if epoch_losses else float("inf")

        valm = eval_days(
            model, data_dir, H, fold.val_days, device,
            batch_size=int(args.batch_size),
            x_center_t=x_center_t, x_scale_t=x_scale_t, x_clip=float(args.x_clip),
            y_sigma_t=y_sigma_t, y_clip_lo_t=y_clip_lo_t, y_clip_hi_t=y_clip_hi_t,
            delta=float(args.huber_delta),
            time_w_t=time_w_t,
            main_step=int(args.main_step),
            use_amp=use_amp,
            score_mult=float(args.score_mult),
        )
        val_loss = float(valm["loss"])

        improved = (math.isfinite(val_loss) and (val_loss < best_val - 1e-4))
        if improved:
            best_val = val_loss
            best_epoch = int(epoch)
            best_val_metrics = {k: float(v) for k, v in valm.items()}
            es_wait = 0

            torch.save(model.state_dict(), best_ckpt)

            meta_out = {
                "fold_idx": int(fold_idx),
                "H": int(H),
                "best_epoch": int(best_epoch),
                "best_val_loss": float(best_val),

                "symbols": [str(s) for s in symbols0.tolist()],
                "features": [str(f) for f in features0.tolist()],
                "L": int(L),
                "Ly": int(Ly),
                "D": int(D),
                "S": int(S),
                "F": int(F),

                "main_step": int(args.main_step),
                "score_mult": float(args.score_mult),
                "window_stride_sec": int(args.window_stride_sec),
                "time_shift_sec": int(args.time_shift_sec),

                "x_norm": str(args.x_norm),
                "x_clip": float(args.x_clip),
                "x_center": (center.tolist() if center is not None else None),
                "x_scale": (scale.tolist() if scale is not None else None),

                "clip_k": float(args.clip_k),
                "y_sigma": y_sigma.tolist(),
                "y_clip_lo": clip_lo.tolist(),
                "y_clip_hi": clip_hi.tolist(),

                "train_days": fold.train_days,
                "val_days": fold.val_days,
                "test_days": fold.test_days,

                "val_metrics": best_val_metrics,

                "model_hparams": {
                    "d_model": int(args.d_model),
                    "nhead": int(args.nhead),
                    "depth": int(args.depth),
                    "d_ff": int(args.d_ff),
                    "dropout": float(args.dropout),
                    "feature_gate": bool(not args.no_feature_gate),
                },
                "conv_frontend": {
                    "enabled": bool(not args.no_conv_frontend),
                    "layers": int(args.conv_layers),
                    "kernel": int(args.conv_kernel),
                    "dilation_base": int(args.conv_dilation_base),
                },
                "lr_scheduler": {
                    "factor": float(args.lr_factor),
                    "patience": int(args.lr_patience),
                    "threshold": float(args.lr_threshold),
                    "threshold_mode": str(args.lr_threshold_mode),
                    "cooldown": int(args.lr_cooldown),
                    "min_lr": float(args.lr_min),
                    "warmup_epochs": int(args.lr_warmup_epochs),
                },
                "optimizer": {
                    "learning_rate": float(args.learning_rate),
                    "weight_decay": float(args.weight_decay),
                    "grad_clip": float(args.grad_clip),
                    "grad_accum_steps": int(args.grad_accum_steps),
                },
                "loss": {
                    "huber_delta_scaled": float(args.huber_delta),
                    "loss_time_weight_min": float(args.loss_time_weight_min),
                },
                "scaler_files": {
                    "x_center_npy": "x_center.npy",
                    "x_scale_npy": "x_scale.npy",
                    "y_sigma_npy": "y_sigma.npy",
                    "y_clip_lo_npy": "y_clip_lo.npy",
                    "y_clip_hi_npy": "y_clip_hi.npy",
                },
            }
            with open(meta_json, "w", encoding="utf-8") as f:
                json.dump(meta_out, f, indent=2)
        else:
            es_wait += 1

        prev_lr = float(optimizer.param_groups[0]["lr"])
        if (epoch + 1) > int(args.lr_warmup_epochs) and math.isfinite(val_loss):
            scheduler.step(val_loss)
        new_lr = float(optimizer.param_groups[0]["lr"])
        if new_lr < prev_lr - 1e-12:
            es_wait = 0

        print(
            f"[Fold {fold_idx} H={H}] Epoch {epoch+1:03d} | LR {new_lr:.2e} | "
            f"TrainLoss {train_loss:.4f} | ValLoss {val_loss:.4f} | "
            f"corr {valm['corr_scaled']:+.3f} | R2 {valm['r2_scaled']:+.4f} | "
            f"std_t_raw {valm['std_target_raw']:.6g} | score {valm['score']:+.6f} | "
            f"{'✓' if improved else ''}",
            flush=True
        )

        if es_wait >= int(args.patience):
            print(f"[Fold {fold_idx} H={H}] Early stopping", flush=True)
            break

    print(f"[Fold {fold_idx} H={H}] train time: {time.perf_counter() - t0:.1f}s", flush=True)

    # ---- load best and eval test, dump preds ----
    if best_ckpt.exists():
        model.load_state_dict(torch.load(best_ckpt, map_location=device), strict=True)

        tem = eval_days(
            model, data_dir, H, fold.test_days, device,
            batch_size=int(args.batch_size),
            x_center_t=x_center_t, x_scale_t=x_scale_t, x_clip=float(args.x_clip),
            y_sigma_t=y_sigma_t, y_clip_lo_t=y_clip_lo_t, y_clip_hi_t=y_clip_hi_t,
            delta=float(args.huber_delta),
            time_w_t=time_w_t,
            main_step=int(args.main_step),
            use_amp=use_amp,
            score_mult=float(args.score_mult),
        )
        print(
            f"[Fold {fold_idx} H={H}] TEST | Loss {tem['loss']:.4f} | "
            f"corr {tem['corr_scaled']:+.3f} | R2 {tem['r2_scaled']:+.4f} | "
            f"std_t_raw {tem['std_target_raw']:.6g} | score {tem['score']:+.6f}",
            flush=True
        )

        # Update meta with test metrics
        try:
            if meta_json.exists():
                j = json.loads(meta_json.read_text(encoding="utf-8"))
            else:
                j = {}
            j["test_metrics"] = {k: float(v) for k, v in tem.items()}
            meta_json.write_text(json.dumps(j, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] failed to update meta.json with test_metrics: {e}", flush=True)

        # Dump predictions for best model
        if int(args.dump_predictions) == 1:
            preds_root = out_dir / "preds_best"
            preds_root.mkdir(parents=True, exist_ok=True)

            dump_scaled = bool(int(args.dump_scaled_preds))

            if int(args.dump_train_predictions) == 1:
                print(f"[DUMP] train preds -> {preds_root/'train'}", flush=True)
                predict_and_dump_split(
                    model=model,
                    data_dir=data_dir,
                    H=int(H),
                    days=fold.train_days,
                    out_root=preds_root,
                    split_name="train",
                    device=device,
                    batch_size=int(args.batch_size),
                    x_center_t=x_center_t,
                    x_scale_t=x_scale_t,
                    x_clip=float(args.x_clip),
                    y_sigma=y_sigma,
                    y_sigma_t=y_sigma_t,
                    y_clip_lo_t=y_clip_lo_t,
                    y_clip_hi_t=y_clip_hi_t,
                    main_step=int(args.main_step),
                    use_amp=use_amp,
                    window_stride_sec=int(args.window_stride_sec),
                    time_shift_sec=int(args.time_shift_sec),
                    dump_scaled=dump_scaled,
                )

            if int(args.dump_val_predictions) == 1:
                print(f"[DUMP] val preds -> {preds_root/'val'}", flush=True)
                predict_and_dump_split(
                    model=model,
                    data_dir=data_dir,
                    H=int(H),
                    days=fold.val_days,
                    out_root=preds_root,
                    split_name="val",
                    device=device,
                    batch_size=int(args.batch_size),
                    x_center_t=x_center_t,
                    x_scale_t=x_scale_t,
                    x_clip=float(args.x_clip),
                    y_sigma=y_sigma,
                    y_sigma_t=y_sigma_t,
                    y_clip_lo_t=y_clip_lo_t,
                    y_clip_hi_t=y_clip_hi_t,
                    main_step=int(args.main_step),
                    use_amp=use_amp,
                    window_stride_sec=int(args.window_stride_sec),
                    time_shift_sec=int(args.time_shift_sec),
                    dump_scaled=dump_scaled,
                )

            if int(args.dump_test_predictions) == 1:
                print(f"[DUMP] test preds -> {preds_root/'test'}", flush=True)
                predict_and_dump_split(
                    model=model,
                    data_dir=data_dir,
                    H=int(H),
                    days=fold.test_days,
                    out_root=preds_root,
                    split_name="test",
                    device=device,
                    batch_size=int(args.batch_size),
                    x_center_t=x_center_t,
                    x_scale_t=x_scale_t,
                    x_clip=float(args.x_clip),
                    y_sigma=y_sigma,
                    y_sigma_t=y_sigma_t,
                    y_clip_lo_t=y_clip_lo_t,
                    y_clip_hi_t=y_clip_hi_t,
                    main_step=int(args.main_step),
                    use_amp=use_amp,
                    window_stride_sec=int(args.window_stride_sec),
                    time_shift_sec=int(args.time_shift_sec),
                    dump_scaled=dump_scaled,
                )

    gc.collect()


# =========================
# Main
# =========================

def parse_args():
    ap = argparse.ArgumentParser("Train horizon models from NPZ day shards (H60/H300/H600).")

    ap.add_argument("--data_dir", required=True, help="Root containing H60/,H300/,H600/ with YYYY-MM-DD.npz")
    ap.add_argument("--model_saved_path", required=True)

    ap.add_argument("--horizons-sec", type=str, default="60,300,600")
    ap.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end-date", required=True, help="YYYY-MM-DD")

    ap.add_argument("--train-span-days", type=int, default=60)
    ap.add_argument("--val-span-days", type=int, default=14)
    ap.add_argument("--test-span-days", type=int, default=14)
    ap.add_argument("--cv-stride-days", type=int, default=14)

    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--no_amp", action="store_true")

    ap.add_argument("--batch_size", type=int, default=64)
    ap.add_argument("--num_epochs", type=int, default=50)
    ap.add_argument("--patience", type=int, default=10)
    ap.add_argument("--grad_accum_steps", type=int, default=1)

    ap.add_argument("--learning_rate", type=float, default=1e-3)
    ap.add_argument("--weight_decay", type=float, default=1e-5)
    ap.add_argument("--grad_clip", type=float, default=1.0)

    ap.add_argument("--x_norm", type=str, default="robust", choices=["none", "zscore", "robust"])
    ap.add_argument("--x_clip", type=float, default=10.0)

    ap.add_argument("--clip_k", type=float, default=5.0)
    ap.add_argument("--huber_delta", type=float, default=2.0)
    ap.add_argument("--loss_time_weight_min", type=float, default=0.3)

    # LR scheduler
    ap.add_argument("--lr_factor", type=float, default=0.8)
    ap.add_argument("--lr_patience", type=int, default=8)
    ap.add_argument("--lr_min", type=float, default=1e-5)
    ap.add_argument("--lr_threshold", type=float, default=1e-3)
    ap.add_argument("--lr_threshold_mode", type=str, default="abs", choices=["abs", "rel"])
    ap.add_argument("--lr_cooldown", type=int, default=2)
    ap.add_argument("--lr_warmup_epochs", type=int, default=8)

    ap.add_argument("--main_step", type=int, default=-1)

    ap.add_argument("--d_model", type=int, default=128)
    ap.add_argument("--nhead", type=int, default=4)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--d_ff", type=int, default=512)
    ap.add_argument("--dropout", type=float, default=0.10)
    ap.add_argument("--no_feature_gate", action="store_true")

    ap.add_argument("--stats_num_days", type=int, default=5)
    ap.add_argument("--stats_num_windows_per_day", type=int, default=2000)

    ap.add_argument("--warmup_len", type=int, default=0)

    ap.add_argument("--no_conv_frontend", action="store_true", help="Disable causal conv/TCN front-end.")
    ap.add_argument("--conv_layers", type=int, default=2)
    ap.add_argument("--conv_kernel", type=int, default=9)
    ap.add_argument("--conv_dilation_base", type=int, default=2)

    # score scaling to "bps"
    ap.add_argument("--score_mult", type=float, default=10000.0,
                    help="Multiply score_raw by this. If y is fractional return, 1e4 => bps.")

    # prediction dumping
    ap.add_argument("--dump_predictions", type=int, default=1,
                    help="1 to dump preds for train/val/test at best epoch; 0 disables.")
    ap.add_argument("--dump_train_predictions", type=int, default=1)
    ap.add_argument("--dump_val_predictions", type=int, default=1)
    ap.add_argument("--dump_test_predictions", type=int, default=1)
    ap.add_argument("--dump_scaled_preds", type=int, default=0,
                    help="If 1, include pred_scaled/target_scaled columns in dumps.")

    # timestamp mapping for dumps
    ap.add_argument("--window_stride_sec", type=int, default=60)
    ap.add_argument("--time_shift_sec", type=int, default=0)

    return ap.parse_args()


def main():
    args = parse_args()
    set_seed(int(args.seed))

    # Optional perf knobs
    if torch.cuda.is_available() and not args.cpu:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    try:
        torch.set_float32_matmul_precision("medium")
    except Exception:
        pass

    data_dir = Path(args.data_dir)
    out_root = Path(args.model_saved_path)
    out_root.mkdir(parents=True, exist_ok=True)

    horizons = parse_int_list_csv(args.horizons_sec)
    if not horizons:
        raise ValueError("No horizons provided")

    all_days = daterange(args.start_date, args.end_date)

    for H in horizons:
        avail = set(list_days_for_horizon(data_dir, H))
        days = [d for d in all_days if d in avail]
        need = int(args.train_span_days) + int(args.val_span_days) + int(args.test_span_days)
        if len(days) < need:
            print(f"[WARN] H{H}: not enough available days ({len(days)}) for requested spans ({need}); skipping.", flush=True)
            continue

        folds = build_folds(
            days,
            train_span=int(args.train_span_days),
            val_span=int(args.val_span_days),
            test_span=int(args.test_span_days),
            stride=int(args.cv_stride_days),
        )
        if not folds:
            print(f"[WARN] H{H}: no folds built; skipping.", flush=True)
            continue

        print(f"\n==== Horizon H={H} ====", flush=True)
        print(f"Available days: {len(days)} | folds: {len(folds)}", flush=True)

        for fi, fold in enumerate(folds, start=1):
            train_one_fold_horizon(args, fi, data_dir, int(H), fold)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
