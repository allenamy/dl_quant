"""gate_G4b.py — PREREG §2 G4 retraining items on the REBUILT king pipeline (same X/Y/fold construction as pod_slow_hist_folds.py L11-30,
same LGBM params n_estimators=400 lr=0.05 leaves=63 subsample=0.8 colsample=0.8 n_jobs=-1):
 (iii) shuffle-future null: for seeds 0,1,2 and folds YV in 2022..2026, the TRAINING labels are permuted across rows within each
       training year (feature-label link destroyed, year mix kept); the model is refit and scored out-of-sample on year YV with the
       per-anchor Spearman IC mean. Requirement: |null IC| < 2*SE for all 15, SE = std(per-anchor true IC of the stage-5 model on that
       fold) / sqrt(n_anchors)  (dlw_judge.py L122-148 convention).
 (iv)  offset spectrum: corr_k = mean over anchors i of Spearman(PRED[i, m_i], y4[i+k, m_i]) for k in [-6, 6] (anchor offsets on the meta
       grid, only where E_ts[i+k]-E_ts[i] == k*14400). Requirement: peak at k=0 and max|corr(k in 1..3)| < corr(0).
 (v)   embargo invariance: folds 2024 and 2025 refit with train = years < YV AND anchor index < first test anchor − 60; |IC_embargo −
       IC_no_embargo| < 0.002, where IC_no_embargo is (a) the stage-5 prediction file's fold IC and (b) an in-script refit without embargo
       (same code path, same thread count) — both deltas are reported; the gate uses (b).
Writes results/G4b.json and results/G4_verdict.json (hist_king_admitted = G4a pass AND G4b pass). Exit 0 always."""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
ROOT = os.environ.get("JR_ROOT", "/workspace/review_scratch/jpline_rebuild")   # JR_ROOT only for the dry-test harness
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.0f}s]", *a, flush=True)
FEA = np.load(f"{ROOT}/data/wide_fea_hist_rebuilt.npy", mmap_mode="r")
MT = np.load(f"{ROOT}/data/wide_fea_hist_meta_rebuilt.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
PRED0 = np.load(f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy")
out_quick = os.environ.get("G4B_QUICK") == "1"
out = {"dry_test_quick_mode": out_quick, "self_sha256": sha(os.path.abspath(__file__)), "king_sha256": sha(f"{ROOT}/data/slow_pred_hist_oos_rebuilt.npy"), "lightgbm": lgb.__version__, "n_features": len(keep), "n_threads": os.cpu_count()}
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def anchor_ics(P, anchors):
    v = []
    for a in anchors:
        m = members[a]; v.append(sp(P[a, m], y4[a, m]))
    return np.array(v)
# ---- X / Y / A exactly as pod_slow_hist_folds.py L17-23
rows_X, rows_y, rows_a = [], [], []
for i in range(nA):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, keep], np.float32)); rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]; del rows_X, rows_y, rows_a
log("X", X.shape)
PAR = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, verbose=-1)
if out_quick: PAR["n_estimators"] = 20; print("G4B_QUICK=1: DRY TEST ONLY (20 trees) — not a valid gate run", flush=True)
def fit_predict(tr, te):
    g = lgb.LGBMRegressor(**PAR).fit(X[tr], Y[tr]); pv = g.predict(X[te]); P = np.full((nA, NW), np.nan, np.float32); a_te = A[te]
    for a in np.unique(a_te):
        s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); P[a, m[okm]] = pv[s_]
    return P, np.unique(a_te)
FOLDS = (2022, 2023, 2024, 2025, 2026)
# true per-fold IC of the stage-5 model (reference SE)
true_ic = {}
for YV in FOLDS:
    anchors = np.unique(A[YRA == YV]); ics = anchor_ics(PRED0, anchors) if len(anchors) else np.array([np.nan])
    true_ic[YV] = {"mean": float(np.nanmean(ics)) if np.isfinite(ics).any() else float("nan"), "se": float(np.nanstd(ics) / np.sqrt(max(np.isfinite(ics).sum(), 1))) if np.isfinite(ics).any() else float("nan"), "n_anchors": int(len(anchors))}
