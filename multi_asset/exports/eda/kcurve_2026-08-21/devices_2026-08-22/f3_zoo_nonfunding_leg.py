"""F3 · 非 funding zoo 复合腿录取装置(2026-08-22, Session 6737834a-F3)。
PREREG(判据先冻结): multi_asset/exports/eda/PREREG_RESULT_F3_zoo_nonfunding_leg_2026-08-22.md §P
  (§P 段 SHA256 f597e0f90b8a4b7e820802d59d3c839a54797024a60e4c9cc19c565b95051832, commit 2a2b5e9; 本脚本只实现 §P, 不新增判据)。
口径(全部继承 WA 装置 wide_full_caliber_audit.py, 零改动): 1h 收盘网格简单收益 RET=C(T+4h)/C(T)-1, 实盘相位 (T,T+4h];
  逐结算实现 carry; 成本 c×Σ|Δw| 主臂 3.52(并报 4.137/6.23/0.32/6.64); 净@2 = 每锚按 2/Σ|w| 缩放; 42 锚块自助 2000 次; 配对块自助 Δ。
对象: W-b 链(三腿 king/rev24/fund rank-z → 走前 msharpe 900 → 去均值/L1/cap2.5/n → 止损 d30_n2_c42 → EMA α0.1 → 带 2.5e-4)
  以 N 腿泛化版 run_chain_n 重实现; R2 平价收据 = 三腿 d30 权重 ≡ WA wa_weights_Wb_d30.npz (max|Δw|<1e-6) 且 1.668 / 0.664 复现。
第四腿 = 13 非 funding zoo 因子秩等权复合(符号抄 zoo_scan `ic` 列): ALL13 主臂; NOREV24 / ICW / SLOW12 敏感; REV6 / VOL2 / VP5 族诊断(S1 only)。
S1: ΔIC(0.7 z(king)+0.3 z(cand)) − IC(z(king)) 逐锚 Spearman vs RET; 过 = 逐年均值的均值 ≥ +0.003 且逐年 ≥ 0。
S2: 书级 G 族 A15(w4=0.15 固定)vs B0; 去 fund 腿情景 NF15 vs NF0; G0 同形安慰剂(逐锚成员内置换, seed 0-4)。
用法 @jpline: python f3_zoo_nonfunding_leg.py r1 | run | all [--nw 8]
只读输入; 输出 probe_artifacts/f3/。不碰实盘仓, 不调交易 API。
"""
import os, sys, io, json, time, zipfile, glob, hashlib, math, datetime as dt, argparse
import numpy as np
from scipy.stats import rankdata

T0 = time.time()
def log(*a): print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def yr_of(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])

SELF_SHA = sha(os.path.abspath(__file__))
PREREG_SHA = "f597e0f90b8a4b7e820802d59d3c839a54797024a60e4c9cc19c565b95051832"
ROOT = "/mnt/storage/private/work_hsy"
PD = f"{ROOT}/probe_artifacts"; B = f"{ROOT}/pod_backup_2026-08-21"; W3 = f"{ROOT}/w3lane"; WA = f"{PD}/wa"; CSV5M = f"{W3}/wide5m_csv"; DAILY = f"{W3}/wide_daily_aug"
OUT = f"{PD}/f3"; os.makedirs(OUT, exist_ok=True)
H4 = 14400; H1 = 3600
ANN_A = math.sqrt(2190); ANN_D = math.sqrt(365)
COST_MAIN = 3.52
COST_ARMS = {"c3.52": 3.52, "c4.137": 4.137, "c6.23": 6.23, "c0.32": 0.32, "c6.64": 6.64}
A_T0 = int(dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp()); A_T1 = int(dt.datetime(2026, 8, 20, 16, tzinfo=dt.timezone.utc).timestamp())
T_END_MAIN = int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())
INPUTS = {"close1h": f"{WA}/close1h_829.npz", "funding": f"{WA}/funding_829.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz",
          "slow_pred": f"{B}/slow_pred_hist_oos.npy", "wa_weights_Wb_d30": f"{WA}/wa_weights_Wb_d30.npz", "wa_run_json": f"{WA}/wide_full_caliber_audit_run_2026-08-22.json"}

# ───────────────────────────── 复合腿定义(P.2, 冻结)
SIGN = {"f_rev_4h": -1, "f_rev_24h": -1, "f_rev_3d": -1, "f_mom_7d": -1, "f_mom_30d": -1, "f_mom_7d_x24": -1,
        "f_vol_7d": -1, "f_range_24h": -1,
        "f_volq_ratio": -1, "f_amihud_24h": +1, "f_cpos_24h": +1, "f_tbf_24h": +1, "f_asz_24h": -1}
FAM = {"REV6": ["f_rev_4h", "f_rev_24h", "f_rev_3d", "f_mom_7d", "f_mom_30d", "f_mom_7d_x24"], "VOL2": ["f_vol_7d", "f_range_24h"],
       "VP5": ["f_volq_ratio", "f_amihud_24h", "f_cpos_24h", "f_tbf_24h", "f_asz_24h"]}
ALL13 = FAM["REV6"] + FAM["VOL2"] + FAM["VP5"]
ARMS = {"ALL13": ALL13, "NOREV24": [k for k in ALL13 if k != "f_rev_24h"], "SLOW12": [k for k in ALL13 if k != "f_rev_4h"], "REV6": FAM["REV6"], "VOL2": FAM["VOL2"], "VP5": FAM["VP5"]}
STOP = (-0.30, 2, 42); LOOK = 900; ALPHA = 0.1; BAND = 2.5e-4; CAPM = 2.5; PLACEBO_SEEDS = [0, 1, 2, 3, 4]

# ───────────────────────────── helpers(WA 同式)
def read_kline_zip(path, cols=(0, 4, 7)):
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
    except Exception:
        return None
    ot = []; cl = []; qv = []
    for ln in raw.decode("utf-8", "ignore").split("\n"):
        if not ln or ln[0] == "o": continue
        p = ln.split(",")
        try: ot.append(int(p[cols[0]])); cl.append(float(p[cols[1]])); qv.append(float(p[cols[2]]))
        except Exception: continue
    if not ot: return None
    return np.array(ot, np.int64), np.array(cl, np.float64), np.array(qv, np.float64)
