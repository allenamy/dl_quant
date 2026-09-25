#!/usr/bin/env python3
"""ladder_dbar_ex4d.py -- lead's SUPPLEMENTARY pre-2026 reading with the four contaminated days dropped.

Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
(sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03). Lead's words:

  "污染上界按你改的按天报(4/915 = 0.437%,2025 年最后四天),并另报去掉那四天的 911 天附加读数
   (明确标附加)"

THE MAIN READING IS NOT THIS. The main reading is the frozen pre2026 segment (915 days) produced by
pnoise_dbar.py. This device produces a SUPPLEMENTARY number on 911 days, and every field here is
labelled supplementary so it cannot be quoted as the main one.

load_cell / seg_mask / full_days / dbar are IMPORTED from the frozen news_stats.py and never
re-implemented, so the caliber cannot drift; the only difference from the main reading is that four
UTC days are removed from the day list handed to the SAME dbar function. news_stats.py L45 is
`BT = DL = None` -- the caller wires the helpers.

GREEN CONTROL (runs every time, before the supplementary number): with NO days excluded this device
must reproduce the main reading's pre2026 mean bit-for-bit. If it does not, the exclusion machinery is
not a pure subsetting of the frozen caliber and the supplementary number is withheld.
"""
import argparse, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


EXCLUDE = ("2025-12-28", "2025-12-29", "2025-12-30", "2025-12-31")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--news-devices", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--new-tag", required=True)
    ap.add_argument("--nc-dir", required=True)
    ap.add_argument("--nc-tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--main-receipt", required=True, help="STEP3_DBAR_<arm>.json, for the green control")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.news_devices)
    import news_stats as NS
    import bt_tables as _BT
    import bt_driver_lib as _DL
    NS.BT, NS.DL = _BT, _DL

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": ("docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f "
                      "(sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03), revision 1"),
           "criterion_author": "team-lead (not news2)",
           "arm": a.arm,
           "status": "SUPPLEMENTARY_READING_NOT_THE_MAIN_READING",
           "what_this_is": ("lead's supplementary pre-2026 reading with the four contaminated UTC days "
                            "removed. The MAIN reading is the frozen 915-day pre2026 segment in "
                            "STEP3_DBAR_<arm>.json and is unchanged by this device."),
           "excluded_days": list(EXCLUDE),
           "why_those_days": ("the coverage artifact's entire pre-2026 footprint: 24 anchors, all 6 anchors "
                              "on each of 2025-12-28..31 (STEP3_COVERAGE_ARTIFACT.json pre2026_days)"),
           "caliber_source": {"news_stats_sha256": sha(NS.__file__),
                              "bt_tables_sha256": sha(_BT.__file__),
                              "bt_driver_lib_sha256": sha(_DL.__file__),
                              "NPATH": NS.NPATH, "BLOCK_MAIN": NS.BLOCK_MAIN}}

    pn, _ = NS.load_cell(a.new_dir, a.new_tag)
    nn, _ = NS.load_cell(a.nc_dir, a.nc_tag)
    if len(pn) != len(nn):
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "path counts differ"
        json.dump(rec, open(a.out, "w"), indent=2); print("EX4D UNAVAILABLE paths"); return 2
    A = pn[0]["A"]
    if not (A.shape == nn[0]["A"].shape and bool((A == nn[0]["A"]).all())):
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "anchor axes differ"
        json.dump(rec, open(a.out, "w"), indent=2); print("EX4D UNAVAILABLE axes"); return 2
    rec["n_paths"] = len(pn)

    segs = getattr(NS, "SEG", {}) or {}
    s0, s1 = segs["pre2026"]
    m = NS.seg_mask(A, s0, s1)
    days = NS.full_days(A, m)

    # ---- green control FIRST: no exclusion must reproduce the main reading bit-for-bit -----------
    db_all, _ = NS.dbar(pn, nn, m, days)
    main = json.load(open(a.main_receipt))
    main_pre = main["dbar_vs_nc"]["pre2026"]
    got = float(1e4 * db_all.mean())
    rec["green_control"] = {"main_receipt": a.main_receipt, "main_receipt_sha256": sha(a.main_receipt),
                            "main_pre2026_mean_bps_per_day": main_pre["mean_bps_per_day"],
                            "recomputed_with_no_exclusion": got,
                            "main_n_days": main_pre["n_days"], "recomputed_n_days": int(days.size),
                            "bitwise_equal": bool(got == main_pre["mean_bps_per_day"]),
                            "n_days_equal": bool(int(days.size) == main_pre["n_days"])}
    if not (rec["green_control"]["bitwise_equal"] and rec["green_control"]["n_days_equal"]):
        rec["verdict"] = "UNAVAILABLE_GREEN_CONTROL_FAILED"
        rec["why"] = ("with no days excluded this device must reproduce the main pre2026 reading exactly; "
                      "it did not, so the exclusion is not a pure subsetting of the frozen caliber and "
                      "the supplementary number is withheld")
        json.dump(rec, open(a.out, "w"), indent=2)
        print("EX4D UNAVAILABLE: green control failed", json.dumps(rec["green_control"]))
        return 3

    # ---- the supplementary reading ---------------------------------------------------------------
    dstr = np.array([datetime.datetime.fromtimestamp(int(d), datetime.timezone.utc).date().isoformat()
                     for d in days])
    keep = ~np.isin(dstr, np.array(EXCLUDE))
    rec["day_accounting"] = {"days_in_frozen_pre2026": int(days.size),
                            "days_excluded_found": int((~keep).sum()),
                            "days_excluded_expected": len(EXCLUDE),
                            "days_used": int(keep.sum()),
                            "excluded_days_actually_present": sorted(set(dstr[~keep].tolist()))}
    assert int(keep.sum()) + int((~keep).sum()) == int(days.size), "day counts must balance"
    db_ex, _ = NS.dbar(pn, nn, m, days[keep])
    rec["supplementary_pre2026_ex4d"] = {
        "n_days": int(keep.sum()),
        "mean_bps_per_day": float(1e4 * db_ex.mean()),
        "max_abs_daily_bps": float(1e4 * np.abs(db_ex).max()),
        "main_reading_mean_bps_per_day": main_pre["mean_bps_per_day"],
        "difference_vs_main": float(1e4 * db_ex.mean() - main_pre["mean_bps_per_day"])}
    rec["verdict"] = "MEASURED_SUPPLEMENTARY"
    rec["limits"] = ["SUPPLEMENTARY, not the main reading; the main reading is the frozen 915-day pre2026",
                     "arms are NOT additive; every ladder arm is a pipeline-unproducible combination"]
    json.dump(rec, open(a.out, "w"), indent=2)

    g = rec["green_control"]; s = rec["supplementary_pre2026_ex4d"]
    print(f"EX4D arm={a.arm} green_control bitwise={g['bitwise_equal']} "
          f"(main {g['main_pre2026_mean_bps_per_day']} vs recomputed {g['recomputed_with_no_exclusion']}, "
          f"n_days {g['main_n_days']}/{g['recomputed_n_days']})")
    print(f"  SUPPLEMENTARY pre-2026 on {s['n_days']} days: {s['mean_bps_per_day']:+.6f} bps/day "
          f"(main 915-day reading {s['main_reading_mean_bps_per_day']:+.6f}, "
          f"difference {s['difference_vs_main']:+.6f})")
    print(f"  excluded days present: {rec['day_accounting']['excluded_days_actually_present']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
