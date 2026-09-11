"""R3-CRITICAL-1 step B3: the density-shape sensitivity, which is the ONE modelling choice in the walk.

UNIF assumed uniform depth density inside the innermost published band [0,0.2%]. The data say the book
is NOT uniform: turnover-weighted 5*A02/A1 = 0.697, i.e. A02 = 0.139*A1, so density BETWEEN 0.2% and 1%
is 1/0.648 = 1.54x the density inside 0.2%. Extrapolating that shape INWARD makes the touch thinner and
the walk more expensive. POWER fits A(x) = A02*(x/0.2)^p per (anchor,name) through the two published
points (0.2%,A02) and (1%,A1): p = ln(A1/A02)/ln(5); x* = 0.2*(Q/A02)^(1/p); VWAP = (p/(p+1))*x*.
Note p is also the impact exponent: impact ~ Q^(1/p).  Both calibers reported with day-block CIs.
"""
import numpy as np, json, time
R3="/workspace/uplift_2026-09-11/r3k"
LC=np.load(R3+"/lobcube.npz",allow_pickle=True); cum=LC["cum"]; lts=LC["ts"].astype(np.int64)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); QV=np.expm1(np.clip(MT["qvk"],0,30))*48.0
Z=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
W=np.asarray(Z["d30_n2_c42_W"],float); cols=[str(c) for c in Z["cols"]]
rec=np.asarray(Z["d30_n2_c42_rec"],float); rts=rec[:,cols.index("ts")].astype(np.int64)
emap={int(t):i for i,t in enumerate(E)}; ridx=np.array([emap[int(t)] for t in rts])
lmap={int(t):i for i,t in enumerate(lts)}; lidx=np.array([lmap.get(int(t),-1) for t in rts])
QVr=QV[ridx]; dWs=np.diff(W,axis=0,prepend=np.zeros((1,W.shape[1]))); dW=np.abs(dWs)
TT=np.full(QVr.shape,2,np.int8); TT[QVr>=1e6]=1; TT[QVr>=5e6]=0
HALF=np.array([1.0999658777781905,1.638999737554008,2.4344380023739175])
IMP_K1=np.array([0.638144642177287,1.557767793871295,4.5250173304217896])
XF=np.array([0.0,0.2,1.0,2.0,3.0,4.0,5.0]); ASK=[6,7,8,9,10,11]; BID=[5,4,3,2,1,0]
def walk_unif(Q,C):
    acc=np.zeros(len(Q)); rem=Q.copy(); prev=np.zeros(len(Q))
    for j in range(C.shape[1]):
        seg=np.maximum(C[:,j]-prev,0.0); take=np.minimum(rem,seg)
        dens=np.where(seg>0,seg/(XF[j+1]-XF[j]),np.inf)
        xe=np.where(np.isfinite(dens)&(dens>0),XF[j]+take/np.maximum(dens,1e-300),XF[j])
        acc+=take*(XF[j]+xe)/2.0; rem-=take; prev=C[:,j]
    acc=acc+np.where(rem>1e-9,rem*XF[-1],0.0)
    return acc/np.maximum(Q,1e-12)*100.0
def walk_power(Q,C):
    A02=C[:,0]; A1=C[:,1]
    p=np.log(np.maximum(A1/np.maximum(A02,1e-12),1.0001))/np.log(5.0)
    p=np.clip(p,0.3,6.0)
    inside=Q<=A02
    xs=0.2*np.power(np.clip(Q/np.maximum(A02,1e-12),0,None),1.0/p)
    v_in=(p/(p+1.0))*xs*100.0
    v_un=walk_unif(Q,C)
    # outside the inner band fall back to the piecewise-uniform walk (2% of turnover)
    return np.where(inside,v_in,v_un), p
yr=np.array([time.gmtime(int(t)).tm_year for t in rts]); m26=(yr==2026)
rows=np.where(m26&(lidx>=0))[0]
def build(G):
    O={k:[] for k in ("vu","vp","p","tier","dw","row","z","part")}
    for i in rows:
        d=dW[i]; s=dWs[i]; m=(d>1e-12)&np.isfinite(QVr[i])&(QVr[i]>0)
        if not m.any(): continue
        book=cum[lidx[i]]; sel=np.where(m)[0]; buy=s[sel]>0
        Cb=np.where(buy[:,None],book[sel][:,ASK],book[sel][:,BID]).astype(np.float64)
        good=np.isfinite(Cb).all(1)&(Cb[:,0]>0)&(Cb[:,1]>Cb[:,0])
        if not good.any(): continue
        sel=sel[good]; Cb=Cb[good]; Q=d[sel]*G
        vu=walk_unif(Q,Cb); vp,pp=walk_power(Q,Cb)
        O["vu"].append(vu); O["vp"].append(vp); O["p"].append(pp); O["tier"].append(TT[i][sel])
        O["dw"].append(d[sel]); O["row"].append(np.full(len(sel),i)); O["z"].append(Q/Cb[:,0])
        O["part"].append(Q/QVr[i][sel])
    return {k:np.concatenate(v) for k,v in O.items()}
