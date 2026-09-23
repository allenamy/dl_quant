#!/usr/bin/env python3
"""news_render.py — renders NEWS_STATS.json / NEWS_EXT.json / BT_P_READING_*.json into markdown (formatting and unit conversion only;
every number is read from a receipt whose sha256 is printed). Mac: /usr/bin/python3 news_render.py <NEWS_STATS.json> <NEWS_EXT.json> <out.md>"""
import sys, json, hashlib, os

STATS, EXT, OUT = sys.argv[1:4]
ARMS = ("OLD", "OLD_HOLD", "NEWS_s42", "NEWS_s2027"); SEEDS = ("NEWS_s42", "NEWS_s2027"); CTRLS = ("OLD", "OLD_HOLD")
SEGS = ("2023H2", "2024", "2025", "pre2026", "2026")


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def pct(x, d=1): return "n/a" if x is None else f"{100 * x:+.{d}f}%"
def num(x, d=2): return "n/a" if x is None else f"{x:+.{d}f}"


S = json.load(open(STATS)); X = json.load(open(EXT)); L = []; w = L.append
w(f"<!-- rendered by news_render.py from NEWS_STATS.json sha256 {sha(STATS)}; NEWS_EXT.json sha256 {sha(EXT)} -->")
w("\n### Verdict (prereg §3; both F10 seeds must satisfy S1–S5)\n")
w(f"- **VERDICT = {S['VERDICT']}** — {S['verdict_rule']}; failing rules by seed: {json.dumps(S['failing_by_seed'])}")
w(f"- 区间说明(原样):{S['interval_statement_verbatim']}")
for s in SEEDS:
    v = S["rules"][s]
    w(f"\n#### {s}\n")
    w("| 规则 | 对 OLD | 对 OLD_HOLD | 判 |")
    w("|---|---|---|---|")
    w(f"| S1 pre-2026 日差点估计 > 0 | {v['S1']['OLD']['estimate_bps_per_day']:+.3f} bps/日 | {v['S1']['OLD_HOLD']['estimate_bps_per_day']:+.3f} bps/日 | **{'PASS' if v['S1']['PASS'] else 'FAIL'}** |")
    seg = lambda c: " / ".join(f"{k} {v['S2'][c]['segment_means'][k]['mean_bps_per_day']:+.3f}" for k in ("2023H2", "2024", "2025")) + f"({v['S2'][c]['segments_positive']}/3)"
    w(f"| S2 三段中 ≥2 段 > 0 | {seg('OLD')} | {seg('OLD_HOLD')} | **{'PASS' if v['S2']['PASS'] else 'FAIL'}** |")
    dd = v["S3"]["maxdd_5m_pre2026_path_mean"]
    w(f"| S3 pre-2026 maxDD(路径均值)不差于 OLD_HOLD | — | NEW_S {pct(dd['NEWS'])} vs OLD_HOLD {pct(dd['OLD_HOLD'])} | **{'PASS' if v['S3']['PASS'] else 'FAIL'}** |")
    hp = v["S4"]["halted_paths"]
    w(f"| S4 R-P 触线路径数 ≤ OLD_HOLD | — | NEW_S {hp['NEWS']}/32 vs OLD_HOLD {hp['OLD_HOLD']}/32 | **{'PASS' if v['S4']['PASS'] else 'FAIL'}** |")
    cc = lambda c: "; ".join(f"{k} {x['estimate_bps_per_day']:+.3f}" for k, x in v["S5"][c]["cells"].items())
    w(f"| S5 三成本格 S1 同号 | {cc('OLD')} | {cc('OLD_HOLD')} | **{'PASS' if v['S5']['PASS'] else 'FAIL'}** |")
    ci = lambda c, k: v["intervals_report_only"][c][k]["ci97.5_two_sided_bps"]
    w(f"| (只报)30 日块 97.5% 区间 | [{ci('OLD','boot_30d')[0]:+.3f}, {ci('OLD','boot_30d')[1]:+.3f}] | [{ci('OLD_HOLD','boot_30d')[0]:+.3f}, {ci('OLD_HOLD','boot_30d')[1]:+.3f}] | 不作门 |")
    w(f"| (只报)5 日块 97.5% 区间 | [{ci('OLD','boot_5d')[0]:+.3f}, {ci('OLD','boot_5d')[1]:+.3f}] | [{ci('OLD_HOLD','boot_5d')[0]:+.3f}, {ci('OLD_HOLD','boot_5d')[1]:+.3f}] | 不作门 |")
    w(f"| (只报)2026 段日差 | {v['S2']['OLD']['segment_means']['2026']['mean_bps_per_day']:+.3f} | {v['S2']['OLD_HOLD']['segment_means']['2026']['mean_bps_per_day']:+.3f} | 只报告 |")
