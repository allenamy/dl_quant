"""crash_model.py — PREREG_crash_risk_long_end_2026-09-06 §1 folds / §3 score-level gates (Phase 1, no book actions).
Rows = cohort rows of features.npz with a finite 4h target. Folds: test year YV ∈ {2024, 2025, 2026≤2026-08-10 20:00Z}, train = anchors with year < YV and
E_train + window ≤ first test anchor (embargo = target window: 4h for T1/T2, 12h for T3). LightGBM 400 trees / lr .05 / 63 leaves / subsample .8 / colsample .8,
seeds 42/2027, n_jobs 12; T1/T3 binary classifiers, T2 quantile regressor α = 0.05; NaN kept.
S-a (T1): fold AUC ≥ 0.60 AND event rate among the per-anchor top-10% risk names (ceil(0.10·n) by p̂ within the anchor's cohort) ≥ 2.0 × the fold's cohort base rate; both seeds.
S-b (directional): per anchor d = mean(4h return of top-10% risk names) − mean(4h return of the cohort); fold mean d ≤ −30 bps AND UTC-day-block bootstrap CI95 upper < 0
     (2000 resamples, seed 20260905); holds in ≥ 2 of 3 folds AND in 2026; both seeds. PASS = S-a ∧ S-b (both seeds); FAIL otherwise. T2/T3 report only.
S-c (report): top-5 gain features per fold; S-b split into positive-funding vs non-positive-funding names; yearly event counts and predicted-top-10% event counts.
Guards: shift spectrum — AUC of the seed-42 T1 predictions vs targets whose window is moved by j ∈ {−2..+3} bars (rows E+1+j..E+48+j; peak must be at j=0);
shuffle-future — labels permuted within each training anchor, model retrained (seed 42), AUC on true test labels (null band).
Outputs: results/phase1.json, results/model_tables.md, data/preds_<target>_s<seed>.npz. env: ROOT NJOBS"""
import os, sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata
import lightgbm as lgb
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/crash_risk"); NJOBS = int(os.environ.get("NJOBS", "12")); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; NB = 2000; BSEED = 20260905; SEEDS = [42, 2027]; FOLDS = [2024, 2025, 2026]
F = np.load(f"{ROOT}/data/features.npz", allow_pickle=True); PI = F["PI"]; PJ = F["PJ"]; X = np.asarray(F["X"], np.float32); NAMES = [str(n) for n in F["names"]]
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); E_ts = P0["E_ts"].astype(np.int64); T1 = P0["T1"]; T2 = P0["T2"]; T3 = P0["T3"]; R144 = P0["R144"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); ET = E_ts[PI]; YR = yrs[PI]; DAY = ET // 86400
y1 = T1[PI, PJ].astype(int); y2 = T2[PI, PJ].astype(np.float64); y3 = T3[PI, PJ].astype(int); ok2 = np.isfinite(y2); ok3 = np.isfinite(R144[PI, PJ])
fund_now = X[:, NAMES.index("fund_now")]
LGB = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, n_jobs=NJOBS, verbose=-1)
CFG = {"self_sha256": SELF, "prereg": "PREREG_crash_risk_long_end_2026-09-06 commit 3dfd906 sha256 424ccd332148aa66f515877fcd4a03252c3a3142bd4a9ab2bbb034473a773efb", "lgbm": LGB, "seeds": SEEDS, "folds": FOLDS, "cut": "2026-08-10 20:00Z", "embargo": "train anchors with E + window <= first test anchor", "lightgbm": lgb.__version__, "numpy": np.__version__, "n_rows": int(len(PI)), "n_cols": len(NAMES), "utc": time.strftime("%FT%TZ", time.gmtime())}
print("CONFIG " + json.dumps(CFG), flush=True)
def auc(score, y):
    y = np.asarray(y); s = np.asarray(score, np.float64); f = np.isfinite(s); s, y = s[f], y[f]; npos = int(y.sum()); nneg = len(y) - npos
    if npos == 0 or nneg == 0: return float("nan")
    r = rankdata(s); return float((r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))
def boot_ci(x, days):
    ud, inv = np.unique(days, return_inverse=True); s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(BSEED); idx = rng.integers(0, len(ud), size=(NB, len(ud))); m = s1[idx].sum(1) / c[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 2), round(float(np.percentile(m, 97.5)), 2)]
