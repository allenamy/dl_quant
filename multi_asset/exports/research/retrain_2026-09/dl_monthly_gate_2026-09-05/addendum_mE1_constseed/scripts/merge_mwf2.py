"""merge_mwf2.py — addendum §11: merge the 4 sharded constant-seed monthly runs (tag mE1c, seed 42) into one stitched ext-grid file + merged fold report,
then build the spliced replay inputs on the 0822 grid (rows < 2025-01-01 from yearly s42 = spl42 [same-seed, primary] and from yearly s2027 = spl27).
Asserts: every month once; seed_fold == 42 (constant); embargo 1; causality_ok; input shas = 09-01 gate run; finite mask equal to the mE1 s42 stitched file.
usage: merge_mwf2.py"""
import os, json, time, hashlib, calendar, glob
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/mE1_constseed"; G = "/workspace/review_scratch/dl_monthly_gate"; TAG = "mE1c"; SEED = 42
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); Ea = A["E_ts"].astype(np.int64); MEM = A["members"]; nA = len(Ea)
Bt = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); Eb = Bt["E_ts"].astype(np.int64); nB = len(Eb); assert np.array_equal(Ea[:nB], Eb)
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); assert Ea[i25] == T25
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
GATE = {"targets_sha256": "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9", "fea82_sha256": "9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e", "fea89_sha256": "bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PRED = np.full((nA, 829), np.nan, np.float32); folds = {}; seen = {}
for cf in sorted(glob.glob(f"{M}/shard*/models/{TAG}_*_config.json")):
    C = json.load(open(cf)); YM = int(C["fold"]); shard = cf.split("/")[-3]; assert YM not in seen, (YM, seen.get(YM), shard); seen[YM] = shard
    assert C["recipe"]["seed"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"] and C["seed_fold"] == SEED, (YM, C["recipe"], C["seed_fold"])
    for k, v in GATE.items(): assert C[k] == v, (YM, k)
    pf = f"{M}/{shard}/preds_fold/{TAG}_{YM}.npz"; z = np.load(pf); f0, l0 = int(z["first_te"]), int(z["last_te"]); P = z["P"]
    te = np.where(ym == YM)[0]; assert f0 == int(te[0]) and l0 == int(te[-1]); PRED[f0:l0 + 1] = P[:l0 - f0 + 1]
    folds[str(YM)] = {k: C[k] for k in ("n_test", "first_test", "last_test", "n_train", "n_val", "max_train_label_end", "cutoff", "embargo_anchors", "causality_ok", "best_va", "best_epoch", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean", "wall_clock_s", "finished_utc")}
    folds[str(YM)].update({"shard": shard, "seed_fold": C["seed_fold"], "pt_sha256": sha(f"{M}/{shard}/models/{TAG}_{YM}.pt"), "preds_fold_sha256": sha(pf), "self_sha256": C["self_sha256"], "base_sha256": C["base_sha256"]})
missing = [m for m in MONTHS if m not in seen]; assert not missing, f"missing folds {missing}"
os.makedirs(f"{M}/preds", exist_ok=True); os.makedirs(f"{M}/results", exist_ok=True)
out = f"{M}/preds/f10_V2MAIN_{TAG}_s{SEED}.npy"; np.save(out, PRED)
rep = {"tag": TAG, "seed": SEED, "seed_rule": "constant seed 42 for every fold (torch + numpy)", "embargo": 1, "trainer": f"{B}/pod_f10_train_monthly_constseed.py", "trainer_sha256": sha(f"{B}/pod_f10_train_monthly_constseed.py"), "base_verbatim_monthly_trainer_sha256": sha("/workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py"),
       "folds": folds, "net_mean_all": round(float(np.mean([f["net_mean_bps"] for f in folds.values()])), 4), "stitched": out, "stitched_sha256": sha(out), "n_finite_rows": int(np.isfinite(PRED).any(1).sum())}
json.dump(rep, open(f"{M}/results/f10_V2MAIN_{TAG}_s{SEED}_merged.json", "w"), indent=1)
print("| fold | shard | seed_fold | n_train | best_ep | net bps | ES5 | turnover | α* | wall s | .pt sha |"); print("|---|---|---|---|---|---|---|---|---|---|---|")
for m in MONTHS:
    f = folds[str(m)]; print(f"| {m} | {f['shard']} | {f['seed_fold']} | {f['n_train']} | {f['best_epoch']} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.2f} | {f['turnover_mean']:.4f} | {f['alpha_final']:.4f} | {f['wall_clock_s']:.0f} | {f['pt_sha256'][:12]} |")
print(f"stitched {out} sha {rep['stitched_sha256'][:16]} finite rows {rep['n_finite_rows']} net_mean_all {rep['net_mean_all']:+.3f}")
S42 = np.load(f"{G}/series/mE1_R0.npy"); m42, mc = np.isfinite(S42), np.isfinite(PRED); rows_eq = bool(np.array_equal(m42.any(1), mc.any(1))); cells_eq = bool(np.array_equal(m42, mc))
rc = []
for i in range(i25, nA):
    mm = MEM[i]; a = PRED[i, mm]; b = S42[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() >= 30: rc.append(spearmanr(a[ok], b[ok]).correlation)
print(f"vs mE1 s42 stitched: finite rows equal {rows_eq}, cells equal {cells_eq}; per-anchor rank corr const42 vs s42: mean {np.mean(rc):+.3f} median {np.median(rc):+.3f} p10 {np.percentile(rc, 10):+.3f} (n={len(rc)})")
Y42 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"); Y27 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy")
pure = PRED[:nB]; assert int(np.isfinite(pure[:i25]).sum()) == 0
d = f"{B}/replay/dev_alt/f8_2026-08-22/preds"; rec = {}
for nm, Y in (("spl42", Y42), ("spl27", Y27)):
    spl = Y.copy(); spl[i25:] = pure[i25:]; p = f"{d}/f10_gate_{TAG}_R0_{nm}.npy"; np.save(p, spl.astype(np.float32))
    assert np.array_equal(spl[:i25], Y[:i25], equal_nan=True) and np.array_equal(spl[i25:], pure[i25:], equal_nan=True)
    ovl = slice(i25, nB); rec[nm] = {"path": p, "sha256": sha(p), "yearly_src": ("s42" if nm == "spl42" else "s2027"), "overlap_rows_mask_diff": int((np.isfinite(pure[ovl]).any(1) != np.isfinite(Y[ovl]).any(1)).sum()), "overlap_cells_mask_diff": int((np.isfinite(pure[ovl]) != np.isfinite(Y[ovl])).sum())}
    print(f"{nm}: {p} sha {rec[nm]['sha256'][:16]} overlap rows diff {rec[nm]['overlap_rows_mask_diff']} cells diff {rec[nm]['overlap_cells_mask_diff']}")
cov = {str(m): f"{int(np.isfinite(PRED[ym == m]).any(1).sum())}/{int((ym == m).sum())}" for m in MONTHS}
json.dump({"merged": rep, "coverage_by_month": cov, "vs_s42_monthly": {"finite_rows_equal": rows_eq, "finite_cells_equal": cells_eq, "rank_corr_mean": float(np.mean(rc)), "rank_corr_median": float(np.median(rc)), "rank_corr_p10": float(np.percentile(rc, 10)), "n": len(rc)}, "splices": rec}, open(f"{M}/results/merge.json", "w"), indent=1)
print("coverage", cov); print("MERGE_DONE", flush=True)
