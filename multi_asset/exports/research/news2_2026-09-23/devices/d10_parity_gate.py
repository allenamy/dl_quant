#!/usr/bin/env python3
"""d10_parity_gate.py -- line B: the train/live bitwise parity gate.

Criteria: lead's docs/DECISION_RULE_D10_stage2_2026-09-26.md (1814d4334, revision 1 57fa49eea) §2.
  * each column DECLARES the dtype it is judged in, and equality is bitwise IN THAT dtype
  * the positive control is ONE ULP OF THE TARGET ARRAY'S OWN dtype, and it must be detected or the gate is void
  * covered columns: fund_now, fund_ema, rn8, iv (plus any funding feature added in the October rebuild)
  * population = book members at the anchor; BOTH the raw cell count and the book-touching count are reported,
    and the book-touching one is the impact caliber
  * RED MEANS STOP: research side -> no retrain, no book-layer reading; live side -> no new producer publish.
    Tolerance may not be widened to get past it.

WHY dtype IS PER-COLUMN AND NOT A GLOBAL SETTING -- measured, not stylistic:
  the wide panel stores float32, so the archive's exact decimal -0.00039508 reads back as
  -0.00039507998735643923 and the float64 gap is 1.264356e-11. A 1e-12 "bitwise" test therefore FAILS ON
  CORRECT DATA (fresh hit exactly this and reported 0/12). Meanwhile NC's fn_v is float64 from the same decimal
  source and matches bitwise with no tolerance at all. So the same comparison is float32 on one side of the
  chain and float64 on the other, and a single global epsilon is wrong in both directions: too tight for the
  panel, needlessly loose for fn_v. Each column names its own dtype here and the receipt records it.

WHY THE ULP MUST BE IN THE TARGET'S dtype:
  a float64 `math.nextafter` stored into a float32 array rounds back to the original, so the control becomes a
  no-op and reports PASS while testing nothing. That happened to me on 2026-09-25 (CONTROL_FAIL caught it).
  np.nextafter on operands of the array's own dtype steps one real ULP; this device asserts the perturbation
  did not collapse before using it.

★ THE GATE IS BITWISE, AND THE MAGNITUDE BUCKETS DO NOT SOFTEN IT (lead's ruling, 2026-09-26).
  The three-way split (NaN-vs-finite / float-level / large) is a REQUIRED DESCRIPTIVE report and is NOT an
  exculpation. In the October rebuild the training side and the live side must call the SAME function, so even
  a 1e-12 accumulation difference MUST NOT appear -- if it does, that is evidence the two sides are NOT the
  same implementation, and the column is RED just the same. My own earlier wording ("89.6% of the differing
  EMA cells are within 1e-12, i.e. float accumulation noise") read as though that bucket were benign; it is
  not. It is the signature of two implementations where there should be one. Nothing in this device treats a
  small |diff| as passing: `eq` is bitwise equality in the declared dtype, and the buckets only say WHAT KIND
  of failure is present.

WHAT THIS DEVICE DOES NOT DO: it does not decide whether a difference is acceptable. It reports bitwise
equality per column, the counts, the buckets and the control outcome. The threshold is lead's and there is
none here.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import sys

import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def ulp_in_dtype(x, dt):
    """One ULP of `x` in dtype `dt`, asserted not to collapse. A float64 step stored into float32 rounds back
    to x and silently voids the control."""
    dt = np.dtype(dt)
    a = np.array(x, dtype=dt)
    up = np.nextafter(a, np.array(np.inf, dtype=dt), dtype=dt) if dt == np.float32 else np.nextafter(a, np.inf)
    up = np.array(up, dtype=dt)
    assert float(up) != float(a), (
        f"a 1-ULP perturbation collapsed in {dt}: the control would test nothing. value={x!r}")
    return up


def load_member_sets(features):
    """Per-anchor book member columns, from the construction the trainer uses (dlarch). `cand = mask & crypto`
    is a DIFFERENT quantity (tradable/candidate) and is deliberately not used."""
    F = np.load(features, allow_pickle=True)
    anchors = F["anchors"].astype(np.int64)
    syms = [str(s) for s in F["symbols"]]
    off = F["off"].astype(np.int64)
    m = F["m"].astype(np.int64)
    count = F["count"].astype(np.int64)
    assert len(off) == len(anchors) + 1, "off/anchors length mismatch"
    assert np.array_equal(np.diff(off), count), "member construction does not close (count vs off)"
    assert m.max() < len(syms), "member index beyond the symbol axis"
    return anchors, syms, [set(int(x) for x in m[off[i]:off[i + 1]]) for i in range(len(anchors))], int(count.sum())


DENSE, CSR = "dense[anchor,symbol]", "csr[member_entry]"


def detect_layout(arr, n_anchors, n_syms, n_member_entries):
    """Which of the two representations this array is in. Asserted, never guessed: a wrong guess would
    compare unrelated cells and still produce a tidy number."""
    if arr.ndim == 2 and arr.shape == (n_anchors, n_syms):
        return DENSE
    if arr.ndim == 1 and arr.shape[0] == n_member_entries:
        return CSR
    raise AssertionError(
        f"array shape {arr.shape} is neither dense ({n_anchors},{n_syms}) nor CSR ({n_member_entries},); "
        "the gate refuses to guess a layout")


def compare_column(av, bv, dt, name, off, m, anchors, syms, a_index, b_index,
                   a_layout, b_layout, control=False, examples=10, amax=None):
    """Compare one column over the MEMBER CELL SET, which is both lead's population and the only
    representation the two sides share. A CSR side is read at its entry k; a dense side at [anchor, column].
    """
    dt = np.dtype(dt)
    c = collections.Counter()
    ex = []
    diffs = []
    ctrl = None
    for i, t in enumerate(anchors):
        if amax is not None and int(t) > amax:
            c["anchor_above_window"] += 1
            continue
        ia = a_index.get(int(t)) if a_layout == DENSE else i
        ib = b_index.get(int(t)) if b_layout == DENSE else i
        if ia is None or ib is None:
            c["anchor_not_on_both_sides"] += 1
            continue
        for k in range(int(off[i]), int(off[i + 1])):
            j = int(m[k])
            s = syms[j]
            x = av[k] if a_layout == CSR else av[ia, a_index[("sym", s)]]
            y = bv[k] if b_layout == CSR else bv[ib, b_index[("sym", s)]]
            x = float(x)
            if control and ctrl is None and np.isfinite(x):
                x = float(ulp_in_dtype(x, dt))
                ctrl = {"column": name, "anchor": iso(t), "symbol": s, "dtype": str(dt),
                        "from": float(av[k] if a_layout == CSR else av[ia, a_index[("sym", s)]]),
                        "to": x, "expect": "must be reported as differing"}
            xa, yb = np.array(x, dt), np.array(float(y), dt)
            fa, fb = bool(np.isfinite(xa)), bool(np.isfinite(yb))
            both_nan = (not fa) and (not fb)
            eq = bool(xa == yb) or both_nan
            # every cell here IS a book member cell, by construction of the loop
            c["book_cells_compared"] += 1
            if eq:
                c["book_equal"] += 1
            else:
                c["book_DIFFER"] += 1
                # A single DIFFER count conflates three different things, and merging them hides the one that
                # matters: a NaN-vs-finite cell is a COVERAGE difference, a 1e-20 cell is float accumulation
                # noise, and a 1e-2 cell is a real value defect. They are counted separately here.
                if fa != fb:
                    c["DIFFER_nan_vs_finite"] += 1
                else:
                    d = abs(float(xa) - float(yb))
                    diffs.append(d)
                    c["DIFFER_both_finite"] += 1
                    for thr, key in ((1e-12, "le_1e-12"), (1e-9, "le_1e-9"), (1e-6, "le_1e-6"),
                                     (1e-3, "le_1e-3")):
                        if d <= thr:
                            c["mag_" + key] += 1
                            break
                    else:
                        c["mag_gt_1e-3"] += 1
                if len(ex) < examples:
                    ex.append({"anchor": iso(t), "symbol": s, "a": x, "b": float(y), "dtype": str(dt),
                               "a_finite": fa, "b_finite": fb,
                               "abs_diff": abs(x - float(y)) if fa and fb else None})
    c["cells_compared"] = c["book_cells_compared"]
    c["equal"] = c["book_equal"]
    c["DIFFER"] = c["book_DIFFER"]
    stats = None
    if diffs:
        d = np.sort(np.array(diffs))
        stats = {"n": int(d.size),
                 "median": float(d[d.size // 2]),
                 "p90": float(np.percentile(d, 90)), "p99": float(np.percentile(d, 99)),
                 "p99_9": float(np.percentile(d, 99.9)), "max": float(d[-1])}
    return c, ex, ctrl, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="side A npz (e.g. the training feature file)")
    ap.add_argument("--b", required=True, help="side B npz (e.g. the live/replay artifact)")
    ap.add_argument("--features", required=True, help="NEWS_FEATURES.npz -- supplies the member sets")
    ap.add_argument("--columns", required=True,
                    help="comma list of name:a_key:b_key:dtype, e.g. fund_now:fn_v:fund_now:float32")
    ap.add_argument("--out", required=True)
    ap.add_argument("--positive-control", action="store_true")
    ap.add_argument("--anchor-max-utc", default=None,
                    help="restrict to anchors <= this (YYYY-MM-DDTHH:MMZ). Used to strip a COVERAGE factor out "
                         "of the comparison: the two sides' event sets are identical below the splice boundary "
                         "2026-09-01T02:00Z, so restricting there removes coverage and leaves the rule.")
    a = ap.parse_args()

    anchors, syms, members, total_member_cells = load_member_sets(a.features)
    amax = None
    if a.anchor_max_utc:
        amax = int(datetime.datetime.strptime(a.anchor_max_utc, "%Y-%m-%dT%H:%MZ")
                   .replace(tzinfo=datetime.timezone.utc).timestamp())
    Fz = np.load(a.features, allow_pickle=True)
    off, mcol = Fz["off"].astype(np.int64), Fz["m"].astype(np.int64)
    n_member_entries = int(mcol.size)
    A = np.load(a.a, allow_pickle=True)
    B = np.load(a.b, allow_pickle=True)

    def axis(Z):
        t = None
        for k in ("anchors", "E_ts", "ts"):
            if k in Z.files:
                t = Z[k].astype(np.int64)
                break
        s = [str(x) for x in Z["symbols"]]
        ix = {int(v): i for i, v in enumerate(t)}
        ix.update({("sym", v): j for j, v in enumerate(s)})
        return t, s, ix

    ta, sa, ia = axis(A)
    tb, sb, ib = axis(B)

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "criteria": "docs/DECISION_RULE_D10_stage2_2026-09-26.md (1814d4334, rev 1 57fa49eea) §2",
           "mode": "POSITIVE_CONTROL" if a.positive_control else "GATE",
           "sides": {"a": {"path": a.a, "sha256": sha(a.a), "anchors": int(ta.size), "symbols": len(sa)},
                     "b": {"path": a.b, "sha256": sha(a.b), "anchors": int(tb.size), "symbols": len(sb)}},
           "member_source": {"path": a.features, "sha256": sha(a.features),
                             "construction": "members[i] = m[off[i]:off[i+1]]",
                             "explicitly_not": "cand = mask & crypto",
                             "total_member_cells_on_axis": total_member_cells},
           "anchor_window": {"max_utc": a.anchor_max_utc, "epoch": amax,
                             "why": ("the two sides' event sets are IDENTICAL below the spliced ledger's cut "
                                     "1788228000 = 2026-09-01T02:00Z (measured: 2,633,090 each, 0 events on "
                                     "either side only, 0 symbols differing), so restricting here removes the "
                                     "coverage factor and leaves the rule difference")},
           "axis": {"anchor_sets_equal": bool(set(ta.tolist()) == set(tb.tolist())),
                    "comparable_anchors": len(set(ta.tolist()) & set(tb.tolist())),
                    "symbol_sets_equal": bool(set(sa) == set(sb)),
                    "note": "only the intersection is comparable; equality is reported, never asserted"},
           "columns": {}}

    controls = []
    for spec in [x.strip() for x in a.columns.split(",") if x.strip()]:
        parts = spec.split(":")
        assert len(parts) == 4, ("column spec must be name:a_key:b_key:dtype", spec)
        name, ak, bk, dt = parts
        if ak not in A.files or bk not in B.files:
            rec["columns"][name] = {"status": "COLUMN_ABSENT", "a_key": ak, "b_key": bk,
                                    "a_has": ak in A.files, "b_has": bk in B.files,
                                    "note": "an absent column is not a pass; the gate cannot judge it"}
            continue
        arr_a, arr_b = np.asarray(A[ak], np.float64), np.asarray(B[bk], np.float64)
        la = detect_layout(arr_a, len(anchors), len(syms), n_member_entries)
        lb = detect_layout(arr_b, len(anchors), len(syms), n_member_entries)
        c, ex, ctrl, stats = compare_column(arr_a, arr_b, dt, name, off, mcol, anchors, syms, ia, ib,
                                            la, lb, control=a.positive_control, amax=amax)
        if ctrl:
            controls.append(ctrl)
        rec["columns"][name] = {
            "status": "COMPARED", "a_key": ak, "b_key": bk, "judged_in_dtype": dt,
            "a_layout": la, "b_layout": lb,
            "population": "the member cell set -- the only representation the two sides share",
            "cells_compared": int(c["cells_compared"]), "equal": int(c["equal"]),
            "DIFFER": int(c["DIFFER"]),
            "book_cells_compared": int(c["book_cells_compared"]),
            "book_equal": int(c["book_equal"]), "book_DIFFER": int(c["book_DIFFER"]),
            "closes": bool(c["equal"] + c["DIFFER"] == c["cells_compared"]),
            "DIFFER_nan_vs_finite": int(c["DIFFER_nan_vs_finite"]),
            "DIFFER_both_finite": int(c["DIFFER_both_finite"]),
            "magnitude_buckets": {k[4:]: int(v) for k, v in c.items() if k.startswith("mag_")},
            "abs_diff_stats_both_finite": stats,
            "why_split": ("one DIFFER count conflates a coverage difference (NaN vs finite), a float-level "
                          "difference (~1e-20) and a large value difference (~1e-2); merging them hides the "
                          "last inside the first two. DESCRIPTIVE ONLY -- per lead 2026-09-26 the gate stays "
                          "bitwise: with both sides calling the same function even a 1e-12 difference must "
                          "not occur, so a float-level bucket is evidence of two implementations, not a pass"),
            "examples": ex,
            "impact_caliber": "book_DIFFER -- the raw DIFFER count is reported but is not the impact number"}
        assert rec["columns"][name]["closes"], (name, "column classification does not close")

    judged = [v for v in rec["columns"].values() if v.get("status") == "COMPARED"]
    absent = [k for k, v in rec["columns"].items() if v.get("status") == "COLUMN_ABSENT"]
    rec["totals"] = {"columns_compared": len(judged), "columns_absent": absent,
                     "any_DIFFER": bool(any(v["DIFFER"] for v in judged)),
                     "any_book_DIFFER": bool(any(v["book_DIFFER"] for v in judged)),
                     "total_DIFFER": int(sum(v["DIFFER"] for v in judged)),
                     "total_book_DIFFER": int(sum(v["book_DIFFER"] for v in judged))}

    if a.positive_control:
        seen = rec["totals"]["total_DIFFER"] >= len(controls) and len(controls) > 0
        rec["positive_control"] = {"cells": controls, "n": len(controls),
                                   "verdict": "CONTROL_PASS" if seen else "CONTROL_FAIL",
                                   "meaning": ("one ULP of each column's OWN dtype was injected and must be "
                                               "reported as differing; every red count in this run is mine")}
        rec["verdict"] = "POSITIVE_CONTROL_RUN_NOT_A_GATE"
    elif absent:
        rec["verdict"] = "GATE_CANNOT_JUDGE_COLUMN_ABSENT"
    elif rec["totals"]["any_DIFFER"]:
        rec["verdict"] = "PARITY_RED"
    else:
        rec["verdict"] = "PARITY_GREEN"

    print(f"parity gate   mode={rec['mode']}")
    print(f"  A {a.a}\n    sha {rec['sides']['a']['sha256'][:16]}  anchors={ta.size} symbols={len(sa)}")
    print(f"  B {a.b}\n    sha {rec['sides']['b']['sha256'][:16]}  anchors={tb.size} symbols={len(sb)}")
    print(f"  comparable anchors {rec['axis']['comparable_anchors']}  "
          f"anchor sets equal {rec['axis']['anchor_sets_equal']}  symbols equal {rec['axis']['symbol_sets_equal']}")
    for k, v in rec["columns"].items():
        if v.get("status") != "COMPARED":
            print(f"    {k:12s} {v['status']}  a_has={v['a_has']} b_has={v['b_has']}")
            continue
        st = v.get("abs_diff_stats_both_finite") or {}
        print(f"    {k:12s} dtype={v['judged_in_dtype']:8s} a={v['a_layout'][:5]} b={v['b_layout'][:5]} "
              f"cells={v['book_cells_compared']:>9d} DIFFER={v['book_DIFFER']:>7d} "
              f"(nan_vs_finite={v['DIFFER_nan_vs_finite']} both_finite={v['DIFFER_both_finite']})")
        if st:
            print(f"                 |diff| median={st['median']:.3e} p99={st['p99']:.3e} max={st['max']:.3e}"
                  f"   buckets={v['magnitude_buckets']}")
        for e in v["examples"][:2]:
            print(f"        {e}")
    if a.positive_control:
        print(f"  CONTROL {rec['positive_control']['verdict']} (n={rec['positive_control']['n']})")
    print(f"  VERDICT {rec['verdict']}")
    if rec["verdict"] == "PARITY_RED":
        print("  RED MEANS STOP (lead §2): no retrain, no book-layer reading, no new producer publish. "
              "Widening the tolerance is not a remedy.")
    print(f"  receipt -> {a.out}  sha256={DW.write_json(a.out, rec, indent=1, allow_nan=True)}")
    return 0 if rec["verdict"] in ("PARITY_GREEN", "POSITIVE_CONTROL_RUN_NOT_A_GATE") else 2


if __name__ == "__main__":
    sys.exit(main())
