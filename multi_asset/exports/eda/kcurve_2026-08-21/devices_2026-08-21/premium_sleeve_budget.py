"""§4.3 保费 sleeve 风险预算化 · 纸面叠加装置(第一轮, 2026-08-22, Session 6737834a-P2)
===========================================================================================
输入(只读, SHA256 钉定; 不碰实盘仓/share/交易 API):
  multi_asset/exports/eda/kcurve_2026-08-21/devices_2026-08-21/results/series/w2_live_series_slim.npz
  SHA256 = 502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003
  (在役回放 9821 锚 2022-01-01→2026-06-29, 实盘 compose_book 原样 import; S1=在役逐名止损; 字段: S1_net/S1_carry/S0_gross/mkt_ew/btc4/yr/ts)

口径(与 RESULT_two_book_allocation §0.2/§1 主口径同式):
  net_t = (S1_net_t − S1_carry_t) / S0_gross_t × G(G=2.0) = bps of NAV @gross2, 含 carry, 扣 4.137×换手;
  敏感性: S1 不含 carry / S0(无止损)含 carry。年化 √(6×365)。
  r_s,t = mkt_ew_t − btc4_t(等权山寨−BTC 同锚 4h 收益, bps; mkt_ew 含 BTC/ETH 各 1/N, 与前装置 ex-BTC/ETH 差 ~1%)。

装置(纸面叠加, 不改书):
  β̂_{t−1} = 只用 [t−Wb, t−1] 的 OLS 斜率(net 对 r_s, 带截距), Wb ∈ {90,180,360};
  sleeve_t = β̂_{t−1}·r_s,t(归因, 用同锚 r_s); resid_t = net_t − sleeve_t;
  σ̂_{t−1} = sleeve 在 [t−Ws, t−1] 的滚动 sd, Ws ∈ {30,60,120}; σ* = 全史 σ̂ 的分位数 q ∈ {40,50,60}%(主臂 50=中位数);
  m_t = min(1, σ*/σ̂_{t−1}); net'_t = resid_t + m_t·sleeve_t − cost_t;
  cost_t = |m_t − m_{t−1}|·|β̂_{t−1}|·G·4 bps(对冲腿换手近似, 保守; 敏感性 ×2 与"精确对冲名义变化"口径)。
  热身段(无估计)m=1; 评估窗 = 所有臂共同可用起点 i0 = 360+120 = 480(2022-03-21 起), 基线同窗。

★ 冻结判据(看数字前写定; 主臂 = Wb180 / Ws60 / q50, 评估窗 i0 起, 主口径):
  C1 净夏普(主臂) ≥ 基线 + 0.10
  C2 普涨锚(评估窗内 r_s 最高 5% 的锚)净额均值改善 ≥ 30%: (mean'_top − mean_top)/|mean_top| ≥ 0.30(mean_top<0)
  C3 2026 年净额均值 ≥ 基线
  C4 逐年(2022–2026)年度夏普 ≥ 基线 的年数 ≥ 4/5(年度净额版本并列报告, 不作主判)
  全过 ⇒ 进二审(书级装置); 任一不过 ⇒ 判负。网格/分位只作敏感性, 不许事后选臂。
对照: ①不动 ②全书 vol-targeting(同 Ws60/σ*=中位, m·net − |Δm|·G·4; 复现已判负方向) ③静态部分对冲 h=0.5·β̂_{t−1}(校验"对冲毁收益"方向);
      校准块: 全样本 β/r/逐年 β/h=1.0 全对冲 vs 前装置(β −0.249/r −0.767/h1 夏普 0.59)。
红队: 口径(m 只用 t−1; sleeve 同锚归因非预测) / 泄漏(σ* 全史分位 = 水平泄漏 ⇒ 因果扩张中位数臂) / 选择效应(全网格通过数 + 反向规则安慰剂) / regime(逐年, 市场方向五分位)。
输出: results/premium_sleeve_budget_2026-08-21.json
"""
import sys, json, time, hashlib, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NPZ = os.path.join(HERE, "results", "series", "w2_live_series_slim.npz")
NPZ_SHA = "502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003"
OUT = os.path.join(HERE, "results", "premium_sleeve_budget_2026-08-21.json")
G = 2.0; ANN = np.sqrt(6 * 365); COST_BPS = 4.0
WB_GRID = (90, 180, 360); WS_GRID = (30, 60, 120); Q_GRID = (40, 50, 60)
MAIN = (180, 60, 50)
I0 = max(WB_GRID) + max(WS_GRID)  # 480
FROZEN = {"C1_sharpe_gain_min": 0.10, "C2_top_spread_loss_improve_min": 0.30, "C3_2026_mean_not_worse": True, "C4_yearly_sharpe_not_worse_min": 4,
          "main_arm": {"Wb": 180, "Ws": 60, "q": 50}, "eval_start_index": I0, "top_spread_quantile": 0.95, "cost_bps_per_unit": COST_BPS, "G": G}

