"""Diagnose the king FEA parity failure: WHERE (dates), WHICH symbols, WHAT values."""
import numpy as np, time
from collections import Counter
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); eo = MO["E_ts"].astype(np.int64); names = [str(x) for x in MO["names"]]
sym = [str(s) for s in np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)["symbols"]]
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2holefix.npy", mmap_mode="r")
MEM = MO["members"]
rows = []; symc = Counter(); insidemem = 0; outsidemem = 0; ex = []
for i in range(len(eo)):
    a = np.asarray(FO[i], dtype=np.float64); b = np.asarray(FN[i], dtype=np.float64)
    d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
    if not d.any(): continue
    s_idx = np.where(d.any(1))[0]; rows.append((eo[i], int(d.sum()), len(s_idx)))
    m = set(np.asarray(MEM[i]).tolist())
    for j in s_idx:
        symc[sym[j]] += 1
        if j in m: insidemem += 1
        else: outsidemem += 1
    if len(ex) < 6:
        j = s_idx[0]; c = np.where(d[j])[0][0]; ex.append((T(eo[i]), sym[j], names[c], float(a[j, c]), float(b[j, c]), "in-members" if j in m else "NOT-member"))
print("changed anchors %d" % len(rows))
yrs = Counter(time.strftime("%Y-%m", time.gmtime(r[0])) for r in rows); print("by month:", dict(sorted(yrs.items())))
print("symbol-rows changed: inside members %d / outside members %d" % (insidemem, outsidemem))
print("top symbols:", symc.most_common(12))
print("examples (anchor, symbol, column, old, new):"); [print("  ", e) for e in ex]
# are the pre-2026 changed cells all NaN<->finite or value changes?
nanflip = 0; valchg = 0
for t, _, _ in rows[:60]:
    i = int(np.where(eo == t)[0][0]); a = np.asarray(FO[i], dtype=np.float64); b = np.asarray(FN[i], dtype=np.float64)
    nanflip += int((np.isfinite(a) ^ np.isfinite(b)).sum()); valchg += int((np.isfinite(a) & np.isfinite(b) & (a != b)).sum())
print("first 60 changed anchors: nan<->finite flips %d, finite value changes %d" % (nanflip, valchg))
