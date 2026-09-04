"""统一单位: 逐年 net_ex(bps/锚, 每单位 NAV 书, 书 gross=gross_total) → 每单位 gross 的 bps/锚 → 年化 %/gross → 2× gross 下 % NAV; DD 同法."""
import numpy as np, time, json
runs=[("pod_canon_callog_s42","正典 动态席位 正确口径"),("pod_canon_calsimple_s42","正典 动态席位 旧口径"),("pod_live_callog_s42","实盘形态 动态席位 正确口径"),("pod_live_calsimple_s42","实盘形态 动态席位 旧口径"),("pod_live_w3fix_callog_s42","实盘形态 固定席位0.21 正确口径"),("pod_live_w3fix_calsimple_s42","实盘形态 固定席位0.21 旧口径")]
for tag,lab in runs:
    z=np.load(f"probe_artifacts/w10_ablation_series_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; ts=R[:,cols.index("ts")].astype(np.int64)
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); net=R[:,cols.index("net_ex")]; gt=R[:,cols.index("gross_total")]
    print(f"== {lab}")
    for yv,label in ((2024,"2024"),(2025,"2025"),(2026,"2026→08-30"),(0,"2024→26")):
        s=(yr==yv) if yv else (yr>=2024)
        g=gt[s].mean(); m=net[s].mean(); sd=net[s].std(ddof=1); n=s.sum()
        per_g=m/g; ann_g=per_g*2190/100; sharpe=m/sd*np.sqrt(2190)
        cum=np.cumsum(net[s]); dd=(np.maximum.accumulate(cum)-cum).max()/g/100
        wm=min(sum(v for t,v in zip(ts[s],net[s]) if time.strftime('%Y-%m',time.gmtime(int(t)))==mo) for mo in sorted(set(time.strftime('%Y-%m',time.gmtime(int(t))) for t in ts[s])))/g/100
        print(f"  {label:9s} n={n:4d} gross={g:.3f} | net {m:+.3f} bps/锚(每NAV) = {per_g:+.3f} bps/锚(每gross) | 年化 {ann_g:+.1f}%/gross ⇒ 2×gross {2*ann_g:+.1f}% NAV | Sharpe {sharpe:+.2f} | maxDD {dd:.1f}% gross ⇒ 2× {2*dd:.1f}% NAV | 最坏月 {wm:+.1f}% gross")
print("UNITS_DONE")
