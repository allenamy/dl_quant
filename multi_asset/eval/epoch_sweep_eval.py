"""STAGE-2 SELECTOR SWEEP (D5) — offline epoch-menu evaluation, near-zero GPU.

For an instrumented fold (metrics.json val_hist + epoch_ckpts/ from train_dual_lob with
save_epoch_ckpts=True), forward-pass EVERY saved epoch ckpt on BOTH the val and test sets,
then score the 4 pre-registered D5 selectors on VAL data ONLY and report the TEST outcome
(per-day-CLEAN + DENSE) of each chosen epoch vs the shipped selection (always-EMA best) and
the test-peek ORACLE ceiling.

Selectors (docs/2026-07-02_phase2_design_appendix.md D5):
  S1 tail-composite   : 0.5*IC_conf(top-20% |pred| val rows) + 0.5*composite -> argmax
  S2 health-gated     : eligible iff val β∈[0.5,1.8] AND σŷ/σy∈[0.02,0.12], then max composite
                        (fallback: epoch nearest the band)
  S3 one-SE-earliest  : split val into 3 time-blocks; score = mean-std(block composites);
                        pick EARLIEST epoch within 1 SE of the best score (kills patience crawl)
  S4 raw-vs-EMA arb   : the S3 rule over the UNION {raw ep, ema ep}, excluding pre-warmup ema

All caliber = same as final_deliverable_l01 (mask applied, q50 vs y std-units). Val composite
matches the trainer's _run_val (full masked val, Pearson+Spearman). ORACLE = test-peek ceiling
(diagnostic only, NEVER a headline). Run on SERVER (needs the caches):
  PYTHONPATH=. python multi_asset/eval/epoch_sweep_eval.py \
      --config configs/d1gate/d1_2026_01_run1.json \
      --fold-dir experiments/d1gate/d1_2026_01_run1/fold_0 [--device cpu]
"""
from __future__ import annotations
import argparse, json, os, os.path as osp, glob
import numpy as np
import torch
# CPU inference: oneDNN can fail to create a conv primitive for this model's shapes
# ("could not create a primitive"); force the native conv path (slower, correct).
torch.backends.mkldnn.enabled = False
from torch.utils.data import DataLoader
from scipy.stats import pearsonr, spearmanr

from multi_asset.train.train_dual_lob import (
    build_dual_lob_model, _forward_dual, _build_folds, _common_ds_kwargs,
    DualLOBDataset, LOBDatasetV2, SlicedLOBDataset,
)

HZ = 600 * 1_000_000
DAY = 86400 * 1_000_000
SIG_BAND = (0.02, 0.12)
BETA_BAND = (0.5, 1.8)


# ---- caliber helpers (identical to final_deliverable_l01) --------------------
def _clean_idx(ts):
    o = np.argsort(ts); keep = []; last = -1e18
    for i in range(len(o)):
        if ts[o[i]] - last >= HZ:
            keep.append(o[i]); last = ts[o[i]]
    return np.array(keep, dtype=int)

def perday_clean(q, y, ts):
    dk = ts // DAY; rs = []; ss = []
    for d in np.unique(dk):
        m = dk == d; k = _clean_idx(ts[m])
        if len(k) > 20:
            qk = q[m][k]; yk = y[m][k]
            if qk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]; s = spearmanr(qk, yk)[0]
                if np.isfinite(r): rs.append(r); ss.append(s)
    return (np.mean(rs) if rs else np.nan), (np.mean(ss) if ss else np.nan)

def dense_P(q, y):
    return pearsonr(q, y)[0] if q.std() > 1e-12 else np.nan

def val_composite(q, y):
    """0.5*Pearson + 0.5*Spearman over all (masked) val rows — matches _run_val."""
    if q.std() < 1e-12: return -9.0, 0.0, 0.0
    P = pearsonr(q, y)[0]; S = spearmanr(q, y)[0]
    P = P if np.isfinite(P) else 0.0; S = S if np.isfinite(S) else 0.0
    return 0.5 * P + 0.5 * S, P, S

def tail_ic(q, y, frac=0.20):
    """IC_conf: Pearson over the top-frac |q| rows."""
    n = len(q); k = max(20, int(frac * n))
    idx = np.argsort(-np.abs(q))[:k]
    qk = q[idx]; yk = y[idx]
    if qk.std() < 1e-12: return 0.0
    r = pearsonr(qk, yk)[0]; return r if np.isfinite(r) else 0.0

def beta_sigma(q, y):
    b = np.cov(y, q)[0, 1] / q.var() if q.var() > 1e-12 else np.nan
    sg = q.std() / (y.std() + 1e-12); return b, sg

def block_composites(q, y, ts, nblocks=3):
    """Split val by time into nblocks equal-duration blocks; composite per block."""
    t0, t1 = ts.min(), ts.max() + 1
    edges = np.linspace(t0, t1, nblocks + 1)
    out = []
    for b in range(nblocks):
        m = (ts >= edges[b]) & (ts < edges[b + 1])
        if m.sum() > 20 and q[m].std() > 1e-12:
            out.append(val_composite(q[m], y[m])[0])
    return np.array(out) if out else np.array([-9.0])


