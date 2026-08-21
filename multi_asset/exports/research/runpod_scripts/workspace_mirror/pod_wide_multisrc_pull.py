"""pod 宽币多源下载器(data.binance.vision; 404快跳/超时重试/可续).
用法: python3 pod_wide_multisrc_pull.py <src> <syms.txt> <start> <end> [workers]
  src ∈ funding | premidx | markpx | idxpx | metrics | spot5m
  monthly 类 start/end = 2022-01 2026-08; metrics(daily) = 2023-01-01 2026-08-14
落盘: /workspace/wide_multisrc/<src>/<sym>/<期>.zip
"""
import sys, os, time, socket, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
socket.setdefaulttimeout(30)

SRC = {
    'klines5m': ('monthly', 'data/futures/um/monthly/klines/{s}/5m/{s}-5m-{p}.zip'),
    'funding': ('monthly', 'data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{p}.zip'),
    'premidx': ('monthly', 'data/futures/um/monthly/premiumIndexKlines/{s}/5m/{s}-5m-{p}.zip'),
    'markpx':  ('monthly', 'data/futures/um/monthly/markPriceKlines/{s}/5m/{s}-5m-{p}.zip'),
    'idxpx':   ('monthly', 'data/futures/um/monthly/indexPriceKlines/{s}/5m/{s}-5m-{p}.zip'),
    'metrics': ('daily',   'data/futures/um/daily/metrics/{s}/{s}-metrics-{p}.zip'),
    'spot5m':  ('monthly', 'data/spot/monthly/klines/{s}/5m/{s}-5m-{p}.zip'),
}

def months(a, b):
    ya, ma = map(int, a.split('-')); yb, mb = map(int, b.split('-'))
    out = []
    while (ya, ma) <= (yb, mb):
        out.append(f'{ya}-{ma:02d}'); ma += 1
        if ma > 12: ma = 1; ya += 1
    return out

def days(a, b):
    import datetime as dt
    d0 = dt.date.fromisoformat(a); d1 = dt.date.fromisoformat(b)
    return [(d0 + dt.timedelta(n)).isoformat() for n in range((d1 - d0).days + 1)]

src = sys.argv[1]; gran, tmpl = SRC[src]
syms = open(sys.argv[2]).read().split()
periods = months(sys.argv[3], sys.argv[4]) if gran == 'monthly' else days(sys.argv[3], sys.argv[4])
workers = int(sys.argv[5]) if len(sys.argv) > 5 else 24
base = f'/workspace/wide_multisrc/{src}'

jobs = []
for s in syms:
    d = f'{base}/{s}'; os.makedirs(d, exist_ok=True)
    for p in periods:
        fp = f'{d}/{p}.zip'
        if os.path.exists(fp) and os.path.getsize(fp) > 100: continue
        if os.path.exists(fp + '.404'): continue
        jobs.append((tmpl.format(s=s, p=p), fp))
print(f'{src}: {len(jobs)} 待下 ({len(syms)} 币 × {len(periods)} 期, 已存在即跳)', flush=True)

cnt = {'ok': 0, 'miss': 0, 'fail': 0}
def pull(job):
    u, fp = job
    for att in range(3):
        try:
            urllib.request.urlretrieve('https://data.binance.vision/' + u, fp)
            cnt['ok'] += 1; return
        except urllib.error.HTTPError as e:
            if os.path.exists(fp): os.remove(fp)
            if e.code == 404:
                open(fp + '.404', 'w').close(); cnt['miss'] += 1; return
            time.sleep(2)
        except Exception:
            if os.path.exists(fp): os.remove(fp)
            time.sleep(2)
    cnt['fail'] += 1

with ThreadPoolExecutor(max_workers=workers) as ex:
    t0 = time.time(); last = 0
    for i, _ in enumerate(ex.map(pull, jobs)):
        if time.time() - last > 30:
            last = time.time()
            done = cnt['ok'] + cnt['miss'] + cnt['fail']
            print(f'{done}/{len(jobs)} ok={cnt["ok"]} 404={cnt["miss"]} fail={cnt["fail"]} '
                  f'{done/max(time.time()-t0,1):.1f}/s', flush=True)
print(f'MULTISRC_DONE {src} ok={cnt["ok"]} 404={cnt["miss"]} fail={cnt["fail"]}', flush=True)
