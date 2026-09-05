"""identity_check.py — Track B identity test: patched trainer with DRO_T=inf SS_W=0 (ARM V2MAIN_IDENT, seed 42, all 4 yearly folds) must reproduce the
09-01 gate run /workspace/f8_ext/preds/f10_V2MAIN_s42.npy bitwise (per fold: finite mask equal, max|Δ| = 0.0) and the fold metrics in its json.
usage: identity_check.py → logs/identity_check.log (stdout), results/identity_check.json"""
import json, hashlib, numpy as np
B = "/workspace/review_scratch/allweather_trackB"
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); yrs = A["yrs"].astype(int)
mine = f"{B}/f8_out/preds/f10_V2MAIN_IDENT_s42.npy"; ref = "/workspace/f8_ext/preds/f10_V2MAIN_s42.npy"
P = np.load(mine); Q = np.load(ref); sh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
OUT = {"mine": mine, "mine_sha256": sh(mine), "ref": ref, "ref_sha256": sh(ref), "shape": list(P.shape), "folds": {}}
allok = True
for yv in (2023, 2024, 2025, 2026):
    m = yrs == yv; a = P[m]; b = Q[m]; fa = np.isfinite(a); fb = np.isfinite(b); eq = bool(np.array_equal(a, b, equal_nan=True)); mx = float(np.nanmax(np.abs(a - b))) if fa.any() else float("nan")
    OUT["folds"][str(yv)] = {"rows": int(m.sum()), "finite_mine": int(fa.sum()), "finite_ref": int(fb.sum()), "mask_equal": bool(np.array_equal(fa, fb)), "bitwise_equal": eq, "max_abs_delta": mx}; allok &= eq
    print(f"fold {yv}: rows {int(m.sum())} finite {int(fa.sum())}/{int(fb.sum())} mask_equal {np.array_equal(fa, fb)} bitwise_equal {eq} max|Δ| {mx}")
OUT["file_bitwise_equal"] = bool(np.array_equal(P, Q, equal_nan=True)); OUT["file_sha_equal"] = OUT["mine_sha256"] == OUT["ref_sha256"]
JM = json.load(open(f"{B}/f8_out/results/f10_V2MAIN_IDENT_s42.json")); JR = json.load(open("/workspace/f8_ext/results/f10_V2MAIN_s42.json"))
OUT["json_folds_equal"] = {yv: {k: (JM["folds"][yv][k] == JR["folds"][yv][k]) for k in ("n_test", "best_va", "va_curve", "alpha_curve", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean")} for yv in JR["folds"]}
OUT["json_inputs_equal"] = {k: JM[k] == JR[k] for k in ("targets_sha256", "fea82_sha256", "fea89_sha256", "cost", "ldd", "afix", "epochs", "lr", "win", "burn", "stride", "embargo", "seed")}
OUT["json_self_sha"] = {"mine": JM["self_sha256"], "ref": JR["self_sha256"]}; OUT["mine_knobs"] = {"dro_t": JM.get("dro_t"), "ss_w": JM.get("ss_w")}
print("file bitwise equal:", OUT["file_bitwise_equal"], "| sha equal:", OUT["file_sha_equal"], "| json fold metrics equal:", OUT["json_folds_equal"], "| inputs equal:", OUT["json_inputs_equal"])
OUT["verdict"] = "IDENTITY_OK" if (allok and OUT["file_bitwise_equal"] and all(all(v.values()) for v in OUT["json_folds_equal"].values())) else "IDENTITY_FAIL"
json.dump(OUT, open(f"{B}/results/identity_check.json", "w"), indent=1); print(OUT["verdict"], flush=True)
