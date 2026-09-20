#!/usr/bin/env python3
"""bt_g_convention.py — what exactly "g bps per anchor per gross" means in these tables, and how the plausible alternative conventions
differ on the same path files. Written to reconcile three numbers on the HIST window (2023-06-30 → 2025-12-31): the attribution agent's
+0.073, the lead's +0.043, and this project's tables. No simulation; it only reads PATH npz files.

THE CONVENTION THESE TABLES USE (bt_tables.series_from_path / cell_metrics, unchanged since the first commit of the device):
  per anchor k:  r_k = navm1_k / navm0_k − 1            (main-reading NAV, one 4h window, simple return)
                 g_k = 1e4 · r_k / gross_mult           (gross_mult = 2.0 ⇒ the denominator is the TARGET gross = 2 × NAV at window start)
  per cell:      g = arithmetic MEAN of g_k over EVERY anchor in the cell — hold anchors, halt anchors and day-stop anchors included,
                 none dropped; paths are averaged per window first (the mean path) or pooled, which for a mean is the same number.
  identity:      g = price − funding_paid − fee − unknown_excluded (each 1e4 · X / (gross_mult · nav0)); residual ≤ 1.3e-10.
The variants below are the ways the same words can be read differently; each is computed on the same files so the gap can be attributed.
usage: /workspace/venv/bin/python -B bt_g_convention.py PATH,HOME,LC_CTYPE <run_dir> <n_seeds> <start_iso> <end_iso> <out.json>
"""
import os, sys, json, time, calendar, hashlib

import numpy as np

if __name__ == "__main__":
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"

RUN_D, NSEED, A_ISO, B_ISO, OUTP = sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
GM = 2.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(x): return calendar.timegm(time.strptime(x, "%Y-%m-%dT%H:%M:%SZ"))


tag = os.path.basename(RUN_D.rstrip("/"))
P = []
for s in range(NSEED):
    st = os.path.join(RUN_D, f"PATH_{tag}_seed_{s:02d}")
    J = json.load(open(st + ".json")); assert J["npz_sha256"] == sha(st + ".npz"), st
    P.append(dict(np.load(st + ".npz")))
A = P[0]["A"].astype(np.int64)
m = (A >= ts(A_ISO)) & (A <= ts(B_ISO))
out = {"device": "bt_g_convention.py", "self_sha256": sha(os.path.abspath(__file__)), "run_dir": RUN_D, "n_seeds": NSEED,
       "window": [A_ISO, B_ISO], "n_anchors_in_window": int(m.sum()), "gross_mult": GM, "variants": {}}


def rec(name, vals, note):
    out["variants"][name] = {"g_bps_per_anchor": float(np.mean(vals)), "per_path_p05": float(np.percentile(vals, 5)),
                             "per_path_p95": float(np.percentile(vals, 95)), "note": note}


r = [(p["navm1"] / p["navm0"] - 1.0) for p in P]
st = [p["status"] for p in P]
rec("TABLES (this project): mean over ALL anchors of 1e4·r/gross_mult", [1e4 * x[m].mean() / GM for x in r],
    "the convention of every g in the A0 / A0ext tables; nothing is dropped")
for lab, keep in (("no HOLD anchors", 2), ("no HALT anchors", 1)):
    v = []
    for x, s_ in zip(r, st):
        mm = m & (s_ != keep); v.append(1e4 * x[mm].mean() / GM)
    rec(f"drop {lab}", v, f"status == {keep} removed from the population ({int(np.mean([np.sum(m & (s_ == keep)) for s_ in st])):d} anchors on average)")
v = []
for x, s_ in zip(r, st):
    mm = m & (s_ == 0); v.append(1e4 * x[mm].mean() / GM)
rec("drop HOLD and HALT anchors (traded anchors only)", v, "status == 0 only")
rec("value weighted: 1e4 · Σ(navm1−navm0) / Σ(gross_mult·navm0)", [1e4 * np.sum((p["navm1"] - p["navm0"])[m]) / np.sum(GM * p["navm0"][m]) for p in P],
    "one ratio of sums instead of the mean of per-anchor ratios; later (larger) windows weigh more")
rec("realized gross denominator: 1e4 · mean((navm1−navm0)/gross0)", [1e4 * np.mean(((p["navm1"] - p["navm0"]) / np.where(p["gross0"] > 0, p["gross0"], np.nan))[m][np.isfinite(((p["navm1"] - p["navm0"]) / np.where(p["gross0"] > 0, p["gross0"], np.nan))[m])]) for p in P],
    "divides by the REALIZED gross of that window instead of the target gross 2×NAV; windows with gross 0 (flat book) drop out")
rec("compounded: 1e4·(Π(1+r)−1)/n/gross_mult", [1e4 * (np.prod(1.0 + x[m]) - 1.0) / m.sum() / GM for x in r],
    "the window's compounded return spread over its anchors (not an average of per-anchor rates)")
rec("no /gross_mult (NAV-relative bps per anchor)", [1e4 * x[m].mean() for x in r], "same population, denominator = NAV instead of gross")
rec("sim NAV instead of main-reading NAV", [1e4 * (p["nav1"] / p["nav0"] - 1.0)[m].mean() / GM for p in P],
    "UA-FREEZE-EXCLUDE removes UNKNOWN cells from the main NAV; when the rule never binds the two coincide")
json.dump(out, open(OUTP, "w"), indent=1, default=float)
print(f"BT_G_CONVENTION {RUN_D.split('/')[-1]} {A_ISO[:10]}→{B_ISO[:10]} n={int(m.sum())}")
for k, v in out["variants"].items(): print(f"  {v['g_bps_per_anchor']:+.4f}  {k}")
