#!/usr/bin/env python3
"""TRACK B step 1: true realized cost per anchor from live ledgers. READ-ONLY."""
import json,os,glob,math,sys
from collections import defaultdict
import numpy as np

LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
days=sorted(os.listdir(LOG))
days=[d for d in days if d.isdigit()]

# ---------- anchors ----------
anch={}   # anchor_ts -> dict
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        try: r=json.loads(ln)
        except: continue
        ts=r.get("anchor_ts")
        if ts is None: continue
        mid=r.get("mid_at_anchor_vector")
        if isinstance(mid,str):
            try: mid=json.loads(mid)
            except: mid={}
        anch[ts]={"day":d,"realized_gross":r.get("realized_gross"),"target_gross":r.get("target_gross"),
                  "regime":r.get("regime_at_anchor"),"mid":mid or {},"hash":r.get("target_vector_hash"),
                  "n_skip":r.get("n_names_skipped")}
print("anchors:",len(anch), "range", min(anch), max(anch))

# ---------- fills, deduped ----------
raw=0
seen=set()
fills=[]
dupe_notional=0.0
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        try: r=json.loads(ln)
        except: continue
        raw+=1
        k=(r.get("symbol"),r.get("trade_id"))
        if k in seen:
            dupe_notional+=abs(r.get("fill_notional") or 0.0); continue
        seen.add(k); fills.append(r)
print(f"fills raw={raw} deduped={len(fills)} dropped={raw-len(fills)} dropped_notional={dupe_notional:,.0f}")

# also dedupe key sensitivity: trade_id alone
tid=set(f.get("trade_id") for f in fills)
print("unique trade_id alone (post symbol+tid dedupe):",len(tid))

# ---------- BNB price per anchor for commission conversion ----------
def bnb_px(ts):
    a=anch.get(ts)
    if a and a["mid"].get("BNBUSDT"): return a["mid"]["BNBUSDT"]
    # nearest anchor with a BNB mid
    best=None
    for t,aa in anch.items():
        if aa["mid"].get("BNBUSDT"):
            if best is None or abs(t-ts)<abs(best-ts): best=t
    return anch[best]["mid"]["BNBUSDT"] if best else None

# per-anchor aggregation
A=defaultdict(lambda: dict(traded=0.0, maker_n=0.0, taker_n=0.0, fee_usdt=0.0, fee_bnb=0.0,
                           fee_other=defaultdict(float), n=0,
                           slip_num=0.0, slip_den=0.0,       # notional-weighted slippage vs anchor mid
                           mk_slip_num=0.0, mk_slip_den=0.0,
                           tk_slip_num=0.0, tk_slip_den=0.0,
                           mo_num=0.0, mo_den=0.0))          # markout mid@+60s vs fill px
missing_mid=0; missing_mo=0
for f in fills:
    ts=f.get("anchor_ts"); sym=f.get("symbol")
    a=anch.get(ts)
    n=abs(f.get("fill_notional") or 0.0)
    side=f.get("side"); sgn=1.0 if side=="buy" else -1.0
    px=f.get("fill_px")
    ot=f.get("order_type"); mk = (ot=="maker") or bool(f.get("venue_maker_flag"))
    r=A[ts]; r["n"]+=1; r["traded"]+=n
    if mk: r["maker_n"]+=n
    else:  r["taker_n"]+=n
    c=f.get("commission") or 0.0; ca=(f.get("commission_asset") or "USDT")
    if ca=="USDT": r["fee_usdt"]+=c
    elif ca=="BNB": r["fee_bnb"]+=c
    else: r["fee_other"][ca]+=c
    m0 = a["mid"].get(sym) if a else None
    if m0 and px:
        s=sgn*(px-m0)/m0*1e4     # bps, positive = we paid worse than anchor mid
        r["slip_num"]+=s*n; r["slip_den"]+=n
        if mk: r["mk_slip_num"]+=s*n; r["mk_slip_den"]+=n
        else:  r["tk_slip_num"]+=s*n; r["tk_slip_den"]+=n
    else: missing_mid+=1
    mo=f.get("mid_at_fill_plus_60s")
    if mo and px:
        # adverse selection cost: mid moved against us after the fill
        adv = -sgn*(mo-px)/px*1e4   # positive = mid moved against us => our fill was adversely selected
        r["mo_num"]+=adv*n; r["mo_den"]+=n
    else: missing_mo+=1
