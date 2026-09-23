#!/usr/bin/env python3
"""ens_render.py — render receipts/ENS_STATS.json into the markdown tables of docs/RESULT_f10_seed_ensemble_book_2026-09-23.md (no computation of
new statistics; every number is read from the stats receipt). usage: python3 ens_render.py <ENS_STATS.json> <out.md>"""
import sys, json, hashlib

P, OUT = sys.argv[1:3]
R = json.load(open(P)); h = hashlib.sha256(open(P, "rb").read()).hexdigest()
ARMS = [("NEW_ENS", "ENS"), ("NEW_s42", "s42"), ("NEW_s2027", "s2027")]
SEGS = ["2023H2", "2024", "2025", "pre2026", "2026"]
L = [f"<!-- rendered by ens_render.py from ENS_STATS.json sha256 {h} -->", ""]
V = R["criteria"]
L.append("### E1–E4(判据, pre-2026)\n")
L.append("| # | 实测 | 门 | 判 |\n|---|---|---|---|")
for k, lab in (("NEW_s42", "s42"), ("NEW_s2027", "s2027")):
    e = V["E1"]["per_single_seed"][k]; ci = e["boot_30d"]["ci97.5_two_sided_bps"]
    L.append(f"| E1 vs {lab} | d̄ = {e['estimate_bps_per_day']:+.3f} bps/日, 97.5% 区间(30 日块) [{ci[0]:+.3f}, {ci[1]:+.3f}], n = {e['n_days']} 日 × {e['n_paths']} 路径 | 下界 > −0.5 | {'PASS' if e['PASS'] else 'FAIL'} |")
for s in ("2023H2", "2024", "2025"):
    e = V["E2"]["segments"][s]
    L.append(f"| E2 {s} | Sharpe ENS {e['ENS']:.3f}(s42 {e['s42']:.3f} / s2027 {e['s2027']:.3f}) | ≥ {e['floor']:.3f} | {'PASS' if e['PASS'] else 'FAIL'} |")
e = V["E3"]; t = e["turnover_over_gross_pre2026"]
L.append(f"| E3 | 换手/gross ENS {t['NEW_ENS']:.5f}(s42 {t['NEW_s42']:.5f} / s2027 {t['NEW_s2027']:.5f}) | ≤ {e['limit_1.05x_mean_single']:.5f} | {'PASS' if e['PASS'] else 'FAIL'} |")
e = V["E4"]; d = e["maxdd_5m_pre2026_path_mean"]
L.append(f"| E4 | 5m 最大回撤 ENS {100*d['NEW_ENS']:.2f}%(s42 {100*d['NEW_s42']:.2f}% / s2027 {100*d['NEW_s2027']:.2f}%) | ≥ {100*e['floor']:.2f}% | {'PASS' if e['PASS'] else 'FAIL'} |")
L.append(f"\n**判词: {R['VERDICT']}**\n")
L.append("E1 旁报(非判据):\n")
L.append("| 对照 | 95% 区间(30 日块) | 97.5% 区间(5 日块) | 含 2023-06-30 半日 | 逐段 d̄ bps/日 2023H2 / 2024 / 2025 / 2026 |\n|---|---|---|---|---|")
for k, lab in (("NEW_s42", "s42"), ("NEW_s2027", "s2027")):
    e = V["E1"]["per_single_seed"][k]; c95 = e["boot_30d"]["ci95_bps"]; c5 = e["boot_5d_sensitivity"]["ci97.5_two_sided_bps"]; sp = e["sensitivity_partial_first_day_included"]
    sm = " / ".join(f"{e['segment_means'][s]['mean_bps_per_day']:+.3f}" for s in ("2023H2", "2024", "2025", "2026"))
    L.append(f"| ENS − {lab} | [{c95[0]:+.3f}, {c95[1]:+.3f}] | [{c5[0]:+.3f}, {c5[1]:+.3f}] | {sp['estimate_bps_per_day']:+.3f} [{sp['boot_30d']['ci97.5_two_sided_bps'][0]:+.3f}, {sp['boot_30d']['ci97.5_two_sided_bps'][1]:+.3f}],改判 E1: {sp['changes_E1']} | {sm} |")
