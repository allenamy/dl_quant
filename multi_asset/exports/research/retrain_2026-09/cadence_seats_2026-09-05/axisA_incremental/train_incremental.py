"""train_incremental.py — PREREG_incremental_retrain_2026-09-06 §2 (king arms KR / KC) — pod, read-only inputs; writes only under
/workspace/review_scratch/cadence_seats/axisA_incremental/.
Data preparation + fold rule = axisA/pod_king_cadence.py MODE=d1 VERBATIM (itself rolling_king/pod_king_rolling_monthly.py = pod_export_bundle_v3.py L22, L26-47):
FEA/meta/keep 78 cols/rows over members with finite y4, anchors <50 skipped, label rr = rankdata(y4[ok])/max(n-1,1)-0.5; 32 monthly test folds 2024-01..2026-08;
K1 rule train rows: E_ts + 48*300 < first_test_E_ts - 60*14400 (embargo 60 anchors, strict '<'); per-fold causal ASSERT printed; train_rows asserted == folds_d1.json (K1).
Start model (both arms) = K1's 2024-01 model = axisA/models_d1/fold000_202401.txt (D1 retrain, same seed; its fold-0 test predictions are asserted bitwise == K1 slow_pred_rollm.npy).
MODE=ident : identity receipts — KR: start.refit(fold-0 train window, decay_rate=1.0) ⇒ model string sha / leaf values / fold-0 predictions unchanged;
             KC: lgb.train(num_boost_round=0, init_model=start) is refused by lightgbm 4.7.0 (ValueError, probe 09-06) ⇒ receipt = continued model truncated to its inherited 400 trees
             (predict num_iteration=400) predicts bitwise == start, i.e. the new trees are purely additive on the inherited structure (both the raw-API 1-round path and the sklearn 40-tree path are checked).
MODE=KR    : month t model = model(t-1).refit(train rows of fold t, label, decay_rate=0.9)  (tree structure fixed, leaf values re-estimated; 400 trees always).
MODE=KC    : month t model = LGBMRegressor(n_estimators=40, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, verbose=-1, n_jobs=NJOBS,
             random_state=SEED0+t).fit(train rows of fold t, init_model=model(t-1))  (continued training, +40 trees per month; sklearn param translation == K1's).
Both: fold 0 predictions come from the start model itself (Δ vs K1 = 0 in 2024-01 by construction). Test-fold predictions stitched exactly as K1
(float32 (nA, NW), NaN outside test folds; finite mask asserted == slow_pred_pinned). Secondary receipts: each model also predicts its own and the next 11 months
(ages 1..12) ⇒ per-(model, anchor) rank-IC matrix (IC–age curve, same construction as axisA d1_curve) and adjacent-month consistency
(per-anchor Spearman between model t and model t-1 on month t's anchors). KR also reports leaf-value change vs the previous model (parsed from model strings).
"""
import os, sys, json, time, hashlib, calendar, re
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