sha = hashlib.sha256(open(NPZ, "rb").read()).hexdigest()
assert sha == NPZ_SHA, f"input SHA mismatch {sha}"
z = np.load(NPZ, allow_pickle=True)
ts = z["ts"].astype(np.int64); yr = z["yr"].astype(int); n = len(ts)
rs = (z["mkt_ew"] - z["btc4"]).astype(float); mkt = z["mkt_ew"].astype(float)
assert np.isfinite(rs).all() and np.isfinite(z["S1_net"]).all()
SERIES = {
    "primary_S1_carry": (z["S1_net"] - np.nan_to_num(z["S1_carry"])) / z["S0_gross"] * G,
    "S1_nocarry": z["S1_net"] / z["S0_gross"] * G,
    "S0_carry": (z["S0_net"] - np.nan_to_num(z["S0_carry"])) / z["S0_gross"] * G,
}
YEARS = sorted(set(yr.tolist()))


def sharpe(x):
    s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")


def roll_sum(a, W):
    """S[t] = sum a[t-W:t] (window ends at t-1), NaN where t<W."""
    c = np.concatenate([[0.0], np.cumsum(a)]); out = np.full(len(a), np.nan)
    out[W:] = c[W:len(a)] - c[:len(a) - W]; return out


def roll_beta(y, x, W):
    """OLS slope of y on x (with intercept) over [t-W, t-1]; defined for t>=W."""
    Sx, Sy, Sxx, Sxy = roll_sum(x, W), roll_sum(y, W), roll_sum(x * x, W), roll_sum(x * y, W)
    cov = Sxy - Sx * Sy / W; var = Sxx - Sx * Sx / W
    with np.errstate(invalid="ignore", divide="ignore"):
        return cov / var


def roll_sd(a, W, start):
    """rolling sd(ddof=1) of a over [t-W, t-1], only using a[start:] (a undefined before start)."""
    b = np.where(np.arange(len(a)) >= start, a, 0.0)
    S1, S2 = roll_sum(b, W), roll_sum(b * b, W)
    with np.errstate(invalid="ignore"):
        v = (S2 - S1 * S1 / W) / (W - 1)
    out = np.sqrt(np.maximum(v, 0.0)); out[: start + W] = np.nan; return out


def causal_quantile_series(v, q, start, min_n=180):
    """σ*_t = quantile of v[start:t] (past only); NaN until min_n values."""
    out = np.full(len(v), np.nan)
    for t in range(start + min_n, len(v)):
        out[t] = np.percentile(v[start:t], q)
    return out


def maxdd(x):
    nav = np.cumprod(1.0 + x / 1e4); return float((nav / np.maximum.accumulate(nav) - 1.0).min())


def es5(x):
    k = max(1, int(round(0.05 * len(x)))); return float(np.sort(x)[:k].mean())


def yearly(x, y):
    return {int(v): {"mean": float(x[y == v].mean()), "sharpe": sharpe(x[y == v]), "n": int((y == v).sum())} for v in YEARS if (y == v).sum() > 10}


