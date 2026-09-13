#!/usr/bin/env python3
"""t7_probe_c_survivorship.py — PROBE C: can delisted Korean KRW markets be recovered from public keyless fallbacks?
C1 Upbit web-chart CDN (unofficial, undocumented): crix-api-cdn.upbit.com/v1/crix/candles/days?code=CRIX.UPBIT.KRW-<X>
C2 CryptoCompare keyless histoday/histohour with e=Upbit / e=Bithumb (third-party aggregator; ToS require a key for sustained use)
Controls: a currently listed market (BTC, positive) and a never-existed code (negative). ≤ 16 requests total. Logged; no prices printed."""
import sys, os, json, time, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_probe_c.jsonl"
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "C1_upbit_crix": {}, "C2_cryptocompare": {}}
def summarize(st, body, js):
    rec = {"status": st, "body_len": len(body), "type": type(js).__name__}
    if isinstance(js, list):
        rec["n"] = len(js)
        if js and isinstance(js[0], dict):
            rec["keys"] = sorted(js[0].keys())[:20]
            for k in ("candleDateTime", "candle_date_time_utc", "candleDateTimeKst"):
                if k in js[0]: rec["newest_" + k] = js[0][k]; rec["oldest_" + k] = js[-1][k]
    elif isinstance(js, dict):
        rec["top_keys"] = sorted(js.keys())[:10]
        rec["Response"] = js.get("Response"); rec["Message"] = str(js.get("Message"))[:160]
        d = js.get("Data")
        if isinstance(d, dict) and isinstance(d.get("Data"), list):
            rows = d["Data"]; nz = [r for r in rows if (r.get("volumefrom") or r.get("volumeto"))]
            rec["n_rows"] = len(rows); rec["n_rows_nonzero_volume"] = len(nz)
            if nz: rec["first_nonzero_utc"] = time.strftime("%Y-%m-%d", time.gmtime(nz[0]["time"])); rec["last_nonzero_utc"] = time.strftime("%Y-%m-%d", time.gmtime(nz[-1]["time"]))
    if st != 200 or (not isinstance(js, (list, dict))): rec["body_head"] = body[:200].decode("utf-8", "replace")
    return rec
for mk in ("KRW-BTC", "KRW-LUNA", "KRW-WEMIX", "KRW-ZZZNOTACOIN"):
    for extra in ("", "&to=2022-05-01T00:00:00Z"):
        url = f"https://crix-api-cdn.upbit.com/v1/crix/candles/days?code=CRIX.UPBIT.{mk}&count=5{extra}"
        st, hdr, body, js = H.get_json(url, LOG, f"crix_{mk}")
        out["C1_upbit_crix"][mk + (" to=2022-05-01" if extra else " latest")] = summarize(st, body, js)
toTs = calendar.timegm((2022, 6, 1, 0, 0, 0))
for e, fsym in (("Upbit", "BTC"), ("Upbit", "LUNA"), ("Bithumb", "LUNA"), ("Upbit", "ZZZNOTACOIN")):
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={fsym}&tsym=KRW&e={e}&limit=60&toTs={toTs}"
    st, hdr, body, js = H.get_json(url, LOG, f"cc_{e}_{fsym}")
    out["C2_cryptocompare"][f"{e}:{fsym}/KRW histoday to 2022-06-01"] = summarize(st, body, js)
json.dump(out, open(T7 + "/receipts/PROBE_C_survivorship.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
