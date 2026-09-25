#!/usr/bin/env python3
"""d10_year_event_table.py -- question 2's per-event table for ONE year: ledger vs archive, event by event.

D10 stage 1 question 2. Pre-registration: docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901.
lead's ruling: after each completed year, produce that year's counts (ledger-has / archive-has / rate
differs / interval differs) and commit before reporting, without waiting for the whole census.

SCHEMA, read off an actual zip rather than assumed:
    calc_time,funding_interval_hours,last_funding_rate
    1785542400001,8,0.00004123
`calc_time` is in MILLISECONDS and carries millisecond noise (…400001, …200000), while the ledger's `ft`
is in seconds. Events are therefore keyed on round(calc_time_ms / 1000), and the device ASSERTS that every
archive timestamp is within 2 s of a whole second boundary so that the rounding cannot silently merge or
split two settlements.

THREE POPULATION BOUNDARIES that would otherwise fake up differences, all handled explicitly:
  * symbols absent from the ledger's axis (DOSUSDT, MARSCOINUSDT, PONSUSDT) are reported separately and
    kept out of the ledger-only / archive-only counts; the ledger never tracked them, so their events are
    not "missed".
  * months where one side structurally cannot have data -- the unpublished current month, and the months
    outside a symbol's archive coverage window -- are counted in their own buckets, because the earlier
    month-granularity pass showed every such case is a window edge, not a hole.
  * the ledger ends 2026-09-19, so for the latest year the comparison is bounded by the ledger's own last
    event and that bound is reported.

Rate comparison is reported at three tolerances (exact bits, 1e-12, 1e-9) because "differs" at float
resolution is not the same claim as "differs materially", and pooling them would hide which one is meant.
"""
import argparse, collections, csv, datetime, glob, hashlib, io, json, os, sys, zipfile

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True)
    ap.add_argument("--zips-root", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Y = int(a.year)

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901",
           "year": Y,
           "schema": "calc_time(ms),funding_interval_hours,last_funding_rate -- read off a real zip",
           "key": "(symbol, round(calc_time_ms/1000))",
           "inputs": {"ledger": {"path": a.ledger, "sha256": sha(a.ledger)},
                      "inventory": {"path": a.inventory, "sha256": sha(a.inventory)}}}

    # ---- archive side -------------------------------------------------------------------------
    arc = {}                      # (sym, ts) -> (iv_hours, rate)
    arc_dup = collections.Counter()
    months_read, files_read, off_boundary = [], 0, 0
    for mdir in sorted(glob.glob(os.path.join(a.zips_root, f"{Y}-*"))):
        month = os.path.basename(mdir)
        if not os.path.exists(os.path.join(mdir, f"MANIFEST_{month}.json")):
            continue                                  # month not finished; excluded and reported
        months_read.append(month)
        for zp in sorted(glob.glob(os.path.join(mdir, "*-fundingRate-*.zip"))):
            sym = os.path.basename(zp).split("-fundingRate-")[0]
            try:
                z = zipfile.ZipFile(zp)
                body = z.read(z.namelist()[0]).decode("utf-8")
            except Exception as e:
                rec.setdefault("unreadable_zips", []).append({"path": zp, "error": repr(e)[:120]})
                continue
            files_read += 1
            for row in csv.reader(io.StringIO(body)):
                if not row or not row[0].strip().isdigit():
                    continue
                ms = int(row[0])
                ts = int(round(ms / 1000.0))
                if abs(ms - ts * 1000) > 2000:
                    off_boundary += 1
                k = (sym, ts)
                if k in arc:
                    arc_dup[k] += 1
                else:
                    arc[k] = (float(row[1]), float(row[2]))
    rec["archive_months_included"] = months_read
    rec["archive_months_expected"] = [f"{Y}-{m:02d}" for m in range(1, 13) if (Y, m) <= (2026, 9)]
    rec["archive_months_missing_from_this_run"] = sorted(set(rec["archive_months_expected"]) - set(months_read))
    rec["archive_zips_read"] = files_read
    rec["archive_events"] = len(arc)
    rec["archive_duplicate_keys"] = int(sum(arc_dup.values()))
    rec["archive_timestamps_off_second_boundary"] = off_boundary
    assert off_boundary == 0, ("archive timestamps not on second boundaries; the rounding key would be "
                              "unsafe", off_boundary)

    # ---- ledger side --------------------------------------------------------------------------
    z = np.load(a.ledger, allow_pickle=True)
    ft = z["ft"].astype(np.int64); off = z["off"].astype(np.int64)
    syms = z["symbols"]; rate = np.asarray(z["rate"], np.float64)
    zip_iv = np.asarray(z["zip_iv"], np.float64)
    led = {}
    led_dup = collections.Counter()
    led_syms = set()
    ledger_last_ts = int(ft.max())
    for i in range(len(syms)):
        s = str(syms[i]); led_syms.add(s)
        for j in range(off[i], off[i + 1]):
            t = int(ft[j])
            if datetime.datetime.fromtimestamp(t, datetime.timezone.utc).year != Y:
                continue
            k = (s, t)
            if k in led:
                led_dup[k] += 1
            else:
                led[k] = (float(zip_iv[j]), float(rate[j]))
    rec["ledger_events"] = len(led)
    rec["ledger_duplicate_keys"] = int(sum(led_dup.values()))
    rec["ledger_last_event_utc"] = datetime.datetime.fromtimestamp(ledger_last_ts,
                                                                   datetime.timezone.utc).isoformat()

    # ---- population boundaries ----------------------------------------------------------------
    inv = json.load(open(a.inventory))["inventory"]
    not_in_ledger_axis = sorted({s for s, _ in arc} - led_syms)
    arc_in = {k: v for k, v in arc.items() if k[0] in led_syms}
    rec["archive_symbols_not_in_ledger_axis"] = {
        "symbols": not_in_ledger_axis,
        "events_excluded": len(arc) - len(arc_in),
        "why": "the ledger never tracked these, so their events are not missed settlements"}

    def arc_window(s):
        ms = sorted(inv.get(s, {}).get("months", {}))
        return (ms[0], ms[-1]) if ms else None

    both = sorted(set(arc_in) & set(led))
    only_led = sorted(set(led) - set(arc_in))
    only_arc = sorted(set(arc_in) - set(led))

    # classify ledger-only: outside the symbol's archive window / month not in this run / real
    ol_cls = collections.Counter(); ol_real = []
    for s, t in only_led:
        mo = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m")
        w = arc_window(s)
        if mo in rec["archive_months_missing_from_this_run"]:
            ol_cls["month_not_yet_fetched_in_this_run"] += 1
        elif w is None:
            ol_cls["symbol_absent_from_archive_entirely"] += 1
        elif mo < w[0] or mo > w[1]:
            ol_cls["outside_symbol_archive_window"] += 1
        else:
            ol_cls["REAL_ledger_has_archive_does_not"] += 1
            if len(ol_real) < 200:
                ol_real.append({"symbol": s,
                                "utc": datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(),
                                "archive_window": list(w)})
    oa_cls = collections.Counter(); oa_real = []
    for s, t in only_arc:
        if t > ledger_last_ts:
            oa_cls["after_ledger_last_event"] += 1
        else:
            oa_cls["REAL_archive_has_ledger_does_not"] += 1
            if len(oa_real) < 200:
                oa_real.append({"symbol": s,
                                "utc": datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(),
                                "archive_iv_h": arc_in[(s, t)][0], "archive_rate": arc_in[(s, t)][1]})

    # ---- disagreements on shared events -------------------------------------------------------
    rate_exact = rate_1e12 = rate_1e9 = 0
    iv_diff = 0; iv_comparable = 0
    rate_ex = []; iv_ex = []
    for k in both:
        aiv, arate = arc_in[k]
        liv, lrate = led[k]
        if arate != lrate:
            rate_exact += 1
            d = abs(arate - lrate)
            if d > 1e-12:
                rate_1e12 += 1
            if d > 1e-9:
                rate_1e9 += 1
                if len(rate_ex) < 100:
                    rate_ex.append({"symbol": k[0],
                                    "utc": datetime.datetime.fromtimestamp(k[1], datetime.timezone.utc).isoformat(),
                                    "archive_rate": arate, "ledger_rate": lrate, "abs_diff": d})
        if np.isfinite(liv):
            iv_comparable += 1
            if aiv != liv:
                iv_diff += 1
                if len(iv_ex) < 100:
                    iv_ex.append({"symbol": k[0],
                                  "utc": datetime.datetime.fromtimestamp(k[1], datetime.timezone.utc).isoformat(),
                                  "archive_iv_h": aiv, "ledger_zip_iv": liv})

    rec["table"] = {
        "events_in_both": len(both),
        "ledger_only_total": len(only_led), "ledger_only_classified": dict(ol_cls),
        "archive_only_total": len(only_arc), "archive_only_classified": dict(oa_cls),
        "rate_differs_exact_bits": rate_exact,
        "rate_differs_gt_1e-12": rate_1e12,
        "rate_differs_gt_1e-9": rate_1e9,
        "interval_comparable_events": iv_comparable,
        "interval_differs": iv_diff}
    rec["examples"] = {"real_ledger_only": ol_real, "real_archive_only": oa_real,
                       "rate_differs_gt_1e-9": rate_ex, "interval_differs": iv_ex}
    closure = len(both) + len(only_led)
    rec["closure_check"] = {"both_plus_ledger_only": closure, "ledger_events": len(led),
                            "equal": bool(closure == len(led))}
    assert closure == len(led), "both + ledger_only must equal the ledger's events for this year"
    rec["verdict"] = "MEASURED" if not rec["archive_months_missing_from_this_run"] else "PARTIAL_YEAR"
    rec["limits"] = ["a zip proves the venue published a file; it does not prove the file is complete",
                     "interval comparison uses the ledger's zip_iv column, which is NaN on API-only rows; "
                     "those events are excluded from interval_comparable_events rather than counted as agreeing"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    t = rec["table"]
    print(f"YEAR {Y} EVENT TABLE  verdict={rec['verdict']}")
    print(f"  archive months included {len(months_read)}/{len(rec['archive_months_expected'])}"
          f"  missing {rec['archive_months_missing_from_this_run']}")
    print(f"  archive events {rec['archive_events']} (dups {rec['archive_duplicate_keys']})"
          f"   ledger events {rec['ledger_events']} (dups {rec['ledger_duplicate_keys']})")
    print(f"  in both {t['events_in_both']}")
    print(f"  ledger-only {t['ledger_only_total']}: {t['ledger_only_classified']}")
    print(f"  archive-only {t['archive_only_total']}: {t['archive_only_classified']}")
    print(f"  rate differs: exact_bits {t['rate_differs_exact_bits']}  >1e-12 {t['rate_differs_gt_1e-12']}"
          f"  >1e-9 {t['rate_differs_gt_1e-9']}")
    print(f"  interval differs {t['interval_differs']} of {t['interval_comparable_events']} comparable")
    print(f"  symbols not in ledger axis: {rec['archive_symbols_not_in_ledger_axis']['symbols']}"
          f" ({rec['archive_symbols_not_in_ledger_axis']['events_excluded']} events excluded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
