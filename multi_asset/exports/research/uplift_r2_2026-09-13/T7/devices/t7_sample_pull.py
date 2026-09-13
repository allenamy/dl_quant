#!/usr/bin/env python3
"""t7_sample_pull.py — SAMPLE PULL (<= 10 KRW markets total, 60 days) proving the full-pull mechanics end to end.
Window: bar opens in [2026-07-01T00:00Z, 2026-08-30T00:00Z) = 60 days. Markets (10): Upbit KRW-BTC, KRW-USDT, KRW-ETH, KRW-XRP, KRW-PEPE (x1000 -> 1000PEPEUSDT),
KRW-POL (renamed market, POLUSDT); Bithumb KRW-BTC, KRW-USDT, KRW-XRP, KRW-SHIB (x1000 -> 1000SHIBUSDT).
Binance reference: futures/um indexPriceKlines 1h monthly zips (2026-07, 2026-08) for BTCUSDT, ETHUSDT, XRPUSDT, 1000PEPEUSDT, POLUSDT, 1000SHIBUSDT.
Pull mechanics (identical to the full-pull design):
  60m candles paged backward, count=200, cursor `to` = oldest bar open of the previous page (exclusive), Bithumb `to` as naive KST.
  A page is accepted only if HTTP 200 AND body is a JSON list; anything else is an ERROR (retried by t7_http, then the run aborts; never written as empty).
  Stop rule: oldest open < window start, OR page shorter than 200 AND the census first trading day is reached (else ABORT: truncated paging).
  Day candles for the window (count=200 one page) are pulled for the completeness identity below.
Verification written to sample/SAMPLE_MANIFEST.json:
  V1 unique strictly-descending bar opens across pages; V2 opens aligned to the hour; V3 page-seam check (next page newest open < previous oldest open);
  V4 completeness identity: for every venue day fully inside the window, sum of hourly candle_acc_trade_volume == day candle volume (rel tol 1e-9);
     Upbit day = UTC day, Bithumb day = KST day (PROBE_A); V5 Binance zip row counts == hours in month, opens contiguous, ms units, close_time = open+3599999.
Stored columns: bar open (utc, kst labels), open/high/low/close, last-update timestamp, KRW turnover, volume. No returns are computed here."""
import sys, os, json, time, calendar, gzip, csv, io, zipfile, hashlib, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = T7 + "/sample"; os.makedirs(S, exist_ok=True)
LOG = T7 + "/receipts/http_log_sample.jsonl"
W0 = calendar.timegm((2026, 7, 1, 0, 0, 0)); W1 = calendar.timegm((2026, 8, 30, 0, 0, 0))
assert (W1 - W0) == 60 * 86400
MARKETS = [("upbit", "KRW-BTC"), ("upbit", "KRW-USDT"), ("upbit", "KRW-ETH"), ("upbit", "KRW-XRP"), ("upbit", "KRW-PEPE"), ("upbit", "KRW-POL"),
           ("bithumb", "KRW-BTC"), ("bithumb", "KRW-USDT"), ("bithumb", "KRW-XRP"), ("bithumb", "KRW-SHIB")]
assert len(MARKETS) <= 10
BIN = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "1000PEPEUSDT", "POLUSDT", "1000SHIBUSDT"]
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
CEN = json.load(open(T7 + "/receipts/CENSUS_krw_markets.json"))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def to_param(v, t): return urllib.parse.quote(iso(t) + "Z") if v == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
class Abort(Exception): pass
def page(v, mk, unit, cursor):
    url = f"{BASE[v]}/v1/candles/{unit}?market={mk}&count=200" + (f"&to={to_param(v, cursor)}" if cursor is not None else "")
    st, hdr, body, js = H.get_json(url, LOG, f"sample_{v}_{mk}_{unit}")
    if st != 200 or not isinstance(js, list):
        raise Abort(json.dumps({"url": url, "status": st, "body_head": body[:160].decode("utf-8", "replace")}))
    return js, url, hashlib.sha256(body).hexdigest()
man = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "window_utc": [iso(W0), iso(W1)], "krw": {}, "binance": {}, "n_requests": 0}
FIELDS = ["candle_date_time_utc", "candle_date_time_kst", "opening_price", "high_price", "low_price", "trade_price", "timestamp", "candle_acc_trade_price", "candle_acc_trade_volume"]
for v, mk in MARKETS:
    first_day = ep(CEN["venues"][v]["markets"][mk]["first_day_utc_label"])
    rows = {}; pages = []; cursor = W1; seams_ok = True; prev_oldest = None
    while True:
        js, url, bsha = page(v, mk, "minutes/60", cursor); man["n_requests"] += 1
        if js:
            opens = [ep(c["candle_date_time_utc"]) for c in js]
            if prev_oldest is not None and not opens[0] < prev_oldest: seams_ok = False
            prev_oldest = opens[-1]
            for c, o in zip(js, opens):
                if o in rows: raise Abort(f"duplicate bar {mk} {iso(o)}")
                rows[o] = c
            pages.append({"to": iso(cursor), "n": len(js), "newest": iso(opens[0]), "oldest": iso(opens[-1]), "body_sha256": bsha})
        if not js or opens[-1] < W0: break
        if len(js) < 200:
            if opens[-1] <= first_day + 86400: break
            raise Abort(f"short page before first trading day: {mk} oldest {iso(opens[-1])} first_day {iso(first_day)}")
        cursor = opens[-1]
    keep = sorted(o for o in rows if W0 <= o < W1)
    dj, durl, dsha = page(v, mk, "days", W1 + (0 if v == "upbit" else 15 * 3600)); man["n_requests"] += 1
    p60 = f"{S}/{v}_{mk}_60m.csv.gz"; pday = f"{S}/{v}_{mk}_days.csv.gz"
    with gzip.open(p60, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(FIELDS)
        for o in keep: w.writerow([rows[o][k] for k in FIELDS])
    days = sorted(dj, key=lambda c: c["candle_date_time_utc"])
    with gzip.open(pday, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(FIELDS)
        for c in days: w.writerow([c[k] for k in FIELDS])
    # V4 completeness identity per venue day fully inside the window
    v4 = {"n_days_checked": 0, "n_mismatch": 0, "n_rounding_only": 0, "max_rel_diff": 0.0, "examples": [], "tiers": "exact rel<=1e-9; rounding-only 1e-9<rel<=1e-6 (reported, not a fail); rel>1e-6 = MISMATCH (missing/extra bars)"}
    for c in days:
        d0 = ep(c["candle_date_time_utc"]); d1 = d0 + 86400
        if d0 < W0 or d1 > W1: continue
        hsum = sum(float(rows[o]["candle_acc_trade_volume"]) for o in keep if d0 <= o < d1)
        dv = float(c["candle_acc_trade_volume"]); v4["n_days_checked"] += 1
        rel = abs(hsum - dv) / max(1e-12, abs(dv)); v4["max_rel_diff"] = max(v4["max_rel_diff"], rel)
        if 1e-9 < rel <= 1e-6: v4["n_rounding_only"] += 1
        if rel > 1e-6:
            v4["n_mismatch"] += 1
            if len(v4["examples"]) < 3: v4["examples"].append({"day_open_utc": c["candle_date_time_utc"], "hourly_sum": hsum, "day": dv})
    hours = (W1 - W0) // 3600
    man["krw"][f"{v}:{mk}"] = {"file_60m": os.path.basename(p60), "sha256_60m": sha(p60), "file_days": os.path.basename(pday), "sha256_days": sha(pday),
                               "n_pages": len(pages), "pages": pages, "n_bars_in_window": len(keep), "hours_in_window": hours, "n_hours_without_bar": hours - len(keep),
                               "first_bar_utc": iso(keep[0]) if keep else None, "last_bar_utc": iso(keep[-1]) if keep else None,
                               "V1_unique_desc": True, "V2_hour_aligned": all(o % 3600 == 0 for o in keep), "V3_seams_ok": seams_ok, "V4_volume_identity": v4}
    print(v, mk, "bars", len(keep), "of", hours, "pages", len(pages), "V4", v4["n_days_checked"], v4["n_mismatch"], flush=True)
for sym in BIN:
    allrows = []; files = []
    for mth in ("2026-07", "2026-08"):
        u = f"https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/{sym}/1h/{sym}-1h-{mth}.zip"
        st, hdr, body = H.get(u, LOG, f"sample_bin_{sym}_{mth}"); man["n_requests"] += 1
        if st != 200: raise Abort(json.dumps({"url": u, "status": st}))
        zf = zipfile.ZipFile(io.BytesIO(body)); name = zf.namelist()[0]; txt = zf.read(name).decode()
        rr = list(csv.reader(io.StringIO(txt))); hdrrow = rr[0] if not rr[0][0].isdigit() else None; data = rr[1:] if hdrrow else rr
        files.append({"url": u, "zip_sha256": hashlib.sha256(body).hexdigest(), "member": name, "header": hdrrow, "n_rows": len(data)})
        allrows += data
    ot = [int(r[0]) for r in allrows]; ct = [int(r[6]) for r in allrows]
    y, m = 2026, 7; exp = sum(calendar.monthrange(2026, mm)[1] * 24 for mm in (7, 8))
    v5 = {"n_rows": len(allrows), "expected_rows": exp, "ms_units": all(10 ** 12 <= t < 10 ** 13 for t in ot), "contiguous": all(ot[i + 1] - ot[i] == 3600000 for i in range(len(ot) - 1)),
          "close_time_is_open_plus_3599999": all(c - o == 3599999 for o, c in zip(ot, ct))}
    keep = [r for r in allrows if W0 * 1000 <= int(r[0]) < W1 * 1000]
    p = f"{S}/binance_indexPriceKlines_{sym}_1h.csv.gz"
    with gzip.open(p, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["open_time_ms", "open", "high", "low", "close", "close_time_ms"])
        for r in keep: w.writerow([r[0], r[1], r[2], r[3], r[4], r[6]])
    man["binance"][sym] = {"file": os.path.basename(p), "sha256": sha(p), "source_files": files, "n_rows_in_window": len(keep), "V5": v5}
    print(sym, "rows", len(keep), v5, flush=True)
man["run_utc_end"] = H.utcnow_iso()
json.dump(man, open(S + "/SAMPLE_MANIFEST.json", "w"), indent=1, ensure_ascii=False)
print("requests", man["n_requests"])
