"""Render NEWS2_STATS.json into the result tables (FREEZE §2 shape: A / B1 / B2 + the must-report set).

Renders from the receipt only; it never recomputes a number, so the document and the receipt cannot
disagree. Every section that the freeze requires has a fixed slot: if its input is absent the slot
prints an explicit NOT PRESENT line naming what is missing. A required section is never silently
dropped, because a missing table and a table of zeros read the same way in a finished document.

usage: python news2_render.py <NEWS2_STATS.json> <out.md> [--ext NEWS2_EXT.json] [--vs-new VS_NEW.json]
                             [--diag DIAGNOSTICS.json]
"""
import argparse, hashlib, json, os, sys

SEEDS = ("s42", "s2027")
CTRL = ("OLD", "OLD_HOLD")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def pct(x):
    return "n/a" if x is None else f"{100.0 * float(x):.1f}%"


def bps(x):
    return "n/a" if x is None else f"{float(x):+.3f}"


def ci(b):
    """boot() returns a dict; the 97.5% two-sided pair lives under a named key, not at index 0."""
    if not isinstance(b, dict):
        return None
    v = b.get("ci97.5_two_sided_bps")
    return v if isinstance(v, (list, tuple)) and len(v) == 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stats"); ap.add_argument("out")
    ap.add_argument("--ext"); ap.add_argument("--vs-new"); ap.add_argument("--diag")
    a = ap.parse_args()
    R = json.load(open(a.stats))
    L = []
    w = L.append

    w(f"<!-- rendered by news2_render.py from {os.path.basename(a.stats)} sha256 {sha(a.stats)}; no number is recomputed here -->")
    w("")
    w("### 判词(FREEZE §2;判据由 lead 书写)")
    w("")
    w(f"- **VERDICT = {R['VERDICT']}** — {R.get('verdict_rule', '')}")
    w(f"- 逐种子未过项:`{json.dumps(R.get('failing_by_seed', {}))}`")
    w(f"- 区间说明(原样):{R.get('interval_statement_verbatim', 'NOT PRESENT: interval_statement_verbatim')}")
    w("")

    for s in SEEDS:
        v = R.get("rules", {}).get(s)
        if v is None:
            w(f"#### NEWS2_{s}"); w(""); w(f"**NOT PRESENT**: rules.{s} missing from the receipt"); w(""); continue
        A = v["A"]
        w(f"#### NEWS2_{s}")
        w("")
        w("**A 门 — 能否替换在役(对 OLD 与 OLD_HOLD,写法同 db0123df7 §3)**")
        w("")
        w("| 规则 | 对 OLD | 对 OLD_HOLD | 判 |")
        w("|---|---|---|---|")
        w(f"| S1 判据窗日差点估计 > 0 | {bps(A['S1']['OLD']['estimate_bps_per_day'])} bps/日 | "
          f"{bps(A['S1']['OLD_HOLD']['estimate_bps_per_day'])} bps/日 | **{'PASS' if A['S1']['PASS'] else 'FAIL'}** |")
        segs = {c: A["S2"][c]["segment_means"] for c in CTRL}
        names = [k for k in segs["OLD"] if k != "2026"]
        cells = {c: " / ".join(f"{k} {bps(segs[c][k]['mean_bps_per_day'])}" for k in names) +
                    f"({A['S2'][c]['segments_positive']}/{len(names)})" for c in CTRL}
        w(f"| S2 分段中 ≥2 段 > 0 | {cells['OLD']} | {cells['OLD_HOLD']} | **{'PASS' if A['S2']['PASS'] else 'FAIL'}** |")
        dd = A["S3"]["maxdd_5m_pre2026_path_mean"]
        w(f"| S3 最大回撤(路径均值)不差于 OLD_HOLD | — | NEW_S2 {pct(dd['NEWS2'])} vs OLD_HOLD {pct(dd['OLD_HOLD'])} | "
          f"**{'PASS' if A['S3']['PASS'] else 'FAIL'}** |")
        hp = A["S4"]["halted_paths"]
        w(f"| S4 R-P 触线路径数 ≤ OLD_HOLD | — | NEW_S2 {hp['NEWS2']}/32 vs OLD_HOLD {hp['OLD_HOLD']}/32 | "
          f"**{'PASS' if A['S4']['PASS'] else 'FAIL'}** |")
        c5 = {c: "; ".join(f"{k} {bps(x['estimate_bps_per_day'])}" for k, x in A["S5"][c]["cells"].items()) for c in CTRL}
        w(f"| S5 三成本格 S1 同号 | {c5['OLD']} | {c5['OLD_HOLD']} | **{'PASS' if A['S5']['PASS'] else 'FAIL'}** |")
        iv = A.get("intervals_report_only", {})
        for c in CTRL:
            b = ci(iv.get(c, {}).get("boot_30d"))
            w(f"| (只报)30 日块 97.5% 区间 vs {c} | " + (f"[{bps(b[0])}, {bps(b[1])}]" if b else "NOT PRESENT: ci97.5_two_sided_bps") + " | | 不作门 |")
        w("")
        w(f"**A 合判**:{'PASS' if A['PASS'] else 'FAIL'}(未过:`{json.dumps(A['failing'])}`)")
        w("")
        w("**B 门 — 修复有没有把书弄差(对 NEW_S 同种子)**")
        w("")
        w("| 规则 | 值 | 判 |")
        w("|---|---|---|")
        w(f"| B1 判据窗合并日差点估计 ≥ 0 | {bps(v['B1']['estimate_bps_per_day'])} bps/日({v['B1']['n_days']} 天)| "
          f"**{'PASS' if v['B1']['PASS'] else 'FAIL'}** |")
        b2 = v["B2"]["halted_paths"]
        w(f"| B2 R-P 触线 ≤ NEW_S | NEW_S2 {b2['NEWS2']}/32 vs NEW_S {b2['NEWS']}/32 | **{'PASS' if v['B2']['PASS'] else 'FAIL'}** |")
        w("")
        vs = v.get("vs_NEW_S_report_only")
        w("**对 NEW_S 的 N1–N5 全表(必报,不作门)**")
        w("")
        if vs is None:
            w("**NOT PRESENT**: rules.%s.vs_NEW_S_report_only missing" % s)
        else:
            w("| 项 | 值 |")
            w("|---|---|")
            w(f"| 判据窗日差点估计 | {bps(vs['S1']['estimate_bps_per_day'])} bps/日 |")
            w("| 分段 | " + " / ".join(f"{k} {bps(x['mean_bps_per_day'])}" for k, x in vs["S2"]["segment_means"].items()) +
              f"({vs['S2']['segments_positive']} 段为正)|")
            w("| 三成本格 | " + "; ".join(f"{k} {bps(x['estimate_bps_per_day'])}" for k, x in vs["S5"]["cells"].items()) + " |")
            bb = ci(vs.get("intervals_report_only", {}).get("boot_30d"))
            w("| 30 日块 97.5% 区间 | " + (f"[{bps(bb[0])}, {bps(bb[1])}]" if bb else "NOT PRESENT: ci97.5_two_sided_bps") + " |")
        w("")

    w("### 对研究员 NEW 的差距(必报,不作门)")
    w("")
    if a.vs_new and os.path.exists(a.vs_new):
        V = json.load(open(a.vs_new))
        w(f"<!-- from {os.path.basename(a.vs_new)} sha256 {sha(a.vs_new)} -->")
        w("```json")
        w(json.dumps(V.get("summary", V), indent=1)[:2000])
        w("```")
    else:
        w("**NOT PRESENT**: 未提供 vs-NEW 收据(NEW_S2 对研究员 NEW 的差距)。FREEZE §2 把它列为必报,"
          "所以这里留一个具名空位,而不是省略这一节。")
    w("")

    w("### 两项诊断(必报,不作门)")
    w("")
    if a.diag and os.path.exists(a.diag):
        Dg = json.load(open(a.diag))
        w(f"<!-- from {os.path.basename(a.diag)} sha256 {sha(a.diag)} -->")
        for key, title in (("score_ic_three_versions", "三版本(NEW / NEW_S / NEW_S2)分数层 IC,同锚同成员"),
                           ("per_fix_columns", "逐修复项作用的特征列数")):
            w(f"**{title}**")
            w("")
            if key in Dg:
                w("```json"); w(json.dumps(Dg[key], indent=1)[:1500]); w("```")
            else:
                w(f"**NOT PRESENT**: 诊断收据里没有 `{key}`")
            w("")
    else:
        w("**NOT PRESENT**: 未提供诊断收据。必报两项:① 三版本分数层 IC 同锚比较;② 逐修复项作用列数。")
    w("")

    w("### 延伸段(只描述)")
    w("")
    if a.ext and os.path.exists(a.ext):
        E = json.load(open(a.ext))
        w(f"<!-- from {os.path.basename(a.ext)} sha256 {sha(a.ext)} -->")
        w("```json"); w(json.dumps(E.get("arms", E), indent=1)[:1500]); w("```")
    else:
        w("**NOT PRESENT**: 未提供延伸段收据(2026-08-31 → 09-18)。")
    w("")

    w("### 前置条件")
    w("")
    pc = R.get("preconditions", {})
    w(f"- OLD 复现复核:`{json.dumps(pc.get('P1_old_reproduction_recheck'))}`")
    w(f"- 四臂共用窗口轴:`{json.dumps(pc.get('P2_common_axis'))}`")
    w(f"- 不可用臂:{len(R.get('unavailable', []))} 个" +
      (f" — `{json.dumps(R['unavailable'])[:400]}`" if R.get("unavailable") else ""))
    w(f"- 统计量来自 `news_stats.py` sha256 `{list(R.get('statistics_imported_from', {}).values())[0] if R.get('statistics_imported_from') else 'NOT PRESENT'}`(import,非复制)")
    w("")

    open(a.out, "w").write("\n".join(L) + "\n")
    missing = sum(1 for x in L if "NOT PRESENT" in x)
    print(f"NEWS2_RENDER wrote {a.out} lines={len(L)} named_gaps={missing} out_sha256={sha(a.out)}", flush=True)


if __name__ == "__main__":
    main()
