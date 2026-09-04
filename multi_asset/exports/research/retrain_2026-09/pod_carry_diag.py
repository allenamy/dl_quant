"""carry 低估诊断: 用 W3FIX 实盘形态跑的逐锚权重 W, 分别按 (a) 锚时快照费率 f_fund_now(装置法) (b) 下一锚快照费率 (c) 两者均值, 算 carry, 与装置 carry_ex 列及实盘实收(重叠 27 锚 1.98) 比. 另报 4h/8h 结算名占比与费率单位自检."""
import numpy as np, time
z=np.load("probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]; ts=R[:,cols.index("ts")].astype(np.int64)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; prow={int(t):i for i,t in enumerate(pts)}
print("W shape", W.shape, "| f_fund_now 非空占比", np.isfinite(FN).mean().round(3), "| f_fund_iv 取值", np.unique(IV[np.isfinite(IV)])[:6], "| f_fund_now 量级(中位|x|)", np.nanmedian(np.abs(FN)))
def carry(i, j, W_i):
    fn=np.nan_to_num(FN[j]); iv=np.where(np.isfinite(IV[j])&(IV[j]>0), IV[j], 8.0)
    return float((W_i*fn*(4.0/iv)).sum()*1e4)
rows=[]
for k,t in enumerate(ts):
    j=prow.get(int(t)); j1=prow.get(int(t)+14400)
    if j is None or j1 is None: continue
    g=np.abs(W[k]).sum()
    if g<1e-9: continue
    w=W[k]/g
    rows.append((t, R[k,cols.index("carry_ex")], carry(k,j,w), carry(k,j1,w), R[k,cols.index("gross_total")], g))
A=np.array(rows)
for lab,s in (("2026 全年",A[:,0]>=1767225600),("重叠 08-26→08-30",A[:,0]>=1787713600)):
    print(f"{lab} n={s.sum()}: 装置 carry_ex 均 {A[s,1].mean():+.2f} | 复算(锚时费率, 单位 gross) {A[s,2].mean():+.2f} | 下一锚费率 {A[s,3].mean():+.2f} | gross_total 均 {A[s,4].mean():.3f} | Σ|W| 均 {A[s,5].mean():.3f}")
print("CARRY_DIAG_DONE")
