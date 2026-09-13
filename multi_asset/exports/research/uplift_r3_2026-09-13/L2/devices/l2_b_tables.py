"""l2_b_tables.py — Mac renderer: receipts/pod2/RECEIPT_L2_B_{build,selftest,fit,null,judge}.json → receipts/TABLES_L2.md (no computation beyond formatting).
Usage: /usr/bin/python3 devices/l2_b_tables.py <L2 dir>"""
import os, sys, json

L2 = sys.argv[1]
RD = os.path.join(L2, "receipts", "pod2")
R = {k: json.load(open(os.path.join(RD, "RECEIPT_L2_B_%s.json" % k))) for k in ("build", "selftest", "fit", "null", "judge")}
J = R["judge"]; SEEDS = ("42", "2027"); CELLS = ("R_A", "R_B", "L_A", "L_B"); YEARS = ("2023", "2024", "2025", "2026")
f = lambda x, d=2: ("—" if x is None else ("%+.*f" % (d, x)))
ci = lambda c, d=2: "[%s, %s]" % (f(c[0], d), f(c[1], d))
out = []
w = out.append
w("# TABLES · L2(由 `devices/l2_b_tables.py` 从 pod2 收据渲染; 单位 bps / 名 / 锚, s = 空头价格盈亏, 负 = 挤空亏损)\n")
w("## T0 前置门\n")
w("| 门 | 读数 |\n|---|---|")
b = R["build"]
w("| G-IN | POP 重算不一致 %s; MANIFEST sha `%s…`; CHECKSUM 未解决 %d; 失败文件 %s; 语义违例占比 %.5f |" % (
    json.dumps(b["G_IN_pop_recompute_mismatch"]), b["G_IN"]["manifest_sha256"][:12], b["G_IN"]["checksum_mismatch"], b["G_IN"]["files_failed"], b["G_IN"]["regime_violation_share"]))
st = R["selftest"]
w("| G-SF | 逐位不变 %d/%d; 负控变化 %s / 测试 %s |" % (st["G_SF"]["identical"], st["G_SF"]["total"], json.dumps(st["G_SF"]["neg"]), json.dumps(st["G_SF"]["neg_tested"])))
pc = st["G_PC"]
w("| G-PC | 方向 G %s %s → %s; 方差 G %s → %s; 噪声 G %s → %s; 方向分数锚内秩 IC %.4f |" % (
    f(pc["direction"]["G"]), ci(pc["direction"]["G_ci"]), json.dumps(pc["direction"]["conds"]), f(pc["variance"]["G"]), pc["variance"]["first_fail"],
    f(pc["noise"]["G"]), pc["noise"]["first_fail"], pc["direction_rank_ic_sampled_anchors"]))
