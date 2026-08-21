'''B4 宽宇宙: S3 列目录取全部 USDT 永续符号 → 下载缺失的 5m klines(纯网络, 幂等)'''
import os, time, urllib.request, urllib.error, re
from concurrent.futures import ThreadPoolExecutor
BASE = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
syms, marker = [], ''
while True:
    u = BASE + '?delimiter=/&prefix=data/futures/um/monthly/klines/' + (('&marker=' + marker) if marker else '')
    xml = urllib.request.urlopen(u, timeout=30).read().decode()
    ps = re.findall(r'<Prefix>data/futures/um/monthly/klines/([A-Z0-9]+)/</Prefix>', xml)
    syms += ps
    if '<IsTruncated>true' in xml and ps:
        marker = 'data/futures/um/monthly/klines/' + ps[-1] + '/'
    else:
        break
syms = sorted(set(s for s in syms if s.endswith('USDT')))
open('/workspace/panel_symbols_wide.txt', 'w').write('|'.join(syms))
old = set(open('/workspace/panel_symbols.txt').read().strip().split('|'))
new = [s for s in syms if s not in old]
print(f'全宇宙USDT {len(syms)}, 已有 {len(old)}, 新增 {len(new)}', flush=True)
D = '/workspace/klines5m'
CDN = 'https://data.binance.vision/data/futures/um'
months = [f'{y}-{m:02d}' for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
jobs = []
for s in new:
    os.makedirs(f'{D}/{s}', exist_ok=True)
    for mo in months:
        f = f'{D}/{s}/{s}-5m-{mo}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/monthly/klines/{s}/5m/{s}-5m-{mo}.zip', f))
    for i in range(1, 13):
        d = f'2026-08-{i:02d}'
        f = f'{D}/{s}/{s}-5m-{d}.zip'
        if not (os.path.exists(f) and os.path.getsize(f) > 0):
            jobs.append((f'{CDN}/daily/klines/{s}/5m/{s}-5m-{d}.zip', f))
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
with ThreadPoolExecutor(max_workers=16) as ex:
    for i, _ in enumerate(ex.map(get, jobs)):
        if (i+1) % 2000 == 0: print(i+1, 'ok', ok, 'ab', ab, 'rt', rt, flush=True)
print('WIDE_DL_DONE ok', ok, 'ab', ab, 'rt', rt, flush=True)
