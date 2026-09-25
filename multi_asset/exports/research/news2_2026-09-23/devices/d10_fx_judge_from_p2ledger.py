#!/usr/bin/env python3
"""d10_fx_judge_from_p2ledger.py -- judge the FX mismatch cells using P2 ledger_full.npz as the truth source.

lead's ruling 2026-09-25: the P2 line is closed, 2026-05/06/07 are not being pulled, and the FX cells that
the archive cannot reach are to be judged directly from P2 ledger_full.npz by the production as-of rule
instead of downloading more months. This device is that, and it is handed to fresh.

WHY P2 ledger_full CAN BE THE TRUTH SOURCE -- measured today, not asserted (D10_P2_LEDGER_VS_ARCHIVE_full):
  * 6,294 archive settlements inside +/-24h interval-switch windows over 2026-01..04 + 08: all present
  * 463,715 rates compared against the CHECKSUM-verified archive: ALL bitwise equal
  * src == 4 (the API and the monthly zip disagreeing on a shared second) is 0 across all 2,633,090 rows
  * 2026-08 is an INDEPENDENT check, not a circular one: the ledger holds that month 100% src == 1 (API only,
    the zip did not exist when the ledger was built), and it matches the later-published zip bitwise
The weak direction is stated rather than hidden: 2026-01..04 are largely circular, because the ledger's zip
side is the same monthly archive. 2026-08 is what carries the independence.

THE AS-OF RULE, bound to the lines that define it:
  nc_contract.py:84-98 funding_asof -- the last row with ft <= anchor; NaN unless anchor - ft <= FRESH_S
  (43200 s); the rate is that row's rate. The FX judgement compares RATES, so no interval is needed: `iv`
  never enters this comparison. Spacing and zip_iv are reported as context only, and zip_iv is NaN exactly
  when the row is API-only (p2_prep_inputs.py L7), which is a provenance fact and not a missing interval.

COMPARISON CALIBER: at float32, the panel's storage dtype -- NOT a float64 tolerance. The archive publishes an
exact decimal (e.g. -0.00039508) while the panel stores float32, whose widened value is
-0.00039507998735643923; the float64 gap is 1.26e-11, so any 1e-12 "bitwise" test fails on correct data. The
caliber is bound to the panel file, which is the project rule, rather than to a tolerance chosen to pass.

SELF-VALIDATION, which is the point. --crosscheck-csv takes the cells the ARCHIVE already judged
(D10_FXFIELD_CELLS_fullprecision.csv, 2,021 rows) and re-judges them from P2 ledger_full. If the two truth
sources disagree on any of them, P2-as-truth is NOT established and the extension to unjudged cells is
refused. A truth source is earned on the overlap before it is used beyond it.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import sys

import numpy as np

FRESH_S = 43200          # nc_contract.py:21
EXPECT_MISMATCH = 5613   # fresh's count, asserted before any judging (d10_fxfield_adjudicate.py:57)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


class P2Ledger:
    """The production as-of, read from P2 ledger_full.npz (CSR by symbol)."""

    def __init__(self, path, pinned_sha=None):
        self.path = path
        self.sha256 = sha(path)
        if pinned_sha:
            assert self.sha256 == pinned_sha, ("ledger is not the pinned artifact", self.sha256, pinned_sha)
        Z = np.load(path, allow_pickle=True)
        self.off = Z["off"].astype(np.int64)
        self.ft = Z["ft"].astype(np.int64)
        self.rate = Z["rate"].astype(np.float64)
        self.src = Z["src"].astype(np.int8)
        self.zip_iv = Z["zip_iv"].astype(np.float64)
        self.syms = [str(s) for s in Z["symbols"]]
        self.idx = {s: j for j, s in enumerate(self.syms)}

    def span(self, s):
        j = self.idx[s]
        a, b = int(self.off[j]), int(self.off[j + 1])
        return (int(self.ft[a]), int(self.ft[b - 1])) if b > a else None

    def asof(self, s, anchor):
        """(ft, rate, src, zip_iv, spacing_h) of the last event at or before `anchor`, or None."""
        j = self.idx.get(s)
        if j is None:
            return None
        a, b = int(self.off[j]), int(self.off[j + 1])
        if b <= a:
            return None
        seg = self.ft[a:b]
        k = int(np.searchsorted(seg, anchor, side="right")) - 1
        if k < 0:
            return None
        g = a + k
        spacing = (int(seg[k]) - int(seg[k - 1])) / 3600.0 if k >= 1 else None
        return (int(self.ft[g]), float(self.rate[g]), int(self.src[g]), float(self.zip_iv[g]), spacing)


def judge(panel_v, ledger_v, truth):
    """The same four verdicts the archive-based adjudication uses, at float32."""
    if truth is None or not np.isfinite(truth):
        return "TRUTH_IS_STALE_both_sides_should_be_nan"
    t = np.float32(truth)
    pm = np.float32(panel_v) == t
    lm = np.float32(ledger_v) == t
    if pm and not lm:
        return "PANEL_RIGHT"
    if lm and not pm:
        return "LEDGER_RIGHT"
    if pm and lm:
        return "IMPOSSIBLE_both_match_but_they_differ"
    return "NEITHER"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--ledger-sha", default=None)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--replay", required=True)
    ap.add_argument("--crosscheck-csv", default=None,
                    help="the archive-judged cells; P2-as-truth must reproduce them or the run refuses")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells-csv", default=None)
    ap.add_argument("--positive-control", action="store_true")
    a = ap.parse_args()

    L = P2Ledger(a.ledger, a.ledger_sha)
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "argv": sys.argv[1:],
           "truth_source": {"path": a.ledger, "sha256": L.sha256, "symbols": len(L.syms),
                            "rows": int(L.ft.size), "span": [iso(L.ft.min()), iso(L.ft.max())],
                            "earned_by": "D10_P2_LEDGER_VS_ARCHIVE_full: 6,294/6,294 switch-window "
                                         "settlements present, 463,715 rates bitwise equal, src==4 is 0 "
                                         "across 2,633,090 rows, and 2026-08 is an independent match "
                                         "(ledger 100% API-only there)",
                            "weak_direction": "2026-01..04 are largely circular (the ledger's zip side is "
                                              "the same monthly archive); 2026-08 carries the independence"},
           "caliber": "float32, the panel's storage dtype -- not a float64 tolerance (a 1e-12 test against "
                      "the archive's exact decimal fails on correct data by ~1.26e-11)",
           "asof_rule": "nc_contract.py:84-98: last ft <= anchor, NaN unless anchor-ft <= 43200; rates only, "
                        "so no interval enters the comparison"}

    P = np.load(a.panel, allow_pickle=True)
    R = np.load(a.replay, allow_pickle=True)

    def pick(Z, names):
        for n in names:
            if n in Z.files:
                return Z[n]
        raise KeyError((names, list(Z.files)[:20]))

    ti = pick(P, ["anchors", "ts", "E_ts"]).astype(np.int64)
    si = [str(s) for s in pick(P, ["symbols"])]
    FN = np.asarray(pick(P, ["f_fund_now", "fund_now", "FN"]), np.float64)
    ra = pick(R, ["anchors"]).astype(np.int64)
    rs = [str(s) for s in pick(R, ["symbols"])]
    LRr = np.asarray(pick(R, ["last_rate"]), np.float64)

    # Align by SET INTERSECTION and name what falls outside -- never by position, and never by asserting the
    # axes are equal. They are NOT: the panel ends 2026-08-31 while the replay axis runs into September
    # (fresh measured the same thing on the legs axis: 294 anchors present there and absent from the panel).
    # An equality assertion here would have been a brittle check welded to a population expectation; the
    # comparable population is the intersection, and the remainder is reported rather than dropped silently.
    rmap = {int(t): i for i, t in enumerate(ra)}
    rcol = {s: j for j, s in enumerate(rs)}
    pa_set, ra_set = {int(t) for t in ti}, {int(t) for t in ra}
    only_panel = sorted(pa_set - ra_set)
    only_replay = sorted(ra_set - pa_set)
    rec["alignment"] = {
        "panel_anchors": int(ti.size), "replay_anchors": int(ra.size),
        "anchor_sets_equal": bool(ra_set == pa_set),
        "comparable_anchors": len(pa_set & ra_set),
        "anchors_only_in_panel": len(only_panel),
        "anchors_only_in_replay": len(only_replay),
        "anchors_only_in_panel_range": [iso(only_panel[0]), iso(only_panel[-1])] if only_panel else None,
        "anchors_only_in_replay_range": [iso(only_replay[0]), iso(only_replay[-1])] if only_replay else None,
        "panel_symbols": len(si), "replay_symbols": len(rs),
        "symbol_sets_equal": bool(set(si) == set(rs)),
        "symbols_only_in_panel": len(set(si) - set(rs)),
        "symbols_only_in_replay": len(set(rs) - set(si)),
        "note": ("only the intersection is judgeable; a cell on an anchor the other side does not carry is "
                 "not a mismatch and not an agreement, it is outside the comparable population")}

    # THE MISMATCH POPULATION MUST BE THE FX POPULATION, not one of my own making. The canonical definition
    # is d10_fxfield_adjudicate.py:120  `bad = both & (FN != LR.astype(np.float32))`, where `both` requires
    # BOTH sides finite. My first version also counted cells where one side was finite and the other NaN,
    # which pulled in ~448,000 extra cells and would have reported 453,428 "FX cells" -- a different
    # population wearing the same name. The 5,613 assertion below is what makes the population checkable,
    # so it is copied from the canonical device rather than re-derived.
    bad = np.zeros((ti.size, len(si)), bool)
    both = np.zeros((ti.size, len(si)), bool)
    for i, t in enumerate(ti):
        ri = rmap.get(int(t))
        if ri is None:
            continue
        for j, s in enumerate(si):
            rj = rcol.get(s)
            if rj is None:
                continue
            p_, l_ = FN[i, j], LRr[ri, rj]
            if np.isfinite(p_) and np.isfinite(l_):
                both[i, j] = True
                if np.float32(p_) != np.float32(l_):
                    bad[i, j] = True
    rec["reproduction"] = {"common_finite_cells": int(both.sum()), "mismatched_cells": int(bad.sum()),
                           "expected_fresh_count": EXPECT_MISMATCH,
                           "matches_fresh": bool(int(bad.sum()) == EXPECT_MISMATCH),
                           "why": "the same definition as d10_fxfield_adjudicate.py:120; reproducing 5,613 "
                                  "first is what proves this is the FX population and not another one"}
    assert int(bad.sum()) == EXPECT_MISMATCH, (
        "must reproduce fresh's 5,613 before judging anything", int(bad.sum()), EXPECT_MISMATCH)
    rec["mismatched_cells"] = int(bad.sum())

    counts = collections.Counter()
    rows_out = []
    for i in np.flatnonzero(bad.any(1)):
        anchor = int(ti[i])
        ri = rmap[anchor]
        for j in np.flatnonzero(bad[i]):
            s = si[j]
            if s not in L.idx:
                counts["EXCLUDED_symbol_not_on_ledger_axis"] += 1
                continue
            sp = L.span(s)
            if sp is None or anchor < sp[0]:
                counts["EXCLUDED_anchor_before_symbol_first_ledger_row"] += 1
                continue
            if anchor > int(L.ft.max()):
                counts["EXCLUDED_anchor_after_ledger_end"] += 1
                continue
            r = L.asof(s, anchor)
            if r is None:
                counts["EXCLUDED_no_asof_in_ledger"] += 1
                continue
            ft, rate, src, ziv, spacing = r
            truth = rate if (anchor - ft) <= FRESH_S else float("nan")
            pv, lv = float(FN[i, j]), float(LRr[ri, rcol[s]])
            if a.positive_control and not counts["_ctrl"]:
                pv = float(np.nextafter(np.float32(pv), np.float32(np.inf)))
                counts["_ctrl"] += 1
                rec["positive_control_cell"] = {"symbol": s, "anchor": iso(anchor),
                                                "perturbed": "panel value by one float32 ULP",
                                                "expect": "this cell must stop being PANEL_RIGHT"}
            v = judge(pv, lv, truth)
            counts[v] += 1
            rows_out.append((s, iso(anchor), v, truth, pv, lv, iso(ft), anchor - ft, src, ziv, spacing))

    counts.pop("_ctrl", None)
    rec["verdict_counts"] = dict(counts)
    judged = sum(v for k, v in counts.items() if not k.startswith("EXCLUDED"))
    rec["cells_judged"] = judged
    rec["cells_excluded"] = int(sum(v for k, v in counts.items() if k.startswith("EXCLUDED")))
    rec["closure"] = bool(judged + rec["cells_excluded"] == rec["mismatched_cells"])
    assert rec["closure"], ("verdict classification does not close", rec["mismatched_cells"], dict(counts))

    # ---- the overlap test: P2-as-truth must reproduce what the archive already judged ----
    if a.crosscheck_csv:
        arch = {}
        with open(a.crosscheck_csv) as fh:
            for row in csv.DictReader(l for l in fh if not l.startswith("#")):
                arch[(row["symbol"], row["anchor_utc"])] = row
        got = {(r[0], r[1]): r for r in rows_out}
        both = sorted(set(arch) & set(got))
        agree = [k for k in both if arch[k]["verdict"] == got[k][2]]
        disagree = [{"symbol": k[0], "anchor": k[1], "archive_verdict": arch[k]["verdict"],
                     "p2_verdict": got[k][2], "archive_truth": arch[k]["archive_truth_rate"],
                     "p2_truth": got[k][3]} for k in both if arch[k]["verdict"] != got[k][2]]
        rec["crosscheck_vs_archive"] = {
            "archive_judged_cells": len(arch), "overlap": len(both),
            "verdict_agree": len(agree), "verdict_disagree": len(disagree),
            "disagreements": disagree[:20],
            "truth_bitwise_equal": sum(1 for k in both
                                       if np.float32(float(arch[k]["archive_truth_rate"]))
                                       == np.float32(got[k][3])),
            "meaning": ("P2-as-truth is earned on the overlap before being used beyond it. Zero "
                        "disagreements is the condition; anything else refuses the extension.")}
        if disagree and not a.positive_control:
            rec["verdict"] = "P2_AS_TRUTH_NOT_ESTABLISHED"
            json.dump(rec, open(a.out, "w"), indent=1)
            print(json.dumps(rec["crosscheck_vs_archive"], indent=1))
            sys.stderr.write("REFUSING to extend: P2 and the archive disagree on the overlap.\n")
            return 2

    if a.cells_csv:
        with open(a.cells_csv, "w") as fh:
            fh.write("# FX cells judged from P2 ledger_full.npz, FULL PRECISION (repr, round-trips)\n")
            fh.write("# src: 1=API only, 2=zip only, 3=both equal, 4=both unequal (p2_prep_inputs.py L7)\n")
            fh.write("# zip_iv is NaN exactly when src==1 -- a provenance fact, not a missing interval\n")
            fh.write("symbol,anchor_utc,verdict,p2_truth_rate,panel_value,ledger_value,"
                     "asof_event_utc,asof_age_s,src,zip_iv,spacing_h\n")
            for t in rows_out:
                fh.write(",".join([t[0], t[1], t[2], repr(t[3]), repr(t[4]), repr(t[5]), t[6],
                                   str(t[7]), str(t[8]), repr(t[9]), repr(t[10])]) + "\n")
        rec["cells_csv"] = {"path": a.cells_csv, "rows": len(rows_out), "sha256": sha(a.cells_csv)}

    if a.positive_control:
        rec["verdict"] = "POSITIVE_CONTROL_RUN_NOT_AN_AUDIT"
    elif "verdict" not in rec:
        rec["verdict"] = ("FX_JUDGED_FROM_P2_LEDGER" if judged else "NO_JUDGEABLE_CELLS")

    print(f"FX judged from P2 ledger_full   truth={a.ledger}")
    print(f"  ledger sha {L.sha256[:16]}  rows={L.ft.size}  span {iso(L.ft.min())}..{iso(L.ft.max())}")
    print(f"  mismatched cells {rec['mismatched_cells']}  judged {judged}  excluded {rec['cells_excluded']}"
          f"  closure {rec['closure']}")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"     {k:52s} {v}")
    if "crosscheck_vs_archive" in rec:
        c = rec["crosscheck_vs_archive"]
        print(f"  CROSSCHECK vs archive: overlap {c['overlap']}  agree {c['verdict_agree']}  "
              f"disagree {c['verdict_disagree']}  truth_bitwise_equal {c['truth_bitwise_equal']}")
    print(f"  VERDICT {rec['verdict']}")
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"  receipt -> {a.out}  sha256={sha(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
