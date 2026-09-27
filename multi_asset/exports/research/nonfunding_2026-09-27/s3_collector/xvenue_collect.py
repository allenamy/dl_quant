#!/usr/bin/python3
"""xvenue_collect.py — S3 forward collector (DECISION_RULE_nonfunding_sources_2026-09-27 §0-4): one snapshot per run of the
PUBLIC perpetual tickers of three NON-Binance venues. Run by launchd every 60 s (StartInterval); one run = at most one request per venue.
Read-only public market data; no keys, no account endpoints, no Binance.

  okx       GET  https://www.okx.com/api/v5/market/tickers?instType=SWAP          (all swaps in one response)
  bybit     GET  https://api.bybit.com/v5/market/tickers?category=linear          (all linear perps in one response)
  hl        POST https://api.hyperliquid.xyz/info {"type": "metaAndAssetCtxs"}    (all perps in one response)

Rate limit (self-imposed, far below every venue's public limit): a venue is fetched at most once per MIN_INTERVAL_S; after an error the
venue backs off exponentially (60 s * 2^k, capped at 30 min) and the backoff is recorded. A run that finds another run still holding the
lock exits without fetching.
Output: <ROOT>/data/<UTC date>/<venue>.csv.gz, one gzip member appended per run (valid multi-member gzip). Columns:
  recv_ms, venue, symbol, exch_ts_ms, last, bid, ask, mark, index, funding, oi
(empty = the venue does not publish that field). Heartbeat <ROOT>/state/heartbeat.json is written atomically every run (write tmp, fsync,
rename, read back); one log line per run in <ROOT>/logs/collect_<UTC date>.log.
Disk guard: if free space under <ROOT> < MIN_FREE_GB the run writes nothing but the log line "DISK_LOW" (a terminal marker for patrol).
Standard library only (/usr/bin/python3, the macOS system interpreter).
"""
import os, sys, json, time, gzip, fcntl, shutil, urllib.request

ROOT = os.environ.get("XVENUE_ROOT", os.path.expanduser("~/xvenue_collector"))   # override only for tests
MIN_INTERVAL_S = 50
MIN_FREE_GB = 20.0
TIMEOUT_S = 10
UA = {"User-Agent": "xvenue-collector/1.0 (research, read-only public tickers)"}
VERSION = "1.0"


def now_ms(): return int(time.time() * 1000)
def utc_date(ms): return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))
def s(x): return "" if x is None else str(x)


def fetch_okx():
    r = urllib.request.urlopen(urllib.request.Request("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=UA), timeout=TIMEOUT_S)
    d = json.loads(r.read()); assert d.get("code") == "0", ("okx code", d.get("code"), d.get("msg"))
    return [(x.get("instId"), x.get("ts"), x.get("last"), x.get("bidPx"), x.get("askPx"), None, None, None, None) for x in d["data"]]


def fetch_bybit():
    r = urllib.request.urlopen(urllib.request.Request("https://api.bybit.com/v5/market/tickers?category=linear", headers=UA), timeout=TIMEOUT_S)
    d = json.loads(r.read()); assert d.get("retCode") == 0, ("bybit retCode", d.get("retCode"), d.get("retMsg"))
    ts = d.get("time")
    return [(x.get("symbol"), ts, x.get("lastPrice"), x.get("bid1Price"), x.get("ask1Price"), x.get("markPrice"), x.get("indexPrice"),
             x.get("fundingRate"), x.get("openInterestValue")) for x in d["result"]["list"]]


def fetch_hl():
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=json.dumps({"type": "metaAndAssetCtxs"}).encode(),
                                 headers=dict(UA, **{"Content-Type": "application/json"}))
    d = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT_S).read())
    uni, ctx = d[0]["universe"], d[1]; assert len(uni) == len(ctx), ("hl universe/ctx length", len(uni), len(ctx))
    return [(u.get("name"), None, c.get("midPx"), None, None, c.get("markPx"), c.get("oraclePx"), c.get("funding"), c.get("openInterest"))
            for u, c in zip(uni, ctx)]


VENUES = {"okx": fetch_okx, "bybit": fetch_bybit, "hl": fetch_hl}


def atomic_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    assert json.load(open(path)) == json.loads(json.dumps(obj)), "heartbeat read-back mismatch"


def main():
    for d in ("data", "state", "logs"): os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    t0 = now_ms(); logp = os.path.join(ROOT, "logs", f"collect_{utc_date(t0)}.log")
    lock = open(os.path.join(ROOT, "state", "run.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        with open(logp, "a") as f: f.write(f"{t0} SKIP_LOCKED\n")
        return
    free_gb = shutil.disk_usage(ROOT).free / 2 ** 30
    if free_gb < MIN_FREE_GB:
        with open(logp, "a") as f: f.write(f"{t0} DISK_LOW free_gb={free_gb:.1f}\n")
        return
    stp = os.path.join(ROOT, "state", "venues.json")
    try:
        st = json.load(open(stp))
    except Exception:
        st = {}
    res = {}
    for v, fn in VENUES.items():
        vs = st.setdefault(v, {"last_ok_ms": 0, "last_try_ms": 0, "fail_streak": 0, "backoff_until_ms": 0})
        if t0 < vs["backoff_until_ms"] or t0 - vs["last_try_ms"] < MIN_INTERVAL_S * 1000:
            res[v] = "skip"; continue
        vs["last_try_ms"] = t0
        try:
            rows = fn(); recv = now_ms()
            out = os.path.join(ROOT, "data", utc_date(recv)); os.makedirs(out, exist_ok=True)
            body = "".join(",".join([str(recv), v] + [s(x) for x in r]) + "\n" for r in rows).encode()
            with gzip.open(os.path.join(out, f"{v}.csv.gz"), "ab") as f: f.write(body)
            vs.update(last_ok_ms=recv, fail_streak=0, backoff_until_ms=0, last_rows=len(rows)); res[v] = f"ok:{len(rows)}"
        except Exception as e:
            vs["fail_streak"] += 1
            vs["backoff_until_ms"] = t0 + min(60_000 * 2 ** (vs["fail_streak"] - 1), 1_800_000)
            vs["last_error"] = f"{type(e).__name__}: {str(e)[:200]}"; res[v] = f"ERR:{type(e).__name__}"
    atomic_json(stp, st)
    atomic_json(os.path.join(ROOT, "state", "heartbeat.json"), {"version": VERSION, "run_ms": t0, "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 / 1000)),
                                                                 "result": res, "free_gb": round(free_gb, 1)})
    with open(logp, "a") as f: f.write(f"{t0} RUN " + " ".join(f"{k}={v}" for k, v in res.items()) + "\n")


if __name__ == "__main__":
    main()