log("true fold IC (stage-5 king):", {k: round(v["mean"], 4) for k, v in true_ic.items()})
# ---- (iii) shuffle-future null
null = []; ok_iii = True
for seed in (0, 1, 2):
    rng = np.random.default_rng(seed)
    for YV in FOLDS:
        tr = YRA < YV; te = YRA == YV
        if te.sum() == 0 or tr.sum() < 20000:   # same skip rule as pod_slow_hist_folds.py L29; a skipped fold counts as FAIL for (iii)
            ok_iii = False; null.append({"seed": seed, "fold": YV, "skipped": True, "train_rows": int(tr.sum()), "pass": False}); log(f"(iii) seed {seed} fold {YV}: SKIPPED (train rows {int(tr.sum())}) -> FAIL"); continue
        Yp = Y.copy()
        for y in np.unique(YRA[tr]):
            idx = np.where(tr & (YRA == y))[0]; Yp[idx] = Yp[rng.permutation(idx)]
        g = lgb.LGBMRegressor(**PAR).fit(X[tr], Yp[tr]); pv = g.predict(X[te]); P = np.full((nA, NW), np.nan, np.float32); a_te = A[te]
        for a in np.unique(a_te):
            s_ = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m]); P[a, m[okm]] = pv[s_]
        ics = anchor_ics(P, np.unique(a_te)); nic = float(np.nanmean(ics)); se = true_ic[YV]["se"]; p = abs(nic) < 2 * se; ok_iii &= p
        null.append({"seed": seed, "fold": YV, "null_ic": nic, "se_true": se, "true_ic": true_ic[YV]["mean"], "pass": bool(p), "train_rows": int(tr.sum())})
        log(f"(iii) seed {seed} fold {YV}: null IC {nic:+.5f} vs 2*SE {2*se:.5f} (true IC {true_ic[YV]['mean']:+.4f}) -> {'PASS' if p else 'FAIL'}")
