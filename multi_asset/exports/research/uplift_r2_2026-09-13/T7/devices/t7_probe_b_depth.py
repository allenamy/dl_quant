#!/usr/bin/env python3
"""t7_probe_b_depth.py — PROBE B: history depth (binary search for the earliest candle), delisted-market queryability,
KRW-USDT market start, zero-trade (gap) convention. Logged. No price-derived numbers computed or printed.
`to` spelling per PROBE A: Upbit ISO '...Z' (UTC); Bithumb naive local KST (a 'Z' or '+09:00' spelling returns 200 + [] silently).
Binary-search invariant: pred(T) = 'a candle with open < T exists' is monotone; any non-200 aborts the search (never read as empty)."""
import sys, os, json, time, calendar, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_probe_b.jsonl"
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def to_param(v, t):
    return urllib.parse.quote(iso(t) + "Z") if v == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
def unit_path(unit): return "days" if unit == "days" else f"minutes/{unit}"
class SearchError(Exception): pass
def one(v, market, unit, t=None, tag=""):
    url = f"{BASE[v]}/v1/candles/{unit_path(unit)}?market={market}&count=1" + (f"&to={to_param(v, t)}" if t is not None else "")
    st, hdr, body, js = H.get_json(url, LOG, tag)
    if st != 200 or not isinstance(js, list):
        raise SearchError(json.dumps({"status": st, "url": url, "body_head": body[:200].decode("utf-8", "replace")}))
    return js[0] if js else None
def earliest(v, market, unit, lo=calendar.timegm((2013, 6, 1, 0, 0, 0)), step=None):
    hi = int(time.time()); step = step or (86400 if unit == "days" else 60 * int(unit))
    top = one(v, market, unit, None, f"{v}_{market}_{unit}_latest")
    if top is None: return {"latest": None, "earliest": None, "n_requests": 1}
    if one(v, market, unit, lo, f"{v}_{market}_{unit}_lo") is not None:
        return {"latest": top["candle_date_time_utc"], "earliest": "BEFORE_LO", "lo": iso(lo)}
    n = 2; best = top
    while hi - lo > step:
        mid = lo + ((hi - lo) // 2 // step) * step
        if mid <= lo: mid = lo + step
        c = one(v, market, unit, mid, f"{v}_{market}_{unit}_bs"); n += 1
        if c is None: lo = mid
        else: hi = mid; best = c
    return {"latest": top["candle_date_time_utc"], "earliest": best["candle_date_time_utc"], "n_requests": n}
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "log": os.path.basename(LOG), "venues": {}}
DELISTED_CANDIDATES = ["LUNA", "WEMIX", "SRM", "PCI", "NU", "BTT", "XEM", "WAVES", "OMG", "BTG", "ANT", "KEEP", "DAWN", "LOOM", "MFT", "STPT", "EMC2", "IGNIS", "DGB", "LSK", "ZZZNOTACOIN"]
for v in BASE:
    R = out["venues"][v] = {}
    st, hdr, body, js = H.get_json(f"{BASE[v]}/v1/market/all?isDetails=true", LOG, f"{v}_market_all")
    assert st == 200 and isinstance(js, list), (v, st)
    listed = set(m["market"] for m in js)
    # B1 history depth KRW-BTC
    for unit in ("days", 60, 1):
        try: R[f"B1_KRW-BTC_{unit}"] = earliest(v, "KRW-BTC", unit)
        except SearchError as e: R[f"B1_KRW-BTC_{unit}"] = {"ERROR": str(e)}
    # B2 KRW-USDT start (60m and days)
    for unit in ("days", 60):
        try: R[f"B2_KRW-USDT_{unit}"] = earliest(v, "KRW-USDT", unit, lo=calendar.timegm((2016, 1, 1, 0, 0, 0)))
        except SearchError as e: R[f"B2_KRW-USDT_{unit}"] = {"ERROR": str(e)}
    R["B2_KRW-USDT_in_market_all"] = "KRW-USDT" in listed
    # B3 delisted-market queryability
    B3 = R["B3_delisted_candidates"] = {}
    for base in DELISTED_CANDIDATES:
        mk = "KRW-" + base
        url = f"{BASE[v]}/v1/candles/days?market={mk}&count=1"
        st, hdr, body, js = H.get_json(url, LOG, f"{v}_{mk}_delist_probe")
        rec = {"in_market_all_now": mk in listed, "status": st, "n": len(js) if isinstance(js, list) else None,
               "last_day_open_utc": js[0]["candle_date_time_utc"] if st == 200 and isinstance(js, list) and js else None,
               "body_head": None if st == 200 else body[:200].decode("utf-8", "replace")}
        if rec["last_day_open_utc"] and not rec["in_market_all_now"]:
            try: rec["first_day"] = earliest(v, mk, "days", lo=calendar.timegm((2013, 6, 1, 0, 0, 0)))["earliest"]
            except SearchError as e: rec["first_day"] = {"ERROR": str(e)}
        B3[mk] = rec
    # B4 zero-trade convention: thinnest KRW market by 24h KRW turnover (ticker), count 60m and 1m candles over their span
    krw = sorted(m for m in listed if m.startswith("KRW-"))
    turn = {}
    for k in range(0, len(krw), 100):
        st, hdr, body, js = H.get_json(f"{BASE[v]}/v1/ticker?markets={','.join(krw[k:k+100])}", LOG, f"{v}_ticker_{k}")
        if st == 200 and isinstance(js, list):
            for t in js: turn[t["market"]] = t.get("acc_trade_price_24h")
        else:
            R.setdefault("B4_ticker_errors", []).append({"status": st, "body_head": body[:200].decode("utf-8", "replace")})
    thin = sorted((x for x in turn.items() if x[1] is not None), key=lambda x: x[1])[:3]
    B4 = R["B4_gaps"] = {"n_ticker": len(turn), "n_krw_listed": len(krw), "thinnest3": [m for m, _ in thin]}
    for mk, _ in thin:
        for unit in (60, 1):
            st, hdr, body, js = H.get_json(f"{BASE[v]}/v1/candles/minutes/{unit}?market={mk}&count=200", LOG, f"{v}_{mk}_gap_m{unit}")
            if st == 200 and isinstance(js, list) and js:
                opens = [ep(c["candle_date_time_utc"]) for c in js]
                span_units = (opens[0] - opens[-1]) // (unit * 60) + 1
                B4[f"{mk}_m{unit}"] = {"n_candles": len(js), "span_units": int(span_units), "missing_units_in_span": int(span_units - len(js)),
                                       "max_gap_units": int(max([(opens[i] - opens[i + 1]) // (unit * 60) for i in range(len(opens) - 1)] or [1])),
                                       "zero_volume_candles": sum(1 for c in js if not c.get("candle_acc_trade_volume"))}
            else:
                B4[f"{mk}_m{unit}"] = {"status": st, "n": len(js) if isinstance(js, list) else None}
json.dump(out, open(T7 + "/receipts/PROBE_B_depth.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
