#!/usr/bin/env python3
"""at_render.py — renders the receipts of at_control / at_build / at_attrib / at_regime into one markdown
table file. Presentation only: it computes nothing, it selects nothing, it prints every period and every bin
the compute devices produced. Runs on the mac, reads the receipts directory, writes ATTRIB_TABLES.md there.

usage: python at_render.py <RECEIPTS_DIR>
"""
import hashlib, json, os, sys

R = sys.argv[1] if len(sys.argv) > 1 else "."
CT = json.load(open(f"{R}/AT_CONTROL.json"))
BD = json.load(open(f"{R}/AT_BUILD.json"))
AT = json.load(open(f"{R}/AT_ATTRIB.json"))
RG = json.load(open(f"{R}/AT_REGIME.json"))
import os
LG = json.load(open(f"{R}/AT_LEGS2.json")) if os.path.exists(f"{R}/AT_LEGS2.json") else None
BT = json.load(open(f"{R}/AT_BETA.json")) if os.path.exists(f"{R}/AT_BETA.json") else None
COLS = ["2022H2", "2023pre", "2023full", "2024", "2025", "2026H1", "2026JA", "2026", "FULL_RECIPE"]
O = []


def w(s=""):
    O.append(s)


def f(x, n=3):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    try:
        return ("%+." + str(n) + "f") % float(x)
    except Exception:
        return str(x)


def pct(x, n=2):
    return "—" if x is None else ("%+." + str(n) + "f%%") % (100.0 * float(x))


def row(cells):
    w("| " + " | ".join(str(c) for c in cells) + " |")


def head(cells):
    row(cells)
    row(["---"] * len(cells))


w("<!-- rendered by at_render.py from AT_CONTROL.json / AT_BUILD.json / AT_ATTRIB.json / AT_REGIME.json -->")
w("")
w("# 归因全表 · 2026 与历史(认证生产路径 object B / A0 / scaled)")
w("")
w("单位: **bps / 锚 / 单位目标 gross**(与基线表同口径, 分母 gm·NAV(A), gm = 2.0), 除非另有标注。")
w("L1 = 模拟器已实现现金(32 条成交路径均值); L2 = 目标书纸面层。")
w("")

# ── T0 control ──
w("## T0 控制复现(先于任何新数字)")
w("")
w("自己的实现从 32 条原始成交路径重算逐时段表, 与已发表 `BT_MAIN_A0.json` fa3c2ce7 逐格对比。")
w("")
c = CT["control"]["per_metric_max_abs_diff"]
head(["量", "max |Δ|", "出现在", "我的值", "已发表值"])
for k in sorted(c, key=lambda k: -c[k]["max_abs"]):
    if k.startswith("pathdist"):
        continue
    row([k, "%.3e" % c[k]["max_abs"], c[k]["at"] or "—", "%.10g" % c[k].get("mine", 0), "%.10g" % c[k].get("published", 0)])
pd = {k: v for k, v in c.items() if k.startswith("pathdist")}
kk = max(pd, key=lambda k: pd[k]["max_abs"])
row(["(逐路径分布 24 格最差)", "%.3e" % pd[kk]["max_abs"], kk, "%.10g" % pd[kk].get("mine", 0), "%.10g" % pd[kk].get("published", 0)])
w("")
w("最差相对格: `%s` / %s, 相对偏差 %.2e。" % (CT["control"]["worst_cell"]["metric"], CT["control"]["worst_cell"]["period"], CT["control"]["worst_cell"]["abs"]))
w("")

# ── T1 block R ──
w("## T1 块 R · L1(已实现)vs L2(纸面)逐时段对账")
w("")
head(["时段", "锚", "L1 g", "L1 价格", "L1 资金费", "L1 手续费", "L2 价格", "L2 资金费", "L2 净", "残差 L1−L2", "残差占 L1 g"])
for k in COLS + ["PARTIAL_RECIPE", "HIST", "WHOLE_WINDOW"]:
    d = AT["block_R_reconciliation"].get(k)
    if not d:
        continue
    row([k, d["n_anchors"], f(d["L1"]["g"]), f(d["L1"]["price"]), f(d["L1"]["funding_paid"]), f(d["L1"]["fee"]),
         f(d["L2"]["price"]), f(d["L2"]["funding_paid"]), f(d["L2"]["net"]), f(d["resid_L1_minus_L2"]),
         pct(d["resid_share_of_L1_g"], 1)])
w("")

