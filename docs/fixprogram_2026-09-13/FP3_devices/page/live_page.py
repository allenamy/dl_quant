#!/usr/bin/env python3
"""FP3 observability page v4 (read-only; independent review e25d30fd §5-D; round 11 R11-PAGE, round 12 R12-M1, round 13 R13-M1). One Markdown page per UTC day.
ROUND 13 (both reviewer counterexamples): (6) the two sub-period numbers for a segment containing a flow are SCENARIOS, not a range — the true
time-weighted return can fall OUTSIDE them (100 → 200, deposit 100 → 300, → 220: true 46.67%, scenarios 10% / 20%), so the page no longer prints them
as an interval and says in words that a point value needs a valuation at the flow instant; (7) net-zero is not no-flow — +100 then −100 in one segment
was labelled exact while the capital timing really changed (true 33.33% vs the page's "exact" 20%), so exactness is now decided by the GROSS flow.
ROUND 12 (each a reviewer counterexample v2 passed): (1) `(NAV − net inflow)/prev − 1` was CALLED a TWR and is not — with a deposit at the start of
the day it reports 20% where the true time-weighted return is 10%. The day return is now a chain of sub-period returns across every LIVE NAV row,
exact for segments with no external flow and reported as an INTERVAL [flow-at-start, flow-at-end] for the segment that contains one; (2) the
long/short split assigned a whole name by its start (or end) position sign, so a round trip that begins and ends flat vanished from BOTH legs and from
the total — the total is now formed first and the split comes from the engine's per-SEGMENT sign (`pnl_long` + `pnl_short` == `pnl`); (3) the six
decision windows cover 21.5 h — the six carry gaps are priced too and the coverage is printed; (4) a page for a PAST day no longer prints the CURRENT
guard_twin / per-name-stop / IC state as if it were that day's: those blocks are bound to an as-of and labelled when they are not.
What changed in v2 (each a reviewer finding): (1) the price leg computed from a snapshot × later returns is labelled 「静态持仓价格暴露估计」 with its
coverage, and the ACTUAL price P&L of the day comes from the event-path engine shared with P-C2 v3 (pc/pnl_path.py: previous readback → fills →
flattens, priced on the producer 5m panel); (2) the top losers are merged per symbol over the day (not name×anchor rows); (3) under the per-name stop's
depth definition (unrealised / CURRENT notional, average price and quantity fixed) a long crosses −30% at a price move of 1/1.3 − 1 = −23.08%, a short at
1/0.7 − 1 = +42.86% (v1 wrote −30% for the long); (4) NAV / net transfers − 1 is a CAPITAL-BASIS ratio, not a return; the day return is a flow-adjusted
TWR (the day's signed TRANSFER rows removed from the closing NAV) and the cumulative TWR chains those days; (5) the IC line gives a verdict with the
window census (present / expected / missing vs max_missing), maturity lag and thresholds, or says UNJUDGEABLE and why; (6) the page no longer claims to
show "only realised numbers": NAV and every mark-to-market line include unrealised P&L. Nothing here is a verdict — it keeps 'ledger anomaly', 'IC
tripped' and 'positive expectation' apart. Read-only; env FP3_LIVE_REPO / FP3_WS override the ledger roots (tests / mirrors).
usage: live_page.py <YYYYMMDD> <out.md>"""
import sys, os, json, time, glob, collections
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pc"))
import pnl_path as PP

DAY, OUT = sys.argv[1], sys.argv[2]; REPO = PP.REPO; P = PP.P; GT = os.path.expanduser("~/guard_twin/state")
rows = PP.rows
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t))); d0 = int(time.mktime(time.strptime(DAY, "%Y%m%d")) - time.timezone)
days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if d.split("/")[-1] <= DAY)
nav = [r for d in days for r in rows(d, "daily_nav") if r.get("mode") in (None, "LIVE")]; nav.sort(key=lambda r: float(r["nav_ts"]))
latest = nav[-1] if nav else None
# transfers: the same rows guard_twin sums (its income.jsonl, type TRANSFER, asset USDT), by UTC day; cross-checked against daily_nav.external_flow_usdt
inc = [json.loads(l) for l in open(f"{GT}/income.jsonl") if l.strip()] if os.path.exists(f"{GT}/income.jsonl") else []
flow_by_day = collections.defaultdict(float)
_navd = sorted((float(r["nav_ts"]), time.strftime("%Y%m%d", time.gmtime(float(r["nav_ts"])))) for r in nav)   # a transfer belongs to the first daily NAV close that includes it
for r in inc:
    if r.get("type") == "TRANSFER" and r.get("asset") == "USDT":
        t = float(r["time"]) / 1000; d_ = next((d for ts_, d in _navd if ts_ >= t), time.strftime("%Y%m%d", time.gmtime(t)))
        flow_by_day[d_] += float(r["income"])
