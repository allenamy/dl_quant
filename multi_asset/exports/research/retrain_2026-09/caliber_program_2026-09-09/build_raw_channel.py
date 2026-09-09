"""PREREG_caliber_program §3 — ch7 = ret5_raw. Only bars judged CLIPPED (ch0 == float16(±0.3) AND official |raw| > 0.3) are
replaced by the official close_t/close_{t-1}-1; everything else is ch0 verbatim. Gate R1: ch7 != ch0 exactly on that set."""
import numpy as np, pandas as pd, os, sys, time, calendar, csv, hashlib
sys.path.insert(0, "/workspace"); from zload import zload
SRC = os.environ.get("RAW_SRC", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"); DST = os.environ.get("RAW_DST", "/workspace/data/dlnative_5m_wide829_f16_holefix2_raw.npz"); D = "/workspace/review_scratch/raw5m_kl"
Z = zload(SRC, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
DATA = np.array(Z["data"]); TT, NW, NC = DATA.shape; assert NC == 7
HI = np.float16(0.3); LO = np.float16(-0.3)
ch0 = DATA[:, :, 0]; cand = np.isfinite(ch0) & ((ch0 == HI) | (ch0 == LO))
rows, cols = np.where(cand); print("boundary candidates (ch0 == float16(±0.3)): %d over %d symbols" % (len(rows), len(np.unique(cols))), flush=True)
rowof = {int(t): k for k, t in enumerate(CTS)}
def month_closes(s, ym):
    p = os.path.join(D, "%s_%s.csv" % (s, ym)); d = {}
    if not os.path.exists(p): return d
    with open(p, "rb") as f: hdr = 0 if f.read(1).isalpha() else None
    k = pd.read_csv(p, header=hdr).iloc[:, :11]; k.columns = ["open_time", "o", "h", "l", "c", "v", "close_time", "qv", "cnt", "tbv", "tbqv"][:k.shape[1]]
    ts = (k.open_time.astype(np.int64) // 1000 + 300).to_numpy(); c = k.c.astype(float).to_numpy()   # cache ts = bar close = open + 5m
    return dict(zip(ts.tolist(), c.tolist()))
cache = {}
def close_at(s, t):
    ym = time.strftime("%Y-%m", time.gmtime(t)); key = (s, ym)
    if key not in cache: cache[key] = month_closes(s, ym)
    v = cache[key].get(int(t))
    if v is None:
        y, m = map(int, ym.split("-")); m -= 1
        if m == 0: y, m = y - 1, 12
        key2 = (s, "%04d-%02d" % (y, m))
        if key2 not in cache: cache[key2] = month_closes(s, key2[1])
        v = cache[key2].get(int(t))
    return v
raw = ch0.copy(); n_true = 0; n_notclip = 0; n_miss = 0; ex = []
for r, c in zip(rows, cols):
    t = int(CTS[r]); a = close_at(syms[c], t); b = close_at(syms[c], t - 300)
    if a is None or b is None or b <= 0: n_miss += 1; continue
    rv = a / b - 1.0
    if abs(rv) > 0.3:
        raw[r, c] = np.float16(rv); n_true += 1
        if len(ex) < 5: ex.append((time.strftime("%F %H:%M", time.gmtime(t)), syms[c], float(ch0[r, c]), round(rv, 6)))
    else: n_notclip += 1
print("true clips replaced %d ; boundary-but-not-clipped %d ; unresolved (no official bar) %d" % (n_true, n_notclip, n_miss), flush=True)
print("examples (ts, sym, clipped, raw):", ex, flush=True)
diff = (raw != ch0) & np.isfinite(ch0); assert bool((diff <= cand).all()), "R1: differences outside the clipped set"
same16 = n_true - int(diff.sum()); print("clipped bars whose raw value rounds to the SAME float16 as the clip (|r| in (0.3, 0.30017)): %d (reported, legitimate)" % same16, flush=True)
assert n_miss == 0, "R1: %d clipped bars have no official bar — download incomplete" % n_miss
nanm = int((np.isfinite(raw) ^ np.isfinite(ch0)).sum()); assert nanm == 0
print("GATE_R1 PASS: ch7 differs from ch0 on exactly %d cells (= %d true clips − %d float16-identical), all inside the boundary set; nan_mismatch 0" % (int(diff.sum()), n_true, same16), flush=True)
OUT = np.concatenate([DATA, raw[:, :, None]], axis=2); assert OUT.shape == (TT, NW, 8)
np.savez_compressed(DST + ".tmp", ts=CTS, symbols=np.array(syms), ch=np.array(CH + ["ret5_raw"]), data=OUT)
os.replace(DST + ".tmp.npz" if os.path.exists(DST + ".tmp.npz") else DST + ".tmp", DST)
print("written %s %s sha16 %s" % (DST, OUT.shape, hashlib.sha256(open(DST, "rb").read()).hexdigest()[:16]), flush=True); print("RAW_CHANNEL_DONE", flush=True)
