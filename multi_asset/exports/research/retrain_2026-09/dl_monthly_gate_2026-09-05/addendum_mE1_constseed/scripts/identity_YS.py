"""identity_YS.py — addendum §11: the yearly_save diagnostic patch must leave the test-pass predictions bitwise equal to the 09-01 gate run (both seeds);
also lists the saved state dicts / all-anchor score files with sha256. → mE1_constseed/results/identity_YS.json"""
import json, hashlib, os, numpy as np
B = "/workspace/review_scratch/allweather_trackB/mE1_constseed/yearly_out"; sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); yrs = A["yrs"].astype(int)
OUT = {}; ok_all = True
for s in ("42", "2027"):
    mine = f"{B}/preds/f10_V2MAIN_YS_s{s}.npy"; ref = f"/workspace/f8_ext/preds/f10_V2MAIN_s{s}.npy"; P = np.load(mine); Q = np.load(ref)
    eq = bool(np.array_equal(P, Q, equal_nan=True)); ok_all &= eq
    folds = {str(yv): {"bitwise": bool(np.array_equal(P[yrs == yv], Q[yrs == yv], equal_nan=True)), "max_abs": float(np.nanmax(np.abs(P[yrs == yv] - Q[yrs == yv])))} for yv in (2023, 2024, 2025, 2026)}
    files = {}
    for yv in (2023, 2024, 2025, 2026):
        pt = f"{B}/models/f10_V2MAIN_YS_s{s}_{yv}.pt"; pf = f"{B}/preds_fold/f10_V2MAIN_YS_s{s}_{yv}.npz"; z = np.load(pf)
        files[str(yv)] = {"pt_sha256": sh(pt), "preds_fold_sha256": sh(pf), "first_te": int(z["first_te"]), "P_shape": list(z["P"].shape), "own_year_rows_equal_preds": bool(np.array_equal(z["P"][: int((yrs == yv).sum())], P[yrs == yv], equal_nan=True))}
    JM = json.load(open(f"{B}/results/f10_V2MAIN_YS_s{s}.json")); JR = json.load(open(f"/workspace/f8_ext/results/f10_V2MAIN_s{s}.json"))
    jeq = all(JM["folds"][yv][k] == JR["folds"][yv][k] for yv in JR["folds"] for k in ("best_va", "va_curve", "alpha_curve", "net_mean_bps", "es5_bps", "turnover_mean"))
    OUT[f"s{s}"] = {"mine_sha256": sh(mine), "ref_sha256": sh(ref), "file_bitwise_equal": eq, "folds": folds, "json_fold_metrics_equal": bool(jeq), "self_sha256": JM["self_sha256"], "files": files}
    print(f"s{s}: file bitwise {eq} sha mine {sh(mine)[:16]} ref {sh(ref)[:16]} json metrics equal {jeq} folds {[(k, v['bitwise'], v['max_abs']) for k, v in folds.items()]} own-year rows == preds {[v['own_year_rows_equal_preds'] for v in files.values()]}")
OUT["verdict"] = "IDENTITY_YS_OK" if ok_all else "IDENTITY_YS_FAIL"; json.dump(OUT, open(f"/workspace/review_scratch/allweather_trackB/mE1_constseed/results/identity_YS.json", "w"), indent=1); print(OUT["verdict"])
