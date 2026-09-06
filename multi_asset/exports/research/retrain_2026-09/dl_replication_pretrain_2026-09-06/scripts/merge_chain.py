"""merge_chain.py — generic merge for ONE sequential warm-start-family chain (W1F5 / P1 / P1F / P0eE): 20 fold configs under <root>/models/<tag>_*_config.json,
preds_fold npz → stitched ext-grid file <root>/preds/f10_V2MAIN_<tag>_s42.npy + merged report; spliced replay inputs f10_gate_<tag>_R0_spl42.npy (pre-2025 = yearly s42)
and _spl27.npy. Asserts: every month once; seed_fold == 42; embargo 1; causality; input shas = gate run; init_mode warm; first fold init sha = yearly-2025 .pt;
later folds init sha = previous fold's .pt; lr as given; rule: argmax (best_epoch == argmax va) | floor5 (== 5+argmax va[5:]) | p0 (best_epoch == EPOCHS-1, p0_mode 1).
usage: merge_chain.py <root> <tag> <lr> <rule> [expected_epochs_for_p0]"""
import os, sys, json, time, hashlib, calendar, glob
import numpy as np
from scipy.stats import spearmanr
root, TAG, LR, RULE = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]; P0E = int(sys.argv[5]) if len(sys.argv) > 5 else None
B = "/workspace/review_scratch/allweather_trackB"; SEED = 42
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); Ea = A["E_ts"].astype(np.int64); MEM = A["members"]; nA = len(Ea)
Bt = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); Eb = Bt["E_ts"].astype(np.int64); nB = len(Eb); assert np.array_equal(Ea[:nB], Eb)
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); assert Ea[i25] == T25
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]; PREV = {MONTHS[k]: MONTHS[k - 1] for k in range(1, len(MONTHS))}
GATE = {"targets_sha256": "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9", "fea82_sha256": "9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e", "fea89_sha256": "bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
INIT_PT = f"{B}/mE1_constseed/yearly_out/models/f10_V2MAIN_YS_s42_2025.pt"; INIT_SHA = sha(INIT_PT)
PRED = np.full((nA, 829), np.nan, np.float32); folds = {}; seen = {}
for cf in sorted(glob.glob(f"{root}/models/{TAG}_*_config.json")):
    C = json.load(open(cf)); YM = int(C["fold"]); assert YM not in seen; seen[YM] = 1
    assert C["recipe"]["seed"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"] and C["seed_fold"] == SEED and C["init_mode"] == "warm" and abs(C["lr"] - LR) < 1e-12, (YM, C["recipe"], C.get("seed_fold"), C.get("init_mode"), C.get("lr"))
    for k, v in GATE.items(): assert C[k] == v, (YM, k)
    if YM == 202501: assert C["init_from"] == "INIT_STATE" and C["init_state_sha256"] == INIT_SHA, (YM, C.get("init_from"))
    else: assert C["init_from"] == f"prev_fold_best_state:{PREV[YM]}" and C["init_state_sha256"] == sha(f"{root}/models/{TAG}_{PREV[YM]}.pt"), (YM, C.get("init_from"))
    if RULE == "argmax": assert C["best_epoch"] == int(np.argmax(C["va_curve"])), YM
    elif RULE == "floor5": assert C["best_epoch_rule"] == "floor5" and C["best_epoch"] == 5 + int(np.argmax(C["va_curve"][5:])), YM
    elif RULE == "p0": assert C["p0_mode"] == 1 and C["epochs"] == P0E and C["best_epoch"] == P0E - 1 and C["musd_source"] == ("yearly2025_rule" if YM == 202501 else "inherited"), (YM, C.get("epochs"), C.get("musd_source"))
    else: raise SystemExit(f"bad rule {RULE}")
    pf = f"{root}/preds_fold/{TAG}_{YM}.npz"; z = np.load(pf); f0, l0 = int(z["first_te"]), int(z["last_te"]); P = z["P"]; te = np.where(ym == YM)[0]; assert f0 == int(te[0]) and l0 == int(te[-1]); PRED[f0:l0 + 1] = P[:l0 - f0 + 1]
    folds[str(YM)] = {k: C.get(k) for k in ("n_test", "n_train", "n_val", "cutoff", "best_va", "best_epoch", "best_epoch_rule", "init_from", "init_state_sha256", "lr", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean", "wall_clock_s", "finished_utc", "train_win_days", "train_first_anchor", "p0_mode", "p0_train_month", "epochs", "musd_source", "theta_rel_change")}
    folds[str(YM)].update({"pt_sha256": sha(f"{root}/models/{TAG}_{YM}.pt"), "preds_fold_sha256": sha(pf), "self_sha256": C["self_sha256"]})
missing = [m for m in MONTHS if m not in seen]; assert not missing, f"missing folds {missing}"
os.makedirs(f"{root}/preds", exist_ok=True); os.makedirs(f"{root}/results", exist_ok=True)
out = f"{root}/preds/f10_V2MAIN_{TAG}_s{SEED}.npy"; np.save(out, PRED)
be = [folds[str(m)]["best_epoch"] for m in MONTHS]
rep = {"root": root, "tag": TAG, "lr": LR, "rule": RULE, "init_pt": INIT_PT, "init_pt_sha256": INIT_SHA, "folds": folds, "net_mean_all": round(float(np.mean([f["net_mean_bps"] for f in folds.values()])), 4), "stitched": out, "stitched_sha256": sha(out), "n_finite_rows": int(np.isfinite(PRED).any(1).sum()),
       "best_epoch_list": be, "n_best_ep0": int(sum(x == 0 for x in be)), "n_best_ep_le2": int(sum(x <= 2 for x in be)), "alpha_final_list": [folds[str(m)]["alpha_final"] for m in MONTHS], "theta_rel_change_list": [folds[str(m)]["theta_rel_change"] for m in MONTHS], "n_train_list": [folds[str(m)]["n_train"] for m in MONTHS]}
json.dump(rep, open(f"{root}/results/f10_V2MAIN_{TAG}_s{SEED}_merged.json", "w"), indent=1)
print(f"| fold | init_from | n_train | best_ep | va@best | net bps | ES5 | turnover | α* | ‖Δθ‖/‖θ‖ | wall s | .pt sha |"); print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for m in MONTHS:
    f = folds[str(m)]; vb = (C_ := None); vab = "-"
    print(f"| {m} | {f['init_from']} | {f['n_train']} | {f['best_epoch']} | {(f['best_va'] if f['best_va'] is not None else float('nan')):+.3f} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.2f} | {f['turnover_mean']:.4f} | {f['alpha_final']:.4f} | {(f['theta_rel_change'] if f['theta_rel_change'] is not None else float('nan')):.4f} | {f['wall_clock_s']:.0f} | {f['pt_sha256'][:12]} |")
print(f"stitched {out} sha {rep['stitched_sha256'][:16]} finite rows {rep['n_finite_rows']} net_mean_all {rep['net_mean_all']:+.3f}; best_ep {be}; ep0 {rep['n_best_ep0']}/20 le2 {rep['n_best_ep_le2']}/20")
SC = np.load(f"{B}/mE1_constseed/preds/f10_V2MAIN_mE1c_s42.npy"); rows_eq = bool(np.array_equal(np.isfinite(SC).any(1), np.isfinite(PRED).any(1))); cells_eq = bool(np.array_equal(np.isfinite(SC), np.isfinite(PRED)))
rc = []
for i in range(i25, nA):
    mm = MEM[i]; a = PRED[i, mm]; b = SC[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() >= 30: rc.append(spearmanr(a[ok], b[ok]).correlation)
print(f"vs CONST stitched: finite rows equal {rows_eq}, cells equal {cells_eq}; same-anchor rank corr {TAG} vs CONST: mean {np.mean(rc):+.3f} median {np.median(rc):+.3f} p10 {np.percentile(rc, 10):+.3f} (n={len(rc)})")
Y42 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"); Y27 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"); pure = PRED[:nB]; assert int(np.isfinite(pure[:i25]).sum()) == 0
d = f"{B}/replay/dev_alt/f8_2026-08-22/preds"; rec = {}
for nm, Y in (("spl42", Y42), ("spl27", Y27)):
    spl = Y.copy(); spl[i25:] = pure[i25:]; p = f"{d}/f10_gate_{TAG}_R0_{nm}.npy"; np.save(p, spl.astype(np.float32)); rec[nm] = {"path": p, "sha256": sha(p)}; print(f"{nm}: {p} sha {rec[nm]['sha256'][:16]}")
json.dump({"merged": rep, "vs_const": {"finite_rows_equal": rows_eq, "finite_cells_equal": cells_eq, "rank_corr_mean": float(np.mean(rc)), "rank_corr_median": float(np.median(rc)), "rank_corr_p10": float(np.percentile(rc, 10)), "n": len(rc)}, "splices": rec}, open(f"{root}/results/merge.json", "w"), indent=1)
print("MERGE_DONE", TAG, flush=True)
