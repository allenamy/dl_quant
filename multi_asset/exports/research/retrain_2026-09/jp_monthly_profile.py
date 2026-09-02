"""候选臂月度 Δ 剖面(2025-01..2026-08): 增益是否集中在少数月/锚; 正月占比; 最大单月负; 最近 3 个月(含实盘时代前夜)."""
import numpy as np, time, sys
PD="/mnt/storage/private/work_hsy/probe_artifacts"
def load(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float)
tb,nb=load("w10_canonpred_s42"); mb={int(t):i for i,t in enumerate(tb)}
ym=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in tb])
for run in sys.argv[1:]:
    ta,na=load(run); d=np.full(len(tb),np.nan)
    for k,t in enumerate(ta):
        i=mb.get(int(t)); 
        if i is not None: d[i]=na[k]-nb[i]
    d=np.where(np.isnan(d),0.0,d); months=sorted(set(ym[ym>=202501]))
    prof=[(m,d[ym==m].mean()) for m in months]
    pos=sum(1 for _,v in prof if v>0); worst=min(prof,key=lambda x:x[1]); best=max(prof,key=lambda x:x[1])
    # 锚级集中度: 2023+ 正增益中前 1% 锚贡献占比
    sel=ym>=202301; dd=d[sel]; top=np.sort(dd)[::-1]; k=max(1,len(dd)//100)
    conc=top[:k].sum()/max(dd.sum(),1e-9)
    print(f"[{run}] 月正占比 {pos}/{len(prof)} 最差月 {worst[0]} {worst[1]:+.3f} 最好月 {best[0]} {best[1]:+.3f} | 2023+ 前1%锚贡献占总增益 {conc*100:.0f}% | 月剖面(2026): " + " ".join(f"{m%100:02d}:{v:+.2f}" for m,v in prof if m>=202601))
