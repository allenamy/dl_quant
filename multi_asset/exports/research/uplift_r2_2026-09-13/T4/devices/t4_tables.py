#!/usr/bin/env python3
"""t4_tables.py — renders receipts/TABLES_T4.md from RECEIPT_T4_judge.json (score + book + verdict) and RECEIPT_T4_live_judge.json
(live-window gates, summary, per-anchor rows). No computation beyond formatting. Mac, read-only on receipts.
Launch: env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4_tables.py"""
import json, os, hashlib, time
HERE = os.path.dirname(os.path.abspath(__file__)); T4 = os.path.dirname(HERE); R = T4 + "/receipts"
J = json.load(open(R + "/RECEIPT_T4_judge.json")); L = json.load(open(R + "/RECEIPT_T4_live_judge.json"))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
f4 = lambda x: "%+.4f" % x; f6 = lambda x: "%+.6f" % x; ci = lambda c, f=f4: "[%s, %s]" % (f(c[0]), f(c[1]))
out = ["> 由 `devices/t4_tables.py` 从 `receipts/RECEIPT_T4_judge.json`(sha256 %s)与 `receipts/RECEIPT_T4_live_judge.json`(sha256 %s)渲染, %s" % (sha(R + "/RECEIPT_T4_judge.json")[:16], sha(R + "/RECEIPT_T4_live_judge.json")[:16], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), ""]
S = J["score"]
out += ["## T1 · 分数层(K1 = 按服务 v1, K0 = 训练一致 v0 = 归档研究 king; K0f = 未量化 v0 零对照)", "",
        "窗口锚数: " + ", ".join("%s %d" % (k, v) for k, v in S["windows_n"].items()) + "; 「W_ALPHA 上有 king 分数的锚」== KING_LIVE: %s; 首个有 king 分数的锚 %s" % (S["W_ALPHA_kingfinite_equals_KING_LIVE"], S["first_king_finite_anchor_in_WA"]), "",
        "| 窗 | 逐锚 Spearman(K0,K1) 均值 / 中位 / p5 / p1 / 最小 | 十分位变动份额 全部 / 4h / 1h / 8h | IC K0 [CI95] | IC K1 [CI95] | ΔIC K1−K0 [CI95] | ΔIC K0f−K0 [CI95] |", "|---|---|---|---|---|---|---|"]
for w in ("KING_LIVE", "Y2026"):
    o = S[w]; r = o["spearman_K0_vs_K1"]; d = o["decile_change_share_K1"]
    out.append("| %s | %.5f / %.5f / %.5f / %.5f / %.5f | %.2f%% / %.2f%% / %.2f%% / %.2f%% | %.5f %s | %.5f %s | %s %s | %.1e %s |" % (
        w, r["mean"], r["median"], r["p5"], r["p1"], r["min"], 100 * d["all"]["share"], 100 * d["4h"]["share"], 100 * d["1h"]["share"], 100 * d["8h"]["share"],
        o["IC_K0"]["mean"], ci(o["IC_K0"]["ci95"], lambda x: "%.5f" % x), o["IC_K1"]["mean"], ci(o["IC_K1"]["ci95"], lambda x: "%.5f" % x), f6(o["dIC_K1_minus_K0"]["mean"]), ci(o["dIC_K1_minus_K0"]["ci95"], f6),
        o["dIC_K0f_minus_K0"]["mean"], ci(o["dIC_K0f_minus_K0"]["ci95"], lambda x: "%.1e" % x)))
out += ["", "十分位格数(KING_LIVE): " + ", ".join("%s %d/%d" % (c, v["changed"], v["cells"]) for c, v in S["KING_LIVE"]["decile_change_share_K1"].items()) + "; K0f 零对照十分位变动: " + ", ".join("%s %d" % (c, v["changed"]) for c, v in S["KING_LIVE"]["decile_change_share_K0f"].items()),
        "", "ΔIC 逐年(KING_LIVE, 描述): " + ", ".join("%s %s" % (y, f6(v["mean"])) for y, v in S["KING_LIVE"]["dIC_K1_minus_K0"]["by_year"].items()), ""]
