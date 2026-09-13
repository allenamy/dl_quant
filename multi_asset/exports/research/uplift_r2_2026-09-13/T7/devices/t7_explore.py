#!/usr/bin/env python3
"""t7_explore.py — first-contact shape probe (logged). Prints keys/timestamps only, no price-derived numbers."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_explore.jsonl"
def show(tag, url):
    st, hdr, body, js = H.get_json(url, LOG, tag)
    kind = type(js).__name__
    n = len(js) if isinstance(js, (list, dict)) else None
    first = js[0] if isinstance(js, list) and js else js
    keys = sorted(first.keys()) if isinstance(first, dict) else None
    print(f"[{tag}] {st} len={len(body)} kind={kind} n={n} rl={hdr.get('remaining-req')} keys={keys}")
    if st != 200: print("   body:", body[:300])
    return st, hdr, js
print("request utc", H.utcnow_iso())
st, hdr, js = show("upbit_market_all", "https://api.upbit.com/v1/market/all?isDetails=true")
if isinstance(js, list):
    krw = [m for m in js if m["market"].startswith("KRW-")]; print("  upbit KRW markets:", len(krw), "total", len(js)); print("  sample:", krw[0])
st, hdr, js = show("upbit_c60_latest", "https://api.upbit.com/v1/candles/minutes/60?market=KRW-BTC&count=3")
if isinstance(js, list):
    for c in js: print("  ", {k: c[k] for k in ("candle_date_time_utc", "candle_date_time_kst", "timestamp", "unit")})
st, hdr, js = show("bithumb_market_all", "https://api.bithumb.com/v1/market/all?isDetails=true")
if isinstance(js, list):
    krw = [m for m in js if m["market"].startswith("KRW-")]; print("  bithumb KRW markets:", len(krw), "total", len(js)); print("  sample:", krw[0])
st, hdr, js = show("bithumb_c60_latest", "https://api.bithumb.com/v1/candles/minutes/60?market=KRW-BTC&count=3")
if isinstance(js, list):
    for c in js: print("  ", {k: c.get(k) for k in ("candle_date_time_utc", "candle_date_time_kst", "timestamp", "unit")})
st, hdr, js = show("bithumb_public_candle_1h", "https://api.bithumb.com/public/candlestick/BTC_KRW/1h")
if isinstance(js, dict):
    d = js.get("data"); print("  status", js.get("status"), "rows", len(d) if isinstance(d, list) else None, "first", d[0][:1] if d else None, "last", d[-1][:1] if d else None)
print("hdr bithumb:", {k: v for k, v in hdr.items() if k in H.KEEP_HEADERS})
