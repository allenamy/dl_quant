"""R5/ND1: build the BASIS panel on the v4 4h anchor axis.
CAUSALITY BAR, enforced in code (assert, not comment):
  at anchor E we use ONLY 1h premium-index bars with open_time <= E-3600s, i.e. close_time <= E-1ms.
  The device return y4 spans [E, E+4h).  Nothing at E touches data at or after E.
Outputs /workspace/uplift_2026-09-11/r5_basis/basis_panel.npz aligned EXACTLY to
wide_panel_4h_v2ext.npz ts (10039) x symbols (829)."""
import numpy as np, zipfile, glob, os, json, time, calendar
R="/workspace/uplift_2026-09-11/r5_basis"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=[str(s) for s in PW["symbols"]]; NS=len(SYM)
FN=np.asarray(PW["f_fund_now"],float); IVp=np.asarray(PW["f_fund_iv"],float)
assert np.all(np.diff(TS)==14400) and np.all(TS%14400==0)
H0=int(TS[0])-30*86400; H1=int(TS[-1])+86400
NH=(H1-H0)//3600+1
P=np.full((NH,NS),np.nan,np.float32)
zero_rows=0; tot_rows=0; nofile=[]
t0=time.time()
for c,s in enumerate(SYM):
    fs=sorted(glob.glob(R+"/raw/prem/%s/*.zip"%s))
    if not fs: nofile.append(s); continue
    ot=[]; cl=[]
    for f in fs:
        try: z=zipfile.ZipFile(f)
        except Exception: continue
        for n in z.namelist():
            for ln in z.read(n).decode().splitlines():
                if not ln or ln[0]=="o": continue
                p=ln.split(",")
                ot.append(int(p[0])); cl.append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    if not ot: nofile.append(s); continue
    ot=np.array(ot,np.int64)//1000; A=np.array(cl,float)
    tot_rows+=len(ot)
    bad=(A[:,0]==0)&(A[:,1]==0)&(A[:,2]==0)&(A[:,3]==0)
    zero_rows+=int(bad.sum())
    v=np.where(bad,np.nan,A[:,3])
    assert np.all(ot%3600==0), s
    k=(ot-H0)//3600
    m=(k>=0)&(k<NH)
    # dedupe: later file wins only if earlier is nan; use ordered assignment on sorted unique
    o=np.argsort(ot[m],kind="stable"); kk=k[m][o]; vv=v[m][o]
    P[kk,c]=vv
    if c%200==0: print("sym",c,"/",NS,"%.0fs"%(time.time()-t0),flush=True)
print("zero-OHLC rows treated as NaN:",zero_rows,"/",tot_rows,"=%.5f"%(zero_rows/max(tot_rows,1)),flush=True)
print("symbols with no premium archive:",len(nofile),nofile[:20],flush=True)
print("hour-grid finite frac",float(np.isfinite(P).mean()),flush=True)
# ---- windowed stats via masked cumsum over the HOUR axis ----
F=np.isfinite(P); V=np.where(F,P,0.0).astype(np.float64); V2=V*V
CS=np.vstack([np.zeros((1,NS)),np.cumsum(V,0)])
CS2=np.vstack([np.zeros((1,NS)),np.cumsum(V2,0)])
CN=np.vstack([np.zeros((1,NS)),np.cumsum(F.astype(np.float64),0)])
def win(idx_end,w):
    """mean/std/count over hour rows [idx_end-w+1, idx_end] inclusive."""
    hi=idx_end+1; lo=hi-w
    n=CN[hi]-CN[lo]; s=CS[hi]-CS[lo]; s2=CS2[hi]-CS2[lo]
    mu=np.where(n>0,s/np.maximum(n,1),np.nan)
    var=np.where(n>1,(s2-n*mu*mu)/np.maximum(n-1,1),np.nan)
    return mu,np.sqrt(np.maximum(var,0.0)),n
# anchor -> index of the LAST FULLY CLOSED hour bar, open_time = E-3600
ai=np.array([(int(t)-3600-H0)//3600 for t in TS],np.int64)
assert np.all(ai>=0) and np.all(ai<NH)
# THE CAUSALITY ASSERT: open_time of the newest bar used, +3600s (its close), <= E
assert np.all((H0+ai*3600)+3600<=TS), "CAUSALITY VIOLATION"
nT=len(TS)
p_last=np.full((nT,NS),np.nan); p_tw8=np.full((nT,NS),np.nan); p_tw24=np.full((nT,NS),np.nan)
p_sd8=np.full((nT,NS),np.nan); p_tw_iv=np.full((nT,NS),np.nan); n8=np.zeros((nT,NS)); n24=np.zeros((nT,NS))
IVH=np.where(np.isfinite(IVp)&(IVp>0),IVp,8.0).astype(int)
for i in range(nT):
    e=int(ai[i])
    p_last[i]=P[e]
    m8,s8,c8=win(e,8);   p_tw8[i]=m8; p_sd8[i]=s8; n8[i]=c8
    m24,_,c24=win(e,24); p_tw24[i]=m24; n24[i]=c24
    for w in (1,2,4,6,8):
        sel=IVH[i]==w
        if sel.any():
            mw,_,cw=win(e,w); p_tw_iv[i,sel]=np.where(cw[sel]>=max(1,w//2),mw[sel],np.nan)
# full-window requirement (conservative; no partial-window bias)
p_tw8=np.where(n8>=8,p_tw8,np.nan); p_sd8=np.where(n8>=8,p_sd8,np.nan); p_tw24=np.where(n24>=24,p_tw24,np.nan)
np.savez_compressed(R+"/basis_panel.npz",ts=TS,symbols=np.array(SYM),
    p_last=p_last.astype(np.float32),p_tw8=p_tw8.astype(np.float32),p_tw24=p_tw24.astype(np.float32),
    p_sd8=p_sd8.astype(np.float32),p_tw_iv=p_tw_iv.astype(np.float32),
    hour0=H0,ai=ai)
BM=np.isfinite(np.asarray(PW["f_fund_ema_v1"],float))
cov={"n_anchors":nT,"n_syms":NS,"no_archive":len(nofile),
 "zero_ohlc_frac":round(zero_rows/max(tot_rows,1),6),
 "finite_p_last":round(float(np.isfinite(p_last).mean()),4),
 "finite_p_last_on_fundmask":round(float(np.isfinite(p_last[BM]).mean()),4),
 "finite_p_tw24_on_fundmask":round(float(np.isfinite(p_tw24[BM]).mean()),4),
 "finite_p_tw_iv_on_fundmask":round(float(np.isfinite(p_tw_iv[BM]).mean()),4),
 "fundmask_frac":round(float(BM.mean()),4)}
print(json.dumps(cov,indent=1),flush=True)
json.dump({"coverage":cov,"no_archive_symbols":nofile},open(R+"/BASIS_COVERAGE.json","w"),indent=1)
print("BUILD_DONE %.0fs"%(time.time()-t0),flush=True)
