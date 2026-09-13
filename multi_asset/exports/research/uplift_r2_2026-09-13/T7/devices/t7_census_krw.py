#!/usr/bin/env python3
"""t7_census_krw.py — KRW market census on both venues (currently listed markets only; delisted codes are not queryable, PROBE_B/C).
Per market, 2 requests: (1) months candles count=200 -> first trading month, months present, gap months;
(2) days candles count=200 with `to` = first-month label + 40 d -> oldest row = first trading day.
Candles exist only for intervals with trades (PROBE_B B4), so 'first candle' = first trade in that unit.
Bithumb `to` spelled as naive KST (PROBE_A). Error discipline: any non-200 status OR a body that is not a JSON list
(Bithumb answers HTTP 200 + {"error":{...}}) is an ERROR; errored markets are retried in a second pass and never recorded as empty.
Stores listing metadata and candle DATE LABELS only (no prices, no volumes). Logged."""
import sys, os, json, time, calendar, gzip, hashlib, urllib.parse, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def to_param(v, t): return urllib.parse.quote(iso(t) + "Z") if v == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
def fetch_list(v, url, log, tag):
    st, hdr, body, js = H.get_json(url, log, tag)
    if st != 200 or not isinstance(js, list):
        return None, {"status": st, "body_head": body[:160].decode("utf-8", "replace")}
    return js, None
def month_key(label): return label[:7]
def census_market(v, mk, log):
    rec = {}
    js, err = fetch_list(v, f"{BASE[v]}/v1/candles/months?market={mk}&count=200", log, f"{v}_{mk}_months")
    if err: return {"ERROR": {"step": "months", **err}}
    if not js: return {"NO_CANDLES": True}
    labels_utc = [c["candle_date_time_utc"] for c in js]; labels_kst = [c["candle_date_time_kst"] for c in js]
    rec["n_months_present"] = len(js); rec["newest_month_utc_label"] = labels_utc[0]; rec["first_month_utc_label"] = labels_utc[-1]; rec["first_month_kst_label"] = labels_kst[-1]
    rec["months_returned_capped"] = len(js) >= 200
    present = set(month_key(l) for l in labels_kst)   # month identity in the venue's own calendar (KST label is the venue-local month for both)
    y, m = int(labels_kst[-1][:4]), int(labels_kst[-1][5:7]); ny, nm = int(labels_kst[0][:4]), int(labels_kst[0][5:7]); gaps = []
    while (y, m) <= (ny, nm):
        if "%04d-%02d" % (y, m) not in present: gaps.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13: y, m = y + 1, 1
    rec["gap_months_kst"] = gaps
    t_to = ep(labels_utc[-1]) + 40 * 86400
    js2, err2 = fetch_list(v, f"{BASE[v]}/v1/candles/days?market={mk}&count=200&to={to_param(v, t_to)}", log, f"{v}_{mk}_firstdays")
    if err2: return {**rec, "ERROR": {"step": "days", **err2}}
    if not js2: return {**rec, "ERROR": {"step": "days", "status": 200, "body_head": "EMPTY LIST for a window that must contain the first month"}}
    rec["first_day_utc_label"] = js2[-1]["candle_date_time_utc"]; rec["first_day_kst_label"] = js2[-1]["candle_date_time_kst"]
    rec["first_day_in_first_month"] = month_key(js2[-1]["candle_date_time_kst"]) == month_key(labels_kst[-1])
    rec["days_page_n"] = len(js2)
    return rec
OUT = {"device": os.path.basename(__file__), "run_utc_start": H.utcnow_iso(), "venues": {}}
def run_venue(v):
    log = T7 + f"/receipts/http_log_census_{v}.jsonl"
    st, hdr, body, js = H.get_json(f"{BASE[v]}/v1/market/all?isDetails=true", log, f"{v}_market_all")
    assert st == 200 and isinstance(js, list), (v, st, body[:200])
    raw = T7 + f"/receipts/raw/{v}_market_all_isDetails_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json.gz"
    with gzip.open(raw, "wb") as f: f.write(body)
    krw = sorted([m for m in js if m["market"].startswith("KRW-")], key=lambda m: m["market"])
    R = OUT["venues"][v] = {"market_all_raw": os.path.basename(raw), "market_all_body_sha256": hashlib.sha256(body).hexdigest(), "n_markets_all": len(js), "n_krw": len(krw), "markets": {}}
    for m in krw:
        R["markets"][m["market"]] = {"english_name": m.get("english_name"), "korean_name": m.get("korean_name"),
                                     "flags": m.get("market_event") if v == "upbit" else m.get("market_warning")}
    for p in (1, 2):
        todo = [mk for mk, r in R["markets"].items() if p == 1 or "ERROR" in r]
        for mk in todo:
            res = census_market(v, mk, log)
            keep = {k: R["markets"][mk][k] for k in ("english_name", "korean_name", "flags")}
            if p == 2: keep["retry_pass"] = 2
            R["markets"][mk] = {**keep, **res}
        R[f"pass{p}_n_attempted"] = len(todo)
    R["n_error_final"] = sum(1 for r in R["markets"].values() if "ERROR" in r)
    R["n_no_candles"] = sum(1 for r in R["markets"].values() if r.get("NO_CANDLES"))
th = [threading.Thread(target=run_venue, args=(v,)) for v in BASE]
[t.start() for t in th]; [t.join() for t in th]
OUT["run_utc_end"] = H.utcnow_iso()
json.dump(OUT, open(T7 + "/receipts/CENSUS_krw_markets.json", "w"), indent=1, ensure_ascii=False)
for v, R in OUT["venues"].items():
    fm = [r.get("first_day_utc_label", "")[:4] for r in R["markets"].values() if "first_day_utc_label" in r]
    print(v, "n_krw", R["n_krw"], "errors", R["n_error_final"], "no_candles", R["n_no_candles"], "first-day years", {y: fm.count(y) for y in sorted(set(fm))},
          "gapped", sum(1 for r in R["markets"].values() if r.get("gap_months_kst")), "first_day_not_in_first_month", sum(1 for r in R["markets"].values() if r.get("first_day_in_first_month") is False))
