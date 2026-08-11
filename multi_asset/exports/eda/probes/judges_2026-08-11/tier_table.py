import json
P = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/fee_fill_sensitivity.json"
d = json.load(open(P))
SLOPE = d["anchors"]["pct_per_bps_of_cost"]
TURN = d["anchors"]["ann_turnover_unit_gross"]
BE = d["anchors"]["break_even_eff_cost_bps_with_funding"]
print("斜率 %.3f pp/yr per bps | 年化换手 %.1f unit-gross | 盈亏平衡有效成本 %.2f bps" % (SLOPE, TURN, BE))
print()
tiers = [("VIP0 无 BNB 抵扣", 2.0, 5.0), ("VIP0 + BNB 抵扣(-10%)", 1.8, 4.5),
         ("VIP1", 1.6, 4.0), ("maker 返佣档 (maker=0)", 0.0, 4.5)]
phis = (0.51, 0.70, 1.00)
print("=== A. 只含手续费的那一半 —— 完全可算, 是 c 的下界 (bps) ===")
print("%-24s %9s %9s %9s" % ("档位", "phi=0.51", "phi=0.70", "phi=1.00"))
rows = {}
for name, mk, tk in tiers:
    rows[name] = [phi * mk + (1 - phi) * tk for phi in phis]
    print("%-24s %9.3f %9.3f %9.3f" % (name, *rows[name]))
ref = rows["VIP0 无 BNB 抵扣"][0]
print()
print("=== B. 相对基准(VIP0 无抵扣 / phi=0.51) 的年化收益改善 (pp/yr = dbps x 斜率) ===")
print("%-24s %9s %9s %9s" % ("档位", "phi=0.51", "phi=0.70", "phi=1.00"))
for name, _, _ in tiers:
    print("%-24s %+9.1f %+9.1f %+9.1f" % (name, *[(ref - x) * SLOPE for x in rows[name]]))
print()
print("=== C. 网格里的完整单元 (含微观结构那一半 —— 校准值, 非证明值) ===")
for k in sorted(d["grid"]):
    if k.startswith("topup|") and "adv=normal" in k and ("maker=1.8" in k or "maker=0.0" in k) \
       and any(f in k for f in ("fill=0.51", "fill=0.7", "fill=1.0")):
        c = d["grid"][k]
        wf = c.get("with_funding") or c.get("price_only")
        print("  %-56s eff %5.3f bps -> %6.1f%%/yr  Sharpe %5.2f"
              % (k, c["eff_cost_bps"], 100 * wf["ann_return"], wf["sharpe"]))
