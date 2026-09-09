"""E-0909-B repair from DAILY official archives (the MONTHLY archives themselves lack these days for ~49 symbols; daily files exist).
Same contract as Task A: verbatim channel math, fill-only-NaN, bitwise identity on existing cells, fills counted per day."""
import numpy as np, pandas as pd, os, io, sys, time, calendar, zipfile, urllib.request, hashlib, concurrent.futures as cf
from collections import Counter
sys.path.insert(0, "/workspace"); from zload import zload
SRC = "/workspace/data/dlnative_5m_wide829_f16_holefix.npz"; DST = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"; KL = "/workspace/review_scratch/holefix2_daily_kl"; os.makedirs(KL, exist_ok=True)
t0 = time.time(); Z = zload(SRC, allow_pickle=True); CTS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = Z["ch"]; DATA = np.array(Z["data"])
day = CTS // 86400; ud, inv = np.unique(day, return_inverse=True); nd = len(ud)
fin0 = np.isfinite(DATA[:, :, 0]); cnt = np.zeros((nd, len(SY)), np.int32); np.add.at(cnt, inv, fin0.astype(np.int32))
alive = cnt >= 200; first = np.array([np.argmax(alive[:, j]) if alive[:, j].any() else -1 for j in range(len(SY))]); last = np.array([nd - 1 - np.argmax(alive[::-1, j]) if alive[:, j].any() else -1 for j in range(len(SY))])
inlife = np.zeros_like(alive)
for j in range(len(SY)):
    if first[j] >= 0: inlife[first[j]:last[j] + 1, j] = True
partial_or_hole = inlife & (cnt < 288)
hd = np.where((inlife & (cnt == 0)).sum(1) >= 3)[0]
# target days = hole days ± 2 (to include the partial edge days), only where the symbol is in-life and not full
days = sorted({int(x) for d in hd for x in range(d - 2, d + 3) if 0 <= x < nd}); syms_idx = sorted(set(np.where((inlife & (cnt == 0))[hd].any(0))[0].tolist()))
D = lambda d: time.strftime("%F", time.gmtime(ud[d] * 86400))
print("hole days %s ; target days %s ; symbols %d" % ([D(d) for d in hd], [D(d) for d in days], len(syms_idx)), flush=True)
jobs = [(SY[j], d) for j in syms_idx for d in days if partial_or_hole[d, j]] + [(SY[j], d - 1) for j in syms_idx for d in days if partial_or_hole[d, j] and d - 1 >= 0]   # previous day for pct_change continuity
jobs = sorted(set(jobs)); print("daily archives to fetch: %d" % len(jobs), flush=True)
def get(p):
    s, d = p; ds = D(d); out = os.path.join(KL, "%s_%s.csv" % (s, ds))
    if os.path.exists(out) and os.path.getsize(out) > 0: return "cached"
    u = "https://data.binance.vision/data/futures/um/daily/klines/%s/5m/%s-5m-%s.zip" % (s, s, ds)
    try:
        raw = urllib.request.urlopen(u, timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z: open(out, "wb").write(z.read(z.namelist()[0]))
        return "ok"
    except Exception as e: return "MISS:" + type(e).__name__
with cf.ThreadPoolExecutor(max_workers=8) as ex: res = list(ex.map(get, jobs))
print("archives:", dict(Counter(r.split(":")[0] for r in res)), flush=True)
n_eq = n_cmp = 0; maxabs = 0.0; filled = Counter()
for j in syms_idx:
    s = SY[j]; frames = []
    for (ss, d) in jobs:
        if ss != s: continue
        p = os.path.join(KL, "%s_%s.csv" % (s, D(d)))
        if not os.path.exists(p): continue
        with open(p, "rb") as f: hdr = 0 if f.read(1).isalpha() else None
        k = pd.read_csv(p, header=hdr).iloc[:, :11]; k.columns = ["open_time", "o", "h", "l", "c", "v", "close_time", "qv", "cnt", "tbv", "tbqv"][:k.shape[1]]; frames.append(k)
    if not frames: continue
    k = pd.concat(frames); k["ts"] = pd.to_datetime(k.open_time.astype(np.int64), unit="ms") + pd.Timedelta("5min"); k = k.drop_duplicates("ts").set_index("ts").sort_index()
    grid = pd.date_range(k.index.min(), k.index.max(), freq="5min"); k = k.reindex(grid)
    A = np.full((len(grid), 7), np.nan, np.float16)
    A[:, 0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3); A[:, 1] = np.clip((k.h - k.l) / k.c, 0, 0.5); A[:, 2] = ((k.c - k.l) / (k.h - k.l)).clip(0, 1)
    A[:, 3] = np.log1p(k.qv).clip(0, 25); A[:, 4] = np.log1p(k.cnt).clip(0, 20); A[:, 5] = np.log((k.qv / k.cnt.replace(0, np.nan))).clip(-5, 15); A[:, 6] = (k.tbqv / k.qv).clip(0, 1)
    gts = np.array(grid, dtype="datetime64[s]").astype(np.int64); rowof = {int(t): i for i, t in enumerate(CTS)}
    sel = [(i, rowof[int(t)]) for i, t in enumerate(gts) if int(t) in rowof]
    gi = np.array([a for a, _ in sel]); ci = np.array([b for _, b in sel]); mine = A[gi]; cur = DATA[ci, j, :]
    cf_ = np.isfinite(cur); mf = np.isfinite(mine); both = cf_ & mf
    if both.any(): n_cmp += int(both.sum()); n_eq += int((cur[both] == mine[both]).sum()); maxabs = max(maxabs, float(np.abs(cur[both].astype(np.float64) - mine[both].astype(np.float64)).max()))
    fill = (~cf_) & mf
    if fill.any():
        rr, cc = np.where(fill)
        for t in np.unique(CTS[ci[rr]]): filled[time.strftime("%F", time.gmtime(int(t)))] += int((CTS[ci[rr]] == t).sum())
        DATA[ci[rr], j, cc] = mine[fill]
print("=== SELF-CHECKS === 1. pre-existing cells: %d/%d bitwise, maxabs %.3e -> %s" % (n_eq, n_cmp, maxabs, "PASS" if n_eq == n_cmp else "FAIL"), flush=True)
print("3. fills by day:", dict(sorted(filled.items())), "total", sum(filled.values()), flush=True); assert n_eq == n_cmp and maxabs == 0.0
np.savez_compressed(DST + ".tmp", ts=CTS, symbols=np.array(SY), ch=CH, data=DATA); os.replace(DST + ".tmp.npz" if os.path.exists(DST + ".tmp.npz") else DST + ".tmp", DST)
print("written %s sha16 %s (%.0fs)" % (DST, hashlib.sha256(open(DST, "rb").read()).hexdigest()[:16], time.time() - t0), flush=True); print("HOLEFIX2_DONE", flush=True)
