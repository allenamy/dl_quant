"""W2 两书配置装置(DESIGN_optimization_path_2026-08-21 §3.1)· 2026-08-22 · Session 6737834a-W2
判据(冻结于 §3.1, 先于本装置): 配置夏普 ≥ max(单书)+0.15 且 逐年 ≥4/5 且 Q4 最坏五分位不劣于在役; 否则配置不成立。

输入(逐锚序列, 由 jpline 生成器 w2_live_replay.py / w2_wide_replay.py 产出, 复现收据 maxabs_diff=0 见 summary json):
  results/series/w2_live_series_slim.npz  SHA256 502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003
     在役书 9821 锚 2022-01-01→2026-06-29: S0(无止损, 文档基线 1.154/1.46) / S1(在役逐名止损 1.122/1.485), 逐锚 gross/换手/carry(宽面板映射)/regime 变量/单腿子书
  results/series/w2_wide_series_slim.npz  SHA256 fa1ced6d15c014d8617623d6768eff987f80ea2f5d23e82006df1b3193f1ba4a
     宽书 12279 锚 2021-01-06→2026-08-15: S0 / d30_n2_c42(慢三腿 hist_oos king, v2 面板正确 carry, 成本分层), 逐锚 pnl/carry/cost/gross_total/gross_member/三腿贡献
  results/w2_overlap_2026-08-21.json(重叠名注记, 由 w2_overlap.py 产出)
口径: 两书逐锚 净额/当锚 gross × 恒定 gross G(默认 2.0); 主口径 = 在役 S1 含 carry(与宽书同式 fund_now×4/iv) / 宽 d30 按 gross_total 归一(§J-bis 同口径);
      敏感性 = 在役 S0 / 不含 carry / 宽按 gross_member 归一。年化 √(6×365)。
输出: results/two_book_allocation_2026-08-21.json
用法: python3 two_book_allocation.py [G]
"""
import sys, os, json, time, hashlib, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results")
G = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
ANN = np.sqrt(6 * 365); NY = 2190
PIN = {"w2_live_series_slim.npz": "502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003",
       "w2_wide_series_slim.npz": "fa1ced6d15c014d8617623d6768eff987f80ea2f5d23e82006df1b3193f1ba4a"}
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
for f, s in PIN.items():
    got = sha(os.path.join(RES, "series", f)); assert got == s, f"{f} SHA mismatch {got}"
L = np.load(os.path.join(RES, "series", "w2_live_series_slim.npz"), allow_pickle=True)
Wd = np.load(os.path.join(RES, "series", "w2_wide_series_slim.npz"), allow_pickle=True)
cols = [str(c) for c in Wd["cols"]]; C = {c: k for k, c in enumerate(cols)}
RW = Wd["d30_n2_c42_rec"]; RW0 = Wd["S0_rec"]
lts = L["ts"].astype(np.int64); wts = RW[:, C["ts"]].astype(np.int64)
assert np.array_equal(wts, RW0[:, C["ts"]].astype(np.int64))
# ---- align on common anchors ----
wpos = {int(t): j for j, t in enumerate(wts)}
li = np.array([i for i, t in enumerate(lts) if int(t) in wpos]); wi = np.array([wpos[int(t)] for t in lts[li]])
ts = lts[li]; yr = np.array([time.gmtime(int(t)).tm_year for t in ts]); n = len(ts)
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
cov = {"live": {"n": int(len(lts)), "first": fmt(lts[0]), "last": fmt(lts[-1])}, "wide": {"n": int(len(wts)), "first": fmt(wts[0]), "last": fmt(wts[-1])},
       "common": {"n": int(n), "first": fmt(ts[0]), "last": fmt(ts[-1]), "by_year": {int(y): int((yr == y).sum()) for y in sorted(set(yr.tolist()))}}}
# ---- per-unit-gross series (variants) ----
def live_pg(arm, carry, own_gross=False):
    """每单位【目标 gross】净额: 分母 = 无止损臂 S0 的当锚 gross(止损只临时削减已部署 gross, 目标 gross 不变); own_gross=True 改用本臂止损后 gross(敏感性)。"""
    net = L[f"{arm}_net"][li].astype(float); g = L[f"{arm}_gross" if own_gross else "S0_gross"][li].astype(float); cr = L[f"{arm}_carry"][li].astype(float)
    if carry: net = net - np.nan_to_num(cr)
    return net / g
