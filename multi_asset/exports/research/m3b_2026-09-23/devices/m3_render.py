#!/usr/bin/env python3
"""m3_render.py (Mac) — renders M3 readout / feasibility receipts into the markdown tables of docs/RESULT_m3_beta_overlay_2026-09-23.md.
Every number is read from a receipt (sha printed in the header comment); nothing is recomputed here.
usage: /usr/bin/python3 m3_render.py <M3_FEASIBILITY.json> <M3_READOUT_OLD.json> <M3_READOUT_NEW_s42.json> > tables.md"""
import sys, json, hashlib


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def pct(x, d=1): return "—" if x is None else f"{100 * x:+.{d}f}%"


def f(x, d=3): return "—" if x is None else f"{x:+.{d}f}"


feas_p, *ro_ps = sys.argv[1:]
F = json.load(open(feas_p)) if feas_p != "-" else {"bases": {}}           # M3b: no feasibility receipt ⇒ "-"
if feas_p != "-":
    print(f"<!-- from {feas_p.split('/')[-1]} sha {sha(feas_p)[:16]} -->")
    print("### 可行性三行(先于任何 M3 NAV;提交 14891549c)\n")
    print("| 底座 | (a) 2026 窗日 β 标准误 NW / 经典(n 日) | 带半宽 0.10 ÷ SE(NW) | 底座已实现日 β | (b) 平书交付 D / 中位比(主窗) | (b) 辅助窗 D / 中位比 | (c) 事前执行书 β 平书 / 在路径 seed0 | 发布目标层 β |")
    print("|---|---|---|---|---|---|---|---|")
for b, o in F["bases"].items():
    a = o["a_resolution"]; bb = o["b_delivery_flat_book"]; ks = list(bb); m, x = bb[ks[0]]["R3"], bb[ks[1]]["R3"]; c = o["c_phenomenon"]
    print(f"| {b} | {a['se_newey_west_lag5']:.3f} / {a['se_classical']:.3f} ({a['n_days']}) | {a['band_half_width_over_se_nw']:.2f} | {f(a['base_realised_daily_beta'])} | "
          f"{m['D_delivered_share']:.3f} / {m['median_ratio(|intended|>0.01)']:.4f} ({'过' if m['pass'] else '不过'}) | {x['D_delivered_share']:.3f} / {x['median_ratio(|intended|>0.01)']:.4f} | "
          f"{f(c['flat_book_MAIN']['beta_exec']['mean'])} / {f(c['in_path_control_seed0_MAIN']['beta_exec']['mean'])} | {f(c['flat_book_MAIN']['beta_pre_published']['mean'])} |")
