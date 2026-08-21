"""W2 红队追加 B/C/D · 精确腿归因上的 ρ 表 / 配置分解 / 腿移植变体 / regime 表 / 符号证据(2026-08-22, Session 6737834a-W2)。
输入(SHA256 钉定):
  results/w2_live_legattrib.npz  da8cbfa6de169b6208e988dc38fae17c987ccb66e348f560117cdc90b6f6c73a (S1: 逐锚 king/s2/funding 的 pnl/carry/cost/gross, 精确可加)
  results/w2_wide_legattrib.npz  1a61b324a1b369180ac64af603249516316d290169e0bb49eeafc9eb2a56f70e (d30_n2_c42: king/rev24/fund 同上)
  results/series/w2_live_series_slim.npz / w2_wide_series_slim.npz(S0 gross 作"目标 gross"分母, 与 two_book_allocation 主口径一致)
口径: 每腿 net_k = (pnl_k − carry_k − cost_k) ÷ 当锚无止损臂 gross(书级目标 gross); carry 正=付出; Σ_k net_k ≡ 书 net(含 carry)。
输出: results/w2_legs_analysis_2026-08-21.json
"""
import os, json, time, hashlib, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results")
G = 2.0; ANN = np.sqrt(2190)
PIN = {"w2_live_legattrib.npz": "da8cbfa6de169b6208e988dc38fae17c987ccb66e348f560117cdc90b6f6c73a", "w2_wide_legattrib.npz": "1a61b324a1b369180ac64af603249516316d290169e0bb49eeafc9eb2a56f70e"}
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
for f, s in PIN.items():
    assert sha(os.path.join(RES, f)) == s, f"SHA mismatch {f}"
LA = np.load(os.path.join(RES, "w2_live_legattrib.npz"), allow_pickle=True); WA = np.load(os.path.join(RES, "w2_wide_legattrib.npz"), allow_pickle=True)
LS = np.load(os.path.join(RES, "series", "w2_live_series_slim.npz"), allow_pickle=True); WS = np.load(os.path.join(RES, "series", "w2_wide_series_slim.npz"), allow_pickle=True)
lc = [str(c) for c in LA["cols"]]; LC = {c: k for k, c in enumerate(lc)}; RL = LA["S1"]
wc = [str(c) for c in WA["cols"]]; WC = {c: k for k, c in enumerate(wc)}; RW = WA["d30_n2_c42"]
wsc = [str(c) for c in WS["cols"]]; WSC = {c: k for k, c in enumerate(wsc)}; RW0 = WS["S0_rec"]
lts = RL[:, LC["ts"]].astype(np.int64); wts = RW[:, WC["ts"]].astype(np.int64)
assert np.array_equal(lts, LS["ts"].astype(np.int64)) and np.array_equal(wts, RW0[:, WSC["ts"]].astype(np.int64))
wpos = {int(t): j for j, t in enumerate(wts)}
li = np.array([i for i, t in enumerate(lts) if int(t) in wpos]); wi = np.array([wpos[int(t)] for t in lts[li]])
ts = lts[li]; yr = np.array([time.gmtime(int(t)).tm_year for t in ts]); n = len(ts); YRS = sorted(set(yr.tolist()))
gL0 = LS["S0_gross"][li].astype(float); gW0 = RW0[wi, WSC["gross_total"]]
LLEGS = ("king", "s2", "funding"); WLEGS = ("king", "rev24", "fund")
def comp(R, C, k, g, idx):
    return {"pnl": R[idx, C[f"{k}_pnl"]] / g, "carry": R[idx, C[f"{k}_carry"]] / g, "cost": R[idx, C[f"{k}_cost"]] / g,
            "gross": R[idx, C[f"{k}_gross"]], "net": (R[idx, C[f"{k}_pnl"]] - R[idx, C[f"{k}_carry"]] - R[idx, C[f"{k}_cost"]]) / g}
