#!/usr/bin/env python3
"""legal_res_breakdown.py -- LEGAL_res's mandatory reporting, written BEFORE the arm's dbar.

Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
(sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03). Lead's words:

  "LEGAL_res 的必报(写在读数之前): 94,054 个不一致格按原因拆 -- NC 侧 tradable_mask=False
   (死合约/不可交易) / crypto=False / 资金费 legal 本身不同, 各多少格、多少锚、逐年; 以及 NEW 在
   「NC 判为不可交易」的格上实际持有的权重与 P&L 贡献"

WHAT THE TWO SIDES ACTUALLY ARE (read off continuous_combo.py:69 and news2_combo.py):
  NC   book_legal = align_universe(a, syms, universe) & tradable_mask & crypto
  NEW  book_legal = align_universe(a, syms, universe) & funding_state['legal']

WHAT THE "tradable_mask=False" BUCKET MEANS, precisely: the mask npz stores only the CONJUNCTION
`MEMBER_LIVENESS AND MASK_IN 9793722e`, where MEMBER_LIVENESS = "at least one REAL bar (not
hole-filled, log_qv finite) in the 86400 s window ending at the anchor". So a False cell means
"no real bar in the trailing 24h, OR excluded upstream by mask_in" -- the finer split is NOT
available from this artifact and is not claimed here.

ON P&L: the engine emits per-PATH NAV only, with no per-cell decomposition, so an exact per-cell
P&L attribution does not exist to be read. This device therefore reports the EXACT held weight
(NEW's own archived combo weights on those cells, and their share of NEW's gross) and does NOT
manufacture a price-return proxy and call it P&L. The book-layer answer in dbar units comes from
the separate leave-one-out arm `all_new_nclegal`, whose reading rule is lead's to write.
"""
import argparse, collections, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def yr_of(ts):
    return np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in ts])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", required=True)
    ap.add_argument("--features", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--crypto-axis", required=True)
    ap.add_argument("--new-funding", required=True)
    ap.add_argument("--new-combo-dir", required=True, help="NEW's archived combo_s42 (weights live here)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.devices)
    from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": ("docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f "
                      "(sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03), revision 1"),
           "criterion_author": "team-lead (not news2)",
           "status": "MANDATORY_REPORTING_FOR_LEGAL_RES_WRITTEN_BEFORE_THE_ARM_DBAR",
           "definitions": {
               "NC_book_legal": "align_universe & tradable_mask & crypto",
               "NEW_book_legal": "align_universe & funding_state['legal']",
               "tradable_mask_bucket_meaning": (
                   "the mask npz stores only the CONJUNCTION 'MEMBER_LIVENESS AND MASK_IN 9793722e'; "
                   "MEMBER_LIVENESS = at least one REAL bar (not hole-filled, log_qv finite) in the "
                   "86400s window ending at the anchor. A False cell = no real bar in the trailing 24h "
                   "OR excluded upstream by mask_in. The finer split is NOT available from this "
                   "artifact and is not claimed."),
               "pnl_note": (
                   "the engine emits per-PATH NAV only, with no per-cell decomposition, so an exact "
                   "per-cell P&L attribution does not exist to be read. Exact held WEIGHT is reported "
                   "instead; no price-return proxy is presented as P&L. The dbar-unit answer comes from "
                   "the leave-one-out arm all_new_nclegal.")},
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("features", a.features), ("mask", a.mask), ("crypto_axis", a.crypto_axis),
                       ("new_funding", a.new_funding))}}

    F = np.load(a.features, allow_pickle=False)
    anchors = F["anchors"].astype(np.int64); syms = F["symbols"]
    mk = np.load(a.mask, allow_pickle=True)
    assert np.array_equal(mk["ts"].astype(np.int64), anchors), "mask anchor axis"
    assert np.array_equal(mk["symbols"], syms), "mask symbol axis"
    crypto = np.load(a.crypto_axis, allow_pickle=False)["crypto"]
    fu = np.load(a.new_funding, allow_pickle=False)
    assert np.array_equal(fu["symbols"], syms), "funding symbol axis"

    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, "universe content identity"
    universe = np.load(UNIVERSE_PATH)
    use = (anchors >= 1672531200) & (anchors <= universe["ts"][-1])
    au = anchors[use]
    uni = align_universe(au, syms, universe)

    tmask = np.asarray(mk["mask"], bool)[use]
    cry = np.broadcast_to(np.asarray(crypto, bool)[None, :], tmask.shape)
    pos = {int(t): i for i, t in enumerate(fu["E_ts"].astype(np.int64))}
    rows = np.array([pos.get(int(t), -1) for t in au])
    assert (rows >= 0).all(), "NEW funding lacks anchors inside the use window"
    flegal = np.asarray(fu["legal"], bool)[rows]

    nc_legal = uni & tmask & cry
    new_legal = uni & flegal
    dis = nc_legal != new_legal
    yr = yr_of(au)

    rec["consumed_layer"] = {
        "note": "this is the layer combo actually consumes (after align_universe), not the pre-universe compare",
        "nc_true_cells": int(nc_legal.sum()), "new_true_cells": int(new_legal.sum()),
        "disagreeing_cells": int(dis.sum()),
        "anchors_with_any_disagreement": int(dis.any(1).sum()),
        "nc_false_new_true": int((~nc_legal & new_legal).sum()),
        "nc_true_new_false": int((nc_legal & ~new_legal).sum())}
    # the pre-universe compare, because lead's 94,054 was quoted at that layer
    pre = (tmask & cry) != flegal
    rec["pre_universe_layer"] = {
        "note": "mask&crypto vs funding_state[legal], BEFORE align_universe -- the layer lead's 94,054 came from",
        "disagreeing_cells": int(pre.sum()), "anchors_with_any_disagreement": int(pre.any(1).sum())}

    # ---- lead's three-way split, on NC-illegal / NEW-legal cells (the direction that adds exposure)
    add = ~nc_legal & new_legal            # NEW trades where NC would not
    drop = nc_legal & ~new_legal           # NC trades where NEW would not
    buckets = {}
    # a cell can fail NC for more than one reason; report the joint census, never a forced split
    for name, cond in (("tradable_mask_False_only", (~tmask) & cry & uni),
                       ("crypto_False_only", tmask & (~cry) & uni),
                       ("both_mask_and_crypto_False", (~tmask) & (~cry) & uni),
                       ("outside_book_universe", ~uni)):
        m = add & cond
        buckets[name] = {"cells": int(m.sum()),
                         "anchors": int(m.any(1).sum()),
                         "per_year": {str(int(y)): int(m[yr == y].sum()) for y in np.unique(yr)}}
    # the remaining direction-add cells where NC's mask and crypto are both True: funding legal itself
    rest = add & tmask & cry & uni
    buckets["funding_legal_itself"] = {"cells": int(rest.sum()), "anchors": int(rest.any(1).sum()),
                                       "per_year": {str(int(y)): int(rest[yr == y].sum()) for y in np.unique(yr)},
                                       "note": "NC mask AND crypto both True and in-universe, so only funding_state[legal] explains it"}
    tot = sum(v["cells"] for v in buckets.values())
    rec["split_of_cells_NEW_trades_but_NC_would_not"] = {
        "total_cells": int(add.sum()), "buckets": buckets,
        "closure_check": {"sum_of_buckets": int(tot), "equals_total": bool(tot == int(add.sum()))}}
    assert tot == int(add.sum()), ("buckets must partition the add set", tot, int(add.sum()))
    rec["cells_NC_trades_but_NEW_would_not"] = {
        "total_cells": int(drop.sum()), "anchors": int(drop.any(1).sum()),
        "per_year": {str(int(y)): int(drop[yr == y].sum()) for y in np.unique(yr)}}

    # ---- NEW's ACTUAL held weight on the cells NC calls untradable -------------------------------
    held = {}
    for pol in ("literal", "scaled_diagnostic"):
        p = os.path.join(a.new_combo_dir, pol + ".npz")
        Z = np.load(p, allow_pickle=False)
        assert np.array_equal(Z["E_ts"].astype(np.int64), au), "NEW combo anchor axis"
        assert np.array_equal(Z["symbols"], syms), "NEW combo symbol axis"
        W = np.abs(np.asarray(Z["weights"], np.float64))
        gross = W.sum()
        d = {"path": p, "sha256": sha(p), "new_total_gross_abs_weight": float(gross)}
        for name, m in (("on_nc_untradable_mask_False", add & (~tmask) & uni),
                        ("on_nc_noncrypto", add & (~cry) & uni),
                        ("on_any_cell_nc_calls_illegal", add)):
            w = W * m
            d[name] = {"cells_with_nonzero_weight": int((w > 0).sum()),
                       "sum_abs_weight": float(w.sum()),
                       "share_of_new_gross_pct": round(100.0 * w.sum() / gross, 4) if gross else None,
                       "anchors_with_any": int((w > 0).any(1).sum()),
                       "per_year_share_pct": {str(int(y)): (round(100.0 * w[yr == y].sum() / W[yr == y].sum(), 4)
                                                            if W[yr == y].sum() else None)
                                              for y in np.unique(yr)}}
        held[pol] = d
    rec["new_held_weight_on_cells_nc_calls_illegal"] = held
    rec["reading_note"] = (
        "share_of_new_gross_pct is the exact fraction of NEW's own book, by absolute weight, placed on "
        "cells NC would not trade. It bounds how much of the gap COULD come from there; it does not by "
        "itself say how much DOES -- that is the leave-one-out arm all_new_nclegal, in dbar units.")
    rec["limits"] = ["weights are NEW's archived combo weights, not executed positions",
                     "no per-cell P&L exists in the engine output; none is fabricated here",
                     "arms are NOT additive; every ladder arm is a pipeline-unproducible combination"]
    rec["verdict"] = "MEASURED"
    json.dump(rec, open(a.out, "w"), indent=2)

    c = rec["consumed_layer"]
    print("LEGAL_RES BREAKDOWN (consumed layer, after align_universe)")
    print(f"  NC legal cells {c['nc_true_cells']}   NEW legal cells {c['new_true_cells']}"
          f"   disagree {c['disagreeing_cells']} over {c['anchors_with_any_disagreement']} anchors")
    print(f"  pre-universe layer (lead's 94,054 came from here): {rec['pre_universe_layer']['disagreeing_cells']}"
          f" cells / {rec['pre_universe_layer']['anchors_with_any_disagreement']} anchors")
    print(f"  NEW trades where NC would not: {c['nc_false_new_true']} cells;"
          f"  NC trades where NEW would not: {c['nc_true_new_false']} cells")
    print("  split of the cells NEW trades but NC would not:")
    for k, v in buckets.items():
        print(f"    {k:32s} cells={v['cells']:8d} anchors={v['anchors']:5d}  per_year={v['per_year']}")
    print(f"    closure: sum {tot} == total {int(add.sum())}")
    for pol, d in held.items():
        x = d["on_any_cell_nc_calls_illegal"]; y = d["on_nc_untradable_mask_False"]
        print(f"  [{pol}] NEW weight on NC-illegal cells: {x['share_of_new_gross_pct']}% of its gross "
              f"({x['cells_with_nonzero_weight']} cells, {x['anchors_with_any']} anchors); "
              f"of which mask=False: {y['share_of_new_gross_pct']}%")
        print(f"           per-year share on NC-illegal: {x['per_year_share_pct']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