print("fills missing anchor mid:",missing_mid,"missing +60s markout:",missing_mo)

rows=[]
for ts in sorted(A):
    r=A[ts]; a=anch.get(ts)
    if a is None: continue
    G=a["realized_gross"] or a["target_gross"]
    if not G: continue
    bp=bnb_px(ts)
    fee_bnb_usdt = r["fee_bnb"]*bp if bp else 0.0
    fee_tot = r["fee_usdt"]+fee_bnb_usdt+sum(r["fee_other"].values())
    rows.append(dict(ts=ts, day=a["day"], gross=G, regime=a["regime"],
        traded=r["traded"], traded_pct=100*r["traded"]/G,
        maker_frac = r["maker_n"]/r["traded"] if r["traded"] else float('nan'),
        fee_usdt=fee_tot, fee_bps_gross=1e4*fee_tot/G,
        fee_bps_traded=1e4*fee_tot/r["traded"] if r["traded"] else float('nan'),
        fee_bnb_share = fee_bnb_usdt/fee_tot if fee_tot else 0.0,
        slip_bps_traded = r["slip_num"]/r["slip_den"] if r["slip_den"] else float('nan'),
        mk_slip = r["mk_slip_num"]/r["mk_slip_den"] if r["mk_slip_den"] else float('nan'),
        tk_slip = r["tk_slip_num"]/r["tk_slip_den"] if r["tk_slip_den"] else float('nan'),
        slip_cov = r["slip_den"]/r["traded"] if r["traded"] else 0.0,
        adv_bps_traded = r["mo_num"]/r["mo_den"] if r["mo_den"] else float('nan'),
        adv_cov = r["mo_den"]/r["traded"] if r["traded"] else 0.0,
        nfill=r["n"]))
import datetime as dt
for x in rows: x["iso"]=dt.datetime.utcfromtimestamp(x["ts"]).strftime("%Y-%m-%dT%H:%MZ")
json.dump(rows,open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/trackB_anchor_cost_rows.json","w"),indent=1)

def summ(sel,label):
    R=[x for x in rows if sel(x)]
    if not R: print(label,"EMPTY"); return
    n=len(R)
    def m(k,w=None):
        v=np.array([x[k] for x in R],float)
        ok=np.isfinite(v)
        if w:
            ww=np.array([x[w] for x in R],float)[ok]
            return float(np.sum(v[ok]*ww)/np.sum(ww))
        return float(np.nanmean(v[ok]))
    tr=np.array([x["traded"] for x in R]); gr=np.array([x["gross"] for x in R])
    print(f"\n=== {label}  n_anchors={n}")
    print(f"  traded/gross      {100*tr.sum()/gr.sum():8.3f}%  (per-anchor mean {m('traded_pct'):.3f}%)")
    print(f"  maker frac(notional-wtd) {m('maker_frac','traded'):8.4f}")
    print(f"  FEE   bps of gross {m('fee_bps_gross'):8.4f}   bps of traded {1e4*sum(x['fee_usdt'] for x in R)/tr.sum():8.4f}")
    print(f"        BNB share of fee {m('fee_bnb_share','fee_usdt'):6.3f}   total fee USDT {sum(x['fee_usdt'] for x in R):,.1f}")
    print(f"  SLIP vs anchor mid bps/traded  all {m('slip_bps_traded','traded'):8.4f}  maker {m('mk_slip','traded'):8.4f}  taker {m('tk_slip','traded'):8.4f}  cov {m('slip_cov','traded'):.3f}")
    print(f"  ADVSEL (mid@+60s vs fill) bps/traded {m('adv_bps_traded','traded'):8.4f}  cov {m('adv_cov','traded'):.3f}")
    allin_traded = 1e4*sum(x['fee_usdt'] for x in R)/tr.sum() + m('slip_bps_traded','traded')
    print(f"  ==> CASH all-in (fee+slip vs anchor mid) {allin_traded:8.4f} bps per unit traded")
    print(f"  ==> CASH all-in in bps of GROSS per anchor {allin_traded*(tr.sum()/gr.sum()):8.4f}")
summ(lambda x: True,"ALL (08-01 .. 09-11)")
summ(lambda x: x["ts"]>=1787716800,"COMBO era (>=2026-08-26T04:00Z)")
summ(lambda x: x["ts"]>=1788436800,"post-deposit (>=2026-09-03T12:00Z)")