L = {k: comp(RL, LC, k, gL0, li) for k in LLEGS}; Wl = {k: comp(RW, WC, k, gW0, wi) for k in WLEGS}
Lbook = sum(L[k]["net"] for k in LLEGS); Wbook = sum(Wl[k]["net"] for k in WLEGS)
gWtot = RW[wi, WC["gross_total"]]; gLtot = RL[li, LC["gross"]]
def sh(x): return float(x.mean() / x.std(ddof=1) * ANN) if x.std(ddof=1) > 0 else float("nan")
def r(x, d=3): return round(float(x), d)
OUT = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-W2", "n_common": int(n), "inputs_sha256": PIN,
                "caliber": "leg net_k = (pnl_k − carry_k − cost_k)/target gross(S0 arm); carry positive = PAID; ×G=2 for bps@G",
                "live_summary": json.load(open(os.path.join(RES, "w2_live_legattrib_summary.json"))), "wide_summary": json.load(open(os.path.join(RES, "w2_wide_legattrib_summary.json")))}}
# ---- A. leg tables ----
def legtab(D, legs, gtot):
    T = {}
    for k in legs:
        x = D[k]
        T[k] = {"mean_pnl_at_G": r(x["pnl"].mean() * G), "mean_carry_paid_at_G": r(x["carry"].mean() * G), "mean_cost_at_G": r(x["cost"].mean() * G), "mean_net_at_G": r(x["net"].mean() * G),
                "sharpe_net": r(sh(x["net"])), "sharpe_price_only": r(sh(x["pnl"])), "sharpe_net_nocarry": r(sh(x["pnl"] - x["cost"])),
                "gross_share_of_book": r(np.mean(x["gross"] / gtot)), "by_year_net_at_G": {y: r(x["net"][yr == y].mean() * G) for y in YRS}, "by_year_sharpe_net": {y: r(sh(x["net"][yr == y])) for y in YRS},
                "by_year_carry_paid_at_G": {y: r(x["carry"][yr == y].mean() * G) for y in YRS}, "by_year_pnl_at_G": {y: r(x["pnl"][yr == y].mean() * G) for y in YRS}}
    return T
OUT["A_live_legs_S1"] = legtab(L, LLEGS, gLtot); OUT["A_wide_legs_d30"] = legtab(Wl, WLEGS, gWtot)
OUT["A_books"] = {"live_S1_with_carry": {"mean_at_G": r(Lbook.mean() * G), "sharpe": r(sh(Lbook)), "by_year_sharpe": {y: r(sh(Lbook[yr == y])) for y in YRS}},
                  "wide_d30": {"mean_at_G": r(Wbook.mean() * G), "sharpe": r(sh(Wbook)), "by_year_sharpe": {y: r(sh(Wbook[yr == y])) for y in YRS}},
                  "check_vs_two_book_allocation_primary": "live 1.586 / wide 2.107 expected"}
OUT["A_carry_reconciliation"] = {"live_S1_carry_raw_mean_bps_per_anchor(at realized gross~0.96)": r(RL[li, LC["carry"]].mean(), 4),
                                 "live_S1_carry_per_unit_target_gross_x2": r((RL[li, LC["carry"]] / gL0).mean() * G, 4),
                                 "wide_d30_carry_raw_mean": r(RW[wi, WC["carry"]].mean(), 4), "wide_d30_carry_per_unit_target_gross_x2": r((RW[wi, WC["carry"]] / gW0).mean() * G, 4),
                                 "convention": "carry 列 = 付出金额(正=付); 在役为负 ⇒ 书【收到】; team-lead 读到的 −0.17 = 每单位 gross ×2 的付出 = 收到 0.17 bps/锚 @gross2 = 我说的 +0.08/锚 @gross≈1 —— 同一事实"}