def xz(v):
    """截面秩 z ∈ [−0.5, 0.5]: rankdata/(n−1) − 0.5; NaN 保持 NaN(WA 同式)."""
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def xrank(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2: out[ok] = rankdata(v[ok]) / ok.sum() - 0.5 - 0.5 / ok.sum()
    return out
def zsc(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 2 and np.nanstd(v[ok]) > 1e-12: out[ok] = (v[ok] - v[ok].mean()) / v[ok].std()
    return out
def spear(x, y, mn=10):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < mn: return np.nan
    return float(np.corrcoef(rankdata(x[ok]), rankdata(y[ok]))[0, 1])
def sharpe_a(x):
    x = np.asarray(x, float); s = x.std(ddof=1); return float(x.mean() / s * ANN_A) if s > 0 else float("nan")
def agg_daily(x, ts):
    d = (np.asarray(ts) // 86400); ud, inv = np.unique(d, return_inverse=True); out = np.zeros(len(ud)); np.add.at(out, inv, x); return out, ud
def sharpe_d(x, ts):
    y, _ = agg_daily(x, ts); s = y.std(ddof=1); return float(y.mean() / s * ANN_D) if s > 0 else float("nan")
def _blocks(n, Lb, reps, seed):
    rng = np.random.RandomState(seed); nb = n // Lb
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); yield (idx[:, None] * Lb + np.arange(Lb)[None, :]).ravel()
def boot_sharpe_ci(x, Lb=42, reps=2000, seed=11):
    v = np.array([sharpe_a(x[sel]) for sel in _blocks(len(x), Lb, reps, seed)]); return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]
def boot_delta_sharpe(x, y, Lb=42, reps=2000, seed=7):
    n = min(len(x), len(y)); d = np.array([sharpe_a(x[sel]) - sharpe_a(y[sel]) for sel in _blocks(n, Lb, reps, seed)])
    return {"mean": round(float(d.mean()), 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)], "P_gt_0": round(float((d > 0).mean()), 3)}
def boot_delta_mean(x, y, Lb=42, reps=2000, seed=7):
    n = min(len(x), len(y)); dd = x[:n] - y[:n]; d = np.array([dd[sel].mean() for sel in _blocks(n, Lb, reps, seed)])
    return {"mean": round(float(dd.mean()), 4), "CI95": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)], "P_gt_0": round(float((d > 0).mean()), 3)}
def boot_sharpe_minus_meanplacebo(x, P, base, Lb=42, reps=2000, seed=7):
    """G1: ΔSharpe(真 − 基线) − mean_s ΔSharpe(安慰剂_s − 基线) = Sharpe(x) − mean_s Sharpe(P_s); 同块自助."""
    n = len(x); d = np.array([sharpe_a(x[sel]) - np.mean([sharpe_a(p[sel]) for p in P]) for sel in _blocks(n, Lb, reps, seed)])
    pt = sharpe_a(x) - float(np.mean([sharpe_a(p) for p in P]))
    return {"point": round(pt, 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)], "P_gt_0": round(float((d > 0).mean()), 3)}
def maxdd(x_bps):
    nav = np.cumprod(1 + np.asarray(x_bps) / 1e4); return float(-(nav / np.maximum.accumulate(nav) - 1).min())
def es(x, q=0.05): k = max(1, int(len(x) * q)); return float(np.sort(np.asarray(x))[:k].mean())
def quintile_table(x, v):
    v2 = np.where(np.isfinite(v), v, np.nan); edges = np.nanpercentile(v2, [20, 40, 60, 80]); qi = np.digitize(v2, edges)
    return [round(float(x[qi == k].mean()), 3) if (qi == k).any() else None for k in range(5)]
def series_block(x, ts):
    x = np.asarray(x, float); yr = yr_of(ts); yrs = sorted(set(yr.tolist()))
    out = {"n": int(len(x)), "mean_bps": round(float(x.mean()), 4), "sd_bps": round(float(x.std(ddof=1)), 3), "sharpe_anchor": round(sharpe_a(x), 3), "sharpe_daily": round(sharpe_d(x, ts), 3),
           "sharpe_CI95_blk42": boot_sharpe_ci(x), "by_year_mean": {int(y): round(float(x[yr == y].mean()), 3) for y in yrs}, "by_year_sharpe": {int(y): round(sharpe_a(x[yr == y]), 3) for y in yrs},
           "n_years_nonneg_mean": int(sum(1 for y in yrs if x[yr == y].mean() >= 0)), "maxDD": round(maxdd(x), 4), "ES5": round(es(x), 2),
           "sharpe_2022_23": round(sharpe_a(x[yr <= 2023]), 3) if (yr <= 2023).sum() > 10 else None, "sharpe_2024_26": round(sharpe_a(x[yr >= 2024]), 3) if (yr >= 2024).sum() > 10 else None}
    return out

# ───────────────────────────── R1: 因子时间约定(5m zip 重建)
def stage_r1():
    R = {"stage": "r1", "self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); pts = PW["ts"].astype(np.int64); psym = [str(s) for s in PW["symbols"]]
    F4 = PW["f_rev_4h"]; F24 = PW["f_rev_24h"]; prow = {int(t): i for i, t in enumerate(pts)}
    y0 = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp()); y1 = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    anchors = [t for t in pts if y0 <= t < y1]
    out = {}
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"]:
        j = psym.index(sym); files = sorted(glob.glob(f"{CSV5M}/{sym}/*.zip")) + sorted(glob.glob(f"{DAILY}/{sym}/5m/*.zip"))
        ot = []; cl = []
        for f in files:
            r = read_kline_zip(f)
            if r is None: continue
            ot.append(r[0]); cl.append(r[1])
        ot = np.concatenate(ot); cl = np.concatenate(cl); o = np.argsort(ot); ot = ot[o]; cl = cl[o]
        _, first = np.unique(ot, return_index=True); ot = ot[first]; cl = cl[first]
        ct = ot // 1000 + 300                         # 收盘时刻(s)
        r5 = np.concatenate([[np.nan], cl[1:] / cl[:-1] - 1.0])   # r5[i] = bar i 相对前一根(简单)
        # 连续性: 仅在前后 bar 连续(间隔 300s)时有效
        gapok = np.concatenate([[False], np.diff(ct) == 300]); r5 = np.where(gapok, r5, np.nan)
        pos = {int(t): i for i, t in enumerate(ct)}
        cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(r5))]); cf = np.concatenate([[0], np.cumsum(np.isfinite(r5))])
        def wsum(i_end_incl, nbar):           # Σ r5 over bars (i_end−nbar+1 .. i_end), 要求全部有限
            a = i_end_incl - nbar + 1
            if a < 0: return np.nan
            if cf[i_end_incl + 1] - cf[a] < nbar: return np.nan
            return cs[i_end_incl + 1] - cs[a]
        res = {"rev4h": {"a_[T-4h,T-5m]": [], "b_(T-4h,T]": [], "c_(T-4h+5m,T+5m]": []}, "rev24h": {"a": [], "b": [], "c": []}}
        n_used = 0
        for T in anchors:
            iT = pos.get(int(T)); ip = prow.get(int(T))
            if iT is None or ip is None: continue
            fv4 = float(F4[ip, j]); fv24 = float(F24[ip, j])
            if not (np.isfinite(fv4) and np.isfinite(fv24)): continue
            n_used += 1
            for nb, key, fv in ((48, "rev4h", fv4), (288, "rev24h", fv24)):
                a = wsum(iT - 1, nb); b_ = wsum(iT, nb); c = wsum(iT + 1, nb)
                ka, kb, kc = (("a_[T-4h,T-5m]", "b_(T-4h,T]", "c_(T-4h+5m,T+5m]") if key == "rev4h" else ("a", "b", "c"))
                res[key][ka].append(abs(a - fv) if np.isfinite(a) else np.nan); res[key][kb].append(abs(b_ - fv) if np.isfinite(b_) else np.nan); res[key][kc].append(abs(c - fv) if np.isfinite(c) else np.nan)
        out[sym] = {"n_anchors_2024": n_used, **{key: {k: {"median_absdiff": float(np.nanmedian(v)), "mean_absdiff": float(np.nanmean(v)), "frac_lt_1e-4": float(np.nanmean(np.array(v) < 1e-4))} for k, v in d.items()} for key, d in res.items()}}
        log("R1", sym, json.dumps(out[sym])[:400])
    # 判读: 哪个窗口逐锚 |Δ| 中位 < 1e-4
    verdict = {}
    for sym, d in out.items():
        m = {k: v["median_absdiff"] for k, v in d["rev4h"].items()}; best = min(m, key=m.get)
        verdict[sym] = {"rev4h_best_window": best, "rev4h_median": m[best], "rev24h_best": min(d["rev24h"], key=lambda k: d["rev24h"][k]["median_absdiff"])}
    R["per_symbol"] = out; R["verdict"] = verdict
    allbest = set(v["rev4h_best_window"] for v in verdict.values())
    R["causal_ok"] = bool(allbest <= {"a_[T-4h,T-5m]", "b_(T-4h,T]"}) and all(v["rev4h_median"] < 1e-4 for v in verdict.values())
    R["reading"] = "面板因子窗口 = " + "/".join(sorted(allbest)) + (" ⇒ 因果(≤T)" if R["causal_ok"] else " ⇒ ★不因果或不匹配, 停")
    json.dump(R, open(f"{OUT}/f3_r1_factor_timing_2026-08-22.json", "w"), indent=1)
    log("R1 DONE", R["reading"], verdict)
    return R

