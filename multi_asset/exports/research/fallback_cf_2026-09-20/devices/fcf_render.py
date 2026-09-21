#!/usr/bin/env python3
"""fcf_render.py — render the F-family result tables to markdown from the receipts, so no number is transcribed by hand.
Reads FCF_TABLES.json (+ optionally the P / P2 receipts), FCF_RISK_WEIGHTS.json and FCF_ARM_STATUS*.json.
Prints markdown to stdout. Every table prints its cell's anchor count n, and a cell with no measurement prints as `—`
with its n, never as 0 (E-0920-C).

═══ 2026-09-21 REPAIR — round-7 independent review, finding FB-04 ═══════════════════════════════════════════════════
The previous version emitted 32 rows of F4b′ with no sign that the arm had been demoted to a named, non-pre-registered
sensitivity. A status line at the top of one document does not bind a table that flows out on its own.

This version takes the standing of every arm from `fcf_arm_status.py`'s receipt and:
  · FAILS CLOSED (exit 3, named error) on any arm in the tables that has no status entry — so a NEW arm cannot be
    rendered until somebody declares what it is;
  · prints `label_short` beside the arm in EVERY row it emits, from the status field. Nobody has to remember to edit
    this renderer when a different arm is demoted tomorrow — that is the whole point of the repair;
  · prints, above the tables, a note generated from the status data naming every arm that carries no pre-registered
    verdict, with its reason.

usage: fcf_render.py <FCF_TABLES.json> <FCF_RISK_WEIGHTS.json> <FCF_ARM_STATUS.json> [out.md]
"""
import json, sys

MAIN_CELLS = ["R_level_2023-06-30→2026-08-31", "HIST_2023-06-30→2025-12-31 (the FINDING's window)",
              "fallback_subsample_R", "fallback_subsample_HIST", "combo_subsample_R", "combo_subsample_HIST"]
RISK_CELLS = ["whole_window", "full_recipe_window", "fallback_subsample", "fallback_subsample_full_recipe"]


class StatusMissing(Exception):
    """An arm with no declared status. Fail closed: rendering it would publish numbers with no standing."""


def f(x, n=4, sign=True):
    if x is None: return "—"
    try: return ("%+." + str(n) + "f") % x if sign else ("%." + str(n) + "f") % x
    except (TypeError, ValueError): return str(x)


def arm_cell(a, S):
    """The ONE place an arm's name is turned into a table cell. The marker comes from the status receipt, never from a
    literal in this file, so a differently demoted arm is labelled without touching the renderer."""
    st = S["arms"].get(a)
    if st is None:
        raise StatusMissing(a)
    mk = st.get("label_short")
    return f"{a} {mk}" if mk else a


def standing_note(S):
    rows = [a for a, v in S["arms"].items() if v.get("non_preregistered") or v.get("label_short")]
    if not rows: return []
    out = ["\n> **臂的地位(逐行随数字同行印出, 来源 = `FCF_ARM_STATUS` 收据, 不是本渲染器里的字面量)**\n",
           "| 臂 | 标记 | 地位 | 携带预注册判词? | 依据 |", "|---|---|---|---|---|"]
    for a in rows:
        v = S["arms"][a]
        out.append(f"| {arm_cell(a, S)} | {v.get('label_short') or '—'} | {v.get('label') or v.get('status')} | "
                   f"{'**否**' if not v.get('carries_a_preregistered_verdict') else '是'} | {v.get('reason')} |")
    out.append(f"\n> **F4 of record = {S['F_of_record']}**。现行判语: **{S['live_verdict']}**。\n")
    return out


