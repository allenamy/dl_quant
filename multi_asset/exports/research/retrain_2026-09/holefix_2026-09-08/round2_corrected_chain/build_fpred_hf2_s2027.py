"""F10 prediction file for the extended replay, on the dlw_hf2 axis (10212 anchors):
   rows for anchors present in the G_FIX7_UCRYPTO arm's file (f10_gate_mE1cX7s27_R0_spl27.npy, 10086 axis) are copied verbatim,
   the 186 August-2026 anchors come from HF2_s42 (FIX7 202608 fold on corrected inputs).
GATES: (a) axis prefix identity; (b) on the 60 overlapping August anchors (08-01..08-10 20Z) HF2 rows == splice rows bitwise;
       (c) every anchor of the new axis is covered by exactly one source; (d) symbol axis identical."""
import numpy as np, time, sys, hashlib, os
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
SPL = "/workspace/review_scratch/allweather_trackB/replay/dev_alt/f8_2026-08-22/preds/f10_gate_mE1cX7s27_R0_spl27.npy"
a = np.load(SPL); t86 = np.load("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
N = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True); tn = N["E_ts"].astype(np.int64); sym_n = [str(x) for x in N["symbols"]]
s86 = [str(x) for x in np.load("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)["symbols"]]
H = np.load("/workspace/review_scratch/hf2_infer/HF2_s2027.npz"); th = H["ts"].astype(np.int64); sh_ = [str(x) for x in H["symbols"]]
assert sym_n == s86 == sh_, "symbol axes differ"
assert (tn[:len(t86)] == t86).all(), "10086 axis is not a prefix of the 10212 axis"
out = np.full((len(tn), 829), np.nan, np.float32); src = np.zeros(len(tn), np.int8)   # 1 = splice, 2 = HF2
out[:len(t86)] = a; src[:len(t86)] = 1
rh = {int(x): i for i, x in enumerate(th)}
n_overlap = 0; n_diff = 0
for i, t in enumerate(tn):
    j = rh.get(int(t))
    if j is None: continue
    if src[i] == 1:
        n_overlap += 1
        x = a[i]; y = H["P"][j]; f = np.isfinite(x) & np.isfinite(y)
        n_diff += int((np.isfinite(x) ^ np.isfinite(y)).sum()) + int((x[f].view(np.uint32) != y[f].view(np.uint32)).sum())
    out[i] = H["P"][j]; src[i] = 2
print("overlap August anchors (splice ∩ HF2): %d ; differing cells %d -> %s" % (n_overlap, n_diff, "OK" if n_diff == 0 else "FAIL"), flush=True)
assert n_overlap == 60 and n_diff == 0
uncovered = np.where(src == 0)[0]; print("anchors covered by neither: %d" % len(uncovered), flush=True); assert len(uncovered) == 0
print("source breakdown: splice %d (last %s), HF2 %d (%s .. %s)" % (int((src == 1).sum()), T(tn[np.where(src == 1)[0][-1]]), int((src == 2).sum()), T(th[0]), T(th[-1])), flush=True)
D = "/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds"; os.makedirs(D, exist_ok=True)
P = D + "/f10_gate_mE1cX7s27_R0_spl27_hf2.npy"; np.save(P, out)
h = hashlib.sha256(open(P, "rb").read()).hexdigest()
print("written %s shape %s finite %.4f sha16 %s" % (P, out.shape, np.isfinite(out).mean(), h[:16]), flush=True)
print("FPRED_HF2_DONE", flush=True)