# ---- B1. correlations ----
cor = lambda a, b: r(np.corrcoef(a, b)[0, 1])
OUT["B1_rho"] = {"book_live_vs_wide": cor(Lbook, Wbook),
                 "leg3x3(live_leg | wide_leg)": {f"{a}|{b}": cor(L[a]["net"], Wl[b]["net"]) for a in LLEGS for b in WLEGS},
                 "live_book_vs_wide_legs": {b: cor(Lbook, Wl[b]["net"]) for b in WLEGS}, "wide_book_vs_live_legs": {a: cor(Wbook, L[a]["net"]) for a in LLEGS},
                 "within_live_legs": {f"{a}|{b}": cor(L[a]["net"], L[b]["net"]) for a in LLEGS for b in LLEGS if a < b},
                 "within_wide_legs": {f"{a}|{b}": cor(Wl[a]["net"], Wl[b]["net"]) for a in WLEGS for b in WLEGS if a < b},
                 "price_only_leg3x3": {f"{a}|{b}": cor(L[a]["pnl"], Wl[b]["pnl"]) for a in LLEGS for b in WLEGS}}
# ---- B2. blend decomposition ----
Wfund = Wl["fund"]["net"]; Wexf = Wl["king"]["net"] + Wl["rev24"]["net"]; Lexf = L["king"]["net"] + L["s2"]["net"]; Lfund = L["funding"]["net"]
def decomp(w):
    comps = {"live_book(1-w)": (1 - w) * Lbook, "wide_fund(w)": w * Wfund, "wide_exfund(w)": w * Wexf}
    T = sum(comps.values()); vT = T.var(ddof=1); out = {"sharpe_total": r(sh(T)), "mean_total_at_G": r(T.mean() * G)}
    for k, x in comps.items():
        out[k] = {"mean_share": r(x.mean() / T.mean()), "euler_var_share": r(np.cov(x, T, ddof=1)[0, 1] / vT), "sharpe_without": r(sh(T - x)), "marginal_sharpe": r(sh(T) - sh(T - x)), "own_sharpe": r(sh(x))}
    return out
OUT["B2_blend_decomposition"] = {"w=0.7": decomp(0.7), "w=0.5": decomp(0.5), "w=0.6": decomp(0.6)}
# ---- B3. variants ----
WGRID = [round(0.1 * k, 1) for k in range(11)]
def curve(Lx, Wx, label):
    g = {}
    for w in WGRID:
        b = (1 - w) * Lx + w * Wx; g[str(w)] = {"sharpe": r(sh(b)), "mean_at_G": r(b.mean() * G), "by_year_sharpe": {y: r(sh(b[yr == y])) for y in YRS}}
    best = max(WGRID, key=lambda w: g[str(w)]["sharpe"]); maxS = max(sh(Lx), sh(Wx))
    return {"label": label, "single_L": r(sh(Lx)), "single_W": r(sh(Wx)), "rho": cor(Lx, Wx), "best_w": best, "best_sharpe": g[str(best)]["sharpe"], "sharpe_w0.5": g["0.5"]["sharpe"], "sharpe_w0.7": g["0.7"]["sharpe"],
            "delta_best_vs_maxsingle": r(g[str(best)]["sharpe"] - maxS), "years_best_ge_maxsingle": sum(1 for y in YRS if g[str(best)]["by_year_sharpe"][y] >= max(sh(Lx[yr == y]), sh(Wx[yr == y]))), "grid": g}
gF = Wl["fund"]["gross"]; gE = Wl["king"]["gross"] + Wl["rev24"]["gross"]; gLf = L["funding"]["gross"]; gLe = L["king"]["gross"] + L["s2"]["gross"]
with np.errstate(all="ignore"):
    Wfund_s = np.where(gF > 1e-9, Wfund * gW0 / gF, 0.0)       # standalone: per unit of the leg's own gross
    Wexf_s = np.where(gE > 1e-9, Wexf * gW0 / gE, 0.0)
    Lexf_s = np.where(gLe > 1e-9, Lexf * gL0 / gLe, 0.0)
