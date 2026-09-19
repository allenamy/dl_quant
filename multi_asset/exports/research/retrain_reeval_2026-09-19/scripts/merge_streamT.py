#!/usr/bin/env python3
"""merge_streamT.py — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (9b403aad) stream T: build one F10 arm's prediction file for the book replay.
The arm file = the A1 file (FP2-8 merge output f10_v4RAW_s<seed>.npy, sha asserted) with EVERY row from 2025-01-01T00Z on replaced by this arm's
out-of-sample scores; rows before 2025 stay byte-identical (they are the in-service yearly OOS splice both arms share), so the replay differs from A1
only through the named change.
  T1: 20 monthly folds 202501..202608 at TRAIN_FRAC = 1.0 (mwf/T1_s<seed>/shard*); row block of month m = fold m's P[: n_test]  (= the A1 merge rule)
  T2: yearly folds = the monthly fold 202501 (label end < 2025-01-01) for every 2025 anchor, fold 202601 (label end < 2026-01-01) for every 2026 anchor,
      both at TRAIN_FRAC = 0.85 (mwf/SELFCHK_s<seed>/shardm2025{01}|m2026{01}); P covers every anchor >= that fold's first test anchor.
Asserts per fold config (as merge_mwf_v4b.py): seed, embargo 1, causality_ok, fix7 / best_epoch 7, 15-point va_curve, gate shas == F10_GATE_RAW.json,
plus train_frac / va_in_sample of the arm and self_sha256 == the research trainer; the stitched finite pattern must equal A1's on every 2025+ row.
usage: merge_streamT.py <T1|T2> <42|2027>"""
import calendar, glob, hashlib, json, os, sys, time
import numpy as np
from scipy.stats import spearmanr
ARM, SEED = sys.argv[1], int(sys.argv[2]); assert ARM in ("T1", "T2") and SEED in (42, 2027)
W = "/workspace/retrain_reeval_2026-09-19"; TAG = "mE1cX7"; R = "/workspace/fp2_2026-09"
TRAINER = f"{W}/device/pod_f10_train_monthly_v4_tf.py"
A1 = {42: (f"{R}/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "297751ba47ff9463d79dd9a4a66cd55cd20a2c9d19270616cb9d06fe70b3e822"),
      2027: (f"{R}/health_check/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy", "b12a5d71abe538d48aa447dfbbffad440573932ce5a0e1dff28b8745a4a734a2")}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
a1p, a1s = A1[SEED]; assert sha(a1p) == a1s, "A1 file sha"
TG = np.load(f"{R}/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True); Ea = TG["E_ts"].astype(np.int64); nA = len(Ea); y4s = TG["y4s"]; MEM = TG["members"]
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in Ea])
i25 = int(np.searchsorted(Ea, calendar.timegm((2025, 1, 1, 0, 0, 0)))); i26 = int(np.searchsorted(Ea, calendar.timegm((2026, 1, 1, 0, 0, 0))))
assert Ea[i25] == calendar.timegm((2025, 1, 1, 0, 0, 0)) and Ea[i26] == calendar.timegm((2026, 1, 1, 0, 0, 0))
GATE = json.load(open(f"{R}/f8_v4/gates/F10_GATE_RAW.json")); TSHA = sha(TRAINER)
BASEP = np.load(a1p); assert BASEP.shape == (nA, 829)
MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
def fold_cfg(root, m, tf):
    cf = glob.glob(f"{root}/shard*/models/{TAG}_{m}_config.json"); assert len(cf) == 1, (m, cf); C = json.load(open(cf[0]))
    assert int(C["fold"]) == m and C["recipe"]["seed"] == SEED and C["seed_fold"] == SEED and C["recipe"]["embargo"] == 1 and C["causality_ok"], (m, C["recipe"])
    assert C["best_epoch_rule"] == "fix7" and C["best_epoch"] == 7 and len(C["va_curve"]) == 15, m
    for k, v in GATE.items(): assert C[k] == v, (m, k)
    assert C["self_sha256"] == TSHA, (m, "trainer sha", C["self_sha256"][:12], TSHA[:12])
    assert C["train_frac"] == tf and C["va_in_sample"] == (tf > 0.85), (m, C["train_frac"], C["va_in_sample"])
    pf = cf[0].replace("/models/", "/preds_fold/").replace("_config.json", ".npz"); z = np.load(pf)
    te = np.where(ym == m)[0]; assert int(z["first_te"]) == int(te[0]) and int(z["last_te"]) == int(te[-1]), m
    return C, z, pf
