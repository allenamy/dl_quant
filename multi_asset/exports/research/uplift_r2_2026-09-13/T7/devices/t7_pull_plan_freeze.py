#!/usr/bin/env python3
"""t7_pull_plan_freeze.py — freezes the T7 full-pull plan into <root>/plan/PULL_PLAN_FROZEN.json (+ .sha256) BEFORE any data request,
and copies the pull devices into <root>/devices (the pull runs from there, outside the iCloud-synced research repo).
Scope (lead dispatch 2026-09-13, = RESULT §9 S-MAP/H-REPLAY): identity-verified mapped KRW markets (MAPPING_guard_r2 'chosen') plus KRW-BTC and
KRW-USDT on each venue, 60m and day candles from max(census first trading day, CUTOFF = 2021-12-01T00:00Z) to PULL_END (= freeze time floored to the hour,
exclusive); Binance futures/um indexPriceKlines 1h MONTHLY zips for every mapped symbol over months overlapping
[max(CUTOFF, first C0-eligible anchor - 62 d), min(2026-08-31, last C0-eligible anchor + 62 d)] (no monthly zip exists yet for 2026-09).
Everything the later checks and guards use is frozen here (thresholds, criteria) so no threshold is chosen after data is seen.
--test builds a tiny plan (2 markets per venue, cutoff 2026-08-20, 2 symbols x 2 months) for the interruption/resume test."""
import os, sys, json, time, calendar, hashlib, shutil, argparse
import numpy as np
REPO_T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--test", action="store_true"); a = ap.parse_args()
ROOT = a.root; assert not ROOT.startswith("/Users/haosiyu/Desktop") and not ROOT.startswith("/Users/haosiyu/Documents"), "pull root must be outside iCloud-synced folders"
for _d in ("plan", "devices", "run", "manifest", "logs"): os.makedirs(ROOT + "/" + _d, exist_ok=True)   # run/ must exist before the launcher redirects stdout into it
assert not os.path.exists(ROOT + "/plan/PULL_PLAN_FROZEN.json"), "plan already frozen in this root (refusing to overwrite)"
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
R = REPO_T7 + "/receipts"
CEN = json.load(open(R + "/CENSUS_krw_markets.json")); MP = json.load(open(R + "/MAPPING_guard_r2.json"))
Z = np.load(R + "/pod2/T7_universe_elig.npz", allow_pickle=True); SYM = [str(s) for s in Z["symbols"]]; E = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]
SM = json.load(open(REPO_T7 + "/sample/SAMPLE_MANIFEST.json"))
now = time.time(); PULL_END = int(now // 3600) * 3600
CUTOFF = calendar.timegm((2026, 8, 20, 0, 0, 0)) if a.test else calendar.timegm((2021, 12, 1, 0, 0, 0))
LAST_MONTH = "2026-08"
pairs = []; markets = {"upbit": set(), "bithumb": set()}
for s, d in sorted(MP["pairs"].items()):
    for v in ("upbit", "bithumb"):
        if v in d and d[v]["chosen"]:
            mk = d[v]["chosen"]; cand = next(c for c in d[v]["candidates"] if c["krw_market"] == mk and c["verdict"] == "PASS")
            c = SYM.index(s); idx = np.where(EL[:, c])[0]
            pairs.append({"symbol": s, "venue": v, "market": mk, "mult": cand["mult"], "rule": cand["rule"], "R_at_check": cand.get("R"), "T_check_utc": cand["T_utc"],
                          "elig_first_utc": iso(int(E[idx[0]])), "elig_last_utc": iso(int(E[idx[-1]]))})
            markets[v].add(mk)
for v in markets: markets[v] |= {"KRW-BTC", "KRW-USDT"}
if a.test:
    markets = {"upbit": {"KRW-BTC", "KRW-POL"}, "bithumb": {"KRW-BTC", "KRW-XRP"}}
    pairs = [p for p in pairs if (p["venue"], p["market"]) in {("upbit", "KRW-BTC"), ("upbit", "KRW-POL"), ("bithumb", "KRW-BTC"), ("bithumb", "KRW-XRP")}]
krw = {}
for v in ("upbit", "bithumb"):
    rows = []
    for mk in sorted(markets[v]):
        fd = CEN["venues"][v]["markets"][mk]["first_day_utc_label"]
        rows.append({"market": mk, "first_day_utc_label": fd, "first_day_epoch": ep(fd), "start_epoch": max(ep(fd), CUTOFF)})
    if a.test:   # error-path fixture: a code that never existed must end as an ERROR (never DONE, never an empty page)
        rows.append({"market": "KRW-ZZZNOTACOIN", "first_day_utc_label": "2026-08-01T00:00:00", "first_day_epoch": calendar.timegm((2026, 8, 1, 0, 0, 0)), "start_epoch": CUTOFF, "fixture": "NEGATIVE"})
    krw[v] = rows
def month_add(y, m, k):
    m0 = m - 1 + k; return y + m0 // 12, m0 % 12 + 1
binance = []
syms = sorted({p["symbol"] for p in pairs} | {"BTCUSDT", "XRPUSDT"})
for s in syms:
    c = SYM.index(s); idx = np.where(EL[:, c])[0]
    lo = max(CUTOFF, int(E[idx[0]]) - 62 * 86400); hi = min(calendar.timegm((2026, 8, 31, 23, 0, 0)), int(E[idx[-1]]) + 62 * 86400)
    if s in ("BTCUSDT", "XRPUSDT"): lo = CUTOFF; hi = calendar.timegm((2026, 8, 31, 23, 0, 0))
    if a.test: lo, hi = calendar.timegm((2026, 7, 1, 0, 0, 0)), calendar.timegm((2026, 8, 31, 23, 0, 0))
    y, m = time.gmtime(lo).tm_year, time.gmtime(lo).tm_mon; months = []
    while "%04d-%02d" % (y, m) <= time.strftime("%Y-%m", time.gmtime(hi)) and "%04d-%02d" % (y, m) <= LAST_MONTH:
        months.append("%04d-%02d" % (y, m)); y, m = month_add(y, m, 1)
    binance.append({"symbol": s, "months": months, "elig_first_utc": iso(int(E[idx[0]])), "elig_last_utc": iso(int(E[idx[-1]]))})
if a.test:
    binance = [b for b in binance if b["symbol"] in ("BTCUSDT", "XRPUSDT")]
    binance.append({"symbol": "ZZZNOTACOINUSDT", "months": ["2026-07"], "elig_first_utc": "2026-07-01T00:00:00Z", "elig_last_utc": "2026-07-31T00:00:00Z", "fixture": "NEGATIVE_404_INSIDE_WINDOW"})
ctrl_zip = SM["binance"]["BTCUSDT"]["source_files"][0]; assert ctrl_zip["url"].endswith("BTCUSDT-1h-2026-07.zip")
PLAN = {
 "created_utc": iso(now), "mode": "TEST" if a.test else "FULL", "root": ROOT,
 "pull_end_epoch": PULL_END, "pull_end_utc": iso(PULL_END), "cutoff_epoch": CUTOFF, "cutoff_utc": iso(CUTOFF), "last_binance_month": LAST_MONTH,
 "min_free_bytes": 3 * 1024 ** 3,
 "rate": {"max_requests_in_any_1s_per_host": 5, "min_gap_s": 0.21, "hosts_in_parallel": ["api.upbit.com", "api.bithumb.com", "data.binance.vision"]},
 "krw": krw, "n_krw_markets": {v: len(krw[v]) for v in krw}, "pairs": pairs, "n_pairs": len(pairs), "binance": binance,
 "n_binance_symbol_months": sum(len(b["months"]) for b in binance),
 "inputs_sha256": {"CENSUS_krw_markets.json": sha(R + "/CENSUS_krw_markets.json"), "MAPPING_guard_r2.json": sha(R + "/MAPPING_guard_r2.json"),
                   "T7_universe_elig.npz": sha(R + "/pod2/T7_universe_elig.npz"), "SAMPLE_MANIFEST.json": sha(REPO_T7 + "/sample/SAMPLE_MANIFEST.json")},
 "controls": {
   "krw_pos": "KRW-BTC minutes/60 count=200 with `to` = 2026-09-01T00:00Z (Upbit '...Z', Bithumb naive KST '2026-09-01T09:00:00') must return 200 rows, newest bar open 2026-08-31T23:00:00; body sha256 must equal the first run's (reference stored in plan/control_reference_<venue>.json)",
   "krw_neg_to": "Upbit: `to`=2016-01-01T00:00:00Z (before venue launch) must return HTTP 200 + []; Bithumb: `to`='2026-09-01T00:00:00Z' (Z spelling) must return HTTP 200 + a non-list body containing 'Invalid parameter' (CORRECTION_1: not an empty list)",
   "krw_neg_code": "market KRW-ZZZNOTACOIN must return a non-list body containing 'Code not found' (Upbit HTTP 404, Bithumb HTTP 200)",
   "binance_pos": {"url": ctrl_zip["url"], "zip_sha256": ctrl_zip["zip_sha256"]},
   "binance_neg": "futures/um monthly indexPriceKlines ZZZNOTACOINUSDT 2026-07 must return HTTP 404",
   "on_failure": "worker writes run/ABORT_<venue>_<run>.json and exits 2 before any data request"},
 "stop_rules": {
   "page_accept": "HTTP 200 AND JSON list AND bar opens strictly descending AND newest open < cursor AND opens aligned (60m: hour; day: Upbit 00:00Z, Bithumb 15:00Z) AND market field == requested market",
   "cursor": "first request `to` = PULL_END; next `to` = oldest bar open of the last accepted page (exclusive); resume = min oldest open over accepted manifest pages",
   "done_cutoff": "oldest open < CUTOFF (60m) or < CUTOFF - 1 day (days)",
   "done_first_trade": "page shorter than 200 AND oldest open < census first day label + 1 day",
   "empty_list": "accepted as DONE only when cursor <= census first day label + 1 day or <= the unit cutoff; otherwise EMPTY_UNEXPECTED (retried once after 5 s, then error; market left not done)",
   "short_page_early": "page shorter than 200 with oldest open >= census first day + 1 day => SHORT_PAGE_BEFORE_FIRST_DAY error (truncation suspect), market left not done",
   "errors": "non-200 status or non-list body (incl. Bithumb HTTP 200 + error body) => errors_<venue>.jsonl, market left not done, retried in pass 2; never written as a page",
   "binance": "HTTP 200 + valid zip (one CSV member) => stored; HTTP 404 => NOT_FOUND record (a fact); other status or bad zip => error, retried in pass 2"},
 "checks": {
   "C0_integrity": "every manifest page file exists, gunzipped body sha256 == manifest body_sha256, row count == manifest n; orphan page files counted",
   "C1_earliest_bar": "60m: if census first day >= CUTOFF, earliest bar open in [first day label, +1 day); else earliest bar open < CUTOFF. days: earliest day open <= max(first day label, CUTOFF - 1 day)",
   "C2_seams": "pages ordered by cursor descending: page(k+1).to == page(k).oldest_open and page(k+1).newest_open < page(k).oldest_open; 0 duplicate bar opens",
   "C3_volume_identity": "for every venue day [d0, d0+24h) with d0 >= max(first day label, CUTOFF) and d0+24h <= PULL_END: sum of 60m candle_acc_trade_volume == day candle_acc_trade_volume; rel diff <= 1e-9 EXACT, <= 1e-6 ROUNDING, else MISMATCH (also a day bar with no hourly bars or hourly bars with no day bar is MISMATCH)",
   "C4_freshness": "newest 60m bar open == PULL_END - 1h => FRESH; else if any complete venue day after the newest hourly bar has day volume > 0 => STALE_MISSING (fail), else THIN_OK",
   "C5_http": "per host: attempts by status, unresolved errors, accepted empty lists with reasons, 429 count, max requests in any rolling 1 s window from send log (must be <= 5)",
   "C6_binance": "per zip: header present, ms open_time, contiguous hours, close_time == open + 3599999, rows == hours in month unless first/last listing month; NOT_FOUND months inside [elig_first, elig_last] => FLAG_MISSING_INDEX"},
 "identity_guard": {
   "series": "per pair and hour t with KRW bar, KRW-BTC bar (same venue), Binance index bar and BTCUSDT index bar: r(t) = ln(Pkrw_i/Pkrw_BTC) - ln((Pidx_i/mult)/Pidx_BTC)",
   "daily": "d(day) = median r over the UTC day's hours (days with >= 6 hours)",
   "rolling": "m30(day) = median of d over the trailing 30 UTC days (>= 10 days present); m7 likewise over 7 days (>= 3 present)",
   "FLAG_DIVERGE": "|m30| > ln 1.25 (merged into contiguous day ranges)",
   "FLAG_SCALE_SUSPECT": "|m30| > ln 4 OR |m7(day) - m7(day - 14)| > ln 4",
   "policy": "flag only; nothing is dropped; per pair report n hours checked, checked range, flagged ranges and the extreme |m30| inside flagged ranges only"},
 "offset_spectrum": {
   "targets": "per venue, per calendar year in the pull (2021 = December only): KRW-BTC vs BTCUSDT index and KRW-XRP vs XRPUSDT index",
   "method": "hourly ln close; detrend x~(t) = x(t) - mean over |s - t| <= 24 h (>= 24 finite); rho(k) = Pearson corr(x~(t+k), y~(t)), k = -12..+12; dispersion D(k) = std of [x(t+k) - y(t)] minus its centred 49 h median",
   "PASS": "argmax rho == 0 AND rho(0) > max(rho(-1), rho(+1)) AND argmin D == 0",
   "negative_controls": "KST-as-UTC relabel (x(t-9h)) must give argmax +9 and argmin +9; close-time relabel (x(t-1h)) must give +1 and +1"},
 "device_sha256": {}}
for f in ("t7_http2.py", "t7_pull.py", "t7_pull_launch.sh", "t7_pull_checks.py", "t7_pull_identity_guard.py", "t7_pull_offset_spectrum.py", "t7_pull_summarize.py", "t7_pull_plan_freeze.py"):
    src = os.path.join(REPO_T7, "devices", f)
    if os.path.exists(src):
        shutil.copy2(src, ROOT + "/devices/" + f); PLAN["device_sha256"][f] = sha(src)
        assert sha(ROOT + "/devices/" + f) == PLAN["device_sha256"][f]
blob = json.dumps(PLAN, indent=1, ensure_ascii=False).encode()
open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "wb").write(blob)
open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256", "w").write(hashlib.sha256(blob).hexdigest() + "  PULL_PLAN_FROZEN.json\n")
print(json.dumps({"mode": PLAN["mode"], "pull_end": PLAN["pull_end_utc"], "cutoff": PLAN["cutoff_utc"], "n_krw_markets": PLAN["n_krw_markets"], "n_pairs": PLAN["n_pairs"],
                  "n_binance_symbols": len(binance), "n_binance_symbol_months": PLAN["n_binance_symbol_months"], "devices": PLAN["device_sha256"], "plan_sha256": hashlib.sha256(blob).hexdigest()}, indent=1))
