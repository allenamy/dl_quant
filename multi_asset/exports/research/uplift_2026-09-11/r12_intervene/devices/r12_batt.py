"""r12 BATTERY. Criteria frozen by PREREG_r12 sha 17dd2db7b116b262 BEFORE any arm number.
g = net_ex/gross_total (bps/anchor/unit gross).  ALPHA: post-warm drop 900 (E-0911-A), n=9199.
TAIL/HALT: NO warm drop (task constraint 4), whole UTC days.  Bootstrap: UTC-day blocks, B=2000,
numpy.default_rng([20260905,k]), k in {0,9}.  Bonferroni K=29 -> pct 0.086207/99.913793.
ENV whitelist = EMPTY SET, asserted."""
import os, sys, json, time, calendar, hashlib, glob
import numpy as np
_W=["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","W3FIX","MEMBERS_TOPN","FTRIM","FTRIM_TH","FTPOS",
    "CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","UMASK_NPZ","UMASK_SCOPE","COSTB_JSON","SLOW_NPY"]
assert {k:os.environ[k] for k in _W if k in os.environ}=={}
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"; T=f"{R}/dev_ext/probe_artifacts"
APY=2190; WARM=900; NB=2000; K_DECL=29
PLO=100*(0.05/K_DECL)/2; PHI_=100-PLO
RATE_BOOK=2.9537                                  # costb_PWR_G230k book average, bps/unit turnover
SHARE=[0.3092,0.4041,0.2867]; TAKER=[5.874314,6.487762,8.09014]
RATE_TAKER=float(sum(s*t for s,t in zip(SHARE,TAKER)))
REPRICE=3.2167                                    # contested costtruth multiple (r11 §2), UNRESOLVED
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ",time.gmtime(int(t)))
MON=np.load(f"{R}/out/monitors.npz",allow_pickle=True)
ts=MON["ts"].astype(np.int64); SIG=MON["sig"]; IC=MON["ic"]; PATH=np.asarray(MON["path5m"],np.float64)
COLS=[str(c) for c in MON["cols"]]; C={k:i for i,k in enumerate(COLS)}
nA=len(ts); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
SIG_T1,SIG_T2=2.643969560695577,8.31055264894391   # full-sample tertiles, REPORTING cells only
def regime_cell(s):
    return np.where(np.isnan(s),"NA",np.where(s<SIG_T1,"sigLOW",np.where(s<SIG_T2,"sigMID","sigHIGH")))
