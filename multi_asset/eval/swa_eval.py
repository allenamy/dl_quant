"""SWA / EPOCH-AVERAGING eval on the saved per-epoch ckpts (Stage-2, §3.6).

For an instrumented fold, average the state_dicts of the top-K VAL-composite epochs
(VAL-side selection only, NO test peek — ranks from metrics.json val_hist, which is the
same val composite the trainer logged), then run ONE test inference per (tag,K) with the
averaged weights. Kills the single-epoch variance that a point selector (S4) is exposed to.

Reports cd-CLEAN + DENSE + β for SWA-{raw,ema}-K{3,5} vs the shipped always-EMA selection.
LIGHT: ranks from val_hist (no per-epoch val inference), so it's ~4 test inferences/menu.
Reuses the sweep's dataset/inference helpers. Same caliber as final_deliverable_l01.

Run (GPU exclusivity — CPU or a clean GPU slot):
  PYTHONPATH=. python multi_asset/eval/swa_eval.py \
      --config configs/d1gate/d1_2026_01_run1.json \
      --fold-dir experiments/d1gate/d1_2026_01_run1/fold_0 [--device cpu]
"""
from __future__ import annotations
import argparse, json, os, os.path as osp, glob
import numpy as np
import torch
torch.backends.mkldnn.enabled = False   # CPU oneDNN conv guard (same as sweep)

from multi_asset.eval.epoch_sweep_eval import (
    _build_ds, infer, perday_clean, dense_P, beta_sigma,
)
from multi_asset.train.train_dual_lob import build_dual_lob_model, _build_folds


def _load_state(path, device):
    sd = torch.load(path, map_location=device, weights_only=False)
    return sd["state"] if isinstance(sd, dict) and "state" in sd else sd


def swa_average(paths, device):
    """Elementwise mean of the state_dicts; int buffers keep the first (frozen stats)."""
    states = [_load_state(p, device) for p in paths]
    avg = {}
    for name in states[0]:
        ts = [s[name] for s in states]
        if torch.is_floating_point(ts[0]):
            avg[name] = torch.stack([t.float() for t in ts]).mean(0).to(ts[0].dtype)
        else:
            avg[name] = ts[0]
    return avg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-dir", required=True)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    cfg = json.load(open(a.config)); mcfg = cfg.get("model", {}); dcfg = cfg["data"]; tcfg = cfg["training"]
    device = torch.device(a.device)
    npz_dir = dcfg["npz_dir"]
    days = sorted(p[:-4].split("/")[-1] for p in glob.glob(f"{npz_dir}/*.npz")
                  if p.split("/")[-1][0].isdigit())
    fold = _build_folds(days, tcfg, int(tcfg.get("embargo_days", 0)))[0]
    norm = dict(np.load(osp.join(a.fold_dir, "norm_params.npz")))
    _, test_ds, has_perp = _build_ds(cfg, fold, norm, npz_dir, mcfg, dcfg)
    s0 = test_ds._load_day(0)
    model = build_dual_lob_model(mcfg, int(s0["X"].shape[-1]), int(s0["X_raw"].shape[-2])).to(device)

    mj = json.load(open(osp.join(a.fold_dir, "metrics.json")))
    vh = mj.get("val_hist") or []
    shipped_ep = (mj.get("selection") or {}).get("ema_best_epoch") or mj.get("best_epoch")
    ema_warmup = 5

    # rank epochs by VAL composite (from val_hist), per tag; map epoch -> ckpt path
    def ckpt_path(tag, ep):
        return osp.join(a.fold_dir, "epoch_ckpts", f"{tag}_ep{ep:03d}.pt")
    ranked = {"raw": [], "ema": []}
    for e in vh:
        ep = e["epoch"]
        if e.get("raw") and os.path.exists(ckpt_path("raw", ep)):
            ranked["raw"].append((ep, e["raw"]["composite"]))
        if e.get("ema") and ep >= ema_warmup and os.path.exists(ckpt_path("ema", ep)):
            ranked["ema"].append((ep, e["ema"]["composite"]))
    for t in ranked:
        ranked[t].sort(key=lambda x: x[1], reverse=True)   # top val composite first

    # shipped test cd-CLEAN from the saved EMA preds (no inference)
    def shipped_metrics():
        f = osp.join(a.fold_dir, "ema_test_preds.npz")
        z = np.load(f, allow_pickle=True); pr = z["predictions"].astype(np.float64)
        q = pr[:, 1] if pr.ndim == 2 else pr; y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
        if "mask" in z.files:
            m = z["mask"].astype(bool); q, y, ts = q[m], y[m], ts[m]
        cd, _ = perday_clean(q, y, ts); dn = dense_P(q, y); b, _ = beta_sigma(q, y)
        return cd, dn, b
    scd, sdn, sb = shipped_metrics()

    print(f"\n=== SWA EVAL: {a.fold_dir} ===")
    print(f"{'method':16s} {'epochs':22s} {'cdCLEAN':>8s} {'DENSE':>8s} {'β':>7s} {'Δcd_ship':>9s}")
    print(f"{'SHIPPED(EMA e'+str(shipped_ep)+')':16s} {'-':22s} {scd:+8.4f} {sdn:+8.4f} {sb:+7.2f} {'—':>9s}")
    results = {}
    for tag in ("raw", "ema"):
        for K in (3, 5):
            if len(ranked[tag]) < K:
                continue
            eps = [ep for ep, _ in ranked[tag][:K]]
            avg = swa_average([ckpt_path(tag, ep) for ep in eps], device)
            model.load_state_dict(avg)
            tq, ty, tts = infer(model, test_ds, has_perp, device)
            cd, _ = perday_clean(tq, ty, tts); dn = dense_P(tq, ty); b, _ = beta_sigma(tq, ty)
            results[f"SWA-{tag}-K{K}"] = (cd, dn, b, eps)
            print(f"{'SWA-'+tag+'-K'+str(K):16s} {str(sorted(eps)):22s} {cd:+8.4f} {dn:+8.4f} "
                  f"{b:+7.2f} {cd-scd:+9.4f}", flush=True)
    if results:
        best = max(results, key=lambda k: results[k][0])
        print(f"\nbest SWA = {best} cd={results[best][0]:+.4f} (Δ vs shipped {results[best][0]-scd:+.4f})")
    print("DONE_SWA.")


if __name__ == "__main__":
    main()