ROOT = "/workspace/review_scratch/cadence_seats/axisA_incremental"; AXA = "/workspace/review_scratch/cadence_seats/axisA"
os.makedirs(ROOT, exist_ok=True)
MODE = os.environ.get("MODE", ""); assert MODE in ("ident", "KR", "KC"), MODE
NJOBS = int(os.environ.get("NJOBS", "12")); assert NJOBS <= 12, "thread cap 12 (team-lead 09-06)"
LABEL_S = 48 * 300; SEED0 = 20260905; EMB = 60; EMB_S = EMB * 14400
DECAY = float(os.environ.get("DECAY", "0.9")); NEW_TREES = int(os.environ.get("NEW_TREES", "40")); AGE_MAX = 12
START_MODEL = f"{AXA}/models_d1/fold000_202401.txt"
K1_FOLDS_D1 = f"{AXA}/folds_d1.json"; K1_NPY = "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy"
LGBM_PARAMS = {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 63, "subsample": 0.8, "colsample_bytree": 0.8, "verbose": -1}
_CFG = {"MODE": MODE, "NJOBS": NJOBS, "EMB_anchors": EMB, "EMB_s": EMB_S, "LABEL_s": LABEL_S, "SEED0": SEED0, "DECAY": DECAY, "NEW_TREES": NEW_TREES, "AGE_MAX": AGE_MAX,
        "train_rule": "E_ts + 48*300 < first_test_E_ts - 60*14400 (K1 rule verbatim; strict '<')", "start_model": START_MODEL, "start_model_sha256": hashlib.sha256(open(START_MODEL, "rb").read()).hexdigest(),
        "lightgbm": lgb.__version__, "numpy": np.__version__, "python": sys.version.split()[0], "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "FEA": "/workspace/data/wide_fea_v2ext.npy", "META": "/workspace/data/wide_fea_v2ext_meta.npz", "k1_lgbm_params": LGBM_PARAMS, "k1_folds_d1_json": K1_FOLDS_D1, "k1_npy": K1_NPY,
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS")}
print("CONFIG " + json.dumps(_CFG), flush=True)
t00 = time.time()

# ── production data preparation: pod_export_bundle_v3.py L22, L26-47 verbatim (== axisA/pod_king_cadence.py) ──
PINS = json.load(open("/workspace/live_pins.json"))
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a, rows_k = [], [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32)); rows_k.append(m[ok].astype(np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); KCOL = np.concatenate(rows_k)
# ── end verbatim block (rows_k / KCOL = column index of each row, added for receipts only) ──
del rows_X, rows_y, rows_a, rows_k, FEA
A_ts = E_ts[A]
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
print(f"PREP X {X.shape} {X.dtype} Y {Y.shape} rows_anchors {len(np.unique(A))}/{nA} keep {len(keep)} E_ts[0] {iso(E_ts[0])} E_ts[-1] {iso(E_ts[-1])} prep_s {time.time()-t00:.1f}", flush=True)
assert X.shape == (2741477, 78), "PREP shape differs from axisA D1 receipt"

gm = [time.gmtime(int(t)) for t in E_ts]
keys = np.array([g.tm_year * 100 + g.tm_mon for g in gm]); keysA = keys[A]
fold_keys = [y * 100 + m for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 8)]
K1F = json.load(open(K1_FOLDS_D1))["folds"]; assert [f["key"] for f in K1F] == fold_keys
FOLD = []
for fi, fk in enumerate(fold_keys):
    te_anchor = np.where(keys == fk)[0]; t_first = int(E_ts[te_anchor].min()); t_last = int(E_ts[te_anchor].max()); cut = t_first - EMB_S
    tr = (A_ts + LABEL_S) < cut; te = keysA == fk
    tr_max = int(A_ts[tr].max()); tr_min = int(A_ts[tr].min()); lhs = tr_max + LABEL_S; rhs = cut; ok_assert = lhs < rhs
    print(f"ASSERT fold {fi} key {fk}: max(train E_ts)+48*300 = {lhs} ({iso(lhs)}) < min(test E_ts)-60*14400 = {rhs} ({iso(rhs)}) -> {ok_assert} gap {(rhs - lhs) / 14400:.2f} anchors; train_span {iso(tr_min)}..{iso(tr_max)} test_span {iso(t_first)}..{iso(t_last)}", flush=True)
    assert ok_assert and not np.any(tr & te) and tr_max + LABEL_S <= t_first - 14400
    assert int(tr.sum()) == K1F[fi]["train_rows"], f"train_rows differ from K1 fold {fi}: {int(tr.sum())} vs {K1F[fi]['train_rows']}"
    FOLD.append({"fi": fi, "key": int(fk), "tr": tr, "te": te, "t_first": t_first, "t_last": t_last, "train_rows": int(tr.sum()), "test_rows": int(te.sum()), "train_first": tr_min, "train_last": tr_max, "gap_anchors": (rhs - lhs) / 14400})
