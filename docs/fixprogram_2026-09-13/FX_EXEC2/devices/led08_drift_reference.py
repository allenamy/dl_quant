#!/usr/bin/python3
"""LED-08 drift reference builder (offline, read-only, no credentials, no venue).

WHAT IT PRODUCES. The frozen reference levels that `config/cost_drift_reference.json` pins, measured on a ledger COPY
over a named window, **in the report's own caliber**, plus the current trailing comparison and the fee-only economic
translation of the drift. It never writes to a ledger.

WHY IT IMPORTS THE READER INSTEAD OF RE-IMPLEMENTING IT. A pinned number that was computed by a second implementation
can drift from the reader that consumes it and nothing would notice. This device imports the executor tree's own
`ops/anchor_report.order_facts` and `live/pilot_log.anchor_series`, and records the sha256 of every file it imported,
so the pinned level is by construction the number the report computes. (`judge_device_must_outlive_verdict`.)

CALIBER — DECLARED, NOT ASSUMED. Two different "maker share" numbers exist for this book and they are NOT the same
quantity:
  · X-COST RESULT_X_COST.md T1 reports M/(M+T) by the fill-level `venue_maker_flag` over fills de-duplicated on
    (symbol, trade_id), pooled by notional over a period. Its S1a maker share is 93.1 % (⇒ taker 6.9 %).
  · ops/anchor_report.order_facts reports, per anchor, Σ|filled_notional| of order rows whose `order_type` is
    `topup_taker`, over Σ|filled_notional| of all order rows of that anchor. A maker order row that the venue filled
    as taker (from_reject MARKET, chase IOC) stays `order_type == "maker"` here and is NOT counted.
The reference this device pins is the SECOND one, because that is the quantity the warning judges. The X-COST number
is carried in the receipt for cross-reference only and is never the pinned value.

POSITIVE CONTROL ON THE POPULATION. The eligibility rule (traded slot, not halted, not a rebuild) is the report's
trailing-band rule, applied to a fixed window instead of a trailing one. On the S1a window it must select exactly the
27 anchors / 0 halted / 0 rebuild that X-COST's independently-written device selected (RESULT_X_COST.md T1). The
device asserts an expected population passed as a parameter; a mismatch is a hard failure, not a note.

THRESHOLD. Reported, not decided here: |median_now - median_ref| > k · 1.4826 · MAD_ref (k = 3), needing at least
`min_n` eligible anchors on BOTH sides. The economic column is the fee-only translation of the drift,
  Δ(taker share) × (taker_fee_bps - maker_fee_bps) × median(filled_notional / realized_gross),
in bps per anchor per gross, so it can be compared with the frozen K2 book-level δ of 0.05. It is REPORTED beside the
verdict and is deliberately NOT part of the trip condition; see the report for why.

Usage:
  /usr/bin/python3 led08_drift_reference.py <executor_tree> <pilot_log_root_copy> <receipt.json>
"""
import calendar, hashlib, json, os, statistics, sys, time
import collections

TREE, PLOG, RECEIPT = sys.argv[1:4]
sys.path.insert(0, os.path.join(TREE, "live"))
sys.path.insert(0, os.path.join(TREE, "ops"))
import pilot_log as PL          # noqa: E402
import anchor_report as AR      # noqa: E402

K_MADS = 3.0
MAD_TO_SIGMA = 1.4826
MIN_N = 12
MAKER_FEE_BPS = 2.00            # config/book.json fee schedule, unchanged through both windows (X-COST §1)
TAKER_FEE_BPS = 5.00
DELTA_BPS_ANCHOR_GROSS = 0.05   # FIXPROGRAM §4.1, book-level equivalence band (K2), frozen before this measurement

# (name, first nominal slot inclusive, last nominal slot inclusive, expected (n_slots, n_halted, n_rebuild) or None)
# NAMES ARE NOT X-COST'S. Only the first window is X-COST's S1a and only its expected population is an INDEPENDENT
# control (RESULT_X_COST.md T1: 27 anchors / 0 halted / 0 rebuild, written by a device I did not write). The second
# window is MINE; X-COST's "S3" is a DIFFERENT window (34 anchors / 6 halted / 2 rebuild, from 09-05 12Z), so it is
# named LAST5D_ here and its expected population is my own earlier read, i.e. a regression pin, NOT a control.
WINDOWS = [
    ("S1a_2026-08-28_2026-09-01T12Z", "2026-08-28T00:00:00Z", "2026-09-01T12:00:00Z", (27, 0, 0)),
    ("LAST5D_2026-09-08_2026-09-13T12Z", "2026-09-08T00:00:00Z", "2026-09-13T12:00:00Z", (27, 0, 2)),
]


def sha(p):
    raw = open(p, "rb").read()
    assert len(raw) == os.stat(p).st_size, f"short read {p}"
    return hashlib.sha256(raw).hexdigest()