def overlay(net, Wb, Ws, q, sigma_mode="global", cost_mode="lead", reverse=False, cost_mult=1.0):
    """returns dict of series: beta, sleeve, resid, sig, m, cost, netp (all length n)."""
    beta = roll_beta(net, rs, Wb)                     # β̂_{t-1}, valid t>=Wb
    sleeve = np.where(np.isfinite(beta), beta * rs, np.nan)
    sig = roll_sd(np.nan_to_num(sleeve), Ws, Wb)      # σ̂_{t-1}, valid t>=Wb+Ws
    valid = np.isfinite(sig)
    if sigma_mode == "global":
        sstar = np.full(n, np.percentile(sig[valid], q))
    elif sigma_mode == "causal":
        sstar = causal_quantile_series(sig, q, Wb + Ws)
    elif sigma_mode == "uncond":  # alternative reading of "全史 sleeve 波动": unconditional full-history sd of the sleeve P&L
        sstar = np.full(n, np.nanstd(sleeve[valid], ddof=1))
    else:
        raise ValueError(sigma_mode)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = sstar / sig
        if reverse: ratio = sig / sstar
    m = np.where(np.isfinite(ratio), np.minimum(1.0, ratio), 1.0)
    b0 = np.nan_to_num(beta)
    m_prev = np.concatenate([[1.0], m[:-1]])
    if cost_mode == "lead":
        cost = np.abs(m - m_prev) * np.abs(b0) * G * COST_BPS
    elif cost_mode == "exact":  # hedge notional h_t=(1-m_t)β̂_{t-1}; turnover = |h_t - h_{t-1}| on each side (×2 sides)
        h = (1.0 - m) * b0; h_prev = np.concatenate([[0.0], h[:-1]])
        cost = np.abs(h - h_prev) * G * COST_BPS * 2.0
    else:
        raise ValueError(cost_mode)
    cost = cost * cost_mult
    slv = np.nan_to_num(sleeve)
    netp = net - (1.0 - m) * slv - cost
    return dict(beta=beta, sleeve=sleeve, resid=net - slv, sig=sig, sstar=sstar, m=m, cost=cost, netp=netp)


def evaluate(base, alt, ev, top_mask, label=""):
    """metrics on eval window ev (bool mask). top_mask: 普涨锚 within ev."""
    b, a = base[ev], alt[ev]; yb = yr[ev]
    yb_b, yb_a = yearly(b, yb), yearly(a, yb)
    ys_cnt = sum(1 for v in yb_b if yb_a[v]["sharpe"] >= yb_b[v]["sharpe"])
    ym_cnt = sum(1 for v in yb_b if yb_a[v]["mean"] >= yb_b[v]["mean"])
    tb, ta = base[top_mask].mean(), alt[top_mask].mean()
    imp = float((ta - tb) / abs(tb)) if tb < 0 else float("nan")
    r = {"label": label, "n_eval": int(ev.sum()),
         "base": {"mean": float(b.mean()), "sd": float(b.std(ddof=1)), "sharpe": sharpe(b), "maxDD": maxdd(b), "ES5": es5(b), "by_year": yb_b},
         "alt": {"mean": float(a.mean()), "sd": float(a.std(ddof=1)), "sharpe": sharpe(a), "maxDD": maxdd(a), "ES5": es5(a), "by_year": yb_a},
         "d_sharpe": sharpe(a) - sharpe(b), "d_mean": float(a.mean() - b.mean()), "d_mean_pct": float((a.mean() - b.mean()) / abs(b.mean())),
         "top_spread": {"n": int(top_mask.sum()), "base_mean": float(tb), "alt_mean": float(ta), "improve_frac": imp},
         "yearly_sharpe_not_worse": int(ys_cnt), "yearly_mean_not_worse": int(ym_cnt), "n_years": len(yb_b),
         "y2026": {"base_mean": yb_b.get(2026, {}).get("mean"), "alt_mean": yb_a.get(2026, {}).get("mean")}}
    c1 = r["d_sharpe"] >= FROZEN["C1_sharpe_gain_min"]
    c2 = (imp >= FROZEN["C2_top_spread_loss_improve_min"]) if np.isfinite(imp) else False
    c3 = (yb_a[2026]["mean"] >= yb_b[2026]["mean"]) if 2026 in yb_b else False
    c4 = ys_cnt >= FROZEN["C4_yearly_sharpe_not_worse_min"]
    r["criteria"] = {"C1_sharpe": bool(c1), "C2_top_spread": bool(c2), "C3_2026": bool(c3), "C4_yearly_sharpe": bool(c4), "PASS": bool(c1 and c2 and c3 and c4)}
    return r