def fold_masks(YV, window_s, okmask):
    te = (YR == YV) & okmask & (ET <= CUT if YV == 2026 else True); first = ET[te].min()
    tr = (YR < YV) & okmask & (ET + window_s <= first)
    return tr, te, first
def top10_per_anchor(score, rows):
    """boolean mask over `rows` (indices into the row space): top ceil(10%) by score within each anchor."""
    top = np.zeros(len(rows), bool); pi = PI[rows]; order = np.argsort(pi, kind="stable"); starts = np.searchsorted(pi[order], np.unique(pi)); ends = np.append(starts[1:], len(rows))
    for a, b in zip(starts, ends):
        idx = order[a:b]; s = score[idx]; f = np.isfinite(s)
        if f.sum() == 0: continue
        k = int(np.ceil(0.10 * f.sum())); sel = idx[f][np.argsort(-s[f])[:k]]; top[sel] = True
    return top
def directional(rows, top, ret):
    """per-anchor d = mean ret(top) − mean ret(cohort) in bps; returns per-anchor d array and its days."""
    pi = PI[rows]; ua, inv = np.unique(pi, return_inverse=True); n = len(ua)
    s_all = np.bincount(inv, ret, minlength=n); c_all = np.bincount(inv, minlength=n).astype(float)
    s_top = np.bincount(inv[top], ret[top], minlength=n); c_top = np.bincount(inv[top], minlength=n).astype(float)
    ok = (c_top > 0) & (c_all > 0); d = (s_top[ok] / c_top[ok] - s_all[ok] / c_all[ok]) * 1e4; return d, E_ts[ua[ok]] // 86400
res = {"config": CFG, "T1": {}, "T2": {}, "T3": {}, "guards": {}, "reading": {}}
for s in SEEDS:
    for tgt in ("T1", "T3", "T2"):
        y = {"T1": y1, "T3": y3, "T2": y2}[tgt]; okm = {"T1": ok2, "T3": ok3, "T2": ok2}[tgt]; win = 14400 if tgt != "T3" else 43200
        out = {}; preds = np.full(len(PI), np.nan, np.float32)
        for YV in FOLDS:
            tr, te, first = fold_masks(YV, win, okm); t0 = time.time()
            if tgt == "T2": mdl = lgb.LGBMRegressor(objective="quantile", alpha=0.05, random_state=s, **LGB).fit(X[tr], y[tr]); p = mdl.predict(X[te])
            else: mdl = lgb.LGBMClassifier(objective="binary", random_state=s, **LGB).fit(X[tr], y[tr]); p = mdl.predict_proba(X[te])[:, 1]
            rows = np.where(te)[0]; preds[rows] = p; d = {"n_train": int(tr.sum()), "n_test": int(te.sum()), "train_events": int(y[tr].sum()) if tgt != "T2" else None, "test_events": int(y[te].sum()) if tgt != "T2" else None, "fit_s": round(time.time() - t0, 1), "first_test_anchor": time.strftime("%F %H:%M", time.gmtime(int(first)))}
            imp = mdl.booster_.feature_importance(importance_type="gain"); top5 = np.argsort(-imp)[:5]; d["top5_gain"] = [[NAMES[k], round(float(imp[k] / imp.sum()), 4)] for k in top5]
            if tgt in ("T1", "T3"):
                d["auc"] = round(auc(p, y[te]), 4); base = float(y[te].mean()); top = top10_per_anchor(p, rows)
                d["base_rate"] = round(base, 5); d["top10_event_rate"] = round(float(y[te][top].mean()), 5); d["lift"] = round(float(y[te][top].mean() / base), 3) if base > 0 else None; d["top10_n"] = int(top.sum()); d["top10_events"] = int(y[te][top].sum())
                dd, days = directional(rows, top, y2[te]); d["dir_mean_bps"] = round(float(dd.mean()), 2); d["dir_ci95"] = boot_ci(dd, days); d["dir_n_anchors"] = int(len(dd))
                d["cohort_mean_bps"] = round(float(y2[te].mean() * 1e4), 2); d["top10_mean_bps"] = round(float(y2[te][top].mean() * 1e4), 2)
                for lab, sub in (("pos_funding", fund_now[te] > 0), ("nonpos_funding", ~(fund_now[te] > 0))):
                    if sub.sum() > 100 and (top & sub).sum() > 10:
                        dd2, days2 = directional(rows[sub], top[sub], y2[te][sub]); d[f"dir_{lab}"] = {"mean_bps": round(float(dd2.mean()), 2), "ci95": boot_ci(dd2, days2), "n_rows": int(sub.sum()), "n_top": int((top & sub).sum())}
                if tgt == "T1":
                    d["Sa_auc_ok"] = bool(d["auc"] >= 0.60); d["Sa_lift_ok"] = bool(d["lift"] is not None and d["lift"] >= 2.0); d["Sb_ok"] = bool(d["dir_mean_bps"] <= -30 and d["dir_ci95"][1] < 0)
            else:
                q = np.quantile(y[tr], 0.05); pin = lambda yy, qq: float(np.mean(np.maximum(0.05 * (yy - qq), (0.05 - 1) * (yy - qq))))
                d["pinball_model"] = round(pin(y[te], p), 6); d["pinball_const_q05_train"] = round(pin(y[te], q), 6); d["coverage_model"] = round(float(np.mean(y[te] <= p)), 4); d["coverage_const"] = round(float(np.mean(y[te] <= q)), 4)
                bot = top10_per_anchor(-p, rows); dd, days = directional(rows, bot, y2[te]); d["bottom10_dir_mean_bps"] = round(float(dd.mean()), 2); d["bottom10_dir_ci95"] = boot_ci(dd, days)
                d["bottom10_T1_rate"] = round(float(y1[te][bot].mean()), 5); d["T1_base_rate"] = round(float(y1[te].mean()), 5)
            out[str(YV)] = d; print(f"[{tgt} s{s} {YV}] " + json.dumps({k: v for k, v in d.items() if k != "top5_gain"}) + " top5 " + str(d["top5_gain"]), flush=True)
        res[tgt][f"s{s}"] = out; np.savez_compressed(f"{ROOT}/data/preds_{tgt}_s{s}.npz", PI=PI, PJ=PJ, pred=preds, E_ts=E_ts)
