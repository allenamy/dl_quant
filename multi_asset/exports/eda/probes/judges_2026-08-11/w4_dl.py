"""W4 数据面: metrics 增量(2026-07-01..08-10) + 5m klines 全史(2022-01..2026-07 月度 + 08 日度)。
遵循 track-2 地雷手册: 只走 CDN GET(不依赖 S3 listing); 404=真缺(记 absent), 超时/5xx=RETRY 名单;
已存在非空文件跳过(幂等可重跑)。"""
import os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
CDN = "https://data.binance.vision/data/futures/um"
syms = sorted(os.listdir(f"{M}/wide_metrics_raw"))
jobs = []
import datetime as dt
for s in syms:
    for i in range(41):
        d = (dt.date(2026, 7, 1) + dt.timedelta(i)).isoformat()
        f = f"{M}/wide_metrics_raw/{s}/{s}-metrics-{d}.zip"
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f"{CDN}/daily/metrics/{s}/{s}-metrics-{d}.zip", f))
    os.makedirs(f"{M}/w4_klines5m/{s}", exist_ok=True)
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if (y, m) <= (2026, 7)]
    for mo in months:
        f = f"{M}/w4_klines5m/{s}/{s}-5m-{mo}.zip"
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f"{CDN}/monthly/klines/{s}/5m/{s}-5m-{mo}.zip", f))
    for i in range(1, 11):
        d = f"2026-08-{i:02d}"
        f = f"{M}/w4_klines5m/{s}/{s}-5m-{d}.zip"
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f"{CDN}/daily/klines/{s}/5m/{s}-5m-{d}.zip", f))
print(f"jobs={len(jobs)}", flush=True)
absent, retry, ok = [], [], 0
def get(j):
    global ok
    url, out = j
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            with open(out + ".part", "wb") as w:
                w.write(data)
            os.replace(out + ".part", out)
            ok += 1
            return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                absent.append(url); return
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    retry.append(url)
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, _ in enumerate(ex.map(get, jobs)):
        if (i + 1) % 1000 == 0:
            print(f"{i+1}/{len(jobs)} ok={ok} absent={len(absent)} retry={len(retry)}", flush=True)
print(f"FINAL ok={ok} absent={len(absent)} retry={len(retry)}", flush=True)
with open(f"{M}/w4_dl_absent.txt", "w") as w: w.write("\n".join(absent))
with open(f"{M}/w4_dl_retry.txt", "w") as w: w.write("\n".join(retry))
# 完整性对账: 每 symbol 报 5m 覆盖首末月(区分"晚上市"与"截断")
for s in syms[:5]:
    fs = sorted(os.listdir(f"{M}/w4_klines5m/{s}"))
    print(f"  {s}: {len(fs)} files {fs[0] if fs else '-'} .. {fs[-1] if fs else '-'}", flush=True)
print("W4_DL_DONE", flush=True)
