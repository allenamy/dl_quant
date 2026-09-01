"""缓存延长下载 @pod: Vision daily zips 08-10..08-15, klines5m + premiumIndexKlines5m.
450 现存币(以 wide_multisrc/klines5m 目录为准), 8 线程, 404 记账不重试(新币缺日正常).
产物: /workspace/wide_multisrc/{klines5m,premidx}_daily/<SYM>/<date>.zip
"""
import os, glob, socket, urllib.request, urllib.error, threading, queue, sys

socket.setdefaulttimeout(30)
DAYS = (os.environ.get("EXT_DAYS") or "2026-08-10,2026-08-11,2026-08-12,2026-08-13,2026-08-14,2026-08-15").split(",")
SYMS = sorted(os.path.basename(d) for d in glob.glob("/workspace/wide_multisrc/klines5m/*"))
BASE = "https://data.binance.vision/data/futures/um/daily"
JOBS = []
for s in SYMS:
    for d in DAYS:
        JOBS.append(("klines5m_daily", f"{BASE}/klines/{s}/5m/{s}-5m-{d}.zip", s, d))
        JOBS.append(("premidx_daily", f"{BASE}/premiumIndexKlines/{s}/5m/{s}-5m-{d}.zip", s, d))
q = queue.Queue()
for j in JOBS: q.put(j)
ok = [0]; miss = [0]; err = [0]; lock = threading.Lock()

def worker():
    while True:
        try: kind, url, s, d = q.get_nowait()
        except queue.Empty: return
        out_dir = f"/workspace/wide_multisrc/{kind}/{s}"
        os.makedirs(out_dir, exist_ok=True)
        out = f"{out_dir}/{d}.zip"
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
import time
while any(t.is_alive() for t in ths):
    time.sleep(15)
    print(f"ok {ok[0]} miss404 {miss[0]} err {err[0]} left {q.qsize()}", flush=True)
print(f"EXTEND_DL_DONE ok {ok[0]} miss404 {miss[0]} err {err[0]}", flush=True)
