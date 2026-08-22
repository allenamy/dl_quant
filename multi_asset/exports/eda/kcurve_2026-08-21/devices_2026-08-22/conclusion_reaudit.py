"""RC · 结论复审(简单口径 × 实盘相位 × 实测成本)— 净额类结论系统重算 + IC 类结论不变性抽检(2026-08-22, Session 6737834a-RC)。
两阶段同一文件(可重跑):
  `python conclusion_reaudit.py jp [--nproc 14] [--smoke]`  @jpline — 在役管线(SR/PH 装置 replay 逐字同构: legs.compose_book + apply_harvest_ema α0.05
        + 带 b0.002 + 逐名止损 S1(−25%×2 锚/冷却 42)), 实盘相位 p3(ph_preds_2026-08-22.npz, 因果面板五折 OOS), 收益 {log, simple=expm1(Y4)},
        成本 {4.137 主, 3.52 T1 实测, 6.23 上界}; 臂目录见 ARMS(); 写 probe_artifacts/rc/conclusion_reaudit_jp_2026-08-22.{json,npz,log}
  `python conclusion_reaudit.py local`  @本机 — 合并 jp 结果 + 算术类复核(执行蛋糕/84 锚窗/杠杆触线/IC 不变性汇总)→ results/conclusion_reaudit_2026-08-22.json

问题(用户质询): 有了"离线族 Y4 是对数收益"(SR 57038bd: 在役 S1 1.063→0.272 bps/锚, 凸性 −0.83 = 毛 70%, 全在空头山寨侧)与 funding 地基审计(FF 1e2a5df)
的认识, 此前的复杂模型/特征/前沿因子/二阶三阶构造/腿录取 S2/执行蛋糕/保费/换手/杠杆结论会不会反转?

【分类原则(先写, 后套)】
  (a) IC/排序类结论(模型类等价、DL 天花板、三整合、K 曲线、zoo 扫、弹药构造、泄漏审计、特征门 S1): Spearman rank-IC 对严格单调变换 y→expm1(y) 【精确不变】
      (本装置数值验证 max|Δ| 应为 0), Pearson 值 IC 只动 ≤1e-3 ⇒ 预期不反转; 抽 3 类代表(模型分数 IC / 面板因子 IC / 书级 IC)数值复核。
  (b) 净额类结论: 全部在【同一管线】重算(简单收益 + 实盘相位 + 三档成本), 与对数口径并列, 判定 = 不变 / 重表 / 翻转 / 需重跑。
  (c) funding 腿类: 不重算(FF 已在简单口径+实盘相位完成), 只按 FF 结论重标注。

【判据冻结, 先于看数】
  G 族(腿录取 S2 / 干预臂; 逐字继承 rm_build_gate/betaside/volstruct): Δ净@4.137 块自助(5 锚块, 2000 次)CI95 下界>0 且 Δ净@6.23≥0 且 逐年 Δ≥0 ≥4/5 且 净夏普不降 ⇒ PASS; 否则 fail。
  vol-target(逐字继承 vol_target.py): ΔSharpe ≥ +0.10 且 Δ净 CI95 上界>0 且 逐年夏普不差 ≥4/5 且 最差年净额不降 ⇒ PASS。
  映射四臂(逐字继承 map4): G1 Δ净 双档(4.137/6.23)CI 下界>0 · G2 逐年≥80% · G3 净夏普双档更高; 三关全过才取代在役 M3。
  "判定"词表: 不变 = 原判与简单口径判一致且方向一致; 重表 = 判不变但绝对数字改写; 翻转 = 判变(PASS↔fail 或符号变); 需重跑 = 本装置未覆盖/装置缺, 给优先级。
  收据: R1 本装置 LOG 基线 S0/S1 净序列 与 SR npz `mine_p3_LOG_S{0,1}_net` 逐元素 maxabs<1e-9(管线逐字同构); R2 SIM 同(= SR 0.272/0.37 逐位);
        R3 自写 compose_with_cand(w4=0) 与 legs.compose_book 逐锚 maxabs<1e-12(第四槽注入的基底与生产函数同构); R4 RM 原装置路径复现: 候选经 compose_book 第 4 位参数
        (dvol30)= size_dvol_factor(−log) 变换, 与自写 "sizefactor" 变换逐位同(这是原 RM1 S2 判决实际测的腿); 全部输入 SHA256 入 JSON。
  IC 不变性: 逐锚 Spearman(x, y_log) vs Spearman(x, expm1(y_log)) 的 max|Δ| 必须 < 1e-12(定理); Pearson 值 IC |Δ均值| 报出(预期 <1e-3)。
输入(只读): probe_artifacts/{ph_preds_2026-08-22.npz, inrole_sr/inrole_simple_return_rerun_jp_2026-08-22.npz, legs.py, takerflow_factors_panel.npz,
  basis_premium_1h.npz, king/s2_pred_newgen.npz(仅用于构造 PanelSource, 预测立即被 p3 覆盖)}, exports/{wide_dl_full.npz(Y4/CH/member 分数级回放, 与 SR/PH/W2 同),
  rm_channels_v1.npz, w4_liq_proxy_v1.npz}。不碰 share / 实盘仓 / 交易 API; 不写训练目录。
"""
import os, sys, json, time, hashlib, argparse
import numpy as np, pandas as pd

SESSION = "6737834a-RC"
W_LIVE = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB_LIVE = {"alpha": .5, "lambda": 1.}
C_MAIN, C_T1, C_HI = 4.137, 3.52, 6.23
BW = 0.002; COOL = 42; ALPHA_LIVE = 0.05; ANN = np.sqrt(6 * 365)
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"; MA = REPO + "/multi_asset"
OUTD = f"{PD}/rc"
t0 = time.time()
G = {}   # fork-shared globals for workers


def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()


def sharpe_anchor(x):
    x = np.asarray(x, float); s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")


def daily(x, ats):
    d = (np.asarray(ats) // 86400).astype(np.int64)
    u, inv = np.unique(d, return_inverse=True)
    s = np.zeros(len(u)); np.add.at(s, inv, np.nan_to_num(x)); return u, s


def sharpe_daily(x, ats):
    _, s = daily(x, ats); return float(s.mean() / (s.std(ddof=1) + 1e-12) * np.sqrt(365.0))


def summ(x, yr, ats):
    x = np.asarray(x, float)
    return {"mean_bps": round(float(np.nanmean(x)), 4), "sd": round(float(np.nanstd(x, ddof=1)), 3),
            "sharpe_anchor": round(sharpe_anchor(x), 3), "sharpe_daily": round(sharpe_daily(x, ats), 3),
            "by_year_mean": {int(y): round(float(np.nanmean(x[yr == y])), 4) for y in sorted(set(yr.tolist()))},
            "by_year_sharpe_anchor": {int(y): round(sharpe_anchor(x[yr == y]), 3) for y in sorted(set(yr.tolist()))}}


def boot_mean_ci(d, nb=2000, bl=5, seed=41):
    """rm_build_gate/betaside/volstruct 同式: 5 锚块自助, 2000 次, Δ均值 CI95。"""
    rng = np.random.default_rng(seed); L = len(d); k = int(np.ceil(L / bl)); o = np.empty(nb)
    for q in range(nb):
        st = rng.integers(0, max(L - bl, 1), size=k)
        ix = (st[:, None] + np.arange(bl)[None, :]).ravel()[:L]; ix = ix[ix < L]
        o[q] = d[ix].mean()
    return float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))