# ── T2 block A ──
w("## T2 块 A · 逐腿(两条路径 A1 / A2 并列, 价格项)")
w("")
w("> ⛔ **本表整体作废(E-0920-B)**: 装置把组件内部的信号席位当成了两个组件之间的融合权重。原字节保留作历史。")
w("> **更正后的组件层分解见下面的 T2b, 以及结果件 §3。**")
w("")
head(["时段", "A1 king", "A1 fund", "A1 整形残差", "A1 合计", "A2 king", "A2 fund", "A2 合计",
      "腿自身 gross 上的原始收益 king / fund", "φ_fund 均值", "只写 king 文件的锚占比", "A1−A2 差 >5%?"])
for k in COLS:
    d = AT["block_A_legs"].get(k)
    if not d:
        continue
    g_ = d["A1_vs_A2_gap"]
    fl = ("king " if g_["king_exceeds_5pct"] else "") + ("fund" if g_["fund_exceeds_5pct"] else "")
    row([k, f(d["A1_price"]["king"]), f(d["A1_price"]["fund"]), f(d["A1_price"]["shape_residual"]), f(d["A1_price"]["total"]),
         f(d["A2_price"]["king"]), f(d["A2_price"]["fund"]), f(d["A2_price"]["total"]),
         "%s / %s" % (f(d["raw_leg_price_per_own_gross"]["king"], 2), f(d["raw_leg_price_per_own_gross"]["fund"], 2)),
         f(d["seats"]["phi_fund_mean"], 3), pct(d["seats"]["share_anchors_king_file_only"], 1), fl or "—"])
w("")
w("资金费项的同一拆分:")
w("")
head(["时段", "A1 king 付出", "A1 fund 付出", "A1 整形残差", "A2 king 付出", "A2 fund 付出"])
for k in COLS:
    d = AT["block_A_legs"].get(k)
    if not d:
        continue
    row([k, f(d["A1_funding_paid"]["king"]), f(d["A1_funding_paid"]["fund"]), f(d["A1_funding_paid"]["shape_residual"]),
         f(d["A2_funding_paid"]["king"]), f(d["A2_funding_paid"]["fund"])])
w("")

# ── T3 block B ──
w("## T3 块 B · 逐分组(净贡献 / 价格 / 资金费 / gross 份额)")
w("")
for gname, tab in AT["block_B_groups"].items():
    w("### %s" % gname)
    w("")
    bins = list(tab[COLS[0]].keys())
    head(["档"] + ["%s 净" % k for k in COLS])
    for b in bins:
        row([b] + [f(tab[k][b]["net"]) for k in COLS])
    w("")
    head(["档"] + ["%s gross份额" % k for k in COLS])
    for b in bins:
        row([b] + [pct(tab[k][b]["gross_share"], 1) for k in COLS])
    w("")
    head(["档"] + ["%s 价格" % k for k in COLS] )
    for b in bins:
        row([b] + [f(tab[k][b]["price"]) for k in COLS])
    w("")
    head(["档"] + ["%s 资金费付出" % k for k in COLS])
    for b in bins:
        row([b] + [f(tab[k][b]["funding_paid"]) for k in COLS])
    w("")
    head(["档"] + ["%s 选股" % k for k in COLS])
    for b in bins:
        row([b] + [f(tab[k][b]["selection"]) for k in COLS])
    w("")

# ── T4 block C ──
w("## T4 块 C · 市场 vs 选股")
w("")
w("> ⛔ **本表的「市场」「选股」两列整体作废(E-0920-B)**: 市场项算的是美元净敞口 × 宇宙收益, 按构造为零, 证明的只是美元中性。")
w("> **更正后的事前风险分解见下面的 T4b, 以及结果件 §5。** 其余列(ȳ、多空篮相对 ȳ、死名与成员集份额)不受影响。")
w("")
head(["时段", "价格", "= 市场", "+ 选股", "市场多 / 空", "选股多 / 空", "宇宙 ȳ bps/4h",
      "多头篮−ȳ", "空头篮−ȳ", "已计价净敞口 /gross", "死名 gross 份额", "成员集外 gross 份额"])
for k in COLS:
    d = AT["block_C_market_vs_selection"].get(k)
    if not d:
        continue
    row([k, f(d["price"]), f(d["market"]), f(d["selection"]),
         "%s / %s" % (f(d["market_long"], 2), f(d["market_short"], 2)),
         "%s / %s" % (f(d["selection_long"], 2), f(d["selection_short"], 2)),
         f(d["ubar_bps"], 2), f(d["long_basket_minus_ubar_bps"], 2), f(d["short_basket_minus_ubar_bps"], 2),
         pct(d["net_priced_exposure_share_of_gross"], 2), pct(d["gross_out_of_life_share"], 3),
         pct(d["gross_outside_member_set_share"], 2)])