def wide_pg(arm, gcol, own_gross=False):
    R_ = RW if arm == "d30_n2_c42" else RW0
    g = (R_ if own_gross else RW0)[wi, C[gcol]]
    return R_[wi, C["net"]] / g
VAR = {"primary": ("S1", True, "d30_n2_c42", "gross_total", False),
       "own_poststop_gross": ("S1", True, "d30_n2_c42", "gross_total", True),
       "live_S1_nocarry": ("S1", False, "d30_n2_c42", "gross_total", False),
       "live_S0_carry": ("S0", True, "d30_n2_c42", "gross_total", False),
       "live_S0_nocarry": ("S0", False, "d30_n2_c42", "gross_total", False),
       "wide_member_gross": ("S1", True, "d30_n2_c42", "gross_member", False),
       "wide_S0_nostop": ("S1", True, "S0", "gross_total", False)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * ANN) if x.std(ddof=1) > 0 else float("nan")
def maxdd_bps(x): c = np.cumsum(x); return float(-(c - np.maximum.accumulate(c)).min())
def maxdd_nav(x, g):
    nav = np.cumprod(1 + g * x / 1e4); return float(-(nav / np.maximum.accumulate(nav) - 1).min())
def es(x, q=0.05): k = max(1, int(len(x) * q)); return float(np.sort(x)[:k].mean())
def agg(x, k): m = (len(x) // k) * k; return x[:m].reshape(-1, k).sum(1)
def blend(Lx, Wx, w): return (1 - w) * Lx + w * Wx
WGRID = [round(0.1 * k, 1) for k in range(11)]
def summarize(Lx, Wx, tag):
    out = {"tag": tag, "G": G}
    out["single"] = {}
    for nm, x in (("live", Lx), ("wide", Wx)):
        out["single"][nm] = {"mean_pg": round(float(x.mean()), 4), "sd_pg": round(float(x.std(ddof=1)), 3), "sharpe": round(sharpe(x), 3),
                             "mean_at_G": round(float(x.mean() * G), 4), "by_year_sharpe": {int(y): round(sharpe(x[yr == y]), 3) for y in sorted(set(yr.tolist()))},
                             "by_year_mean_at_G": {int(y): round(float(x[yr == y].mean() * G), 3) for y in sorted(set(yr.tolist()))},
                             "sharpe_2022_23": round(sharpe(x[yr <= 2023]), 3), "sharpe_2024_26": round(sharpe(x[yr >= 2024]), 3), "sharpe_2022_25_ex2026": round(sharpe(x[yr <= 2025]), 3),
                             "maxDD_bps_at_G": round(maxdd_bps(x * G), 0), "maxDD_nav_at_G": round(maxdd_nav(x, G), 4), "ES5_pg": round(es(x), 2), "ES1_pg": round(es(x, 0.01), 2),
                             "sharpe_daily_agg": round(float(agg(x, 6).mean() / agg(x, 6).std(ddof=1) * np.sqrt(365)), 3),
                             "sharpe_weekly_agg": round(float(agg(x, 42).mean() / agg(x, 42).std(ddof=1) * np.sqrt(365 / 7)), 3)}
    # ---- correlations ----
    rho = {"all_pearson": round(float(np.corrcoef(Lx, Wx)[0, 1]), 4)}
    from scipy.stats import spearmanr
    rho["all_spearman"] = round(float(spearmanr(Lx, Wx).correlation), 4)
    rho["by_year"] = {int(y): round(float(np.corrcoef(Lx[yr == y], Wx[yr == y])[0, 1]), 3) for y in sorted(set(yr.tolist()))}
    rho["daily_agg"] = round(float(np.corrcoef(agg(Lx, 6), agg(Wx, 6))[0, 1]), 3); rho["weekly_agg"] = round(float(np.corrcoef(agg(Lx, 42), agg(Wx, 42))[0, 1]), 3)
    rho["monthly_agg"] = round(float(np.corrcoef(agg(Lx, 180), agg(Wx, 180))[0, 1]), 3)
    roll = [np.corrcoef(Lx[i:i + NY], Wx[i:i + NY])[0, 1] for i in range(0, n - NY, 42)]
    rho["rolling_1y_min_med_max"] = [round(float(np.min(roll)), 3), round(float(np.median(roll)), 3), round(float(np.max(roll)), 3)]
    # tail co-movement
    q5L = np.percentile(Lx, 5); q5W = np.percentile(Wx, 5)
    rho["P_both_worst5pct"] = round(float(np.mean((Lx <= q5L) & (Wx <= q5W))), 4); rho["P_indep"] = 0.0025
    rho["corr_in_union_tail"] = round(float(np.corrcoef(Lx[(Lx <= q5L) | (Wx <= q5W)], Wx[(Lx <= q5L) | (Wx <= q5W)])[0, 1]), 3)
    # Q4 subsamples
    Q = {}
    qL = np.percentile(Lx, 20); mA = Lx <= qL; Q["a_live_worst_quintile_anchor"] = mA
    bl = agg(Lx, 42); qb = np.percentile(bl, 20); mB = np.zeros(n, bool)
    for b, v in enumerate(bl):
        if v <= qb: mB[b * 42:(b + 1) * 42] = True
    Q["b_live_worst_quintile_weekly_block"] = mB
    mkt = L["mkt_ew"][li].astype(float); btc = L["btc4"][li].astype(float); spr = mkt - btc
    for nm, v in (("c_mkt_ew", mkt), ("d_alt_minus_btc_spread", spr), ("e_abs_mkt", np.abs(mkt))):
        v2 = np.where(np.isfinite(v), v, np.nan); edges = np.nanpercentile(v2, [20, 40, 60, 80]); qi = np.digitize(v2, edges)
        means = [float(Lx[qi == k].mean()) for k in range(5)]; worst = int(np.argmin(means))
        Q[f"{nm}_q{worst}_worst_for_live"] = (qi == worst); Q[f"{nm}_quintile_means_live"] = means
    rho["Q4_rho"] = {}
    out["Q4_def"] = {}
    for k, m in Q.items():
        if k.endswith("_quintile_means_live"): out["Q4_def"][k] = [round(v, 3) for v in m]; continue
        rho["Q4_rho"][k] = round(float(np.corrcoef(Lx[m], Wx[m])[0, 1]), 3)
        out["Q4_def"][k] = {"n": int(m.sum()), "live_mean_at_G": round(float(Lx[m].mean() * G), 3), "wide_mean_at_G": round(float(Wx[m].mean() * G), 3)}
    out["rho"] = rho
    # ---- weight grid ----
    grid = {}
    for w in WGRID:
        b = blend(Lx, Wx, w)
        row = {"sharpe": round(sharpe(b), 3), "mean_at_G": round(float(b.mean() * G), 4), "sd_pg": round(float(b.std(ddof=1)), 3),
               "maxDD_bps_at_G": round(maxdd_bps(b * G), 0), "maxDD_nav_at_G": round(maxdd_nav(b, G), 4), "ES5_pg": round(es(b), 2),
               "by_year_sharpe": {int(y): round(sharpe(b[yr == y]), 3) for y in sorted(set(yr.tolist()))},
               "by_year_mean_at_G": {int(y): round(float(b[yr == y].mean() * G), 3) for y in sorted(set(yr.tolist()))},
               "sharpe_2022_23": round(sharpe(b[yr <= 2023]), 3), "sharpe_2024_26": round(sharpe(b[yr >= 2024]), 3), "sharpe_2022_25_ex2026": round(sharpe(b[yr <= 2025]), 3),
               "sharpe_daily_agg": round(float(agg(b, 6).mean() / agg(b, 6).std(ddof=1) * np.sqrt(365)), 3),
               "sharpe_weekly_agg": round(float(agg(b, 42).mean() / agg(b, 42).std(ddof=1) * np.sqrt(365 / 7)), 3),
               "Q4_mean_at_G": {k: round(float(b[m].mean() * G), 3) for k, m in Q.items() if not k.endswith("_quintile_means_live")}}
        # criteria
        maxS = max(out["single"]["live"]["sharpe"], out["single"]["wide"]["sharpe"])
        yrs = sorted(set(yr.tolist()))
        c1 = row["sharpe"] >= maxS + 0.15
        n_beat_max = sum(1 for y in yrs if row["by_year_sharpe"][y] >= max(out["single"]["live"]["by_year_sharpe"][y], out["single"]["wide"]["by_year_sharpe"][y]))
        n_beat_live = sum(1 for y in yrs if row["by_year_sharpe"][y] >= out["single"]["live"]["by_year_sharpe"][y])
        n_pos = sum(1 for y in yrs if row["by_year_mean_at_G"][y] > 0)
        q4ok = {k: bool(row["Q4_mean_at_G"][k] >= out["Q4_def"][k]["live_mean_at_G"]) for k in row["Q4_mean_at_G"]}
        row["criteria"] = {"c1_sharpe_ge_maxsingle_plus_0.15": bool(c1), "delta_vs_maxsingle": round(row["sharpe"] - maxS, 3),
                           "years_ge_max_single": f"{n_beat_max}/{len(yrs)}", "years_ge_live": f"{n_beat_live}/{len(yrs)}", "years_positive": f"{n_pos}/{len(yrs)}",
                           "Q4_not_worse_than_live": q4ok,
                           "PASS_strict(c1 & years_ge_max>=4 & all Q4)": bool(c1 and n_beat_max >= 4 and all(q4ok.values())),
                           "PASS_lenient(c1 & years_ge_live>=4 & Q4 a,b,d)": bool(c1 and n_beat_live >= 4 and all(q4ok[k] for k in q4ok if k[0] in "abd"))}
        grid[str(w)] = row
    out["grid"] = grid
    # ---- analytic weights ----
    sL, sW = Lx.std(ddof=1), Wx.std(ddof=1); r = np.corrcoef(Lx, Wx)[0, 1]; mL, mW = Lx.mean(), Wx.mean()
    w_rp = (1 / sW) / (1 / sL + 1 / sW)
    esL, esW = -es(Lx), -es(Wx); w_tail = (1 / esW) / (1 / esL + 1 / esW)
    cov2 = np.cov(np.stack([Lx, Wx])); mu = np.array([mL, mW]); inv = np.linalg.inv(cov2); wmv = inv @ mu; wmv = wmv / wmv.sum()
    def at(w):
        b = blend(Lx, Wx, w); return {"w_wide": round(float(w), 4), "sharpe": round(sharpe(b), 3), "mean_at_G": round(float(b.mean() * G), 4),
                                     "by_year_sharpe": {int(y): round(sharpe(b[yr == y]), 3) for y in sorted(set(yr.tolist()))}}
    out["analytic_weights"] = {"risk_parity_inverse_vol": at(w_rp), "tail_parity_inverse_ES5": at(w_tail), "max_sharpe_insample": at(float(np.clip(wmv[1], 0, 1))),
                               "max_sharpe_raw_w": [round(float(v), 4) for v in wmv], "vol_ratio_live_over_wide": round(float(sL / sW), 3)}
    best_w = max(WGRID, key=lambda w: grid[str(w)]["sharpe"]); out["best_grid_w"] = best_w
    # ---- paired block bootstrap of ΔSharpe(best w / 0.5) vs max single ----
    rng = np.random.RandomState(7); Lb = 42; nb = n // Lb; reps = 2000
    d_best = []; d_half = []; d_rp = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nb); sel = np.concatenate([np.arange(i * Lb, (i + 1) * Lb) for i in idx])
        Ls, Ws = Lx[sel], Wx[sel]; m_ = max(sharpe(Ls), sharpe(Ws))
        d_best.append(sharpe(blend(Ls, Ws, best_w)) - m_); d_half.append(sharpe(blend(Ls, Ws, 0.5)) - m_); d_rp.append(sharpe(blend(Ls, Ws, w_rp)) - m_)
    def ci(v): v = np.array(v); return {"mean": round(float(v.mean()), 3), "CI95": [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)], "P_ge_0.15": round(float((v >= 0.15).mean()), 3), "P_gt_0": round(float((v > 0).mean()), 3)}
    out["bootstrap_delta_sharpe_vs_maxsingle"] = {"block": Lb, "reps": reps, f"w={best_w}": ci(d_best), "w=0.5": ci(d_half), f"w_rp={round(w_rp,3)}": ci(d_rp)}
    return out, Q