w("| G-ALIGN | %s(行 %d) |" % (json.dumps({k: round(v, 4) for k, v in st["G_ALIGN"]["corr_by_offset"].items()}), st["G_ALIGN"]["rows"]))
w("| 自检门 | %s |" % json.dumps(st["gates"]))
w("| 拟合 | %d 个; lightgbm %s |" % (R["fit"]["n_fits"], R["fit"]["lightgbm"]))
w("| 判官前置 | %s |\n" % json.dumps(J["preconditions"]))
w("## T1 判决格(FULL, P_all)\n")
w("| 种子 | 格 | 锚 / 块 | G [CI95] | G_Y 2023 / 24 / 25 / 26 | ΔG 对 BASE [CI95] | TB CI95 | H [CI95] | G_med | z / q05 | 前向峰 | C1–C6 | 首个不满足 |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    for c in CELLS:
        m, T = c.split("_"); x = J["per_seed"][s]["stats"]["P_all|%s" % T]["%s|FULL" % m]; rd = J["per_seed"][s]["reading"][c]
        w("| %s | %s | %d / %d | %s %s | %s | %s %s | %s | %s %s | %s | %s / %s | %s | %s | %s |" % (
            s, c, x["n_anchors"], x["n_blocks"], f(x["G"]), ci(x["G_ci"]), " / ".join(f(x["G_years"][y]) for y in YEARS), f(x["dG_vs_BASE"]), ci(x["dG_vs_BASE_ci"]),
            ci(x["TB_ci"]), f(x["H"]), ci(x["H_ci"]), f(x["G_med"]), f(x["z"]), f(x["q05"]), x["shift_peak_forward"],
            "".join("✓" if rd["conds"][k] else "✗" for k in ("C1", "C2", "C3", "C4", "C5", "C6")), rd["first_fail"] or "—"))
w("\n**判决**: `%s`; 标签 `%s`; 过门格 %s; 最接近的格 %s(深度 %d)\n" % (J["verdict"], J["fail_label"], J["passing_cells"], J["closest_cell"], J["closest_cell_depth"]))
w("## T2 描述量(不参与判决)\n")
w("| 种子 | 格 | G(BASE) | G(DESC) | G(FULL) − G(DESC) [CI95] | |smr| 加权 G | 锚内秩 IC(分数, 收益) | 顶十分位 s 标准差 / 人口 |")
w("|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    for c in CELLS:
        m, T = c.split("_"); S = J["per_seed"][s]["stats"]["P_all|%s" % T]; x = S["%s|FULL" % m]
        w("| %s | %s | %s %s | %s %s | %s %s | %s | %+.4f | %.3f |" % (s, c, f(S["%s|BASE" % m]["G"]), ci(S["%s|BASE" % m]["G_ci"]), f(S["%s|DESC" % m]["G"]), ci(S["%s|DESC" % m]["G_ci"]),
                                                            f(x["dG_vs_DESC"]), ci(x["dG_vs_DESC_ci"]), f(x["G_gross_weighted"]), x["rank_ic_score_vs_return"], x["top_sd_ratio"]))
w("\n## T3 次要人口 P_neg(C1–C4 标签, 只报)\n")
w("| 种子 | 格 | 锚 | G [CI95] | G_Y | ΔG 对 BASE [CI95] | H [CI95] | G_med | 标签 |")
w("|---|---|---|---|---|---|---|---|---|")
for s in SEEDS:
    for c in CELLS:
        m, T = c.split("_"); x = J["per_seed"][s]["stats"]["P_neg|%s" % T]["%s|FULL" % m]; sec = J["per_seed"][s]["secondary_P_neg"][c]
        w("| %s | %s | %d | %s %s | %s | %s %s | %s %s | %s | %s |" % (s, c, x["n_anchors"], f(x["G"]), ci(x["G_ci"]), " / ".join(f(x["G_years"][y]) for y in YEARS),
                                                             f(x["dG_vs_BASE"]), ci(x["dG_vs_BASE_ci"]), f(x["H"]), ci(x["H_ci"]), f(x["G_med"]), sec["label"]))
w("\n## T4 平移谱(锚内 Spearman(分数, 平移收益) 均值)\n")
for s in SEEDS:
    for c in CELLS:
        m, T = c.split("_"); x = J["per_seed"][s]["stats"]["P_all|%s" % T]["%s|FULL" % m]
        w("- s%s %s: %s; 前向峰 %s" % (s, c, " ".join("%s:%+.4f" % (h, v) for h, v in x["shift_spectrum"].items()), x["shift_peak_forward"]))
w("\n## T5 特征覆盖(有限率, 按年)\n")
for s in SEEDS:
    w("- s%s: %s" % (s, "; ".join("%s rows %d: %s" % (y, v["rows"], ", ".join("%s %.3f" % (k, q) for k, q in v["feature_finite"].items())) for y, v in b["per_seed"][s]["coverage"].items())))
w("\n## T6 零分布(日块循环平移, 500 次)\n")
for s in SEEDS:
    nu = R["null"]["per_seed"][s]
    w("- s%s: sd_null %s; 族最小 z 分位 %s; q05 %.3f; 平移后保留行比例 %s" % (s, json.dumps({k: round(v, 3) for k, v in nu["sd_null"].items()}),
                                                                 json.dumps({k: round(v, 3) for k, v in nu["family_min_quantiles"].items()}), nu["family_min_q05"], json.dumps({k: round(v, 3) for k, v in nu["kept_share_mean"].items()})))
w("\n## T7 模型内部(FULL; Ridge 标准化系数 / LGBM gain 占比, 逐测试年)\n")
feats = ["DOI1H", "DOI24H", "LSDIV", "TKR24", "R3D", "DD7", "AGE", "FZ", "RN8", "DRN8"]
for s in SEEDS:
    for T in ("A", "B"):
        rows = []
        for y in YEARS:
            kR = "%s|%s|FULL|R|%s" % (s, T, y); kL = "%s|%s|FULL|L|%s" % (s, T, y)
            bR = R["fit"]["fits"][kR]["beta"]; gL = R["fit"]["fits"][kL]["gain"]; tg = sum(gL) or 1.0
            rows.append("%s R[%s] L[%s]" % (y, " ".join("%s %+.2f" % (feats[q], bR[q]) for q in range(10)), " ".join("%s %.2f" % (feats[q], gL[q] / tg) for q in range(10))))
        w("- s%s %s: %s" % (s, T, " | ".join(rows)))
open(os.path.join(L2, "receipts", "TABLES_L2.md"), "w").write("\n".join(out) + "\n")
print("SUMMARY l2_b_tables OK lines=%d verdict=%s" % (len(out), J["verdict"]))
