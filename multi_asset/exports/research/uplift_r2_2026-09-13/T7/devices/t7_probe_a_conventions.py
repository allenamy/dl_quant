#!/usr/bin/env python3
"""t7_probe_a_conventions.py — PROBE A: candle timestamp convention and `to` parameter semantics, both venues (logged).
Facts extracted programmatically into receipts/PROBE_A_conventions.json. No price-derived numbers are computed."""
import sys, os, json, time, calendar, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_probe_a.jsonl"
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
def ep(s):  # 'YYYY-MM-DDTHH:MM:SS' (naive, as labelled) -> epoch seconds treating the label as UTC
    return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "log": os.path.basename(LOG), "venues": {}}
for v, b in BASE.items():
    R = out["venues"][v] = {}
    # A1: in-progress candle label vs request time; KST-UTC label offset; timestamp in [open, open+unit)
    for unit in (60, 1, 240):
        t_req = time.time()
        st, hdr, body, js = H.get_json(f"{b}/v1/candles/minutes/{unit}?market=KRW-BTC&count=200", LOG, f"{v}_m{unit}_latest")
        rec = {"status": st, "n": len(js) if isinstance(js, list) else None, "rate_header": hdr.get("remaining-req") or hdr.get("x-ratelimit-remaining")}
        if st == 200 and js:
            opens = [ep(c["candle_date_time_utc"]) for c in js]
            kst_off = sorted(set(ep(c["candle_date_time_kst"]) - ep(c["candle_date_time_utc"]) for c in js))
            ts_in = [(opens[k] * 1000 <= js[k]["timestamp"] < (opens[k] + unit * 60) * 1000) for k in range(len(js))]
            rec.update(newest_open_utc=js[0]["candle_date_time_utc"], request_utc_epoch=round(t_req, 3),
                       request_floor_to_unit_utc=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(t_req // (unit * 60)) * unit * 60)),
                       newest_is_request_floor=(opens[0] == int(t_req // (unit * 60)) * unit * 60),
                       kst_minus_utc_label_seconds=kst_off, timestamp_within_open_window_frac=sum(ts_in) / len(ts_in),
                       n_timestamp_outside=len(ts_in) - sum(ts_in), strictly_descending=all(opens[k] > opens[k + 1] for k in range(len(opens) - 1)),
                       spacing_seconds_set=sorted(set(opens[k] - opens[k + 1] for k in range(len(opens) - 1)))[:10],
                       open_aligned_to_unit=all(o % (unit * 60) == 0 for o in opens))
        R[f"A1_m{unit}"] = rec
    # A2: `to` semantics on 60m: which newest candle is returned for each spelling of 2026-09-01 00:00 UTC
    spell = {"iso_Z": "2026-09-01T00:00:00Z", "naive_T": "2026-09-01T00:00:00", "naive_space": "2026-09-01 00:00:00",
             "kst_offset": "2026-09-01T09:00:00+09:00", "iso_Z_plus1s": "2026-09-01T00:00:01Z"}
    for k, s in spell.items():
        st, hdr, body, js = H.get_json(f"{b}/v1/candles/minutes/60?market=KRW-BTC&count=2&to={urllib.parse.quote(s)}", LOG, f"{v}_to_{k}")
        R[f"A2_to_{k}"] = {"to": s, "status": st, "newest_open_utc": js[0]["candle_date_time_utc"] if st == 200 and isinstance(js, list) and js else None,
                           "body_head": None if st == 200 else body[:200].decode("utf-8", "replace")}
    # A3: days candle label convention (does a UTC day candle open at 00:00 UTC = 09:00 KST?)
    st, hdr, body, js = H.get_json(f"{b}/v1/candles/days?market=KRW-BTC&count=3", LOG, f"{v}_days_latest")
    R["A3_days"] = {"status": st, "rows": [{k: c.get(k) for k in ("candle_date_time_utc", "candle_date_time_kst")} for c in js] if st == 200 and isinstance(js, list) else None,
                    "body_head": None if st == 200 else body[:200].decode("utf-8", "replace")}
    # A4: max count per request
    for cnt in (200, 201, 1000):
        st, hdr, body, js = H.get_json(f"{b}/v1/candles/minutes/60?market=KRW-BTC&count={cnt}", LOG, f"{v}_count_{cnt}")
        R[f"A4_count_{cnt}"] = {"status": st, "n": len(js) if isinstance(js, list) else None, "body_head": None if st == 200 else body[:200].decode("utf-8", "replace")}
json.dump(out, open(T7 + "/receipts/PROBE_A_conventions.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
