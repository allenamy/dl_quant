#!/usr/bin/env python3
import json, glob, os, collections
import numpy as np
import sys as _sys; _sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/pilot_journal/tools")
from fills_reader import collapse_supersedes as _collapse  # ★ LED-01: fills.jsonl 是追加式日志, 回填把同一笔再写一遍(全史 2.269 倍)。不坍缩 ⇒ 成交额/费用/笔数虚高 ~2.1 倍, 跨源比率(换手/费率对 gross)虚高 ~2.3 倍。
PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
# BNB mid per anchor from anchors.jsonl
bnb={}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l); mv=r.get("mid_at_anchor_vector")
        if isinstance(mv,str):
            try: mv=json.loads(mv)
            except Exception: mv={}
        if mv and "BNBUSDT" in mv: bnb[float(r["anchor_ts"])]=float(mv["BNBUSDT"])
bts=sorted(bnb)
def bnb_px(t):
    if not bts: return None
    i=min(range(len(bts)), key=lambda k: abs(bts[k]-t)); return bnb[bts[i]]
agg=collections.defaultdict(lambda: {"usdt":0.0,"bnb":0.0,"notional":0.0,"maker_n":0,"n":0})
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for r in _collapse([json.loads(l) for l in open(p) if l.strip()]):
        t=float(r.get("anchor_ts") or 0); A=int(t//14400*14400)
        a=agg[A]; c=float(r.get("commission") or 0.0)
        if r.get("commission_asset")=="BNB": a["bnb"]+=c
        else: a["usdt"]+=c
        a["notional"]+=abs(float(r.get("fill_notional") or 0.0)); a["n"]+=1
        a["maker_n"]+= 1 if r.get("venue_maker_flag") else 0
# ★ 独立复审 R2-5(2026-09-19): 上一版 gross 分母取自 live_anchor_table.json, 而该表
#   【有 gross 的锚止于 09-11 00Z】, 于是筛选后只剩 87 锚, 静默排除最近 8 天。
#   改为优先用实盘 anchors.jsonl 自己的 realized_gross(覆盖全锚), 表只作回退,
#   并把每个锚的 gross 来源写进产物 —— 口径来源必须可核, 不能靠记忆。
LIVE={r["grid_anchor"]:r for r in json.load(open(f"{OUT}/live_anchor_table.json"))}
GROSS_LIVE={}
for d in sorted(glob.glob(f"{PL}/2026*")):
    ap=f"{d}/anchors.jsonl"
    if not os.path.exists(ap): continue
    for l in open(ap, errors="ignore"):
        if not l.strip(): continue
        try: rr=json.loads(l)
        except Exception: continue
        g=rr.get("realized_gross")
        if g: GROSS_LIVE[int(float(rr["anchor_ts"])//14400*14400)]=float(g)
def gross_of(A):
    if A in GROSS_LIVE: return GROSS_LIVE[A], "anchors.jsonl:realized_gross"
    t=LIVE.get(A,{}).get("gross")
    return (t, "live_anchor_table.json(回退)") if t else (None, "UNAVAILABLE")
rows=[]
for A,a in sorted(agg.items()):
    px=bnb_px(A+1400) or 0.0
    fee=a["usdt"]+a["bnb"]*px
    g,gsrc=gross_of(A)
    rows.append({"A":A,"fee_usdt_total":fee,"fee_usdt_leg":a["usdt"],"fee_bnb_leg_usdt":a["bnb"]*px,
                 "bnb_px":px,"traded_notional":a["notional"],"n_fills":a["n"],"maker_frac":a["maker_n"]/max(a["n"],1),
                 "gross":g,"gross_source":gsrc,"fee_bps_of_gross": fee/g*1e4 if g else None,
                 "fee_bps_of_traded": fee/a["notional"]*1e4 if a["notional"] else None,
                 "turnover_frac": a["notional"]/g if g else None})
json.dump(rows,open(f"{OUT}/fee_table.json","w"),indent=1)
C=[r for r in rows if r["A"]>=1787716800 and r["gross"]]
def a_(k,s=C): return np.array([x[k] for x in s if x[k] is not None],float)
import collections as _c
print("combo era anchors with fees:",len(C), "| gross 来源:", dict(_c.Counter(x.get("gross_source") for x in C)))
for k in ("fee_bps_of_gross","fee_bps_of_traded","turnover_frac","maker_frac"):
    v=a_(k); print(f"  {k:20s} mean {v.mean():8.4f} sd {v.std(ddof=1):7.4f} n {len(v)}")
print(f"  combo era total fees USD: {sum(x['fee_usdt_total'] for x in C):.1f} (usdt-leg {sum(x['fee_usdt_leg'] for x in C):.1f}, bnb-leg {sum(x['fee_bnb_leg_usdt'] for x in C):.1f})")
print(f"  combo era traded notional: {sum(x['traded_notional'] for x in C):.0f}")
ALL=[r for r in rows if r["gross"]]
print(f"  whole period fees USD: {sum(x['fee_usdt_total'] for x in ALL):.1f}  traded {sum(x['traded_notional'] for x in ALL):.0f}")
