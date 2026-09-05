"""leakcheck_yearly.py — Track B leak gate (PREREG_allweather §3 Track B (iv)): yearly-fold preds on the ext grid (nA rows).
Spectrum: mean over test anchors of Spearman(score_i, y4s_{i+k}) over members, k ∈ [−3, +3].
  ① future side no peak: max|corr(k∈{+1,+2,+3})| < |corr(k=0)|   (full test set, stride 1; and the gate-literal stride max(1, nA//800))
  ③ out-of-fold leak: finite cells before the first fold (2023-01-01 00Z) must be 0; and each year's finite rows ⊆ that year's test rows
  ② (diagnostic, not in the gate) shape vs the same-seed ext baseline (f8_ext/preds/f10_V2MAIN_s<seed>.npy): per-k |Δ| on the common anchor set
usage: leakcheck_yearly.py <LABEL:SEED> [...]   → results/leakcheck_<labels>.json, exit 3 on FAIL of ① or ③"""
import sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; yrs = A["yrs"].astype(int); nA = len(E)
T23 = calendar.timegm((2023, 1, 1, 0, 0, 0)); i23 = int(np.searchsorted(E, T23))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def spectrum(P, idx):
    spec = {}
    for k in range(-3, 4):
        vals = []
        for i in idx:
            if not (3 <= i < nA - 3): continue
            m = MEM[i]; a = P[i, m]; b = Y4[i + k, m]; ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals)) if vals else float("nan")
    return spec
OUT = {"targets_sha256": sha("/workspace/dlw_ext/data/dlw_targets.npz"), "files": {}}; bad = []
for spec_ in sys.argv[1:]:
    L, S = spec_.split(":"); p = f"{B}/f8_out/preds/f10_V2MAIN_{L}_s{S}.npy"; P = np.load(p); assert P.shape == (nA, 829)
    ref = f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy"; PR = np.load(ref)
    test = [i for i in range(nA) if np.isfinite(P[i]).any()]; stride = max(1, nA // 800)
    s_full = spectrum(P, test); s_lit = spectrum(P, test[::stride])
    fut = max(abs(s_full[k]) for k in (1, 2, 3)); c1 = fut < abs(s_full[0]); fut_lit = max(abs(s_lit[k]) for k in (1, 2, 3)); c1_lit = fut_lit < abs(s_lit[0])
    leak = int(np.isfinite(P[:i23]).sum()); c3 = leak == 0
    rows_by_year = {int(y): int(np.isfinite(P[yrs == y]).any(1).sum()) for y in (2022, 2023, 2024, 2025, 2026)}
    paired = [i for i in test if np.isfinite(PR[i]).any()]; s_ref = spectrum(PR, paired); s_com = spectrum(P, paired); dmax = max(abs(s_com[k] - s_ref[k]) for k in range(-3, 4))
    OUT["files"][f"{L}_s{S}"] = {"sha256": sha(p), "ref": ref, "ref_sha256": sha(ref), "n_test_anchors": len(test), "rows_by_year": rows_by_year, "spectrum_own_full": s_full, "spectrum_own_stride": s_lit, "stride": stride,
                                 "c1_future_no_peak_full": bool(c1), "c1_future_no_peak_stride": bool(c1_lit), "max_abs_future_full": fut, "c3_prefold_finite": leak, "c3_pass": bool(c3),
                                 "shape_vs_ref_maxabs": dmax, "spectrum_common": s_com, "ref_spectrum_same_anchors": s_ref, "n_paired": len(paired), "leak_gate_pass_c1_and_c3": bool(c1 and c3)}
    print(f"{L}_s{S} own(full, n={len(test)}) " + " ".join(f"k{k:+d}:{s_full[k]:+.4f}" for k in range(-3, 4)))
    print(f"{L}_s{S} ①未来侧无峰 max|k>0|={fut:.4f} < |k0|={abs(s_full[0]):.4f} {'OK' if c1 else 'FAIL'} (stride {stride}: {'OK' if c1_lit else 'FAIL'}) | ③折外泄出 pre-2023 finite {leak} {'OK' if c3 else 'FAIL'} rows/yr {rows_by_year} | ②谱形 vs ext baseline s{S} max|Δ|={dmax:.4f} (诊断)", flush=True)
    if not (c1 and c3): bad.append(f"{L}_s{S}")
OUT["verdict"] = "PASS" if not bad else f"FAIL {bad}"
json.dump(OUT, open(f"{B}/results/leakcheck_{'_'.join(a.replace(':', '_s') for a in sys.argv[1:])}.json", "w"), indent=1)
print("LEAK_GATE_YEARLY", OUT["verdict"], flush=True); sys.exit(0 if not bad else 3)
