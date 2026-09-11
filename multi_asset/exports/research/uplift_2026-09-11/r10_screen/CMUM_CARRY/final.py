"""CMUM_CARRY final screen. Tradability gate: COIN-M leg must have REALISED VOLUME>0 in the bar
(Binance emits frozen-price zero-volume klines for dormant contracts -> naive builders read fake alpha).
Sign convention: w_CM=+s/(2M), w_UM=-s/(2M); funding P&L of a leg = -w*f; pair = s/(2M)*[(f_UM-f_CM)+(r_CM-r_UM)].
Signal s=sign(h_UM-h_CM) from the LAST settlement at or before the anchor (strictly causal)."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","PANEL_IN","JUDGE_REQUIRE_W"): assert _v not in os.environ,_v
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TSf=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0gf=Z["A0g"];A0grossf=Z["A0gross"];A0turnf=Z["A0turn"]
names=[str(x) for x in Z["names"]]
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"]
N,n=D.shape
def ret(P):
    r=np.full_like(P,np.nan);r[1:]=P[1:]/P[:-1]-1.0;return r
rCM=ret(CMP);rUM=ret(UMP)
cmq=np.where(np.isfinite(CMV)&np.isfinite(CMP),CMV*CMP,0.0)
umq=np.nan_to_num(UMV,nan=0.0)
LIVE=np.zeros((N,n),bool); LIVE[1:]=(cmq[1:]>0)&(cmq[:-1]>0)&(umq[1:]>0)&(umq[:-1]>0)
EL=H&LIVE&np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
cov=(TSf<=CM_END)&(EL.sum(1)>=8)
TS=TSf[cov];A0g=A0gf[cov];A0gross=A0grossf[cov];A0turn=A0turnf[cov]
print("COVERED anchors %d / 9138  %s .. %s ; mean live names %.2f  min %d"%(cov.sum(),
  dt.datetime.utcfromtimestamp(TS[0]),dt.datetime.utcfromtimestamp(TS[-1]),EL[cov].sum(1).mean(),EL[cov].sum(1).min()))
CB=json.load(open(W+"/pin/costb_PWR_G230k.json"));TIER=np.array(CB["blended_bps_per_unit_turnover"])
def tier_of(q):
    t=np.full(q.shape,2,np.int64);t=np.where(q>=1e6,1,t);t=np.where(q>=5e6,0,t);return t
bpsUM=TIER[tier_of(umq)];bpsCM=TIER[tier_of(cmq)]
Rn=np.nan_to_num(R);DR=np.nan_to_num(rCM-rUM)
def book(s,cmmult=1.0):
    sg=np.where(EL,s,0.0);M=np.abs(sg).sum(1);Ms=np.where(M==0,np.nan,M)
    wl=np.nan_to_num(sg/(2.0*Ms[:,None]))
    carry=1e4*(wl*Rn).sum(1);price=1e4*(wl*DR).sum(1)
    dwl=np.abs(np.vstack([wl[:1],np.diff(wl,axis=0)]))
    turn=2.0*dwl.sum(1); cost=(dwl*(bpsUM+cmmult*bpsCM)).sum(1)
    return dict(carry=carry[cov],price=price[cov],cost=cost[cov],turn=turn[cov],
                gross=(carry+price)[cov],net=(carry+price-cost)[cov],M=np.nan_to_num(M)[cov])
day=(TS//86400).astype(np.int64);ud=np.unique(day);didx=[np.where(day==d)[0] for d in ud]
def bb(f,B=2000,base=20260905):
    out=np.empty(B)
    for b in range(B):
        rng=np.random.default_rng([base,b]);pick=rng.integers(0,len(ud),len(ud))
        ii=np.concatenate([didx[p] for p in pick]);out[b]=f(ii)
    return out
def ci(a):return [float(np.percentile(a,2.5)),float(np.percentile(a,97.5))]
Dn=np.nan_to_num(D)
ARMS={"A_last":np.sign(Dn)}
Df=np.where(H,Dn,np.nan)
for k in (6,30,90):
    a=2.0/(k+1);E=np.zeros_like(D);prev=np.zeros(n)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev);prev=(1-a)*prev+a*x;E[i]=prev
    ARMS["B_ema%d"%k]=np.sign(E)
for b in (0.10,0.25):
    th=b/1e4;s=np.zeros((N,n));prev=np.zeros(n)
    for i in range(N):
        cur=np.where(Dn[i]>th,1.0,np.where(Dn[i]<-th,-1.0,prev));s[i]=cur;prev=cur
    ARMS["C_hyst%.2f"%b]=s
ARMS["D_static_longCM"]=np.ones((N,n))
OUT={}
print(f"{'arm':18s}{'carry':>9s}{'price':>9s}{'GROSS':>9s}{'cost':>8s}{'NET':>9s}{'CI95':>22s}{'SR':>8s}{'turn':>8s}{'surv%':>8s}{'M':>6s}")
for tag,s in ARMS.items():
    B=book(s);g=B["net"]
    c=bb(lambda ii: g[ii].mean())
    sr=g.mean()/g.std(ddof=1)*np.sqrt(2190)
    d=dict(n=int(len(g)),carry=float(B["carry"].mean()),price=float(B["price"].mean()),gross=float(B["gross"].mean()),
        cost=float(B["cost"].mean()),net=float(g.mean()),net_ci=ci(c),sharpe=float(sr),se_sharpe=float(np.sqrt(2190/len(g))),
        sd=float(g.std(ddof=1)),turnover=float(B["turn"].mean()),
        cost_survival_pct=float(100*g.mean()/B["gross"].mean()) if B["gross"].mean()!=0 else None,
        gross_sharpe=float(B["gross"].mean()/B["gross"].std(ddof=1)*np.sqrt(2190)),names=float(B["M"].mean()))
    OUT[tag]=d
    print(f"{tag:18s}{d['carry']:+9.4f}{d['price']:+9.4f}{d['gross']:+9.4f}{d['cost']:8.4f}{d['net']:+9.4f}  [{d['net_ci'][0]:+8.4f},{d['net_ci'][1]:+8.4f}]{d['sharpe']:+8.3f}{d['turnover']:8.4f}{(d['cost_survival_pct'] if d['cost_survival_pct'] is not None else float('nan')):8.1f}{d['names']:6.1f}")
np.savez_compressed(W+"/final_series.npz",TS=TS,A0g=A0g,A0gross=A0gross,A0turn=A0turn,
   **{f"{t}_{k}":book(s)[k] for t,s in ARMS.items() for k in ("net","gross","carry","price","cost","turn")})
json.dump(OUT,open(W+"/STEP3_final_arms.json","w"),indent=1)
print("\nA0 on the same covered sub-axis: mean_g=%.4f SR=%.4f n=%d"%(A0g.mean(),A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190),len(A0g)))
