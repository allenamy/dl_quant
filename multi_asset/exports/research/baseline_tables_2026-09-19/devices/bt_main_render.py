#!/usr/bin/env python3
"""bt_main_render.py — renders bt_tables.py main_a0 output (+ bt_run_summary output) into the markdown tables of the A0 result doc. Pure formatting.
usage: python3 bt_main_render.py <BT_MAIN_A0.json> <BT_RUN_SUMMARY_A0.json> <out.md>
"""
import json, sys

M = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); OUT = sys.argv[3]; T = M["tables"]


def pc(x, d=1): return "—" if x is None else f"{100 * x:+.{d}f}%"
def pp(x, d=2): return "—" if x is None else f"{100 * x:+.{d}f} pp"
def f2(x, d=2): return "—" if x is None else f"{x:+.{d}f}"
def md_cell(s): return s.replace("|", "\\|")          # a run tag contains | and would otherwise split the markdown row
def dist(q, fn=pc): return "—" if not q or q.get("median") is None else f"{fn(q['median'])} [{fn(q['p05'])}, {fn(q['p95'])}]"


L = [f"对象: {M['object']} · {M['part']} · 窗口 {M['window'][0]} → {M['window'][1]} · 完整配方窗起点 {M['full_recipe_start']} · 覆盖: {M.get('coverage')}", ""]
for label in ("scaled (main)", "lit (reported)"):
    tb = T[f"per_period {label}"]
    L.append(f"\n**§3.1 / §3.3 逐时段 · 读数 {label} · 均值路径(32 条成交路径逐窗均值收益复利)+ 逐路径分布 中位 [5%, 95%]**\n")
    L.append("| 时段 | 锚 / 日 | 2× NAV 收益 | CAGR | 日夏普 | 最大回撤 4h | 最大回撤 5m | 最差 30 天 | CVaR 5% | g bps (价格 / 资金费付出 / 手续费 / UNKNOWN) | 换手/gross | 日止损 / 停机 / 持有 | 碎仓 bps | CAGR 路径分布 | 5m 回撤路径分布 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for nm, v in tb.items():
        m = v["mean_path"]; d = v["path_distribution"]; lab = nm + (" · 只描述" if v.get("describe_only") else "")
        dust = "—" if m["dust_over_gross_mean"] is None else f"{1e4 * m['dust_over_gross_mean']:.2f}"
        L.append(f"| {lab} | {m['n_anchors']:,} / {m['n_days']:,} | {pc(m['nav_return'])} | {pc(m['cagr'])} | {f2(m['sharpe_daily'])} | {pc(m['maxdd_4h'])} | {pc(m['maxdd_5m'])} | "
                 f"{pc(m['worst_30d'])} | {pc(m['cvar5_daily'], 2)} | {f2(m['g'])} ({f2(m['price'])} / {f2(m['funding_paid'])} / {f2(m['fee'])} / {f2(m['unknown_excluded'])}) | "
                 f"{m['turnover_over_gross']:.4f} | {m['day_stop_flattens']:.2f} / {m['halt_anchors']:.2f} / {m['hold_anchors']:.0f} | {dust} | "
                 f"{dist(d['cagr'])} | {dist(d['maxdd_5m'])} |")
for var in ("EXCL", "INCL"):
    key = f"regime_21_cells {var} (FULL_RECIPE window, main reading)"; R = T[key]
    L.append(f"\n**§3.2 21 格 · 标签 {var}{'(主读数)' if var == 'EXCL' else '(敏感性)'} · 完整配方窗 · 主读数 · g 的 CI95 = 5 日移动块(1 / 10 日块敏感性), B = 10,000, rng [20260919, 1000 + 格序号]; † = CI95 不含 0, †† = Bonferroni K = 21 不含 0**\n")
    L.append("| 格 | 序号 | 锚 / 日 | g bps [CI95 5 日] | 标记 | CI95 1 日 / 10 日 | CAGR | 日夏普 | 最大回撤 4h / 5m | 价格 / 资金费付出 / 手续费 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for v, lv in R.items():
        for l, c in lv.items():
            if c.get("n_anchors", 0) == 0:
                L.append(f"| {v} {l} | {c.get('cell_index', '')} | 0 | — | | | | | | |"); continue
            if "g_ci" not in c:
                L.append(f"| {v} {l} | {c['cell_index']} | {c['n_anchors']:,} / {c['n_days']} | {f2(c['g'])} | 只描述(单日) | | {pc(c['cagr'])} | {f2(c['sharpe_daily'])} | | |"); continue
            g5 = c["g_ci"]["block_5d"]; g1 = c["g_ci"]["block_1d"]; g10 = c["g_ci"]["block_10d"]
            L.append(f"| {v} {l} | {c['cell_index']} | {c['n_anchors']:,} / {c['n_days']} | {f2(c['g'])} [{f2(g5['ci95'][0])}, {f2(g5['ci95'][1])}] | {c.get('mark', '')} | "
                     f"[{f2(g1['ci95'][0])}, {f2(g1['ci95'][1])}] / [{f2(g10['ci95'][0])}, {f2(g10['ci95'][1])}] | {pc(c['cagr'])} | {f2(c['sharpe_daily'])} | {pc(c['maxdd_4h'])} / {pc(c['maxdd_5m'])} | "
                     f"{f2(c['price'])} / {f2(c['funding_paid'])} / {f2(c['fee'])} |")
CC = T["cost_sensitivity (main reading, Δ = cell − base, same fill seeds)"]
L.append("\n**§3.4 成本敏感性(主读数; Δ = 成本格 − 基准, 同成交种子; 定义见 AMENDMENT 1 第 1、2 条)**\n")
cells = list(CC); per = list(next(iter(CC.values())))
L.append("| 时段 | " + " | ".join(f"{c}: ΔCAGR / Δ日夏普 / Δg bps" for c in cells) + " |")
L.append("|---|" + "---|" * len(cells))
for nm in per:
    L.append(f"| {nm} | " + " | ".join(f"{pp(CC[c][nm]['d_cagr'])} / {f2(CC[c][nm]['d_sharpe'], 3)} / {f2(CC[c][nm]['d_g'], 3)}" for c in cells) + " |")
L.append("\n完整配方窗上逐成交路径 ΔCAGR 5% / 50% / 95%: " + "; ".join(f"{c} {pp(CC[c]['FULL_RECIPE window']['per_fill_path_d_cagr']['p05'])} / {pp(CC[c]['FULL_RECIPE window']['per_fill_path_d_cagr']['median'])} / {pp(CC[c]['FULL_RECIPE window']['per_fill_path_d_cagr']['p95'])}" for c in cells if "FULL_RECIPE window" in CC[c]))
RK = next(k for k in T if k.startswith("reconciliation")); RC = T[RK]
L.append(f"\n**§3.6 新旧对账第 ③ 步 · {RK} · 顺序 ①→②→③, 交互项归入后一步**\n")
L.append("| 步 | ΔCAGR [CI95] (p↑ / p↓) | Δ日夏普 [CI95] | Δg bps [CI95] | Δ最大回撤 4h / 5m(点) | 逐成交路径 Δ 5 / 50 / 95%: CAGR · 回撤 4h |")
L.append("|---|---|---|---|---|---|")
for lab, st in RC["steps_3"].items():
    b = st["paired_bootstrap"]["main_5d"]; dpt = st["delta_point"]; pf = st.get("per_fill_path_delta", {})
    q = lambda k: "—" if not pf.get(k) or pf[k].get("median") is None else f"{100 * pf[k]['p05']:+.1f} / {100 * pf[k]['median']:+.1f} / {100 * pf[k]['p95']:+.1f}"
    L.append(f"| {lab} | {pp(b['d_cagr']['estimate'])} [{100 * b['d_cagr']['ci95'][0]:+.2f}, {100 * b['d_cagr']['ci95'][1]:+.2f}] ({b['d_cagr']['p_up']:.3f} / {b['d_cagr']['p_down']:.3f}) | "
             f"{f2(b['d_sharpe']['estimate'])} [{f2(b['d_sharpe']['ci95'][0])}, {f2(b['d_sharpe']['ci95'][1])}] | {f2(b['d_g']['estimate'])} [{f2(b['d_g']['ci95'][0])}, {f2(b['d_g']['ci95'][1])}] | "
             f"{pp(dpt['maxdd_4h'])} / {pp(dpt['maxdd_5m'])} | {q('cagr')} · {q('maxdd_4h')} ({pf.get('pairing', '')}) |")
ch = RC["chain_1_2_3"]
L.append("\n| 链(s42) | CAGR | 日夏普 | 最大回撤 4h | g bps |")
L.append("|---|---|---|---|---|")
for nm, key in (("流 R 已发表: v2 × 旧价 × P2-CMB", "v2_published"), ("① 后: v3.1 × 旧价 × P2-CMB", "after_1"), ("② 后: v3.1 × 恢复价 × P2-CMB", "after_2"), ("③ 后: v3.1 × 恢复价 × 认证对象 B A0", "after_3")):
    x = ch[key]; L.append(f"| {nm} | {pc(x['cagr'])} | {f2(x['sharpe_daily'])} | {pc(x['maxdd_4h'])} | {f2(x['g'])} |")
L.append(f"\n伸缩核对 |① + ② + ③ − 总差|: " + ", ".join(f"{k} {v:.1e}" for k, v in ch["telescoping_abs_err"].items()) + "; ② 后 = ③ 前: " + ", ".join(f"{k} {v:.1e}" for k, v in ch["step2_after_equals_step3_before"].items()) + f"。{RC['note']}")
L.append("\n**UNAVAILABLE 规则(AMENDMENT 1 第 5 条)每个运行的触发数与名义(32 条路径; 每路径范围 或 合计)**\n")
L.append("| 运行 | 冻结锚(每路径) | 冻结名-锚(每路径) | 冻结持仓名义 USDT(每路径中位) | 丢弃计划名义 USDT(每路径中位) | 缺口内取消成交(合计)/ 名义 USDT | 持有 UNKNOWN 名的窗(每路径) | UNKNOWN 名义 USDT(每路径中位) | UNKNOWN 价格 / 资金费 USDT(每路径中位) |")
L.append("|---|---|---|---|---|---|---|---|---|")
for tag, o in S["runs"].items():
    u = o["unknown_cells_per_path"]; c = o["ua_counters_sum_over_paths"]
    g = lambda k, f="median": u.get(k, {}).get(f, 0.0)
    L.append(f"| {md_cell(tag)} | {g('frozen_anchors', 'min'):.0f}–{g('frozen_anchors', 'max'):.0f} | {g('frozen_name_anchors', 'min'):.0f}–{g('frozen_name_anchors', 'max'):.0f} | {g('frozen_held_notional_usdt_sum'):,.0f} | "
             f"{g('frozen_plan_notional_dropped_usdt_sum'):,.0f} | {c.get('fills_cancelled_ua_bar', 0):.0f} / {c.get('fill_notional_cancelled_ua_bar', 0):,.0f} | "
             f"{g('windows_with_held_unknown_names', 'min'):.0f}–{g('windows_with_held_unknown_names', 'max'):.0f} | {g('notional_at_risk_usdt_sum'):,.0f} | {g('unknown_price_pnl_usdt'):+,.2f} / {g('unknown_funding_usdt'):+,.2f} |")
L.append(f"\n计算: 启动墙钟 {S['launch_wall_s']:,.0f} s; 路径单线程合计 {S['core_seconds_paths']:,.0f} s = {S['core_hours_paths']:.2f} 核时。")
open(OUT, "w").write("\n".join(L) + "\n"); print("rendered", OUT)
