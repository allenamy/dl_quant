#!/usr/bin/env python3
"""FP3 observability page (read-only; independent review e25d30fd §5-D): one Markdown page per UTC day from the LIVE ledgers and the twin guard.
Shows, side by side and with their true denominators: drawdown from the recent equity high, day return, return on starting capital; long / short leg price P&L,
funding, fees; loss breadth and concentration; actual gross / NAV and the short-leg risk budget; per-name stop counts with the REAL denominator (unrealised /
current notional ⇒ a short needs +42.9% to cross −30%) and cooldown list; whether the IC windows are judgeable. Nothing here is a verdict — it separates
'ledger has no anomaly', 'IC not tripped' and 'the book still has positive expected return', which the reversal audit found were being conflated.
usage: live_page.py <YYYYMMDD> <out.md>"""
import sys, os, json, time, glob, collections
import numpy as np
DAY, OUT = sys.argv[1], sys.argv[2]; REPO = os.path.expanduser("~/dl_quant_live"); WS = os.path.expanduser("~/wide_shadow"); P = f"{REPO}/state/live/pilot_log"
rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t))); d0 = int(time.mktime(time.strptime(DAY, "%Y%m%d")) - time.timezone)
days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if d.split("/")[-1] <= DAY)
nav = [r for d in days for r in rows(d, "daily_nav") if r.get("mode") in (None, "LIVE")]; nav.sort(key=lambda r: float(r["nav_ts"]))
today = [r for r in nav if time.strftime("%Y%m%d", time.gmtime(float(r["nav_ts"]))) == DAY]; latest = nav[-1] if nav else None
navs = [float(r["nav"]) for r in nav]; peak = max(navs) if navs else None; peak_ts = nav[int(np.argmax(navs))]["nav_ts"] if navs else None
gt = json.load(open(os.path.expanduser("~/guard_twin/state/latest.json"))) if os.path.exists(os.path.expanduser("~/guard_twin/state/latest.json")) else {}
start_nav = float(gt.get("transfers_all") or 0.0) or (float(nav[0]["nav"]) if nav else None)          # capital basis = total transfers in (guard_twin), not the first tiny pre-deposit NAV row
lines = [f"# 实盘一页 {DAY}(只读, 生成 {time.strftime('%FT%TZ', time.gmtime())})", ""]
if latest:
    prev = [r for r in nav if float(r["nav_ts"]) < d0]; prev_close = float(prev[-1]["nav"]) if prev else None
    lines += ["## 1. 权益", f"- 最新 NAV {float(latest['nav']):,.0f}({U(latest['nav_ts'])}); 近期高点 {peak:,.0f}({U(peak_ts)}); **相对高点回撤 {float(latest['nav']) / peak - 1:+.2%}**",
              f"- 当日回报(自前一 LIVE 行 {prev_close:,.0f} 起) **{float(latest['nav']) / prev_close - 1:+.2%}**" if prev_close else "- 当日回报: 无前一日 NAV 行", f"- 相对总入金 {start_nav:,.0f}(guard_twin transfers_all): {float(latest['nav']) / start_nav - 1:+.2%}; twin 当日 {gt.get('day_pct_twin')} / 累计 {gt.get('cum_pct_twin')}(%)", ""]