w("")

# ── T2b / T4b: the corrected blocks ──
if LG:
    w("## T2b 块 A(**已更正**)· 组件层分解 —— 0.55 King 组件 + 0.45 F10 组件, 权重固定")
    w("")
    w("结构断言逐位通过: %s" % LG["structure"]["book_level"])
    w("")
    head(["时段", "锚", "写 combo", "KC", "FC", "整形位移", "三腿 king 文件", "= 价格", "r(KC)", "r(FC)", "模型分歧", "资金费信号 z 权重"])
    for k in COLS:
        d = LG["per_period"].get(k)
        if not d:
            continue
        c_ = d["component_own_gross_return"]; s_ = d["seats_z_level"]
        row([k, d["n_anchors"], pct(d["share_anchors_combo"], 1), f(d["price"]["KC_king_component"]),
             f(d["price"]["FC_f10_component"]), f(d["price"]["reshape_shift"]), f(d["price"]["KING_FILE_3leg"]),
             f(d["price_total"]), f(c_["kc_king_component"], 2), f(c_["fc_f10_component"], 2),
             f(c_["difference_kc_minus_fc_isolates_model_disagreement"], 2), f(s_["funding_signal_z_weight_mean"], 3)])
    w("")
    w("**三信号(资金费 / king / F10)的书层拆分不可识别**: %s" % LG["structure"]["not_identifiable"])
    w("")
    w("席位取极值的子样本(按恒等式精确; ⚠ %s):" % LG["seat_extreme_subsamples"]["caveat"])
    w("")
    head(["子样本", "时段", "锚", "占比", "g", "价格", "资金费付出"])
    for tag, lab in (("pure_model_composite_funding_seat_exactly_zero", "资金费席位=0 ⇒ 纯 0.55/0.45 模型复合"),
                     ("pure_funding_book_model_seat_exactly_zero", "模型席位=0 ⇒ 纯资金费书")):
        for k, v in LG["seat_extreme_subsamples"][tag].items():
            if k in COLS or k in ("HIST",):
                row([lab, k, v["n_anchors"], pct(v["share_of_period"], 1), f(v["g"]), f(v["price"]), f(v["funding_paid"])])
    w("")
    w("king 文件锚(回落到生产者原三腿 king 书)单列:")
    w("")
    head(["时段", "king 文件锚", "占比", "那些锚上的 g", "那些锚上的纸面价格", "对全期价格的贡献"])
    for k in COLS + ["HIST"]:
        v = LG.get("king_file_anchors_conditional", {}).get(k)
        if not v:
            continue
        row([k, v["n_king_file_anchors"], pct(v["share_of_period"], 1), f(v["g_on_those_anchors"], 2),
             f(v["paper_price_on_those_anchors"], 2), f(v["contribution_to_the_period_price"])])
    w("")
if BT:
    w("## T4b 块 C(**已更正**)· 事前 β 与风格的风险分解")
    w("")
    w("β 分布(持仓名): " + json.dumps(BT["beta_distribution_held_names"]))
    w("")
    head(["时段", "价格", "共同(β×市场)", "残差", "未归属", "事前净 β 均值", "|净 β| 均值", "净 β p05/p95",
          "多头净 β", "空头净 β", "美元净/gross", "市场 bps/4h"])
    for k in COLS:
        d = BT["per_period"].get(k)
        if not d:
            continue
        row([k, f(d["price"]), f(d["common_market"]), f(d["residual_selection"]), f(d["unattributed_no_beta"]),
             f(d["book_ex_ante_net_beta_mean"]), f(d["book_ex_ante_net_beta_absmean"]),
             "[%s, %s]" % (f(d["book_ex_ante_net_beta_p05_p95"][0], 2), f(d["book_ex_ante_net_beta_p05_p95"][1], 2)),
             f(d["net_beta_long_side"]), f(d["net_beta_short_side"]), f(d["dollar_net_over_gross"], 5), f(d["mean_market_bps"], 2)])
    w("")
    head(["时段", "共同(β+风格)", "残差(名字特有)", "多头 共同/残差", "空头 共同/残差", "入回归名数", "BTC 净 β", "BTC 共同"])
    for k in COLS:
        d = BT["per_period"].get(k)
        if not d:
            continue
        row([k, f(d["style_common_risk_and_style"]), f(d["style_residual_selection"]),
             "%s / %s" % (f(d["style_common_long"], 2), f(d["style_residual_long"], 2)),
             "%s / %s" % (f(d["style_common_short"], 2), f(d["style_residual_short"], 2)),
             "%.0f" % d["style_mean_names_in_fit"], f(d.get("btc_net_beta_mean"), 3), f(d.get("btc_common_market"), 3)])
    w("")
    w("2026 − HIST 的 Δg = +2.915 按状态量做「格间移动 vs 格内变化」:")
    w("")
    head(["状态量", "高档占比 HIST → 2026", "总 Δ", "格间移动", "格内变化"])
    for cn, v in BT["bucket_shift_vs_within_2026_minus_HIST"].items():
        row([cn, "%s → %s" % (pct(v["share_hist"][2], 1), pct(v["share_2026"][2], 1)),
             f(v["total_delta"]), f(v["between_bucket_shift"]), f(v["within_bucket_change"])])
    w("")

