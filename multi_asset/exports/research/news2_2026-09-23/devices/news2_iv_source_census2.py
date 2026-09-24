#!/usr/bin/env python3
"""news2_iv_source_census2.py -- the iv-source census, redone on the iv the researcher ACTUALLY uses.

SUPERSEDES my IV_SOURCE_CENSUS.json. That run used the spliced ledger's `zip_iv` column and reported
4.1028% disagreement. THAT NUMBER IS WRONG and is retracted here.

WHY IT WAS WRONG. build_combo_inputs.py L140-141:
    iv, ivaudit = official_intervals(fund, latest, official)
    fe, fn, fi, rn = funding_state(a, fund['off'], fund['ft'], fund['rate'], iv)
The iv handed to funding_state is ASSEMBLED from three sources -- the spliced ledger, the `latest`
ledger, and the 2026-08 official archive -- not the ledger's `zip_iv` column. `zip_iv` is NaN on
109,070 rows that the assembly then fills (the researcher's own audit records
trusted_latest_events_matched 98,066 and official_events_matched 103,527), which is the whole of my
inflated "researcher iv absent" category.

I had even noted in v1's receipt that "funding_state() takes iv as an argument" and used zip_iv anyway.
The judgement this earns: A FIELD NAMED LIKE THE QUANTITY IS NOT THE QUANTITY -- same family as
"the input file is not the input columns", which I had already been corrected on today.

This device calls the researcher's own `official_intervals` unmodified (imported, not reimplemented)
and rebuilds `official` exactly as build_combo_inputs.py L129-139 does, then classifies by lead's four
reasons and reconciles against the in-case audit (692 / 821 / 4,655 = 0.229%).

READ-ONLY. NOT JUDGED: which side is right (contract question).
"""
import argparse, collections, csv, datetime, hashlib, io, json, os, pathlib, sys, zipfile

import numpy as np