OUT = BASEP.copy(); OUT[i25:] = np.nan; folds = {}
if ARM == "T1":
    root = f"{W}/mwf/T1_s{SEED}"
    for m in MONTHS:
        C, z, pf = fold_cfg(root, m, 1.0); f0, l0 = int(z["first_te"]), int(z["last_te"]); OUT[f0:l0 + 1] = z["P"][:l0 - f0 + 1]
        folds[str(m)] = {k: C.get(k) for k in ("n_train", "n_val", "n_grad_anchors", "grad_last_ts", "grad_loss_last_ts", "va_first_ts", "va_last_ts", "max_train_label_end", "cutoff", "train_frac", "va_in_sample", "net_mean_bps", "wall_clock_s")}
        folds[str(m)].update({"preds_fold": pf, "preds_fold_sha256": sha(pf), "a1_withheld_from_gradient_from": C.get("va_first_ts")})
else:
    root = f"{W}/mwf/SELFCHK_s{SEED}"
    for m, lo, hi in ((202501, i25, i26), (202601, i26, nA)):
        C, z, pf = fold_cfg(root, m, 0.85); f0 = int(z["first_te"]); assert f0 == lo, (m, f0, lo)
        OUT[lo:hi] = z["P"][:hi - lo]
        folds[str(m)] = {k: C.get(k) for k in ("n_train", "n_val", "n_grad_anchors", "grad_last_ts", "grad_loss_last_ts", "max_train_label_end", "cutoff", "train_frac", "net_mean_bps", "wall_clock_s")}
        folds[str(m)].update({"preds_fold": pf, "preds_fold_sha256": sha(pf), "rows": [time.strftime("%FT%TZ", time.gmtime(int(Ea[lo]))), time.strftime("%FT%TZ", time.gmtime(int(Ea[hi - 1])))]})
assert np.array_equal(OUT[:i25], BASEP[:i25], equal_nan=True), "pre-2025 rows must be A1's"
assert np.array_equal(np.isfinite(OUT[i25:]), np.isfinite(BASEP[i25:])), "2025+ finite pattern must equal A1's (same members per anchor)"
os.makedirs(f"{W}/preds", exist_ok=True); p = f"{W}/preds/f10_{ARM}_s{SEED}.npy"; np.save(p, OUT.astype(np.float32))
hp = f"{W}/hc/dev_v4/f8_2026-08-22/preds/f10_{ARM}_s{SEED}.npy"
if os.path.islink(hp) or os.path.exists(hp): os.remove(hp)
os.symlink(p, hp)
# information only (score layer; PREREG §4: an IC change is not a book change): per-anchor rank corr with A1 and member rank-IC of both, 2025+
rc, ica, icb = [], [], []
for i in range(i25, nA):
    mm = MEM[i]; a = OUT[i, mm]; b = BASEP[i, mm]; y = y4s[i, mm]; ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(y)
    if ok.sum() >= 30:
        rc.append(spearmanr(a[ok], b[ok]).correlation); ica.append(spearmanr(a[ok], y[ok]).correlation); icb.append(spearmanr(b[ok], y[ok]).correlation)
rep = {"arm": ARM, "seed": SEED, "out": p, "out_sha256": sha(p), "hc_link": hp, "a1_file": a1p, "a1_sha256": a1s, "trainer_sha256": TSHA, "gate": GATE, "folds": folds,
       "rows_replaced_from": time.strftime("%FT%TZ", time.gmtime(int(Ea[i25]))), "n_rows_replaced": int(nA - i25), "pre2025_identical_to_A1": True,
       "info_rank_corr_vs_A1": {"mean": float(np.mean(rc)), "median": float(np.median(rc)), "p10": float(np.percentile(rc, 10)), "n": len(rc)},
       "info_member_rankIC_2025on": {"arm": float(np.mean(ica)), "A1": float(np.mean(icb)), "n": len(ica)}}
json.dump(rep, open(f"{W}/receipts/MERGE_{ARM}_s{SEED}.json", "w"), indent=1, default=str)
print(f"MERGE_STREAMT_DONE {ARM} s{SEED} -> {p} sha {rep['out_sha256'][:16]} rankcorr vs A1 {rep['info_rank_corr_vs_A1']['mean']:+.3f} IC arm {rep['info_member_rankIC_2025on']['arm']:+.4f} A1 {rep['info_member_rankIC_2025on']['A1']:+.4f}", flush=True)
