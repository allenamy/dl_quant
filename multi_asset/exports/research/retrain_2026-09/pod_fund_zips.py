"""funding 月度 zip 全量下载 @pod: data.binance.vision monthly fundingRate(含 funding_interval_hours 真值列).
动机(2026-09-01 门①全列版红): 空 zip 目录 ⇒ interval 全靠时间差推断 ⇒ ema_v1/v2 normfix 递归污染
(f_fund_iv exact 99.96% → f_fund_ema_v1 corr 0.9796)。zip 供 2019-09..2026-08, AUG 只补 API 尾巴。
产物: /workspace/wide_multisrc/funding/<SYM>/<YYYY-MM>.zip; 8 线程, 404 记账不重试, 幂等。
"""
import os, socket, urllib.request, urllib.error, threading, queue

socket.setdefaulttimeout(30)
SYMS = open("/workspace/panel_symbols_wide.txt").read().strip().split("|")
MONTHS = [f"{y}-{m:02d}" for y in range(2019, 2027) for m in range(1, 13)][8:-4]  # 2019-09..2026-08
BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
q = queue.Queue()
for s in SYMS:
    for d in MONTHS:
        q.put((f"{BASE}/{s}/{s}-fundingRate-{d}.zip", s, d))
ok = [0]; miss = [0]; err = [0]; lock = threading.Lock()

def worker():
    while True:
        try: url, s, d = q.get_nowait()
        except queue.Empty: return
        out_dir = f"/workspace/wide_multisrc/funding/{s}"
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
    time.sleep(20)
    print(f"ok {ok[0]} miss404 {miss[0]} err {err[0]} left {q.qsize()}", flush=True)
print(f"FUND_ZIPS_DONE ok {ok[0]} miss404 {miss[0]} err {err[0]}", flush=True)
