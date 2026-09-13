#!/usr/bin/python3
"""LED-04 amendment builder (offline, read-only, no credentials): for every daily_nav row of a ledger COPY, recompute the
realised split by income type and asset from guard_twin's income ledger (5-field key, closes to the wallet within 0.001
USDT), over the same window the carrier reads: [UTC 00:00 of the row's day, nav_ts]. Rows written BEFORE the E-0909-H
fix (no `realised_by_type_asset` key) get an AMENDMENT record; rows written after it are the POSITIVE CONTROL (their own
per-asset split must equal the income-ledger recomputation). Nothing is rewritten; output = one JSONL of amendment
records + a receipt JSON with the control. Usage:
  /usr/bin/python3 led04_daily_nav_amendment.py <pilot_log_root_copy> <guard_twin_income.jsonl> <out_amendments.jsonl> <receipt.json>"""
import calendar, collections, hashlib, json, os, sys, time
ROOT, INCOME, OUT, RECEIPT = sys.argv[1:5]
TYPES = ("REALIZED_PNL", "COMMISSION", "FUNDING_FEE")
TOL = 1e-6
raw_inc = open(INCOME, "rb").read(); assert len(raw_inc) == os.stat(INCOME).st_size
inc_sha = hashlib.sha256(raw_inc).hexdigest()
inc = [json.loads(l) for l in raw_inc.splitlines() if l.strip()]
inc.sort(key=lambda r: r["time"])
times = [r["time"] for r in inc]
import bisect
def split(t0_ms, t1_ms):
    i, j = bisect.bisect_left(times, t0_ms), bisect.bisect_right(times, t1_ms)
    bta = collections.defaultdict(lambda: collections.defaultdict(float)); n = 0
    for r in inc[i:j]:
        if r["type"] in TYPES:
            bta[r["type"]][r["asset"]] += float(r["income"]); n += 1
    return {t: dict(v) for t, v in bta.items()}, n, (inc[j - 1]["time"] if j > i else None)
def fixed(d): return {t: {a: round(v, 8) for a, v in sorted(av.items())} for t, av in sorted(d.items())}
amend, ctrl = [], []
for day in sorted(d for d in os.listdir(ROOT) if d.isdigit() and len(d) == 8):
    p = os.path.join(ROOT, day, "daily_nav.jsonl")
    if not os.path.exists(p):
        continue
    raw = open(p, "rb").read(); assert len(raw) == os.stat(p).st_size
    t0 = calendar.timegm(time.strptime(day, "%Y%m%d")) * 1000
    for i, line in enumerate(raw.splitlines(keepends=True)):
        if not line.strip():
            continue
        r = json.loads(line)
        nts = r.get("nav_ts")
        if nts is None:
            continue
        t1 = int(float(nts) * 1000)
        bta, n, last_t = split(t0, t1)
        usdt = {t: bta.get(t, {}).get("USDT", 0.0) for t in TYPES}
        non_usdt = {t: {a: v for a, v in bta.get(t, {}).items() if a != "USDT"} for t in TYPES}
        rec_bt = r.get("realised_by_type") or {}
        base = {"day": day, "line": i + 1, "row_sha256": hashlib.sha256(line).hexdigest(), "nav_ts": nts,
                "window_ms": [t0, t1], "n_income_rows": n}
        if "realised_by_type_asset" in r:
            ctrl.append(dict(base, recorded=fixed(r["realised_by_type_asset"]), income_ledger=fixed(bta),
                             equal=fixed(r["realised_by_type_asset"]) == {t: v for t, v in fixed(bta).items() if v}
                             or all(abs((r["realised_by_type_asset"].get(t) or {}).get(a, 0.0) - (bta.get(t) or {}).get(a, 0.0)) <= TOL
                                    for t in TYPES for a in set((r["realised_by_type_asset"].get(t) or {})) | set(bta.get(t) or {}))))
            continue
        amend.append(dict(base, kind="daily_nav_realised_split_amendment",
                          reason=("written before the E-0909-H carrier fix (b681ca5, 2026-09-12 06:05Z): income rows were de-duplicated on "
                                  "tranId alone, which dropped one of each COMMISSION/REALIZED_PNL twin pair, and BNB commission amounts "
                                  "were summed into the USDT figure"),
                          recorded={"realised_pnl": r.get("realised_pnl"), "realised_by_type": rec_bt,
                                    "realised_truncated": r.get("realised_truncated")},
                          amended={"realised_by_type_asset": fixed(bta),
                                   "realised_usdt_by_type": {t: round(v, 8) for t, v in usdt.items()},
                                   "realised_pnl_usdt": round(sum(usdt.values()), 8),
                                   "non_usdt_unconverted": {t: {a: round(v, 8) for a, v in av.items()} for t, av in non_usdt.items() if av}},
                          delta_recorded_minus_amended_usdt={t: (None if rec_bt.get(t) is None else round(float(rec_bt[t]) - usdt[t], 8)) for t in TYPES},
                          source={"income_ledger": "guard_twin state/income.jsonl", "income_sha256": inc_sha, "income_rows": len(inc),
                                  "key": "(tranId, incomeType, symbol, time, income)", "window": "[UTC 00:00 of day, nav_ts]",
                                  "caliber_note": ("the ledger holds every row the venue published, including any published after nav_ts "
                                                   "for times <= nav_ts; the carrier read at nav_ts may not have seen those")}))
with open(OUT, "w") as f:
    for a in amend:
        f.write(json.dumps(a, sort_keys=True) + "\n")
out_sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
res = {"income_sha256": inc_sha, "income_rows": len(inc), "n_amendments": len(amend), "amendments_sha256": out_sha,
       "control_rows": len(ctrl), "control_equal": sum(1 for c in ctrl if c["equal"]), "control": ctrl,
       "first_amended": (amend[0]["day"], amend[0]["line"]) if amend else None, "last_amended": (amend[-1]["day"], amend[-1]["line"]) if amend else None,
       "sum_abs_delta_usdt_by_type": {t: round(sum(abs(a["delta_recorded_minus_amended_usdt"][t] or 0) for a in amend), 6) for t in TYPES}}
json.dump(res, open(RECEIPT, "w"), indent=1)
print("LED04_AMEND n", len(amend), "sha", out_sha[:16], "control", res["control_equal"], "/", len(ctrl), "sum|delta|", res["sum_abs_delta_usdt_by_type"])