SELF = os.path.realpath(__file__)
IV_GRID = (1.0, 2.0, 4.0, 8.0)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def snap_interval(dt_s):
    """verbatim from nc_contract.py L32-44"""
    h = float(dt_s) / 3600.0
    if not (h > 0.0 and h <= 24.0):
        return None
    best, bd = None, None
    for g in IV_GRID:
        d = abs(g - h)
        if bd is None or d < bd or (d == bd and g > best):
            best, bd = g, d
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fund", required=True)
    ap.add_argument("--latest", required=True)
    ap.add_argument("--archive-root", required=True)
    ap.add_argument("--helper-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.helper_dir)
    from corrected_inputs import official_intervals   # called, never modified

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "COUNTS_BY_REASON_ON_THE_ASSEMBLED_IV",
           "supersedes": {"receipt": "IV_SOURCE_CENSUS.json",
                          "why": ("it used the ledger's zip_iv column; the researcher passes "
                                  "official_intervals(fund, latest, official) to funding_state "
                                  "(build_combo_inputs.py L140-141). The 4.1028% it reported is retracted.")},
           "helper": {"module": "corrected_inputs.official_intervals", "dir": a.helper_dir},
           "inputs": {"fund": {"path": a.fund, "sha256": sha(a.fund)},
                      "latest": {"path": a.latest, "sha256": sha(a.latest)}}}

    with np.load(a.fund) as z:
        fund = {k: z[k] for k in z.files}
    with np.load(a.latest) as z:
        latest = {k: z[k] for k in z.files}
    symbols = fund["symbols"]

    root = pathlib.Path(a.archive_root)
    manifest = json.load(open(root / "MANIFEST_2026-08.json"))["files"]
    archive, n_zip = [], 0
    for j, s in enumerate(symbols):
        p = root / (str(s) + "-fundingRate-2026-08.zip")
        if not p.exists():
            continue
        h = sha(p)
        assert h == manifest[str(s)]["sha256"] and manifest[str(s)].get("checksum_match") is not False
        n_zip += 1
        with zipfile.ZipFile(p) as zz:
            names = zz.namelist()
            assert len(names) == 1
            for row in csv.DictReader(io.StringIO(zz.read(names[0]).decode())):
                archive.append((j, int(row["calc_time"]) // 1000,
                                float(row["last_funding_rate"]), float(row["funding_interval_hours"])))
    ar = np.asarray(archive)
    official = dict(sym=ar[:, 0].astype(int), ts=ar[:, 1].astype(np.int64), rate=ar[:, 2], iv=ar[:, 3])
    rec["archive"] = {"zips_read": n_zip, "rows": int(ar.shape[0])}

    iv, ivaudit = official_intervals(fund, latest, official)
    rec["researcher_iv_audit"] = {k: v for k, v in ivaudit.items()
                                  if not isinstance(v, (list, dict))}
    iv = np.asarray(iv, np.float64)

    off = fund["off"].astype(np.int64)
    ft = fund["ft"].astype(np.int64)
    syms = [str(s) for s in symbols]
    rec["assembled_iv"] = {"n_events": int(iv.size),
                           "n_unknown": int((~np.isfinite(iv)).sum()),
                           "zip_iv_n_unknown_for_contrast": int((~np.isfinite(
                               np.asarray(fund["zip_iv"], np.float64))).sum())}

    reasons = collections.Counter()
    by_year = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    k_hist = collections.Counter()
    n_ev = 0
    for j in range(len(syms)):
        b, e = off[j], off[j + 1]
        if e <= b:
            continue
        t = ft[b:e]
        v = iv[b:e]
        prev = None
        for k in range(e - b):
            n_ev += 1
            nc_iv = None if prev is None else snap_interval(int(t[k]) - int(prev))
            r_iv = float(v[k]) if np.isfinite(v[k]) else None
            prev = int(t[k])
            if (nc_iv is None and r_iv is None) or (
                    nc_iv is not None and r_iv is not None and nc_iv == r_iv):
                continue
            if k == 0:
                why = "iii_first_event"
            elif r_iv is None:
                why = "ii_researcher_iv_absent"
            elif nc_iv is None:
                why = "iv_other"
            elif r_iv > 0 and abs(nc_iv / r_iv - round(nc_iv / r_iv)) < 1e-9 and round(nc_iv / r_iv) >= 2:
                why = "i_missing_settlement"
                k_hist[int(round(nc_iv / r_iv))] += 1
            else:
                why = "iv_other"
            reasons[why] += 1
            by_year[why][datetime.datetime.utcfromtimestamp(int(t[k])).year] += 1
            if len(examples[why]) < 3:
                examples[why].append({
                    "symbol": syms[j], "utc": datetime.datetime.utcfromtimestamp(int(t[k])).strftime("%Y-%m-%dT%H:%MZ"),
                    "gap_hours": (None if k == 0 else round((int(t[k]) - int(t[k - 1])) / 3600.0, 4)),
                    "researcher_iv": r_iv, "nc_snap_interval": nc_iv,
                    "ratio_nc_over_researcher": (None if (r_iv in (None, 0) or nc_iv is None)
                                                 else round(nc_iv / r_iv, 4))})
    total = sum(reasons.values())
    rec["totals"] = {"events": n_ev, "disagreeing": total, "pct": 100.0 * total / max(1, n_ev)}
    rec["by_reason"] = {k: {"count": v, "pct_of_events": 100.0 * v / max(1, n_ev),
                            "by_year": {str(y): c for y, c in sorted(by_year[k].items())}}
                        for k, v in reasons.most_common()}
    rec["missing_settlement_multiples"] = {str(k): v for k, v in sorted(k_hist.items())}
    rec["examples"] = dict(examples)

    # reconciliation against the in-case audit quoted in ANALYSIS_researcher_feature_contract_validity
    incase = {"both_known_differ": 692, "researcher_known_gap_unknown": 821,
              "researcher_unknown_gap_known": 4655}
    incase["total"] = sum(incase.values())
    mine = {"both_known_differ": reasons["i_missing_settlement"] + reasons["iv_other"],
            "researcher_known_gap_unknown": reasons["iii_first_event"],
            "researcher_unknown_gap_known": reasons["ii_researcher_iv_absent"]}
    mine["total"] = total
    rec["reconciliation"] = {
        "in_case_receipt": "news_2026-09-23/receipts/IV_AUDIT_gap_rule_vs_research.json (40530ad7)",
        "in_case": incase, "mine": mine,
        "delta": {k: mine[k] - incase[k] for k in incase},
        "in_case_pct": 100.0 * incase["total"] / max(1, n_ev),
        "matches_total": mine["total"] == incase["total"]}

    # RED CONTROL
    ctrl = {"snap_3h_is_4": snap_interval(10800) == 4.0, "snap_25h_is_None": snap_interval(90000) is None,
            "classification_exhaustive": sum(reasons.values()) == total,
            "assembled_iv_differs_from_zip_iv": (rec["assembled_iv"]["n_unknown"]
                                                 != rec["assembled_iv"]["zip_iv_n_unknown_for_contrast"]),
            "n_distinct_reasons": len([k for k, v in reasons.items() if v > 0])}
    ctrl["baseline_green"] = bool(ctrl["snap_3h_is_4"] and ctrl["snap_25h_is_None"]
                                  and ctrl["classification_exhaustive"]
                                  and ctrl["assembled_iv_differs_from_zip_iv"]
                                  and ctrl["n_distinct_reasons"] > 1)
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    json.dump(rec, open(a.out, "w"), indent=2)

    print(f"IV_SOURCE_CENSUS2 VERDICT={rec['verdict']}")
    print(f"  red control: {ctrl}")
    print(f"  assembled iv unknown {rec['assembled_iv']['n_unknown']} "
          f"(zip_iv unknown was {rec['assembled_iv']['zip_iv_n_unknown_for_contrast']})")
    print(f"  researcher audit: {rec['researcher_iv_audit']}")
    t = rec["totals"]
    print(f"  events {t['events']}  disagreeing {t['disagreeing']} = {t['pct']:.4f}%  "
          f"(in-case 0.229%)")
    for k, d in rec["by_reason"].items():
        print(f"   {k:26s} {d['count']:7d}  {d['pct_of_events']:.4f}%  by_year {d['by_year']}")
    print(f"  multiples k: {rec['missing_settlement_multiples']}")
    R = rec["reconciliation"]
    print(f"  RECONCILIATION vs in-case {R['in_case']}")
    print(f"                      mine {R['mine']}")
    print(f"                     delta {R['delta']}  total_matches={R['matches_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
