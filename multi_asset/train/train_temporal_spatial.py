"""Temporal-Spatial panel trainer for crypto y_600 (per-asset Pearson target).

Trains `TemporalSpatialPanelModel` by STREAMING 600-bar windows from the
seq_cache (the panel never fits in RAM). Same leakage-safe walk-forward folds and
train-only stats as the shallow `train_cross_asset.py`, so the ONLY change vs the
shallow panel (per-asset P=0.033) is last-token-MLP -> temporal-Conformer.

Milestones (--milestone):
    M0  pure per-asset temporal (n_xattn=0). GATE: per-asset P approaches the
        single-asset 0.058 (sanity that the temporal stem + dataset are correct).
    M1  + cross-asset attention (n_xattn=2).   GATE: +>=0.003 per-asset P over M0.
    M2  + market token + factor split.          GATE: +>=0.003 per-asset P over M1.

Loss (masked over valid assets, per-asset-P focused):
    0.10 * pinball(q10,q50,q90)        # quantile calib + gives the DAQH encoder
                                       #   gradient at init (q50 path is zero-init)
  + 0.50 * Huber(q50, y_norm)          # magnitude calib -> Pearson + beta slope
  + 0.20 * soft_xsec_rank              # a touch of cross-sectional breadth (ADD)

Val metric = 0.5*avg_per_asset_P + 0.5*avg_per_asset_S (the USER target), gated by
sigma_pred/sigma_y >= 0.02 (anti-pattern #24: reject init-noise BEST epochs).

Usage:
    python3 multi_asset/train/train_temporal_spatial.py --milestone 0 --smoke
    python3 multi_asset/train/train_temporal_spatial.py --milestone 0   # full 3-fold
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
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.seq_panel_dataset import SeqPanelData, SYMBOLS  # noqa: E402
from multi_asset.model.temporal_spatial_panel import (  # noqa: E402
    TemporalSpatialPanelModel, count_params,
)
from multi_asset.train.train_cross_asset import (  # noqa: E402  reuse exact recipe
    FOLDS, EMBARGO, VAL_DAYS, masked_huber, soft_xsec_rank_loss, load_cap_weights,
)
from multi_asset.losses.xsec_residual_loss import (  # noqa: E402
    residual_loss, cross_sectional_residual,
)

RANK_KIND = "lambda"   # "lambda" (LambdaRankIC) or "pearson" (Pearson-IC fallback)
W_HUBER, W_RANK, W_PIN = 0.30, 0.70, 0.10   # overridable via --w_* flags

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")

# --- recipe (matched to single-asset where it matters) ---
D_MODEL = 32
N_BLOCKS = 2
KERNEL = 15
NHEAD = 4
DROPOUT = 0.2
LR = 6e-4
WD = 0.01
BATCH_TS = 64           # timestamps/batch -> 64*14=896 asset-sequences/batch
TRAIN_STRIDE_SUB = 2    # subsample TRAIN pred grid 180s->360s (eval stays full/clean)
MAX_EPOCHS = 20
PATIENCE = 4
HUBER_DELTA = 2.0
LAMBDA_PINBALL = 0.10
LAMBDA_HUBER = 0.50
LAMBDA_XSEC = 0.20
SIGMA_GATE = 0.02
SEED = 42
TAUS = (0.1, 0.5, 0.9)

DEV = "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------------------------------------------------------- #
# Masked pinball over the 3 quantiles (the q10/q90 paths give encoder gradient).
# --------------------------------------------------------------------------- #
def pinball_loss(quantiles, target, mask, taus=TAUS):
    # quantiles: (B,S,3); target/mask: (B,S)
    valid = (mask > 0.5) & torch.isfinite(target)
    if not valid.any():
        return torch.zeros((), device=quantiles.device, dtype=quantiles.dtype)
    t = target.unsqueeze(-1)                                    # (B,S,1)
    err = t - quantiles                                        # (B,S,3)
    tau = torch.tensor(taus, device=quantiles.device, dtype=quantiles.dtype)
    pin = torch.maximum(tau * err, (tau - 1.0) * err)          # (B,S,3)
    pin = pin.mean(dim=-1)                                      # (B,S)
    return pin[valid].mean()


# --------------------------------------------------------------------------- #
# Fold day split (mirrors train_cross_asset.fold_day_masks but returns day lists).
# --------------------------------------------------------------------------- #
def fold_day_lists(uniq, fold):
    n = uniq.shape[0]
    if fold["te"][1] > n:
        return None
    te0, te1 = fold["te"]
    tr0, tr1 = fold["tr"]
    tri = np.arange(tr0, tr1)
    tri = tri[tri < te0 - EMBARGO]
    tr_all = uniq[tri]
    if len(tr_all) > VAL_DAYS + 10:
        tr_days, va_days = tr_all[:-VAL_DAYS], tr_all[-VAL_DAYS:]
    else:
        tr_days, va_days = tr_all, tr_all[-5:]
    te_days = uniq[te0:te1]
    return tr_days, va_days, te_days


# --------------------------------------------------------------------------- #
# GPU-side windowing: keep each day's F on the GPU, slice/standardize windows
# there (the CPU numpy gather was starving the GPU). Yields GPU tensors.
# --------------------------------------------------------------------------- #
COARSE_POOL = 15          # 15s pooling for the NX-M1 coarse branch
COARSE_LEN = 240          # 240 pooled steps = 1h context
COARSE_MIN_BAR = COARSE_POOL * COARSE_LEN + COARSE_POOL - 1   # 3614


def gpu_day_batches(F_all, mask_all, y_all, rows, bars, mu_g, sd_g, sigma_g,
                    offs_g, W, batch_ts, rng=None, shuffle=True, coarse=False,
                    y_extra=None):
    F_g = torch.from_numpy(F_all).to(DEV)                       # (S,T,F)
    F_g = torch.nan_to_num(F_g, nan=0.0)
    F_g = ((F_g - mu_g) / sd_g).clamp_(-10.0, 10.0)             # standardize whole day once
    y_g = torch.from_numpy(y_all).to(DEV)                       # (S,T)
    yx_g = {h: torch.from_numpy(a).to(DEV) for h, a in (y_extra or {}).items()}
    mask_g = torch.from_numpy(mask_all.astype(np.float32)).to(DEV)
    if coarse:
        # NX-M1: pool the standardized day once -> (S, T//15, F); causal bins
        # (bin j covers bars [15j, 15j+14], usable for pred bar bi iff 15j+14<=bi)
        F15 = torch.nn.functional.avg_pool1d(
            F_g.permute(0, 2, 1), kernel_size=COARSE_POOL, stride=COARSE_POOL
        ).permute(0, 2, 1).contiguous()                          # (S, T15, F)
        keep = bars >= COARSE_MIN_BAR                            # drop first hour
        rows, bars = rows[keep], bars[keep]
        coffs = torch.arange(-COARSE_LEN, 0, device=DEV)
    if bars.shape[0] == 0:
        return
    bars_g = torch.from_numpy(bars).to(DEV)                     # (n,)
    order = np.arange(bars.shape[0])
    if shuffle and rng is not None:
        rng.shuffle(order)
    for b0 in range(0, order.shape[0], batch_ts):
        bidx = torch.from_numpy(order[b0:b0 + batch_ts]).to(DEV)
        bb = bars_g[bidx]                                       # (B,)
        widx = bb[:, None] + offs_g[None, :]                   # (B,W)
        Xseq = F_g[:, widx, :].permute(1, 0, 2, 3).contiguous()  # (B,S,W,F)
        Xc = None
        if coarse:
            jend = torch.div(bb - (COARSE_POOL - 1), COARSE_POOL,
                             rounding_mode="floor") + 1          # (B,) exclusive
            cwidx = jend[:, None] + coffs[None, :]               # (B, 240)
            Xc = F15[:, cwidx, :].permute(1, 0, 2, 3).contiguous()  # (B,S,240,F)
        ymat = y_g[:, bb].t()                                   # (B,S) RAW y
        mmat = mask_g[:, bb].t() * torch.isfinite(ymat).float()  # (B,S)
        yx = {h: torch.nan_to_num(g[:, bb].t(), nan=0.0) for h, g in yx_g.items()}
        # yield RAW y (nan->0, masked) so the trainer can form the cross-sectional
        # residual; sigma_g kept for back-compat but residual uses resid_sigma.
        yield Xseq, torch.nan_to_num(ymat, nan=0.0), mmat, rows[order[b0:b0 + batch_ts]], Xc, yx


# --------------------------------------------------------------------------- #
# Streaming predict over a split -> pred (T,S) in NORM units (NaN where invalid).
# --------------------------------------------------------------------------- #
def predict_split(model, data, split_rows, mu_g, sd_g, sigma_g, offs_g, batch_ts=96,
                  coarse=False, z_g=None):
    model.eval()
    T, S = data.ts.shape[0], data.S
    pred = np.full((T, S), np.nan, np.float32)
    with torch.no_grad():
        for F_all, mask_all, y_all, rows, bars, _ in data.iter_days(
                split_rows, rng=None, shuffle=False):
            for Xseq, yn, mmat, rr, Xc, _yx in gpu_day_batches(
                    F_all, mask_all, y_all, rows, bars, mu_g, sd_g, sigma_g,
                    offs_g, data.W, batch_ts, rng=None, shuffle=False, coarse=coarse):
                zb = z_g[rr] if z_g is not None else None
                q50 = model(Xseq, mmat, x_coarse=Xc, z_btc=zb).detach().cpu().numpy()
                q50 = np.where(mmat.cpu().numpy() > 0.5, q50, np.nan)
                pred[rr] = q50
    return pred


def load_btc25(data):
    """(T,8) BTC-25 deep-book scalars aligned to the panel grid by exact ts
    match (panel ts is a subset of the builder's candidate grid)."""
    root = p.join(p.dirname(EXPORT), "btc25_state")
    Z = np.full((len(data.ts), 8), np.nan, np.float32)
    miss = []
    for d in data.uniq_days:
        f = p.join(root, f"{int(d)}.npz")
        if not p.exists(f):
            miss.append(int(d)); continue
        z = np.load(f)
        rows = np.where(data.day == d)[0]
        idx = np.searchsorted(z["ts"], data.ts[rows])
        idx_c = np.minimum(idx, len(z["ts"]) - 1)
        ok = z["ts"][idx_c] == data.ts[rows]
        Z[rows[ok]] = z["Z"][idx_c[ok]]
    cov = float(np.isfinite(Z).all(axis=1).mean())
    print(f"[btc25] aligned coverage={cov:.4f} missing_days={miss[:5]}"
          f"{'...' if len(miss) > 5 else ''} (n={len(miss)})", flush=True)
    assert cov > 0.95, "btc25 alignment coverage too low"
    return np.nan_to_num(Z, nan=0.0)


def eval_metrics(pred, Y, CL, sigma, clean=True, min_n=50):
    S = Y.shape[1]
    per_P, per_S, per_beta, sr_n, sr_d = [], [], [], 0.0, 0.0
    pooled_pr, pooled_y = [], []          # de-normed pred + raw y, for bias/monotonicity
    # sigma_ratio denominator = cross-sectional RESIDUAL y (the unit the model
    # predicts), not raw y. Raw-y std is ~1.8x residual std at y1800, so the old
    # raw denominator understated collapse risk. Audit fix 2026-06-11.
    with np.errstate(all="ignore"):
        rmean = np.nanmean(np.where(np.isfinite(Y), Y, np.nan), axis=1, keepdims=True)
    Yres = Y - rmean
    for si in range(S):
        m = np.isfinite(pred[:, si]) & np.isfinite(Y[:, si])
        if clean:
            m = m & CL[:, si]
        if m.sum() < min_n:
            continue
        ph, yr = pred[m, si], Y[m, si]
        P_, S_ = pearsonr(ph, yr)[0], spearmanr(ph, yr)[0]
        if np.isfinite(P_):
            per_P.append(P_)
        if np.isfinite(S_):
            per_S.append(S_)
        # beta = slope of raw y on de-normed pred (healthy ~1); pred is in NORM units
        pr = ph * sigma[si]               # de-norm to raw y units
        vp = np.var(pr)
        if vp > 1e-18:
            per_beta.append(float(np.cov(yr, pr)[0, 1] / vp))
        pooled_pr.append(pr); pooled_y.append(yr)
        sr_n += pr.std() * m.sum()
        sr_d += Yres[m, si].std() * m.sum()
    # pooled bias + monotonicity (E[y|pred-decile] should rise monotonically)
    bias_bps = mono = float("nan")
    if pooled_pr:
        PR = np.concatenate(pooled_pr); YY = np.concatenate(pooled_y)
        bias_bps = float(PR.mean() * 1e4)              # long-short bias (mean pred, bps)
        if PR.size > 500 and PR.std() > 0:
            q = np.quantile(PR, np.linspace(0, 1, 11))
            q[-1] += 1e-12
            binid = np.clip(np.digitize(PR, q[1:-1]), 0, 9)
            ybin = [YY[binid == b].mean() for b in range(10) if (binid == b).sum() > 5]
            if len(ybin) >= 5:
                mono = float(spearmanr(np.arange(len(ybin)), ybin).correlation)
    xsec = []
    for t in range(pred.shape[0]):
        v = np.isfinite(pred[t]) & np.isfinite(Y[t])
        if clean:
            v = v & CL[t]
        if v.sum() >= 5:
            ic = spearmanr(pred[t, v], Y[t, v])[0]
            if np.isfinite(ic):
                xsec.append(ic)
    xsec = np.array(xsec)
    return dict(
        per_asset_P=float(np.mean(per_P)) if per_P else float("nan"),
        per_asset_S=float(np.mean(per_S)) if per_S else float("nan"),
        per_asset_P_list=[round(float(x), 4) for x in per_P],
        per_asset_S_list=[round(float(x), 4) for x in per_S],
        xsec_rank_ic=float(xsec.mean()) if xsec.size else float("nan"),
        xsec_ic_ir=(float(xsec.mean() / xsec.std() * np.sqrt(xsec.size))
                    if xsec.size > 1 and xsec.std() > 1e-9 else float("nan")),
        n_xsec_ts=int(xsec.size),
        sigma_ratio=float(sr_n / sr_d) if sr_d > 0 else float("nan"),
        avg_beta=round(float(np.mean(per_beta)), 3) if per_beta else float("nan"),
        bias_bps=round(bias_bps, 4),
        monotonicity=round(mono, 3),
    )


# --------------------------------------------------------------------------- #
# Train one fold.
# --------------------------------------------------------------------------- #
def train_fold(fold_i, fold, data, milestone, max_epochs, patience,
               cap_w=None, verbose=True, day_override=None, save_dir=None,
               multipool=False, horizon=600, coarse=False, init_ckpt=None, stats_from=None,
               aux_horizons=(), bilinear=False, epnet=False, epnet_soft=False,
               attnpool=False, zall=None):
    uniq = data.uniq_days
    if day_override is not None:
        tr_days, va_days, te_days = day_override
    else:
        lists = fold_day_lists(uniq, fold)
        if lists is None:
            return None
        tr_days, va_days, te_days = lists
    # restrict to days that actually exist in seq_cache (smoke/partial builds)
    import glob
    built = set(int(p.basename(f)[:8])
                for f in glob.glob(p.join(data.seq_dir, "2*.npz")))
    tr_days = np.array([d for d in tr_days if int(d) in built])
    va_days = np.array([d for d in va_days if int(d) in built])
    te_days = np.array([d for d in te_days if int(d) in built])
    if len(tr_days) < 20 or len(va_days) < 3 or len(te_days) < 3:
        print(f"[fold {fold_i}] not enough built days "
              f"(tr={len(tr_days)} va={len(va_days)} te={len(te_days)}) — skip", flush=True)
        return None

    data.set_fold(tr_days)
    if stats_from:
        st = np.load(stats_from)
        data.mu, data.sd = st["mu"], st["sd"]
        data.resid_sigma = st["resid_sigma"]
        if verbose:
            print(f"[stats] overrode mu/sd/resid_sigma from {stats_from}", flush=True)
    data._day_cache.clear()          # free previous fold's cached days
    data.enable_cache(True)          # cache day arrays in RAM (no per-epoch disk IO)
    tr_rows = np.where(np.isin(data.day, tr_days))[0]
    tr_rows = tr_rows[::TRAIN_STRIDE_SUB]    # thin train grid (less overlap, ~2x faster)
    va_rows = np.where(np.isin(data.day, va_days))[0]
    te_rows = np.where(np.isin(data.day, te_days))[0]
    z_g = None
    if zall is not None:
        # standardize the BTC-25 state with TRAIN-row stats (causal per fold)
        zmu = zall[tr_rows].mean(axis=0)
        zsd = zall[tr_rows].std(axis=0) + 1e-9
        z_g = torch.from_numpy(((zall - zmu) / zsd).astype(np.float32)).to(DEV)
        z_g = torch.clamp(z_g, -8.0, 8.0)
    if verbose:
        print(f"[fold {fold_i}] days tr={len(tr_days)} va={len(va_days)} te={len(te_days)} | "
              f"rows tr={len(tr_rows)} va={len(va_rows)} te={len(te_rows)}", flush=True)
        print(f"[fold {fold_i}] y MAD-sigma: "
              f"{np.array2string(data.sigma, precision=4, max_line_width=200)}", flush=True)

    flags = {0: dict(n_xattn=0),
             1: dict(n_xattn=2),
             2: dict(n_xattn=2, use_market_token=True, use_factor_split=True)}[milestone]
    cap_t = (torch.from_numpy(cap_w).to(DEV)
             if (milestone == 2 and cap_w is not None) else None)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    model = TemporalSpatialPanelModel(
        data.F, data.S, d=D_MODEL, n_blocks=N_BLOCKS, kernel_size=KERNEL,
        nhead=NHEAD, dropout=DROPOUT, cap_weights=cap_t, multipool=multipool,
        coarse=coarse, horizons=tuple([horizon] + sorted(aux_horizons)),
        bilinear=bilinear, epnet=epnet, epnet_soft=epnet_soft,
        attnpool=attnpool, btc25=(zall is not None), **flags).to(DEV)
    if init_ckpt:
        st = torch.load(init_ckpt, map_location="cpu")
        missing, unexpected = model.load_state_dict(st, strict=False)
        if verbose:
            print(f"[init] loaded {init_ckpt} (missing={len(missing)} unexpected={len(unexpected)})", flush=True)
    if fold_i == 0 and verbose:
        print(f"[model] TemporalSpatialPanelModel params={count_params(model):,} "
              f"(d={D_MODEL}, blocks={N_BLOCKS}, kernel={KERNEL}, milestone=M{milestone}, "
              f"flags={flags})", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    rng = np.random.default_rng(SEED)
    # GPU-resident stat tensors + window offsets (broadcast over (S,T,F) / (B,W))
    mu_g = torch.from_numpy(data.mu).to(DEV)
    sd_g = torch.from_numpy(data.sd).to(DEV)
    sigma_g = torch.from_numpy(data.sigma).to(DEV)
    resid_sigma_g = torch.from_numpy(data.resid_sigma).to(DEV)
    offs_g = torch.arange(-data.W + 1, 1, device=DEV)

    best_val, best_state, best_epoch, bad = -1e9, None, -1, 0
    for ep in range(max_epochs):
        model.train()
        t_ep = time.time()
        ep_loss = ep_pin = ep_h = ep_x = 0.0
        nb = 0
        for F_all, mask_all, y_all, rows, bars, y_extra in data.iter_days(
                tr_rows, rng=rng, shuffle=True):
            for xb, yraw, mb, rr_b, xc, yx in gpu_day_batches(
                    F_all, mask_all, y_all, rows, bars, mu_g, sd_g, sigma_g,
                    offs_g, data.W, BATCH_TS, rng=rng, shuffle=True, coarse=coarse,
                    y_extra=y_extra):
                zb = z_g[rr_b] if z_g is not None else None
                out = model(xb, mb, return_dict=True, x_coarse=xc, z_btc=zb)
                # cross-sectional RESIDUAL target (demean over valid assets, per-asset
                # MAD-norm, clip) -> both rank + magnitude losses see the SAME residual.
                r, _ = cross_sectional_residual(yraw, mb)
                r = (r / resid_sigma_g[None, :]).clamp(-5.0, 5.0)
                loss, parts = residual_loss(out["quantiles"], r, mb, rank_kind=RANK_KIND,
                                            w_huber=W_HUBER, w_rank=W_RANK, w_pin=W_PIN)
                # NX-S3 MTL: aux-horizon heads on the shared trunk (w=0.3 each).
                # Aux residual sigma via diffusion scaling sqrt(h/h0) (measured-exact).
                for ai, (h_aux, y_aux) in enumerate(sorted(yx.items())):
                    r_a, _ = cross_sectional_residual(y_aux, mb)
                    scale = resid_sigma_g[None, :] * float(np.sqrt(h_aux / horizon))
                    r_a = (r_a / scale).clamp(-5.0, 5.0)
                    l_a, _ = residual_loss(out["aux_quantiles"][ai], r_a, mb,
                                           rank_kind=RANK_KIND, w_huber=W_HUBER,
                                           w_rank=W_RANK, w_pin=W_PIN)
                    loss = loss + 0.3 * l_a
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                ep_loss += float(loss.item()); ep_pin += parts["pin"]
                ep_h += parts["huber"]; ep_x += parts["rank"]; nb += 1
        ep_loss /= max(nb, 1); ep_pin /= max(nb, 1); ep_h /= max(nb, 1); ep_x /= max(nb, 1)

        vpred = predict_split(model, data, va_rows, mu_g, sd_g, sigma_g, offs_g, coarse=coarse, z_g=z_g)
        if horizon > 600:
            # match the TEST statistic: thinned non-overlap view (dense val
            # overweights smooth/persistent components -> misleads checkpointing)
            vstep = horizon // 180
            vthin = np.zeros(vpred.shape[0], bool)
            va_day = data.day[va_rows]
            for d in np.unique(va_day):
                dr = va_rows[va_day == d]
                vthin[dr[::vstep]] = True
            vpred = np.where(vthin[:, None], vpred, np.nan)
        vm = eval_metrics(vpred, data.Y, data.CL, data.resid_sigma, clean=False)
        vIC, vP, vS = vm["xsec_rank_ic"], vm["per_asset_P"], vm["per_asset_S"]
        # PRIMARY objective for the residual long-short = cross-sectional rank-IC.
        # sigma-gate (anti-pattern #24): reject near-collapse checkpoints.
        # sigma_ratio is residual-denominated (audit fix 2026-06-11), so the
        # methodology gate applies directly at 0.02.
        vscore = vIC
        gated = np.isfinite(vscore) and np.isfinite(vm["sigma_ratio"]) and vm["sigma_ratio"] >= 0.02
        if verbose:
            print(f"  ep{ep:2d} ({time.time()-t_ep:.0f}s) loss={ep_loss:.4f} "
                  f"(huber={ep_h:.4f} rank={ep_x:.4f} pin={ep_pin:.4f})  "
                  f"val_rankIC={vIC:+.4f} val_perP={vP:+.4f} val_perS={vS:+.4f}", flush=True)
        score = vscore if (np.isfinite(vscore) and gated) else -1e9
        if score > best_val:
            best_val, best_epoch, bad = score, ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                if verbose:
                    print(f"  early stop ep{ep} (best ep{best_epoch} score={best_val:+.4f})", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    # clean non-overlap eval: stride-180 grid is non-overlapping for h<=180;
    # h=600 uses the clean600 flag; h>600 thins the grid to spacing>=h.
    if horizon > 600:
        # predict DENSE (saved preds must cover all te_rows so nx_battery can
        # pair models on its canonical per-day thinned grid); the trainer's own
        # logged metric uses a per-day thinned VIEW for non-overlap honesty.
        tpred = predict_split(model, data, te_rows, mu_g, sd_g, sigma_g, offs_g, coarse=coarse, z_g=z_g)
        step = horizon // 180
        thin = np.zeros(tpred.shape[0], bool)
        te_day = data.day[te_rows]
        for d in np.unique(te_day):
            dr = te_rows[te_day == d]
            thin[dr[::step]] = True
        tview = np.where(thin[:, None], tpred, np.nan)
        metrics = eval_metrics(tview, data.Y, data.CL, data.resid_sigma, clean=False)
    else:
        # clean600 spacing (>=600s) is valid non-overlap for any h<=600 and keeps
        # comparability with all published numbers (R1-y180 0.0668 used it).
        tpred = predict_split(model, data, te_rows, mu_g, sd_g, sigma_g, offs_g, coarse=coarse, z_g=z_g)
        metrics = eval_metrics(tpred, data.Y, data.CL, data.resid_sigma, clean=True)
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        np.savez(p.join(save_dir, f"fold_{fold_i}_preds.npz"),
                 pred=tpred, te_rows=te_rows, te_days=te_days,
                 resid_sigma=data.resid_sigma, horizon=horizon,
                 x_mu=data.mu, x_sd=data.sd)
        torch.save(best_state, p.join(save_dir, f"fold_{fold_i}_model.pt"))
    metrics["best_epoch"] = best_epoch
    metrics["best_val_score"] = round(best_val, 4) if best_val > -1e8 else None
    metrics["n_params"] = count_params(model)
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--milestone", type=int, choices=[0, 1, 2], default=0)
    ap.add_argument("--smoke", action="store_true",
                    help="fold 0 only, few epochs on whatever days are built")
    ap.add_argument("--tag", type=str, default=None)
    ap.add_argument("--save_tag", type=str, default=None,
                    help="if set, save per-fold test preds + model to EXPORT/<save_tag>/")
    ap.add_argument("--w_pin", type=float, default=None, help="pinball weight override (ablation)")
    ap.add_argument("--w_huber", type=float, default=None)
    ap.add_argument("--w_rank", type=float, default=None)
    ap.add_argument("--data_root", type=str, default=None,
                    help="alternate cache root (e.g. exports/pretrain) with seq_cache/panel_cache/mh_* inside")
    ap.add_argument("--bilinear", action="store_true", help="NX-S4: bilinear cross-asset interaction")
    ap.add_argument("--epnet", action="store_true",
                    help="NX-M3a: asset-conditioned input channel gate (PEPNet)")
    ap.add_argument("--attnpool", action="store_true",
                    help="NX A/B: learned-query attention pool blended with last-token")
    ap.add_argument("--epnet_soft", action="store_true",
                    help="EPNet v2: gamma in [0.5,1.5] (tanh) instead of [0,2]")
    ap.add_argument("--coarse_pool", type=int, default=None,
                    help="coarse branch pooling seconds (default 15; 60 -> 4h span)")
    ap.add_argument("--btc25", action="store_true",
                    help="NX-S5: BTC-25 deep-book scalar FiLM conditioning")
    ap.add_argument("--aux_horizons", type=str, default="",
                    help="comma-sep MTL aux horizons, e.g. 180,600 (NX-S3)")
    ap.add_argument("--lr", type=float, default=None, help="override LR (ft: pretrain/10)")
    ap.add_argument("--patience", type=int, default=None)
    ap.add_argument("--stats_from", type=str, default=None,
                    help="npz with mu/sd/resid_sigma to use instead of fold-fit stats (pretrain-period stats)")
    ap.add_argument("--init_ckpt", type=str, default=None,
                    help="warm-start state_dict (NX-S2 pretrained stem; strict=False)")
    ap.add_argument("--pretrain_mode", action="store_true",
                    help="single split over ALL available days (last 20 = val); saves model for fine-tune init")
    ap.add_argument("--coarse", action="store_true",
                    help="NX-M1: 1h@15s coarse context branch (multi-scale)")
    ap.add_argument("--multipool", action="store_true",
                    help="A1a: multi-pool divided space-time (cross-asset attn reads 3 temporal pools)")
    ap.add_argument("--seed", type=int, default=None, help="override SEED (noise-floor measurement)")
    ap.add_argument("--horizon", type=int, default=600,
                    choices=[60, 180, 600, 1800, 3600],
                    help="target horizon (mh_targets for 60/180; mh_targets_long for 1800/3600)")
    args = ap.parse_args()
    save_dir = p.join(EXPORT, args.save_tag) if args.save_tag else None
    global W_HUBER, W_RANK, W_PIN, LR, PATIENCE
    if args.lr is not None: LR = args.lr
    if args.patience is not None: PATIENCE = args.patience
    if args.w_pin is not None: W_PIN = args.w_pin
    if args.w_huber is not None: W_HUBER = args.w_huber
    if args.w_rank is not None: W_RANK = args.w_rank
    if args.seed is not None:
        global SEED
        SEED = args.seed
    if args.coarse_pool is not None:
        global COARSE_POOL, COARSE_MIN_BAR
        COARSE_POOL = args.coarse_pool
        COARSE_MIN_BAR = COARSE_POOL * COARSE_LEN + COARSE_POOL - 1
        print(f"[coarse] pool={COARSE_POOL}s x {COARSE_LEN} steps "
              f"= {COARSE_POOL*COARSE_LEN/3600:.1f}h span (min_bar={COARSE_MIN_BAR})",
              flush=True)

    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    t0 = time.time()
    aux_h = tuple(int(x) for x in args.aux_horizons.split(",") if x.strip())
    if args.data_root:
        data = SeqPanelData(seq_dir=p.join(args.data_root, "seq_cache"),
                            panel_cache=p.join(args.data_root, "panel_cache"),
                            target_horizon=args.horizon, extra_horizons=aux_h)
    else:
        data = SeqPanelData(target_horizon=args.horizon, extra_horizons=aux_h)
    print(f"[panel] T={len(data.ts)} S={data.S} uniq_days={len(data.uniq_days)} "
          f"horizon=y_{args.horizon} (index built {time.time()-t0:.1f}s)", flush=True)
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        np.savez(p.join(save_dir, "panel_ref.npz"), ts=data.ts, day=data.day,
                 Y=data.Y, CL=data.CL, symbols=np.array(SYMBOLS))
    cap_w = load_cap_weights() if args.milestone == 2 else None
    zall = load_btc25(data) if args.btc25 else None
    tag = args.tag or f"M{args.milestone}"

    if args.smoke:
        # synthetic fold over whatever days are built (partial seq_cache OK)
        import glob
        built = sorted(int(p.basename(f)[:8])
                       for f in glob.glob(p.join(data.seq_dir, "2*.npz")))
        built = [d for d in built if d in set(data.uniq_days.tolist())]
        built = built[:55]                       # cap for a fast smoke
        n = len(built)
        ntr = max(20, int(n * 0.7))
        tr = built[:ntr]; va = built[ntr:ntr + max(5, (n - ntr) // 2)]
        te = built[ntr + len(va):]
        print(f"\n===== SMOKE: {n} built days -> tr={len(tr)} va={len(va)} te={len(te)}, "
              f"4 epochs, M{args.milestone} =====", flush=True)
        m = train_fold(0, FOLDS[0], data, args.milestone,
                       max_epochs=4, patience=999, cap_w=cap_w, verbose=True,
                       day_override=(np.array(tr), np.array(va), np.array(te)))
        print("\n----- SMOKE RESULT -----", flush=True)
        print(json.dumps(m, indent=2), flush=True)
        return

    if args.pretrain_mode:
        days = data.uniq_days
        tr, va = days[:-20], days[-20:]
        print(f"\n===== PRETRAIN ({len(tr)} train / {len(va)} val days, h={args.horizon}) =====", flush=True)
        m = train_fold(0, FOLDS[0], data, args.milestone, max_epochs=MAX_EPOCHS,
                       patience=PATIENCE, cap_w=cap_w, verbose=True, save_dir=save_dir,
                       multipool=args.multipool, horizon=args.horizon, coarse=args.coarse,
                       day_override=(tr, va, va))
        if save_dir is not None:
            np.savez(p.join(save_dir, "pretrain_stats.npz"),
                     mu=data.mu, sd=data.sd, resid_sigma=data.resid_sigma)
        print(json.dumps({k: v for k, v in (m or {}).items() if not k.endswith("_list")}, indent=2), flush=True)
        return

    print(f"\n===== FULL 3-FOLD (M{args.milestone}) =====", flush=True)
    all_m = []
    for i, fold in enumerate(FOLDS):
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, data, args.milestone,
                       max_epochs=MAX_EPOCHS, patience=PATIENCE,
                       cap_w=cap_w, verbose=True, save_dir=save_dir,
                       multipool=args.multipool, horizon=args.horizon, coarse=args.coarse,
                       init_ckpt=args.init_ckpt, stats_from=args.stats_from,
                       aux_horizons=aux_h, bilinear=args.bilinear, epnet=args.epnet,
                       epnet_soft=args.epnet_soft, attnpool=args.attnpool, zall=zall)
        if m is not None:
            all_m.append(m)
            print(f"[fold {i}] xsec_rankIC={m['xsec_rank_ic']:+.4f} IC-IR={m['xsec_ic_ir']:.2f} "
                  f"| per-asset P={m['per_asset_P']:+.4f} S={m['per_asset_S']:+.4f} "
                  f"sigma={m['sigma_ratio']:.3f} mono={m['monotonicity']}", flush=True)

    if all_m:
        pooled = dict(
            milestone=args.milestone,
            mean_per_asset_P=round(float(np.mean([m["per_asset_P"] for m in all_m])), 4),
            mean_per_asset_S=round(float(np.mean([m["per_asset_S"] for m in all_m])), 4),
            mean_xsec_rank_ic=round(float(np.mean([m["xsec_rank_ic"] for m in all_m])), 4),
            mean_xsec_ic_ir=round(float(np.nanmean([m["xsec_ic_ir"] for m in all_m])), 3),
            linear_residual_rankic_ref=0.0254,
            mean_sigma_ratio=round(float(np.mean([m["sigma_ratio"] for m in all_m])), 4),
            mean_beta=round(float(np.nanmean([m["avg_beta"] for m in all_m])), 3),
            mean_bias_bps=round(float(np.nanmean([m["bias_bps"] for m in all_m])), 4),
            mean_monotonicity=round(float(np.nanmean([m["monotonicity"] for m in all_m])), 3),
            per_fold_P=[round(m["per_asset_P"], 4) for m in all_m],
            per_fold_S=[round(m["per_asset_S"], 4) for m in all_m],
            per_fold_xsec_ic=[round(m["xsec_rank_ic"], 4) for m in all_m],
            per_fold=all_m,
            single_asset_ref_P=0.058,
            shallow_panel_ref_P=0.0328,
            n_params=all_m[0]["n_params"],
        )
        os.makedirs(EXPORT, exist_ok=True)
        out = p.join(EXPORT, f"temporal_spatial_{tag}.json")
        with open(out, "w") as f:
            json.dump(pooled, f, indent=2)
        print("\n===== POOLED 3-FOLD =====", flush=True)
        print(json.dumps({k: v for k, v in pooled.items() if k != "per_fold"}, indent=2), flush=True)
        print(f"\nsaved -> {out}", flush=True)


if __name__ == "__main__":
    main()
