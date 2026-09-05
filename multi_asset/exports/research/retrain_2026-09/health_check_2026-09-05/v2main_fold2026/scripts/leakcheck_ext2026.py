"""leakcheck_ext2026.py — gate V3′ (pod_f10_v3_leakcheck_v2.py, sha 70edc0aa…) adapted to the 2026-fold files of this campaign:
① future side has no peak: max|corr(k=+1..+3)| < corr(k=0) (and corr(0) > 0), spectrum over ALL 2026 anchors with i+3 < nA (no sub-sampling);
② spectrum shape equals the existing old-generation file per k, |Δ| ≤ 0.03, on the overlap anchors 2026-01-01→08-10 (same anchors for both);
③ no leakage outside the fold: finite entries in rows before the first 2026 anchor == 0; finite rows == n_test (1452);
④ causal assertion from the saved fold config: max(train∪val E_ts) + 4h vs first test anchor − 60 anchors (both readings printed), embargo anchors == 60.
Exit 0 on PASS of ①②③ and ④(≤ reading)."""
import numpy as np, json, time, sys
from scipy.stats import spearmanr
ROOT = "/workspace/review_scratch/v2main_fold2026"
TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = TE["E_ts"].astype(np.int64); y4s = TE["y4s"]; MEM = TE["members"]; yrs = TE["yrs"].astype(int); nA = len(E)
TO = np.load("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True); assert np.array_equal(TO["E_ts"].astype(np.int64), E[:10086])
def ft(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
i26 = np.where(yrs == 2026)[0]; first_te = int(i26[0]); spec_idx = i26[i26 + 3 < nA]; ovl_idx = i26[i26 < 10086 - 3]
def spectrum(P, idx):
    spec = {}
    for k in range(-3, 4):
        vals = []
        for i in idx:
            m = MEM[i]; a = P[i, m]; b = y4s[i + k, m]; ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 30: vals.append(spearmanr(a[ok], b[ok]).correlation)
        spec[k] = float(np.nanmean(vals))
    return spec
bad = []; out = {}
for S in (42, 2027):
    P = np.load(f"{ROOT}/preds/f10_V2MAIN_ext2026_s{S}.npy"); O = np.load(f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy"); Op = np.full((nA, 829), np.nan, np.float32); Op[:10086] = O
    E01 = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy")
    sn = spectrum(P, spec_idx); so = spectrum(Op, ovl_idx); sn_ovl = spectrum(P, ovl_idx); se = spectrum(E01, spec_idx)
    fut = max(abs(sn[k]) for k in (1, 2, 3)); c1 = (fut < sn[0]) and (sn[0] > 0)
    dmax = max(abs(sn_ovl[k] - so[k]) for k in range(-3, 4)); c2 = dmax <= 0.03
    leak = int(np.isfinite(P[:first_te]).sum()); nfin = int(np.isfinite(P).any(1).sum()); c3 = (leak == 0) and (nfin == len(i26))
    cfg = json.load(open(f"{ROOT}/models/f10_V2MAIN_ext2026_s{S}_fold2026_config.json"))
    lab_end = cfg["max_trainval_E_ts"] + 4 * 3600; emb_start = cfg["first_test_E_ts"] - 60 * 4 * 3600
    c4_strict = lab_end < emb_start; c4_le = lab_end <= emb_start; gap_anchors = (cfg["first_test_E_ts"] - cfg["max_trainval_E_ts"]) // (4 * 3600)
    c4 = c4_le and cfg["embargo_anchors_between"] == 60 and cfg["max_trainval_idx"] == first_te - 61
    out[str(S)] = {"spectrum_new_2026": sn, "spectrum_new_overlap": sn_ovl, "spectrum_old_overlap": so, "spectrum_ext0901_2026": se, "n_spec_anchors": int(len(spec_idx)), "n_overlap_anchors": int(len(ovl_idx)),
                   "c1_future_no_peak": {"max_abs_k1_3": round(fut, 4), "k0": round(sn[0], 4), "pass": bool(c1)}, "c2_shape_vs_old": {"max_abs_delta": round(dmax, 4), "pass": bool(c2)},
                   "c3_no_leak_outside_fold": {"finite_entries_before_first_test": leak, "finite_rows": nfin, "n_test": int(len(i26)), "pass": bool(c3)},
                   "c4_causal": {"max_trainval_E_ts": ft(cfg["max_trainval_E_ts"]), "label_end_plus4h": ft(lab_end), "first_test_E_ts": ft(cfg["first_test_E_ts"]), "first_test_minus_60_anchors": ft(emb_start), "gap_anchors_first_test_minus_max_train": int(gap_anchors),
                                 "embargo_anchors_between": cfg["embargo_anchors_between"], "max_trainval_idx": cfg["max_trainval_idx"], "first_te_idx": first_te, "strict_lt": bool(c4_strict), "le": bool(c4_le), "pass_le_and_60": bool(c4)}}
    print(f"s{S} new  2026 spectrum " + " ".join(f"k{k:+d}:{sn[k]:+.4f}" for k in range(-3, 4)) + f"  (n={len(spec_idx)})")
    print(f"s{S} new  ovl  spectrum " + " ".join(f"k{k:+d}:{sn_ovl[k]:+.4f}" for k in range(-3, 4)) + f"  (n={len(ovl_idx)})")
    print(f"s{S} old  ovl  spectrum " + " ".join(f"k{k:+d}:{so[k]:+.4f}" for k in range(-3, 4)))
    print(f"s{S} e0901 2026 spectrum " + " ".join(f"k{k:+d}:{se[k]:+.4f}" for k in range(-3, 4)))
    print(f"s{S} ① max|k>0|={fut:.4f} < k0={sn[0]:.4f} {'OK' if c1 else 'FAIL'} | ② max|Δ| vs old={dmax:.4f} {'OK' if c2 else 'FAIL'} | ③ leak_before_fold={leak} finite_rows={nfin}/{len(i26)} {'OK' if c3 else 'FAIL'} | ④ label_end {ft(lab_end)} vs first_test−60 anchors {ft(emb_start)}: strict< {c4_strict}, ≤ {c4_le}, embargo anchors {cfg['embargo_anchors_between']} {'OK' if c4 else 'FAIL'}", flush=True)
    if not (c1 and c2 and c3 and c4): bad.append(S)
json.dump(out, open(f"{ROOT}/results/leakcheck_ext2026.json", "w"), indent=1)
print("V3P_EXT2026", "PASS" if not bad else f"FAIL {bad}", flush=True); sys.exit(0 if not bad else 3)
