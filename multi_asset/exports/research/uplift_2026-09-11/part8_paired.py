#!/usr/bin/env python3
"""Part 8: PAIRED test of the smoothing counterfactual (per-anchor difference + CI), plus a
placebo that checks the recovery machinery cannot manufacture an effect out of noise."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])
COST=3.870

def build_leg(S, anchors):
    A=[a for a in anchors if (a-14400) in S]; T=len(A)
    EX=np.full((T,NW),np.nan); HH=np.zeros((T,NW)); SS=np.zeros((T,NW))
    for i,a in enumerate(A):
        H=S[a-14400]; sm=S[a]; HH[i]=H; SS[i]=sm; d=sm-H
        forced=(sm==0.0)&(np.abs(H)>1e-12); moved=(np.abs(d)>1e-12)&(~forced)
        EX[i,moved]=H[moved]+d[moved]/ALPHA; EX[i,forced]=0.0
    return A,EX,HH,SS
def fill_interp(EX):
    T,N=EX.shape; out=EX.copy(); idx=np.arange(T)
    for j in range(N):
        c=EX[:,j]; k=np.isfinite(c)
        if k.sum()==0: out[:,j]=0.0
        elif k.sum()==1: out[:,j]=c[k][0]
        else: out[:,j]=np.interp(idx,idx[k],c[k])
    return out
def renorm(TG,HH):
    out=TG.copy()
    for i in range(out.shape[0]):
        act=(np.abs(out[i])>1e-12)|(np.abs(HH[i])>1e-12)
        if act.sum()==0: continue
        v=out[i].copy(); v[act]-=v[act].mean(); g=np.abs(v).sum()
        if g>1e-12: v/=g
        out[i]=v
    return out

AK,EXK,HHK,SSK=build_leg(SKC,sorted(SKC)); AF,EXF,HHF,SSF=build_leg(SFC,sorted(SFC))
keep=[i for i,a in enumerate(AK) if y4_of(a) is not None]
A=[AK[i] for i in keep]
EXK,HHK,SSK=EXK[keep],HHK[keep],SSK[keep]; EXF,HHF,SSF=EXF[keep],HHF[keep],SSF[keep]
FK=(SSK==0.0)&(np.abs(HHK)>1e-12); FF=(SSF==0.0)&(np.abs(HHF)>1e-12)
E={"E1":(renorm(np.where(np.isfinite(EXK),EXK,HHK),HHK), renorm(np.where(np.isfinite(EXF),EXF,HHF),HHF)),
   "E2":(renorm(fill_interp(EXK),HHK), renorm(fill_interp(EXF),HHF))}
Y=[np.nan_to_num(y4_of(a),nan=0.0) for a in A]
Yp=[y.copy() for y in Y]

def run(TK,TF,alpha,band,YY):
    Hk=HHK[0].copy(); Hf=HHF[0].copy(); b=[]; t=[]
    for i in range(len(A)):
        nk=Hk+alpha*(TK[i]-Hk); tk=nk-Hk; nk=np.where(np.abs(tk)<band,Hk,nk); nk=np.where(FK[i],0.0,nk)
        nf=Hf+alpha*(TF[i]-Hf); tf=nf-Hf; nf=np.where(np.abs(tf)<band,Hf,nf); nf=np.where(FF[i],0.0,nf)
        rp=0.55*Hk+0.45*Hf; r=0.55*nk+0.45*nf
        g=np.abs(r).sum(); gp=np.abs(rp).sum()
        w=r/g if g>1e-12 else r; wp=rp/gp if gp>1e-12 else rp
        b.append(float((w*YY[i]).sum()*1e4)); t.append(float(np.abs(w-wp).sum()))
        Hk,Hf=nk,nf
    return np.array(b),np.array(t)

print("[PAIRED SMOOTHING COUNTERFACTUAL] deployed (a=0.10, band=2.5e-4) vs faster arms.")
print("  net = gross - 3.870*turnover ; unit-gross bps/anchor ; n=93 anchors (08-26..09-11)")
print(f"  {'estimator / arm':<30s}{'d_gross':>9s}{'d_cost':>8s}{'d_net':>9s}{'se':>7s}{'t':>6s}{'d_turn':>8s}")
res={}
for est in ("E1","E2"):
    TK,TF=E[est]
    b0,t0=run(TK,TF,ALPHA,BAND,Y)
    n0=b0-COST*t0
    for alpha,band,lab in ((0.2,BAND,"a=.20 keep band"),(0.1,0.0,"a=.10 band=0"),(0.2,0.0,"a=.20 band=0"),
                           (0.35,0.0,"a=.35 band=0"),(0.5,0.0,"a=.50 band=0"),(1.0,0.0,"a=1.0 band=0 (no smooth)")):
        b,t=run(TK,TF,alpha,band,Y); n=b-COST*t; d=n-n0
        se=d.std(ddof=1)/np.sqrt(len(d))
        print(f"  [{est}] {lab:<24s}{(b-b0).mean():>9.3f}{(COST*(t-t0)).mean():>8.3f}{d.mean():>9.3f}{se:>7.3f}{d.mean()/se:>6.2f}{(t-t0).mean():>8.4f}")
        res[f"{est}|{lab}"]=dict(d_net=float(d.mean()),se=float(se),t=float(d.mean()/se),d_turn=float((t-t0).mean()))

print("\n[PLACEBO] same machinery, y4 randomly permuted across anchors (200 draws). If the recovery")
print("  machinery itself creates an edge for faster alpha, the placebo mean will not be 0.")
rng=np.random.default_rng(7)
for est in ("E1","E2"):
    TK,TF=E[est]
    ds=[]
    for _ in range(200):
        p=rng.permutation(len(A)); YY=[Y[j] for j in p]
        b0,t0=run(TK,TF,ALPHA,BAND,YY); b,t=run(TK,TF,0.5,0.0,YY)
        ds.append(((b-COST*t)-(b0-COST*t0)).mean())
    ds=np.array(ds)
    print(f"  [{est}] placebo d_net(a=.50 band=0 - deployed): mean {ds.mean():+.4f} sd {ds.std(ddof=1):.4f}  "
          f"real value's percentile vs placebo = {100*(ds<res[f'{est}|a=.50 band=0']['d_net']).mean():.1f}%")
json.dump(res,open(f"{OUT}/paired_smoothing.json","w"),indent=1)
