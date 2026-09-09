"""Sparse float32 raw-return patch for the clipped bars (exact, no float16 re-quantisation of the raw value).
Output raw_patch.npz: row, col, ts, symbol, raw32 (official close_t/close_{t-1}-1), clip16 (the cache value)."""
import numpy as np, pandas as pd, os, sys, time, hashlib
sys.path.insert(0, "/workspace"); from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_holefix.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]
ch0 = Z["data"][:, :, 0]; cand = np.isfinite(ch0) & ((ch0 == np.float16(0.3)) | (ch0 == np.float16(-0.3))); rows, cols = np.where(cand)
D = "/workspace/review_scratch/raw5m_kl"; cache = {}
def month_closes(s, ym):
    p = os.path.join(D, "%s_%s.csv" % (s, ym)); d = {}
    if not os.path.exists(p): return d
    with open(p, "rb") as f: hdr = 0 if f.read(1).isalpha() else None
    k = pd.read_csv(p, header=hdr).iloc[:, :11]; ts = (k.iloc[:, 0].astype(np.int64) // 1000 + 300).to_numpy(); c = k.iloc[:, 4].astype(float).to_numpy()
    return dict(zip(ts.tolist(), c.tolist()))
def close_at(s, t):
    ym = time.strftime("%Y-%m", time.gmtime(t)); key = (s, ym)
    if key not in cache: cache[key] = month_closes(s, ym)
    v = cache[key].get(int(t))
    if v is None:
        y, m = map(int, ym.split("-")); m -= 1
        if m == 0: y, m = y - 1, 12
        k2 = (s, "%04d-%02d" % (y, m))
        if k2 not in cache: cache[k2] = month_closes(s, k2[1])
        v = cache[k2].get(int(t))
    return v
R, C, TS, SY, RAW, CL = [], [], [], [], [], []; miss = 0; notclip = 0
for r, c in zip(rows, cols):
    t = int(CTS[r]); a = close_at(syms[c], t); b = close_at(syms[c], t - 300)
    if a is None or b is None or b <= 0: miss += 1; continue
    rv = a / b - 1.0
    if abs(rv) <= 0.3: notclip += 1; continue
    R.append(r); C.append(c); TS.append(t); SY.append(syms[c]); RAW.append(np.float32(rv)); CL.append(ch0[r, c])
assert miss == 0, miss
np.savez_compressed("/workspace/review_scratch/raw_patch.npz", row=np.array(R, np.int64), col=np.array(C, np.int64), ts=np.array(TS, np.int64), symbol=np.array(SY), raw32=np.array(RAW, np.float32), clip16=np.array(CL, np.float16))
print("raw_patch.npz: %d clipped bars (candidates %d, not-clipped %d, unresolved %d) sha16 %s" % (len(R), len(rows), notclip, miss, hashlib.sha256(open("/workspace/review_scratch/raw_patch.npz", "rb").read()).hexdigest()[:16]), flush=True)
print("RAW_PATCH_DONE", flush=True)
