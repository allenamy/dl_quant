"""r5nd/mk_masks.py -- universe masks for NEW DATA 3 (round 5).
Selection logic copied VERBATIM from /workspace/review_scratch/health_check/build_umask.py, with ONE
substitution: the 5m cache is the PINNED v4 file dlnative_5m_wide829_f16_holefix2.npz instead of the
FORBIDDEN _ext cache.  G0 parity gate: MONTHLY449 & coin must equal the pinned umask_UPIT_CRYPTO.npz
cell-for-cell; if not, the pinned mask stays the A0 control and MONTHLY449 is reported separately.
Outputs (r5nd/masks/): umask_R5_<NAME>.npz {ts, symbols, mask} + r5nd/mask_summary_r5.json + agemat.npz
"""
import numpy as np, json, time, os, hashlib, calendar
t0=time.time()
R="/workspace/uplift_2026-09-11/r5nd"; HC="/workspace/review_scratch/health_check"
os.makedirs(R+"/masks",exist_ok=True)
CACHE="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
Z=np.load(CACHE,allow_pickle=True)
CTS=Z["ts"].astype(np.int64); CSYM=[str(s) for s in Z["symbols"]]; CH=[str(c) for c in Z["ch"]]
iq=CH.index("log_qv"); ir=CH.index("ret5")
D=Z["data"]; print("cache",D.shape,D.dtype,"%.0fs"%(time.time()-t0),flush=True)
P=np.load(PANEL,allow_pickle=True); PTS=P["ts"].astype(np.int64); PSYM=[str(s) for s in P["symbols"]]
assert PSYM==CSYM,"panel/cache symbol order differs"
NW=len(PSYM); col={s:j for j,s in enumerate(PSYM)}
ret5=D[:,:,ir].astype(np.float32); fin=np.isfinite(ret5)
has=fin.any(0); first_idx=np.argmax(fin,0)
_lq_fin=np.isfinite(D[:,:,iq]); _fi_lq0=np.argmax(_lq_fin,0)
first_ts=np.where(has,np.where(_fi_lq0<=2,CTS[0],CTS[np.clip(_fi_lq0,0,len(CTS)-1)]),2**62)
lq=D[:,:,iq].astype(np.float32)
qv5=np.expm1(np.clip(np.nan_to_num(lq,nan=0.0),0,30)).astype(np.float64); del lq
cs=np.zeros((len(CTS)+1,NW),np.float64); np.cumsum(qv5,axis=0,out=cs[1:]); del qv5
print("cumsum %.0fs"%(time.time()-t0),flush=True)
BARS30=30*288; pos={int(t):k for k,t in enumerate(CTS)}
mstart={}
for j,t in enumerate(PTS):
    tm=time.gmtime(int(t)); key=(tm.tm_year,tm.tm_mon)
    if key not in mstart: mstart[key]=j
keys=sorted(mstart)
# ---- per-month ranked eligible order (once) ----
ORDER={}; ELIG={}; VOL30={}
for n,key in enumerate(keys):
    j0=mstart[key]; t=int(PTS[j0]); k=pos[t]; lo=max(0,k-BARS30)
    vol30=cs[k]-cs[lo]; age=(t-first_ts)/86400.0
    elig=has&(age>=30)&(vol30>0)
    order=np.argsort(-vol30); order=order[elig[order]]
    ORDER[key]=order; ELIG[key]=elig; VOL30[key]=vol30
def mask_from(selfn):
    """selfn(key)->array of column indices allowed for that month; held for the month."""
    M=np.zeros((len(PTS),NW),bool)
    for n,key in enumerate(keys):
        j0=mstart[key]; j1=mstart[keys[n+1]] if n+1<len(keys) else len(PTS)
        sel=selfn(key); m=np.zeros(NW,bool); m[sel]=True; M[j0:j1]=m
    return M
MONTHLY449=mask_from(lambda key: ORDER[key][:449])
# ---- coin vector: recovered EXACTLY from the pinned pair where determinable ----
U0=np.load(HC+"/masks/umask_UPIT.npz",allow_pickle=True); UC=np.load(HC+"/masks/umask_UPIT_CRYPTO.npz",allow_pickle=True)
assert [str(s) for s in U0["symbols"]]==PSYM and [str(s) for s in UC["symbols"]]==PSYM
assert np.array_equal(U0["ts"].astype(np.int64),PTS) and np.array_equal(UC["ts"].astype(np.int64),PTS)
M0=np.asarray(U0["mask"]); MC=np.asarray(UC["mask"])
det=M0.any(0); coin=np.zeros(NW,bool); coin[det]=MC[:,det].any(0)
VC=json.load(open(R+"/venue_class_2026-09-11.json"))
undet=~det
for j in np.where(undet)[0]:
    s=PSYM[j]; coin[j]= (VC[s]["underlyingType"] in ("COIN","INDEX")) if s in VC else True
