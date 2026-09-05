"""leakcheck_monthly.py — dl_monthly_wf: 门V3′ (AMENDMENT A1; /workspace/pod_f10_v3_leakcheck_v2.py) adapted to the monthly stitched files.
Spectrum: mean Spearman(score_i, y4s_{i+k}) over members, k ∈ [−3, +3].
  ① future side no peak: max|corr(k∈{+1,+2,+3})| < |corr(k=0)|          (own test set, gate-literal stride max(1, nA//800) AND full set)
  ② shape vs the yearly-fold file: per-k |Δ| ≤ 0.03 on the COMMON anchor set 2025-01-01 → 2026-08-10 20Z (full set, stride 1; both files, same targets)
  ③ out-of-fold leak: finite cells before the first fold (2025-01-01) must be 0 (pure stitched file)
usage: leakcheck_monthly.py <TAG> [<TAG>...]   → logs/leakcheck_<tags>.json, exit 3 on FAIL"""
import sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
R = "/workspace/review_scratch/dl_monthly_wf"; YEARLY = "/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E)
nB = len(np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)["E_ts"])
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(E, T25))
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
PY = np.full((nA, 829), np.nan, np.float32); PY[:nB] = np.load(YEARLY)
common = [i for i in range(nA) if T25 <= E[i] <= CUT]
spec_y_common = spectrum(PY, common)
OUT = {"yearly_sha256": sha(YEARLY), "common_window": "2025-01-01 → 2026-08-10 20:00Z (full set, stride 1)", "yearly_spectrum_common": spec_y_common, "files": {}}
print("yearly (common window) " + " ".join(f"k{k:+d}:{v:+.4f}" for k, v in spec_y_common.items()))
bad = []
for T in sys.argv[1:]:
    p = f"{R}/preds/f10_V2MAIN_{T}_s42.npy"; P = np.load(p)
    test = [i for i in range(nA) if np.isfinite(P[i]).any()]
    stride = max(1, nA // 800)
    paired = [i for i in common if np.isfinite(P[i]).any() and np.isfinite(PY[i]).any()]   # same anchor set for both files (② is a paired shape comparison)
    s_lit = spectrum(P, test[::stride]); s_full = spectrum(P, test); s_com = spectrum(P, paired); s_y = spectrum(PY, paired)
    fut = max(abs(s_full[k]) for k in (1, 2, 3)); c1 = fut < abs(s_full[0])
    fut_lit = max(abs(s_lit[k]) for k in (1, 2, 3)); c1_lit = fut_lit < abs(s_lit[0])
    dmax = max(abs(s_com[k] - s_y[k]) for k in range(-3, 4)); c2 = dmax <= 0.03
    leak = int(np.isfinite(P[:i25]).sum()); c3 = leak == 0
    OUT["files"][T] = {"sha256": sha(p), "n_test_anchors": len(test), "n_paired_anchors": len(paired), "spectrum_own_full": s_full, "spectrum_own_stride": s_lit, "stride": stride, "spectrum_common": s_com, "yearly_spectrum_same_anchors": s_y,
                       "c1_future_no_peak_full": c1, "c1_future_no_peak_stride": c1_lit, "max_abs_future_full": fut, "c2_shape_vs_yearly_maxabs": dmax, "c2_pass": c2, "c3_prefold_finite": leak, "c3_pass": c3,
                       "leak_relevant_pass_c1_and_c3": bool(c1 and c3)}
    print(f"{T} own(full) " + " ".join(f"k{k:+d}:{s_full[k]:+.4f}" for k in range(-3, 4)))
    print(f"{T} own(stride {stride}) " + " ".join(f"k{k:+d}:{s_lit[k]:+.4f}" for k in range(-3, 4)))
    print(f"{T} paired({len(paired)}) " + " ".join(f"k{k:+d}:{s_com[k]:+.4f}" for k in range(-3, 4)) + " | yearly same anchors " + " ".join(f"k{k:+d}:{s_y[k]:+.4f}" for k in range(-3, 4)))
    print(f"{T} ①未来侧无峰 max|k>0|={fut:.4f} < |k0|={abs(s_full[0]):.4f} {'OK' if c1 else 'FAIL'} (stride-literal {'OK' if c1_lit else 'FAIL'}) | ②谱形 vs yearly(common) max|Δ|={dmax:.4f} {'OK' if c2 else 'FAIL'} | ③折外泄出 {leak} {'OK' if c3 else 'FAIL'}", flush=True)
    if not (c1 and c2 and c3): bad.append(T)
# per-month k=−1 / k=0 loadings (diagnostic: is the shape difference a per-fold property or a property of the whole file?)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E])
OUT["per_month_k"] = {}
for T in list(OUT["files"]) + ["yearly"]:
    P = PY if T == "yearly" else np.load(f"{R}/preds/f10_V2MAIN_{T}_s42.npy")
    for m in sorted(set(ym[(ym >= 202501)].tolist())):
        idx = [i for i in range(nA) if ym[i] == m and np.isfinite(P[i]).any() and E[i] <= CUT]
        if len(idx) < 30: continue
        s = spectrum(P, idx); OUT["per_month_k"].setdefault(str(m), {})[T] = {"k-1": s[-1], "k0": s[0], "n": len(idx)}
print("per-month k-1 / k0: " + json.dumps({m: {t: [round(v["k-1"], 3), round(v["k0"], 3)] for t, v in d.items()} for m, d in OUT["per_month_k"].items()}))
OUT["verdict"] = "PASS" if not bad else f"FAIL {bad}"
json.dump(OUT, open(f"{R}/logs/leakcheck_{'_'.join(sys.argv[1:])}.json", "w"), indent=1)
print("V3P_GATE_MONTHLY", OUT["verdict"], flush=True)
sys.exit(0 if not bad else 3)