RC=regime_cell(SIG)
# ---------- arm loading ----------
def load_dev(tag):
    Z=np.load(f"{T}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    Rr=np.asarray(Z["d30_n2_c42_rec"],float)
    assert np.array_equal(np.round(Rr[:,C["ts"]]).astype(np.int64),ts), tag+" ts axis"
    gt=Rr[:,C["gross_total"]]
    D=np.asarray(Z["d30_n2_c42_DIAG"],float) if "d30_n2_c42_DIAG" in Z.files else None
    return {"g":Rr[:,C["net_ex"]]/gt,"p":Rr[:,C["pnl_ex"]]/gt,"c":Rr[:,C["carry_ex"]]/gt,
            "k":Rr[:,C["cost_ex"]]/gt,"tov":Rr[:,C["cost_ex"]]/gt/RATE_BOOK,   # matched caliber, executor
            "tovf":Rr[:,C["turnover"]]/gt,"gross":gt,"e":np.ones(nA),"DIAG":D,"kind":"device"}
A0=load_dev("R12_GATEP_s42")
# unit self-check demanded by the brief: cost/gross ÷ turnover/gross must equal the model rate
UC={"mean_cost_per_gross":float(A0["k"].mean()),"mean_turn_ex_per_gross":float(A0["tov"].mean()),
    "ratio":float(A0["k"].mean()/A0["tov"].mean()),"model_rate":RATE_BOOK,
    "raw_turnover_mean_file_caliber":float(np.mean(np.asarray(np.load(f"{T}/w10_ablation_series_R12_GATEP_s42.npz",allow_pickle=True)["d30_n2_c42_rec"],float)[:,C["turnover"]])),
    "mean_gross_total":float(A0["gross"].mean())}
assert abs(UC["ratio"]-RATE_BOOK)<1e-6, UC
# ---------- overlay arms (I-2 leverage, I-4 intra-anchor stop) ----------
def trail_mean(x,L):
    out=np.full(len(x),np.nan)
    v=np.nan_to_num(x); f=np.isfinite(x).astype(float)
    cs=np.concatenate([[0.0],np.cumsum(v)]); cn=np.concatenate([[0.0],np.cumsum(f)])
    for i in range(L,len(x)):
        n=cn[i]-cn[i-L]
        if n>=L/2: out[i]=(cs[i]-cs[i-L])/n
    return out
def overlay_ICO(L,th,lam):
    tr=trail_mean(IC,L)
    e=np.where(np.isfinite(tr)&(tr<th),lam,1.0)
    fire=(np.isfinite(tr)&(tr<th)).astype(float)
    de=np.abs(np.diff(np.concatenate([[1.0],e])))
    extra=de*RATE_BOOK                         # scheduled anchor trade => maker/book-average rate
    g=e*A0["g"]-extra
    return {"g":g,"p":e*A0["p"],"c":e*A0["c"],"k":e*A0["k"]+extra,"tov":e*A0["tov"]+de,
            "tovf":e*A0["tovf"]+de,"gross":A0["gross"],"e":e,"fire":fire,"kind":"overlay"}
p_i=A0["p"]; c_i=A0["c"]; k_i=A0["k"]
PATHc=PATH+(p_i-PATH[:,47])[:,None]*(np.arange(1,49)[None,:]/48.0)   # endpoint-matched, bounded
PATHc=np.where(np.isfinite(PATHc),PATHc,np.repeat(p_i[:,None],48,1)*(np.arange(1,49)[None,:]/48.0))
days=ts//86400; ud,inv=np.unique(days,return_inverse=True)
DAY_IDX=[np.where(inv==d)[0] for d in range(len(ud))]
def overlay_IAS(th_pct,phi,L=2.0):
    g=np.empty(nA); e=np.ones(nA); fire=np.zeros(nA); tov=np.empty(nA); kk=np.empty(nA)
    pp=np.empty(nA); cc=np.empty(nA)
    for idxs in DAY_IDX:
        F=1.0; cur=1.0; tripped=False
        for a,p in enumerate(idxs):
            ecost=0.0
            if not tripped:
                dayc=F*(1.0+L*PATHc[p]/1e4)-1.0
                hit=np.where(dayc<=th_pct)[0]
                if len(hit):
                    Kh=int(hit[0]); tripped=True; fire[p]=1.0
                    price=1.0*PATHc[p,Kh]+phi*(p_i[p]-PATHc[p,Kh])
                    ecost=abs(1.0-phi)*RATE_TAKER
                    pp[p]=price; cc[p]=c_i[p]; kk[p]=k_i[p]+ecost; tov[p]=A0["tov"][p]+abs(1.0-phi)
                    e[p]=phi
                else:
                    pp[p]=p_i[p]; cc[p]=c_i[p]; kk[p]=k_i[p]; tov[p]=A0["tov"][p]; e[p]=1.0
            else:
                pp[p]=phi*p_i[p]; cc[p]=phi*c_i[p]; kk[p]=phi*k_i[p]; tov[p]=phi*A0["tov"][p]; e[p]=phi
            g[p]=pp[p]-cc[p]-kk[p]
            F=F*(1.0+L*g[p]/1e4)
        if tripped:   # resume at next UTC day open: scheduled trade back to full gross
            nxt=idxs[-1]+1
            if nxt<nA:
                g[nxt]=g[nxt] if False else g[nxt]
    # resume cost is charged on the first anchor of the following day
    for di,idxs in enumerate(DAY_IDX):
        if fire[idxs].sum()>0 and di+1<len(DAY_IDX):
            p0=DAY_IDX[di+1][0]; rc=abs(1.0-phi)*RATE_BOOK
            kk[p0]+=rc; tov[p0]+=abs(1.0-phi); g[p0]-=rc
    return {"g":g,"p":pp,"c":cc,"k":kk,"tov":tov,"tovf":tov,"gross":A0["gross"],"e":e,"fire":fire,"kind":"overlay"}
ARMS={}
for tag in sorted(glob.glob(f"{T}/w10_ablation_series_R12_*.npz")):
    t=os.path.basename(tag)[len("w10_ablation_series_"):-4]
    if t=="R12_GATEP_s42": continue
    ARMS[t]=load_dev(t)
for L in (24,42):
    for th in (-0.0228,-0.0443):
        for lam in (0.5,0.0):
            ARMS["R12_ICO_L%d_th%s_lam%02d"%(L,str(abs(th)).replace("0.",""),int(lam*100))]=overlay_ICO(L,th,lam)
for thp,nm in ((-0.0200,"200"),(-0.0268,"268"),(-0.0300,"300")):
    for phi in (0.0,0.5):
        ARMS["R12_IAS_th%s_phi%02d"%(nm,int(phi*100))]=overlay_IAS(thp,phi)
print("arms:",len(ARMS),flush=True)
# ---------- statistics ----------
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
def prep(x,d):
    ud2,inv2=np.unique(d,return_inverse=True); nd=len(ud2)
    return nd,np.bincount(inv2,minlength=nd).astype(float),np.bincount(inv2,weights=x,minlength=nd),np.bincount(inv2,weights=x*x,minlength=nd)
def boot_pair(a,s,d,k,B=NB):
    nd,n,sa,qa=prep(a,d); _,_,ss,qs=prep(s,d)
    rng=np.random.default_rng([20260905,k]); idx=rng.integers(0,nd,size=(B,nd))
    def msd(S,Q):
        N=n[idx].sum(1); SS=S[idx].sum(1); QQ=Q[idx].sum(1); mu=SS/N
        return mu,np.sqrt(np.maximum((QQ-N*mu*mu)/(N-1.0),0.0))
    ma,da=msd(sa,qa); ms,ds=msd(ss,qs)
    return (ms/ds-ma/da)*np.sqrt(APY), ms-ma
def cis(v): return {"ci95":[float(np.percentile(v,2.5)),float(np.percentile(v,97.5))],
                    "ci_bonf%d"%K_DECL:[float(np.percentile(v,PLO)),float(np.percentile(v,PHI_))]}
# alpha window
slP=slice(WARM,None); tsP=ts[slP]; dP=tsP//86400
assert len(tsP)==9199
# tail window: whole UTC days, NO warm drop
ud_all,cnt_all=np.unique(days,return_counts=True); full=ud_all[cnt_all==6]
mT=np.isin(days,full); NDAY=len(full)
def daily(gv,L):
    G=gv[mT].reshape(NDAY,6); return np.prod(1.0+L*G/1e4,axis=1)-1.0, np.cumprod(1.0+L*G/1e4,axis=1)-1.0
def maxdd(dr):
    nav=np.concatenate([[1.0],np.cumprod(1.0+dr)]); return float((1.0-nav/np.maximum.accumulate(nav)).max())
OUT={"prereg_sha256":"17dd2db7b116b2625f6e7eacab7caf9eb025876e1a3f564f32429f31a2ea551f",
     "device_sha256":sha(f"{R}/w12_intervene.py"),"pinned_sha256":sha(f"{U}/w10_sleeve.py"),
     "self_sha256":sha(os.path.abspath(__file__)),"env_whitelist":[],"K_declared":K_DECL,
     "B_boot":NB,"rate_book":RATE_BOOK,"rate_taker":RATE_TAKER,"reprice_multiple":REPRICE,
     "unit_selfcheck":UC,"n_alpha":int(len(tsP)),"n_tail_days":int(NDAY),
     "tail_window":[iso(ts[mT][0]),iso(ts[mT][-1])],"alpha_window":[iso(tsP[0]),iso(tsP[-1])],
     "sigma_tertiles":[SIG_T1,SIG_T2],"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
     "A0":{},"arms":{}}
def tailblock(gv,L):
    dr,ip=daily(gv,L)
    out={"worst_day_pct":float(dr.min()*100),"maxDD_pct":float(maxdd(dr)*100),
         "ann_vol_pct":float(dr.std(ddof=1)*np.sqrt(365)*100),
         "cagr_pct":float(((np.prod(1.0+dr))**(365.0/NDAY)-1.0)*100)}
    for th,nm in ((-0.02,"le2.00"),(-0.0268,"le2.68"),(-0.03,"le3.00"),(-0.04,"le4.00"),(-0.05,"le5.00")):
        n_cc=int((dr<=th).sum()); n_id=int((ip.min(1)<=th).sum())
        out[nm]={"n":n_cc,"per_yr":round(n_cc/NDAY*365,4),"touch_n":n_id,"touch_per_yr":round(n_id/NDAY*365,4)}
    return out
OUT["A0"]={"mean_g":float(A0["g"][slP].mean()),"sharpe":sr(A0["g"][slP]),
           "turn_per_gross":float(A0["tov"][slP].mean()),"cost_per_gross":float(A0["k"][slP].mean()),
           "carry_per_gross":float(A0["c"][slP].mean()),
           "tail_2.0x":tailblock(A0["g"],2.0),"tail_2.81x":tailblock(A0["g"],2.81),
           "by_year":{str(y):{"mean_g":float(A0["g"][(yrs==y)].mean()),"sharpe":sr(A0["g"][(yrs==y)])} for y in sorted(set(yrs.tolist()))},
           "by_regime":{c:{"n":int((RC==c).sum()),"mean_g":float(A0["g"][RC==c].mean()),"sharpe":sr(A0["g"][RC==c])} for c in ("sigLOW","sigMID","sigHIGH")}}
a=A0["g"][slP]
for tag,S in sorted(ARMS.items()):
    s=S["g"][slP]
    D,G=boot_pair(a,s,dP,0); D9,G9=boot_pair(a,s,dP,9)
    if S["kind"]=="device" and S["DIAG"] is not None:
        DG=S["DIAG"]; DC=["ts","bill_pre","bill_post","cem_fire","cem_n","cem_th","byp_fire","a_ema","s6","byp_q","mkt_med"]
        fr=DG[:,DC.index("cem_fire")]+DG[:,DC.index("byp_fire")]
    else: fr=S.get("fire",np.zeros(nA))
    row={"kind":S["kind"],"n":int(len(s)),"mean_g":float(s.mean()),"sharpe":sr(s),
         "dg":float(s.mean()-a.mean()),"dSharpe":sr(s)-sr(a),
         "dg_k0":cis(G),"dg_k9":cis(G9),"dSharpe_k0":cis(D),"dSharpe_k9":cis(D9),
         "dpnl":float(S["p"][slP].mean()-A0["p"][slP].mean()),
         "dcarry":float(S["c"][slP].mean()-A0["c"][slP].mean()),
         "dcost":float(S["k"][slP].mean()-A0["k"][slP].mean()),
         "turn_per_gross":float(S["tov"][slP].mean()),
         "dturn_per_gross":float(S["tov"][slP].mean()-A0["tov"][slP].mean()),
         "dturn_frac_pct":float(100*(S["tov"][slP].mean()/A0["tov"][slP].mean()-1.0)),
         "fire_rate_pct":float(100*fr[slP].mean()),"fire_n":int(fr[slP].sum()),
         "rho_to_A0":float(np.corrcoef(a,s)[0,1]),
         "tail_2.0x":tailblock(S["g"],2.0),"tail_2.81x":tailblock(S["g"],2.81),
         "by_year_dg":{str(y):float(S["g"][yrs==y].mean()-A0["g"][yrs==y].mean()) for y in sorted(set(yrs.tolist()))},
         "by_year_dSharpe":{str(y):sr(S["g"][yrs==y])-sr(A0["g"][yrs==y]) for y in sorted(set(yrs.tolist()))},
         "by_regime_dg":{c:float(S["g"][RC==c].mean()-A0["g"][RC==c].mean()) for c in ("sigLOW","sigMID","sigHIGH")},
         "by_regime_dSharpe":{c:sr(S["g"][RC==c])-sr(A0["g"][RC==c]) for c in ("sigLOW","sigMID","sigHIGH")}}
    row["identity_resid"]=float((row["dpnl"]-row["dcarry"]-row["dcost"])-row["dg"])
    row["cost_surv_frac"]=float(1-row["dcost"]/row["dpnl"]) if abs(row["dpnl"])>1e-12 else None
    # sign of the change under the CONTESTED 3.2167x repricing
    row["dg_reprice3.2x"]=float(row["dg"]-(REPRICE-1.0)*RATE_BOOK*row["dturn_per_gross"])
    row["dnav_pct_yr_at_2x"]=float(row["dg"]*APY*2.0/1e4*100)
    OUT["arms"][tag]=row
    t2=row["tail_2.0x"]; a2=OUT["A0"]["tail_2.0x"]
    print("%-34s dg %+.5f [%+.4f,%+.4f]b29  dSR %+.4f  dturn %+.2f%%  fire %5.2f%%  worstday %+.3f(A0 %+.3f)  le4/yr %.3f(A0 %.3f)"%(
        tag,row["dg"],row["dg_k0"]["ci_bonf%d"%K_DECL][0],row["dg_k0"]["ci_bonf%d"%K_DECL][1],row["dSharpe"],
        row["dturn_frac_pct"],row["fire_rate_pct"],t2["worst_day_pct"],a2["worst_day_pct"],
        t2["le4.00"]["per_yr"],a2["le4.00"]["per_yr"]),flush=True)
json.dump(OUT,open(f"{R}/out/BATTERY_r12.json","w"),indent=1)
print("BATTERY_DONE")