# ---- trip probabilities (§J-bis / §M method: block 180, 2000 paths of 1y; peak-DD −25% and from-start −25%) ----
def trip(x, g, shr=1.0, seed=11, Lb=180, reps=2000):
    x = x - x.mean() * (1 - shr); rng = np.random.RandomState(seed); nb = len(x) // Lb; nbk = NY // Lb + 1
    hp = 0; hs = 0; ann = []
    for _ in range(reps):
        idx = rng.randint(0, nb, nbk); path = np.concatenate([x[i * Lb:(i + 1) * Lb] for i in idx])[:NY] * g / 1e4
        cum = np.cumprod(1 + path); dd = cum / np.maximum.accumulate(cum) - 1
        hp += dd.min() <= -0.25; hs += cum.min() <= 0.75; ann.append(cum[-1] - 1)
    return {"P_peakDD_-25%": round(hp / reps, 3), "P_fromstart_-25%": round(hs / reps, 3), "ann_median": round(float(np.median(ann)), 3), "ann_p5": round(float(np.percentile(ann, 5)), 3)}
def trip_hist(x, g, step=6):
    """历史滚动 1 年窗口(每日起点), 起点口径: 窗口内 nav 是否触及 0.75; 并给峰值回撤口径。"""
    hits_s = 0; hits_p = 0; cnt = 0
    for s in range(0, len(x) - NY, step):
        path = x[s:s + NY] * g / 1e4; cum = np.cumprod(1 + path); cnt += 1
        hits_s += cum.min() <= 0.75; hits_p += (cum / np.maximum.accumulate(cum) - 1).min() <= -0.25
    return {"n_windows": cnt, "frac_fromstart_-25%": round(hits_s / cnt, 3), "frac_peakDD_-25%": round(hits_p / cnt, 3)}