def block_boot(base, alt, ev, L=180, B=2000, seed=7):
    b, a = base[ev], alt[ev]; N = len(b); nb = N // L; rng = np.random.RandomState(seed); d = np.empty(B)
    for k in range(B):
        idx = rng.randint(0, nb, nb + 1); sel = np.concatenate([np.arange(i * L, (i + 1) * L) for i in idx])[:N]
        d[k] = sharpe(a[sel]) - sharpe(b[sel])
    return {"block": L, "B": B, "d_sharpe_mean": float(d.mean()), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "P_ge_0.10": float((d >= 0.10).mean()), "P_ge_0": float((d >= 0).mean())}


t0 = time.time()
RES = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-P2", "python": sys.version.split()[0], "numpy": np.__version__, "input": os.path.relpath(NPZ, HERE), "input_sha256": sha,
                "n_anchors": int(n), "first": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[0]))), "last": time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts[-1]))),
                "caliber": "net=(S1_net−S1_carry)/S0_gross×2 bps of NAV @gross2; r_s=mkt_ew−btc4 bps; ann √(6×365)", "frozen_criteria": FROZEN}}

# ---------- 0. calibration vs prior device (raw S1_net caliber, full-sample β) ----------
net_raw = z["S1_net"].astype(float)
bfull = float(np.cov(net_raw, rs)[0, 1] / np.var(rs, ddof=1)); rfull = float(np.corrcoef(net_raw, rs)[0, 1])
cal = {"beta_full_S1_net_on_rs": bfull, "r": rfull, "r2": rfull ** 2, "rs_mean_bps": float(rs.mean()), "rs_sd": float(rs.std(ddof=1)),
       "beta_by_year": {int(v): float(np.cov(net_raw[yr == v], rs[yr == v])[0, 1] / np.var(rs[yr == v], ddof=1)) for v in YEARS},
       "premium_share_of_mean": float(bfull * rs.mean() / net_raw.mean()),
       "S1_net_mean": float(net_raw.mean()), "S1_net_sharpe": sharpe(net_raw),
       "static_hedge_fullbeta": {f"h{h}": {"mean": float((net_raw - h * bfull * rs).mean()), "sharpe": sharpe(net_raw - h * bfull * rs)} for h in (0.25, 0.5, 1.0)},
       "prior_device_ref": {"beta": -0.249, "r": -0.767, "by_year": [-0.22, -0.28, -0.25, -0.24, -0.30], "rs_mean": -3.54, "h1_sharpe": 0.59, "h0.5_sharpe": 1.25,
                            "note": "前装置 altspread_hedge_overlay.py 用 ex-BTC/ETH 等权山寨且叠加层含 funding carry 项; 本处 mkt_ew 含 BTC/ETH 各 1/N 且不计对冲 carry ⇒ 允许 ~0.01 β / ~0.1 夏普 差"}}
RES["calibration"] = cal
print("CAL", json.dumps({k: cal[k] for k in ("beta_full_S1_net_on_rs", "r", "rs_mean_bps", "premium_share_of_mean")}), flush=True)