# information only (gate unchanged): seed-averaged null per fold (dlw_judge.py L122-148 convention) and a UTC-day-block SE of the true per-anchor IC
info_iii = {}
for YV in FOLDS:
    vals = [r["null_ic"] for r in null if r["fold"] == YV and not r.get("skipped")]
    anchors = np.unique(A[YRA == YV]); ics = anchor_ics(PRED0, anchors) if len(anchors) else np.array([np.nan])
    dd = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(E_ts[a]))) for a in anchors]) if len(anchors) else np.array([])
    se_day = float("nan")
    if len(anchors):
        ud, inv = np.unique(dd, return_inverse=True); okv = np.isfinite(ics); dsum = np.bincount(inv[okv], weights=ics[okv], minlength=len(ud)); dcnt = np.bincount(inv[okv], minlength=len(ud)); dm = dsum[dcnt > 0] / dcnt[dcnt > 0]
        se_day = float(np.std(dm, ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else float("nan")
    info_iii[str(YV)] = {"null_ic_seed_mean": float(np.mean(vals)) if vals else float("nan"), "null_ic_per_seed": vals, "se_anchor": true_ic[YV]["se"], "se_dayblock": se_day,
                         "seed_mean_pass_2se_anchor": bool(vals and abs(np.mean(vals)) < 2 * true_ic[YV]["se"]), "all_seeds_pass_2se_dayblock": bool(vals and all(abs(v) < 2 * se_day for v in vals)) if np.isfinite(se_day) else None}
    log(f"(iii) info fold {YV}: seed-mean null {info_iii[str(YV)]['null_ic_seed_mean']:+.5f} vs 2*SE_anchor {2*true_ic[YV]['se']:.5f} / 2*SE_dayblock {2*se_day:.5f}")
out["iii_shuffle_null"] = {"runs": null, "pass": bool(ok_iii), "info_not_gate": info_iii}
# ---- (iv) offset spectrum
spec = {}
fin_anchor = np.where(np.isfinite(PRED0).any(1))[0]
for k in range(-6, 7):
    v = []
    for i in fin_anchor:
        j = i + k
        if 0 <= j < nA and E_ts[j] - E_ts[i] == k * 14400:
            m = members[i]; v.append(sp(PRED0[i, m], y4[j, m]))
    spec[k] = float(np.nanmean(v));
peak = max(spec, key=lambda kk: spec[kk] if np.isfinite(spec[kk]) else -9)
side = max(abs(spec[k]) for k in (1, 2, 3)); ok_iv = (peak == 0) and (side < spec[0])
out["iv_offset_spectrum"] = {"spectrum": {str(k): v for k, v in spec.items()}, "peak_k": int(peak), "max_abs_k1_3": side, "corr0": spec[0], "n_anchors": int(len(fin_anchor)), "pass": bool(ok_iv)}
log(f"(iv) spectrum " + " ".join(f"{k}:{spec[k]:+.4f}" for k in range(-6, 7)) + f" peak {peak} max|k1..3| {side:.4f} -> {'PASS' if ok_iv else 'FAIL'}")
# ---- (v) embargo invariance
emb = {}; ok_v = True
for YV in (2024, 2025):
    te = YRA == YV; a0 = int(np.unique(A[te]).min())
    tr0 = YRA < YV; tr1 = (YRA < YV) & (A < a0 - 60)
    P0, an = fit_predict(tr0, te); ic0 = float(np.nanmean(anchor_ics(P0, an)))
    P1, _ = fit_predict(tr1, te); ic1 = float(np.nanmean(anchor_ics(P1, an)))
    ic_stage5 = true_ic[YV]["mean"]
    d_refit = ic1 - ic0; d_stage5 = ic1 - ic_stage5; p = abs(d_refit) < 0.002; ok_v &= p
    emb[str(YV)] = {"first_test_anchor": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(E_ts[a0]))), "last_train_anchor_embargo": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(E_ts[int(A[tr1].max())]))),
                    "ic_no_embargo_refit": ic0, "ic_embargo60": ic1, "ic_stage5_file": ic_stage5, "delta_vs_refit": d_refit, "delta_vs_stage5": d_stage5, "refit_reproduces_stage5": bool(abs(ic0 - ic_stage5) < 1e-6), "pass": bool(p)}
    log(f"(v) fold {YV}: IC no-embargo refit {ic0:+.5f} (stage-5 file {ic_stage5:+.5f}, refit==file {abs(ic0-ic_stage5)<1e-6}), embargo-60 {ic1:+.5f}, Δ {d_refit:+.5f} -> {'PASS' if p else 'FAIL'}")
out["v_embargo"] = {"folds": emb, "pass": bool(ok_v)}
out["G4b_PASS"] = bool(ok_iii and ok_iv and ok_v)
g4a = json.load(open(f"{ROOT}/results/G4a.json"))
verdict = {"G4a_pass": bool(g4a["G4a_PASS"]), "G4b_pass": out["G4b_PASS"], "items": {"i": g4a["i_causality"]["pass"], "ii": g4a["ii_foldout"]["pass"], "iii": ok_iii, "iv": ok_iv, "v": ok_v, "vi": g4a["vi_feature_window"]["pass"]},
           "hist_king_admitted": bool(g4a["G4a_PASS"] and out["G4b_PASS"])}
json.dump(out, open(f"{ROOT}/results/G4b.json", "w"), indent=1); json.dump(verdict, open(f"{ROOT}/results/G4_verdict.json", "w"), indent=1)
log(f"G4b (iii) {'PASS' if ok_iii else 'FAIL'} (iv) {'PASS' if ok_iv else 'FAIL'} (v) {'PASS' if ok_v else 'FAIL'}; G4 verdict {verdict}")
