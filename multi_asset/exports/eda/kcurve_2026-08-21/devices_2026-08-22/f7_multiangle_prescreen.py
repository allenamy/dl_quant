#!/usr/bin/env python
"""F7 · 多角度非 funding 价格反应来源 S1 预筛装置 @jpline(2026-08-22, Session 6737834a-F7)。
PREREG(判据先冻结): multi_asset/exports/eda/PREREG_RESULT_F7_multiangle_sources_2026-08-22.md §P (git a262418, 文件 sha256 d9c75ca5…; 本脚本只实现 §P, 不新增判据)。
口径(= FF funding_factor_deepdive.py 同源): 简单收益 expm1(R_wide), 实盘相位 [N, N+4h], 9821 锚 2022-01-01→2026-06-29, U400 = meta members ∩ qv4h≥2.5e5, king = slow_pred_hist_oos(宽 slow-LGBM OOS)。
S1 门: ΔIC = IC(0.7 z_king + 0.3 z_cand) − IC(z_king); 过 = 评估年(≥100 锚)逐年均值 ≥ +0.003 且每年 ≥ 0。子集规则: 覆盖 <80% ⇒ "子集预读"。
8 候选(§P1): P1 d_oi_24h(+) P2 doi_x_ret(+) P3 top_vs_global_divergence(+) P4 oi_level_norm(−) [metrics 行 N−1h, 140 名子集];
            P5 r_settle(−) [结算后首小时反应, 829 名 1h]; S1 sshare24(+) S2 stbi24(+) S3 dsshare(+) [现货 1h, 映射名]。
收据 R1-R7 脚本断言(§P5)。只读输入; 输出 probe_artifacts/f7/。不碰实盘仓, 不调交易 API, 不写训练目录。
用法: python f7_multiangle_prescreen.py [--smoke K]
"""
import os, sys, json, time, hashlib, argparse
import numpy as np, pandas as pd
from scipy.stats import rankdata

ap = argparse.ArgumentParser(); ap.add_argument("--smoke", type=int, default=0); args = ap.parse_args()
B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"; W3 = "/mnt/storage/private/work_hsy/w3lane"; F7 = f"{PD}/f7"
TAG = "_smoke" if args.smoke else ""
OUT_JSON = f"{F7}/f7_multiangle_prescreen_2026-08-22{TAG}.json"
IN = {"panel_wide_v2": f"{B}/wide_panel_4h_hist_v2.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "slow_oos": f"{B}/slow_pred_hist_oos.npy",
      "cube": f"{PD}/w2b_ret_cube.npz", "metrics": f"{MA}/exports/wide_metrics_ch.npz", "perp1h": f"{F7}/perp1h_panel.npz", "spot1h": f"{F7}/spot1h_panel.npz",
      "xvenue": f"{W3}/xvenue_funding_binance.npz", "spot_map": f"{F7}/f7_spot_map.json"}
H4 = 14400; H1 = 3600; ANN = np.sqrt(6 * 365)
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
# ---- helpers verbatim from FF (S1 definition identity) ----
def xrank(v):
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
    d = {"n": int(np.isfinite(x).sum()), "mean": float(np.nanmean(x)) if np.isfinite(x).any() else None, "t": tstat(x, k), "by_year": {}}
    for y in sorted(set(yr.tolist())):
        s = x[yr == y]
        d["by_year"][int(y)] = {"mean": float(np.nanmean(s)) if np.isfinite(s).any() else None, "t": tstat(s, k), "n": int(np.isfinite(s).sum())}
    return d
def f4(x):
    return "nan" if x is None or not np.isfinite(x) else f"{x:+.4f}"
def f1(x):
    return "nan" if x is None or not np.isfinite(x) else f"{x:+.1f}"
def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.ndarray): return clean(o.tolist())
    if isinstance(o, (np.bool_,)): return bool(o)
    return o

RES = {"session": "6737834a-F7", "prereg": "PREREG_RESULT_F7_multiangle_sources_2026-08-22.md §P (git a262418)", "script_sha256": sha(__file__),
       "inputs_sha256": {}, "receipts": {}, "candidates": {}, "corr": {}, "notes": []}
