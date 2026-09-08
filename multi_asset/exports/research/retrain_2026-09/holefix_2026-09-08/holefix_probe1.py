"""Task A step 0 — ONE symbol, end to end, before spending anything.
Rebuild BLZUSDT's 2026-08 rows from the official monthly 5m archive using the VERBATIM math of
pod_build_wide_ext.py L27-33 / pod_merge_cache_ext.py L27-33, and check it reproduces the cache
BITWISE on the cells the cache already has. Only then is the hole fill trustworthy."""
import numpy as np, pandas as pd, io, zipfile, urllib.request, sys, time
sys.path.insert(0, "/workspace"); from zload import zload
SYM = "BLZUSDT"
u = "https://data.binance.vision/data/futures/um/monthly/klines/%s/5m/%s-5m-2026-08.zip" % (SYM, SYM)
raw = urllib.request.urlopen(u, timeout=120).read()
with zipfile.ZipFile(io.BytesIO(raw)) as z: buf = z.read(z.namelist()[0])
d = pd.read_csv(io.BytesIO(buf), header=0 if buf[:1].isalpha() else None).iloc[:, :11]
d.columns = ['open_time','o','h','l','c','v','close_time','qv','cnt','tbv','tbqv'][:d.shape[1]]
print("official monthly rows:", len(d), "| first/last open_time:",
      time.strftime("%F %H:%M", time.gmtime(int(d.open_time.iloc[0])//1000)),
      time.strftime("%F %H:%M", time.gmtime(int(d.open_time.iloc[-1])//1000)))
# ---- verbatim build math ----
IDX = pd.date_range('2026-08-01', '2026-09-01', freq='5min')
k = d.copy()
k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
A = np.full((len(IDX), 7), np.nan, np.float16)
A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)
A[:,1] = np.clip((k.h-k.l)/k.c, 0, 0.5)
A[:,2] = ((k.c-k.l)/(k.h-k.l)).clip(0,1)
A[:,3] = np.log1p(k.qv).clip(0, 25); A[:,4] = np.log1p(k.cnt).clip(0, 20)
A[:,5] = np.log((k.qv/k.cnt.replace(0,np.nan))).clip(-5, 15)
A[:,6] = (k.tbqv/k.qv).clip(0,1)
mine_ts = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
# ---- cache ----
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; j = syms.index(SYM)
lo, hi = mine_ts[0], mine_ts[-1]
sel = (CTS >= lo) & (CTS <= hi)
cts = CTS[sel]; cache = Z["data"][sel, j, :]
pos = {int(t): i for i, t in enumerate(mine_ts)}
mrow = np.array([pos[int(t)] for t in cts])
mine = A[mrow]
print("aligned rows:", len(cts))
cf = np.isfinite(cache); mf = np.isfinite(mine)
both = cf & mf
print("cache finite %d | mine finite %d | both %d" % (cf.sum(), mf.sum(), both.sum()))
same = np.array_equal(cache[both].astype(np.float32), mine[both].astype(np.float32))
diff = np.abs(cache[both].astype(np.float64) - mine[both].astype(np.float64))
print("★ BITWISE identical on cells the cache already has: %s | maxabs %.3e" % (same, diff.max() if diff.size else 0.0))
onlym = mf & ~cf; onlyc = cf & ~mf
print("cells I can fill (mine finite, cache NaN): %d" % onlym.sum())
print("cells cache has but I do NOT (would be a regression): %d" % onlyc.sum())
if onlyc.sum():
    r, c = np.where(onlyc); print("  first few:", [(time.strftime('%F %H:%M', time.gmtime(int(cts[a]))), int(b)) for a, b in list(zip(r, c))[:5]])
# per-day fill map for ch0
day = np.array([time.strftime("%m-%d", time.gmtime(int(t))) for t in cts])
print("\nper-day ch0 (cache/mine) finite counts:")
for dd in sorted(set(day)):
    m = day == dd
    print("  %s  cache %3d  mine %3d" % (dd, int(np.isfinite(cache[m,0]).sum()), int(np.isfinite(mine[m,0]).sum())))
