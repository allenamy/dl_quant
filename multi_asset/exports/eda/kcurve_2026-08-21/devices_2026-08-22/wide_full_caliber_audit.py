"""WA · 宽书最深入独立口径审计装置(2026-08-22, Session 6737834a-WA)。
SHA256: 脚本自身 SHA 与全部输入 SHA 在运行时写入结果 JSON(`self_sha256` / `input_sha256`); 文档引用以 JSON 为准。

【独立路径声明】本装置不 import、不调用 w2_wide_replay.py / w2b_common.py / wide_return_source_audit.py / pod_stop_arms*.py /
  engine.replay_fullhist / legs.py 的任何函数。收益从原始 1h K 线 zip(data.binance.vision 月度 + 8 月逐日)自建小时收盘网格重算;
  5m 对照臂从原始 5m zip 重算; 资金费从交易所 fundingRate 月度 zip(s30 缓存 + 本装置补拉 379 名)逐币逐结算重算(按真实结算时刻,
  不用面板 f_fund_now/f_fund_iv); 权重两路: (W-a) 读取现有装置的权重输出 `w2_wide_series.npz::{S0_W,d30_n2_c42_W}` 作为输入;
  (W-b) 本装置按 PREREG_wide_book_assembly §1 规格自行复现整条权重链(三腿 rank-z → 走前 msharpe(900) → 去均值/L1/cap2.5/n →
  止损 d30_n2_c42(EMA 前置零) → EMA α0.1 → 带 2.5e-4), 腿收益与止损价格路径均用本装置 1h 简单收益; 与 W-a 的一致性作为收据报告, 不作结论。
  唯一与现有装置共享的输入 = 信号数据本身(slow LGBM OOS 预测 / 面板 f_rev_24h / f_fund_ema_v1 / meta members / qvk)与在役 S1 权重矩阵。

【冻结定义】(先于看任何数字)
- 锚: 名义 4h 锚 T ∈ {00,04,08,12,16,20}Z; 持仓窗 (T, T+4h]; 仓位向量 w(T) = NAV 份额(Σ|w| = 实际 gross, 宽书 ≈1.37).
- 价格盈亏(交易所记账): pnl_bps = Σ_s w_s(T)·(C_s(T+4h)/C_s(T) − 1)·1e4, C = 1h K 线 close(bar close_time = T−1ms 的 bar); 对数口径仅作凸性对照.
- 资金费(交易所记账): 结算时刻 f(calc_time)∈(T, T+4h] 的费率 r_s(f) 作用于当时持仓 = w_s(T); carry_paid_bps = Σ_s Σ_f w_s(T)·r_s(f)·1e4(正 = 付出);
  每币按其真实结算时刻(1h/2h/4h/8h 周期自然体现), 不做 ×4/iv 平摊; 影子式"预测 carry"(最近一次已结算费率 × 4/iv)仅作对照.
- 成本: cost_bps = c × Σ_s|w_s(T) − w_s(T−4h)| (单向意图换手, NAV 份额); 主臂 c = 3.52(T1 实测全口径 bps/单位意图); 敏感 c ∈ {0.32, 4.137, 6.64, 1.75(纯 maker 费), 2.49(maker 1.75×73% + taker 4.5×27%)}; 影子分层情景b 仅作对照.
- 净额 = pnl − carry_paid − cost. "@实际 gross" = 权重原样; "@gross 2" = 每锚按 2/Σ|w(T)| 缩放(恒定 gross 口径; 成本/carry 同比例).
- 夏普: 锚级 均/σ×√2190 (主) 与 日聚合 ×√365 并报; CI = 42 锚块自助 2000 次(周块), 差值 CI 为配对块自助.
- 最坏五分位 Q4: 等权市场 4h 收益(829 名可得收益均值)五分位中书最差档 / |市场| 最高档 / 书自身最差五分位 / 周块最差五分位.
- 触线: 恒定 gross 2.0, (i) 历史滚动 1 年窗(逐日起点)峰谷回撤 ≤ −25% 的窗口占比 与 自起点 ≤ −25% 占比; (ii) 180 锚块自助 1 年路径 2000 次(W2 同式).
- 凸性项 = Σ w·((C1/C0−1) − ln(C1/C0)) 逐锚, 分多头侧(w>0)/空头侧(w<0).
- 腿级归因(W-b): 权重链逐分量精确可加分解(z_k 经去均值/÷g/cap 同比例缩放/÷g2/止损掩码/EMA 线性/带掩码), Σ_k w_k ≡ w(逐锚断言 <1e-9);
  腿价格 = w_k·ret, 腿 carry = w_k 的持仓 × 自身结算费率, 腿成本 = 名级成本按 |Δw_k|/Σ_j|Δw_j| 分摊.
- 情景: no_fund(w3_fund=0, 其余按 msharpe 份额重归一) / half_fund(w3_fund×0.5 后重归一); 读 Sharpe Δ vs 基线.
- 在役(C): 读 SR 装置 `mine_p3_SIM_W_S1`(在役 S1 简单臂持仓, 实盘相位 [N,N+4h]) × 本装置 1h 简单收益 + 本装置资金费 + c×换手 ⇒ 同口径在役净额;
  复核段 = 2025 年: 本装置 pnl vs SR pnl 逐锚差; 两书相关 = 日聚合净额 Pearson; 最优配权 = 净@2 夏普最大的 w_wide ∈ [0,1](0.05 步), 全样本 + 逐年走前.
【冻结判读】
- 影子对账可信: 27 共同锚 |Δgross| 中位 ≤ 2 bps 且 均值 |Δ| ≤ 1 bps ⇒ "影子记账可信(价格侧)"; carry 按 realized vs predicted 各自报, 差 ≥ 1 bps/锚 记为"预测 carry 偏差".
- 三选一(E): 以 W-b d30 主臂 2022-01→2026-06 共同锚净@2 夏普 S_w 与在役 S1 同口径夏普 S_l 的配对块自助 ΔS: CI 下界 > 0 ⇒ "显著优于"; CI 含 0 ⇒ "传闻级"; 上界 < 0 ⇒ "否".
- 任何一致性锚点对不上照实报, 不调和.
用法 @jpline: python wide_full_caliber_audit.py build1h | build5m | funding | run ; @本机: python3 wide_full_caliber_audit.py shadow
"""
import os, sys, io, json, time, zipfile, hashlib, glob, datetime as dt, math
import numpy as np

T0 = time.time()
def log(*a):
    print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""): h.update(chunk)
    return h.hexdigest()
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def yr_of(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])

SELF_SHA = sha(os.path.abspath(__file__))
ON_JP = os.path.exists("/mnt/storage/private/work_hsy")
if ON_JP:
    PD = "/mnt/storage/private/work_hsy/probe_artifacts"; B = "/mnt/storage/private/work_hsy/pod_backup_2026-08-21"; W3 = "/mnt/storage/private/work_hsy/w3lane"
    WA = f"{PD}/wa"; CSV1H = f"{W3}/wide1h_csv"; CSV5M = f"{W3}/wide5m_csv"; DAILY = f"{W3}/wide_daily_aug"; S30F = f"{W3}/s30/funding"; S30F21 = f"{W3}/s30/hist2021/fund"; WAF = f"{WA}/funding_csv"
    os.makedirs(WA, exist_ok=True)
H4 = 14400; H1 = 3600
ANN_A = math.sqrt(2190); ANN_D = math.sqrt(365)
COST_MAIN = 3.52
COST_ARMS = {"c3.52": 3.52, "c0.32": 0.32, "c4.137": 4.137, "c6.64": 6.64, "c1.75_maker": 1.75, "c2.49_fee27taker": 2.49}
COST_B_TIER = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]   # 影子情景b(对照)
RATE_B = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B_TIER])

# ───────────────────────────────────────────── helpers: raw zip parsing
def read_kline_zip(path, cols=(0, 4, 7)):
    """vision kline zip -> (open_time_ms int64, close float64, quote_vol float64). 跳表头; 空文件 -> 空数组."""
    try:
        with zipfile.ZipFile(path) as z:
            raw = z.read(z.namelist()[0])
    except Exception:
        return None
    txt = raw.decode("utf-8", "ignore")
    lines = txt.split("\n")
    ot = []; cl = []; qv = []
    for ln in lines:
        if not ln or ln[0] == "o": continue   # header 'open_time'
        p = ln.split(",")
        try:
            ot.append(int(p[cols[0]])); cl.append(float(p[cols[1]])); qv.append(float(p[cols[2]]))
        except Exception:
            continue
    if not ot: return None
    return np.array(ot, np.int64), np.array(cl, np.float64), np.array(qv, np.float64)

def panel_symbols():
    return [str(s) for s in np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)["symbols"]]

