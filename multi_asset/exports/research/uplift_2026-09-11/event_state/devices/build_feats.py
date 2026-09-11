"""Track G feature builder. Strictly causal: a settlement contributes to anchor E only if S+25min <= E."""
import numpy as np, json, time, os
OUT="/workspace/uplift_2026-09-11/event_state"
PW=np.load("/workspace/uplift_2026-09-11/dev_v4ev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]; SY=[str(s) for s in sym]; nA=len(ts); NW=len(SY)
MT=np.load("/workspace/uplift_2026-09-11/dev_v4ev/pod_backup_2026-08-21/wide_fea_hist_meta.npz",allow_pickle=True)
Z=np.load(f"{OUT}/sett_v4.npz",allow_pickle=True)
ET=Z["ts"].astype(np.int64); EK=Z["k"].astype(np.int64); ER=Z["rate"].astype(np.float64); EDR=Z["dr"].astype(np.float64); EM=Z["miss"]
assert [str(s) for s in Z["symbols"]]==SY
# drop events with any missing 5m bar in the 35-min window
good=np.isfinite(EDR)&(EM==0)
ET,EK,ER,EDR=ET[good],EK[good],ER[good],EDR[good]
print("usable events",len(ET),flush=True)
# --- per-name ordering, interval from spacing, rn8
ordr=np.lexsort((ET,EK)); ET,EK,ER,EDR=ET[ordr],EK[ordr],ER[ordr],EDR[ordr]
IVh=np.full(len(ET),8.0)
sp=np.diff(ET)/3600.0; samek=(np.diff(EK)==0)
IVh[1:]=np.where(samek&np.isin(np.round(sp),[1.,2.,4.,8.]),np.round(sp),np.nan)
# backfill first event of each name with the following spacing
bad=~np.isfinite(IVh)
IVh[bad]=np.nan
for i in np.where(bad)[0]:
    j=i+1
    if j<len(ET) and EK[j]==EK[i] and np.isfinite(IVh[j]): IVh[i]=IVh[j]
IVh=np.where(np.isfinite(IVh),IVh,8.0)
RN8=ER*(8.0/IVh)
print("interval hist",{float(k):int(v) for k,v in zip(*np.unique(IVh,return_counts=True))},flush=True)
# --- cap atoms in the upper tail
av=np.abs(ER); tail=av[av>=0.003]
uq,cnt=np.unique(np.round(tail,6),return_counts=True)
atoms=[(float(uq[i]),int(cnt[i])) for i in np.argsort(-cnt)[:12]]
print("TAIL_ATOMS(|rate|>=0.003)",atoms,flush=True)
# --- per-settlement-time cross-sectional OLS of dr on rn8  -> SWRESID
RES=np.full(len(ET),np.nan)
uT,inv=np.unique(ET,return_inverse=True)
ordT=np.argsort(inv,kind="stable"); bnd=np.searchsorted(inv[ordT],np.arange(len(uT)+1))
nfit=0
for a in range(len(uT)):
    idx=ordT[bnd[a]:bnd[a+1]]
    if len(idx)<20: continue
    x=RN8[idx]; y=EDR[idx]
    ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()<20: continue
    xm=x[ok]-x[ok].mean(); ym=y[ok]-y[ok].mean(); vx=float((xm*xm).sum())
    b=float((xm*ym).sum()/vx) if vx>1e-18 else 0.0
    RES[idx[ok]]=y[ok]-y[ok].mean()-b*(x[ok]-x[ok].mean()); nfit+=1
print(f"per-settlement OLS fits {nfit}/{len(uT)}; resid finite {np.isfinite(RES).mean():.4f}",flush=True)
# --- assemble anchor x name features
def blank(): return np.full((nA,NW),np.nan)
SWDRIFT=blank(); SWRESID=blank(); SWRESID3=blank(); SWABS=blank(); CAPPIN=blank(); IVNOW=blank()
CAP=0.0075   # set below from atoms if a clear atom exists
STALE=24*3600
kstart=np.searchsorted(EK,np.arange(NW+1))
cut=ts-1800
for k in range(NW):
    a,b=kstart[k],kstart[k+1]
    if b-a<3: continue
    tk=ET[a:b]; dk=EDR[a:b]; rk=RES[a:b]; ak=np.abs(ER[a:b]); ivk=IVh[a:b]
    pos=np.searchsorted(tk,cut,side="right")-1
    ok=(pos>=0)
    ok&= np.where(ok, ts-tk[np.clip(pos,0,len(tk)-1)]<=STALE, False)
    p=np.clip(pos,0,len(tk)-1)
    SWDRIFT[ok,k]=dk[p[ok]]
    SWRESID[ok,k]=rk[p[ok]]
    IVNOW[ok,k]=ivk[p[ok]]
    ok3=ok&(pos>=2)
    if ok3.any():
        pp=p[ok3]
        SWRESID3[ok3,k]=np.nanmean(np.stack([rk[pp],rk[pp-1],rk[pp-2]]),axis=0)
        SWABS[ok3,k]=np.nanmean(np.stack([np.abs(dk[pp]),np.abs(dk[pp-1]),np.abs(dk[pp-2])]),axis=0)
    ok6=ok&(pos>=5)
    if ok6.any():
        pp=p[ok6]
        CAPPIN[ok6,k]=np.mean(np.stack([ak[pp-i]>=CAP for i in range(6)]),axis=0)
# --- IVSWITCH: -log2(iv_now / iv_42ago)
IVSWITCH=blank()
IVSWITCH[42:,:]=-np.log2(IVNOW[42:,:]/IVNOW[:-42,:])
# --- LISTEVT: exp(-age/42), age in anchors since first finite y4 (v4 meta, era-synchronous)
Ets=MT["E_ts"].astype(np.int64); y4=MT["y4"]
mrow={int(t):i for i,t in enumerate(Ets)}
fin=np.isfinite(y4)
first=np.where(fin.any(0), fin.argmax(0), -1)
LISTEVT=blank()
mi=np.array([mrow.get(int(t),-1) for t in ts])
for k in range(NW):
    if first[k]<0: continue
    age=mi-first[k]
    LISTEVT[:,k]=np.where((mi>=0)&(age>=0),np.exp(-np.maximum(age,0)/42.0),np.nan)
np.savez_compressed(f"{OUT}/feats_v4.npz",ts=ts,symbols=sym,
    SWDRIFT=SWDRIFT.astype(np.float32),SWRESID=SWRESID.astype(np.float32),
    SWRESID3=SWRESID3.astype(np.float32),SWABS=SWABS.astype(np.float32),
    CAPPIN=CAPPIN.astype(np.float32),IVSWITCH=IVSWITCH.astype(np.float32),
    LISTEVT=LISTEVT.astype(np.float32),IVNOW=IVNOW.astype(np.float32))
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
cov={}
for nm,M in [("SWDRIFT",SWDRIFT),("SWRESID",SWRESID),("SWRESID3",SWRESID3),("SWABS",SWABS),
             ("CAPPIN",CAPPIN),("IVSWITCH",IVSWITCH),("LISTEVT",LISTEVT)]:
    per=np.isfinite(np.where(BASE,M,np.nan)).sum(1)
    cov[nm]={"mean_names_per_anchor":float(per.mean()),
             "by_year":{y:float(per[(ts>=int(np.datetime64(f"{y}-01-01").astype("datetime64[s]").astype(int)))&(ts<int(np.datetime64(f"{int(y)+1}-01-01").astype("datetime64[s]").astype(int)))].mean()) for y in ["2022","2023","2024","2025","2026"]},
             "nonzero_share":float(np.isfinite(M).mean())}
cov["BASE_mean_names_per_anchor"]=float(BASE.sum(1).mean())
cov["cap_used"]=CAP; cov["tail_atoms"]=atoms
cov["interval_hist"]={str(float(k)):int(v) for k,v in zip(*np.unique(IVh,return_counts=True))}
cov["usable_events"]=int(len(ET))
json.dump(cov,open(f"{OUT}/COVERAGE.json","w"),indent=1)
print(json.dumps(cov,indent=1))
print("FEATS_DONE",flush=True)
