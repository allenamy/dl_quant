#!/usr/bin/env python3
"""r11_live_vs_replay_vol.py -- why the halt is touched more often than the ladder says:
decompose the live/replay DAILY volatility ratio into (a) per-anchor vol and (b) within-day
serial correlation, then read the halt frequency at the live-vol-equivalent gross.
READ-ONLY. Env whitelist = EMPTY SET (E-0826-D)."""
import os, json, time, calendar, hashlib
import numpy as np
ENV_WHITELIST = []
_W = ["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","COSTB_JSON","SLOW_NPY","UMASK_NPZ",
      "UMASK_SCOPE","JUDGE_HC","PANEL_IN","OMP_NUM_THREADS","PYTHONHASHSEED"]
_s = {k: os.environ[k] for k in _W if k in os.environ}; assert _s == {}, _s

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
PIN  = f"{ROOT}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()

Z=np.load(PIN,allow_pickle=True); CFG=json.loads(str(Z["config_json"]))
assert CFG["UPLIFT"]["self_sha256"][:16]=="b88e35a46b93d712"
COLS=[str(c) for c in Z["cols"]]; C={k:i for i,k in enumerate(COLS)}; R=Z["rec"]
ts=R[:,0].astype(np.int64); g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
UB=calendar.timegm(time.strptime("2026-08-30 20","%Y-%m-%d %H"))
m=np.zeros(len(ts),bool); m[900:]=True; m &= ts<=UB
gp=g[m]; NDAY=len(gp)//6; G=gp.reshape(NDAY,6)

def stats(L):
    r=L*G/1e4
    dr=np.prod(1+r,axis=1)-1
    return dict(anchor_sd_pct=float(r.std(ddof=1)*100), daily_sd_pct=float(dr.std(ddof=1)*100),
                var_ratio=float(dr.var(ddof=1)/(6*r.var(ddof=1))),
                sqrt6_x_anchor_sd_pct=float(r.std(ddof=1)*100*np.sqrt(6)))
REP2=stats(2.0)
REP2["anchor_sd_bps_per_gross"]=float(gp.std(ddof=1))
REP2["anchor_lag1_autocorr_within_window"]=float(np.corrcoef(gp[:-1],gp[1:])[0,1])

