"""W1 增量关(冻结): fund_div 对 下期资金费 的【偏】预测力, 控制在役信号 funding_ema。
判据: 偏 spearman |IC|≥0.05 且逐年同号 4/4 —— 达标才有资格进腿级回放。
另报: 双变量 OLS 的 R² 提升, 与 funding_ema 单独的自预测力(基线锚定)。"""
import numpy as np, json
from scipy.stats import spearmanr, rankdata
MA='/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset'
HL=np.load(f'{MA}/exports/hl_hourly.npz', allow_pickle=True)
P=np.load(f'{MA}/exports/wide_dl_full_corrfund_causal_0731.npz', allow_pickle=True)
X,feats=HL['X'],list(HL['feats'])
DIV=X[:,:,feats.index('fund_div')]
ch=list(P['ch_names']); FU=P['CH'][:,:,[i for i,c in enumerate(ch) if 'fund' in str(c).lower()][0]]
MEM=P['MEMBER110']; ts=HL['ts']//1000
T,N=FU.shape
FWD=np.full_like(FU,np.nan); FWD[:-8]=FU[8:]
hours=(ts//3600)%24; anchors=np.where(hours%4==0)[0]
import datetime
years=np.array([datetime.datetime.utcfromtimestamp(t).year for t in ts])
def zr(v):
    r=rankdata(v); return (r-r.mean())/(r.std()+1e-12)
part, base, yr_part = [], [], {}
for t in anchors:
    if t+8>=T: continue
    m=np.isfinite(DIV[t])&np.isfinite(FU[t])&np.isfinite(FWD[t])&MEM[t].astype(bool)
    if m.sum()<30: continue
    d,f,y=zr(DIV[t][m]),zr(FU[t][m]),zr(FWD[t][m])
    # 偏相关: 先把 y 与 d 各自对 f 正交化, 再相关
    ry=y-f*np.dot(y,f)/np.dot(f,f)
    rd=d-f*np.dot(d,f)/np.dot(f,f)
    if np.std(ry)>1e-9 and np.std(rd)>1e-9:
        p=float(np.corrcoef(rd,ry)[0,1]); part.append(p)
        yr_part.setdefault(int(years[t]),[]).append(p)
    base.append(float(np.corrcoef(f,y)[0,1]))
mp=float(np.nanmean(part)); mb=float(np.nanmean(base))
yrs={y:round(float(np.mean(v)),4) for y,v in sorted(yr_part.items()) if len(v)>100}
sign_ok=sum(1 for v in yrs.values() if v*mp>0)
print(f"在役基线: funding_ema 自预测下期 IC = {mb:+.4f}")
print(f"★ fund_div 偏IC(控制 funding_ema)= {mp:+.4f} 逐年{yrs} 同号{sign_ok}/{len(yrs)}")
print("判读:", "★★过增量关 — 进腿级回放" if abs(mp)>=0.05 and sign_ok>=len(yrs)-0 else
      ("过线但逐年有反号 — 降级观察" if abs(mp)>=0.05 else "增量不足 — fund_div 的 -0.75 主要是自相关的影子, 记录关闭"))
json.dump(dict(base=mb, partial=mp, by_year=yrs), open('/mnt/storage/private/work_hsy/probe_artifacts/w1_incr.json','w'), indent=1)
print("W1INCR_DONE")
