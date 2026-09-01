"""缓存增量合并(2026-09-01, PREREG c24b8d2f8567 战役): per-symbol 数学逐字自 pod_build_wide_ext.py;
输入=wide_multisrc/klines5m_daily 新zip(08-21起, 首日作warmup), 基底=dlnative_..._fresh.npz(至08-24 04:00);
平价门: 重叠窗(08-22 08:00..08-24 04:00) 有限单元逐位相等率≥99.9%; 过门才写合并产物 _ext.npz."""
import os, glob, zipfile, io
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
D = '/workspace/wide_multisrc/klines5m_daily'
IDX = pd.date_range('2026-08-21', '2026-09-01', freq='5min')
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
            if (i+1) % 100 == 0: print('build', i+1, flush=True)
    ext = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in SY], axis=1)
    ets = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
    base = np.load('/workspace/data/dlnative_5m_wide829_f16_fresh.npz', allow_pickle=True)
    bts = base['ts']; bdat = base['data']
    assert [str(x) for x in base['symbols']] == SY, "符号轴不一致"
    # 平价门: 重叠窗
    lo = int(pd.Timestamp('2026-08-22 08:00').value // 10**9); hi = int(bts[-1])
    bm = (bts >= lo) & (bts <= hi); em = (ets >= lo) & (ets <= hi)
    assert bm.sum() == em.sum() and (bts[bm] == ets[em]).all(), "重叠窗网格不齐"
    B = bdat[bm]; E = ext[em]
    fin = np.isfinite(B) & np.isfinite(E)
    eq = (B[fin] == E[fin]).mean() if fin.any() else 0.0
    nan_mismatch = (np.isfinite(B) ^ np.isfinite(E)).mean()
    print(f"PARITY overlap cells={fin.sum():,} exact_eq={eq:.6f} nan_mismatch={nan_mismatch:.6f}")
    assert eq >= 0.999, f"平价门红: exact_eq={eq}"
    # 合并: 基底全部 + ext 在基底末之后的行
    keep = ets > int(bts[-1])
    mts = np.concatenate([bts, ets[keep]])
    mdat = np.concatenate([bdat, ext[keep]], axis=0)
    np.savez_compressed('/workspace/data/dlnative_5m_wide829_f16_ext.npz.tmp',
                        ts=mts, symbols=base['symbols'], ch=base['ch'], data=mdat)
    os.replace('/workspace/data/dlnative_5m_wide829_f16_ext.npz.tmp.npz' if os.path.exists('/workspace/data/dlnative_5m_wide829_f16_ext.npz.tmp.npz') else '/workspace/data/dlnative_5m_wide829_f16_ext.npz.tmp', '/workspace/data/dlnative_5m_wide829_f16_ext.npz')
    import time
    print("MERGED", mdat.shape, "end:", time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(mts[-1]))))