print(f"FOLDS {len(FOLD)} all K1 train_rows equal; prep+folds {time.time()-t00:.0f}s", flush=True)

K1 = np.load(K1_NPY); K1_rows = K1[A, KCOL]   # K1 prediction per row (NaN outside K1 test folds)
def model_sha(b): return hashlib.sha256(b.model_to_string().encode()).hexdigest()[:16]
def leaf_values(b):
    return np.array([float(v) for v in re.findall(r"leaf_value=([^\n]+)", b.model_to_string()) for v in v.split()], dtype=np.float64)
def load_start():
    b = lgb.Booster(model_file=START_MODEL); b.params["num_threads"] = NJOBS; return b   # NOTE: Booster.reset_parameter on a file-loaded booster segfaults in lightgbm 4.7.0 (probe 09-06 02:2xZ); params dict edit propagates to refit; predict gets num_threads explicitly
M0 = load_start()
p0 = M0.predict(X[FOLD[0]["te"]], num_threads=NJOBS).astype(np.float32); k1_0 = K1_rows[FOLD[0]["te"]]
start_eq = bool(np.array_equal(p0, k1_0)); start_maxabs = float(np.nanmax(np.abs(p0.astype(np.float64) - k1_0)))
print(f"START RECEIPT: models_d1/fold000_202401.txt trees {M0.num_trees()} fold-0 test predictions == K1 slow_pred_rollm rows: {start_eq} max|Δ| {start_maxabs:.3e} n {len(p0)}", flush=True)
assert start_eq, "start model does not reproduce K1 fold-0 predictions"