# ── T5 block D ──
w("## T5 块 D · 锚级条件量")
w("")
names = list(AT["block_D_conditions_levels"][COLS[0]].keys())
head(["条件量(均值)"] + COLS)
for n in names:
    row([n] + [f(AT["block_D_conditions_levels"][k][n]["mean"], 4) if AT["block_D_conditions_levels"].get(k) else "—" for k in COLS])
w("")
w("完整配方窗内按扩张窗三分位分档的 g(bps/锚/gross):")
w("")
head(["条件量", "低档 锚/g", "中档 锚/g", "高档 锚/g", "高−低 g", "低档 选股", "高档 选股", "低档 资金费", "高档 资金费"])
for n, cell in AT["block_D_conditions_cells_FULL_RECIPE"].items():
    def gv(b, key="g"):
        return cell.get(b, {}).get(key)
    row([n,
         "%s / %s" % (cell["low"].get("n_anchors"), f(gv("low"))),
         "%s / %s" % (cell["mid"].get("n_anchors"), f(gv("mid"))),
         "%s / %s" % (cell["high"].get("n_anchors"), f(gv("high"))),
         f((gv("high") - gv("low")) if (gv("high") is not None and gv("low") is not None) else None),
         f(gv("low", "selection")), f(gv("high", "selection")),
         f(gv("low", "funding_paid")), f(gv("high", "funding_paid"))])
w("")

# ── T6 family ──
w("## T6 冻结家族(22 个分组检验 + 8 个条件量检验 = 30, Holm 0.05)")
w("")
w("分组检验: H0 = 该组的每锚净贡献在 2026(01-01…08-31)与 HIST(2023-06-30…2025-12-31)相同。")
w("条件量检验: H0 = 完整配方窗内高档与低档的 g 相同。")
w("")
head(["检验", "点估计", "CI95(5 日块)", "CI95(1 日)", "CI95(10 日)", "p(双侧)", "Holm 阈值", "Holm 拒绝", "2026 / HIST 或 高 / 低"])
for t in AT["family_holm"]["tests"]:
    ci = t.get("ci95") or [None, None]
    c1 = t.get("ci95_block1") or [None, None]
    c10 = t.get("ci95_block10") or [None, None]
    aux = ("%s / %s" % (f(t.get("mean_2026")), f(t.get("mean_hist")))) if "mean_2026" in t else \
          ("%s / %s" % (f(t.get("g_high")), f(t.get("g_low"))))
    row([t["test"], f(t.get("point")), "[%s, %s]" % (f(ci[0]), f(ci[1])), "[%s, %s]" % (f(c1[0]), f(c1[1])),
         "[%s, %s]" % (f(c10[0]), f(c10[1])),
         ("%.4f" % t["p"]) if t.get("p") is not None else "—",
         ("%.5f" % t["holm_threshold"]) if t.get("holm_threshold") else "—",
         "**是**" if t.get("holm_reject_at_0.05") else "否", aux])
w("")
w("拒绝 %d / %d。" % (AT["family_holm"]["n_rejected"], AT["family_holm"]["m"]))
w("")

