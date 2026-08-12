#!/usr/bin/env python3
"""Does the fapi replay reproduce the training panel's REAL MEMBER110 masks?

> **created:** 2026-07-29 UTC | **Session:** ma-v2 universe_guard pin | **状态:** final

The reconstruction replays `build_wide_dl.py::MEMBER110` on re-fetched daily klines. Two things
could break it and neither announces itself: the daily->hourly DVOL30 mapping (see the CALIBER NOTE
in reconstruct_training_member_union.py) and any drift between the venue's kline history today and
the archive the panel was built from. So it is checked against masks the SERVER actually produced,
at every block where we hold one -- 9 blocks spanning 2021-01 to 2026-06.

★ THE COMPARISON IS SET-EXACT, NOT "close". A member list that is 108/110 right is not 98% correct;
it is two coins the model is asked about that the replay says it was not, which is precisely the
question universe_guard exists to answer. Reported as exact-match booleans plus the offending
symbols, never as a match rate.

★ AND A PASS HERE DOES NOT PROMOTE THE RECONSTRUCTION OVER THE ARTIFACTS. The union shipped to
MANIFEST comes from training_member_union_from_artifacts.py. This script can only corroborate it or
contradict it; it cannot be the source, because it is the weaker of the two instruments.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

LIVE_REPO = os.path.expanduser("~/dl_quant_live")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
HOUR_MS = 3_600_000
TS0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
TS_END = int(pd.Timestamp("2026-07-01", tz="UTC").value // 10**6)


def main():
    z = np.load(os.path.join(OUT_DIR, "training_member_union_blocks.npz"), allow_pickle=True)
    syms = [str(s) for s in z["symbols"]]
    M = z["M"]                                                   # (n_blk, N) reconstructed

    fx = np.load(os.path.join(LIVE_REPO, "state/fixtures/parity_fixture_v2.npz"), allow_pickle=True)
    pi = np.load(os.path.join(LIVE_REPO, "state/fixtures/panel_inputs.npz"), allow_pickle=True)
    assert [str(s) for s in fx["symbols"]] == syms, "axis mismatch vs fixture"

    checks = []

    def compare(label, when, blk, truth):
        rec = M[blk]
        a = {syms[j] for j in np.where(rec)[0]}
        b = {syms[j] for j in np.where(truth)[0]}
        checks.append({"label": label, "when": when, "block": int(blk),
                       "n_recon": len(a), "n_truth": len(b),
                       "exact": a == b,
                       "recon_only": sorted(a - b), "truth_only": sorted(b - a)})

    ats, MK, kinds = fx["anchor_ts"], fx["masks"] > 0, [str(k) for k in fx["anchor_kind"]]
    for i in range(len(ats)):
        ts = int(ats[i])
        blk = ((ts - TS0) // HOUR_MS // 24) // 30
        if ts >= TS_END and blk >= M.shape[0]:
            continue                                             # post-freeze block, not replayed
        compare(kinds[i], str(pd.to_datetime(ts, unit="ms", utc=True))[:10], blk, MK[i])

    pts, PM = pi["ts"].astype(np.int64), pi["MEMBER"]
    row = (pts - TS0) // HOUR_MS
    for b in np.unique((row // 24) // 30):
        idx = np.where(((row // 24) // 30) == b)[0]
        compare("panel_inputs_slice", str(pd.to_datetime(int(pts[idx[0]]), unit="ms", utc=True))[:10],
                int(b), PM[idx[0]])

    art = json.load(open(os.path.join(OUT_DIR, "training_member_union_from_artifacts.json")))
    recon_union = {syms[j] for j in np.where(M.any(0))[0]}
    art_union = set(art["union"])

    res = {"n_checks": len(checks), "n_exact": sum(c["exact"] for c in checks), "checks": checks,
           "union_reconstructed": sorted(recon_union), "n_union_reconstructed": len(recon_union),
           "n_union_artifacts": len(art_union),
           "union_agrees_with_artifacts": recon_union == art_union,
           "in_recon_not_artifacts": sorted(recon_union - art_union),
           "in_artifacts_not_recon": sorted(art_union - recon_union)}
    p = os.path.join(OUT_DIR, "validate_member_reconstruction.json")
    with open(p, "w") as f:
        json.dump(res, f, indent=1)
    for c in checks:
        print(f"  blk{c['block']:>3} {c['when']} {c['label']:<24} recon={c['n_recon']:>3} "
              f"truth={c['n_truth']:>3} EXACT={c['exact']}"
              + ("" if c["exact"] else f"  recon_only={c['recon_only']} truth_only={c['truth_only']}"))
    print(f"\nexact {res['n_exact']}/{res['n_checks']} | union recon={res['n_union_reconstructed']} "
          f"artifacts={res['n_union_artifacts']} agree={res['union_agrees_with_artifacts']}")
    print(f"-> {p}")
    return res


if __name__ == "__main__":
    main()