if MODE == "ident":
    rec = {"start_pred_equal_k1_fold0": start_eq, "start_pred_maxabs": start_maxabs}
    t0 = time.time(); R1 = M0.refit(X[FOLD[0]["tr"]], Y[FOLD[0]["tr"]], decay_rate=1.0, num_threads=NJOBS)   # KR identity: same window, decay 1.0 ⇒ leaves unchanged
    R1.params["num_threads"] = NJOBS
    s0, s1 = model_sha(M0), model_sha(R1); lv0, lv1 = leaf_values(M0), leaf_values(R1)
    pr1 = R1.predict(X[FOLD[0]["te"]], num_threads=NJOBS).astype(np.float32)
    str0 = M0.model_to_string().splitlines(); str1 = R1.model_to_string().splitlines(); ndiff = sum(1 for a_, b_ in zip(str0, str1) if a_ != b_) + abs(len(str0) - len(str1))
    diff_lines = [(a_[:60], b_[:60]) for a_, b_ in zip(str0, str1) if a_ != b_][:5]
    rec["KR_identity"] = {"decay_rate": 1.0, "refit_s": round(time.time() - t0, 1), "model_sha_equal": s0 == s1, "sha_start": s0, "sha_refit": s1, "n_leaf_values": int(len(lv0)), "leaf_values_equal": bool(len(lv0) == len(lv1) and np.array_equal(lv0, lv1)),
                         "leaf_maxabs": float(np.max(np.abs(lv0 - lv1))) if len(lv0) == len(lv1) else None, "fold0_pred_equal": bool(np.array_equal(pr1, p0)), "fold0_pred_maxabs": float(np.max(np.abs(pr1.astype(np.float64) - p0))), "model_string_lines_differ": ndiff, "diff_examples": diff_lines}
    print("KR_IDENTITY " + json.dumps(rec["KR_identity"]), flush=True)
    # KC identity: 0 new trees with init_model ⇒ predictions bitwise == start
    tr1, te1 = FOLD[1]["tr"], FOLD[1]["te"]; params = {"objective": "regression", "learning_rate": 0.05, "num_leaves": 63, "bagging_fraction": 0.8, "bagging_freq": 0, "feature_fraction": 0.8, "verbose": -1, "num_threads": NJOBS, "seed": SEED0 + 1}
    t0 = time.time(); path_used = "lgb.train(num_boost_round=0, init_model=start)"
    try:
        C0 = lgb.train(params, lgb.Dataset(X[tr1], Y[tr1], free_raw_data=False), num_boost_round=0, init_model=M0)
        pc = C0.predict(X[te1], num_threads=NJOBS).astype(np.float32); ntr = C0.num_trees()
    except Exception as e:
        path_used = f"fallback: lgb.train(num_boost_round=1, init_model=start).predict(num_iteration=400) [0 rounds refused: {type(e).__name__}: {str(e)[:120]}]"
        C0 = lgb.train(params, lgb.Dataset(X[tr1], Y[tr1], free_raw_data=False), num_boost_round=1, init_model=M0)
        pc = C0.predict(X[te1], num_iteration=M0.num_trees(), num_threads=NJOBS).astype(np.float32); ntr = C0.num_trees()
    pm = M0.predict(X[te1], num_threads=NJOBS).astype(np.float32)
    rec["KC_identity"] = {"path": path_used, "s": round(time.time() - t0, 1), "trees_after": int(ntr), "fold1_pred_equal_start": bool(np.array_equal(pc, pm)), "fold1_pred_maxabs": float(np.max(np.abs(pc.astype(np.float64) - pm))), "n": int(len(pc))}
    print("KC_IDENTITY " + json.dumps(rec["KC_identity"]), flush=True)
    # sklearn continued-training path used by MODE=KC: 40 trees appended ⇒ num_trees 440 and predict(num_iteration=400) == start (structure preserved)
    t0 = time.time(); g = lgb.LGBMRegressor(n_estimators=NEW_TREES, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=NJOBS, verbose=-1, random_state=SEED0 + 1).fit(X[tr1], Y[tr1], init_model=M0)
    b = g.booster_; ptr = b.predict(X[te1], num_iteration=M0.num_trees(), num_threads=NJOBS).astype(np.float32)
    rec["KC_sklearn_path"] = {"fit_s": round(time.time() - t0, 1), "trees_after": int(b.num_trees()), "expected": int(M0.num_trees() + NEW_TREES), "truncated_pred_equal_start": bool(np.array_equal(ptr, pm)), "truncated_pred_maxabs": float(np.max(np.abs(ptr.astype(np.float64) - pm)))}
    print("KC_SKLEARN_PATH " + json.dumps(rec["KC_sklearn_path"]), flush=True)
    rec["all_identities_hold"] = bool(rec["KR_identity"]["leaf_values_equal"] and rec["KR_identity"]["fold0_pred_equal"] and rec["KC_identity"]["fold1_pred_equal_start"] and rec["KC_sklearn_path"]["truncated_pred_equal_start"] and rec["KC_sklearn_path"]["trees_after"] == rec["KC_sklearn_path"]["expected"])
    json.dump({"config": _CFG, "identity": rec, "wall_s": round(time.time() - t00, 1)}, open(f"{ROOT}/identity_receipt.json", "w"), indent=1)
    print(f"IDENTITY_DONE all_identities_hold {rec['all_identities_hold']} wall {time.time()-t00:.0f}s", flush=True); sys.exit(0)

