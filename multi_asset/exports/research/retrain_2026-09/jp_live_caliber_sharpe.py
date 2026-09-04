"""实盘口径回放参考值 @jpline: W3FIX 正典 vs 冻结宇宙仿真臂 的 2023+/2025-26 夏普; 广度分档夏普(2025-26)。审计 live vs replay 2026-09-04。"""
import numpy as np, time
PD="probe_artifacts"
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    return rec[:,cols.index("ts")].astype(np.int64), rec[:,cols.index("net_ex")].astype(float), rec[:,cols.index("nsel")].astype(float)
def sh(x): return x.mean()/(x.std()+1e-12)*np.sqrt(2190)
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts])
print("臂 | 2023+ 夏普 / 均 bps | 2025-26 夏普 / 均 | 2026 夏普 / 均 | 2026-07..08 夏普 / 均")
for tag,lab in (("canonfix_s42","W3FIX 正典(动态400)"),("uni2_F_M7_fx_s42","W3FIX+月度冻结450(年龄≥7)"),("uni2_F_Q_fx_s42","W3FIX+季度冻结450"),("uni2_N400rF_fx_s42","W3FIX+FTRIM(部署态, 动态400)"),("uni2_N829T400F_fx_s42","W3FIX+FTRIM+M1"),("canonpred_s42","msharpe 正典(表头数字)")):
    try: ts,ne,ns=load(tag)
    except Exception as e: print(lab,"缺",e); continue
    Y=yr(ts); s23=Y>=2023; s25=Y>=2025; s26=Y==2026; ja=(ts>=1782864000)
    print(f"{lab} | {sh(ne[s23]):.2f} / {ne[s23].mean():+.2f} | {sh(ne[s25]):.2f} / {ne[s25].mean():+.2f} | {sh(ne[s26]):.2f} / {ne[s26].mean():+.2f} | {sh(ne[ja]):.2f} / {ne[ja].mean():+.2f}")
ts,ne,ns=load("canonfix_s42"); Y=yr(ts); s=Y>=2025
print("\nW3FIX 正典 2025-26 按有效名数分档: 档 | 锚数 | 夏普 | 均 bps")
for lo,hi in ((0,250),(250,300),(300,350),(350,1000)):
    m=s&(ns>=lo)&(ns<hi); print(f"  nsel [{lo},{hi}) | {m.sum()} | {sh(ne[m]):.2f} | {ne[m].mean():+.2f}")
m=s&(ns<250); print(f"  nsel<250 的锚分布(年-月): {sorted(set((time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon) for t in ts[m]))}")
print("LIVE_CALIBER_DONE")
