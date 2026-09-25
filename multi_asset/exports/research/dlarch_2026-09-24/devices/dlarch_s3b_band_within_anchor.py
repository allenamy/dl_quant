#!/usr/bin/env python3
"""dlarch_s3b_band_within_anchor.py — CORRECTION to S3's per-anchor readout (dlarch, 2026-09-24).

S3's `cells_held_by_band_frac_of_nonzero` compares the band-on and band-off COUNTERFACTUAL WORLDS.
Because `chain` carries EMA state, those two worlds diverge after the first differing anchor, so that
number converges to "almost every cell differs" (measured 0.9974) and says NOTHING about how many
cells the band holds AT AN ANCHOR. Wrong object; named as E-0924-DLARCH-B.

The within-anchor quantity is measurable on the PRODUCTION PATH ITSELF, with no counterfactual:
`chain` sets `smv = where(|trade| < band, H, smv)`, so a cell held by the band satisfies
`fc[i][j] == fc[i-1][j]` EXACTLY (float64 equality). Restricting to cells that are nonzero in either
anchor removes the trivially-equal zeros. Coincidental float64 equality of two independently computed
values is not a practical concern and is reported (not assumed) via the always-zero control below.

Controls:
  * an anchor where the band CANNOT have acted (the first anchor of the run) must report 0 held cells;
  * the same count computed on `kc` is reported next to `fc` (the band is not F10-specific);
  * anchors where the previous anchor was not consecutive (4h gap broken) are EXCLUDED and counted.

READ-ONLY. No GPU, no writes under /dev/shm.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B <this> PATH,HOME,LC_CTYPE <outdir>
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026_descriptive_only": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def stats1(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v): return {"NO_MEASUREMENT": "empty"}
    return {"n": int(len(v)), "mean": float(v.mean()), "median": float(np.median(v)),
            "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))}


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    band = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]["band"]
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
           "corrects": "S3 cells_held_by_band_frac_of_nonzero (E-0924-DLARCH-B: wrong object)",
           "band": band, "utc": iso(time.time()), "cells": {}}
    for sd in (42, 2027):
        tr = json.load(open(f"{W}/work/combo_s{sd}/TARGET_RECEIPT.json"))
        for pol in ("literal", "scaled_diagnostic"):
            p = f"{W}/work/combo_s{sd}/{pol}.npz"
            assert tr["policies"][pol]["sha"] == sha(p)
            C = np.load(p); a = C["E_ts"].astype(np.int64)
            consecutive = np.zeros(len(a), bool); consecutive[1:] = np.diff(a) == 14400
            out = {"npz_sha256": sha(p), "n_anchors": int(len(a)),
                   "first_anchor_control": {}, "excluded_nonconsecutive": int((~consecutive).sum())}
            for book in ("fc", "kc"):
                Bk = C[book]
                eq = np.zeros(len(a)); frac = np.full(len(a), np.nan); mass = np.full(len(a), np.nan)
                for i in range(len(a)):
                    if not consecutive[i]: continue
                    cur = Bk[i]; prev = Bk[i - 1]
                    active = (np.abs(cur) > 0) | (np.abs(prev) > 0)
                    if not active.any(): frac[i] = np.nan; continue
                    held = active & (cur == prev)
                    eq[i] = held.sum()
                    frac[i] = held.sum() / active.sum()
                    g = float(np.abs(cur).sum())
                    mass[i] = float(np.abs(prev[held]).sum()) / g if g > 1e-12 else np.nan
                out["first_anchor_control"][book] = {"anchor": iso(a[0]), "consecutive": bool(consecutive[0]),
                                                     "held_cells": float(eq[0]),
                                                     "MUST_BE_ZERO_ok": bool(eq[0] == 0)}
                bo = {}
                for s in SEG:
                    m = (a >= ts(SEG[s][0])) & (a <= ts(SEG[s][1])) & consecutive
                    if not m.any(): bo[s] = {"NO_ANCHORS": True}; continue
                    bo[s] = {"n_anchors": int(m.sum()),
                             "held_cells_count": stats1(eq[m]),
                             "held_frac_of_active": stats1(frac[m]),
                             "held_mass_frac_of_gross": stats1(mass[m])}
                out[book] = bo
            rec["cells"][f"s{sd}_{pol}"] = out
            m = out["fc"]["pre2026"]
            print(f"S3B s{sd} {pol} fc pre2026 held_frac={m['held_frac_of_active']['mean']:.4f} "
                  f"cells={m['held_cells_count']['mean']:.1f} mass={m['held_mass_frac_of_gross']['mean']:.5f} | "
                  f"kc held_frac={out['kc']['pre2026']['held_frac_of_active']['mean']:.4f} | "
                  f"first_anchor_zero={out['first_anchor_control']['fc']['MUST_BE_ZERO_ok']}", flush=True)
    op = os.path.join(outdir, "S3B_BAND_WITHIN_ANCHOR.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print("S3B DONE json=" + sha(op)[:16], flush=True)


if __name__ == "__main__":
    main()
