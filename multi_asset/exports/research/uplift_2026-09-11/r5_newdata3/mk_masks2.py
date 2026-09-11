"""r5nd/mk_masks2.py -- STALENESS DOSE-RESPONSE family (descriptive, not in K) + the live frozen list.
Same selection logic as mk_masks.py (itself verbatim from build_umask.py) -- the ONLY change is WHICH
month's selection is in force at each anchor.
  STALE_L : at every anchor use the top-449 selection made L calendar months earlier (L=0 is A0).
  UFROZEN450: the LIVE syms450.txt list at every anchor. LOOK-AHEAD (today's survivors projected back)
              => an UPPER BOUND on the frozen book, never a fair estimate. Labelled as such.
"""
import numpy as np, json, time, os, hashlib
t0=time.time()
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
CACHE="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"; PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
Z=np.load(CACHE,allow_pickle=True)
CTS=Z["ts"].astype(np.int64); CSYM=[str(s) for s in Z["symbols"]]; CH=[str(c) for c in Z["ch"]]
iq=CH.index("log_qv"); ir=CH.index("ret5"); D=Z["data"]
P=np.load(PANEL,allow_pickle=True); PTS=P["ts"].astype(np.int64); PSYM=[str(s) for s in P["symbols"]]
assert PSYM==CSYM
NW=len(PSYM); col={s:j for j,s in enumerate(PSYM)}
ret5=D[:,:,ir].astype(np.float32); fin=np.isfinite(ret5); has=fin.any(0)
_fi_lq0=np.argmax(np.isfinite(D[:,:,iq]),0)
first_ts=np.where(has,np.where(_fi_lq0<=2,CTS[0],CTS[np.clip(_fi_lq0,0,len(CTS)-1)]),2**62)
lq=D[:,:,iq].astype(np.float32)
qv5=np.expm1(np.clip(np.nan_to_num(lq,nan=0.0),0,30)).astype(np.float64); del lq
cs=np.zeros((len(CTS)+1,NW),np.float64); np.cumsum(qv5,axis=0,out=cs[1:]); del qv5
BARS30=30*288; pos={int(t):k for k,t in enumerate(CTS)}
mstart={}
for j,t in enumerate(PTS):
    tm=time.gmtime(int(t)); key=(tm.tm_year,tm.tm_mon)
    if key not in mstart: mstart[key]=j
keys=sorted(mstart); kidx={k:i for i,k in enumerate(keys)}
ORDER={}
for key in keys:
    j0=mstart[key]; t=int(PTS[j0]); k=pos[t]; lo=max(0,k-BARS30)
    vol30=cs[k]-cs[lo]; age=(t-first_ts)/86400.0
    elig=has&(age>=30)&(vol30>0)
    o=np.argsort(-vol30); ORDER[key]=o[elig[o]]
U0=np.load(HC+"/masks/umask_UPIT.npz",allow_pickle=True); UC=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
M0=np.asarray(U0["mask"]); MC=np.asarray(UC["mask"])
det=M0.any(0); coin=np.zeros(NW,bool); coin[det]=MC[:,det].any(0)
VC=json.load(open(R+"/venue_class_2026-09-11.json"))
for j in np.where(~det)[0]:
    s=PSYM[j]; coin[j]=(VC[s]["underlyingType"] in ("COIN","INDEX")) if s in VC else True
def mask_from(selfn):
    M=np.zeros((len(PTS),NW),bool)
    for n,key in enumerate(keys):
        j0=mstart[key]; j1=mstart[keys[n+1]] if n+1<len(keys) else len(PTS)
        m=np.zeros(NW,bool); m[selfn(key)]=True; M[j0:j1]=m
    return M
ARMS={}
for L in (1,3,6,12):
    def f(key,L=L):
        i=kidx[key]; j=max(0,i-L); return ORDER[keys[j]][:449]
    ARMS["STALE%d"%L]=mask_from(f)&coin[None,:]
S450=[l.strip() for l in open(HC+"/syms450.txt") if l.strip()]
fz=np.zeros(NW,bool); fz[[col[s] for s in S450 if s in col]]=True
print("syms450 file n=%d, mapped into panel n=%d, missing %s"%(len(S450),int(fz.sum()),[s for s in S450 if s not in col]),flush=True)
ARMS["UFROZEN450"]=np.tile(fz&coin,(len(PTS),1))
yr=np.array([time.gmtime(int(t)).tm_year for t in PTS])
summ={}
for nm,M in ARMS.items():
    p=R+"/masks/umask_R5_%s.npz"%nm
    np.savez_compressed(p,ts=PTS,symbols=np.array(PSYM),mask=M)
    ov=float((M&MC).sum()/max(MC.sum(),1))
    by={str(y):round(float(M[yr==y].sum(1).mean()),1) for y in sorted(set(yr.tolist()))}
    summ[nm]={"file":p,"sha256_16":hashlib.sha256(open(p,"rb").read()).hexdigest()[:16],
              "allowed_mean":round(float(M.sum(1).mean()),1),"allowed_by_year":by,"overlap_with_A0_mask":round(ov,4)}
    print("%-12s allowed %6.1f  overlap(A0) %.4f  %s"%(nm,M.sum(1).mean(),ov,by),flush=True)
json.dump(summ,open(R+"/mask_summary_r5b.json","w"),indent=1)
print("MASKS2_DONE %.0fs"%(time.time()-t0),flush=True)
