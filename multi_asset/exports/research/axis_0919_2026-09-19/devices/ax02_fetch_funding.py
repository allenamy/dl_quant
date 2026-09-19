"""AX02 (axis_0919, stream D): funding settlement records from the PUBLIC REST endpoint (no credentials).
  GET https://fapi.binance.com/fapi/v1/fundingInfo                       (declared intervals AT FETCH TIME — recorded, never used as a settlement's interval)
  GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=S&startTime=A&endTime=B&limit=1000   (every settlement in [A, B])
data.binance.vision has no daily fundingRate and no 2026-09 monthly (r6 VERIFIED 404), so REST is the source (precedent: fund_aug.json.gz, r6_fund_sep).
Window: AX_START_MS .. AX_END_MS (inclusive). Raw JSON rows are kept verbatim (fundingTime, fundingRate, markPrice).
Rate: fundingRate shares a 500 req / 5 min / IP budget with fundingInfo => global token bucket AX_RPS (default 1.4 req/s = 420 / 5 min).
429/418: honour Retry-After, back off; a 418 (IP ban) aborts the run. Anchor-window guard as r6 (HH:00-HH:57 of 00/04/08/12/16/20 UTC).
Writes ONLY $AX_ROOT/dl/funding/<tag>.json.gz and $AX_ROOT/receipts/FUNDING_REST_<tag>.json (refuses to overwrite either).
"""
import os, sys, json, gzip, time, hashlib, threading, queue, socket, urllib.request, urllib.error

socket.setdefaulttimeout(30)
ROOT = os.environ["AX_ROOT"]; TAG = os.environ["AX_TAG"]
START_MS = int(os.environ["AX_START_MS"]); END_MS = int(os.environ["AX_END_MS"])
RATE = float(os.environ.get("AX_RPS", "1.4"))
SYMS = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
OUT = f"{ROOT}/dl/funding/{TAG}.json.gz"; RPT = f"{ROOT}/receipts/FUNDING_REST_{TAG}.json"
for p in (OUT, RPT): assert not os.path.exists(p), f"refuse to overwrite {p}"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
_lk = threading.Lock(); _next = [time.time()]; ABORT = [None]
def token():
    while True:
        with _lk:
            now = time.time()
            if now >= _next[0]: _next[0] = max(now, _next[0]) + 1.0 / RATE; return
            slp = _next[0] - now
        time.sleep(slp)
def anchor_guard():
    while True:
        t = time.gmtime()
        if t.tm_hour % 4 == 0 and t.tm_min < 57: time.sleep(30); continue
        return
def get(url):
    for attempt in range(6):
        if ABORT[0]: raise RuntimeError("aborted: " + ABORT[0])
        anchor_guard(); token()
        req = urllib.request.Request(url, headers={"User-Agent": "research-readonly/1.0"})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read()), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 418: ABORT[0] = "HTTP 418 IP ban"; raise
            if e.code == 429:
                ra = float(e.headers.get("Retry-After") or 60); print(f"429 Retry-After {ra}", flush=True)
                with _lk: _next[0] = max(_next[0], time.time() + ra)
                continue
            raise
        except urllib.error.URLError:
            time.sleep(5 * (attempt + 1)); continue
    raise RuntimeError("retries exhausted " + url)

t0 = time.time()
info, hdr = get("https://fapi.binance.com/fapi/v1/fundingInfo")
INFO = {d["symbol"]: d for d in info}
print(f"fundingInfo rows {len(INFO)} used-weight {hdr.get('X-MBX-USED-WEIGHT-1M')}", flush=True)
rates = {}; status = {}; lock = threading.Lock()
q = queue.Queue()
for s in SYMS: q.put(s)
def worker():
    while True:
        try: s = q.get_nowait()
        except queue.Empty: return
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={s}&startTime={START_MS}&endTime={END_MS}&limit=1000"
        try:
            j, _ = get(url)
            with lock:
                rates[s] = j; status[s] = "OK" if j else "EMPTY"
                if len(j) >= 1000: status[s] = "TRUNCATED_1000"
        except urllib.error.HTTPError as e:
            with lock: status[s] = f"HTTP_{e.code}"
        except Exception as e:
            with lock: status[s] = "ERR " + repr(e)[:120]
ths = [threading.Thread(target=worker, daemon=True) for _ in range(3)]
for t in ths: t.start()
while any(t.is_alive() for t in ths):
    time.sleep(20)
    with lock:
        c = {}
        for v in status.values(): c[v.split()[0]] = c.get(v.split()[0], 0) + 1
    print(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] {c} left {q.qsize()}", flush=True)
allt = [int(r["fundingTime"]) for v in rates.values() for r in v]
cnt = {}
for v in status.values(): cnt[v.split()[0]] = cnt.get(v.split()[0], 0) + 1
meta = {"source": "https://fapi.binance.com/fapi/v1/fundingRate + /fapi/v1/fundingInfo (public, no credentials)",
        "start_ms": START_MS, "end_ms": END_MS, "n_symbols_requested": len(SYMS), "status_counts": cnt,
        "n_rows": len(allt), "min_utc": time.strftime("%F %H:%M:%SZ", time.gmtime(min(allt) / 1000)) if allt else None,
        "max_utc": time.strftime("%F %H:%M:%SZ", time.gmtime(max(allt) / 1000)) if allt else None,
        "fetched_start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        "fetched_end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rate_cap_rps": RATE, "abort": ABORT[0]}
blob = json.dumps({"rates_raw": rates, "status": status, "fundingInfo_at_fetch": INFO, "meta": meta}, sort_keys=True).encode()
with open(OUT + ".tmp", "wb") as f: f.write(gzip.compress(blob, mtime=0))
os.replace(OUT + ".tmp", OUT)
h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
rep = dict(meta, out=OUT, out_sha256=h, self_sha256=hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           non_ok={s: v for s, v in status.items() if v not in ("OK", "EMPTY")})
json.dump(rep, open(RPT, "w"), indent=1)
print("AX02_DONE", json.dumps({k: rep[k] for k in ("status_counts", "n_rows", "min_utc", "max_utc", "abort")}), h[:16], flush=True)
