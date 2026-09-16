"""R6 EXTEND: funding rates 2026-08-29 .. now, public REST (fapi.binance.com), NO credentials.
data.binance.vision has NO 2026-09 monthly fundingRate (404, VERIFIED 14:21Z) and publishes no daily fundingRate
(404, VERIFIED), so the bulk archive cannot supply September. REST is the only source and has direct precedent:
the incumbent v4 panel's own August tail is /workspace/fund_aug.json.gz, an API pull of exactly this shape.
Output mirrors fund_aug.json.gz: {"rates": {sym: [[t_ms, rate], ...]}, "intervals": {sym: hours}}.
<=4 req/s global token bucket; sleeps through anchor windows (HH:00-HH:57 of 00/04/08/12/16/20 UTC).
"""
import os, json, gzip, time, threading, queue, urllib.request, urllib.error, socket
socket.setdefaulttimeout(30)
SYMS = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
START_MS = 1787961600000   # 2026-08-28 00:00:00Z  (well before the splice cut 2026-08-31 00:00Z)
OUT = "/workspace/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz"
RATE = 4.0
_lk = threading.Lock(); _next = [time.time()]
def token():
    while True:
        with _lk:
            now = time.time()
            if now >= _next[0]: _next[0] = max(now, _next[0]) + 1.0/RATE; return
            slp = _next[0] - now
        time.sleep(slp)
def anchor_guard():
    while True:
        t = time.gmtime()
        if t.tm_hour % 4 == 0 and t.tm_min < 57: time.sleep(30); continue
        return
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "research-readonly/1.0"})
    with urllib.request.urlopen(req) as r: return json.loads(r.read())

anchor_guard(); token()
try:
    INFO = {d["symbol"]: float(d["fundingIntervalHours"]) for d in get("https://fapi.binance.com/fapi/v1/fundingInfo")
            if "fundingIntervalHours" in d}
except Exception as e:
    INFO = {}; print("fundingInfo failed:", e, flush=True)
print(f"fundingInfo: {len(INFO)} symbols with a declared interval", flush=True)

rates = {}; ok=[0]; empty=[0]; err=[0]; lock=threading.Lock()
q = queue.Queue()
for s in SYMS: q.put(s)
def worker():
    while True:
        try: s = q.get_nowait()
        except queue.Empty: return
        anchor_guard(); token()
        try:
            j = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={s}&startTime={START_MS}&limit=1000")
            rows = [[int(d["fundingTime"]), float(d["fundingRate"])] for d in j]
            with lock:
                if rows: rates[s] = rows; ok[0]+=1
                else: empty[0]+=1
        except urllib.error.HTTPError as e:
            with lock:
                (empty if e.code == 400 else err)[0] += 1
        except Exception:
            with lock: err[0]+=1
ths=[threading.Thread(target=worker, daemon=True) for _ in range(4)]
for t in ths: t.start()
while any(t.is_alive() for t in ths):
    time.sleep(20); print(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] ok {ok[0]} empty {empty[0]} err {err[0]} left {q.qsize()}", flush=True)
allt = [t for v in rates.values() for t,_ in v]
meta = {"n_symbols": len(rates), "n_rows": len(allt),
        "min_utc": time.strftime("%F %H:%MZ", time.gmtime(min(allt)/1000)) if allt else None,
        "max_utc": time.strftime("%F %H:%MZ", time.gmtime(max(allt)/1000)) if allt else None,
        "ok": ok[0], "empty": empty[0], "err": err[0], "start_ms": START_MS,
        "source": "https://fapi.binance.com/fapi/v1/fundingRate (public, no credentials)",
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
with gzip.open(OUT, "wt") as f: json.dump({"rates": rates, "intervals": {k: v for k, v in INFO.items() if k in rates}, "meta": meta}, f)
print("R6_FUND_DONE " + json.dumps(meta), flush=True)
