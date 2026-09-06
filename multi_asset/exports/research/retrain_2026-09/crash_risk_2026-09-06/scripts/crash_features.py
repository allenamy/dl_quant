"""crash_features.py — PREREG_crash_risk_long_end_2026-09-06 §2 features for the cohort rows (anchor i, name j) of phase0.npz. ALL causal: cache rows ≤ E
(row E = the 5-min bar closing at the anchor; the targets start at row E+1). Every raw column also gets an anchor-within-cohort rank form (<name>_r,
rankdata/(n−1) − 0.5 over the cohort names with a finite value; NaN kept). Families (F7 OI not built this round):
 F1 trend shape : r4h, r1d, r3d, r7d (Π(1+r5)−1 over the last 48/288/864/2016 rows ending at E); dd7 = close_E/max(close, 7d) − 1; du7 = close_E/min(close, 7d) − 1;
                  bars_since_hi7 (5-min bars since the 7-day high); up_share_3d (share of the 18 4h-blocks with positive return); accel = r1d − r3d/3; r1h; r1h_over_r4h (clipped ±5)
 F2 funding      : fund_now (per-settlement rate, panel f_fund_now), iv (settlement hours), rn8 = fund_now·8/iv, cap (fundingInfo adjustedFundingRateCap, INFERRED current-value
                  proxy, NaN if the symbol is absent), rate_over_cap = fund_now/cap, at_cap = 1[rate_over_cap ≥ 0.9], d3_settle = rate_last − rate_3_settlements_ago and
                  n_consec_at_cap from the per-settlement history (funding zips 2020-01..2026-07 + /workspace/fund_aug.json.gz August tail, settlements with ts ≤ E),
                  ema_gap = f_fund_ema_v1 − fund_now
 F3 activity     : qv_ratio = Σqv(48)/(Σqv(2016)/42); tbf_diff = mean tbf(48) − mean tbf(864); avgsz_ratio = exp(mean lasz(48) − mean lasz(2016)); cnt_ratio = Σcnt(48)/(Σcnt(2016)/42);
                  range_ratio = mean rng(48)/mean rng(2016)
 F4 intra-anchor : min_ret5_4h; n_big_4h = #|ret5| > 2% in the last 48 rows; cpos_4h = mean cpos(48); r1h_over_r4h (F1); mdd_4h = max drawdown of the close path over the last 48 rows
 F5 listing age  : age_anchors = (E − first observed cache row)/4h (first row with finite ret5 or log_qv; E-0903-E observation existence only); young90 = 1[age < 90 d]
 F6 breadth      : n_rn8_ge15 (members with rn8 ≥ 15 bps), n_r3d_ge50 (members with r3d ≥ 50%), coh_mean_du7, coh_mean_rate_over_cap (all per anchor, same for every row)
Units chain (printed): returns are fractions (Π−1); funding rates are per-settlement fractions (rn8 = 8h-equivalent fraction); cap ratio dimensionless; ages in 4h anchors.
Guard (i) hit rate = share of cohort rows with a finite value per column (assert ≥ 0.95 for cache-derived columns; F2 cap-based columns reported).
Outputs: data/features.npz (PI, PJ, E_ts, X, names, is_rank), results/feature_defs.json (definitions + hit rates + unit chain). env: ROOT NPROC"""
import os, sys, io, json, time, gzip, glob, csv, zipfile, hashlib
import numpy as np
from scipy.stats import rankdata
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/crash_risk"); SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
t0 = time.time()
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); SYMS = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]; D = Z["data"]; del Z
NW = len(SYMS); T = len(CTS)
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); COH = P0["COH"]; MEM = P0["MEM"]; E_ts = P0["E_ts"].astype(np.int64); nA = len(E_ts)
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
PROW = np.array([pw_row.get(int(t), -1) for t in E_ts]); has = PROW >= 0
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; FEMA = PW["f_fund_ema_v1"]
PI, PJ = np.where(COH & has[:, None]); PE = Ei[PI]; n = len(PI); print(f"cohort rows {n} anchors {len(np.unique(PI))} ({time.time()-t0:.0f}s)", flush=True)
X = {}; DEF = {}
def cs(x):
    f = np.isfinite(x); return np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(f, x, 0.0), 0, dtype=np.float64)]), np.concatenate([np.zeros((1, NW), np.int64), np.cumsum(f, 0)])
