#!/usr/bin/env python
"""FF · funding 因子深度重建装置 @jpline(2026-08-22, Session 6737834a-FF)。
PREREG(判据先冻结): multi_asset/exports/eda/RESULT_funding_factor_deepdive_2026-08-22.md §P
  (git f742252, 文件 sha256 2c9b670e…; 本脚本只实现 §P, 不新增判据)。
口径: 简单收益 expm1(log close→close), 实盘相位 [N, N+4h], 9821 锚 2022-01-01→2026-06-29, 两宇宙 140/400。
carry: ex-post 精确(结算时点 ∈ (N, N+4h], 各币真实周期) + ex-ante 代理 fund_now×4/iv。
A 十分位×regime / B 两腿同口径 / C 收敛候选 S1+S2 初筛 / 收据 R1-R6。
用法: python funding_factor_deepdive.py [--smoke K](只取前 K 锚, 结果文件带 _smoke 后缀)
只读输入; 输出 probe_artifacts/ff_results/。不碰实盘仓, 不调 API, 不写训练目录。
"""
import os, sys, json, time, hashlib, argparse
import numpy as np, pandas as pd
from scipy.stats import rankdata

ap = argparse.ArgumentParser(); ap.add_argument("--smoke", type=int, default=0); args = ap.parse_args()
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"; W3 = "/mnt/storage/private/work_hsy/w3lane"
OUTD = f"{PD}/ff_results"; os.makedirs(OUTD, exist_ok=True)
TAG = "_smoke" if args.smoke else ""
OUT_JSON = f"{OUTD}/funding_factor_deepdive_2026-08-22{TAG}.json"
IN = {"panel_wide_v2": f"{B}/wide_panel_4h_hist_v2.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "slow_oos": f"{B}/slow_pred_hist_oos.npy",
      "cube": f"{PD}/w2b_ret_cube.npz", "ph_preds": f"{PD}/ph_preds_2026-08-22.npz", "basis": f"{PD}/basis_premium_1h.npz",
      "panel_train": f"{MA}/exports/wide_dl_full_corrfund_causal_v1.npz", "metrics": f"{MA}/exports/wide_metrics_ch.npz",
      "xvenue": f"{W3}/xvenue_funding_binance.npz"}
COSTS = (4.137, 6.23); ANN = np.sqrt(6 * 365); H4 = 14400
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
def sha(p, full=True):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
def xrank(v):
    """xsec rank centred to [-0.5, 0.5], average ties, NaN kept NaN."""
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2: out[ok] = rankdata(v[ok]) / ok.sum() - 0.5 - 0.5 / ok.sum()
    return out
def spear(x, y, mn=10):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < mn: return np.nan
    return float(np.corrcoef(rankdata(x[ok]), rankdata(y[ok]))[0, 1])
def zsc(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2 and np.nanstd(v[ok]) > 1e-12: out[ok] = (v[ok] - v[ok].mean()) / v[ok].std()
    return out
def tstat(x, k=1):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3: return np.nan
    return float(x.mean() / (x.std(ddof=1) + 1e-30) * np.sqrt(len(x) / k))
def summ(x, yr, k=1):
    x = np.asarray(x, float)
    d = {"n": int(np.isfinite(x).sum()), "mean": float(np.nanmean(x)), "t": tstat(x, k),
         "sharpe": float(np.nanmean(x) / (np.nanstd(x, ddof=1) + 1e-30) * ANN), "by_year": {}}
    for y in sorted(set(yr.tolist())):
        s = x[yr == y]
        d["by_year"][int(y)] = {"mean": float(np.nanmean(s)), "t": tstat(s, k), "n": int(np.isfinite(s).sum()),
                                "sharpe": float(np.nanmean(s) / (np.nanstd(s, ddof=1) + 1e-30) * ANN)}
    return d
def r4(x): return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else (round(float(x), 5) if isinstance(x, (float, np.floating)) else x)
def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.ndarray): return clean(o.tolist())
    if isinstance(o, (np.bool_,)): return bool(o)
    return o

RES = {"session": "6737834a-FF", "prereg": "RESULT_funding_factor_deepdive_2026-08-22.md §P (git f742252)", "script_sha256": sha(__file__),
       "inputs_sha256": {}, "receipts": {}, "A": {}, "B": {}, "C": {}, "notes": []}
log("sha256 inputs ...")
for k, p in IN.items():
    RES["inputs_sha256"][k] = sha(p)
# ===================================================================== 1. load
PW = np.load(IN["panel_wide_v2"], allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); SYMS = [str(s) for s in PW["symbols"]]; NW = len(SYMS)
pw_row = {int(t): i for i, t in enumerate(pw_ts)}
FN_all = PW["f_fund_now"].astype(np.float64); IV_all = PW["f_fund_iv"].astype(np.float64)
V0_all = PW["f_fund_ema"].astype(np.float64); V1_all = PW["f_fund_ema_v1"].astype(np.float64); V2_all = PW["f_fund_ema_v2"].astype(np.float64)
M7_all = PW["f_mom_7d"].astype(np.float64); M30_all = PW["f_mom_30d"].astype(np.float64)
CUBE = np.load(IN["cube"], allow_pickle=True)
cts = CUBE["ts"].astype(np.int64); csyms = [str(s) for s in CUBE["symbols"]]
RES["receipts"]["R1_symbols_aligned"] = bool(csyms == SYMS); assert csyms == SYMS, "R1 FAIL: symbol order differs"
A = cts if not args.smoke else cts[:args.smoke]; n = len(A)
yr = pd.to_datetime(A, unit="s", utc=True).year.to_numpy(); hr = pd.to_datetime(A, unit="s", utc=True).hour.to_numpy()
crow = {int(t): i for i, t in enumerate(cts)}
R4L = CUBE["R_wide"].astype(np.float64)
def cube_at(offset_s):
    out = np.full((n, NW), np.nan)
    for i, t in enumerate(A):
        j = crow.get(int(t) + offset_s)
        if j is not None: out[i] = R4L[j]
    return out
r4 = np.expm1(R4L[[crow[int(t)] for t in A]])
r8 = (1 + r4) * (1 + np.expm1(cube_at(H4))) - 1
r24 = np.ones((n, NW))
for k in range(6): r24 *= (1 + np.expm1(cube_at(k * H4)))
r24 -= 1
log(f"anchors n={n} [{pd.Timestamp(A[0], unit='s', tz='UTC')} .. {pd.Timestamp(A[-1], unit='s', tz='UTC')}] r4 finite frac {np.isfinite(r4).mean():.3f} r24 {np.isfinite(r24).mean():.3f}")
def pw_at(X, offset_s, default=np.nan):
    out = np.full((n, NW), default)
    for i, t in enumerate(A):
        j = pw_row.get(int(t) + offset_s)
        if j is not None: out[i] = X[j]
    return out