def gfam(p, t, p0, t0_, yr):
    """G 族判据(Δ净@4.137 CI 下界>0 且 @6.23≥0 且 逐年≥4/5 且 夏普不降)+ 三档成本 Δ。"""
    out = {}
    for c, tag in ((C_MAIN, "4.137"), (C_T1, "3.52"), (C_HI, "6.23")):
        d = (p - t * c) - (p0 - t0_ * c)
        out[f"dnet@{tag}"] = round(float(d.mean()), 4)
        if tag == "4.137":
            lo, hi = boot_mean_ci(d); out["dnet@4.137_CI95"] = [round(lo, 4), round(hi, 4)]
            dfy = pd.Series(d).groupby(yr).mean()
            out["dnet_by_year@4.137"] = {int(k): round(float(v), 4) for k, v in dfy.items()}
            out["n_years_nonneg"] = int((dfy >= 0).sum())
            out["sharpe_arm@4.137"] = round(sharpe_anchor(p - t * c), 3); out["sharpe_base@4.137"] = round(sharpe_anchor(p0 - t0_ * c), 3)
    out["net_arm@4.137"] = round(float((p - t * C_MAIN).mean()), 4); out["net_base@4.137"] = round(float((p0 - t0_ * C_MAIN).mean()), 4)
    out["net_arm@3.52"] = round(float((p - t * C_T1).mean()), 4); out["net_base@3.52"] = round(float((p0 - t0_ * C_T1).mean()), 4)
    out["G_PASS"] = bool(out["dnet@4.137_CI95"][0] > 0 and out["dnet@6.23"] >= 0 and out["n_years_nonneg"] >= 4 and out["sharpe_arm@4.137"] >= out["sharpe_base@4.137"])
    return out


# ====================================================================== composition (legs.compose_book 逐字复刻 + 第四槽)
def compose_with_cand(LG, k, s, f, rv, rb, cand=None, w4=0.0, xform="z", sign=1.0, weights=W_LIVE):
    """legs.compose_book 的逐字复刻(z/rank_centered/SIGNS/l1/cap99/demean/RB/l1), 外加第四槽候选:
    xform='z' ⇒ l1(z(sign·cand))(compose_book size 槽若为恒等变换时的形态, = rm_build_gate 的意图); 'rank' ⇒ l1(rank_centered(sign·cand))(gate_takerflow / breadth2 的形态);
    'sizefactor' ⇒ l1(z(size_dvol_factor(sign·cand)))(= 原 rm_build_gate 实际发生的变换: 候选当 dvol30 传入)。w4=0 时与 LG.compose_book 逐位相同(收据 R3)。"""
    w3 = {kk: vv * (1.0 - w4) for kk, vv in weights.items()}
    legs_unit = {"king": LG.l1(LG.SIGNS["king"] * LG.z(k)), "s2": LG.l1(LG.SIGNS["s2"] * LG.z(s)),
                 "funding": LG.l1(LG.SIGNS["funding"] * LG.rank_centered(f))}
    combo = w3["king"] * legs_unit["king"] + w3["s2"] * legs_unit["s2"] + w3["funding"] * legs_unit["funding"]
    if cand is not None and w4 > 0:
        c = sign * np.asarray(cand, float)
        if xform == "z": cu = LG.l1(LG.z(c))
        elif xform == "rank": cu = LG.l1(LG.rank_centered(c))
        elif xform == "sizefactor": cu = LG.l1(LG.z(LG.size_dvol_factor(np.nan_to_num(c))))
        else: raise ValueError(xform)
        combo = combo + w4 * cu
    mag = np.nan_to_num(np.asarray(combo, float))
    if LG.POS_CAP_PCT and mag.size >= 10 and np.isfinite(mag).any():
        lo = np.nanpercentile(mag, 100 - LG.POS_CAP_PCT); hi = np.nanpercentile(mag, LG.POS_CAP_PCT)
        mag = np.clip(mag, lo, hi)
    shaped = mag - mag.mean()
    if rb and rv is not None:
        _a = float(rb.get("alpha", 1.0)); _l = float(rb.get("lambda", 0.0))
        if not (_a == 1.0 and _l == 0.0):
            _s = np.asarray(rv, float); _fin = np.isfinite(_s) & (_s > 0)
            if _fin.any():
                _med = float(np.median(_s[_fin]))
                if _med > 0:
                    _s = np.where(_fin, _s, _med)
                    _w = np.sign(shaped) * np.abs(shaped) ** _a / np.power(_s / _med, _l)
                    shaped = _w - _w.mean()
    return LG.l1(shaped)


def shrink_long(x, gamma):
    x = np.asarray(x, float).copy(); f = np.isfinite(x)
    if f.sum() < 20: return x
    thr = np.nanpercentile(x[f], 90); hi = f & (x > thr) & (x > 0)
    x[hi] = thr + (x[hi] - thr) * gamma
    return x


def apply_post(w, m, i, post, rv):
    """betaside.transform(bneu/bhalf/acap) · volstruct cap(cap_sym/cap_long) · shortrule(剔最跌40%空头) · majors(大盘剔除/减半) 逐字同构。"""
    kind = post[0]; w = np.asarray(w, float).copy()
    if kind in ("bneu", "bhalf"):
        b = G["BETA"][i][m]; f = np.isfinite(b)
        if f.sum() > 30:
            bf = np.where(f, b, np.nanmean(b[f])); X = np.stack([np.ones(len(w)), bf], 1)
            coef, *_ = np.linalg.lstsq(X, w, rcond=None); proj = X @ coef
            w = w - (proj if kind == "bneu" else 0.5 * proj)
        s1 = np.abs(w).sum()
        if s1 > 0: w = w / s1
    elif kind == "acap":
        p_hi = post[1]; pos = w > 0
        if pos.sum() > 10:
            lim = np.percentile(w[pos], p_hi); w[pos] = np.minimum(w[pos], lim)
        w = w - w.mean(); s1 = np.abs(w).sum()
        if s1 > 0: w = w / s1
    elif kind in ("cap_sym", "cap_long"):
        c = post[1]; sig = np.where(np.isfinite(rv) & (rv > 0), rv, np.nanmedian(rv))
        contrib = np.abs(w) * sig; med = np.nanmedian(contrib[contrib > 0]) if (contrib > 0).any() else 0.0
        if med > 0:
            lim = c * med / sig; over = np.abs(w) > lim
            if kind == "cap_long": over &= (w > 0)
            w = np.where(over, np.sign(w) * lim, w); w = w - np.nanmean(w); s1 = np.abs(w).sum()
            if s1 > 0: w = w / s1
    elif kind == "shortrule":        # RESULT_short_side_rule: 空头里 mom_24h 最跌 40% 置零, 再 demean+L1
        mom = G["MOM24"][i][m]; sh = w < 0
        if sh.sum() > 10:
            thr = np.nanpercentile(mom[sh & np.isfinite(mom)], 40) if np.isfinite(mom[sh]).sum() > 5 else -np.inf
            w[sh & (mom <= thr)] = 0.0
        w = w - w.mean(); s1 = np.abs(w).sum()
        if s1 > 0: w = w / s1
    elif kind in ("majors_excl", "majors_half"):
        mj = np.isin(m, [G["btc_j"], G["eth_j"]])
        w[mj] = 0.0 if kind == "majors_excl" else 0.5 * w[mj]
        w = w - w.mean(); s1 = np.abs(w).sum()
        if s1 > 0: w = w / s1
    else:
        raise ValueError(kind)
    return w


