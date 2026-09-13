#!/usr/bin/env python3
"""t7_probe_a2_tsfield.py — PROBE A2: where does the candle `timestamp` field fall relative to [open, open+unit)?
Hypotheses: (i) last-trade time (always inside); (ii) record-update time (can exceed close => late revision risk).
Also re-reads the same closed window twice ~70 s apart to detect revisions of already-closed candles. Logged; no prices printed."""
import sys, os, json, time, calendar, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_probe_a2.jsonl"
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso()}
def fetch(v, unit, market, extra=""):
    b = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}[v]
    st, hdr, body, js = H.get_json(f"{b}/v1/candles/minutes/{unit}?market={market}&count=200{extra}", LOG, f"{v}_{market}_m{unit}")
    assert st == 200 and isinstance(js, list), (v, unit, market, st, body[:200])
    return js
res = {}
for v in ("upbit", "bithumb"):
    for unit in (60, 1):
        for market in ("KRW-BTC", "KRW-XRP", "KRW-USDT"):
            js = fetch(v, unit, market)
            offs = []
            for c in js:
                o = ep(c["candle_date_time_utc"]) * 1000
                offs.append((c["timestamp"] - o) / 1000.0)
            outside = [(js[k]["candle_date_time_utc"], round(offs[k], 3)) for k in range(len(js)) if not (0 <= offs[k] < unit * 60)]
            res[f"{v}_{market}_m{unit}"] = {"n": len(js), "n_outside": len(outside), "outside_examples_open_utc_and_ts_minus_open_s": outside[:8],
                                           "max_ts_minus_open_s": round(max(offs), 3), "min_ts_minus_open_s": round(min(offs), 3),
                                           "newest_open_utc": js[0]["candle_date_time_utc"]}
out["A2_ts_field"] = res
# revision check: fetch closed 60m candles for KRW-BTC twice ~70 s apart; compare all fields of candles with open <= now-2h
rev = {}
first = {v: fetch(v, 60, "KRW-BTC") for v in ("upbit", "bithumb")}
time.sleep(70)
for v in ("upbit", "bithumb"):
    second = fetch(v, 60, "KRW-BTC")
    a = {c["candle_date_time_utc"]: c for c in first[v]}; b = {c["candle_date_time_utc"]: c for c in second}
    cutoff = time.time() - 2 * 3600
    common = [k for k in a if k in b and ep(k) < cutoff]
    diff = [k for k in common if a[k] != b[k]]
    rev[v] = {"n_closed_common": len(common), "n_changed": len(diff), "changed_examples": diff[:5]}
out["A2_revision_70s"] = rev
json.dump(out, open(T7 + "/receipts/PROBE_A2_tsfield.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
