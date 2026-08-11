#!/usr/bin/env python3
"""The training MEMBER110 union, DETERMINED (not reconstructed) from real training-panel slices.

> **created:** 2026-07-29 UTC | **Session:** ma-v2 universe_guard pin | **状态:** final
> **作废条件:** 若 funding_span_table.json 的 140 列集合变更, 或冻结模型换代(重训) 则重算

★ THE PREMISE THAT TURNED OUT TO BE FALSE.
`live/universe_guard.py` states the union "must be computed WHERE THE PANEL LIVES (the training
host) and cannot be reconstructed from the checkpoints". The second clause is right about the
CHECKPOINTS -- they carry per-channel statistics and no symbol axis. But the repo also ships
`state/fixtures/`, cut from the server panel `exports/live/wide_dl_live.npz` for the parity tests,
and those fixtures carry BOTH the panel's symbol axis AND its actual MEMBER110 masks. The union is
therefore determinable here, exactly, without replaying any rule.

★ THE ARGUMENT IS A SANDWICH, AND EACH SIDE COMES FROM A DIFFERENT PLACE.
    UPPER BOUND (definitional): MEMBER110 is a (T,140) mask over the panel's symbol axis, so every
      member is one of those 140 columns. union <= 140.
    LOWER BOUND (measured): the union of the real masks over the in-window rows we hold locally
      -- 8 anchors spanning 2021-01-31..2025-07-01 plus a contiguous 1080h slice ending
      2026-06-30T23Z -- is already all 140. union >= 140.
  The two bounds meet, so the union is EXACTLY the panel axis. No sampling gap is left to argue
  about: the lower bound does not need the blocks we cannot see, because it already saturates.

★ WHY IT SATURATES -- the mechanism, so the result is not mistaken for a coincidence.
  `build_wide_dl.py::MEMBER110` takes the top 110 by trailing dollar volume, but ONLY when at least
  110 symbols have a finite DVOL30; otherwise it takes every finite one. The panel had 62/70/75/83/
  97 listed coins at the 2021-2023 anchors, so through that whole stretch "top 110" never binds and
  every listed coin is a member. The union is the panel axis by construction, not by luck.

★ WHAT THIS DOES AND DOES NOT ESTABLISH -- the distinction the manifest block must carry.
  ESTABLISHES: over the training window, MEMBER110 covered all 140 columns of the panel the
    fixtures were cut from, and that panel's axis is byte-identical (same members, same order) to
    the live column set in config/funding_span_table.json.
  DOES NOT ESTABLISH: that the panel used by the TRAINING RUNS had this same 140-column axis. The
    fixtures come from `wide_dl_live.npz`, a live-extended rebuild. If a column had been added to
    the archive after training, it would appear here and not there -- and historical DVOL30 ranks
    would have shifted retroactively for everyone. Only the training host can close that, by
    reading the symbol axis of the panel the fold-4 checkpoints were trained on.
  ⇒ the residual risk is one-directional and it is the DANGEROUS direction: an over-wide union
    makes universe_guard LESS likely to fire. It is recorded, not smoothed over.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

LIVE_REPO = os.path.expanduser("~/dl_quant_live")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(LIVE_REPO, "signal"), os.path.join(LIVE_REPO, "live")]

HOUR_MS = 3_600_000
TS0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
TS_END = int(pd.Timestamp("2026-07-01", tz="UTC").value // 10**6)      # exclusive: window ends 06-30T23Z
TOPN = 110


def main():
    import live_panel as LP

    fx = np.load(os.path.join(LIVE_REPO, "state/fixtures/parity_fixture_v2.npz"), allow_pickle=True)
    pi = np.load(os.path.join(LIVE_REPO, "state/fixtures/panel_inputs.npz"), allow_pickle=True)
    syms = [str(s) for s in fx["symbols"]]
    assert [str(s) for s in pi["symbols"]] == syms, "the two fixtures disagree on the symbol axis"

    # ── the axis identity check. This is what licenses using a fixture cut from the SERVER panel
    # to answer a question about the LIVE column set: same symbols, same ORDER (order matters --
    # the encoder attends across columns).
    live_axis = LP.panel_symbols()
    axis_identical = live_axis == syms

    # ── lower bound: real masks, in-window rows only ──────────────────────────────────────────
    ats, M, kinds = fx["anchor_ts"], fx["masks"] > 0, [str(k) for k in fx["anchor_kind"]]
    inw = [i for i in range(len(ats)) if int(ats[i]) < TS_END]
    anchors = [{"kind": kinds[i], "ts": str(pd.to_datetime(int(ats[i]), unit="ms", utc=True))[:10],
                "n_members": int(M[i].sum())} for i in inw]
    lower = M[inw].any(0)

    pts, PM = pi["ts"].astype(np.int64), pi["MEMBER"]
    assert int(pts[-1]) < TS_END, "panel_inputs slice extends past the training window"
    slice_span = (str(pd.to_datetime(int(pts[0]), unit="ms", utc=True)),
                  str(pd.to_datetime(int(pts[-1]), unit="ms", utc=True)))
    lower = lower | PM.any(0)

    union = sorted([syms[j] for j in np.where(lower)[0]])

    # ── the rule replay, on the one block whose start row we actually hold ────────────────────
    # Independent of the fapi reconstruction: recompute build_wide_dl's MEMBER110 from the
    # fixture's OWN DVOL30 and require it to equal the fixture's OWN mask, bit for bit.
    DV = pi["DVOL30"].astype(np.float64)
    row = (pts - TS0) // HOUR_MS
    blk = (row // 24) // 30
    replay = []
    for b in np.unique(blk):
        idx = np.where(blk == b)[0]
        const = bool((PM[idx] == PM[idx[0]]).all())
        rec = {"block": int(b), "rows": [int(row[idx[0]]), int(row[idx[-1]])],
               "n_members": int(PM[idx[0]].sum()), "member_constant_within_block": const}
        hit = np.where(row == b * 30 * 24)[0]
        if len(hit):
            dv = DV[hit[0]]
            fin = np.isfinite(dv)
            m = np.zeros(len(syms), bool)
            if fin.sum() >= TOPN:
                m[np.argsort(-np.where(fin, dv, -np.inf))[:TOPN]] = True
            else:
                m = fin.copy()
            rec["rule_replay_exact"] = bool(np.array_equal(m, PM[hit[0]]))
            rec["n_finite_dvol30"] = int(fin.sum())
        replay.append(rec)

    res = {
        "n_axis": len(syms), "n_union": int(lower.sum()),
        "union": union,
        "never_member_in_window": sorted([syms[j] for j in np.where(~lower)[0]]),
        "axis_identical_to_live_column_set": axis_identical,
        "in_window_anchors": anchors,
        "panel_inputs_slice": slice_span,
        "rule_replay": replay,
        "bounds": {
            "upper": "union <= 140: MEMBER110 is a mask over the panel's 140-column axis",
            "lower": "union >= 140: measured from real masks over in-window rows",
            "conclusion": "exactly 140" if lower.all() else "bounds do NOT meet",
        },
    }
    p = os.path.join(OUT_DIR, "training_member_union_from_artifacts.json")
    with open(p, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "union"}, indent=1))
    print(f"-> {p}")
    return res


if __name__ == "__main__":
    main()
