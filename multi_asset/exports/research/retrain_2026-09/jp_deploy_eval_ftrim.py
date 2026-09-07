"""候选① 部署前评估电池: 基线 vs pre(−∞,−10] zero, 两口径(msharpe 路径 / W3FIX 实盘席位), 双种子;
分 regime(年 / 离散度三分 / 市场涨跌平 / 费率σ三分 / 2026 逐月)× 分杠杆(1.5/2.0/2.5: 年化收益, 最大回撤, 最差日, −4%日数, −25%触线)。口径: net_ex bps/锚 of gross, 简单收益, 常 gross(leverage_killline_constgross)。"""
import numpy as np, time, sys, json
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    g=lambda k: rec[:,cols.index(k)].astype(float); return rec[:,cols.index("ts")].astype(np.int64), g("net_ex"), g("turnover"), g("carry_ex"), g("pnl_ex")
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
Y4=PW["Y4"]; FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
def regime_feats(ts):
    mk=np.full(len(ts),np.nan); sg=np.full(len(ts),np.nan); fs=np.full(len(ts),np.nan)
    for i,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        y=Y4[j]; y=y[np.isfinite(y)]; f=FN8[j]; f=f[np.isfinite(f)]
        if len(y)>50: mk[i]=np.median(y); sg[i]=np.std(y)
        if len(f)>50: fs[i]=np.std(f)
    return mk,sg,fs
def lev_metrics(net, ts, L):
    r=L*net*1e-4                       # 每锚 NAV 收益(常 gross 口径)
    days={}
    for t,x in zip(ts,r): days.setdefault(time.strftime("%Y-%m-%d",time.gmtime(int(t))),[]).append(x)
    dr=np.array([np.sum(v) for v in days.values()])   # 日收益(锚内简单加总近似)
    eq=np.cumprod(1+r); peak=np.maximum.accumulate(eq); dd=(eq/peak-1).min()
    ann=(eq[-1])**(365*6/len(r))-1
    kill=int((eq/peak-1<=-0.25).any()); bad=int((dr<=-0.04).sum())
    return ann, dd, dr.min(), bad, kill
PAIRS=[("msharpe s42","w10_canonpred_s42","w10_band_pre_all10_zero"),("msharpe s2027","w10_canonpred_s2027","w10_band_pre_all10_zero_s2027"),
       ("W3FIX s42","w10_canonfix_s42","w10_band_fix_all10z"),("W3FIX s2027","w10_canonfix_s2027","w10_band_fix_all10z_s2027")]
import os
for tag,bn,an in PAIRS:
    if not (os.path.exists(f"{PD}/{bn}.npz") and os.path.exists(f"{PD}/{an}.npz")): print(f"[{tag}] 缺文件 {bn}/{an}"); continue
    tb,nb,tob,cb,pb=load(bn); ta,na,toa,ca,pa=load(an)
    mb={int(t):i for i,t in enumerate(tb)}; ia=[]; ib=[]
    for k,t in enumerate(ta):
        i=mb.get(int(t)); 
        if i is not None: ia.append(k); ib.append(i)
    ia=np.array(ia); ib=np.array(ib); ts=tb[ib]; nb_=nb[ib]; na_=na[ia]; yrs=np.array([time.gmtime(int(t)).tm_year for t in ts]); sel=yrs>=2023
    ts=ts[sel]; nb_=nb_[sel]; na_=na_[sel]; yrs=yrs[sel]; d=na_-nb_
    mk,sg,fs=regime_feats(ts)
    print(f"\n===== [{tag}] 基线 {bn} vs 臂 {an} | 2023+ 锚 {len(ts)} =====")
    print(f"总: 基线 {nb_.mean():+.3f} 臂 {na_.mean():+.3f} Δ {d.mean():+.3f} bps/锚 | 换手 基 {tob[ib][sel].mean():.4f} 臂 {toa[ia][sel].mean():.4f} | carry 基 {cb[ib][sel].mean():+.3f} 臂 {ca[ia][sel].mean():+.3f} | 价差 基 {pb[ib][sel].mean():+.3f} 臂 {pa[ia][sel].mean():+.3f}")
    print("逐年 净 基/臂/Δ | 夏普 基/臂:")
    for Y in sorted(set(yrs)):
        s=yrs==Y; sh=lambda v: v.mean()/(v.std()+1e-12)*np.sqrt(2190)
        print(f"  {Y}: {nb_[s].mean():+.3f} / {na_[s].mean():+.3f} / {d[s].mean():+.3f} | {sh(nb_[s]):.2f} / {sh(na_[s]):.2f}")
    def tert(v):
        q=np.nanquantile(v,[1/3,2/3]); return np.where(v<=q[0],0,np.where(v<=q[1],1,2))
    for nm,v,labels in (("离散度σ(y4)",sg,("低","中","高")),("费率σ(8h)",fs,("低","中","高"))):
        t3=tert(v); print(f"{nm} 三分 Δ: "+" | ".join(f"{labels[k]} {d[(t3==k)&np.isfinite(v)].mean():+.3f}(n{int(((t3==k)&np.isfinite(v)).sum())})" for k in range(3)))
    down=mk<-0.01; up=mk>0.01; flat=np.abs(mk)<=0.01
    print(f"市场状态 Δ: 跌(<−1%) {d[down].mean():+.3f}(n{down.sum()}) | 平 {d[flat].mean():+.3f}(n{flat.sum()}) | 涨(>+1%) {d[up].mean():+.3f}(n{up.sum()}) ; 基线同态净 跌 {nb_[down].mean():+.2f} 平 {nb_[flat].mean():+.3f} 涨 {nb_[up].mean():+.2f}")
    m26=[(time.gmtime(int(t)).tm_mon) for t in ts]; m26=np.array(m26)
    print("2026 逐月 Δ: "+" ".join(f"{M:02d}:{d[(yrs==2026)&(m26==M)].mean():+.2f}" for M in range(1,9)))
    print("分杠杆(2023+ 全程, 常 gross): L | 基线 年化/最大回撤/最差日/−4%日数/−25%触线 || 臂 同序")
    for L in (1.5,2.0,2.5):
        a=lev_metrics(nb_,ts,L); b=lev_metrics(na_,ts,L)
        print(f"  {L}x | {a[0]*100:+.1f}% / {a[1]*100:.1f}% / {a[2]*100:.2f}% / {a[3]} / {a[4]} || {b[0]*100:+.1f}% / {b[1]*100:.1f}% / {b[2]*100:.2f}% / {b[3]} / {b[4]}")
    print("分杠杆 2026 单年: L | 基线 年化/最大回撤/最差日 || 臂")
    s26=yrs==2026
    for L in (1.5,2.0,2.5):
        a=lev_metrics(nb_[s26],ts[s26],L); b=lev_metrics(na_[s26],ts[s26],L)
        print(f"  {L}x | {a[0]*100:+.1f}% / {a[1]*100:.1f}% / {a[2]*100:.2f}% || {b[0]*100:+.1f}% / {b[1]*100:.1f}% / {b[2]*100:.2f}%")
print("DEPLOY_EVAL_DONE")
