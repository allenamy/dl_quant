"""NX-S2 pretrain data: ONE share pass over 2022-01-01..2024-05-31 (strictly
BEFORE every fold window -> zero leakage by construction) producing the three
products the P1 ranking-as-pretext pretraining needs, in a layout mirroring the
labeled-period caches so SeqPanelData can be pointed at it unchanged:

  <ROOT>/seq_cache/<day>.npz        F (S,T,44) fp16, mask (S,T), y (S,T y_600), ts
  <ROOT>/mh_targets_long/<day>.npz  y_600/y_1800/y_3600 (S,T) + masks + ts
  <ROOT>/mh_targets/<day>.npz       y_60/y_180/y_600 (S,T) + masks + ts
  <ROOT>/panel_cache/<sym>.npz      X (N,44) last-token @stride-180, y, ts, day,
                                    clean600  (panel index + train stats source)

F-only (no raw LOB) and fp16 keep it ~95GB. Idempotent (skips existing days).
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402
from multi_asset.data.features_ma import (  # noqa: E402
    build_features, compute_y600, valid_mask, HORIZON,
)

SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
WIN_START, WIN_END = 20220101, 20240531
ROOT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
        "multi_asset/exports/pretrain")
PRED_STRIDE, CLEAN_GAP = 180, 600
H_SHORT = [60, 180, 600]
H_LONG = [600, 1800, 3600]


def list_days(a, b):
    return sorted(int(n) for n in os.listdir(_BAR_PATH)
                  if n.isdigit() and len(n) == 8 and a <= int(n) <= b)


def fwd_ret(logm, h):
    T = logm.shape[0]
    y = np.full(T, np.nan, np.float64)
    y[:T - h] = logm[h:] - logm[:T - h]
    return y


def build(force=False):
    for sub in ("seq_cache", "mh_targets_long", "mh_targets", "panel_cache"):
        os.makedirs(p.join(ROOT, sub), exist_ok=True)
    days = list_days(WIN_START, WIN_END)
    print(f"[pre] {len(days)} days {WIN_START}..{WIN_END}", flush=True)
    acc = {s: {k: [] for k in ("X", "y", "ts", "day", "clean600")} for s in SYMBOLS}
    feat_names = None
    t0 = time.time(); n_done = n_skip = n_fail = 0
    for di, d in enumerate(days):
        seq_out = p.join(ROOT, "seq_cache", f"{d}.npz")
        if (not force) and p.exists(seq_out):
            n_skip += 1; continue
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            n_fail += 1; print(f"  [warn] {d}: {e}", flush=True); continue
        T = dp.ts.shape[0]; S = len(SYMBOLS)
        ts_day = dp.ts.astype(np.int64)
        mid_i = dp.cols.index("mid")
        F_all = np.zeros((S, T, 44), np.float16)
        mask_all = np.zeros((S, T), bool)
        y600_all = np.full((S, T), np.nan, np.float32)
        ys = {h: np.full((S, T), np.nan, np.float32) for h in set(H_SHORT + H_LONG)}
        base_idx = np.arange(0, T - HORIZON, PRED_STRIDE)
        for si, s in enumerate(SYMBOLS):
            F, names = build_features(dp, s)
            if feat_names is None:
                feat_names = names
            vm = valid_mask(dp, s)
            mid = dp.data[s][:, mid_i].astype(np.float64)
            logm = np.log(np.where(mid > 0, mid, np.nan))
            F_all[si] = F.astype(np.float16)
            mask_all[si] = vm.astype(bool)
            for h in ys:
                ys[h][si] = fwd_ret(logm, h).astype(np.float32)
            y600_all[si] = ys[600][si]
            # panel_cache accumulation (last-token @ stride-180, valid + finite y600)
            sel = base_idx[vm[base_idx] & np.isfinite(ys[600][si][base_idx])]
            if sel.size:
                flags = np.zeros(sel.shape[0], bool)
                last = None; gap = CLEAN_GAP * 1_000_000_000
                for i, pi in enumerate(sel):
                    t = ts_day[pi]
                    if last is None or t - last >= gap:
                        flags[i] = True; last = t
                acc[s]["X"].append(F[sel].astype(np.float32))
                acc[s]["y"].append(ys[600][si][sel])
                acc[s]["ts"].append(ts_day[sel])
                acc[s]["day"].append(np.full(sel.shape[0], d, np.int32))
                acc[s]["clean600"].append(flags)
        np.savez(seq_out, F=F_all, mask=mask_all, y=y600_all, ts=ts_day)
        np.savez(p.join(ROOT, "mh_targets_long", f"{d}.npz"), ts=ts_day,
                 **{f"y_{h}": ys[h] for h in H_LONG},
                 **{f"m_{h}": np.isfinite(ys[h]) for h in H_LONG})
        np.savez(p.join(ROOT, "mh_targets", f"{d}.npz"), ts=ts_day,
                 **{f"y_{h}": ys[h] for h in H_SHORT},
                 **{f"m_{h}": np.isfinite(ys[h]) for h in H_SHORT})
        n_done += 1
        if n_done % 20 == 0 or di == len(days) - 1:
            el = time.time() - t0
            eta = (len(days) - di - 1) / max(n_done / el, 1e-9)
            print(f"  [{di+1}/{len(days)}] {d} done={n_done} skip={n_skip} "
                  f"fail={n_fail} {el/60:.1f}min ETA {eta/60:.0f}min", flush=True)
    for s in SYMBOLS:
        if acc[s]["X"]:
            np.savez(p.join(ROOT, "panel_cache", f"{s}.npz"),
                     X=np.concatenate(acc[s]["X"]),
                     y=np.concatenate(acc[s]["y"]),
                     ts=np.concatenate(acc[s]["ts"]).astype(np.int64),
                     day=np.concatenate(acc[s]["day"]),
                     clean600=np.concatenate(acc[s]["clean600"]))
    json.dump({"window": [WIN_START, WIN_END], "built": n_done, "skip": n_skip,
               "fail": n_fail, "n_features": len(feat_names or [])},
              open(p.join(ROOT, "build_meta.json"), "w"), indent=2)
    print(f"[pre] DONE built={n_done} skip={n_skip} fail={n_fail} "
          f"in {(time.time()-t0)/60:.0f}min", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    build(force=ap.parse_args().force)
