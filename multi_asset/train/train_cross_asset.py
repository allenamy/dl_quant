"""Cross-asset attention panel trainer for crypto y_600.

Trains `CrossAssetPanelModel` directly on the per-window feature cache
(`multi_asset/exports/panel_cache/<sym>.npz`) — no heavy sequence pipeline.

Leakage-safe walk-forward, SAME fold layout as the Ridge gate (xsec_ridge.py /
a2_ridge_snr.json):
    FOLDS = [(tr 0:250, te 272:312), (80:330, te 352:392), (160:410, te 432:472)]
over unique sorted days, 1-day embargo (train day idx < te_start - 1). A val
slice is carved from the TRAIN tail (last `VAL_DAYS` train days) for early stop.

Per fold, everything fit on TRAIN only:
    - X standardize: per-feature mean/std over all TRAIN asset-rows (clip +-10).
    - y MAD-sigma: per-asset, median(|y - median(y)|)*1.4826 over TRAIN rows.
      Predict normalized y (y / sig_asset). (We use the RAW per-asset target, NOT
      the cross-sectionally-demeaned residual — the model gets the full panel and
      the cross-sectional aux loss handles the relative-ranking objective.)

Loss (masked over valid assets per timestamp):
    0.5 * Huber(pred, y_norm) + 0.5 * cross_sectional_pearson_aux
where the aux = mean over timesteps of (1 - Pearson(pred, y_norm) across the
valid assets at that timestamp). Adapted from src/losses/cross_sectional_ic_loss.

Eval (CLEAN test rows, clean600):
    - per-asset Pearson + Spearman (pooled over the fold's clean test rows),
      averaged across assets.
    - cross-sectional rank-IC: per-timestamp Spearman across the >=5 valid clean
      assets, mean over timestamps. THIS is the number to beat (Ridge 0.0403).
    - sigma_pred / sigma_y health check.

Usage:
    python3 multi_asset/train/train_cross_asset.py --smoke   # fold 0, 5 epochs
    python3 multi_asset/train/train_cross_asset.py           # full 3-fold (controller)
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.model.cross_asset_panel import CrossAssetPanelModel, count_params  # noqa: E402

# --- server-local paths (cache reads are fast) ---
CACHE = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
         "multi_asset/exports/panel_cache")
EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")

SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]

DVOL_FILE = p.join(CACHE, "dollar_vol.npz")   # train-fixed cap weights (Phase 1)

# SAME fold layout as the Ridge gate (a2_ridge_snr.json / xsec_ridge.py).
FOLDS = [dict(tr=(0, 250), te=(272, 312)),
         dict(tr=(80, 330), te=(352, 392)),
         dict(tr=(160, 410), te=(432, 472))]
EMBARGO = 1
VAL_DAYS = 20            # carve val from the train tail (before embargo gap)

# --- recipe ---
D_MODEL = 64            # d=64,L=2 -> ~75K params (in the 50-150K budget; low-SNR safe)
N_LAYERS = 2
N_HEAD = 4
DROPOUT = 0.2
N_OUT = 1               # 1 = predict normalized q50 (quantiles optional, see --quantiles)
LR = 1e-3
WD = 1e-4
BATCH_TS = 256          # a batch = this many timestamps
MAX_EPOCHS = 30
PATIENCE = 6
HUBER_DELTA = 2.0
LAMBDA_HUBER = 0.5
LAMBDA_XSEC = 0.5
SIGMA_GATE = 0.02       # reject BEST epochs whose sigma_pred/sigma_y collapses
SEED = 42

DEV = "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------------------------------------------------------- #
# Panel assembly (aligned on common ts) — mirrors xsec_ridge.build_panel.
# --------------------------------------------------------------------------- #
def load_sym(sym):
    d = np.load(p.join(CACHE, f"{sym}.npz"))
    return d["X"], d["y"], d["day"], d["ts"], d["clean600"]


def load_cap_weights():
    """Train-fixed per-asset dollar-volume cap weights for the Phase-1 market
    token (built by build_dollar_vol.py). Order MUST match SYMBOLS. Returns None
    if the file is absent (model then falls back to equal weights)."""
    if not p.exists(DVOL_FILE):
        print(f"[cap] {DVOL_FILE} missing -> market token uses equal cap weights", flush=True)
        return None
    d = np.load(DVOL_FILE, allow_pickle=True)
    syms = [str(s) for s in d["sym"]]
    assert syms == SYMBOLS, f"dollar_vol sym order {syms} != SYMBOLS {SYMBOLS}"
    return d["dvol_med"].astype(np.float32)


def build_panel():
    """Returns ts(T,), day(T,), X(T,S,F), Y(T,S), CLEAN(T,S). Aligned on the
    common ts across all symbols (the shared stride-180 grid)."""
    per = {s: load_sym(s) for s in SYMBOLS}
    ts_sets = [set(per[s][3].tolist()) for s in SYMBOLS]
    common = sorted(set.intersection(*ts_sets))
    cidx = {int(t): i for i, t in enumerate(common)}
    nF = per[SYMBOLS[0]][0].shape[1]
    nT, nS = len(common), len(SYMBOLS)
    X = np.full((nT, nS, nF), np.nan, np.float32)
    Y = np.full((nT, nS), np.nan, np.float32)
    CL = np.zeros((nT, nS), bool)
    DAY = np.zeros(nT, np.int64)
    for si, s in enumerate(SYMBOLS):
        Xs, ys, days, tss, cl = per[s]
        # vectorized scatter onto the common grid
        rows = np.fromiter((cidx[int(t)] for t in tss), dtype=np.int64, count=len(tss))
        X[rows, si] = Xs
        Y[rows, si] = ys
        CL[rows, si] = cl
        DAY[rows] = days  # day is shared across syms at a ts; last write is fine
    return np.array(common), DAY, X, Y, CL


# --------------------------------------------------------------------------- #
# Fold day masks (leakage-safe: train day idx < te_start - EMBARGO).
# --------------------------------------------------------------------------- #
def fold_day_masks(uniq, day, fold):
    n = uniq.shape[0]
    if fold["te"][1] > n:
        return None
    te0, te1 = fold["te"]
    tr0, tr1 = fold["tr"]
    tri = np.arange(tr0, tr1)
    tri = tri[tri < te0 - EMBARGO]           # 1-day embargo before test
    tr_days_all = uniq[tri]
    # carve val from the TRAIN tail
    if len(tr_days_all) > VAL_DAYS + 10:
        tr_days = tr_days_all[:-VAL_DAYS]
        va_days = tr_days_all[-VAL_DAYS:]
    else:
        tr_days, va_days = tr_days_all, tr_days_all[-5:]
    te_days = uniq[te0:te1]
    trm = np.isin(day, tr_days)
    vam = np.isin(day, va_days)
    tem = np.isin(day, te_days)
    return trm, vam, tem


# --------------------------------------------------------------------------- #
# Cross-sectional Pearson aux loss (per-timestep, across valid assets).
# Adapted from src/losses/cross_sectional_ic_loss.py: differentiable, masked,
# returns mean over timesteps of (1 - Pearson) where >=2 assets are valid.
# --------------------------------------------------------------------------- #
def xsec_pearson_loss(pred, target, mask, eps=1e-6):
    # pred,target,mask: (B, S). valid = mask & finite.
    valid = (mask > 0.5) & torch.isfinite(pred) & torch.isfinite(target)
    v = valid.to(pred.dtype)
    count = v.sum(dim=1, keepdim=True)               # (B,1)
    enough = count.squeeze(1) >= 2.0
    if not enough.any():
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    p0 = torch.where(valid, pred, torch.zeros_like(pred))
    t0 = torch.where(valid, target, torch.zeros_like(target))
    mp = p0.sum(dim=1, keepdim=True) / count.clamp(min=1.0)
    mt = t0.sum(dim=1, keepdim=True) / count.clamp(min=1.0)
    pc = torch.where(valid, pred - mp, torch.zeros_like(pred))
    tc = torch.where(valid, target - mt, torch.zeros_like(target))
    num = (pc * tc).sum(dim=1)                        # (B,)
    sp = torch.sqrt((pc * pc).sum(dim=1).clamp(min=eps))
    st = torch.sqrt((tc * tc).sum(dim=1).clamp(min=eps))
    ic = num / (sp * st)
    losses = (1.0 - ic) * enough.to(pred.dtype)
    n_ok = enough.to(pred.dtype).sum().clamp(min=1.0)
    return losses.sum() / n_ok


def soft_xsec_rank_loss(pred, target, mask, temp=0.1, eps=1e-6):
    """Differentiable soft cross-sectional rank loss (Spearman surrogate).

    Per timestep, over the valid assets: soft-rank each of pred/target via the
    pairwise-sigmoid rank approximation r_i = sum_j sigmoid((x_i - x_j)/temp),
    then return mean over timesteps of (1 - Pearson(soft_rank_pred,
    soft_rank_target)). S<=14 so the O(S^2) pairwise op is cheap. ADD-only term
    (weight <=0.1) — never replaces the Huber+Pearson primary.
    """
    valid = (mask > 0.5) & torch.isfinite(pred) & torch.isfinite(target)
    v = valid.to(pred.dtype)                              # (B, S)
    count = v.sum(dim=1)                                  # (B,)
    enough = count >= 3.0
    if not enough.any():
        return torch.zeros((), device=pred.device, dtype=pred.dtype)

    def soft_rank(x):
        # pairwise difference (B, S, S); compare i vs j among VALID j only.
        xi = x.unsqueeze(2)                               # (B, S, 1)
        xj = x.unsqueeze(1)                               # (B, 1, S)
        vj = v.unsqueeze(1)                               # (B, 1, S) valid of j
        gt = torch.sigmoid((xi - xj) / temp) * vj         # (B, S, S)
        return gt.sum(dim=2)                              # (B, S) soft rank

    # mask invalid assets to a neutral value so they don't perturb the ranks of
    # valid ones (they get zero weight via vj, and we drop them from the corr).
    p0 = torch.where(valid, pred, torch.zeros_like(pred))
    t0 = torch.where(valid, target, torch.zeros_like(target))
    rp = soft_rank(p0)                                    # (B, S)
    rt = soft_rank(t0)
    # Pearson across valid assets per timestep on the soft ranks.
    cnt = count.clamp(min=1.0).unsqueeze(1)
    mp = (rp * v).sum(dim=1, keepdim=True) / cnt
    mt = (rt * v).sum(dim=1, keepdim=True) / cnt
    pc = (rp - mp) * v
    tc = (rt - mt) * v
    num = (pc * tc).sum(dim=1)
    sp = torch.sqrt((pc * pc).sum(dim=1).clamp(min=eps))
    st = torch.sqrt((tc * tc).sum(dim=1).clamp(min=eps))
    ic = num / (sp * st)
    losses = (1.0 - ic) * enough.to(pred.dtype)
    n_ok = enough.to(pred.dtype).sum().clamp(min=1.0)
    return losses.sum() / n_ok


def masked_huber(pred, target, mask, delta=HUBER_DELTA):
    valid = (mask > 0.5) & torch.isfinite(pred) & torch.isfinite(target)
    if not valid.any():
        return torch.zeros((), device=pred.device, dtype=pred.dtype)
    diff = (pred - target)[valid]
    a = diff.abs()
    quad = torch.minimum(a, torch.full_like(a, delta))
    lin = a - quad
    return (0.5 * quad * quad + delta * lin).mean()


# --------------------------------------------------------------------------- #
# Per-fold standardization (TRAIN only).
# --------------------------------------------------------------------------- #
def fit_x_stats(X, trm):
    """Per-feature mean/std over all TRAIN asset-rows (finite only)."""
    blk = X[trm].reshape(-1, X.shape[2])             # (n_tr*S, F)
    finite = np.isfinite(blk).all(axis=1)
    blk = blk[finite]
    mu = blk.mean(axis=0)
    sd = blk.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    return mu.astype(np.float32), sd.astype(np.float32)


def fit_y_sigma(Y, trm):
    """Per-asset MAD-sigma on TRAIN rows."""
    sig = np.ones(Y.shape[1], np.float32)
    for si in range(Y.shape[1]):
        col = Y[trm, si]
        col = col[np.isfinite(col)]
        if col.size > 10:
            mad = np.median(np.abs(col - np.median(col))) * 1.4826
            sig[si] = mad if mad > 1e-12 else 1.0
    return sig


def standardize(X, mu, sd):
    Xn = (np.nan_to_num(X, nan=0.0) - mu) / sd
    return np.clip(Xn, -10.0, 10.0).astype(np.float32)


# --------------------------------------------------------------------------- #
# Eval on CLEAN test rows.
# --------------------------------------------------------------------------- #
def predict_block(model, Xn, valid, batch=512):
    """Xn: (T,S,F) standardized; valid: (T,S) bool. Returns pred (T,S) in NORM units."""
    model.eval()
    T, S, _ = Xn.shape
    out = np.full((T, S), np.nan, np.float32)
    mask = valid.astype(np.float32)
    with torch.no_grad():
        for i in range(0, T, batch):
            j = min(i + batch, T)
            xb = torch.from_numpy(Xn[i:j]).to(DEV)
            mb = torch.from_numpy(mask[i:j]).to(DEV)
            pb = model(xb, mb)                        # (b,S) norm units
            out[i:j] = pb.detach().cpu().numpy()
    return out


def eval_fold(model, Xn_te, Y_te, CL_te, sig, target="raw"):
    """Returns dict of metrics. Predictions evaluated on CLEAN test rows only.
    pred is in NORM units; per-asset corr is scale-invariant so no de-norm needed
    for ranking, but we report sigma_ratio in RAW y units for the health check."""
    S = Y_te.shape[1]
    # per-timestamp validity for the FORWARD pass: feature-finite (we feed all
    # rows; mask=feature-finite). For metrics we additionally require clean600.
    feat_valid = np.isfinite(Xn_te).all(axis=2)      # (T,S)
    pred = predict_block(model, Xn_te, feat_valid)   # (T,S) norm units

    # per-asset Pearson/Spearman on clean rows (pooled over the fold)
    per_P, per_S = [], []
    sr_num, sr_den = 0.0, 0.0                          # sigma ratio in raw y
    for si in range(S):
        m = CL_te[:, si] & feat_valid[:, si] & np.isfinite(Y_te[:, si]) & np.isfinite(pred[:, si])
        if m.sum() < 50:
            continue
        ph = pred[m, si]
        yr = Y_te[m, si]
        P_ = pearsonr(ph, yr)[0]
        S_ = spearmanr(ph, yr)[0]
        if np.isfinite(P_):
            per_P.append(P_)
        if np.isfinite(S_):
            per_S.append(S_)
        # sigma ratio: pred is normalized -> de-norm to raw with sig[si]
        sr_num += (ph * sig[si]).std() * m.sum()
        sr_den += yr.std() * m.sum()

    # cross-sectional rank-IC: per-ts Spearman across >=5 valid clean assets
    xsec_ic = []
    for t in range(pred.shape[0]):
        v = CL_te[t] & feat_valid[t] & np.isfinite(Y_te[t]) & np.isfinite(pred[t])
        if v.sum() >= 5:
            ic = spearmanr(pred[t, v], Y_te[t, v])[0]
            if np.isfinite(ic):
                xsec_ic.append(ic)
    xsec_ic = np.array(xsec_ic)

    return dict(
        per_asset_P=float(np.mean(per_P)) if per_P else float("nan"),
        per_asset_S=float(np.mean(per_S)) if per_S else float("nan"),
        per_asset_P_list=[round(float(x), 4) for x in per_P],
        per_asset_S_list=[round(float(x), 4) for x in per_S],
        xsec_rank_ic=float(xsec_ic.mean()) if xsec_ic.size else float("nan"),
        xsec_ic_ir=(float(xsec_ic.mean() / xsec_ic.std() * np.sqrt(len(xsec_ic)))
                    if xsec_ic.size and xsec_ic.std() > 0 else float("nan")),
        n_xsec_ts=int(xsec_ic.size),
        sigma_ratio=float(sr_num / sr_den) if sr_den > 0 else float("nan"),
    )


def val_xsec_ic(model, Xn_va, Y_va, sig):
    """Val metrics for early-stop/BEST on ALL valid val rows (not just clean —
    val is for early stop, denser is fine and faster to react). Uses feature-
    finite mask. Returns (xsec_rank_ic, mean_per_asset_P, sigma_ratio)."""
    feat_valid = np.isfinite(Xn_va).all(axis=2)
    pred = predict_block(model, Xn_va, feat_valid)
    ics, per_P, sr_n, sr_d = [], [], 0.0, 0.0
    for t in range(pred.shape[0]):
        v = feat_valid[t] & np.isfinite(Y_va[t]) & np.isfinite(pred[t])
        if v.sum() >= 5:
            ic = spearmanr(pred[t, v], Y_va[t, v])[0]
            if np.isfinite(ic):
                ics.append(ic)
    for si in range(Y_va.shape[1]):
        m = feat_valid[:, si] & np.isfinite(Y_va[:, si]) & np.isfinite(pred[:, si])
        if m.sum() > 50:
            P_ = pearsonr(pred[m, si], Y_va[m, si])[0]
            if np.isfinite(P_):
                per_P.append(P_)
            sr_n += (pred[m, si] * sig[si]).std() * m.sum()
            sr_d += Y_va[m, si].std() * m.sum()
    sig_ratio = (sr_n / sr_d) if sr_d > 0 else 0.0
    return (float(np.mean(ics)) if ics else float("nan"),
            float(np.mean(per_P)) if per_P else float("nan"),
            sig_ratio)


# --------------------------------------------------------------------------- #
# Train one fold.
# --------------------------------------------------------------------------- #
def make_batches(ts_idx, batch, rng, shuffle=True):
    idx = ts_idx.copy()
    if shuffle:
        rng.shuffle(idx)
    return [idx[i:i + batch] for i in range(0, len(idx), batch)]


def train_fold(fold_i, fold, uniq, day, X, Y, CL, max_epochs, patience,
               cfg, cap_w=None, verbose=True):
    masks = fold_day_masks(uniq, day, fold)
    if masks is None:
        return None
    trm, vam, tem = masks
    tr_ts = np.where(trm)[0]
    va_ts = np.where(vam)[0]
    te_ts = np.where(tem)[0]

    mu, sd = fit_x_stats(X, trm)
    sig = fit_y_sigma(Y, trm)

    Xn = standardize(X, mu, sd)                       # (T,S,F)
    Yn = (Y / sig[None, :]).astype(np.float32)        # normalized target (T,S)
    Yn = np.nan_to_num(Yn, nan=0.0)                   # NaN slots masked out anyway
    feat_valid = np.isfinite(X).all(axis=2)           # (T,S) — train mask = feat-finite & finite-y
    train_mask = (feat_valid & np.isfinite(Y)).astype(np.float32)

    if verbose:
        print(f"[fold {fold_i}] train_ts={len(tr_ts)} val_ts={len(va_ts)} "
              f"test_ts={len(te_ts)} | x_mu/sd fit on {int(trm.sum())} ts", flush=True)
        print(f"[fold {fold_i}] y MAD-sigma per asset: "
              f"{np.array2string(sig, precision=4, max_line_width=200)}", flush=True)

    n_feat, n_assets = X.shape[2], X.shape[1]
    cap_t = (torch.from_numpy(cap_w).to(DEV)
             if (cfg["market_token"] and cap_w is not None) else None)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    model = CrossAssetPanelModel(n_feat, n_assets, d=D_MODEL, nhead=N_HEAD,
                                 n_layers=N_LAYERS, n_out=N_OUT, dropout=DROPOUT,
                                 use_market_token=cfg["market_token"],
                                 use_factor_split=cfg["factor_split"],
                                 cap_weights=cap_t).to(DEV)
    if fold_i == 0 and verbose:
        print(f"[model] CrossAssetPanelModel params = {count_params(model):,} "
              f"(d={D_MODEL}, layers={N_LAYERS}, nhead={N_HEAD}) "
              f"market_token={cfg['market_token']} factor_split={cfg['factor_split']} "
              f"composite_val={cfg['composite_val']} soft_rank={cfg['soft_rank']})", flush=True)
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WD)
    rng = np.random.default_rng(SEED)

    best_val = -1e9
    best_state = None
    best_epoch = -1
    bad = 0
    for ep in range(max_epochs):
        model.train()
        batches = make_batches(tr_ts, BATCH_TS, rng, shuffle=True)
        ep_loss = ep_h = ep_x = ep_r = 0.0
        nb = 0
        for bts in batches:
            xb = torch.from_numpy(Xn[bts]).to(DEV)        # (B,S,F)
            yb = torch.from_numpy(Yn[bts]).to(DEV)        # (B,S)
            mb = torch.from_numpy(train_mask[bts]).to(DEV)
            pred = model(xb, mb)                          # (B,S)
            lh = masked_huber(pred, yb, mb)
            lx = xsec_pearson_loss(pred, yb, mb)
            loss = LAMBDA_HUBER * lh + LAMBDA_XSEC * lx
            # Phase 3: ADD soft cross-sectional rank term (never REPLACE).
            if cfg["soft_rank"] > 0:
                lr_ = soft_xsec_rank_loss(pred, yb, mb)
                loss = loss + cfg["soft_rank"] * lr_
                ep_r += float(lr_.item())
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += float(loss.item()); ep_h += float(lh.item()); ep_x += float(lx.item())
            nb += 1
        ep_loss /= max(nb, 1); ep_h /= max(nb, 1); ep_x /= max(nb, 1); ep_r /= max(nb, 1)

        vic, vp, vsig = val_xsec_ic(model, Xn[va_ts], Y[va_ts], sig)
        gated = (vsig >= SIGMA_GATE)
        # composite val (Phase 3): 0.5*xsec_rank_IC + 0.5*mean per-asset P.
        if cfg["composite_val"] and np.isfinite(vic) and np.isfinite(vp):
            vscore = 0.5 * vic + 0.5 * vp
        else:
            vscore = vic
        tag = "" if gated else "  [sigma<gate -> not BEST]"
        if verbose:
            rstr = f" rank={ep_r:.4f}" if cfg["soft_rank"] > 0 else ""
            print(f"  ep{ep:2d}  loss={ep_loss:.4f} (huber={ep_h:.4f} xsec={ep_x:.4f}{rstr})  "
                  f"val_xsec_IC={vic:+.4f} val_P={vp:+.4f} val_score={vscore:+.4f}  "
                  f"val_sigma_ratio={vsig:.3f}{tag}", flush=True)
        score = vscore if (np.isfinite(vscore) and gated) else -1e9
        if score > best_val:
            best_val = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = ep
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                if verbose:
                    print(f"  early stop at ep{ep} (best ep{best_epoch} val_score={best_val:+.4f})", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    metrics = eval_fold(model, Xn[te_ts], Y[te_ts], CL[te_ts], sig)
    metrics["best_epoch"] = best_epoch
    metrics["best_val_score"] = round(best_val, 4) if best_val > -1e8 else None
    metrics["n_params"] = count_params(model)
    return metrics


# --------------------------------------------------------------------------- #
# Phase config. Default = full Phase-3 (all modules on). Individual flags let
# the baseline graph be recovered; --phase {0,1,2,3} is a convenience preset
# for the gate sweep (each preset is the SAME as setting the flags by hand).
# --------------------------------------------------------------------------- #
PHASE_PRESETS = {
    0: dict(market_token=False, factor_split=False, composite_val=False, soft_rank=0.0),
    1: dict(market_token=True,  factor_split=False, composite_val=False, soft_rank=0.0),
    2: dict(market_token=True,  factor_split=True,  composite_val=False, soft_rank=0.0),
    3: dict(market_token=True,  factor_split=True,  composite_val=True,  soft_rank=0.1),
}


def build_cfg(args):
    if args.phase is not None:
        cfg = dict(PHASE_PRESETS[args.phase])
    else:
        # default = full Phase-3; individual flags override.
        cfg = dict(PHASE_PRESETS[3])
    # individual flags (if explicitly given) override the preset
    if args.market_token is not None:
        cfg["market_token"] = args.market_token
    if args.factor_split is not None:
        cfg["factor_split"] = args.factor_split
    if args.composite_val is not None:
        cfg["composite_val"] = args.composite_val
    if args.soft_rank is not None:
        cfg["soft_rank"] = args.soft_rank
    if cfg["factor_split"] and not cfg["market_token"]:
        raise SystemExit("factor_split requires market_token (factor reads the market token)")
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="fold 0 only, 5 epochs (no early stop) — leakage/learning sanity")
    ap.add_argument("--phase", type=int, choices=[0, 1, 2, 3], default=None,
                    help="preset: 0=baseline 1=+market_token 2=+factor_split 3=full (default)")
    # individual flags (override the preset). store as tri-state (None=use preset)
    ap.add_argument("--market_token", dest="market_token", action="store_true", default=None)
    ap.add_argument("--no_market_token", dest="market_token", action="store_false")
    ap.add_argument("--factor_split", dest="factor_split", action="store_true", default=None)
    ap.add_argument("--no_factor_split", dest="factor_split", action="store_false")
    ap.add_argument("--composite_val", dest="composite_val", action="store_true", default=None)
    ap.add_argument("--no_composite_val", dest="composite_val", action="store_false")
    ap.add_argument("--soft_rank", type=float, default=None,
                    help="weight of the ADD soft xsec rank term (<=0.1); 0 disables")
    ap.add_argument("--tag", type=str, default=None,
                    help="output JSON suffix (default = derived from cfg)")
    args = ap.parse_args()

    cfg = build_cfg(args)
    tag = args.tag or (f"mt{int(cfg['market_token'])}_fs{int(cfg['factor_split'])}"
                       f"_cv{int(cfg['composite_val'])}_sr{cfg['soft_rank']:g}")
    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    print(f"[cfg] {cfg}  tag={tag}", flush=True)
    cap_w = load_cap_weights() if cfg["market_token"] else None

    t0 = time.time()
    ts, day, X, Y, CL = build_panel()
    uniq = np.unique(day)
    print(f"[panel] nT={len(ts)} nS={X.shape[1]} nF={X.shape[2]} unique_days={len(uniq)} "
          f"(built in {time.time()-t0:.1f}s)", flush=True)

    if args.smoke:
        print("\n===== SMOKE: fold 0, 5 epochs =====", flush=True)
        m = train_fold(0, FOLDS[0], uniq, day, X, Y, CL,
                       max_epochs=5, patience=999, cfg=cfg, cap_w=cap_w, verbose=True)
        print("\n----- SMOKE RESULT (fold 0, 5 epochs) -----", flush=True)
        print(json.dumps(m, indent=2), flush=True)
        beat = (np.isfinite(m["xsec_rank_ic"]) and m["xsec_rank_ic"] > 0.0403)
        print(f"\ncross-sectional rank-IC = {m['xsec_rank_ic']:+.4f}  "
              f"(Ridge baseline 0.0403)  -> {'BEATS' if beat else 'below'} Ridge at 5 ep", flush=True)
        print(f"per-asset avg P={m['per_asset_P']:+.4f} S={m['per_asset_S']:+.4f}  "
              f"sigma_pred/sigma_y={m['sigma_ratio']:.3f}", flush=True)
        return

    # full 3-fold run (controller launches this; no --smoke)
    print("\n===== FULL 3-FOLD RUN =====", flush=True)
    all_m = []
    for i, fold in enumerate(FOLDS):
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, uniq, day, X, Y, CL,
                       max_epochs=MAX_EPOCHS, patience=PATIENCE,
                       cfg=cfg, cap_w=cap_w, verbose=True)
        if m is not None:
            all_m.append(m)
            print(f"[fold {i}] xsec_rank_IC={m['xsec_rank_ic']:+.4f} "
                  f"per-asset P={m['per_asset_P']:+.4f} S={m['per_asset_S']:+.4f} "
                  f"sigma_ratio={m['sigma_ratio']:.3f}", flush=True)

    if all_m:
        pooled = dict(
            cfg=cfg,
            mean_xsec_rank_ic=round(float(np.mean([m["xsec_rank_ic"] for m in all_m])), 4),
            mean_per_asset_P=round(float(np.mean([m["per_asset_P"] for m in all_m])), 4),
            mean_per_asset_S=round(float(np.mean([m["per_asset_S"] for m in all_m])), 4),
            mean_sigma_ratio=round(float(np.mean([m["sigma_ratio"] for m in all_m])), 4),
            per_fold_P=[round(m["per_asset_P"], 4) for m in all_m],
            per_fold_S=[round(m["per_asset_S"], 4) for m in all_m],
            per_fold_xsec_ic=[round(m["xsec_rank_ic"], 4) for m in all_m],
            per_fold=all_m,
            ridge_xsec_baseline=0.0403,
            n_params=all_m[0]["n_params"],
        )
        os.makedirs(EXPORT, exist_ok=True)
        out = p.join(EXPORT, f"cross_asset_panel_3fold_{tag}.json")
        with open(out, "w") as f:
            json.dump(pooled, f, indent=2)
        print("\n===== POOLED 3-FOLD =====", flush=True)
        print(json.dumps({k: v for k, v in pooled.items() if k != "per_fold"}, indent=2), flush=True)
        print(f"\nsaved -> {out}", flush=True)


if __name__ == "__main__":
    main()
