"""全天候诊断 @jpline(PREREG_allweather_2026-09-04): H1 σ_fund gross 阶梯叠加, H2 β 对冲叠加, H3 三腿 msharpe 逐年。臂序列 = d30_n2_c42_rec(net_ex, 单位 gross bps)+ W。"""
import numpy as np, time, os, sys
PD="probe_artifacts"; B="pod_backup_2026-08-21"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]; mrow={int(t):i for i,t in enumerate(E)}
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); syms=[str(s) for s in P["symbols"]]; FN=P["f_fund_now"]; IV=P["f_fund_iv"]; prow={int(t):j for j,t in enumerate(pts)}; b=syms.index("BTCUSDT")
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float), W
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); ym=lambda ts: np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
def sigfund(ts):
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        f=FN[j]; iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
def stats(r, ts, L=2.0):
    x=L*r/1e4; eq=np.cumprod(1+x); n=len(x); ann=eq[-1]**(2190/n)-1; sh=x.mean()/(x.std()+1e-12)*np.sqrt(2190); dd=(eq/np.maximum.accumulate(eq)-1).min()
    return ann,sh,dd
def yearly(r, ts, lab):
    Y=yr(ts); row=[]
    for y in range(2021,2027):
        s=Y==y
        if s.sum()<100: continue
        a,sh,dd=stats(r[s],ts[s]); row.append(f"{y} {a:+.0%}/S{sh:.2f}/DD{dd:.0%}")
    a,sh,dd=stats(r[Y>=2021],ts[Y>=2021]); a2,sh2,dd2=stats(r[Y>=2023],ts[Y>=2023]); a3,sh3,dd3=stats(r[Y>=2025],ts[Y>=2025])
    print(f"  [{lab}] "+" | ".join(row)+f" || 2021+ {a:+.0%}/S{sh:.2f}/DD{dd:.0%} | 2023+ {a2:+.0%}/S{sh2:.2f}/DD{dd2:.0%} | 2025-26 {a3:+.0%}/S{sh3:.2f}/DD{dd3:.0%}")
def dci(d, sel, seed=0):
    rng=np.random.default_rng(seed); x=d[sel]; nb=len(x)//6; blocks=x[:nb*6].reshape(nb,6).sum(1); boots=np.array([blocks[rng.integers(0,nb,nb)].mean() for _ in range(4000)])/6
    return x.mean(), np.quantile(boots,0.025), np.quantile(boots,0.975)
ARMS={"C":"uni2_F_M7F_fx_s42","E":"uni2_N829T400F_fx_s42"}
print("=== 基臂逐年(2.0× 复利)===")
data={}
for k,tag in ARMS.items():
    ts,ne,W=load(tag); data[k]=(ts,ne,W); yearly(ne,ts,f"基臂 {k}")
# H1: σ_fund 阶梯
print("\n=== H1 σ_fund 条件化 gross 阶梯(因果滚动 2 年分位; 降 <p33 ×84 锚, 升 >p50 ×84 锚; 换档成本 3.5 bps×|Δg|)===")
for k,(ts,ne,W) in data.items():
    sf=sigfund(ts); roll=np.array([np.nanmean(sf[max(0,i-29):i+1]) for i in range(len(sf))])
    pct=np.full(len(ts),np.nan)
    for i in range(len(ts)):
        lo=max(0,i-4380); h=roll[lo:i+1]; h=h[np.isfinite(h)]
        if len(h)>=1000 and np.isfinite(roll[i]): pct[i]=np.mean(h<=roll[i])
    for glow,lab in ((0.5,"降至 0.5"),(0.0,"降至 0(全平)")):
        g=np.ones(len(ts)); cur=1.0; cl=0; ch=0
        for i in range(len(ts)):
            p=pct[i]
            if np.isfinite(p):
                cl=cl+1 if p<0.33 else 0; ch=ch+1 if p>0.50 else 0
                if cur==1.0 and cl>=84: cur=glow
                if cur<1.0 and ch>=84: cur=1.0
            g[i]=cur
        gprev=np.concatenate([[1.0],g[:-1]]); pl=gprev*ne-3.5*np.abs(g-gprev)
        Y=yr(ts); frac=np.mean(g[Y>=2021]<1.0); m,lo,hi=dci(pl-ne, Y>=2023)
        yearly(pl,ts,f"H1 {k} {lab} | 低档时间占比 {frac:.0%} | 2023+ Δ {m:+.3f} CI[{lo:+.3f},{hi:+.3f}]")
        print(f"      低档年份占比: "+", ".join(f"{y}:{np.mean(g[Y==y]<1):.0%}" for y in range(2021,2027)))
# H2: β 对冲
print("\n=== H2 β 对冲叠加(180 锚滚动 β on y4 vs BTC y4; h=0.5/1.0; 成本 1 bps×|Δ(hβ)|)===")
yb=y4[:,b]
for k,(ts,ne,W) in data.items():
    idx=np.array([mrow.get(int(t),-1) for t in ts]); ok=idx>=0
    beta_book=np.full(len(ts),np.nan)
    # 逐名 β: 滚动 180 锚 cov/var, 只用 ≤t 的 y4(t 锚的 y4 是 t→t+4h 的未来收益 ⇒ 用到 i-1 为止)
    Yb=np.nan_to_num(yb,nan=0.0); Y4=np.nan_to_num(y4,nan=0.0); fin=np.isfinite(y4).astype(float)
    cs_xy=np.cumsum(Y4*Yb[:,None],axis=0); cs_x=np.cumsum(Y4,axis=0); cs_y=np.cumsum(Yb); cs_yy=np.cumsum(Yb*Yb); cs_n=np.cumsum(fin,axis=0)
    for p,i in enumerate(idx):
        if i<181: continue
        hi=i-1; lo=i-181; n=cs_n[hi]-cs_n[lo]; sxy=cs_xy[hi]-cs_xy[lo]; sx=cs_x[hi]-cs_x[lo]; sy=cs_y[hi]-cs_y[lo]; syy=cs_yy[hi]-cs_yy[lo]; nn=hi-lo
        var=syy/nn-(sy/nn)**2; cov=sxy/np.maximum(n,1)-(sx/np.maximum(n,1))*(sy/nn); beta=np.where(n>120, cov/max(var,1e-12), np.nan)
        w=W[p]; g=np.abs(w).sum()
        if g>0:
            m_=np.isfinite(beta)&(w!=0); beta_book[p]=float((w[m_]*beta[m_]).sum()/g)
    Y=yr(ts); print(f"  [{k}] β_book/gross: 2021+ 均 {np.nanmean(beta_book[Y>=2021]):+.3f}, 2025-26 均 {np.nanmean(beta_book[Y>=2025]):+.3f}")
    for h in (0.5,1.0):
        hb=np.nan_to_num(h*beta_book,nan=0.0); hedge=-hb*np.nan_to_num(yb[idx],nan=0.0)*1e4 - 1.0*np.abs(np.diff(np.concatenate([[0],hb])))
        pl=ne+hedge; m,lo,hi=dci(pl-ne, Y>=2023); yearly(pl,ts,f"H2 {k} h={h} | 2023+ Δ {m:+.3f} CI[{lo:+.3f},{hi:+.3f}]")
print("ALLWEATHER_DONE")
