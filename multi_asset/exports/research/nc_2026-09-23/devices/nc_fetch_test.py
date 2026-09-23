#!/usr/bin/env python3
"""F-1 (DESIGN §F-1, §E4′-1): the NC producer's parallel fetch layer (d), measured live in a quiet window — revision 2 (lead 2026-09-23:
production state as the sequential reference, funding-class request gate, 429/418 abort, N+3:10 deadline).
Mac, production venv, READ-ONLY on the exchange's public endpoints; never writes ~/wide_shadow or ~/dl_quant_live (it reads a copy of
state/rolling.npz and state/aux.json taken at start).
For each of 3 closed anchors A (the last three 4h anchors before now), the NC producer's own Fetcher (patched tree) fetches:
  K-lines (limit 52, endTime A-1ms) for the whole dynamic fetch list (exchangeInfo TRADING perpetual USDT ∩ 829 axis ∩ crypto), 6 workers,
  900 weight/min; funding via the symbol-less bulk endpoint over [A-26h, A] (time pages).
References (no re-fetch for names the production state already holds):
  K-lines: the production rolling cache rows of the 450 fetched names — the parallel arm's bars through bars_to_channels + clipch must
           equal the stored float16 channels 1-6 element for element, and channel 0 wherever the previous bar is in the same response;
           the ~72 names production does not fetch are re-fetched SEQUENTIALLY (1 worker) and compared response for response.
  funding: the production ledger (aux.json ledger_tail): every (fundingTime, rate) in [A-26h, A] of each name identical; a name missing
           from the production ledger is queried per name, sequentially, only that name.
Timing per phase of the parallel arm = the F-1 numbers for the E3 gate. Worst-case backfill: K names, 40-day window, the producer's
nc_backfill paging (limit 1000, weight 5), timed.
Guards: require_quiet_window(>= 45 min) at start; wait_for_quiet_window(5) before every request; own funding-class requests
(fundingRate / fundingInfo share 500 per 5 min per IP, not visible in the weight header) <= 300 in any rolling 5 minutes, else wait;
IP used weight > 1200 aborts; ANY HTTP 429 / 418 aborts at once (no retry; Retry-After and the response headers recorded);
no request is started after the deadline (default: this quiet window's N+3:10).
usage: ~/wide_shadow/venv/bin/python nc_fetch_test.py <patched tree> <crypto npz> <out dir> [--backfill-k 10]"""
import os, sys, json, time, importlib.util, argparse, hashlib, shutil, collections, urllib.error
import numpy as np

HOME = os.path.expanduser("~")
sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
from venue_quiet_window import require_quiet_window, wait_for_quiet_window

HARD = 1200; FUND_5MIN_CAP = 300; FUND_PATHS = ("/fapi/v1/fundingRate", "/fapi/v1/fundingInfo")


class Abort(BaseException):
    """BaseException on purpose: the producer's Fetcher catches Exception and retries; an abort must pass straight through it."""