transfers_all = sum(flow_by_day.values())
# R12-M1 (4): guard_twin / per-name-stop / IC state files hold the CURRENT state. For a page about a PAST day they are not that day's state; they are
# printed with an explicit as-of label instead of being mixed in silently.
TODAY = time.strftime("%Y%m%d", time.gmtime()); IS_TODAY = (DAY == TODAY)
gt = json.load(open(f"{GT}/latest.json")) if os.path.exists(f"{GT}/latest.json") else {}
asof_note = "" if IS_TODAY else f" ⚠ **as-of {gt.get('utc')}(当前状态, 不是 {DAY} 当日状态)**"
lines = [f"# 实盘一页 {DAY} v4(只读, 生成 {time.strftime('%FT%TZ', time.gmtime())}; 账本根 {REPO})", ""]
# ── §1 equity: flow-adjusted TWR by day (last LIVE NAV row of each day), capital-basis ratio labelled as such
by_day = collections.OrderedDict()
for r in nav: by_day[time.strftime("%Y%m%d", time.gmtime(float(r["nav_ts"])))] = r          # last row of each day
dk = list(by_day)
# R12-M1: a real sub-period chain. Valuation points = EVERY LIVE NAV row; flows = the TRANSFER rows by timestamp. A segment with no flow activity has
# an exact return.
# ★ ROUND 13 R13-M1 — TWO CORRECTIONS.
# (6) The two numbers for a segment that CONTAINS a flow are SCENARIOS, not bounds. Placing the flow at the segment's start and at its end gives two
#     admissible answers, and the true time-weighted return need not lie between them: the reviewer's path 100 → 200, deposit 100 → 300, → 220 has a
#     true TWR of 46.67% while the two scenarios are 10% and 20%. Without a valuation AT the flow instant the segment's return is UNKNOWN; the page
#     now says so and never calls the pair a range or a bound.
# (7) NET-ZERO IS NOT NO-FLOW. `abs(F) < 1e-9` called +100 then −100 inside one segment "exact"; the capital timing really changed (the reviewer's
#     path gives a true 33.33% against the page's "exact" 20%). The exactness test is now the GROSS flow activity in the segment.
flows_t = sorted((float(r["time"]) / 1000, float(r["income"])) for r in inc if r.get("type") == "TRANSFER" and r.get("asset") == "USDT")
vps = [(float(r["nav_ts"]), float(r["nav"])) for r in nav]
segs = []                                             # (day_of_end, r_scen_lo, r_scen_hi, net_flow, exact, gross_flow, n_flows)
for (t0, v0), (t1, v1) in zip(vps, vps[1:]):
    seg_f = [a for t, a in flows_t if t0 < t <= t1]
    F = sum(seg_f); Fg = sum(abs(a) for a in seg_f)                    # R13-M1 (7): GROSS activity decides exactness, not the net
    d_ = time.strftime("%Y%m%d", time.gmtime(t1))
    if Fg < 1e-9:
        r_ = (v1 / v0 - 1.0) if v0 else 0.0; segs.append((d_, r_, r_, 0.0, True, 0.0, 0))
    else:
        cand = [(v1 / (v0 + F) - 1.0) if (v0 + F) else 0.0, ((v1 - F) / v0 - 1.0) if v0 else 0.0]
        segs.append((d_, min(cand), max(cand), F, False, Fg, len(seg_f)))
