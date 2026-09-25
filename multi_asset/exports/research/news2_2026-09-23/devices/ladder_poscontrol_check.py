#!/usr/bin/env python3
"""ladder_poscontrol_check.py -- lead's step-3 positive control gate.

Gate, lead's words: "正控制(新增): 全部数组换成 NEW 的 ⇒ 目标文件须复现 NEW 在案目标
(max|Δw| <= 1e-6, 不到就逐输入报哪一项没带进来). 这证明阶梯的两端就是 NC 与 NEW".

So this device reports, per policy, max|Δw| over the common anchor axis, and when the gate fails it
reports WHERE (which anchors / which fields) rather than a single pooled number -- a pooled max hides
whether one anchor or all of them disagree, and a pooled rate already burned me once this week.
"""
import argparse, hashlib, json, os, pathlib, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine-dir", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "prereg": "docs/PREREG_gap_carrier_ladder_2026-09-25.md @ be4a013a8 (step 3 positive control)",
           "criterion_author": "team-lead (not news2)",
           "gate": "max|dw| <= 1e-6 vs NEW's archived targets, else report which input is missing",
           "policies": {}}

    verdicts = []
    for pol in ("literal", "scaled_diagnostic"):
        pm = pathlib.Path(a.mine_dir) / (pol + ".npz")
        pn = pathlib.Path(a.new_dir) / (pol + ".npz")
        M = np.load(pm, allow_pickle=False)
        N = np.load(pn, allow_pickle=False)
        d = {"mine": str(pm), "mine_sha": sha(pm), "new": str(pn), "new_sha": sha(pn),
             "mine_keys": sorted(M.files), "new_keys": sorted(N.files)}

        tm = M["E_ts"].astype(np.int64)
        tn = N["E_ts"].astype(np.int64)
        d["axis"] = {"mine_n": int(tm.size), "new_n": int(tn.size),
                     "identical": bool(np.array_equal(tm, tn))}
        assert np.array_equal(M["symbols"], N["symbols"]), "symbol axis differs"
        if not d["axis"]["identical"]:
            common = np.intersect1d(tm, tn)
            im = np.searchsorted(tm, common); inn = np.searchsorted(tn, common)
            d["axis"]["common_n"] = int(common.size)
        else:
            im = inn = slice(None)
            d["axis"]["common_n"] = int(tm.size)

        wm = np.asarray(M["weights"], np.float64)[im]
        wn = np.asarray(N["weights"], np.float64)[inn]
        dw = np.abs(wm - wn)
        d["weights"] = {"max_abs_dw": float(dw.max()), "n_cells": int(dw.size),
                        "n_cells_over_1e-6": int((dw > 1e-6).sum()),
                        "n_anchors_over_1e-6": int((dw > 1e-6).any(1).sum()),
                        "bitwise_identical": bool(np.array_equal(wm, wn))}
        tmk_m = np.asarray(M["trade_mask"], bool)[im]
        tmk_n = np.asarray(N["trade_mask"], bool)[inn]
        d["trade_mask"] = {"mine_publish": int(tmk_m.sum()), "new_publish": int(tmk_n.sum()),
                           "disagreeing_anchors": int((tmk_m != tmk_n).sum())}
        rsn_m = np.asarray(M["reason"])[im]
        rsn_n = np.asarray(N["reason"])[inn]
        d["reason"] = {"disagreeing_anchors": int((rsn_m != rsn_n).sum())}
        if d["weights"]["max_abs_dw"] > 1e-6:
            bad = np.flatnonzero(dw.max(1) > 1e-6)
            d["first_disagreeing_anchors"] = [int(tm[im][i]) if not isinstance(im, slice) else int(tm[i])
                                              for i in bad[:10]]
            d["per_year_anchors_over_1e-6"] = {}
            import datetime
            ts = tm if isinstance(im, slice) else tm[im]
            yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in ts])
            over = dw.max(1) > 1e-6
            for y in np.unique(yr):
                m = yr == y
                d["per_year_anchors_over_1e-6"][str(int(y))] = {
                    "anchors": int(m.sum()), "over": int((over & m).sum()),
                    "max_abs_dw": float(dw[m].max())}
        verdicts.append(d["weights"]["max_abs_dw"] <= 1e-6)
        rec["policies"][pol] = d

    rec["verdict"] = "POSITIVE_CONTROL_PASS" if all(verdicts) else "POSITIVE_CONTROL_FAIL"
    pathlib.Path(a.out).write_text(json.dumps(rec, indent=2))
    print("VERDICT", rec["verdict"])
    for pol, d in rec["policies"].items():
        w = d["weights"]
        print(f"  {pol:18s} max|dw|={w['max_abs_dw']:.6e}  cells>1e-6={w['n_cells_over_1e-6']}"
              f"  anchors>1e-6={w['n_anchors_over_1e-6']}/{d['axis']['common_n']}"
              f"  bitwise={w['bitwise_identical']}")
        print(f"                     publish mine={d['trade_mask']['mine_publish']} "
              f"new={d['trade_mask']['new_publish']} "
              f"mask_disagree={d['trade_mask']['disagreeing_anchors']} "
              f"reason_disagree={d['reason']['disagreeing_anchors']}")
        if "per_year_anchors_over_1e-6" in d:
            for y, v in d["per_year_anchors_over_1e-6"].items():
                print(f"                       {y}: {v['over']:5d}/{v['anchors']:5d} anchors  "
                      f"max|dw|={v['max_abs_dw']:.4e}")
    return 0 if all(verdicts) else 3


if __name__ == "__main__":
    sys.exit(main())
