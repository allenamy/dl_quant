#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_rnn_tbptt_mtl.py

Stateful Truncated Backpropagation Through Time (TBPTT) Multi-Task Trainer.
Ingests continuous Parquet files, treats Symbols as the batch dimension, 
and detaches hidden states across chronological chunks to achieve infinite memory.
"""

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch import nn, optim
import torch.nn.functional as Fnn
from contextlib import nullcontext
import gc

# ======================================================================
# 1. Configuration & Utils
# ======================================================================

def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def amp_autocast_ctx(device: str, use_amp: bool):
    if use_amp and device == "cuda":
        try:
            return torch.amp.autocast("cuda", enabled=True)
        except AttributeError:
            return torch.cuda.amp.autocast(enabled=True)
    return nullcontext()

@dataclass
class Fold:
    train_days: List[str]
    val_days: List[str]

def build_embargoed_folds(all_days: List[str], train_span: int, val_span: int, stride: int, embargo_days: int) -> List[Fold]:
    """Builds Train/Val folds with a strict embargo gap to prevent target leakage."""
    folds = []
    total_req = train_span + embargo_days + val_span
    max_start = len(all_days) - total_req
    
    for i in range(0, max(0, max_start) + 1, max(1, stride)):
        tr = all_days[i : i + train_span]
        va = all_days[i + train_span + embargo_days : i + total_req]
        if len(tr) == train_span and len(va) == val_span:
            folds.append(Fold(tr, va))
    return folds


# ======================================================================
# 2. Continuous Parquet Loader & TBPTT Iterator
# ======================================================================

def load_day_continuous(
    data_dir: Path, 
    date_str: str, 
    symbols: List[str], 
    features: List[str], 
    horizons: List[int]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Loads all symbols for a day. Aligns them to a strict 86400-second grid.
    Returns X (T, S, F), Y (T, S, H), M (T, S, H).
    """
    T, S, F, H = 86400, len(symbols), len(features), len(horizons)
    
    X_out = np.zeros((T, S, F), dtype=np.float32)
    Y_out = np.zeros((T, S, H), dtype=np.float32)
    M_out = np.zeros((T, S, H), dtype=np.float32)

    day_idx = pd.date_range(start=date_str, end=f"{date_str} 23:59:59", freq="1s", tz="UTC")

    for s_idx, sym in enumerate(symbols):
        pqt_path = data_dir / sym / f"{sym}_{date_str}.parquet"
        if not pqt_path.exists(): continue
            
        try:
            df = pd.read_parquet(pqt_path)
            if df.empty: continue
            
            if df.index.tz is None: df.index = df.index.tz_localize("UTC")
            else: df.index = df.index.tz_convert("UTC")
                
            # Reindex to strict 86400 grid (carry forward states up to 60s)
            df = df[~df.index.duplicated(keep="last")]
            df = df.reindex(day_idx, method="ffill", limit=60)

            # Extract Features
            avail_feats = [f for f in features if f in df.columns]
            if avail_feats:
                X_df = df[avail_feats].fillna(0.0)
                for f_idx, feat in enumerate(features):
                    if feat in X_df.columns:
                        X_out[:, s_idx, f_idx] = X_df[feat].to_numpy(dtype=np.float32)

            # Extract Targets (Multi-Task)
            for h_idx, horiz in enumerate(horizons):
                m_mins = int(horiz // 60)
                tgt_col = f"target_{m_mins}m_bps"
                val_col = f"target_{m_mins}m_valid"
                
                if tgt_col in df.columns:
                    tgt_val = df[tgt_col].fillna(0.0).to_numpy(dtype=np.float32)
                    mask_val = df[val_col].fillna(False).to_numpy(dtype=bool) if val_col in df.columns else np.isfinite(df[tgt_col].values)
                    
                    tgt_val[~mask_val] = 0.0
                    Y_out[:, s_idx, h_idx] = tgt_val
                    M_out[:, s_idx, h_idx] = mask_val.astype(np.float32)

        except Exception as e:
            print(f"[WARN] Failed to load {sym} on {date_str}: {e}")

    return X_out, Y_out, M_out

def iter_day_tbptt(X: np.ndarray, y: np.ndarray, m: np.ndarray, bptt_len: int):
    """
    Yields chronologically contiguous chunks for TBPTT. NO SHUFFLING ALLOWED.
    Outputs: (bptt_len, S, F) tensors.
    """
    T = X.shape[0]
    for start in range(0, T, bptt_len):
        end = min(start + bptt_len, T)
        if end - start < 2: continue # Skip fragments at 23:59
        yield X[start:end], y[start:end], m[start:end]

def fit_robust_scalers(X_sample: np.ndarray, Y_sample: np.ndarray, M_sample: np.ndarray, clip_k: float = 5.0):
    """Fits robust MAD scalers per-horizon to prevent blowups from crypto wicks."""
    # X Scaling
    flat_X = X_sample.reshape(-1, X_sample.shape[-1])
    center = np.median(flat_X, axis=0)
    mad = np.median(np.abs(flat_X - center), axis=0)
    scale = np.where(mad < 1e-6, 1.0, 1.4826 * mad)

    # Y Scaling (Per Horizon)
    H = Y_sample.shape[-1]
    y_sigma = np.zeros(H, dtype=np.float32)
    y_clip_lo = np.zeros(H, dtype=np.float32)
    y_clip_hi = np.zeros(H, dtype=np.float32)
    
    for h in range(H):
        vals = Y_sample[..., h][M_sample[..., h] > 0]
        if len(vals) == 0:
            y_sigma[h] = 1.0
            continue
            
        med = np.median(vals)
        sig = 1.4826 * np.median(np.abs(vals - med))
        sig = sig if sig > 1e-6 else float(np.std(vals)) + 1e-6
        
        y_clip_lo[h] = -clip_k * sig
        y_clip_hi[h] = clip_k * sig
        
        clipped = np.clip(vals, y_clip_lo[h], y_clip_hi[h])
        final_sig = 1.4826 * np.median(np.abs(clipped - np.median(clipped)))
        y_sigma[h] = final_sig if final_sig > 1e-6 else 1.0

    return center.astype(np.float32), scale.astype(np.float32), y_clip_lo, y_clip_hi, y_sigma


# ======================================================================
# 3. Stateful HRT Recurrent Model (MTL)
# ======================================================================

def cubic_sigmoid(x: torch.Tensor) -> torch.Tensor:
    return torch.sigmoid(x) ** 3

def interpolate(new_push: torch.Tensor, prev_buffer: torch.Tensor, decay: torch.Tensor) -> torch.Tensor:
    return prev_buffer * (1.0 - decay) + new_push * decay

@dataclass
class HRTRNNState:
    block0_buffer: torch.Tensor
    block1_buffer: torch.Tensor
    block2_buffer: torch.Tensor
    block3_buffer: torch.Tensor

    def detach(self):
        """CRITICAL: Cuts the autograd graph between BPTT chunks to prevent OOM."""
        return HRTRNNState(
            block0_buffer=self.block0_buffer.detach(),
            block1_buffer=self.block1_buffer.detach(),
            block2_buffer=self.block2_buffer.detach(),
            block3_buffer=self.block3_buffer.detach()
        )

class HRTRNNCore(nn.Module):
    def __init__(self, input_dim: int, num_horizons: int, state_dim: int = 64, block_dim: int = 32, predecay_dim: int = 16, head_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.state_dim, self.block_dim = state_dim, block_dim
        self.drop = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        
        # Block 0
        self.b0_pass = nn.Linear(input_dim, block_dim)
        self.b0_push = nn.Linear(input_dim, state_dim)
        self.b0_pdec = nn.Linear(input_dim, predecay_dim)
        self.b0_dec  = nn.Linear(predecay_dim, state_dim)
        self.b0_out  = nn.Linear(block_dim + state_dim, block_dim)
        
        # Block 1
        self.b1_pass = nn.Linear(block_dim, block_dim)
        self.b1_push = nn.Linear(block_dim, state_dim)
        self.b1_pdec = nn.Linear(predecay_dim + block_dim, predecay_dim)
        self.b1_dec  = nn.Linear(predecay_dim, state_dim)
        self.b1_out  = nn.Linear(block_dim + state_dim, block_dim)

        # Output Head (Multi-Task)
        self.head = nn.Sequential(
            nn.Linear(block_dim, head_dim), 
            nn.LeakyReLU(0.1), 
            nn.Linear(head_dim, num_horizons)
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.1, nonlinearity="leaky_relu")
                if m.bias is not None: nn.init.zeros_(m.bias)
        # Slow memory decay bias
        for layer in (self.b0_dec, self.b1_dec):
            nn.init.constant_(layer.bias, -1.5)
        # Initial predictions near zero
        nn.init.normal_(self.head[-1].weight, mean=0.0, std=1e-4)

    def init_state(self, batch_size: int, device: torch.device) -> HRTRNNState:
        # batch_size == number of symbols (S)
        return HRTRNNState(
            block0_buffer=torch.zeros(batch_size, self.state_dim, device=device),
            block1_buffer=torch.zeros(batch_size, self.state_dim, device=device),
            block2_buffer=torch.zeros(batch_size, self.state_dim, device=device), # Placeholder for future blocks
            block3_buffer=torch.zeros(batch_size, self.block_dim, device=device),
        )

    def step(self, x_t: torch.Tensor, state: HRTRNNState) -> Tuple[torch.Tensor, HRTRNNState]:
        # x_t shape: (S, F)
        p0 = self.drop(Fnn.leaky_relu(self.b0_pass(x_t), 0.1))
        push0 = self.b0_push(x_t)
        pdec0 = Fnn.leaky_relu(self.b0_pdec(x_t), 0.1)
        dec0 = cubic_sigmoid(self.b0_dec(pdec0))
        buf0 = interpolate(push0, state.block0_buffer, dec0)
        out0 = self.drop(Fnn.leaky_relu(self.b0_out(torch.cat([p0, buf0], dim=-1)), 0.1))
        
        p1 = self.drop(Fnn.leaky_relu(self.b1_pass(out0), 0.1))
        push1 = self.b1_push(out0)
        pdec1 = Fnn.leaky_relu(self.b1_pdec(torch.cat([pdec0, out0], dim=-1)), 0.1)
        dec1 = cubic_sigmoid(self.b1_dec(pdec1))
        buf1 = interpolate(push1, state.block1_buffer, dec1)
        out1 = self.drop(Fnn.leaky_relu(self.b1_out(torch.cat([p1, buf1], dim=-1)), 0.1))

        out = self.head(out1) # Shape: (S, H)
        return out, HRTRNNState(buf0, buf1, state.block2_buffer, state.block3_buffer)

    def forward(self, x: torch.Tensor, state: Optional[HRTRNNState] = None) -> Tuple[torch.Tensor, HRTRNNState]:
        # x is (L, S, F). Time is dimension 0.
        L, S, _ = x.shape
        if state is None:
            state = self.init_state(S, x.device)
            
        outputs = []
        for t in range(L):
            out_t, state = self.step(x[t, :, :], state)
            outputs.append(out_t)
            
        return torch.stack(outputs, dim=0), state # (L, S, H)


# ======================================================================
# 4. Multi-Task Losses (Dense & Cross-Sectional)
# ======================================================================

def masked_mtl_loss(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, delta: float = 2.0) -> Tuple[torch.Tensor, torch.Tensor]:
    # Shapes: (L, S, H)
    valid = (mask > 0) & torch.isfinite(pred) & torch.isfinite(target)
    
    # 1. Huber Loss (Magnitude)
    diff = torch.where(valid, pred - target, torch.zeros_like(pred))
    ad = diff.abs()
    hub = torch.where(ad <= delta, 0.5 * diff * diff, delta * (ad - 0.5 * delta))
    loss_hub = (hub * valid.float()).sum() / torch.clamp(valid.float().sum(), min=1.0)
    
    # 2. Cross-Sectional IC Proxy Loss (Rank / Direction)
    v = valid.float()
    count = v.sum(dim=1, keepdim=True) # Sum across symbols S
    ok = (count.squeeze(1) >= 2.0)
    
    if not torch.any(ok):
        return loss_hub, torch.tensor(0.0, device=pred.device, requires_grad=True)
        
    p0 = torch.where(valid, pred, torch.zeros_like(pred))
    t0 = torch.where(valid, target, torch.zeros_like(target))
    
    mp = p0.sum(dim=1, keepdim=True) / torch.clamp(count, min=1.0)
    mt = t0.sum(dim=1, keepdim=True) / torch.clamp(count, min=1.0)
    
    pc = torch.where(valid, pred - mp, torch.zeros_like(pred))
    tc = torch.where(valid, target - mt, torch.zeros_like(target))
    
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt(torch.clamp((pc * pc).sum(dim=1) * (tc * tc).sum(dim=1), min=1e-6))
    ic = num / den
    
    loss_ic = (1.0 - ic[ok]).mean()
    return loss_hub, loss_ic


# ======================================================================
# 5. Training Loop
# ======================================================================

def train_epoch(model, optimizer, data_dir, days, symbols, features, horizons, bptt_len, scalers, device, use_amp):
    model.train()
    scaler_amp = torch.cuda.amp.GradScaler(enabled=use_amp) if use_amp else None
    x_c, x_s, y_lo, y_hi, y_sig = [s.to(device) for s in scalers]
    
    epoch_losses = []
    
    for day in days:
        X, y, m = load_day_continuous(data_dir, day, symbols, features, horizons)
        
        # CRITICAL: Reset RNN memory to None ONLY at midnight
        rnn_state = None 
        
        for X_chunk, y_chunk, m_chunk in iter_day_tbptt(X, y, m, bptt_len):
            xb = torch.from_numpy(X_chunk).to(device)
            yb = torch.from_numpy(y_chunk).to(device)
            mb = torch.from_numpy(m_chunk).to(device)
            
            # Normalize X and Scale Y
            xb = torch.clamp((xb - x_c) / x_s, -10.0, 10.0)
            yb_norm = torch.clamp(yb, y_lo, y_hi) / y_sig
            
            # CRITICAL: Detach state from previous chunk to avoid backprop OOM
            if rnn_state is not None:
                rnn_state = rnn_state.detach()
                
            optimizer.zero_grad(set_to_none=True)
            
            with amp_autocast_ctx(device, use_amp):
                pred, rnn_state = model(xb, rnn_state)
                l_hub, l_ic = masked_mtl_loss(pred, yb_norm, mb)
                
                # Hybrid Loss: 30% Magnitude, 70% Rank
                loss = l_hub * 0.3 + l_ic * 0.7 
                
            if not torch.isfinite(loss) or loss.item() == 0.0:
                continue
                
            if scaler_amp:
                scaler_amp.scale(loss).backward()
                scaler_amp.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler_amp.step(optimizer)
                scaler_amp.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            
            epoch_losses.append(loss.item())
            
    return float(np.mean(epoch_losses)) if epoch_losses else float('inf')


@torch.no_grad()
def eval_epoch(model, data_dir, days, symbols, features, horizons, bptt_len, scalers, device, use_amp):
    model.eval()
    x_c, x_s, y_lo, y_hi, y_sig = [s.to(device) for s in scalers]
    losses = []
    
    for day in days:
        X, y, m = load_day_continuous(data_dir, day, symbols, features, horizons)
        rnn_state = None
        
        for X_chunk, y_chunk, m_chunk in iter_day_tbptt(X, y, m, bptt_len):
            xb = torch.from_numpy(X_chunk).to(device)
            yb = torch.from_numpy(y_chunk).to(device)
            mb = torch.from_numpy(m_chunk).to(device)
            
            xb = torch.clamp((xb - x_c) / x_s, -10.0, 10.0)
            yb_norm = torch.clamp(yb, y_lo, y_hi) / y_sig
            
            with amp_autocast_ctx(device, use_amp):
                pred, rnn_state = model(xb, rnn_state)
                l_hub, l_ic = masked_mtl_loss(pred, yb_norm, mb)
                loss = l_hub * 0.3 + l_ic * 0.7
                
            if torch.isfinite(loss) and loss.item() != 0.0:
                losses.append(loss.item())
                
    return float(np.mean(losses)) if losses else float('inf')


# ======================================================================
# 6. Main Entry Point
# ======================================================================

def main():
    ap = argparse.ArgumentParser("RNN-Native TBPTT Multi-Task Trainer")
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--model_saved_path", required=True)
    ap.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT")
    ap.add_argument("--features", type=str, default="log_ret_1s,spread_bps,spread_acceleration,rel_volume_60s,deep_impulse_bps,qd_impulse_bps,ofi_instant_bps,energy_skew,temp_imb,apb_60s,ent_gap,day_sin,day_cos")
    ap.add_argument("--horizons", type=str, default="60,300,600", help="Comma separated horizons in seconds")
    
    ap.add_argument("--start_date", required=True)
    ap.add_argument("--end_date", required=True)
    ap.add_argument("--train_span", type=int, default=30)
    ap.add_argument("--val_span", type=int, default=7)
    ap.add_argument("--embargo_days", type=int, default=1)
    
    ap.add_argument("--bptt_len", type=int, default=120, help="TBPTT chunk length (seconds)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--compile", action="store_true", help="Use PyTorch 2.0+ torch.compile()")
    args = ap.parse_args()

    set_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_amp = (device == "cuda")
    
    features = [f.strip() for f in args.features.split(",") if f.strip()]
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    horizons = [int(h) for h in args.horizons.split(",") if h.strip()]
    
    all_days = pd.date_range(args.start_date, args.end_date).strftime("%Y-%m-%d").tolist()
    folds = build_embargoed_folds(all_days, args.train_span, args.val_span, stride=14, embargo_days=args.embargo_days)
    
    Path(args.model_saved_path).mkdir(parents=True, exist_ok=True)
    
    print(f"=== TBPTT RNN Multi-Task | Horizons: {horizons}s | BPTT: {args.bptt_len}s ===")
    
    for fi, fold in enumerate(folds, 1):
        print(f"\n--- FOLD {fi} | Train: {fold.train_days[0]}->{fold.train_days[-1]} | Val: {fold.val_days[0]}->{fold.val_days[-1]} ---")
        
        # 1. Fit robust scalers on first 3 days of train fold to save RAM
        print("Fitting robust scalers...")
        X_samp, Y_samp, M_samp = [], [], []
        for d in fold.train_days[:3]:
            x, y, m = load_day_continuous(Path(args.data_dir), d, symbols, features, horizons)
            X_samp.append(x); Y_samp.append(y); M_samp.append(m)
        
        x_c, x_s, y_lo, y_hi, y_sig = fit_robust_scalers(
            np.concatenate(X_samp, axis=0), np.concatenate(Y_samp, axis=0), np.concatenate(M_samp, axis=0)
        )
        scalers = [torch.tensor(t, device=device) for t in (x_c, x_s, y_lo, y_hi, y_sig)]
        del X_samp, Y_samp, M_samp; gc.collect()
        
        # 2. Initialize Model
        model = HRTRNNCore(input_dim=len(features), num_horizons=len(horizons)).to(device)
        
        # CRITICAL SPEEDUP: Fuses Python loops into a highly optimized C++ graph. ~5x faster.
        if args.compile and hasattr(torch, "compile") and device == "cuda":
            print("Compiling model (PyTorch 2.0+)...")
            model = torch.compile(model)
            
        optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
        
        best_val, wait = float('inf'), 0
        
        # 3. Training Loop
        for ep in range(1, args.epochs + 1):
            t0 = time.perf_counter()
            tr_loss = train_epoch(model, optimizer, Path(args.data_dir), fold.train_days, symbols, features, horizons, args.bptt_len, scalers, device, use_amp)
            val_loss = eval_epoch(model, Path(args.data_dir), fold.val_days, symbols, features, horizons, args.bptt_len, scalers, device, use_amp)
            
            scheduler.step(val_loss)
            
            mark = ""
            if val_loss < best_val:
                best_val = val_loss
                torch.save(model.state_dict(), Path(args.model_saved_path) / f"best_model_fold{fi}.pt")
                wait, mark = 0, "★"
            else:
                wait += 1
                
            print(f"Ep {ep:02d} | Tr: {tr_loss:.4f} | Va: {val_loss:.4f} | LR: {optimizer.param_groups[0]['lr']:.1e} | Time: {time.perf_counter()-t0:.1f}s {mark}")
            if wait >= 5: 
                print("Early stopping triggered.")
                break

if __name__ == "__main__":
    main()