# ───────────────────────────── 主数据装载(run 阶段; 作为 fork 前全局)
G = {}
def load_all():
    R = {}
    R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}; log("input shas", R["input_sha256"])
    try:
        wa = json.load(open(INPUTS["wa_run_json"])); wsha = wa.get("input_sha256", {})
        R["input_sha_match_WA"] = {k: (R["input_sha256"][k] == wsha.get(k)) for k in ("close1h", "funding", "meta", "panel_v2", "slow_pred")}
        log("R3 input SHA vs WA", R["input_sha_match_WA"])
    except Exception as e:
        R["input_sha_match_WA"] = repr(e)
    Z = np.load(INPUTS["close1h"], allow_pickle=True); hts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; C = Z["close"]; NW = len(syms)
    hpos = {int(t): i for i, t in enumerate(hts)}
    A = np.arange(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1 + 1, H4, dtype=np.int64); nA = len(A); apos = {int(t): i for i, t in enumerate(A)}
    i0 = np.array([hpos[int(t)] for t in A]); i1 = i0 + 4
    with np.errstate(all="ignore"):
        RET = (C[i1] / C[i0] - 1.0).astype(np.float64); LRET = np.log(C[i1] / C[i0])
    RET[~np.isfinite(RET)] = np.nan; LRET[~np.isfinite(LRET)] = np.nan
    del C, Z
    FZ = np.load(INPUTS["funding"], allow_pickle=True); assert np.array_equal(FZ["anchors"].astype(np.int64), A) and [str(s) for s in FZ["symbols"]] == syms
    F = {k: FZ[k] for k in ("fr_sum", "nset", "last_rate", "last_iv", "last_age_h", "cov")}
    MT = np.load(INPUTS["meta"], allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; qvk = MT["qvk"]
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    jp = np.array([pw_row.get(int(t), -1) for t in E_ts]); jp_ok = jp >= 0          # WA 同式: 无面板行的锚整锚跳过(含 LR 不追加)
    PANEL = {k: np.where(jp_ok[:, None], PW[k][np.maximum(jp, 0)], np.nan).astype(np.float32) for k in ALL13 + ["f_rev_24h", "f_fund_ema_v1"]}      # E 对齐 (nE, NW)
    R["E_anchors_without_panel_row"] = {"n": int((~jp_ok).sum()), "first_last": [fmt(E_ts[~jp_ok][0]), fmt(E_ts[~jp_ok][-1])] if (~jp_ok).any() else None}
    SLOW = np.load(INPUTS["slow_pred"])
    ai_E = np.array([apos.get(int(t), -1) for t in E_ts])
    mkt = np.full(len(E_ts), np.nan)
    for j in range(len(E_ts)):
        if ai_E[j] < 0: continue
        v = RET[ai_E[j], members[j]]; v = v[np.isfinite(v)]
        if len(v): mkt[j] = v.mean() * 1e4
    G.update(dict(syms=syms, NW=NW, A=A, apos=apos, RET=RET, LRET=LRET, F=F, E_ts=E_ts, members=members, qvk=qvk, PANEL=PANEL, SLOW=SLOW, ai_E=ai_E, mkt=mkt, nE=len(E_ts), jp_ok=jp_ok))
    log("loaded", "NW", NW, "anchors grid", fmt(A[0]), "->", fmt(A[-1]), "E", fmt(E_ts[0]), "->", fmt(E_ts[-1]), len(E_ts))
    return R

# ───────────────────────────── 复合腿构造(P.2)
def build_composites():
    nE, NW = G["nE"], G["NW"]; members = G["members"]; PANEL = G["PANEL"]; RET = G["RET"]; ai_E = G["ai_E"]
    ZF = {k: np.full((nE, NW), np.nan, np.float32) for k in ALL13}       # s_k·xz(f_k) 成员内
    ICF = np.full((nE, len(ALL13)), np.nan)                                # 逐因子逐锚 IC (供 ICW 走前权重)
    navail = np.zeros(nE, np.int16)
    for j in range(nE):
        m = members[j]; ai = ai_E[j]
        yr_ = xrank(RET[ai, m]) if ai >= 0 else None
        for ki, k in enumerate(ALL13):
            z = xz(PANEL[k][j, m].astype(float)) * SIGN[k]
            ZF[k][j, m] = z
            if np.isfinite(z).sum() >= 10: navail[j] += 1
            if yr_ is not None:
                ok = np.isfinite(z) & np.isfinite(yr_)
                if ok.sum() >= 30: ICF[j, ki] = float(np.corrcoef(z[ok], yr_[ok])[0, 1])
        if j % 3000 == 0: log("composites", j, "/", nE)
    def comp(keys, w=None):
        out = np.full((nE, NW), np.nan, np.float32); need = math.ceil(len(keys) / 2)
        for j in range(nE):
            m = members[j]; Zs = np.stack([ZF[k][j, m] for k in keys]).astype(float)      # (K, nm)
            fin = np.isfinite(Zs); cnt = fin.sum(0)
            ww = np.ones(len(keys)) if w is None else w[j]
            num = (np.where(fin, Zs, 0.0) * ww[:, None]).sum(0); den = (fin * ww[:, None]).sum(0)
            with np.errstate(all="ignore"):
                v = np.where((cnt >= need) & (den > 0), num / den, np.nan)
            out[j, m] = v
        return out
    ZC = {arm: comp(keys) for arm, keys in ARMS.items()}
    # ICW: 走前 900 锚逐因子 IC 均值 (锚 j'≤j−1), 负截 0, 归一; 不足 900 锚等权
    icf0 = np.nan_to_num(ICF); fin = np.isfinite(ICF).astype(float)
    cs = np.concatenate([np.zeros((1, len(ALL13))), np.cumsum(icf0, 0)]); cf = np.concatenate([np.zeros((1, len(ALL13))), np.cumsum(fin, 0)])
    WICW = np.ones((nE, len(ALL13)))
    for j in range(nE):
        a = j - LOOK; b = j     # 窗 [j−900, j−1] ⇒ cs[b] − cs[a]
        if a < 0: continue
        with np.errstate(all="ignore"):
            mu = np.where(cf[b] - cf[a] >= LOOK * 0.5, (cs[b] - cs[a]) / np.maximum(cf[b] - cf[a], 1), 0.0)
        w = np.maximum(mu, 0.0)
        WICW[j] = w / w.sum() if w.sum() > 0 else np.ones(len(ALL13)) / len(ALL13)
    ZC["ICW"] = comp(ALL13, w=WICW)
    # 安慰剂: ALL13 复合逐锚成员内置换
    for s in PLACEBO_SEEDS:
        P = np.full((nE, NW), np.nan, np.float32)
        for j in range(nE):
            m = members[j]; v = ZC["ALL13"][j, m].copy(); rng = np.random.default_rng([s, j]); P[j, m] = v[rng.permutation(len(v))]
        ZC[f"PLACEBO{s}"] = P
    G["ZC"] = ZC; G["ICF"] = ICF; G["WICW"] = WICW; G["navail"] = navail
    meta = {"frac_anchors_all13_available": float((navail == 13).mean()), "navail_hist": {int(k): int(v) for k, v in zip(*np.unique(navail, return_counts=True))},
            "composite_finite_frac_on_members": {arm: float(np.mean([np.isfinite(ZC[arm][j, members[j]]).mean() for j in range(0, nE, 25)])) for arm in ARMS},
            "ICW_weight_mean_by_factor(2022+)": {k: round(float(WICW[G["E_ts"] >= A_T0, i].mean()), 4) for i, k in enumerate(ALL13)},
            "factor_IC_mean_2022+(sign-adjusted, vs true (T,T+4h])": {k: round(float(np.nanmean(ICF[G["E_ts"] >= A_T0, i])), 5) for i, k in enumerate(ALL13)},
            "factor_IC_by_year(sign-adjusted)": {k: {int(y): round(float(np.nanmean(ICF[yr_of(G["E_ts"]) == y, i])), 5) for y in range(2022, 2027)} for i, k in enumerate(ALL13)}}
    log("composites done", json.dumps(meta)[:600])
    return meta

# ───────────────────────────── S1(P.3)
def s1_all():
    E_ts = G["E_ts"]; members = G["members"]; RET = G["RET"]; ai_E = G["ai_E"]; SLOW = G["SLOW"]; ZC = G["ZC"]; PANEL = G["PANEL"]; mkt = G["mkt"]; nA = len(G["A"])
    R24n = -PANEL["f_rev_24h"].astype(float); FE = PANEL["f_fund_ema_v1"].astype(float)
    cands = {**{a: ZC[a] for a in list(ARMS) + ["ICW"]}, **{f"PLACEBO{s}": ZC[f"PLACEBO{s}"] for s in PLACEBO_SEEDS}, "POS_fund_ema_v1": FE, "POS_rev24": R24n}
    sel_j = [j for j in range(len(E_ts)) if E_ts[j] >= A_T0 and ai_E[j] >= 0 and G["jp_ok"][j]]
    yr = yr_of(E_ts[sel_j]); main = E_ts[sel_j] <= T_END_MAIN
    names = list(cands); nC = len(names); n = len(sel_j)
    dic = np.full((nC, n), np.nan); icc = np.full((nC, n), np.nan); icr = np.full((nC, n), np.nan); rho_k = np.full((nC, n), np.nan); rho_r = np.full((nC, n), np.nan); rho_f = np.full((nC, n), np.nan)
    ick = np.full(n, np.nan); icr24 = np.full(n, np.nan); icfe = np.full(n, np.nan)
    offs = {k: np.full((nC, n), np.nan) for k in (-1, 0, 1, 2, 3)}
    for ii, j in enumerate(sel_j):
        m = members[j]; ai = ai_E[j]; K = SLOW[j, m].astype(float); Rr = RET[ai, m]
        base_ok = np.isfinite(K) & np.isfinite(Rr)
        if base_ok.sum() < 30: continue
        rk_all = R24n[j, m]; fe_all = FE[j, m]
        ick[ii] = spear(K[base_ok], Rr[base_ok])
        for ci, nm in enumerate(names):
            cv = cands[nm][j, m].astype(float); mm = base_ok & np.isfinite(cv)
            if mm.sum() < 30: continue
            zk = zsc(np.where(mm, K, np.nan)); zc = zsc(np.where(mm, cv, np.nan))
            if not (np.isfinite(zk[mm]).all() and np.isfinite(zc[mm]).all()): continue
            b = 0.7 * zk + 0.3 * zc
            ik = spear(zk[mm], Rr[mm]); icc[ci, ii] = spear(zc[mm], Rr[mm]); dic[ci, ii] = spear(b[mm], Rr[mm]) - ik
            x = xrank(np.where(mm, K, np.nan))[mm]; y = xrank(np.where(mm, Rr, np.nan))[mm]
            beta = float(np.dot(x, y) / (np.dot(x, x) + 1e-30)); icr[ci, ii] = spear(cv[mm], y - beta * x)
            rho_k[ci, ii] = spear(cv[mm], K[mm]); rho_r[ci, ii] = spear(cv[mm], rk_all[mm]); rho_f[ci, ii] = spear(cv[mm], fe_all[mm])
            for k in offs:
                a2 = ai + k
                if 0 <= a2 < nA: offs[k][ci, ii] = spear(cv[mm], RET[a2, m][mm])
        icr24[ii] = spear(rk_all[base_ok], Rr[base_ok]); icfe[ii] = spear(fe_all[base_ok], Rr[base_ok])
        if ii % 2000 == 0: log("S1", ii, "/", n)
    def bymean(v, mask):
        yrs = sorted(set(yr[mask].tolist())); d = {}
        for y in yrs:
            s = v[mask & (yr == y)]
            if np.isfinite(s).sum() >= 100: d[int(y)] = round(float(np.nanmean(s)), 5)
        return d
    def gate(v, mask):
        by = bymean(v, mask); mean = float(np.mean(list(by.values()))) if by else float("nan")
        return {"by_year": by, "year_mean_of_years": round(mean, 5), "pooled_mean": round(float(np.nanmean(v[mask])), 5), "t_pooled": round(float(np.nanmean(v[mask]) / (np.nanstd(v[mask], ddof=1) + 1e-30) * math.sqrt(np.isfinite(v[mask]).sum())), 2),
                "pass": bool(by and mean >= 0.003 and all(x >= 0 for x in by.values()))}
    mq = mkt[sel_j]; edges = np.nanpercentile(mq[main], [20, 40, 60, 80]); qi = np.digitize(np.where(np.isfinite(mq), mq, np.nan), edges)
    OUT = {"n_anchors": int(n), "n_anchors_main": int(main.sum()), "king_IC": {"main": gate(ick, main), "full": gate(ick, np.ones(n, bool))}, "rev24_leg_IC_main": gate(icr24, main), "fund_ema_v1_IC_main": gate(icfe, main), "cands": {}}
    for ci, nm in enumerate(names):
        OUT["cands"][nm] = {"S1_dIC_main": gate(dic[ci], main), "S1_dIC_full": gate(dic[ci], np.ones(n, bool)), "cand_IC_main": gate(icc[ci], main), "cand_IC_on_king_resid_main": gate(icr[ci], main),
                            "rho_cand_king_xsec_mean": round(float(np.nanmean(rho_k[ci][main])), 4), "rho_cand_rev24leg_xsec_mean": round(float(np.nanmean(rho_r[ci][main])), 4), "rho_cand_fundleg_xsec_mean": round(float(np.nanmean(rho_f[ci][main])), 4),
                            "rho_cand_king_by_year": {int(y): round(float(np.nanmean(rho_k[ci][main & (yr == y)])), 4) for y in range(2022, 2027)},
                            "offset_spectrum_IC(k*4h forward window; k=-1 constructional)": {str(k): round(float(np.nanmean(offs[k][ci][main])), 5) for k in offs},
                            "dIC_by_market_quintile(q0=most_down)": [round(float(np.nanmean(dic[ci][main & (qi == q)])), 5) if (main & (qi == q)).any() else None for q in range(5)]}
    # S1 级安慰剂尺子
    pl = [OUT["cands"][f"PLACEBO{s}"]["S1_dIC_main"]["year_mean_of_years"] for s in PLACEBO_SEEDS]
    OUT["G0_S1_placebo"] = {"year_mean_of_years_per_seed": pl, "mean_abs": round(float(np.mean(np.abs(pl))), 5), "ruler_ok(|mean|<0.001)": bool(abs(float(np.mean(pl))) < 0.001)}
    G["S1_dic_ALL13_series"] = dic[0]; G["S1_sel_ts"] = E_ts[sel_j]
    log("S1 done", {nm: (OUT["cands"][nm]["S1_dIC_main"]["year_mean_of_years"], OUT["cands"][nm]["S1_dIC_main"]["pass"]) for nm in names})
    return OUT

# ───────────────────────────── N 腿权重链(WA run_chain 逐字泛化)
def run_chain_n(leg_names, stop=STOP, wmode=("msharpe",), record_from=None, tag=""):
    E_ts = G["E_ts"]; members = G["members"]; RET = G["RET"]; ai_E = G["ai_E"]; qvk = G["qvk"]; NW = G["NW"]
    SC = {"king": G["SLOW"], "rev24": -G["PANEL"]["f_rev_24h"], "fund": G["PANEL"]["f_fund_ema_v1"]}
    def score(nm, j, m):
        if nm in SC: return SC[nm][j, m].astype(float)
        return G["ZC"][nm][j, m].astype(float)
    nL = len(leg_names); depth, need, cool = stop if stop else (None, 0, 0)
    H = np.zeros(NW); HL = np.zeros((nL, NW)); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    LR = [[] for _ in range(nL)]
    recs = []; W = []; WL = []; WH = []; skipped = 0; nfires = 0
    rf = 0 if record_from is None else record_from
    for j in range(len(E_ts)):
        T = int(E_ts[j]); ai = ai_E[j]
        if ai < 0 or not G["jp_ok"][j]: continue
        m = members[j]
        sc = [score(nm, j, m) for nm in leg_names]
        yv_m = RET[ai, m].astype(float); ok = np.isfinite(yv_m); yv0 = np.where(ok, yv_m, 0.0)
        for li in range(nL):
            z = np.nan_to_num(xz(sc[li])); z = np.where(ok, z, 0.0); z -= (z[ok].mean() if ok.sum() else 0.0); g = np.abs(z).sum()
            LR[li].append(float((z / g * yv0).sum() * 1e4) if g > 1e-9 else 0.0)
        p = len(LR[0]) - 1
        def msh(idx):
            if p >= LOOK:
                r = np.stack([np.array(LR[l][p - LOOK:p]) for l in idx]); shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
                return shp / shp.sum() if shp.sum() > 0 else np.array([1 / len(idx)] * len(idx))
            return np.array([1 / len(idx)] * len(idx))
        if wmode[0] == "msharpe":
            w = msh(list(range(nL)))
        elif wmode[0] == "fixed_last":
            wl = float(wmode[1]); w = np.concatenate([msh(list(range(nL - 1))) * (1.0 - wl), [wl]])
        else:
            raise ValueError(wmode)
        qv4h = np.expm1(np.clip(qvk[j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        zk = np.stack([wk * np.nan_to_num(xz(sc[li])) for li, wk in enumerate(w)])
        if sel.sum() < 80:
            skipped += 1; tgt_k = HL[:, :].copy() * 0; do_trade = False
        else:
            do_trade = True
            zk = np.where(sel[None, :], zk, 0.0); zk = zk - np.where(sel[None, :], zk[:, sel].mean(1, keepdims=True), 0.0)
            wv = zk.sum(0); g = np.abs(wv).sum()
            if g < 1e-9: skipped += 1; do_trade = False
            else:
                zk = zk / g; wv = wv / g; capw = CAPM / max(int(sel.sum()), 1); wc = np.clip(wv, -capw, capw)
                with np.errstate(all="ignore"):
                    f = np.where(np.abs(wv) > 1e-15, wc / wv, 1.0)
                zk = zk * f[None, :]; g2 = np.abs(wc).sum()
                if g2 > 1e-9: zk = zk / g2
                tgt_k = np.zeros((nL, NW)); tgt_k[:, m] = zk
        if do_trade:
            if depth is not None:
                bl = su > j
                if bl.any(): tgt_k[:, bl] = 0.0
            tgt = tgt_k.sum(0)
            sm = H + ALPHA * (tgt - H); trade = sm - H
            keep = np.abs(trade) < BAND
            sm = np.where(keep, H, sm)
            HLn = HL + ALPHA * (tgt_k - HL); HLn = np.where(keep[None, :], HL, HLn)
            H = sm; HL = HLn
        if j >= rf:
            recs.append(T); W.append(H.astype(np.float32)); WL.append(HL.astype(np.float32)); WH.append(w)
        yfull = np.nan_to_num(RET[ai].astype(float))
        nsh = np.where(Pi > 1e-12, H / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all="ignore"):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all="ignore"):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan); dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if depth is not None:
            cand = (np.abs(sh) > 1e-12) & (dep <= depth) & (su <= j)
            cnt = np.where(cand, cnt + 1, 0); fire = cnt >= need
            if fire.any(): su[fire] = j + cool; cnt[fire] = 0; nfires += int(fire.sum())
        Pi = Pi * (1.0 + yfull)
    W = np.stack(W); WL = np.stack(WL)
    assert np.abs(WL.sum(1) - W).max() < 1e-5, "leg decomposition not additive"
    return {"ts": np.array(recs, np.int64), "W": W, "WL": WL, "wh": np.array(WH), "skipped": skipped, "fires": nfires, "legs": list(leg_names)}

# ───────────────────────────── 记账(WA account 泛化)
def account(W, ts, F, RET, LRET, WL=None, leg_names=None, cost_c=COST_MAIN):
    n, NW = W.shape
    R = np.nan_to_num(RET); L = np.nan_to_num(LRET); finR = np.isfinite(RET)
    pnl = (W * R).sum(1) * 1e4; pnl_log = (W * L).sum(1) * 1e4
    conv = pnl - pnl_log
    FR = F["fr_sum"]; carry = (W * FR).sum(1) * 1e4
    Wp = np.vstack([np.zeros((1, NW), W.dtype), W[:-1]]); dW = np.abs(W - Wp); trn = dW.sum(1)
    gross = np.abs(W).sum(1); nheld = (np.abs(W) > 1e-9).sum(1)
    out = {"ts": ts, "pnl": pnl, "pnl_log": pnl_log, "conv": conv, "carry": carry, "trn": trn, "gross": gross, "nheld": nheld, "cost": cost_c * trn,
           "long_pnl": (np.where(W > 0, W, 0) * R).sum(1) * 1e4, "short_pnl": (np.where(W < 0, W, 0) * R).sum(1) * 1e4, "unc_ret": (np.abs(W) * (~finR)).sum(1)}
    with np.errstate(all="ignore"):
        g = np.where(gross > 1e-9, gross, np.nan)
    out["net"] = pnl - carry - out["cost"]; out["net_g2"] = 2.0 * np.nan_to_num(out["net"] / g)
    out["pnl_g2"] = 2.0 * np.nan_to_num(pnl / g); out["carry_g2"] = 2.0 * np.nan_to_num(carry / g); out["cost_g2"] = 2.0 * np.nan_to_num(out["cost"] / g)
    for k, c in COST_ARMS.items():
        out[f"net_g2_{k}"] = 2.0 * np.nan_to_num((pnl - carry - c * trn) / g); out[f"net_{k}"] = pnl - carry - c * trn
    if WL is not None:
        out["legs"] = {}
        dWL = np.abs(WL - np.concatenate([np.zeros((1,) + WL.shape[1:], WL.dtype), WL[:-1]]))
        with np.errstate(all="ignore"):
            share = np.where(dWL.sum(1, keepdims=True) > 1e-15, dWL / dWL.sum(1, keepdims=True), 1.0 / WL.shape[1])
        for k, leg in enumerate(leg_names):
            Wk = WL[:, k, :]
            d = {"pnl": (Wk * R).sum(1) * 1e4, "carry": (Wk * FR).sum(1) * 1e4, "cost": cost_c * (share[:, k, :] * dW).sum(1), "gross": np.abs(Wk).sum(1), "trn_own": np.abs(Wk - np.vstack([np.zeros((1, NW), Wk.dtype), Wk[:-1]])).sum(1)}
            d["net"] = d["pnl"] - d["carry"] - d["cost"]; out["legs"][leg] = d
    return out

def summarize(acc, ts, mkt, tag, yr_mask=None, wh=None, leg_names=None):
    sel = np.ones(len(ts), bool) if yr_mask is None else yr_mask
    t = ts[sel]; yr = yr_of(t); yrs = sorted(set(yr.tolist())); g2 = acc["net_g2"][sel]; ga = acc["net"][sel]
    with np.errstate(all="ignore"):
        gq = np.where(acc["gross"][sel] > 1e-9, acc["gross"][sel], np.nan)
    blk = {"tag": tag, "span": [fmt(t[0]), fmt(t[-1]), int(len(t))], "gross_mean": round(float(acc["gross"][sel].mean()), 4), "nheld_mean": round(float(acc["nheld"][sel].mean()), 1), "turnover_mean": round(float(acc["trn"][sel].mean()), 5),
           "net_at_gross2": series_block(g2, t),
           "net_at_actual_gross": {"mean_bps": round(float(ga.mean()), 4), "sharpe_anchor": round(sharpe_a(ga), 3), "sharpe_CI95_blk42": boot_sharpe_ci(ga), "by_year_sharpe": {int(y): round(sharpe_a(ga[yr == y]), 3) for y in yrs}, "maxDD": round(maxdd(ga), 4)},
           "components_at_gross2": {"pnl": round(float(acc["pnl_g2"][sel].mean()), 4), "carry_paid": round(float(acc["carry_g2"][sel].mean()), 4), "cost": round(float(acc["cost_g2"][sel].mean()), 4), "net": round(float(g2.mean()), 4)},
           "convexity_at_actual": round(float(acc["conv"][sel].mean()), 4),
           "cost_arms_net_g2": {k: {"mean": round(float(acc[f"net_g2_{k}"][sel].mean()), 4), "sharpe": round(sharpe_a(acc[f"net_g2_{k}"][sel]), 3)} for k in COST_ARMS},
           "unc_ret_gross_share_mean": round(float((acc["unc_ret"][sel] / np.maximum(acc["gross"][sel], 1e-9)).mean()), 5)}
    if mkt is not None:
        mk = mkt[sel]; blk["Q4"] = {"mkt_ew_quintiles_net_g2(q0=most_down)": quintile_table(g2, mk), "abs_mkt_quintiles_net_g2(q4=highest)": quintile_table(g2, np.abs(mk))}
    if wh is not None and leg_names is not None:
        blk["leg_weight_mean"] = {leg: round(float(wh[sel][:, k].mean()), 4) for k, leg in enumerate(leg_names)}
        blk["leg_weight_by_year"] = {leg: {int(y): round(float(wh[sel][yr == y, k].mean()), 4) for y in yrs} for k, leg in enumerate(leg_names)}
    if "legs" in acc:
        blk["legs"] = {}
        for leg, d in acc["legs"].items():
            blk["legs"][leg] = {"gross_share": round(float((d["gross"][sel] / np.maximum(acc["gross"][sel], 1e-9)).mean()), 4), "own_turnover_mean": round(float(d["trn_own"][sel].mean()), 5),
                                "pnl_g2": round(float((2 * d["pnl"][sel] / gq).mean()), 4), "carry_paid_g2": round(float((2 * d["carry"][sel] / gq).mean()), 4), "cost_g2": round(float((2 * d["cost"][sel] / gq).mean()), 4), "net_g2": round(float((2 * d["net"][sel] / gq).mean()), 4),
                                "net_sharpe": round(sharpe_a(2 * d["net"][sel] / gq), 3), "price_sharpe": round(sharpe_a(2 * d["pnl"][sel] / gq), 3),
                                "by_year_net_g2": {int(y): round(float((2 * d["net"][sel] / gq)[yr == y].mean()), 3) for y in yrs}}
    return blk

# ───────────────────────────── 任务表(P.4; 全部事前列出)
JOBS = {}
def _add(name, legs, wmode, stop=STOP): JOBS[name] = {"legs": legs, "wmode": wmode, "stop": stop}
_add("B0", ["king", "rev24", "fund"], ("msharpe",)); _add("B0_S0", ["king", "rev24", "fund"], ("msharpe",), None)
_add("NF0", ["king", "rev24"], ("msharpe",)); _add("NF0_S0", ["king", "rev24"], ("msharpe",), None)
_add("A15", ["king", "rev24", "fund", "ALL13"], ("fixed_last", 0.15)); _add("A15_S0", ["king", "rev24", "fund", "ALL13"], ("fixed_last", 0.15), None)
_add("A25", ["king", "rev24", "fund", "ALL13"], ("fixed_last", 0.25)); _add("AM", ["king", "rev24", "fund", "ALL13"], ("msharpe",))
_add("NF15", ["king", "rev24", "ALL13"], ("fixed_last", 0.15)); _add("NF15_S0", ["king", "rev24", "ALL13"], ("fixed_last", 0.15), None)
_add("NF25", ["king", "rev24", "ALL13"], ("fixed_last", 0.25)); _add("NFM", ["king", "rev24", "ALL13"], ("msharpe",))
for arm in ("NOREV24", "ICW", "SLOW12"):
    _add(f"A15_{arm}", ["king", "rev24", "fund", arm], ("fixed_last", 0.15)); _add(f"NF15_{arm}", ["king", "rev24", arm], ("fixed_last", 0.15))
for s in PLACEBO_SEEDS:
    _add(f"A15_PLACEBO{s}", ["king", "rev24", "fund", f"PLACEBO{s}"], ("fixed_last", 0.15)); _add(f"NF15_PLACEBO{s}", ["king", "rev24", f"PLACEBO{s}"], ("fixed_last", 0.15))

def _job(name):
    spec = JOBS[name]; rec_from = int(np.searchsorted(G["E_ts"], A_T0)); t0 = time.time()
    ch = run_chain_n(spec["legs"], stop=spec["stop"], wmode=spec["wmode"], record_from=rec_from, tag=name)
    ts = ch["ts"]; ai = np.array([G["apos"].get(int(t), -1) for t in ts]); ok = (ai >= 0) & (ts >= A_T0)
    ai = ai[ok]; ts = ts[ok]; W = ch["W"][ok]; WL = ch["WL"][ok]; wh = ch["wh"][ok]
    Fsub = {k: G["F"][k][ai] for k in G["F"]}
    acc = account(W, ts, Fsub, G["RET"][ai], G["LRET"][ai], WL=WL, leg_names=spec["legs"])
    mkt_ai = np.full(len(ts), np.nan)
    mrow = {int(t): j for j, t in enumerate(G["E_ts"])}
    for i, t in enumerate(ts):
        j = mrow.get(int(t)); mkt_ai[i] = G["mkt"][j] if j is not None else np.nan
    if name in ("B0", "A15", "NF15", "NF0"):
        np.savez_compressed(f"{OUT}/f3_weights_{name}.npz", ts=ts, W=W, symbols=np.array(G["syms"]), legs=np.array(spec["legs"]), wh=wh)
    out = {"name": name, "legs": spec["legs"], "ts": ts, "acc": acc, "wh": wh, "mkt": mkt_ai, "skipped": ch["skipped"], "fires": ch["fires"], "secs": round(time.time() - t0, 1)}
    if name == "B0": out["W"] = W
    return out

def stage_run(nw=8):
    R = {"session": "6737834a-F3", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "stage": "run", "jobs": list(JOBS)}
    R.update(load_all())
    R["composite_meta"] = build_composites()
    R["S1"] = s1_all()
    json.dump(R, open(f"{OUT}/f3_zoo_nonfunding_leg_2026-08-22_partial_S1.json", "w"), indent=1, default=str)
    from multiprocessing import Pool
    t0 = time.time(); RES = {}
    with Pool(nw) as pool:
        for o in pool.imap_unordered(_job, list(JOBS)):
            RES[o["name"]] = o; log("job", o["name"], o["secs"], "s", "skipped", o["skipped"], "fires", o["fires"], "net@2 sharpe(main)", round(sharpe_a(o["acc"]["net_g2"][o["ts"] <= T_END_MAIN]), 3))
    log("all chains done", round(time.time() - t0, 1), "s")
    # ---- R2 平价
    WZ = np.load(INPUTS["wa_weights_Wb_d30"], allow_pickle=True); wts = WZ["ts"].astype(np.int64); Wa = WZ["W"]
    b0 = RES["B0"]; cm = np.intersect1d(wts, b0["ts"]); ia = np.searchsorted(wts, cm); ib = np.searchsorted(b0["ts"], cm)
    dw = np.abs(Wa[ia].astype(np.float64) - b0["W"][ib].astype(np.float64))
    R["receipt_R2_parity"] = {"n_common": int(len(cm)), "maxabs_dw": float(dw.max()), "mean_abs_dw": float(dw.mean()), "pass(<1e-6)": bool(dw.max() < 1e-6)}
    log("RECEIPT R2 parity", R["receipt_R2_parity"])
    # ---- 汇总
    SUMM = {}; SER = {}
    for nm, o in RES.items():
        ts = o["ts"]; m_main = ts <= T_END_MAIN; yr = yr_of(ts)
        SUMM[nm] = {"2022-01..2026-06": summarize(o["acc"], ts, o["mkt"], nm, yr_mask=m_main, wh=o["wh"], leg_names=o["legs"]),
                    "FULL": summarize(o["acc"], ts, o["mkt"], nm, wh=o["wh"], leg_names=o["legs"]),
                    "2022-23": summarize(o["acc"], ts, o["mkt"], nm, yr_mask=(yr <= 2023), wh=o["wh"], leg_names=o["legs"]),
                    "2024-26": summarize(o["acc"], ts, o["mkt"], nm, yr_mask=(yr >= 2024) & m_main, wh=o["wh"], leg_names=o["legs"]),
                    "skipped": o["skipped"], "fires": o["fires"]}
        for k in ("net_g2", "net_g2_c4.137", "net_g2_c6.23", "pnl_g2", "carry_g2", "cost_g2", "gross", "trn"):
            SER[f"{nm}__{k}"] = o["acc"][k]
        SER[f"{nm}__ts"] = ts
        if o["wh"] is not None: SER[f"{nm}__wh"] = o["wh"]
    R["summary"] = SUMM
    R["receipt_R2_sharpe"] = {"B0_main_net_g2_sharpe": SUMM["B0"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "WA_published": 1.668, "NF0_main": SUMM["NF0"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"], "WA_published_nofund": 0.664}
    # ---- G 族 / Δ
    def common(n1, n2, key):
        a = RES[n1]; b = RES[n2]; cm = np.intersect1d(a["ts"], b["ts"]); cm = cm[cm <= T_END_MAIN]
        return a["acc"][key][np.searchsorted(a["ts"], cm)], b["acc"][key][np.searchsorted(b["ts"], cm)], cm
    def gfam(arm, base, placebo_names=None):
        x4, y4, cm = common(arm, base, "net_g2_c4.137"); x6, y6, _ = common(arm, base, "net_g2_c6.23"); x3, y3, _ = common(arm, base, "net_g2")
        yr = yr_of(cm); by = {int(y): round(float((x4 - y4)[yr == y].mean()), 4) for y in sorted(set(yr.tolist()))}
        d4 = boot_delta_mean(x4, y4); d6 = boot_delta_mean(x6, y6); ds3 = boot_delta_sharpe(x3, y3); ds4 = boot_delta_sharpe(x4, y4)
        out = {"n": int(len(cm)), "dnet@4.137": d4, "dnet@6.23": d6, "dnet@4.137_by_year": by, "n_years_dnet_nonneg": int(sum(v >= 0 for v in by.values())),
               "dSharpe@3.52": ds3, "dSharpe@4.137": ds4, "sharpe_arm@3.52": round(sharpe_a(x3), 3), "sharpe_base@3.52": round(sharpe_a(y3), 3), "sharpe_arm@4.137": round(sharpe_a(x4), 3), "sharpe_base@4.137": round(sharpe_a(y4), 3),
               "corr_arm_base_net_g2": round(float(np.corrcoef(x3, y3)[0, 1]), 4)}
        out["gates"] = {"(i)dnet@4.137_CI_lower>0": bool(d4["CI95"][0] > 0), "(ii)dnet@6.23_mean>=0": bool(d6["mean"] >= 0), "(iii)years_nonneg>=4of5": bool(out["n_years_dnet_nonneg"] >= 4), "(iv)dSharpe@4.137>=0": bool(ds4["mean"] >= 0)}
        if placebo_names:
            P = []; pds = []
            for pn in placebo_names:
                px, py, pcm = common(pn, base, "net_g2_c4.137"); assert len(pcm) == len(cm); P.append(px); pds.append(round(sharpe_a(px) - sharpe_a(py), 3))
            g1 = boot_sharpe_minus_meanplacebo(x4, P, y4)
            out["G0_placebo_dSharpe@4.137_per_seed"] = pds; out["G0_ruler_ok(|mean|<0.10)"] = bool(abs(float(np.mean(pds))) < 0.10)
            out["G1_dSharpe_real_minus_meanplacebo"] = g1; out["gates"]["(v)G1>0_CI_lower>0"] = bool(g1["point"] > 0 and g1["CI95"][0] > 0)
        out["S2_pass_all"] = bool(all(out["gates"].values())) if placebo_names else None
        return out
    R["S2"] = {}
    R["S2"]["A15_vs_B0"] = gfam("A15", "B0", [f"A15_PLACEBO{s}" for s in PLACEBO_SEEDS])
    R["S2"]["A25_vs_B0"] = gfam("A25", "B0"); R["S2"]["AM_vs_B0"] = gfam("AM", "B0"); R["S2"]["A15_S0_vs_B0_S0"] = gfam("A15_S0", "B0_S0")
    R["S2"]["NF15_vs_NF0"] = gfam("NF15", "NF0", [f"NF15_PLACEBO{s}" for s in PLACEBO_SEEDS])
    R["S2"]["NF25_vs_NF0"] = gfam("NF25", "NF0"); R["S2"]["NFM_vs_NF0"] = gfam("NFM", "NF0"); R["S2"]["NF15_S0_vs_NF0_S0"] = gfam("NF15_S0", "NF0_S0")
    R["S2"]["NF15_vs_B0(去fund腿+zoo vs 三腿基线)"] = gfam("NF15", "B0"); R["S2"]["NF0_vs_B0"] = gfam("NF0", "B0")
    for arm in ("NOREV24", "ICW", "SLOW12"):
        R["S2"][f"A15_{arm}_vs_B0"] = gfam(f"A15_{arm}", "B0"); R["S2"][f"NF15_{arm}_vs_NF0"] = gfam(f"NF15_{arm}", "NF0")
    # ---- 去 fund 腿情景阶段判据
    nf = {}
    for nm in ("NF0", "NF15", "NF25", "NFM", "NF15_NOREV24", "NF15_ICW", "NF15_SLOW12"):
        sb = SUMM[nm]["2022-01..2026-06"]["net_at_gross2"]
        nf[nm] = {"sharpe": sb["sharpe_anchor"], "CI95": sb["sharpe_CI95_blk42"], "by_year_sharpe": sb["by_year_sharpe"], "n_years_nonneg_mean": sb["n_years_nonneg_mean"], "maxDD": sb["maxDD"],
                  "stage_target(sharpe>=1.0 & years_nonneg>=4of5)": bool(sb["sharpe_anchor"] >= 1.0 and sb["n_years_nonneg_mean"] >= 4)}
    R["nofund_scenario"] = nf
    R["verdict"] = {"S1_main_ALL13_pass": R["S1"]["cands"]["ALL13"]["S1_dIC_main"]["pass"], "S1_main_ALL13_dIC": R["S1"]["cands"]["ALL13"]["S1_dIC_main"]["year_mean_of_years"],
                    "S2_A15_pass": R["S2"]["A15_vs_B0"]["S2_pass_all"], "G0_book_ruler_ok": R["S2"]["A15_vs_B0"].get("G0_ruler_ok(|mean|<0.10)"),
                    "nofund_NF15_sharpe": nf["NF15"]["sharpe"], "nofund_NF15_stage_target": nf["NF15"]["stage_target(sharpe>=1.0 & years_nonneg>=4of5)"], "R2_parity_pass": R["receipt_R2_parity"]["pass(<1e-6)"]}
    json.dump(R, open(f"{OUT}/f3_zoo_nonfunding_leg_2026-08-22.json", "w"), indent=1, default=str)
    np.savez_compressed(f"{OUT}/f3_series.npz", **SER)
    log("RUN DONE", json.dumps(R["verdict"]))
    return R

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["r1", "run", "all"]); ap.add_argument("--nw", type=int, default=8); a = ap.parse_args()
    if a.stage in ("r1", "all"): stage_r1()
    if a.stage in ("run", "all"): stage_run(a.nw)
