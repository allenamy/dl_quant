"""STEP3b cost sensitivity on the COIN-M leg + STEP4b capacity/quanto arithmetic + combo curve."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TSf=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0gf=Z["A0g"];names=[str(x) for x in Z["names"]]
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"];N,n=D.shape
def ret(P):
    r=np.full_like(P,np.nan);r[1:]=P[1:]/P[:-1]-1.0;return r
rCM=ret(CMP);rUM=ret(UMP)
cmq=np.where(np.isfinite(CMV)&np.isfinite(CMP),CMV*CMP,0.0);umq=np.nan_to_num(UMV,nan=0.0)
LIVE=np.zeros((N,n),bool);LIVE[1:]=(cmq[1:]>0)&(cmq[:-1]>0)&(umq[1:]>0)&(umq[:-1]>0)
EL=H&LIVE&np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
cov=(TSf<=CM_END)&(EL.sum(1)>=8);TS=TSf[cov];A0g=A0gf[cov]
CB=json.load(open(W+"/pin/costb_PWR_G230k.json"));TIER=np.array(CB["blended_bps_per_unit_turnover"])
def tier_of(q):
    t=np.full(q.shape,2,np.int64);t=np.where(q>=1e6,1,t);t=np.where(q>=5e6,0,t);return t
bpsUM=TIER[tier_of(umq)];bpsCM=TIER[tier_of(cmq)]
Rn=np.nan_to_num(R);DR=np.nan_to_num(rCM-rUM);Dn=np.nan_to_num(D);Df=np.where(H,Dn,np.nan)
def ema_sign(k):
    a=2.0/(k+1);E=np.zeros_like(D);prev=np.zeros(n)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev);prev=(1-a)*prev+a*x;E[i]=prev
    return np.sign(E)
def book(s,cmmult=1.0):
    sg=np.where(EL,s,0.0);M=np.abs(sg).sum(1);Ms=np.where(M==0,np.nan,M)
    wl=np.nan_to_num(sg/(2.0*Ms[:,None]))
    carry=1e4*(wl*Rn).sum(1);price=1e4*(wl*DR).sum(1)
    dwl=np.abs(np.vstack([wl[:1],np.diff(wl,axis=0)]))
    return dict(gross=(carry+price)[cov],cost=(dwl*(bpsUM+cmmult*bpsCM)).sum(1)[cov],
                turn=(2.0*dwl.sum(1))[cov],wl=wl)
OUT={}
S=ema_sign(360);SS=-np.ones((N,n))
print("COIN-M leg cost multiplier sensitivity (the fitted model was calibrated on USDT-M LOB only)")
print(f"{'x_cm':>6s}{'B_ema360 net':>14s}{'SR':>8s}{'  |  '}{'E_static net':>14s}{'SR':>8s}")
for m in (1,2,2.72,3,5,10):
    r=[]
    for s in (S,SS):
        B=book(s,m);g=B["gross"]-B["cost"]
        r.append((g.mean(),g.mean()/g.std(ddof=1)*np.sqrt(2190)))
    OUT["cmmult_%.2f"%m]=dict(ema360_net=round(r[0][0],4),ema360_sr=round(r[0][1],3),static_net=round(r[1][0],4),static_sr=round(r[1][1],3))
    print(f"{m:6.2f}{r[0][0]:+14.4f}{r[0][1]:+8.3f}  |  {r[1][0]:+14.4f}{r[1][1]:+8.3f}")
# break-even multiplier
for tag,s in (("B_ema360",S),("E_static_shortCM",SS)):
    B=book(s,1.0); be=B["gross"].mean()/ (B["cost"].mean()) if B["cost"].mean()>0 else None
    OUT["breakeven_cm_mult_"+tag]=round(float(be),2)
    print("break-even COIN-M cost multiplier, %s = %.2f x"%(tag,be))
# --- venue depth ratio: COIN-M vs USDT-M traded USD per 4h, on the 20 live names
live20=[k for k in range(n) if (cmq[cov,k]>0).mean()>0.95]
print("\nnames live in >95%% of covered anchors: %d"%len(live20))
rows=[]
for k in live20:
    m=(cmq[cov,k]>0)&(umq[cov,k]>0)
    rows.append((names[k],float(np.median(cmq[cov,k][m])),float(np.median(umq[cov,k][m]))))
rat=np.array([r[1]/r[2] for r in rows])
print(f"{'name':16s}{'CM USD/4h':>14s}{'UM USD/4h':>16s}{'CM/UM':>9s}")
for r in sorted(rows,key=lambda z:z[1]/z[2]):
    print(f"{r[0]:16s}{r[1]:14.0f}{r[2]:16.0f}{r[1]/r[2]:9.4f}")
OUT["venue_depth"]=dict(n_names=len(rows),cm_um_volume_ratio_median=round(float(np.median(rat)),4),
   cm_um_volume_ratio_min=round(float(rat.min()),4),cm_um_volume_ratio_max=round(float(rat.max()),4),
   cm_usd_4h_median_smallest=round(float(min(r[1] for r in rows)),0),rows=[[r[0],round(r[1]),round(r[2])] for r in rows])
print("\nCOIN-M / USDT-M traded-USD ratio: median %.4f  min %.4f  max %.4f"%(np.median(rat),rat.min(),rat.max()))
# --- capacity / quanto at the desk's scale
G0=CB["calibration"]["gross_usdt"]; NAV=G0/2.0
B=book(S,1.0);Mn=np.nan_to_num(np.abs(np.where(EL,S,0.0)).sum(1))[cov].mean()
print("\nA0 book gross $%.0f (NAV $%.0f at 2.0x). candidate live names/anchor %.1f"%(G0,NAV,Mn))
for x in (1,2,4,8,13.7):
    Gc=G0*x; per_leg=Gc/(2*Mn)
    im10=0.5*Gc*0.10   # COIN-M half of gross, 10x max leverage -> coin collateral
    OUT.setdefault("capacity",{})["x%.2f"%x]=dict(cand_gross_usd=round(Gc),per_leg_usd=round(per_leg),
        per_leg_vs_smallest_cm_4h_vol=round(float(per_leg/min(r[1] for r in rows)),4),
        coin_collateral_usd_at_10x=round(im10),coin_collateral_pct_of_NAV=round(100*im10/NAV,1))
    print("x%-5.2f gross $%-10.0f per-COIN-M-leg $%-9.0f = %5.1f%% of the SMALLEST live name's median 4h COIN-M volume ; coin collateral @10x = $%-9.0f = %.0f%% of NAV"%(
        x,Gc,per_leg,100*per_leg/min(r[1] for r in rows),im10,100*im10/NAV))
# --- combo curve fine
g=book(S,1.0);GG=g["gross"]-g["cost"]
print("\nx   combined Sharpe   (A0 alone %.4f)"%(A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190)))
cc={}
for x in (0,0.5,1,2,3,4,6,8,10,13.7,20,40):
    c=A0g+x*GG;cc["%.2f"%x]=round(float(c.mean()/c.std(ddof=1)*np.sqrt(2190)),4)
    print("%6.2f  %.4f"%(x,cc["%.2f"%x]))
OUT["combo_sharpe_vs_x"]=cc
OUT["max_theoretical"]=round(float(np.sqrt((A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190))**2+(GG.mean()/GG.std(ddof=1)*np.sqrt(2190))**2)),4)
print("theoretical uncorrelated cap sqrt(S_A0^2+S_c^2) = %.4f"%OUT["max_theoretical"])
json.dump(OUT,open(W+"/STEP345_capacity.json","w"),indent=1)
