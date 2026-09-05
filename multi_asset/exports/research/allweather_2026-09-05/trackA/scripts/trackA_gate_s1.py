"""trackA_gate_s1.py — Track A S1 gate device (PREREG_allweather_programme_2026-09-05 §3 Track A; sha 8a02895c).
Same form as jp_f7_gate.py (multi_asset/exports/eda/kcurve_2026-08-15/devices_2026-08-19): LightGBM 400 trees / lr 0.05 / 63 leaves /
subsample 0.8 / colsample 0.8, target = rank of Y4 within anchor members (rankdata/(n-1)-0.5), folds test-year in FOLDS (default 2024,2025,2026),
train = years < test year, baseline = the 78 panel columns (82 minus ret5_sum_48/288 value+rank, = pod_slow_hist_folds.py keep list),
new columns rank-transformed within the anchor's members. Differences from jp_f7_gate.py, all declared:
  * xrank keeps missing as NaN (the template writes 0 for non-finite); PREREG: 缺失→NaN 不填 0. LightGBM handles NaN natively.
  * seeds = SEEDS env (default 42,2027; template used 0,1); random_state passed to LGBMRegressor; n_jobs = NJOBS (default 24, as template).
  * baseline is RE-FITTED here (BASE arm) and the gate Δ is vs this run's baseline of the same seed; the frozen BASE dicts are only reported
    (BASE_JP = jp_f7_gate.py frozen dict for the jpline instrument; BASE_POD = pod_slow_hist_folds.py base_ic_2024_26 for the pod v2ext instrument).
  * S1': per-anchor Spearman rho(arm pred, BASE pred of the same seed) and IC of arm pred on the residual of Y(rank target) vs BASE pred
    (OLS a+b*pred_base fitted on the fold's test rows), both averaged over anchors per fold.
Gate S1 (frozen): Δavg over the FOLDS ≥ +0.003 on BOTH seeds AND the 2026-fold Δ ≥ 0 on BOTH seeds.
env: FEA_IN META_IN NEWF (comma list of npz files: F (nA,829,k) float32, names, E_ts) ARMS ("BASE:;A1:0;A2:1;A1A2:0,1" = family indices into NEWF)
     SEEDS FOLDS OUT_JSON PRED_DIR NJOBS
"""
import json, time, os, sys, hashlib
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
FEA_IN = os.environ["FEA_IN"]; META_IN = os.environ["META_IN"]
NEWF = [p for p in os.environ.get("NEWF", "").split(",") if p]
ARMS = [(a.split(":")[0], [int(x) for x in a.split(":")[1].split(",") if x != ""]) for a in os.environ.get("ARMS", "BASE:").split(";") if a]
SEEDS = [int(s) for s in os.environ.get("SEEDS", "42,2027").split(",")]
FOLDS = [int(s) for s in os.environ.get("FOLDS", "2024,2025,2026").split(",")]
OUT_JSON = os.environ["OUT_JSON"]; PRED_DIR = os.environ.get("PRED_DIR"); NJOBS = int(os.environ.get("NJOBS", "24"))
BASE_JP = {"2024": 0.0530, "2025": 0.0550, "2026": 0.0545}     # jp_f7_gate.py frozen dict (jpline instrument, 2026-08-19)
BASE_POD = {"2024": 0.0574, "2025": 0.0617, "2026": 0.0571}    # pod_slow_hist_folds.py base_ic_2024_26 (pod v2ext instrument)
CFG = {"self_sha256": SELF, "FEA_IN": FEA_IN, "META_IN": META_IN, "NEWF": NEWF, "ARMS": ARMS, "SEEDS": SEEDS, "FOLDS": FOLDS, "NJOBS": NJOBS,
       "lgbm": {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 63, "subsample": 0.8, "colsample_bytree": 0.8},
       "lightgbm_version": lgb.__version__, "numpy_version": np.__version__, "utc": time.strftime("%FT%TZ", time.gmtime())}
