"""26/28 正锚 值多少? —— 用书自己的 12046 锚历史给它定价。
不预设"92.9% 很高": 先算基准率, 再算 28 锚窗口里 ≥26 正的经验频率(块-保持, 非独立假设)。"""
import sys, numpy as np, pandas as pd, json
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
from engine.signal_chain import SignalChain
from engine.funding_risk import FundingLegRiskControl
from engine.vol_gate import VolGate
from engine.netting import LEG_CADENCE_H
PD="/mnt/storage/private/work_hsy/probe_artifacts"
L={"king":0.5952380952380952,"s2":0.20238095238095238,"funding":0.20238095238095238,"size":0.0}
src=RF.get_src(None,f"{PD}/king_pred_newgen.npz",f"{PD}/s2_pred_newgen.npz")
a,yr=RF._all_anchors(src); dref=FundingLegRiskControl.calibrate_dispersion(src,a)
frc=FundingLegRiskControl(winsor_z=4.,name_cap=.15,disp_gate_z=4.,disp_shrink=.3,disp_ref=dref)
ch=SignalChain(src,weights=L,funding_mode="rank",vol_gate=VolGate(src),funding_risk=frc,pos_cap_pct=99.)
ch.calibrator=None
RVI=src.ch.index("rvol_24h"); cad=dict(LEG_CADENCE_H); LK=["king","s2","funding"]
held={k:np.zeros(src.N) for k in LK}; wv=np.array([L[k] for k in LK])
ric=np.full(len(a),np.nan); gr=np.full(len(a),np.nan)
for i,t in enumerate(a):
    ti=int(t); lp,m=ch.leg_positions(ti); H=np.zeros((3,src.N))
    for j,k in enumerate(LK):
        if i==0 or (ti%cad[k]==0):
            nw=np.zeros(src.N); nw[m]=lp[k]; held[k]=nw
        H[j]=held[k]
    v=src.CH[ti,m,RVI].astype(np.float64); fin=np.isfinite(v)&(v>0)
    med=float(np.median(v[fin])) if fin.any() else 1.
    v=np.where(fin,v,med) if med>0 else np.ones_like(v)
    s=ch.shape_position((wv@H)[m]); w=np.sign(s)*np.abs(s)**.5/(v/med); w=w-w.mean()
    g=float(np.abs(w).sum()); w=w/g if g>1e-12 else w
    r=src.Y4[ti,m]; ok=np.isfinite(r)
    if ok.sum()>=5:
        ric[i]=float(np.corrcoef(pd.Series(w[ok]).rank(),pd.Series(r[ok]).rank())[0,1])
        gr[i]=float(np.nansum(w[ok]*r[ok])*1e4)
v=ric[np.isfinite(ric)]; gv=gr[np.isfinite(gr)]
print(f"全期 {len(v)} 锚   IC>0 基准率 = {(v>0).mean():.4f}   毛额>0 基准率 = {(gv>0).mean():.4f}")
for W,K in [(28,26),(22,11)]:
    if len(v)>=W:
        roll=pd.Series((v>0).astype(int)).rolling(W).sum().dropna().values
        pge=(roll>=K).mean(); ple=(roll<=K).mean()
        print(f"  {W} 锚窗口里 正锚≥{K} 的历史频率 = {pge:.4f}  (≤{K}: {ple:.4f})   窗口数 {len(roll)}")
rollg=pd.Series((gv>0).astype(int)).rolling(28).sum().dropna().values
print(f"  28 锚窗口里 毛额正锚≥21 的历史频率 = {(rollg>=21).mean():.4f}")
# 逐年 IC>0 率, 看 2026 是不是特别差
df=pd.DataFrame({"y":np.asarray(yr)[np.isfinite(ric)],"ic":v,"g":gv})
print("\n逐年 IC>0 率 / 均值IC / 均值毛额:")
print(df.groupby("y").agg(n=("ic","size"),pos=("ic",lambda x:(x>0).mean()),ic=("ic","mean"),g=("g","mean")).round(4).to_string())
print("\nIC 自相关 AR(1..3):", [round(float(np.corrcoef(v[:-k],v[k:])[0,1]),4) for k in (1,2,3)])
json.dump({"base_pos":float((v>0).mean()),"n":int(len(v))},open(f"{PD}/baserate.json","w"))
print("BASERATE_DONE")
