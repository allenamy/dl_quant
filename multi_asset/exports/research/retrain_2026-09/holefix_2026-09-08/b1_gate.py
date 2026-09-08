"""PREREG_holefix §3 GATE B1 — build meta_newprod_holefix and prove the rebuilt king side reproduces the
current book bitwise on anchors <= 2026-08-10 20:00Z. The F10 leg is held at the EXISTING prediction file,
so this isolates the king-side rebuild. If B1 fails, no number downstream is read."""
import numpy as np, os, sys, time, calendar, subprocess, hashlib
KM = "/workspace/data/wide_fea_v2holefix_meta.npz"
TG = "/workspace/dlw_holefix/data/dlw_targets.npz"
OUT = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_holefix.npz"
k = np.load(KM, allow_pickle=True); t = np.load(TG, allow_pickle=True)
kt = k["E_ts"].astype(np.int64); tt = t["E_ts"].astype(np.int64)
row = {int(x): i for i, x in enumerate(tt)}
idx = np.array([row.get(int(x), -1) for x in kt])
print("king meta anchors %d | dlw_holefix anchors %d | matched %d" % (len(kt), len(tt), int((idx >= 0).sum())), flush=True)
assert (idx >= 0).all(), "some king anchors have no dlw target row"
y4 = t["y4s"][idx].astype(np.float32)
np.savez_compressed(OUT, E_ts=kt, members=k["members"], y4=y4, qvk=k["qvk"], names=k["names"])
print("wrote %s (%.0f MB)" % (OUT, os.path.getsize(OUT) / 1e6), flush=True)
# --- verify the recipe reproduces the OLD meta_newprod on the shared, pre-change region ---
MN = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True)
mt = MN["E_ts"].astype(np.int64)
CH = calendar.timegm((2026, 8, 12, 0, 0, 0))       # y4 is a 4h-forward target -> boundary is CH_feat - 4h
rowh = {int(x): i for i, x in enumerate(kt)}
sel = np.array([rowh[int(x)] for x in mt if int(x) in rowh])
selm = np.array([i for i, x in enumerate(mt) if int(x) in rowh])
pre = mt[selm] < CH
A = MN["y4"][selm][pre].astype(np.float64); B = y4[sel][pre].astype(np.float64)
f = np.isfinite(A) & np.isfinite(B); nm = int((np.isfinite(A) ^ np.isfinite(B)).sum())
print("RECIPE CHECK  y4 old vs new, anchors < %s : both-finite %d  maxabs %.3e  nan_mismatch %d -> %s"
      % (time.strftime("%F %H:%MZ", time.gmtime(CH)), int(f.sum()), float(np.abs(A[f] - B[f]).max()), nm,
         "OK" if (np.abs(A[f] - B[f]).max() == 0.0 and nm == 0) else "FAIL"), flush=True)
assert np.abs(A[f] - B[f]).max() == 0.0 and nm == 0