def wsum(S, a, b):   # Σ rows PE-a+1 .. PE-b  (i.e. last a rows ending at E when b=0): S[PE-b+1] − S[PE-a+1]
    return S[PE - b + 1, PJ] - S[PE - a + 1, PJ]
# ---------- F1 / F4 from ret5 ----------
r5 = np.asarray(D[:, :, CH.index("ret5")], np.float32); fin = np.isfinite(r5)
LL, NN = cs(np.log1p(np.clip(r5, -0.99, None)))
def ret(a): return np.expm1(wsum(LL, a, 0))
X["r4h"] = ret(48); X["r1d"] = ret(288); X["r3d"] = ret(864); X["r7d"] = ret(2016); X["r1h"] = ret(12)
X["accel"] = X["r1d"] - X["r3d"] / 3.0
with np.errstate(invalid="ignore", divide="ignore"): X["r1h_over_r4h"] = np.where(np.abs(X["r4h"]) > 1e-4, np.clip(X["r1h"] / X["r4h"], -5, 5), np.nan)
DEF.update({"r4h": "Π(1+r5) rows E−47..E − 1", "r1d": "…288 rows", "r3d": "…864 rows", "r7d": "…2016 rows", "r1h": "…12 rows", "accel": "r1d − r3d/3", "r1h_over_r4h": "r1h/r4h if |r4h|>1e-4, clipped ±5"})
dd7 = np.full(n, np.nan); du7 = np.full(n, np.nan); bsh = np.full(n, np.nan); mdd4 = np.full(n, np.nan); mn5 = np.full(n, np.nan); nbig = np.full(n, np.nan); up3 = np.full(n, np.nan)
order = np.argsort(PI, kind="stable"); starts = np.searchsorted(PI[order], np.unique(PI)); ends = np.append(starts[1:], n)
LC = LL[1:]   # LC[k] = cumulative log price up to and including row k (relative)
blk = np.arange(0, 18 * 48 + 1, 48)
for a, b in zip(starts, ends):
    idx = order[a:b]; i = PI[idx[0]]; e = Ei[i]; cj = PJ[idx]
    if e < 2016: continue
    path = LC[e - 2015: e + 1][:, cj]; ce = LC[e, cj]
    dd7[idx] = np.expm1(ce - path.max(0)); du7[idx] = np.expm1(ce - path.min(0)); bsh[idx] = 2015 - path.argmax(0)
    p4 = LC[e - 47: e + 1][:, cj]; run = np.maximum.accumulate(p4, 0); mdd4[idx] = np.expm1(-(run - p4).max(0))
    q = r5[e - 47: e + 1][:, cj].astype(np.float64); mn5[idx] = np.nanmin(np.where(np.isfinite(q), q, np.inf), 0); mn5[idx][~np.isfinite(mn5[idx])] = np.nan; nbig[idx] = np.nansum(np.abs(q) > 0.02, 0)
    edges = LC[(e - 864) + blk][:, cj]   # cumulative log price at rows e−864, e−816, …, e (19 edges) → 18 block returns over rows e−863..e
    br = np.diff(edges, axis=0); up3[idx] = (br > 0).mean(0)
