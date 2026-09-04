import numpy as np, time
B="pod_backup_2026-08-21"; PD="probe_artifacts"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); y4=M["y4"]
P=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); syms=[str(s) for s in P["symbols"]]; b=syms.index("BTCUSDT")
def ym(t): g=time.gmtime(int(t)); return g.tm_year*100+g.tm_mon
yb=y4[:,b]; 
print("面板 BTC(y4 累乘) 2026 逐月:", {k: f"{np.expm1(np.nansum(np.log1p(np.nan_to_num(yb[[i for i,t in enumerate(E) if ym(t)==k]],nan=0)))):+.1%}" for k in range(202601,202609)})
z=np.load(f"{PD}/w10_canonfix_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; ts=rec[:,cols.index("ts")].astype(np.int64); ne=rec[:,cols.index("net_ex")].astype(float); lf=rec[:,cols.index("leg_fund")].astype(float)
for a,bb,lab in ((1785542400,1786406400,"08-01→08-10"),(1786406400,1787356800,"08-11→08-21"),(1784246400,1785542400,"07-17→07-31")):
    s=(ts>=a)&(ts<bb); print(f"W3FIX 正典 {lab}: {s.sum()} 锚 net_ex 均 {ne[s].mean():+.2f} bps (夏普 {ne[s].mean()/(ne[s].std()+1e-9)*np.sqrt(2190):.2f}) | leg_fund 均 {lf[s].mean():+.2f} | BTC {np.expm1(np.nansum(np.log1p(np.nan_to_num(yb[[i for i,t in enumerate(E) if a<=t<bb]],nan=0)))):+.1%}")
print("AUG_TAIL_DONE")
