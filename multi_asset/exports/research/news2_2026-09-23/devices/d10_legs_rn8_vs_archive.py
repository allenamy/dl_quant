#!/usr/bin/env python3
"""d10_legs_rn8_vs_archive.py -- instrument 2 of the legs.npz 9ee5886f closure: BEHAVIOUR, not provenance.

Instrument 1 (provenance) identified every input of legs.npz BY HASH, not by directory name:
  source_sha            18387627 -> /dev/shm/news2_2026-09-23/devices/nc_legs.py     (the builder)
  features              3c886a2b -> /dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz
  king_oof              a10b8725 -> /dev/shm/news2_2026-09-23/work/king/KING_OOF.npz
  fund_state            a12a8ed3 -> /dev/shm/nc_2026-09-23/work/fund_state.npz
  tree_shadow_loop      9403dedd -> /dev/shm/nc_2026-09-23/tree/shadow_loop_v3.py
i.e. legs.npz consumed the NC chain's fund_state, NOT news/fund_replay.npz. But "it reads a differently
named file" is not cleanliness -- the name of the quantity is not the quantity. This device measures the
values.

WHY THIS TEST AND NOT AN EVENT-TABLE TEST. The fund_replay defect was NOT missing data: the settlements
were in the ledger and the as-of INDEX froze, so the value served was a real but stale rate. An audit of
the event table would have passed it. So the thing to compare is the number legs.npz actually carries:
  nc_legs.py:74   RN8[i, m] = [NC.funding_asof(ema.get(syms[j]), led[syms[j]][-1], A)[3] ...]
  nc_contract.py:98  return acc, rate, iv, rate * 8 / iv          # [3] is rn8
  nc_contract.py:95  NaN unless anchor - ft <= FRESH_S (43200 s) and the EMA is finite
  nc_contract.py:92  raises if the as-of row is AFTER the anchor
So for every cell where legs.npz carries a finite RN8, the correct value is rate*8/iv of the LAST archive
settlement at or before that anchor. A frozen as-of shows up here as a finite-but-wrong RN8, which is
exactly the defect class.

POPULATION GUARDS:
  1. only symbols on both the legs axis and the month's archive;
  2. a cell whose as-of would fall in the PREVIOUS month is out-of-coverage, not wrong: the last in-month
     event at or before the anchor is the true as-of only if at least one in-month event exists at or
     before it (any earlier-month event is necessarily older). Cells without one are excluded BY NAME.
  3. the reverse direction (legs NaN while the archive has a fresh event) is counted but NOT called a
     miss: RN8 is only filled at MEMBER columns and this device has no member mask, so that count is
     reported as undecidable rather than as completeness.

The archive is read only through the R25-11 gate. --positive-control perturbs legs values (1 ULP and a
stale substitution) and each must be SEEN, because "all cells agree" is otherwise indistinguishable from a
comparison that cannot fail.
"""
import argparse
import collections
import csv
import datetime
import glob
import hashlib
import io
import json
import math
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE

