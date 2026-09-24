#!/usr/bin/env python3
"""news2_iv_source_census.py -- count, by reason, the events where the two iv sources disagree.

For lead, as material for the user's ruling on D10. D10 is a frozen, deliberate choice:
  NC        iv = snap_interval(ft - previous ledger ft)      (nc_contract.py L32-44)
  researcher iv = the ledger's recorded zip_iv
`ANALYSIS_researcher_feature_contract_validity` (bff28680f, D10 correction) measured these as differing
on about 0.23% of events. This device reproduces that count on the delivered ledger and splits it by
reason so the trade-off can be judged rather than argued.

REASONS (lead's list, each event gets exactly ONE, first match wins, in this order):
  (iii) first_event          no previous settlement for the name, so NC has no gap to snap => unknown
  (ii)  researcher_iv_absent the ledger has no zip_iv for the row (src==1 rows carry NaN zip_iv);
                             lead's "extension rows" category -- see the LIMIT below
  (i)   missing_settlement   NC's snapped gap is an integer multiple k>=2 of the recorded zip_iv,
                             i.e. the ledger is missing k-1 settlements so the gap widened
  (iv)  other                everything else, counted and NOT explained away

LIMIT, stated rather than glossed: lead described (ii) as "zip_iv on extension rows equals the value at
fetch time". What is actually observable in the delivered ledger is that src==1 rows carry NaN zip_iv
(109,070 rows, exactly the src==1 count). "Equals the fetch-time value" is a claim about how the value
was produced, which this file cannot show. So (ii) is reported as "researcher iv absent", and whether
that is the same phenomenon as the remembered x0910 interval mismatch is NOT asserted here.

READ-ONLY. NOT JUDGED: which side is right (contract question).
"""
import argparse, collections, datetime, hashlib, json, os, sys

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
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "COUNTS_BY_REASON_NOT_WHICH_SIDE_IS_RIGHT",
           "d10": {"nc": "snap_interval(ft - previous ledger ft), nc_contract.py L32-44",
                   "researcher": "the ledger's recorded zip_iv",
                   "prior_measurement": "ANALYSIS_researcher_feature_contract_validity (bff28680f): "
                                        "the two differ on about 0.23% of events"},
           "limit_on_reason_ii": ("lead described (ii) as 'zip_iv on extension rows equals the fetch-time "
                                  "value'. What is observable here is that src==1 rows carry NaN zip_iv. "
                                  "'Equals the fetch-time value' is a claim about provenance this file "
                                  "cannot show, so (ii) is reported as 'researcher iv absent' and is NOT "
                                  "asserted to be the same phenomenon as the remembered x0910 mismatch."),
           "inputs": {"ledger": {"path": a.ledger, "sha256": sha(a.ledger)}}}

    Z = np.load(a.ledger, allow_pickle=False)
    off = Z["off"].astype(np.int64)
    ft, rate, zi = Z["ft"].astype(np.int64), np.asarray(Z["rate"]), np.asarray(Z["zip_iv"], np.float64)
    src = np.asarray(Z["src"])
    syms = [str(s) for s in Z["symbols"]]
    cut = int(Z["cut"])
    rec["ledger"] = {"n_events": int(ft.size), "n_symbols": len(syms), "cut": cut,
                     "cut_utc": datetime.datetime.utcfromtimestamp(cut).strftime("%Y-%m-%dT%H:%MZ"),
                     "src_counts": {int(k): int(v) for k, v in
                                    collections.Counter(src.tolist()).most_common()},
                     "zip_iv_nan": int((~np.isfinite(zi)).sum())}

    reasons = collections.Counter()
    by_year = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    n_events = n_compared = 0
    k_hist = collections.Counter()

    for j in range(len(syms)):
        b, e = off[j], off[j + 1]
        if e <= b:
            continue
        t = ft[b:e]
        z_ = zi[b:e]
        s_ = src[b:e]
        prev = None
        for k in range(e - b):
            n_events += 1
            nc_iv = None if prev is None else snap_interval(int(t[k]) - int(prev))
            r_iv = float(z_[k]) if np.isfinite(z_[k]) else None
            prev = int(t[k])
            agree = (nc_iv is None and r_iv is None) or (
                nc_iv is not None and r_iv is not None and nc_iv == r_iv)
            n_compared += 1
            if agree:
                continue
            if k == 0:
                why = "iii_first_event"
            elif r_iv is None:
                why = "ii_researcher_iv_absent"
            elif nc_iv is not None and r_iv > 0 and abs(nc_iv / r_iv - round(nc_iv / r_iv)) < 1e-9 \
                    and round(nc_iv / r_iv) >= 2:
                why = "i_missing_settlement"
                k_hist[int(round(nc_iv / r_iv))] += 1
            else:
                why = "iv_other"
            reasons[why] += 1
            yr = datetime.datetime.utcfromtimestamp(int(t[k])).year
            by_year[why][yr] += 1
            if len(examples[why]) < 3:
                examples[why].append({
                    "symbol": syms[j],
                    "ft": int(t[k]),
                    "utc": datetime.datetime.utcfromtimestamp(int(t[k])).strftime("%Y-%m-%dT%H:%MZ"),
                    "prev_gap_hours": (None if k == 0 else round((int(t[k]) - int(t[k - 1])) / 3600.0, 4)),
                    "researcher_zip_iv": r_iv, "nc_snap_interval": nc_iv,
                    "src": int(s_[k]), "rate": float(rate[b + k]),
                    "after_cut": bool(int(t[k]) > cut)})

    total_dis = sum(reasons.values())
    rec["totals"] = {"events": n_events, "compared": n_compared, "disagreeing": total_dis,
                     "pct_disagreeing": 100.0 * total_dis / max(1, n_compared)}
    rec["by_reason"] = {k: {"count": v, "pct_of_events": 100.0 * v / max(1, n_compared),
                            "pct_of_disagreements": 100.0 * v / max(1, total_dis),
                            "by_year": {str(y): c for y, c in sorted(by_year[k].items())}}
                        for k, v in reasons.most_common()}
    rec["missing_settlement_multiples"] = {str(k): v for k, v in sorted(k_hist.items())}
    rec["examples"] = {k: v for k, v in examples.items()}

    # RED CONTROL: the classification must be exhaustive (the four reasons must sum to the
    # disagreement count) and non-degenerate (more than one reason must actually occur, otherwise
    # the split carries no information).
    ctrl = {"reasons_sum": sum(reasons.values()), "disagreeing": total_dis,
            "exhaustive": sum(reasons.values()) == total_dis,
            "n_distinct_reasons_seen": len([k for k, v in reasons.items() if v > 0]),
            "snap_interval_selftest": {
                "3600s->1h": snap_interval(3600), "7200s->2h": snap_interval(7200),
                "28800s->8h": snap_interval(28800), "90000s(25h)->None": snap_interval(90000),
                "0s->None": snap_interval(0), "tie_10800s(3h)->larger": snap_interval(10800)}}
    st = ctrl["snap_interval_selftest"]
    ctrl["snap_interval_ok"] = (st["3600s->1h"] == 1.0 and st["7200s->2h"] == 2.0
                                and st["28800s->8h"] == 8.0 and st["90000s(25h)->None"] is None
                                and st["0s->None"] is None and st["tie_10800s(3h)->larger"] == 4.0)
    ctrl["baseline_green"] = bool(ctrl["exhaustive"] and ctrl["snap_interval_ok"]
                                  and ctrl["n_distinct_reasons_seen"] > 1)
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = ("red control: classification not exhaustive, snap_interval reimplementation "
                      "wrong, or only one reason present (no information in the split)")

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"IV_SOURCE_CENSUS VERDICT={rec['verdict']}")
    print(f"  red control: exhaustive={ctrl['exhaustive']} snap_interval_ok={ctrl['snap_interval_ok']} "
          f"distinct_reasons={ctrl['n_distinct_reasons_seen']}")
    t = rec["totals"]
    print(f"  events {t['events']}  disagreeing {t['disagreeing']}  = {t['pct_disagreeing']:.4f}% "
          f"(prior measurement: about 0.23%)")
    for k, d in rec["by_reason"].items():
        print(f"   {k:26s} {d['count']:8d}  {d['pct_of_events']:.4f}% of events  "
              f"{d['pct_of_disagreements']:5.1f}% of disagreements")
    if rec["missing_settlement_multiples"]:
        print(f"   gap multiples k (nc/res): {rec['missing_settlement_multiples']}")
    for k, exs in rec["examples"].items():
        for ex in exs[:2]:
            print(f"   e.g. {k:24s} {ex['utc']} {ex['symbol']:12s} gap_h={ex['prev_gap_hours']} "
                  f"res_zip_iv={ex['researcher_zip_iv']} nc_snap={ex['nc_snap_interval']} "
                  f"src={ex['src']} after_cut={ex['after_cut']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
