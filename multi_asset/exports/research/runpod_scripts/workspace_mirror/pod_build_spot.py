'''build-only rebuild: raw zips -> tmp npz -> atomic os.replace; lock guards double-run'''
import os, glob, zipfile, io
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
LOCK = '/workspace/spot.lock'
fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
os.write(fd, str(os.getpid()).encode()); os.close(fd)
SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
D = '/workspace/spot5m'
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
if __name__ == '__main__':
    res = {}
    with ProcessPoolExecutor(max_workers=12) as ex:
        for i, (s, arr) in enumerate(ex.map(build, SY)):
            res[s] = arr
            if (i+1) % 20 == 0: print('build', i+1, flush=True)
    data = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in SY], axis=1)
    tmp = '/workspace/data/.tmp_spot.npz'
    np.savez_compressed(tmp, ts=np.array(IDX, dtype='datetime64[s]').astype(np.int64), symbols=np.array(SY),
                        ch=np.array(['ret5','range','cpos','log_qv','log_cnt','log_avgsz','tbf']), data=data)
    os.replace(tmp, '/workspace/data/dlnative_5m_spot_f16.npz')
    os.remove(LOCK)
    print('REBUILT', data.shape, flush=True)