log("sha256 inputs ...")
for k, p in IN.items(): RES["inputs_sha256"][k] = sha(p)
# ===================================================================== 1. load (FF-identical)
PW = np.load(IN["panel_wide_v2"], allow_pickle=True)
pw_ts = PW["ts"].astype(np.int64); SYMS = [str(s) for s in PW["symbols"]]; NW = len(SYMS); pw_row = {int(t): i for i, t in enumerate(pw_ts)}
CUBE = np.load(IN["cube"], allow_pickle=True); cts = CUBE["ts"].astype(np.int64); csyms = [str(s) for s in CUBE["symbols"]]
RES["receipts"]["R1_symbols_aligned"] = bool(csyms == SYMS); assert csyms == SYMS, "R1 FAIL"
A = cts if not args.smoke else cts[:args.smoke]; n = len(A)
yr = pd.to_datetime(A, unit="s", utc=True).year.to_numpy()
crow = {int(t): i for i, t in enumerate(cts)}
R4L = CUBE["R_wide"].astype(np.float64); r4 = np.expm1(R4L[[crow[int(t)] for t in A]])
def pw_at(X, offset_s):
    out = np.full((n, NW), np.nan)
    for i, t in enumerate(A):
        j = pw_row.get(int(t) + offset_s)
        if j is not None: out[i] = X[j]
    return out
IV = pw_at(PW["f_fund_iv"].astype(np.float64), 0); FN = pw_at(PW["f_fund_now"].astype(np.float64), 0)
V1 = pw_at(PW["f_fund_ema_v1"].astype(np.float64), 0); V2 = pw_at(PW["f_fund_ema_v2"].astype(np.float64), 0)
REV24 = pw_at(PW["f_rev_24h"].astype(np.float64), 0); AMI = pw_at(PW["f_amihud_24h"].astype(np.float64), 0)
VOLQ = pw_at(PW["f_volq_ratio"].astype(np.float64), 0); M7 = pw_at(PW["f_mom_7d"].astype(np.float64), 0)
with np.errstate(all="ignore"): FN_nf = FN * 8.0 / IV
MT = np.load(IN["meta"], allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]; e_row = {int(t): i for i, t in enumerate(E_ts)}
SLOW_all = np.load(IN["slow_oos"])
U400 = np.zeros((n, NW), bool); SLOW = np.full((n, NW), np.nan)
for i, t in enumerate(A):
    j = e_row[int(t)]; m = np.asarray(members[j]); qv4h = np.expm1(np.clip(qvk[j, m], 0, 30)) * 48
    sel = m[(qv4h >= 2.5e5) & np.isfinite(r4[i, m])]; U400[i, sel] = True; SLOW[i, m] = SLOW_all[j, m]