def agg(B,key):
    w=B["dw"]; v=B[key]
    vw=float((v*w).sum()/w.sum()); ex=float((np.maximum(v-HALF[B["tier"]],0)*w).sum()/w.sum())
    ia=float((IMP_K1[B["tier"]]*w).sum()/w.sum())
    per={}
    for t in range(3):
        m=B["tier"]==t; ww=w[m]
        per["tier%d"%t]=dict(vwap=round(float((v[m]*ww).sum()/ww.sum()),5),
            excess=round(float((np.maximum(v[m]-HALF[t],0)*ww).sum()/ww.sum()),5),
            K_vwap=round(float((v[m]*ww).sum()/ww.sum()/IMP_K1[t]),4),
            K_excess=round(float((np.maximum(v[m]-HALF[t],0)*ww).sum()/ww.sum()/IMP_K1[t]),4))
    return dict(book_vwap_bps=round(vw,5),book_excess_bps=round(ex,5),infra1_K1=round(ia,4),
                K_vwap=round(vw/ia,4),K_excess=round(ex/ia,4),per_tier=per)
def ci(B,key,which):
    w=B["dw"]; v=B[key]; day=(rts[B["row"]]//86400).astype(np.int64)
    ud,inv=np.unique(day,return_inverse=True); idx=[np.where(inv==i)[0] for i in range(len(ud))]
    rng=np.random.default_rng([20260905,31]); out=[]
    for _ in range(2000):
        pick=rng.integers(0,len(ud),len(ud)); ix=np.concatenate([idx[i] for i in pick])
        ww=w[ix]; vv=v[ix]; tt=B["tier"][ix]
        num=float(((vv if which=="vwap" else np.maximum(vv-HALF[tt],0))*ww).sum()/ww.sum())
        den=float((IMP_K1[tt]*ww).sum()/ww.sum()); out.append(num/den)
    return [round(float(np.percentile(out,2.5)),4),round(float(np.percentile(out,97.5)),4)],round(float(np.std(out)),4)
B=build(230000.0)
RES={"n_trades":int(len(B["dw"])),"n_anchors":int(len(np.unique(B["row"]))),
     "p_exponent_turnwtd":round(float((B["p"]*B["dw"]).sum()/B["dw"].sum()),4),
     "p_exponent_median":round(float(np.median(B["p"])),4),
     "implied_impact_exponent_alpha_1_over_p":round(float(1.0/((B["p"]*B["dw"]).sum()/B["dw"].sum())),4),
     "turnwtd_z":round(float((B["z"]*B["dw"]).sum()/B["dw"].sum()),5)}
for key,lab in (("vu","UNIF"),("vp","POWER")):
    a=agg(B,key)
    for which in ("vwap","excess"):
        c,s=ci(B,key,which); a["K_%s_CI95"%which]=c; a["K_%s_bootsd"%which]=s
    RES[lab]=a
    print(lab,json.dumps(a,indent=1),flush=True)
# G ladder under POWER, per tier (for the capacity cost models)
LAD=[230000.,345000.,460000.,690000.,920000.,1380000.,2300000.,4600000.,9200000.,23000000.]
import copy
A1D="/workspace/uplift_2026-09-11/infra1_cost"
S=json.load(open(A1D+"/tier_stats.json"))["all"]
fee_mk=[d["mk_fee_bps"] for d in S]; fee_tk=[d["tk_fee_bps"] for d in S]
spread=[d["spread_bps"] for d in S]; mshare=[d["mk_nz"]/(d["mk_nz"]+d["tk_nz"]) for d in S]
RP=json.load(open(A1D+"/replay_participation.json")); tsh=[RP[str(t)]["turnover_share"] for t in range(3)]
LADOUT={}
for G in LAD:
    BB=build(G); a=agg(BB,"vp")
    I=[a["per_tier"]["tier%d"%t]["excess"] for t in range(3)]
    tiers=[];bl=[]
    for t in range(3):
        m=fee_mk[t]+I[t]; k=fee_tk[t]+spread[t]/2.0+I[t]; f=mshare[t]
        tiers.append({"name":["tier0_qv4h>=5e6","tier1_qv4h>=1e6","tier2_rest"][t],
                      "maker_bps":round(m,6),"taker_bps":round(k,6),"maker_share":round(f,6)})
        bl.append(f*m+(1-f)*k)
    avg=sum(b*s for b,s in zip(bl,tsh))
    json.dump(dict(tiers=tiers,model="POWER-shape book-walk impact, excess of half-spread, G=$%.0f"%G,
        impact_bps_by_tier=[round(x,6) for x in I],blended_bps_per_unit_turnover=[round(b,4) for b in bl],
        book_avg_bps_per_unit_turnover=round(avg,4),turnover_share_by_tier=[round(s,4) for s in tsh],
        calibration=dict(source="r3k_fitK3.py POWER caliber, LOB 0.2%/1% bands, 2026 anchors",
            gross_usdt=G,note="A(x)=A02*(x/0.2)^p fitted per (anchor,name) through the two published bands")),
        open(R3+"/costb_PWR_G%dk.json"%int(G/1000),"w"),indent=1)
    LADOUT["%d"%int(G)]=dict(I=[round(x,5) for x in I],book_avg=round(avg,4),
        vwap=a["book_vwap_bps"],excess=a["book_excess_bps"])
    print("G=%9.0f POWER I %s book_avg_cost %.4f"%(G,[round(x,4) for x in I],avg),flush=True)
RES["G_ladder_POWER"]=LADOUT
json.dump(RES,open(R3+"/FITK_v3_shape.json","w"),indent=1)
print("WROTE",R3+"/FITK_v3_shape.json")
