#!/usr/bin/env python3
"""t7_mapping_guard_r2.py — round 2 of the identity-verified mapping: venue renames that kept history under a new code (found in ARCHIVE vs CENSUS:
current codes trading before a snapshot but absent from it). Candidates (Binance base -> KRW code), ALL subject to the frozen r1 guard
(same T rule, same R, PASS |ln R| <= ln 1.25, REVIEW <= ln 2, FAIL beyond; staleness <= 24 h; first trading day <= T - 2 d):
  STPT -> AWE, DAR -> D, FXS -> FRAX, OM -> MANTRA.   (MAP -> MAPO not testable: no MAPUSDT in the panel.)
Only venues where r1 chose no PASS for that symbol are affected. Output MAPPING_guard_r2.json = r1 pairs + r2 candidate records merged; r1 file untouched. Logged."""
import sys, os, json, time, calendar, io, zipfile, csv, math, urllib.parse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_mapping_r2.jsonl"
MANUAL2 = {"STPT": ["AWE"], "DAR": ["D"], "FXS": ["FRAX"], "OM": ["MANTRA"]}
PASS_LN, FAIL_LN = math.log(1.25), math.log(2.0); T_CAP = calendar.timegm((2026, 8, 30, 23, 0, 0))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
BASEURL = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
def to_param(v, t): return urllib.parse.quote(iso(t) + "Z") if v == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
def krw_close(v, mk, T):
    st, hdr, body, js = H.get_json(f"{BASEURL[v]}/v1/candles/minutes/60?market={mk}&count=1&to={to_param(v, T + 3600)}", LOG, f"r2_{v}_{mk}_{T}")
    if st != 200 or not isinstance(js, list) or not js: return {"err": {"status": st, "body_head": body[:160].decode("utf-8", "replace")}}
    return {"close": float(js[0]["trade_price"]), "stale_s": T - ep(js[0]["candle_date_time_utc"])}
def bin_index_close(sym, T):
    d = time.strftime("%Y-%m-%d", time.gmtime(T))
    for u in (f"https://data.binance.vision/data/futures/um/daily/indexPriceKlines/{sym}/1h/{sym}-1h-{d}.zip",
              f"https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/{sym}/1h/{sym}-1h-{d[:7]}.zip"):
        st, hdr, body = H.get(u, LOG, f"r2_bin_{sym}_{T}")
        if st != 200: continue
        zf = zipfile.ZipFile(io.BytesIO(body)); rows = list(csv.reader(io.StringIO(zf.read(zf.namelist()[0]).decode())))
        data = rows[1:] if not rows[0][0].isdigit() else rows
        assert all(10 ** 12 <= int(x[0]) < 10 ** 13 for x in data), "open_time not ms"
        hit = [x for x in data if int(x[0]) == T * 1000]
        return {"close": float(hit[0][4])} if hit else {"err": "bar missing"}
    return {"err": "not found"}
Z = np.load(T7 + "/receipts/pod2/T7_universe_elig.npz", allow_pickle=True)
SYM = [str(s) for s in Z["symbols"]]; E = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]
C = json.load(open(T7 + "/receipts/CENSUS_krw_markets.json")); R1 = json.load(open(T7 + "/receipts/MAPPING_guard.json"))
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "r1_file_sha256": __import__("hashlib").sha256(open(T7 + "/receipts/MAPPING_guard.json", "rb").read()).hexdigest(),
       "pairs": json.loads(json.dumps(R1["pairs"])), "r2_records": []}
for base, codes in MANUAL2.items():
    s = base + "USDT"; c = SYM.index(s); idx = np.where(EL[:, c])[0]
    if not len(idx): continue
    T = min(T_CAP, (int(E[idx[-1]]) - 3600) // 3600 * 3600)
    for v in ("upbit", "bithumb"):
        prev = out["pairs"].get(s, {}).get(v)
        if prev and prev.get("chosen"): continue
        for code in codes:
            mk = "KRW-" + code
            if mk not in C["venues"][v]["markets"]: continue
            fd = C["venues"][v]["markets"][mk]["first_day_utc_label"]
            rr = {"symbol": s, "venue": v, "krw_market": mk, "english_name": C["venues"][v]["markets"][mk]["english_name"], "rule": "manual_r2", "mult": 1, "T_utc": iso(T), "krw_first_day_utc": fd}
            if ep(fd) > T - 2 * 86400: rr["verdict"] = "NO_OVERLAP_AT_T"
            else:
                a = krw_close(v, mk, T); b = krw_close(v, "KRW-BTC", T); ci = bin_index_close(s, T); cb = bin_index_close("BTCUSDT", T)
                if "err" in a or "err" in b or "err" in ci or "err" in cb: rr["verdict"] = "DATA_ERROR"; rr["detail"] = [a, b, ci, cb]
                elif a["stale_s"] > 86400 or b["stale_s"] > 86400: rr["verdict"] = "STALE"
                else:
                    R = (a["close"] / b["close"]) / (ci["close"] / cb["close"]); lr = abs(math.log(R)); rr["R"] = round(R, 6)
                    rr["verdict"] = "PASS" if lr <= PASS_LN else ("REVIEW" if lr <= FAIL_LN else "FAIL")
            out["r2_records"].append(rr)
            d = out["pairs"].setdefault(s, {}).setdefault(v, {"candidates": [], "chosen": None, "elig_window_utc": [iso(int(E[idx[0]])), iso(int(E[idx[-1]]))]})
            d["candidates"].append(rr)
            if rr["verdict"] == "PASS" and not d["chosen"]: d["chosen"] = mk
json.dump(out, open(T7 + "/receipts/MAPPING_guard_r2.json", "w"), indent=1, ensure_ascii=False)
for r in out["r2_records"]: print(r)