OUT["B3_variants"] = {
    "ref_live+wide_whole": curve(Lbook, Wbook, "在役 + 宽整书(主口径参照)"),
    "v1a_live+wide_fund_as_in_book": curve(Lbook, Wfund, "① 在役 + 仅宽 fund 腿(按宽书内份额, 每单位宽目标 gross)"),
    "v1b_live+wide_fund_standalone": curve(Lbook, Wfund_s, "① 在役 + 仅宽 fund 腿(独立单位 gross 腿书)"),
    "v2a_live+wide_exfund_as_in_book": curve(Lbook, Wexf, "② 在役 + 宽 ex-fund(king+rev24, 按宽书内份额)"),
    "v2b_live+wide_exfund_standalone": curve(Lbook, Wexf_s, "② 在役 + 宽 ex-fund(独立单位 gross)"),
    "v3a_live_exfunding+wide_whole": curve(Lexf, Wbook, "③ 在役去 funding 腿(king+s2 份额)+ 宽整书"),
    "v3b_live_exfunding_standalone+wide_whole": curve(Lexf_s, Wbook, "③ 在役去 funding 腿(独立单位 gross)+ 宽整书"),
    "v4_live_fundingleg_vs_wide_fundleg": {"rho": cor(Lfund, Wfund), "live_funding_leg_sharpe": r(sh(Lfund)), "wide_fund_leg_sharpe": r(sh(Wfund)), "sum_sharpe": r(sh(Lfund + Wfund)),
                                           "note": "两 funding 腿按各自书内份额直接相加(反向持仓部分抵消)"}}
# carry attribution sensitivity for the wide fund leg (team-lead's 粗算 range)
allcarry = RW[wi, WC["carry"]] / gW0
OUT["B4_wide_fund_carry_sensitivity"] = {"precise_own_carry": r(sh(Wfund)), "all_book_carry_to_fund": r(sh(Wl["fund"]["pnl"] - allcarry - Wl["fund"]["cost"])), "no_carry": r(sh(Wl["fund"]["pnl"] - Wl["fund"]["cost"])),
                                         "wide_exfund_precise": r(sh(Wexf)), "wide_exfund_if_fund_takes_all_carry": r(sh(Wl["king"]["pnl"] - Wl["king"]["cost"] + Wl["rev24"]["pnl"] - Wl["rev24"]["cost"])),
                                         "fund_share_of_book_carry": r(Wl["fund"]["carry"].mean() / allcarry.mean()), "king_share_of_book_carry": r(Wl["king"]["carry"].mean() / allcarry.mean()), "rev24_share": r(Wl["rev24"]["carry"].mean() / allcarry.mean())}
# ---- C. regime table ----
b7 = 0.3 * Lbook + 0.7 * Wbook; b5 = 0.5 * Lbook + 0.5 * Wbook; b6 = 0.4 * Lbook + 0.6 * Wbook
OUT["C_regime_by_year"] = {y: {"wide_fund_net_at_G": r(Wfund[yr == y].mean() * G), "wide_fund_sharpe": r(sh(Wfund[yr == y])), "wide_fund_price_at_G": r(Wl["fund"]["pnl"][yr == y].mean() * G), "wide_fund_carry_paid_at_G": r(Wl["fund"]["carry"][yr == y].mean() * G),
                               "wide_exfund_sharpe": r(sh(Wexf[yr == y])), "wide_exfund_net_at_G": r(Wexf[yr == y].mean() * G),
                               "live_funding_net_at_G": r(Lfund[yr == y].mean() * G), "live_funding_sharpe": r(sh(Lfund[yr == y])), "live_exfunding_sharpe": r(sh(Lexf[yr == y])),
                               "live_sharpe": r(sh(Lbook[yr == y])), "wide_sharpe": r(sh(Wbook[yr == y])),
                               "blend0.7_sharpe": r(sh(b7[yr == y])), "blend0.7_gain_vs_live": r(sh(b7[yr == y]) - sh(Lbook[yr == y])), "blend0.5_gain_vs_live": r(sh(b5[yr == y]) - sh(Lbook[yr == y])), "blend0.6_gain_vs_live": r(sh(b6[yr == y]) - sh(Lbook[yr == y])),
                               "blend0.7_mean_at_G": r(b7[yr == y].mean() * G), "live_mean_at_G": r(Lbook[yr == y].mean() * G), "wide_mean_at_G": r(Wbook[yr == y].mean() * G),
                               "wide_fund_negative_year": bool(Wfund[yr == y].mean() < 0), "wide_w3_fund_mean": r(RW[wi, WC["w3_fund"]][yr == y].mean())} for y in YRS}
