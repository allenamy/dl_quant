"""集中度补充: 对称截尾均值(5/5, 10/10) / 逐年增益占比 / 按市场状态分层的条件 Δ(跌 <−1%, 平, 涨 >+1%; 高离散 vs 低离散)."""
import numpy as np, time, sys
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float)
tb,nb=load("w10_canonpred_s42"); mb={int(t):i for i,t in enumerate(tb)}
yrs=np.array([time.gmtime(int(t)).tm_year for t in tb]); sel=yrs>=2023
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}; Y4=PW["Y4"]
mk=np.full(len(tb),np.nan); sg=np.full(len(tb),np.nan)
for i,t in enumerate(tb):
    j=prow.get(int(t))
    if j is None: continue
    y=Y4[j]; y=y[np.isfinite(y)]
    if len(y)>50: mk[i]=np.median(y); sg[i]=np.std(y)
hi=sg>np.nanmedian(sg[sel])
for run in sys.argv[1:]:
    ta,na=load(run); d=np.zeros(len(tb))
    for k,t in enumerate(ta):
        i=mb.get(int(t))
        if i is not None: d[i]=na[k]-nb[i]
    dd=np.sort(d[sel]); n=len(dd)
    tm5=dd[n//20:n-n//20].mean(); tm10=dd[n//10:n-n//10].mean()
    tot=d[sel].sum(); share={y:round(d[yrs==y].sum()/tot*100) for y in (2023,2024,2025,2026)}
    down=sel&(mk<-0.01); up=sel&(mk>0.01); mid=sel&(np.abs(mk)<=0.01)
    print(f"[{run}] 均值 {d[sel].mean():+.3f} | 截尾5/5 {tm5:+.3f} | 截尾10/10 {tm10:+.3f} | 逐年增益占比% {share} | 条件Δ: 跌锚(<−1%, n{down.sum()}) {d[down].mean():+.2f} / 平 {d[mid].mean():+.3f} / 涨锚(>+1%, n{up.sum()}) {d[up].mean():+.2f} | 高离散锚 {d[sel&hi].mean():+.3f} / 低离散锚 {d[sel&~hi].mean():+.3f}")
