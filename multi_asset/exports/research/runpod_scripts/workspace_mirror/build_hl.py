"""HL 跨场所族: Hyperliquid funding/premium 对齐到面板 ts × 140 symbol。
机制: 我们面板里有【币安】funding, 但从没有过另一个【参与者结构完全不同】的场所的杠杆价格。
     HL 是链上永续, 参与者更偏投机/散户; 两地 funding 之差 = 杠杆需求在场所间的不对称,
     这是价量族与币安 funding 都无法张成的量(它不是价格的函数, 是【谁在哪里加杠杆】的函数)。
特征(6, 全部 ≤t):
  hl_fund_ema   HL funding 的 24h EMA(该场所的杠杆需求水平)
  hl_prem_ema   HL premium 的 24h EMA(该场所的基差)
  fund_div      hl_fund_ema − 币安 funding_ema(★核心: 场所间分歧)
  div_mom24     fund_div 的 24h 变化(分歧在扩大还是收敛)
  hl_fund_vol   HL funding 的 24h 标准差(该场所杠杆的不稳定度)
  prem_div      hl_prem_ema − 该币横截面中位(相对基差)
覆盖: HL 2023-07 起; 2022-23 前段全 NaN(与 metrics 断层同族, 塔门可学会关闭)。
"""
import numpy as np, glob, re, os
P=np.load("/workspace/data/wide_dl_pm32_hz.npz",allow_pickle=True)
ts=P["ts"].astype(np.int64); sym=[str(x) for x in P["symbols"]]; CH=P["CH"]
names=[str(x) for x in P["ch_names"]]
fidx=names.index("funding_ema")
base=[re.sub(r"(USDT|USDC)$","",s) for s in sym]
base=[re.sub(r"^1000+","",b) for b in base]
T,N=len(ts),len(sym)
FE=["hl_fund_ema","hl_prem_ema","fund_div","div_mom24","hl_fund_vol","prem_div"]
X=np.full((T,N,len(FE)),np.nan,np.float32)
def ema(a,n):
    o=np.full(len(a),np.nan); al=2.0/(n+1); s=np.nan
    for i,v in enumerate(a):
        if not np.isfinite(v): o[i]=s; continue
        s=v if not np.isfinite(s) else al*v+(1-al)*s; o[i]=s
    return o
hit=0
for j,b in enumerate(base):
    f=f"/workspace/data/hl/funding/{b}.npz"
    if not os.path.exists(f): continue
    a=np.load(f,allow_pickle=True)["a"]
    t=a[:,0].astype(np.int64); fu=a[:,1].astype(np.float64); pr=a[:,2].astype(np.float64)
    idx=np.searchsorted(ts,t)
    ok=(idx>=0)&(idx<T)&(np.abs(np.take(ts,np.clip(idx,0,T-1))-t)<3600000)
    if ok.sum()<2000: continue
    hit+=1
    FU=np.full(T,np.nan); PR=np.full(T,np.nan)
    FU[idx[ok]]=fu[ok]; PR[idx[ok]]=pr[ok]
    fe=ema(FU,24); pe=ema(PR,24)
    X[:,j,0]=fe; X[:,j,1]=pe
    bn=CH[:,j,fidx].astype(np.float64); bn[bn==0]=np.nan
    X[:,j,2]=fe-bn
    X[24:,j,3]=X[24:,j,2]-X[:-24,j,2]
    s=np.full(T,np.nan)
    for i in range(24,T): 
        w=FU[i-24:i]
        if np.isfinite(w).sum()>8: s[i]=np.nanstd(w)
    X[:,j,4]=s
med=np.nanmedian(X[:,:,1],axis=1)
X[:,:,5]=X[:,:,1]-med[:,None]
print("HL 命中 %d/%d 币"%(hit,N),flush=True)
cov=np.isfinite(X[:,:,2]).mean()
print("fund_div 全期格覆盖 %.4f | 2024后 %.4f"%(cov, np.isfinite(X[-20000:,:,2]).mean()),flush=True)
np.savez("/workspace/data/hl_hourly.npz",X=X,feats=np.array(FE),ts=ts,symbols=np.array(sym))
print("HL_BUILD_DONE",flush=True)
