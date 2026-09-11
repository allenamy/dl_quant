"""CMUM_CARRY full screen. Sign convention derived explicitly:
  leg weights at anchor i for name k:  w_CM = +s/(2M),  w_UM = -s/(2M)   (s = +1 -> long COIN-M, short USDT-M)
  funding P&L for a leg = -w * f   (a long pays when f>0)
  => pair funding P&L = s/(2M) * (f_UM - f_CM) = s/(2M) * R
  => pair price   P&L = s/(2M) * (r_CM - r_UM)
  M = eligible names at that anchor; sum|w| over 2M legs = 1  => g is already bps per unit gross.
Signal: d = h_UM - h_CM (per-hour, last settled at or before the anchor). To RECEIVE, s = sign(d).
Returns r use close[i-1] -> close[i], i.e. the window [TS[i], TS[i]+4h) -- decided-at-TS[i], no lookahead.
"""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","PANEL_IN","JUDGE_REQUIRE_W"): assert _v not in os.environ,_v
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True)
K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TS=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0g=Z["A0g"];A0gross=Z["A0gross"];A0turn=Z["A0turn"]
names=[str(x) for x in Z["names"]]; ums=[str(x) for x in Z["um"]]
assert [str(x) for x in K["names"]]==names
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"]
N,n=D.shape
# --- returns over [TS[i], TS[i]+4h) : close[i]/close[i-1]-1
def ret(P):
    r=np.full_like(P,np.nan); r[1:]=P[1:]/P[:-1]-1.0
    return r
rCM=ret(CMP); rUM=ret(UMP)
PRICE_OK=np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
# --- eligibility
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
EL=H&PRICE_OK
covmask=(TS<=CM_END)&(EL.sum(1)>=10)
print("anchors covered %d / %d   %s .. %s"%(covmask.sum(),N,dt.datetime.utcfromtimestamp(TS[covmask][0]),dt.datetime.utcfromtimestamp(TS[covmask][-1])))
# --- cost tiers (pinned)
CB=json.load(open(W+"/pin/costb_PWR_G230k.json"))
TIER=np.array(CB["blended_bps_per_unit_turnover"])
print("tier bps/unit turnover",TIER.tolist())
# UM leg tier from the UM contract's own quote volume (qv over the 4h bar), same thresholds as the device
qv=UMV   # quote volume USDT per 4h bar
def tier_of(q):
    t=np.full(q.shape,2,np.int64); t=np.where(q>=1e6,1,t); t=np.where(q>=5e6,0,t); return t
TUM=tier_of(np.nan_to_num(qv,nan=0.0))
# CM leg: coin-margined; quote_volume column is in COIN -> convert with the CM price
cmq=np.nan_to_num(CMV,nan=0.0)*np.nan_to_num(CMP,nan=0.0)
TCM=tier_of(cmq)
bpsUM=TIER[TUM]; bpsCM=TIER[TCM]
def book(s,mask=covmask,bps_cm_mult=1.0):
    """s: (N,n) desired sign. returns dict of per-anchor series"""
    sg=np.where(EL,s,0.0)
    M=np.abs(sg).sum(1); M=np.where(M==0,np.nan,M)
    wl=sg/(2.0*M[:,None])                      # signed CM-leg weight; UM leg = -wl
    carry=1e4*(wl*np.nan_to_num(R)).sum(1)
    price=1e4*(wl*np.nan_to_num(rCM-rUM)).sum(1)
    dwl=np.abs(np.vstack([wl[:1],np.diff(wl,axis=0)]))
    turn=(2.0*dwl).sum(1)                      # both legs move by |dwl|
    cost=(dwl*(bpsUM+bpsCM*bps_cm_mult)).sum(1)
    gross_alpha=carry+price
    net=gross_alpha-cost
    return dict(carry=carry,price=price,gross=gross_alpha,cost=cost,net=net,turn=turn,M=np.nan_to_num(M))