def build_targets(cfg):
    LG = G["LG"]; n = G["n"]; N = G["N"]
    rb = cfg.get("rb", RB_LIVE); cand = cfg.get("cand"); w4 = cfg.get("w4", 0.0)
    xform = cfg.get("cand_xform", "z"); sign = cfg.get("cand_sign", 1.0); king_cad = cfg.get("king_cad", 2)
    shr = cfg.get("shrink_long"); post = cfg.get("post"); origpath = cfg.get("cand_origpath", False)
    TGT = []
    for i in range(n):
        m = G["MSK"][i]; k = G["KH"][i] if king_cad == 2 else G["KF"][i]; s = G["SH"][i]; f = G["FH"][i]; rv = G["RV"][i]
        if shr: k = shrink_long(k, shr); s = shrink_long(s, shr)
        cvec = G["CANDS"][cand][i][m] if cand else None
        if origpath:   # 原 rm_build_gate 路径: 候选作为 dvol30 传入生产 compose_book(size 槽 = z(size_dvol_factor(·)))
            sc = 1.0 - w4; W_ = {"king": W_LIVE["king"] * sc, "s2": W_LIVE["s2"] * sc, "funding": W_LIVE["funding"] * sc, "size": w4}
            r = LG.compose_book(k, s, f, np.nan_to_num(sign * cvec), weights=W_, rvol=rv, risk_budget=rb)
            w = np.asarray(r["target_w"], float)
        else:
            w = compose_with_cand(LG, k, s, f, rv, rb, cvec, w4, xform, sign)
        if post: w = apply_post(w, m, i, post, rv)
        wf = np.zeros(N); wf[m] = w; TGT.append(wf)
    return TGT


def run_book(TGT, RET, stop, alpha=ALPHA_LIVE, band=BW, scale=None, want_W=False):
    """SR/PH replay.run 逐字(EMA α → 止损屏蔽 → 带 b → 记账 → 止损价格路径); 新增 scale(vol-target, EMA 后带前, = vol_target.py 位置)。"""
    LG = G["LG"]; n = G["n"]; N = G["N"]; SYMS = G["SYMS"]; MSK = G["MSK"]
    state = None; prev = np.zeros(N); Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N)
    cnt = np.zeros(N, int); su = np.full(N, -1)
    pnl = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); fires = np.zeros(n, int); ic = np.full(n, np.nan)
    pnl_long = np.zeros(n); pnl_short = np.zeros(n); gross_long = np.zeros(n)
    WS = np.zeros((n, N), np.float32) if want_W else None
    from scipy.stats import rankdata
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, alpha); state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        if scale is not None: tgt = tgt * scale[i]
        if stop:
            bs = set(np.where(su > i)[0].tolist())
            if bs:
                for k2, j in enumerate(m):
                    if j in bs: tgt[k2] = 0.0
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        d = tgt - w[m]; Tm = np.abs(d) > band
        wm = w[m].copy(); wm[Tm] = tgt[Tm]
        if Tm.any(): wm[Tm] -= wm.sum() / Tm.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y); idx = m[ok]
        c = np.zeros(N); c[idx] = w[m][ok] * y[ok] * 1e4
        pnl[i] = c.sum(); trn[i] = float(np.abs(w - prev).sum()); gross[i] = float(np.abs(w).sum())
        pnl_long[i] = c[w > 0].sum(); pnl_short[i] = c[w < 0].sum(); gross_long[i] = float(w[w > 0].sum())
        hv = ok & (np.abs(w[m]) > 1e-12)
        if hv.sum() >= 10:
            ic[i] = np.corrcoef(rankdata(w[m][hv]), rankdata(y[hv]))[0, 1]
        if want_W: WS[i] = w.astype(np.float32)
        nsh = np.where(Pi > 1e-12, w / Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh); add = same & (np.abs(nsh) > np.abs(sh))
        red = same & (~add) & (np.abs(nsh) > 1e-12); new = (~same) | (np.abs(sh) < 1e-12)
        cb = np.where(add, cb + (nsh - sh) * Pi, cb)
        with np.errstate(all='ignore'):
            ratio = np.where(np.abs(sh) > 1e-12, nsh / np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cb = np.where(red, cb * ratio, cb); cb = np.where(new, nsh * Pi, cb); cb = np.where(np.abs(nsh) < 1e-12, 0.0, cb)
        sh = nsh
        with np.errstate(all='ignore'):
            avg = np.where(np.abs(sh) > 1e-12, cb / sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh) * (1.0 - avg / Pi), 0.0)
        if stop:
            thr = np.full(N, -0.25)
            cand = (np.abs(sh) > 1e-12) & (dep <= thr) & (su <= i)
            cnt = np.where(cand, cnt + 1, 0)
            fire = cnt >= 2
            if fire.any(): su[fire] = i + COOL; cnt[fire] = 0; fires[i] = int(fire.sum())
        prev = w; upd = np.zeros(N); upd[idx] = y[ok]; Pi = Pi * (1.0 + upd)
    return dict(pnl=pnl, trn=trn, gross=gross, fires=fires, ic=ic, W=WS, pnl_long=pnl_long, pnl_short=pnl_short, gross_long=gross_long)


def run_arm(cfg):
    tt = time.time()
    TGT = build_targets(cfg)
    RET = G["YL"] if cfg["ret"] == "log" else G["YS"]
    out = {}
    for key, stop in (("S0", False), ("S1", True)):
        if cfg.get("only") and key not in cfg["only"]: continue
        out[key] = run_book(TGT, RET, stop, alpha=cfg.get("alpha", ALPHA_LIVE), band=cfg.get("band", BW),
                            scale=G["SCALES"].get(cfg["scale"]) if cfg.get("scale") else None, want_W=cfg.get("want_W", False))
    print(f"  [arm] {cfg['name']:34s} done {time.time()-tt:5.0f}s", flush=True)
    return cfg["name"], out