twr = []                                              # (day, r_scen_lo, r_scen_hi, net_flow, exact, gross_flow, n_flows)
for d in dk:
    ss = [x for x in segs if x[0] == d]
    if not ss: continue
    lo = float(np.prod([1.0 + x[1] for x in ss]) - 1.0); hi = float(np.prod([1.0 + x[2] for x in ss]) - 1.0)
    twr.append((d, min(lo, hi), max(lo, hi), sum(x[3] for x in ss), all(x[4] for x in ss), sum(x[5] for x in ss), sum(x[6] for x in ss)))
scen_lo = float(np.prod([1.0 + x[1] for x in twr]) - 1.0) if twr else None     # R13-M1 (6): SCENARIOS, not bounds — renamed so no reader can take them for a range
scen_hi = float(np.prod([1.0 + x[2] for x in twr]) - 1.0) if twr else None
cum_lo, cum_hi = scen_lo, scen_hi                                              # kept as aliases for downstream lines; the LABELS below say scenario
cum_twr = scen_lo if (scen_lo is not None and scen_hi is not None and abs(scen_hi - scen_lo) < 1e-12) else None
n_approx = sum(1 for x in twr if not x[4])
n_flow_days = sum(1 for x in twr if x[6])
idx = [1.0]
for x in twr: idx.append(idx[-1] * (1.0 + x[1]))
dd_twr = idx[-1] / max(idx) - 1.0 if idx else None
if latest:
    prev = [r for r in nav if float(r["nav_ts"]) < d0]; prev_close = float(prev[-1]["nav"]) if prev else None; f_today = flow_by_day.get(DAY, 0.0)
    ext = by_day[DAY].get("external_flow_usdt") if DAY in by_day else None
    navs = [float(r["nav"]) for r in nav]; peak = max(navs); peak_ts = nav[int(np.argmax(navs))]["nav_ts"]
    td = [x for x in twr if x[0] == DAY]
    day_txt = ("无当日 NAV 环节" if not td else
               (f"**{td[0][1]:+.2%}**(精确: 当日各子区间**无任何**外部流, 毛额也为 0)" if td[0][4] else
                f"**情景 {td[0][1]:+.2%} / {td[0][2]:+.2%}**(当日有 {td[0][6]} 笔外部流, 净 {td[0][3]:+,.0f} / 毛 {td[0][5]:,.0f}, 而无该时点估值 ⇒ "
                f"两个**情景**=流在子区间起点 / 终点; **真实时间加权收益不必落在两者之间**, 见下方口径说明)"))
    cum_txt = (f"**{scen_lo:+.2%}**(精确: 全部 {len(twr)} 个日环节都无外部流)" if n_approx == 0 else
               f"**情景 {scen_lo:+.2%} / {scen_hi:+.2%}**({len(twr)} 个日环节, 其中 {n_approx} 个含外部流 ⇒ **两个情景, 不是区间也不是上下界**)")
    lines += ["## 1. 权益(NAV 含未实现损益)",
              f"- 最新 NAV {float(latest['nav']):,.0f}({U(latest['nav_ts'])}); 原始 NAV 高点 {peak:,.0f}({U(peak_ts)}), 相对原始高点 {float(latest['nav']) / peak - 1:+.2%}(**含资金流**, 不是回撤); 按日回报指数(取较低的那个情景值)的回撤 **{dd_twr:+.2%}**",
              f"- 当日回报(**子区间链**, 逐 LIVE NAV 行分段, 流按时刻归段): {day_txt}"
              + (f"; daily_nav 自记当日外部流 {ext:+,.2f}" if ext is not None else "") + (f"; 未调整的 NAV 比值 {float(latest['nav']) / prev_close - 1:+.2%}" if prev_close else ""),
              f"- 累计(自首个 LIVE 日 {dk[0]} 起): {cum_txt}; twin 当日 {gt.get('day_pct_twin')} / 累计 {gt.get('cum_pct_twin')}(%){asof_note}",
              f"- **口径说明(复审第十二轮 R12-M1 + 第十三轮 R13-M1)**: ① 旧页把 (NAV − 净转入)/前值 − 1 叫 TWR —— 那是「流在期末」的单一假设, 期初入金时会高估"
              f"(100 起、期初入金 100、整体赚 10%、期末 220 ⇒ 旧式报 20%, 真 TWR 10%)。② **上面两个数是情景, 不是上下界**: 没有流时点估值时, 真实时间加权收益"
              f"**可以落在两者之外** —— 反例 100 涨到 200、入金 100 成 300、再跌到 220, 真 TWR **46.67%**, 而两情景是 10% / 20%。要得到点值必须有流发生时刻的估值。"
              f"③ **净额为零不等于没有资金流**: 同一区间先入 100 后出 100 的净额是 0, 资本时点却真的变了(真 TWR 33.33%, 旧页按「精确」报 20%); 现在按**毛额活动**判精确, "
              f"当日毛额 {(td[0][5] if td else 0):,.0f} / {(td[0][6] if td else 0)} 笔。",
              f"- 资本基准比: NAV / 净转入 {transfers_all:,.0f} − 1 = {float(latest['nav']) / transfers_all - 1:+.2%}(**不是收益率**: 分母是带号转账之和, 入金时点不同的钱不可比; guard_twin transfers_all {float(gt.get('transfers_all') or 0):,.0f})", ""]
