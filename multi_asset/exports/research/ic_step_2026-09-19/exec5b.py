# -*- coding: utf-8 -*-
"""00Z 2026-09-19 anchor, section (5), CORRECTED.
E-0919-D discipline: every table states its counting unit.
LED-01 discipline: fills are COLLAPSED on (symbol, trade_id) — amount once, markout from whichever row has it.
No orders<->fills join is used: attempt_idx means different things in the two files
(orders {1,2} = quote attempt; fills {1,2,3} = venue attempt, every topup_taker fill is 3)."""
import json, collections, statistics
L = "/Users/haosiyu/dl_quant_live/state/live/pilot_log/20260919"
A = 1789777442.671038
O = [r for r in (json.loads(l) for l in open(f"{L}/orders.jsonl") if l.strip()) if r["anchor_ts"] == A]
Fraw = [r for r in (json.loads(l) for l in open(f"{L}/fills.jsonl") if l.strip()) if r["anchor_ts"] == A]

# --- collapse: 走规范访问器(单一实现, 带对执行器的漂移守卫) ---
import sys as _sys; _sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/pilot_journal/tools")
from fills_reader import collapse_supersedes
F = collapse_supersedes(Fraw)
gf = sum(abs(f["fill_notional"]) for f in F); go = sum(abs(r.get("filled_notional") or 0) for r in O)
print(f"坍缩对账: 原始行 {len(Fraw)} -> 唯一成交 {len(F)}; 名义 {gf:,.2f} vs orders.filled_notional {go:,.2f}; 差 {gf-go:+.2f}")
assert abs(gf-go) < 0.01, "坍缩后与订单账不符, 不出数"
print(f"单位: 【订单行】{len(O)}  ·  【唯一成交】{len(F)}  ·  【名】{len({r['symbol'] for r in O})}")
print()

