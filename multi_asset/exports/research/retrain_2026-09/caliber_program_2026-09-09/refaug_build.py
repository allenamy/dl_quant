"""Same-coverage reference (reviewer item 3): F10 predictions on the ORIGINAL (holed) inputs for ALL of August 2026 =
splice file rows (10086 axis) + the reviewer's OLD_s{seed}.npz (FIX7 202608 on dlw_ext, 180 anchors 08-01..08-30 20Z), on the
dlw_ext axis (10206). Gate: the 60 overlapping August anchors must be bitwise between splice and OLD."""
import numpy as np, os, hashlib, sys
t86 = np.load("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); te = TE["E_ts"].astype(np.int64); assert (te[:len(t86)] == t86).all()
D = "/workspace/review_scratch/health_check/dev_refaug/f8_2026-08-22/preds"; os.makedirs(D, exist_ok=True)
for seed, spl in ((42, "f10_gate_mE1cX7_R0_spl42.npy"), (2027, "f10_gate_mE1cX7s27_R0_spl27.npy")):
    a = np.load("/workspace/review_scratch/allweather_trackB/replay/dev_alt/f8_2026-08-22/preds/" + spl)
    O = np.load("/workspace/codex_research/QNT-2026-0907/holefix_review_2026-09-08/inference_contract/parity_attempt/OLD_s%d.npz" % seed); ots = O["ts"].astype(np.int64); P = O["P"]
    out = np.full((len(te), 829), np.nan, np.float32); out[:len(t86)] = a; rh = {int(x): i for i, x in enumerate(ots)}; n_ov = n_diff = 0; n_new = 0
    for i, t in enumerate(te):
        j = rh.get(int(t))
        if j is None: continue
        if i < len(t86):
            n_ov += 1; x = a[i]; y = P[j]; f = np.isfinite(x) & np.isfinite(y); n_diff += int((np.isfinite(x) ^ np.isfinite(y)).sum()) + int((x[f].view(np.uint32) != y[f].view(np.uint32)).sum())
        else: n_new += 1
        out[i] = P[j]
    assert n_ov == 60 and n_diff == 0, (n_ov, n_diff)
    p = D + "/" + spl.replace(".npy", "_refaug.npy"); np.save(p, out)
    print("seed %d: overlap %d bitwise OK, new August anchors %d, uncovered new-axis anchors %d, written %s sha16 %s" % (seed, n_ov, n_new, int(np.isnan(out[len(t86):]).all(1).sum()), p, hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]))
print("REFAUG_BUILD_DONE")