K = SLOW
RES["notes"].append({"U400_size_mean": float(U400.sum(1).mean()), "anchors": int(n), "first": str(pd.Timestamp(A[0], unit="s", tz="UTC")), "last": str(pd.Timestamp(A[-1], unit="s", tz="UTC"))})
log(f"anchors {n} U400 mean {U400.sum(1).mean():.1f}")
# ===================================================================== 2. 1h panels (perp + spot)
P1H = np.load(IN["perp1h"], allow_pickle=True); hts = P1H["ts"].astype(np.int64); T0H = int(hts[0]); NH = len(hts)
assert [str(s) for s in P1H["symbols"]] == SYMS, "perp1h symbols != panel"
S1H = np.load(IN["spot1h"], allow_pickle=True); assert np.array_equal(S1H["ts"].astype(np.int64), hts) and [str(s) for s in S1H["symbols"]] == SYMS, "spot1h grid/symbols"
pCL = P1H["close"].astype(np.float64); pQV = P1H["qv"].astype(np.float64); sCL = S1H["close"].astype(np.float64); sQV = S1H["qv"].astype(np.float64); sTB = S1H["tbq"].astype(np.float64)
hidx = ((A - T0H) // H1).astype(np.int64); assert ((A - T0H) % H1 == 0).all() and (hidx >= 169).all() and (hidx + 4 < NH).all(), "anchor hour index"
# R2: my perp close -> R_wide reproduction (log(close[h+3]/close[h-1]))
with np.errstate(all="ignore"): myR = np.log(pCL[hidx + 3] / pCL[hidx - 1])
okc = np.isfinite(myR) & np.isfinite(R4L[[crow[int(t)] for t in A]]) & U400
rng = np.random.default_rng(0); cells = np.argwhere(okc); pick = cells[rng.choice(len(cells), size=min(2000, len(cells)), replace=False)]
d2 = np.abs(myR[pick[:, 0], pick[:, 1]] - R4L[[crow[int(A[i])] for i in pick[:, 0]], pick[:, 1]])
RES["receipts"]["R2_myclose_vs_cube_maxabs"] = float(d2.max()); RES["receipts"]["R2_median"] = float(np.median(d2)); RES["receipts"]["R2_pass"] = bool(d2.max() < 1e-5)
RES["receipts"]["R2_coverage_myR_on_U400"] = float(np.isfinite(myR[U400]).mean())
log(f"R2 maxabs {d2.max():.2e} median {np.median(d2):.2e} pass {RES['receipts']['R2_pass']}; perp1h coverage on U400 {RES['receipts']['R2_coverage_myR_on_U400']:.4f}")
# rolling sums over bars open_time in [N-W h, N-1h] == indices [h-W, h-1]
def csum(X):
    Z = np.where(np.isfinite(X), X, 0.0); C = np.concatenate([np.zeros((1, X.shape[1])), np.cumsum(Z, 0)]); F = np.concatenate([np.zeros((1, X.shape[1])), np.cumsum(np.isfinite(X).astype(np.float64), 0)]); return C, F
def wsum(C, F, W, minfrac=0.8):
    """sum over indices [h-W, h-1]; NaN if fewer than minfrac*W finite bars"""
    s = C[hidx] - C[hidx - W]; f = F[hidx] - F[hidx - W]; s[f < minfrac * W] = np.nan; return s
cPQ, fPQ = csum(pQV); cSQ, fSQ = csum(sQV); cST, fST = csum(sTB)
pqv24 = wsum(cPQ, fPQ, 24); sqv24 = wsum(cSQ, fSQ, 24); stb24 = wsum(cST, fST, 24); pqv168 = wsum(cPQ, fPQ, 168); sqv168 = wsum(cSQ, fSQ, 168)
RES["receipts"]["R5_max_bar_open_time_minus_N_hours"] = -1   # windows end at index h-1 == N-1h by construction (asserted above on hidx)
# R6: spot mapping sanity — hourly log-return corr perp vs spot per symbol
with np.errstate(all="ignore"): pr = np.diff(np.log(pCL), axis=0); sr = np.diff(np.log(sCL), axis=0)
MAPJ = json.load(open(IN["spot_map"])); r6 = {}; bad = []
for k, s in enumerate(SYMS):
    ok = np.isfinite(pr[:, k]) & np.isfinite(sr[:, k])
    if ok.sum() < 500: continue
    c = float(np.corrcoef(pr[ok, k], sr[ok, k])[0, 1]); r6[s] = {"spot": MAPJ["map"].get(s), "corr": c, "n_hours": int(ok.sum())}
    if not (c >= 0.95): bad.append(s)
RES["receipts"]["R6_n_symbols_with_spot_overlap"] = len(r6); RES["receipts"]["R6_corr_median"] = float(np.median([v["corr"] for v in r6.values()])) if r6 else None
RES["receipts"]["R6_excluded_symbols"] = {s: r6[s] for s in bad}; RES["receipts"]["R6_pass"] = bool(r6 and RES["receipts"]["R6_corr_median"] >= 0.95)
spot_ok = np.ones(NW, bool)
for s in bad: spot_ok[SYMS.index(s)] = False
for k, s in enumerate(SYMS):
    if s not in r6: spot_ok[k] = np.isfinite(sCL[:, k]).any()   # symbols with spot data but <500 overlap hours: keep (coverage small)
log(f"R6 spot overlap symbols {len(r6)} corr median {RES['receipts']['R6_corr_median']} excluded {len(bad)}: {bad[:20]}")
# ===================================================================== 3. candidates
with np.errstate(all="ignore"):
    sshare24 = sqv24 / (sqv24 + pqv24); sshare24[~spot_ok[None, :].repeat(n, 0)] = np.nan; sshare24[~(pqv24 > 0)] = np.nan
    sshare168 = sqv168 / (sqv168 + pqv168); sshare168[~spot_ok[None, :].repeat(n, 0)] = np.nan; sshare168[~(pqv168 > 0)] = np.nan
    stbi24 = (2.0 * stb24 - sqv24) / sqv24; stbi24[~(sqv24 > 0)] = np.nan; stbi24[~spot_ok[None, :].repeat(n, 0)] = np.nan
    dsshare = sshare24 - sshare168
    # P5 settlement reaction: s = largest multiple of iv*3600 <= N-1h; r = close_bar(s)/close_bar(s-1h) - 1 ; minus xsec median on U400
    ivh = np.where(np.isfinite(IV) & (IV > 0), IV, np.nan)
    per = ivh * 3600.0
    s_ts = np.floor((A[:, None] - H1) / per) * per
    si = np.where(np.isfinite(s_ts), ((s_ts - T0H) // H1), -1).astype(np.int64)
    valid = (si >= 1) & (si <= hidx[:, None] - 1)
    rset = np.full((n, NW), np.nan)
    ii, jj = np.where(valid)
    rset[ii, jj] = pCL[si[ii, jj], jj] / pCL[si[ii, jj] - 1, jj] - 1.0
    RES["receipts"]["R5_settle_bar_index_le_hm1"] = bool((si[valid] <= (hidx[:, None] - 1).repeat(NW, 1)[valid]).all())
    med = np.full(n, np.nan)
    for i in range(n):
        v = rset[i][U400[i]]; v = v[np.isfinite(v)]
        if len(v) >= 10: med[i] = np.median(v)
    rset_dm = rset - med[:, None]
# R4: inferred settlement times vs xvenue actual (140 syms)
XV = np.load(IN["xvenue"], allow_pickle=True)["data"].item(); hit = 0; tot = 0
for s, a in XV.items():
    if s not in SYMS or a is None or len(a) == 0: continue
    k = SYMS.index(s); a = np.asarray(a, float); act = np.unique(np.round(a[:, 0] / 1000.0 / 60.0) * 60.0)
    st = s_ts[:, k]; okk = np.isfinite(st) & U400[:, k] & (st >= act.min()) & (st <= act.max())
    if okk.sum() == 0: continue
    pos = np.searchsorted(act, st[okk]); pos = np.clip(pos, 0, len(act) - 1)
    near = np.minimum(np.abs(act[pos] - st[okk]), np.abs(act[np.maximum(pos - 1, 0)] - st[okk]))
    hit += int((near <= 60).sum()); tot += int(okk.sum())
RES["receipts"]["R4_settlement_inferred_hit_frac"] = float(hit / tot) if tot else None; RES["receipts"]["R4_n"] = tot; RES["receipts"]["R4_pass"] = bool(tot and hit / tot >= 0.95)
log(f"R4 settlement inference hit {hit}/{tot} = {hit/max(tot,1):.4f}")
# metrics (140) at row N-1h
MX = np.load(IN["metrics"], allow_pickle=True, mmap_mode="r"); mx_ts = np.asarray(MX["ts"]).astype(np.int64); mx_row = {int(t): i for i, t in enumerate(mx_ts)}
msym = [str(s) for s in MX["symbols"]]; midx = np.array([SYMS.index(s) for s in msym]); mxn = [str(c) for c in MX["ch_names"]]
rowM = np.array([mx_row.get((int(t) - H1) * 1000, -1) for t in A]); RES["receipts"]["R3_metrics_row_Nm1h_exist_frac"] = float((rowM >= 0).mean()); RES["receipts"]["R3_pass"] = bool((rowM >= 0).all())
assert (rowM >= 0).all(), "R3 FAIL: metrics row N-1h missing"
RES["receipts"]["R3_metrics_grid_hourly_ms"] = bool(np.all(np.diff(mx_ts[:100]) == 3600000))
def mchan(name):
    ci = mxn.index(name); X = np.asarray(MX["CH"][:, :, ci])[rowM].astype(np.float64); M = np.asarray(MX["MASK"][:, :, ci])[rowM]; X[~M] = np.nan
    out = np.full((n, NW), np.nan); out[:, midx] = X; return out
CANDS = {  # name: (matrix, sign, angle, note)
    "P1_d_oi_24h": (mchan("d_oi_24h"), +1, "合约/持仓(metrics 140 子集)", "OI 24h 变化"),
    "P2_doi_x_ret": (mchan("doi_x_ret"), +1, "合约/持仓(metrics 140 子集)", "OI 变化×收益交互"),
    "P3_top_vs_global_div": (mchan("top_vs_global_divergence"), +1, "合约/持仓(metrics 140 子集)", "大户 vs 散户多空比分歧"),
    "P4_oi_level_norm": (mchan("oi_level_norm"), -1, "合约/持仓(metrics 140 子集)", "OI/成交额 杠杆强度"),
    "P5_r_settle": (rset_dm, -1, "合约/结构(829 名 1h)", "结算后首小时反应(去截面中位)"),
    "S1_sshare24": (sshare24, +1, "现货(映射名)", "现货成交占比 24h"),
    "S2_stbi24": (stbi24, +1, "现货(映射名)", "现货主动买入失衡 24h"),
    "S3_dsshare": (dsshare, +1, "现货(映射名)", "现货占比 24h − 7d"),
}
# diagnostic (not a candidate): has_spot indicator
has_spot = np.isfinite(sshare24).astype(float); has_spot[~U400] = np.nan
# ===================================================================== 4. S1 machinery (FF-identical gate + extras)
def s1_gate(cand, K, U, R):
    dic = np.full(n, np.nan); icr = np.full(n, np.nan); ick = np.full(n, np.nan); icc = np.full(n, np.nan); cov = np.full(n, np.nan)
    for i in range(n):
        m = U[i] & np.isfinite(K[i]) & np.isfinite(cand[i]) & np.isfinite(R[i])
        base = U[i] & np.isfinite(K[i]) & np.isfinite(R[i])
        cov[i] = m.sum() / max(base.sum(), 1)
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
    seg = {"2022_24": float(np.nanmean(dic[(yr <= 2024)])) if np.isfinite(dic[yr <= 2024]).any() else None, "2025_26": float(np.nanmean(dic[(yr >= 2025)])) if np.isfinite(dic[yr >= 2025]).any() else None}
    return {"dIC_blend_0.7_0.3": summ(dic, yr), "dIC_year_mean_of_years": mean, "dIC_by_year": by, "pass": bool(by and mean >= 0.003 and all(v >= 0 for v in by.values())),
            "ic_king_same_subset": summ(ick, yr), "ic_cand": summ(icc, yr), "ic_cand_on_king_resid": summ(icr, yr), "years_evaluated": yrs_ok,
            "coverage_mean": float(np.nanmean(cov)), "coverage_by_year": {int(y): float(np.nanmean(cov[yr == y])) for y in sorted(set(yr.tolist()))}, "dIC_segments": seg, "_dic": dic}
def xsec_corr_mean(X, Y, U):
    v = np.array([spear(X[i][U[i]], Y[i][U[i]]) for i in range(n)]); return {"mean": float(np.nanmean(v)), "median": float(np.nanmedian(v)), "n": int(np.isfinite(v).sum())}
REFS = {"king": K, "fund_ema_v1": V1, "fund_ema_v2": V2, "fund_now_nf": FN_nf, "rev24": REV24, "amihud24": AMI, "volq_ratio": VOLQ, "mom7d": M7}
for name, (X, sgn, angle, note) in CANDS.items():
    log(f"--- {name}")
    Xs = sgn * X
    g = s1_gate(Xs, K, U400, r4); gflip = s1_gate(-Xs, K, U400, r4)
    # placebo: within-anchor permutation, 5 seeds
    plc = []
    for seed in range(5):
        rg = np.random.default_rng(seed); Xp = np.full_like(Xs, np.nan)
        for i in range(n):
            m = U400[i] & np.isfinite(Xs[i]); idx = np.where(m)[0]
            if len(idx) >= 2: Xp[i, idx] = Xs[i, rg.permutation(idx)]
        gp = s1_gate(Xp, K, U400, r4); plc.append(gp["dIC_year_mean_of_years"])
    corr = {r: xsec_corr_mean(Xs, Y, U400) for r, Y in REFS.items()}
    fund_pen = max([abs(corr[r]["mean"]) for r in ("fund_ema_v1", "fund_ema_v2", "fund_now_nf") if corr[r]["mean"] is not None and np.isfinite(corr[r]["mean"])] + [0.0])
    subset = g["coverage_mean"] < 0.80
    verdict = ("PASS" if g["pass"] else "FAIL") + ("(子集预读)" if subset else "")
    if g["pass"] and fund_pen >= 0.5: verdict += "+funding渗透"
    RES["candidates"][name] = {"angle": angle, "note": note, "sign": sgn, "S1": {k: v for k, v in g.items() if k != "_dic"}, "S1_flipped_sign": {"dIC_year_mean_of_years": gflip["dIC_year_mean_of_years"], "dIC_by_year": gflip["dIC_by_year"], "pass_would_be": gflip["pass"]},
                             "placebo_dIC_year_mean_5seeds": plc, "placebo_mean": float(np.nanmean(plc)), "corr": corr, "max_abs_corr_funding": fund_pen, "subset_read": subset, "verdict": verdict}
    log(f"{name}: ΔIC {f4(g['dIC_year_mean_of_years'])} by_year {{{', '.join(f'{y}:{v:+.4f}' for y, v in g['dIC_by_year'].items())}}} | cand IC {f4(g['ic_cand']['mean'])} (t {f1(g['ic_cand']['t'])}) | resid IC {f4(g['ic_cand_on_king_resid']['mean'])} (t {f1(g['ic_cand_on_king_resid']['t'])}) | king(same subset) {f4(g['ic_king_same_subset']['mean'])} | cov {g['coverage_mean']:.2f} | flip {f4(gflip['dIC_year_mean_of_years'])} | placebo {f4(np.nanmean(plc))} | ρfund max {fund_pen:.3f} | {verdict}")
RES["receipts"]["R7_placebo_all_negative"] = bool(all(v["placebo_mean"] < 0 for v in RES["candidates"].values()))
# diagnostic: has_spot indicator IC and spot coverage by year
RES["diagnostics"] = {"has_spot_ic": summ(np.array([spear(has_spot[i][U400[i]], r4[i][U400[i]]) for i in range(n)]), yr),
                      "has_spot_frac_by_year": {int(y): float(np.nanmean(has_spot[yr == y][U400[yr == y]])) for y in sorted(set(yr.tolist()))},
                      "spot_symbols_mapped_with_data": int(spot_ok.sum() - (~np.isfinite(sCL).any(0)).sum()) if True else None}
RES["diagnostics"]["spot_symbols_with_any_data"] = int(np.isfinite(sCL).any(0).sum())
# ===================================================================== 5. save + md
RES["meta"] = {"n_anchors": int(n), "smoke": bool(args.smoke), "years": {int(y): int((yr == y).sum()) for y in sorted(set(yr.tolist()))}, "king": "slow_pred_hist_oos (wide slow-LGBM OOS)", "universe": "U400 = meta members ∩ qv4h>=2.5e5"}
json.dump(clean(RES), open(OUT_JSON, "w"), indent=1, ensure_ascii=False)
print("\n| 候选 | 角度 | 符号 | ΔIC 逐年均值 | 逐年 | 单独 IC (t) | 对 king 残差 IC (t) | king IC(同子集) | 覆盖 | 反号 ΔIC | 安慰剂 ΔIC | max|ρ| funding | 判 |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for name, v in RES["candidates"].items():
    g = v["S1"]; by = " / ".join(f"{y}:{x:+.4f}" for y, x in g["dIC_by_year"].items())
    print(f"| {name} | {v['angle']} | {v['sign']:+d} | **{f4(g['dIC_year_mean_of_years'])}** | {by} | {f4(g['ic_cand']['mean'])} ({f1(g['ic_cand']['t'])}) | {f4(g['ic_cand_on_king_resid']['mean'])} ({f1(g['ic_cand_on_king_resid']['t'])}) | {f4(g['ic_king_same_subset']['mean'])} | {g['coverage_mean']:.2f} | {f4(v['S1_flipped_sign']['dIC_year_mean_of_years'])} | {f4(v['placebo_mean'])} | {v['max_abs_corr_funding']:.3f} | {v['verdict']} |")
log("DONE ->", OUT_JSON, "sha", sha(OUT_JSON)[:16])
