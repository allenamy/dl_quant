"""Reconcile the two instruments on RESID_SHARPE: cross-sectional RANK-IC (ordering) vs the device s own
VALUE-caliber leg return (the quantity the book earns).  Leg construction copied verbatim from
w10_sleeve.py legs() with UMASK_SCOPE=m1, LEGS=001, CAL=log: z = xz over the 829 base subset to members,
NaN->0, zeroed where y4 is not finite, demeaned over the finite set; leg_ret = sum(z/|z|_1 * y4) * 1e4.
"""
import numpy as np, calendar, json
from scipy.stats import rankdata
HC="/workspace/review_scratch/health_check"; B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=np.asarray(MT["y4"],float); nA=len(E_ts)
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
WSYM=[str(s) for s in PW["symbols"]]; NW=len(WSYM)
UM=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
UROW={j:UMM[umap[int(t)]] for j,t in enumerate(pts) if int(t) in umap}
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
dts=TG["E_ts"].astype(np.int64); dsy=[str(x) for x in TG["symbols"]]
rmap={int(t):k for k,t in enumerate(dts)}; cmap={s:k for k,s in enumerate(dsy)}
cols=np.array([cmap.get(s,-1) for s in WSYM],np.int64); okc=cols>=0
def align(p):
    pd=np.load(p); M=np.full((nA,NW),np.nan)
    for i in range(nA):
        k=rmap.get(int(E_ts[i]))
        if k is not None: M[i,okc]=pd[k,cols[okc]]
    return M
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan)
    if ok.sum()>=10: out[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return out
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WIN={"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"pre2025":(T(2023,1,1),T(2025,1,1)),
     "2025on":(T(2025,1,1),T(2026,8,10,20)+1),"FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),"F23all":(T(2023,1,1),T(2026,8,10,20)+1)}
res={}
for tag,path in [("RESID_SHARPE_s42","/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s42.npy"),
                 ("RESID_SHARPE_s2027","/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s2027.npy"),
                 ("XIB_ref_LIVE_FUND",None)]:
    if path is None:
        FE=np.asarray(PW["f_fund_ema_v1"],float); S=None
    else: S=align(path)
    ts=[]; LR=[]; RIC=[]; TOPQ=[]
    for i in range(nA):
        j=pw_row.get(int(E_ts[i]))
        if j is None: continue
        m=members[i]; mk=UROW.get(j)
        if mk is not None: m=m[mk[m]]
        if len(m)<50: continue
        sc = xz(FE[j,:])[m] if S is None else xz(S[i,:])[m]
        yy=y4[i,m]; ok=np.isfinite(yy)
        if ok.sum()<50 or not np.isfinite(sc).any(): continue
        z=np.nan_to_num(sc); z=np.where(ok,z,0.0); z=z-z[ok].mean()
        g=np.abs(z).sum()
        if g<=1e-9: continue
        lr=float((z/g*np.nan_to_num(yy,nan=0.0)).sum()*1e4)
        okf=ok&np.isfinite(sc)
        a=rankdata(sc[okf]); b=rankdata(yy[okf]); a=a-a.mean(); b=b-b.mean()
        d=np.sqrt((a*a).sum()*(b*b).sum()); ric=float((a*b).sum()/d) if d>0 else np.nan
        ts.append(int(E_ts[i])); LR.append(lr); RIC.append(ric)
    ts=np.array(ts); LR=np.array(LR); RIC=np.array(RIC)
    res[tag]={}
    print("--",tag)
    print("   %-8s %6s %14s %14s %10s"%("win","n","leg_ret(value)","rank_IC","LR_Sharpe"))
    for w,(lo,hi) in WIN.items():
        m=(ts>=lo)&(ts<hi)
        if m.sum()<10: continue
        v=LR[m]; r=RIC[m]
        sh=v.mean()/v.std(ddof=1)*np.sqrt(2190)
        res[tag][w]={"n":int(m.sum()),"leg_ret_bps":round(float(v.mean()),4),"leg_sharpe":round(float(sh),3),"rank_ic":round(float(np.nanmean(r)),5)}
        print("   %-8s %6d %+14.4f %+14.5f %+10.3f"%(w,m.sum(),v.mean(),np.nanmean(r),sh))
json.dump(res,open("/workspace/uplift_2026-09-11/r3_gates/rs_reconcile.json","w"),indent=1)
