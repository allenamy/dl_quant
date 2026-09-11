"""R3-CRITICAL-1 step D: emit COSTB JSONs in the device schema at the FITTED impact, per tier,
and at a ladder of book gross levels (the capacity curve).

Same schema/blend as infra1_cost/mk_costb.py:
   maker_bps_t = fee_maker_t + I_t ; taker_bps_t = fee_taker_t + S_t/2 + I_t ; maker_share_t measured.
Only I_t changes: instead of K * sigma_4h * sqrt(participation) with K DECLARED-UNFITTED, I_t is the
MEASURED order-book walk cost of the book's own per-name trades at that gross:
   FIT  : I_t = turnover-weighted (VWAP_vs_mid - half_spread_t), floored at 0   [central]
   FITU : I_t = turnover-weighted  VWAP_vs_mid                                   [upper: charges the
          touch twice on the taker leg, and charges the maker leg a full crossing it never pays]
"""
import numpy as np, json, time, os
R3="/workspace/uplift_2026-09-11/r3k"; A1="/workspace/uplift_2026-09-11/infra1_cost"
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
S=json.load(open(A1+"/tier_stats.json"))["all"]
fee_mk=[d["mk_fee_bps"] for d in S]; fee_tk=[d["tk_fee_bps"] for d in S]
spread=[d["spread_bps"] for d in S]; mshare=[d["mk_nz"]/(d["mk_nz"]+d["tk_nz"]) for d in S]
RP=json.load(open(A1+"/replay_participation.json")); tsh_infra=[RP[str(t)]["turnover_share"] for t in range(3)]
HALF=np.array([s/2 for s in spread])
ASK=[6,7,8,9,10,11]; BID=[5,4,3,2,1,0]; XF=np.array([0.0,0.2,1.0,2.0,3.0,4.0,5.0])
def walk(Q,C,X):
    acc=np.zeros(len(Q)); rem=Q.copy(); prev=np.zeros(len(Q))
    for j in range(C.shape[1]):
        seg=np.maximum(C[:,j]-prev,0.0); take=np.minimum(rem,seg)
        dens=np.where(seg>0,seg/(X[j+1]-X[j]),np.inf)
        xend=np.where(np.isfinite(dens)&(dens>0),X[j]+take/np.maximum(dens,1e-300),X[j])
        acc+=take*(X[j]+xend)/2.0; rem-=take; prev=C[:,j]
    acc=acc+np.where(rem>1e-9,rem*X[-1],0.0)
    return np.where(Q>0,acc/np.maximum(Q,1e-12)*100.0,np.nan), rem>1e-9
yr=np.array([time.gmtime(int(t)).tm_year for t in rts]); m26=(yr==2026)
rows=np.where(m26&(lidx>=0))[0]
def tiers_at(G):
    V=[[] for _ in range(3)]; Wt=[[] for _ in range(3)]; CN=[[] for _ in range(3)]
    for i in rows:
        d=dW[i]; s=dWs[i]; m=(d>1e-12)&np.isfinite(QVr[i])&(QVr[i]>0)
        if not m.any(): continue
        book=cum[lidx[i]]; sel=np.where(m)[0]; buy=s[sel]>0
        Cb=np.where(buy[:,None],book[sel][:,ASK],book[sel][:,BID]).astype(np.float64)
        good=np.isfinite(Cb).all(1)&(Cb[:,0]>0)
        if not good.any(): continue
        sel=sel[good]; Cb=Cb[good]; Q=d[sel]*G
        v,cen=walk(Q,Cb,XF); tt=TT[i][sel]; ww=d[sel]
        for t in range(3):
            mm=tt==t
            if mm.any(): V[t].append(v[mm]); Wt[t].append(ww[mm]); CN[t].append(cen[mm])
    out=[]
    for t in range(3):
        v=np.concatenate(V[t]); w=np.concatenate(Wt[t]); c=np.concatenate(CN[t])
        vw=float((v*w).sum()/w.sum()); ex=float((np.maximum(v-HALF[t],0)*w).sum()/w.sum())
        out.append(dict(tier=t,vwap=vw,excess=ex,turn_share=float(w.sum()),n=int(len(v)),
                        cens=float(w[c].sum()/w.sum())))
    tot=sum(o["turn_share"] for o in out)
    for o in out: o["turn_share"]=o["turn_share"]/tot
    return out
