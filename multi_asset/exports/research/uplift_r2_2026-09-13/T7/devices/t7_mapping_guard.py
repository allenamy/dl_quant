#!/usr/bin/env python3
"""t7_mapping_guard.py — map Binance USDT-perp panel symbols (829) to KRW markets on Upbit / Bithumb and verify identity by price level.
MAPPING (fixed before any price is fetched):
  base = symbol minus 'USDT'; multiplier prefixes stripped: '1000000' -> 1e6, '1000' -> 1e3, '1M' -> 1e6 (only when followed by a letter).
  candidates = [base] + MANUAL.get(base, []) + [base + '2'] (Korean venues' disambiguation suffix; accepted only if the guard passes).
  MANUAL (reason): BEAMX->BEAM (Beam ticker), DODOX->DODO, LUNA2->LUNA (Terra 2.0), BTTC->BTT (new BitTorrent), MATIC->POL, FTM->S,
    EOS->A (Vaulta), RNDR->RENDER, KLAY->KAIA (1:1 swaps; venues re-keyed the market and kept history, CENSUS first days), AXL->WAXL (Bithumb ticker).
  NOT mapped on purpose (non-1:1 swaps break price level): GAL->G, MKR->SKY, AGIX/OCEAN->FET, NU/KEEP->T.
IDENTITY GUARD (thresholds frozen here, before running):
  check hour T (bar open, UTC) = min(2026-08-30T23:00Z, last C0-eligible anchor of the symbol - 1h), floored to the hour.
  KRW: 60m candle count=1 with `to`=T+1h (exclusive) -> latest candle with open <= T; staleness = T - open; > 24h => STALE (unverified).
  Binance: futures/um indexPriceKlines 1h close of bar open T (data.binance.vision daily zip for date(T), monthly zip fallback).
  R = (P_krw(coin)/P_krw(BTC)) / ((P_idx(sym)/mult)/P_idx(BTCUSDT)); BTC legs taken at the same T on the same venue (FX cancels).
  PASS |ln R| <= ln 1.25 ; REVIEW ln 1.25 < |ln R| <= ln 2 ; FAIL |ln R| > ln 2. Only PASS pairs count as covered downstream.
  If several candidates exist on a venue, the first PASS candidate in candidate order is used; all candidate results are kept.
  KRW market must have first trading day <= T - 2d (CENSUS) else NO_OVERLAP_AT_T (pair can still be checked at an earlier/later T in the full pull).
Only the ratio R (a single price-level ratio used as an identity test) is reported; no returns. Logged."""
import sys, os, json, time, calendar, io, zipfile, csv, math, urllib.parse, threading
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_mapping.jsonl"
MANUAL = {"BEAMX": ["BEAM"], "DODOX": ["DODO"], "LUNA2": ["LUNA"], "BTTC": ["BTT"], "MATIC": ["POL"], "FTM": ["S"], "EOS": ["A"], "RNDR": ["RENDER"], "KLAY": ["KAIA"], "AXL": ["WAXL"]}
PASS_LN, FAIL_LN = math.log(1.25), math.log(2.0)
T_CAP = calendar.timegm((2026, 8, 30, 23, 0, 0))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def norm(sym):
    b = sym[:-4]; m = 1
    for p, mm in (("1000000", 10 ** 6), ("1000", 1000), ("1M", 10 ** 6)):
        if b.startswith(p) and len(b) > len(p) and b[len(p)].isalpha():
            return b[len(p):], mm
    return b, m
Z = np.load(T7 + "/receipts/pod2/T7_universe_elig.npz", allow_pickle=True)
SYM = [str(s) for s in Z["symbols"]]; E = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]
C = json.load(open(T7 + "/receipts/CENSUS_krw_markets.json"))
BASEURL = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
def to_param(v, t): return urllib.parse.quote(iso(t) + "Z") if v == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
_krw_cache = {}; _bin_cache = {}; _lk = threading.Lock()
def krw_close(v, mk, T):
    key = (v, mk, T)
    if key in _krw_cache: return _krw_cache[key]
    st, hdr, body, js = H.get_json(f"{BASEURL[v]}/v1/candles/minutes/60?market={mk}&count=1&to={to_param(v, T + 3600)}", LOG, f"{v}_{mk}_{T}")
    if st != 200 or not isinstance(js, list): r = {"err": {"status": st, "body_head": body[:160].decode("utf-8", "replace")}}
    elif not js: r = {"err": {"status": st, "body_head": "EMPTY"}}
    else: r = {"close": float(js[0]["trade_price"]), "open_utc": js[0]["candle_date_time_utc"], "stale_s": T - ep(js[0]["candle_date_time_utc"])}
    _krw_cache[key] = r; return r