# ---------- 1. main arm + grid on primary caliber ----------
ev = np.arange(n) >= I0
for tag, net in SERIES.items():
    top_thr = np.percentile(rs[ev], 95)
    top = ev & (rs >= top_thr)
    top_mkt = ev & (mkt >= np.percentile(mkt[ev], 95))
    top_abs = ev & (np.abs(rs) >= np.percentile(np.abs(rs[ev]), 95))
    bot = ev & (rs <= np.percentile(rs[ev], 5))
    out = {"top_spread_threshold_bps": float(top_thr), "base_full": {"mean": float(net.mean()), "sharpe": sharpe(net), "by_year": yearly(net, yr)}}
    # main arm
    Wb, Ws, q = MAIN
    o = overlay(net, Wb, Ws, q)
    main = evaluate(net, o["netp"], ev, top, label=f"main Wb{Wb}/Ws{Ws}/q{q}")
    main["m_stats"] = {"mean_m": float(o["m"][ev].mean()), "frac_m_lt_1": float((o["m"][ev] < 1).mean()), "p10_m": float(np.percentile(o["m"][ev], 10)),
                       "mean_abs_dm": float(np.abs(np.diff(o["m"][ev])).mean()), "cost_total_bps": float(o["cost"][ev].sum()), "cost_per_year_bps": float(o["cost"][ev].sum() / (ev.sum() / 2190)),
                       "beta_mean": float(np.nanmean(o["beta"][ev])), "beta_sd": float(np.nanstd(o["beta"][ev])), "beta_p5_p95": [float(np.nanpercentile(o["beta"][ev], 5)), float(np.nanpercentile(o["beta"][ev], 95))],
                       "sigma_star": float(o["sstar"][ev][0]), "sig_median": float(np.nanmedian(o["sig"][ev])),
                       "sleeve_mean": float(np.nanmean(o["sleeve"][ev])), "sleeve_sd": float(np.nanstd(o["sleeve"][ev])), "sleeve_sharpe": sharpe(np.nan_to_num(o["sleeve"][ev])),
                       "resid_mean": float(o["resid"][ev].mean()), "resid_sharpe": sharpe(o["resid"][ev]), "corr_sleeve_resid": float(np.corrcoef(np.nan_to_num(o["sleeve"][ev]), o["resid"][ev])[0, 1])}
    # mechanism: does high sleeve-vol predict worse sleeve Sharpe next anchor? (the only way budgeting can help)
    sv = o["sig"][ev]; sl = np.nan_to_num(o["sleeve"][ev]); nn = net[ev]
    qs = np.nanpercentile(sv, [20, 40, 60, 80]); bins = np.digitize(sv, qs)
    main["mechanism_by_sigma_quintile"] = {int(k): {"sleeve_mean": float(sl[bins == k].mean()), "sleeve_sd": float(sl[bins == k].std(ddof=1)), "sleeve_sharpe": sharpe(sl[bins == k]),
                                                     "net_mean": float(nn[bins == k].mean()), "net_sharpe": sharpe(nn[bins == k]), "n": int((bins == k).sum())} for k in range(5)}
    # alternative 普涨 definitions (descriptive)
    main["top_defs"] = {"top5_mkt_ew": {"base": float(net[top_mkt].mean()), "alt": float(o["netp"][top_mkt].mean())},
                        "top5_abs_spread": {"base": float(net[top_abs].mean()), "alt": float(o["netp"][top_abs].mean())},
                        "bottom5_spread": {"base": float(net[bot].mean()), "alt": float(o["netp"][bot].mean())}}
    main["bootstrap"] = block_boot(net, o["netp"], ev)
    # regime: market-direction quintiles & bear/bull
    mq = np.percentile(mkt[ev], [20, 40, 60, 80]); mb = np.digitize(mkt[ev], mq)
    main["regime_mkt_quintile"] = {int(k): {"base_mean": float(net[ev][mb == k].mean()), "alt_mean": float(o["netp"][ev][mb == k].mean())} for k in range(5)}
    bear = ev & (yr == 2022); bull = ev & (yr >= 2025)
    main["regime_bear_bull"] = {"2022": {"base": {"mean": float(net[bear].mean()), "sharpe": sharpe(net[bear])}, "alt": {"mean": float(o["netp"][bear].mean()), "sharpe": sharpe(o["netp"][bear])}},
                                "2025_26": {"base": {"mean": float(net[bull].mean()), "sharpe": sharpe(net[bull])}, "alt": {"mean": float(o["netp"][bull].mean()), "sharpe": sharpe(o["netp"][bull])}}}
    # sensitivities on the main arm
    sens = {}
    for nm, kw in {"cost_x2": dict(cost_mult=2.0), "cost_exact_2side": dict(cost_mode="exact"), "cost_zero": dict(cost_mult=0.0),
                   "sigma_causal_expanding": dict(sigma_mode="causal"), "sigma_star_uncond_sleeve_sd": dict(sigma_mode="uncond"),
                   "reverse_rule_placebo": dict(reverse=True)}.items():
        oo = overlay(net, Wb, Ws, q, **kw); ee = evaluate(net, oo["netp"], ev, top, label=nm)
        ee["m_stats"] = {"mean_m": float(oo["m"][ev].mean()), "frac_m_lt_1": float((oo["m"][ev] < 1).mean()), "cost_total_bps": float(oo["cost"][ev].sum())}
        sens[nm] = ee
    main["sensitivity"] = sens
    # controls
    ctl = {}
    # ② whole-book vol targeting (same Ws / σ* median, de-lever only)
    sigb = roll_sd(net, Ws, 0); vb = np.isfinite(sigb); sb = np.percentile(sigb[vb], q)
    with np.errstate(invalid="ignore", divide="ignore"):
        mb_ = np.where(vb, np.minimum(1.0, sb / sigb), 1.0)
    mprev = np.concatenate([[1.0], mb_[:-1]]); cb = np.abs(mb_ - mprev) * G * COST_BPS
    vt = mb_ * net - cb
    e2 = evaluate(net, vt, ev, top, label="whole-book vol-targeting (de-lever only)")
    e2["m_stats"] = {"mean_m": float(mb_[ev].mean()), "frac_m_lt_1": float((mb_[ev] < 1).mean()), "cost_total_bps": float(cb[ev].sum())}
    ctl["vol_targeting_whole_book"] = e2
    # ②b whole-book vol-targeting symmetric (lever up & down, cap 2) — closer to the classic judged-negative form
    with np.errstate(invalid="ignore", divide="ignore"):
        ms = np.where(vb, np.minimum(2.0, sb / sigb), 1.0)
    mprev = np.concatenate([[1.0], ms[:-1]]); cs = np.abs(ms - mprev) * G * COST_BPS
    e2b = evaluate(net, ms * net - cs, ev, top, label="whole-book vol-targeting symmetric cap2")
    e2b["m_stats"] = {"mean_m": float(ms[ev].mean()), "cost_total_bps": float(cs[ev].sum())}
    ctl["vol_targeting_whole_book_symmetric"] = e2b
    # ③ static partial hedge h=0.5 β̂_{t-1} (rolling causal β), cost on β̂ drift (2 sides)
    b0 = np.nan_to_num(o["beta"]); h = 0.5 * b0; hprev = np.concatenate([[0.0], h[:-1]]); ch = np.abs(h - hprev) * G * COST_BPS * 2
    e3 = evaluate(net, net - h * rs - ch, ev, top, label="static hedge h=0.5·β̂_{t-1}")
    e3["cost_total_bps"] = float(ch[ev].sum())
    ctl["static_hedge_h0.5"] = e3
    e3b = evaluate(net, net - b0 * rs - 2 * ch, ev, top, label="static hedge h=1.0·β̂_{t-1}")
    ctl["static_hedge_h1.0"] = e3b
    out["main"] = main; out["controls"] = ctl
    # grid (sensitivity only; no post-hoc arm selection)
    grid = {}
    for Wb_ in WB_GRID:
        for Ws_ in WS_GRID:
            for q_ in Q_GRID:
                oo = overlay(net, Wb_, Ws_, q_); ee = evaluate(net, oo["netp"], ev, top, label=f"Wb{Wb_}/Ws{Ws_}/q{q_}")
                grid[f"Wb{Wb_}_Ws{Ws_}_q{q_}"] = {"d_sharpe": ee["d_sharpe"], "d_mean_pct": ee["d_mean_pct"], "alt_sharpe": ee["alt"]["sharpe"], "top_improve": ee["top_spread"]["improve_frac"],
                                                 "y2026_ok": ee["criteria"]["C3_2026"], "yearly_sharpe_ok": ee["yearly_sharpe_not_worse"], "PASS": ee["criteria"]["PASS"],
                                                 "mean_m": float(oo["m"][ev].mean())}
    ds = np.array([g["d_sharpe"] for g in grid.values()])
    out["grid"] = grid
    out["grid_summary"] = {"n_arms": len(grid), "n_pass": int(sum(g["PASS"] for g in grid.values())), "d_sharpe_min": float(ds.min()), "d_sharpe_median": float(np.median(ds)), "d_sharpe_max": float(ds.max()),
                           "n_c1_pass": int(sum(g["d_sharpe"] >= 0.10 for g in grid.values())), "n_top_pass": int(sum((g["top_improve"] or -1) >= 0.30 for g in grid.values()))}
    RES[tag] = out
    print(f"[{tag}] base sharpe(ev) {main['base']['sharpe']:.3f} mean {main['base']['mean']:.3f} | main alt sharpe {main['alt']['sharpe']:.3f} mean {main['alt']['mean']:.3f} "
          f"dS {main['d_sharpe']:+.3f} top {main['top_spread']['base_mean']:.1f}->{main['top_spread']['alt_mean']:.1f} imp {main['top_spread']['improve_frac']:+.2f} "
          f"y26 {main['y2026']} yrS {main['yearly_sharpe_not_worse']}/{main['n_years']} PASS={main['criteria']['PASS']} | grid pass {out['grid_summary']['n_pass']}/{len(grid)} "
          f"| VT dS {e2['d_sharpe']:+.3f} dmean {e2['d_mean_pct']:+.2%} | hedge0.5 dS {e3['d_sharpe']:+.3f} | hedge1.0 S {e3b['alt']['sharpe']:.2f}", flush=True)

