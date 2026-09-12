"""R8/BUILD-1: (i) GIVEBACK robustness -- the 18-anchor day-block bootstrap has only 3 blocks, so it is
reported alongside an ANCHOR-level bootstrap and the raw per-anchor series; (ii) G8 regime-conditional rho.
Regime labels copied verbatim from r6j1_regime.py (= trackF/build_regime.py): sig_fund = 1e4*xsec sd of
8h-equiv funding, disp24 = xsec sd of f_rev_24h, expanding-median split, BURN=2190, on the m1 live base."""
import numpy as np, json, calendar, time, sys
R="/workspace/uplift_2026-09-11/r8_inbook"; HC="/workspace/review_scratch/health_check"
B=HC+"/dev_v4/pod_backup_2026-08-21"
MT=np.load(B+"/wide_fea_hist_meta.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); qvk=MT["qvk"]; nA=len(E_ts)
PW=np.load(B+"/wide_panel_4h_hist_v2.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
UM=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
umap={int(t):k for k,t in enumerate(UM["ts"].astype(np.int64))}; UMM=np.asarray(UM["mask"])
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; R24=PW["f_rev_24h"]
_IVf=np.where(np.isfinite(IV)&(IV>0),IV,8.0); RN8=FN*(8.0/_IVf)
MEM=np.empty(nA,dtype=object)
for i in range(nA):
    q=np.nan_to_num(qvk[i],nan=-1.0); o=np.argsort(-q); o=o[q[o]>-0.5]; MEM[i]=np.sort(o[:829]).astype(np.int64)
rows=[]
for i,t in enumerate(E_ts):
    j=pw_row.get(int(t))
    if j is None: continue
    m=MEM[i]; k=umap.get(int(t))
    if k is not None: m=m[UMM[k][m]]
    if len(m)<50: continue
    f=RN8[j,m]; f=f[np.isfinite(f)]; r=R24[j,m]; r=r[np.isfinite(r)]
    nn=lambda a,fn:(float(fn(a)) if len(a)>50 else np.nan)
    rows.append((int(t),nn(f,lambda a:1e4*np.std(a)),nn(r,np.std)))
A=np.array(rows,float); rts=A[:,0].astype(np.int64); BURN=2190
def lab1(x):
    L=np.full(len(x),-1,np.int8)
    for i in range(len(x)):
        if i<BURN: continue
        p=x[:i]; p=p[np.isfinite(p)]
        if len(p)<BURN//2 or not np.isfinite(x[i]): continue
        L[i]=1 if x[i]>np.median(p) else 0
    return L
LF=lab1(A[:,1]); LD=lab1(A[:,2]); LAB=np.full(len(rts),-1,np.int8)
ok=(LF>=0)&(LD>=0); LAB[ok]=LF[ok]*2+LD[ok]
labmap={int(t):int(l) for t,l in zip(rts,LAB)}
NM={0:"LL",1:"LH",2:"HL",3:"HH"}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
CEIL=T(2026,8,30,20); FULL_HI=T(2026,8,10,20); WARM=900
def load(p):
    Z=np.load(p,allow_pickle=True); c=[str(x) for x in Z["cols"]]; ix={x:i for i,x in enumerate(c)}
    Rr=np.asarray(Z["rec"],float)[WARM:]; ts=np.round(Rr[:,ix["ts"]]).astype(np.int64)
    m=ts<=CEIL; Rr=Rr[m]; ts=ts[m]; gt=Rr[:,ix["gross_total"]]
    return ts,Rr[:,ix["net_ex"]]/gt
ts0,a=load(R+"/arms/R8_A0_dyn_s42.npz")
ARMS=["R8A_BLEND_005","R8A_BLEND_010","R8A_BLEND_020","R8A_BLEND_050","R8B_OVL_010","R8B_OVL_100","R8C_GT_025","R8C_GT_100"]
OUT={"regime_n":{},"arms":{}}
lab=np.array([labmap.get(int(t),-1) for t in ts0])
mf=ts0<=FULL_HI
for c in (0,1,2,3): OUT["regime_n"][NM[c]]=int(((lab==c)&mf).sum())
gb=(ts0>=T(2026,8,19))&(ts0<=T(2026,8,21,20))
print("GIVEBACK anchors",int(gb.sum()),"UTC days",len(set((ts0[gb]//86400).tolist())),flush=True)
print("A0 giveback per-anchor g:", " ".join("%.1f"%x for x in a[gb]),flush=True)
for A_ in ARMS:
    ts1,s=load(R+"/arms/%s_dyn_s42.npz"%A_); assert np.array_equal(ts1,ts0)
    d=s-a
    o={"rho_g_to_A0_full":float(np.corrcoef(a[mf],s[mf])[0,1]),
       "rho_marginal_to_A0_full":float(np.corrcoef(a[mf],d[mf])[0,1]),"cells":{}}
    for c in (0,1,2,3):
        m=(lab==c)&mf
        if m.sum()<50: continue
        o["cells"][NM[c]]={"n":int(m.sum()),"rho_g":round(float(np.corrcoef(a[m],s[m])[0,1]),4),
                           "rho_marginal":round(float(np.corrcoef(a[m],d[m])[0,1]),4),
                           "dg":round(float(d[m].mean()),5)}
    # giveback: anchor-level bootstrap (18 anchors), B=20000
    rng=np.random.default_rng([20260912,1]); x=d[gb]; n=len(x)
    bs=x[rng.integers(0,n,size=(20000,n))].mean(1)
    o["giveback"]={"n":int(n),"dg":float(x.mean()),
                   "anchor_boot_ci95":[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],
                   "anchor_boot_ci_bonf13":[float(np.percentile(bs,0.05/13/2*100)),float(np.percentile(bs,100-0.05/13/2*100))],
                   "per_anchor":[round(float(v),3) for v in x],
                   "n_pos":int((x>0).sum()),
                   "dg_ex_worst_anchor":float((x.sum()-x[np.argmax(np.abs(x))])/(n-1))}
    OUT["arms"][A_]=o
    print("%-16s rho_g %.4f rho_marg %+.3f | cells %s | GB dg %+.3f ci95[%+.3f,%+.3f] pos %d/18 ex-worst %+.3f"%(
        A_,o["rho_g_to_A0_full"],o["rho_marginal_to_A0_full"],
        {k:v["dg"] for k,v in o["cells"].items()},o["giveback"]["dg"],
        o["giveback"]["anchor_boot_ci95"][0],o["giveback"]["anchor_boot_ci95"][1],
        o["giveback"]["n_pos"],o["giveback"]["dg_ex_worst_anchor"]),flush=True)
json.dump(OUT,open("/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r8_inbook/REGIME_GIVEBACK.json","w"),indent=1)
print("REGIME_GB_DONE")