L.append("\n### §4.1 逐段三方对照(32 路径均值;[2.5%, 97.5%] 路径分位)\n")
L.append("| 段 | 臂 | Sharpe | 总收益 | CAGR | 5m 最大回撤 | 最差日 | 价格+成交 | 资金费(付) | 手续费 | 未知剔除 | g | 换手/gross | §4-2 平仓 | 逐名止损 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for s in SEGS:
    for arm, lab in ARMS:
        p = R["tables"][arm][s]["paths"]
        f = lambda k, m=1.0, fmt="{:.3f}": fmt.format(m * p[k]["path_mean"])
        sh = p["sharpe"]
        L.append(f"| {s} | {lab} | {sh['path_mean']:.3f} [{sh['p2.5']:.2f}, {sh['p97.5']:.2f}] | {100*p['total_return']['path_mean']:+.2f}% | {100*p['cagr']['path_mean']:+.2f}% | "
                 f"{100*p['maxdd_5m']['path_mean']:.2f}% [{100*p['maxdd_5m']['p2.5']:.1f}, {100*p['maxdd_5m']['p97.5']:.1f}] | {100*p['worst_day']['path_mean']:.2f}% | "
                 f"{p['price']['path_mean']:+.3f} | {p['funding_paid']['path_mean']:+.3f} | {p['fee']['path_mean']:.3f} | {p['unknown_excluded']['path_mean']:.3f} | {p['g']['path_mean']:+.3f} | "
                 f"{p['turnover_over_gross']['path_mean']:.4f} | {p['day_stop_flattens']['path_mean']:.1f} | {p['per_name_stops']['path_mean']:.1f} |")
L.append("\n(价格+成交 / 资金费 / 手续费 / 未知剔除 / g 单位: bps 每锚每单位目标 gross;g = 价格 − 资金费 − 手续费 − 未知,逐窗断言 ≤ 1e-9)\n")
L.append("### §4.2 分数层平均(ENS)vs 资金层平均(50/50 分仓,逐 UTC 日再平衡)\n")
L.append("| 段 | 臂 | Sharpe(完整日) | 完整日总收益 | 最差日 | 日频 NAV 最大回撤 | d̄(ENS − 50/50) bps/日 |\n|---|---|---|---|---|---|---|")
for s in SEGS:
    m = R["report_capital_50_50"][s]
    for key, lab in (("ENS_same_quantities", "ENS"), ("MIX_50_50", "50/50")):
        q = m[key]
        extra = f"{m['dbar_ENS_minus_MIX_bps_per_day']:+.3f}" if lab == "ENS" else ""
        if lab == "ENS" and s == "pre2026":
            b = m["dbar_ENS_minus_MIX_boot_30d"]; extra += f",97.5% [{b['ci97.5_two_sided_bps'][0]:+.3f}, {b['ci97.5_two_sided_bps'][1]:+.3f}],95% [{b['ci95_bps'][0]:+.3f}, {b['ci95_bps'][1]:+.3f}]"
        L.append(f"| {s} | {lab} | {q['sharpe']['path_mean']:.3f} | {100*q['total_return_full_days']['path_mean']:+.2f}% | {100*q['worst_day']['path_mean']:.2f}% | {100*q['maxdd_daily']['path_mean']:.2f}% | {extra} |")
L.append("\n### §4.3 目标距离(scaled_diagnostic 组合目标;L1 = Σ|w_X − w_Y|)\n")
L.append("| 对 | 年/段 | raw L1 逐锚均值 | 两者平均 gross | L1/gross | n_eff 锚 | 同时发布锚上权重 L1 | n_eff |\n|---|---|---|---|---|---|---|---|")
for pair, rows in R["report_target_distance"].items():
    for lab, r in rows.items():
        g = lambda k, fmt: (fmt.format(r[k]) if r[k] is not None else "n/a")
        L.append(f"| {pair.replace('NEW_', '')} | {lab} | {g('raw_L1_mean', '{:.4f}')} | {g('raw_mean_gross', '{:.4f}')} | {g('raw_L1_over_gross', '{:.3f}')} | {r['n_eff_raw']} | {g('published_both_L1_mean', '{:.4f}')} | {r['n_eff_published_both']} |")
L.append("\n### §4.4 发布资格(scaled_diagnostic trade_mask)\n")
L.append("| 段 | 锚 | 发布 ENS | 发布 s42 | 发布 s2027 | ENS≠s42 | ENS≠s2027 | s42≠s2027 | ENS 未发布原因 |\n|---|---|---|---|---|---|---|---|---|")
for s, r in R["report_publication"].items():
    rs = ", ".join(f"{k} {v}" for k, v in sorted(r["ENS_reasons"].items()) if k != "publish") or "—"
    L.append(f"| {s} | {r['anchors']} | {r['published_NEW_ENS']} | {r['published_NEW_s42']} | {r['published_NEW_s2027']} | {r['differ_ENS_vs_s42']} | {r['differ_ENS_vs_s2027']} | {r['differ_s42_vs_s2027']} | {rs} |")
o = R["report_one_seed_only_names"]
L.append(f"\n仅一个种子有限的名字: 全文件轴 {o['n_eff_anchors']} 锚合计 **{o['total']}** 名,出现于 {o['anchors_with_any']} 锚。\n")
open(OUT, "w").write("\n".join(L) + "\n")
print("rendered", OUT)