FN = pw_at(FN_all, 0); IV = pw_at(IV_all, 0); V0 = pw_at(V0_all, 0); V1 = pw_at(V1_all, 0); V2 = pw_at(V2_all, 0); M7 = pw_at(M7_all, 0); M30 = pw_at(M30_all, 0)
with np.errstate(all="ignore"):
    FN_nf = FN * 8.0 / IV
    CHG = FN_nf - V1
    D24 = V1 - pw_at(V1_all, -6 * H4)
    # settlement at N (for stale variants) and at N+4h (ex-post carry)
    ivs = np.where(np.isfinite(IV) & (IV > 0), IV, np.nan)
    settleN = np.isfinite(ivs) & (np.mod(A[:, None], (ivs * 3600.0)) == 0)
    FN_m4 = pw_at(FN_all, -H4); V2_m4 = pw_at(V2_all, -H4)
    FN_stale = np.where(settleN, FN_m4, FN); V2_stale = np.where(settleN, V2_m4, V2)
    IVn = pw_at(IV_all, H4); FNn = pw_at(FN_all, H4)
    ivn = np.where(np.isfinite(IVn) & (IVn > 0), IVn, np.nan)
    settle_end = np.isfinite(ivn) & (np.mod(A[:, None] + H4, (ivn * 3600.0)) == 0)
    mult = np.where(ivn >= 4, 1.0, 4.0 / ivn)
    CARRY = np.where(settle_end, FNn * mult, 0.0); CARRY[~np.isfinite(ivn) | ~np.isfinite(FNn)] = np.nan   # carry_long, positive = long pays
    CARRY_P = FN * 4.0 / IV                                                                              # ex-ante proxy
RES["notes"].append({"carry_iv_lt4_cells_approx": int((settle_end & (ivn < 4)).sum()), "carry_cells_total": int(np.isfinite(CARRY).sum())})
# ---- meta: U400
MT = np.load(IN["meta"], allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]
e_row = {int(t): i for i, t in enumerate(E_ts)}
SLOW_all = np.load(IN["slow_oos"])
U400 = np.zeros((n, NW), bool); SLOW = np.full((n, NW), np.nan); miss400 = 0
for i, t in enumerate(A):
    j = e_row.get(int(t))
    if j is None: miss400 += 1; continue
    m = np.asarray(members[j]); qv4h = np.expm1(np.clip(qvk[j, m], 0, 30)) * 48
    sel = m[(qv4h >= 2.5e5) & np.isfinite(r4[i, m])]
    U400[i, sel] = True; SLOW[i, m] = SLOW_all[j, m]
