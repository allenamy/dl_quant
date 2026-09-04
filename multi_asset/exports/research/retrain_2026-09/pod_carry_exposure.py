"""同锚对比: 实盘目标权重 vs 回放(W3FIX 实盘形态)权重 的资金费暴露 Σ w·f_fund_now·(4/IV) (单位 gross, bps/锚), 同一面板费率; 与实盘实收 1.98 比."""
import numpy as np, json, glob, os, tarfile, time
tarfile.open("tl_overlap.tgz").extractall(".")
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; psym=[str(s) for s in PW["symbols"]]; sidx={s:i for i,s in enumerate(psym)}; prow={int(t):i for i,t in enumerate(pts)}
z=np.load("probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; R=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]; ts=R[:,cols.index("ts")].astype(np.int64); wrow={int(t):k for k,t in enumerate(ts)}
def expo(wvec, j):
    iv=np.where(np.isfinite(IV[j])&(IV[j]>0), IV[j], 8.0); fn=np.nan_to_num(FN[j]); g=np.abs(wvec).sum()
    return float((wvec*fn*(4.0/iv)).sum()/g*1e4), float(np.abs(wvec[fn>0]).sum()/g), float(np.abs(wvec[(fn>0)&(wvec>0)]).sum()/g), float(np.abs(wvec[(fn<0)&(wvec<0)]).sum()/g)
rows=[]
for f in sorted(glob.glob("tl_overlap/*.json")):
    A=int(os.path.basename(f)[:10]); j=prow.get(A); k=wrow.get(A)
    if j is None or k is None: continue
    w=json.load(open(f))["weights"]; lv=np.zeros(len(psym)); miss=0
    for s,x in w.items():
        if s in sidx: lv[sidx[s]]=x
        else: miss+=1
    e_live=expo(lv,j); e_rep=expo(W[k],j)
    rows.append((A,)+e_live+e_rep+(miss,len(w)))
A=np.array(rows)
print(f"锚数 {len(A)} | 实盘权重: 费率暴露 均 {A[:,1].mean():+.2f} bps/锚(付为正) | 正费率名权重占比 {A[:,2].mean():.2f} | 多头·正费率 {A[:,3].mean():.2f} | 空头·负费率 {A[:,4].mean():.2f} | 面板外名 {A[:,9].mean():.1f}/{A[:,10].mean():.0f}")
print(f"          回放权重: 费率暴露 均 {A[:,5].mean():+.2f} bps/锚 | 正费率名占比 {A[:,6].mean():.2f} | 多头·正费率 {A[:,7].mean():.2f} | 空头·负费率 {A[:,8].mean():.2f}")
print("EXPO_DONE")