print()
for p in ro_ps:
    R = json.load(open(p)); C = R["criteria"]; T = R["table"]; W = list(T)
    print(f"<!-- from {p.split('/')[-1]} sha {sha(p)[:16]} · device m3_readout.py {R['self_sha256'][:12]} · UTC {R['utc']} -->")
    print(f"#### {R['label']} — VERDICT **{R['VERDICT']}**" + (f"(不过: {', '.join(R['failing'])})" if R["failing"] else "") + "\n")
    print("| 判据 | 实测 | 门 | 结果 |\n|---|---|---|---|")
    r1 = C["R1"]; print(f"| R1 主窗书+对冲已实现日 β | {f(r1['measured'])}(底座 {f(r1['base'])};SE NW {r1['se_nw_m3']:.3f};32 路径 [{r1['per_path_m3']['p2.5']:+.3f}, {r1['per_path_m3']['p97.5']:+.3f}]) | [−0.10, +0.10] | {'过' if r1['pass'] else '不过'} |")
    r2 = C["R2"]
    if r2.get("pass") is None:
        print(f"| R2 | {r2.get('undecided')} | — | 不可算 |")
    else:
        print(f"| R2 BTC 当日 > +2% 的 {r2['n_days']} 日, 书日均收益 | M3 {pct(r2['mean_m3'], 2)} vs 底座 {pct(r2['mean_base'], 2)}(差 {pct(r2['diff'], 2)};{r2['n_days_m3_better']}/{r2['n_days']} 日 M3 更好) | M3 > 底座 | {'过' if r2['pass'] else '不过'} |")
    r3 = C["R3"]; print(f"| R3 平书交付(主窗) | D {r3['D_delivered_share']:.3f};中位比 {r3['median_ratio(|intended|>0.01)']:.4f};{r3['n_anchors_zero_move_with_intended']}/{r3['n_anchors']} 锚零交付 | 两者 ∈ [0.95, 1.05] | {'过' if r3['pass'] else '不过'} |")
    print()
    print("| 窗 | 臂 | 日数 | Sharpe | 累计收益 | CAGR | maxDD 5m | 最差日 | 日 β vs BTC | g bps/锚 | 资金费 bps | 手续费 bps | 日止损 | 逐名止损 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for w in W:
        for arm in ("base", "m3"):
            m = T[w][arm]["mean_path"]; pp = T[w][arm]["paths"]
            print(f"| {w.split('_')[0]} | {arm} | {m['n_days']} | {m['sharpe']:.2f} [{pp['sharpe']['p2.5']:.2f}, {pp['sharpe']['p97.5']:.2f}] | {pct(m['total_return'])} | {pct(m['cagr'])} | "
                  f"{pct(m['maxdd_5m'])} [{100*pp['maxdd_5m']['p2.5']:.1f}, {100*pp['maxdd_5m']['p97.5']:.1f}] | {pct(m['worst_day'], 2)} | {f(m['beta_daily_vs_btc'])} | {m['g_bps_per_anchor']:+.3f} | "
                  f"{m['funding_paid_bps']:+.3f} | {m['fee_bps']:.3f} | {m['day_stop_flattens']:.1f} | {m['per_name_stops']:.0f} |")
    print()
    r4 = R["R4_report_only"]
    print("R4(只报告;对冲腿成本 = M3 臂 BTCUSDT 手续费 + 付出资金费 − 零对冲对照臂同项, bps/日 of 当日开盘 NAV;32 路径均值 [2.5%, 97.5%]):\n")
    print("| 窗 | Δ手续费 bps/日 | Δ资金费 bps/日 | Δ合计 bps/日 | ΔSharpe | Δ累计收益 | ΔmaxDD 5m | Δ最差日 | Δμ bps/日 | Δσ bps/日 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for w in W:
        x = r4[w]
        g = lambda k: f"{x[k]['path_mean']:+.2f} [{x[k]['p2.5']:+.2f}, {x[k]['p97.5']:+.2f}]"
        print(f"| {w.split('_')[0]} | {g('d_fee')} | {g('d_fund')} | {g('d_total')} | {f(x['delta_sharpe'])} | {pct(x['delta_total_return'])} | {pct(x['delta_maxdd_5m'])} | "
              f"{pct(x['delta_worst_day'], 2)} | {x['delta_mu_daily_bps']:+.2f} | {x['delta_sd_daily_bps']:+.2f} |")
    print()
    ip = R["in_path_hedge_report_only"]
    print("在路径对冲统计(只报告;M3 臂 32 路径合池):\n")
    print("| 窗 | 交易锚记录 | 原因计数 | 目标层交付份额 | 意图对冲 /Gs 均值 | 已加对冲锚的计划后书 β 均值 [p5, p95] | 跳过锚的计划后书 β 均值 |")
    print("|---|---|---|---|---|---|---|")
    for w in W:
        y = ip[w]; a = y["planned_post_trade_book_beta_applied_anchors"]; s = y["planned_post_trade_book_beta_skipped_anchors"]
        print(f"| {w.split('_')[0]} | {y['trading_anchor_records']} | {y['cause_counts']} | {y['delivered_share_at_target (Σ applied·sign(intended) / Σ|intended|)']:.3f} | "
              f"{y['intended_hedge_over_gs']['mean']:+.3f} | {a['mean']:+.4f} [{a['p5']:+.4f}, {a['p95']:+.4f}] | {f(s['mean'], 4) if s else '—'} |")
    print()
    if r2.get("pass") is not None:
        print(f"R2 逐日对照({r2['n_days']} 日;均值路径日收益):\n")
        print("| 日期 | BTC 当日 | M3 | 底座 | 差 |\n|---|---|---|---|---|")
        for d, rb, rm, rbs, df in r2["rows[date, r_btc, r_m3, r_base, diff]"]:
            print(f"| {d} | {pct(rb, 2)} | {pct(rm, 2)} | {pct(rbs, 2)} | {pct(df, 2)} |")
        print()
