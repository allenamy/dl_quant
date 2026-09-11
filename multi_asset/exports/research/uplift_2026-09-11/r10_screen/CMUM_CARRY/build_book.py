"""CMUM_CARRY builder. FROZEN SPEC (written before any P&L was looked at):
 signal  d_n(i) = h_UM(<=t_i) - h_CM(<=t_i)   [per-HOUR funding rate, last settled at or before anchor]
 position: sigma_n(i) = sign(d_n(i)) ; long CM / short UM when sigma=+1 (we then RECEIVE f_UM, PAY f_CM)
 realised per-name pair funding over [t_i,t_i+4h):  F_n(i) = sum(UM rates in (t_i,t_i+4h]) - sum(CM rates in (t_i,t_i+4h])
 book: equal weight, sum|w| = 1 over 2N legs -> each leg |w| = 1/(2N)
 carry_bps(i) = 1e4 * (1/(2N_i)) * sum_n sigma_n(i)*F_n(i)
 turnover(i)  = (1/(2N)) * sum_n |sigma_n(i) - sigma_n(i-1)| * 2legs   (per unit gross, both legs trade)
NO LOOKAHEAD: every quantity at index i uses only calc_time <= t_i for the signal.
No network, no live touch, no GPU."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","PANEL_IN"): assert _v not in os.environ, _v
W=os.path.dirname(os.path.abspath(__file__))
F=np.load(W+"/funding_raw.npz",allow_pickle=True)
A0=np.load(W+"/pin/A0_PWR230k_s42.npz",allow_pickle=True)
cols=[str(c) for c in A0["cols"]]; rec=A0["rec"]
ts_all=rec[:,cols.index("ts")].astype(np.int64)
POST=900; CAP=int(dt.datetime(2026,8,30,20,tzinfo=dt.timezone.utc).timestamp())
sel=np.zeros(len(ts_all),bool); sel[POST:]=True; sel&= (ts_all<=CAP)
TS=ts_all[sel]
A0g=rec[sel,cols.index("net_ex")]/rec[sel,cols.index("gross_total")]
A0gross=rec[sel,cols.index("pnl_ex")]/rec[sel,cols.index("gross_total")]
A0turn=rec[sel,cols.index("turnover")]/rec[sel,cols.index("gross_total")]
assert len(TS)==9138 and np.all(np.diff(TS)==14400)
print("A0 VERIFIED n=%d mean_g=%.4f SR=%.4f turn=%.4f"%(len(TS),A0g.mean(),A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190),A0turn.mean()))
pairs=[l.split() for l in open(W+"/raw_listings/pairs_all.txt") if l.strip()]
N=len(TS)
def grid(arr):
    """returns (last_hourly[N], realised_sum[N], have[N]) for one leg"""
    t=(arr[:,0]/1000.0).astype(np.int64); iv=arr[:,1]; r=arr[:,2]
    h=r/np.where(iv>0,iv,8.0)
    last=np.full(N,np.nan); real=np.zeros(N); have=np.zeros(N,bool)
    # last settled at or before TS[i]
    j=np.searchsorted(t,TS,side="right")-1
    ok=j>=0
    last[ok]=h[j[ok]]
    age=np.full(N,1e18); age[ok]=TS[ok]-t[j[ok]]
    have=ok&(age<=36*3600)          # stale guard: settlement within 36h
    # realised in (TS[i], TS[i]+4h]
    lo=np.searchsorted(t,TS,side="right"); hi=np.searchsorted(t,TS+14400,side="right")
    cs=np.concatenate([[0.0],np.cumsum(r)])
    real=cs[hi]-cs[lo]
    return last,real,have
SIG={};REAL={};HAVE={};NAMES=[]
for cmS,umS in pairs:
    if ("CM_"+cmS) not in F or ("UM_"+umS) not in F: continue
    lc,rc,hc=grid(F["CM_"+cmS]); lu,ru,hu=grid(F["UM_"+umS])
    NAMES.append((cmS,umS))
    SIG[cmS]=lu-lc; REAL[cmS]=ru-rc; HAVE[cmS]=hc&hu&np.isfinite(lu-lc)
n=len(NAMES); print("names built",n)
D=np.array([SIG[c] for c,_ in NAMES]).T        # (N, n) signal spread per hour
Rr=np.array([REAL[c] for c,_ in NAMES]).T      # (N, n) realised 4h spread
H=np.array([HAVE[c] for c,_ in NAMES]).T       # (N, n)
np.savez_compressed(W+"/book_inputs.npz",TS=TS,D=D,R=Rr,H=H,
   names=np.array([c for c,_ in NAMES]),um=np.array([u for _,u in NAMES]),
   A0g=A0g,A0gross=A0gross,A0turn=A0turn)
# ---- STEP1c magnitude diagnostics
out={}
cnt=H.sum(1); print("eligible names per anchor: mean %.2f min %d max %d"%(cnt.mean(),cnt.min(),cnt.max()))
dd=np.where(H,D,np.nan)
out["spread_per_hour_abs_mean_bps"]=float(np.nanmean(np.abs(dd))*1e4)
out["spread_per_hour_median_abs_bps"]=float(np.nanmedian(np.abs(dd))*1e4)
out["spread_per_4h_abs_mean_bps"]=float(np.nanmean(np.abs(dd))*1e4*4)
rr=np.where(H,Rr,np.nan)
out["realised_4h_spread_abs_mean_bps"]=float(np.nanmean(np.abs(rr))*1e4)
out["realised_4h_spread_mean_bps"]=float(np.nanmean(rr)*1e4)
# persistence: corr(sign(d_i), realised_i)
sg=np.sign(dd); harv=sg*rr
out["harvest_per_name_per_anchor_bps"]=float(np.nanmean(harv)*1e4)
out["hit_rate_sign"]=float(np.nanmean((harv>0).astype(float)[np.isfinite(harv)&(rr!=0)]))
out["eligible_names_mean"]=float(cnt.mean()); out["eligible_names_min"]=int(cnt.min())
print(json.dumps(out,indent=1))
json.dump(out,open(W+"/STEP1c_magnitude.json","w"),indent=1)