print("CONFIG " + json.dumps(CFG), flush=True)

FEA = np.load(FEA_IN, mmap_mode="r")
MT = np.load(META_IN, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
Y4_ALT = os.environ.get("Y4_ALT")   # sensitivity (not the frozen S1): alternative target matrix (npz with y4, E_ts), e.g. y4_startE = Σ ret5 rows E+1..E+48
if Y4_ALT:
    _ya = np.load(Y4_ALT, allow_pickle=True); assert np.array_equal(_ya["E_ts"].astype(np.int64), E_ts); y4 = np.asarray(_ya["y4"], np.float32)
    CFG["Y4_ALT"] = {"path": Y4_ALT, "definition": str(_ya["definition"]), "finite": int(np.isfinite(y4).sum())}; print("Y4_ALT " + json.dumps(CFG["Y4_ALT"]), flush=True)
names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = y4.shape[1]
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert len(keep) == 78, len(keep)
NEW = []
for p in NEWF:
    z = np.load(p, allow_pickle=True)
    assert np.array_equal(z["E_ts"].astype(np.int64), E_ts), f"{p}: E_ts mismatch with META"
    F = np.asarray(z["F"], dtype=np.float32); assert F.shape[0] == nA and F.shape[1] == NW, F.shape
    NEW.append((p, F, [str(n) for n in z["names"]]))
    print(f"NEWF {p} shape {F.shape} names {[str(n) for n in z['names']]} finite {np.isfinite(F).mean():.4f}", flush=True)

def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def xrank(v):
    out = np.full(len(v), np.nan, np.float32); ok = np.isfinite(v)
    if ok.sum() > 1: out[ok] = rankdata(v[ok]) / (ok.sum() - 1) - 0.5
    return out

rows_X, rows_y, rows_a = [], [], []; rows_N = [[] for _ in NEW]
for i in range(nA):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    rows_X.append(np.asarray(FEA[i, m[ok]][:, keep], dtype=np.float32))
    for f, (_, F, _) in enumerate(NEW):
        fo = F[i, m[ok]]
        rows_N[f].append(np.column_stack([xrank(fo[:, j]) for j in range(fo.shape[1])]))
    rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32))
XB = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); YRA = yrs[A]
XN = [np.concatenate(r) for r in rows_N]
del rows_X, rows_N
print(f"rows {len(Y)} base_cols {XB.shape[1]} new_cols {[x.shape[1] for x in XN]} anchors_used {len(np.unique(A))} "
      f"rows_by_year {dict(zip(*[list(map(str, u)) for u in np.unique(YRA, return_counts=True)]))}", flush=True)

def fit_fold(X, seed, YV):
    tr = YRA < YV; te = YRA == YV
    t0 = time.time()
    g = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8,
                          n_jobs=NJOBS, verbose=-1, random_state=seed).fit(X[tr], Y[tr])
    pv = g.predict(X[te]).astype(np.float32)
    return pv, te, int(tr.sum()), time.time() - t0

def per_anchor(pv, te, other=None):
    """mean per-anchor Spearman of pv vs y4 (IC), optionally vs `other` (same row layout as pv)."""
    a_te = A[te]; ics = []; rhos = []
    for a in np.unique(a_te):
        s_ = a_te == a; mm = members[a]; okm = np.isfinite(y4[a, mm])
        ics.append(sp(pv[s_], y4[a, mm][okm]))
        if other is not None: rhos.append(sp(pv[s_], other[s_]))
    return float(np.nanmean(ics)), (float(np.nanmean(rhos)) if other is not None else None), len(ics)