MDIR = f"{ROOT}/models_{MODE}"; os.makedirs(MDIR, exist_ok=True)
PRED = np.full((nA, NW), np.nan, np.float32); PM = []; folds = []; prev = M0; prev_lv = leaf_values(M0) if MODE == "KR" else None
mi = np.array([((g.tm_year - 2024) * 12 + (g.tm_mon - 1)) if g.tm_year >= 2024 else -1 for g in gm])
for f in FOLD:
    fi = f["fi"]; t0 = time.time()
    if fi == 0:
        cur = M0; fit_s = 0.0; how = "start model (K1 2024-01)"
    elif MODE == "KR":
        cur = prev.refit(X[f["tr"]], Y[f["tr"]], decay_rate=DECAY, num_threads=NJOBS); cur.params["num_threads"] = NJOBS; fit_s = time.time() - t0; how = f"refit(prev, fold train window, decay {DECAY})"
    else:
        g = lgb.LGBMRegressor(n_estimators=NEW_TREES, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=NJOBS, verbose=-1, random_state=SEED0 + fi).fit(X[f["tr"]], Y[f["tr"]], init_model=prev)
        cur = g.booster_; fit_s = time.time() - t0; how = f"LGBMRegressor(n_estimators={NEW_TREES}, seed {SEED0 + fi}).fit(fold train window, init_model=prev)"
    mpath = f"{MDIR}/fold{fi:03d}_{f['key']}.txt"; cur.save_model(mpath); bsha = model_sha(cur); mbytes = os.path.getsize(mpath)
    pv = cur.predict(X[f["te"]], num_threads=NJOBS); a_te = A[f["te"]]; ics = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); PRED[a, m[okm]] = pv[sel]; ics.append(sp(pv[sel], y4[a, m[okm]]))
    # future predictions (ages 1..AGE_MAX) for the IC–age curve and adjacent-month consistency
    t1 = time.time(); fut_end = FOLD[fi + AGE_MAX]["t_first"] if fi + AGE_MAX < len(FOLD) else E_ts[-1] + 1
    fut = (A_ts >= f["t_first"]) & (A_ts < fut_end); pf = cur.predict(X[fut], num_threads=NJOBS); a_f = A[fut]
    Pm = np.full((nA, NW), np.nan, np.float32); order = np.argsort(a_f, kind="stable"); a_s = a_f[order]; p_s = pf[order]; bounds = np.searchsorted(a_s, np.arange(nA + 1))
    for a in np.unique(a_s):
        m = members[a]; okm = np.isfinite(y4[a, m]); Pm[a, m[okm]] = p_s[bounds[a]:bounds[a + 1]]
    PM.append(Pm)
    cons = float("nan");
    if fi >= 1:
        cs = [sp(PM[fi][a], PM[fi - 1][a]) for a in np.unique(a_te)]; cons = float(np.nanmean(cs))
    rec = {"fold": fi, "key": f["key"], "how": how, "seed": (SEED0 + fi if (MODE == "KC" and fi > 0) else None), "train_rows": f["train_rows"], "train_rows_equal_k1": True, "test_rows": f["test_rows"], "test_anchors": int(len(np.unique(a_te))),
           "fit_s": round(fit_s, 1), "predict_future_s": round(time.time() - t1, 1), "rankIC_raw_y4": round(float(np.nanmean(ics)), 5), "k1_rankIC_raw_y4": K1F[fi]["rankIC_raw_y4"], "n_trees": int(cur.num_trees()), "model_bytes": int(mbytes), "booster_sha256": bsha,
           "consistency_prev_spearman": round(cons, 4) if np.isfinite(cons) else None, "train_first": f["train_first"], "train_last": f["train_last"], "test_first": f["t_first"], "test_last": f["t_last"], "gap_anchors": f["gap_anchors"], "future_anchors": int(len(np.unique(a_f)))}
    if MODE == "KR" and fi >= 1:
        lv = leaf_values(cur); d = lv - prev_lv if len(lv) == len(prev_lv) else None
        rec["leaf_change"] = {"n_leaves": int(len(lv)), "mean_abs_delta": float(np.mean(np.abs(d))) if d is not None else None, "share_changed": float((np.abs(d) > 0).mean()) if d is not None else None, "mean_abs_leaf": float(np.mean(np.abs(lv)))}; prev_lv = lv
    folds.append(rec); prev = cur
    print(f"FOLD {fi} key {f['key']} {how} train_rows {f['train_rows']} test_anchors {rec['test_anchors']} fit_s {fit_s:.1f} rankIC {rec['rankIC_raw_y4']:+.4f} (K1 {rec['k1_rankIC_raw_y4']:+.4f}) trees {rec['n_trees']} bytes {mbytes} cons_prev {cons:+.3f} booster {bsha} elapsed {time.time()-t00:.0f}s", flush=True)