# ── T7 extremes ──
E = AT["block_E_extremes"]
w("## T7 块 E · 极端锚(完整配方窗上下各 1%%, 各 %d 个)" % E["n_each"])
w("")
w("逐年个数 —— 最好: %s; 最差: %s" % (json.dumps(E["year_counts_top"], ensure_ascii=False), json.dumps(E["year_counts_bottom"], ensure_ascii=False)))
w("")
for tag, lab in (("top", "最好 1%"), ("bottom", "最差 1%")):
    w("### %s(按已实现 g 排序, 前 12 个)" % lab)
    w("")
    head(["锚", "书", "L1 g", "L1 价格", "L1 资金费", "L2 市场", "L2 选股", "A1 king", "A1 fund", "ȳ bps", "止损/平仓/停机", "贡献最大的 5 名(净 bps)"])
    for d in E[tag][:12]:
        nm = ", ".join("%s %s" % (x["name"], f(x["net"], 1)) for x in d["top10_names_by_abs_net"][:5])
        ev = d["L1_events"]
        row([d["anchor"][:16], d["kind"], f(d["L1"]["g"], 2), f(d["L1"]["price"], 2), f(d["L1"]["funding_paid"], 2),
             f(d["L2"]["market"], 2), f(d["L2"]["selection"], 2), f(d["L2"]["A1_king"], 2), f(d["L2"]["A1_fund"], 2),
             f(d["ubar_bps"], 1), "%g/%g/%g" % (ev["stops"], ev["flattens"], ev["halt"]), nm])
    w("")
w("连续段极值:")
w("")
head(["段", "最差 起—止", "最差 Σg bps", "最差 2× NAV", "最好 起—止", "最好 Σg bps", "最好 2× NAV"])
for lab, key in (("3 锚", "segments_3_anchors"), ("24h(6 锚)", "segments_24h_6_anchors")):
    s = E[key]
    row([lab, "%s → %s" % (s["worst"]["from"][:16], s["worst"]["to"][:16]), f(s["worst"]["sum_g_bps"], 1), pct(s["worst"]["nav_return_2x"]),
         "%s → %s" % (s["best"]["from"][:16], s["best"]["to"][:16]), f(s["best"]["sum_g_bps"], 1), pct(s["best"]["nav_return_2x"])])
w("")

# ── T8 block F ──
F = AT["block_F_2023"]
w("## T8 块 F · 2023-06-30 → 2023-12-31 的下跌(%d 锚), 每项带 CI" % F["n_anchors"])
w("")
head(["项", "2023H2 点估计", "CI95", "2024–2026 参照", "CI95", "差(2023H2 − 参照)"])
for n, d in F["items"].items():
    a, b = d["2023H2"], d["2024_2026_reference"]
    row([n, f(a["point"]), "[%s, %s]" % (f(a["ci95"][0]), f(a["ci95"][1])), f(b["point"]),
         "[%s, %s]" % (f(b["ci95"][0]), f(b["ci95"][1])), f(a["point"] - b["point"])])
w("")
for gname, tab in F["groups_2023_vs_reference"].items():
    w("**%s** (2023H2 净 / 参照净 / 2023H2 gross份额 / 参照 gross份额)" % gname)
    w("")
    head(["档", "2023H2 净", "参照 净", "2023H2 价格", "2023H2 资金费", "2023H2 选股", "2023H2 gross", "参照 gross"])
    for b, d in tab.items():
        row([b, f(d["net_2023H2"]), f(d["net_reference"]), f(d["price_2023H2"]), f(d["funding_2023H2"]),
             f(d["selection_2023H2"]), pct(d["gross_share_2023H2"], 1), pct(d["gross_share_reference"], 1)])
    w("")

# ── T9 block G ──
w("## T9 块 G · 条件的持续性(描述性 —— 历史频率, 不是预测)")
w("")
w("> " + RG["caveat"])
w("")
head(["条件量", "档", "游程中位(天)", "p90(天)", "最长(天)", "游程数", "+7d 同档", "+30d 同档", "+90d 同档", "完整配方窗 g", "CI95", "锚"])
for n, d in RG["conditions"].items():
    for b in ("low", "mid", "high"):
        r_ = d["run_lengths_anchors"][b]
        p_ = d["persistence_same_bucket"][b]
        g_ = d["g_FULL_RECIPE"][b]
        ci = g_.get("ci95") or [None, None]
        row([n, b, f(r_.get("median_days"), 1), f(r_.get("p90_days"), 1), f(r_.get("max_days"), 1), r_.get("n_runs", 0),
             pct(p_["+7d"].get("share_same_bucket"), 1), pct(p_["+30d"].get("share_same_bucket"), 1),
             pct(p_["+90d"].get("share_same_bucket"), 1), f(g_.get("point")),
             "[%s, %s]" % (f(ci[0]), f(ci[1])), g_.get("n_anchors", 0)])
