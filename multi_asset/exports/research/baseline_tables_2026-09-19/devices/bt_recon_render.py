#!/usr/bin/env python3
"""bt_recon_render.py — renders the reconciliation receipt (bt_tables.py recon → BT_RECON_steps12_P2CMB.json) and the run summary
(bt_run_summary.py) into markdown tables for the result doc, so that no number is copied by hand. Pure formatting; no statistic is computed here.
usage: python3 bt_recon_render.py <BT_RECON.json> <BT_RUN_SUMMARY.json> <out.md>
"""
import json, sys

R = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); OUT = sys.argv[3]


def pc(x, d=1):
    return "—" if x is None else f"{100 * x:+.{d}f}%"


def pp(x, d=1):
    return "—" if x is None else f"{100 * x:+.{d}f} pp"


def f2(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def ci(c, scale=1.0, unit=""):
    return f"[{c[0] * scale:+.2f}, {c[1] * scale:+.2f}]{unit}"


L = []
for seed in ("s42", "s2027"):
    st = R["steps"][seed]; v = st["v2_full"]
    import time as _t
    span = _t.strftime("%Y-%m-%dT%HZ", _t.gmtime(v["first_anchor"])) + " → " + _t.strftime("%Y-%m-%dT%HZ", _t.gmtime(v["last_anchor"]))
    L.append(f"\n**S2_A0pred {seed} · 对象 P2-CMB(不是认证对象 B)· 锚 {span}({v['n_anchors']:,} 个 4h 窗, {v['n_days']:,} 个 UTC 日)· v3.1 列 = 32 条成交路径的均值路径**\n")
    L.append("| 读数 | v2 × 旧价(流 R 已发表) | v3.1 × 旧价 | v3.1 × 恢复价 |")
    L.append("|---|---|---|---|")
    a, b, c = st["v2_full"], st["v31_old_mean_full"], st["v31_raw_mean_full"]
    L.append(f"| 2× NAV 总收益 | {pc(a['nav_return'])} | {pc(b['nav_return'])} | {pc(c['nav_return'])} |")
    L.append(f"| CAGR | {pc(a['cagr'])} | {pc(b['cagr'])} | {pc(c['cagr'])} |")
    L.append(f"| 日夏普(√365) | {f2(a['sharpe_daily'])} | {f2(b['sharpe_daily'])} | {f2(c['sharpe_daily'])} |")
    L.append(f"| 最大回撤(4h 采样) | {pc(a['maxdd_4h'])} | {pc(b['maxdd_4h'])} | {pc(c['maxdd_4h'])} |")
    L.append(f"| 最大回撤(5 分钟采样) | 无(v2 无 5 分钟路径) | {pc(b['maxdd_5m'])} | {pc(c['maxdd_5m'])} |")
    L.append(f"| g bps/锚/gross (价格 / 资金费付出 / 手续费 / UNKNOWN 剔除) | {f2(a['g'])} ({f2(a['price'])} / {f2(a['funding_paid'])} / {f2(a['fee'])} / {f2(a['unknown_excluded'])}) | "
             f"{f2(b['g'])} ({f2(b['price'])} / {f2(b['funding_paid'])} / {f2(b['fee'])} / {f2(b['unknown_excluded'])}) | {f2(c['g'])} ({f2(c['price'])} / {f2(c['funding_paid'])} / {f2(c['fee'])} / {f2(c['unknown_excluded'])}) |")
    L.append(f"| 换手 / gross (每窗) | {a['turnover_over_gross']:.4f} | {b['turnover_over_gross']:.4f} | {c['turnover_over_gross']:.4f} |")
    L.append(f"| 日止损平仓(路径均值) / 停机锚 / 持有锚 | {a['day_stop_flattens']:.0f} / {a['halt_anchors']:.0f} / {a['hold_anchors']:.0f} | {b['day_stop_flattens']:.2f} / {b['halt_anchors']:.2f} / {b['hold_anchors']:.0f} | "
             f"{c['day_stop_flattens']:.2f} / {c['halt_anchors']:.2f} / {c['hold_anchors']:.0f} |")
    L.append(f"| 最差 30 天 / 日收益 CVaR 5% | {pc(a['worst_30d'])} / {pc(a['cvar5_daily'], 2)} | {pc(b['worst_30d'])} / {pc(b['cvar5_daily'], 2)} | {pc(c['worst_30d'])} / {pc(c['cvar5_daily'], 2)} |")
    L.append("")
    L.append("| 步 | ΔCAGR [CI95] (p↑ / p↓) | Δ日夏普 [CI95] (p↑ / p↓) | Δg bps [CI95] | Δ最大回撤 4h / 5m(点) | 逐成交路径 Δ 5 / 50 / 95%: CAGR · 夏普 · 回撤 4h |")
    L.append("|---|---|---|---|---|---|")
    for k in ("step1", "step2"):
        s_ = st[k]; b5 = s_["paired_bootstrap"]["main_5d"]; dp = s_["delta_point"]; pf = s_.get("per_fill_path_delta", {})
        def trip(key, scale=100.0, unit="pp"):
            q = pf.get(key) or {}
            if not q or q.get("median") is None: return "—"
            return f"{q['p05'] * scale:+.1f} / {q['median'] * scale:+.1f} / {q['p95'] * scale:+.1f}" if scale != 1 else f"{q['p05']:+.2f} / {q['median']:+.2f} / {q['p95']:+.2f}"
        L.append(f"| {s_['step']} | {pp(b5['d_cagr']['estimate'])} {ci(b5['d_cagr']['ci95'], 100, ' pp')} ({b5['d_cagr']['p_up']:.3f} / {b5['d_cagr']['p_down']:.3f}) | "
                 f"{f2(b5['d_sharpe']['estimate'])} {ci(b5['d_sharpe']['ci95'])} ({b5['d_sharpe']['p_up']:.3f} / {b5['d_sharpe']['p_down']:.3f}) | "
                 f"{f2(b5['d_g']['estimate'])} {ci(b5['d_g']['ci95'])} | {pp(dp['maxdd_4h'])} / {pp(dp['maxdd_5m'])} | "
                 f"{trip('cagr')} · {trip('sharpe_daily', 1)} · {trip('maxdd_4h')} ({pf.get('pairing', '')}) |")
    L.append("")
    L.append("敏感性(同一估计量, 1 日块 / 10 日块): " + "; ".join(
        f"{k}: ΔCAGR CI {ci(st[k]['paired_bootstrap']['sens_1d']['d_cagr']['ci95'], 100, ' pp')} / {ci(st[k]['paired_bootstrap']['sens_10d']['d_cagr']['ci95'], 100, ' pp')}, "
        f"Δ夏普 CI {ci(st[k]['paired_bootstrap']['sens_1d']['d_sharpe']['ci95'])} / {ci(st[k]['paired_bootstrap']['sens_10d']['d_sharpe']['ci95'])}" for k in ("step1", "step2")))
    L.append(f"\n伸缩核对: 两步之和 = 总差(|误差| CAGR {st['telescoping_abs_err']['cagr']:.1e}, 夏普 {st['telescoping_abs_err']['sharpe_daily']:.1e}, 回撤 {st['telescoping_abs_err']['maxdd_4h']:.1e}, g {st['telescoping_abs_err']['g']:.1e}); "
             f"逐路径 g 恒等式最大误差 旧 {st['identity']['v31_old_paths_max_g_identity_err']:.1e} / 恢复 {st['identity']['v31_raw_paths_max_g_identity_err']:.1e}。")
    for nm, key in (("v3.1 × 旧价", "path_distribution_old"), ("v3.1 × 恢复价", "path_distribution_raw")):
        pdist = st[key]
        L.append(f"\n{nm} 32 条成交路径的分布(中位 [5%, 95%], 只作描述): CAGR {pc(pdist['cagr']['median'])} [{pc(pdist['cagr']['p05'])}, {pc(pdist['cagr']['p95'])}] · "
                 f"日夏普 {f2(pdist['sharpe_daily']['median'])} [{f2(pdist['sharpe_daily']['p05'])}, {f2(pdist['sharpe_daily']['p95'])}] · "
                 f"最大回撤 4h {pc(pdist['maxdd_4h']['median'])} [{pc(pdist['maxdd_4h']['p05'])}, {pc(pdist['maxdd_4h']['p95'])}] · "
                 f"5m {pc(pdist['maxdd_5m']['median'])} [{pc(pdist['maxdd_5m']['p05'])}, {pc(pdist['maxdd_5m']['p95'])}] · "
                 f"最差 30 天 {pc(pdist['worst_30d']['median'])} · CVaR5 {pc(pdist['cvar5_daily']['median'], 2)}")
L.append("\n**UNAVAILABLE 规则计数(32 条路径合计 / 每路径范围)**\n")
L.append("| 运行 | 规则 | 冻结锚(每路径) | 冻结计划丢弃 | 不可得 bar 内取消成交 | 持有 UNKNOWN 名的窗(每路径) | UNKNOWN 名义合计 USDT(每路径中位) | UNKNOWN 价格 / 资金费损益 USDT(每路径中位) | 是否移出主读数 |")
L.append("|---|---|---|---|---|---|---|---|---|")
for tag, o in S["runs"].items():
    u = o["unknown_cells_per_path"]; c = o["ua_counters_sum_over_paths"]
    L.append(f"| {tag} | {o['policy']} | {u['frozen_anchors']['min']:.0f}–{u['frozen_anchors']['max']:.0f} | {c.get('frozen_plans_dropped', 0):.0f} | {c.get('fills_cancelled_ua_bar', 0):.0f} | "
             f"{u['windows_with_held_unknown_names']['min']:.0f}–{u['windows_with_held_unknown_names']['max']:.0f} | {u['notional_at_risk_usdt_sum']['median']:,.0f} | "
             f"{u['unknown_price_pnl_usdt']['median']:+,.2f} / {u['unknown_funding_usdt']['median']:+,.2f} | {'是' if u['excluded_from_main']['max'] else '否(只报)'} |")
L.append(f"\n计算: 启动墙钟 {S['launch_wall_s']:,.0f} s; 路径单线程时间合计 {S['core_seconds_paths']:,.0f} s = {S['core_hours_paths']:.2f} 核时; 每条路径中位 " +
         ", ".join(f"{t.split('|')[0]} {t.split('|')[3]} {o['path_runtime_s']['median']:.0f} s" for t, o in S["runs"].items()) + "。")
open(OUT, "w").write("\n".join(L) + "\n")
print("rendered", OUT)