# --- live, first hand, same read-only device as stoploss_frequency/devices/stop_stats.py -------
LIVE = {"source":"~/dl_quant_live/state/live/pilot_log/*/daily_nav.jsonl (READ-ONLY)",
        "recomputed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
import glob, statistics as st
root=os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
days=sorted(os.path.basename(d) for d in glob.glob(root+"/2026*") if os.path.isdir(d))
rows=[];prev=None;recs=[]
for d in days:
    p=f"{root}/{d}/daily_nav.jsonl"
    rr=[json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
    if not rr: continue
    last=rr[-1];nav=float(last["nav"])
    flows=[float(r.get("external_flow_usdt") or 0.0) for r in rr]
    flow=max(flows,key=abs) if flows else 0.0
    lev=(float(last.get("target_gross") or 0.0)/nav) if nav else 0.0
    wd=None if (abs(flow)>1e-9 or prev in (None,0)) else (nav-prev)/prev*100
    rows.append(dict(day=d,wd=wd,lev=lev));prev=nav
    for r in rr: recs.append(dict(day=d,nav=float(r["nav"]),flow=float(r.get("external_flow_usdt") or 0.0),
                                  tg=float(r.get("target_gross") or 0.0)))
J=[r for r in rows if r["wd"] is not None]
v2=[r["wd"]*2.0/r["lev"] for r in J if r["lev"]>0.2]
ser=[]
for i in range(1,len(recs)):
    a,b=recs[i-1],recs[i]
    df=(b["flow"]-a["flow"]) if b["day"]==a["day"] else b["flow"]
    if abs(df)<1e-6: ser.append(dict(day=b["day"],r=(b["nav"]-df-a["nav"])/a["nav"]*100,
                                     lev=(b["tg"]/b["nav"] if b["nav"] else 0.0)))
an=[x["r"]*2.0/x["lev"] for x in ser if x["lev"]>0.2]
LIVE.update({"n_calendar_days":len(rows),"n_judgeable_days":len(J),
             "daily_sd_pct_raw":float(st.stdev([r["wd"] for r in J])),
             "daily_sd_pct_2x_equivalent":float(st.stdev(v2)),"n_days_2x_equiv":len(v2),
             "anchor_sd_pct_2x_equivalent":float(st.stdev(an)),"n_anchors_2x_equiv":len(an),
             "breaches":{"le_4.00":[(r["day"],round(r["wd"],3)) for r in J if r["wd"]<=-4.0],
                         "le_2.68":[(r["day"],round(r["wd"],3)) for r in J if r["wd"]<=-2.68],
                         "le_2.00":[(r["day"],round(r["wd"],3)) for r in J if r["wd"]<=-2.0]}})
LIVE["variance_ratio_2x_equiv"]=LIVE["daily_sd_pct_2x_equivalent"]**2/(6*LIVE["anchor_sd_pct_2x_equivalent"]**2)

# --- decomposition and the live-vol-equivalent gross -------------------------------------------
ra=LIVE["anchor_sd_pct_2x_equivalent"]/REP2["anchor_sd_pct"]
rv=np.sqrt(LIVE["variance_ratio_2x_equiv"]/REP2["var_ratio"])
rd=LIVE["daily_sd_pct_2x_equivalent"]/REP2["daily_sd_pct"]
DEC={"per_anchor_vol_ratio_live_over_replay":float(ra),
     "within_day_serial_corr_ratio":float(rv),"product":float(ra*rv),
     "observed_daily_vol_ratio":float(rd),
     "reading":"daily vol ratio = per-anchor vol ratio x sqrt(variance-ratio ratio); the product "
               "should reproduce the observed daily ratio."}
# chi2 CI on the live daily sd (n-1 dof), for the equivalent-gross interval
from math import sqrt
n=LIVE["n_days_2x_equiv"]; dof=n-1
try:
    from scipy.stats import chi2
    lo=LIVE["daily_sd_pct_2x_equivalent"]*sqrt(dof/chi2.ppf(0.975,dof))
    hi=LIVE["daily_sd_pct_2x_equivalent"]*sqrt(dof/chi2.ppf(0.025,dof))
except Exception:
    lo=hi=None
EQ={"replay_daily_sd_pct_at_2x":REP2["daily_sd_pct"],
    "live_daily_sd_pct_2x_equiv":LIVE["daily_sd_pct_2x_equivalent"],
    "live_vol_equivalent_gross":2.0*rd,
    "live_vol_equivalent_gross_CI95_from_sd_chi2":
        ([2.0*lo/REP2["daily_sd_pct"], 2.0*hi/REP2["daily_sd_pct"]] if lo else None),
    "note":"the gross at which the REPLAY book would have the DAILY volatility the LIVE book has actually shown"}

# halt frequency at that equivalent gross, same bootstrap contract as r11_tail.py
NB=2000
def boot_halt(L,line=-0.04):
    h=np.empty(NB,int); mdd=np.empty(NB); cg=np.empty(NB)
    for k in range(NB):
        rng=np.random.default_rng([20260905,k]); idx=rng.integers(0,NDAY,365)
        Gs=G[idx]; f=1.0+L*Gs/1e4
        dr=np.prod(f,axis=1)-1.0
        h[k]=int((dr<=line).sum())
        nav=np.concatenate([[1.0],np.cumprod(1+dr)]); mdd[k]=float((1-nav/np.maximum.accumulate(nav)).max())
        cg[k]=np.prod(1+dr)-1.0
    return {"L":L,"E_halt_per_yr":float(h.mean()),"P_ge1":float((h>=1).mean()),
            "P_ge2":float((h>=2).mean()),"P_ge3":float((h>=3).mean()),
            "median_maxDD_pct":float(np.percentile(mdd,50)*100),
            "P_maxDD_ge25":float((mdd>=0.25).mean()),
            "median_cagr_pct":float(np.percentile(cg,50)*100)}
EQ["halt_at_live_vol_equivalent_gross"]=boot_halt(round(2.0*rd,2))
EQ["halt_at_2.00x_for_contrast"]=boot_halt(2.0)

# Kelly optimum, unconstrained, on the empirical daily distribution (NOT drawdown aware)
KEL=[]
for L in [round(0.5+0.1*i,1) for i in range(0,86)]:
    dr=np.prod(1+L*G/1e4,axis=1)-1.0
    KEL.append((L,float(np.log1p(dr).mean()*365*100)))
kbest=max(KEL,key=lambda t:t[1])
OUT={"env_whitelist":ENV_WHITELIST,"gpu_used":False,"live_written":False,"network_used":False,
     "inputs":{"pin_npz":{"path":PIN,"sha256":sha256(PIN)}},
     "device_self_sha256":sha256(os.path.abspath(__file__)),
     "replay_primary_window_at_2x":REP2,"live":LIVE,"vol_decomposition":DEC,
     "equivalent_gross":EQ,
     "kelly_unconstrained":{"L_star":kbest[0],"E_log_growth_ann_pct":kbest[1],
        "caveat":"expected-log-growth is scale-greedy and NOT drawdown aware; reported only to show "
                 "that the binding constraint here is drawdown, not growth"}}
json.dump(OUT,open(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_live_vs_replay_vol_2026-09-12.json","w"),indent=1)
print(json.dumps({k:OUT[k] for k in ("replay_primary_window_at_2x","vol_decomposition","equivalent_gross","kelly_unconstrained")},indent=1))
print("LIVE",json.dumps(LIVE,indent=1))
