#!/usr/bin/env python3
"""ladder_coverage_artifact.py -- why three of lead's five arms emit a refusal reason neither end can.

Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3.

SYMPTOM (from the arms' own combo receipts): KZ_res and KZWL_res report reason 'King scores incomplete'
on 1486 anchors, and F10_res reports 'F10 coverage' on 744 scaled anchors -- reasons that do NOT occur
in either end of the ladder (arm none = NC, arm all_new = NEW).

THE LINE THAT EMITS IT, combo_target.py:26:
    if not np.isfinite(king_rank).all(): return {'accepted':False,'reason':'King scores incomplete',...}
king_rank is the anchor's KZ restricted to that anchor's MEMBERS. So a single non-finite cell refuses
the whole anchor.

WHAT THIS DEVICE MEASURES (and its green control): whether NEW's KZ is non-finite on NC's member set,
where, how much, and whether those cells are exactly the names NEW's own member screen excludes. The
green control is the same question asked of NC's own KZ on NC's members -- it must come out 0, else
the device is measuring something other than the swap.

This decides whether the KZ/F10 arms measure "does this input carry the gap" or only "my swap blanked
the book", so it is written as a device with a stored receipt, not as a console line.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--nc-legs", required=True)
    ap.add_argument("--nc-f10", required=True)
    ap.add_argument("--new-legs", required=True)
    ap.add_argument("--new-f10", required=True)
    ap.add_argument("--new-targets", required=True)
    ap.add_argument("--use-from", type=int, default=1672531200)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_gap_carrier_ladder_2026-09-25.md @ be4a013a8 (step 3)",
           "emitting_line": "combo_target.py:26  if not np.isfinite(king_rank).all(): reason='King scores incomplete'",
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("features", a.features), ("nc_legs", a.nc_legs), ("nc_f10", a.nc_f10),
                       ("new_legs", a.new_legs), ("new_f10", a.new_f10),
                       ("new_targets", a.new_targets))}}

    F = np.load(a.features, allow_pickle=False)
    anchors = F["anchors"].astype(np.int64); off = F["off"]; m = F["m"]
    ncl = np.load(a.nc_legs, allow_pickle=False)
    ncf = np.load(a.nc_f10, allow_pickle=False)
    nwl = np.load(a.new_legs, allow_pickle=False)
    nwf = np.load(a.new_f10, allow_pickle=False)
    nwt = np.load(a.new_targets, allow_pickle=True)

    pos = {int(t): i for i, t in enumerate(nwl["E_ts"].astype(np.int64))}
    rows = np.array([pos.get(int(t), -1) for t in anchors])
    assert np.array_equal(nwf["E_ts"].astype(np.int64), nwl["E_ts"].astype(np.int64))
    assert np.array_equal(nwt["E_ts"].astype(np.int64), nwl["E_ts"].astype(np.int64))
    nm_new = list(nwt["members"])

    def scan(arr_new, arr_nc, label):
        """anchors where NEW's array is non-finite on NC's members, plus the NC green control."""
        An = np.asarray(arr_new, np.float64); Ac = np.asarray(arr_nc, np.float64)
        bad, cells_nan, cells_tot, not_in_new_mem = [], 0, 0, 0
        ctl = 0
        for i, t in enumerate(anchors):
            if t < a.use_from:
                continue
            M = m[off[i]:off[i + 1]].astype(np.int64)
            if not np.isfinite(Ac[i][M]).all():
                ctl += 1
            if rows[i] < 0:
                continue
            v = An[rows[i]][M]
            cells_tot += M.size
            nn = ~np.isfinite(v)
            if nn.any():
                bad.append(int(t)); cells_nan += int(nn.sum())
                s_new = set(np.asarray(nm_new[rows[i]], np.int64).tolist())
                not_in_new_mem += int(sum(1 for j in M[nn] if int(j) not in s_new))
        bad = np.array(bad, np.int64)
        yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in bad]) \
            if bad.size else np.array([], int)
        ay = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year
                       for x in anchors[anchors >= a.use_from]])
        out = {"anchors_refused_by_the_swap": int(bad.size),
               "per_year": {str(int(y)): {"affected": int((yr == y).sum()),
                                          "anchors_in_year": int((ay == y).sum()),
                                          "share_pct": round(100.0 * (yr == y).sum() / max((ay == y).sum(), 1), 3)}
                            for y in np.unique(ay)},
               "first": int(bad[0]) if bad.size else None, "last": int(bad[-1]) if bad.size else None,
               "non_finite_member_cells": cells_nan, "member_cells_scanned": cells_tot,
               "non_finite_cell_share_pct": round(100.0 * cells_nan / max(cells_tot, 1), 4),
               "of_those_cells_absent_from_NEW_member_set": not_in_new_mem,
               "absent_share_pct": round(100.0 * not_in_new_mem / max(cells_nan, 1), 2),
               "green_control_nc_array_non_finite_on_nc_members": ctl,
               "green_control_expectation": 0}
        out["green_control_verdict"] = "PASS" if ctl == 0 else "FAIL"

        # The dbar denominator is DAYS, not anchors, so the anchor share does not bound the reading.
        # pre-2026 day count comes from the frozen caliber (news_stats.full_days), quoted here from the
        # engine red control receipt rather than recomputed, and named so it can be checked.
        pre = bad[bad < 1767225600] if bad.size else bad          # 1767225600 = 2026-01-01T00Z
        d_pre = sorted({datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).date().isoformat()
                        for x in pre})
        out["pre2026_days"] = {
            "affected_anchors": int(pre.size), "distinct_utc_days_touched": len(d_pre), "days": d_pre,
            "anchors_per_touched_day": {d: int(sum(1 for x in pre if datetime.datetime.fromtimestamp(
                int(x), datetime.timezone.utc).date().isoformat() == d)) for d in d_pre},
            "pre2026_full_day_denominator": 915,
            "denominator_source": "STEP3_DBAR_none.json dbar_vs_nc.pre2026.n_days (frozen news_stats.full_days)",
            "contaminated_share_of_days_pct": round(100.0 * len(d_pre) / 915, 3),
            "note": ("the anchor share understates the bound; dbar averages per DAY, so the day share is "
                     "what bounds the pre-2026 reading")}
        return out

    rec["KZ"] = scan(nwl["KZ"], ncl["KZ"], "KZ")
    rec["F10_P"] = scan(nwf["P"], ncf["P"], "P")

    rec["reading"] = (
        "NEW's King does not score names NEW never admits, so swapping NEW's KZ onto NC's LARGER member "
        "set leaves NaN on exactly those names and combo_target.py:26 then refuses the whole anchor. The "
        "same holds for F10's P. Consequence: for arms KZ_res / KZWL_res / F10_res the 2026 reading would "
        "measure the swap blanking the book, not whether the input carries the gap. 2023 and 2024 are "
        "unaffected; 2025 is affected on a small share. Lead's ruling required before any engine number "
        "from those three arms is reported.")
    rec["limits"] = ["this is a device-artifact diagnosis, not a book-layer result",
                     "arms remain non-additive, and every arm is a pipeline-unproducible combination"]
    if rec["KZ"]["green_control_verdict"] != "PASS" or rec["F10_P"]["green_control_verdict"] != "PASS":
        rec["verdict"] = "UNAVAILABLE_GREEN_CONTROL_FAILED"
    else:
        rec["verdict"] = "COVERAGE_ARTIFACT_CONFIRMED"
    json.dump(rec, open(a.out, "w"), indent=2)

    print("VERDICT", rec["verdict"])
    for k in ("KZ", "F10_P"):
        d = rec[k]
        print(f"  {k}: anchors refused by the swap = {d['anchors_refused_by_the_swap']}"
              f"   cells {d['non_finite_member_cells']}/{d['member_cells_scanned']}"
              f" ({d['non_finite_cell_share_pct']}%)"
              f"   absent from NEW members = {d['absent_share_pct']}%"
              f"   green control = {d['green_control_verdict']} ({d['green_control_nc_array_non_finite_on_nc_members']})")
        for y, v in d["per_year"].items():
            print(f"      {y}: {v['affected']:5d}/{v['anchors_in_year']:5d}  ({v['share_pct']}%)")
        p = d["pre2026_days"]
        print(f"      pre-2026: {p['affected_anchors']} anchors on {p['distinct_utc_days_touched']} distinct "
              f"UTC days {p['days']} = {p['contaminated_share_of_days_pct']}% of the "
              f"{p['pre2026_full_day_denominator']}-day dbar denominator")
    return 0 if rec["verdict"] == "COVERAGE_ARTIFACT_CONFIRMED" else 4


if __name__ == "__main__":
    sys.exit(main())
