"""未整形 DL 合成的 rank-IC 基准 —— 给 0.0953 定价。
回填测的是 equal-z(king,s2) 未整形合成; 整书 rank-IC 0.0548 是【整形后】的。两者不可直接比。
本脚本在 9821 锚上算【同一个未整形合成】, 给出它自己的基准率与分布。"""
import sys, numpy as np, pandas as pd, json
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
PD="/mnt/storage/private/work_hsy/probe_artifacts"
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz")
a,yr=RF._all_anchors(src)
def z(v):
    v=np.asarray(v,float); s=np.nanstd(v)
    return (v-np.nanmean(v))/s if s>0 else v*np.nan
ic=np.full(len(a),np.nan); icK=np.full(len(a),np.nan); icS=np.full(len(a),np.nan)
for i,t in enumerate(a):
    ti=int(t); m=src.tradeable(ti)
    k=src.KING[ti,m].astype(np.float64); s=src.S2[ti,m].astype(np.float64)
    r=src.Y4[ti,m].astype(np.float64)
    ok=np.isfinite(r)&np.isfinite(k)&np.isfinite(s)
    if ok.sum()<10: continue
    comp=z(k[ok])+z(s[ok])
    rr=pd.Series(r[ok]).rank()
    ic[i]=float(np.corrcoef(pd.Series(comp).rank(),rr)[0,1])
    icK[i]=float(np.corrcoef(pd.Series(k[ok]).rank(),rr)[0,1])
    icS[i]=float(np.corrcoef(pd.Series(s[ok]).rank(),rr)[0,1])
v=ic[np.isfinite(ic)]
print(f"未整形 DL 合成, n={len(v)} 锚 (2022-01→2026-06)")
print(f"  均值 rank-IC = {v.mean():+.5f}   中位 {np.median(v):+.5f}   sd {v.std():.4f}")
print(f"  IC>0 基准率 = {(v>0).mean():.4f}")
print(f"  king 单腿 {np.nanmean(icK):+.5f}   s2 单腿 {np.nanmean(icS):+.5f}")
print()
print("★ 50 锚窗口均值的历史分布(回填 n=50, 得 +0.0953):")
roll=pd.Series(v).rolling(50).mean().dropna().values
for q in (5,25,50,75,90,95,99):
    print(f"   p{q:<3d} = {np.percentile(roll,q):+.5f}")
print(f"   ≥+0.0953 的历史频率 = {(roll>=0.0953).mean():.4f}   窗口数 {len(roll)}")
print(f"   ≥+0.0600 的历史频率 = {(roll>=0.0600).mean():.4f}   (旧臂 +0.0600)")
print()
print("逐年未整形合成 IC:")
df=pd.DataFrame({"y":np.asarray(yr)[np.isfinite(ic)],"ic":v})
print(df.groupby("y").agg(n=("ic","size"),ic=("ic","mean"),pos=("ic",lambda x:(x>0).mean())).round(4).to_string())
json.dump({"mean":float(v.mean()),"n":int(len(v)),"p_ge_0953":float((roll>=0.0953).mean())},open(f"{PD}/unshaped_base.json","w"))
print("UNSHAPED_DONE")
