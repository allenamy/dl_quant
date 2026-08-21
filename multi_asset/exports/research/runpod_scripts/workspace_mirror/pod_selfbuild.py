import os, time, urllib.request, urllib.error, glob, zipfile, io
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np, pandas as pd
SY = open('/workspace/panel_symbols.txt').read().strip().split('|')
D = '/workspace/klines5m'; os.makedirs(D, exist_ok=True)
CDN = 'https://data.binance.vision/data/futures/um'
months = [f'{y}-{m:02d}' for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
jobs = []
for s in SY:
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
        if (i+1) % 1000 == 0: print(i+1, 'ok', ok, 'ab', ab, 'rt', rt, flush=True)
print('DL final ok', ok, 'ab', ab, 'rt', rt, flush=True)
IDX = pd.date_range('2022-01-01', '2026-08-11', freq='5min')
def read_zip(path):
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        return pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    except Exception: return None
def build(sym):
    ks = []
    for f in sorted(glob.glob(f'{D}/{sym}/*.zip')):
        d = read_zip(f)
        if d is None or len(d) == 0: continue
        d.columns = ['open_time','o','h','l','c','v','close_time','qv','cnt','tbv','tbqv'][:d.shape[1]]
        ks.append(d)
    if not ks: return sym, None
    k = pd.concat(ks)
    k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
    k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
    A = np.full((len(IDX), 7), np.nan, np.float16)
    A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)
    A[:,1] = np.clip((k.h-k.l)/k.c, 0, 0.5)
    A[:,2] = ((k.c-k.l)/(k.h-k.l)).clip(0,1)
    A[:,3] = np.log1p(k.qv).clip(0, 25); A[:,4] = np.log1p(k.cnt).clip(0, 20)
    A[:,5] = np.log((k.qv/k.cnt.replace(0,np.nan))).clip(-5, 15)
    A[:,6] = (k.tbqv/k.qv).clip(0,1)
    return sym, A
res = {}
with ProcessPoolExecutor(max_workers=12) as ex:
    for i, (s, arr) in enumerate(ex.map(build, SY)):
        res[s] = arr
        if (i+1) % 20 == 0: print('build', i+1, flush=True)
data = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in SY], axis=1)
np.savez_compressed('/workspace/data/dlnative_5m_k7_f16.npz', ts=np.array(IDX, dtype='datetime64[s]').astype(np.int64),
                    symbols=np.array(SY), ch=np.array(['ret5','range','cpos','log_qv','log_cnt','log_avgsz','tbf']), data=data)
print('BUILT', data.shape, flush=True)
print('SELFBUILD_DONE', flush=True)
