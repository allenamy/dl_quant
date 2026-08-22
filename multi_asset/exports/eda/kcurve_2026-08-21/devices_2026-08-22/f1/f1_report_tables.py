"""F-1 结果 JSON → markdown 表(文档回填用; 只读 JSON, 不算新量). 用法: python f1_report_tables.py <result.json>"""
import json, sys
R = json.load(open(sys.argv[1]))
def f(x, n=3):
    try: return f"{float(x):.{n}f}"
    except Exception: return str(x)
print("## R0/R1/R2 收据")
print("R0", json.dumps(R["fea_report"]["R0"], ensure_ascii=False)[:1500])
print("R1", json.dumps(R["receipt_R1"], ensure_ascii=False))
print("R2", json.dumps(R["train"]["receipt_R2"], ensure_ascii=False))
print("cache", json.dumps(R["cache_report"], ensure_ascii=False)[:800])
print("\n## A/B · king IC(逐锚 Spearman 年均; 两口径)")
yrs = ["2022", "2023", "2024", "2025", "2026"]
print("| 臂 | 口径 | " + " | ".join(yrs) + " | 合并 22-26 |"); print("|---|---|" + "---|" * (len(yrs) + 1))
k0 = R["train"]["K0_reference"]
print("| K0(pod 参考) | y4 | " + " | ".join(f(k0["ic_y4_by_year"].get(y, k0["ic_y4_by_year"].get(int(y))), 4) for y in yrs) + " | — |")
print("| K0(pod 参考) | 1h 简单 | " + " | ".join(f(k0["ic_ret1h_by_year"].get(y, k0["ic_ret1h_by_year"].get(int(y))), 4) for y in yrs) + " | — |")
print("| pod json | y4 | " + " | ".join(f(k0["pod_slow_hist_folds_json"]["ic_by_year"].get(y, "—"), 4) for y in yrs) + " | — |")
for arm in ("K1", "K2"):
    a = R["train"]["arms"][arm]
    print(f"| {arm} | y4 | " + " | ".join(f(a["ic_y4_by_year"].get(y, "—"), 4) for y in yrs) + f" | {f(a['ic_y4_pooled_2022_26'], 4)} |")
    print(f"| {arm} | 1h 简单 | " + " | ".join(f(a["ic_ret1h_by_year"].get(y, "—"), 4) for y in yrs) + f" | {f(a['ic_ret1h_pooled_2022_26'], 4)} |")
print("\n臂间逐锚 Spearman:", json.dumps(R["train"]["cross_arm_spearman"]))
print("king vs 腿 Spearman:", json.dumps(R["king_vs_leg_spearman"]))
print("K3 funding R2:", R.get("K3_funding_R2_mean"), R.get("K3_funding_R2_by_year"))
print("\n## A · 特征族重要性(SHAP 份额 / 置换 ΔIC)")
fams = ["FUND", "RET", "VOL", "RANGE", "CPOS", "LIQ", "TBF"]
print("| 臂 | 量 | " + " | ".join(fams) + " |"); print("|---|---|" + "---|" * len(fams))
for arm in ("K1", "K2"):
    a = R["train"]["arms"][arm]
    print(f"| {arm} | SHAP 份额(合并) | " + " | ".join(f(a["shap_family_share_pooled"].get(x, 0), 3) for x in fams) + " |")
    print(f"| {arm} | 置换 ΔIC(行加权) | " + " | ".join(f(a["perm_dIC_pooled_rowweighted"].get(x, float("nan")), 4) for x in fams) + " |")
    for y, d in a["perm_dIC_by_fold"].items():
        print(f"| {arm} | 置换 ΔIC {y} | " + " | ".join(f(d.get(x, float("nan")), 4) for x in fams) + " |")
print("\n## B/C · 书级(净@2, 2022-01..2026-06 主跨度; 夏普 锚级 [CI]; 逐年; 均值 bps/锚; maxDD; 2024-26 夏普)")
print("| 臂 | 夏普 [CI95] | 逐年 22/23/24/25/26 | 净@2 均 | maxDD | 22-23 / 24-26 | FULL 夏普 | gross/换手 |"); print("|---|---|---|---|---|---|---|---|")
for name in sorted(R["summary"]):
    s = R["summary"][name]; m = s["2022-01..2026-06"]["net_at_gross2"]; fu = s["FULL(2022-01..2026-08-10)"]["net_at_gross2"]
    by = m["by_year_sharpe"]; byv = [by.get(str(y), by.get(y)) for y in range(2022, 2027)]
    print(f"| {name} | {f(m['sharpe_anchor'])} {m['sharpe_CI95_blk42']} | " + " / ".join(f(v, 2) for v in byv) + f" | {f(m['mean_bps'])} | {f(m['maxDD'], 3)} | {f(m['sharpe_2022_23'], 2)} / {f(m['sharpe_2024_26'], 2)} | {f(fu['sharpe_anchor'])} | {f(s['2022-01..2026-06']['gross_mean'], 3)}/{f(s['2022-01..2026-06']['turnover_mean'], 4)} |")
print("\n## Δ(配对块自助, 主跨度)")
print("| 对 | Δ均 | CI95 | P>0 | 2024-26 Δ | 逐年 Δ | Sx / Sy |"); print("|---|---|---|---|---|---|---|")
for k, d in R["deltas"].items():
    mm = d["main_2022-01..2026-06"]
    print(f"| {k} | {f(mm['mean'])} | {mm['CI95']} | {mm['P_gt_0']} | {f(d['2024-26']['mean'])} {d['2024-26']['CI95']} | {d['by_year_delta_sharpe']} | {f(d['sharpe_x_main'])} / {f(d['sharpe_y_main'])} |")
print("\n## C · 配权归因")
print(json.dumps(R["C_allocation"], ensure_ascii=False, indent=0)[:6000])
print("C_verdict", json.dumps(R.get("C_verdict"), ensure_ascii=False))
print("\n## 阶段判据 / 缺口分解")
print(json.dumps(R["stage_criterion"], ensure_ascii=False)); print(json.dumps(R.get("stage_criterion_K3_secondary"), ensure_ascii=False)); print(json.dumps(R["gap_decomposition"], ensure_ascii=False))
print("\n## 腿级读数(主跨度, WA 可加分解)")
for name in ("K0_base_d30", "K2_base_d30", "K0_equal_d30", "K0_no_fund_d30", "K2_no_fund_d30"):
    if name in R["summary"]:
        lg = R["summary"][name]["2022-01..2026-06"].get("legs", {})
        print(name, {k: {kk: v[kk] for kk in ("gross_share", "net_g2", "net_sharpe", "by_year_net_g2")} for k, v in lg.items()})
print("\n## Q4(市场五分位 净@2)")
for name in ("K0_base_d30", "K0_no_fund_d30", "K2_no_fund_d30", "K2_base_d30", "K3_no_fund_d30"):
    if name in R["summary"]: print(name, R["summary"][name]["2022-01..2026-06"].get("Q4"))
