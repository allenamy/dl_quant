"""Reach gate on the nc tree: with one B fix enabled at a time, only the declared outputs may move.

Same contract as the pre-merge news2_global_gate.py, rebuilt on the integrator's replay core
(nc_hist_features, driven through news2_nc_adapter) and on arms of the nc derivation built with
NC_NEWS2_FAMILIES / NC_TREND_ROWS.

This covers PASS 1 (the King block) only. Pass 2 needs the as-of member history, and for an arm that
changes the member screen the history would have to be recomputed FROM THAT ARM (integrator, 2026-09-23:
using the default history for such an arm is an approximation that must be declared). Rather than
declare an approximation, the pass-2 comparison is left to a separate run for the arms whose members
provably do not move; the arms that do move members are reported with their member deltas, which is
the finding those arms are for.

Non-vacuity, same three rules as before:
  * an arm with no comparable anchor            -> UNAVAILABLE, never PASS
  * an arm that moved nothing                   -> NO-MEASUREMENT, unless declared expected-zero
  * a declared-zero arm still prints its counts, so "zero" is a measurement and not a silence

usage: python news2_nc_reach_gate.py <arms_root> <nc_devices> <cfg> <work> <out.json> <anchor> [...]
"""
import json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from news2_nc_adapter import Replay

# ★ The arms carry a D5+D6 FLOOR, and that is not a convenience. The nc A-part King block references
# `c7`, a name introduced by B's D5/D6 member-screen rewrite, so any NC_NEWS2_FAMILIES subset without
# D5 or D6 produces a tree that PARSES and then dies with NameError at the first anchor (measured:
# base / D4 / D7 / D8 / D9 / D14 all crash; receipts/ARM_VIABILITY.json). The baseline is therefore
# "D5,D6" and each test arm is "D5,D6,+X". Consequence, stated rather than hidden: D5 and D6 cannot be
# isolated from each other or from the floor by this mechanism, and this gate does not claim to.
ARMS = ["floor", "floorD4", "floorD7", "floorD8", "floorD9", "floorD14"]
BASE_ARM = "floor"
NOT_ISOLABLE = {"D5": "in the floor (A-part depends on it)", "D6": "in the floor (A-part depends on it)"}

# what each arm is ALLOWED to move in pass 1. King X78 covers the 78 served King columns.
# D4 / D7 / D8 / D9 patch files the King block does not read, so they must not move it at all.
KING_MAY_MOVE = set()          # relative to the D5+D6 floor, no remaining fix may move the King block
MEMBERS_MAY_MOVE = {"floorD14"}
EXPECTED_ZERO = {
    "floorD4": "dlw_features only; the King block does not read it",
    "floorD7": "f8 / combo_stage only; the King block does not read them",
    "floorD8": "f8 only; the King block does not read it",
    "floorD9": "combo_stage btcv only; the King block does not read it",
}


def diff(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    if a.shape != b.shape:
        return -1
    return int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())


def main():
    arms_root, nc_dev, cfg, work, out_path = sys.argv[1:6]
    anchors = [int(x) for x in sys.argv[6:]]
    assert anchors, "at least one anchor"
    t0 = time.time()

    res, timing, trees = {}, {}, {}
    for arm in ARMS:
        tree = os.path.join(arms_root, f"tree_{arm}")
        R = Replay(nc_dev, tree, cfg, os.path.join(work, arm))
        trees[arm] = R.tree_outputs()
        res[arm], timing[arm] = {}, {}
        for A in anchors:
            t1 = time.time()
            r = R.at(A)
            timing[arm][str(A)] = round(time.time() - t1, 2)
            res[arm][A] = r
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} {arm:5s} {A} "
                  f"members={len(r['m']) if r.get('m') is not None else None} {timing[arm][str(A)]}s", flush=True)

    cells = []
    for arm in ARMS:
        if arm == BASE_ARM:
            continue
        same, memdiff, kingmoved, other = [], {}, 0, {}
        for A in anchors:
            b, x = res[BASE_ARM][A], res[arm][A]
            if b.get("m") is None or x.get("m") is None:
                memdiff[str(A)] = None
                continue
            sd = int(len(set(b["m"].tolist()) ^ set(x["m"].tolist())))
            memdiff[str(A)] = sd
            if sd:
                continue
            same.append(A)
            kingmoved += max(diff(b["king_X78"], x["king_X78"]), 0)
            for key in ("qvm", "rev24", "fe_v", "fn_v", "iv_v"):
                if b.get(key) is not None and x.get(key) is not None:
                    other[key] = other.get(key, 0) + max(diff(b[key], x[key]), 0)
        out_of_reach = 0
        if kingmoved and arm not in KING_MAY_MOVE:
            out_of_reach += kingmoved
        moved_members = any(v for v in memdiff.values() if v)
        if moved_members and arm not in MEMBERS_MAY_MOVE:
            out_of_reach += sum(v for v in memdiff.values() if v)
        n_changed = kingmoved + sum(other.values())
        if not same:
            verdict = "UNAVAILABLE(no anchor with identical members)"
        elif out_of_reach:
            verdict = "FAIL(out of declared reach)"
        elif n_changed == 0 and arm not in EXPECTED_ZERO:
            verdict = "NO-MEASUREMENT"
        else:
            verdict = "PASS"
        cells.append({"arm": arm, "verdict": verdict, "n_same_member_anchors": len(same),
                      "member_symmetric_difference": memdiff, "king_X78_cells_changed": kingmoved,
                      "other_pass1_cells_changed": other, "cells_out_of_reach": out_of_reach,
                      "expected_zero": EXPECTED_ZERO.get(arm),
                      "king_may_move": arm in KING_MAY_MOVE, "members_may_move": arm in MEMBERS_MAY_MOVE})
        print(f"  {arm:5s} {verdict:38s} king={kingmoved} other={other} memdiff={list(memdiff.values())}", flush=True)

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "news2_nc_reach_gate.py",
           "self_sha256": __import__("hashlib").sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "scope": "pass 1 (King block) only; pass 2 needs per-arm member history, see module docstring",
           "floor": "D5,D6 (the nc A-part references c7 from B's member-screen rewrite; subsets without D5/D6 crash)",
           "not_isolable": NOT_ISOLABLE,
           "anchors": anchors, "arms": ARMS, "tree_outputs": trees,
           "cells": cells, "seconds_per_anchor": timing,
           "n_pass": sum(1 for c in cells if c["verdict"] == "PASS"), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_NC_REACH_GATE VERDICT={rec['VERDICT']} arms={len(cells)} pass={rec['n_pass']} "
          f"not_pass={rec['n_not_pass']} receipt_sha256="
          f"{__import__('hashlib').sha256(open(out_path,'rb').read()).hexdigest()}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