# ── §2 P&L: (a) static exposure estimate (old method, labelled), (b) actual event-path price P&L, (c) merged top losers, breadth
rb = [r for r in rows(DAY, "position_readback") if str(r.get("source", "")).endswith("@post_anchor")]; snaps = collections.defaultdict(dict)
for r in rb: snaps[int(float(r["anchor_ts"]) // 14400 * 14400)][r["symbol"]] = r
ank = sorted(snaps); estL = estS = 0.0; priced = 0; n_pairs = max(len(ank) - 1, 0)
for i in range(len(ank) - 1):
    a, b = ank[i], ank[i + 1]
    for s, r in snaps[a].items():
        q = float(r["venue_position_qty"]); v = float(r["venue_position_notional"]); r2 = snaps[b].get(s)
        if not q or not r2 or not float(r2["venue_position_qty"]): continue
        m0 = abs(v) / abs(q); m1 = abs(float(r2["venue_position_notional"])) / abs(float(r2["venue_position_qty"])); pl = v * (m1 / m0 - 1.0); priced += 1
        if v > 0: estL += pl
        else: estS += pl
panel = PP.Panel(); L = PP.LedgerDay(DAY); per_sym = collections.defaultdict(float); actL = actS = act_tot = 0.0; n_ok = 0; cens_n = 0
fees = collections.defaultdict(float); statuses = []; fp_corr = 0.0; cov_w = cov_g = 0; gap_tot = gap_L = gap_S = 0.0; n_gap_ok = 0; gap_statuses = []
# R13-P2 (1): the page prices the day with the SAME chronological day price chain as P-C2 v5 — gap(A) precedes window(A), and one reference per symbol
px_chain = {}
prev_rec = PP.window_pnl(L, panel, d0 - 14400, px_chain=px_chain)                # carry state for the day's FIRST gap only
for A in [d0 + 14400 * k for k in range(6)]:
    _td, _tds = PP.decision_time(L, A)
    g = PP.gap_pnl(L, panel, A, _td, prev_rec, px_chain=px_chain)                # the gap precedes the window in time
    rec = PP.window_pnl(L, panel, A, px_chain=px_chain); statuses.append((U(A), rec.get("status"), rec.get("window_class"))); prev_rec = rec
    gap_statuses.append((U(A), g.get("status")))
    if g.get("status") == "GAP_OK":
        n_gap_ok += 1; gap_tot += g["pnl_usdt"]; gap_L += g["pnl_long_usdt"]; gap_S += g["pnl_short_usdt"]; fp_corr += g["fill_price_correction_usdt"]; cov_g += g.get("coverage_s", 0)
    if rec.get("status") != "OK": continue
    n_ok += 1; cens_n += rec["layers"]["L3_actual_path"]["censored"]["n"]; cov_w += rec.get("coverage_s", 0); fp_corr += rec["fill_price_correction_usdt"]
    for k, v in rec["fees_in_window"].items(): fees[k] += v
    # R12-M1 (2): the TOTAL is formed from every priced name first; the long/short split then comes from the engine's per-SEGMENT sign, so a name that
    # starts and ends flat (a round trip) keeps its P&L instead of disappearing from both legs.
    for s, v in rec["per_name_layers"]["L3_actual_path"].items():
        if not v: continue
        per_sym[s] += v["pnl"]; act_tot += v["pnl"]; actL += v.get("pnl_long", 0.0); actS += v.get("pnl_short", 0.0)
fu = sum(float(x.get("funding_paid") or 0.0) for x in rows(DAY, "funding"))
lines += ["## 2. 当日损益分解(价格损益含未实现; 两种口径分开列)",
          f"- (a) **静态持仓价格暴露估计**(锚后回读快照 × 到下一锚的标记变化, **不吃期间成交**, 下一锚已平的名跳过): 多头 {estL:+,.0f} / 空头 {estS:+,.0f} USDT; 覆盖 {n_pairs} 个锚对、{priced} 名-锚",
          f"- (b) **实际价格损益(事件路径, 引擎 pnl_path.py, 同 P-C2 v4)**: 决策窗合计 {act_tot:+,.0f}(多头 {actL:+,.0f} / 空头 {actS:+,.0f}) USDT; "
          f"**逐名合计先成立, 再按逐段持仓符号拆多空**(复审 R12-M1: 旧页按期初/期末符号归名, 期初期末均为 0 的来回交易两条腿都漏掉)",
          f"- (b2) **锚与决策之间的携带缺口**: {n_gap_ok}/6 段已定价, 合计 {gap_tot:+,.0f}(多 {gap_L:+,.0f} / 空 {gap_S:+,.0f}) USDT — 六个决策窗只覆盖 21.5 h, 这 150 分钟此前完全没算(复审 R12-P3); 状态 {', '.join(f'{u} {st}' for u, st in gap_statuses)}",
          f"- (b3) **全日实际价格损益 = 决策窗 + 缺口 = {act_tot + gap_tot:+,.0f} USDT**; 按**记录成交价**修正 {fp_corr:+,.0f} ⇒ {act_tot + gap_tot + fp_corr:+,.0f}(边界价与成交价两个口径并列, 互不替代)",
          f"- 覆盖: 窗 {cov_w:,} s + 缺口 {cov_g:,} s = **{cov_w + cov_g:,} / 86,400 s({(cov_w + cov_g) / 86400:.1%})**; 窗状态 {', '.join(f'{u} {st}' + (f'/{wc}' if wc else '') for u, st, wc in statuses)}; 删失名 {cens_n}; 窗内手续费 {dict((k, round(v, 4)) for k, v in fees.items())}",
          f"- 资金费 {fu:+,.2f} USDT(结算行, 全日)"]
if per_sym:
    neg = sorted([(s, p) for s, p in per_sym.items() if p < 0], key=lambda x: x[1]); tot_loss = sum(p for _, p in neg)
    lines += [f"- 亏损广度(事件路径, 逐名合并全日, 决策窗口径): {len(neg)} / {len(per_sym)} 名为负; 前 5 名占亏损 {sum(p for _, p in neg[:5]) / tot_loss:.0%}" if tot_loss else "- 无亏损名",
              f"- 最大亏损名(逐名合并, 非名×锚行): {[(s, round(p)) for s, p in neg[:5]]}"]
lines.append("")
# ── §3 risk budget (unchanged)
an = rows(DAY, "anchors")
if an and latest and ank:
    r = an[-1]; g = float(r.get("venue_gross_usdt") or 0); ns = sum(abs(float(x["venue_position_notional"])) for x in snaps[ank[-1]].values() if float(x["venue_position_notional"]) < 0)
    lines += ["## 3. 风险预算", f"- 实际 gross {g:,.0f} / NAV {float(latest['nav']):,.0f} = **{g / float(latest['nav']):.3f}×**(目标 2.0); 空头腿名义 {ns:,.0f}(占 gross {ns / g:.0%})" if g else "- 无 gross 记录",
              f"- 场所净 {float(r.get('venue_net_usdt') or 0):+,.0f} USDT(net/gross {float(r.get('net_over_gross') or 0):+.2%})", ""]
# ── §4 per-name stop with the real denominator, both legs' price thresholds
pns = json.load(open(f"{REPO}/state/live/per_name_stop.json")) if os.path.exists(f"{REPO}/state/live/per_name_stop.json") else {}
lines += ["## 4. 逐名止损(真实分母)",
          "- 规则: 深度 = 未实现损益 / **当前**名义 ≤ −30%, 连续 2 个终锚, 出场后冷却 7 天。均价与数量不变时: **空头**要涨 **+42.86%**(1/0.7 − 1)才越线, **多头**要跌 **−23.08%**(1/1.3 − 1)才越线(多头跌 30% 时深度已是 −42.86%); 不是「价格反向 30% 立即止损」, 也不是整书安全距离。",
          f"- {'当前' if IS_TODAY else f'⚠ **当前状态(文件即时值), 不是 {DAY} 当日状态**'}: stopped {list((pns.get('stopped') or {}).keys())}; counters {pns.get('counters')}; cooldown {[(s, U(t)) for s, t in (pns.get('cooldown') or {}).items()]}", ""]
# ── §5 IC monitor: verdict with census, maturity and thresholds
icp = f"{REPO}/state/live/ic_monitor_state.json"; ic = json.load(open(icp)) if os.path.exists(icp) else {}
le = ic.get("last_eval") or {}; th = (ic.get("contract") or {}).get("thresholds") or {}; fg = (ic.get("contract") or {}).get("freshness_gate") or {}; cen = le.get("census") or {}
lines += ["## 5. IC 监控是否可判" + ("" if IS_TODAY else f" ⚠ **as-of {le_at if (le_at := ((ic.get('last_eval') or {}).get('at_iso'))) else '未知'}(当前状态文件, 不是 {DAY} 当日)**")]
if le:
    for w in ("r24", "r48"):
        c = cen.get(w) or {}; val = le.get(w); judged = w in (le.get("judged_windows") or [])
        thr = {k: v for k, v in th.items() if w in k}
        if judged:
            trip = any((val is not None and val < v) for v in thr.values())
            lines.append(f"- {w}: **可判** — 值 {val:+.5f} vs 阈值 {thr} ⇒ {'触线' if trip else '未触线'}; 窗口 {c.get('present')}/{c.get('expected')} 锚, 缺 {c.get('missing')}(上限 {c.get('max_missing')})")
        else:
            lines.append(f"- {w}: **不可判(UNJUDGEABLE)** — 窗口 {c.get('present')}/{c.get('expected')} 锚, 缺 {c.get('missing')} > 上限 {c.get('max_missing')}(缺锚 {c.get('missing_anchors')}); 值 {val} 只作记录")
    lines.append(f"- 评估时刻 {le.get('at_iso')}, 前沿锚 {cen.get('frontier')}(成熟滞后 {fg.get('mature_lag_s')} s), 级别 {le.get('level')}; 事件 {(le.get('event') or {}).get('level')} open={(le.get('event') or {}).get('open')}(legacy={(le.get('event') or {}).get('legacy')})")
else:
    lines.append("- 无 last_eval 记录 ⇒ 不可判")
lines += ["- 口径: 书级实现 rank-IC(场所实持仓名义排序 vs 下锚隐含价收益排序), 24/48 锚 ≈ 4/8 天; 阈值按离线书标定, 未按在役形态重标(合同自述)。「未触线」只说明四到八天的秩相关没崩, 不说明当日不会亏。", ""]
lines += ["## 6. 三句话分开说",
          "- 账本有没有异常: 看 §3 的 net/gross、§2(b) 的删失与窗状态、D 现金核账的窗残差(本页不判)。",
          "- IC 有没有触线: 看 §5 的可判/不可判与触线(本页不判)。",
          "- 策略是否仍有正期望: 本页**不能**回答——它显示的是账本读数与事件路径价格损益(含未实现), 不是策略期望; 那要由正确口径的全史回放与现金结果回答。", ""]
open(OUT, "w").write("\n".join(lines)); print("\n".join(lines))