def load_producer(tree, scratch):
    os.environ["WIDE_SHADOW_HOME"] = scratch; os.environ["WIDE_SHADOW_BUNDLE"] = f"{HOME}/wide_shadow/shadow_bundle"
    spec = importlib.util.spec_from_file_location("nc_shadow_loop", f"{tree}/shadow_loop_v3.py")
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("crypto"); ap.add_argument("out"); ap.add_argument("--backfill-k", type=int, default=10)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    st0 = require_quiet_window(min_remaining_min=45)
    now = time.time(); N = int(now) // 14400 * 14400; deadline = N + 3 * 3600 + 10 * 60      # N+3:10
    # read-only copies of the production state taken now (quiet window: the producer does not write)
    cp = os.path.join(a.out, "prod_state_copy"); os.makedirs(cp, exist_ok=True)
    for f in ("rolling.npz", "aux.json"): shutil.copy2(f"{HOME}/wide_shadow/state/{f}", f"{cp}/{f}")
    M = load_producer(a.tree, os.path.join(a.out, "scratch_home"))
    reqlog = open(os.path.join(a.out, "requests.jsonl"), "a"); fund_times = collections.deque(); aborted = {}
    real_urlopen = M.urllib.request.urlopen

    def guarded_urlopen(url, *args, **kw):
        try:
            return real_urlopen(url, *args, **kw)
        except urllib.error.HTTPError as e:
            if e.code in (429, 418):
                aborted.update({"code": e.code, "url": str(url)[:200], "headers": dict(e.headers.items()), "retry_after": e.headers.get("Retry-After"),
                                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                raise Abort(f"HTTP {e.code}")
            raise
    M.urllib.request.urlopen = guarded_urlopen

    class TF(M.Fetcher):
        arm = "?"
        def get(self, path, params, weight):
            if time.time() > deadline: raise Abort("deadline N+3:10 reached")
            wait_for_quiet_window(min_remaining_min=5)
            if path in FUND_PATHS:
                while True:
                    t = time.time()
                    while fund_times and t - fund_times[0] > 300: fund_times.popleft()
                    if len(fund_times) < FUND_5MIN_CAP: fund_times.append(t); break
                    time.sleep(1.0)
            r = super().get(path, params, weight)
            used = self._diag.get("used_weight_1m_last", 0)
            reqlog.write(json.dumps({"utc": time.strftime("%H:%M:%S", time.gmtime()), "arm": self.arm, "path": path, "symbol": params.get("symbol"),
                                     "rows": (len(r) if isinstance(r, list) else None), "err": (r.get("_err") if isinstance(r, dict) else None),
                                     "used_weight_1m": used, "fund_5min": len(fund_times)}) + "\n"); reqlog.flush()
            if used > HARD: raise Abort(f"X-MBX-USED-WEIGHT-1M {used} > {HARD}")
            return r

    cfg = json.load(open(f"{HOME}/wide_shadow/shadow_bundle/config.json")); axis = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(axis)}
    live = set(cfg["symbols_live"])
    crypto = np.load(a.crypto)["crypto"].astype(bool); assert crypto.shape == (len(axis),)
    Z = np.load(f"{cp}/rolling.npz", allow_pickle=True); pts = Z["ts"].astype(np.int64); pdat = Z["data"]; prow = {int(t): i for i, t in enumerate(pts)}
    AUX = json.load(open(f"{cp}/aux.json")); pled = AUX["ledger_tail"]
    _load0 = [round(x, 2) for x in os.getloadavg()]   # lead 2026-09-23: load average at start / end goes into the receipt (E3 gate input)
    rec = {"device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "tree_shadow_loop_sha256": hashlib.sha256(open(f"{a.tree}/shadow_loop_v3.py", "rb").read()).hexdigest(),
           "quiet_window_at_start": st0 if isinstance(st0, dict) else str(st0), "deadline_utc": time.strftime("%H:%M:%SZ", time.gmtime(deadline)),
           "prod_state_copy_sha256": {f: hashlib.sha256(open(f"{cp}/{f}", "rb").read()).hexdigest() for f in ("rolling.npz", "aux.json")}, "results": []}
    import concurrent.futures
    try:
        fx0 = TF(); fx0.arm = "exinfo"
        xi = fx0.get("/fapi/v1/exchangeInfo", {}, weight=1)
        tb = {x["symbol"] for x in xi["symbols"] if x.get("contractType") == "PERPETUAL" and x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING"}
        fetch = [s for j, s in enumerate(axis) if s in tb and crypto[j]]
        rec["fetch_n"] = len(fetch); rec["fetch_not_in_production"] = sorted(set(fetch) - live)
        A0 = N; anchors = [A0 - 8 * 3600, A0 - 4 * 3600, A0]; rec["anchors"] = anchors
        for A in anchors:
            row = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A))}
            M.FETCH_WORKERS, M.FETCH_BUDGET, M.FUND_BULK = 6, 900, 1
            fx = TF(); fx.arm = f"parallel@{A}"
            q = lambda s: ("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": 52, "endTime": A * 1000 - 1})
            t0 = time.time(); kl = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
                for s, r in zip(fetch, ex.map(lambda s: fx.get(*q(s), weight=1), fetch)): kl[s] = r
            t_k = time.time() - t0; t0 = time.time()
            w0 = (A - 26 * 3600 + 1) * 1000; fd = {}; seen = set(); start = w0; pages = 0; bulk_ok = True
            for _ in range(10):
                r = fx.get("/fapi/v1/fundingRate", {"startTime": start, "endTime": A * 1000 + 999, "limit": 1000}, weight=1); pages += 1
                if not isinstance(r, list): bulk_ok = False; break
                for x in r:
                    k = (x["symbol"], int(x["fundingTime"]))
                    if k in seen: continue
                    seen.add(k); fd.setdefault(x["symbol"], []).append((int(x["fundingTime"]) // 1000, float(x["fundingRate"])))
                if len(r) < 1000: break
                start = int(r[-1]["fundingTime"])
            else:
                bulk_ok = False
            t_f = time.time() - t0; d = fx.diagnostics()
            row["parallel"] = {"t_klines_s": round(t_k, 2), "t_funding_s": round(t_f, 2), "own_weight": fx.weight_used, "used_weight_1m_max": d.get("used_weight_1m_max"),
                               "errors": sum(1 for v in kl.values() if isinstance(v, dict)), "exhausted": d.get("exhausted_calls"),
                               "throttle_sleep_s": round(d.get("throttle_sleep_s", 0), 1), "bulk_ok": bulk_ok, "bulk_pages": pages}
            # ---- K-lines vs production rolling (names production fetches) / sequential re-fetch (the others)
            k_eq = k_ne = k_rows = prod_missing = 0; k_bad = []
            seq_names = [s for s in fetch if s not in live]
            fxs = TF(); fxs.arm = f"sequential@{A}"; M.FETCH_WORKERS = 1
            seq = {s: fxs.get(*q(s), weight=1) for s in seq_names}
            for s in fetch:
                r = kl[s]
                if not isinstance(r, list): k_bad.append(s); continue
                if s in live:
                    j = sidx[s]; pc = None; pts_ = None; ok = True
                    for kline in r:
                        close_s = (int(kline[0]) + 300000) // 1000
                        c, ch = M.bars_to_channels(kline)
                        adj = (pts_ == close_s - 300)
                        ch[0] = (c / pc - 1) if (adj and pc and pc > 0) else np.nan
                        v = np.array(M.clipch(ch), np.float16); i = prow.get(close_s)
                        if i is not None:
                            p = pdat[i, j]; k_rows += 1
                            if not np.isfinite(np.float32(p[3])):
                                prod_missing += 1                       # production never ingested this bar: not a fetch-layer difference
                            else:
                                cmp_ch = range(0, 7) if adj else range(1, 7)
                                for c_ in cmp_ch:
                                    if not (np.float16(v[c_]).view(np.uint16) == np.float16(p[c_]).view(np.uint16) or (np.isnan(v[c_]) and np.isnan(p[c_]))): ok = False
                        pc = c; pts_ = close_s
                    k_eq += ok; k_ne += (not ok)
                    if not ok and len(k_bad) < 20: k_bad.append(s)
                else:
                    if seq[s] == r: k_eq += 1
                    else:
                        k_ne += 1
                        if len(k_bad) < 20: k_bad.append(s)
            row["klines"] = {"names_equal": k_eq, "names_differ": k_ne, "rows_compared_vs_production": k_rows, "production_rows_missing": prod_missing, "sequential_refetch_names": len(seq_names), "differ_first": k_bad}
            # ---- funding vs production ledger; per-name sequential only for names the ledger lacks
            f_eq = f_ne = 0; f_bad = []; f_seq = 0
            for s in fetch:
                mine = sorted(e for e in fd.get(s, []) if e[0] <= A)
                if s in pled and pled[s]:
                    ref = sorted((int(x[0]), float(x[1])) for x in pled[s] if w0 // 1000 <= int(x[0]) <= A)
                    if int(pled[s][0][0]) > w0 // 1000: mine = [e for e in mine if e[0] >= int(pled[s][0][0])]
                else:
                    fs = TF(); fs.arm = f"fund_seq@{A}"; f_seq += 1
                    rr = fs.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": w0, "endTime": A * 1000 + 999, "limit": 100}, weight=1)
                    ref = sorted((int(x["fundingTime"]) // 1000, float(x["fundingRate"])) for x in rr) if isinstance(rr, list) else None
                if mine == ref: f_eq += 1
                else:
                    f_ne += 1
                    if len(f_bad) < 20: f_bad.append(s)
            row["funding"] = {"names_equal": f_eq, "names_differ": f_ne, "per_name_queries": f_seq, "differ_first": f_bad}
            row["PASS"] = k_ne == 0 and not k_bad and f_ne == 0 and bulk_ok
            rec["results"].append(row); print("F1_ANCHOR", json.dumps(row)[:700], flush=True)
        # worst-case same-anchor backfill: K names, 40-day window, nc_backfill paging, 6 workers
        M.FETCH_WORKERS, M.FETCH_BUDGET = 6, 900
        fx = TF(); fx.arm = "backfill"; K = fetch[:a.backfill_k]; t0 = time.time()
        def one(s):
            n = 0; start = (A0 - 40 * 86400 - 600) * 1000
            while True:
                r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "startTime": start, "endTime": A0 * 1000 - 1, "limit": 1000}, weight=5); n += 1
                if not isinstance(r, list) or len(r) < 1000: return n
                start = int(r[-1][0]) + 300000
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            pages = sum(ex.map(one, K))
        rec["backfill_worst"] = {"names": len(K), "requests": pages, "seconds": round(time.time() - t0, 1), "own_weight": fx.weight_used,
                                 "used_weight_1m_max": fx.diagnostics().get("used_weight_1m_max")}
        print("F1_BACKFILL", json.dumps(rec["backfill_worst"]), flush=True)
        rec["VERDICT"] = "PASS" if len(rec["results"]) == 3 and all(r["PASS"] for r in rec["results"]) else "FAIL"
    except Abort as e:
        rec["VERDICT"] = f"ABORTED: {e}"; rec["abort_http"] = aborted or None
    mins = {}
    for l in open(os.path.join(a.out, "requests.jsonl")):
        x = json.loads(l); m = x["utc"][:5]; mins.setdefault(m, {"requests": 0, "fund_requests": 0, "used_weight_1m_max": 0, "fund_5min_max": 0})
        mins[m]["requests"] += 1; mins[m]["fund_requests"] += int(x["path"] in FUND_PATHS)
        mins[m]["used_weight_1m_max"] = max(mins[m]["used_weight_1m_max"], x["used_weight_1m"] or 0); mins[m]["fund_5min_max"] = max(mins[m]["fund_5min_max"], x["fund_5min"])
    rec["per_minute"] = mins
    rec["loadavg_1_5_15"] = {"start": _load0, "end": [round(x, 2) for x in os.getloadavg()], "ncpu": os.cpu_count()}
    json.dump(rec, open(os.path.join(a.out, "NC_FETCH_TEST.json"), "w"), indent=1)
    print(f"NC_FETCH_TEST VERDICT={rec['VERDICT']} anchors={len(rec['results'])} fetch_n={rec.get('fetch_n')}", flush=True)
    sys.exit(0 if rec["VERDICT"] == "PASS" else 3)


if __name__ == "__main__":
    main()