def render(tables_path, risk_path, status_path):
    T = json.load(open(tables_path)); R = json.load(open(risk_path)); S = json.load(open(status_path))
    out = []
    arms = list(T["arms"])

    # fail closed BEFORE any number is printed
    undeclared = [a for a in arms if a not in S["arms"]]
    if undeclared:
        raise StatusMissing(", ".join(undeclared))

    cells = [c for c in MAIN_CELLS if c in T["cell_definitions"]] + [c for c in T["cell_definitions"] if c.startswith("year ")]

    out.extend(standing_note(S))
    out.append("\n### A · 主读数逐格(判官口径, level R)\n")
    out.append("> g = 1e4·(navm1/navm0−1)/2.0, 全格锚取算术平均(hold/halt/日止损锚都算在内, 一个不丢);"
               " CAGR / Sharpe 走日度复利; maxDD 4h 与 5m 各报一列。定义全部来自认证渲染器 `bt_tables.py`"
               f" (sha256 {T['bt_tables_sha256'][:16]}…), 本装置不自定义任何一个指标。\n")
    for c in cells:
        d = T["cell_definitions"][c]
        if not d["n_anchors"]: continue
        out.append(f"\n**{c}** — n = {d['n_anchors']} 锚, {d['first']} → {d['last']}\n")
        out.append("| 臂 | g (bps/锚/gross) | CAGR | Sharpe(日) | maxDD 4h | maxDD 5m | 换手/gross | 手续费 | 日止损平仓 | 逐名止损 | hold 锚 | halt 锚 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a in arms:
            m = T["arms"][a]["cells"][c]
            if not m.get("n_anchors"):
                out.append(f"| {arm_cell(a, S)} | — | — | — | — | — | — | — | — | — | — | — |"); continue
            out.append(f"| {arm_cell(a, S)} | {f(m['g'])} | {f(m['cagr'])} | {f(m['sharpe_daily'], 3)} | {f(m['maxdd_4h'])} | {f(m['maxdd_5m'])} "
                       f"| {f(m['turnover_over_gross'], 4, False)} | {f(m['fee'])} | {m['day_stop_flattens']:.1f} | {m['per_name_stops']:.1f} "
                       f"| {m['hold_anchors']:.0f} | {m['halt_anchors']:.0f} |")

    out.append("\n### B · 配对 Δ vs F0(同锚、同成交路径; 5 日移动块自举 B=10,000)\n")
    out.append("> **level R 只能否决, 不能晋级。** 下表的 (A)/(B)/(C) 标签是 `bt_tables.paired` 自带的描述性标签, "
               "在本文中一律**不得**读作「有效」或「改进」; 它们只用来指出哪一格连描述性都过不了。Holm 不在此处施加"
               "(预注册把族内控制放在前瞻级)。**带标记的臂不携带预注册判词, 见上面的地位表。**\n")
    for c in cells:
        if not T["cell_definitions"].get(c, {}).get("n_anchors"): continue
        rows = []
        for a in arms:
            if a == "F0": continue
            p = T["paired_vs_F0"].get(a, {}).get(c)
            if not p or "UNAVAILABLE" in p:
                rows.append(f"| {arm_cell(a, S)} − F0 | {(p or {}).get('n_anchors', 0)} | UNAVAILABLE | | | |"); continue
            def ci(q, n=4):
                c = q.get("ci95")
                return f"{f(q.get('estimate'), n)}" + (f" [{f(c[0], n)}, {f(c[1], n)}]" if c else " [CI UNAVAILABLE]")
            g_ = p["d_g"]; s_ = p["d_sharpe"]; cg = p["d_cagr"]
            deg = " **退化格**" if p.get("DEGENERATE_CELL") else ""
            rows.append(f"| {arm_cell(a, S)} − F0 | {p['n_anchors']} | {ci(g_)} | {ci(s_, 3)} | {ci(cg)} | {g_.get('label', '')} / {s_.get('label', '')}{deg} |")
        if rows:
            out.append(f"\n**{c}** — n = {T['cell_definitions'][c]['n_anchors']} 锚, rng 见收据\n")
            out.append("| 对比 | n 锚 | Δg [CI95] | ΔSharpe [CI95] | ΔCAGR [CI95] | 标签(Δg / ΔSharpe) |")
            out.append("|---|---|---|---|---|---|")
            out.extend(rows)

    out.append("\n### C · 预注册 §4 必报风险列\n")
    out.append("> 归一化口径 = 生产执行器自己的: `target = w / gross_in × NAV × gross_mult`"
               "(`external_book.py` L403-404), `gross_in` = 生产者宇宙**之内**的 Σ|w|。"
               "「放大倍数」= gross_mult / gross_in, 即预注册 §4 里那个 5.3×。**每个统计量旁边都带它的有效样本数。**\n")
    for c in RISK_CELLS:
        if c not in R["arms"][arms[0]]["cells"]: continue
        out.append(f"\n**{c}**\n")
        out.append("| 臂 | n 锚 | 有测量 | 单名最大权重 中位 / p95 | 有效名数 中位 / p95 | 放大倍数 中位 / p95 | gross_in 中位 | 不可交易权重占比 p95(实持) |")
        out.append("|---|---|---|---|---|---|---|---|")
        for a in arms:
            w = R["arms"][a]["cells"][c]["written"]; e = R["arms"][a]["cells"][c]["effective_book_held"]
            mw = w["single_name_max_weight"]; en = w["effective_names_1_over_sumw2"]; am = w["amplification_gross_mult_over_gross_in"]
            gi = w["gross_in"]; ut = e["untradable_weight_share"]
            out.append(f"| {arm_cell(a, S)} | {mw['n_population']} | {mw['n_measured']} | {f(mw['median'], 4, False)} / {f(mw['p95'], 4, False)} "
                       f"| {f(en['median'], 1, False)} / {f(en['p95'], 1, False)} | {f(am['median'], 3, False)} / {f(am['p95'], 3, False)} "
                       f"| {f(gi['median'], 4, False)} | {f(ut['p95'], 4, False)} |")
    out.append("\n**不再平衡的连续锚数**(F2 的核心风险; 一段 run 归属于它**起始锚**所在的格, 长度按真实不间断长度报, 不在格边界截断)\n")
    out.append("| 臂 | 窗 | run 数 | 最长(锚 / 天) | 中位(锚) | p95(锚) | hold 锚合计 |")
    out.append("|---|---|---|---|---|---|---|")
    for a in arms:
        for lab in ("whole_window", "full_recipe_window"):
            h = R["arms"][a]["consecutive_hold_runs"][lab]
            out.append(f"| {arm_cell(a, S)} | {lab} | {h['n_runs']} | {h['longest_anchors']} / {h['longest_days']} | "
                       f"{f(h['median_anchors'], 1, False)} | {f(h['p95_anchors'], 1, False)} | {h['total_hold_anchors']} |")

    gate = R.get("prereg_s4_F1_concentration_gate", {})
    if gate:
        out.append("\n**预注册 §4 对 F1 的集中度门**(F1 的单名最大权重 p95 若超过 F0 的 1.5 倍, 即使收益更好也只能标 (C))\n")
        out.append("| 格 | F0 p95 | F1 p95 | 比值 | 阈值 | 越界? |")
        out.append("|---|---|---|---|---|---|")
        for c, v in gate.items():
            out.append(f"| {c} | {f(v['F0_p95'], 5, False)} | {f(v['F1_p95'], 5, False)} | {f(v['ratio'], 3, False)} | {v['threshold']} | "
                       f"{'**是**' if v['breached'] else '否'} |")

    return "\n".join(out) + "\n"


def unlabelled_rows(text, S):
    """Self-check, also used by fcf_doc_check: every table row naming an arm that has a marker must carry that marker."""
    bad = []
    for line in text.splitlines():
        if not line.startswith("| "): continue
        first = line.split("|")[1].strip()
        for a, v in S["arms"].items():
            mk = v.get("label_short")
            if not mk: continue
            token = first.split(" ")[0].replace("**", "")
            if token == a and mk not in first:
                bad.append(line)
    return bad


def main():
    if len(sys.argv) < 4:
        print("FCF_RENDER VERDICT=REFUSED reason=no_arm_status_receipt_given "
              "usage='fcf_render.py <FCF_TABLES.json> <FCF_RISK_WEIGHTS.json> <FCF_ARM_STATUS.json> [out.md]'", flush=True)
        sys.exit(3)
    try:
        txt = render(sys.argv[1], sys.argv[2], sys.argv[3])
    except StatusMissing as e:
        print(f"FCF_RENDER VERDICT=REFUSED reason=arm_with_no_declared_status arms={e}", flush=True)
        sys.exit(3)
    S = json.load(open(sys.argv[3]))
    bad = unlabelled_rows(txt, S)
    if bad:
        print(f"FCF_RENDER VERDICT=REFUSED reason=marked_arm_rendered_without_its_marker n={len(bad)} first={bad[0]!r}", flush=True)
        sys.exit(3)
    if len(sys.argv) > 4:
        open(sys.argv[4], "w").write(txt)
        print("wrote", sys.argv[4], len(txt), "bytes")
    else:
        print(txt)
    marked = {a: v["label_short"] for a, v in S["arms"].items() if v.get("label_short")}
    print(f"FCF_RENDER VERDICT=PASS bytes={len(txt)} rows={sum(1 for l in txt.splitlines() if l.startswith('| '))} "
          f"marked_arms={json.dumps(marked, ensure_ascii=False)} unlabelled_rows=0", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