FRESH_S = 43200  # nc_contract.py:21
# DERIVED, not redeclared. I first hardcoded (1.0, 2.0, 4.0, 8.0) here while the canonical set in
# common/funding_interval.py is ALLOWED_IV = (1.0, 2.0, 4.0, 6.0, 8.0) -- it includes 6.0. Two constants that
# must agree, written twice, drift; so this imports the one that lead's ruling names as authoritative. (No
# judged verdict changed: all 28 UNRESOLVED cells have a 3.0h gap, checked before the fix. What was wrong was
# the DESCRIPTIVE label on any 6h-spacing as-of row.)
for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
               os.path.realpath(__file__))))), "common")):
    if os.path.exists(os.path.join(_c, "funding_interval.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/funding_interval.py not found; this device must not redeclare ALLOWED_IV")
from funding_interval import ALLOWED_IV as STANDARD_IV   # lead's ruling: use this module's tiering


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def u(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def month_bounds(m):
    lo = datetime.datetime.strptime(m, "%Y-%m").replace(tzinfo=datetime.timezone.utc)
    hi = (lo + datetime.timedelta(days=32)).replace(day=1)
    return int(lo.timestamp()), int(hi.timestamp())


def read_month(zipdir, month):
    GATE.require_verified(zipdir, month, what=f"legs-rn8-audit {month}")
    arc = {}
    for zp in sorted(glob.glob(os.path.join(zipdir, f"*-fundingRate-{month}.zip"))):
        s = os.path.basename(zp).split("-fundingRate-")[0]
        z = zipfile.ZipFile(zp)
        ev = []
        for row in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
            if row and row[0].strip().isdigit():
                ev.append((int(round(int(row[0]) / 1000.0)), float(row[1]), float(row[2])))
        ev.sort()
        arc[s] = ev
    return arc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legs", required=True)
    ap.add_argument("--legs-sha", default=None)
    ap.add_argument("--zips-root", required=True)
    ap.add_argument("--months", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--features", default=None,
                    help="NEWS_FEATURES.npz -- supplies the per-anchor MEMBER set so the "
                         "legs_nan_archive_fresh direction stops being undecidable. RN8 is filled only at "
                         "member columns, so a NaN at a non-member column is CORRECT, not a miss. Without "
                         "this the device reports that count as undecidable rather than as completeness.")
    ap.add_argument("--positive-control", action="store_true")
    a = ap.parse_args()
    months = [m.strip() for m in a.months.split(",") if m.strip()]

    lsha = sha(a.legs)
    if a.legs_sha:
        assert lsha.startswith(a.legs_sha), ("legs.npz is not the pinned artifact", lsha, a.legs_sha)

    Z = np.load(a.legs, allow_pickle=True)
    E = Z["E_ts"].astype(np.int64)
    syms = [str(s) for s in Z["symbols"]]
    RN8 = np.array(Z["RN8"], dtype=np.float32)          # a copy: the control perturbs it in memory only
    ready = np.array(Z["ready"], dtype=bool)
    idx = {s: j for j, s in enumerate(syms)}

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "gate_sha256": sha(os.path.realpath(GATE.__file__)), "argv": sys.argv[1:],
           "what": "legs.npz RN8 vs the last archive settlement at or before each anchor (rate*8/iv)",
           "legs": {"path": a.legs, "sha256": lsha, "anchors": int(E.size), "symbols": len(syms),
                    "ready_anchors": int(ready.sum()),
                    "E_ts_range": [u(E.min()), u(E.max())]},
           "standard_iv_set": {"value": list(STANDARD_IV),
                               "source": "common/funding_interval.py ALLOWED_IV, imported not redeclared",
                               "why": "lead's ruling names that module's tiering as authoritative"},
           "cited": ["nc_legs.py:74 RN8 = funding_asof(...)[3]",
                     "nc_contract.py:98 rn8 = rate*8/iv", "nc_contract.py:95 FRESH_S=43200 gate",
                     "nc_contract.py:92 raises if the as-of row is after the anchor"],
           "provenance_instrument_1": {
               "source_sha_18387627": "/dev/shm/news2_2026-09-23/devices/nc_legs.py",
               "features_3c886a2b": "/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz",
               "king_oof_a10b8725": "/dev/shm/news2_2026-09-23/work/king/KING_OOF.npz",
               "fund_state_a12a8ed3": "/dev/shm/nc_2026-09-23/work/fund_state.npz",
               "tree_shadow_loop_9403dedd": "/dev/shm/nc_2026-09-23/tree/shadow_loop_v3.py",
               "method": "matched BY HASH over /dev/shm, not by directory name",
               "note": ("P3_LEGS.json is not modified by this device; its own file sha256 is 21cf687f, "
                        "which nothing in the fanom receipts pins -- their legs_receipt_sha256 field is "
                        "lr['sha256'], the receipt's CLAIM about legs.npz, not the receipt file's hash")},
           "months": {}}

    # the member set, from the construction dlarch's trainer uses (not a mask whose name sounds right;
    # `cand = mask & crypto` is the tradable/candidate mask and is a DIFFERENT quantity)
    member_at = None
    if a.features:
        Fz = np.load(a.features, allow_pickle=True)
        fa = Fz["anchors"].astype(np.int64)
        fs = [str(x) for x in Fz["symbols"]]
        foff = Fz["off"].astype(np.int64)
        fm = Fz["m"].astype(np.int64)
        fcount = Fz["count"].astype(np.int64)
        assert np.array_equal(np.diff(foff), fcount), "member construction does not close (count vs off)"
        assert fm.max() < len(fs), "member index beyond the symbol axis"
        # index directly only if the axes match in ORDER; otherwise map by value
        assert fs == syms, "feature and legs symbol axes differ in order; refusing to index by position"
        assert np.array_equal(fa, E), "feature and legs anchor axes differ in order; refusing to index by position"
        member_at = [set(int(x) for x in fm[foff[i]:foff[i + 1]]) for i in range(len(fa))]
        rec["member_source"] = {"path": a.features, "sha256": sha(a.features),
                                "construction": "members[i] = m[off[i]:off[i+1]] -> columns into symbols",
                                "explicitly_not": "cand = mask & crypto (tradable/candidate mask)",
                                "axes_identical_in_order": True,
                                "total_member_cells": int(fcount.sum())}

    ctrl = {"perturbed": []} if a.positive_control else None
    ctrl_used = set()   # (i, j) already perturbed: the controls must not overwrite one another
    tot = collections.Counter()
    for m in months:
        arc = read_month(os.path.join(a.zips_root, m), m)
        lo, hi = month_bounds(m)
        ai = np.flatnonzero((E >= lo) & (E < hi))
        shared = sorted(set(arc) & set(idx))
        c = collections.Counter()
        mism = []

        if a.positive_control and len(ai) and shared:
            # perturb legs RN8 in memory: 1 ULP, and a STALE substitution (the previous settlement's value),
            # which is the fund_replay defect's actual shape. Both must be seen.
            placed = 0
            for i in ai:
                A = int(E[i])
                for s in shared:
                    j = idx[s]
                    if not np.isfinite(RN8[i, j]):
                        continue
                    ev = [e for e in arc[s] if e[0] <= A]
                    if len(ev) < 2:
                        continue
                    if placed == 0:
                        ctrl_used.add((int(i), int(j)))
                        old = float(RN8[i, j])
                        # ULP in the array's OWN dtype. The first version took a float64 nextafter and
                        # stored it into this float32 array, so it rounded straight back to `old` and the
                        # control was a no-op -- CONTROL_FAIL caught my own control, which is what a
                        # control is for. np.nextafter on float32 operands steps one float32 ULP.
                        RN8[i, j] = np.nextafter(np.float32(old), np.float32(np.inf))
                        assert float(RN8[i, j]) != old, "1 ULP perturbation collapsed; control would be vacuous"
                        ctrl["perturbed"].append({"kind": "1_ulp_float32", "symbol": s, "anchor": u(A),
                                                  "from": old, "to": float(RN8[i, j]),
                                                  "delta": float(RN8[i, j]) - old})
                    else:
                        ctrl_used.add((int(i), int(j)))
                        old = float(RN8[i, j])
                        psec, _pivcol, prate = ev[-2]
                        pgap = (psec - ev[-3][0]) / 3600.0 if len(ev) >= 3 else _pivcol
                        RN8[i, j] = np.float32(prate * 8.0 / (pgap or _pivcol))
                        ctrl["perturbed"].append({"kind": "stale_previous_settlement", "symbol": s,
                                                  "anchor": u(A), "from": old, "to": float(RN8[i, j]),
                                                  "stale_event": u(psec)})
                    placed += 1
                    break
                if placed >= 2:
                    break
            # THIRD control, for the class whose emptiness is a headline. legs_nan_BUT_MEMBER_archive_fresh
            # reads 0, and a class that has never fired cannot certify its own silence -- so blank one MEMBER
            # cell's RN8 where the archive IS fresh, and that class must become >= 1.
            ctrl["member_nan_control"] = None
            if member_at is not None:
                done3 = False
                for i in ai:
                    if done3:
                        break
                    A = int(E[i])
                    for s in shared:
                        j = idx[s]
                        if (int(i), int(j)) in ctrl_used:
                            continue   # a control that overwrites another control's cell silently cancels it:
                                       # the first run of this third control blanked the ULP cell and DIFFER
                                       # fell from 2 to 1, so the suite reported FAIL for the wrong reason
                        if j not in member_at[i] or not np.isfinite(RN8[i, j]):
                            continue
                        # The cell must actually REACH the member-NaN branch: that needs a computable
                        # spacing (so the as-of has an in-month predecessor) and a FRESH as-of, otherwise the
                        # cell is consumed earlier by a coverage bucket. My first version ignored this and
                        # picked a first-in-month as-of, so the control silently tested nothing -- CONTROL_FAIL
                        # caught it, which is the second time today a control caught my own control.
                        ev = [e for e in arc[s] if e[0] <= A]
                        if len(ev) < 2 or (A - ev[-1][0]) > FRESH_S:
                            continue
                        gap = (ev[-1][0] - ev[-2][0]) / 3600.0
                        if not gap:
                            continue
                        RN8[i, j] = np.float32(np.nan)
                        ctrl["member_nan_control"] = {"symbol": s, "anchor": u(A),
                                                      "blanked": "a MEMBER cell's RN8 set to NaN",
                                                      "expect": "legs_nan_BUT_MEMBER_archive_fresh >= 1"}
                        done3 = True
                        break
            ctrl["placed"] = placed

        for i in ai:
            A = int(E[i])
            for s in shared:
                j = idx[s]
                got = RN8[i, j]
                ev = arc[s]
                # guard 2: the as-of must be determined by in-month data
                k = -1
                for t in range(len(ev) - 1, -1, -1):
                    if ev[t][0] <= A:
                        k = t
                        break
                if k < 0:
                    if np.isfinite(got):
                        c["legs_finite_but_no_in_month_asof"] += 1
                    else:
                        c["out_of_coverage_no_in_month_asof"] += 1
                    continue
                sec, iv_col, r = ev[k]
                # WHICH interval normalises the rate. The archive's funding_interval_hours column at a
                # TRANSITION row carries the NEW regime's interval, not the interval this payment accrued
                # over. Measured, not assumed: all four disagreements in the first run were the exact
                # moment a symbol left a 1h spike for 4h -- the column said 4.0 while the actual gap from
                # the previous settlement was 2.0h (or 1.0h), and legs.npz matched the GAP bitwise. The
                # payment accrued over the elapsed time, so the gap is the correct normaliser and the
                # column would understate RN8 by 2-4x at exactly the spike exits. This is the same
                # column-vs-spacing split that NONSTANDARD_SPACING exists for, and it is why the rule is
                # "take the exchange's real record" rather than one field of it.
                iv_gap = (sec - ev[k - 1][0]) / 3600.0 if k >= 1 else None
                iv = iv_gap if iv_gap else None
                if iv is None:
                    if np.isfinite(got):
                        c["legs_finite_but_no_spacing_available"] += 1
                    else:
                        c["out_of_coverage_no_spacing"] += 1
                    continue
                if iv_gap != iv_col:
                    c["asof_row_where_iv_column_disagrees_with_spacing"] += 1
                    if iv_gap in STANDARD_IV:
                        c["  of_those_spacing_is_standard"] += 1
                    else:
                        c["  of_those_spacing_is_NONSTANDARD"] += 1
                fresh = (A - sec) <= FRESH_S
                exp = np.float32(r * 8.0 / iv)
                exp_col = np.float32(r * 8.0 / iv_col) if iv_col else np.float32(np.nan)
                if not fresh:
                    exp = np.float32(np.nan)
                    exp_col = np.float32(np.nan)
                if np.isfinite(got) and np.isfinite(exp):
                    c["compared_finite"] += 1
                    if got == exp:
                        c["bitwise_equal"] += 1
                    elif (iv not in STANDARD_IV) and np.isfinite(exp_col) and got == exp_col:
                        # NONSTANDARD spacing (e.g. a 3h gap when a 1h spike ends on a non-4h-grid slot).
                        # Which interval normalises the payment is then UNDECIDABLE from the archive alone:
                        # the money accrued over 3h, but the venue's stated interval is 4h. legs.npz falls
                        # back to the venue field here -- and follows the SPACING on every standard-spacing
                        # row. That is the same tiering my own common/funding_interval.py arrived at
                        # independently (EXACT_BY_SPACING, else UNRESOLVED_NONSTANDARD_SPACING), so it is a
                        # modelling convention, not an error, and this device has no basis to prefer one.
                        c["unresolved_nonstandard_spacing_legs_used_iv_column"] += 1
                        if len(mism) < 25:
                            mism.append({"symbol": s, "anchor": u(A), "class": "UNRESOLVED_NONSTANDARD_SPACING",
                                         "legs_rn8": float(got), "by_spacing": float(exp),
                                         "by_iv_column": float(exp_col), "iv_gap_h": iv,
                                         "iv_column_h": iv_col, "asof_event": u(sec)})
                    else:
                        c["DIFFER"] += 1
                        if np.isfinite(exp_col) and got == exp_col:
                            c["DIFFER_but_matches_iv_column"] += 1
                        if len(mism) < 25:
                            mism.append({"symbol": s, "anchor": u(A), "legs_rn8": float(got),
                                         "expected_rn8_by_spacing": float(exp),
                                         "expected_rn8_by_iv_column": float(exp_col),
                                         "asof_event": u(sec), "age_s": A - sec, "archive_rate": r,
                                         "iv_gap_h": iv, "iv_column_h": iv_col,
                                         "abs_diff": abs(float(got) - float(exp))})
                elif not np.isfinite(got) and not np.isfinite(exp):
                    c["both_nan_agree"] += 1
                elif np.isfinite(got) and not np.isfinite(exp):
                    c["legs_finite_archive_says_stale"] += 1      # would be a freshness-gate violation
                    if len(mism) < 25:
                        mism.append({"symbol": s, "anchor": u(A), "legs_rn8": float(got),
                                     "expected_rn8_by_spacing": None, "asof_event": u(sec),
                                     "age_s": A - sec,
                                     "why": "archive as-of is older than FRESH_S, so RN8 should be NaN"})
                else:
                    # guard 3, now DECIDABLE when --features is given: RN8 is filled only at member columns,
                    # so NaN at a non-member column is correct behaviour and not a miss.
                    if member_at is None:
                        c["legs_nan_archive_fresh_UNDECIDABLE_no_member_mask"] += 1
                    elif j in member_at[i]:
                        c["legs_nan_BUT_MEMBER_archive_fresh"] += 1   # a genuine miss; must be named
                        if len(mism) < 25:
                            mism.append({"symbol": s, "anchor": u(A), "class": "MEMBER_WITH_NAN_RN8",
                                         "archive_asof": u(sec), "age_s": A - sec,
                                         "archive_rate": r, "iv_gap_h": iv, "iv_column_h": iv_col})
                    else:
                        c["legs_nan_correct_NOT_a_member"] += 1

        rec["months"][m] = {
            "anchors_in_month": int(ai.size), "shared_symbols": len(shared),
            "cells": {k: int(v) for k, v in c.items()},
            "agreement_pct": (round(100.0 * c["bitwise_equal"] / c["compared_finite"], 6)
                              if c["compared_finite"] else None),
            "mismatch_examples": mism,
            "legs_nan_archive_fresh_note": ("NOT a miss: RN8 is filled only at member columns and this "
                                            "device has no member mask, so this count is undecidable here"),
        }
        for k, v in c.items():
            tot[k] += v

    rec["all_months"] = {k: int(v) for k, v in tot.items()}
    # bad = genuine disagreements only. `legs_finite_but_no_spacing_available` is a COVERAGE class, not a
    # disagreement: the as-of row is the first in-month event, so there is no in-month predecessor to
    # measure the spacing from and this device cannot judge the cell either way. Counting it as bad would
    # be the same error as calling a symbol whose archive simply ends a missing settlement. And the 26
    # UNRESOLVED nonstandard-spacing cells are a modelling convention, reported and excluded by name.
    bad = (tot["DIFFER"] + tot["legs_finite_archive_says_stale"] + tot["legs_finite_but_no_in_month_asof"]
           + tot["legs_nan_BUT_MEMBER_archive_fresh"])
    undecidable = {
        "legs_finite_but_no_spacing_available": int(tot["legs_finite_but_no_spacing_available"]),
        "unresolved_nonstandard_spacing_legs_used_iv_column":
            int(tot["unresolved_nonstandard_spacing_legs_used_iv_column"]),
        "legs_nan_archive_fresh_UNDECIDABLE_no_member_mask":
            int(tot["legs_nan_archive_fresh_UNDECIDABLE_no_member_mask"]),
        "legs_nan_correct_NOT_a_member": int(tot["legs_nan_correct_NOT_a_member"]),
        "out_of_coverage_no_in_month_asof": int(tot["out_of_coverage_no_in_month_asof"]),
        "out_of_coverage_no_spacing": int(tot["out_of_coverage_no_spacing"]),
    }
    rec["undecidable_by_this_device"] = undecidable
    closes = (tot["bitwise_equal"] + tot["DIFFER"]
              + tot["unresolved_nonstandard_spacing_legs_used_iv_column"] == tot["compared_finite"])
    rec["classification_closes"] = bool(closes)
    assert closes, ("finite-cell classification does not close", dict(tot))
    rec["verdict"] = ("LEGS_RN8_MATCHES_ARCHIVE_AS_OF" if bad == 0 and tot["compared_finite"]
                      else ("NO_COMPARABLE_CELLS" if not tot["compared_finite"] else "LEGS_RN8_DISAGREES"))

    print(f"legs.npz RN8 vs archive as-of   legs={a.legs}")
    print(f"  sha {lsha[:16]}  anchors={E.size} ready={int(ready.sum())} symbols={len(syms)}")
    for m in months:
        d = rec["months"][m]
        cc = d["cells"]
        print(f"  {m}: anchors={d['anchors_in_month']} shared_syms={d['shared_symbols']}")
        print(f"       compared_finite={cc.get('compared_finite',0)} bitwise_equal={cc.get('bitwise_equal',0)} "
              f"DIFFER={cc.get('DIFFER',0)}  agreement={d['agreement_pct']}%")
        print(f"       iv_column_disagrees_with_spacing_on_asof_rows="
              f"{cc.get('asof_row_where_iv_column_disagrees_with_spacing',0)}"
              f"  (standard spacing {cc.get('  of_those_spacing_is_standard',0)},"
              f" NONSTANDARD {cc.get('  of_those_spacing_is_NONSTANDARD',0)})")
        print(f"       unresolved_nonstandard_spacing={cc.get('unresolved_nonstandard_spacing_legs_used_iv_column',0)}"
              f"  DIFFER_but_matches_iv_column={cc.get('DIFFER_but_matches_iv_column',0)}")
        print(f"       both_nan_agree={cc.get('both_nan_agree',0)} "
              f"legs_finite_archive_says_stale={cc.get('legs_finite_archive_says_stale',0)} "
              f"nan_not_member={cc.get('legs_nan_correct_NOT_a_member',0)} "
              f"nan_BUT_MEMBER={cc.get('legs_nan_BUT_MEMBER_archive_fresh',0)} "
              f"nan_undecidable={cc.get('legs_nan_archive_fresh_UNDECIDABLE_no_member_mask',0)} "
              f"out_of_coverage={cc.get('out_of_coverage_no_in_month_asof',0)}")
        for e in d["mismatch_examples"][:5]:
            print(f"         {e}")
    print(f"  ALL {rec['all_months']}")

    if a.positive_control:
        seen = (tot["DIFFER"] >= 1)
        seen_member_nan = (tot["legs_nan_BUT_MEMBER_archive_fresh"] >= 1)
        rec["positive_control"] = ctrl
        rec["positive_control_result"] = {
            "differ_channel_saw_the_perturbations": bool(seen),
            "member_nan_class_reddened": bool(seen_member_nan),
            "member_nan_class_note": ("this class reads 0 in the clean run; a class that never fires cannot "
                                      "certify its own silence, so the control must make it fire"),
            "verdict": ("CONTROL_PASS" if (seen and tot["DIFFER"] >= 2 and
                                           (seen_member_nan or ctrl.get("member_nan_control") is None))
                        else "CONTROL_FAIL"),
            "n_differ": int(tot["DIFFER"]),
            "data_verdict_this_run_would_have_reported": rec["verdict"],
            "meaning": "with the control on, every red counter here is my own injected perturbation",
        }
        rec["verdict"] = "POSITIVE_CONTROL_RUN_NOT_AN_AUDIT"
        print(f"  CONTROL {rec['positive_control_result']['verdict']} n_differ={tot['DIFFER']} "
              f"placed={ctrl.get('placed')}")

    print(f"  VERDICT {rec['verdict']}")
    if a.out:
        json.dump(rec, open(a.out, "w"), indent=1)
        print(f"  receipt -> {a.out}  sha256={sha(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
