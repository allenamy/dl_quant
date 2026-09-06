"""merge_mwf3s.py — PREREG_dl_monthly_earlystop §5 replication merge: 4 shards of one seed-2027 early-stop arm (earlystop/<ARM>/shard*/, tag TAG) → stitched
ext-grid file + merged report; spliced replay inputs f10_gate_<TAG>_R0_spl27.npy (pre-2025 rows from yearly s2027; primary for the s2027 family) and _spl42.npy.
Asserts: every month once; seed_fold == 2027; embargo 1; causality; input shas = gate run; rule floor5 (best_epoch == 5+argmax va[5:]) or fix7 (== 7); finite mask equal
to the mE1 s2027 stitched file (same anchors). usage: merge_mwf3s.py <ARM> <TAG> <RULE>"""
import os, sys, json, time, hashlib, calendar, glob
import numpy as np
from scipy.stats import spearmanr
ARM, TAG, RULE = sys.argv[1], sys.argv[2], sys.argv[3]; B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/earlystop/{ARM}"; SEED = 2027
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); Ea = A["E_ts"].astype(np.int64); MEM = A["members"]; nA = len(Ea)
Bt = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); Eb = Bt["E_ts"].astype(np.int64); nB = len(Eb); assert np.array_equal(Ea[:nB], Eb)
T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); i25 = int(np.searchsorted(Ea, T25)); assert Ea[i25] == T25
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea]); MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
GATE = {"targets_sha256": "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9", "fea82_sha256": "9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e", "fea89_sha256": "bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PRED = np.full((nA, 829), np.nan, np.float32); folds = {}; seen = {}
for cf in sorted(glob.glob(f"{M}/shard*/models/{TAG}_*_config.json")):
    C = json.load(open(cf)); YM = int(C["fold"]); shard = cf.split("/")[-3]; assert YM not in seen, (YM, seen.get(YM), shard); seen[YM] = shard
    assert C["recipe"]["seed"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"] and C["seed_fold"] == SEED and C["best_epoch_rule"] == RULE and len(C["va_curve"]) == 15, (YM, C["recipe"], C.get("seed_fold"), C.get("best_epoch_rule"))
    if RULE == "floor5": assert C["best_epoch"] == 5 + int(np.argmax(C["va_curve"][5:])), YM
    else: assert C["best_epoch"] == 7, YM
    for k, v in GATE.items(): assert C[k] == v, (YM, k)
    pf = f"{M}/{shard}/preds_fold/{TAG}_{YM}.npz"; z = np.load(pf); f0, l0 = int(z["first_te"]), int(z["last_te"]); P = z["P"]; te = np.where(ym == YM)[0]; assert f0 == int(te[0]) and l0 == int(te[-1]); PRED[f0:l0 + 1] = P[:l0 - f0 + 1]
    folds[str(YM)] = {k: C[k] for k in ("n_test", "n_train", "best_va", "best_epoch", "best_epoch_rule", "alpha_final", "net_mean_bps", "es5_bps", "turnover_mean", "wall_clock_s", "finished_utc")}
    folds[str(YM)].update({"argmax_va_unrestricted": int(np.argmax(C["va_curve"])), "shard": shard, "seed_fold": C["seed_fold"], "pt_sha256": sha(f"{M}/{shard}/models/{TAG}_{YM}.pt"), "preds_fold_sha256": sha(pf), "self_sha256": C["self_sha256"]})
missing = [m for m in MONTHS if m not in seen]; assert not missing, f"missing folds {missing}"
os.makedirs(f"{M}/preds", exist_ok=True); os.makedirs(f"{M}/results", exist_ok=True); out = f"{M}/preds/f10_V2MAIN_{TAG}_s{SEED}.npy"; np.save(out, PRED)
be = [folds[str(m)]["best_epoch"] for m in MONTHS]; am = [folds[str(m)]["argmax_va_unrestricted"] for m in MONTHS]
rep = {"arm": ARM, "tag": TAG, "rule": RULE, "seed": SEED, "trainer_sha256": sha(f"{B}/pod_f10_train_monthly_earlystop_s2027.py"), "folds": folds, "net_mean_all": round(float(np.mean([f["net_mean_bps"] for f in folds.values()])), 4), "stitched": out, "stitched_sha256": sha(out), "n_finite_rows": int(np.isfinite(PRED).any(1).sum()), "best_epoch_list": be, "argmax_unrestricted_list": am, "n_changed_vs_unrestricted": int(sum(b != a for b, a in zip(be, am))), "n_unrestricted_le2": int(sum(a <= 2 for a in am))}
json.dump(rep, open(f"{M}/results/f10_V2MAIN_{TAG}_s{SEED}_merged.json", "w"), indent=1)
print("| fold | shard | best_ep | argmax(va) unrestricted | n_train | net bps | ES5 | turnover | α* | .pt sha |"); print("|---|---|---|---|---|---|---|---|---|---|")
for m in MONTHS:
    f = folds[str(m)]; print(f"| {m} | {f['shard']} | {f['best_epoch']} | {f['argmax_va_unrestricted']} | {f['n_train']} | {f['net_mean_bps']:+.3f} | {f['es5_bps']:.2f} | {f['turnover_mean']:.4f} | {f['alpha_final']:.4f} | {f['pt_sha256'][:12]} |")
print(f"stitched {out} sha {rep['stitched_sha256'][:16]} finite rows {rep['n_finite_rows']}; best_ep {be}; unrestricted argmax {am}; changed {rep['n_changed_vs_unrestricted']}/20; unrestricted argmax<=2 {rep['n_unrestricted_le2']}/20")
S27 = np.load(f"{B}/mwf_s2027/preds/f10_V2MAIN_mE1_s2027.npy"); rows_eq = bool(np.array_equal(np.isfinite(S27).any(1), np.isfinite(PRED).any(1))); cells_eq = bool(np.array_equal(np.isfinite(S27), np.isfinite(PRED)))
Y42 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"); Y27 = np.load("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"); pure = PRED[:nB]; assert int(np.isfinite(pure[:i25]).sum()) == 0
d = f"{B}/replay/dev_alt/f8_2026-08-22/preds"; rec = {}
for nm, Y in (("spl27", Y27), ("spl42", Y42)):
    spl = Y.copy(); spl[i25:] = pure[i25:]; p = f"{d}/f10_gate_{TAG}_R0_{nm}.npy"; np.save(p, spl.astype(np.float32)); rec[nm] = {"path": p, "sha256": sha(p)}; print(f"{nm}: {p} sha {rec[nm]['sha256'][:16]}")
json.dump({"merged": rep, "vs_mE1_s2027": {"finite_rows_equal": rows_eq, "finite_cells_equal": cells_eq}, "splices": rec}, open(f"{M}/results/merge.json", "w"), indent=1)
print(f"finite mask vs mE1 s2027 stitched: rows {rows_eq} cells {cells_eq}"); print("MERGE_DONE", ARM, flush=True)
