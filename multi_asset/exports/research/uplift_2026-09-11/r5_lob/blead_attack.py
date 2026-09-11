"""Is BLEAD's forward rank-IC (+0.0314, 24 SE) NEW information, or the panel's own f_rev_4h re-spelled?
BLEAD = d4h(book price centre) - f_rev_4h, so it contains -f_rev_4h BY CONSTRUCTION."""
import numpy as np, json, calendar
from scipy.stats import rankdata
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=P["ts"].astype(np.int64); Y=np.asarray(P["Y4"],float)
BASE=np.isfinite(np.asarray(P["f_fund_ema_v1"],float))
R4=np.where(BASE,np.asarray(P["f_rev_4h"],float),np.nan)
BL=np.where(BASE,np.asarray(np.load("/workspace/uplift_2026-09-11/r5_lob/feat/BLEAD.npz",allow_pickle=True)["mat"],float),np.nan)
ME=np.where(BASE,np.asarray(np.load("/workspace/uplift_2026-09-11/r5_lob/feat/MEND.npz",allow_pickle=True)["mat"],float),np.nan)
dM=np.full(ME.shape,np.nan); dM[1:]=ME[1:]-ME[:-1]
COV=np.isfinite(BL)   # evaluate every variant on the SAME cells as BLEAD
END=T(2026,8,10,20)+1
def rz(v):
    ok=np.isfinite(v); o=np.full(len(v),np.nan)
    if ok.sum()>=20: o[ok]=rankdata(v[ok])/max(ok.sum()-1,1)-0.5
    return o
def ic0(S,name):
    ics=[]
    for i in range(len(ts)):
        if ts[i]>=END: continue
        a=np.where(COV[i],S[i],np.nan); b=Y[i]
        ok=np.isfinite(a)&np.isfinite(b)
        if ok.sum()<50: continue
        ics.append(np.corrcoef(rankdata(a[ok]),rankdata(b[ok]))[0,1])
    m=float(np.mean(ics)); se=float(np.std(ics,ddof=1)/np.sqrt(len(ics)))
    print("  %-34s forward IC k=0  %+0.5f  (SE %0.5f, %.1f SE, n=%d)"%(name,m,se,abs(m)/se,len(ics)))
    return m,se
print("Same cells as BLEAD (COV), same span, forward k=0 rank-IC:")
a=ic0(BL,"BLEAD")
b=ic0(-R4,"-f_rev_4h  (existing panel channel)")
c=ic0(dM,"d4h(book price) alone")
# BLEAD residualised on f_rev_4h, per anchor, in rank space
Rres=np.full(BL.shape,np.nan)
for i in range(len(ts)):
    x=rz(np.where(COV[i],R4[i],np.nan)); y=rz(np.where(COV[i],BL[i],np.nan))
    ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()<50: continue
    vx=float((x[ok]*x[ok]).sum()); bb=float((x[ok]*y[ok]).sum()/vx) if vx>1e-12 else 0.0
    Rres[i][ok]=y[ok]-bb*x[ok]
d=ic0(Rres,"BLEAD orthogonalised to f_rev_4h")
# how much of BLEAD is just -f_rev_4h?
rr=[]
for i in range(0,len(ts),7):
    x=rz(np.where(COV[i],-R4[i],np.nan)); y=rz(np.where(COV[i],BL[i],np.nan))
    ok=np.isfinite(x)&np.isfinite(y)
    if ok.sum()>=50: rr.append(np.corrcoef(x[ok],y[ok])[0,1])
print("  xsec rank-rho( BLEAD , -f_rev_4h ) = %+0.4f"%np.mean(rr))
json.dump({"ic_BLEAD":a,"ic_neg_rev4h":b,"ic_dbook_alone":c,"ic_BLEAD_orth_rev4h":d,
           "rho_BLEAD_to_neg_rev4h":round(float(np.mean(rr)),4)},
          open("/workspace/uplift_2026-09-11/r5_lob/BLEAD_ATTACK.json","w"),indent=1)
