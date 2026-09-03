"""M1(fund 腿归一基变宽, 成交集不变)稳健性包 @jpline — PREREG_deploy_universe §评估. 输入: w10_uni2_*.npz(d30_n2_c42 部署平滑口径)."""
import numpy as np, json, time, sys, os
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]
    key=[k for k in z.files if k.endswith("_rec") and k.startswith("d30")][0]; rec=z[key]; W=z[key[:-4]+"_W"]
    return {c: rec[:,i] for i,c in enumerate(cols)}, W
def sharpe(x): x=np.asarray(x,float); x=x[np.isfinite(x)]; return float(x.mean()/(x.std()+1e-12)*np.sqrt(2190)) if len(x)>10 else float("nan")   # 判官同式
def yr(ts): return np.array([time.gmtime(int(t)).tm_year for t in ts])
def mon(ts): return np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
def bootstrap_ci(d, nb=2000, blk=30, seed=0):
    rng=np.random.default_rng(seed); n=len(d); out=[]
    for _ in range(nb):
        idx=np.concatenate([np.arange(s, min(s+blk,n)) for s in rng.integers(0,n,size=n//blk+1)])[:n]; out.append(d[idx].mean())
    return np.percentile(out,[2.5,97.5])
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64)
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); FN=P["f_fund_now"]; IV=P["f_fund_iv"] if "f_fund_iv" in P.files else None
prow={int(t):j for j,t in enumerate(pts)}
def sigfund(ts):   # 每锚 8h 当量费率横截面 std(bp), 全部有限名
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        f=FN[j]; iv=IV[j] if IV is not None else np.full_like(f,8.0); iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
pairs=[("N400rF_fx_s42","N829T400F_fx_s42","部署口径 W3FIX+FTRIM s42"),("N400rF_fx_s2027","N829T400F_fx_s2027","W3FIX+FTRIM s2027"),("N400rF_ms_s42","N829T400F_ms_s42","msharpe+FTRIM s42"),("N400r_fx_s42","N829T400_fx_s42","W3FIX 无FTRIM s42")]
for base,arm,lab in pairs:
    if not (os.path.exists(f"{PD}/w10_uni2_{base}.npz") and os.path.exists(f"{PD}/w10_uni2_{arm}.npz")): print("skip",lab); continue
    rb,Wb=load("uni2_"+base); ra,Wa=load("uni2_"+arm); ts=rb["ts"].astype(np.int64); assert (ts==ra["ts"].astype(np.int64)).all()
    nb_,na_=rb["net_ex"],ra["net_ex"]; d=na_-nb_; Y=yr(ts); s25=Y>=2025; s23=Y>=2023   # 判官口径列 net_ex
    print(f"\n==== {lab}: {arm} vs {base}")
    print(f"基线 net_ex 均/锚 2023+ {nb_[s23].mean():+.4f} std {nb_[s23].std():.3f} (判官单位) | Δ(判官) 2023+ {d[s23].mean():+.4f} | 2025-26 {d[s25].mean():+.4f} CI {np.round(bootstrap_ci(d[s25]),4)} | ΔSharpe 2023+ {sharpe(na_[s23])-sharpe(nb_[s23]):+.3f} 2025-26 {sharpe(na_[s25])-sharpe(nb_[s25]):+.3f} (基 {sharpe(nb_[s25]):.2f})")
    # 月度命中率
    mm=mon(ts[s25]); dm=d[s25]; months=np.unique(mm); hit=np.mean([dm[mm==m].sum()>0 for m in months]); print(f"月度 Δ>0 命中 {hit:.0%} ({len(months)} 月) | 逐月Δ(判官单位, 月合计) 最差 {min(dm[mm==m].sum() for m in months):+.2f} 最好 {max(dm[mm==m].sum() for m in months):+.2f}")
    # regime 条件: σ_fund 三分位 / nsel 三分位(2025-26)
    sf=sigfund(ts); q=np.nanpercentile(sf[s25],[33,67]); ns=rb["nsel"]; qn=np.nanpercentile(ns[s25],[33,67])
    for nm,v,qq in (("σ_fund",sf,q),("有效名数",ns,qn)):
        rows=[]
        for lo,hi,tag in ((-np.inf,qq[0],"低"),(qq[0],qq[1],"中"),(qq[1],np.inf,"高")):
            sel=s25&(v>lo)&(v<=hi); rows.append(f"{tag}[{np.nanmean(v[sel]):.1f}] Δ {d[sel].mean():+.4f} ΔS {sharpe(na_[sel])-sharpe(nb_[sel]):+.3f} n{sel.sum()}")
        print(f"regime {nm}: "+" | ".join(rows))
    # 杠杆表(净额线性缩放; 成本已含于 net? 装置 net 为 gross=1 口径 ⇒ ×L)
    # 杠杆表: net_ex 单位判定 —— 若 |均值| < 0.5 视为 "gross 的比例(小数)" 否则视为 bps; 报两口径
    unit = "bps" if abs(nb_[s23].mean())>0.05 else "frac"; conv = (1e-4 if unit=="bps" else 1.0)
    print(f"杠杆表(net_ex 单位判定={unit}; 年化=均×2190×L; DD=累计; ES5=最差5%锚均, %NAV):  基线 → 臂")
    for L in (1.5,2.0,2.5):
        for sel,tag in ((s23,"2023+"),(s25,"25-26")):
            def stats(x):
                x=x[sel]*L*conv; eq=np.cumsum(x); dd=(eq-np.maximum.accumulate(eq)).min(); es=np.mean(np.sort(x)[:max(int(len(x)*0.05),1)])
                return f"年化{x.mean()*2190:+.1%} S{sharpe(x):.2f} DD{dd:+.1%} ES5 {es:+.2%}"
            print(f"  {L}× {tag}: {stats(nb_)} → {stats(na_)}")
    # 权重差: Σ|Δw|/gross, 多空 gross, 集中度, 翻号名数(2025-26)
    G=np.abs(Wb).sum(1); Ga=np.abs(Wa).sum(1); ok=s25&(G>0)&(Ga>0)
    dw=np.abs(Wa-Wb).sum(1)/np.maximum(G,1e-9); ls_b=(np.clip(Wb,0,None).sum(1)/np.maximum(G,1e-9)); ls_a=(np.clip(Wa,0,None).sum(1)/np.maximum(Ga,1e-9))
    mx_b=np.abs(Wb).max(1)/np.maximum(G,1e-9); mx_a=np.abs(Wa).max(1)/np.maximum(Ga,1e-9)
    top10=lambda W_,G_: np.array([np.sort(np.abs(w))[-10:].sum() for w in W_])/np.maximum(G_,1e-9)
    flips=((np.sign(Wa)*np.sign(Wb))<0).sum(1)
    print(f"权重差 Σ|Δw|/gross 2025-26 中位 {np.median(dw[ok]):.3f} p90 {np.percentile(dw[ok],90):.3f} | 多头 gross 占比 基 {ls_b[ok].mean():.3f} 臂 {ls_a[ok].mean():.3f} | max|w|/gross 基 {mx_b[ok].mean():.4f} 臂 {mx_a[ok].mean():.4f} | top10 占比 基 {top10(Wb[ok],G[ok]).mean():.3f} 臂 {top10(Wa[ok],Ga[ok]).mean():.3f} | 翻号名/锚 均 {flips[ok].mean():.1f}")
    print(f"换手(Σ|Δw_t−w_t−1|/gross)2025-26: 基 {np.mean(np.abs(np.diff(Wb[s25],axis=0)).sum(1)/G[s25][1:]):.4f} 臂 {np.mean(np.abs(np.diff(Wa[s25],axis=0)).sum(1)/Ga[s25][1:]):.4f}")
print("M1_ROBUSTNESS_DONE")
