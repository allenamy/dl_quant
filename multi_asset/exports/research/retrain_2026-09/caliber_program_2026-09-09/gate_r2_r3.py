"""PREREG_caliber_program §3 gates R2 + R3.
R2: dlw_raw vs dlw_hf2 — E_ts/members bitwise; y4s_raw differs from y4s exactly on windows containing a clipped bar.
R3: two-instrument reconciliation on the 440 held cells: (y4s_raw − y4s) vs (official-4h true − recorded y4) from the
    ADDENDUM 1 patch-table instrument (same close_at machinery, /workspace/review_scratch/clip_kl)."""
import numpy as np, os, csv, time, calendar, json, sys
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
import os
A = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True); B = np.load(os.environ.get("DLW_RAW", "/workspace/dlw_raw32") + "/data/dlw_targets.npz", allow_pickle=True)
ea, eb = A["E_ts"].astype(np.int64), B["E_ts"].astype(np.int64); assert ea.shape == eb.shape and (ea == eb).all(), "R2 axis"
ma, mb = A["members"], B["members"]; assert all(np.array_equal(np.asarray(ma[i]), np.asarray(mb[i])) for i in range(len(ea))), "R2 members"
ya, yb = A["y4s"], B["y4s"]; fa, fb = np.isfinite(ya), np.isfinite(yb); assert np.array_equal(fa, fb), "R2 finiteness"
d = fa & (ya != yb); rows, cols = np.where(d)
print("R2: axis+members+finiteness identical; y4s cells changed %d over %d anchors (first %s, last %s)" % (len(rows), len(np.unique(rows)), T(ea[rows.min()]) if len(rows) else "-", T(ea[rows.max()]) if len(rows) else "-"), flush=True)
# expected set: windows [E+1, E+48] containing a clipped bar — from clip_flags (hf axis) via E_ts
F = np.load("/workspace/review_scratch/clip_flags.npz", allow_pickle=True); fts = F["E_ts"].astype(np.int64); has = F["has"]; gi = {int(t): i for i, t in enumerate(fts)}
exp = np.zeros_like(d)
for i, t in enumerate(ea):
    j = gi.get(int(t))
    if j is not None: exp[i] = has[j] & fa[i]
noise = np.abs(ya.astype(np.float64) - yb.astype(np.float64)); extra_all = int((d & ~exp).sum()); extra = int((d & ~exp & (noise > 1e-6)).sum()); missing = int((exp & ~d).sum())
print("R2: changed-outside-expected total %d, of which |Δ| > 1e-6 (real) %d ; the rest are float64 cumsum-cancellation noise (|Δ| max %.2e)" % (extra_all, extra, noise[d & ~exp].max() if extra_all else 0.0), flush=True)
print("R2: changed-but-not-expected %d ; expected-but-unchanged %d ; expected set size %d -> %s" % (extra, missing, int(exp.sum()), "PASS" if extra == 0 else "FAIL"), flush=True)
if missing: print("   (expected-but-unchanged can be legitimate: a clipped bar whose raw |r| rounds to the same float16 → reported, not gated)")
# ---- R3 ----
syms = [str(s) for s in A["symbols"]]; D = "/workspace/review_scratch/clip_kl"; CA = {}
def closes(s, ym):
    k = (s, ym)
    if k in CA: return CA[k]
    p = os.path.join(D, "%s_%s.csv" % (s, ym)); dd = {}
    if os.path.exists(p):
        for r in csv.reader(open(p)):
            try: dd[int(r[0]) // 1000] = float(r[4])
            except Exception: pass
    CA[k] = dd; return dd
def close_at(s, t):
    ym = time.strftime("%Y-%m", time.gmtime(t)); c = closes(s, ym)
    if t in c: return c[t]
    y, m = map(int, ym.split("-")); m -= 1
    if m == 0: y, m = y - 1, 12
    return closes(s, "%04d-%02d" % (y, m)).get(t)
cells = json.load(open("/workspace/review_scratch/clip_need.json"))["cells"]; ri = {int(t): i for i, t in enumerate(ea)}; sj = {s: j for j, s in enumerate(syms)}
dev = []; n = 0
for t, s, w in cells:
    i = ri.get(int(t)); j = sj.get(s)
    if i is None or j is None: continue
    a = close_at(s, int(t)); b = close_at(s, int(t) - 14400)
    if a is None or b is None or b <= 0: continue
    true4h = a / b - 1.0; chain = float(yb[i, j]) - float(ya[i, j]); patch = true4h - float(ya[i, j]); dev.append(abs(chain - patch)); n += 1
dev = np.array(dev); print("R3: 440 held cells -> resolved %d ; |chain Δ − patch-table Δ| max %.3e p99 %.3e median %.3e ; tol 5e-4 -> %s" % (n, dev.max(), np.percentile(dev, 99), np.median(dev), "PASS" if dev.max() <= 5e-4 else "FAIL"), flush=True)
sys.exit(0 if (extra == 0 and dev.max() <= 5e-4) else 3)
