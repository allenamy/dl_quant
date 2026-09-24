#!/usr/bin/env python3
"""news2_prod_ledger_gaps.py -- does the PRODUCTION funding ledger have missing settlements?

For lead, as the last piece of the D10 material: the census on the researcher's ledger found 485
"missing settlement" events (gap an integer multiple of the recorded interval). D10's NC side infers the
interval from the gap, so a missing settlement makes NC infer a longer interval. The question for the
live book is whether that situation occurs in production at all.

SOURCE: ~/wide_shadow/state/aux.json key `ledger_tail` -- the producer's own per-name ledger tail,
{symbol: [[ft, rate, iv], ...]}. READ-ONLY: this device opens the file for reading and writes nothing
under ~/wide_shadow.

METHOD: for consecutive events of a name, compare the observed gap in hours against the interval
RECORDED ON THE EARLIER event. A gap that is an integer multiple k>=2 of it means k-1 settlements are
absent from the ledger between them.

LIMITS, stated:
  - the tail is a WINDOW, not full history; the covered span is reported, and a "missing" settlement at
    the very start of a name's tail cannot be distinguished from the tail simply beginning there, so the
    first event of each name is excluded.
  - a recorded interval that itself changed between the two events would show up here as a multiple; the
    count is therefore an UPPER bound on "ledger missing a settlement", not a proven count.
  - this reads the producer's ledger, which is the input to NC's snap_interval. It does NOT show what
    the exchange actually settled.
"""
import argparse, collections, datetime, hashlib, json, os, sys

SELF = os.path.realpath(__file__)
IV_GRID = (1.0, 2.0, 4.0, 8.0)


def snap_interval(dt_s):
    """verbatim from nc_contract.py L32-44 -- what NC would actually infer from the widened gap.
    Reporting the raw gap hours here instead (my first version) was a mislabel: snap_interval(3h) is
    4.0, not 3.0, because 3h ties between 2 and 4 and the tie goes to the LARGER grid value."""
    h = float(dt_s) / 3600.0
    if not (h > 0.0 and h <= 24.0):
        return None
    best, bd = None, None
    for g in IV_GRID:
        d = abs(g - h)
        if bd is None or d < bd or (d == bd and g > best):
            best, bd = g, d
    return best


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aux", required=True)
    ap.add_argument("--since", type=int, default=0, help="only count events at or after this ts")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable,
           "status": "UPPER_BOUND_ON_MISSING_SETTLEMENTS_READ_ONLY",
           "source": {"path": a.aux, "sha256": sha(a.aux),
                      "key": "ledger_tail (producer's own per-name ledger tail)"},
           "limits": ["tail is a window, not full history; each name's first event excluded",
                      "an interval that genuinely changed also shows as a multiple => UPPER bound",
                      "reads the producer's ledger, not what the exchange actually settled"]}

    d = json.load(open(a.aux))
    lt = d["ledger_tail"]
    n_names = len(lt)
    n_ev = 0
    tmin, tmax = None, None
    mult = collections.Counter()
    per_year = collections.Counter()
    examples = []
    iv_values = collections.Counter()

    for sym, evs in lt.items():
        prev = None
        for e in evs:
            ft = int(e[0]); iv = e[2]
            n_ev += 1
            tmin = ft if tmin is None else min(tmin, ft)
            tmax = ft if tmax is None else max(tmax, ft)
            if iv is not None:
                iv_values[float(iv)] += 1
            if prev is not None and ft >= a.since:
                pft, piv = prev
                if piv is not None and float(piv) > 0:
                    gap_h = (ft - pft) / 3600.0
                    k = gap_h / float(piv)
                    if abs(k - round(k)) < 1e-9 and round(k) >= 2:
                        kk = int(round(k))
                        mult[kk] += 1
                        per_year[datetime.datetime.utcfromtimestamp(ft).year] += 1
                        if len(examples) < 8:
                            examples.append({
                                "symbol": sym, "prev_ft": pft, "ft": ft,
                                "utc": datetime.datetime.utcfromtimestamp(ft).strftime("%Y-%m-%dT%H:%MZ"),
                                "recorded_iv_on_prev": float(piv), "gap_hours": gap_h,
                                "k_multiple": kk,
                                "nc_would_snap_to": snap_interval(ft - pft),
                                "ratio_nc_over_recorded": (
                                    None if snap_interval(ft - pft) is None
                                    else round(snap_interval(ft - pft) / float(piv), 4))})
            prev = (ft, iv)

    total = sum(mult.values())
    rec["ledger_tail"] = {
        "n_names": n_names, "n_events": n_ev,
        "window_first_utc": datetime.datetime.utcfromtimestamp(tmin).strftime("%Y-%m-%dT%H:%MZ") if tmin else None,
        "window_last_utc": datetime.datetime.utcfromtimestamp(tmax).strftime("%Y-%m-%dT%H:%MZ") if tmax else None,
        "recorded_iv_distribution": {str(k): v for k, v in sorted(iv_values.items())}}
    rec["missing_settlement_upper_bound"] = {
        "total": total, "by_multiple": {str(k): v for k, v in sorted(mult.items())},
        "by_year": {str(k): v for k, v in sorted(per_year.items())},
        "pct_of_events": 100.0 * total / max(1, n_ev)}
    rec["examples"] = examples

    # RED CONTROL: the detector must fire on a constructed gap and not on a clean 1x gap.
    def detect(piv, gap_h):
        k = gap_h / piv
        return abs(k - round(k)) < 1e-9 and round(k) >= 2
    ctrl = {"fires_on_2x": detect(4.0, 8.0), "fires_on_4x": detect(1.0, 4.0),
            "silent_on_1x": not detect(4.0, 4.0), "silent_on_1p5x": not detect(4.0, 6.0),
            "snap_selftest_3h_is_4": snap_interval(10800) == 4.0,
            "snap_selftest_25h_is_None": snap_interval(90000) is None}
    ctrl["baseline_green"] = bool(ctrl["fires_on_2x"] and ctrl["fires_on_4x"]
                                 and ctrl["silent_on_1x"] and ctrl["silent_on_1p5x"]
                                 and ctrl["snap_selftest_3h_is_4"]
                                 and ctrl["snap_selftest_25h_is_None"])
    ctrl["iv_distribution_non_degenerate"] = len(iv_values) > 1
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = "red control: the multiple detector did not behave on constructed inputs"

    json.dump(rec, open(a.out, "w"), indent=2)
    L = rec["ledger_tail"]; M = rec["missing_settlement_upper_bound"]
    print(f"PROD_LEDGER_GAPS VERDICT={rec['verdict']}")
    print(f"  red control: {ctrl}")
    print(f"  ledger_tail: {L['n_names']} names, {L['n_events']} events, "
          f"{L['window_first_utc']} .. {L['window_last_utc']}")
    print(f"  recorded iv distribution: {L['recorded_iv_distribution']}")
    print(f"  missing-settlement UPPER BOUND: {M['total']} ({M['pct_of_events']:.4f}% of events)  "
          f"by multiple {M['by_multiple']}  by year {M['by_year']}")
    for e in rec["examples"][:5]:
        print(f"   e.g. {e['utc']} {e['symbol']:12s} recorded_iv={e['recorded_iv_on_prev']} "
              f"gap={e['gap_hours']}h k={e['k_multiple']} nc_would_snap_to={e['nc_would_snap_to']} "
              f"ratio_nc/recorded={e.get('ratio_nc_over_recorded')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