def epoch(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def band(values, k=K_MADS, min_n=MIN_N):
    v = [x for x in values if x is not None]
    if len(v) < min_n:
        return {"n": len(v), "median": None, "mad": None, "threshold": None, "min": None, "max": None}
    med = statistics.median(v)
    mad = statistics.median([abs(x - med) for x in v])
    return {"n": len(v), "median": med, "mad": mad, "threshold": med + k * MAD_TO_SIGMA * mad,
            "min": min(v), "max": max(v)}


anchors, orders_by_rid, day_shas = [], collections.defaultdict(list), {}
for d in sorted(x for x in os.listdir(PLOG) if x.isdigit() and len(x) == 8):
    for fn, sink in (("anchors.jsonl", None), ("orders.jsonl", None)):
        p = os.path.join(PLOG, d, fn)
        if not os.path.exists(p):
            continue
        day_shas[f"{d}/{fn}"] = sha(p)
        for r in PL._read_jsonl(p):
            if fn == "anchors.jsonl":
                anchors.append(r)
            else:
                orders_by_rid[r.get("rebalance_id")].append(r)

S = PL.anchor_series(anchors)
rebuild = set(S["rebuild_nominal_ts"])
slots = list(zip(S["nominal_ts"], S["series"]))

out_windows = {}
for name, lo_s, hi_s, expect in WINDOWS:
    lo, hi = epoch(lo_s), epoch(hi_s)
    taker, ngabs, turn = [], [], []
    n_slots = n_halted = n_rebuild = 0
    per_anchor = []
    for t, r in slots:
        if not (lo <= t <= hi):
            continue
        n_slots += 1
        halted = bool(r.get("opening_halted"))
        is_reb = t in rebuild
        n_halted += halted
        n_rebuild += is_reb
        if halted or is_reb:
            continue
        f = AR.order_facts(orders_by_rid.get(r.get("rebalance_id"), []))
        ng = AR._fin(r.get("net_over_gross"))
        rg = AR._fin(r.get("realized_gross"))
        ts = f["taker_share"]
        na = None if ng is None else abs(ng)
        tr = (f["filled_known_usdt"] / rg) if rg else None
        taker.append(ts); ngabs.append(na); turn.append(tr)
        per_anchor.append({"nominal_ts": t, "rebalance_id": r.get("rebalance_id"), "taker_share": ts,
                           "net_over_gross_abs": na, "filled_over_realized_gross": tr,
                           "n_unknown_fill": f["n_unknown_fill"]})
    got = (n_slots, n_halted, n_rebuild)
    assert expect is None or got == expect, f"{name}: population {got} != expected {expect}"
    out_windows[name] = {
        "first_nominal_ts_inclusive": lo, "last_nominal_ts_inclusive": hi,
        "first_utc": lo_s, "last_utc": hi_s,
        "n_slots_in_window": n_slots, "n_halted": n_halted, "n_rebuild": n_rebuild,
        "n_eligible": len(taker), "expected_population": list(expect) if expect else None,
        "taker_share": band(taker), "net_over_gross_abs": band(ngabs),
        "filled_over_realized_gross": band(turn, min_n=1),
        "n_taker_share_none": sum(1 for x in taker if x is None),
        "per_anchor": per_anchor,
    }

REF, XREF = WINDOWS[0][0], WINDOWS[1][0]

# THE OPERATIVE CURRENT SIDE is not a window I chose: it is the report's own trailing band, computed by the report's
# own history_facts as the next report run would compute it (slots strictly before the latest slot + one anchor, i.e.
# the last <=42 eligible slots inclusive of the latest). The fixed window above is cross-reference only.
LATEST = max(t for t, _ in slots)
CURBAND = AR.history_facts(anchors, orders_by_rid, LATEST + 14400)
current = {"as_of_latest_nominal_ts": LATEST, "n_slots_in_band": len(CURBAND["slots"]),
           "first_slot": (CURBAND["slots"][0] if CURBAND["slots"] else None),
           "last_slot": (CURBAND["slots"][-1] if CURBAND["slots"] else None),
           "taker_share": CURBAND["taker"], "net_over_gross_abs": CURBAND["net_over_gross_abs"]}

drift = {}
for key in ("taker_share", "net_over_gross_abs"):
    ref, cur = out_windows[REF][key], current[key]
    thr = (None if ref["mad"] is None else K_MADS * MAD_TO_SIGMA * ref["mad"])
    d = (None if (ref["median"] is None or cur["median"] is None) else cur["median"] - ref["median"])
    drift[key] = {
        "reference_median": ref["median"], "current_median": cur["median"], "drift": d,
        "threshold": thr, "k_mads": K_MADS, "mad_reference": ref["mad"],
        "min_n": MIN_N, "n_reference": ref["n"], "n_current": cur["n"],
        "enough_on_both_sides": (ref["n"] >= MIN_N and cur["n"] >= MIN_N),
        "warn": (d is not None and thr is not None and abs(d) > thr
                 and ref["n"] >= MIN_N and cur["n"] >= MIN_N),
        "threshold_alternative_se_of_median": (
            None if ref["mad"] is None or ref["n"] < 2 else
            K_MADS * 1.2533 * (MAD_TO_SIGMA * ref["mad"]) / (ref["n"] ** 0.5)),
    }

turn_med = out_windows[XREF]["filled_over_realized_gross"]["median"]
dt_taker = drift["taker_share"]["drift"]
drift["taker_share"]["economic_fee_only"] = {
    "formula": "drift x (taker_fee_bps - maker_fee_bps) x median(filled_notional / realized_gross)",
    "maker_fee_bps": MAKER_FEE_BPS, "taker_fee_bps": TAKER_FEE_BPS,
    "median_filled_over_realized_gross_current": turn_med,
    "turnover_source_window": XREF,
    "bps_per_anchor_per_gross": (None if (dt_taker is None or turn_med is None)
                                 else dt_taker * (TAKER_FEE_BPS - MAKER_FEE_BPS) * turn_med),
    "delta_bps_per_anchor_per_gross": DELTA_BPS_ANCHOR_GROSS,
    "note": "REPORTED, never part of the trip condition; see REPORT_FX_EXEC2 LED-08 drift.",
}

rec = {
    "device": os.path.basename(__file__),
    "device_sha256": sha(os.path.abspath(__file__)),
    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "executor_tree": TREE,
    "imported_file_sha256": {rel: sha(os.path.join(TREE, rel))
                             for rel in ("ops/anchor_report.py", "live/pilot_log.py", "live/cost_buckets.py")},
    "ledger_root": PLOG,
    "n_ledger_files_read": len(day_shas),
    "ledger_file_sha256": day_shas,
    "caliber": {
        "name": "anchor_report_order_type_topup_taker_over_filled",
        "taker_share": "sum |filled_notional| of order rows with order_type == 'topup_taker' / sum |filled_notional| "
                       "of all order rows of the anchor; None when any row's filled_notional is unreadable",
        "net_over_gross_abs": "abs(anchors row net_over_gross)",
        "eligibility": "pilot_log.anchor_series traded external-era slot, not opening_halted, not a rebuild slot",
        "NOT_this_caliber": "X-COST RESULT_X_COST.md T1 maker share = M/(M+T) by fill-level venue_maker_flag over "
                            "fills de-duplicated on (symbol, trade_id), pooled by notional over the period",
        "x_cost_cross_reference": {"S1a_maker_share_pooled": 0.931, "S1a_maker_share_median_anchor": 0.950,
                                   "S3_ex_rebuild_maker_share_pooled": 0.739, "S3_maker_share_median_anchor": 0.772,
                                   "source": "docs/fixprogram_2026-09-13/X_COST/RESULT_X_COST.md T1"},
    },
    "reference_window": REF, "cross_reference_window": XREF,
    "current_side": "ops/anchor_report.history_facts trailing band as of the latest ledger slot",
    "windows": out_windows,
    "current": current,
    "drift": drift,
}
with open(RECEIPT, "w") as f:
    json.dump(rec, f, ensure_ascii=False, indent=1, sort_keys=False)

print(f"device_sha256 {rec['device_sha256'][:16]}  ledger files {len(day_shas)}")
for w in (REF, XREF):
    o = out_windows[w]
    print(f"{w}: slots {o['n_slots_in_window']} halted {o['n_halted']} rebuild {o['n_rebuild']} "
          f"eligible {o['n_eligible']}")
    for key in ("taker_share", "net_over_gross_abs"):
        b = o[key]
        print(f"   {key:<20} n {b['n']:>3}  median {b['median']!r}  MAD {b['mad']!r}")
print(f"TRAILING BAND as of {current['as_of_latest_nominal_ts']} : {current['n_slots_in_band']} slots "
      f"{current['first_slot']}..{current['last_slot']}")
for key in ("taker_share", "net_over_gross_abs"):
    b = current[key]
    print(f"   {key:<20} n {b['n']:>3}  median {b['median']!r}  MAD {b['mad']!r}")
for key, d in drift.items():
    print(f"DRIFT {key:<20} ref {d['reference_median']!r} -> now {d['current_median']!r}  "
          f"drift {d['drift']!r}  threshold {d['threshold']!r}  WARN {d['warn']}")
e = drift["taker_share"]["economic_fee_only"]
print(f"fee-only economic translation {e['bps_per_anchor_per_gross']!r} bps/anchor/gross "
      f"vs frozen delta {e['delta_bps_per_anchor_per_gross']}")
print(f"receipt -> {RECEIPT}")
