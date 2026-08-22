"""SR · 在役离线回放族的收益口径重跑: 对数 Y4 → 简单持有收益 expm1(Y4)(2026-08-22, Session 6737834a-SR)。
两阶段同一文件(可重跑):
  `python inrole_simple_return_rerun.py jp`     @jpline — 在役管线重放(PH 装置 phase_alignment_replay_jp.replay 逐字 + 收益变换开关),
                                                   写 probe_artifacts/inrole_sr/inrole_simple_return_rerun_jp_2026-08-22.{json,npz,log}
  `python inrole_simple_return_rerun.py local`  @本机  — 实盘对账(只读 ~/dl_quant_live)+ 合并 jp 结果 → results/inrole_simple_return_rerun_2026-08-22.json

问题(WS RESULT_wide_return_source_2026-08-22 §6 溢出): 在役离线回放族(9821 锚; 1.154/1.46 等一切数)pnl = Σ w·Y4,
Y4 = log CLOSE[T+4]/CLOSE[T](multi_asset/data/build_wide_dl.py:151; engine/panel_source.py:34 "raw 4h fwd logret"; engine/replay_fullhist.py:120;
w2_live_replay.py / phase_alignment_replay_jp.py `c[idx] = w*y*1e4`), 而实盘盈亏 = 场所权益差 = 持仓名义 × 简单价格变化
(~/dl_quant_live/scheduler/anchor_loop.py:2171-2187: nav = totalWalletBalance + totalUnrealizedProfit, /fapi/v3/account)。
对任意持仓 simple − log = w·(expm1(L) − L), 恒为 "多头得、空头失" ≈ |w|·L²/2 ⇒ "多低波动/空高波动" 的书在对数口径下偏乐观。
WS 旁估(固定 W2 S1 持仓 × 1h 立方体): 凸性项 −0.84 bps/锚 = S1 毛 pnl 的 68%。本装置在同构管线上【重跑】而非旁估。

【判据冻结, 先于看数】
 主读 = 在役 S1(逐名止损 −25%×2 锚/冷却 42 + EMA α0.05 + 带 b0.002), 实盘相位 p3(ph_preds_2026-08-22.npz, 因果面板), 成本 4.137×换手
        (与 PH/W2 逐字同, 以便逐位复现 PH 的 1.063/1.42); 成本 3.52(T1 实测)并列给出(净额对成本线性: net@3.52 = net@4.137 + 0.617×换手)。
        全史 2022-01→2026-06(名义时刻)。年化: 锚级 √(6·365); 日级 日和×√365(STATE §0 口径)。
 收据 R1: newgen_p0 对数臂 net_S0/net_S1 与 probe_artifacts/net_S{0,1}.npy 逐元素 maxabs < 1e-9(PH G2 同式; 证明管线逐字同构);
      R2: mine_p3 对数臂 S0/S1 net 与 ph_series_2026-08-22.npz::mine_p3_S{0,1}_net 逐元素 maxabs < 1e-9(= PH 1.063/1.42 逐位复现);
      R3: 面板 Y4[p3 行](价格 N→N+4h, 对数)与独立下载的 1h K 线立方体 R_wide[ts==N](同窗同口径, 另一份数据) 在 140 在役名上:
          逐锚相关中位 ≥ 0.99 且 |Δ| 中位 < 1 bps ⇒ 收益源可信(expm1 作用于同一量);
      R4: probe_artifacts/legs.py 与实盘 signal/legs.py 的差异仅为实盘新增 apply_no_trade_band(回放内联同语义), compose_book/apply_harvest_ema 逐字相同
          (本地 diff; 两个 SHA 记录在 JSON)。
 Δ = SIM − LOG(同相位/同预测/同管线/同成本, 唯一变量 = 收益变换 y → expm1(y); S0 的 Δ 是纯记账差(持仓逐位相同), S1 的 Δ 另含止损价格路径 Pi 的变化)。
 三选一(以 S1 p3 Δ净 bps/锚 的日块自助 CI95[2000 次, 共同日] 为准):
   (a) 对数口径无实质影响: |Δ净| < 0.10 且 CI 含 0;
   (b) 有系统偏差: CI 排除 0 ⇒ 给简单版全部数字 + CI, 建议今后离线族一律简单收益; 受影响清单按 PH §5 清单逐条标注(绝对水平重算 / 相对结论);
   (c) 传闻: R1/R2 任一不过(管线不同构)或 R3 不过(收益源不可信)。
 附读: 凸性项分解(固定持仓 Σ W·(expm1−log): 逐年 / 多空侧 / BTC·ETH·山寨 / 腿子书 / 逐名 top); 全重跑 Δ 与固定持仓凸性之差 = 止损路径效应;
      最坏五分位(|等权市场| 最高档 / 市场方向对书最差档 / 书自身最差五分位)两口径; 逐名义钟点; 夏普双口径; 逐年同号数。
 实盘对账(local): 08-05→08-21 场所持仓读回向量(position_readback, fapi/v3/account@post_anchor) × 实盘名义窗 [N,N+4h] 1h K 线 简单 vs 对数 盈亏(USDT),
      对 Δnav(扣出入金, 再扣费/资金费的毛当量)的 ρ/斜率/截距/MAE/均残差/累计; 剔除事故日 08-21 与含转账的锚区间。
      "哪个贴实盘" = 均残差更接近 0 且 MAE 更小。注: 场所盈亏恒等式本身就是简单口径, 此检验的价值在【量级】: 实盘期凸性项(USDT, bps/gross)与离线旁估是否同量级。
输入(只读): probe_artifacts/{ph_preds_2026-08-22.npz, ph_series_2026-08-22.npz, king/s2_pred_newgen.npz, net_S0/S1.npy, legs.py, w2b_ret_cube.npz},
      engine.panel_source 默认面板(仅 Y4/CH/member, 分数级回放与 W2/PH 同), engine.replay_fullhist._all_anchors;
      本机 ~/dl_quant_live/state/live/pilot_log/{anchors,position_readback,daily_nav}.jsonl + state/panel_cache/klines_1h.npz(只读)。
不碰 share / 实盘仓写 / 交易 API。
"""
import os, sys, json, time, hashlib, glob
import numpy as np, pandas as pd

STAGE = sys.argv[1] if len(sys.argv) > 1 else "local"
SESSION = "6737834a-SR"
W_LIVE = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; C_T1 = 3.52; BW = 0.002; COOL = 42; ALPHA = 0.05; ANN = np.sqrt(6 * 365)
LIVE_LEGS_SHA = "7c0665f817fca948e2f9226dbd20607c9ea7b7fd6c9abfac63d69e3bc8b47da6"   # ~/dl_quant_live/signal/legs.py @ ab569b8 (本地 shasum)
t0 = time.time()


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
            "by_year_mean": {int(y): round(float(np.nanmean(x[yr == y])), 3) for y in sorted(set(yr.tolist()))},
            "by_year_sharpe_anchor": {int(y): round(sharpe_anchor(x[yr == y]), 3) for y in sorted(set(yr.tolist()))},
            "by_year_sharpe_daily": {int(y): round(sharpe_daily(x[yr == y], ats[yr == y]), 3) for y in sorted(set(yr.tolist()))}}


