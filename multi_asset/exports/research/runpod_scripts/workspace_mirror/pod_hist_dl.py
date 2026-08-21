"""§28 回溯下载 @pod: 2020-01..2021-12 月度 5m klines(829 币, 未上市自然 404)+ funding 月度(450 币).
写入既有目录树(/workspace/klines5m/<S>/<S>-5m-YYYY-MM.zip 与 wide_multisrc/funding/<S>/YYYY-MM.zip), 幂等.
"""
import os, glob, socket, urllib.request, urllib.error, threading, queue, time

socket.setdefaulttimeout(30)
MONTHS = [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13)]
K_SYMS = sorted(open("/workspace/panel_symbols_wide.txt").read().strip().split("|"))
F_SYMS = sorted(os.path.basename(d) for d in glob.glob("/workspace/wide_multisrc/funding/*"))
BASE = "https://data.binance.vision/data/futures/um/monthly"
JOBS = []
for s in K_SYMS:
    for m in MONTHS:
        JOBS.append((f"/workspace/klines5m/{s}/{s}-5m-{m}.zip", f"{BASE}/klines/{s}/5m/{s}-5m-{m}.zip"))
for s in F_SYMS:
    for m in MONTHS:
        JOBS.append((f"/workspace/wide_multisrc/funding/{s}/{m}.zip", f"{BASE}/fundingRate/{s}/{s}-fundingRate-{m}.zip"))
q = queue.Queue()
for j in JOBS: q.put(j)
ok = [0]; miss = [0]; err = [0]; lock = threading.Lock()
def worker():
    while True:
        try: out, url = q.get_nowait()
        except queue.Empty: return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out) or os.path.exists(out + ".404"):
            with lock: ok[0] += 1
            q.task_done(); continue
        try:
            urllib.request.urlretrieve(url, out + ".part")
            os.rename(out + ".part", out)
            with lock: ok[0] += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(out + ".404", "w").close()
                with lock: miss[0] += 1
            else:
                with lock: err[0] += 1
        except Exception:
            try: os.remove(out + ".part")
            except OSError: pass
            with lock: err[0] += 1
        q.task_done()
ths = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
for t in ths: t.start()
while any(t.is_alive() for t in ths):
    time.sleep(30)
    print(f"ok {ok[0]} miss404 {miss[0]} err {err[0]} left {q.qsize()}", flush=True)
print(f"HIST_DL_DONE ok {ok[0]} miss404 {miss[0]} err {err[0]}", flush=True)