res = {"config": CFG, "base_frozen": {"BASE_JP": BASE_JP, "BASE_POD": BASE_POD}, "arms": {}}
BASEPRED = {}   # (seed, YV) -> pv over test rows
for arm, fam in ARMS:
    X = XB if not fam else np.column_stack([XB] + [XN[f] for f in fam])
    res["arms"][arm] = {"families": fam, "n_cols": int(X.shape[1]), "runs": {}}
    for seed in SEEDS:
        PRED = np.full((nA, NW), np.nan, np.float32); run = {"ic": {}, "n_anchors": {}, "train_rows": {}, "fit_s": {}, "rho_base": {}, "ic_resid_base": {}}
        for YV in FOLDS:
            pv, te, ntr, secs = fit_fold(X, seed, YV)
            a_te = A[te]
            for a in np.unique(a_te):
                s_ = a_te == a; mm = members[a]; okm = np.isfinite(y4[a, mm]); PRED[a, mm[okm]] = pv[s_]
            if arm == "BASE": BASEPRED[(seed, YV)] = pv
            base = BASEPRED.get((seed, YV))
            ic, rho, na = per_anchor(pv, te, base)
            run["ic"][str(YV)] = round(ic, 4); run["n_anchors"][str(YV)] = na; run["train_rows"][str(YV)] = ntr; run["fit_s"][str(YV)] = round(secs, 1)
            if base is not None:
                run["rho_base"][str(YV)] = round(rho, 4)
                yy = Y[te]; b = np.polyfit(base, yy, 1); resid = yy - (b[0] * base + b[1])
                ics = []
                for a in np.unique(a_te):
                    s_ = a_te == a; ics.append(sp(pv[s_], resid[s_]))
                run["ic_resid_base"][str(YV)] = round(float(np.nanmean(ics)), 4)
            print(f"[{arm} s{seed} {YV}] IC {ic:.4f} rho_base {run['rho_base'].get(str(YV))} ic_resid {run['ic_resid_base'].get(str(YV))} "
                  f"train_rows {ntr} anchors {na} {secs:.0f}s", flush=True)
        if arm != "BASE":
            bic = res["arms"]["BASE"]["runs"][str(seed)]["ic"]
            run["delta"] = {y: round(run["ic"][y] - bic[y], 4) for y in run["ic"]}
            run["avg_delta"] = round(float(np.mean(list(run["delta"].values()))), 4)
        else:
            run["repro_vs_BASE_POD"] = {y: round(run["ic"][y] - BASE_POD[y], 4) for y in run["ic"] if y in BASE_POD}
            run["repro_vs_BASE_JP"] = {y: round(run["ic"][y] - BASE_JP[y], 4) for y in run["ic"] if y in BASE_JP}
            run["repro_within_0.003_POD"] = bool(all(abs(v) <= 0.003 for v in run["repro_vs_BASE_POD"].values()))
            run["repro_within_0.003_JP"] = bool(all(abs(v) <= 0.003 for v in run["repro_vs_BASE_JP"].values()))
        res["arms"][arm]["runs"][str(seed)] = run
        if PRED_DIR:
            os.makedirs(PRED_DIR, exist_ok=True); np.save(f"{PRED_DIR}/pred_{arm}_s{seed}.npy", PRED)
        print(f"[{arm} s{seed}] {run['ic']} " + (f"Δ {run['delta']} Δavg {run['avg_delta']:+.4f}" if arm != "BASE" else f"repro_POD {run['repro_vs_BASE_POD']} repro_JP {run['repro_vs_BASE_JP']}"), flush=True)
    if arm != "BASE":
        runs = res["arms"][arm]["runs"]
        ok = all(r["avg_delta"] >= 0.003 and r["delta"].get("2026", 0.0) >= 0 for r in runs.values())
        res["arms"][arm]["verdict"] = "PASS" if ok else "KILLED"
        print(f"{arm} VERDICT {res['arms'][arm]['verdict']}", flush=True)
    json.dump(res, open(OUT_JSON, "w"), indent=1)
json.dump(res, open(OUT_JSON, "w"), indent=1)
print("S1_GATE_DONE", flush=True)