RES["notes"].append({"U400_anchors_missing_in_meta": miss400, "U400_size_mean": float(U400.sum(1).mean()), "U400_size_p10": float(np.percentile(U400.sum(1), 10)), "U400_size_p90": float(np.percentile(U400.sum(1), 90))})
# ---- training panel (140): member, Y1, Y4, CH funding_ema; ph_preds king_p3
TP = np.load(IN["panel_train"], allow_pickle=True, mmap_mode="r")
tp_ts = np.asarray(TP["ts"]).astype(np.int64); s140 = [str(s) for s in TP["symbols"]]; idx140 = np.array([SYMS.index(s) for s in s140])
tp_row = {int(t): i for i, t in enumerate(tp_ts)}
rowT = np.array([tp_row.get(int(t) * 1000 - 3600 * 1000, -1) for t in A]); assert (rowT >= 0).all(), "training panel row N-1h missing"
chn = [str(c) for c in TP["ch_names"]]; FI = chn.index("funding_ema")
MEM = np.asarray(TP["MEMBER110"])[rowT]; Y1 = np.asarray(TP["Y1"])[rowT].astype(np.float64); Y4 = np.asarray(TP["Y4"])[rowT].astype(np.float64)
log("reading CH[:,:,funding_ema] (strided mmap) ...")
CHF = np.asarray(TP["CH"][:, :, FI])[rowT].astype(np.float64)
r1h = np.expm1(Y1)
U140 = MEM & np.isfinite(r4[:, idx140])
PH = np.load(IN["ph_preds"], allow_pickle=True); ph_ts = PH["ts"].astype(np.int64)
assert np.array_equal(ph_ts, tp_ts), "ph_preds ts grid != training panel"
K140 = np.asarray(PH["king_p3"])[rowT].astype(np.float64)
d5 = np.abs(np.expm1(Y4) - r4[:, idx140]); okb = np.isfinite(d5)
RES["receipts"]["R5_expm1Y4_vs_cube_maxabs"] = float(np.nanmax(d5)) if okb.any() else None
RES["receipts"]["R5_pass"] = bool(okb.any() and np.nanmax(d5) < 1e-5)
log(f"U140 size mean {U140.sum(1).mean():.1f}; king_p3 finite frac on U140 {np.isfinite(K140[U140]).mean():.3f}; R5 maxabs {RES['receipts']['R5_expm1Y4_vs_cube_maxabs']:.2e}")
# ---- R4: in-role factor parity (stale ema_v2 vs training channel at live row)
a_, b_ = V2_stale[:, idx140][U140], CHF[U140]; ok = np.isfinite(a_) & np.isfinite(b_)
c_stale = float(np.corrcoef(a_[ok], b_[ok])[0, 1]); a2 = V2[:, idx140][U140]; ok2 = np.isfinite(a2) & np.isfinite(b_)
c_fresh = float(np.corrcoef(a2[ok2], b_[ok2])[0, 1])
ic_rows = [spear(V2_stale[i, idx140][U140[i]], CHF[i][U140[i]]) for i in range(0, n, max(1, n // 400))]
RES["receipts"]["R4_corr_ema_v2_stale_vs_train_channel"] = c_stale; RES["receipts"]["R4_corr_ema_v2_fresh_vs_train_channel"] = c_fresh
RES["receipts"]["R4_xsec_spearman_stale_vs_channel_median"] = float(np.nanmedian(ic_rows)); RES["receipts"]["R4_pass"] = bool(c_stale >= 0.99)
log(f"R4 corr stale {c_stale:.5f} fresh {c_fresh:.5f} xsec-spearman median {np.nanmedian(ic_rows):.4f}")
# ---- xvenue (140): R2/R3 exact carry
XV = np.load(IN["xvenue"], allow_pickle=True)["data"].item()
CARRY_X = np.full((n, 140), np.nan); LAST_X = np.full((n, 140), np.nan); nsym_x = 0
for k, s in enumerate(s140):
    a = XV.get(s)
    if a is None or len(a) == 0: continue
    a = np.asarray(a, float); ts_s = np.round(a[:, 0] / 1000.0 / 60.0) * 60.0; o = np.argsort(ts_s); ts_s = ts_s[o]; rt = a[o, 1]
    u, first = np.unique(ts_s, return_index=True); ts_s = u; rt = rt[first]; nsym_x += 1
    cs = np.concatenate([[0.0], np.cumsum(rt)])
    lo = np.searchsorted(ts_s, A, side="right"); hi = np.searchsorted(ts_s, A + H4, side="right")
    CARRY_X[:, k] = cs[hi] - cs[lo]
    p = lo - 1; okp = p >= 0; LAST_X[okp, k] = rt[p[okp]]
    # stale >12h guard same as wide builder
    stale = okp & ((A - np.where(okp, ts_s[np.maximum(p, 0)], 0)) > 12 * 3600); LAST_X[stale, k] = np.nan
    # coverage guard: only trust carry where last settlement within 12h of N+4h
    hi_p = hi - 1; okh = hi_p >= 0
    cov = okh & ((A + H4 - np.where(okh, ts_s[np.maximum(hi_p, 0)], 0)) <= 12 * 3600); CARRY_X[~cov, k] = np.nan
fn140 = FN[:, idx140]; okx = np.isfinite(fn140) & np.isfinite(LAST_X) & U140
RES["receipts"]["R2_fund_now_eq_xvenue_last_frac"] = float((np.abs(fn140[okx] - LAST_X[okx]) < 1e-9).mean()); RES["receipts"]["R2_n"] = int(okx.sum())
cg = CARRY[:, idx140]; okc = np.isfinite(cg) & np.isfinite(CARRY_X) & U140
RES["receipts"]["R3_carry_grid_eq_xvenue_frac"] = float((np.abs(cg[okc] - CARRY_X[okc]) < 1e-9).mean()); RES["receipts"]["R3_n"] = int(okc.sum())
RES["receipts"]["R3_carry_grid_vs_xvenue_corr"] = float(np.corrcoef(cg[okc], CARRY_X[okc])[0, 1])
RES["receipts"]["R3_mean_abs_diff_bps"] = float(np.mean(np.abs(cg[okc] - CARRY_X[okc])) * 1e4)
RES["receipts"]["R2_pass"] = bool(RES["receipts"]["R2_fund_now_eq_xvenue_last_frac"] >= 0.99); RES["receipts"]["R3_pass"] = bool(RES["receipts"]["R3_carry_grid_eq_xvenue_frac"] >= 0.99)
RES["receipts"]["xvenue_symbols_used"] = nsym_x
log(f"R2 frac {RES['receipts']['R2_fund_now_eq_xvenue_last_frac']:.4f} (n {okx.sum()}) | R3 frac {RES['receipts']['R3_carry_grid_eq_xvenue_frac']:.4f} corr {RES['receipts']['R3_carry_grid_vs_xvenue_corr']:.5f} mad {RES['receipts']['R3_mean_abs_diff_bps']:.4f} bps")
# ex-ante proxy vs ex-post exact (all cells, both universes)
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    if cols is None: ce, cp = CARRY[U], CARRY_P[U]
    else: ce, cp = CARRY[:, cols][U], CARRY_P[:, cols][U]
    ok = np.isfinite(ce) & np.isfinite(cp)
    RES["receipts"][f"carry_exante_vs_expost_{uname}"] = {"corr": float(np.corrcoef(ce[ok], cp[ok])[0, 1]), "mean_exact_bps": float(ce[ok].mean() * 1e4),
                                                          "mean_proxy_bps": float(cp[ok].mean() * 1e4), "mad_bps": float(np.abs(ce[ok] - cp[ok]).mean() * 1e4),
                                                          "frac_zero_exact": float((ce[ok] == 0).mean())}
# ---- metrics (140) and basis (140)
MX = np.load(IN["metrics"], allow_pickle=True, mmap_mode="r"); mx_ts = np.asarray(MX["ts"]).astype(np.int64)
assert np.array_equal(mx_ts, tp_ts) and [str(s) for s in MX["symbols"]] == s140, "metrics grid/symbols != training panel"
mxn = [str(c) for c in MX["ch_names"]]
DOI24 = np.asarray(MX["CH"][:, :, mxn.index("d_oi_24h")])[rowT].astype(np.float64); DOIM = np.asarray(MX["MASK"][:, :, mxn.index("d_oi_24h")])[rowT]
DOI24[~DOIM] = np.nan
BS = np.load(IN["basis"], allow_pickle=True); bs_ts = BS["ts_hour"].astype(np.int64); bs_row = {int(t): i for i, t in enumerate(bs_ts)}
assert [str(s) for s in BS["symbols"]] == s140
rb = np.array([bs_row.get(int(t) * 1000 - 3600 * 1000, -1) for t in A]); PREM = np.full((n, 140), np.nan); okr = rb >= 0
PREM[okr] = np.asarray(BS["PREM"])[rb[okr]].astype(np.float64)
log(f"metrics d_oi_24h finite frac on U140 {np.isfinite(DOI24[U140]).mean():.3f}; basis finite frac {np.isfinite(PREM[U140]).mean():.3f}")
# ---- state variables
iBTC = SYMS.index("BTCUSDT")
btc7 = M7[:, iBTC]; btc30 = M30[:, iBTC]
def xmed(X, U):
    out = np.full(n, np.nan)
    for i in range(n):
        v = X[i][U[i]]; v = v[np.isfinite(v)]
        if len(v) >= 10: out[i] = np.median(v)
    return out
STATES = {}
def terc(v):
    q1, q2 = np.nanpercentile(v, [100 / 3, 200 / 3]); b = np.full(n, -1)
    ok = np.isfinite(v); b[ok & (v <= q1)] = 0; b[ok & (v > q1) & (v <= q2)] = 1; b[ok & (v > q2)] = 2
    return b, (float(q1), float(q2))
STATES["btc7_sign"] = {"bucket": np.where(np.isfinite(btc7), (btc7 > 0).astype(int), -1), "labels": ["btc7<=0", "btc7>0"], "thr": None}
STATES["btc30_sign"] = {"bucket": np.where(np.isfinite(btc30), (btc30 > 0).astype(int), -1), "labels": ["btc30<=0", "btc30>0"], "thr": None}
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    M7u = M7[:, cols] if cols is not None else M7; V1u = V1[:, cols] if cols is not None else V1
    b, thr = terc(xmed(M7u, U)); STATES[f"mkt7_terc_{uname}"] = {"bucket": b, "labels": ["mkt7 low", "mid", "high"], "thr": thr}
    b, thr = terc(xmed(V1u, U)); STATES[f"fundreg_terc_{uname}"] = {"bucket": b, "labels": ["fund regime low", "mid", "high"], "thr": thr}
b, thr = terc(xmed(DOI24, U140)); STATES["oi24_terc_U140"] = {"bucket": b, "labels": ["dOI24 low", "mid", "high"], "thr": thr}
RES["states"] = {k: {"labels": v["labels"], "thr": v["thr"], "counts": [int((v["bucket"] == j).sum()) for j in range(len(v["labels"]))]} for k, v in STATES.items()}
# ===================================================================== 2. A · deciles
def decile_engine(S, U, rets, carry, carryp, ndec=10):
    """per-anchor decile means of each return horizon + carry; spread D_top-D_bottom; IC per horizon (S signed +)."""
    out = {h: np.full((n, ndec), np.nan) for h in rets}; cd = np.full((n, ndec), np.nan); cpd = np.full((n, ndec), np.nan)
    ic = {h: np.full(n, np.nan) for h in rets}; nn = np.zeros(n, int)
    for i in range(n):
        m = U[i] & np.isfinite(S[i]); idx = np.where(m)[0]
        if len(idx) < 30: continue
        s = S[i, idx]; r = rankdata(s); dec = np.minimum((r - 1) * ndec / len(idx), ndec - 1).astype(int); nn[i] = len(idx)
        for h, R in rets.items():
            rv = R[i, idx]; ic[h][i] = spear(s, rv)
            for d in range(ndec):
                sel = dec == d; v = rv[sel]; v = v[np.isfinite(v)]
                if len(v): out[h][i, d] = v.mean()
        cv = carry[i, idx]; cpv = carryp[i, idx]
        for d in range(ndec):
            sel = dec == d; v = cv[sel]; v = v[np.isfinite(v)]; w = cpv[sel]; w = w[np.isfinite(w)]
            if len(v): cd[i, d] = v.mean()
            if len(w): cpd[i, d] = w.mean()
    return out, cd, cpd, ic, nn
def agg_dec(DM, yr, k=1, scale=1e4):
    """DM: (n, 10) -> pooled/by-year decile means (bps) + spread + t."""
    def one(X):
        sp = X[:, -1] - X[:, 0]
        return {"dec": (np.nanmean(X, 0) * scale).tolist(), "spread": float(np.nanmean(sp) * scale), "t": tstat(sp * scale, k), "n": int(np.isfinite(sp).sum())}
    d = {"pooled": one(DM), "by_year": {int(y): one(DM[yr == y]) for y in sorted(set(yr.tolist()))}}
    return d
HOR = {"U140": ("1h", "4h", "8h", "24h"), "U400": ("4h", "8h", "24h")}
KH = {"1h": 1, "4h": 1, "8h": 2, "24h": 6}
VARS = {"fund_now_nf": FN_nf, "ema_v1": V1, "ema_v2": V2, "chg": CHG, "d24_ema_v1": D24, "ema_v0": V0}
DEC_STORE = {}
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    sub = (lambda X: X[:, cols]) if cols is not None else (lambda X: X)
    rets = {"4h": sub(r4), "8h": sub(r8), "24h": sub(r24)}
    if uname == "U140": rets["1h"] = r1h
    car, carp = sub(CARRY), sub(CARRY_P)
    RES["A"][uname] = {}
    for vn, Xv in VARS.items():
        S = sub(Xv)
        out, cd, cpd, ic, nn = decile_engine(S, U, rets, car, carp)
        DEC_STORE[(uname, vn)] = (out, cd, cpd, ic, nn)
        ent = {"n_names_mean": float(nn[nn > 0].mean()) if (nn > 0).any() else None, "price": {}, "ic": {}}
        for h in rets:
            ent["price"][h] = agg_dec(out[h], yr, KH[h]); ent["ic"][h] = summ(ic[h], yr, KH[h])
        ent["carry_long_4h"] = agg_dec(cd, yr); ent["carry_proxy_4h"] = agg_dec(cpd, yr)
        tot = out["4h"] - cd                      # long total = price − carry paid by long
        ent["total_long_4h"] = agg_dec(tot, yr)
        ic_tot = np.full(n, np.nan)
        for i in range(n):
            m = U[i]
            if m.sum() >= 30: ic_tot[i] = spear(S[i][m], (rets["4h"][i] - car[i])[m])
        ent["ic_total_long_4h"] = summ(ic_tot, yr)
        RES["A"][uname][vn] = ent
        log(f"A {uname} {vn}: IC4h {ent['ic']['4h']['mean']:+.4f} (t {ent['ic']['4h']['t']:+.1f}) spread4h {ent['price']['4h']['pooled']['spread']:+.2f} bps carry spread {ent['carry_long_4h']['pooled']['spread']:+.2f} | by_year IC4h " +
            " ".join(f"{y}:{v['mean']:+.4f}" for y, v in ent["ic"]["4h"]["by_year"].items()))
    # stale variants (U140 only)
    if uname == "U140":
        for vn, Xs in (("fund_now_nf_stale", (FN_stale * 8.0 / IV)[:, idx140]), ("ema_v2_stale", V2_stale[:, idx140]), ("train_channel_funding_ema", CHF)):
            ics = np.full(n, np.nan)
            for i in range(n):
                m = U[i]
                if m.sum() >= 30: ics[i] = spear(Xs[i][m], r4[i, idx140][m])
            RES["A"][uname][vn] = {"ic": {"4h": summ(ics, yr)}}
            log(f"A U140 {vn}: IC4h {np.nanmean(ics):+.4f}")
# ---- regime conditioning of the D10-D1 price spread (main vars: ema_v1, ema_v2, chg, fund_now_nf)
RES["A"]["regime"] = {}
for uname in ("U140", "U400"):
    RES["A"]["regime"][uname] = {}
    for vn in ("ema_v1", "ema_v2", "chg", "fund_now_nf"):
        out, cd, cpd, ic, nn = DEC_STORE[(uname, vn)]
        ent = {}
        for sname, sv in STATES.items():
            if sname.endswith("U140") and uname != "U140": continue
            if sname.endswith("U400") and uname != "U400": continue
            bk = sv["bucket"]; ent[sname] = {"labels": sv["labels"], "buckets": []}
            for j, lab in enumerate(sv["labels"]):
                sel = bk == j; row = {"label": lab, "n": int(sel.sum())}
                for h in ("4h", "8h", "24h"):
                    sp = (out[h][:, -1] - out[h][:, 0]) * 1e4
                    row[f"spread_{h}"] = float(np.nanmean(sp[sel])) if sel.any() else None; row[f"t_{h}"] = tstat(sp[sel], KH[h])
                    row[f"spread_{h}_2022_24"] = float(np.nanmean(sp[sel & (yr <= 2024)])) if (sel & (yr <= 2024)).any() else None
                    row[f"spread_{h}_2025_26"] = float(np.nanmean(sp[sel & (yr >= 2025)])) if (sel & (yr >= 2025)).any() else None
                    row[f"t_{h}_2022_24"] = tstat(sp[sel & (yr <= 2024)], KH[h]); row[f"t_{h}_2025_26"] = tstat(sp[sel & (yr >= 2025)], KH[h])
                    row[f"spread_{h}_by_year"] = {int(y): float(np.nanmean(sp[sel & (yr == y)])) for y in sorted(set(yr.tolist())) if (sel & (yr == y)).any()}
                csp = (cd[:, -1] - cd[:, 0]) * 1e4; row["carry_spread_4h"] = float(np.nanmean(csp[sel])) if sel.any() else None
                row["ic_4h"] = float(np.nanmean(ic["4h"][sel])) if sel.any() else None
                ent[sname]["buckets"].append(row)
            # frozen reading: sign flip with |t|>=2 in two buckets (4h or 8h)
            flips = []
            for h in ("4h", "8h"):
                vals = [(b[f"spread_{h}"], b[f"t_{h}"]) for b in ent[sname]["buckets"] if b[f"spread_{h}"] is not None]
                pos = [v for v in vals if v[0] > 0 and v[1] is not None and v[1] >= 2]; neg = [v for v in vals if v[0] < 0 and v[1] is not None and v[1] <= -2]
                flips.append(bool(pos and neg))
            ent[sname]["sign_flip_4h_or_8h"] = bool(any(flips))
        RES["A"]["regime"][uname][vn] = ent
log("regime tables done")
# ---- double sorts on U140: funding (ema_v1) decile × own dOI24 tercile; × basis tercile; basis⟂funding residual deciles
def double_sort(S, C, U, R, nd=10, nc=3):
    tab = np.full((n, nd, nc), np.nan)
    for i in range(n):
        m = U[i] & np.isfinite(S[i]) & np.isfinite(C[i]) & np.isfinite(R[i]); idx = np.where(m)[0]
        if len(idx) < 45: continue
        rs = rankdata(S[i, idx]); ds = np.minimum((rs - 1) * nd / len(idx), nd - 1).astype(int)
        rc = rankdata(C[i, idx]); dc = np.minimum((rc - 1) * nc / len(idx), nc - 1).astype(int)
        for a in range(nd):
            for b in range(nc):
                sel = (ds == a) & (dc == b)
                if sel.any(): tab[i, a, b] = R[i, idx][sel].mean()
    return tab
r4_140 = r4[:, idx140]; V1_140 = V1[:, idx140]; V2_140 = V2[:, idx140]; CHG_140 = CHG[:, idx140]
RES["A"]["double_sort_U140"] = {}
for nm, C in (("dOI24", DOI24), ("basis_PREM", PREM)):
    tab = double_sort(V1_140, C, U140, r4_140, nd=5, nc=3)
    pooled = np.nanmean(tab, 0) * 1e4
    sp_by_c = [(tab[:, -1, b] - tab[:, 0, b]) * 1e4 for b in range(3)]
    RES["A"]["double_sort_U140"][f"ema_v1_q5_x_{nm}_terc"] = {"price4h_bps_5x3": pooled.tolist(), "spread_Q5_Q1_by_cterc": [float(np.nanmean(s)) for s in sp_by_c],
                                                             "t_by_cterc": [tstat(s) for s in sp_by_c], "n": int(np.isfinite(tab[:, 0, 0]).sum()),
                                                             "spread_by_cterc_2022_24": [float(np.nanmean(s[yr <= 2024])) for s in sp_by_c], "spread_by_cterc_2025_26": [float(np.nanmean(s[yr >= 2025])) for s in sp_by_c]}
    # and own-variable as sort with funding as control (symmetry)
    tab2 = double_sort(C, V1_140, U140, r4_140, nd=5, nc=3)
    sp2 = [(tab2[:, -1, b] - tab2[:, 0, b]) * 1e4 for b in range(3)]
    RES["A"]["double_sort_U140"][f"{nm}_q5_x_ema_v1_terc"] = {"spread_Q5_Q1_by_fundterc": [float(np.nanmean(s)) for s in sp2], "t_by_fundterc": [tstat(s) for s in sp2]}
# chg × level double sort (both universes): is it level or change?
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    sub = (lambda X: X[:, cols]) if cols is not None else (lambda X: X)
    tab = double_sort(sub(V1), sub(CHG), U, sub(r4), nd=5, nc=3)
    sp_lvl = [(tab[:, -1, b] - tab[:, 0, b]) * 1e4 for b in range(3)]
    tab2 = double_sort(sub(CHG), sub(V1), U, sub(r4), nd=5, nc=3)
    sp_chg = [(tab2[:, -1, b] - tab2[:, 0, b]) * 1e4 for b in range(3)]
    RES["A"][uname]["double_sort_level_x_chg"] = {"level_Q5_Q1_within_chg_terc": [float(np.nanmean(s)) for s in sp_lvl], "t": [tstat(s) for s in sp_lvl],
                                                  "chg_Q5_Q1_within_level_terc": [float(np.nanmean(s)) for s in sp_chg], "t_chg": [tstat(s) for s in sp_chg],
                                                  "level_Q5_Q1_within_chg_terc_2025_26": [float(np.nanmean(s[yr >= 2025])) for s in sp_lvl],
                                                  "chg_Q5_Q1_within_level_terc_2025_26": [float(np.nanmean(s[yr >= 2025])) for s in sp_chg]}
# basis ⟂ funding residual deciles (U140)
BRES = np.full((n, 140), np.nan)
for i in range(n):
    m = U140[i] & np.isfinite(PREM[i]) & np.isfinite(V1_140[i])
    if m.sum() < 30: continue
    x = xrank(V1_140[i]); y = xrank(PREM[i]); xm, ym = x[m], y[m]
    beta = float(np.dot(xm, ym) / (np.dot(xm, xm) + 1e-30)); BRES[i, m] = ym - beta * xm
out, cd, cpd, ic, nn = decile_engine(BRES, U140, {"4h": r4_140, "8h": r8[:, idx140], "24h": r24[:, idx140]}, CARRY[:, idx140], CARRY_P[:, idx140])
RES["A"]["U140"]["basis_orth_funding"] = {"price": {h: agg_dec(out[h], yr, KH[h]) for h in out}, "ic": {h: summ(ic[h], yr, KH[h]) for h in ic}, "carry_long_4h": agg_dec(cd, yr)}
outb, cdb, _, icb, _ = decile_engine(PREM, U140, {"4h": r4_140, "8h": r8[:, idx140], "24h": r24[:, idx140]}, CARRY[:, idx140], CARRY_P[:, idx140])
RES["A"]["U140"]["basis_raw"] = {"price": {h: agg_dec(outb[h], yr, KH[h]) for h in outb}, "ic": {h: summ(icb[h], yr, KH[h]) for h in icb}, "carry_long_4h": agg_dec(cdb, yr)}
log("double sorts done")
# ---- factor-level correlations
def xsec_corr_mean(X, Y, U):
    v = [spear(X[i][U[i]], Y[i][U[i]]) for i in range(n)]; return float(np.nanmean(v)), float(np.nanmedian(v))
RES["A"]["factor_corr"] = {}
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    sub = (lambda X: X[:, cols]) if cols is not None else (lambda X: X)
    RES["A"]["factor_corr"][uname] = {"ema_v1_vs_ema_v2": xsec_corr_mean(sub(V1), sub(V2), U), "fund_now_nf_vs_ema_v1": xsec_corr_mean(sub(FN_nf), sub(V1), U),
                                      "chg_vs_ema_v1": xsec_corr_mean(sub(CHG), sub(V1), U), "d24_vs_ema_v1": xsec_corr_mean(sub(D24), sub(V1), U),
                                      "ema_v0_vs_ema_v1": xsec_corr_mean(sub(V0), sub(V1), U), "chg_vs_d24": xsec_corr_mean(sub(CHG), sub(D24), U)}
    if uname == "U140":
        RES["A"]["factor_corr"][uname]["basis_vs_ema_v1"] = xsec_corr_mean(PREM, V1_140, U140)
        RES["A"]["factor_corr"][uname]["dOI24_vs_ema_v1"] = xsec_corr_mean(DOI24, V1_140, U140)
log("factor corr done")
# ===================================================================== 3. B · two legs same caliber
def leg_sim(score, U, R, CAR, hold8=False, ema_alpha=None, costs=COSTS):
    """pure rank book; score signed so that + = long. hold8: refresh only at nominal hour%8==0 (held score vector)."""
    M = score.shape[1]; prev = np.zeros(M); held = None
    pnl = np.zeros(n); carp = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); ic = np.full(n, np.nan); nheld = np.zeros(n, int)
    for i in range(n):
        if held is None or (not hold8) or (hr[i] % 8 == 0): held = score[i].copy()
        m = U[i] & np.isfinite(held)
        w = np.zeros(M)
        if m.sum() >= 30:
            z = xrank(np.where(m, held, np.nan)); z = np.where(m, z, 0.0); z -= z[m].mean(); g = np.abs(z).sum()
            if g > 1e-12: w = z / g
        if ema_alpha is not None: w = prev + ema_alpha * (w - prev)
        rv = np.where(np.isfinite(R[i]), R[i], 0.0); cv = np.where(np.isfinite(CAR[i]), CAR[i], 0.0)
        pnl[i] = float(np.dot(w, rv)) * 1e4; carp[i] = float(np.dot(w, cv)) * 1e4; trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum())
        if m.sum() >= 30: ic[i] = spear(held[m], R[i][m])
        nheld[i] = int((np.abs(w) > 0).sum()); prev = w
    out = {"pnl": pnl, "carry_paid": carp, "trn": trn, "gross": gross, "ic": ic, "nheld": nheld}
    for c in costs: out[f"net@{c}"] = pnl - carp - trn * c
    out["total"] = pnl - carp
    return out
def leg_report(o):
    rep = {k: summ(o[k], yr) for k in ("pnl", "carry_paid", "total", "ic") + tuple(f"net@{c}" for c in COSTS)}
    rep["trn_mean"] = float(o["trn"].mean()); rep["gross_mean"] = float(o["gross"].mean()); rep["nheld_mean"] = float(o["nheld"].mean())
    return rep
LEGS = {}
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    sub = (lambda X: X[:, cols]) if cols is not None else (lambda X: X)
    R, CAR = sub(r4), sub(CARRY)
    LEGS[uname] = {"IN_fresh4h": leg_sim(-sub(V2), U, R, CAR), "IN_hold8h": leg_sim(-sub(V2), U, R, CAR, hold8=True),
                   "WIDE_fresh4h": leg_sim(sub(V1), U, R, CAR), "WIDE_ema0.1": leg_sim(sub(V1), U, R, CAR, ema_alpha=0.1),
                   "IN_fresh4h_on_v1sign-": leg_sim(-sub(V1), U, R, CAR), "CHG_fresh4h": leg_sim(sub(CHG), U, R, CAR), "D24_fresh4h": leg_sim(sub(D24), U, R, CAR),
                   "FUNDNOW_short": leg_sim(-sub(FN_nf), U, R, CAR)}
    if uname == "U140":
        LEGS[uname]["IN_hold8h_stale"] = leg_sim(-V2_stale[:, idx140], U, R, CAR, hold8=True)
        LEGS[uname]["IN_hold8h_trainchannel"] = leg_sim(-CHF, U, R, CAR, hold8=True)
    RES["B"][uname] = {k: leg_report(v) for k, v in LEGS[uname].items()}
    a_, b_ = LEGS[uname]["IN_fresh4h"], LEGS[uname]["WIDE_fresh4h"]
    RES["B"][uname]["rho"] = {"net_IN_vs_WIDE": float(np.corrcoef(a_["net@4.137"], b_["net@4.137"])[0, 1]), "pnl_IN_vs_WIDE": float(np.corrcoef(a_["pnl"], b_["pnl"])[0, 1]),
                               "net_INhold8_vs_WIDEema": float(np.corrcoef(LEGS[uname]["IN_hold8h"]["net@4.137"], LEGS[uname]["WIDE_ema0.1"]["net@4.137"])[0, 1])}
    yrs = sorted(set(yr.tolist()))
    both = {int(y): {"IN_net": RES["B"][uname]["IN_hold8h"]["net@4.137"]["by_year"][y]["mean"], "WIDE_net": RES["B"][uname]["WIDE_ema0.1"]["net@4.137"]["by_year"][y]["mean"]} for y in yrs}
    for y in both: both[y]["class"] = "both+" if both[y]["IN_net"] > 0 and both[y]["WIDE_net"] > 0 else ("both-" if both[y]["IN_net"] < 0 and both[y]["WIDE_net"] < 0 else "exclusive")
    RES["B"][uname]["year_classes"] = both
    # horizon IC of the two variables (signed +)
    RES["B"][uname]["horizon_ic"] = {vn: {h: {"mean": RES["A"][uname][vn]["ic"][h]["mean"], "t": RES["A"][uname][vn]["ic"][h]["t"], "by_year": {y: v["mean"] for y, v in RES["A"][uname][vn]["ic"][h]["by_year"].items()}}
                                           for h in HOR[uname]} for vn in ("ema_v1", "ema_v2", "chg", "fund_now_nf", "d24_ema_v1")}
    log(f"B {uname}: IN_hold8h net {RES['B'][uname]['IN_hold8h']['net@4.137']['mean']:+.3f} (S {RES['B'][uname]['IN_hold8h']['net@4.137']['sharpe']:+.2f}) price {RES['B'][uname]['IN_hold8h']['pnl']['mean']:+.3f} carry_paid {RES['B'][uname]['IN_hold8h']['carry_paid']['mean']:+.3f} | WIDE_ema net {RES['B'][uname]['WIDE_ema0.1']['net@4.137']['mean']:+.3f} (S {RES['B'][uname]['WIDE_ema0.1']['net@4.137']['sharpe']:+.2f}) price {RES['B'][uname]['WIDE_ema0.1']['pnl']['mean']:+.3f} carry_paid {RES['B'][uname]['WIDE_ema0.1']['carry_paid']['mean']:+.3f} rho_net {RES['B'][uname]['rho']['net_IN_vs_WIDE']:+.3f}")
# ===================================================================== 4. C · convergence candidates (first read)
def s1_gate(cand, K, U, R):
    dic = np.full(n, np.nan); icr = np.full(n, np.nan); ick = np.full(n, np.nan); icc = np.full(n, np.nan)
    for i in range(n):
        m = U[i] & np.isfinite(K[i]) & np.isfinite(cand[i]) & np.isfinite(R[i])
        if m.sum() < 30: continue
        zk = zsc(np.where(m, K[i], np.nan)); zc = zsc(np.where(m, cand[i], np.nan))
        if not (np.isfinite(zk[m]).all() and np.isfinite(zc[m]).all()): continue
        b = 0.7 * zk + 0.3 * zc
        ick[i] = spear(zk[m], R[i][m]); icc[i] = spear(zc[m], R[i][m]); dic[i] = spear(b[m], R[i][m]) - ick[i]
        x = xrank(np.where(m, K[i], np.nan))[m]; y = xrank(np.where(m, R[i], np.nan))[m]
        beta = float(np.dot(x, y) / (np.dot(x, x) + 1e-30)); icr[i] = spear(cand[i][m], y - beta * x)
    yrs_ok = [y for y in sorted(set(yr.tolist())) if np.isfinite(dic[yr == y]).sum() >= 100]
    by = {int(y): float(np.nanmean(dic[yr == y])) for y in yrs_ok}
    mean = float(np.nanmean([v for v in by.values()])) if by else np.nan
    return {"dIC_blend_0.7_0.3": summ(dic, yr), "dIC_year_mean_of_years": mean, "dIC_by_year": by, "pass": bool(by and mean >= 0.003 and all(v >= 0 for v in by.values())),
            "ic_king": summ(ick, yr), "ic_cand": summ(icc, yr), "ic_cand_on_king_resid": summ(icr, yr), "years_evaluated": yrs_ok}
def day_boot_ci(x, ats, nb=2000, seed=0):
    d = (np.asarray(ats) // 86400).astype(np.int64); u, inv = np.unique(d, return_inverse=True)
    s = np.zeros(len(u)); np.add.at(s, inv, np.nan_to_num(x)); c = np.zeros(len(u)); np.add.at(c, inv, 1.0)
    rng = np.random.default_rng(seed); means = []
    for _ in range(nb):
        idx = rng.integers(0, len(u), len(u)); means.append(s[idx].sum() / c[idx].sum())
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]
def s2_screen(o):
    net1 = o[f"net@{COSTS[0]}"]; net2 = o[f"net@{COSTS[1]}"]; ci = day_boot_ci(net1, A)
    by = {int(y): float(np.nanmean(net1[yr == y])) for y in sorted(set(yr.tolist()))}
    npos = sum(v > 0 for v in by.values()); sh = float(np.nanmean(net1) / (np.nanstd(net1, ddof=1) + 1e-30) * ANN)
    return {"net@4.137_mean": float(np.nanmean(net1)), "ci95_dayblock": ci, "net@6.23_mean": float(np.nanmean(net2)), "by_year_net@4.137": by, "n_years_pos": int(npos),
            "sharpe": sh, "pass": bool(ci[0] > 0 and np.nanmean(net2) >= 0 and npos >= 4 and sh > 0), "trn_mean": float(o["trn"].mean())}
RES["C"] = {}
for uname, U, cols in (("U140", U140, idx140), ("U400", U400, None)):
    sub = (lambda X: X[:, cols]) if cols is not None else (lambda X: X)
    R, CAR = sub(r4), sub(CARRY); K = K140 if uname == "U140" else SLOW
    ent = {}
    # C1 carry leg with causal state gate (6 cells = btc7_sign × fundreg terc of this universe)
    base = LEGS[uname]["IN_hold8h"]; tot = base["total"]
    cell = STATES["btc7_sign"]["bucket"] * 3 + STATES[f"fundreg_terc_{uname}"]["bucket"]; cell[(STATES["btc7_sign"]["bucket"] < 0) | (STATES[f"fundreg_terc_{uname}"]["bucket"] < 0)] = -1
    gate = np.ones(n, bool); ncell = {}
    # causal: anchors j with A[j] <= A[i]-86400
    jmax = np.searchsorted(A, A - 86400, side="right")      # number of anchors with ts <= A[i]-1d
    cs_tot = {c: np.concatenate([[0.0], np.cumsum(np.where(cell == c, np.nan_to_num(tot), 0.0))]) for c in range(6)}
    cs_cnt = {c: np.concatenate([[0], np.cumsum((cell == c).astype(int))]) for c in range(6)}
    for i in range(n):
        c = cell[i]
        if c < 0: continue
        k = jmax[i]; cnt = cs_cnt[c][k]
        if cnt >= 60 and cs_tot[c][k] / cnt <= 0: gate[i] = False
    # gated simulation: recompute with weights zeroed when gate off (cost on actual weight changes)
    def leg_sim_gated(score, U, R, CAR, gate):
        M = score.shape[1]; prev = np.zeros(M); held = None
        pnl = np.zeros(n); carp = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); ic = np.full(n, np.nan); nheld = np.zeros(n, int)
        for i in range(n):
            if held is None or (hr[i] % 8 == 0): held = score[i].copy()
            m = U[i] & np.isfinite(held); w = np.zeros(M)
            if gate[i] and m.sum() >= 30:
                z = xrank(np.where(m, held, np.nan)); z = np.where(m, z, 0.0); z -= z[m].mean(); g = np.abs(z).sum()
                if g > 1e-12: w = z / g
            rv = np.where(np.isfinite(R[i]), R[i], 0.0); cv = np.where(np.isfinite(CAR[i]), CAR[i], 0.0)
            pnl[i] = float(np.dot(w, rv)) * 1e4; carp[i] = float(np.dot(w, cv)) * 1e4; trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum())
            if m.sum() >= 30: ic[i] = spear(held[m], R[i][m])
            nheld[i] = int((np.abs(w) > 0).sum()); prev = w
        out = {"pnl": pnl, "carry_paid": carp, "trn": trn, "gross": gross, "ic": ic, "nheld": nheld, "total": pnl - carp}
        for c in COSTS: out[f"net@{c}"] = pnl - carp - trn * c
        return out
    gated = leg_sim_gated(-sub(V2), U, R, CAR, gate)
    cell_stats = {}
    for c in range(6):
        sel = cell == c
        cell_stats[c] = {"label": f"{STATES['btc7_sign']['labels'][c // 3]} & {STATES[f'fundreg_terc_{uname}']['labels'][c % 3]}", "n": int(sel.sum()),
                         "ungated_total_mean": float(np.nanmean(tot[sel])) if sel.any() else None, "gate_on_frac": float(gate[sel].mean()) if sel.any() else None}
    ent["C1_carry_leg_gated"] = {"gate_on_frac": float(gate.mean()), "cells": cell_stats, "report": leg_report(gated), "ungated_report": RES["B"][uname]["IN_hold8h"],
                                 "delta_net@4.137_vs_ungated": float(np.nanmean(gated["net@4.137"]) - np.nanmean(base["net@4.137"])),
                                 "S1": s1_gate(-sub(V2), K, U, R), "S2_screen_gated": s2_screen(gated), "S2_screen_ungated": s2_screen(base)}
    # C2 momentum leg: +chg (primary) / +d24 (secondary)
    ent["C2_momentum_chg"] = {"report": RES["B"][uname]["CHG_fresh4h"], "S1": s1_gate(sub(CHG), K, U, R), "S2_screen": s2_screen(LEGS[uname]["CHG_fresh4h"])}
    ent["C2_momentum_d24"] = {"report": RES["B"][uname]["D24_fresh4h"], "S1": s1_gate(sub(D24), K, U, R), "S2_screen": s2_screen(LEGS[uname]["D24_fresh4h"])}
    # reference: the two deployed legs through the same screens
    ent["ref_WIDE_ema_v1"] = {"S1": s1_gate(sub(V1), K, U, R), "S2_screen": s2_screen(LEGS[uname]["WIDE_ema0.1"])}
    ent["ref_IN_minus_ema_v2"] = {"S1": ent["C1_carry_leg_gated"]["S1"], "S2_screen": ent["C1_carry_leg_gated"]["S2_screen_ungated"]}
    RES["C"][uname] = ent
    log(f"C {uname}: C1 gate on {gate.mean():.2f} Δnet {ent['C1_carry_leg_gated']['delta_net@4.137_vs_ungated']:+.3f} S1 pass {ent['C1_carry_leg_gated']['S1']['pass']} (dIC {ent['C1_carry_leg_gated']['S1']['dIC_year_mean_of_years']:+.4f}) S2 {ent['C1_carry_leg_gated']['S2_screen_gated']['pass']} | C2 chg S1 {ent['C2_momentum_chg']['S1']['pass']} (dIC {ent['C2_momentum_chg']['S1']['dIC_year_mean_of_years']:+.4f}) S2 {ent['C2_momentum_chg']['S2_screen']['pass']} | WIDE ref S1 {ent['ref_WIDE_ema_v1']['S1']['pass']} (dIC {ent['ref_WIDE_ema_v1']['S1']['dIC_year_mean_of_years']:+.4f})")
# ===================================================================== 5. save
RES["meta"] = {"n_anchors": int(n), "first": str(pd.Timestamp(A[0], unit="s", tz="UTC")), "last": str(pd.Timestamp(A[-1], unit="s", tz="UTC")), "smoke": bool(args.smoke),
               "years": {int(y): int((yr == y).sum()) for y in sorted(set(yr.tolist()))}, "costs": COSTS, "ann": float(ANN)}
json.dump(clean(RES), open(OUT_JSON, "w"), indent=1, ensure_ascii=False)
np.savez_compressed(OUT_JSON.replace(".json", "_series.npz"), ts=A, yr=yr, **{f"{u}__{k}__{s}": v[s] for u in LEGS for k, v in LEGS[u].items() for s in ("pnl", "carry_paid", "trn", "net@4.137", "ic")})
log("DONE ->", OUT_JSON, "sha", sha(OUT_JSON)[:16])