RESULT = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-W2", "G": G, "inputs_sha256": PIN, "coverage": cov,
                   "caliber": "per-anchor net/gross × constant G; primary = live S1 (in-service stop) incl. carry(wide-panel fund_now×4/iv mapped) / wide d30_n2_c42 ÷ gross_total; ann √(6×365)"}}
# reproduction table from generator receipts
for f in ("w2_live_summary.json", "w2_wide_summary.json"):
    p = os.path.join(RES, f)
    if os.path.exists(p): RESULT["meta"][f] = json.load(open(p))
VARS = {}; QS = {}
for tag, (larm, carry, warm, gcol, og) in VAR.items():
    Lx = live_pg(larm, carry, og); Wx = wide_pg(warm, gcol, og)
    o, Q = summarize(Lx, Wx, tag); VARS[tag] = o; QS[tag] = (Lx, Wx)
RESULT["variants"] = VARS
# predecessor-caliber check (§J-bis: live net/0.987 const; wide pergross from pinned-king gross rows) on ≥2022 samples
Lc = (L["S1_net"].astype(float) / 0.987); RESULT["predecessor_check"] = {
    "live_S1_over_const0.987_all9821": {"mean": round(float(Lc.mean()), 3), "sd": round(float(Lc.std()), 2), "doc_J_bis": {"mean": 1.132, "sd": 35.83}},
    "wide_d30_over_gross_total_ge2022": {"mean": round(float((RW[:, C["net"]] / RW[:, C["gross_total"]])[np.array([time.gmtime(int(t)).tm_year for t in wts]) >= 2022].mean()), 3),
                                          "sd": round(float((RW[:, C["net"]] / RW[:, C["gross_total"]])[np.array([time.gmtime(int(t)).tm_year for t in wts]) >= 2022].std()), 2),
                                          "doc_J_bis_pinned_gross": {"mean": 1.176, "sd": 26.26, "n": 9941}},
    "note": "§J-bis 宽书每单位 gross 用 pinned-king 构造的 gross 行除 hist-king 的 net(分子分母构造不同); 本装置分子分母同构造"}