def emit(I,tag,name,extra):
    tiers=[];bl=[]
    for t in range(3):
        m=fee_mk[t]+I[t]; k=fee_tk[t]+spread[t]/2.0+I[t]; f=mshare[t]
        tiers.append({"name":["tier0_qv4h>=5e6","tier1_qv4h>=1e6","tier2_rest"][t],
                      "maker_bps":round(m,6),"taker_bps":round(k,6),"maker_share":round(f,6)})
        bl.append(f*m+(1-f)*k)
    avg=sum(b*s for b,s in zip(bl,tsh_infra))
    doc=dict(tiers=tiers,model=name,impact_bps_by_tier=[round(x,6) for x in I],
             blended_bps_per_unit_turnover=[round(b,4) for b in bl],
             book_avg_bps_per_unit_turnover=round(avg,4),
             turnover_share_by_tier=[round(s,4) for s in tsh_infra],
             calibration=extra)
    json.dump(doc,open(f"{R3}/costb_{tag}.json","w"),indent=1)
    return bl,avg
CAL_BASE=dict(fees_and_spread="MEASURED, infra1_cost/tier_stats.json (33,886 deduped live fills, 243 anchors)",
  impact_source="MEASURED order-book walk, /workspace/lob_npz 0.2%-band era (2026 anchors only, 1331 of them), "
                "causal mean cumulative notional over [E-3600,E), book's own per-name trades from the archived "
                "A0 d30_n2_c42_W at the stated gross; piecewise-uniform density between published band edges.",
  known_limits=["the +-0.2% band exists only from 2026, so the tier constants are measured on 2026 and applied "
                "to 2022-2026; the 1%-band control says the full-history book-average walk is 0.40x the 2026 level, "
                "so this is CONSERVATIVE (over-charges the pre-2026 years)",
                "book-walk cost is INSTANTANEOUS aggressive-execution cost. 81-85% of live fills are MAKER and never "
                "cross; charging them the walk is deliberately conservative.",
                "no temporary/permanent decomposition and no queue/adverse-selection term."])
OUT={"G_ladder":{}}
LAD=[230000.,345000.,460000.,690000.,920000.,1380000.,2300000.,4600000.,9200000.,23000000.]
for G in LAD:
    T=tiers_at(G)
    Ie=[max(o["excess"],0.0) for o in T]; Iv=[o["vwap"] for o in T]
    tag="FIT_G%d"%int(G/1000)
    ble,avge=emit(Ie,tag+"k",("book-walk impact, excess of half-spread, G=$%.0f"%G),
                  dict(CAL_BASE,gross_usdt=G,caliber="excess_of_half_spread"))
    blu,avgu=emit(Iv,tag+"k_U",("book-walk impact, full VWAP vs mid, G=$%.0f"%G),
                  dict(CAL_BASE,gross_usdt=G,caliber="full_vwap_vs_mid"))
    OUT["G_ladder"]["%d"%int(G)]=dict(impact_excess=[round(x,5) for x in Ie],impact_vwap=[round(x,5) for x in Iv],
        blended_excess=[round(x,4) for x in ble],book_avg_excess=round(avge,4),
        blended_vwap=[round(x,4) for x in blu],book_avg_vwap=round(avgu,4),
        turn_share_2026=[round(o["turn_share"],4) for o in T],censored=[round(o["cens"],5) for o in T])
    print("G=%9.0f  I_excess %s  book-avg %.4f | I_vwap %s  book-avg %.4f"%(G,[round(x,4) for x in Ie],avge,[round(x,4) for x in Iv],avgu),flush=True)
# deployed + infra1 references on the same blend
D=json.load(open("/workspace/review_scratch/health_check/calib/costb_fee_steady.json"))["tiers"]
bl=[t["maker_share"]*t["maker_bps"]+(1-t["maker_share"])*t["taker_bps"] for t in D]
OUT["reference_deployed"]=dict(blended=[round(b,4) for b in bl],book_avg=round(sum(b*s for b,s in zip(bl,tsh_infra)),4))
for t in ("H0","X1","X2","X3"):
    J=json.load(open(A1+"/costb_honest_%s.json"%t))
    OUT["reference_infra1_"+t]=dict(blended=J["blended_bps_per_unit_turnover"],book_avg=J["book_avg_bps_per_unit_turnover"])
json.dump(OUT,open(R3+"/COSTB_LADDER.json","w"),indent=1)
print(json.dumps({k:OUT[k] for k in OUT if k!="G_ladder"},indent=1))
print("WROTE",R3+"/COSTB_LADDER.json")
