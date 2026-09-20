#!/usr/bin/env python3
"""bt_p_render.py — renders a bt_p_reading.py receipt into the markdown tables of a result doc. Pure formatting, no computation.

AMENDMENT 4 §A4: every mean/median printed here carries its effective sample size. Reading P has no E-0920-C instance (no value was
ever substituted for a missing one — `halt_of` always returns a computed cumulative return), so NO NUMBER IN THIS TABLE CHANGED when
the device moved onto the contract; the n_eff annotations are the only addition, and the receipt diff proves it.
usage: /usr/bin/python3 bt_p_render.py <BT_P_READING_*.json> <out.md>
"""
import json, sys

d = json.load(open(sys.argv[1])); L = []


def pc(x, n=1): return "—" if x is None else f"{100 * x:+.{n}f}%"


def ne(b): return f" (n_eff {b['measured']['n_eff']}/{b['population']['n']})"


for lbl, R in d["runs"].items():
    L.append(f"\n**P-halt · {lbl} · 窗口 {R['window'][0]} → {R['window'][1]} · 两个基准起点**\n")
    L.append("| 基准 | 逐路径跌破 | 首次跌破 最早 / 中位 / 最晚 | 停机时累计收益(中位) | 停机后仍有的锚占比(中位) | 不停机 窗末(中位) | P-halt 窗末(均值 / 中位) | 均值路径: 跌破点 / cum |")
    L.append("|---|---|---|---|---|---|---|---|")
    for bn, B in R["bases"].items():
        s = B["summary"]; per = B["per_path"]; mp = R["mean_path"]["bases"][bn]
        ha = sorted(x["halt_anchor"] for x in per if x["fired"]); sh = sorted(x["share_anchors_after_halt"] for x in per)
        L.append(f"| {bn} | {s['fired_paths']}/{s['n_paths']} | {ha[0][:16].replace('T', ' ') if ha else '—'} / {ha[len(ha) // 2][:16].replace('T', ' ') if ha else '—'} / "
                 f"{ha[-1][:16].replace('T', ' ') if ha else '—'} | {pc(s['cum_at_halt']['median'], 2)}{ne(s['cum_at_halt'])} | {sh[len(sh) // 2]:.3f} | {pc(s['end_return_nohalt']['median'])} | "
                 f"{pc(s['end_return_phalt']['mean'], 2)} / {pc(s['end_return_phalt']['median'], 2)}{ne(s['end_return_phalt'])} | "
                 f"{(mp['halt_anchor'][:16].replace('T', ' ') + ' / ' + pc(mp['cum_at_halt'], 2)) if mp['fired'] else '未跌破'} |")
    L.append(f"\n**P-start · {lbl} · 17 个季度起点 · 判「{d['rule']['breach_by'][:10]} 前是否跌破」· 收益到窗末 {R['window'][1][:10]}**\n")
    L.append("| 起点 | 逐路径跌破 | 首次跌破(中位) | 均值路径跌破 | 不停机 窗末(路径均值 [5%,95%]) | P-halt 窗末(路径均值 [5%,95%]) | 日末节奏敏感性 |")
    L.append("|---|---|---|---|---|---|---|")
    for st, v in R["p_start"].items():
        if not v.get("in_window"):
            L.append(f"| {st[:10]} | — | — | — | — | — | {v['status']} |"); continue
        k = [x for x in v if x.startswith("breach_by_")][0]; b = v[k]; e = v["to_window_end"]; mp = R["mean_path"]["p_start"][st]
        L.append(f"| {st[:10]} | {b['fired_paths']}/{b['n_paths']} | {str(v['first_breach_utc']['median'] or '—')[:16].replace('T', ' ')} | "
                 f"{('是 ' + mp['halt_anchor'][:10]) if mp['fired'] else '否'} | {pc(e['end_return_nohalt']['mean'])} [{pc(e['end_return_nohalt']['p05'])}, {pc(e['end_return_nohalt']['p95'])}]{ne(e['end_return_nohalt'])} | "
                 f"{pc(e['end_return_phalt']['mean'])} [{pc(e['end_return_phalt']['p05'])}, {pc(e['end_return_phalt']['p95'])}]{ne(e['end_return_phalt'])} | {v['sensitivity_utc_day_ends_only']['fired_paths']}/{b['n_paths']} |")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("rendered", sys.argv[2])
