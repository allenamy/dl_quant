"""R6 EXTEND step 1/2: fetch data.binance.vision daily 5m klines for 2026-08-31..2026-09-10.
Frontier FROZEN by date at 2026-09-10 (PREREG §1.1). Global token bucket <= 4 req/s (hard cap).
Anchor-window guard: sleeps through HH:00-HH:57 of 00/04/08/12/16/20 UTC (PREREG §8.5).
Writes ONLY under /workspace/uplift_2026-09-11/r6/ — the shared wide_multisrc tree is NOT mutated.
"""
import os, time, threading, queue, urllib.request, urllib.error, socket, json, sys

socket.setdefaulttimeout(60)
SYMS = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
DAYS = ["2026-08-31"] + [f"2026-09-{d:02d}" for d in range(1, 11)]   # 11 days, frontier 09-10 inclusive
OUT = "/workspace/uplift_2026-09-11/r6/dl/klines"
BASE = "https://data.binance.vision/data/futures/um/daily/klines"
RATE = 4.0

_lk = threading.Lock(); _next = [time.time()]
def token():
    while True:
        with _lk:
            now = time.time()
            if now >= _next[0]:
                _next[0] = max(now, _next[0]) + 1.0 / RATE
                slp = 0.0
            else:
                slp = _next[0] - now
        if slp <= 0: return
        time.sleep(slp)

def anchor_guard():
    while True:
        t = time.gmtime()
        if t.tm_hour % 4 == 0 and t.tm_min < 57:
            time.sleep(30); continue
        return

JOBS = [(s, d) for s in SYMS for d in DAYS]
q = queue.Queue()
for j in JOBS: q.put(j)
ok=[0]; miss=[0]; err=[0]; lock=threading.Lock()

def worker():
    while True:
        try: s, d = q.get_nowait()
        except queue.Empty: return
        od = f"{OUT}/{s}"; os.makedirs(od, exist_ok=True)
        out = f"{od}/{d}.zip"
        if os.path.exists(out) or os.path.exists(out + ".404"):
            with lock: ok[0]+=1
            continue
        anchor_guard(); token()
        url = f"{BASE}/{s}/5m/{s}-5m-{d}.zip"
        try:
            urllib.request.urlretrieve(url, out + ".part")
            os.rename(out + ".part", out)
            with lock: ok[0]+=1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(out + ".404","w").close()
                with lock: miss[0]+=1
            else:
                with lock: err[0]+=1
        except Exception:
            try: os.remove(out + ".part")
            except OSError: pass
            with lock: err[0]+=1

ths=[threading.Thread(target=worker, daemon=True) for _ in range(6)]
for t in ths: t.start()
while any(t.is_alive() for t in ths):
    time.sleep(20)
    print(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] ok {ok[0]} miss404 {miss[0]} err {err[0]} left {q.qsize()}", flush=True)
print(f"R6_KLINES_DL_DONE ok {ok[0]} miss404 {miss[0]} err {err[0]} jobs {len(JOBS)}", flush=True)
json.dump({"ok":ok[0],"miss404":miss[0],"err":err[0],"jobs":len(JOBS),"days":DAYS,"rate_cap_rps":RATE,
           "finished_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},
          open("/workspace/uplift_2026-09-11/r6/dl/klines_dl_receipt.json","w"), indent=1)