B = J["book"]
out += ["## T2 · 书层 Δg(bps/锚/单位 gross; 配对 = 同基线同种子; CI95 = UTC 日块自举 2000)", "",
        "| 臂 − 基线 | 基线 | 种子 | W_ALPHA Δg [CI95] | KING_LIVE Δg [CI95] | KING_LIVE g 基线 → 臂 | KING_LIVE Sharpe 基线 → 臂 | Δpnl / Δcarry / Δcost | Δτ % | Y2026 Δg [CI95] | 2024 前 max|Δg| |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for key, v in B.items():
    arm, base, seed = key.split("|"); kl = v["KING_LIVE"]; wa = v["W_ALPHA"]; y6 = v["Y2026"]
    out.append("| %s | %s | %s | %s %s | %s %s | %.4f → %.4f | %.3f → %.3f | %s / %s / %s | %+.2f | %s %s | %.1e |" % (
        arm.replace("_minus_", " − "), base, seed[1:], f4(wa["dg"]), ci(wa["ci95"]), f4(kl["dg"]), ci(kl["ci95"]), kl["g_base"], kl["g_arm"], kl["sharpe_base"], kl["sharpe_arm"],
        f4(kl["dpnl"]), f4(kl["dcarry"]), f4(kl["dcost"]), kl["dtau_pct"], f4(y6["dg"]), ci(y6["ci95"]), v["pre2024_max_abs_dg"]))
out += ["", "KING_LIVE 逐年 Δg(描述): " + "; ".join("%s: %s" % (k, ", ".join("%s %s" % (y, f4(z["dg"])) for y, z in v["KING_LIVE"]["by_year"].items())) for k, v in B.items() if k.startswith("K1")), ""]
V = J["verdict"]
out += ["## T3 · 判决(§5 冻结规则)", "", "```", json.dumps(V, indent=1, default=str), "```", ""]
G = L["gates"]; SU = L["summary"]
out += ["## T4 · 实盘窗门", "", "| 门 | 读数 | 判 |", "|---|---|---|",
        "| PC1 served ≡ 线上 | king L∞ 最大 %.2e(%d/41 ≤ 1e-6); combo target_live L∞ 最大 %.2e(%d/41 ≤ 2e-4); 席位腿收益条目差最大 %.1e | %s |" % (G["PC1"]["king_Linf_max"], G["PC1"]["king_pass_anchors"], G["PC1"]["combo_target_live_Linf_max"], G["PC1"]["combo_pass_anchors"], G["PC1"]["lr_entry_max_abs_diff"], "PASS" if G["PC1"]["PASS"] else "FAIL"),
        "| PC-INJ 注入路径惰性 | X 逐位 %s / pred 逐位 %s / king npz 逐位 %s / king target 文件逐位 %s | %s |" % (G["PC_INJ"]["X_bitwise"], G["PC_INJ"]["pred_bitwise"], G["PC_INJ"]["king_npz_bitwise"], G["PC_INJ"]["king_target_json_bitwise"], "PASS" if G["PC_INJ"]["PASS"] else "FAIL"),
        "| ONE-PLACE | diff 改动行 %d; 成员集全同 %s; 第 76 列外 X 逐位 %s; 第 76 列相同行 pred 相同 %s(第 76 列相同 %d / 不同 %d / 总 %d 行) | %s |" % (G["ONE_PLACE"]["diff_changed_lines"], G["ONE_PLACE"]["members_equal_all"], G["ONE_PLACE"]["X_other_cols_bitwise_all"], G["ONE_PLACE"]["pred_equal_where_col76_equal_all"], G["ONE_PLACE"]["rows_col76_equal"], G["ONE_PLACE"]["rows_col76_differ"], G["ONE_PLACE"]["rows_total"], "PASS" if G["ONE_PLACE"]["PASS"] else "FAIL")]
for gk in ("V0P", "V1R", "C81"):
    g = G[gk]
    out.append("| %s | n %d(相对比较 %d); 相对差中位 %s; ≤1e-3 份额 %s; ≤1e-6 份额 %s; 最大 %s; 超 1e-3 名(前 25): %s | %s |" % (gk, g["n"], g["n_rel"], "%.2e" % g["median_rel"] if g["median_rel"] is not None else "—", "%.4f" % g["share_rel_le_1e3"] if g["share_rel_le_1e3"] is not None else "—",
               "%.4f" % g["share_rel_le_1e6"] if g["share_rel_le_1e6"] is not None else "—", "%.2e" % g["max_rel"] if g["max_rel"] is not None else "—", json.dumps(g.get("names_over_1e3", {}), ensure_ascii=False), "PASS" if g["PASS"] else "FAIL"))
out += ["", "## T5 · 实盘窗汇总(v0 臂 − served 臂, 41 链式锚)", "", "```", json.dumps(SU, indent=1, default=str), "```", "",
        "## T6 · 逐锚(v0 臂对 served 臂)", "",
        "| 锚 UTC | king 分数 Spearman | 十分位变动 全部 / 4h / 1h / 8h | 第 76 列不同行 | king 目标 L∞ / 归一 L1 | combo target_live L∞ / 归一 L1 / 相关 | combo gross v0 / served | 掩码席位 king v0 / served | 价格 Δg(描述) |", "|---|---|---|---|---|---|---|---|---|"]
for r in L["per_anchor"]:
    d = r["decile_change"]; kt = r["king_target"]; ct = r["combo_target_live"]
    sh = lambda c: "%d/%d" % (d[c]["changed"], d[c]["n"])
    out.append("| %s | %.4f | %s / %s / %s / %s | %d/%d | %.2e / %.4f | %.2e / %.4f / %.5f | %.4f / %.4f | %.4f / %.4f | %s |" % (
        r["utc"], r["king_score_spearman"], sh("all"), sh("4h"), sh("1h"), sh("8h"), r["col76_rows_differ"], r["members"], kt["Linf"], kt["L1_norm"], ct["Linf"], ct["L1_norm"], ct["corr"],
        ct["gross_v0"], ct["gross_served"], r["w3m_v0"][0], r["w3m_served"][0], ("%+.3f" % r["price_dg_bps_descriptive"]) if "price_dg_bps_descriptive" in r else "—"))
open(R + "/TABLES_T4.md", "w").write("\n".join(out) + "\n"); print("wrote", R + "/TABLES_T4.md", len(out), "lines")
