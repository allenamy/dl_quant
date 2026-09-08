"""Task A step 2 — build dlnative_5m_wide829_f16_holefix.npz per PREREG §2.
Math verbatim from pod_build_wide_ext.py L27-33. FILL-ONLY-NaN: never overwrite an existing cell.
All five self-checks are asserted; any failure stops before the file is written."""
import numpy as np, pandas as pd, os, sys, json, time, calendar, hashlib
sys.path.insert(0, "/workspace"); from zload import zload
KL = "/workspace/review_scratch/holefix_kl"
SRC = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
DST = "/workspace/data/dlnative_5m_wide829_f16_holefix.npz"
HOLE_LO = calendar.timegm((2026, 8, 13, 0, 5, 0)); HOLE_HI = calendar.timegm((2026, 8, 24, 4, 0, 0))
D31_LO = calendar.timegm((2026, 8, 31, 0, 0, 0)); D31_HI = calendar.timegm((2026, 9, 1, 0, 0, 0))
t0 = time.time()
Z = zload(SRC, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = Z["ch"]
DATA = np.array(Z["data"])                     # materialise once
print("cache %s loaded in %.0fs" % (str(DATA.shape), time.time() - t0), flush=True)
AUG_LO = calendar.timegm((2026, 8, 1, 0, 0, 0)); AUG_HI = calendar.timegm((2026, 9, 1, 0, 0, 0))
aug = (CTS >= AUG_LO) & (CTS <= AUG_HI)
augrows = np.where(aug)[0]; augts = CTS[aug]
print("august rows in axis: %d (%s .. %s)" % (len(augts), time.strftime("%F %H:%M", time.gmtime(augts[0])), time.strftime("%F %H:%M", time.gmtime(augts[-1]))), flush=True)
IDX = pd.date_range('2026-08-01', '2026-09-01', freq='5min')
IDX_TS = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
pos = {int(t): i for i, t in enumerate(IDX_TS)}
mrow = np.array([pos[int(t)] for t in augts])
# the 348 hole symbols, recomputed here (never trusted from a saved list)
sub = DATA[aug]
holeset = set()
pre = (CTS >= HOLE_LO - 7 * 86400) & (CTS < HOLE_LO); post = (CTS > HOLE_HI) & (CTS <= HOLE_HI + 5 * 86400)
npre = np.isfinite(DATA[pre][:, :, 0]).sum(0); npost = np.isfinite(DATA[post][:, :, 0]).sum(0)
hw = (CTS >= HOLE_LO) & (CTS <= HOLE_HI)
nhw = np.isfinite(DATA[hw]).sum(axis=(0, 2))
alive = (npre > 500) & (npost > 500)
hole_mask = (nhw == 0) & alive
print("hole symbols recomputed: %d (alive %d)" % (int(hole_mask.sum()), int(alive.sum())), flush=True)
n_eq = 0; n_cmp = 0; maxabs = 0.0; fill_hole = 0; fill_d31 = 0; fill_other = 0
other_examples = []
missing = set(json.load(open("/workspace/review_scratch/holefix_missing.json")))
built = 0; n_hdr = 0
for j, s in enumerate(SY):
    p = os.path.join(KL, "%s.csv" % s)
    if not os.path.exists(p): continue
    with open(p, "rb") as _f: _first = _f.read(1)
    _hdr = 0 if _first.isalpha() else None
    if _hdr == 0: n_hdr += 1
    d = pd.read_csv(p, header=_hdr).iloc[:, :11]
    d.columns = ['open_time','o','h','l','c','v','close_time','qv','cnt','tbv','tbqv'][:d.shape[1]]
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
    mine = A[mrow]                       # aligned to the cache's august rows
    cur = DATA[augrows, j, :]
    cf = np.isfinite(cur); mf = np.isfinite(mine)
    both = cf & mf
    if both.any():
        n_cmp += int(both.sum())
        eq = cur[both] == mine[both]
        n_eq += int(eq.sum())
        dd = np.abs(cur[both].astype(np.float64) - mine[both].astype(np.float64))
        maxabs = max(maxabs, float(dd.max()))
    fillm = (~cf) & mf
    if fillm.any():
        rr, cc = np.where(fillm)
        ts_f = augts[rr]
        inhole = (ts_f >= HOLE_LO) & (ts_f <= HOLE_HI) & bool(hole_mask[j])
        ind31 = (ts_f >= D31_LO) & (ts_f < D31_HI)
        oth = ~(inhole | ind31)
        fill_hole += int(inhole.sum()); fill_d31 += int(ind31.sum()); fill_other += int(oth.sum())
        if oth.any() and len(other_examples) < 8:
            o = np.where(oth)[0][:2]
            other_examples += [(s, time.strftime("%F %H:%M", time.gmtime(int(ts_f[x]))), int(cc[x])) for x in o]
        cur[fillm] = mine[fillm]
        DATA[augrows[rr], j, cc] = mine[fillm]
    built += 1
    if built % 100 == 0: print("  built %d/%d  (%.0fs)" % (built, len(SY), time.time() - t0), flush=True)
print("\ncsv files WITH a header row: %d / %d (the original readers detect this with raw[:1].isalpha())" % (n_hdr, built), flush=True)
print("\n=== SELF-CHECKS (PREREG §2) ===", flush=True)
print("1. bitwise identity on pre-existing cells: %d/%d equal, maxabs %.3e -> %s" % (n_eq, n_cmp, maxabs, "PASS" if n_eq == n_cmp else "FAIL"))
print("3. fills: hole(D1) %d | 2026-08-31(D2) %d | OTHER %d" % (fill_hole, fill_d31, fill_other))
if other_examples: print("   OTHER examples (symbol, ts, ch):", other_examples)
print("   symbols not fetched (delisted): %d" % len(missing))
assert n_eq == n_cmp and maxabs == 0.0, "self-check 1 FAILED"
np.savez_compressed(DST + ".tmp", ts=CTS, symbols=np.array(SY), ch=CH, data=DATA)
os.replace(DST + ".tmp.npz" if os.path.exists(DST + ".tmp.npz") else DST + ".tmp", DST)
print("\nwritten %s (%.1f GB) in %.0fs" % (DST, os.path.getsize(DST) / 1e9, time.time() - t0), flush=True)
print("HOLEFIX_BUILD_DONE", flush=True)
