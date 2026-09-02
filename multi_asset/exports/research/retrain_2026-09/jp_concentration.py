"""候选臂增益集中度拆解: 去尾 Δ / 中位锚 Δ / 正锚占比 / 顶锚重叠 / 顶锚事件特征(市场中位 y4, 截面离散, 深负名占比, 当锚基线净)."""
import numpy as np, time, sys
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float)
tb,nb=load("w10_canonpred_s42"); mb={int(t):i for i,t in enumerate(tb)}
yrs=np.array([time.gmtime(int(t)).tm_year for t in tb]); sel=yrs>=2023
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
Y4=PW["Y4"]; FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; ivn=np.where(np.isfinite(IV)&(IV>0),IV,8.0); FN8=FN*(8.0/ivn)
def anchor_feats(t):
    j=prow.get(int(t)); 
    if j is None: return (np.nan,)*3
    y=Y4[j]; y=y[np.isfinite(y)]; f=FN8[j]; f=f[np.isfinite(f)]
    return (np.median(y)*1e4 if len(y) else np.nan, np.std(y)*1e4 if len(y) else np.nan, (f<-0.0010).mean()*100 if len(f) else np.nan)
tops={}
for run in sys.argv[1:]:
    ta,na=load(run); d=np.zeros(len(tb))
    for k,t in enumerate(ta):
        i=mb.get(int(t))
        if i is not None: d[i]=na[k]-nb[i]
    dd=d[sel]; idx=np.where(sel)[0]; order=np.argsort(dd)[::-1]; k=max(1,len(dd)//100)
    top=idx[order[:k]]; tops[run]=set(top.tolist())
    rest=np.delete(dd,order[:k])
    print(f"[{run}] 全 Δ {dd.mean():+.3f} | 去前1%锚 Δ {rest.mean():+.3f} | 去前5% Δ {np.delete(dd,order[:len(dd)//20]).mean():+.3f} | 中位锚 Δ {np.median(dd):+.4f} | 正锚占比 {(dd>0).mean()*100:.0f}% 负锚 {(dd<0).mean()*100:.0f}% 零 {(dd==0).mean()*100:.0f}% | 最坏锚 Δ {dd.min():+.2f}")
    fe=[anchor_feats(tb[i]) for i in top]; fe=np.array(fe,float)
    yy=[time.strftime("%y%m%d%H",time.gmtime(int(tb[i]))) for i in top[:8]]
    print(f"    顶锚(前1%={k}): 市场中位y4 {np.nanmean(fe[:,0]):+.0f}bp(全样本≈{np.nanmedian([anchor_feats(t)[0] for t in tb[sel][::50]]):+.0f}) | 截面σ(y4) {np.nanmean(fe[:,1]):.0f}bp(全样本 {np.nanmedian([anchor_feats(t)[1] for t in tb[sel][::50]]):.0f}) | 深负名占比 {np.nanmean(fe[:,2]):.1f}% | 基线该锚净 {nb[top].mean():+.1f} | 顶锚年分布 {dict(zip(*np.unique(yrs[top],return_counts=True)))} | 例 {yy}")
runs=list(tops)
for a in range(len(runs)):
    for b in range(a+1,len(runs)):
        s1,s2=tops[runs[a]],tops[runs[b]]; print(f"重叠 {runs[a]} ∩ {runs[b]}: {len(s1&s2)}/{len(s1)}")