neg = [y for y in YRS if Wfund[yr == y].mean() < 0]
OUT["C_summary"] = {"years_wide_fund_negative": neg, "blend0.7_gain_vs_live_in_those_years": {y: OUT["C_regime_by_year"][y]["blend0.7_gain_vs_live"] for y in neg},
                    "blend_exfund_only(live+wide_exfund, w=0.7)_by_year_sharpe": {y: r(sh((0.3 * Lbook + 0.7 * Wexf)[yr == y])) for y in YRS},
                    "wide_fund_sharpe_2022_24": r(sh(Wfund[yr <= 2024])), "wide_fund_sharpe_2025_26": r(sh(Wfund[yr >= 2025])), "wide_exfund_sharpe_2022_24": r(sh(Wexf[yr <= 2024])), "wide_exfund_sharpe_2025_26": r(sh(Wexf[yr >= 2025]))}
# ---- D. sign evidence (computed facts) ----
OUT["D_sign_evidence"] = {"wide_fund_leg": {"construction": "sc['fund'] = +f_fund_ema_v1(多高 funding EMA); shadow_loop.py L344 legz['fund']=xz(fe_v) 同号; PREREG_wide_book_assembly §1 三腿 slow+rev24+fund_ema",
                                            "carry_paid_per_unit_target_gross_x2": r(Wl["fund"]["carry"].mean() * G), "price_pnl_x2": r(Wl["fund"]["pnl"].mean() * G), "=> direction": "付 carry 且价格 P&L 为正 ⇒ 多高 funding(动量/拥挤)"},
                          "live_funding_leg": {"construction": "legs.py SIGNS funding=-1 × rank_centered(funding_ema) ⇒ 空高 funding", "carry_paid_per_unit_target_gross_x2": r(L["funding"]["carry"].mean() * G), "price_pnl_x2": r(L["funding"]["pnl"].mean() * G), "=> direction": "收 carry, 价格 P&L≈0 ⇒ 该腿的收益 = 纯 carry 收取"},
                          "zoo_ic_f_fund_ema(kcurve_2026-08-15/zoo_scan.json)": {"ic": 0.0132, "t": 8.08, "liq110": 0.0175, "wide400": 0.0237, "by_year": {"2023": 0.0018, "2024": 0.0122, "2025": 0.0192, "2026": 0.024}, "reading": "正 IC = 高 funding → 下 4h 更高收益 ⇒ 宽书 +FE 是 zoo 认证方向(2024-26 走强, 2023≈0)"},
                          "live_certification(memory ma_v2_funding_ema_GO 2026-07-08)": "high funding → low future return(crowding-reversion), long lowest / short highest; 1h L/S BE 18.8bps ⇒ 在役 −1 号亦是认证方向(不同窗口/视界/口径)"}
json.dump(OUT, open(os.path.join(RES, "w2_legs_analysis_2026-08-21.json"), "w"), indent=1, ensure_ascii=False)
print("A_live", json.dumps(OUT["A_live_legs_S1"], ensure_ascii=False)); print("A_wide", json.dumps(OUT["A_wide_legs_d30"], ensure_ascii=False)); print("A_books", json.dumps(OUT["A_books"], ensure_ascii=False))
print("A_carry", json.dumps(OUT["A_carry_reconciliation"], ensure_ascii=False)); print("B1", json.dumps(OUT["B1_rho"], ensure_ascii=False)); print("B2", json.dumps(OUT["B2_blend_decomposition"], ensure_ascii=False))
for k, v in OUT["B3_variants"].items(): print("B3", k, json.dumps({kk: vv for kk, vv in v.items() if kk != "grid"}, ensure_ascii=False))
print("B4", json.dumps(OUT["B4_wide_fund_carry_sensitivity"], ensure_ascii=False)); print("C", json.dumps(OUT["C_regime_by_year"], ensure_ascii=False)); print("C_sum", json.dumps(OUT["C_summary"], ensure_ascii=False))
