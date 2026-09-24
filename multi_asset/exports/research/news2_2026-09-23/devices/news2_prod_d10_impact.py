#!/usr/bin/env python3
"""news2_prod_d10_impact.py -- how much does each production missing-settlement event move fund_ema, and for how long?

Material for the user's D10 ruling. `PROD_LEDGER_GAPS.json` found 41 events in the production ledger
tail where the gap is an integer multiple k>=2 of the previous cadence. This device measures the
CONSEQUENCE of each one on that name's fund_ema.

WHAT IS AND IS NOT DETERMINABLE FROM THE PRODUCTION LEDGER -- this bounds the whole device:
  The producer's own ledger stores iv = snap_interval(gap) (nc_contract.ingest_settlements L77). So the
  ledger contains NC's INFERRED interval, not an independent truth. Production therefore cannot tell us
  whether the exchange truly changed cadence or a settlement was missed.
  => This device computes a CONDITIONAL counterfactual: "IF a settlement was missed (i.e. the true
  interval stayed at the previous cadence), how far does the ema NC computed sit from the ema it would
  have had?" It does NOT claim the settlement was in fact missed.

TWO CHAINS, same loop body (feature_contract funding_state L80-88 == nc_contract ema_step L55-63):
  actual        the events as the ledger records them (iv = the snapped value)
  counterfactual the same events, but the flagged event's iv forced to the previous cadence
Reported per event: |delta| right after, the peak |delta|, and how many events / hours until |delta|
falls below 10% of its peak (the 3-day half life decays it).

READ-ONLY on ~/wide_shadow. Writes nothing there.
"""
import argparse, collections, datetime, hashlib, json, math, os, sys

SELF = os.path.realpath(__file__)
IV_GRID = (1.0, 2.0, 4.0, 8.0)
HALFLIFE_S = 3 * 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def snap_interval(dt_s):
    h = float(dt_s) / 3600.0
    if not (h > 0.0 and h <= 24.0):
        return None
    best, bd = None, None
    for g in IV_GRID:
        d = abs(g - h)
        if bd is None or d < bd or (d == bd and g > best):
            best, bd = g, d
    return best


