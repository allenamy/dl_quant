"""pod_king_cadence.py — PREREG_retrain_cadence_and_seat_rule_2026-09-05 §1 (axis A) — pod, read-only inputs.
Data preparation + LGBM recipe = /workspace/review_scratch/rolling_king/pod_king_rolling_monthly.py VERBATIM
(itself = /workspace/pod_export_bundle_v3.py L22, L26-47): FEA/meta/keep 78 cols/rows over members with finite y4, anchors <50 skipped,
label rr = rankdata(y4[ok])/max(n-1,1)-0.5; LGBMRegressor(400, 0.05, 63, subsample 0.8, colsample 0.8, verbose -1), n_jobs=NJOBS (48),
random_state = 20260905 + fold_index.
MODE=d1       : diagnostic D1 — the 32 K1 monthly folds (test = calendar month 2024-01..2026-08, embargo 60 anchors, K1 rule
                E_ts + 48*300 < first_test_E_ts - 60*14400) are RETRAINED with the same seeds (K1 saved no boosters); each fold model
                predicts ALL rows from its own test-month start through 2026-08-30. Receipts: per-fold booster sha256 vs folds_rollm.json,
                age-1 stitched array vs slow_pred_rollm.npy (array_equal, equal_nan). Outputs: d1_pred_age{1..12}.npy (age k for an anchor in
                calendar month M = model whose test month is M-(k-1)), d1_matrices.npz (per (model, anchor) rank-IC and king-leg return,
                raw y4 and dlw y4s), folds_d1.json, models_d1/.
MODE=monthly1 : K2 — monthly folds, embargo 1 anchor: train rows = anchors with E_ts + 48*300 <= first_test_E_ts - 14400
                (label window (E, E+4h] realized by the previous anchor). Output slow_pred_rollm1.npy + folds_rollm1.json.
MODE=weekly1  : K3 — calendar-week folds (Monday 00:00Z, 2024-01-01 .. 2026-08-24), same 1-anchor rule. Output slow_pred_rollw1.npy + folds_rollw1.json.
ASSERT per fold (printed): d1: max(train E_ts)+48*300 <  min(test E_ts)-60*14400 ; monthly1/weekly1: max(train E_ts)+48*300 <= min(test E_ts)-14400.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
sys.path.insert(0, "/workspace")
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

OUT = "/workspace/review_scratch/cadence_seats/axisA"
os.makedirs(OUT, exist_ok=True)
MODE = os.environ.get("MODE", ""); assert MODE in ("d1", "monthly1", "weekly1"), MODE
NJOBS = int(os.environ.get("NJOBS", "48"))
LABEL_S = 48 * 300
SEED0 = 20260905
if MODE == "d1":
    EMB = 60; EMB_S = EMB * 14400; TAG = "d1"; STRICT = True
    TRAIN_RULE = "E_ts + 48*300 < first_test_E_ts - 60*14400 (rolling_king K1 rule verbatim; strict '<')"
else:
    EMB = 1; EMB_S = 14400; TAG = {"monthly1": "rollm1", "weekly1": "rollw1"}[MODE]; STRICT = False
    TRAIN_RULE = "E_ts + 48*300 <= first_test_E_ts - 14400 (label window (E,E+4h] realized by the previous anchor; '<=')"
K1_FOLDS = "/workspace/review_scratch/rolling_king/folds_rollm.json"; K1_NPY = "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy"
_CFG = {"MODE": MODE, "TAG": TAG, "NJOBS": NJOBS, "EMB_anchors": EMB, "EMB_s": EMB_S, "LABEL_s": LABEL_S, "SEED0": SEED0, "train_rule": TRAIN_RULE,
        "assert": ("max(train E_ts)+48*300 < min(test E_ts)-60*14400" if STRICT else "max(train E_ts)+48*300 <= min(test E_ts)-14400"),
        "lightgbm": lgb.__version__, "numpy": np.__version__, "python": sys.version.split()[0],
        "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "FEA": "/workspace/data/wide_fea_v2ext.npy", "META": "/workspace/data/wide_fea_v2ext_meta.npz",
        "PANEL": "/workspace/data/wide_panel_4h_v2ext.npz", "DLW": "/workspace/data/dlw_targets.npz",
        "lgbm_params": {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 63, "subsample": 0.8, "colsample_bytree": 0.8, "verbose": -1},
        "k1_folds_json": K1_FOLDS, "k1_npy": K1_NPY}
print("CONFIG " + json.dumps(_CFG), flush=True)
t00 = time.time()

# ── production data preparation: /workspace/pod_export_bundle_v3.py L22, L26-47 verbatim (== rolling_king/pod_king_rolling_monthly.py) ──
PINS = json.load(open("/workspace/live_pins.json"))          # Δ4/Δ5
FEA = np.load("/workspace/data/wide_fea_v2ext.npy")
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert [names[k] for k in keep] == PINS["keep_names"], "keep_names 与在役不一致"  # Δ5
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]
    yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
YRA = yrs[A]
# ── end verbatim block ──
del rows_X, rows_y, rows_a, FEA
A_ts = E_ts[A]
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
print(f"PREP X {X.shape} {X.dtype} Y {Y.shape} rows_anchors {len(np.unique(A))}/{nA} keep {len(keep)} "
      f"E_ts[0] {iso(E_ts[0])} E_ts[-1] {iso(E_ts[-1])} prep_s {time.time()-t00:.1f}", flush=True)

gm = [time.gmtime(int(t)) for t in E_ts]
if MODE in ("d1", "monthly1"):
    keys = np.array([g.tm_year * 100 + g.tm_mon for g in gm])
    fold_keys = [y * 100 + m for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 8)]
    key_label = lambda fk: str(fk)
else:
    T0 = calendar.timegm((2024, 1, 1, 0, 0, 0)); assert time.gmtime(T0).tm_wday == 0, "2024-01-01 must be a Monday"
    keys = np.where(E_ts >= T0, (E_ts - T0) // (7 * 86400), -1).astype(np.int64)
    fold_keys = list(range(0, int(keys.max()) + 1))
    key_label = lambda fk: time.strftime("%Y-%m-%d", time.gmtime(T0 + int(fk) * 7 * 86400))
keysA = keys[A]
PRED = np.full((nA, NW), np.nan, np.float32)
folds = []
MDIR = f"{OUT}/models_{TAG}"; os.makedirs(MDIR, exist_ok=True)
if MODE == "d1":
    K1F = json.load(open(K1_FOLDS))["folds"]; assert len(K1F) == len(fold_keys) and [f["key"] for f in K1F] == fold_keys, "K1 folds json mismatch"
    PM = []   # per-model full-width predictions from its test month onward
for fi, fk in enumerate(fold_keys):
    te_anchor = np.where(keys == fk)[0]
    assert len(te_anchor) > 0, f"empty fold {fk}"
    t_first = int(E_ts[te_anchor].min()); t_last = int(E_ts[te_anchor].max())
    cut = t_first - EMB_S
    tr = ((A_ts + LABEL_S) < cut) if STRICT else ((A_ts + LABEL_S) <= cut)
    te = keysA == fk
    tr_max = int(A_ts[tr].max()); tr_min = int(A_ts[tr].min())
    lhs = tr_max + LABEL_S; rhs = cut
    ok_assert = (lhs < rhs) if STRICT else (lhs <= rhs)
    cmp = "<" if STRICT else "<="
    print(f"ASSERT fold {fi} key {key_label(fk)}: max(train E_ts)+48*300 = {lhs} ({iso(lhs)}) {cmp} min(test E_ts)-{EMB}*14400 = {rhs} ({iso(rhs)}) -> {ok_assert} "
          f"gap {rhs - lhs}s = {(rhs - lhs) / 14400:.2f} anchors; train_span {iso(tr_min)}..{iso(tr_max)} test_span {iso(t_first)}..{iso(t_last)}", flush=True)
    assert ok_assert, f"CAUSALITY ASSERT FAILED fold {fi} {fk}: {lhs} vs {rhs}"
    assert not np.any(tr & te), "train/test row overlap"
    assert tr_max + LABEL_S <= t_first - 14400, "last training label not realized by the previous anchor"
    seed = SEED0 + fi
    t0 = time.time()
    gbm = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                            subsample=0.8, colsample_bytree=0.8, n_jobs=NJOBS, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
    fit_s = time.time() - t0
    bsha = hashlib.sha256(gbm.booster_.model_to_string().encode()).hexdigest()[:16]
    gbm.booster_.save_model(f"{MDIR}/fold{fi:03d}_{key_label(fk)}.txt")
    pv = gbm.predict(X[te]); a_te = A[te]
    ics = []
    for a in np.unique(a_te):
        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])
        PRED[a, m[okm]] = pv[sel]
        ics.append(sp(pv[sel], y4[a, m[okm]]))
    rec = {"fold": fi, "key": (int(fk) if MODE != "weekly1" else key_label(fk)), "seed": seed, "train_rows": int(tr.sum()), "train_anchors": int(len(np.unique(A[tr]))),
           "test_anchors_in_fold": int(len(te_anchor)), "test_anchors_with_rows": int(len(np.unique(a_te))), "test_rows": int(te.sum()),
           "fit_s": round(fit_s, 1), "rankIC_raw_y4": round(float(np.nanmean(ics)), 5), "assert_lhs": lhs, "assert_rhs": rhs, "assert_cmp": cmp, "assert_ok": bool(ok_assert),
           "gap_anchors": (rhs - lhs) / 14400, "train_first": tr_min, "train_last": tr_max, "test_first": t_first, "test_last": t_last, "booster_sha256": bsha}
    if MODE == "d1":
        rec["k1_booster_sha256"] = K1F[fi]["booster_sha256"]; rec["booster_equal_k1"] = bool(bsha == K1F[fi]["booster_sha256"])
        rec["k1_train_rows"] = K1F[fi]["train_rows"]; rec["train_rows_equal_k1"] = bool(rec["train_rows"] == K1F[fi]["train_rows"])
        # predict every row from this model's test-month start onward (its future), full width
        t1 = time.time(); fut = A_ts >= t_first
        pf = gbm.predict(X[fut]); a_f = A[fut]
        Pm = np.full((nA, NW), np.nan, np.float32)
        order = np.argsort(a_f, kind="stable"); a_s = a_f[order]; p_s = pf[order]
        bounds = np.searchsorted(a_s, np.arange(nA + 1))
        for a in np.unique(a_s):
            m = members[a]; okm = np.isfinite(y4[a, m]); Pm[a, m[okm]] = p_s[bounds[a]:bounds[a + 1]]
        PM.append(Pm); rec["future_rows"] = int(fut.sum()); rec["future_anchors"] = int(len(np.unique(a_f))); rec["predict_future_s"] = round(time.time() - t1, 1)
    folds.append(rec)
    extra = (f" booster_equal_k1 {rec['booster_equal_k1']} future_anchors {rec['future_anchors']} pred_s {rec['predict_future_s']}" if MODE == "d1" else "")
    print(f"FOLD {fi} key {key_label(fk)} seed {seed} train_rows {rec['train_rows']} train_anchors {rec['train_anchors']} "
          f"test_anchors {rec['test_anchors_with_rows']}/{rec['test_anchors_in_fold']} test_rows {rec['test_rows']} "
          f"fit_s {fit_s:.1f} rankIC {rec['rankIC_raw_y4']:+.4f} booster {bsha}{extra} elapsed {time.time()-t00:.0f}s", flush=True)

pin = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")
fin = np.isfinite(PRED); fin_anchor = fin.any(1)
first_fin = int(np.where(fin_anchor)[0][0]); last_fin = int(np.where(fin_anchor)[0][-1])
mask_equal = bool(np.array_equal(np.isfinite(pin), fin))
if MODE == "d1":
    k1 = np.load(K1_NPY)
    eq_k1 = bool(np.array_equal(PRED, k1, equal_nan=True)); maxabs = float(np.nanmax(np.abs(PRED - k1)))
    print(f"D1 RECEIPT: stitched test-fold predictions vs K1 slow_pred_rollm.npy array_equal(equal_nan) {eq_k1} max|Δ| {maxabs:.3e} "
          f"boosters_equal_k1 {sum(f['booster_equal_k1'] for f in folds)}/{len(folds)} train_rows_equal_k1 {sum(f['train_rows_equal_k1'] for f in folds)}/{len(folds)}", flush=True)
    # age-stitched arrays: anchor in calendar month index mi (2024-01 = 0); age k -> model index mi-(k-1)
    mi = np.array([((g.tm_year - 2024) * 12 + (g.tm_mon - 1)) if g.tm_year >= 2024 else -1 for g in gm])
    ages_out = {}
    for k in range(1, 13):
        Ak = np.full((nA, NW), np.nan, np.float32)
        for i in range(nA):
            fi = mi[i] - (k - 1)
            if mi[i] >= 0 and 0 <= fi < len(PM): Ak[i] = PM[fi][i]
        p = f"{OUT}/d1_pred_age{k}.npy"; np.save(p, Ak)
        ages_out[k] = {"path": p, "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(), "finite_anchors": int(np.isfinite(Ak).any(1).sum())}
        if k == 1:
            eq1 = bool(np.array_equal(Ak, PRED, equal_nan=True)); print(f"D1 age-1 stitched == test-fold stitched: {eq1}", flush=True); ages_out[1]["equal_testfold_stitch"] = eq1
    # per-(model, anchor) rank-IC and king-leg return (production leg definition), raw y4 and dlw y4s
    PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_ts = set(PW["ts"].astype(np.int64).tolist())
    DT = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); dts = DT["E_ts"].astype(np.int64); y4s_src = DT["y4s"]; dmap = {int(t): k for k, t in enumerate(dts)}
    Y4S = np.full((nA, NW), np.nan, np.float32)
    for i in range(nA):
        kk = dmap.get(int(E_ts[i]))
        if kk is not None: Y4S[i] = y4s_src[kk]
    has_panel = np.array([int(t) in pw_ts for t in E_ts])
    def xz(v):
        ok = np.isfinite(v); out = np.full(len(v), np.nan)
        if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
        return out
    def leg(score, yv):   # production leg definition (pod_export_bundle_v3.py L102-109 == device legs())
        ok = np.isfinite(yv); z = np.nan_to_num(xz(score)); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum(); return float((z / g * np.nan_to_num(yv, nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0
    nM = len(PM); IC_raw = np.full((nM, nA), np.nan, np.float32); IC_y4s = IC_raw.copy(); LEG_raw = IC_raw.copy(); LEG_y4s = IC_raw.copy()
    t1 = time.time()
    for fi in range(nM):
        tf = folds[fi]["test_first"]
        for i in np.where(E_ts >= tf)[0]:
            m = members[i]; p = PM[fi][i, m]
            if not np.isfinite(p).any(): continue
            IC_raw[fi, i] = sp(p, y4[i, m]); IC_y4s[fi, i] = sp(p, Y4S[i, m])
            if has_panel[i]: LEG_raw[fi, i] = leg(p, y4[i, m]); LEG_y4s[fi, i] = leg(p, Y4S[i, m])
    np.savez_compressed(f"{OUT}/d1_matrices.npz", IC_raw=IC_raw, IC_y4s=IC_y4s, LEG_raw=LEG_raw, LEG_y4s=LEG_y4s, E_ts=E_ts, month_index=mi, has_panel=has_panel,
                        has_dlw=np.isfinite(Y4S).any(1), model_test_first=np.array([f["test_first"] for f in folds]), model_train_last=np.array([f["train_last"] for f in folds]),
                        model_key=np.array([f["key"] for f in folds]), label_s=LABEL_S)
    print(f"D1 matrices saved ({time.time()-t1:.0f}s): IC/LEG shape {IC_raw.shape} finite IC_raw {int(np.isfinite(IC_raw).sum())} LEG_raw {int(np.isfinite(LEG_raw).sum())} anchors_with_dlw {int(np.isfinite(Y4S).any(1).sum())}", flush=True)
    path = f"{OUT}/slow_pred_d1_testfold.npy"; np.save(path, PRED.astype(np.float32))
else:
    path = f"{OUT}/slow_pred_{TAG}.npy"; np.save(path, PRED.astype(np.float32))
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
print(f"SAVED {path} shape {PRED.shape} dtype {PRED.dtype} sha256 {sha} finite_anchors {int(fin_anchor.sum())} "
      f"first_finite {iso(E_ts[first_fin])} last_finite {iso(E_ts[last_fin])} pre2024_all_nan {bool(not fin[yrs < 2024].any())} finite_mask_equal_pinned {mask_equal}", flush=True)
outj = {"config": _CFG, "folds": folds, "output": path, "sha256": sha, "finite_mask_equal_pinned": mask_equal, "all_asserts_true": bool(all(f["assert_ok"] for f in folds)),
        "total_fit_s": round(sum(f["fit_s"] for f in folds), 1), "wall_s": round(time.time() - t00, 1)}
if MODE == "d1": outj["ages"] = ages_out; outj["stitched_equal_k1"] = eq_k1; outj["stitched_maxabs_vs_k1"] = maxabs
json.dump(outj, open(f"{OUT}/folds_{TAG}.json", "w"), indent=1)
print(f"DONE {MODE} folds {len(folds)} total_fit_s {outj['total_fit_s']} wall {time.time()-t00:.0f}s", flush=True)