# ───────────────────────────────────────────── stage build1h
GRID_H0 = int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp())       # 小时网格起点(行 = bar 收盘时刻)
GRID_H1 = int(dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc).timestamp())       # 终点(含)
NH = (GRID_H1 - GRID_H0) // H1 + 1
def _work1h(sym):
    close = np.full(NH, np.nan); qv = np.full(NH, np.nan); nbar = 0; nbad = 0
    files = sorted(glob.glob(f"{CSV1H}/{sym}/*.zip")) + sorted(glob.glob(f"{DAILY}/{sym}/1h/*.zip"))
    for f in files:
        r = read_kline_zip(f)
        if r is None: continue
        ot, cl, q = r
        idx = (ot // 1000 + H1 - GRID_H0) // H1          # 行 = 收盘时刻 = open+1h
        ok = (idx >= 0) & (idx < NH) & ((ot // 1000) % H1 == 0)
        nbad += int((~ok).sum())
        close[idx[ok]] = cl[ok]; qv[idx[ok]] = q[ok]; nbar += int(ok.sum())
    return sym, close, qv, nbar, nbad
def stage_build1h():
    from multiprocessing import Pool
    syms = panel_symbols(); log("build1h symbols", len(syms), "grid", fmt(GRID_H0), "->", fmt(GRID_H1), NH)
    C = np.full((NH, len(syms)), np.nan, np.float64); Q = np.full((NH, len(syms)), np.nan, np.float32); stats = {}
    with Pool(24) as pool:
        for k, (s, c, q, nb, nbad) in enumerate(pool.imap_unordered(_work1h, syms, chunksize=4)):
            j = syms.index(s); C[:, j] = c; Q[:, j] = q; stats[s] = (nb, nbad)
            if k % 100 == 0: log("1h", k, "/", len(syms))
    ts = GRID_H0 + H1 * np.arange(NH, dtype=np.int64)
    np.savez_compressed(f"{WA}/close1h_829.npz", ts=ts, symbols=np.array(syms), close=C, qv=Q)
    cov = np.isfinite(C).mean(0)
    json.dump({"n_syms": len(syms), "grid": [fmt(GRID_H0), fmt(GRID_H1), int(NH)], "bars_total": int(sum(v[0] for v in stats.values())), "bad_rows": int(sum(v[1] for v in stats.values())),
               "syms_no_data": [s for s, v in stats.items() if v[0] == 0], "coverage_mean": float(cov.mean())}, open(f"{WA}/close1h_829_report.json", "w"), indent=1)
    log("build1h DONE", "no-data syms", sum(1 for v in stats.values() if v[0] == 0))

# ───────────────────────────────────────────── stage build5m (450 名: 5m 收盘-收盘 与 Σ简单 5m 两个对照量)
A_T0 = int(dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp()); A_T1 = int(dt.datetime(2026, 8, 20, 16, tzinfo=dt.timezone.utc).timestamp())
def anchors_grid(t0=A_T0, t1=A_T1): return np.arange(t0, t1 + 1, H4, dtype=np.int64)
G5_H0 = A_T0 - 300 * 0; N5 = (A_T1 + H4 - G5_H0) // 300 + 1
def _work5m(sym):
    close = np.full(N5, np.nan)
    files = sorted(glob.glob(f"{CSV5M}/{sym}/*.zip")) + sorted(glob.glob(f"{DAILY}/{sym}/5m/*.zip"))
    for f in files:
        r = read_kline_zip(f)
        if r is None: continue
        ot, cl, _ = r
        idx = (ot // 1000 + 300 - G5_H0) // 300
        ok = (idx >= 0) & (idx < N5) & ((ot // 1000) % 300 == 0)
        close[idx[ok]] = cl[ok]
    A = anchors_grid(); ia = (A - G5_H0) // 300; ib = ia + 48
    valid = (ib < N5)
    r_cc = np.full(len(A), np.nan); r_sum = np.full(len(A), np.nan); r_sumlog = np.full(len(A), np.nan); nfin = np.zeros(len(A), np.int16)
    ret5 = close[1:] / close[:-1] - 1.0          # ret5[i] = bar i+1 的收益(相对前一根)
    ret5 = np.concatenate([[np.nan], ret5])
    fin = np.isfinite(ret5)
    cs = np.concatenate([[0.0], np.cumsum(np.where(fin, ret5, 0.0))]); csl = np.concatenate([[0.0], np.cumsum(np.where(fin, np.log1p(np.where(fin, ret5, 0.0)), 0.0))]); cf = np.concatenate([[0], np.cumsum(fin)])
    for k in np.where(valid)[0]:
        a, b = ia[k], ib[k]
        if np.isfinite(close[a]) and np.isfinite(close[b]): r_cc[k] = close[b] / close[a] - 1.0
        nf = cf[b + 1] - cf[a + 1]; nfin[k] = nf
        if nf > 0: r_sum[k] = cs[b + 1] - cs[a + 1]; r_sumlog[k] = csl[b + 1] - csl[a + 1]
    return sym, r_cc, r_sum, r_sumlog, nfin
def stage_build5m():
    from multiprocessing import Pool
    syms = sorted(os.listdir(CSV5M)); A = anchors_grid(); log("build5m symbols", len(syms), "anchors", len(A), fmt(A[0]), fmt(A[-1]))
    RCC = np.full((len(A), len(syms)), np.nan, np.float32); RSUM = np.full((len(A), len(syms)), np.nan, np.float32); RSL = np.full((len(A), len(syms)), np.nan, np.float32); NF = np.zeros((len(A), len(syms)), np.int16)
    with Pool(24) as pool:
        for k, (s, a, b, c, nf) in enumerate(pool.imap_unordered(_work5m, syms, chunksize=2)):
            j = syms.index(s); RCC[:, j] = a; RSUM[:, j] = b; RSL[:, j] = c; NF[:, j] = nf
            if k % 50 == 0: log("5m", k, "/", len(syms))
    np.savez_compressed(f"{WA}/ret5m_450.npz", anchors=A, symbols=np.array(syms), r_cc=RCC, r_sum=RSUM, r_sumlog=RSL, nfin=NF)
    log("build5m DONE")

# ───────────────────────────────────────────── stage funding
def read_funding_zip(path):
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
    except Exception:
        return []
    out = []
    for ln in raw.decode("utf-8", "ignore").split("\n"):
        if not ln or ln[0] == "c": continue
        p = ln.split(",")
        try:
            out.append((int(p[0]), float(p[1]) if p[1] not in ("", "nan") else np.nan, float(p[2])))
        except Exception:
            continue
    return out
def _workfund(sym):
    files = sorted(glob.glob(f"{S30F}/{sym}/*.zip")) + sorted(glob.glob(f"{S30F21}/{sym}_*.zip")) + sorted(glob.glob(f"{WAF}/{sym}/*.zip"))
    rows = []
    for f in files: rows += read_funding_zip(f)
    if not rows: return sym, None
    arr = np.array(rows, np.float64); arr = arr[np.argsort(arr[:, 0])]
    _, first = np.unique(arr[:, 0].astype(np.int64), return_index=True); arr = arr[first]
    return sym, arr
def stage_funding():
    from multiprocessing import Pool
    syms = panel_symbols(); A = anchors_grid(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1); nA = len(A)
    FRS = np.zeros((nA, len(syms)), np.float32); NSET = np.zeros((nA, len(syms)), np.int8); LRATE = np.full((nA, len(syms)), np.nan, np.float32); LIV = np.full((nA, len(syms)), np.nan, np.float32); LAGE = np.full((nA, len(syms)), np.nan, np.float32)
    COV = np.zeros((nA, len(syms)), bool); span = {}; ivstats = {}
    with Pool(24) as pool:
        for k, (s, arr) in enumerate(pool.imap_unordered(_workfund, syms, chunksize=4)):
            j = syms.index(s)
            if arr is None: continue
            fs = (arr[:, 0] // 1000).astype(np.int64); rate = arr[:, 2]; ivc = arr[:, 1]
            span[s] = [fmt(fs[0]), fmt(fs[-1]), int(len(fs))]
            gaps = np.diff(fs) / 3600.0
            ivstats[s] = {"col_uniq": sorted(set(np.round(ivc[np.isfinite(ivc)]).astype(int).tolist()))[:6], "gap_median_h": float(np.median(gaps)) if len(gaps) else None}
            # 结算归属: f ∈ (T, T+4h]  ⇒ T = ceil(f/4h)*4h − 4h  (f 恰在边界 ⇒ 归前一窗)
            Tw = ((fs - 1) // H4) * H4
            ai = (Tw - A[0]) // H4
            ok = (ai >= 0) & (ai < nA)
            np.add.at(FRS[:, j], ai[ok], rate[ok].astype(np.float32)); np.add.at(NSET[:, j], ai[ok], 1)
            # 最近一次已结算(≤T)费率/周期/龄
            pos = np.searchsorted(fs, A, side="right") - 1
            okp = pos >= 0
            LRATE[okp, j] = rate[pos[okp]]; LAGE[okp, j] = (A[okp] - fs[pos[okp]]) / 3600.0
            ivv = np.where(np.isfinite(ivc), ivc, np.nan)
            # 周期: 优先列值, 缺则由时间差推断(与影子同法: 取最近的 {1,2,4,6,8})
            gap_prev = np.concatenate([[np.nan], gaps])
            ivg = np.array([min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (g if (np.isfinite(g) and 0 < g <= 24) else 8.0))) for g in gap_prev])
            ivuse = np.where(np.isfinite(ivv), ivv, ivg)
            LIV[okp, j] = ivuse[pos[okp]]
            COV[:, j] = (A + H4 >= fs[0]) & (A + H4 <= fs[-1] + 8 * 3600)
            if k % 100 == 0: log("funding", k, "/", len(syms))
    np.savez_compressed(f"{WA}/funding_829.npz", anchors=A, symbols=np.array(syms), fr_sum=FRS, nset=NSET, last_rate=LRATE, last_iv=LIV, last_age_h=LAGE, cov=COV)
    json.dump({"n_syms_with_data": len(span), "span": span, "ivstats": ivstats, "syms_without_data": [s for s in syms if s not in span]}, open(f"{WA}/funding_829_report.json", "w"), indent=1)
    log("funding DONE syms with data", len(span), "without", len(syms) - len(span))

# ───────────────────────────────────────────── metrics
def sharpe_a(x):
    x = np.asarray(x, float); s = x.std(ddof=1); return float(x.mean() / s * ANN_A) if s > 0 else float("nan")
def agg_daily(x, ts):
    d = (np.asarray(ts) // 86400); ud, inv = np.unique(d, return_inverse=True); out = np.zeros(len(ud)); np.add.at(out, inv, x); return out, ud
def sharpe_d(x, ts):
    y, _ = agg_daily(x, ts); s = y.std(ddof=1); return float(y.mean() / s * ANN_D) if s > 0 else float("nan")
def boot_sharpe_ci(x, Lb=42, reps=2000, seed=11):
    rng = np.random.RandomState(seed); n = len(x); nb = n // Lb; vals = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = (idx[:, None] * Lb + np.arange(Lb)[None, :]).ravel(); vals.append(sharpe_a(x[sel]))
    v = np.array(vals); return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]
def boot_delta_sharpe(x, y, Lb=42, reps=2000, seed=7):
    rng = np.random.RandomState(seed); n = min(len(x), len(y)); nb = n // Lb; d = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = (idx[:, None] * Lb + np.arange(Lb)[None, :]).ravel(); d.append(sharpe_a(x[sel]) - sharpe_a(y[sel]))
    d = np.array(d); return {"mean": round(float(d.mean()), 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)], "P_gt_0": round(float((d > 0).mean()), 3)}
def maxdd(x_bps):
    nav = np.cumprod(1 + np.asarray(x_bps) / 1e4); return float(-(nav / np.maximum.accumulate(nav) - 1).min())
def trip_hist(x_bps, L=2190, step=6):
    """历史滚动 1 年窗: 峰谷回撤 ≤ −25% / 自起点 ≤ −25% 的窗口占比(逐日起点)."""
    x = np.asarray(x_bps) / 1e4; n = len(x)
    if n < L: return {"n_windows": 0}
    lr = np.log1p(x); cs = np.concatenate([[0.0], np.cumsum(lr)])
    hp = hs = 0; cnt = 0
    for i in range(0, n - L + 1, step):
        seg = cs[i:i + L + 1] - cs[i]; nav = np.exp(seg); dd = nav / np.maximum.accumulate(nav) - 1
        hp += dd.min() <= -0.25; hs += nav.min() <= 0.75; cnt += 1
    return {"n_windows": cnt, "P_peakDD_-25%": round(hp / cnt, 4), "P_fromstart_-25%": round(hs / cnt, 4)}
def trip_boot(x_bps, Lb=180, reps=2000, seed=11, L=2190):
    x = np.asarray(x_bps) / 1e4; rng = np.random.RandomState(seed); nb = len(x) // Lb; nbk = L // Lb + 1; hp = hs = 0; ann = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nbk); path = np.concatenate([x[i * Lb:(i + 1) * Lb] for i in idx])[:L]
        cum = np.cumprod(1 + path); dd = cum / np.maximum.accumulate(cum) - 1
        hp += dd.min() <= -0.25; hs += cum.min() <= 0.75; ann.append(cum[-1] - 1)
    return {"P_peakDD_-25%": round(hp / reps, 4), "P_fromstart_-25%": round(hs / reps, 4), "ann_median": round(float(np.median(ann)), 3), "ann_p5": round(float(np.percentile(ann, 5)), 3)}
def es(x, q=0.05): k = max(1, int(len(x) * q)); return float(np.sort(np.asarray(x))[:k].mean())
def quintile_table(x, v):
    v2 = np.where(np.isfinite(v), v, np.nan); edges = np.nanpercentile(v2, [20, 40, 60, 80]); qi = np.digitize(v2, edges)
    return [round(float(x[qi == k].mean()), 3) for k in range(5)]
def series_block(x, ts, G_note=""):
    """标准读数块: 均值/夏普(锚/日)/CI/逐年/最坏五分位(自身)/maxDD/ES/触线."""
    x = np.asarray(x, float); yr = yr_of(ts); yrs = sorted(set(yr.tolist()))
    out = {"n": int(len(x)), "mean_bps": round(float(x.mean()), 4), "sd_bps": round(float(x.std(ddof=1)), 3), "sharpe_anchor": round(sharpe_a(x), 3), "sharpe_daily": round(sharpe_d(x, ts), 3),
           "sharpe_CI95_blk42": boot_sharpe_ci(x), "by_year_mean": {int(y): round(float(x[yr == y].mean()), 3) for y in yrs}, "by_year_sharpe": {int(y): round(sharpe_a(x[yr == y]), 3) for y in yrs},
           "own_worst_quintile_mean": round(float(np.sort(x)[:max(1, len(x) // 5)].mean()), 3), "maxDD": round(maxdd(x), 4), "ES5": round(es(x), 2), "ES1": round(es(x, 0.01), 2),
           "sharpe_2022_23": round(sharpe_a(x[yr <= 2023]), 3), "sharpe_2024_26": round(sharpe_a(x[yr >= 2024]), 3), "trip_hist_1y": trip_hist(x), "trip_boot_1y": trip_boot(x)}
    # 周块最差五分位
    nb = len(x) // 42; bl = x[:nb * 42].reshape(nb, 42).sum(1); out["weekly_block_worst_quintile_mean"] = round(float(np.sort(bl)[:max(1, nb // 5)].mean()), 2)
    return out

# ───────────────────────────────────────────── W-b 权重链(自行复现)
def xz(v):
    """截面秩 z ∈ [−0.5, 0.5], 与规格同: rankdata/(n−1) − 0.5; NaN 保持 NaN."""
    from scipy.stats import rankdata
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def run_chain(D, RET, stop=None, w3_mode="base", tag="", record_from=None, parity_y4=None):
    """D: dict(E_ts, members, SLOW, R24, FE, qvk, pw_row, NW, apos(锚->RET 行)); RET: (nA_grid, NW) 简单收益(腿收益/ok/止损路径皆用它; parity_y4 给出则三处改用 meta y4).
    返回 W (n_rec, NW) 与 WL (n_rec, 3, NW) 腿分量, 对应锚 ts, 及 w3 序列/跳过计数."""
    NW = D["NW"]; alpha = 0.1; band = 2.5e-4; capm = 2.5; look = 900
    depth, need, cool = stop if stop else (None, 0, 0)
    H = np.zeros(NW); HL = np.zeros((3, NW)); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW); cnt = np.zeros(NW, int); su = np.full(NW, -1)
    LR = {"king": [], "rev24": [], "fund": []}
    recs = []; W = []; WL = []; W3 = []; skipped = 0; nfires = 0; fires_ts = []
    E_ts = D["E_ts"]; rf = 0 if record_from is None else record_from
    for j in range(len(E_ts)):
        T = int(E_ts[j]); jp = D["pw_row"].get(T); ai = D["apos"].get(T)
        if jp is None or ai is None: continue
        m = D["members"][j]
        sc = {"king": D["SLOW"][j, m], "rev24": -D["R24"][jp, m], "fund": D["FE"][jp, m]}
        yv_m = (parity_y4[j, m] if parity_y4 is not None else RET[ai, m]).astype(float)
        ok = np.isfinite(yv_m); yv0 = np.where(ok, yv_m, 0.0)
        # 腿纯价格收益(供 msharpe)
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= (z[ok].mean() if ok.sum() else 0.0); g = np.abs(z).sum()
            LR[leg].append(float((z / g * yv0).sum() * 1e4) if g > 1e-9 else 0.0)
        p = len(LR["king"]) - 1
        if p >= look:
            r = np.stack([np.array(LR[l][p - look:p]) for l in ("king", "rev24", "fund")]); shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
            w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            w3 = np.array([1 / 3] * 3)
        if w3_mode == "no_fund":
            w3 = np.array([w3[0], w3[1], 0.0]); w3 = w3 / w3.sum() if w3.sum() > 0 else np.array([0.5, 0.5, 0.0])
        elif w3_mode == "half_fund":
            w3 = np.array([w3[0], w3[1], 0.5 * w3[2]]); w3 = w3 / w3.sum()
        qv4h = np.expm1(np.clip(D["qvk"][j, m], 0, 30)) * 48
        sel = ok & (qv4h >= 2.5e5)
        zk = np.stack([wk * np.nan_to_num(xz(sc[l])) for wk, l in zip(w3, ("king", "rev24", "fund"))])      # (3, nm)
        if sel.sum() < 80:
            skipped += 1; tgt_k = HL[:, :].copy() * 0; do_trade = False       # 无目标: 持仓不动
        else:
            do_trade = True
            zk = np.where(sel[None, :], zk, 0.0); zk = zk - np.where(sel[None, :], zk[:, sel].mean(1, keepdims=True), 0.0)
            w = zk.sum(0); g = np.abs(w).sum()
            if g < 1e-9: skipped += 1; do_trade = False
            else:
                zk = zk / g; w = w / g; capw = capm / max(int(sel.sum()), 1); wc = np.clip(w, -capw, capw)
                with np.errstate(all="ignore"):
                    f = np.where(np.abs(w) > 1e-15, wc / w, 1.0)
                zk = zk * f[None, :]; g2 = np.abs(wc).sum()
                if g2 > 1e-9: zk = zk / g2
                tgt_k = np.zeros((3, NW)); tgt_k[:, m] = zk
        if do_trade:
            if depth is not None:
                bl = su > j
                if bl.any(): tgt_k[:, bl] = 0.0
            tgt = tgt_k.sum(0)
            sm = H + alpha * (tgt - H); trade = sm - H
            keep = np.abs(trade) < band
            sm = np.where(keep, H, sm)
            HLn = HL + alpha * (tgt_k - HL); HLn = np.where(keep[None, :], HL, HLn)
            H = sm; HL = HLn
        # 记账行(持仓 H 在 (T,T+4h] 持有)
        if j >= rf:
            recs.append(T); W.append(H.astype(np.float32)); WL.append(HL.astype(np.float32)); W3.append(w3)
        # 止损记账(成本均价深度, 价格路径 = RET 全名)
        yfull = np.nan_to_num((parity_y4[j] if parity_y4 is not None else RET[ai]).astype(float))
        if parity_y4 is not None:
            yf = np.zeros(NW); yf[m] = yv0; yfull = yf
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
            if fire.any(): su[fire] = j + cool; cnt[fire] = 0; nfires += int(fire.sum()); fires_ts.append((T, int(fire.sum())))
        Pi = Pi * (1.0 + yfull)
        if j % 3000 == 0: log(tag, "chain", j, "/", len(E_ts))
    W = np.stack(W); WL = np.stack(WL)
    assert np.abs(WL.sum(1) - W).max() < 1e-5, "leg decomposition not additive"
    return {"ts": np.array(recs, np.int64), "W": W, "WL": WL, "w3": np.array(W3), "skipped": skipped, "fires": nfires, "fires_ts": fires_ts}

# ───────────────────────────────────────────── 记账(任意权重矩阵 → 逐锚序列)
def account(W, ts, F, RET, LRET, qv_tier=None, WL=None, cost_c=COST_MAIN):
    """W (n, NW) 持仓; ts (n,) 锚; F = funding dict(fr_sum,nset,last_rate,last_iv,last_age_h,cov, apos); RET/LRET (n, NW) 简单/对数收益(已对齐到 ts)."""
    n, NW = W.shape
    R = np.nan_to_num(RET); L = np.nan_to_num(LRET); finR = np.isfinite(RET)
    pnl = (W * R).sum(1) * 1e4; pnl_log = (W * L).sum(1) * 1e4
    conv = pnl - pnl_log; conv_long = (np.where(W > 0, W, 0) * (R - L)).sum(1) * 1e4; conv_short = (np.where(W < 0, W, 0) * (R - L)).sum(1) * 1e4
    unc_ret = (np.abs(W) * (~finR)).sum(1)
    FR = F["fr_sum"]; carry = (W * FR).sum(1) * 1e4          # 正 = 付出
    lr = np.nan_to_num(F["last_rate"]); iv = np.where(np.isfinite(F["last_iv"]) & (F["last_iv"] > 0), F["last_iv"], 8.0); age = F["last_age_h"]
    fresh = np.isfinite(age) & (age <= 12.0)
    carry_pred = (W * np.where(fresh, lr, 0.0) * (4.0 / iv)).sum(1) * 1e4
    unc_carry = (np.abs(W) * (~F["cov"])).sum(1)
    Wp = np.vstack([np.zeros((1, NW), W.dtype), W[:-1]]); dW = np.abs(W - Wp); trn = dW.sum(1)
    gross = np.abs(W).sum(1); nheld = (np.abs(W) > 1e-9).sum(1)
    long_pnl = (np.where(W > 0, W, 0) * R).sum(1) * 1e4; short_pnl = (np.where(W < 0, W, 0) * R).sum(1) * 1e4
    out = {"ts": ts, "pnl": pnl, "pnl_log": pnl_log, "conv": conv, "conv_long": conv_long, "conv_short": conv_short, "carry": carry, "carry_pred": carry_pred, "unc_ret": unc_ret, "unc_carry": unc_carry,
           "trn": trn, "gross": gross, "nheld": nheld, "long_pnl": long_pnl, "short_pnl": short_pnl, "cost": cost_c * trn}
    for k, c in COST_ARMS.items(): out[f"cost_{k}"] = c * trn
    if qv_tier is not None:
        out["cost_tierb"] = (dW * RATE_B[qv_tier]).sum(1)
    out["net"] = pnl - carry - out["cost"]
    with np.errstate(all="ignore"):
        g = np.where(gross > 1e-9, gross, np.nan)
    out["net_pg"] = np.nan_to_num(out["net"] / g); out["net_g2"] = 2.0 * out["net_pg"]
    out["pnl_g2"] = 2.0 * np.nan_to_num(pnl / g); out["carry_g2"] = 2.0 * np.nan_to_num(carry / g); out["cost_g2"] = 2.0 * np.nan_to_num(out["cost"] / g)
    if WL is not None:
        out["legs"] = {}
        dWL = np.abs(WL - np.concatenate([np.zeros((1,) + WL.shape[1:], WL.dtype), WL[:-1]]))   # (n,3,NW)
        with np.errstate(all="ignore"):
            share = np.where(dWL.sum(1, keepdims=True) > 1e-15, dWL / dWL.sum(1, keepdims=True), 1 / 3)
        for k, leg in enumerate(("king", "rev24", "fund")):
            Wk = WL[:, k, :]
            out["legs"][leg] = {"pnl": (Wk * R).sum(1) * 1e4, "carry": (Wk * FR).sum(1) * 1e4, "cost": cost_c * (share[:, k, :] * dW).sum(1), "gross": np.abs(Wk).sum(1),
                                "conv": (Wk * (R - L)).sum(1) * 1e4}
            out["legs"][leg]["net"] = out["legs"][leg]["pnl"] - out["legs"][leg]["carry"] - out["legs"][leg]["cost"]
    return out

def summarize(acc, ts, mkt, tag, yr_mask=None):
    """从 account() 输出生成读数块(净@2 为主, 另报 @实际 gross, 成本臂, 凸性, carry 预测 vs 实现)."""
    sel = np.ones(len(ts), bool) if yr_mask is None else yr_mask
    t = ts[sel]; yr = yr_of(t); yrs = sorted(set(yr.tolist()))
    g2 = acc["net_g2"][sel]; ga = acc["net"][sel]
    blk = {"tag": tag, "span": [fmt(t[0]), fmt(t[-1]), int(len(t))], "gross_mean": round(float(acc["gross"][sel].mean()), 4), "nheld_mean": round(float(acc["nheld"][sel].mean()), 1), "turnover_mean": round(float(acc["trn"][sel].mean()), 5),
           "net_at_gross2": series_block(g2, t), "net_at_actual_gross": {"mean_bps": round(float(ga.mean()), 4), "sharpe_anchor": round(sharpe_a(ga), 3), "sharpe_daily": round(sharpe_d(ga, t), 3), "sharpe_CI95_blk42": boot_sharpe_ci(ga), "by_year_mean": {int(y): round(float(ga[yr == y].mean()), 3) for y in yrs}, "by_year_sharpe": {int(y): round(sharpe_a(ga[yr == y]), 3) for y in yrs}, "maxDD_at_actual": round(maxdd(ga), 4)},
           "components_at_gross2": {"pnl": round(float(acc["pnl_g2"][sel].mean()), 4), "carry_paid": round(float(acc["carry_g2"][sel].mean()), 4), "cost": round(float(acc["cost_g2"][sel].mean()), 4), "net": round(float(g2.mean()), 4)},
           "components_at_actual": {"pnl": round(float(acc["pnl"][sel].mean()), 4), "pnl_log": round(float(acc["pnl_log"][sel].mean()), 4), "carry_paid": round(float(acc["carry"][sel].mean()), 4), "carry_pred_shadowstyle": round(float(acc["carry_pred"][sel].mean()), 4), "cost": round(float(acc["cost"][sel].mean()), 4), "net": round(float(ga.mean()), 4),
                                    "long_pnl": round(float(acc["long_pnl"][sel].mean()), 4), "short_pnl": round(float(acc["short_pnl"][sel].mean()), 4)},
           "convexity_at_actual": {"total": round(float(acc["conv"][sel].mean()), 4), "frac_of_log_pnl": round(float(acc["conv"][sel].mean() / acc["pnl_log"][sel].mean()), 3) if abs(acc["pnl_log"][sel].mean()) > 1e-9 else None,
                                   "long_side": round(float(acc["conv_long"][sel].mean()), 4), "short_side": round(float(acc["conv_short"][sel].mean()), 4),
                                   "by_year": {int(y): round(float(acc["conv"][sel][yr == y].mean()), 3) for y in yrs}, "by_year_long": {int(y): round(float(acc["conv_long"][sel][yr == y].mean()), 3) for y in yrs}, "by_year_short": {int(y): round(float(acc["conv_short"][sel][yr == y].mean()), 3) for y in yrs}},
           "carry": {"realized_paid_mean": round(float(acc["carry"][sel].mean()), 4), "pred_shadowstyle_mean": round(float(acc["carry_pred"][sel].mean()), 4), "corr_real_pred": round(float(np.corrcoef(acc["carry"][sel], acc["carry_pred"][sel])[0, 1]), 3),
                     "by_year_realized": {int(y): round(float(acc["carry"][sel][yr == y].mean()), 3) for y in yrs}, "by_year_pred": {int(y): round(float(acc["carry_pred"][sel][yr == y].mean()), 3) for y in yrs},
                     "unc_carry_gross_share_mean": round(float((acc["unc_carry"][sel] / np.maximum(acc["gross"][sel], 1e-9)).mean()), 4), "unc_carry_by_year": {int(y): round(float((acc["unc_carry"][sel] / np.maximum(acc["gross"][sel], 1e-9))[yr == y].mean()), 4) for y in yrs}},
           "unc_ret_gross_share_mean": round(float((acc["unc_ret"][sel] / np.maximum(acc["gross"][sel], 1e-9)).mean()), 5),
           "cost_arms_net_g2_sharpe": {}, "cost_arms_net_g2_mean": {}}
    with np.errstate(all="ignore"):
        gq = np.where(acc["gross"][sel] > 1e-9, acc["gross"][sel], np.nan)
    for k in COST_ARMS:
        ng = 2.0 * np.nan_to_num((acc["pnl"][sel] - acc["carry"][sel] - acc[f"cost_{k}"][sel]) / gq)
        blk["cost_arms_net_g2_sharpe"][k] = round(sharpe_a(ng), 3); blk["cost_arms_net_g2_mean"][k] = round(float(ng.mean()), 4)
    if "cost_tierb" in acc:
        ng = 2.0 * np.nan_to_num((acc["pnl"][sel] - acc["carry"][sel] - acc["cost_tierb"][sel]) / gq)
        blk["cost_arms_net_g2_sharpe"]["tier_b_shadow"] = round(sharpe_a(ng), 3); blk["cost_arms_net_g2_mean"]["tier_b_shadow"] = round(float(ng.mean()), 4)
    ng_pred = 2.0 * np.nan_to_num((acc["pnl"][sel] - acc["carry_pred"][sel] - acc["cost"][sel]) / gq)
    blk["net_g2_if_pred_carry"] = {"mean": round(float(ng_pred.mean()), 4), "sharpe_anchor": round(sharpe_a(ng_pred), 3)}
    if mkt is not None:
        mk = mkt[sel]
        blk["Q4"] = {"mkt_ew_quintiles_net_g2(q0=most_down)": quintile_table(g2, mk), "abs_mkt_quintiles_net_g2(q4=highest)": quintile_table(g2, np.abs(mk))}
    if "legs" in acc:
        blk["legs"] = {}
        for leg, d in acc["legs"].items():
            with np.errstate(all="ignore"):
                gq2 = gq
            blk["legs"][leg] = {"gross_share": round(float((d["gross"][sel] / np.maximum(acc["gross"][sel], 1e-9)).mean()), 3),
                                "pnl_g2": round(float((2 * d["pnl"][sel] / gq2).mean()), 4), "carry_paid_g2": round(float((2 * d["carry"][sel] / gq2).mean()), 4), "cost_g2": round(float((2 * d["cost"][sel] / gq2).mean()), 4), "net_g2": round(float((2 * d["net"][sel] / gq2).mean()), 4),
                                "net_sharpe": round(sharpe_a(2 * d["net"][sel] / gq2), 3), "price_sharpe": round(sharpe_a(2 * d["pnl"][sel] / gq2), 3), "conv_g2": round(float((2 * d["conv"][sel] / gq2).mean()), 4),
                                "by_year_net_g2": {int(y): round(float((2 * d["net"][sel] / gq2)[yr == y].mean()), 3) for y in yrs}, "by_year_net_sharpe": {int(y): round(sharpe_a((2 * d["net"][sel] / gq2)[yr == y]), 3) for y in yrs}}
    return blk

# ───────────────────────────────────────────── stage run
def stage_run():
    R = {"session": "6737834a-WA", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "stage": "run"}
    INPUTS = {"close1h": f"{WA}/close1h_829.npz", "ret5m": f"{WA}/ret5m_450.npz", "funding": f"{WA}/funding_829.npz", "meta": f"{B}/wide_fea_hist_meta.npz", "panel_v2": f"{B}/wide_panel_4h_hist_v2.npz",
              "slow_pred": f"{B}/slow_pred_hist_oos.npy", "w2_wide_series": f"{PD}/w2_wide_series.npz", "nets_S0": f"{B}/nets_histv2_0_0_0.npy", "nets_d30": f"{B}/nets_histv2_-30_2_42.npy",
              "inrole_sr_npz": f"{PD}/inrole_sr/inrole_simple_return_rerun_jp_2026-08-22.npz", "close1h_report": f"{WA}/close1h_829_report.json", "funding_report": f"{WA}/funding_829_report.json"}
    R["input_sha256"] = {k: (sha(v) if os.path.exists(v) else None) for k, v in INPUTS.items()}; log("input shas done")
    # ---- 1h grid → anchor returns
    Z = np.load(INPUTS["close1h"], allow_pickle=True); hts = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; C = Z["close"]; QV = Z["qv"]; NW = len(syms)
    hpos = {int(t): i for i, t in enumerate(hts)}
    A = anchors_grid(int(dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc).timestamp()), A_T1); nA = len(A); apos = {int(t): i for i, t in enumerate(A)}
    i0 = np.array([hpos[int(t)] for t in A]); i1 = i0 + 4
    with np.errstate(all="ignore"):
        RET = (C[i1] / C[i0] - 1.0).astype(np.float64); LRET = np.log(C[i1] / C[i0])
    RET[~np.isfinite(RET)] = np.nan; LRET[~np.isfinite(LRET)] = np.nan
    # 7 日均 4h 成交额(分层成本对照用): 1h qv 滚动 168h 均 ×4
    qv7 = np.full((nA, NW), np.nan, np.float32)
    cq = np.concatenate([np.zeros((1, NW)), np.cumsum(np.nan_to_num(QV.astype(np.float64)), 0)]); cf = np.concatenate([np.zeros((1, NW)), np.cumsum(np.isfinite(QV), 0)])
    a0 = np.maximum(i0 - 168, 0)
    with np.errstate(all="ignore"):
        qv7 = ((cq[i0 + 1] - cq[a0]) / np.maximum(cf[i0 + 1] - cf[a0], 1) * 4).astype(np.float32)
    tier = np.full((nA, NW), 2, np.int8); tier[np.isfinite(qv7) & (qv7 >= 1e6)] = 1; tier[np.isfinite(qv7) & (qv7 >= 5e6)] = 0
    log("returns grid", RET.shape, fmt(A[0]), "->", fmt(A[-1]), "finite frac", round(float(np.isfinite(RET).mean()), 3))
    # ---- funding
    FZ = np.load(INPUTS["funding"], allow_pickle=True); assert np.array_equal(FZ["anchors"].astype(np.int64), A) and [str(s) for s in FZ["symbols"]] == syms
    F = {k: FZ[k] for k in ("fr_sum", "nset", "last_rate", "last_iv", "last_age_h", "cov")}
    R["funding_summary"] = {"frac_anchors_syms_covered": round(float(F["cov"].mean()), 3), "settlements_total": int(F["nset"].sum()), "nset_hist": {int(k): int(v) for k, v in zip(*np.unique(F["nset"], return_counts=True))}}
    # ---- meta/panel/slow (signal data inputs)
    MT = np.load(INPUTS["meta"], allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4m = MT["y4"]; qvk = MT["qvk"]
    PW = np.load(INPUTS["panel_v2"], allow_pickle=True); assert [str(s) for s in PW["symbols"]] == syms
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    D = {"E_ts": E_ts, "members": members, "SLOW": np.load(INPUTS["slow_pred"]), "R24": PW["f_rev_24h"], "FE": PW["f_fund_ema_v1"], "qvk": qvk, "pw_row": pw_row, "NW": NW, "apos": apos}
    mrow = {int(t): j for j, t in enumerate(E_ts)}
    # 等权市场 4h 收益(成员名均值)
    mkt = np.full(nA, np.nan)
    for i, t in enumerate(A):
        j = mrow.get(int(t))
        if j is None: continue
        v = RET[i, members[j]]; v = v[np.isfinite(v)]
        if len(v): mkt[i] = v.mean() * 1e4
    # ---- W-a: 现有装置权重输出
    WZ = np.load(INPUTS["w2_wide_series"], allow_pickle=True); assert [str(s) for s in WZ["symbols"]] == syms
    cols = [str(c) for c in WZ["cols"]]; recS0 = WZ["S0_rec"]; recD = WZ["d30_n2_c42_rec"]; WaS0 = WZ["S0_W"]; WaD = WZ["d30_n2_c42_W"]
    wa_ts = recS0[:, 0].astype(np.int64); assert np.array_equal(wa_ts, recD[:, 0].astype(np.int64))
    log("W-a loaded", WaS0.shape, fmt(wa_ts[0]), "->", fmt(wa_ts[-1]))
    # ---- W-b: 自建链 (parity + independent) ; 腿 msharpe 需 2021 暖机 ⇒ 从 2021-01-01 起跑, 记录从 2022-01-01 起
    rec_from = int(np.searchsorted(E_ts, A_T0))
    t0 = time.time()
    chains = {}
    chains["par_S0"] = run_chain(D, RET, stop=None, tag="par_S0", record_from=rec_from, parity_y4=y4m)
    chains["par_d30"] = run_chain(D, RET, stop=(-0.30, 2, 42), tag="par_d30", record_from=rec_from, parity_y4=y4m)
    chains["S0"] = run_chain(D, RET, stop=None, tag="S0", record_from=rec_from)
    chains["d30"] = run_chain(D, RET, stop=(-0.30, 2, 42), tag="d30", record_from=rec_from)
    chains["d30_nofund"] = run_chain(D, RET, stop=(-0.30, 2, 42), w3_mode="no_fund", tag="d30_nofund", record_from=rec_from)
    chains["d30_halffund"] = run_chain(D, RET, stop=(-0.30, 2, 42), w3_mode="half_fund", tag="d30_halffund", record_from=rec_from)
    chains["S0_nofund"] = run_chain(D, RET, stop=None, w3_mode="no_fund", tag="S0_nofund", record_from=rec_from)
    log("chains done", round(time.time() - t0, 1), "s", {k: (len(v["ts"]), v["skipped"], v["fires"]) for k, v in chains.items()})
    R["chain_meta"] = {k: {"n_rec": int(len(v["ts"])), "skipped_anchors": int(v["skipped"]), "fires_total": int(v["fires"]), "w3_mean": [round(float(x), 4) for x in v["w3"].mean(0)]} for k, v in chains.items()}
    # ---- receipts: parity W-b(meta y4 everywhere) vs W-a on common anchors
    cts = chains["par_S0"]["ts"]; common = np.intersect1d(cts, wa_ts)
    ci = np.searchsorted(cts, common); wi = np.searchsorted(wa_ts, common)
    for nm, Wa, Wb in (("S0", WaS0, chains["par_S0"]["W"]), ("d30", WaD, chains["par_d30"]["W"])):
        dw = np.abs(Wa[wi].astype(np.float64) - Wb[ci].astype(np.float64))
        R[f"receipt_parity_{nm}"] = {"n_common": int(len(common)), "maxabs_dw": float(dw.max()), "mean_abs_dw": float(dw.mean()), "gross_a": float(np.abs(Wa[wi]).sum(1).mean()), "gross_b": float(np.abs(Wb[ci]).sum(1).mean()),
                                     "frac_anchors_maxdw_lt_1e-4": float((dw.max(1) < 1e-4).mean()), "corr_flat": float(np.corrcoef(Wa[wi].ravel(), Wb[ci].ravel())[0, 1])}
        log("RECEIPT parity", nm, R[f"receipt_parity_{nm}"])
    # ---- accounting for each weight source on its recorded anchors (≥2022-01-01, ≤ A_T1)
    def align(ts):
        ai = np.array([apos.get(int(t), -1) for t in ts]); ok = ai >= 0; return ai, ok
    ACC = {}; SUMM = {}
    sources = {"Wa_S0": (wa_ts, WaS0, None), "Wa_d30": (wa_ts, WaD, None)}
    for k, v in chains.items():
        if k.startswith("par_"): continue
        sources[f"Wb_{k}"] = (v["ts"], v["W"], v["WL"])
    for nm, (ts_, W_, WL_) in sources.items():
        ai, ok = align(ts_); ai = ai[ok]; ts_ = ts_[ok]; W_ = W_[ok]; WL_ = None if WL_ is None else WL_[ok]
        keep = (ts_ >= A_T0)
        ai = ai[keep]; ts_ = ts_[keep]; W_ = W_[keep]; WL_ = None if WL_ is None else WL_[keep]
        Fsub = {k2: F[k2][ai] for k2 in F}
        acc = account(W_, ts_, Fsub, RET[ai], LRET[ai], qv_tier=tier[ai], WL=WL_)
        ACC[nm] = acc
        SUMM[nm] = {"FULL(2022-01..2026-07)": summarize(acc, ts_, mkt[ai], nm)}
        m26 = ts_ <= int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())
        SUMM[nm]["2022-01..2026-06"] = summarize(acc, ts_, mkt[ai], nm, yr_mask=m26)
        m2426 = yr_of(ts_) >= 2024
        SUMM[nm]["2024-26"] = summarize(acc, ts_, mkt[ai], nm, yr_mask=m2426)
        log("accounted", nm, "net@2 sharpe FULL", SUMM[nm]["FULL(2022-01..2026-07)"]["net_at_gross2"]["sharpe_anchor"], "2022-06", SUMM[nm]["2022-01..2026-06"]["net_at_gross2"]["sharpe_anchor"])
    R["summary"] = SUMM
    # ---- receipt: W-a published caliber replica (their nets) vs my replica of their caliber on their weights: meta y4 pnl − pred carry×4/iv(panel) − tier-b cost == nets_histv2?
    try:
        FNp = PW["f_fund_now"]; IVp = PW["f_fund_iv"]
        for nm, Wa, reff in (("S0", WaS0, INPUTS["nets_S0"]), ("d30", WaD, INPUTS["nets_d30"])):
            ref = np.load(reff); assert np.array_equal(ref[:, 0].astype(np.int64), wa_ts)
            mine = np.full(len(wa_ts), np.nan)
            for i, t in enumerate(wa_ts):
                j = mrow.get(int(t)); jp = pw_row.get(int(t))
                if j is None or jp is None: continue
                m = members[j]; sm = Wa[i].astype(float); yv = np.nan_to_num(y4m[j, m], nan=0.0)
                fn = np.nan_to_num(FNp[jp, m], nan=0.0); iv = IVp[jp, m]; iv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
                car = (sm[m] * fn * (4.0 / iv)).sum() * 1e4; pnl_ = (sm[m] * yv).sum() * 1e4
                mine[i] = pnl_ - car
            rc = {"net": 1, "cost": 4}
            ok = np.isfinite(mine)
            d = (ref[ok, 1] + (recS0 if nm == "S0" else recD)[ok, 4]) - mine[ok]      # ref net + their cost = pnl − carry
            R[f"receipt_published_caliber_replica_{nm}"] = {"n": int(ok.sum()), "maxabs_diff_bps": float(np.abs(d).max()), "mean_abs_diff_bps": float(np.abs(d).mean())}
            log("RECEIPT published caliber replica", nm, R[f"receipt_published_caliber_replica_{nm}"])
    except Exception as e:
        R["receipt_published_caliber_replica_error"] = repr(e); log("receipt replica error", repr(e))
    # ---- 5m arms (450 名) on Wb_d30 weights: 1h cc vs 5m cc vs 5m Σsimple vs 5m Σlog
    try:
        Z5 = np.load(INPUTS["ret5m"], allow_pickle=True); A5 = Z5["anchors"].astype(np.int64); s5 = [str(s) for s in Z5["symbols"]]; RCC = Z5["r_cc"]; RSUM = Z5["r_sum"]; RSL = Z5["r_sumlog"]; NF5 = Z5["nfin"]
        col5 = np.array([syms.index(s) for s in s5]); a5pos = {int(t): i for i, t in enumerate(A5)}
        acc = ACC["Wb_d30"]; ts_ = acc["ts"]; W_ = sources["Wb_d30"][1]
        ai, ok = align(ts_); Wd = sources["Wb_d30"][1]
        # rebuild W aligned as in accounting (ts_ already filtered): need same W rows → recompute from chain
        v = chains["d30"]; aiv, okv = align(v["ts"]); keepv = okv & (v["ts"] >= A_T0); Wv = v["W"][keepv]; tsv = v["ts"][keepv]; aiv = aiv[keepv]
        i5 = np.array([a5pos.get(int(t), -1) for t in tsv]); ok5 = i5 >= 0
        Wsub = Wv[ok5][:, col5].astype(np.float64); R1 = np.nan_to_num(RET[aiv[ok5]][:, col5]); r5cc = RCC[i5[ok5]]; r5s = RSUM[i5[ok5]]; r5l = RSL[i5[ok5]]
        fin_all = np.isfinite(r5cc) & np.isfinite(r5s) & np.isfinite(RET[aiv[ok5]][:, col5])
        p1 = (Wsub * np.where(fin_all, R1, 0)).sum(1) * 1e4; p5c = (Wsub * np.where(fin_all, np.nan_to_num(r5cc), 0)).sum(1) * 1e4; p5s = (Wsub * np.where(fin_all, np.nan_to_num(r5s), 0)).sum(1) * 1e4; p5l = (Wsub * np.where(fin_all, np.nan_to_num(r5l), 0)).sum(1) * 1e4
        gsub = np.abs(Wsub).sum(1); gall = np.abs(Wv[ok5]).sum(1)
        nn = int(fin_all.sum()); dcc = (r5cc - R1)[fin_all] * 1e4; dsum = (r5s - R1)[fin_all] * 1e4
        R["arm_5m_vs_1h"] = {"n_anchors": int(ok5.sum()), "gross_share_on_450": round(float((gsub / np.maximum(gall, 1e-9)).mean()), 4), "name_anchor_pairs_compared": nn,
                             "per_name_diff_bps_5mcc_minus_1hcc": {"mean": float(dcc.mean()), "median": float(np.median(dcc)), "mean_abs": float(np.abs(dcc).mean()), "p99_abs": float(np.percentile(np.abs(dcc), 99)), "frac_abs_gt_1bp": float((np.abs(dcc) > 1).mean())},
                             "per_name_diff_bps_5msum_minus_1hcc": {"mean": float(dsum.mean()), "median": float(np.median(dsum)), "mean_abs": float(np.abs(dsum).mean()), "p99_abs": float(np.percentile(np.abs(dsum), 99))},
                             "book_pnl_bps_per_anchor_on_450_slice": {"1h_cc": float(p1.mean()), "5m_cc": float(p5c.mean()), "5m_sum_simple(shadow_conv)": float(p5s.mean()), "5m_sum_log": float(p5l.mean())},
                             "book_delta_vs_1hcc_mean_bps": {"5m_cc": float((p5c - p1).mean()), "5m_sum_simple": float((p5s - p1).mean()), "5m_sum_log": float((p5l - p1).mean())},
                             "book_delta_sd_bps": {"5m_cc": float((p5c - p1).std()), "5m_sum_simple": float((p5s - p1).std())},
                             "sharpe_on_slice_pnl_only": {"1h_cc": round(sharpe_a(p1), 3), "5m_cc": round(sharpe_a(p5c), 3), "5m_sum_simple": round(sharpe_a(p5s), 3), "5m_sum_log": round(sharpe_a(p5l), 3)},
                             "nfin_lt46_frac": float((NF5[i5[ok5]][:, :] < 46).mean())}
        log("5m arm", R["arm_5m_vs_1h"]["book_delta_vs_1hcc_mean_bps"])
    except Exception as e:
        import traceback; R["arm_5m_error"] = traceback.format_exc()[-800:]; log("5m arm error", repr(e))
    # ---- Δ readings between arms (paired block bootstrap on net@2, common anchors)
    def common_series(n1, n2, key="net_g2"):
        a = ACC[n1]; b = ACC[n2]; cm = np.intersect1d(a["ts"], b["ts"]); return a[key][np.searchsorted(a["ts"], cm)], b[key][np.searchsorted(b["ts"], cm)], cm
    R["deltas"] = {}
    for (n1, n2, lab) in (("Wb_d30", "Wb_S0", "stop_effect(d30-S0)_Wb"), ("Wa_d30", "Wa_S0", "stop_effect(d30-S0)_Wa"), ("Wb_d30", "Wa_d30", "Wb_vs_Wa_d30"), ("Wb_S0", "Wa_S0", "Wb_vs_Wa_S0"),
                        ("Wb_d30_nofund", "Wb_d30", "no_fund_minus_base_d30"), ("Wb_d30_halffund", "Wb_d30", "half_fund_minus_base_d30"), ("Wb_S0_nofund", "Wb_S0", "no_fund_minus_base_S0")):
        x, y, cm = common_series(n1, n2); m26 = cm <= int(dt.datetime(2026, 6, 30, 23, tzinfo=dt.timezone.utc).timestamp())
        R["deltas"][lab] = {"n": int(len(cm)), "FULL": boot_delta_sharpe(x, y), "2022-01..2026-06": boot_delta_sharpe(x[m26], y[m26]), "sharpe_x": round(sharpe_a(x), 3), "sharpe_y": round(sharpe_a(y), 3), "mean_x": round(float(x.mean()), 4), "mean_y": round(float(y.mean()), 4),
                            "corr": round(float(np.corrcoef(x, y)[0, 1]), 4)}
    # ---- C: in-role S1 (SR weights) same caliber
    try:
        SR = np.load(INPUTS["inrole_sr_npz"], allow_pickle=True); ats = SR["mine_p3_SIM_ats"].astype(np.int64); WS1 = SR["mine_p3_SIM_W_S1"].astype(np.float64); lsym = [str(s) for s in SR["symbols"]]
        sr_net = SR["mine_p3_SIM_S1_net"]; sr_pnl = SR["mine_p3_SIM_S1_pnl"]; sr_trn = SR["mine_p3_SIM_S1_trn"]; sr_gross = SR["mine_p3_SIM_S1_gross"]
        lmap = np.array([syms.index(s) for s in lsym]); ai, ok = align(ats); assert ok.all()
        Wl = np.zeros((len(ats), NW)); Wl[:, lmap] = WS1
        Fsub = {k2: F[k2][ai] for k2 in F}
        accL = account(Wl, ats, Fsub, RET[ai], LRET[ai], qv_tier=tier[ai])
        ACC["inrole_S1"] = accL
        # receipt: my pnl vs SR pnl (both simple 1h, same clock) — full + 2025 segment
        yr = yr_of(ats); d = accL["pnl"] - sr_pnl
        R["inrole_receipt"] = {"n": int(len(ats)), "pnl_mine_mean": round(float(accL["pnl"].mean()), 4), "pnl_sr_mean": round(float(sr_pnl.mean()), 4), "corr": round(float(np.corrcoef(accL["pnl"], sr_pnl)[0, 1]), 6),
                               "mean_abs_diff_bps": float(np.abs(d).mean()), "max_abs_diff_bps": float(np.abs(d).max()), "frac_abs_lt_0.01": float((np.abs(d) < 0.01).mean()),
                               "seg2025": {"n": int((yr == 2025).sum()), "pnl_mine": round(float(accL["pnl"][yr == 2025].mean()), 4), "pnl_sr": round(float(sr_pnl[yr == 2025].mean()), 4), "mean_abs_diff": float(np.abs(d[yr == 2025]).mean()), "max_abs_diff": float(np.abs(d[yr == 2025]).max()),
                                           "sharpe_mine_net_sr_cost": round(sharpe_a((accL["pnl"] - 4.137 * sr_trn)[yr == 2025]), 3), "sharpe_sr_net": round(sharpe_a(sr_net[yr == 2025]), 3)},
                               "trn_mine_mean": round(float(accL["trn"].mean()), 5), "trn_sr_mean": round(float(sr_trn.mean()), 5), "gross_mine_mean": round(float(accL["gross"].mean()), 4), "gross_sr_mean": round(float(sr_gross.mean()), 4),
                               "sr_net_sharpe_full(quoted 0.37)": round(sharpe_a(sr_net), 3), "sr_net_mean_full(quoted 0.272)": round(float(sr_net.mean()), 4)}
        log("RECEIPT inrole", R["inrole_receipt"])
        SUMM["inrole_S1"] = {"FULL(2022-01..2026-06)": summarize(accL, ats, mkt[ai], "inrole_S1_same_caliber"), "2024-26": summarize(accL, ats, mkt[ai], "inrole_S1_same_caliber", yr_mask=yr >= 2024)}
        # two-book: common anchors with Wb_d30 (and Wa_d30), 2022-01..2026-06
        R["two_book"] = {}
        for wn in ("Wb_d30", "Wa_d30", "Wb_S0"):
            x, y, cm = common_series(wn, "inrole_S1")          # x = wide net@2, y = inrole net@2
            xa, ya, _ = common_series(wn, "inrole_S1", key="net")
            dx, ud = agg_daily(x, cm); dy, _ = agg_daily(y, cm)
            yrc = yr_of(cm)
            grid = np.round(np.arange(0, 1.0001, 0.05), 2)
            def blend_sh(w, xx, yy): return sharpe_a(w * xx + (1 - w) * yy)
            curve = {float(w): round(blend_sh(w, x, y), 3) for w in grid}
            wbest = max(curve, key=curve.get)
            # walk-forward by year: choose w on prior years, apply to this year
            wf = {}; wf_series = []
            for yy in sorted(set(yrc.tolist()))[1:]:
                past = yrc < yy; cur = yrc == yy
                wsel = max(grid, key=lambda w: blend_sh(w, x[past], y[past]))
                wf[int(yy)] = {"w_wide": float(wsel), "sharpe_blend": round(sharpe_a(wsel * x[cur] + (1 - wsel) * y[cur]), 3), "sharpe_wide": round(sharpe_a(x[cur]), 3), "sharpe_inrole": round(sharpe_a(y[cur]), 3)}
                wf_series.append(wsel * x[cur] + (1 - wsel) * y[cur])
            wfs = np.concatenate(wf_series) if wf_series else np.array([0.0])
            R["two_book"][wn] = {"n_common": int(len(cm)), "span": [fmt(cm[0]), fmt(cm[-1])], "corr_anchor_net_g2": round(float(np.corrcoef(x, y)[0, 1]), 4), "corr_daily_net_g2": round(float(np.corrcoef(dx, dy)[0, 1]), 4),
                                 "corr_by_year_daily": {int(yy): round(float(np.corrcoef(agg_daily(x[yrc == yy], cm[yrc == yy])[0], agg_daily(y[yrc == yy], cm[yrc == yy])[0])[0, 1]), 3) for yy in sorted(set(yrc.tolist()))},
                                 "sharpe_wide": round(sharpe_a(x), 3), "sharpe_inrole": round(sharpe_a(y), 3), "sharpe_wide_daily": round(sharpe_d(x, cm), 3), "sharpe_inrole_daily": round(sharpe_d(y, cm), 3),
                                 "mean_wide_g2": round(float(x.mean()), 4), "mean_inrole_g2": round(float(y.mean()), 4), "mean_wide_actual": round(float(xa.mean()), 4), "mean_inrole_actual": round(float(ya.mean()), 4),
                                 "delta_sharpe_wide_minus_inrole": boot_delta_sharpe(x, y), "delta_sharpe_2024_26": boot_delta_sharpe(x[yrc >= 2024], y[yrc >= 2024]),
                                 "blend_curve_sharpe": curve, "w_best_insample": float(wbest), "sharpe_best_insample": curve[wbest], "walk_forward": wf, "walk_forward_sharpe_all": round(sharpe_a(wfs), 3),
                                 "by_year": {int(yy): {"wide": round(sharpe_a(x[yrc == yy]), 3), "inrole": round(sharpe_a(y[yrc == yy]), 3), "wide_mean": round(float(x[yrc == yy].mean()), 3), "inrole_mean": round(float(y[yrc == yy].mean()), 3)} for yy in sorted(set(yrc.tolist()))}}
        log("two_book", {k: (v["corr_daily_net_g2"], v["sharpe_wide"], v["sharpe_inrole"], v["w_best_insample"]) for k, v in R["two_book"].items()})
    except Exception as e:
        import traceback; R["inrole_error"] = traceback.format_exc()[-1200:]; log("inrole error", repr(e))
    R["summary"] = SUMM
    # ---- E verdict (frozen rule)
    try:
        tb = R["two_book"]["Wb_d30"]; ds = tb["delta_sharpe_wide_minus_inrole"]
        verdict = "显著优于" if ds["CI95"][0] > 0 else ("否" if ds["CI95"][1] < 0 else "传闻级")
        R["E_verdict"] = {"rule": "Wb_d30 净@2 vs 在役 S1 同口径 配对块自助 ΔSharpe CI95", "wide_sharpe": tb["sharpe_wide"], "wide_sharpe_CI95": SUMM["Wb_d30"]["2022-01..2026-06"]["net_at_gross2"]["sharpe_CI95_blk42"], "inrole_sharpe": tb["sharpe_inrole"], "delta": ds, "verdict": verdict}
        log("E_verdict", R["E_verdict"])
    except Exception as e:
        R["E_verdict_error"] = repr(e)
    # ---- save series
    np.savez_compressed(f"{WA}/wa_series.npz", **{f"{nm}__{k}": v for nm, acc in ACC.items() for k, v in acc.items() if not isinstance(v, dict)},
                        **{f"{nm}__leg_{leg}__{k}": v for nm, acc in ACC.items() if "legs" in acc for leg, d in acc["legs"].items() for k, v in d.items()},
                        **{f"chain_{k}__ts": v["ts"] for k, v in chains.items()}, **{f"chain_{k}__w3": v["w3"] for k, v in chains.items()}, mkt_ew=mkt, anchors=A)
    np.savez_compressed(f"{WA}/wa_weights_Wb_d30.npz", ts=chains["d30"]["ts"], W=chains["d30"]["W"], symbols=np.array(syms))
    json.dump(R, open(f"{WA}/wide_full_caliber_audit_run_2026-08-22.json", "w"), indent=1, ensure_ascii=False, default=float)
    log("run DONE ->", f"{WA}/wide_full_caliber_audit_run_2026-08-22.json")

# ───────────────────────────────────────────── stage shadow (@本机: fapi 公共端点 1h K 线 + fundingRate; 影子存档权重; score 行对账)
def stage_shadow():
    import urllib.request
    SHD = os.path.expanduser("~/wide_shadow"); OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(OUT, exist_ok=True)
    cfg = json.load(open(f"{SHD}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
    wfiles = sorted(glob.glob(f"{SHD}/state/weights/*.npz")); wts = np.array([int(os.path.basename(f)[:-4]) for f in wfiles], np.int64)
    Wsh = np.zeros((len(wfiles), len(syms)), np.float64)
    for i, f in enumerate(wfiles):
        z = np.load(f); Wsh[i, z["idx"]] = z["val"]
    score = {}; sig = {}
    for ln in open(f"{SHD}/shadow_log.jsonl"):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("e") == "score": score[int(r["anchor_ts"])] = r
        if r.get("e") == "signal": sig[int(r["anchor_ts"])] = r
    need = sorted(set(int(j) for j in np.where(np.abs(Wsh).sum(0) > 0)[0])); nsym = [syms[j] for j in need]
    log("shadow weights", Wsh.shape, fmt(wts[0]), "->", fmt(wts[-1]), "symbols with weight", len(nsym), "score rows", len(score))
    now = int(time.time()); t_start = int(wts[0]) - 3600 * 6
    BASE = "https://fapi.binance.com"
    def get(path, params):
        q = "&".join(f"{k}={v}" for k, v in params.items()); url = f"{BASE}{path}?{q}"
        for att in range(4):
            try:
                with urllib.request.urlopen(url, timeout=20) as r: return json.loads(r.read())
            except Exception as e:
                time.sleep(1 + att)
        return None
    cache = f"{OUT}/wa_shadow_pull_cache.json"
    if os.path.exists(cache):
        PULL = json.load(open(cache))
    else:
        PULL = {"kl": {}, "fr": {}}
    for k, s in enumerate(nsym):
        if s in PULL["kl"] and PULL["kl"][s] and int(PULL["kl"][s][-1][0]) // 1000 + 3600 >= (now // 3600) * 3600 - 3600: continue
        r = get("/fapi/v1/klines", {"symbol": s, "interval": "1h", "startTime": t_start * 1000, "limit": 1000})
        if r is None: log("kl fail", s); continue
        PULL["kl"][s] = [[int(x[0]), float(x[4]), float(x[7])] for x in r]
        f = get("/fapi/v1/fundingRate", {"symbol": s, "startTime": t_start * 1000, "limit": 1000})
        PULL["fr"][s] = [[int(x["fundingTime"]), float(x["fundingRate"])] for x in (f or [])]
        if k % 50 == 0: log("pull", k, "/", len(nsym)); json.dump(PULL, open(cache, "w"))
        time.sleep(0.05)
    json.dump(PULL, open(cache, "w"))
    # close grid (hour-end rows)
    hts = np.arange((t_start // 3600) * 3600, (now // 3600) * 3600 + 3600, 3600, dtype=np.int64); hpos = {int(t): i for i, t in enumerate(hts)}
    C = np.full((len(hts), len(syms)), np.nan)
    for s, rows in PULL["kl"].items():
        j = syms.index(s)
        for ot, cl, qv in rows:
            i = hpos.get(ot // 1000 + 3600)
            if i is not None: C[i, j] = cl
    res = []; last_w = None
    for i, T in enumerate(wts):
        if T + 4 * 3600 > now - 60: break
        a = hpos.get(int(T)); b = hpos.get(int(T) + 4 * 3600)
        if a is None or b is None: continue
        w = Wsh[i]; r = C[b] / C[a] - 1.0; fin = np.isfinite(r)
        gross_bps = float((w * np.where(fin, r, 0)).sum() * 1e4); lg = np.log(C[b] / C[a]); conv = float((w * np.where(fin, r - lg, 0)).sum() * 1e4)
        unc = float(np.abs(w[~fin]).sum())
        # realized funding in (T, T+4h]
        carry = 0.0; nset = 0; carry_pred = 0.0
        for s, rows in PULL["fr"].items():
            j = syms.index(s)
            if abs(w[j]) < 1e-12 or not rows: continue
            for ft, rate in rows:
                fs = ft // 1000
                if T < fs <= T + 4 * 3600: carry += w[j] * rate * 1e4; nset += 1
            # shadow-style predicted: last settled ≤ T, × 4/iv (iv from gap)
            prev = [(ft // 1000, rate) for ft, rate in rows if ft // 1000 <= T]
            if prev:
                fs, rate = prev[-1]
                iv = 8.0
                if len(prev) >= 2: iv = min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a_: abs(a_ - (prev[-1][0] - prev[-2][0]) / 3600.0))
                if T - fs <= 12 * 3600: carry_pred += w[j] * rate * (4.0 / iv) * 1e4
        trn = float(np.abs(w - last_w).sum()) if last_w is not None else (float(sig[int(T)]["turnover"]) if int(T) in sig else np.nan)
        last_w = w
        cost_main = COST_MAIN * trn if np.isfinite(trn) else np.nan
        sc = score.get(int(T))
        res.append({"anchor_ts": int(T), "utc": fmt(T), "gross_mine": gross_bps, "conv_mine": conv, "carry_real_mine": carry, "carry_pred_mine": carry_pred, "nset": nset, "trn_mine": trn, "cost_main": cost_main,
                    "net_mine_main": gross_bps - carry - cost_main if np.isfinite(cost_main) else np.nan, "net_mine_shadowcost": gross_bps - carry - (sc["cost_bps"] if sc else np.nan), "unc_gross": unc, "gross_pos": float(np.abs(w).sum()),
                    "shadow": {k: sc[k] for k in ("gross_bps", "net_bps", "carry_bps", "cost_bps")} if sc else None})
    both = [r for r in res if r["shadow"]]
    def arr(k): return np.array([r[k] for r in both], float)
    def sarr(k): return np.array([r["shadow"][k] for r in both], float)
    dg = arr("gross_mine") - sarr("gross_bps"); dc = arr("carry_real_mine") - sarr("carry_bps"); dcp = arr("carry_pred_mine") - sarr("carry_bps"); dn = arr("net_mine_shadowcost") - sarr("net_bps")
    OUTJ = {"session": "6737834a-WA", "stage": "shadow", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": SELF_SHA, "n_weight_anchors": int(len(wts)), "n_scored_common": int(len(both)),
            "gross_diff_mine_minus_shadow": {"mean": float(dg.mean()), "sd": float(dg.std(ddof=1)), "median": float(np.median(dg)), "max_abs": float(np.abs(dg).max()), "corr": float(np.corrcoef(arr("gross_mine"), sarr("gross_bps"))[0, 1])},
            "carry_realized_minus_shadow_pred": {"mean": float(dc.mean()), "sd": float(dc.std(ddof=1)), "max_abs": float(np.abs(dc).max())},
            "carry_predreplica_minus_shadow": {"mean": float(dcp.mean()), "sd": float(dcp.std(ddof=1)), "max_abs": float(np.abs(dcp).max()), "corr": float(np.corrcoef(arr("carry_pred_mine"), sarr("carry_bps"))[0, 1])},
            "net_shadowcost_diff": {"mean": float(dn.mean()), "sd": float(dn.std(ddof=1)), "max_abs": float(np.abs(dn).max())},
            "sums_common": {"shadow_net": float(sarr("net_bps").sum()), "shadow_gross": float(sarr("gross_bps").sum()), "mine_gross": float(arr("gross_mine").sum()), "mine_carry_real": float(arr("carry_real_mine").sum()), "shadow_carry_pred": float(sarr("carry_bps").sum()),
                            "mine_cost_main": float(np.nansum(arr("cost_main"))), "shadow_cost": float(sarr("cost_bps").sum()), "mine_net_main": float(np.nansum(arr("net_mine_main"))), "mine_net_shadowcost": float(dn.sum() + sarr("net_bps").sum()),
                            "conv_mine": float(arr("conv_mine").sum())},
            "first_week": {}, "rows": res}
    # first week: 08-16 12:00Z .. +42 anchors on shadow score rows (all) and mine (common)
    t0w = 1786881600; sc_sorted = sorted(score.items())
    fw = [v for k, v in sc_sorted if t0w <= k < t0w + 42 * 14400]
    OUTJ["first_week"]["shadow_score_rows_n"] = len(fw); OUTJ["first_week"]["shadow_net_sum"] = float(sum(v["net_bps"] for v in fw)); OUTJ["first_week"]["shadow_gross_sum"] = float(sum(v["gross_bps"] for v in fw))
    fwm = [r for r in both if t0w <= r["anchor_ts"] < t0w + 42 * 14400]
    OUTJ["first_week"]["mine_common_n"] = len(fwm); OUTJ["first_week"]["mine_net_main_sum_common"] = float(np.nansum([r["net_mine_main"] for r in fwm])); OUTJ["first_week"]["shadow_net_sum_common"] = float(sum(r["shadow"]["net_bps"] for r in fwm))
    OUTJ["first_week"]["mine_gross_sum_common"] = float(sum(r["gross_mine"] for r in fwm)); OUTJ["first_week"]["shadow_gross_sum_common"] = float(sum(r["shadow"]["gross_bps"] for r in fwm))
    OUTJ["all_mine_anchors"] = {"n": len(res), "net_main_sum": float(np.nansum([r["net_mine_main"] for r in res])), "gross_sum": float(sum(r["gross_mine"] for r in res)), "carry_real_sum": float(sum(r["carry_real_mine"] for r in res)), "cost_main_sum": float(np.nansum([r["cost_main"] for r in res]))}
    json.dump(OUTJ, open(f"{OUT}/wide_full_caliber_audit_shadow_2026-08-22.json", "w"), indent=1, default=float)
    log("shadow DONE", {k: v for k, v in OUTJ.items() if k in ("gross_diff_mine_minus_shadow", "carry_realized_minus_shadow_pred", "carry_predreplica_minus_shadow", "sums_common", "first_week")})

if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"build1h": stage_build1h, "build5m": stage_build5m, "funding": stage_funding, "run": stage_run, "shadow": stage_shadow}[st]()