# ---- reading (T1 primary) ----
rd = {}
for s in SEEDS:
    o = res["T1"][f"s{s}"]; sa = all(o[str(y)]["Sa_auc_ok"] and o[str(y)]["Sa_lift_ok"] for y in FOLDS); nb = sum(o[str(y)]["Sb_ok"] for y in FOLDS); sb = nb >= 2 and o["2026"]["Sb_ok"]
    rd[f"s{s}"] = {"S_a": bool(sa), "S_b": bool(sb), "S_b_folds_ok": int(nb), "S_b_2026_ok": bool(o["2026"]["Sb_ok"])}
rd["PASS"] = bool(all(rd[f"s{s}"]["S_a"] and rd[f"s{s}"]["S_b"] for s in SEEDS)); rd["verdict"] = "PASS" if rd["PASS"] else "FAIL"; res["reading"] = rd; print("READING " + json.dumps(rd), flush=True)
# ---- guards ----
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0c = int(CTS[0]); r5 = np.asarray(Z["data"][:, :, 0], np.float32); del Z
fin = np.isfinite(r5); LL = np.concatenate([np.zeros((1, r5.shape[1])), np.cumsum(np.where(fin, np.log1p(np.clip(r5, -0.99, None)), 0.0), 0, dtype=np.float64)]); NN = np.concatenate([np.zeros((1, r5.shape[1]), np.int64), np.cumsum(fin, 0)]); del r5, fin
Ei = (E_ts - T0c) // 300; assert np.all(CTS[Ei] == E_ts)
p42 = np.load(f"{ROOT}/data/preds_T1_s42.npz")["pred"]; spec = {}
for j in range(-2, 4):
    a = Ei[PI] + 1 + j; b = Ei[PI] + 48 + j; sh = LL[b + 1, PJ] - LL[a, PJ]; nn = NN[b + 1, PJ] - NN[a, PJ]; rj = np.where(nn >= 46, np.expm1(sh), np.nan); yj = (rj <= -0.10).astype(int)
    spec[str(j)] = {}
    for YV in FOLDS:
        te = (YR == YV) & ok2 & np.isfinite(rj) & (ET <= CUT if YV == 2026 else True); spec[str(j)][str(YV)] = round(auc(p42[te], yj[te]), 4)
    spec[str(j)]["mean"] = round(float(np.mean([spec[str(j)][str(y)] for y in FOLDS])), 4)
