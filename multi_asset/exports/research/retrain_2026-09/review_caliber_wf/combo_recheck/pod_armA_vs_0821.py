import numpy as np, time, glob, os
def load(tag):
    p=glob.glob(f"/workspace/review_scratch/combo_recheck/dev/probe_artifacts/w10_ablation_series_{tag}.npz")[0]
    z=np.load(p, allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]
    ts=R[:,cols.index("ts")].astype(np.int64); g=R[:,cols.index("gross_total")]
    return ts, R[:,cols.index("net")]/g, R[:,cols.index("net_ex")]/g
def yrstats(ts, v, label):
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); out=[]
    for yv in (2022,2023,2024,2025,2026):
        s=yr==yv
        if s.sum(): out.append(f"{yv} n={s.sum()} 均 {v[s].mean():+6.3f} S {v[s].mean()/v[s].std(ddof=1)*2190**0.5:+5.2f}")
    s=yr>=2024; out.append(f"2024→ 均 {v[s].mean():+6.3f} S {v[s].mean()/v[s].std(ddof=1)*2190**0.5:+5.2f}")
    print(f"  {label}: " + " | ".join(out))
ref=np.load("/workspace/review_scratch/combo_recheck/nets_histv2_d30_pergross_ts.npy"); rts=ref[:,0].astype(np.int64); rv=ref[:,1]
for tag,lab in (("A_callog","pod 三腿 A, 原始口径(CAL=log)"),("A_calsimple","pod 三腿 A, 错误换算(CAL=simple)")):
    ts,net_g,nex_g=load(tag)
    common=np.intersect1d(ts, rts); ia={t:i for i,t in enumerate(ts)}; ib={t:i for i,t in enumerate(rts)}
    ca=np.array([ia[t] for t in common]); cb=np.array([ib[t] for t in common])
    print(f"== {lab}: 共同锚 {len(common)} ({time.strftime('%Y-%m-%d',time.gmtime(common.min()))}→{time.strftime('%Y-%m-%d',time.gmtime(common.max()))})")
    yrstats(common, net_g[ca], "pod net/gross   ")
    yrstats(common, nex_g[ca], "pod net_ex/gross")
    yrstats(common, rv[cb],    "08-21 net/gross ")
    d=net_g[ca]-rv[cb]; yr=np.array([time.gmtime(int(t)).tm_year for t in common])
    print("  差(pod net − 08-21 net)/gross 逐年: " + " | ".join(f"{yv} {d[yr==yv].mean():+6.3f}" for yv in (2022,2023,2024,2025,2026) if (yr==yv).any()) + f" | corr 2024→ {np.corrcoef(net_g[ca][yr>=2024], rv[cb][yr>=2024])[0,1]:.3f}")