# ---------- (a) order-level size gradient, unit = ORDER ROW, order-row fields only ----------
sub = [r for r in O if r.get("price_submit") is not None]
skip = [r for r in O if r.get("price_submit") is None]
print(f"(a) 规模梯度  unit=【订单行】")
print(f"    489 行中 {len(sub)} 行真的挂出去了(price_submit 非空), {len(skip)} 行从未挂出")
print(f"    未挂出的终态: {dict(collections.Counter(r.get('terminal_reason') for r in skip))}")
for r in sub: r["_a"] = abs(r["intended_notional"]); r["_f"] = abs(r.get("filled_notional") or 0.0)
rows = sorted(sub, key=lambda r: r["_a"]); n = len(rows)
cuts = [rows[n//3]["_a"], rows[2*n//3]["_a"]]
B = {0:[],1:[],2:[]}
for r in rows: B[0 if r["_a"]<cuts[0] else (1 if r["_a"]<cuts[1] else 2)].append(r)
print(f"    三等分切点: {cuts[0]:.1f} / {cuts[1]:.1f} USDT  (仅在已挂出的 {n} 行上分)")
hdr=f"{'桶':<5}{'n单':>5}{'中位名义':>10}{'意图和':>10}{'成交和':>10}{'成交率':>8}{'挂单价差bps':>12}{'滑点bps中位':>12}{'n滑点':>7}{'全额成交':>9}"
print(hdr)
def slip(r):
    m=r.get("mid_at_submit"); p=r.get("avg_fill_px")
    if not m or not p or r["_f"]<=0: return None
    return (-1.0 if r["side"]=="buy" else 1.0)*(p-m)/m*1e4
for b in (0,1,2):
    rs=B[b]; ti=sum(r["_a"] for r in rs); tf=sum(r["_f"] for r in rs)
    sp=[r["spread_at_submit_bps"] for r in rs if r.get("spread_at_submit_bps") is not None]
    sl=[x for x in (slip(r) for r in rs) if x is not None]
    fullf=sum(1 for r in rs if r.get("terminal_reason")=="filled")
    print(f"{['小','中','大'][b]:<5}{len(rs):>5}{statistics.median(r['_a'] for r in rs):>10.1f}{ti:>10.0f}{tf:>10.0f}{tf/ti*100:>7.1f}%{(statistics.median(sp) if sp else float('nan')):>12.2f}{(statistics.median(sl) if sl else float('nan')):>12.2f}{len(sl):>7}{fullf:>9}")
ti=sum(r["_a"] for r in rows); tf=sum(r["_f"] for r in rows)
sp=[r["spread_at_submit_bps"] for r in rows if r.get("spread_at_submit_bps") is not None]
sl=[x for x in (slip(r) for r in rows) if x is not None]
print(f"{'已挂':<5}{len(rows):>5}{statistics.median(r['_a'] for r in rows):>10.1f}{ti:>10.0f}{tf:>10.0f}{tf/ti*100:>7.1f}%{statistics.median(sp):>12.2f}{statistics.median(sl):>12.2f}{len(sl):>7}{sum(1 for r in rows if r.get('terminal_reason')=='filled'):>9}")
print(f"    ★ 滑点符号: 正 = 成交价优于挂单时中价。加权(按成交名义): {sum(slip(r)*r['_f'] for r in rows if slip(r) is not None)/sum(r['_f'] for r in rows if slip(r) is not None):+.2f} bps")
print()

# ---------- (b) markout backfill, unit = COLLAPSED FILL ----------
have=[f for f in F if f.get("mid_at_fill_plus_60s") is not None]; pend=[f for f in F if f.get("mid_at_fill_plus_60s") is None]
print(f"(b) markout 回填  unit=【唯一成交】")
print(f"    已回填 {len(have)}/{len(F)} = {len(have)/len(F)*100:.1f}%;  待回填 {len(pend)}")
print(f"    mark_source: {dict(collections.Counter(f.get('mark_source') for f in have))}")
print(f"    mark_window_s: {dict(collections.Counter(f.get('mark_window_s') for f in have))}  · mark_lag_s 中位 {statistics.median(f['mark_lag_s'] for f in have):.0f}s (max {max(f['mark_lag_s'] for f in have):.0f}s)")
ht=[f["fill_ts"]-A for f in have]; pt=[f["fill_ts"]-A for f in pend]
print(f"    ★选择性检验 — 成交时刻(相对执行器锚): 已回填 [{min(ht):+.0f}s, {max(ht):+.0f}s] 中位 {statistics.median(ht):+.0f}s")
print(f"                                          待回填 [{min(pt):+.0f}s, {max(pt):+.0f}s] 中位 {statistics.median(pt):+.0f}s")
print(f"    待回填的名: {sorted({f['symbol'] for f in pend})}")
print(f"    待回填 maker 占比 {sum(1 for f in pend if f.get('venue_maker_flag') is True)}/{len(pend)}; 名义 {sum(abs(f['fill_notional']) for f in pend):,.0f} USDT ({sum(abs(f['fill_notional']) for f in pend)/gf*100:.1f}% of gross)")
print()

# ---------- (c) markout, unit = COLLAPSED FILL ----------
def mo(f):
    m=f.get("mid_at_fill_plus_60s"); p=f.get("fill_px")
    if not m or not p: return None
    return (1.0 if f["side"]=="buy" else -1.0)*(m-p)/p*1e4
print("(c) markout(+60s; 正 = 成交后价格朝我们有利方向走 ⇒ 我们没被逆选)  unit=【唯一成交】")
print(f"{'分组':<16}{'n':>5}{'名义USDT':>11}{'名义加权':>10}{'中位':>8}{'>0':>6}{'=0':>6}{'<0':>6}")
def show(lab, rs):
    v=[(mo(f),abs(f["fill_notional"])) for f in rs]; v=[(a,b) for a,b in v if a is not None]
    if not v: print(f"{lab:<16}{0:>5}"); return
    w=sum(b for _,b in v)
    print(f"{lab:<16}{len(v):>5}{w:>11.0f}{sum(a*b for a,b in v)/w:>10.2f}{statistics.median(a for a,_ in v):>8.2f}"
          f"{sum(1 for a,_ in v if a>1e-9):>6}{sum(1 for a,_ in v if abs(a)<=1e-9):>6}{sum(1 for a,_ in v if a<-1e-9):>6}")
show("全部已回填", have)
show("  maker", [f for f in have if f.get("venue_maker_flag") is True])
show("  taker", [f for f in have if f.get("venue_maker_flag") is not True])
fs=sorted(have, key=lambda f: abs(f["fill_notional"])); m=len(fs)
for i,lab in enumerate(("小成交","中成交","大成交")):
    show("  "+lab, fs[i*m//3:(i+1)*m//3])
print()
print("(d) 单笔 markout 的集中度(名义加权贡献前 5 名 / 后 5 名)  unit=【唯一成交】")
c=sorted(((mo(f)*abs(f["fill_notional"]), f) for f in have if mo(f) is not None), key=lambda x:-x[0])
tot=sum(x for x,_ in c)
print(f"    合计贡献 {tot:,.0f} bps·USDT ⇒ 名义加权 {tot/sum(abs(f['fill_notional']) for f in have):+.2f} bps")
for x,f in c[:5]: print(f"      +{x:>9,.0f}  {f['symbol']:<12} {abs(f['fill_notional']):>8.1f} USDT  markout {mo(f):+8.1f} bps  maker={f.get('venue_maker_flag')}")
for x,f in c[-5:]: print(f"      {x:>10,.0f}  {f['symbol']:<12} {abs(f['fill_notional']):>8.1f} USDT  markout {mo(f):+8.1f} bps  maker={f.get('venue_maker_flag')}")
top5=sum(x for x,_ in c[:5])
print(f"    ★ 前 5 笔占 markout 总贡献的 {top5/tot*100:.0f}%")
print()
print("(e) 汇总  unit 标注齐全")
mk_n=sum(1 for f in F if f.get("venue_maker_flag") is True); mk_w=sum(abs(f["fill_notional"]) for f in F if f.get("venue_maker_flag") is True)
print(f"    maker 份额: 笔数 {mk_n}/{len(F)} = {mk_n/len(F)*100:.1f}%   ·   名义 {mk_w:,.0f}/{gf:,.0f} = {mk_w/gf*100:.1f}%")
print(f"    本锚成交 gross = {gf:,.0f} USDT (唯一成交口径, 与 orders 逐分对上)")
cu=sum(f["commission"] for f in F if f["commission_asset"]=="USDT")
print(f"    佣金 {cu:.4f} USDT = {cu/gf*1e4:.3f} bps; 佣金币种 {dict(collections.Counter(f['commission_asset'] for f in F))}")
print(f"    终态  unit=【订单行】: {dict(collections.Counter(r.get('terminal_reason') for r in O).most_common())}")