def boot_delta(xa, ta, xb, tb, nb=2000, seed=0):
    """日块自助(PH 逐字): 两序列按日求和对齐(共同日), 自助日 ⇒ Δ均值(/锚 按 6)与 Δ日夏普 CI。"""
    ua, sa = daily(xa, ta); ub, sb = daily(xb, tb)
    com, ia, ib = np.intersect1d(ua, ub, return_indices=True)
    A = sa[ia]; B = sb[ib]; n = len(com); rng = np.random.default_rng(seed)
    def sh(v): return float(v.mean() / (v.std(ddof=1) + 1e-12) * np.sqrt(365.0))
    dm = []; ds = []
    for _ in range(nb):
        idx = rng.integers(0, n, n)
        dm.append((A[idx] - B[idx]).mean() / 6.0); ds.append(sh(A[idx]) - sh(B[idx]))
    return {"n_days": int(n), "delta_mean_bps_per_anchor": round(float((A - B).mean() / 6.0), 4),
            "delta_mean_ci95": [round(float(np.percentile(dm, 2.5)), 4), round(float(np.percentile(dm, 97.5)), 4)],
            "delta_daily_sharpe": round(sh(A) - sh(B), 3),
            "delta_daily_sharpe_ci95": [round(float(np.percentile(ds, 2.5)), 3), round(float(np.percentile(ds, 97.5)), 3)],
            "daily_sharpe_A": round(sh(A), 3), "daily_sharpe_B": round(sh(B), 3), "frac_days_A_ge_B": round(float((A >= B).mean()), 4)}


def boot_delta_sharpe_anchor(x, y, Lb=42, reps=2000, seed=7):
    """配对锚块自助 ΔSharpe(锚级, w2b_common 同式)."""
    rng = np.random.RandomState(seed); n = len(x); nb = n // Lb; d = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = np.concatenate([np.arange(i * Lb, (i + 1) * Lb) for i in idx])
        d.append(sharpe_anchor(x[sel]) - sharpe_anchor(y[sel]))
    d = np.array(d)
    return {"mean": round(float(d.mean()), 3), "CI95": [round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3)],
            "P_gt_0": round(float((d > 0).mean()), 3)}