# ---- leg-level correlations (primary caliber; legs per unit of target gross) ----
gL0 = L["S0_gross"][li].astype(float); gW0 = RW0[wi, C["gross_total"]]
LL = {k: (L[f"leg_{k}_net"][li].astype(float) - np.nan_to_num(L[f"leg_{k}_carry"][li].astype(float))) / gL0 for k in ("king", "s2", "funding")}
WL = {k: RW[wi, C[f"leg_{k}"]] / gW0 for k in ("king", "rev24", "fund")}
Lx, Wx = QS["primary"]
legcorr = {"live_book_vs_wide_legs": {k: round(float(np.corrcoef(Lx, v)[0, 1]), 3) for k, v in WL.items()},
           "wide_book_vs_live_legs": {k: round(float(np.corrcoef(Wx, v)[0, 1]), 3) for k, v in LL.items()},
           "live_leg_vs_wide_leg": {f"{a}|{b}": round(float(np.corrcoef(LL[a], WL[b])[0, 1]), 3) for a in LL for b in WL},
           "live_legs_sharpe": {k: round(sharpe(v), 3) for k, v in LL.items()}, "wide_legs_mean_pg": {k: round(float(v.mean()), 4) for k, v in WL.items()},
           "live_leg_carry_mean_bps": {k: round(float(np.nanmean(L[f"leg_{k}_carry"][li])), 4) for k in ("king", "s2", "funding")},
           "sign_note": "在役 SIGNS funding=-1(空高 funding_ema, 收 carry); 宽书 fund 腿 = +rank(f_fund_ema_v1)(多高 funding, 付 carry) ⇒ 同一因子反向持仓",
           "wide_w3_mean_by_year": {int(y): [round(float(RW[wi, C[f"w3_{k}"]][yr == y].mean()), 3) for k in ("king", "rev24", "fund")] for y in sorted(set(yr.tolist()))}}