# ====================================================================== JP stage
def stage_jp(nproc, smoke):
    for p_ in (PD, MA, MA + "/engine/live", REPO):
        sys.path.insert(0, p_)
    os.makedirs(OUTD, exist_ok=True)
    import legs as LG
    from engine.panel_source import PanelSource
    from scipy.stats import rankdata, spearmanr
    NEWGEN = {"king": f"{PD}/king_pred_newgen.npz", "s2": f"{PD}/s2_pred_newgen.npz"}
    INP = {"ph_preds": f"{PD}/ph_preds_2026-08-22.npz", "sr_npz": f"{PD}/inrole_sr/inrole_simple_return_rerun_jp_2026-08-22.npz",
           "legs.py": f"{PD}/legs.py", "panel": MA + "/exports/wide_dl_full.npz", "rm_channels": MA + "/exports/rm_channels_v1.npz",
           "w4_liq_proxy": MA + "/exports/w4_liq_proxy_v1.npz", "takerflow_panel": f"{PD}/takerflow_factors_panel.npz",
           "basis_premium": f"{PD}/basis_premium_1h.npz", "king_pred_newgen": NEWGEN["king"], "s2_pred_newgen": NEWGEN["s2"]}
    res = {"session": SESSION, "stage": "jp", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "smoke": bool(smoke),
           "script_sha256": sha(os.path.abspath(__file__)), "inputs_sha256": {k: sha(v) for k, v in INP.items()},
           "criteria_frozen": "见文件头【判据冻结】; G 族/vol-target/映射三关逐字继承原装置"}
    log("input shas done")
    src = PanelSource(king=NEWGEN["king"], s2=NEWGEN["s2"])
    P = np.load(INP["ph_preds"], allow_pickle=True)
    assert np.array_equal(np.asarray(src.ts).astype(np.int64), P["ts"].astype(np.int64)), "panel ts mismatch"
    src.king = P["king_p3"].astype(np.float64); src.s2 = P["s2_p3"].astype(np.float64)
    N = src.N; SYMS = [str(s) for s in src.symbols]; ts_all = np.asarray(src.ts).astype(np.int64)
    hrs = pd.to_datetime(ts_all, unit="ms", utc=True).hour.values; nominal_all = ts_all // 1000 + 3600
    FI, RVI = src.fund_idx, src.ch.index("rvol_24h"); MOMI = src.ch.index("mom_24h")
    btc_j = SYMS.index("BTCUSDT"); eth_j = SYMS.index("ETHUSDT") if "ETHUSDT" in SYMS else -1
    lo = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp()); hi = int(pd.Timestamp("2026-07-01", tz="UTC").timestamp())
    trad_any = (src.member & np.isfinite(src.king) & np.isfinite(src.s2)).any(1)
    a = np.where((hrs % 4 == 3) & trad_any & (nominal_all >= lo) & (nominal_all < hi))[0]
    if smoke: a = a[:400]
    n = len(a); ats = nominal_all[a]; yr = pd.to_datetime(ats, unit="s", utc=True).year.to_numpy()
    log(f"anchors n={n} first={pd.to_datetime(ats[0], unit='s', utc=True)} last={pd.to_datetime(ats[-1], unit='s', utc=True)}")
    # ---- per-anchor precompute (p3 相位: 刷新 (ti+1)%8==0 名义 00/08/16Z; s2 (ti+1)%24==0) ----
    MSK, KH, SH, FH, KF, RV, YL, YS, MOM24 = [], [], [], [], [], [], [], [], []
    held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
    for i, t in enumerate(a):
        ti = int(t); m = np.asarray(src.tradeable(ti))
        if m.dtype == bool: m = np.where(m)[0]
        if i == 0 or (ti + 1) % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
        if i == 0 or (ti + 1) % 24 == 0:
            v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
        if i == 0 or (ti + 1) % 8 == 0:
            v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
        MSK.append(m); KH.append(held["k"][m].copy()); SH.append(held["s"][m].copy()); FH.append(held["f"][m].copy())
        KF.append(src.king[ti, m].astype(float)); RV.append(src.CH[ti, m, RVI].astype(float))
        yl = src.Y4[ti, m].astype(float); YL.append(yl); YS.append(np.expm1(yl))
        mv = np.full(N, np.nan); mv[m] = src.CH[ti, m, MOMI].astype(float); MOM24.append(mv)
    log("precompute done")
    # ---- candidates (n,N) ----
    CANDS = {}
    def madz(X):
        df = pd.DataFrame(X); med = df.rolling(180, min_periods=60).median().shift(1)
        mad = (df - med).abs().rolling(180, min_periods=60).median().shift(1)
        return ((df - med) / (1.4826 * mad + 1e-12)).clip(-3, 3).to_numpy()
    def feat_from_hourly(path, fname):
        Z = np.load(path, allow_pickle=True); zts = Z["ts"]; zsyms = list(Z["symbols"]); zfeats = list(Z["feats"]); zd = Z["data"]
        ts2row = {int(t): i for i, t in enumerate(zts)}; sym2col = {s: j for j, s in enumerate(zsyms)}
        col_of = np.array([sym2col.get(s, -1) for s in SYMS]); rows = np.array([ts2row.get(int(e), -1) for e in ats])
        hit = float((rows >= 0).mean()); fi = zfeats.index(fname)
        X = np.full((n, N), np.nan, np.float32); ok = (rows >= 0)[:, None] & (col_of >= 0)[None, :]
        X[:] = zd[np.where(rows >= 0, rows, 0)][:, np.where(col_of >= 0, col_of, 0), fi]; X[~ok] = np.nan
        return X, hit
    X, hit_rm = feat_from_hourly(INP["rm_channels"], "rm1"); CANDS["RM1"] = madz(X)
    X, hit_w4 = feat_from_hourly(INP["w4_liq_proxy"], "f1_4"); CANDS["W4_F1_4h"] = madz(X)
    Ztf = np.load(INP["takerflow_panel"], allow_pickle=True); tfsyms = [str(s) for s in Ztf["symbols"]]; tfts = Ztf["ts"].astype(np.int64)
    tf_row = {int(t): i for i, t in enumerate(tfts)}; tf_col = np.array([tfsyms.index(s) if s in tfsyms else -1 for s in SYMS])
    tf_rows = np.array([tf_row.get(int(ts_all[int(t)]), -1) for t in a]); hit_tf = float((tf_rows >= 0).mean())
    F3 = Ztf["F3_tbr_rev"]; Xtf = np.full((n, N), np.nan)
    okr = tf_rows >= 0; okc = tf_col >= 0
    Xtf[np.ix_(okr, okc)] = F3[np.ix_(tf_rows[okr], tf_col[okc])]; CANDS["TF_F3"] = Xtf
    Zb = np.load(INP["basis_premium"], allow_pickle=True); bts = Zb["ts_hour"].astype(np.int64); bsym = [str(x) for x in Zb["symbols"]]; PREM = Zb["PREM"].astype(np.float64)
    b_row = {int(t): i for i, t in enumerate(bts)}; b_col = np.array([bsym.index(s) if s in bsym else -1 for s in SYMS])
    b_rows = np.array([b_row.get(int(ts_all[int(t)]), -1) for t in a]); hit_b = float((b_rows >= 0).mean())
    BAS = np.full((n, N), np.nan); okr = b_rows >= 0; okc = b_col >= 0
    BAS[np.ix_(okr, okc)] = PREM[np.ix_(b_rows[okr], b_col[okc])]
    def lsq_resid(y, x):
        ok = np.isfinite(y) & np.isfinite(x); r = np.full_like(y, np.nan)
        if ok.sum() < 5: return r
        Xm = np.column_stack([np.ones(ok.sum()), x[ok]]); b, *_ = np.linalg.lstsq(Xm, y[ok], rcond=None); r[ok] = y[ok] - Xm @ b
        return r
    C1 = np.full((n, N), np.nan); C2 = np.full((n, N), np.nan); hc1 = np.zeros(N); hc2 = np.zeros(N)
    for i, t in enumerate(a):
        ti = int(t); m = MSK[i]
        if i == 0 or (ti + 1) % 8 == 0:          # basis 腿 8h 节奏(与 funding 腿同, 预注册)
            b_r = LG.rank_centered(BAS[i, m]); f_r = LG.rank_centered(FH[i])
            v1 = np.zeros(N); v1[m] = -1.0 * b_r; hc1 = v1
            v2 = np.zeros(N); v2[m] = -1.0 * LG.rank_centered(lsq_resid(b_r, f_r)); hc2 = v2
        C1[i] = hc1; C2[i] = hc2
    CANDS["BASIS_C1"] = C1; CANDS["BASIS_C2"] = C2
    res["candidate_alignment"] = {"RM1_hit": hit_rm, "W4_hit": hit_w4, "TF_hit": hit_tf, "BASIS_hit": hit_b,
                                  "finite_frac": {k: float(np.isfinite(v).mean()) for k, v in CANDS.items()}}
    log("candidates", res["candidate_alignment"])
    assert min(hit_rm, hit_w4, hit_tf, hit_b) > 0.95
    # ---- causal rolling beta (betaside 逐字: 上一锚已实现 Y4 对宇宙等权, 180 锚窗, 最少 60) ----
    WIN, MINW = 180, 60
    BETA = np.full((n, N), np.nan); buf_r = np.full((WIN, N), np.nan); buf_m = np.full(WIN, np.nan); ptr = 0; cntb = 0
    for i in range(n):
        if i > 0:
            ti_prev = int(a[i - 1]); m_prev = MSK[i - 1]
            r = np.full(N, np.nan); r[m_prev] = YL[i - 1]
            mk = np.nanmean(r) if np.isfinite(r).sum() > 30 else np.nan
            buf_r[ptr] = r; buf_m[ptr] = mk; ptr = (ptr + 1) % WIN; cntb += 1
        if cntb >= MINW:
            M_ = buf_m[np.isfinite(buf_m)]
            if np.var(M_) > 0:
                mm = np.where(np.isfinite(buf_m), buf_m, 0.0); fin = np.isfinite(buf_r) & np.isfinite(buf_m)[:, None]
                nn = fin.sum(0).astype(float); rz = np.where(fin, buf_r, 0.0); mz = np.where(fin, mm[:, None], 0.0)
                with np.errstate(invalid="ignore", divide="ignore"):
                    cov = (rz * mz).sum(0) / nn - (rz.sum(0) / nn) * (mz.sum(0) / nn); var = (mz ** 2).sum(0) / nn - (mz.sum(0) / nn) ** 2
                    b_ = cov / var
                b_[nn < MINW] = np.nan; BETA[i] = b_
    log("beta done")
    G.update(dict(LG=LG, n=n, N=N, SYMS=SYMS, MSK=MSK, KH=KH, SH=SH, FH=FH, KF=KF, RV=RV, YL=YL, YS=YS, CANDS=CANDS, BETA=BETA,
                  MOM24=MOM24, btc_j=btc_j, eth_j=eth_j, SCALES={}))
    # ---- R3: compose_with_cand(w4=0) == LG.compose_book ----
    mx = 0.0
    for i in range(n):
        m = MSK[i]; r = LG.compose_book(KH[i], SH[i], FH[i], np.ones(len(m)), weights=W_LIVE, rvol=RV[i], risk_budget=RB_LIVE)
        w2 = compose_with_cand(LG, KH[i], SH[i], FH[i], RV[i], RB_LIVE)
        mx = max(mx, float(np.max(np.abs(np.asarray(r["target_w"], float) - w2))))
    res["R3_compose_replica_maxabs"] = mx; res["R3_pass"] = bool(mx < 1e-12); log("R3", mx)
    # ---- R4: 原 rm_build_gate 路径 == sizefactor 变换 (候选当 dvol30 传入) ----
    mx4 = 0.0; nonzero_share = []
    for i in range(0, n, max(1, n // 300)):
        m = MSK[i]; cv = CANDS["RM1"][i][m]; sc = 0.9
        W_ = {"king": W_LIVE["king"] * sc, "s2": W_LIVE["s2"] * sc, "funding": W_LIVE["funding"] * sc, "size": 0.1}
        r = LG.compose_book(KH[i], SH[i], FH[i], np.nan_to_num(cv), weights=W_, rvol=RV[i], risk_budget=RB_LIVE)
        w2 = compose_with_cand(LG, KH[i], SH[i], FH[i], RV[i], RB_LIVE, cv, 0.1, "sizefactor", 1.0)
        mx4 = max(mx4, float(np.max(np.abs(np.asarray(r["target_w"], float) - w2))))
        cz = np.nan_to_num(cv); nonzero_share.append(float((cz > 0).mean()))
    res["R4_origpath_equals_sizefactor_maxabs"] = mx4; res["R4_pass"] = bool(mx4 < 1e-12)
    res["R4_note"] = ("原 rm_build_gate/w4_gate1 的 S2 把候选作为 compose_book 第 4 位参数(dvol30)传入 ⇒ 经 size_dvol_factor = −log(x>0 else NaN) 与 z(NaN→0): "
                      f"madz 候选中 ≤0 的部分(均占 {1-float(np.mean(nonzero_share)):.1%})被置零, >0 部分被 −log 非单调重排 ⇒ 原 S2 测的是被变换过的腿, 不是候选本体。本装置双路并报。")
    log("R4", mx4, res["R4_note"][:80])
    # ---- IC 不变性(定理数值验证 + Pearson 值 IC) ----
    def ic_pair(x, yl, ys):
        ok = np.isfinite(x) & np.isfinite(yl)
        if ok.sum() < 10: return (np.nan,) * 4
        rx = rankdata(x[ok]); s1 = np.corrcoef(rx, rankdata(yl[ok]))[0, 1]; s2 = np.corrcoef(rx, rankdata(ys[ok]))[0, 1]
        p1 = np.corrcoef(x[ok], yl[ok])[0, 1]; p2 = np.corrcoef(x[ok], ys[ok])[0, 1]
        return s1, s2, p1, p2
    ICV = {}
    chn = {"mom_24h": MOMI, "rev_1h": src.ch.index("rev_1h"), "rvol_24h": RVI, "funding_ema": FI, "size_dvol": src.ch.index("size_dvol"), "max_ret_24h": src.ch.index("max_ret_24h")}
    for nm in ["king_p3_fresh", "s2_p3", "composite_fresh_target"] + list(chn.keys()):
        ICV[nm] = np.full((n, 4), np.nan)
    for i, t in enumerate(a):
        ti = int(t); m = MSK[i]; yl = YL[i]; ys = YS[i]
        ICV["king_p3_fresh"][i] = ic_pair(KF[i], yl, ys); ICV["s2_p3"][i] = ic_pair(src.s2[ti, m].astype(float), yl, ys)
        wc = compose_with_cand(LG, KH[i], SH[i], FH[i], RV[i], RB_LIVE); ICV["composite_fresh_target"][i] = ic_pair(wc, yl, ys)
        for nm, ci in chn.items(): ICV[nm][i] = ic_pair(src.CH[ti, m, ci].astype(float), yl, ys)
    res["IC_invariance"] = {nm: {"rankIC_log": round(float(np.nanmean(v[:, 0])), 5), "rankIC_simple": round(float(np.nanmean(v[:, 1])), 5),
                                 "rankIC_maxabs_delta_per_anchor": float(np.nanmax(np.abs(v[:, 1] - v[:, 0]))),
                                 "pearsonIC_log": round(float(np.nanmean(v[:, 2])), 5), "pearsonIC_simple": round(float(np.nanmean(v[:, 3])), 5),
                                 "pearsonIC_delta_mean": round(float(np.nanmean(v[:, 3] - v[:, 2])), 6),
                                 "pearsonIC_by_year_delta": {int(y): round(float(np.nanmean((v[:, 3] - v[:, 2])[yr == y])), 6) for y in sorted(set(yr.tolist()))}}
                            for nm, v in ICV.items()}
    log("IC invariance", {k: (v["rankIC_maxabs_delta_per_anchor"], v["pearsonIC_delta_mean"]) for k, v in res["IC_invariance"].items()})
    # ---- arm catalog ----
    ARMS = []
    def add(name, **kw): ARMS.append(dict(name=name, **kw))
    for r_ in ("log", "simple"):
        R = "LOG" if r_ == "log" else "SIM"
        add(f"base_{R}", ret=r_, want_W=True)
        # S2 候选(第四槽, S0/S1 都跑)
        for cnm, sgn, xf in (("RM1", 1.0, "z"), ("W4_F1_4h", -1.0, "z"), ("TF_F3", 1.0, "rank"), ("BASIS_C1", 1.0, "rank"), ("BASIS_C2", 1.0, "rank")):
            for w4 in (0.05, 0.10):
                add(f"cand_{cnm}_w{w4}_{R}", ret=r_, cand=cnm, w4=w4, cand_sign=sgn, cand_xform=xf)
        for w4 in (0.05, 0.10):
            add(f"cand_RM1orig_w{w4}_{R}", ret=r_, cand="RM1", w4=w4, cand_sign=1.0, cand_origpath=True)
        # 映射 2×2 (在役栈) + 原装置形态(无 EMA/带/止损) + 探索 λ
        for mn, al, lm in (("M0", 1., 0.), ("M1", .5, 0.), ("M2", 1., 1.), ("M3", .5, 1.)):
            rb = None if (al == 1. and lm == 0.) else {"alpha": al, "lambda": lm}
            add(f"map_{mn}_inrole_{R}", ret=r_, rb=rb)
            add(f"map_{mn}_raw_{R}", ret=r_, rb=rb, alpha=1.0, band=0.0, only=("S0",))
        for lm in (1.5, 2.0):
            add(f"map_explore_a0.5_l{lm}_{R}", ret=r_, rb={"alpha": .5, "lambda": lm})
        # 空头 β 五臂(在役栈)
        for nm_, post in (("bneu", ("bneu",)), ("bhalf", ("bhalf",)), ("acap90", ("acap", 90)), ("acap95", ("acap", 95))):
            add(f"beta_{nm_}_{R}", ret=r_, post=post)
        # 波动结构 cap/收缩 + 空头规则 + 大盘剔除
        for nm_, kw in (("cap_sym2", dict(post=("cap_sym", 2))), ("cap_sym3", dict(post=("cap_sym", 3))), ("shrink_long0.5", dict(shrink_long=0.5)),
                        ("shortrule40", dict(post=("shortrule",))), ("majors_excl", dict(post=("majors_excl",))), ("majors_half", dict(post=("majors_half",)))):
            add(f"vs_{nm_}_{R}", ret=r_, **kw)
        # 节奏 × EMA 绝对水平
        for kc in (1, 2):
            for al in (0.3, 0.05):
                add(f"cad{4 if kc == 1 else 8}_a{al}_{R}", ret=r_, king_cad=kc, alpha=al)
    if smoke: ARMS = [x for x in ARMS if x["name"].startswith(("base_", "cand_RM1_w0.1", "cand_RM1orig_w0.1", "map_M0_inrole", "beta_bneu", "cad4_a0.05"))]
    res["n_arms_stage1"] = len(ARMS); log(f"stage-1 arms: {len(ARMS)}")
    from multiprocessing import Pool
    with Pool(nproc) as pool:
        R1 = dict(pool.map(run_arm, ARMS, chunksize=1))
    # ---- vol-target scales from base S0 pnl (vol_target.py 逐字), then stage-2 arms ----
    def mk_scale(sig, lo_):
        med = pd.Series(sig).rolling(360, min_periods=90).median().shift(1); med = med.fillna(pd.Series(sig).median()).to_numpy()
        return np.clip(med / np.maximum(sig, 1e-12), lo_, 1.0)
    V = np.array([float(np.nanmean(rv)) for rv in RV]); Vlag = np.concatenate([[V[0]], V[:-1]])
    rng = np.random.default_rng(3); shuf = mk_scale(Vlag, 0.5).copy(); rng.shuffle(shuf)
    for R in ("LOG", "SIM"):
        p0 = R1[f"base_{R}"]["S0"]["pnl"]
        sig_pnl = pd.Series(p0).rolling(42, min_periods=20).std().shift(1); sig_pnl = sig_pnl.fillna(sig_pnl.median()).to_numpy()
        G["SCALES"][f"V_lo0.5_{R}"] = mk_scale(Vlag, 0.5); G["SCALES"][f"V_lo0.7_{R}"] = mk_scale(Vlag, 0.7)
        G["SCALES"][f"pnl42_lo0.5_{R}"] = mk_scale(sig_pnl, 0.5); G["SCALES"][f"pnl42_lo0.7_{R}"] = mk_scale(sig_pnl, 0.7)
        G["SCALES"][f"placebo_{R}"] = shuf
    ARMS2 = []
    for r_ in ("log", "simple"):
        R = "LOG" if r_ == "log" else "SIM"
        for sk in ("V_lo0.5", "V_lo0.7", "pnl42_lo0.5", "pnl42_lo0.7", "placebo"):
            ARMS2.append(dict(name=f"vt_{sk}_{R}", ret=r_, scale=f"{sk}_{R}"))
    if smoke: ARMS2 = ARMS2[:2]
    res["n_arms_stage2"] = len(ARMS2); log(f"stage-2 arms: {len(ARMS2)}")
    with Pool(min(nproc, len(ARMS2))) as pool:
        R2 = dict(pool.map(run_arm, ARMS2, chunksize=1))
    RA = {**R1, **R2}
    # ---- receipts R1/R2 vs SR ----
    SR = np.load(INP["sr_npz"], allow_pickle=True)
    rec = {}
    if not smoke:
        for R, tag in (("LOG", "mine_p3_LOG"), ("SIM", "mine_p3_SIM")):
            for S in ("S0", "S1"):
                mine = RA[f"base_{R}"][S]["pnl"] - RA[f"base_{R}"][S]["trn"] * C_MAIN
                ref = SR[f"{tag}_{S}_net"]
                rec[f"{R}_{S}"] = {"n_mine": int(len(mine)), "n_sr": int(len(ref)),
                                   "maxabs": float(np.max(np.abs(mine - ref))) if len(mine) == len(ref) else None}
        rec["ats_equal_SR"] = bool(np.array_equal(SR["mine_p3_LOG_ats"].astype(np.int64), ats.astype(np.int64)))
        rec["pass"] = bool(rec["ats_equal_SR"] and all(v["maxabs"] is not None and v["maxabs"] < 1e-9 for k, v in rec.items() if isinstance(v, dict)))
    res["R1R2_vs_SR"] = rec; log("R1/R2", rec)
    # ---- summaries ----
    S = {}
    for nm, out in RA.items():
        S[nm] = {}
        for key, r in out.items():
            S[nm][key] = {"net@4.137": summ(r["pnl"] - r["trn"] * C_MAIN, yr, ats), "net@3.52": summ(r["pnl"] - r["trn"] * C_T1, yr, ats),
                          "net@6.23": summ(r["pnl"] - r["trn"] * C_HI, yr, ats), "pnl_gross": summ(r["pnl"], yr, ats),
                          "pnl_long_side": round(float(r["pnl_long"].mean()), 4), "pnl_short_side": round(float(r["pnl_short"].mean()), 4),
                          "turnover_mean": round(float(r["trn"].mean()), 5), "gross_mean": round(float(r["gross"].mean()), 4),
                          "fires_total": int(r["fires"].sum()), "book_rank_ic_mean": round(float(np.nanmean(r["ic"])), 5)}
    res["arms"] = S
    # ---- G 族判定: 候选/β/vs 臂 vs 同口径基线(S0 与 S1 各自对照); 映射臂 vs M3 同形态; cad/EMA Δ; vt 判据 ----
    V_ = {}
    for R in ("LOG", "SIM"):
        for nm in RA:
            if not nm.endswith("_" + R): continue
            if nm.startswith(("cand_", "beta_", "vs_")):
                for key in ("S0", "S1"):
                    if key in RA[nm]:
                        b = RA[f"base_{R}"][key]; r = RA[nm][key]
                        V_[f"{nm}/{key}"] = gfam(r["pnl"], r["trn"], b["pnl"], b["trn"], yr)
            elif nm.startswith("map_"):
                form = "inrole" if "_inrole_" in nm else ("raw" if "_raw_" in nm else "inrole")
                ref = f"map_M3_{form}_{R}"
                if ref not in RA: continue
                for key in RA[nm]:
                    if key in RA[ref]:
                        b = RA[ref][key]; r = RA[nm][key]
                        d = gfam(r["pnl"], r["trn"], b["pnl"], b["trn"], yr)
                        # map4 三关: G1 双档 CI 下界>0(4.137 与 6.23), G2 逐年≥80%, G3 夏普双档更高
                        d6 = (r["pnl"] - r["trn"] * C_HI) - (b["pnl"] - b["trn"] * C_HI); lo6, hi6 = boot_mean_ci(d6)
                        d["dnet@6.23_CI95"] = [round(lo6, 4), round(hi6, 4)]
                        d["map4_G1"] = bool(d["dnet@4.137_CI95"][0] > 0 and lo6 > 0); d["map4_G2"] = bool(d["n_years_nonneg"] / 5 >= 0.8)
                        d["map4_G3"] = bool(d["sharpe_arm@4.137"] > d["sharpe_base@4.137"] and sharpe_anchor(r["pnl"] - r["trn"] * C_HI) > sharpe_anchor(b["pnl"] - b["trn"] * C_HI))
                        d["map4_all_pass"] = bool(d["map4_G1"] and d["map4_G2"] and d["map4_G3"]); d["ref"] = ref
                        V_[f"{nm}/{key}"] = d
            elif nm.startswith("cad"):
                ref = f"cad8_a0.05_{R}"   # 在役形态
                if ref not in RA: continue
                for key in RA[nm]:
                    b = RA[ref][key]; r = RA[nm][key]; d = gfam(r["pnl"], r["trn"], b["pnl"], b["trn"], yr); d["ref"] = ref; V_[f"{nm}/{key}"] = d
            elif nm.startswith("vt_"):
                for key in RA[nm]:
                    b = RA[f"base_{R}"][key]; r = RA[nm][key]; n0 = b["pnl"] - b["trn"] * C_MAIN; net = r["pnl"] - r["trn"] * C_MAIN
                    d = net - n0; lo_, hi_ = boot_mean_ci(d, seed=7); sh = sharpe_anchor(net); sh0 = sharpe_anchor(n0)
                    dfy = pd.DataFrame({"y": yr, "b": n0, "a": net}).groupby("y")
                    shy = sum(1 for _, g in dfy if (g.a.mean() / g.a.std(ddof=1)) >= (g.b.mean() / g.b.std(ddof=1)) - 1e-12)
                    worst0 = min(g.b.mean() for _, g in dfy); worstA = min(g.a.mean() for _, g in dfy)
                    V_[f"{nm}/{key}"] = {"net_arm": round(float(net.mean()), 4), "net_base": round(float(n0.mean()), 4), "dnet": round(float(d.mean()), 4),
                                         "dnet_CI95": [round(lo_, 4), round(hi_, 4)], "sharpe_arm": round(sh, 3), "sharpe_base": round(sh0, 3), "dSharpe": round(sh - sh0, 3),
                                         "years_sharpe_not_worse": int(shy), "worst_year_base": round(float(worst0), 3), "worst_year_arm": round(float(worstA), 3),
                                         "VT_PASS": bool(sh - sh0 >= 0.10 and hi_ > 0 and shy >= 4 and worstA >= worst0)}
    res["verdicts"] = V_
    # ---- β 归因 / 侧别 / 主导率保费 / 对冲叠加(基线 S1 W) ----
    BD = {}
    Yfull_l = np.full((n, N), np.nan); Yfull_s = np.full((n, N), np.nan)
    for i in range(n): Yfull_l[i, MSK[i]] = YL[i]; Yfull_s[i, MSK[i]] = YS[i]
    alt = np.array([j for j in range(N) if j not in (btc_j, eth_j)])
    Ffund = np.full((n, N), np.nan)
    for i, t in enumerate(a): Ffund[i, MSK[i]] = src.CH[int(t), MSK[i], FI].astype(float)
    f_alt = np.nanmean(Ffund[:, alt], 1); f_btc = Ffund[:, btc_j]; carry = (-(np.nan_to_num(f_alt)) + np.nan_to_num(f_btc)) * 1e4 * 0.5
    for R, Yf in (("LOG", Yfull_l), ("SIM", Yfull_s)):
        Wb = RA[f"base_{R}"]["S1"]["W"].astype(np.float64); net = RA[f"base_{R}"]["S1"]["pnl"] - RA[f"base_{R}"]["S1"]["trn"] * C_MAIN
        rows = []
        for i in range(n):
            m = MSK[i]; w = Wb[i][m]; y = Yf[i][m]; b = BETA[i][m]; ok = np.isfinite(y) & np.isfinite(b)
            if ok.sum() < 30: continue
            mk = np.nanmean(y[np.isfinite(y)]); nb_ = float((w[ok] * b[ok]).sum()); bt = nb_ * mk * 1e4
            L_, S_ = ok & (w > 0), ok & (w < 0)
            rows.append(dict(y=yr[i], netbeta=nb_, beta_pnl=bt, long=float((w[L_] * y[L_]).sum()) * 1e4, short=float((w[S_] * y[S_]).sum()) * 1e4))
        df = pd.DataFrame(rows); g = df.groupby("y").agg(netbeta=("netbeta", "mean"), beta_pnl=("beta_pnl", "sum"), long=("long", "sum"), short=("short", "sum"))
        tot_b = float(df.beta_pnl.sum()); tot = float(df.long.sum() + df.short.sum())
        r_alt = np.nanmean(Yf[:, alt], 1); r_btc = Yf[:, btc_j]; dAS = (r_alt - r_btc) * 1e4; ok = np.isfinite(dAS) & np.isfinite(net)
        beta_as = float(np.polyfit(dAS[ok], net[ok], 1)[0]); corr_as = float(np.corrcoef(dAS[ok], net[ok])[0, 1])
        contrib = beta_as * float(dAS[ok].mean()); share = contrib / float(net[ok].mean()) if abs(float(net[ok].mean())) > 1e-9 else None
        hedge = {}
        for hm in (0.0, 0.25, 0.5, 1.0):
            h = -hm * beta_as            # 叠加 = 书外加 h×(山寨−BTC) 多头叠加, h = hm × |β|(原装置 beta 取负号后 h=hmul*beta)
            x = net + h * dAS + h * carry; xo = x[ok]
            hedge[f"h{hm}"] = {"mean": round(float(xo.mean()), 3), "sharpe": round(sharpe_anchor(xo), 3),
                               "by_year_sharpe": {int(y): round(sharpe_anchor(xo[yr[ok] == y]), 2) for y in sorted(set(yr.tolist()))}}
        BD[R] = {"by_year": {int(k): {kk: round(float(vv), 2) for kk, vv in v.items()} for k, v in g.iterrows()},
                 "beta_term_total_bps": round(tot_b, 1), "total_pnl_bps": round(tot, 1), "beta_term_share": round(tot_b / tot, 4) if abs(tot) > 1e-9 else None,
                 "long_side_total": round(float(df.long.sum()), 1), "short_side_total": round(float(df.short.sum()), 1),
                 "net_beta_mean_w": round(float(df.netbeta.mean()), 4),
                 "altminusbtc": {"beta_net_on_dAS": round(beta_as, 4), "corr": round(corr_as, 4), "dAS_mean_bps": round(float(dAS[ok].mean()), 3),
                                 "contribution_bps_per_anchor": round(contrib, 4), "share_of_net": round(share, 4) if share is not None else None,
                                 "residual_alpha_bps": round(float(net[ok].mean()) - contrib, 4),
                                 "by_year_beta": {int(y): round(float(np.polyfit(dAS[ok & (yr == y)], net[ok & (yr == y)], 1)[0]), 4) for y in sorted(set(yr.tolist()))}},
                 "hedge_overlay": hedge}
    res["beta_and_premium"] = BD; log("beta/premium", {R: (BD[R]["beta_term_share"], BD[R]["altminusbtc"]["share_of_net"]) for R in BD})
    # ---- 触线/杠杆 + 84 锚窗 ----
    def killp(x, gross, seed=11, nb=2000, L_=180):
        rng_ = np.random.default_rng(seed); nblk = len(x) // L_; NY = 2190; nbk = NY // L_ + 1
        hit_peak = 0; hit_start = 0; rets = []
        for _ in range(nb):
            idx = rng_.integers(0, nblk, nbk); path = np.concatenate([x[i * L_:(i + 1) * L_] for i in idx])[:NY] * gross / 1e4
            cum = np.cumprod(1 + path); hit_peak += (cum / np.maximum.accumulate(cum) - 1).min() <= -0.25; hit_start += (cum - 1).min() <= -0.25; rets.append(cum[-1] - 1)
        return {"P_peakDD_le_-25%": round(float(hit_peak) / nb, 4), "P_fromstart_le_-25%": round(float(hit_start) / nb, 4), "annual_median": round(float(np.median(rets)), 4), "annual_p5": round(float(np.percentile(rets, 5)), 4)}
    LV = {}
    for R in ("LOG", "SIM"):
        for key in ("S0", "S1"):
            net = RA[f"base_{R}"][key]["pnl"] - RA[f"base_{R}"][key]["trn"] * C_MAIN
            LV[f"{R}_{key}"] = {f"gross{gx}": killp(net, gx) for gx in (1.0, 2.0, 3.0)}
            cs = np.cumsum(net); roll84 = cs[84:] - cs[:-84]
            LV[f"{R}_{key}"]["win84_frac_positive"] = round(float((roll84 > 0).mean()), 4); LV[f"{R}_{key}"]["win84_mean_bps_gross"] = round(float(roll84.mean()), 2)
    res["leverage_killline_and_84win"] = LV; log("leverage", {k: v["gross2.0"] for k, v in LV.items()})
    # ---- save ----
    ser = {}
    for nm, out in RA.items():
        for key, r in out.items():
            for fld in ("pnl", "trn", "gross", "ic"): ser[f"{nm}_{key}_{fld}"] = r[fld]
    ser["ats"] = ats; ser["yr"] = yr
    for R in ("LOG", "SIM"): ser[f"base_{R}_S1_W"] = RA[f"base_{R}"]["S1"]["W"]
    suf = "_smoke" if smoke else ""
    np.savez_compressed(f"{OUTD}/conclusion_reaudit_jp_2026-08-22{suf}.npz", **ser)
    res["n_anchors"] = int(n); res["first_nominal"] = str(pd.to_datetime(ats[0], unit="s", utc=True)); res["last_nominal"] = str(pd.to_datetime(ats[-1], unit="s", utc=True))
    res["elapsed_s"] = round(time.time() - t0, 1)
    OUT = f"{OUTD}/conclusion_reaudit_jp_2026-08-22{suf}.json"
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log("DONE ->", OUT)


# ====================================================================== LOCAL stage
def stage_local():
    here = os.path.dirname(os.path.abspath(__file__)); RD = f"{here}/results"
    jp = json.load(open(f"{RD}/conclusion_reaudit_jp_2026-08-22.json"))
    res = {"session": SESSION, "stage": "local", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script_sha256": sha(os.path.abspath(__file__)),
           "jp_json_sha256": sha(f"{RD}/conclusion_reaudit_jp_2026-08-22.json"), "jp": jp}
    A = jp["arms"]
    def net(nm, S, c="4.137"): return A[nm][S][f"net@{c}"]["mean_bps"]
    def shp(nm, S, c="4.137"): return A[nm][S][f"net@{c}"]["sharpe_anchor"]
    # 执行蛋糕(RESULT_event_calendar §P: 补单总代价 0.27 bps NAV/锚 @2× = 0.135 bps/单位 gross; T1: 实现缺口 3.52 × 意图换手 3.38% = 0.119 bps/锚 gross)
    pie_nav = 0.27; pie_gross = pie_nav / 2.0; t1_gap = 3.52 * 0.0338
    EX = {}
    for R in ("LOG", "SIM"):
        for c in ("4.137", "3.52"):
            nn = net("base_" + R, "S1", c)
            EX[f"{R}_S1@{c}"] = {"net_bps_per_gross": nn, "net_bps_NAV_at_2x": round(2 * nn, 4),
                                 "pie_topup_0.27NAV_share_of_net": round(pie_nav / (2 * nn), 4) if nn > 0 else None,
                                 "T1_gap_0.119gross_share_of_net": round(t1_gap / nn, 4) if nn > 0 else None,
                                 "capturable_third_share(原判 1/3 可捕获)": round(pie_nav / (2 * nn) / 3, 4) if nn > 0 else None}
    res["execution_pie"] = EX
    res["published_vs_simple"] = {
        "in_role_S1_net@4.137": {"LOG": net("base_LOG", "S1"), "SIM": net("base_SIM", "S1")},
        "in_role_S1_sharpe@4.137": {"LOG": shp("base_LOG", "S1"), "SIM": shp("base_SIM", "S1")},
        "in_role_S1_net@3.52": {"LOG": net("base_LOG", "S1", "3.52"), "SIM": net("base_SIM", "S1", "3.52")},
        "S0_net@4.137": {"LOG": net("base_LOG", "S0"), "SIM": net("base_SIM", "S0")},
        "cad_ema_abs": {nm: {S: {"net@4.137": net(nm, S), "net@3.52": net(nm, S, "3.52"), "sharpe": shp(nm, S), "turnover": A[nm][S]["turnover_mean"]} for S in A[nm]}
                        for nm in A if nm.startswith("cad")}}
    json.dump(res, open(f"{RD}/conclusion_reaudit_2026-08-22.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps({"execution_pie": EX, "published_vs_simple": res["published_vs_simple"]}, indent=1, ensure_ascii=False))
    print("LOCAL DONE ->", f"{RD}/conclusion_reaudit_2026-08-22.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", nargs="?", default="local"); ap.add_argument("--nproc", type=int, default=14); ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.stage == "jp": stage_jp(args.nproc, args.smoke)
    else: stage_local()
