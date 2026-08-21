#!/bin/bash
while ! grep -q WIDE_DL_DONE /workspace/wide_dl.log 2>/dev/null; do sleep 600; done
/usr/bin/python3 - <<'PYS2'
import os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
SY = open('/workspace/panel_symbols.txt').read().strip().split('|')
def spot_name(s):
    return s[4:] if s.startswith('1000') else s
D = '/workspace/spot5m'; os.makedirs(D, exist_ok=True)
CDN = 'https://data.binance.vision/data/spot'
months = [f'{y}-{m:02d}' for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
jobs = []
for s in SY:
    sp = spot_name(s)
    os.makedirs(f'{D}/{sp}', exist_ok=True)
    for mo in months:
        f = f'{D}/{sp}/{sp}-5m-{mo}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/monthly/klines/{sp}/5m/{sp}-5m-{mo}.zip', f))
print('spot dl jobs', len(jobs), flush=True)
ok = ab = 0
def get(j):
    global ok, ab
    url, out = j
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r: data = r.read()
            open(out + '.part', 'wb').write(data); os.replace(out + '.part', out); ok += 1; return
        except urllib.error.HTTPError as e:
            if e.code == 404: ab += 1; return
            time.sleep(2*(a+1))
        except Exception: time.sleep(2*(a+1))
with ThreadPoolExecutor(max_workers=16) as ex:
    list(ex.map(get, jobs))
print('SPOT_DL_DONE ok', ok, 'ab', ab, flush=True)
PYS2