print("coin determinable from pinned masks:",int(det.sum()),"| from exchangeInfo:",int(undet.sum()),
      "| coin total",int(coin.sum()),flush=True)
# ---- G0 PARITY GATE ----
G0_upit=bool(np.array_equal(MONTHLY449,M0)); G0_crypto=bool(np.array_equal(MONTHLY449&coin[None,:],MC))
print("G0 parity: MONTHLY449 vs pinned UPIT  =",G0_upit,"| &coin vs pinned UPIT_CRYPTO =",G0_crypto,flush=True)
if not G0_upit:
    d=(MONTHLY449!=M0); print("   diff cells",int(d.sum()),"of",d.size,"| rows affected",int(d.any(1).sum()),
        "| cols affected",int(d.any(0).sum()),flush=True)
    rows=np.where(d.any(1))[0]
    if len(rows): print("   first diff anchor",time.strftime("%Y-%m-%d %H:%M",time.gmtime(int(PTS[rows[0]]))),flush=True)
# ---- quarter / annual holds ----
def hold_key(key,step):
    y,m=key
    if step=="qtr": mm=((m-1)//3)*3+1
    elif step=="ann": mm=1
    else: raise ValueError
    k=(y,mm)
    while k not in ORDER:      # walk forward to the first available month at/after the block start
        mm+=1
        if mm>12: mm=1; y+=1
        k=(y,mm)
        if (y,mm)>key: return key
    return k
ARMS={}
ARMS["MONTHLY449"]=MONTHLY449&coin[None,:]
ARMS["WIDE529"]  =mask_from(lambda key: ORDER[key][:529])&coin[None,:]
ARMS["WIDE600"]  =mask_from(lambda key: ORDER[key][:600])&coin[None,:]
ARMS["QTR449"]   =mask_from(lambda key: ORDER[hold_key(key,"qtr")][:449])&coin[None,:]
ARMS["ANN449"]   =mask_from(lambda key: ORDER[hold_key(key,"ann")][:449])&coin[None,:]
def noyoung(key,days=90):
    j0=mstart[key]; t=int(PTS[j0]); age=(t-first_ts)/86400.0
    o=ORDER[key]; o=o[age[o]>=days]; return o[:449]
ARMS["NOYOUNG90"]=mask_from(noyoung)&coin[None,:]
ARMS["DROPTAIL399"]=mask_from(lambda key: ORDER[key][:399])&coin[None,:]
summ={"G0":{"MONTHLY449_equals_pinned_UPIT":G0_upit,"MONTHLY449_coin_equals_pinned_UPIT_CRYPTO":G0_crypto},
      "cache":CACHE,"panel":PANEL,"n_months":len(keys),"coin_n":int(coin.sum()),
      "coin_determinable_from_pinned":int(det.sum()),"arms":{}}
yr=np.array([time.gmtime(int(t)).tm_year for t in PTS])
for nm,M in ARMS.items():
    p=R+"/masks/umask_R5_%s.npz"%nm
    np.savez_compressed(p,ts=PTS,symbols=np.array(PSYM),mask=M)
    sh=hashlib.sha256(open(p,"rb").read()).hexdigest()
    ov=float((M&MC).sum()/max(MC.sum(),1))
    by={str(y):round(float(M[yr==y].sum(1).mean()),1) for y in sorted(set(yr.tolist()))}
    summ["arms"][nm]={"file":p,"sha256_16":sh[:16],"allowed_mean":round(float(M.sum(1).mean()),1),
                      "allowed_by_year":by,"overlap_with_A0_mask":round(ov,4)}
    print("%-13s allowed %6.1f  overlap(A0) %.4f  %s"%(nm,M.sum(1).mean(),ov,by),flush=True)
# ---- listing-age matrix on the panel grid (for the sleeve + the descriptive listing study) ----
AGE=np.full((len(PTS),NW),np.nan)
for j,t in enumerate(PTS):
    a=(int(t)-first_ts)/86400.0
    AGE[j]=np.where(has&(a>=0),a,np.nan)
np.savez_compressed(R+"/agemat.npz",ts=PTS,symbols=np.array(PSYM),age_days=AGE.astype(np.float32),
                    first_ts=first_ts,has=has)
json.dump({PSYM[j]:(time.strftime("%Y-%m-%d",time.gmtime(int(first_ts[j]))) if has[j] else None) for j in range(NW)},
          open(R+"/listing_r5.json","w"),indent=0)
json.dump(summ,open(R+"/mask_summary_r5.json","w"),indent=1)
print("MASKS_DONE %.0fs"%(time.time()-t0),flush=True)
