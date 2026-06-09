"""R4 trainer: FULL shared-backbone REG_arch panel (PanelREGArch = DualPathLOBModelV3
dual-path + raw LOB + FiLM + cross-asset attn) on the cross-sectional RESIDUAL objective.

Same data/folds/loss/eval as the R1 residual run (train_temporal_spatial), but the model
is the full REG_arch (with the 5-level raw-LOB path) instead of the stripped Conformer,
and the dataset additionally streams the raw-LOB windows. Regime prior = zeros for v1
(FiLM degrades to a constant gate; a learned regime can be added later).

Usage:
  python3 multi_asset/train/train_panel_regarch.py            # full 3-fold
  python3 multi_asset/train/train_panel_regarch.py --smoke    # fold 0 partial
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
from scipy.stats import pearsonr, spearmanr  # noqa: F401 (used via eval_metrics)

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.seq_panel_dataset import SeqPanelData  # noqa: E402
from multi_asset.model.panel_reg_arch import PanelREGArch, count_params  # noqa: E402
from multi_asset.losses.xsec_residual_loss import (  # noqa: E402
    residual_loss, cross_sectional_residual,
)
from multi_asset.train.train_temporal_spatial import (  # noqa: E402  reuse
    fold_day_lists, eval_metrics, FOLDS,
)

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
LR = 6e-4
WD = 0.01
BATCH_TS = 24            # raw-LOB adds memory -> smaller than R1's 64
TRAIN_STRIDE_SUB = 2
MAX_EPOCHS = 20
PATIENCE = 4
RANK_KIND = "lambda"
SEED = 42
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def gpu_day_batches_raw(F_all, Xraw_all, mask_all, y_all, rows, bars,
                        mu_g, sd_g, offs_g, W, batch_ts, rng=None, shuffle=True):
    F_g = torch.from_numpy(F_all).to(DEV)
    F_g = ((torch.nan_to_num(F_g, nan=0.0) - mu_g) / sd_g).clamp_(-10.0, 10.0)
    Xr_g = torch.nan_to_num(torch.from_numpy(Xraw_all).to(DEV), nan=0.0)  # (S,T,5,4)
    y_g = torch.from_numpy(y_all).to(DEV)
    mask_g = torch.from_numpy(mask_all.astype(np.float32)).to(DEV)
    bars_g = torch.from_numpy(bars).to(DEV)
    order = np.arange(bars.shape[0])
    if shuffle and rng is not None:
        rng.shuffle(order)
    for b0 in range(0, order.shape[0], batch_ts):
        bidx = torch.from_numpy(order[b0:b0 + batch_ts]).to(DEV)
        bb = bars_g[bidx]
        widx = bb[:, None] + offs_g[None, :]                  # (B,W)
        Xseq = F_g[:, widx, :].permute(1, 0, 2, 3).contiguous()        # (B,S,W,F)
        Xraw = Xr_g[:, widx, :, :].permute(1, 0, 2, 3, 4).contiguous()  # (B,S,W,5,4)
        ymat = y_g[:, bb].t()
        mmat = mask_g[:, bb].t() * torch.isfinite(ymat).float()
        yield Xseq, Xraw, torch.nan_to_num(ymat, nan=0.0), mmat, rows[order[b0:b0 + batch_ts]]


def predict_split_raw(model, data, split_rows, mu_g, sd_g, offs_g, batch_ts=48):
    model.eval()
    T, S = data.ts.shape[0], data.S
    pred = np.full((T, S), np.nan, np.float32)
    with torch.no_grad():
        for F_all, Xraw_all, mask_all, y_all, rows, bars in data.iter_days_raw(
                split_rows, rng=None, shuffle=False):
            for Xseq, Xraw, yraw, mmat, rr in gpu_day_batches_raw(
                    F_all, Xraw_all, mask_all, y_all, rows, bars, mu_g, sd_g,
                    offs_g, data.W, batch_ts, rng=None, shuffle=False):
                B, S_, _, _ = Xseq.shape
                rg = torch.zeros(B, S_, 6, device=DEV)
                q50 = model(Xseq, Xraw, rg, mmat)["q50"].detach().cpu().numpy()
                q50 = np.where(mmat.cpu().numpy() > 0.5, q50, np.nan)
                pred[rr] = q50
    return pred


def train_fold(fold_i, fold, data, max_epochs, patience, verbose=True, day_override=None):
    uniq = data.uniq_days
    if day_override is not None:
        tr_days, va_days, te_days = day_override
    else:
        lists = fold_day_lists(uniq, fold)
        if lists is None:
            return None
        tr_days, va_days, te_days = lists
    import glob
    built = set(int(p.basename(f)[:8]) for f in glob.glob(p.join(data.seq_dir, "2*.npz")))
    tr_days = np.array([d for d in tr_days if int(d) in built])
    va_days = np.array([d for d in va_days if int(d) in built])
    te_days = np.array([d for d in te_days if int(d) in built])
    if len(tr_days) < 20 or len(va_days) < 3 or len(te_days) < 3:
        print(f"[fold {fold_i}] not enough built days — skip", flush=True)
        return None

    data.set_fold(tr_days)
    data._day_cache.clear(); data.enable_cache(True)
    tr_rows = np.where(np.isin(data.day, tr_days))[0][::TRAIN_STRIDE_SUB]
    va_rows = np.where(np.isin(data.day, va_days))[0]
    te_rows = np.where(np.isin(data.day, te_days))[0]
    if verbose:
        print(f"[fold {fold_i}] days tr={len(tr_days)} va={len(va_days)} te={len(te_days)} | "
              f"rows tr={len(tr_rows)} va={len(va_rows)} te={len(te_rows)}", flush=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    model = PanelREGArch(n_assets=data.S).to(DEV)
    if fold_i == 0 and verbose:
        print(f"[model] PanelREGArch (full REG_arch dual-path) params={count_params(model):,}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    rng = np.random.default_rng(SEED)
    mu_g = torch.from_numpy(data.mu).to(DEV); sd_g = torch.from_numpy(data.sd).to(DEV)
    resid_sigma_g = torch.from_numpy(data.resid_sigma).to(DEV)
    offs_g = torch.arange(-data.W + 1, 1, device=DEV)

    best_val, best_state, best_epoch, bad = -1e9, None, -1, 0
    for ep in range(max_epochs):
        model.train(); t_ep = time.time(); ep_loss = ep_h = ep_r = ep_p = 0.0; nb = 0
        for F_all, Xraw_all, mask_all, y_all, rows, bars in data.iter_days_raw(
                tr_rows, rng=rng, shuffle=True):
            for Xseq, Xraw, yraw, mb, _ in gpu_day_batches_raw(
                    F_all, Xraw_all, mask_all, y_all, rows, bars, mu_g, sd_g,
                    offs_g, data.W, BATCH_TS, rng=rng, shuffle=True):
                B, S_, _, _ = Xseq.shape
                rg = torch.zeros(B, S_, 6, device=DEV)
                out = model(Xseq, Xraw, rg, mb, return_dict=True)
                r, _ = cross_sectional_residual(yraw, mb)
                r = (r / resid_sigma_g[None, :]).clamp(-5.0, 5.0)
                loss, parts = residual_loss(out["quantiles"], r, mb, rank_kind=RANK_KIND)
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
                ep_loss += float(loss.item()); ep_h += parts["huber"]
                ep_r += parts["rank"]; ep_p += parts["pin"]; nb += 1
        nb = max(nb, 1); ep_loss/=nb; ep_h/=nb; ep_r/=nb; ep_p/=nb

        vpred = predict_split_raw(model, data, va_rows, mu_g, sd_g, offs_g)
        vm = eval_metrics(vpred, data.Y, data.CL, data.resid_sigma, clean=False)
        vIC = vm["xsec_rank_ic"]; vscore = vIC
        if verbose:
            print(f"  ep{ep:2d} ({time.time()-t_ep:.0f}s) loss={ep_loss:.4f} "
                  f"(huber={ep_h:.4f} rank={ep_r:.4f} pin={ep_p:.4f})  "
                  f"val_rankIC={vIC:+.4f} val_perP={vm['per_asset_P']:+.4f}", flush=True)
        score = vscore if np.isfinite(vscore) else -1e9
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
    tpred = predict_split_raw(model, data, te_rows, mu_g, sd_g, offs_g)
    m = eval_metrics(tpred, data.Y, data.CL, data.resid_sigma, clean=True)
    m["best_epoch"] = best_epoch; m["n_params"] = count_params(model)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--tag", type=str, default="R4_regarch_residual")
    args = ap.parse_args()
    print(f"[env] device={DEV} torch={torch.__version__}", flush=True)
    data = SeqPanelData()
    print(f"[panel] T={len(data.ts)} S={data.S} days={len(data.uniq_days)}", flush=True)

    if args.smoke:
        import glob
        built = sorted(int(p.basename(f)[:8]) for f in glob.glob(p.join(data.seq_dir, "2*.npz")))
        built = [d for d in built if d in set(data.uniq_days.tolist())][:45]
        n = len(built); ntr = max(20, int(n * 0.7))
        tr = built[:ntr]; va = built[ntr:ntr + max(5, (n - ntr)//2)]; te = built[ntr+len(va):]
        print(f"\n===== SMOKE: tr={len(tr)} va={len(va)} te={len(te)} =====", flush=True)
        m = train_fold(0, FOLDS[0], data, 4, 999, verbose=True,
                       day_override=(np.array(tr), np.array(va), np.array(te)))
        print(json.dumps(m, indent=2), flush=True); return

    print("\n===== FULL 3-FOLD (R4 full REG_arch residual) =====", flush=True)
    all_m = []
    for i, fold in enumerate(FOLDS):
        print(f"\n----- fold {i} -----", flush=True)
        m = train_fold(i, fold, data, MAX_EPOCHS, PATIENCE, verbose=True)
        if m is not None:
            all_m.append(m)
            print(f"[fold {i}] xsec_rankIC={m['xsec_rank_ic']:+.4f} IC-IR={m['xsec_ic_ir']:.2f} "
                  f"| per-asset P={m['per_asset_P']:+.4f} S={m['per_asset_S']:+.4f} "
                  f"mono={m['monotonicity']}", flush=True)
    if all_m:
        pooled = dict(
            model="PanelREGArch_full_regarch", objective="cross_sectional_residual",
            mean_xsec_rank_ic=round(float(np.mean([m["xsec_rank_ic"] for m in all_m])), 4),
            mean_xsec_ic_ir=round(float(np.nanmean([m["xsec_ic_ir"] for m in all_m])), 3),
            mean_per_asset_P=round(float(np.mean([m["per_asset_P"] for m in all_m])), 4),
            mean_per_asset_S=round(float(np.mean([m["per_asset_S"] for m in all_m])), 4),
            per_fold_xsec_ic=[round(m["xsec_rank_ic"], 4) for m in all_m],
            linear_residual_rankic_ref=0.0254, r1_conformer_rankic_ref=0.0464,
            per_fold=all_m, n_params=all_m[0]["n_params"])
        os.makedirs(EXPORT, exist_ok=True)
        out = p.join(EXPORT, f"panel_regarch_{args.tag}.json")
        json.dump(pooled, open(out, "w"), indent=2)
        print("\n===== POOLED =====", flush=True)
        print(json.dumps({k: v for k, v in pooled.items() if k != "per_fold"}, indent=2), flush=True)
        print(f"saved -> {out}", flush=True)


if __name__ == "__main__":
    main()
