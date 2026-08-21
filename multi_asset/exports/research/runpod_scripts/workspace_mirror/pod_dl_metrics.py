'''L1-b: metrics(含OI) 日文件下载(过夜, 网络型, 不占GPU); 只下载不建缓存'''
import os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
SY = open('/workspace/panel_symbols.txt').read().strip().split('|')
D = '/workspace/metrics5m'; os.makedirs(D, exist_ok=True)
CDN = 'https://data.binance.vision/data/futures/um'
dates = [d.strftime('%Y-%m-%d') for d in pd.date_range('2022-01-01', '2026-08-11', freq='D')]
jobs = []
for s in SY:
    os.makedirs(f'{D}/{s}', exist_ok=True)
    for dt in dates:
        f = f'{D}/{s}/{s}-metrics-{dt}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/daily/metrics/{s}/{s}-metrics-{dt}.zip', f))
print('dl jobs', len(jobs), flush=True)
ok = ab = rt = 0
def get(j):
    global ok, ab, rt
    url, out = j
    for a in range(4):
        try:
            with urllib.request.urlopen(url, timeout=40) as r: data = r.read()
            open(out + '.part', 'wb').write(data); os.replace(out + '.part', out); ok += 1; return
        except urllib.error.HTTPError as e:
            if e.code == 404: ab += 1; return
            time.sleep(2*(a+1))
        except Exception: time.sleep(2*(a+1))
    rt += 1
with ThreadPoolExecutor(max_workers=24) as ex:
    for i, _ in enumerate(ex.map(get, jobs)):
        if (i+1) % 10000 == 0: print(i+1, 'ok', ok, 'ab', ab, 'rt', rt, flush=True)
print('METRICS_DL_DONE ok', ok, 'ab', ab, 'rt', rt, flush=True)
