#!/usr/bin/env python3
"""pnoise_dbar.py -- dbar(perturbed run, archived NC s42) per segment, using the FROZEN caliber.

Pre-registration: docs/PREREG_perturbation_noise_run_2026-09-24.md (41e5e8776).

load_cell / seg_mask / full_days / daily_on / dbar / boot are IMPORTED from news_stats.py and never
re-implemented here, so there is no second definition of the caliber to drift. news_stats.py L45 is
`BT = DL = None` -- it does not import its own helpers, the caller wires them (news2_stats.py L98-101).

RED CONTROL for random_state=0: dbar against the archived NC cell must be EXACTLY 0.0 in every
segment. That is the pre-registered gate on the whole experiment: it certifies that this harness
(separate root, repointed W constants, base-cell-only config) reproduces the archived chain. A
non-zero value fails the gate; the magnitude is reported so lead can rule, but the gate still fails
and the chain is NOT continued on my own authority.
"""
import argparse, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--news-devices", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--new-tag", required=True)
    ap.add_argument("--nc-dir", required=True)
    ap.add_argument("--nc-tag", required=True)
    ap.add_argument("--random-state", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.news_devices)
    import news_stats as NS
    import bt_tables as _BT
    import bt_driver_lib as _DL
    NS.BT, NS.DL = _BT, _DL

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_perturbation_noise_run_2026-09-24.md @ 41e5e8776",
           "random_state": a.random_state,
           "caliber_source": {"news_stats": os.path.realpath(NS.__file__),
                              "news_stats_sha256": sha(NS.__file__),
                              "bt_tables_sha256": sha(_BT.__file__),
                              "bt_driver_lib_sha256": sha(_DL.__file__),
                              "NPATH": NS.NPATH, "BLOCK_MAIN": NS.BLOCK_MAIN,
                              "SEG": getattr(NS, "SEG", None)},
           "cells": {"perturbed": {"dir": a.new_dir, "tag": a.new_tag},
                     "nc_archived": {"dir": a.nc_dir, "tag": a.nc_tag}}}

    pn, pf = NS.load_cell(a.new_dir, a.new_tag)
    nn, nf = NS.load_cell(a.nc_dir, a.nc_tag)
    rec["n_paths"] = {"perturbed": len(pn), "nc": len(nn)}
    if len(pn) != len(nn):
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "path counts differ; dbar pairs path by path"
        json.dump(rec, open(a.out, "w"), indent=2); print("PNOISE_DBAR UNAVAILABLE"); return 2

    A = pn[0]["A"]
    same_axis = A.shape == nn[0]["A"].shape and bool((A == nn[0]["A"]).all())
    rec["anchor_axis_identical"] = same_axis
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "anchor axes differ; dbar pairs by position"
        json.dump(rec, open(a.out, "w"), indent=2); print("PNOISE_DBAR UNAVAILABLE axes"); return 2

    segs = getattr(NS, "SEG", {}) or {}
    out = {}
    for name, (s0, s1) in segs.items():
        try:
            m = NS.seg_mask(A, s0, s1)
        except Exception as e:
            out[name] = {"note": f"segment unavailable: {type(e).__name__}: {e}"}; continue
        days = NS.full_days(A, m)
        if days.size == 0:
            out[name] = {"note": "no full day in this segment"}; continue
        db, D = NS.dbar(pn, nn, m, days)
        out[name] = {"n_days": int(days.size),
                     "mean_bps_per_day": float(1e4 * db.mean()),
                     "max_abs_daily_bps": float(1e4 * np.abs(db).max()),
                     "exactly_zero": bool(np.all(db == 0.0))}
    rec["dbar_vs_nc"] = out

    if str(a.random_state) == "0":
        zero = all(v.get("exactly_zero") for v in out.values() if "n_days" in v)
        rec["red_control"] = {
            "rule": "random_state=0 must reproduce the archived chain: dbar EXACTLY 0.0 in every segment",
            "all_segments_exactly_zero": bool(zero),
            "baseline_green": bool(zero),
            "note_if_failed": ("the magnitude above is reported so lead can rule; the gate still FAILS "
                               "and the remaining runs are NOT started on my own authority")}
        rec["verdict"] = "MEASURED" if zero else "RED_CONTROL_FAILED"
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"PNOISE_DBAR r={a.random_state} VERDICT={rec['verdict']}")
    for k, v in out.items():
        if "n_days" not in v:
            print(f"   {k:10s} {v.get('note')}"); continue
        print(f"   {k:10s} n_days={v['n_days']:4d}  dbar={v['mean_bps_per_day']:+.6f} bps/day  "
              f"max|daily|={v['max_abs_daily_bps']:.3e}  exactly_zero={v['exactly_zero']}")
    if "red_control" in rec:
        print(f"  RED CONTROL baseline_green={rec['red_control']['baseline_green']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
