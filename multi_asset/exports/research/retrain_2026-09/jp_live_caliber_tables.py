"""实盘口径回放表 @jpline(2026-09-04): 逐年 × 杠杆(2.0/2.5)复利收益/夏普/最大回撤/最差月/ES5 + regime 分档; 臂 = 实盘口径链(W3FIX 固定席位 + FTRIM 部署态 [+ 冻结宇宙仿真 / + M1])。
复利: equity_{t+1} = equity_t × (1 + L × net_ex_t/1e4)(net_ex = 单位 gross 每锚净额 bps, 含 carry 与成本模型); 年化 = 复利^(2190/n) − 1; 夏普 = 均/std × √2190(与杠杆无关)。"""
import numpy as np, time, os
PD="probe_artifacts"; B="pod_backup_2026-08-21"
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    g=lambda k: rec[:,cols.index(k)].astype(float); return rec[:,cols.index("ts")].astype(np.int64), g("net_ex"), g("nsel")
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts]); ym=lambda ts: np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=P["ts"].astype(np.int64); FN=P["f_fund_now"]; IV=P["f_fund_iv"]; prow={int(t):j for j,t in enumerate(pts)}
def sigfund(ts):
    out=np.full(len(ts),np.nan)
    for k,t in enumerate(ts):
        j=prow.get(int(t))
        if j is None: continue
        f=FN[j]; iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); r=f*(8.0/iv); r=r[np.isfinite(r)]
        if len(r)>50: out[k]=np.std(r)*1e4
    return out
def stats(r, L, ts):
    x=L*r/1e4; eq=np.cumprod(1+x); n=len(x); ann=eq[-1]**(2190/n)-1 if n>0 else np.nan; sh=x.mean()/(x.std()+1e-12)*np.sqrt(2190)
    dd=(eq/np.maximum.accumulate(eq)-1).min(); es=np.mean(np.sort(x)[:max(int(n*0.05),1)])
    mm=ym(ts); months=np.unique(mm); wm=min(np.prod(1+x[mm==m])-1 for m in months) if len(months) else np.nan
    return ann, sh, dd, es, wm, n
ARMS=[("canonfix_s42","A 动态400·W3FIX(无FTRIM)"),("uni2_N400rF_fx_s42","B 动态400·W3FIX+FTRIM(部署态)"),("uni2_F_M7F_fx_s42","C 冻结450月刷·W3FIX+FTRIM(实盘≈现状)"),("uni2_F_QF_fx_s42","D 冻结450季刷·W3FIX+FTRIM(陈旧下界)"),("uni2_N829T400F_fx_s42","E 动态400+M1·W3FIX+FTRIM(实盘 M1 后目标)")]
data={}
for tag,lab in ARMS:
    if os.path.exists(f"{PD}/w10_{tag}.npz"): data[lab]=load(tag)
    else: print("缺", tag)
print("=== 逐年 × 杠杆(复利年化 / 夏普 / 最大回撤 / 最差月 / ES5 每锚)===")
for lab,(ts,ne,ns) in data.items():
    Y=yr(ts); print(f"\n[{lab}]")
    for L in (2.0,2.5):
        row=[]
        for y in range(2021,2027):
            s=Y==y
            if s.sum()<100: continue
            ann,sh,dd,es,wm,n=stats(ne[s],L,ts[s]); row.append(f"{y}: {ann:+.0%} S{sh:.2f} DD{dd:.0%} 月min{wm:+.1%} ES5{es*1e4:+.0f}bp")
        s=Y>=2023; ann,sh,dd,es,wm,n=stats(ne[s],L,ts[s]); row.append(f"2023+: {ann:+.0%} S{sh:.2f} DD{dd:.0%} 月min{wm:+.1%}")
        s=Y>=2025; ann,sh,dd,es,wm,n=stats(ne[s],L,ts[s]); row.append(f"2025-26: {ann:+.0%} S{sh:.2f} DD{dd:.0%} 月min{wm:+.1%}")
        print(f"  {L}× | "+" | ".join(row))
print("\n=== regime 分档(臂 C 实盘现状 与 臂 B 部署态; 2.0×; 复利年化 / 夏普 / 锚数)===")
for lab in [l for l in data if l.startswith("C") or l.startswith("B") or l.startswith("E")]:
    ts,ne,ns=data[lab]; Y=yr(ts); sf=sigfund(ts)
    for per,sel0 in (("2023+",Y>=2023),("2025-26",Y>=2025)):
        q=np.nanpercentile(sf[sel0],[33,67]); qn=np.nanpercentile(ns[sel0],[33,67]); parts=[]
        for nm,v,qq in (("σ_fund",sf,q),("广度",ns,qn)):
            for lo,hi,tag in ((-np.inf,qq[0],"低"),(qq[0],qq[1],"中"),(qq[1],np.inf,"高")):
                s=sel0&(v>lo)&(v<=hi)
                if s.sum()<50: continue
                ann,sh,dd,es,wm,n=stats(ne[s],2.0,ts[s]); parts.append(f"{nm}{tag}[{np.nanmean(v[s]):.0f}] {ann:+.0%}/S{sh:.2f}/n{n}")
        print(f"  [{lab}] {per}: "+" | ".join(parts))
print("\n=== 实盘口径调整(臂 C, 2.0×, 2023+ 与 2025-26): 扣执行保真 0.3 bps/锚 ===")
ts,ne,ns=data[[l for l in data if l.startswith("C")][0]]; Y=yr(ts)
for per,sel0 in (("2023+",Y>=2023),("2025-26",Y>=2025)):
    for adj in (0.0,0.3):
        ann,sh,dd,es,wm,n=stats(ne[sel0]-adj,2.0,ts[sel0]); print(f"  {per} 扣 {adj} bps/锚: 年化 {ann:+.0%} 夏普 {sh:.2f} 最大回撤 {dd:.0%} 最差月 {wm:+.1%}")
print("TABLES_DONE")