def bin_index_close(sym, T):
    key = (sym, T)
    if key in _bin_cache: return _bin_cache[key]
    d = time.strftime("%Y-%m-%d", time.gmtime(T)); mth = d[:7]
    urls = [f"https://data.binance.vision/data/futures/um/daily/indexPriceKlines/{sym}/1h/{sym}-1h-{d}.zip",
            f"https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/{sym}/1h/{sym}-1h-{mth}.zip"]
    r = {"err": "not found"}
    for u in urls:
        st, hdr, body = H.get(u, LOG, f"bin_{sym}_{T}")
        if st != 200: r = {"err": {"status": st, "url": u}}; continue
        zf = zipfile.ZipFile(io.BytesIO(body)); name = zf.namelist()[0]
        rows = list(csv.reader(io.StringIO(zf.read(name).decode())))
        header = rows[0] if rows and not rows[0][0].strip().isdigit() else None
        data = rows[1:] if header else rows
        ot = [int(x[0]) for x in data]
        unit = "us" if ot and ot[0] > 10 ** 14 else "ms"
        div = 1000 if unit == "us" else 1
        hit = [x for x in data if int(x[0]) // div == T * 1000]
        r = {"url": u, "header": header, "open_time_unit": unit, "n_rows": len(data)}
        if hit: r["close"] = float(hit[0][4])
        else: r["err"] = "bar missing"
        break
    _bin_cache[key] = r; return r
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "log": os.path.basename(LOG), "pairs": {}, "preflight": {}}
# preflight: Binance archive format on BTCUSDT (units, header) for the cap hour
out["preflight"]["BTCUSDT_T_CAP"] = bin_index_close("BTCUSDT", T_CAP)
assert "close" in out["preflight"]["BTCUSDT_T_CAP"], out["preflight"]
lastel = {}
for c, s in enumerate(SYM):
    idx = np.where(EL[:, c])[0]
    lastel[s] = (int(E[idx[0]]), int(E[idx[-1]])) if len(idx) else None
def work(v):
    M = C["venues"][v]["markets"]
    for s in SYM:
        if lastel[s] is None: continue   # never eligible in the replay -> irrelevant to coverage
        base, mult = norm(s)
        cands = [base] + MANUAL.get(base, []) + [base + "2"]
        cands = [x for i, x in enumerate(cands) if x not in cands[:i]]
        present = [("KRW-" + x) for x in cands if ("KRW-" + x) in M]
        if not present: continue
        T = min(T_CAP, (lastel[s][1] - 3600) // 3600 * 3600)
        res = []
        for mk in present:
            fd = M[mk].get("first_day_utc_label")
            rr = {"krw_market": mk, "english_name": M[mk].get("english_name"), "rule": "exact" if mk[4:] == base else ("manual" if mk[4:] in MANUAL.get(base, []) else "suffix2"),
                  "mult": mult, "T_utc": iso(T), "krw_first_day_utc": fd}
            if fd is None or ep(fd) > T - 2 * 86400:
                rr["verdict"] = "NO_OVERLAP_AT_T"; res.append(rr); continue
            a = krw_close(v, mk, T); b = krw_close(v, "KRW-BTC", T); ci = bin_index_close(s, T); cb = bin_index_close("BTCUSDT", T)
            if "err" in a or "err" in b or "close" not in ci or "close" not in cb:
                rr["verdict"] = "DATA_ERROR"; rr["detail"] = {"krw": a.get("err"), "krw_btc": b.get("err"), "bin": ci.get("err"), "bin_btc": cb.get("err")}; res.append(rr); continue
            rr["krw_stale_s"] = a["stale_s"]; rr["krw_btc_stale_s"] = b["stale_s"]
            if a["stale_s"] > 86400 or b["stale_s"] > 86400:
                rr["verdict"] = "STALE"; res.append(rr); continue
            R = (a["close"] / b["close"]) / ((ci["close"] / mult) / cb["close"])
            rr["R"] = round(R, 6); lr = abs(math.log(R))
            rr["verdict"] = "PASS" if lr <= PASS_LN else ("REVIEW" if lr <= FAIL_LN else "FAIL")
            res.append(rr)
        chosen = next((r["krw_market"] for r in res if r["verdict"] == "PASS"), None)
        with _lk:
            out["pairs"].setdefault(s, {})[v] = {"candidates": res, "chosen": chosen, "elig_window_utc": [iso(lastel[s][0]), iso(lastel[s][1])]}
THREAD_ERR = []
def safe_work(v):
    try: work(v)
    except BaseException as e:
        import traceback; THREAD_ERR.append((v, traceback.format_exc()))
th = [threading.Thread(target=safe_work, args=(v,)) for v in ("upbit", "bithumb")]
[t.start() for t in th]; [t.join() for t in th]
if THREAD_ERR:   # a crashed worker must never leave a partial receipt that looks complete
    for v, tb in THREAD_ERR: print("WORKER CRASH", v, tb, file=sys.stderr)
    sys.exit(3)
out["run_utc_end"] = H.utcnow_iso()
json.dump(out, open(T7 + "/receipts/MAPPING_guard.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
for v in ("upbit", "bithumb"):
    cnt = Counter(); chosen = 0
    for s, d in out["pairs"].items():
        if v in d:
            for r in d[v]["candidates"]: cnt[(r["rule"], r["verdict"])] += 1
            chosen += d[v]["chosen"] is not None
    print(v, "symbols with >=1 candidate:", sum(1 for d in out["pairs"].values() if v in d), "chosen PASS:", chosen, dict(cnt))
print("preflight", out["preflight"])
