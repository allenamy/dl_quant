#!/usr/bin/env python3
"""d10_fund_state_identity.py -- stage 2a identity control, per column and split at the ledger cut.

The first whole-file comparison (d10_build_fund_state.py --compare) reported DIFFERS with 51,715 fewer events on my side. The NC
file was built from `ledger_spliced_p2_to_20260901T0200_streamD_after.npz` (073088e5): P2 up to 2026-09-01T02:00Z, then a second
stream AFTER the cut. ledger_full_ms ends at the cut. A whole-file comparison therefore mixes "different coverage" with "different
arithmetic". This device separates them: per crypto column, events with ft <= CUT are compared field by field bitwise (ft, rate, iv,
ema, prev); events after CUT are COUNTED per side, not compared; kidx is compared on anchors whose as-of cannot reach past the cut
(anchor < CUT). Green = every prefix field bitwise and every pre-cut kidx equal.
usage: d10_fund_state_identity.py MINE.npz REF.npz CUT OUT.json
"""
import hashlib, json, sys
import numpy as np


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    mine, ref, cut, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    A, B = np.load(mine), np.load(ref)
    assert np.array_equal(A["cols"], B["cols"]) and np.array_equal(A["anchors"], B["anchors"])
    an = A["anchors"]; pre_anchor = an < cut
    res = {"mine": [mine, sha(mine)], "ref": [ref, sha(ref)], "cut": cut, "fields": {k: 0 for k in ("ft", "rate", "iv", "ema", "prev")},
           "prefix_len_mismatch_cols": [], "events_pre_cut": {"mine": 0, "ref": 0}, "events_post_cut": {"mine": 0, "ref": 0}}
    for ci in range(len(A["cols"])):
        a0, a1 = int(A["ev_off"][ci]), int(A["ev_off"][ci + 1]); b0, b1 = int(B["ev_off"][ci]), int(B["ev_off"][ci + 1])
        ta, tb = A["ft"][a0:a1], B["ft"][b0:b1]
        na, nb = int((ta <= cut).sum()), int((tb <= cut).sum())
        res["events_pre_cut"]["mine"] += na; res["events_pre_cut"]["ref"] += nb
        res["events_post_cut"]["mine"] += (a1 - a0) - na; res["events_post_cut"]["ref"] += (b1 - b0) - nb
        if na != nb:
            res["prefix_len_mismatch_cols"].append([int(A["cols"][ci]), na, nb]); continue
        for k in res["fields"]:
            x, y = A[k][a0:a0 + na], B[k][b0:b0 + nb]
            if x.dtype.kind == "f":
                same = (x.view(np.uint64) == y.astype(x.dtype).view(np.uint64)) | (np.isnan(x) & np.isnan(y))
            else:
                same = x == y
            res["fields"][k] += int((~same).sum())
    ka, kb = A["kidx"][pre_anchor], B["kidx"][pre_anchor]
    res["kidx_pre_cut_anchors"] = {"cells": int(ka.size), "differ": int((ka != kb).sum())}
    ok = not res["prefix_len_mismatch_cols"] and not any(res["fields"].values()) and res["kidx_pre_cut_anchors"]["differ"] == 0
    res["VERDICT"] = "PREFIX_BITWISE" if ok else "PREFIX_DIFFERS"
    open(out, "w").write(json.dumps(res, indent=1))
    print(res["VERDICT"], json.dumps({k: v for k, v in res.items() if k not in ("mine", "ref")})[:900], flush=True)


if __name__ == "__main__":
    main()
