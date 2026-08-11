#!/usr/bin/env python3
"""Emit the PROPOSED `training_member_union` block for checkpoints/MANIFEST.json. Does not write it.

> **created:** 2026-07-29 UTC | **Session:** ma-v2 universe_guard pin | **状态:** final

Writes exports/eda/PROPOSED_training_member_union.json for a human to paste. It deliberately does
NOT touch MANIFEST.json: `live/frozen_inputs.py` states the principle -- the pin file is written by
an explicit action, never by the code that reads it, because a guard that pins whatever it finds is
a guard that clears its own red.
"""
from __future__ import annotations

import json
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    art = json.load(open(os.path.join(OUT_DIR, "training_member_union_from_artifacts.json")))
    vp = os.path.join(OUT_DIR, "validate_member_reconstruction.json")
    val = json.load(open(vp)) if os.path.exists(vp) else None

    corrob = "NOT RUN"
    if val:
        corrob = (
            f"independently replayed from fapi daily klines (exports/eda/"
            f"reconstruct_training_member_union.py, 140/140 symbols served): the replayed union is "
            f"n={val['n_union_reconstructed']} and agrees with the artifact union "
            f"({val['union_agrees_with_artifacts']}). ★ BUT THE REPLAY IS NOT SET-EXACT PER BLOCK "
            f"-- {val['n_exact']}/{val['n_checks']} of the blocks where we hold a real server mask "
            f"matched exactly; the rest differ by exactly one symbol at the top-110 boundary "
            f"(daily bars cannot reproduce an hourly rolling mean's min_periods edge or its exact "
            f"ranking). Worse, and the reason a replay can only ever corroborate: fapi does not "
            f"serve ICPUSDT before ~2022-09, so the replay silently lacks ~1.5y of history the "
            f"training archive had and drops ICP from three 2021-2022 blocks with no error raised. "
            f"The union survives both defects only because the pre-2024 blocks take EVERY listed "
            f"coin rather than a ranked cut, which is exactly the property that makes the union "
            f"robust and the per-block replay not.")

    block = {
        "symbols": art["union"],
        "n": art["n_union"],
        "panel": "2021-01..2026-06",

        "method": (
            "DETERMINED LOCALLY from real training-panel slices, not read from a training-side "
            "export and not reconstructed by rule. Sandwich argument: (upper) MEMBER110 is a mask "
            "over the panel's 140-column symbol axis, so the union cannot exceed it; (lower) the "
            "union of the ACTUAL masks carried in state/fixtures/ over in-window rows -- 8 anchors "
            "from 2021-01-31 to 2025-07-01 (parity_fixture_v2.npz, cut from the server panel "
            "exports/live/wide_dl_live.npz) plus the contiguous 1080h slice ending 2026-06-30T23Z "
            "(panel_inputs.npz) -- is already all 140. The bounds meet, so the union is exactly the "
            "panel axis; no unobserved block is left to argue about. The axis was checked "
            "member-for-member AND order-for-order against the live column set "
            "(config/funding_span_table.json). Rule replayed for provenance: "
            "multi_asset/data/build_wide_dl.py::MEMBER110 -- top-110 by trailing-30d dollar volume "
            "on 30-DAY BLOCKS counted from panel row 0, with a 'fewer than 110 finite DVOL30 -> "
            "take every finite one' fallback; that fallback is why the union is the whole axis, "
            "since the panel held only 62/70/75/83/97 listed coins through 2021-2023 and the "
            "top-110 cut never bound. Replay verified bit-for-bit against the server's own mask at "
            "block 66. Generated 2026-07-29 UTC by "
            "multi_asset/exports/eda/training_member_union_from_artifacts.py. "
            "★ NOTE the rule is NOT signal/panel_build.py::derive_member -- that is the LIVE "
            "row-wise venue-filtered rule and answers a different question. Corroboration: "
            + corrob),

        "establishes": (
            "over the training window, MEMBER110 was true at some in-window row for every one of "
            "the 140 columns of the panel the parity fixtures were cut from -- i.e. the frozen "
            "models were trained over data from all 140 -- and that panel's symbol axis is "
            "identical, in content and order, to the column set the live stack scores today."),

        "does_not_establish": (
            "(1) that the panel THE TRAINING RUNS CONSUMED had this same 140-column axis. The "
            "fixtures come from wide_dl_live.npz, a live-extended REBUILD; a column added to the "
            "archive after training would appear here and not there, and because DVOL30 ranks are "
            "cross-sectional it would also have shifted history retroactively. The checkpoints "
            "cannot settle it -- they carry no symbol axis and no per-coin tensor (verified). Only "
            "the training host can, by reading the symbol axis of the panel fold_4 was trained on. "
            "The residual error is one-directional and points the DANGEROUS way: an over-wide union "
            "makes universe_guard LESS likely to fire, never more. "
            "(2) that each symbol was well REPRESENTED -- only that the mask was true somewhere, "
            "which for 2021-2023 means merely 'listed', not 'ranked into a top-110 cut'. "
            "(3) that pinning this makes the guard able to fire on the scenario its docstring "
            "describes. It cannot, while the column set stays frozen: live_panel.panel_symbols() "
            "is sorted(funding_span_table.keys()), members are derived within those columns, so "
            "members are a subset of this union BY CONSTRUCTION and the state is OK identically. "
            "Its live function is therefore a TRIPWIRE ON THE COLUMN SET -- it fires if "
            "funding_span_table.json gains a symbol without a retrain. That is a real guard, but "
            "it is not the one the docstring advertises, and the difference should not be "
            "discovered later by someone reading OK as evidence that rotation was checked."),
    }

    p = os.path.join(OUT_DIR, "PROPOSED_training_member_union.json")
    with open(p, "w") as f:
        json.dump({"training_member_union": block}, f, indent=1)
    print(json.dumps({"training_member_union": {k: (f"[{len(v)} symbols]" if k == "symbols" else v)
                                                for k, v in block.items()}}, indent=1))
    print(f"\n-> {p}")


if __name__ == "__main__":
    main()