# leg P&L today from readback marks (price only), funding/fees from ledgers
rb = [r for r in rows(DAY, "position_readback") if str(r.get("source", "")).endswith("@post_anchor")]; snaps = collections.defaultdict(dict)
for r in rb: snaps[int(float(r["anchor_ts"]) // 14400 * 14400)][r["symbol"]] = r
ank = sorted(snaps); legL = legS = 0.0; losers = []; priced = 0
for i in range(len(ank) - 1):
    a, b = ank[i], ank[i + 1]
    for s, r in snaps[a].items():
        q = float(r["venue_position_qty"]); v = float(r["venue_position_notional"]); r2 = snaps[b].get(s)
        if not q or not r2 or not float(r2["venue_position_qty"]): continue
        m0 = abs(v) / abs(q); m1 = abs(float(r2["venue_position_notional"])) / abs(float(r2["venue_position_qty"])); pl = v * (m1 / m0 - 1.0); priced += 1
        if v > 0: legL += pl
        else: legS += pl
        losers.append((s, pl))
fu = sum(float(x.get("funding_paid") or 0.0) for x in rows(DAY, "funding")); fills = rows(DAY, "fills"); seen = {}; 
for r in fills: seen[r.get("trade_id")] = r
fees = collections.defaultdict(float)
for r in seen.values(): fees[r.get("commission_asset")] += float(r.get("commission") or 0.0)
lines += ["## 2. 当日损益分解(价格损益按锚后回读标记, 只到最后一个已回读锚)", f"- 多头腿价格 {legL:+,.0f} USDT; 空头腿价格 {legS:+,.0f} USDT(锚对 {len(ank) - 1}, 定价名 {priced})", f"- 资金费 {fu:+,.2f} USDT(结算行); 手续费 {dict((k, round(v, 4)) for k, v in fees.items())}"]
if losers:
    neg = sorted([x for x in losers if x[1] < 0], key=lambda x: x[1]); tot_loss = sum(x[1] for x in neg)
    lines += [f"- 亏损广度: {len(neg)} / {len(losers)} 名-锚为负; 前 5 名占亏损 {sum(x[1] for x in neg[:5]) / tot_loss:.0%}" if tot_loss else "- 无亏损名", f"- 最大亏损名: {[(s, round(p)) for s, p in neg[:5]]}", ""]
# gross / NAV and short-leg budget from the last anchors row
an = rows(DAY, "anchors")
if an and latest:
    r = an[-1]; g = float(r.get("venue_gross_usdt") or 0); ns = sum(abs(float(x["venue_position_notional"])) for x in snaps[ank[-1]].values() if float(x["venue_position_notional"]) < 0) if ank else 0.0
    lines += ["## 3. 风险预算", f"- 实际 gross {g:,.0f} / NAV {float(latest['nav']):,.0f} = **{g / float(latest['nav']):.3f}×**(目标 2.0); 空头腿名义 {ns:,.0f}(占 gross {ns / g:.0%})", f"- 场所净 {float(r.get('venue_net_usdt') or 0):+,.0f} USDT(net/gross {float(r.get('net_over_gross') or 0):+.2%})", ""]
# per-name stop with the real denominator
pns = json.load(open(f"{REPO}/state/live/per_name_stop.json")) if os.path.exists(f"{REPO}/state/live/per_name_stop.json") else {}
lines += ["## 4. 逐名止损(真实分母)", "- 规则: 深度 = 未实现损益 / **当前**名义 ≤ −30%, 连续 2 个终锚, 出场后冷却 7 天。**空头**要涨 +42.9% 才越线(数量不变时 −30%/0.70), 多头跌 −30% 越线; 不是「价格反向 30% 立即止损」。",
          f"- 当前: stopped {list((pns.get('stopped') or {}).keys())}; counters {pns.get('counters')}; cooldown {[(s, U(t)) for s, t in (pns.get('cooldown') or {}).items()]}", ""]
# IC monitor judgeability
icp = f"{REPO}/state/live/ic_monitor_state.json"; ic = json.load(open(icp)) if os.path.exists(icp) else {}
lines += ["## 5. IC 监控是否可判", f"- 状态文件键: {sorted(ic.keys())[:12]}", "- 24/48 锚窗 ≈ 4 / 8 天: **不是**快速反转保护; 「不触线」只说明四到八天的秩相关没崩, 不说明当日不会亏。", ""]
lines += ["## 6. 三句话分开说", "- 账本有没有异常: 看 §3 的 net/gross 与 D 现金核账的窗残差(本页不判)。", "- IC 有没有触线: 看 §5(本页不判)。", "- 策略是否仍有正期望: 本页**不能**回答——它只显示已实现的数字。", ""]
open(OUT, "w").write("\n".join(lines)); print("\n".join(lines[:14]))
