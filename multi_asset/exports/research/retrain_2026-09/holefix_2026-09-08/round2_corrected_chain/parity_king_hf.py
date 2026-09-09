"""King-side parity: wide_fea_v2holefix(.npy/_meta) vs wide_fea_v2ext. Read-only. Measures the first changed anchor."""
import numpy as np, time, calendar, sys
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
MO = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
MN = np.load("/workspace/data/wide_fea_v2holefix_meta.npz", allow_pickle=True)
eo = MO["E_ts"].astype(np.int64); en = MN["E_ts"].astype(np.int64)
print("== KING META == anchors old %d new %d ; prefix identical: %s ; extra: %s" % (len(eo), len(en), bool((en[:len(eo)] == eo).all()), [T(x) for x in en[len(eo):]]), flush=True)
assert (en[:len(eo)] == eo).all()
print("  names identical: %s" % ([str(x) for x in MO["names"]] == [str(x) for x in MN["names"]]), flush=True)
firsts = {}
for k in ("members", "qvk", "y4"):
    AO = MO[k]; AN = MN[k]          # materialise ONCE — NpzFile[key] re-decompresses per access
    first = None; n = 0
    for i in range(len(eo)):
        a = np.asarray(AO[i]); b = np.asarray(AN[i])
        if k == "members": same = np.array_equal(a, b)
        else:
            a = a.astype(np.float64); b = b.astype(np.float64)
            same = not ((np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))).any()
        if not same:
            n += 1
            if first is None: first = eo[i]
    firsts[k] = first
    print("  %-8s anchors changed %d ; FIRST %s" % (k, n, T(first) if first is not None else "-"), flush=True)
FO = np.load("/workspace/data/wide_fea_v2ext.npy", mmap_mode="r"); FN = np.load("/workspace/data/wide_fea_v2holefix.npy", mmap_mode="r")
print("== KING FEA == shapes old %s new %s dtype %s" % (FO.shape, FN.shape, FO.dtype), flush=True)
first = None; n_anch = 0; cells = 0; cols = np.zeros(FO.shape[2], np.int64)
for i in range(len(eo)):
    a = np.asarray(FO[i], dtype=np.float64); b = np.asarray(FN[i], dtype=np.float64)
    d = (np.isfinite(a) ^ np.isfinite(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
    if d.any():
        n_anch += 1; cells += int(d.sum()); cols += d.sum(0)
        if first is None: first = eo[i]
names = [str(x) for x in MO["names"]]
print("  anchors changed %d ; cells %d ; FIRST %s" % (n_anch, cells, T(first) if first is not None else "-"), flush=True)
if cells: print("  changed columns: %s" % [(names[j], int(cols[j])) for j in np.argsort(-cols) if cols[j] > 0][:12], flush=True)
lim = calendar.timegm((2026, 8, 12, 0, 0, 0)); ok = all((f is None) or (f >= lim) for f in list(firsts.values()) + [first])
print("KING_PARITY_GATE %s" % ("PASS" if ok else "FAIL"), flush=True); sys.exit(0 if ok else 3)
