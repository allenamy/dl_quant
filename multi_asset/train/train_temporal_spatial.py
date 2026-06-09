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
# Streaming predict over a split -> pred (T,S) in NORM units (NaN where invalid).
# --------------------------------------------------------------------------- #
def predict_split(model, data, split_rows, batch_ts=64):
    model.eval()
    T, S = data.ts.shape[0], data.S
    pred = np.full((T, S), np.nan, np.float32)
    with torch.no_grad():
        for b in data.iter_day_batches(split_rows, batch_ts, rng=None, shuffle=False):
            xb = torch.from_numpy(b["Xseq"]).to(DEV)
            mb = torch.from_numpy(b["mask"]).to(DEV)
            q50 = model(xb, mb).detach().cpu().numpy()          # (B,S) norm
            q50 = np.where(b["mask"] > 0.5, q50, np.nan)
            pred[b["rows"]] = q50
    return pred


def eval_metrics(pred, Y, CL, sigma, clean=True, min_n=50):
    S = Y.shape[1]
    per_P, per_S, sr_n, sr_d = [], [], 0.0, 0.0
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
        sr_n += (ph * sigma[si]).std() * m.sum()
        sr_d += yr.std() * m.sum()
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
        n_xsec_ts=int(xsec.size),
        sigma_ratio=float(sr_n / sr_d) if sr_d > 0 else float("nan"),
    )


# --------------------------------------------------------------------------- #
# Train one fold.
# --------------------------------------------------------------------------- #
def train_fold(fold_i, fold, data, milestone, max_epochs, patience,
               cap_w=None, verbose=True, day_override=None):
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
    data._day_cache.clear()          # free previous fold's cached days
    data.enable_cache(True)          # cache day arrays in RAM (no per-epoch disk IO)
    tr_rows = np.where(np.isin(data.day, tr_days))[0]
    tr_rows = tr_rows[::TRAIN_STRIDE_SUB]    # thin train grid (less overlap, ~2x faster)
    va_rows = np.where(np.isin(data.day, va_days))[0]
    te_rows = np.where(np.isin(data.day, te_days))[0]
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
        nhead=NHEAD, dropout=DROPOUT, cap_weights=cap_t, **flags).to(DEV)
    if fold_i == 0 and verbose:
        print(f"[model] TemporalSpatialPanelModel params={count_params(model):,} "
              f"(d={D_MODEL}, blocks={N_BLOCKS}, kernel={KERNEL}, milestone=M{milestone}, "
              f"flags={flags})", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    rng = np.random.default_rng(SEED)

    best_val, best_state, best_epoch, bad = -1e9, None, -1, 0
    for ep in range(max_epochs):
        model.train()
        t_ep = time.time()
        ep_loss = ep_pin = ep_h = ep_x = 0.0
        nb = 0
        for b in data.iter_day_batches(tr_rows, BATCH_TS, rng=rng, shuffle=True):
            xb = torch.from_numpy(b["Xseq"]).to(DEV)
            yb = torch.from_numpy(b["y"]).to(DEV)
            mb = torch.from_numpy(b["mask"]).to(DEV)
            out = model(xb, mb, return_dict=True)
            q50 = out["q50"]
            lpin = pinball_loss(out["quantiles"], yb, mb)
            lh = masked_huber(q50, yb, mb, delta=HUBER_DELTA)
            lx = soft_xsec_rank_loss(q50, yb, mb)
            loss = LAMBDA_PINBALL * lpin + LAMBDA_HUBER * lh + LAMBDA_XSEC * lx
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += float(loss.item()); ep_pin += float(lpin.item())
            ep_h += float(lh.item()); ep_x += float(lx.item()); nb += 1
        ep_loss /= max(nb, 1); ep_pin /= max(nb, 1); ep_h /= max(nb, 1); ep_x /= max(nb, 1)

        vpred = predict_split(model, data, va_rows)
        vm = eval_metrics(vpred, data.Y, data.CL, data.sigma, clean=False)
        vP, vS, vsig = vm["per_asset_P"], vm["per_asset_S"], vm["sigma_ratio"]
        gated = np.isfinite(vsig) and vsig >= SIGMA_GATE
        vscore = (0.5 * vP + 0.5 * vS) if (np.isfinite(vP) and np.isfinite(vS)) else float("nan")
        if verbose:
            tag = "" if gated else "  [sigma<gate -> not BEST]"
            print(f"  ep{ep:2d} ({time.time()-t_ep:.0f}s) loss={ep_loss:.4f} "
                  f"(pin={ep_pin:.4f} huber={ep_h:.4f} xsec={ep_x:.4f})  "
                  f"val_P={vP:+.4f} val_S={vS:+.4f} score={vscore:+.4f} "
                  f"sigma={vsig:.3f}{tag}", flush=True)
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
    tpred = predict_split(model, data, te_rows)
    metrics = eval_metrics(tpred, data.Y, data.CL, data.sigma, clean=True)
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
    args = ap.parse_args()

    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    t0 = time.time()
    data = SeqPanelData()
    print(f"[panel] T={len(data.ts)} S={data.S} uniq_days={len(data.uniq_days)} "
          f"(index built {time.time()-t0:.1f}s)", flush=True)
    cap_w = load_cap_weights() if args.milestone == 2 else None
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

    print(f"\n===== FULL 3-FOLD (M{args.milestone}) =====", flush=True)
    all_m = []
    for i, fold in enumerate(FOLDS):
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, data, args.milestone,
                       max_epochs=MAX_EPOCHS, patience=PATIENCE,
                       cap_w=cap_w, verbose=True)
        if m is not None:
            all_m.append(m)
            print(f"[fold {i}] per-asset P={m['per_asset_P']:+.4f} S={m['per_asset_S']:+.4f} "
                  f"xsec_IC={m['xsec_rank_ic']:+.4f} sigma={m['sigma_ratio']:.3f}", flush=True)

    if all_m:
        pooled = dict(
            milestone=args.milestone,
            mean_per_asset_P=round(float(np.mean([m["per_asset_P"] for m in all_m])), 4),
            mean_per_asset_S=round(float(np.mean([m["per_asset_S"] for m in all_m])), 4),
            mean_xsec_rank_ic=round(float(np.mean([m["xsec_rank_ic"] for m in all_m])), 4),
            mean_sigma_ratio=round(float(np.mean([m["sigma_ratio"] for m in all_m])), 4),
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
