"""merge_mwf_v4.py — PREREG_v4 §2.4 (AMENDMENT 1 item 4: 20 folds). Merge one chain's shards (/workspace/f8_v4/mwf/<T>_s<SD>/shard*/, tag mE1cX7)
into one stitched file on the v4 DL axis (dlw_v4raw == dlw_hf3 axis, 10212 anchors) + merged fold report; splice pre-2025 rows from the
in-service yearly OOS (f8_ext/preds/f10_V2MAIN_s<SD>.npy, axis 10206, aligned by E_ts) -> health_check/dev_v4/f8_2026-08-22/preds/f10_v4<T>_s<SD>.npy.
Asserts (as merge_mwf3.py): every month exactly once; seed == SD; embargo 1; causality_ok; input shas == F10_GATE_<T>.json; rule fix7 => best_epoch == 7.
usage: merge_mwf_v4.py <T: RAW|CLIP> <SEED: 42|2027>"""
import os, sys, json, time, hashlib, calendar, glob
import numpy as np
from scipy.stats import spearmanr
T, SEED = sys.argv[1], int(sys.argv[2]); assert T in ("RAW", "CLIP") and SEED in (42, 2027)
TAG = "mE1cX7"; RULE = "fix7"; M = f"/workspace/f8_v4s/{os.environ.get('MWF_ROOT', 'mwf')}/{T}_s{SEED}"; DLW = {"RAW": "/workspace/dlw_v4raw", "CLIP": "/workspace/dlw_hf3"}[T]
A = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); Ea = A["E_ts"].astype(np.int64); nA = len(Ea)
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); assert Ea[i25] == T25
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
GATE = json.load(open(f"/workspace/f8_v4s/gates/F10_GATE_{T}.json"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
PRED = np.full((nA, 829), np.nan, np.float32); folds = {}; seen = {}
for cf in sorted(glob.glob(f"{M}/shard*/models/{TAG}_*_config.json")):
    C = json.load(open(cf)); YM = int(C["fold"]); shard = cf.split("/")[-3]; assert YM not in seen, (YM, seen.get(YM), shard); seen[YM] = shard
    assert C["recipe"]["seed"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"] and C["seed_fold"] == SEED, (YM, C["recipe"], C["seed_fold"])
    assert C["best_epoch_rule"] == RULE and C["best_epoch"] == 7, (YM, C["best_epoch_rule"], C["best_epoch"]); assert len(C["va_curve"]) == 15, YM
    for k, v in GATE.items(): assert C[k] == v, (YM, k, C[k], v)
    pf = f"{M}/{shard}/preds_fold/{TAG}_{YM}.npz"; z = np.load(pf); f0, l0 = int(z["first_te"]), int(z["last_te"]); P = z["P"]
    te = np.where(ym == YM)[0]; assert f0 == int(te[0]) and l0 == int(te[-1]), (YM, f0, l0, te[0], te[-1]); PRED[f0:l0 + 1] = P[:l0 - f0 + 1]
    folds[str(YM)] = {k: C.get(k) for k in ("n_test", "n_train", "n_val", "cutoff", "embargo_anchors", "causality_ok", "best_va", "best_epoch", "best_epoch_rule", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean", "wall_clock_s", "finished_utc")}
    folds[str(YM)].update({"argmax_va_unrestricted": int(np.argmax(C["va_curve"])), "va_at_best": C["va_curve"][C["best_epoch"]], "va_max": max(C["va_curve"]), "shard": shard, "seed_fold": C["seed_fold"], "pt_sha256": sha(f"{M}/{shard}/models/{TAG}_{YM}.pt"), "preds_fold_sha256": sha(pf), "self_sha256": C["self_sha256"]})
missing = [m for m in MONTHS if m not in seen]; assert not missing, f"missing folds {missing}"
assert int(np.isfinite(PRED[:i25]).sum()) == 0, "monthly preds must be empty before 2025"
os.makedirs(f"{M}/preds", exist_ok=True); os.makedirs(f"{M}/results", exist_ok=True)
out = f"{M}/preds/f10_V2MAIN_{T}_{TAG}_s{SEED}.npy"; np.save(out, PRED)
rep = {"target": T, "tag": TAG, "rule": RULE, "seed": SEED, "embargo": 1, "trainer": "/workspace/review_scratch/pod_f10_train_monthly_v4s.py", "trainer_sha256": sha("/workspace/review_scratch/pod_f10_train_monthly_v4s.py"), "gate": GATE, "folds": folds,
       "net_mean_all": round(float(np.mean([f["net_mean_bps"] for f in folds.values()])), 4), "stitched": out, "stitched_sha256": sha(out), "n_finite_rows": int(np.isfinite(PRED).any(1).sum()),
       "best_epoch_list": [folds[str(m)]["best_epoch"] for m in MONTHS], "argmax_unrestricted_list": [folds[str(m)]["argmax_va_unrestricted"] for m in MONTHS], "n_changed_vs_unrestricted": int(sum(folds[str(m)]["best_epoch"] != folds[str(m)]["argmax_va_unrestricted"] for m in MONTHS))}
print(f"| fold | shard | rule | best_ep | argmax(va) | va@best | va max | n_train | net bps | ES5 | turnover | α* | wall s | .pt sha |"); print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for m in MONTHS:
    f = folds[str(m)]; print(f"| {m} | {f['shard']} | {f['best_epoch_rule']} | {f['best_epoch']} | {f['argmax_va_unrestricted']} | {f['va_at_best']:+.3f} | {f['va_max']:+.3f} | {f['n_train']} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.2f} | {f['turnover_mean']:.4f} | {f['alpha_final']:.4f} | {f['wall_clock_s']:.0f} | {f['pt_sha256'][:12]} |")
print(f"stitched {out} sha {rep['stitched_sha256'][:16]} finite rows {rep['n_finite_rows']} net_mean_all {rep['net_mean_all']:+.3f}; best_ep list {rep['best_epoch_list']}; rule changed epoch vs unrestricted argmax: {rep['n_changed_vs_unrestricted']}/20")
# splice: pre-2025 rows from the in-service yearly OOS (axis 10206 -> v4 axis by E_ts)
EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64); Y = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{SEED}.npy"); assert Y.shape[0] == len(EX)
rmap = {int(t): i for i, t in enumerate(EX)}; spl = PRED.copy(); nsp = 0
for k in range(i25):
    i = rmap.get(int(Ea[k]))
    if i is not None: spl[k] = Y[i]; nsp += 1
assert np.array_equal(spl[i25:], PRED[i25:], equal_nan=True)
d = "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"; os.makedirs(d, exist_ok=True); p = f"{d}/f10_v4s{T}_s{SEED}.npy"; np.save(p, spl.astype(np.float32))
# information: score-level similarity vs the holefix FIX7 arm on the same axis (HF2), 2025+ anchors, members
MEM = A["members"]; hf = "/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds/" + ("f10_gate_mE1cX7_R0_spl42_hf2.npy" if SEED == 42 else "f10_gate_mE1cX7s27_R0_spl27_hf2.npy")
HF = np.load(hf); assert HF.shape == PRED.shape; rc = []
for i in range(i25, nA):
    mm = MEM[i]; a = PRED[i, mm]; b = HF[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() >= 30: rc.append(spearmanr(a[ok], b[ok]).correlation)
cov = {str(m): f"{int(np.isfinite(PRED[ym == m]).any(1).sum())}/{int((ym == m).sum())}" for m in MONTHS}
print(f"splice {p}: pre-2025 rows from yearly s{SEED}: {nsp}/{i25}; vs HF2 FIX7 (same axis) per-anchor rank corr mean {np.mean(rc):+.3f} median {np.median(rc):+.3f} p10 {np.percentile(rc, 10):+.3f} (n={len(rc)})")
json.dump({"merged": rep, "coverage_by_month": cov, "splice": {"path": p, "sha256": sha(p), "pre2025_rows_from_yearly": nsp, "yearly_src": f"/workspace/f8_ext/preds/f10_V2MAIN_s{SEED}.npy"},
           "vs_hf2_fix7": {"file": hf, "rank_corr_mean": float(np.mean(rc)), "rank_corr_median": float(np.median(rc)), "rank_corr_p10": float(np.percentile(rc, 10)), "n": len(rc)}}, open(f"{M}/results/merge.json", "w"), indent=1)
print("coverage", cov); print("MERGE_DONE", T, SEED, flush=True)
