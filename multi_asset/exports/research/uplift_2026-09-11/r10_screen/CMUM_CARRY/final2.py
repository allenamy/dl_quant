"""CMUM_CARRY: extended arms + STEP2 rho + STEP3 nulls + STEP4 downside + leakage checks."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TSf=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0gf=Z["A0g"];A0grossf=Z["A0gross"]
names=[str(x) for x in Z["names"]]
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"];N,n=D.shape
def ret(P):
    r=np.full_like(P,np.nan);r[1:]=P[1:]/P[:-1]-1.0;return r
rCM=ret(CMP);rUM=ret(UMP)
cmq=np.where(np.isfinite(CMV)&np.isfinite(CMP),CMV*CMP,0.0);umq=np.nan_to_num(UMV,nan=0.0)
LIVE=np.zeros((N,n),bool);LIVE[1:]=(cmq[1:]>0)&(cmq[:-1]>0)&(umq[1:]>0)&(umq[:-1]>0)
EL=H&LIVE&np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
cov=(TSf<=CM_END)&(EL.sum(1)>=8)
TS=TSf[cov];A0g=A0gf[cov];A0gross=A0grossf[cov]
CB=json.load(open(W+"/pin/costb_PWR_G230k.json"));TIER=np.array(CB["blended_bps_per_unit_turnover"])
def tier_of(q):
    t=np.full(q.shape,2,np.int64);t=np.where(q>=1e6,1,t);t=np.where(q>=5e6,0,t);return t
bpsUM=TIER[tier_of(umq)];bpsCM=TIER[tier_of(cmq)]
Rn=np.nan_to_num(R);DR=np.nan_to_num(rCM-rUM);Dn=np.nan_to_num(D);Df=np.where(H,Dn,np.nan)
def book(s,cmmult=1.0):
    sg=np.where(EL,s,0.0);M=np.abs(sg).sum(1);Ms=np.where(M==0,np.nan,M)
    wl=np.nan_to_num(sg/(2.0*Ms[:,None]))
    carry=1e4*(wl*Rn).sum(1);price=1e4*(wl*DR).sum(1)
    dwl=np.abs(np.vstack([wl[:1],np.diff(wl,axis=0)]))
    turn=2.0*dwl.sum(1);cost=(dwl*(bpsUM+cmmult*bpsCM)).sum(1)
    return dict(carry=carry[cov],price=price[cov],cost=cost[cov],turn=turn[cov],
                gross=(carry+price)[cov],net=(carry+price-cost)[cov],M=np.nan_to_num(M)[cov],wl=wl)
def ema_sign(k):
    a=2.0/(k+1);E=np.zeros_like(D);prev=np.zeros(n)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev);prev=(1-a)*prev+a*x;E[i]=prev
    return np.sign(E)
def hyst(b):
    th=b/1e4;s=np.zeros((N,n));prev=np.zeros(n)
    for i in range(N):
        cur=np.where(Dn[i]>th,1.0,np.where(Dn[i]<-th,-1.0,prev));s[i]=cur;prev=cur
    return s
ARMS={"A_last":np.sign(Dn),"B_ema90":ema_sign(90),"B_ema180":ema_sign(180),"B_ema360":ema_sign(360),
      "C_hyst0.25":hyst(0.25),"C_hyst0.50":hyst(0.50),"C_hyst1.00":hyst(1.00),
      "E_static_shortCM":-np.ones((N,n))}
day=(TS//86400).astype(np.int64);ud=np.unique(day);didx=[np.where(day==d)[0] for d in ud]
def bb(f,B=2000,base=20260905):
    out=np.empty(B)
    for b in range(B):
        rng=np.random.default_rng([base,b]);pick=rng.integers(0,len(ud),len(ud))
        ii=np.concatenate([didx[p] for p in pick]);out[b]=f(ii)
    return out
def ci(a):return [round(float(np.percentile(a,2.5)),4),round(float(np.percentile(a,97.5)),4)]
OUT={"cov_n":int(cov.sum()),"t0":str(dt.datetime.utcfromtimestamp(TS[0])),"t1":str(dt.datetime.utcfromtimestamp(TS[-1])),
     "A0_on_subaxis":{"mean_g":float(A0g.mean()),"sharpe":float(A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190)),"sd":float(A0g.std(ddof=1))}}
print(f"{'arm':18s}{'carry':>9s}{'price':>9s}{'GROSS':>9s}{'cost':>8s}{'NET':>9s}{'CI95':>22s}{'SR':>8s}{'turn':>8s}{'surv%':>8s}")
best=None
for tag,s in ARMS.items():
    B=book(s);g=B["net"];sr=g.mean()/g.std(ddof=1)*np.sqrt(2190)
    c=bb(lambda ii:g[ii].mean())
    d=dict(carry=round(float(B["carry"].mean()),4),price=round(float(B["price"].mean()),4),gross=round(float(B["gross"].mean()),4),
       cost=round(float(B["cost"].mean()),4),net=round(float(g.mean()),4),net_ci=ci(c),sharpe=round(float(sr),4),
       se_sharpe=round(float(np.sqrt(2190/len(g))),4),sd=round(float(g.std(ddof=1)),4),turnover=round(float(B["turn"].mean()),4),
       cost_survival_pct=round(float(100*g.mean()/B["gross"].mean()),1) if B["gross"].mean()!=0 else None,names=round(float(B["M"].mean()),1))
    OUT.setdefault("arms",{})[tag]=d
    print(f"{tag:18s}{d['carry']:+9.4f}{d['price']:+9.4f}{d['gross']:+9.4f}{d['cost']:8.4f}{d['net']:+9.4f}  [{d['net_ci'][0]:+8.4f},{d['net_ci'][1]:+8.4f}]{d['sharpe']:+8.3f}{d['turnover']:8.4f}{(d['cost_survival_pct'] or float('nan')):8.1f}")
    if best is None or sr>best[1]: best=(tag,sr,g,B)
TAG,SR,G,BB_=best
print("\nBEST ARM =",TAG,"SR=%.4f"%SR)
OUT["best_arm"]=TAG
# ---------- STEP2 rho ----------
def rho(a,b): return float(np.corrcoef(a,b)[0,1])
OUT["rho"]={"uncond_net":round(rho(G,A0g),4),"uncond_net_ci":ci(bb(lambda ii:rho(G[ii],A0g[ii]))),
            "uncond_gross":round(rho(BB_["gross"],A0gross),4)}
q=np.quantile(A0g,[0.1,0.2,0.8])
cells={"A0_bottom_quintile_anchor":A0g<=q[1],"A0_bottom_decile_anchor":A0g<=q[0],"A0_negative_anchor":A0g<0,"A0_top_quintile_anchor":A0g>=q[2]}
dsum={};
for d_ in ud: dsum[d_]=A0g[day==d_].mean()
dv=np.array([dsum[d_] for d_ in ud]);badday=set(ud[dv<=np.quantile(dv,0.2)].tolist())
cells["A0_worst_quintile_UTCday"]=np.array([d_ in badday for d_ in day])
OUT["rho_conditional"]={}
print("\ncell                          n     rho        CI95              cand_net    A0_g")
for cn,m in cells.items():
    r=rho(G[m],A0g[m])
    dd=day[m];uu=np.unique(dd);ix=[np.where(dd==x)[0] for x in uu]
    def f(_):
        rng=np.random.default_rng([20260905,_]);p=rng.integers(0,len(uu),len(uu))
        jj=np.concatenate([ix[t] for t in p]);a=G[m][jj];b=A0g[m][jj]
        return float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else 0.0
    cs=np.array([f(b_) for b_ in range(2000)])
    OUT["rho_conditional"][cn]=dict(n=int(m.sum()),rho=round(r,4),ci=ci(cs),cand_net=round(float(G[m].mean()),4),A0_g=round(float(A0g[m].mean()),4))
    print(f"{cn:28s}{m.sum():6d}{r:+8.4f}  [{ci(cs)[0]:+7.4f},{ci(cs)[1]:+7.4f}]  {G[m].mean():+9.4f}{A0g[m].mean():+9.4f}")
# ---------- STEP3 nulls (turnover-matched) ----------
S=ARMS[TAG]
NULLS={}
for d_ in (1,2,3):
    rng=np.random.default_rng([4242,d_]);pi=rng.permutation(n)
    NULLS["RELAB%d"%d_]=S[:,pi]
for k in (101,503,1009):
    Q=np.zeros_like(S);Q[k:]=S[:-k];NULLS["SHIFT%d"%k]=Q
print("\nnull            net       turn     (real net %.4f turn %.4f)"%(G.mean(),BB_["turn"].mean()))
nv=[]
for tag,s in NULLS.items():
    B=book(s);nv.append(B["net"].mean())
    OUT.setdefault("nulls",{})[tag]=dict(net=round(float(B["net"].mean()),4),turn=round(float(B["turn"].mean()),4),gross=round(float(B["gross"].mean()),4))
    print(f"{tag:14s}{B['net'].mean():+9.4f}{B['turn'].mean():9.4f}")
nv=np.array(nv);OUT["null_z"]=round(float((G.mean()-nv.mean())/nv.std(ddof=1)),3);OUT["null_beat"]=int((G.mean()>nv).sum())
print("real beats %d/6 nulls, z=%.3f"%(OUT["null_beat"],OUT["null_z"]))
# ---------- STEP4 downside ----------
dayret={};A0day={}
for d_ in ud: dayret[d_]=G[day==d_].sum();A0day[d_]=A0g[day==d_].sum()
gd=np.array([dayret[d_] for d_ in ud]);ad=np.array([A0day[d_] for d_ in ud])
cum=np.cumsum(gd);mdd=float((np.maximum.accumulate(cum)-cum).max())
acum=np.cumsum(ad);amdd=float((np.maximum.accumulate(acum)-acum).max())
comb=lambda a: np.cumsum(a)
OUT["downside"]=dict(worst_UTC_day_bps=round(float(gd.min()),3),worst_day_date=str(dt.datetime.utcfromtimestamp(int(ud[int(gd.argmin())])*86400).date()),
  best_UTC_day_bps=round(float(gd.max()),3),maxDD_bps=round(mdd,2),A0_worst_day_bps=round(float(ad.min()),3),A0_maxDD_bps=round(amdd,2),
  daily_sd_bps=round(float(gd.std(ddof=1)),3),skew=round(float(((gd-gd.mean())**3).mean()/gd.std()**3),3),
  frac_days_positive=round(float((gd>0).mean()),4))
b_=np.polyfit(A0g,G,1)[0]
OUT["downside"]["beta_to_A0"]=round(float(b_),4)
print("\nworst UTC day %.3f bps (A0 %.3f) ; maxDD %.1f bps (A0 %.1f) ; beta to A0 %.4f"%(gd.min(),ad.min(),mdd,amdd,b_))
# combined worst day at risk-parity-ish mixes
for wts in (0.25,0.5,1.0,2.0,4.0,8.0,13.7):
    cd=ad+wts*gd; OUT["downside"]["combo_x%.2f"%wts]=dict(worst_day=round(float(cd.min()),3),
      maxDD=round(float((np.maximum.accumulate(np.cumsum(cd))-np.cumsum(cd)).max()),2),
      sharpe=round(float((A0g+wts*G).mean()/(A0g+wts*G).std(ddof=1)*np.sqrt(2190)),4))
# ---------- leakage ----------
LK={}
# offset spectrum: corr(signal d at anchor i, realised pair spread R at anchor i+k) pooled over names
mm=EL[cov]
for k in (-3,-2,-1,0,1,2,3):
    a=np.roll(Dn[cov],-k,axis=0);b=Rn[cov]
    v=mm.copy()
    if k>0: v[-k:]=False
    if k<0: v[:(-k)]=False
    x=a[v];y=b[v]
    LK["offset_%+d"%k]=round(float(np.corrcoef(x,y)[0,1]),5)
# interventional: blank the funding arrays from a random anchor onward, signal before must be bit-identical
rngi=np.random.default_rng([20260905,777]);fails=0
for c in rngi.integers(1000,N-10,24):
    Dm=Dn.copy();Dm[c:]=0.0
    s1=hyst(0.25) if TAG=="C_hyst0.25" else None
    if s1 is None:
        A=np.sign(Dn);A2=np.sign(Dm)
    else:
        th=0.25/1e4;A=np.zeros((N,n));prev=np.zeros(n)
        for i in range(N):
            cur=np.where(Dn[i]>th,1.0,np.where(Dn[i]<-th,-1.0,prev));A[i]=cur;prev=cur
        A2=np.zeros((N,n));prev=np.zeros(n)
        for i in range(N):
            cur=np.where(Dm[i]>th,1.0,np.where(Dm[i]<-th,-1.0,prev));A2[i]=cur;prev=cur
    if not np.array_equal(A[:c],A2[:c]): fails+=1
LK["interventional_future_blank_fail"]=int(fails);LK["interventional_n"]=24
OUT["leakage"]=LK
print("\nleakage offsets",{k:v for k,v in LK.items() if k.startswith("offset")})
print("interventional failures %d/24"%fails)
json.dump(OUT,open(W+"/STEP234_full.json","w"),indent=1)
np.savez_compressed(W+"/best_series.npz",TS=TS,net=G,gross=BB_["gross"],carry=BB_["carry"],price=BB_["price"],cost=BB_["cost"],turn=BB_["turn"],A0g=A0g,A0gross=A0gross,tag=np.array(TAG))