def ema_chain(events):
    """events: [(ft, rate, iv)] -> list of ema after each event (None where reset)"""
    acc, prev, out = float("nan"), None, []
    for ft, rate, iv in events:
        if rate is None or not math.isfinite(float(rate)) or iv is None \
                or not math.isfinite(float(iv)) or float(iv) <= 0:
            acc, prev = float("nan"), None
            out.append(None)
            continue
        rn = float(rate) * 8.0 / float(iv)
        if prev is None:
            acc = rn
        else:
            decay = 2.0 ** (-float(int(ft) - int(prev)) / HALFLIFE_S)
            acc = decay * acc + (1.0 - decay) * rn
        prev = int(ft)
        out.append(acc)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aux", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable,
           "status": "CONDITIONAL_COUNTERFACTUAL_NOT_A_CLAIM_THAT_A_SETTLEMENT_WAS_MISSED",
           "source": {"path": a.aux, "sha256": sha(a.aux), "key": "ledger_tail"},
           "bound": ("the producer's ledger stores iv = snap_interval(gap), i.e. NC's own inference, "
                     "not an independent truth; production cannot distinguish a real cadence change "
                     "from a missed settlement. Everything below is conditional on 'a settlement was "
                     "missed'."),
           "loop_body": "feature_contract funding_state L80-88 == nc_contract ema_step L55-63"}

    lt = json.load(open(a.aux))["ledger_tail"]
    rows = []
    for sym, evs in lt.items():
        evs = [(int(e[0]), float(e[1]), (None if e[2] is None else float(e[2]))) for e in evs]
        for i in range(1, len(evs)):
            pft, _, piv = evs[i - 1]
            ft, _, iv = evs[i]
            if piv is None or piv <= 0:
                continue
            gap_h = (ft - pft) / 3600.0
            k = gap_h / piv
            if not (abs(k - round(k)) < 1e-9 and round(k) >= 2):
                continue
            actual = ema_chain(evs)
            cf_evs = list(evs)
            cf_evs[i] = (ft, evs[i][1], piv)          # force the flagged event back to the prior cadence
            cf = ema_chain(cf_evs)
            d = [None if (actual[j] is None or cf[j] is None) else abs(actual[j] - cf[j])
                 for j in range(len(evs))]
            tail = [(j, d[j]) for j in range(i, len(evs)) if d[j] is not None]
            if not tail:
                continue
            peak = max(v for _, v in tail)
            imm = d[i]
            thr = peak * 0.10
            n_ev_decay, hrs_decay = None, None
            for j, v in tail:
                if v <= thr and j > i:
                    n_ev_decay = j - i
                    hrs_decay = (evs[j][0] - ft) / 3600.0
                    break
            rows.append({
                "symbol": sym,
                "utc": datetime.datetime.utcfromtimestamp(ft).strftime("%Y-%m-%dT%H:%MZ"),
                "ft": ft, "prev_cadence_h": piv, "gap_h": gap_h, "k": int(round(k)),
                "nc_snapped_iv": snap_interval(ft - pft),
                "ratio_nc_over_prev_cadence": (None if snap_interval(ft - pft) is None
                                               else round(snap_interval(ft - pft) / piv, 4)),
                "ema_actual_after": actual[i], "ema_counterfactual_after": cf[i],
                "abs_delta_immediate": imm, "abs_delta_peak": peak,
                "events_until_10pct_of_peak": n_ev_decay,
                "hours_until_10pct_of_peak": hrs_decay,
                "n_events_after": len(evs) - i - 1})

    rows.sort(key=lambda r: -(r["abs_delta_peak"] or 0))
    rec["n_events_flagged"] = len(rows)
    rec["events"] = rows
    if rows:
        peaks = [r["abs_delta_peak"] for r in rows if r["abs_delta_peak"] is not None]
        hrs = [r["hours_until_10pct_of_peak"] for r in rows if r["hours_until_10pct_of_peak"] is not None]
        rec["summary"] = {
            "peak_abs_delta_max": max(peaks), "peak_abs_delta_median": sorted(peaks)[len(peaks) // 2],
            "hours_to_10pct_median": (sorted(hrs)[len(hrs) // 2] if hrs else None),
            "hours_to_10pct_max": (max(hrs) if hrs else None),
            "by_k": dict(collections.Counter(r["k"] for r in rows))}

    # RED CONTROL: forcing the iv to the value it already has must give zero delta; a real change must not.
    probe = [(0, 0.001, 4.0), (14400, 0.001, 4.0), (28800, 0.001, 4.0)]
    same = ema_chain(probe)
    same2 = ema_chain(list(probe))
    changed = ema_chain([(0, 0.001, 4.0), (14400, 0.001, 4.0), (28800, 0.001, 8.0)])
    ctrl = {"identical_inputs_zero_delta": all(abs(same[i] - same2[i]) == 0 for i in range(3)),
            "changed_iv_moves_ema": abs(changed[2] - same[2]) > 0,
            "snap_3h_is_4": snap_interval(10800) == 4.0}
    ctrl["baseline_green"] = all(ctrl.values())
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"PROD_D10_IMPACT VERDICT={rec['verdict']}  flagged {rec['n_events_flagged']}")
    print(f"  red control: {ctrl}")
    if rows:
        s = rec["summary"]
        print(f"  peak |delta ema|: max {s['peak_abs_delta_max']:.6g}  median {s['peak_abs_delta_median']:.6g}")
        print(f"  hours to 10% of peak: median {s['hours_to_10pct_median']}  max {s['hours_to_10pct_max']}")
        print(f"  by k: {s['by_k']}")
        print("  top 8 by peak |delta|:")
        for r in rows[:8]:
            print(f"   {r['utc']} {r['symbol']:14s} prev={r['prev_cadence_h']}h gap={r['gap_h']}h "
                  f"k={r['k']} nc_iv={r['nc_snapped_iv']} ratio={r['ratio_nc_over_prev_cadence']}  "
                  f"|d|imm={r['abs_delta_immediate']:.3e} peak={r['abs_delta_peak']:.3e} "
                  f"decay_to_10%={r['hours_until_10pct_of_peak']}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