RESULT["leg_correlations"] = legcorr
# ---- year-by-year margin detail for the 逐年 criterion ----
P_ = VARS["primary"]; ym = {}
for w in ("0.5", "0.6", "0.7", "0.8"):
    ym[w] = {int(y): {"blend": P_["grid"][w]["by_year_sharpe"][y], "live": P_["single"]["live"]["by_year_sharpe"][y], "wide": P_["single"]["wide"]["by_year_sharpe"][y],
                      "margin_vs_max": round(P_["grid"][w]["by_year_sharpe"][y] - max(P_["single"]["live"]["by_year_sharpe"][y], P_["single"]["wide"]["by_year_sharpe"][y]), 3)} for y in sorted(set(yr.tolist()))}
RESULT["year_margins_primary"] = ym
# trip probabilities on primary + chosen sensitivities
Lx, Wx = QS["primary"]; TP = {}
for w in (0.0, 0.5, 1.0, VARS["primary"]["best_grid_w"], VARS["primary"]["analytic_weights"]["risk_parity_inverse_vol"]["w_wide"]):
    b = blend(Lx, Wx, w); key = f"w_wide={w}"; TP[key] = {}
    for g in (2.0, 2.5, 3.0):
        TP[key][f"G{g}"] = {"replay": trip(b, g, 1.0), "shrink0.55": trip(b, g, 0.55), "hist_rolling_1y": trip_hist(b, g)}
    TP[key]["G2.0_2024on_replay"] = trip(b[yr >= 2024], 2.0, 1.0)
RESULT["trip_probability"] = TP
# overlap note
op = os.path.join(RES, "w2_overlap_2026-08-21.json")
if os.path.exists(op): RESULT["overlap_note"] = json.load(open(op))
json.dump(RESULT, open(os.path.join(RES, "two_book_allocation_2026-08-21.json"), "w"), indent=1, ensure_ascii=False)
# ---- console digest ----
P = VARS["primary"]
print("coverage", json.dumps(cov))
print("single", json.dumps(P["single"], ensure_ascii=False))
print("rho", json.dumps(P["rho"], ensure_ascii=False))
print("Q4_def", json.dumps(P["Q4_def"], ensure_ascii=False))
for w in WGRID:
    r = P["grid"][str(w)]; print(f"w_wide={w}", "sharpe", r["sharpe"], "mean@G", r["mean_at_G"], "maxDDnav", r["maxDD_nav_at_G"], "byyr", r["by_year_sharpe"], "crit", json.dumps(r["criteria"], ensure_ascii=False))
print("analytic", json.dumps(P["analytic_weights"], ensure_ascii=False)); print("best_w", P["best_grid_w"]); print("boot", json.dumps(P["bootstrap_delta_sharpe_vs_maxsingle"], ensure_ascii=False))
for tag in VARS:
    if tag == "primary": continue
    v = VARS[tag]; bw = v["best_grid_w"]; print("VARIANT", tag, "live", v["single"]["live"]["sharpe"], "wide", v["single"]["wide"]["sharpe"], "rho", v["rho"]["all_pearson"], "best_w", bw, "best_sharpe", v["grid"][str(bw)]["sharpe"], "w0.5", v["grid"]["0.5"]["sharpe"], "crit_best", json.dumps(v["grid"][str(bw)]["criteria"], ensure_ascii=False))
print("trip", json.dumps(TP, ensure_ascii=False))
print("predecessor_check", json.dumps(RESULT["predecessor_check"], ensure_ascii=False))
print("legcorr", json.dumps(legcorr, ensure_ascii=False)); print("year_margins", json.dumps(ym, ensure_ascii=False))