def blockboot(x,B=2000,base=20260905):
    day=(TS//86400).astype(np.int64)
    ud=np.unique(day); idx={d:np.where(day==d)[0] for d in ud}
    out=np.empty(B)
    for b in range(B):
        rng=np.random.default_rng([base,b]); pick=rng.integers(0,len(ud),len(ud))
        ii=np.concatenate([idx[ud[p]] for p in pick]); out[b]=x[ii].mean()
    return out
def bootrho(x,y,B=2000,base=20260905):
    day=(TS//86400).astype(np.int64); ud=np.unique(day); idx={d:np.where(day==d)[0] for d in ud}
    out=np.empty(B)
    for b in range(B):
        rng=np.random.default_rng([base,b]); pick=rng.integers(0,len(ud),len(ud))
        ii=np.concatenate([idx[ud[p]] for p in pick])
        a=x[ii];c=y[ii]
        out[b]=np.corrcoef(a,c)[0,1] if a.std()>0 and c.std()>0 else 0.0
    return out
def summ(tag,B,mask):
    g=B["net"][mask]; gr=B["gross"][mask]; ca=B["carry"][mask]; pr=B["price"][mask]; co=B["cost"][mask]; tu=B["turn"][mask]
    bs=blockboot(np.where(mask,B["net"],0.0)[mask] if False else g,)
    sr=g.mean()/g.std(ddof=1)*np.sqrt(2190)
    d=dict(n=int(mask.sum()),carry=float(ca.mean()),price=float(pr.mean()),gross=float(gr.mean()),
        cost=float(co.mean()),net=float(g.mean()),net_ci=[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],
        sd=float(g.std(ddof=1)),sharpe=float(sr),se_sharpe=float(np.sqrt(2190/mask.sum())),
        turnover=float(tu.mean()),cost_survival_pct=float(100*g.mean()/gr.mean()) if gr.mean()!=0 else None,
        names=float(B["M"][mask].mean()))
    print(f"{tag:20s} n={d['n']:5d} carry={d['carry']:+7.4f} price={d['price']:+7.4f} GROSS={d['gross']:+7.4f} cost={d['cost']:7.4f} NET={d['net']:+7.4f} CI[{d['net_ci'][0]:+7.4f},{d['net_ci'][1]:+7.4f}] SR={d['sharpe']:+6.3f} turn={d['turnover']:6.4f} names={d['names']:5.1f}")
    return d
RES={}
# TS/mask restricted globals for bootstrap
TSfull=TS.copy()
TS=TS[covmask]
def restrict(B): return {k:(v[covmask] if isinstance(v,np.ndarray) and v.shape[0]==N else v) for k,v in B.items()}
m_all=np.ones(covmask.sum(),bool)
ARMS={}
Dn=np.nan_to_num(D)
ARMS["A_last"]=np.sign(Dn)
for k in (6,12,30,90):
    a=2.0/(k+1); E=np.zeros_like(D); prev=np.zeros(n)
    Df=np.where(H,Dn,np.nan)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev); prev=(1-a)*prev+a*x; E[i]=prev
    ARMS["B_ema%d"%k]=np.sign(E)
for b in (0.10,0.25):
    th=b/1e4; s=np.zeros((N,n)); prev=np.zeros(n)
    for i in range(N):
        cur=np.where(Dn[i]>th,1.0,np.where(Dn[i]<-th,-1.0,prev)); s[i]=cur; prev=cur
    ARMS["C_hyst%.2f"%b]=s
ARMS["D_static"]=-np.ones((N,n))   # persistent side, sign checked below
for tag,s in ARMS.items():
    B=restrict(book(s)); RES[tag]=summ(tag,B,m_all)
json.dump(RES,open(W+"/STEP3_arms.json","w"),indent=1)
np.savez_compressed(W+"/arms_series.npz",TS=TS,**{("%s_%s"%(t,k)):restrict(book(s))[k] for t,s in ARMS.items() for k in ("net","gross","carry","price","cost","turn")},
   A0g=A0g[covmask],A0gross=A0gross[covmask],A0turn=A0turn[covmask],covmask=covmask)