w("")
for sname in ("JOINT8", "JOINT6"):
    cs = RG.get("current_state_" + sname)
    if not cs:
        continue
    w("**当前档位组合 %s(锚 %s%s)**: %s" % (sname, cs["at_anchor"][:16],
      "" if cs["is_axis_end"] else " —— 不是轴末: 该组合里有条件量的冻结标签只到此", ", ".join("%s=%s" % (k, v) for k, v in cs["buckets"].items())))
    w("")
    js = cs["joint_stats"]
    w("该组合在本轴上共 %d 个锚(占已打档锚 %s), %d 段, 中位 %s 锚, p90 %s 锚, 最长 %s 锚; 完整配方窗内 g = %s, CI95 [%s, %s](%s 锚)。"
      % (js["n_anchors"], pct(js["share_of_labelled"], 2), js["n_episodes"], f(js["median_run_anchors"], 1),
         f(js["p90_run_anchors"], 1), js["max_run_anchors"], f(js["g_FULL_RECIPE"].get("point")),
         f((js["g_FULL_RECIPE"].get("ci95") or [None, None])[0]), f((js["g_FULL_RECIPE"].get("ci95") or [None, None])[1]),
         js["g_FULL_RECIPE"].get("n_anchors")))
    w("")
    m = RG.get("2023_fall_modal_combination_" + sname)
    if m:
        w("**2023 下跌段众数组合 %s**: %s —— 占 2023H2 已打档锚 %s(%d 锚); 全轴 %d 锚 / %d 段, 中位 %s 锚, 完整配方窗 g = %s。"
          % (sname, ", ".join("%s=%s" % (k, v) for k, v in m["buckets"].items()),
             pct(m["share_of_2023H2_labelled_anchors"], 1), m["n_2023H2_fully_labelled"],
             m["stats"]["n_anchors"], m["stats"]["n_episodes"], f(m["stats"]["median_run_anchors"], 1),
             f(m["stats"]["g_FULL_RECIPE"].get("point"))))
        w("")
    for tag, lab in (("match_profile_vs_current_" + sname, "与当前状态"), ("match_profile_vs_2023_fall_" + sname, "与 2023 下跌众数组合")):
        if tag not in RG:
            continue
        w("匹配剖面 %s(%s: 几个条件档位相同 → 锚数 / 该匹配度下完整配方窗的已实现 g):" % (lab, sname))
        w("")
        ks = list(RG[tag]["by_match_count"].keys())
        head(["相同档位个数"] + ks)
        row(["锚数"] + [RG[tag]["by_match_count"][k]["n_anchors"] for k in ks])
        row(["g(完整配方窗)"] + [f(RG[tag]["by_match_count"][k].get("g_FULL_RECIPE")) for k in ks])
        row(["其中完整配方窗锚数"] + [RG[tag]["by_match_count"][k].get("n_anchors_FULL_RECIPE", 0) for k in ks])
        r_ = RG[tag]["runs_with_at_most_one_mismatch"]
        w("")
        w("「最多一个档位不同」的连续段: %d 段, 中位 %s 锚, p90 %s 锚, 最长 %s 锚, 合计 %s 锚。"
          % (r_.get("n_episodes", 0), f(r_.get("median_anchors"), 1), f(r_.get("p90_anchors"), 1), r_.get("max_anchors"), r_.get("total_anchors")))
        w("")

w("## T10 书的形态(逐时段)")
w("")
head(["时段", "锚", "写 combo 的占比", "φ_fund 均值", "持仓名数均值", "成员数均值", "死名 gross 份额", "|s| p99"])
for k in COLS:
    d = AT["book_shape_by_period"].get(k)
    if not d:
        continue
    row([k, d["n_anchors"], pct(d["kind_combo_share"], 1), f(d["phi_fund_mean"], 3), f(d["n_held_mean"], 1),
         f(d["n_members_mean"], 1), pct(d["gross_out_of_life_share"], 3), f(d["share_abs_p99"], 2)])
w("")
w("装置收据: AT_CONTROL.json / AT_BUILD.json / AT_ATTRIB.json / AT_REGIME.json / AT_SELFTEST.json / AT_PRERUN.json。")

txt = "\n".join(O) + "\n"
p = f"{R}/ATTRIB_TABLES.md"
open(p, "w").write(txt)
print("wrote", p, len(O), "lines, sha256", hashlib.sha256(txt.encode()).hexdigest()[:16])