# ====================================================================== JP stage
def stage_jp():
    PD = "/mnt/storage/private/work_hsy/probe_artifacts"
    REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"; MA = REPO + "/multi_asset"
    for p_ in (PD, MA, MA + "/engine/live", REPO, PD):
        sys.path.insert(0, p_)
    OUTD = f"{PD}/inrole_sr"; os.makedirs(OUTD, exist_ok=True)
    OUT_JSON = f"{OUTD}/inrole_simple_return_rerun_jp_2026-08-22.json"; OUT_NPZ = f"{OUTD}/inrole_simple_return_rerun_jp_2026-08-22.npz"
    import legs as LG
    import engine.replay_fullhist as RF
    from engine.panel_source import PanelSource
    from scipy.stats import rankdata
    NEWGEN = {"king": (f"{PD}/king_pred_newgen.npz", "king_pred"), "s2": (f"{PD}/s2_pred_newgen.npz", "s2_pred")}
    INP = {"ph_preds": f"{PD}/ph_preds_2026-08-22.npz", "ph_series": f"{PD}/ph_series_2026-08-22.npz", "legs.py": f"{PD}/legs.py",
           "king_pred_newgen": NEWGEN["king"][0], "s2_pred_newgen": NEWGEN["s2"][0], "net_S0": f"{PD}/net_S0.npy", "net_S1": f"{PD}/net_S1.npy",
           "w2b_ret_cube": f"{PD}/w2b_ret_cube.npz", "panel": MA + "/exports/wide_dl_full.npz"}
    res = {"session": SESSION, "stage": "jp", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script_sha256": sha(os.path.abspath(__file__)),
           "inputs_sha256": {k: (sha(v) if os.path.exists(v) else None) for k, v in INP.items()},
           "legs_sha": {"probe_artifacts/legs.py": sha(f"{PD}/legs.py"), "live_signal/legs.py(local shasum)": LIVE_LEGS_SHA,
                        "note": "R4: 本地 diff = 实盘文件仅新增 apply_no_trade_band(L343-385); compose_book/apply_harvest_ema 逐字相同"}}
    log("input shas done")
    src = PanelSource(king=NEWGEN["king"][0], s2=NEWGEN["s2"][0])
    P = np.load(INP["ph_preds"], allow_pickle=True)
    assert np.array_equal(np.asarray(src.ts).astype(np.int64), P["ts"].astype(np.int64)), "panel ts mismatch"
    N = src.N; SYMS = [str(s) for s in src.symbols]; ts_all = np.asarray(src.ts).astype(np.int64)
    hrs = pd.to_datetime(ts_all, unit="ms", utc=True).hour.values
    nominal_all = ts_all // 1000 + 3600
    FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
    btc_j = SYMS.index("BTCUSDT"); eth_j = SYMS.index("ETHUSDT") if "ETHUSDT" in SYMS else -1
    # --- 1h cube (independent source) mapped to nominal ts ---
    Z = np.load(INP["w2b_ret_cube"], allow_pickle=True); cts = Z["ts"].astype(np.int64); csym = [str(s) for s in Z["symbols"]]
    lmap = np.array([csym.index(s) for s in SYMS]); RW = Z["R_wide"][:, lmap].astype(np.float64); RL = Z["R_live"][:, lmap].astype(np.float64)
    cpos = {int(t): i for i, t in enumerate(cts)}
    log("cube loaded", RW.shape)

    def replay(K, S, phase_row_hour, tag, ret="log", anchors_ref=None, legs=False, ret_override=None):
        """phase_alignment_replay_jp.replay 逐字; 新增 ret∈{log,simple}: y = Y4 (log) 或 expm1(Y4) (simple); ret_override: (n,N) 对数收益矩阵替代 Y4 (交叉核对源)。"""
        src.king = K.astype(np.float64); src.s2 = S.astype(np.float64)
        lo = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp()); hi = int(pd.Timestamp("2026-07-01", tz="UTC").timestamp())
        trad_any = (src.member & np.isfinite(src.king) & np.isfinite(src.s2)).any(1)
        a = np.where((hrs % 4 == phase_row_hour) & trad_any & (nominal_all >= lo) & (nominal_all < hi))[0]
        if anchors_ref is not None:
            a = np.asarray(anchors_ref)
        n = len(a); ats = nominal_all[a]; yr = pd.to_datetime(ats, unit="s", utc=True).year.to_numpy()
        shift = 1 if phase_row_hour == 3 else 0
        TGT, MSK, RET, RETL = [], [], [], np.full((n, N), np.nan, np.float64)
        LEGW = {"king": {"king": 1., "s2": 0., "funding": 0., "size": 0.}, "s2": {"king": 0., "s2": 1., "funding": 0., "size": 0.},
                "funding": {"king": 0., "s2": 0., "funding": 1., "size": 0.}}
        TGTL = {k: [] for k in LEGW} if legs else {}
        held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
        mkt_ew = np.full(n, np.nan); btc4 = np.full(n, np.nan)
        for i, t in enumerate(a):
            ti = int(t); m = np.asarray(src.tradeable(ti))
            if m.dtype == bool: m = np.where(m)[0]
            if i == 0 or (ti + shift) % 8 == 0:
                v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
            if i == 0 or (ti + shift) % 24 == 0:
                v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
            if i == 0 or (ti + shift) % 8 == 0:
                v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
            rv = src.CH[ti, m, RVI].astype(float)
            r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=W_LIVE, rvol=rv, risk_budget=RB)
            w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
            ylog = (src.Y4[ti, m] if ret_override is None else ret_override[i, m]).astype(float)
            RETL[i, m] = ylog
            y = ylog if ret == "log" else np.expm1(ylog)
            TGT.append(w); MSK.append(m); RET.append(y)
            if legs:
                for k, wl in LEGW.items():
                    rl = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)), weights=wl, rvol=rv, risk_budget=RB)
                    wv = np.full(N, 0.0); wv[m] = np.asarray(rl["target_w"], float); TGTL[k].append(wv)
            yf = ylog[np.isfinite(ylog)]
            if len(yf): mkt_ew[i] = (yf.mean() if ret == "log" else np.expm1(yf).mean()) * 1e4
            if np.isfinite(src.Y4[ti, btc_j]) and ret_override is None: btc4[i] = (src.Y4[ti, btc_j] if ret == "log" else np.expm1(src.Y4[ti, btc_j])) * 1e4
            if i % 3000 == 0: log(f"  [{tag}] precompute {i}/{n}")

        def run(TGTx, stop):
            state = None; prev = np.zeros(N); Pi = np.ones(N); sh = np.zeros(N); cb = np.zeros(N)
            cnt = np.zeros(N, int); su = np.full(N, -1)
            pnl = np.zeros(n); trn = np.zeros(n); gross = np.zeros(n); fires = np.zeros(n, int); ic = np.full(n, np.nan)
            pnl_long = np.zeros(n); pnl_short = np.zeros(n); gross_long = np.zeros(n)
            WS = np.zeros((n, N), np.float32)
            for i in range(n):
                m = MSK[i]; syms = [SYMS[j] for j in m]
                out = LG.apply_harvest_ema(TGTx[i][m], syms, state, ALPHA); state = out["state"]
                tgt = np.asarray(out["target_w"], float)
                if stop:
                    bs = set(np.where(su > i)[0].tolist())
                    if bs:
                        for k2, j in enumerate(m):
                            if j in bs: tgt[k2] = 0.0
                w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
                d = tgt - w[m]; Tm = np.abs(d) > BW
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
                WS[i] = w.astype(np.float32)
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
            net = pnl - trn * C1
            return dict(net=net, pnl=pnl, trn=trn, gross=gross, fires=fires, ic=ic, W=WS, pnl_long=pnl_long, pnl_short=pnl_short, gross_long=gross_long)
        R = {"S0": run(TGT, False), "S1": run(TGT, True)}
        if legs:
            for k in LEGW: R["leg_" + k] = run(TGTL[k], False)
        R["meta"] = {"n": int(n), "ats": ats, "yr": yr, "rows": a, "mkt_ew": mkt_ew, "btc4": btc4, "RETL": RETL,
                     "first_nominal": str(pd.to_datetime(ats[0], unit="s", utc=True)), "last_nominal": str(pd.to_datetime(ats[-1], unit="s", utc=True))}
        log(f"  [{tag}] done n={n} S1 net mean={R['S1']['net'].mean():.4f} sharpe={sharpe_anchor(R['S1']['net']):.3f} | S0 {R['S0']['net'].mean():.4f}/{sharpe_anchor(R['S0']['net']):.3f}")
        return R

    # ---------------- arms
    a_ref, _ = RF._all_anchors(src)
    Kng = np.load(NEWGEN["king"][0], allow_pickle=True)[NEWGEN["king"][1]]; Sng = np.load(NEWGEN["s2"][0], allow_pickle=True)[NEWGEN["s2"][1]]
    ARMS = {}
    ARMS["newgen_p0_LOG"] = replay(Kng, Sng, 0, "newgen_p0_LOG", "log", anchors_ref=a_ref)
    ref0 = np.load(INP["net_S0"]); ref1 = np.load(INP["net_S1"])
    R1 = {"maxabs_S0": float(np.max(np.abs(ref0 - ARMS["newgen_p0_LOG"]["S0"]["net"]))), "maxabs_S1": float(np.max(np.abs(ref1 - ARMS["newgen_p0_LOG"]["S1"]["net"]))), "n": int(ARMS["newgen_p0_LOG"]["meta"]["n"])}
    R1["pass"] = bool(R1["maxabs_S0"] < 1e-9 and R1["maxabs_S1"] < 1e-9); res["R1_newgen_p0_log_reproduces_net_S0_S1"] = R1; log("R1", R1)
    ARMS["newgen_p0_SIM"] = replay(Kng, Sng, 0, "newgen_p0_SIM", "simple", anchors_ref=a_ref)
    ARMS["mine_p3_LOG"] = replay(P["king_p3"], P["s2_p3"], 3, "mine_p3_LOG", "log", legs=True)
    PS = np.load(INP["ph_series"], allow_pickle=True)
    R2 = {"n_mine": int(ARMS["mine_p3_LOG"]["meta"]["n"]), "n_ph": int(len(PS["mine_p3_S1_net"]))}
    if R2["n_mine"] == R2["n_ph"]:
        R2["maxabs_S0"] = float(np.max(np.abs(PS["mine_p3_S0_net"] - ARMS["mine_p3_LOG"]["S0"]["net"])))
        R2["maxabs_S1"] = float(np.max(np.abs(PS["mine_p3_S1_net"] - ARMS["mine_p3_LOG"]["S1"]["net"])))
        R2["ats_equal"] = bool(np.array_equal(PS["mine_p3_ats"].astype(np.int64), ARMS["mine_p3_LOG"]["meta"]["ats"].astype(np.int64)))
        R2["pass"] = bool(R2["maxabs_S0"] < 1e-9 and R2["maxabs_S1"] < 1e-9 and R2["ats_equal"])
    else:
        R2["pass"] = False
    res["R2_mine_p3_log_reproduces_PH"] = R2; log("R2", R2)
    ARMS["mine_p3_SIM"] = replay(P["king_p3"], P["s2_p3"], 3, "mine_p3_SIM", "simple", legs=True)
    ARMS["mine_p0_LOG"] = replay(P["king_p0"], P["s2_p0"], 0, "mine_p0_LOG", "log")
    ARMS["mine_p0_SIM"] = replay(P["king_p0"], P["s2_p0"], 0, "mine_p0_SIM", "simple")
    # ---- R3: Y4[p3 rows] vs cube R_wide[ts == nominal N] on 140 live names; + cube-source arm
    M3 = ARMS["mine_p3_LOG"]["meta"]; ats3 = M3["ats"]; n3 = M3["n"]; RETL3 = M3["RETL"]
    crow = np.array([cpos.get(int(t), -1) for t in ats3]); incube = crow >= 0
    RWm = np.full((n3, N), np.nan); RWm[incube] = RW[crow[incube]]
    both = np.isfinite(RETL3) & np.isfinite(RWm)
    d = (RETL3 - RWm)[both]
    cors = []
    for i in np.where(incube)[0][::5]:
        ok = both[i]
        if ok.sum() > 20: cors.append(np.corrcoef(RETL3[i, ok], RWm[i, ok])[0, 1])
    R3 = {"anchors_in_cube": int(incube.sum()), "anchors_total": int(n3), "cells_both_finite": int(both.sum()),
          "cells_panel_only": int((np.isfinite(RETL3) & ~np.isfinite(RWm) & incube[:, None]).sum()),
          "maxabs_diff": float(np.max(np.abs(d))), "median_abs_diff_bps": float(np.median(np.abs(d)) * 1e4), "mean_abs_diff_bps": float(np.mean(np.abs(d)) * 1e4),
          "frac_abs_lt_1e-6": float((np.abs(d) < 1e-6).mean()), "frac_abs_lt_1bps": float((np.abs(d) < 1e-4).mean()),
          "per_anchor_corr_median": float(np.median(cors)), "per_anchor_corr_p5": float(np.percentile(cors, 5)),
          "definition": "panel Y4[row N-1h] = log CLOSE[N+3h bar]/CLOSE[N-1h bar] (1h klines, training panel) vs cube R_wide[ts=N] = log(close_1h[N+3h bar]/close_1h[N-1h bar]) (data.binance.vision 1h zips); same window N->N+4h"}
    R3["pass"] = bool(R3["per_anchor_corr_median"] >= 0.99 and R3["median_abs_diff_bps"] < 1.0)
    res["R3_Y4_vs_1h_cube_same_window"] = R3; log("R3", R3)
    # cube-source arm: simple returns from the independent 1h source (fallback to panel Y4 where cube missing)
    RWfb = np.where(np.isfinite(RWm), RWm, RETL3)
    res["cube_arm_fallback_cells"] = int((~np.isfinite(RWm) & np.isfinite(RETL3)).sum())
    ARMS["mine_p3_SIM_cube1h"] = replay(P["king_p3"], P["s2_p3"], 3, "mine_p3_SIM_cube1h", "simple", ret_override=RWfb)
    ARMS["mine_p3_LOG_cube1h"] = replay(P["king_p3"], P["s2_p3"], 3, "mine_p3_LOG_cube1h", "log", ret_override=RWfb)

    # ---------------- summaries
    out = {}
    for nm, R in ARMS.items():
        yr = R["meta"]["yr"]; ats = R["meta"]["ats"]
        out[nm] = {"n_anchors": int(R["meta"]["n"]), "first_nominal": R["meta"]["first_nominal"], "last_nominal": R["meta"]["last_nominal"]}
        for k in [kk for kk in ("S0", "S1", "leg_king", "leg_s2", "leg_funding") if kk in R]:
            x = R[k]
            out[nm][k] = {"net@4.137": summ(x["net"], yr, ats), "net@3.52": summ(x["pnl"] - x["trn"] * C_T1, yr, ats), "pnl_gross": summ(x["pnl"], yr, ats),
                          "pnl_long_side": round(float(x["pnl_long"].mean()), 4), "pnl_short_side": round(float(x["pnl_short"].mean()), 4),
                          "turnover_mean": round(float(x["trn"].mean()), 5), "gross_mean": round(float(x["gross"].mean()), 4), "gross_long_mean": round(float(x["gross_long"].mean()), 4),
                          "fires_total": int(x["fires"].sum()), "book_rank_ic_mean": round(float(np.nanmean(x["ic"])), 5)}
    res["arms"] = out

    # ---------------- deltas SIM − LOG (paired, same anchors)
    def delta_block(A, B, tagA, tagB):
        D = {}
        for k in ("S0", "S1"):
            xa, xb = A[k]["net"], B[k]["net"]; yr = A["meta"]["yr"]; ats = A["meta"]["ats"]
            assert np.array_equal(A["meta"]["ats"], B["meta"]["ats"])
            dn = xa - xb
            D[k] = {"delta_net_mean_bps": round(float(dn.mean()), 4), "delta_net_sd": round(float(dn.std(ddof=1)), 4),
                    "delta_net_t": round(float(dn.mean() / dn.std(ddof=1) * np.sqrt(len(dn))), 2),
                    "delta_pnl_mean_bps": round(float((A[k]["pnl"] - B[k]["pnl"]).mean()), 4),
                    "delta_sharpe_anchor": round(sharpe_anchor(xa) - sharpe_anchor(xb), 3), "delta_sharpe_daily": round(sharpe_daily(xa, ats) - sharpe_daily(xb, ats), 3),
                    "by_year_delta_net": {int(y): round(float(dn[yr == y].mean()), 4) for y in sorted(set(yr.tolist()))},
                    "by_year_same_sign_neg": int(sum(1 for y in set(yr.tolist()) if dn[yr == y].mean() < 0)),
                    "boot_daily": boot_delta(xa, ats, xb, ats), "boot_anchor_block42_delta_sharpe": boot_delta_sharpe_anchor(xa, xb),
                    "delta_turnover": round(float((A[k]["trn"] - B[k]["trn"]).mean()), 5), "delta_fires": int(A[k]["fires"].sum() - B[k]["fires"].sum()),
                    "positions_identical_maxabs": float(np.max(np.abs(A[k]["W"] - B[k]["W"])))}
        return D
    res["delta_SIM_minus_LOG"] = {"mine_p3": delta_block(ARMS["mine_p3_SIM"], ARMS["mine_p3_LOG"], "SIM", "LOG"),
                                  "newgen_p0": delta_block(ARMS["newgen_p0_SIM"], ARMS["newgen_p0_LOG"], "SIM", "LOG"),
                                  "mine_p0": delta_block(ARMS["mine_p0_SIM"], ARMS["mine_p0_LOG"], "SIM", "LOG"),
                                  "mine_p3_cube1h": delta_block(ARMS["mine_p3_SIM_cube1h"], ARMS["mine_p3_LOG_cube1h"], "SIM", "LOG")}
    res["delta_cube_minus_panel_SIM_p3"] = delta_block(ARMS["mine_p3_SIM_cube1h"], ARMS["mine_p3_SIM"], "cube", "panel")
    log("deltas", json.dumps(res["delta_SIM_minus_LOG"]["mine_p3"]["S1"], default=str)[:600])

    # ---------------- convexity decomposition (fixed positions of the LOG arm; conv = expm1(L) − L)
    def conv_decomp(R, tag):
        RETL = R["meta"]["RETL"]; yr = R["meta"]["yr"]; n = R["meta"]["n"]
        CV = np.nan_to_num(np.expm1(RETL) - RETL)           # (n,N) >= 0
        grp = np.full(N, "alt", object); grp[btc_j] = "BTC"
        if eth_j >= 0: grp[eth_j] = "ETH"
        D = {}
        for k in [kk for kk in ("S1", "S0", "leg_king", "leg_s2", "leg_funding") if kk in R]:
            W = R[k]["W"].astype(np.float64); C = W * CV * 1e4   # bps contributions
            tot = C.sum(1)
            Dk = {"conv_mean_bps": round(float(tot.mean()), 4), "conv_sd": round(float(tot.std(ddof=1)), 3), "conv_t": round(float(tot.mean() / tot.std(ddof=1) * np.sqrt(n)), 2),
                  "conv_share_of_log_pnl": round(float(tot.mean() / R[k]["pnl"].mean()), 4) if abs(R[k]["pnl"].mean()) > 1e-9 else None,
                  "by_year": {int(y): round(float(tot[yr == y].mean()), 4) for y in sorted(set(yr.tolist()))},
                  "long_side": round(float(np.where(W > 0, C, 0).sum(1).mean()), 4), "short_side": round(float(np.where(W < 0, C, 0).sum(1).mean()), 4),
                  "by_group": {g: round(float(C[:, grp == g].sum(1).mean()), 4) for g in ("BTC", "ETH", "alt")},
                  "by_side_x_group": {f"{sd}_{g}": round(float(np.where((W > 0) if sd == "long" else (W < 0), C, 0)[:, grp == g].sum(1).mean()), 4)
                                      for sd in ("long", "short") for g in ("BTC", "ETH", "alt")},
                  "gross_by_side_x_group": {f"{sd}_{g}": round(float(np.where((W > 0) if sd == "long" else (W < 0), np.abs(W), 0)[:, grp == g].sum(1).mean()), 4)
                                            for sd in ("long", "short") for g in ("BTC", "ETH", "alt")},
                  "avg_|w|-weighted L^2/2 by side (bps)": {sd: round(float((np.where((W > 0) if sd == "long" else (W < 0), np.abs(W), 0) * CV).sum() / max(np.where((W > 0) if sd == "long" else (W < 0), np.abs(W), 0).sum(), 1e-9) * 1e4), 4) for sd in ("long", "short")}}
            per_name = C.sum(0) / n
            order = np.argsort(per_name)
            Dk["top10_names_negative"] = [(SYMS[j], round(float(per_name[j]), 4), round(float(W[:, j].mean()), 5)) for j in order[:10]]
            Dk["top5_names_positive"] = [(SYMS[j], round(float(per_name[j]), 4), round(float(W[:, j].mean()), 5)) for j in order[::-1][:5]]
            D[k] = Dk
        # rerun delta vs fixed-position convexity (S1): stop-path effect
        return D
    res["convexity_fixed_positions"] = {"mine_p3_LOG": conv_decomp(ARMS["mine_p3_LOG"], "mine_p3_LOG"), "newgen_p0_LOG": {k: v for k, v in conv_decomp(ARMS["newgen_p0_LOG"], "newgen_p0_LOG").items() if k in ("S0", "S1")}}
    for nm in ("mine_p3", "newgen_p0"):
        cf = res["convexity_fixed_positions"][nm + "_LOG"]["S1"]["conv_mean_bps"]; dr = res["delta_SIM_minus_LOG"][nm]["S1"]["delta_net_mean_bps"]
        res["delta_SIM_minus_LOG"][nm]["S1"]["stop_path_effect_bps(rerun_delta − fixed_conv)"] = round(float(dr - cf), 4)
    log("conv", json.dumps(res["convexity_fixed_positions"]["mine_p3_LOG"]["S1"], default=str)[:800])

    # ---------------- regime / worst quintiles / nominal hour (mine_p3, S1)
    A, B = ARMS["mine_p3_SIM"], ARMS["mine_p3_LOG"]; yr = A["meta"]["yr"]; ats = A["meta"]["ats"]
    xa, xb = A["S1"]["net"], B["S1"]["net"]; mk = B["meta"]["mkt_ew"]; bt = B["meta"]["btc4"]
    def qstats(var, name, worst_by="LOG"):
        v = np.where(np.isfinite(var), var, np.nan); edges = np.nanpercentile(v, [20, 40, 60, 80]); qi = np.digitize(v, edges); qi[~np.isfinite(v)] = -1
        rows = {}
        for q in range(5):
            s = qi == q
            rows[f"q{q}"] = {"n": int(s.sum()), "LOG_mean": round(float(xb[s].mean()), 3), "SIM_mean": round(float(xa[s].mean()), 3), "delta": round(float((xa - xb)[s].mean()), 3),
                             "LOG_sharpe_anchor": round(sharpe_anchor(xb[s]), 3), "SIM_sharpe_anchor": round(sharpe_anchor(xa[s]), 3), "var_mean": round(float(np.nanmean(v[s])), 2)}
        means = [rows[f"q{q}"]["LOG_mean"] for q in range(5)]; rows["worst_q_for_LOG_book"] = int(np.argmin(means))
        return rows
    res["regime_mine_p3_S1"] = {"by_mkt_ew_direction_quintile": qstats(mk, "mkt"), "by_abs_mkt_ew_quintile(q4=highest vol)": qstats(np.abs(mk), "absmkt"),
                                "by_abs_btc4_quintile(q4=highest)": qstats(np.abs(bt), "absbtc")}
    qb = np.percentile(xb, 20); s = xb <= qb
    res["regime_mine_p3_S1"]["book_worst_quintile_by_LOG_net"] = {"n": int(s.sum()), "LOG_mean": round(float(xb[s].mean()), 3), "SIM_mean": round(float(xa[s].mean()), 3), "delta": round(float((xa - xb)[s].mean()), 3)}
    hr = pd.to_datetime(ats, unit="s", utc=True).hour.to_numpy()
    res["by_nominal_hour_mine_p3_S1"] = {int(h): {"n": int((hr == h).sum()), "LOG": round(float(xb[hr == h].mean()), 3), "SIM": round(float(xa[hr == h].mean()), 3), "delta": round(float((xa - xb)[hr == h].mean()), 3)} for h in sorted(set(hr.tolist()))}
    # 2024-26 / 2026 sub-spans (published calibers)
    for lab, msk in (("2024_26", yr >= 2024), ("2026", yr == 2026), ("2022_23", yr <= 2023)):
        res.setdefault("subspans_mine_p3_S1", {})[lab] = {"LOG": {"mean": round(float(xb[msk].mean()), 4), "sharpe_anchor": round(sharpe_anchor(xb[msk]), 3), "sharpe_daily": round(sharpe_daily(xb[msk], ats[msk]), 3)},
                                                          "SIM": {"mean": round(float(xa[msk].mean()), 4), "sharpe_anchor": round(sharpe_anchor(xa[msk]), 3), "sharpe_daily": round(sharpe_daily(xa[msk], ats[msk]), 3)}}
    # ---------------- verdict (frozen reading)
    d1 = res["delta_SIM_minus_LOG"]["mine_p3"]["S1"]; ci = d1["boot_daily"]["delta_mean_ci95"]; dm = d1["delta_net_mean_bps"]
    receipts_ok = bool(R1["pass"] and R2["pass"] and R3["pass"])
    if not receipts_ok: verdict = "(c) 传闻: 收据未过 " + json.dumps({"R1": R1["pass"], "R2": R2["pass"], "R3": R3["pass"]})
    elif ci[0] <= 0 <= ci[1] and abs(dm) < 0.10: verdict = "(a) 对数口径无实质影响"
    elif not (ci[0] <= 0 <= ci[1]): verdict = "(b) 有系统偏差: CI 排除 0"
    else: verdict = "边缘: |Δ| ≥ 0.10 但 CI 含 0(按冻结读法不满足 (a) 的幅度条件也不满足 (b) 的 CI 条件; 如实报, 以 (b) 的保守方向处理绝对水平)"
    res["verdict_jp"] = {"S1_p3_delta_net_bps": dm, "ci95_daily_block": ci, "receipts_pass": receipts_ok, "reading": verdict}
    log("VERDICT", res["verdict_jp"])
    # ---------------- save
    ser = {}
    for nm, R in ARMS.items():
        ser[f"{nm}_ats"] = R["meta"]["ats"]
        for k in [kk for kk in ("S0", "S1", "leg_king", "leg_s2", "leg_funding") if kk in R]:
            for f in ("net", "pnl", "trn", "gross", "fires", "ic", "pnl_long", "pnl_short"):
                ser[f"{nm}_{k}_{f}"] = R[k][f]
    ser["mine_p3_LOG_W_S1"] = ARMS["mine_p3_LOG"]["S1"]["W"]; ser["mine_p3_SIM_W_S1"] = ARMS["mine_p3_SIM"]["S1"]["W"]
    ser["mine_p3_RETL"] = ARMS["mine_p3_LOG"]["meta"]["RETL"].astype(np.float32); ser["mine_p3_mkt_ew"] = ARMS["mine_p3_LOG"]["meta"]["mkt_ew"]; ser["mine_p3_btc4"] = ARMS["mine_p3_LOG"]["meta"]["btc4"]
    ser["symbols"] = np.array(SYMS)
    np.savez_compressed(OUT_NPZ, **ser)
    res["outputs"] = {"json": OUT_JSON, "npz": OUT_NPZ}
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=str)
    log("DONE ->", OUT_JSON)
    print(json.dumps({"R1": R1, "R2": R2, "R3": {k: R3[k] for k in ("pass", "per_anchor_corr_median", "median_abs_diff_bps", "maxabs_diff")},
                      "S1_p3": {"LOG": out["mine_p3_LOG"]["S1"]["net@4.137"], "SIM": out["mine_p3_SIM"]["S1"]["net@4.137"]},
                      "delta_S1_p3": {k: v for k, v in d1.items() if k != "boot_anchor_block42_delta_sharpe"}, "verdict": res["verdict_jp"]}, indent=1, ensure_ascii=False, default=str))


