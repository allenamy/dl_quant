'''L1-b: metrics 日文件 -> OI 4通道 5m 缓存; 原子写+锁'''
import os, glob, zipfile, io
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
LOCK = '/workspace/oi.lock'
fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd)
SY = open('/workspace/panel_symbols.txt').read().strip().split('|')
D = '/workspace/metrics5m'
IDX = pd.date_range('2022-01-01', '2026-08-11', freq='5min')
def build(sym):
    ks = []
    for f in sorted(glob.glob(f'{D}/{sym}/*.zip')):
        try:
            with zipfile.ZipFile(f) as z: raw = z.read(z.namelist()[0])
            d = pd.read_csv(io.BytesIO(raw))
            ks.append(d)
        except Exception: continue
    if not ks: return sym, None
    k = pd.concat(ks)
    k.columns = [c.strip().lower() for c in k.columns]
    k['ts'] = pd.to_datetime(k['create_time'])
    k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
    A = np.full((len(IDX), 4), np.nan, np.float16)
    oi = k['sum_open_interest'].astype(float)
    A[:,0] = np.clip(np.log(oi.replace(0, np.nan)).diff(), -0.1, 0.1)
    for j, c in enumerate(['sum_toptrader_long_short_ratio', 'count_long_short_ratio', 'sum_taker_long_short_vol_ratio']):
        if c in k.columns:
            A[:,1+j] = np.clip(np.log(k[c].astype(float).replace(0, np.nan)), -2, 2)
    return sym, A
if __name__ == '__main__':
    res = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, (s, arr) in enumerate(ex.map(build, SY)):
            res[s] = arr
            if (i+1) % 20 == 0: print('build', i+1, flush=True)
    data = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 4), np.nan, np.float16) for s in SY], axis=1)
    tmp = '/workspace/data/.tmp_oi4.npz'
    np.savez_compressed(tmp, ts=np.array(IDX, dtype='datetime64[s]').astype(np.int64), symbols=np.array(SY),
                        ch=np.array(['d_log_oi','top_ls','cnt_ls','taker_ls']), data=data)
    os.replace(tmp, '/workspace/data/dlnative_5m_oi4_f16.npz')
    os.remove(LOCK)
    fin = np.isfinite(data[::37].astype(np.float32)).mean()
    print('OI_BUILT', data.shape, 'finite %.4f' % fin, flush=True)