pin = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy"); fin = np.isfinite(PRED); mask_equal = bool(np.array_equal(np.isfinite(pin), fin)); fin_anchor = fin.any(1)
path = f"{ROOT}/slow_pred_{MODE}.npy"; np.save(path, PRED.astype(np.float32)); sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
eq0 = bool(np.array_equal(PRED[keys == fold_keys[0]], K1[keys == fold_keys[0]], equal_nan=True))
print(f"SAVED {path} shape {PRED.shape} sha256 {sha} finite_anchors {int(fin_anchor.sum())} pre2024_all_nan {bool(not fin[yrs < 2024].any())} finite_mask_equal_pinned {mask_equal} fold0_equal_k1 {eq0}", flush=True)
# IC–age curve (axisA d1_curve construction): IC[model, anchor] on ages 1..12; paired age1 − age12 on anchors where all 12 exist
nM = len(PM); IC = np.full((nM, nA), np.nan, np.float32)
for fi in range(nM):
    for i in np.where(np.isfinite(PM[fi]).any(1))[0]:
        m = members[i]; IC[fi, i] = sp(PM[fi][i, m], y4[i, m])
age_ic = {}; common = [i for i in range(nA) if mi[i] >= AGE_MAX - 1 and all(0 <= mi[i] - (k - 1) < nM and np.isfinite(IC[mi[i] - (k - 1), i]) for k in range(1, AGE_MAX + 1))]
for k in range(1, AGE_MAX + 1): age_ic[k] = float(np.mean([IC[mi[i] - (k - 1), i] for i in common]))
d112 = np.array([IC[mi[i], i] - IC[mi[i] - (AGE_MAX - 1), i] for i in common]); age_delta = {"age1_minus_age12": float(d112.mean()), "se": float(d112.std(ddof=1) / np.sqrt(len(d112))), "n": int(len(d112))}
np.savez_compressed(f"{ROOT}/ic_{MODE}.npz", IC=IC, E_ts=E_ts, month_index=mi, model_key=np.array([f["key"] for f in folds]), consistency=np.array([f["consistency_prev_spearman"] if f["consistency_prev_spearman"] is not None else np.nan for f in folds]))
print(f"IC_AGE {MODE}: " + json.dumps({"by_age": {k: round(v, 5) for k, v in age_ic.items()}, "paired": age_delta}), flush=True)
cons = [f["consistency_prev_spearman"] for f in folds if f["consistency_prev_spearman"] is not None]
outj = {"config": _CFG, "start_receipt": {"pred_equal_k1_fold0": start_eq, "maxabs": start_maxabs}, "folds": folds, "output": path, "sha256": sha, "finite_mask_equal_pinned": mask_equal, "fold0_equal_k1": eq0,
        "ic_age": {"by_age": age_ic, "paired_age1_minus_age12": age_delta}, "consistency_prev_mean": float(np.mean(cons)) if cons else None, "consistency_prev_min": float(np.min(cons)) if cons else None,
        "total_fit_s": round(sum(f["fit_s"] for f in folds), 1), "final_trees": folds[-1]["n_trees"], "final_model_bytes": folds[-1]["model_bytes"], "wall_s": round(time.time() - t00, 1)}
json.dump(outj, open(f"{ROOT}/folds_{MODE}.json", "w"), indent=1)
print(f"DONE {MODE} folds {len(folds)} total_fit_s {outj['total_fit_s']} final_trees {outj['final_trees']} consistency_mean {outj['consistency_prev_mean']} wall {time.time()-t00:.0f}s", flush=True)