peak = max(spec, key=lambda k: spec[k]["mean"]); res["guards"]["shift_spectrum_T1_s42"] = {"auc_by_shift": spec, "peak_shift": int(peak), "PASS_peak_at_0": bool(int(peak) == 0), "note": "j<0 windows include bars ≤ E that are also feature inputs (partially known target)"}
print("SHIFT " + json.dumps(res["guards"]["shift_spectrum_T1_s42"]), flush=True)
null = {}
rng = np.random.default_rng(BSEED)
for YV in FOLDS:
    tr, te, first = fold_masks(YV, 14400, ok2); ys = y1.copy(); rows = np.where(tr)[0]; pi = PI[rows]; order = np.argsort(pi, kind="stable"); starts = np.searchsorted(pi[order], np.unique(pi)); ends = np.append(starts[1:], len(rows))
    for a, b in zip(starts, ends):
        idx = rows[order[a:b]]; ys[idx] = ys[idx][rng.permutation(len(idx))]
    mdl = lgb.LGBMClassifier(objective="binary", random_state=42, **LGB).fit(X[tr], ys[tr]); p = mdl.predict_proba(X[te])[:, 1]
    top = top10_per_anchor(p, np.where(te)[0]); null[str(YV)] = {"auc_shuffled_labels": round(auc(p, y1[te]), 4), "lift_shuffled": round(float(y1[te][top].mean() / y1[te].mean()), 3), "auc_true": res["T1"]["s42"][str(YV)]["auc"]}
res["guards"]["shuffle_future_T1_s42"] = null; print("SHUFFLE " + json.dumps(null), flush=True)
json.dump(res, open(f"{ROOT}/results/phase1.json", "w"), indent=1)
L = ["| target · seed | fold | n_train / n_test (events) | AUC | base rate | top-10% rate (lift) | S-b d bps [CI95] | cohort mean bps | top5 gain |", "|---|---|---|---|---|---|---|---|---|"]
for tgt in ("T1", "T3"):
    for s in SEEDS:
        for YV in FOLDS:
            d = res[tgt][f"s{s}"][str(YV)]; L.append(f"| {tgt} s{s} | {YV} | {d['n_train']} / {d['n_test']} ({d['test_events']}) | {d['auc']:.4f} | {d['base_rate']:.4f} | {d['top10_event_rate']:.4f} ({d['lift']}) | {d['dir_mean_bps']:+.1f} [{d['dir_ci95'][0]:+.1f}, {d['dir_ci95'][1]:+.1f}] | {d['cohort_mean_bps']:+.1f} | {', '.join(k for k, _ in d['top5_gain'])} |")
L += ["", "| T2 seed | fold | pinball model / const q05 | coverage model / const | bottom-10% predicted-quantile d bps [CI] | bottom-10% T1 rate / base |", "|---|---|---|---|---|---|"]
for s in SEEDS:
    for YV in FOLDS:
        d = res["T2"][f"s{s}"][str(YV)]; L.append(f"| s{s} | {YV} | {d['pinball_model']:.6f} / {d['pinball_const_q05_train']:.6f} | {d['coverage_model']:.3f} / {d['coverage_const']:.3f} | {d['bottom10_dir_mean_bps']:+.1f} [{d['bottom10_dir_ci95'][0]:+.1f}, {d['bottom10_dir_ci95'][1]:+.1f}] | {d['bottom10_T1_rate']:.4f} / {d['T1_base_rate']:.4f} |")
L += ["", "reading: " + json.dumps(rd), "shift spectrum (T1 s42, AUC by window shift j): " + json.dumps({k: v["mean"] for k, v in spec.items()}) + f" peak {peak}", "shuffle-future null (T1 s42): " + json.dumps(null)]
open(f"{ROOT}/results/model_tables.md", "w").write("\n".join(L) + "\n"); print("PHASE1_DONE", flush=True)