w("\n### 逐段四方对照(R-main 主设置,基准成本格,32 路径均值 [2.5%, 97.5%])\n")
w("| 段 | 臂 | Sharpe(完整 UTC 日) | 累计收益 | CAGR | 最大回撤 5m | 最差日 | §4-2 日止损 | 逐名止损 | 换手/gross/锚 |")
w("|---|---|---|---|---|---|---|---|---|---|")
def cell(t, k, f, d):
    v = t["paths"].get(k)
    if not isinstance(v, dict) or "path_mean" not in v: return "UNAVAILABLE"
    return f"{f(v['path_mean'], d)} [{f(v['p2.5'], d)}, {f(v['p97.5'], d)}]"
for sg in SEGS:
    for a in ARMS:
        t = S["tables"][a]["base"][sg]
        w(f"| {sg} | {a} | {cell(t,'sharpe',num,2)} | {cell(t,'total_return',pct,1)} | {cell(t,'cagr',pct,1)} | {cell(t,'maxdd_5m',pct,1)} | {cell(t,'worst_day',pct,2)} | "
          f"{cell(t,'day_stop_flattens',lambda x,d: f'{x:+.1f}',1)} | {cell(t,'per_name_stops',lambda x,d: f'{x:+.0f}',0)} | {t['paths']['turnover_over_gross']['path_mean']:.4f} |")
w("\n### 现金分解(bps/锚/单位目标 gross,32 路径均值;g = 价格 − 资金费 − 手续费 − 未知)\n")
w("| 段 | 臂 | g | 价格与交易 | 资金费支付 | 手续费 | 未知剔除 |")
w("|---|---|---|---|---|---|---|")
for sg in SEGS:
    for a in ARMS:
        p = S["tables"][a]["base"][sg]["paths"]
        w(f"| {sg} | {a} | {p['g']['path_mean']:+.3f} | {p['price']['path_mean']:+.3f} | {p['funding_paid']['path_mean']:+.3f} | {p['fee']['path_mean']:+.3f} | {p['unknown_excluded']['path_mean']:+.3f} |")
w("\n### 成本格与 literal 读数(只报告):路径均值 Sharpe / 累计收益\n")
w("| 格 | 段 | " + " | ".join(ARMS) + " |"); w("|---|---|" + "---|" * len(ARMS))
for c in ("fee_x1.25", "slip_x1.5", "fill_x0.9", "lit"):
    for sg in ("pre2026", "2026"):
        row = []
        for a in ARMS:
            t = S["tables"].get(a, {}).get(c, {}).get(sg)
            row.append("not run (by design)" if t is None else f"S {t['paths']['sharpe']['path_mean']:+.2f} / {pct(t['paths']['total_return']['path_mean'])}")
        w(f"| {c} | {sg} | " + " | ".join(row) + " |")
w("\n### R-P(−25% 自 2023-06-30T04Z 起算的永久停机,窗口至 2026-08-31;只报告)\n")
w("| 臂 | 触线路径 | 收据 |"); w("|---|---|---|")
for a in ARMS:
    r = S["R_P"][a]; w(f"| {a} | {r['halted_paths']}/{r['n_paths']} | {os.path.basename(r['receipt'])} sha {r['receipt_sha256'][:16]} |")
w("\n### 延伸段 2026-08-31T04Z → 2026-09-18T20Z(只描述;OLD = 认证 OBJB_A0X)\n")
w("| 臂 | 累计收益 | Sharpe | 最大回撤 5m | 最差日 | g | 日止损 | d̄ vs OLD(bps/日,点) |"); w("|---|---|---|---|---|---|---|---|")
for a, v in X["arms"].items():
    w(f"| {a} | {pct(v['total_return']['path_mean'])} | {num(v['sharpe']['path_mean'])} | {pct(v['maxdd_5m']['path_mean'])} | {pct(v['worst_day']['path_mean'],2)} | {v['g']['path_mean']:+.3f} | {v['day_stop_flattens']['path_mean']:.2f} | "
      f"{(format(v['dbar_vs_OLD_bps_per_day_point'], '+.2f') + ' (' + str(v['dbar_n_days']) + ' d)') if 'dbar_vs_OLD_bps_per_day_point' in v else '—'} |")
w(f"\n控制(延伸运行 vs 主运行共享锚):{json.dumps(X['control_vs_main_run'])}")
open(OUT, "w").write("\n".join(L) + "\n"); print("rendered", OUT, sha(OUT))
