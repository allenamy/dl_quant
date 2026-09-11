#!/usr/bin/env python3
"""
r9_screen STEP 2 -- COHORT_AGE_DECAY_CURVE, built at BOOK level on the v4 pinned caliber.

Backward attribution of ALREADY-REALISED P&L. No forward information anywhere:
  at anchor t we use only smr[t] (the book the device held, chosen at t from information <= t)
  and y4[t] (the return realised over [E_t+5m, E_t+4h+5m)). Ages come from the past weight path.

Two retirement conventions, both reported (the convention must not be load-bearing):
  PRORATA (primary): a shrinking position sheds every cohort proportionally. This is what an EMA
                     book literally does -- sm_t = sm_{t-1} + 0.1*(tgt_t - sm_{t-1}) scales the
                     whole fungible position.
  FIFO    (robustness): oldest lot retired first (biases surviving ages YOUNGER).

Caliber: g = net_ex/gross_total bps/4h anchor per unit gross. post-warm drop 900 (E-0911-A),
cut 2026-08-30 20Z (E-0911-D: this arm is PHI=0.45, VERIFIED from its own config_json).
Cost = pinned fitted costb_PWR_G230k.json tiers (blended maker/taker per tier), NOT the
device's costb_fee_steady -- the pinned model is 1.21x/1.34x/1.81x more expensive by tier.

E-0826-D ENV WHITELIST = THE EMPTY SET.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
# guard installed post-import (numpy reads its own runtime env at import); from here on any env read raises
_CONFIG_ENV_NAMES = ["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH",
    "LTRIM_TH","CDAMP","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ",
    "OUT_TAG","W3FIX","KMOD","KMOD_L","KMOD_F10","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE",
    "RNSM","FTPOS","SLEEVE","REF_SKIP","TILT","TILT_TAU","TILT_K","JUDGE_HC","V2","PANEL_IN"]
assert sorted([k for k in _CONFIG_ENV_NAMES if k in os.environ]) == []
def _forbid(*a, **k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get = _forbid

OUT  = "/workspace/uplift_2026-09-11/r9_screen"
ARCH = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
R8A0 = "/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
PANEL= "/workspace/data/wide_panel_4h_v2ext.npz"
UMSK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
COSTB= "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM = 900; CUT = T(2026,8,30,20); AMAX = 84          # bucket AMAX == "age >= AMAX" (>14 days)

A  = np.load(ARCH, allow_pickle=True); Bz = np.load(R8A0, allow_pickle=True)
cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
WA = np.asarray(A["d30_n2_c42_W"]); recB = np.asarray(Bz["d30_n2_c42_rec"], float)
tsB = np.round(recB[:,ci["ts"]]).astype(np.int64)
MT = np.load(META, allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; qvk=MT["qvk"]
PW = np.load(PANEL, allow_pickle=True); pts=PW["ts"].astype(np.int64)
pw_row={int(t):j for j,t in enumerate(pts)}
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"],8.0)
NW=len(PW["symbols"]); nA=len(E_ts)
uz=np.load(UMSK,allow_pickle=True); umap={int(t):k for k,t in enumerate(uz["ts"].astype(np.int64))}
UM=np.asarray(uz["mask"]); UROW={}
for j,t in enumerate(pts):
    k=umap.get(int(t))
    if k is not None: UROW[j]=UM[k]
CB=json.load(open(COSTB))["tiers"]
RATE=np.array([float(t["maker_share"])*float(t["maker_bps"])+(1-float(t["maker_share"]))*float(t["taker_bps"]) for t in CB])
def tier_of(q):
    t=np.full(len(q),2,np.int8); t[q>=1e6]=1; t[q>=5e6]=0; return t
MEM=np.empty(nA,dtype=object)
for i in range(nA):
    q=np.nan_to_num(qvk[i],nan=-1.0); o=np.argsort(-q); MEM[i]=o[q[o]>-0.5][:829]
pos={int(t):r for r,t in enumerate(tsB)}
NB=AMAX+1

def run(mode):
    Q=np.zeros((NW,NB)); HR=np.zeros(NW)
    nR=len(tsB)
    P=np.zeros((nR,NB)); C=np.zeros((nR,NB)); K=np.zeros((nR,NB))
    Gm=np.zeros((nR,NB)); Gt=np.zeros((nR,NB))
    t0=time.time()
    for i in range(nA):
        t=int(E_ts[i]); r=pos.get(t)
        if r is None: continue
        j=pw_row[t]; m=MEM[i]; mk=UROW.get(j)
        if mk is not None: m=m[mk[m]]
        sm=WA[r].astype(np.float64)
        smr=sm.copy(); nz=np.abs(sm)>1e-12
        if nz.any():
            smr[nz]-=smr[nz].mean(); g0=np.abs(sm).sum(); g1=np.abs(smr).sum()
            if g1>1e-9: smr*=g0/g1
        aw=np.abs(smr); ao=np.abs(HR)
        # --- age every surviving lot by one anchor
        Q2=np.empty_like(Q); Q2[:,0]=0.0; Q2[:,1:AMAX]=Q[:,0:AMAX-1]; Q2[:,AMAX]=Q[:,AMAX]+Q[:,AMAX-1]
        Q=Q2
        nzn=aw>1e-12; nzo=ao>1e-12
        same=nzn&nzo&(np.sign(smr)==np.sign(HR))
        kill=nzo&~same                      # sign flip or full exit -> close everything
        red=np.zeros(NW); new=np.zeros(NW)
        d=aw-ao
        inc=same&(d>0); dec=same&(d<0)
        new[inc]=d[inc]; red[dec]=-d[dec]
        red[kill]=ao[kill]; new[kill|(nzn&~nzo)]=aw[kill|(nzn&~nzo)]
        # --- retirement: which age buckets shed, and how much (needed for cost attribution)
        SHED=np.zeros((NW,NB))
        if kill.any():
            SHED[kill]=Q[kill]; Q[kill]=0.0
        idx=np.where(dec&(red>1e-15))[0]
        if len(idx):
            if mode=="PRORATA":
                fr=(red[idx]/np.maximum(ao[idx],1e-300))[:,None]
                sh=Q[idx]*fr; SHED[idx]+=sh; Q[idx]-=sh
            else:  # FIFO: oldest bucket first
                rem=red[idx].copy()
                for a in range(AMAX,-1,-1):
                    if not rem.any(): break
                    take=np.minimum(Q[idx,a],rem)
                    Q[idx,a]-=take; SHED[idx,a]+=take; rem-=take
        Q[:,0]+=new
        # --- attribute this anchor's realised P&L / carry / cost to the age buckets
        qv4h=np.expm1(np.clip(qvk[i,m],0,30))*48; tr=tier_of(qv4h); rt=RATE[tr]
        yv=np.nan_to_num(y4[i,m],nan=0.0)
        fnow=np.nan_to_num(FN[j,m],nan=0.0); ivv=IV[j,m]; ivv=np.where(np.isfinite(ivv)&(ivv>0),ivv,8.0)
        sg=np.sign(smr[m])
        Qm=Q[m]                                    # (nm, NB) lots held THROUGH this anchor
        P[r]=((sg*yv*1e4)[:,None]*Qm).sum(0)
        C[r]=((sg*fnow*(4.0/ivv)*1e4)[:,None]*Qm).sum(0)
        K[r]=(rt[:,None]*SHED[m]).sum(0); K[r,0]+=float((new[m]*rt).sum())
        Gm[r]=Qm.sum(0); Gt[r]=Q.sum(0)
        HR=smr
        if i%3000==0: print(mode,i,round(time.time()-t0,1),flush=True)
    return P,C,K,Gm,Gt

R={"env_whitelist":[],"caliber":"g = net_ex/gross_total bps/4h anchor per unit gross; post-warm 900 (E-0911-A); cut 2026-08-30 20Z (E-0911-D, arm PHI=0.45); cost = pinned costb_PWR_G230k.json",
   "AMAX_bucket_is_age_ge":AMAX,
   "sha256_16":{p:hashlib.sha256(open(p,'rb').read()).hexdigest()[:16] for p in (ARCH,R8A0,META,PANEL,UMSK,COSTB)}}
store={}
for mode in ("PRORATA","FIFO"):
    P,C,K,Gm,Gt=run(mode)
    store[mode]=(P,C,K,Gm,Gt)
    # identity checks against the device's own rec (pinned-cost rerun)
    R["identity_"+mode]={
      "pnl_ex_maxabs": float(np.max(np.abs(P.sum(1)-recB[:,ci["pnl_ex"]]))),
      "carry_ex_maxabs": float(np.max(np.abs(C.sum(1)-recB[:,ci["carry_ex"]]))),
      "cost_ex_maxabs": float(np.max(np.abs(K.sum(1)-recB[:,ci["cost_ex"]]))),
      "gross_total_maxabs": float(np.max(np.abs(Gt.sum(1)-recB[:,ci["gross_total"]]))),
    }
    print(mode,"IDENTITY",R["identity_"+mode],flush=True)
np.savez_compressed(OUT+"/cohort_arrays.npz", ts=tsB,
    **{f"{m}_{n}":v for m,(P,C,K,Gm,Gt) in store.items() for n,v in zip(("P","C","K","Gm","Gt"),(P,C,K,Gm,Gt))},
    rec=recB, cols=np.array(cols))
open(OUT+"/COHORT_IDENTITY.json","w").write(json.dumps(R,indent=1))
print(json.dumps(R,indent=1))
