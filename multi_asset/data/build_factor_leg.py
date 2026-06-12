"""F0 FACTOR LEG: frozen single-asset BTCUSDT REG_arch inference on the
multi-asset panel grid.

Per panel day this builds the single-asset model's EXACT inputs (64 hand
features + 20-level raw-LOB tensor + 6-dim regime prior, per-UTC-calendar-day
cold-start semantics — identical to the training `build_npz_for_day` pipeline)
at OUR panel prediction timestamps (stride-180 grid over the seq_cache 1s bar
grid, panel day = ~14:05 UTC D-1 .. 13:54:59 D), runs the frozen REG_arch
(walk-forward fold-aware checkpoints) and saves per day:

    <OUT_DIR>/<day>.npz
        ts        (n,)    int64   ns — exact subset of the panel pred grid
        f_hat     (n,)    float32 de-normalized q50 (RAW log-return units)
        h_btc     (n,32)  float16 penultimate embedding (model.encode output)
        q10_z/q50_z/q90_z (n,) float32 quantiles in z space (diagnostics)
        fold      (n,)    int8    which single-asset checkpoint was used
        insample  (n,)    uint8   1 = row date < 2025-02-09 (inside the fold-0
                                  checkpoint's own train/val period — usable as
                                  residual-model TRAIN input only, never for
                                  panel test-window evaluation)
        meta      ()      str     json provenance (ckpt, stats, conventions)

Checkpoint provenance (IMPORTANT — documented data-loss event)
--------------------------------------------------------------
The original production REG_arch state-dict checkpoints
(`quant_research/experiments/v5push/singh_track_reg_arch/fold_*/best_model.pt`,
trained 2026-05-14, standalone P=+0.0646) were OVERWRITTEN on 2026-06-10 by an
R3 run (dir since renamed `singh_track_reg_arch_OVERWRITTEN_BY_R3_20260610`;
topk/ also partially clobbered, fold_2 fully). The ONLY surviving frozen
artifact is the validated TorchScript inference package
(`~/Desktop/reg_arch_inference/`, end-to-end validated 2026-05-20: 14 days,
live P=+0.094, matches production). This script therefore reconstructs the
eager `DualPathLOBModelV3` from `model_traced.pt::state_dict()` (strict load,
forward-equivalence asserted by --verify-model) so that the penultimate
embedding (`model.encode`) is accessible. Traced ckpts + per-fold norm stats
are staged at <CKPT_ROOT>.

Input-construction parity
-------------------------
* Features are computed PER UTC CALENDAR DAY with cold-start at 00:00 UTC —
  bit-identical to training (`build_npz_for_day` is called with input_len=1 /
  stride=1 to obtain the per-bar feature/raw/regime arrays through the exact
  production code path, incl. nan_to_num + clip(+-1000) and the fp16
  round-trip of X_raw that training NPZs had via quantize_features=True).
* Two consecutive calendar days are concatenated so panel windows that cross
  UTC midnight (~3-4 rows/day, second-of-day(window end) < 599) are still
  servable; all other windows are bit-identical to training-era windows.
* X normalization: TRAINING convention — safe_std = where(x_std<1e-4, 1.0,
  x_std); z = clip((X-mean)/safe_std, +-10) (LOBDatasetV2). 7/64 features have
  x_std < 1e-4; RevIN makes the model affine-invariant per window so this only
  matters in >10-sigma clip tails. Toggle --raw-std reproduces the inference
  package's plain division instead.
* f_hat = q50_z * y_sigma(fold) + y_median(fold) — raw log-return units.

Fold->checkpoint mapping (strictly causal on every panel TEST row)
------------------------------------------------------------------
Single-asset walk-forward: fold f's ckpt saw data only up to its val end.
    fold 0: train <=2024-12-10, val <=2025-02-08  -> causal for rows >= 2025-02-09
    fold 1: data <=2025-04-09                     -> causal for rows >= 2025-04-10
    fold 2: data <=2025-06-10                     -> causal for rows >= 2025-06-11
Date-based selection (same as the inference package):
    [2025-02-09 .. 2025-04-09] -> fold 0
    [2025-04-10 .. 2025-06-10] -> fold 1
    [2025-06-11 .. )           -> fold 2 (causal extrapolation after 2025-09-30)
    (.. 2025-02-08]            -> fold 0, flagged insample=1
Panel folds (train_cross_asset.FOLDS over the 487-day window 20240601..20250930)
have test windows at day idx 272:312 / 352:392 / 432:472 = 2025-02-28..2025-04-08,
2025-05-19..2025-06-27, 2025-08-07..2025-09-15 — ALL >= 2025-02-09, so every
panel test row gets a checkpoint trained strictly before it. insample=1 rows
(2024-06-01..2025-02-08) occur only in panel train/val portions.

Usage (server, CPU-only — a GPU training chain is running)
----------------------------------------------------------
  # 1. model reconstruction equivalence (eager-from-traced == traced):
  nice -n 10 python multi_asset/data/build_factor_leg.py --verify-model
  # 2. reproduction gate vs saved single-asset production preds (3 days):
  nice -n 10 python multi_asset/data/build_factor_leg.py --gate-repro
  # 3. sample panel days (validation prints + plausibility vs realized y):
  nice -n 10 python multi_asset/data/build_factor_leg.py --days 20250415 20250203 20250811
  # 4. full batch (idempotent, atomic writes):
  nohup nice -n 10 python multi_asset/data/build_factor_leg.py --all \
      >> <OUT_DIR>/build.log 2>&1 &
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import os.path as p
import sys
import time
import warnings
from io import StringIO

import numpy as np
import pandas as pd
import torch

# oneDNN conv1d "could not create a primitive" workaround (same as the
# validated inference package — negligible speed cost at our batch sizes).
if hasattr(torch.backends, "mkldnn"):
    torch.backends.mkldnn.enabled = False

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)

from src.features.pipeline import build_npz_for_day              # noqa: E402
from src.features.resample import resample_lob_to_1s             # noqa: E402
from src.model.dual_path_model_v3 import DualPathLOBModelV3      # noqa: E402
from multi_asset.data.seq_panel_dataset import HORIZON, PRED_STRIDE  # noqa: E402

# --------------------------------------------------------------------- paths
BOOK25_ROOT = "/mnt/storage/share/23-25-BTCUSDT/book_snapshot_25"   # READ-ONLY
TRADES_ROOT = "/mnt/storage/share/23-25-BTCUSDT/trades"             # READ-ONLY
MA_ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
SEQ_DIR = MA_ROOT + "/multi_asset/exports/seq_cache"
CKPT_ROOT = MA_ROOT + "/multi_asset/exports/factor_leg_ckpt"        # staged traced pkg
OUT_DIR = MA_ROOT + "/multi_asset/exports/factor_leg"
# production single-asset test preds (staged next to ckpts) for --gate-repro
REPRO_PREDS = CKPT_ROOT + "/standalone_eval"

N_LVL = 25          # book levels read from share (model raw path uses first 20)
WINDOW = 600        # model input length (1s bars)
EMB_DIM = 32        # d_model — penultimate embedding width

# REG_arch constructor config. Base keys mirror the trainer's checkpoint
# config extractor (verified against singh_daqh_lambda0/fold_0/best_model.pt
# 'config', same era/pipeline); + the REG_arch FiLM multi-stage flag, which the
# extractor predates (REG_arch state_dict has 18 film_gate_* keys).
REG_ARCH_CONFIG = dict(
    n_features=64, n_levels=20, d_model=32, d_raw=16,
    n_mask_blocks=1, n_cross_layers=1, patch_size=5,
    attn_nhead=2, attn_d_ff=64, d_prior=6, dropout=0.2,
    n_horizons=1, n_symbols=1,
    use_monotonic_quantile=True, use_masknet=False, use_gdcn=True,
    use_raw_path=True, use_attention=False, use_conv=False, use_revin=True,
    use_channel_mix_conv=True, use_level_attention_pool=True,
    use_patch_attention_pool=False, use_ppnet_gate=True, use_multi_scale=False,
    backbone_kind="conformer",
    backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
    use_regime_film=False, fusion_kind="concat", use_sign_head=False,
    use_direction_aware_head=True,
    use_film_multistage=True,                      # <- REG_arch
)

# fold checkpoint date mapping (see module docstring). end date inclusive.
FOLD_DATE_RANGES = [(0, "2025-02-09", "2025-04-09"),
                    (1, "2025-04-10", "2025-06-10"),
                    (2, "2025-06-11", "9999-12-31")]
INSAMPLE_BEFORE = "2025-02-09"

# exact production 64-feature schema (order matters; assert against pipeline)
EXPECTED_FEATURES = [
    "log_return_1s", "log_return_5s", "log_return_30s", "spread_bps",
    "spread_change", "obi_L1", "obi_L5", "obi_L10", "obi_L25", "obi_L1_delta",
    "bid_depth_L5", "ask_depth_L5", "bid_depth_L25", "ask_depth_L25",
    "depth_ratio_L5", "weighted_price_bid_L10", "weighted_price_ask_L10",
    "price_pressure", "realized_vol_30s", "realized_vol_60s",
    "realized_vol_300s", "depth_flow_ratio_30s", "bid_slope_L10",
    "ask_slope_L10", "bid_concentration", "ask_concentration",
    "bid_amt_ratio_L0", "ask_amt_ratio_L0", "bid_amt_ratio_L1",
    "ask_amt_ratio_L1", "bid_amt_ratio_L2", "ask_amt_ratio_L2",
    "bid_amt_ratio_L3", "ask_amt_ratio_L3", "bid_amt_ratio_L4",
    "ask_amt_ratio_L4", "second_of_day_sin", "second_of_day_cos",
    "delta_bid_depth_L5", "delta_ask_depth_L5", "net_order_flow_L5",
    "delta_obi_L5_5s", "delta_pressure_5s", "buy_volume_1s", "sell_volume_1s",
    "net_trade_flow_1s", "trade_imbalance_1s", "cumulative_net_flow_30s",
    "cumulative_net_flow_300s", "trade_intensity_30s", "vwap_return_1s",
    "kyle_lambda_30s", "microprice_dev_bps", "roll_spread_60s", "vpin_60s",
    "vpin_300s", "book_pressure_imbalance", "price_impact_30s",
    "net_flow_x_spread", "net_flow_x_vol", "obi_L5_rank_1h",
    "net_flow_rank_1h", "large_trade_arrival_60s", "book_pressure_delta_60s",
]

_BOOK_COLS = ["timestamp"]
for _i in range(N_LVL):
    _BOOK_COLS += [f"asks[{_i}].price", f"asks[{_i}].amount",
                   f"bids[{_i}].price", f"bids[{_i}].amount"]


# ------------------------------------------------------------------ raw read
def _read_gz_csv_robust(path, usecols=None):
    """gzip CSV reader robust to truncated streams (mirrors the validated
    inference package's `_read_gzipped_csv_robust`)."""
    try:
        try:
            return pd.read_csv(path, usecols=usecols, engine="pyarrow")
        except Exception:
            return pd.read_csv(path, usecols=usecols)
    except (EOFError, OSError):
        header, rows = None, []
        try:
            with gzip.open(path, "rt", errors="replace") as f:
                for line in f:
                    if header is None:
                        header = line
                        continue
                    rows.append(line)
        except (EOFError, OSError):
            pass
        if header is None or not rows:
            raise ValueError(f"{path}: no readable content")
        df = pd.read_csv(StringIO("".join([header] + rows)), on_bad_lines="skip")
        return df[usecols] if usecols else df


def read_book_day(date_str: str) -> pd.DataFrame:
    path = p.join(BOOK25_ROOT, date_str, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    return _read_gz_csv_robust(path, usecols=_BOOK_COLS)


def read_trades_day(date_str: str) -> pd.DataFrame:
    """Read + normalise trades exactly like the production multi-day pipeline
    (`_read_and_normalise_trades`): amount->size, id->exec_id, side->Title."""
    path = p.join(TRADES_ROOT, date_str, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    df = _read_gz_csv_robust(path)
    ren = {}
    if "amount" in df.columns and "size" not in df.columns:
        ren["amount"] = "size"
    if "id" in df.columns and "exec_id" not in df.columns:
        ren["id"] = "exec_id"
    if ren:
        df.rename(columns=ren, inplace=True)
    if "side" in df.columns:
        df["side"] = df["side"].astype(str).str.title()
    return df


# -------------------------------------------------- per-calendar-day features
def build_calendar_day(date_str: str) -> dict:
    """Per-bar (1s) feature/raw/regime arrays for one UTC calendar day, built
    through the EXACT production pipeline (cold start at 00:00 UTC, identical
    to the training NPZ builder). input_len=1/stride=1 turns the production
    windower into a per-bar emitter — feature values are bit-identical because
    features are computed on the full day BEFORE windowing.
    """
    t0 = time.time()
    raw_book = read_book_day(date_str)
    df_1s = resample_lob_to_1s(raw_book, n_levels=N_LVL)
    del raw_book

    # strip rows outside the folder date (mirrors multi_day_pipeline)
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1_000_000)
    day_end_us = day_start_us + 86_400 * 1_000_000
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    if len(df_1s) < WINDOW:
        raise ValueError(f"{date_str}: only {len(df_1s)} 1s rows")

    trades_df = read_trades_day(date_str)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # stride<horizon warning (n/a here)
        res = build_npz_for_day(
            df_1s, trades_df=trades_df, horizons_sec=[600],
            input_len=1, stride=1, n_levels=N_LVL,
            include_ridge_features=True, include_regime_prior=True,
            quantize_features=True,              # X_raw fp16 round-trip == training
        )
    del df_1s, trades_df

    feats = [str(f) for f in res["features"]]
    if feats != EXPECTED_FEATURES:
        raise RuntimeError(
            f"{date_str}: feature schema drift vs production "
            f"({len(feats)} cols; first diff at "
            f"{next((i for i, (a, b) in enumerate(zip(feats, EXPECTED_FEATURES)) if a != b), 'len')})")

    out = {
        "sec": (res["timestamps"] // 1_000_000).astype(np.int64),   # epoch s
        "F": res["X"][:, 0, :].astype(np.float32),                  # (T,64)
        "R": res["X_raw"][:, 0].astype(np.float32),                 # (T,20,4) fp16->fp32
        "RP": res["regime_prior"].astype(np.float32),               # (T,6)
        "secs_build": time.time() - t0,
    }
    if not np.all(np.diff(out["sec"]) == 1):
        # contiguous by construction (resample full grid); guard anyway
        raise RuntimeError(f"{date_str}: 1s grid not contiguous after strip")
    return out


class CalendarCache:
    """Keep the most recent K calendar days (consecutive panel days share one)."""

    def __init__(self, k: int = 3):
        self.k = k
        self._d: dict[str, dict] = {}

    def get(self, date_str: str) -> dict:
        if date_str not in self._d:
            if len(self._d) >= self.k:
                self._d.pop(sorted(self._d)[0])
            self._d[date_str] = build_calendar_day(date_str)
        return self._d[date_str]


def concat_days(cds: list[dict]):
    sec = np.concatenate([c["sec"] for c in cds])
    if not np.all(np.diff(sec) > 0):
        raise RuntimeError("calendar-day concat: seconds not strictly increasing")
    F = np.concatenate([c["F"] for c in cds], axis=0)
    R = np.concatenate([c["R"] for c in cds], axis=0)
    RP = np.concatenate([c["RP"] for c in cds], axis=0)
    return sec, F, R, RP


def locate_windows(sec: np.ndarray, target_secs: np.ndarray):
    """Indices of complete 600s windows ending exactly at target seconds.
    Returns (ok mask over targets, end positions for ok targets)."""
    pos = np.searchsorted(sec, target_secs)
    ok = (pos < sec.shape[0])
    pos_c = np.clip(pos, 0, sec.shape[0] - 1)
    ok &= (sec[pos_c] == target_secs) & (pos_c >= WINDOW - 1)
    start = np.clip(pos_c - (WINDOW - 1), 0, None)
    ok &= (sec[start] == target_secs - (WINDOW - 1))   # both days contiguous
    return ok, pos_c[ok]


# ------------------------------------------------------------------- model
def fold_for_date(date_str: str):
    """(fold_id, insample) for a UTC date string."""
    if date_str < INSAMPLE_BEFORE:
        return 0, True
    for f, d0, d1 in FOLD_DATE_RANGES:
        if d0 <= date_str <= d1:
            return f, False
    return 2, False


class FoldModel:
    def __init__(self, fold: int, device: str, raw_std: bool = False):
        self.fold = fold
        cdir = p.join(CKPT_ROOT, f"fold_{fold}")
        self.traced_path = p.join(cdir, "model_traced.pt")
        traced = torch.jit.load(self.traced_path, map_location="cpu")
        sd = dict(traced.state_dict())
        # the traced artifact wraps the model under a single prefix (e.g. "m.")
        first = {k.split(".", 1)[0] for k in sd}
        if len(first) == 1 and all("." in k for k in sd):
            pre = next(iter(first)) + "."
            sd = {k[len(pre):]: v for k, v in sd.items()}
        model = DualPathLOBModelV3(**REG_ARCH_CONFIG)
        missing, unexpected = model.load_state_dict(sd, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                f"fold {fold}: eager<-traced state mismatch "
                f"missing={missing[:5]} unexpected={unexpected[:5]}")
        model.eval()
        self.model = model.to(device)
        self.traced = traced            # kept on CPU for --verify-model
        self.device = device

        n = np.load(p.join(cdir, "norm_params.npz"))
        x_std = n["x_std"].astype(np.float32)
        if not raw_std:                  # TRAINING convention (LOBDatasetV2)
            x_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
        self.x_mean = n["x_mean"].astype(np.float32)
        self.x_std = x_std
        self.y_sigma = float(n["y_sigma"])
        self.y_median = float(n["y_median"])

    def normalize(self, Fw: np.ndarray) -> np.ndarray:
        return np.clip((Fw - self.x_mean) / self.x_std, -10.0, 10.0).astype(np.float32)

    @torch.no_grad()
    def forward_windows(self, sec, F, R, RP, end_pos, batch: int = 256):
        """Gather windows at end positions, run encode + head. Returns
        (q (n,3) z-space, h (n,32) f32)."""
        n = end_pos.shape[0]
        q_all = np.zeros((n, 3), np.float32)
        h_all = np.zeros((n, EMB_DIM), np.float32)
        offs = np.arange(-(WINDOW - 1), 1)
        for i in range(0, n, batch):
            ep = end_pos[i:i + batch]
            idx = ep[:, None] + offs[None, :]                    # (b, 600)
            xf = torch.from_numpy(self.normalize(F[idx])).to(self.device)
            xr = torch.from_numpy(R[idx]).to(self.device)
            rp = torch.from_numpy(RP[ep]).to(self.device)
            h = self.model.encode(x_feat=xf, x_raw=xr, regime_prior=rp)
            out = self.model.quantile_heads[0](h)
            q_all[i:i + batch] = out["quantiles"].cpu().numpy()
            h_all[i:i + batch] = h.cpu().numpy()
        return q_all, h_all

    def denorm(self, q50_z: np.ndarray) -> np.ndarray:
        return (q50_z * self.y_sigma + self.y_median).astype(np.float32)


class ModelBank:
    def __init__(self, device: str, raw_std: bool = False):
        self.device, self.raw_std = device, raw_std
        self._m: dict[int, FoldModel] = {}

    def get(self, fold: int) -> FoldModel:
        if fold not in self._m:
            print(f"  [model] loading fold {fold} (eager<-traced) ...", flush=True)
            self._m[fold] = FoldModel(fold, self.device, self.raw_std)
        return self._m[fold]


# ------------------------------------------------------------- panel build
def list_panel_days(start=None, end=None):
    days = sorted(int(f[:-4]) for f in os.listdir(SEQ_DIR)
                  if f.endswith(".npz") and f[:-4].isdigit())
    return [d for d in days if (start is None or d >= start)
            and (end is None or d <= end)]


def build_panel_day(day: int, cache: CalendarCache, bank: ModelBank,
                    out_dir: str, force=False, batch=256, verbose=True):
    out = p.join(out_dir, f"{day}.npz")
    if (not force) and p.exists(out):
        return None
    t0 = time.time()
    seq = np.load(p.join(SEQ_DIR, f"{day}.npz"))
    ts = seq["ts"].astype(np.int64)                          # (T,) ns 1s grid
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {day}: seq ts grid not contiguous")
    base = np.arange(0, ts.shape[0] - HORIZON, PRED_STRIDE)  # pred-candidate grid
    tgt_ns = ts[base]
    tgt_sec = grid_secs[base]

    # calendar days covering [first window start, last window end]
    d0 = dt.datetime.fromtimestamp(int(tgt_sec[0]) - (WINDOW - 1),
                                   dt.timezone.utc).date()
    d1 = dt.datetime.fromtimestamp(int(tgt_sec[-1]), dt.timezone.utc).date()
    dates, d = [], d0
    while d <= d1:
        dates.append(d.isoformat())
        d += dt.timedelta(days=1)
    sec, F, R, RP = concat_days([cache.get(ds) for ds in dates])

    ok, end_pos = locate_windows(sec, tgt_sec)
    kept_ns, kept_sec = tgt_ns[ok], tgt_sec[ok]

    # per-row fold by UTC date of the prediction timestamp
    row_dates = np.array([dt.datetime.fromtimestamp(int(s), dt.timezone.utc)
                          .strftime("%Y-%m-%d") for s in kept_sec])
    folds = np.zeros(kept_sec.shape[0], np.int8)
    insample = np.zeros(kept_sec.shape[0], np.uint8)
    for ds in np.unique(row_dates):
        f, ins = fold_for_date(str(ds))
        m = row_dates == ds
        folds[m], insample[m] = f, ins

    q = np.zeros((kept_sec.shape[0], 3), np.float32)
    h = np.zeros((kept_sec.shape[0], EMB_DIM), np.float32)
    f_hat = np.zeros(kept_sec.shape[0], np.float32)
    for f in np.unique(folds):
        m = folds == f
        fm = bank.get(int(f))
        q[m], h[m] = fm.forward_windows(sec, F, R, RP, end_pos[m], batch=batch)
        f_hat[m] = fm.denorm(q[m, 1])

    meta = dict(
        day=int(day), ckpt_root=CKPT_ROOT, ckpt="model_traced.pt(state->eager)",
        model="REG_arch DualPathLOBModelV3", emb="encode() pre-head d=32",
        x_norm=("raw_std" if bank.raw_std else "safe_std<1e-4->1.0") + ",clip10",
        f_hat_units="raw log-return (q50_z*y_sigma+y_median)",
        window=WINDOW, stride=PRED_STRIDE, horizon=HORIZON,
        fold_map=FOLD_DATE_RANGES, insample_before=INSAMPLE_BEFORE,
        calendar_days=dates, built=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    tmp = out + ".tmp.npz"
    np.savez(tmp, ts=kept_ns, f_hat=f_hat, h_btc=h.astype(np.float16),
             q10_z=q[:, 0], q50_z=q[:, 1], q90_z=q[:, 2],
             fold=folds, insample=insample, meta=json.dumps(meta))
    os.replace(tmp, out)

    st = dict(day=day, n_grid=int(base.shape[0]), n_out=int(ok.sum()),
              secs=time.time() - t0,
              fhat_mean_bps=float(f_hat.mean() * 1e4),
              fhat_std_bps=float(f_hat.std() * 1e4),
              finite=float(np.isfinite(f_hat).mean()),
              h_finite=float(np.isfinite(h).mean()))
    if verbose:
        print(f"  [day {day}] {st['n_out']}/{st['n_grid']} rows, folds "
              f"{sorted(set(folds.tolist()))}, f_hat {st['fhat_mean_bps']:+.3f}"
              f"±{st['fhat_std_bps']:.3f} bps, {st['secs']:.0f}s", flush=True)
    return st


# ------------------------------------------------------------------- gates
def verify_model(device="cpu"):
    """Gate 0: eager-from-traced == traced on random inputs; manual
    encode+head == full forward."""
    torch.manual_seed(0)
    ok_all = True
    for f in (0, 1, 2):
        fm = FoldModel(f, device)
        xf = torch.randn(4, WINDOW, 64)
        xr = torch.randn(4, WINDOW, 20, 4)
        rp = torch.randn(4, 6)
        with torch.no_grad():
            qt = fm.traced(xf, xr, rp)
            qe = fm.model(x_feat=xf, x_raw=xr, regime_prior=rp)["quantiles"]
            h = fm.model.encode(x_feat=xf, x_raw=xr, regime_prior=rp)
            qm = fm.model.quantile_heads[0](h)["quantiles"]
        d_te = (qt - qe).abs().max().item()
        d_em = (qe - qm).abs().max().item()
        ok = d_te < 1e-5 and d_em < 1e-7
        ok_all &= ok
        print(f"[verify fold {f}] |traced-eager|max={d_te:.2e} "
              f"|forward-encode+head|max={d_em:.2e}  -> {'OK' if ok else 'FAIL'}",
              flush=True)
    print(f"[verify] {'ALL OK' if ok_all else 'FAILED'}", flush=True)
    return ok_all


def gate_repro(days_by_fold=None, device="cpu", batch=256, raw_std=False):
    """Gate A: rebuild inputs at the saved single-asset production pred
    timestamps and reproduce the saved q50_z. Saved eval ts = window-end + 1s
    (npz_v4 windows end at second 599; eval ts at second 600 — verified)."""
    days_by_fold = days_by_fold or {0: ["2025-02-20"], 1: ["2025-05-06"],
                                    2: ["2025-07-15"]}
    cache = CalendarCache(k=2)
    results = []
    for f, days in days_by_fold.items():
        sp = np.load(p.join(REPRO_PREDS, f"fold_{f}_test_preds.npz"),
                     allow_pickle=True)
        ts_us = sp["timestamps"].astype(np.int64)
        preds = sp["predictions"].astype(np.float32)
        mask = sp["mask"].astype(bool)
        fm = FoldModel(f, device, raw_std=raw_std)
        for ds in days:
            day_us0 = int(pd.Timestamp(ds, tz="UTC").timestamp() * 1e6)
            sel = (ts_us >= day_us0) & (ts_us < day_us0 + 86_400_000_000) & mask
            if sel.sum() == 0:
                print(f"[gate-repro] fold {f} {ds}: no saved preds — skip", flush=True)
                continue
            best = None
            for off in (1, 0):       # saved ts = window_end + off seconds
                tgt = ts_us[sel] // 1_000_000 - off
                cd = cache.get(ds)
                ok, end_pos = locate_windows(cd["sec"], tgt)
                if ok.mean() < 0.5:
                    continue
                q, _ = fm.forward_windows(cd["sec"], cd["F"], cd["R"], cd["RP"],
                                          end_pos, batch=batch)
                ref = preds[sel][ok]
                c50 = float(np.corrcoef(q[:, 1], ref[:, 1])[0, 1])
                mad = float(np.abs(q[:, 1] - ref[:, 1]).max())
                cand = dict(fold=f, day=ds, offset=off, n=int(ok.sum()),
                            corr_q50=c50, corr_q10=float(np.corrcoef(q[:, 0], ref[:, 0])[0, 1]),
                            corr_q90=float(np.corrcoef(q[:, 2], ref[:, 2])[0, 1]),
                            max_abs_dq50=mad)
                if best is None or cand["corr_q50"] > best["corr_q50"]:
                    best = cand
            if best:
                results.append(best)
                print(f"[gate-repro] fold {best['fold']} {best['day']} "
                      f"off={best['offset']} n={best['n']} "
                      f"corr_q50={best['corr_q50']:+.5f} "
                      f"(q10 {best['corr_q10']:+.4f} q90 {best['corr_q90']:+.4f}) "
                      f"max|dq50|={best['max_abs_dq50']:.4f}", flush=True)
    if results:
        cmin = min(r["corr_q50"] for r in results)
        print(f"[gate-repro] min corr_q50 = {cmin:+.5f}  -> "
              f"{'PASS (>0.99)' if cmin > 0.99 else 'FAIL'}", flush=True)
    return results


def plausibility(days, out_dir):
    """Gate B: f_hat vs realized panel y_600 (BTC row of seq_cache) on built days."""
    fh_all, y_all = [], []
    for d in days:
        z = np.load(p.join(out_dir, f"{d}.npz"), allow_pickle=True)
        seq = np.load(p.join(SEQ_DIR, f"{d}.npz"))
        ts = seq["ts"].astype(np.int64)
        y_btc = seq["y"][0]                                  # (T,) BTC row
        pos = {int(t): i for i, t in enumerate(ts)}
        idx = np.array([pos[int(t)] for t in z["ts"]])
        y = y_btc[idx]
        m = np.isfinite(y) & np.isfinite(z["f_hat"])
        fh_all.append(z["f_hat"][m]); y_all.append(y[m])
    fh, y = np.concatenate(fh_all), np.concatenate(y_all)
    P = float(np.corrcoef(fh, y)[0, 1])
    from scipy.stats import spearmanr
    S = float(spearmanr(fh, y).correlation)
    sig = float(fh.std() / y.std())
    print(f"[plausibility] {len(days)} days n={fh.size}: P={P:+.4f} S={S:+.4f} "
          f"sigma_ratio={sig:.4f} fhat_mean={fh.mean()*1e4:+.3f}bps", flush=True)
    return P, S


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--verify-model", action="store_true")
    g.add_argument("--gate-repro", action="store_true")
    g.add_argument("--days", type=int, nargs="+",
                   help="panel days YYYYMMDD (validation mode + plausibility)")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--raw-std", action="store_true",
                    help="inference-package std convention (no safe-std rule)")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    if args.verify_model:
        sys.exit(0 if verify_model(args.device) else 1)
    if args.gate_repro:
        res = gate_repro(device=args.device, batch=args.batch,
                         raw_std=args.raw_std)
        ok = res and min(r["corr_q50"] for r in res) > 0.99
        sys.exit(0 if ok else 1)

    os.makedirs(args.out_dir, exist_ok=True)
    days = args.days if args.days else list_panel_days(args.start, args.end)
    print(f"[factor_leg] {len(days)} panel day(s) -> {args.out_dir} "
          f"(device={args.device}, threads={args.threads})", flush=True)
    cache, bank = CalendarCache(k=3), ModelBank(args.device, args.raw_std)
    t0, n_done, n_skip, n_fail = time.time(), 0, 0, 0
    for i, d in enumerate(days):
        try:
            st = build_panel_day(d, cache, bank, args.out_dir,
                                 force=args.force, batch=args.batch,
                                 verbose=bool(args.days) or n_done % 5 == 0)
        except Exception as e:
            n_fail += 1
            print(f"  [warn] day {d} failed: {type(e).__name__}: {e}", flush=True)
            continue
        if st is None:
            n_skip += 1
            continue
        n_done += 1
        if n_done % 10 == 0 or i == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el
            eta = (len(days) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:4d}/{len(days)}] built={n_done} skip={n_skip} "
                  f"fail={n_fail}  {el/60:.1f} min, ETA {eta/60:.0f} min", flush=True)

    meta = dict(ckpt_root=CKPT_ROOT, out_dir=args.out_dir,
                n_done=n_done, n_skip=n_skip, n_fail=n_fail,
                fold_map=FOLD_DATE_RANGES, insample_before=INSAMPLE_BEFORE,
                x_norm="raw_std" if args.raw_std else "safe_std",
                window=WINDOW, stride=PRED_STRIDE, horizon=HORIZON)
    with open(p.join(args.out_dir, "build_meta.json"), "w") as fjs:
        json.dump(meta, fjs, indent=2)
    print(f"[factor_leg] done: built={n_done} skip={n_skip} fail={n_fail}",
          flush=True)
    if args.days:
        try:
            plausibility([d for d in days
                          if p.exists(p.join(args.out_dir, f"{d}.npz"))],
                         args.out_dir)
        except Exception as e:
            print(f"[plausibility] failed: {e}", flush=True)


if __name__ == "__main__":
    main()