# ---- inference ---------------------------------------------------------------
def _build_ds(config, fold, norm, npz_dir, model_cfg, data_cfg):
    has_perp = bool(model_cfg.get("use_perp_residual", False))
    DatasetCls = DualLOBDataset if has_perp else LOBDatasetV2
    _hsec = data_cfg.get("horizons_sec")
    horizons_list = [f"y_{int(h)}" for h in _hsec] if _hsec else None
    # PRELOAD both splits ONCE (val 45d + test 28d) into RAM so the 22-epoch
    # re-inference doesn't re-read npz from the contended disk every batch.
    common = dict(normalize=True, x_mean=norm["x_mean"], x_std=norm["x_std"],
                  y_norm=(float(norm["y_median"]), float(norm["y_sigma"]), 5.0),
                  preload=True, **_common_ds_kwargs(data_cfg, horizons_list))
    print("[sweep] building val_ds (preload)...", flush=True)
    val_ds = DatasetCls(npz_dir, fold["val"], **common)
    print("[sweep] building test_ds (preload)...", flush=True)
    test_ds = DatasetCls(npz_dir, fold["test"], **common)
    print("[sweep] datasets ready.", flush=True)
    return val_ds, test_ds, has_perp

def infer(model, ds, has_perp, device, batch=512):
    model.eval(); loader = DataLoader(ds, batch_size=batch, shuffle=False)
    qs, tg, mk = [], [], []
    with torch.no_grad():
        for b in loader:
            if has_perp:
                if len(b) == 6: x_feat, x_raw, rp, y, m, x_perp = b
                else: x_feat, x_raw, y, m, x_perp = b; rp = None
            else:
                x_perp = None
                if len(b) == 5: x_feat, x_raw, rp, y, m = b
                elif len(b) == 4: x_feat, x_raw, y, m = b; rp = None
                else: x_feat, y, m = b; x_raw = None; rp = None
            x_feat = x_feat.to(device)
            x_raw = x_raw.to(device) if x_raw is not None else None
            x_perp = x_perp.to(device) if x_perp is not None else None
            rp = rp.to(device) if rp is not None else None
            out = _forward_dual(model, x_feat, x_raw, rp, x_perp)
            qs.append(out["quantiles"].cpu().numpy()); tg.append(y.numpy()); mk.append(m.numpy())
    q = np.concatenate(qs); y = np.concatenate(tg); m = np.concatenate(mk).astype(bool)
    ts = ds.get_all_timestamps() if hasattr(ds, "get_all_timestamps") else np.zeros(len(m), np.int64)
    q50 = (q[:, 1] if q.ndim == 2 else q).astype(np.float64)
    # apply mask (drop padded rows)
    return q50[m], y[m].astype(np.float64), ts[m].astype(np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-dir", required=True)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    cfg = json.load(open(a.config)); model_cfg = cfg.get("model", {}); data_cfg = cfg["data"]; train_cfg = cfg["training"]
    device = torch.device(a.device)
    npz_dir = data_cfg["npz_dir"]
    days = sorted(p[:-4].split("/")[-1] for p in glob.glob(f"{npz_dir}/*.npz")
                  if p.split("/")[-1][0].isdigit())
    fold = _build_folds(days, train_cfg, int(train_cfg.get("embargo_days", 0)))[0]
    norm = dict(np.load(osp.join(a.fold_dir, "norm_params.npz")))
    val_ds, test_ds, has_perp = _build_ds(cfg, fold, norm, npz_dir, model_cfg, data_cfg)
    s0 = val_ds._load_day(0); n_feat = int(s0["X"].shape[-1]); n_lev = int(s0["X_raw"].shape[-2])
    model = build_dual_lob_model(model_cfg, n_feat, n_lev).to(device)

    mj = json.load(open(osp.join(a.fold_dir, "metrics.json")))
    shipped_ep = mj.get("selection", {}).get("ema_best_epoch") or mj.get("best_epoch")
    ema_warmup = 5  # ema ckpts saved from ep>=warmup

    # ---- inference over the whole epoch menu (raw + ema) ---------------------
    ck = {}   # (tag, ep) -> dict of val/test metrics
    for path in sorted(glob.glob(osp.join(a.fold_dir, "epoch_ckpts", "*.pt"))):
        name = osp.basename(path)[:-3]        # e.g. raw_ep008 / ema_ep008
        tag, ep = name.split("_ep"); ep = int(ep)
        sd = torch.load(path, map_location=device, weights_only=False)
        model.load_state_dict(sd["state"] if isinstance(sd, dict) and "state" in sd else sd)
        vq, vy, vts = infer(model, val_ds, has_perp, device)
        tq, ty, tts = infer(model, test_ds, has_perp, device)
        comp, vP, vS = val_composite(vq, vy)
        vb, vsg = beta_sigma(vq, vy)
        tcp, tcs = perday_clean(tq, ty, tts); tdp = dense_P(tq, ty)
        ck[(tag, ep)] = dict(comp=comp, tailic=tail_ic(vq, vy), beta=vb, sig=vsg,
                             blocks=block_composites(vq, vy, vts),
                             test_cdclean=tcp, test_dense=tdp)
        print(f"  [{tag} ep{ep:02d}] valC={comp:+.4f} tailIC={ck[(tag,ep)]['tailic']:+.4f} "
              f"vβ={vb:+.3f} vσ={vsg:.3f} | TEST cdCLEAN={tcp:+.4f} DENSE={tdp:+.4f}", flush=True)

    raw = {ep: m for (tg, ep), m in ck.items() if tg == "raw"}
    ema = {ep: m for (tg, ep), m in ck.items() if tg == "ema"}

    # ---- selectors (on VAL only) --------------------------------------------
    def pick_S1(cand):   # tail-composite argmax
        return max(cand, key=lambda e: 0.5 * cand[e]["tailic"] + 0.5 * cand[e]["comp"])
    def pick_S2(cand):   # health-gated
        elig = [e for e in cand if BETA_BAND[0] <= cand[e]["beta"] <= BETA_BAND[1]
                and SIG_BAND[0] <= cand[e]["sig"] <= SIG_BAND[1]]
        if elig: return max(elig, key=lambda e: cand[e]["comp"])
        # fallback: nearest to the band (min distance of (β,σ) to band box)
        def dist(e):
            b, s = cand[e]["beta"], cand[e]["sig"]
            db = max(0, BETA_BAND[0]-b, b-BETA_BAND[1]); ds = max(0, SIG_BAND[0]-s, s-SIG_BAND[1])
            return db + 10*ds
        return min(cand, key=dist)
    def pick_S3(cand):   # one-SE earliest
        score = {e: (cand[e]["blocks"].mean() - cand[e]["blocks"].std()) for e in cand}
        best = max(score, key=score.get)
        se = cand[best]["blocks"].std() / np.sqrt(max(len(cand[best]["blocks"]), 1))
        thr = score[best] - se
        return min([e for e in cand if score[e] >= thr])   # EARLIEST within 1 SE
    def pick_S4():       # S3 over union {raw, ema>=warmup}
        cand = {}
        for e, m in raw.items(): cand[("raw", e)] = m
        for e, m in ema.items():
            if e >= ema_warmup: cand[("ema", e)] = m
        score = {k: (cand[k]["blocks"].mean() - cand[k]["blocks"].std()) for k in cand}
        best = max(score, key=score.get)
        se = cand[best]["blocks"].std() / np.sqrt(max(len(cand[best]["blocks"]), 1))
        thr = score[best] - se
        elig = [k for k in cand if score[k] >= thr]
        return min(elig, key=lambda k: k[1])   # earliest epoch (either tag)

    sel = {
        "S1 tail-composite":  ("raw", pick_S1(raw)),
        "S2 health-gated":    ("raw", pick_S2(raw)),
        "S3 one-SE-earliest": ("raw", pick_S3(raw)),
        "S4 raw/ema-arb":     pick_S4(),
    }
    # shipped (always-EMA best) + oracle (test-peek ceiling over all candidates)
    shipped = ("ema", shipped_ep) if ("ema", shipped_ep) in ck else ("raw", shipped_ep)
    oracle = max(ck, key=lambda k: (ck[k]["test_cdclean"] if np.isfinite(ck[k]["test_cdclean"]) else -9))

    ship_cd = ck[shipped]["test_cdclean"]
    print(f"\n=== SELECTOR SWEEP: {a.fold_dir} ===")
    print(f"{'selector':22s} {'pick':10s} {'test-cdCLEAN':>12s} {'test-DENSE':>11s} {'Δcd vs shipped':>15s}")
    print(f"{'SHIPPED (alwaysEMA)':22s} {shipped[0]+' ep'+str(shipped[1]):10s} "
          f"{ship_cd:+12.4f} {ck[shipped]['test_dense']:+11.4f} {'—':>15s}")
    for nm, key in sel.items():
        m = ck[key]
        print(f"{nm:22s} {key[0]+' ep'+str(key[1]):10s} {m['test_cdclean']:+12.4f} "
              f"{m['test_dense']:+11.4f} {m['test_cdclean']-ship_cd:+15.4f}")
    print(f"{'ORACLE (test-peek)':22s} {oracle[0]+' ep'+str(oracle[1]):10s} "
          f"{ck[oracle]['test_cdclean']:+12.4f} {ck[oracle]['test_dense']:+11.4f} "
          f"{ck[oracle]['test_cdclean']-ship_cd:+15.4f}")
    print(f"\noracle gap vs shipped = {ck[oracle]['test_cdclean']-ship_cd:+.4f} "
          f"(D5 kill: selector must capture >=50% of this)")
    print("DONE_SWEEP.")


if __name__ == "__main__":
    main()