# ---------- 2. second path (same author): pandas rolling recomputation of the main arm on primary caliber ----------
try:
    import pandas as pd
    net = SERIES["primary_S1_carry"]; Wb, Ws, q = MAIN
    df = pd.DataFrame({"y": net, "x": rs})
    cov = df["y"].rolling(Wb).cov(df["x"]).shift(1); var = df["x"].rolling(Wb).var().shift(1); beta = (cov / var).values
    sleeve = beta * rs; sig = pd.Series(sleeve).rolling(Ws).std().shift(1).values
    sstar = np.nanpercentile(sig[np.isfinite(sig)], q)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(np.isfinite(sig), np.minimum(1.0, sstar / sig), 1.0)
    mp = np.concatenate([[1.0], m[:-1]]); cost = np.abs(m - mp) * np.abs(np.nan_to_num(beta)) * G * COST_BPS
    netp = net - (1 - m) * np.nan_to_num(sleeve) - cost
    o = overlay(net, Wb, Ws, q)
    RES["second_path_pandas"] = {"max_abs_diff_netp": float(np.nanmax(np.abs(netp[ev] - o["netp"][ev]))), "max_abs_diff_beta": float(np.nanmax(np.abs(beta[ev] - o["beta"][ev]))),
                                 "sharpe_alt": sharpe(netp[ev]), "sharpe_alt_device": sharpe(o["netp"][ev]), "tol_pass": bool(np.nanmax(np.abs(netp[ev] - o["netp"][ev])) < 1e-6)}
    print("SECOND_PATH", RES["second_path_pandas"], flush=True)
except Exception as e:
    RES["second_path_pandas"] = {"error": repr(e)}

RES["meta"]["runtime_s"] = round(time.time() - t0, 1)
json.dump(RES, open(OUT, "w"), indent=1, ensure_ascii=False)
print("WROTE", OUT, "runtime", RES["meta"]["runtime_s"], "s")