mn5[~np.isfinite(mn5)] = np.nan
X["dd7"] = dd7; X["du7"] = du7; X["bars_since_hi7"] = bsh; X["mdd_4h"] = mdd4; X["min_ret5_4h"] = mn5; X["n_big_4h"] = nbig; X["up_share_3d"] = up3
DEF.update({"dd7": "close_E/max(close over rows E−2015..E) − 1", "du7": "close_E/min(…) − 1", "bars_since_hi7": "5-min bars since the 7-day high", "mdd_4h": "max drawdown of the close path over rows E−47..E (negative fraction)", "min_ret5_4h": "min ret5 over rows E−47..E", "n_big_4h": "# |ret5| > 0.02 over rows E−47..E", "up_share_3d": "share of the 18 4h blocks ending at E with positive log return"})
# F6 needs r3d for all members and F4 cpos; do cpos now
cp = np.asarray(D[:, :, CH.index("cpos")], np.float32); S, Nn = cs(cp); X["cpos_4h"] = wsum(S, 48, 0) / np.maximum(wsum(Nn, 48, 0), 1); del cp, S, Nn
DEF["cpos_4h"] = "mean cpos over rows E−47..E"
R3D_ALL = np.expm1(LL[Ei + 1] - LL[Ei - 863]) if True else None   # (nA, NW) for F6
del LL, NN, r5, fin, LC
print(f"F1/F4 done ({time.time()-t0:.0f}s)", flush=True)
# ---------- F3 activity ----------
lq = np.asarray(D[:, :, CH.index("log_qv")], np.float32); S, Nn = cs(np.expm1(np.clip(lq, 0, 30)))
with np.errstate(invalid="ignore", divide="ignore"): X["qv_ratio"] = wsum(S, 48, 0) / (wsum(S, 2016, 0) / 42.0)
del lq, S, Nn
tb = np.asarray(D[:, :, CH.index("tbf")], np.float32); S, Nn = cs(tb)
with np.errstate(invalid="ignore", divide="ignore"): X["tbf_diff"] = wsum(S, 48, 0) / np.maximum(wsum(Nn, 48, 0), 1) - wsum(S, 864, 0) / np.maximum(wsum(Nn, 864, 0), 1)
del tb, S, Nn
la = np.asarray(D[:, :, CH.index("log_avgsz")], np.float32); S, Nn = cs(la)
with np.errstate(invalid="ignore", divide="ignore"): X["avgsz_ratio"] = np.exp(wsum(S, 48, 0) / np.maximum(wsum(Nn, 48, 0), 1) - wsum(S, 2016, 0) / np.maximum(wsum(Nn, 2016, 0), 1))
del la, S, Nn
lc = np.asarray(D[:, :, CH.index("log_cnt")], np.float32); S, Nn = cs(np.expm1(np.clip(lc, 0, 25)))
with np.errstate(invalid="ignore", divide="ignore"): X["cnt_ratio"] = wsum(S, 48, 0) / (wsum(S, 2016, 0) / 42.0)
del lc, S, Nn
rg = np.asarray(D[:, :, CH.index("range")], np.float32); S, Nn = cs(rg)
with np.errstate(invalid="ignore", divide="ignore"): X["range_ratio"] = (wsum(S, 48, 0) / np.maximum(wsum(Nn, 48, 0), 1)) / (wsum(S, 2016, 0) / np.maximum(wsum(Nn, 2016, 0), 1))
del rg, S, Nn
for k in ("qv_ratio", "cnt_ratio", "range_ratio", "avgsz_ratio"): X[k] = np.where(np.isfinite(X[k]), X[k], np.nan)
DEF.update({"qv_ratio": "Σ quote volume rows E−47..E / (Σ rows E−2015..E / 42)", "tbf_diff": "mean taker-buy share 48 rows − mean 864 rows", "avgsz_ratio": "exp(mean log avg trade size 48 rows − mean 2016 rows)", "cnt_ratio": "Σ trade count 48 / (Σ 2016 / 42)", "range_ratio": "mean bar range 48 rows / mean 2016 rows"})
print(f"F3 done ({time.time()-t0:.0f}s)", flush=True)
# ---------- F5 listing age ----------
lq0 = np.asarray(D[:, :, CH.index("log_qv")], np.float32); obs = np.isfinite(lq0) | np.isfinite(np.asarray(D[:, :, 0], np.float32)); del lq0
first = np.where(obs.any(0), obs.argmax(0), -1); del obs
age = np.where(first[PJ] >= 0, (E_ts[PI] - CTS[np.maximum(first[PJ], 0)]) / 14400.0, np.nan); X["age_anchors"] = age; X["young90"] = np.where(np.isfinite(age), (age < 540).astype(float), np.nan)
DEF.update({"age_anchors": "(E − first cache row with finite ret5 or log_qv)/4h; left-censored names (observed at row 0) get the cache start", "young90": "1[age_anchors < 540] (90 days)"})
# ---------- F2 funding ----------
caps = {d["symbol"]: float(d["adjustedFundingRateCap"]) for d in json.load(open(f"{ROOT}/data/fundinginfo.json"))}
CAP = np.array([caps.get(s, np.nan) for s in SYMS]); fn = FN[PROW[PI], PJ]; iv = IV[PROW[PI], PJ]
X["fund_now"] = fn; X["iv_h"] = iv; X["rn8"] = fn * (8.0 / np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)); X["cap"] = CAP[PJ]
with np.errstate(invalid="ignore", divide="ignore"): X["rate_over_cap"] = fn / CAP[PJ]
X["at_cap"] = np.where(np.isfinite(X["rate_over_cap"]), (X["rate_over_cap"] >= 0.9).astype(float), np.nan); X["ema_gap"] = FEMA[PROW[PI], PJ] - fn
# settlement history from zips + August API tail (same parsing as pod_panel_ext.py)
AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read()); hist = {}
for s in SYMS:
    rows = []
    for zp in sorted(glob.glob(f"/workspace/wide_multisrc/funding/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or (not row[0].strip().isdigit()): continue
                    try: rows.append((int(row[0]) // 1000, float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []): rows.append((int(t_ms) // 1000, float(rate)))
    if rows:
        d = {}
        for t_, r_ in rows: d[t_] = r_
        ft = np.array(sorted(d), np.int64); hist[s] = (ft, np.array([d[t] for t in ft]))
d3 = np.full(n, np.nan); ncap = np.full(n, np.nan)
for j in np.unique(PJ):
    if SYMS[j] not in hist: continue
    ft, fr = hist[SYMS[j]]; sel = np.where(PJ == j)[0]; pos = np.searchsorted(ft, E_ts[PI[sel]], side="right") - 1
    ok = pos >= 2; d3[sel[ok]] = fr[pos[ok]] - fr[pos[ok] - 2]
    c = CAP[j]
    if np.isfinite(c):
        atc = fr >= 0.9 * c; run = np.zeros(len(fr), np.int64)
        for k in range(len(fr)): run[k] = run[k - 1] + 1 if (atc[k] and k > 0) else (1 if atc[k] else 0)
        okp = pos >= 0; ncap[sel[okp]] = run[pos[okp]]
X["d3_settle"] = d3; X["n_consec_at_cap"] = ncap
DEF.update({"fund_now": "panel f_fund_now = last settled rate at E (per-settlement fraction)", "iv_h": "settlement interval hours (panel f_fund_iv)", "rn8": "fund_now·8/iv (8h-equivalent fraction)", "cap": "fundingInfo adjustedFundingRateCap (INFERRED current-value proxy; NaN if absent)", "rate_over_cap": "fund_now/cap", "at_cap": "1[rate_over_cap ≥ 0.9]", "ema_gap": "f_fund_ema_v1 − fund_now", "d3_settle": "rate(latest settlement ≤ E) − rate(two settlements earlier), from the per-settlement history", "n_consec_at_cap": "consecutive settlements ≤ E with rate ≥ 0.9·cap (0 if the latest is below)"})
print(f"F2 done: history symbols {len(hist)} ({time.time()-t0:.0f}s)", flush=True)
# ---------- F6 breadth (per anchor over members; constant within anchor) ----------
rn8_all = np.full((nA, NW), np.nan); ok = has
rn8_all[ok] = FN[PROW[ok]] * (8.0 / np.where(np.isfinite(IV[PROW[ok]]) & (IV[PROW[ok]] > 0), IV[PROW[ok]], 8.0))
n15 = np.where(MEM & (rn8_all >= 0.0015), 1, 0).sum(1).astype(float); n50 = np.where(MEM & (R3D_ALL >= 0.5), 1, 0).sum(1).astype(float)
cm_du7 = np.full(nA, np.nan); cm_cap = np.full(nA, np.nan)
for a, b in zip(starts, ends):
    idx = order[a:b]; i = PI[idx[0]]; cm_du7[i] = np.nanmean(du7[idx]) if np.isfinite(du7[idx]).any() else np.nan; cm_cap[i] = np.nanmean(X["rate_over_cap"][idx]) if np.isfinite(X["rate_over_cap"][idx]).any() else np.nan
X["n_rn8_ge15"] = n15[PI]; X["n_r3d_ge50"] = n50[PI]; X["coh_mean_du7"] = cm_du7[PI]; X["coh_mean_rate_over_cap"] = cm_cap[PI]
DEF.update({"n_rn8_ge15": "# members with rn8 ≥ 0.0015 at the anchor", "n_r3d_ge50": "# members with r3d ≥ 0.5", "coh_mean_du7": "cohort mean du7", "coh_mean_rate_over_cap": "cohort mean rate_over_cap"})
# ---------- ranks within cohort per anchor ----------
NOR = {"n_rn8_ge15", "n_r3d_ge50", "coh_mean_du7", "coh_mean_rate_over_cap", "young90", "at_cap", "iv_h", "cap"}
names = list(X.keys()); Xm = np.column_stack([np.asarray(X[k], np.float64) for k in names]).astype(np.float32)
rk_names = [k for k in names if k not in NOR]; RK = np.full((n, len(rk_names)), np.nan, np.float32)
for a, b in zip(starts, ends):
    idx = order[a:b]
    for c, k in enumerate(rk_names):
        v = Xm[idx, names.index(k)]; f = np.isfinite(v)
        if f.sum() > 1: RK[idx[f], c] = rankdata(v[f]) / (f.sum() - 1) - 0.5
ALL = np.concatenate([Xm, RK], 1); ALLN = names + [k + "_r" for k in rk_names]; is_rank = np.array([0] * len(names) + [1] * len(rk_names))
hit = {k: round(float(np.isfinite(ALL[:, c]).mean()), 4) for c, k in enumerate(ALLN)}
cache_cols = [k for k in names if k not in ("cap", "rate_over_cap", "at_cap", "d3_settle", "n_consec_at_cap", "coh_mean_rate_over_cap", "fund_now", "iv_h", "rn8", "ema_gap")]
guard = {"hit_rate": hit, "cache_derived_min_hit": round(min(hit[k] for k in cache_cols), 4), "cache_derived_all_ge_0.95": bool(all(hit[k] >= 0.95 for k in cache_cols)), "cap_coverage_names": int(np.isfinite(CAP).sum()), "cap_coverage_rows": round(float(np.isfinite(X["cap"]).mean()), 4)}
np.savez_compressed(f"{ROOT}/data/features.npz", PI=PI, PJ=PJ, E_ts=E_ts, X=ALL, names=np.array(ALLN), is_rank=is_rank, self_sha256=SELF)
json.dump({"self_sha256": SELF, "n_rows": int(n), "n_cols": len(ALLN), "definitions": DEF, "rank_form": "per anchor, rankdata over cohort names with finite value /(n−1) − 0.5; NaN kept; F6 / indicator / interval / cap columns not ranked", "units": "returns fractions (Π−1); funding per-settlement fractions; rn8 8h-equivalent fraction; cap ratio dimensionless; ages in 4h anchors; cache rows ≤ E only", "guard_hit_rate": guard, "families": {"F1": ["r4h", "r1d", "r3d", "r7d", "dd7", "du7", "bars_since_hi7", "up_share_3d", "accel", "r1h", "r1h_over_r4h"], "F2": ["fund_now", "iv_h", "rn8", "cap", "rate_over_cap", "at_cap", "d3_settle", "n_consec_at_cap", "ema_gap"], "F3": ["qv_ratio", "tbf_diff", "avgsz_ratio", "cnt_ratio", "range_ratio"], "F4": ["min_ret5_4h", "n_big_4h", "cpos_4h", "r1h_over_r4h", "mdd_4h"], "F5": ["age_anchors", "young90"], "F6": ["n_rn8_ge15", "n_r3d_ge50", "coh_mean_du7", "coh_mean_rate_over_cap"]}}, open(f"{ROOT}/results/feature_defs.json", "w"), indent=1)
print("HIT_RATE " + json.dumps(hit), flush=True); print("GUARD_HIT " + json.dumps({k: v for k, v in guard.items() if k != "hit_rate"}), flush=True)
print(f"FEATURES_DONE rows {n} cols {len(ALLN)} ({time.time()-t0:.0f}s)", flush=True)
