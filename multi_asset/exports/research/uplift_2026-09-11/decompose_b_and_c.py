#!/usr/bin/env python3
import json, glob, os, time
import numpy as np
WS="/Users/haosiyu/wide_shadow"; PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
cfg=json.load(open(f"{WS}/shadow_bundle/config.json")); SYMS=cfg["symbols_panel"]; NW=len(SYMS)
IDX={s:j for j,s in enumerate(SYMS)}
R=np.load(f"{WS}/state/rolling.npz",allow_pickle=True); rts=R["ts"].astype(np.int64); RD=R["data"]
row_of={int(t):i for i,t in enumerate(rts)}
aux=json.load(open(f"{WS}/state/aux.json")); LEDG=aux["ledger_tail"]
def y4(A):
    pi=row_of.get(int(A)); ai=row_of.get(int(A)+14400)
    if pi is None or ai is None: return None
    seg=RD[pi+1:ai+1,:,0].astype(np.float32); fin=np.isfinite(seg)
    v=np.where(fin,seg,0).sum(0).astype(np.float64); v[fin.sum(0)<46]=np.nan; return v
def fund_at(A):
    """Replicate shadow_loop_v3 L405-411: latest ledger row with ft<=A and A-ft<=12h -> (rate, iv)."""
    fn=np.full(NW,np.nan); iv=np.full(NW,np.nan)
    for s,rowsx in LEDG.items():
        j=IDX.get(s)
        if j is None or not rowsx: continue
        last=None
        for r in rowsx:
            if r[0]<=A: last=r
            else: break
        if last is None: continue
        if A-last[0]<=12*3600: fn[j]=last[1]; iv[j]=last[2]
    return fn,iv
pos={}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l); pos.setdefault(float(r["anchor_ts"]),{})[r["symbol"]]=float(r.get("venue_position_notional") or 0.0)
LIVE={r["grid_anchor"]:r for r in json.load(open(f"{OUT}/live_anchor_table.json"))}
P={r["anchor"]:r for r in json.load(open(f"{OUT}/recon_anchor_table.json"))}
out=[]
for ets,book in sorted(pos.items()):
    A=int(ets//14400*14400)
    if A<1787716800: continue
    yv=y4(A); tp=f"{WS}/state/target_live/{A}.json"
    if yv is None or not os.path.exists(tp) or A not in P: continue
    g=sum(abs(v) for v in book.values())
    if g<=0: continue
    wa=np.zeros(NW)
    for s,nt in book.items():
        j=IDX.get(s)
        if j is not None: wa[j]+=nt/g
    dtl=json.load(open(tp)); wd=np.zeros(NW)
    for s,v in dtl["weights"].items():
        j=IDX.get(s)
        if j is not None: wd[j]=float(v)
    gd=np.abs(wd).sum(); wdn=wd/gd if gd else wd
    wk=np.zeros(NW); wp=f"{WS}/state/weights/{A}.npz"
    if os.path.exists(wp):
        z=np.load(wp); wk[z["idx"].astype(np.int64)]=z["val"].astype(np.float64)
    gk=np.abs(wk).sum(); wkn=wk/gk if gk else wk
    ok=np.isfinite(yv)
    univ=(np.abs(wdn)>1e-12)|(np.abs(wa)>1e-12)
    ybar=float(np.nanmean(yv[univ & ok])) if (univ&ok).sum() else 0.0
    ycl=np.nan_to_num(yv)
    net_d=float(wdn.sum()); net_a=float(wa.sum())
    fn,iv=fund_at(A)
    ivv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); fnv=np.nan_to_num(fn)
    carry=lambda w: float((w*fnv*(4.0/ivv)).sum()*1e4)
    out.append({"A":A,"utc":time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(A)),"gross_usdt":g,
      "ybar_bps":ybar*1e4,
      "p_king":float((wkn*ycl).sum()*1e4),"p_target":float((wdn*ycl).sum()*1e4),"p_actual":float((wa*ycl).sum()*1e4),
      "net_d":net_d,"net_a":net_a,"net_k":float(wkn.sum()),
      "b_net_part":(net_a-net_d)*ybar*1e4,
      "carry_king_logged_per_unit":P[A]["carry"]/gk if gk else None,
      "carry_king_recomp":carry(wkn),"carry_target_recomp":carry(wdn),"carry_actual_recomp":carry(wa),
      "live_price_bps":LIVE.get(A,{}).get("price_bps_of_gross"),
      "live_fund_bps":LIVE.get(A,{}).get("funding_bps_of_gross")})
json.dump(out,open(f"{OUT}/decomp_table.json","w"),indent=1)
def a(k):
    v=[x[k] for x in out if x.get(k) is not None]; return np.array(v,float)
def rep(k):
    v=a(k); t=v.mean()/(v.std(ddof=1)/np.sqrt(len(v))) if len(v)>1 else float('nan')
    print(f"  {k:28s} mean {v.mean():9.4f} sd {v.std(ddof=1):8.4f} t {t:7.2f} n {len(v)}")
print("n anchors:",len(out))
for k in ("ybar_bps","p_king","p_target","p_actual","net_d","net_a","net_k","b_net_part",
          "carry_king_logged_per_unit","carry_king_recomp","carry_target_recomp","carry_actual_recomp",
          "live_price_bps","live_fund_bps"): rep(k)
pa=a("p_actual"); lp=np.array([x["live_price_bps"] for x in out if x["live_price_bps"] is not None])
pa2=np.array([x["p_actual"] for x in out if x["live_price_bps"] is not None])
print(f"\n  corr(paper_on_actual, live_price_venue) = {np.corrcoef(pa2,lp)[0,1]:.4f}")
d=lp-pa2; print(f"  live_price - paper_on_actual: mean {d.mean():+.4f} sd {d.std(ddof=1):.4f} t {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):.2f}")
dd=a("p_actual")-a("p_target"); print(f"  (b) actual-target: mean {dd.mean():+.4f} sd {dd.std(ddof=1):.4f} t {dd.mean()/(dd.std(ddof=1)/np.sqrt(len(dd))):.2f}")
bn=a("b_net_part"); print(f"      of which net-tilt part: mean {bn.mean():+.4f}  idio part: {dd.mean()-bn.mean():+.4f}")
ck=a("carry_king_recomp"); cl=a("carry_king_logged_per_unit")
print(f"\n  carry recompute check (king): mean recomp {ck.mean():.4f} vs logged/gn {cl.mean():.4f} maxdiff {np.abs(ck-cl).max():.4f}")
lf=np.array([x["live_fund_bps"] for x in out if x["live_fund_bps"] is not None])
ca=np.array([x["carry_actual_recomp"] for x in out if x["live_fund_bps"] is not None])
ct=np.array([x["carry_target_recomp"] for x in out if x["live_fund_bps"] is not None])
print(f"  model carry on ACTUAL book {ca.mean():.4f} vs venue funding charged {-lf.mean():.4f}  -> over-charge {ca.mean()+lf.mean():+.4f}")
print(f"  model carry on TARGET book {ct.mean():.4f}")