# ====================================================================== LOCAL stage (live reconciliation + merge)
def stage_local():
    HERE = os.path.dirname(os.path.abspath(__file__))
    LIVE = os.path.expanduser("~/dl_quant_live"); PLOG = f"{LIVE}/state/live/pilot_log"; KC = f"{LIVE}/state/panel_cache/klines_1h.npz"
    OUT = f"{HERE}/results/inrole_simple_return_rerun_2026-08-22.json"; JP_JSON = f"{HERE}/results/inrole_simple_return_rerun_jp_2026-08-22.json"
    D0, D1 = "20260805", "20260822"; HOUR = 3600
    res = {"session": SESSION, "stage": "local+merge", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script_sha256": sha(os.path.abspath(__file__)),
           "A_fact_alignment": {
               "offline_family_return_input": "Y4 = log CLOSE[T+4]/CLOSE[T], 1h K 线 close(非 5m 合成, 非 VWAP), 未剪裁 — multi_asset/data/build_wide_dl.py:95,151 `logc=np.log(C)`, `Y[:T-H]=logc[H:]-logc[:-H]`; engine/panel_source.py:34 注释 'raw 4h fwd logret'; PH 收据 Y4=ΣY1 4.2e-8",
               "offline_family_pnl_line": "engine/replay_fullhist.py:120-123 `ret=src.Y4[t,m]; pnl=Σ p*ret`; devices w2_live_replay.py / phase_alignment_replay_jp.py `c[idx]=w*y*1e4` with y=src.Y4 ⇒ Σ w·log 收益; 止损价格路径 `Pi=Pi*(1+y)` 把对数当简单复利(小偏差, 简单版下变为精确 Pi=Pi*exp(L))",
               "live_engine_pnl_accounting": "场所权益: nav = totalWalletBalance + totalUnrealizedProfit (/fapi/v3/account) — ~/dl_quant_live/scheduler/anchor_loop.py:2171-2187; 未实现 = qty×(mark−entry), 已实现 = qty×(exit−entry) ⇒ 持仓名义 × 简单价格变化, 逐锚 mark(nav_ts≈N+17min); 逐锚盈亏 = 相邻 daily_nav.nav 之差 − external_flow(FIELD_CALIBERS 行 2-4)",
               "live_window": "[N, N+4h](PH §3 B: ρ0.96 vs 离线窗 0.72); 1h K 线表达 = CLOSE[N+3h bar]/CLOSE[N−1h bar]",
               "conclusion": "离线族 = Σ w·log(P_{+4h}/P); 实盘 = Σ w·(P_{+4h}/P − 1)。两者差 = Σ w·(expm1(L)−L) ≥0 对多头 / ≤0 对空头。"}}
    # ---------------- live reconciliation (PH part_B loader, extended with log/simple dual pricing)
    days = sorted(d for d in os.listdir(PLOG) if d.isdigit() and D0 <= d <= D1)
    A, R, NV = [], [], []
    for d in days:
        for nm, lst in (("anchors", A), ("position_readback", R), ("daily_nav", NV)):
            f = f"{PLOG}/{d}/{nm}.jsonl"
            if os.path.exists(f):
                for line in open(f):
                    line = line.strip()
                    if line:
                        row = json.loads(line); row["_day"] = d; lst.append(row)
    z = np.load(KC, allow_pickle=True); kts = z["ts"].astype(np.int64) // 1000; ksym = [str(s) for s in z["symbols"]]; C = z["close"]
    kidx = {int(t): i for i, t in enumerate(kts)}; sidx = {s: j for j, s in enumerate(ksym)}
    def px(sym, t_open):
        i = kidx.get(int(t_open)); j = sidx.get(sym)
        if i is None or j is None: return np.nan
        return float(C[i, j])
    anc = []
    for a in A:
        if str(a.get("rebalance_id", "")).startswith("R"): continue
        Nn = int(round(a["anchor_ts"] / 14400.0) * 14400)
        if abs(a["anchor_ts"] - Nn) > 20 * 60: continue
        anc.append({"N": Nn, "anchor_ts": float(a["anchor_ts"]), "mids": json.loads(a["mid_at_anchor_vector"]) if isinstance(a.get("mid_at_anchor_vector"), str) else (a.get("mid_at_anchor_vector") or {}), "day": a["_day"]})
    anc.sort(key=lambda r: r["N"]); byN = {r["N"]: r for r in anc}
    held = {}
    for r in R:
        if r.get("source") != "fapi/v3/account@post_anchor": continue
        Nn = int(round(float(r["anchor_ts"]) / 14400.0) * 14400)
        v = r.get("venue_position_notional")
        if v is None or not np.isfinite(float(v)) or abs(float(v)) < 1e-9: continue
        held.setdefault(Nn, {})[r["symbol"]] = float(v)
    navs = []
    for n_ in NV:
        nt = float(n_["nav_ts"]); Nn = int(round(nt / 14400.0) * 14400)
        if abs(nt - Nn) > 30 * 60: continue
        bt = n_.get("realised_by_type") or {}
        navs.append({"N": Nn, "nav": float(n_["nav"]), "day": n_["_day"], "flow": float(n_.get("external_flow_usdt") or 0.0),
                     "comm": float(bt.get("COMMISSION") or 0.0), "fund": float(bt.get("FUNDING_FEE") or 0.0)})
    navs.sort(key=lambda r: r["N"]); navN = {r["N"]: r for r in navs}
    rows = []
    for Nn in sorted(set(held) & set(byN)):
        if not (pd.Timestamp("2026-08-05", tz="UTC").timestamp() <= Nn <= pd.Timestamp("2026-08-21 20:00", tz="UTC").timestamp()): continue
        w = held[Nn]; a = byN[Nn]; gross = sum(abs(v) for v in w.values()); nxt = byN.get(Nn + 14400)
        p_sim = p_log = 0.0; cov = 0.0; p_sim3 = p_log3 = 0.0; cov3 = 0.0; g_long = 0.0
        for s, v in w.items():
            b0, b4 = px(s, Nn - HOUR), px(s, Nn + 3 * HOUR)
            if np.isfinite(b0) and np.isfinite(b4) and b0 > 0:
                p_sim += v * (b4 / b0 - 1.0); p_log += v * np.log(b4 / b0); cov += abs(v)
                if v > 0: g_long += v
            if nxt is not None:
                m0 = a["mids"].get(s); m1 = nxt["mids"].get(s)
                if m0 and m1 and m0 > 0: p_sim3 += v * (m1 / m0 - 1.0); p_log3 += v * np.log(m1 / m0); cov3 += abs(v)
        nv0 = navN.get(Nn); nv1 = navN.get(Nn + 14400)
        dnav = dflow = dcomm = dfund = np.nan
        if nv0 and nv1:
            dnav = nv1["nav"] - nv0["nav"]; same_day = nv0["day"] == nv1["day"]
            dflow = (nv1["flow"] - nv0["flow"]) if same_day else nv1["flow"]
            dcomm = (nv1["comm"] - nv0["comm"]) if same_day else nv1["comm"]
            dfund = (nv1["fund"] - nv0["fund"]) if same_day else nv1["fund"]
        rows.append({"N": Nn, "N_utc": pd.Timestamp(Nn, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%MZ"), "day": a["day"], "n_held": len(w), "gross_held": gross, "gross_long": g_long,
                     "pnl_sim_1h": p_sim, "pnl_log_1h": p_log, "conv_1h": p_sim - p_log, "cov_1h": cov / gross if gross else np.nan,
                     "pnl_sim_mids": (p_sim3 if nxt is not None else np.nan), "pnl_log_mids": (p_log3 if nxt is not None else np.nan), "cov_mids": (cov3 / gross if (gross and nxt is not None) else np.nan),
                     "dnav": dnav, "dflow": dflow, "dcomm": dcomm, "dfund": dfund, "dnav_ex_flow": (dnav - dflow) if np.isfinite(dnav) else np.nan,
                     "dnav_gross_equiv": (dnav - dflow - dcomm - dfund) if np.isfinite(dnav) else np.nan})
    df = pd.DataFrame(rows); ok = df[(df["cov_1h"] >= 0.95) & np.isfinite(df["dnav"])].copy()
    def stats(d):
        o = {"n": int(len(d))}
        if len(d) < 5: return o
        gs = d.gross_held.values
        o["gross_held_mean"] = round(float(gs.mean()), 1); o["sum_gross_long_over_gross"] = round(float(d.gross_long.sum() / gs.sum()), 4)
        o["conv_usdt_total"] = round(float(d.conv_1h.sum()), 2); o["conv_usdt_mean_per_anchor"] = round(float(d.conv_1h.mean()), 3)
        o["conv_bps_of_gross_mean"] = round(float((d.conv_1h / d.gross_held).mean() * 1e4), 4); o["conv_bps_of_gross_sd"] = round(float((d.conv_1h / d.gross_held).std(ddof=1) * 1e4), 4)
        o["conv_bps_t"] = round(float((d.conv_1h / d.gross_held).mean() / (d.conv_1h / d.gross_held).std(ddof=1) * np.sqrt(len(d))), 2)
        o["pnl_sim_bps_of_gross_mean"] = round(float((d.pnl_sim_1h / d.gross_held).mean() * 1e4), 3); o["pnl_log_bps_of_gross_mean"] = round(float((d.pnl_log_1h / d.gross_held).mean() * 1e4), 3)
        o["conv_share_of_log_pnl"] = round(float(d.conv_1h.sum() / d.pnl_log_1h.sum()), 4) if abs(d.pnl_log_1h.sum()) > 1e-9 else None
        gt = float(gs.sum())
        o["money_weighted_bps(total/total_gross)"] = {"conv": round(float(d.conv_1h.sum() / gt * 1e4), 4), "pnl_sim": round(float(d.pnl_sim_1h.sum() / gt * 1e4), 4), "pnl_log": round(float(d.pnl_log_1h.sum() / gt * 1e4), 4),
                                                      "dnav_gross_equiv": round(float(np.nansum(d.dnav_gross_equiv.values) / gt * 1e4), 4), "dnav_ex_flow": round(float(np.nansum(d.dnav_ex_flow.values) / gt * 1e4), 4)}
        o["gross_held_range"] = [round(float(gs.min()), 1), round(float(gs.max()), 1)]
        m3 = np.isfinite(d.pnl_sim_mids.values)
        if m3.sum() >= 5:
            o["conv_mids_bps_of_gross_mean"] = round(float(((d.pnl_sim_mids - d.pnl_log_mids) / d.gross_held)[m3].mean() * 1e4), 4)
        for tgt in ("dnav_ex_flow", "dnav_gross_equiv"):
            y = d[tgt].values; mm = np.isfinite(y)
            o[f"vs_{tgt}"] = {"n": int(mm.sum()), "target_sum": round(float(y[mm].sum()), 2), "target_mean": round(float(y[mm].mean()), 3)}
            for nm, x in (("sim_1h", d.pnl_sim_1h.values), ("log_1h", d.pnl_log_1h.values), ("sim_mids", d.pnl_sim_mids.values), ("log_mids", d.pnl_log_mids.values)):
                m2 = mm & np.isfinite(x)
                if m2.sum() < 5: continue
                sl, ic = np.polyfit(x[m2], y[m2], 1); resid = y[m2] - x[m2]
                o[f"vs_{tgt}"][nm] = {"rho": round(float(np.corrcoef(x[m2], y[m2])[0, 1]), 4), "slope": round(float(sl), 3), "intercept": round(float(ic), 3),
                                      "mae": round(float(np.abs(resid).mean()), 3), "rmse": round(float(np.sqrt((resid ** 2).mean())), 3),
                                      "mean_resid(target−x)": round(float(resid.mean()), 3), "resid_t": round(float(resid.mean() / resid.std(ddof=1) * np.sqrt(m2.sum())), 2),
                                      "sum_x": round(float(x[m2].sum()), 2), "sum_target": round(float(y[m2].sum()), 2)}
        return o
    incident = {"20260821"}
    flow_anchors = ok[(np.abs(ok.dflow) > 1e-6)]
    ok_clean = ok[(~ok.day.isin(incident)) & (np.abs(ok.dflow) <= 1e-6)]
    res["C_live_reconciliation"] = {"inputs": {"klines_cache_sha256": sha(KC), "klines_span_utc": [str(pd.Timestamp(int(kts[0]), unit="s", tz="UTC")), str(pd.Timestamp(int(kts[-1]), unit="s", tz="UTC"))], "pilot_log_days": [D0, D1]},
                                    "n_anchors_total": int(len(df)), "n_anchors_priced": int(len(ok)), "n_anchors_with_transfer": int(len(flow_anchors)),
                                    "transfer_anchors": [str(x) for x in flow_anchors.N_utc.tolist()],
                                    "all_priced": stats(ok), "clean(ex 08-21 incident, ex transfer anchors)": stats(ok_clean),
                                    "by_day_conv_bps": {str(d): round(float((g.conv_1h / g.gross_held).mean() * 1e4), 3) for d, g in ok.groupby("day")},
                                    "per_anchor": [{k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()} for r in ok.to_dict("records")]}
    s = res["C_live_reconciliation"]["clean(ex 08-21 incident, ex transfer anchors)"]
    try:
        vs = s["vs_dnav_gross_equiv"]; r_sim = vs["sim_1h"]; r_log = vs["log_1h"]
        res["C_live_reconciliation"]["verdict_C"] = {"sim_mean_resid": r_sim["mean_resid(target−x)"], "log_mean_resid": r_log["mean_resid(target−x)"], "sim_mae": r_sim["mae"], "log_mae": r_log["mae"],
                                                     "sim_rho": r_sim["rho"], "log_rho": r_log["rho"], "conv_bps_of_gross_live": s["conv_bps_of_gross_mean"], "conv_bps_t": s["conv_bps_t"],
                                                     "closer_to_live": ("simple" if (abs(r_sim["mean_resid(target−x)"]) <= abs(r_log["mean_resid(target−x)"]) and r_sim["mae"] <= r_log["mae"]) else ("log" if (abs(r_log["mean_resid(target−x)"]) < abs(r_sim["mean_resid(target−x)"]) and r_log["mae"] < r_sim["mae"]) else "mixed(均残差与 MAE 不同向)"))}
    except Exception as e:
        res["C_live_reconciliation"]["verdict_C"] = {"error": repr(e)}
    if os.path.exists(JP_JSON):
        jp = json.load(open(JP_JSON)); res["B_jp_rerun"] = jp; res["B_jp_json_sha256"] = sha(JP_JSON)
    else:
        res["B_jp_rerun"] = {"status": "jp JSON not present at " + JP_JSON}
    # ---- post-hoc on the jp series (if the npz was copied into results/): 触线概率(w2b_common.trip 同式: 180 锚块自助 1 年路径, 峰值回撤 ≤ −25% / 自起点 ≤ −25%), 两口径
    JP_NPZ = JP_JSON.replace(".json", ".npz")
    if os.path.exists(JP_NPZ):
        S = np.load(JP_NPZ, allow_pickle=True); NY = 2190
        def trip(x, g, seed=11, Lb=180, reps=2000):
            rng = np.random.RandomState(seed); nb = len(x) // Lb; nbk = NY // Lb + 1; hp = 0; hs = 0; ann = []
            for _ in range(reps):
                idx = rng.randint(0, nb, nbk); path = np.concatenate([x[i * Lb:(i + 1) * Lb] for i in idx])[:NY] * g / 1e4
                cum = np.cumprod(1 + path); dd = cum / np.maximum.accumulate(cum) - 1
                hp += dd.min() <= -0.25; hs += cum.min() <= 0.75; ann.append(cum[-1] - 1)
            return {"P_peakDD_-25%": round(hp / reps, 4), "P_fromstart_-25%": round(hs / reps, 4), "ann_median": round(float(np.median(ann)), 4), "ann_p5": round(float(np.percentile(ann, 5)), 4)}
        TP = {}
        for arm in ("mine_p3_LOG", "mine_p3_SIM", "newgen_p0_LOG", "newgen_p0_SIM"):
            for k in ("S1", "S0"):
                key = f"{arm}_{k}_net"
                if key in S.files:
                    x = S[key].astype(float); TP[f"{arm}_{k}"] = {"gross_2.0": trip(x, 2.0), "gross_1.0": trip(x, 1.0), "mean_bps": round(float(x.mean()), 4)}
        res["B_trip_probability_post_hoc"] = {"caliber": "w2b_common.trip 同式(W2 触线概率口径): 180 锚块自助 1 年(2190 锚)路径 ×2000, 恒定 gross, 峰值回撤 ≤ −25% / 自起点 ≤ −25%", "arms": TP, "npz_sha256": sha(JP_NPZ)}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False, default=str)
    c = res["C_live_reconciliation"]
    print(json.dumps({"n": [c["n_anchors_total"], c["n_anchors_priced"], c["n_anchors_with_transfer"]], "clean": {k: v for k, v in c["clean(ex 08-21 incident, ex transfer anchors)"].items() if k != "per_anchor"},
                      "all": {k: v for k, v in c["all_priced"].items()}, "verdict_C": c.get("verdict_C"), "by_day_conv_bps": c["by_day_conv_bps"]}, indent=1, ensure_ascii=False, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    stage_jp() if STAGE == "jp" else stage_local()
