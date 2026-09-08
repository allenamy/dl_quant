"""PREREG_holefix AMENDMENT 1+2 — STEP1 regression gate.
GATE A (primary, strict): holefix vs the artifact it replaces (wide_panel_4h_v2ext.npz),
    anchors STRICTLY BEFORE 2026-08-12 04:00Z, ALL keys, BITWISE, nan_mismatch must be 0.
GATE B (kept sanity check): holefix vs wide_panel_4h_v1.npz, same region, the 5 kline keys.
    v1's funding coverage differs from v2 BY DESIGN (pod_panel_ext.py docstring: the funding
    section was rewritten for v2), so v1 is not a valid baseline for the funding keys."""
import numpy as np, sys, time, calendar
from scipy.stats import spearmanr
NEW = sys.argv[1] if len(sys.argv) > 1 else "/workspace/data/wide_panel_4h_v2holefix.npz"
VH = np.load(NEW, allow_pickle=True)
VE = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
V1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
CH = calendar.timegm((2026, 8, 12, 4, 0, 0))
fails = []
tse = VE["ts"].astype(np.int64); tsh = VH["ts"].astype(np.int64)
assert tse.shape == tsh.shape and (tse == tsh).all(), "GATE A: anchor axis differs from v2ext"
pre = tsh < CH
print("GATE A  holefix vs v2ext, anchors < %s : %d of %d (%.3f%%)"
      % (time.strftime("%F %H:%MZ", time.gmtime(CH)), int(pre.sum()), len(tsh), 100 * pre.mean()), flush=True)
HZ = {"Y4": 4 * 3600, "Y24": 24 * 3600}          # AMENDMENT 2: forward targets change from CH - horizon
KA = [k for k in VE.files if k.startswith("f_") or k in ("Y4", "Y24", "elig")]
for k in sorted(KA):
    a = np.asarray(VE[k]); b = np.asarray(VH[k])
    if a.shape != b.shape or a.ndim < 1 or a.shape[0] != len(tsh): continue
    reg = tsh < (CH - HZ.get(k, 0))
    A = a[reg].astype(np.float64); B = b[reg].astype(np.float64)
    nm = int((np.isfinite(A) ^ np.isfinite(B)).sum())
    ok = np.isfinite(A) & np.isfinite(B)
    mx = float(np.abs(A[ok] - B[ok]).max()) if ok.any() else 0.0
    bad = (mx != 0.0) or (nm != 0)
    lost = int((np.isfinite(np.asarray(VE[k])) & (~np.isfinite(np.asarray(VH[k])))).sum())   # AMENDMENT 2: all time
    if lost: bad = True
    print("  %-18s [<%s] maxabs %.3e  nan_mismatch %d  n %d  lost(all-time) %d -> %s"
          % (k, time.strftime("%m-%d %H:%MZ", time.gmtime(CH - HZ.get(k, 0))), mx, nm, int(ok.sum()), lost, "FAIL" if bad else "OK"), flush=True)
    if bad: fails.append(("A:" + k, mx, nm, lost))
row = {int(t): i for i, t in enumerate(tsh)}
i1, ix = [], []
for a, t in enumerate(V1["ts"].astype(np.int64)):
    j = row.get(int(t))
    if j is not None: i1.append(a); ix.append(j)
i1 = np.array(i1); ix = np.array(ix); p1 = V1["ts"].astype(np.int64)[i1] < CH
print("\nGATE B  holefix vs v1 (kline keys only), same region: %d anchors" % int(p1.sum()), flush=True)
for k in ("f_rev_24h", "f_mom_7d", "f_vol_7d", "f_amihud_24h", "f_range_24h"):
    A = V1[k][i1[p1]].ravel().astype(np.float64); B = VH[k][ix[p1]].ravel().astype(np.float64)
    ok = np.isfinite(A) & np.isfinite(B)
    mx = float(np.abs(A[ok] - B[ok]).max()); tol = 1e-6 if k == "f_amihud_24h" else 0.0
    bad = mx > tol
    print("  %-18s maxabs %.3e  n %d  tol %.0e -> %s" % (k, mx, int(ok.sum()), tol, "FAIL" if bad else "OK"), flush=True)
    if bad: fails.append(("B:" + k, mx, 0))
post = tsh >= CH
print("\n  [descriptive only, NOT a gate] post-change region vs v2ext, %d anchors:" % int(post.sum()), flush=True)
for k in ("f_rev_24h", "f_amihud_24h", "f_vol_7d"):
    A = np.asarray(VE[k])[post].ravel().astype(np.float64); B = np.asarray(VH[k])[post].ravel().astype(np.float64)
    ok = np.isfinite(A) & np.isfinite(B)
    print("    %-16s changed %d/%d  spearman %.6f  |old|max %.3f -> |new|max %.3f"
          % (k, int((A[ok] != B[ok]).sum()), int(ok.sum()), spearmanr(A[ok], B[ok]).correlation, np.abs(A[ok]).max(), np.abs(B[ok]).max()), flush=True)
print("\nPANEL_REGRESSION_GATE %s" % ("FAIL %s" % fails if fails else "PASS"), flush=True)
sys.exit(3 if fails else 0)
