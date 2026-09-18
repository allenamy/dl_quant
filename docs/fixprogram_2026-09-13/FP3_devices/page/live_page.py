#!/usr/bin/env python3
"""FP3 observability page v2 (read-only; independent review e25d30fd §5-D; corrected after review round 11 R11-PAGE). One Markdown page per UTC day.
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
gt = json.load(open(f"{GT}/latest.json")) if os.path.exists(f"{GT}/latest.json") else {}
lines = [f"# 实盘一页 {DAY} v2(只读, 生成 {time.strftime('%FT%TZ', time.gmtime())}; 账本根 {REPO})", ""]
# ── §1 equity: flow-adjusted TWR by day (last LIVE NAV row of each day), capital-basis ratio labelled as such
by_day = collections.OrderedDict()
for r in nav: by_day[time.strftime("%Y%m%d", time.gmtime(float(r["nav_ts"])))] = r          # last row of each day
dk = list(by_day); twr = []; prev_nav = None
for d in dk:
    n = float(by_day[d]["nav"]); f = flow_by_day.get(d, 0.0)
    if prev_nav: twr.append((d, (n - f) / prev_nav - 1.0, f))
    prev_nav = n
cum_twr = float(np.prod([1.0 + x[1] for x in twr]) - 1.0) if twr else None
idx = [1.0]
for _, r_, _ in twr: idx.append(idx[-1] * (1.0 + r_))
dd_twr = idx[-1] / max(idx) - 1.0 if idx else None
if latest:
    prev = [r for r in nav if float(r["nav_ts"]) < d0]; prev_close = float(prev[-1]["nav"]) if prev else None; f_today = flow_by_day.get(DAY, 0.0)
    ext = by_day[DAY].get("external_flow_usdt") if DAY in by_day else None
    navs = [float(r["nav"]) for r in nav]; peak = max(navs); peak_ts = nav[int(np.argmax(navs))]["nav_ts"]
    lines += ["## 1. 权益(NAV 含未实现损益)",
              f"- 最新 NAV {float(latest['nav']):,.0f}({U(latest['nav_ts'])}); 原始 NAV 高点 {peak:,.0f}({U(peak_ts)}), 相对原始高点 {float(latest['nav']) / peak - 1:+.2%}(**含资金流**, 不是回撤); 按日 TWR 指数的回撤 **{dd_twr:+.2%}**",
              (f"- 当日回报(流量调整 TWR: (NAV − 当日净转入 {f_today:+,.0f}) / 前一 LIVE 行 {prev_close:,.0f} − 1) **{(float(latest['nav']) - f_today) / prev_close - 1:+.2%}**"
               + (f"; daily_nav 自记当日外部流 {ext:+,.2f}" if ext is not None else "") + f"; 未调整的 NAV 比值 {float(latest['nav']) / prev_close - 1:+.2%}") if prev_close else "- 当日回报: 无前一日 NAV 行",
              f"- 累计(自首个 LIVE 日 {dk[0]} 起, {len(twr)} 个日环节的流量调整 TWR 链) **{cum_twr:+.2%}**; twin 当日 {gt.get('day_pct_twin')} / 累计 {gt.get('cum_pct_twin')}(%)",
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
panel = PP.Panel(); L = PP.LedgerDay(DAY); win = []; per_sym = collections.defaultdict(float); actL = actS = 0.0; n_ok = 0; cens_n = 0; fees = collections.defaultdict(float); statuses = []
for A in [d0 + 14400 * k for k in range(6)]:
    rec = PP.window_pnl(L, panel, A); statuses.append((U(A), rec.get("status"), rec.get("window_class")))
    if rec.get("status") != "OK": continue
    n_ok += 1; cens_n += rec["layers"]["L3_actual_path"]["censored"]["n"]
    for k, v in rec["fees_in_window"].items(): fees[k] += v
    for s, v in rec["per_name_layers"]["L3_actual_path"].items():
        if not v: continue
        per_sym[s] += v["pnl"]; side_q = v["qty"] if v["qty"] else v.get("qty_end", 0.0)
        if side_q > 0: actL += v["pnl"]
        elif side_q < 0: actS += v["pnl"]
fu = sum(float(x.get("funding_paid") or 0.0) for x in rows(DAY, "funding"))
lines += ["## 2. 当日损益分解(价格损益含未实现; 两种口径分开列)",
          f"- (a) **静态持仓价格暴露估计**(锚后回读快照 × 到下一锚的标记变化, **不吃期间成交**, 下一锚已平的名跳过): 多头 {estL:+,.0f} / 空头 {estS:+,.0f} USDT; 覆盖 {n_pairs} 个锚对、{priced} 名-锚",
          f"- (b) **实际价格损益(事件路径, 引擎 pnl_path.py, 同 P-C2 v3)**: 多头 {actL:+,.0f} / 空头 {actS:+,.0f} / 合计 {actL + actS:+,.0f} USDT; 覆盖 {n_ok}/6 窗(状态: {', '.join(f'{u} {st}' + (f'/{wc}' if wc else '') for u, st, wc in statuses)}); 删失名 {cens_n}; 窗内手续费 {dict((k, round(v, 4)) for k, v in fees.items())}",
          f"- 资金费 {fu:+,.2f} USDT(结算行, 全日)"]
if per_sym:
    neg = sorted([(s, p) for s, p in per_sym.items() if p < 0], key=lambda x: x[1]); tot_loss = sum(p for _, p in neg)
    lines += [f"- 亏损广度(事件路径, 逐名合并全日): {len(neg)} / {len(per_sym)} 名为负; 前 5 名占亏损 {sum(p for _, p in neg[:5]) / tot_loss:.0%}" if tot_loss else "- 无亏损名",
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
          f"- 当前: stopped {list((pns.get('stopped') or {}).keys())}; counters {pns.get('counters')}; cooldown {[(s, U(t)) for s, t in (pns.get('cooldown') or {}).items()]}", ""]
# ── §5 IC monitor: verdict with census, maturity and thresholds
icp = f"{REPO}/state/live/ic_monitor_state.json"; ic = json.load(open(icp)) if os.path.exists(icp) else {}
le = ic.get("last_eval") or {}; th = (ic.get("contract") or {}).get("thresholds") or {}; fg = (ic.get("contract") or {}).get("freshness_gate") or {}; cen = le.get("census") or {}
lines += ["## 5. IC 监控是否可判"]
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
