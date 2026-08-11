#!/usr/bin/env python3
"""Export the Alpha-101/GTJA-191 sweep survivors as a factor cache for 0C's factory.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Recompute the survivor formulas on the ohlcv panel (full 230351 grid) and write them into
survivor_factor_cache/<sym>.npz (funding-cache schema) so build_funding_ema_preds can emit the
pred panels 0C's factory consumes (panel_ref + fold preds, ≥3600 CL, 3 folds). Survivors + signs
are read from alpha_sweep_h3600.json (sign = +1 if screen IC>0 so high score = long).
Usage: PYTHONPATH=. python multi_asset/alpha/export_survivors.py
"""
from __future__ import annotations
import json, os, os.path as p
import numpy as np

from multi_asset.alpha.alpha_sweep import load_panel, OUT as EDA
from multi_asset.alpha.formulas import build_formulas
from multi_asset.baselines.xsec_ridge import SYMBOLS

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
CACHE = ROOT + "/survivor_factor_cache"


def main():
    d = json.load(open(p.join(EDA, "alpha_sweep_h3600.json")))
    surv = [(r["name"], 1.0 if r["ic"] > 0 else -1.0) for r in d["table"] if r["survivor"]]
    print(f"[export] survivors: {surv}", flush=True)
    P = load_panel()
    F = build_formulas(P)
    names = [nm for nm, _ in surv]
    signs = {nm: s for nm, s in surv}
    cols = [np.asarray(F[nm], dtype=np.float32) for nm in names]      # each (nT,nS)
    X = np.stack(cols, axis=-1)                                        # (nT, nS, k)
    os.makedirs(CACHE, exist_ok=True)
    for si, s in enumerate(SYMBOLS):
        np.savez(p.join(CACHE, f"{s}.npz"), X=X[:, si, :],
                 ts=P.ts.astype(np.int64), day=P.day.astype(np.int64),
                 factor_names=np.array(names, dtype=object))
    fin = np.isfinite(X).mean(axis=(0, 1))
    print(f"[export] wrote {len(names)} survivors -> {CACHE}", flush=True)
    for k, nm in enumerate(names):
        print(f"   {nm:12s} sign={signs[nm]:+.0f} finite={fin[k]:.3f}", flush=True)
    # emit the sign map for the pred-build step
    json.dump({nm: signs[nm] for nm in names}, open(p.join(CACHE, "_signs.json"), "w"))


if __name__ == "__main__":
    main()
