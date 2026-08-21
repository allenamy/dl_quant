import os, time, urllib.request, urllib.error, json
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
D = '/workspace/klines5m'; os.makedirs(D, exist_ok=True)
CDN = 'https://data.binance.vision/data/futures/um'
info = json.loads(urllib.request.urlopen('https://fapi.binance.com/fapi/v1/exchangeInfo', timeout=30).read())
syms = sorted(s['symbol'] for s in info['symbols'] if s['symbol'].endswith('USDT'))
months = [f'{y}-{m:02d}' for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
jobs = []
for s in syms:
    os.makedirs(f'{D}/{s}', exist_ok=True)
    for mo in months:
        f = f'{D}/{s}/{s}-5m-{mo}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/monthly/klines/{s}/5m/{s}-5m-{mo}.zip', f))
    for i in range(1, 12):
        d = f'2026-08-{i:02d}'
        f = f'{D}/{s}/{s}-5m-{d}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/daily/klines/{s}/5m/{s}-5m-{d}.zip', f))
print('jobs', len(jobs), flush=True)
ok = ab = rt = 0
def get(j):
    global ok, ab, rt
    url, out = j
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: data = r.read()
            open(out + '.part', 'wb').write(data); os.replace(out + '.part', out); ok += 1; return
        except urllib.error.HTTPError as e:
            if e.code == 404: ab += 1; return
            time.sleep(2*(a+1))
        except Exception: time.sleep(2*(a+1))
    rt += 1
with ThreadPoolExecutor(max_workers=12) as ex:
    for i, _ in enumerate(ex.map(get, jobs)):
        if (i+1) % 2000 == 0: print(i+1, 'ok', ok, 'absent', ab, 'retry', rt, flush=True)
print('FINAL ok', ok, 'absent', ab, 'retry', rt, flush=True)
print('POD_DL_DONE', flush=True)
