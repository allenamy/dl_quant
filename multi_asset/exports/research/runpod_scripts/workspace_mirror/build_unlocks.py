"""#64 解锁族特征构建 + G1/G2 门。
机制: 解锁 = 合约写死的供给冲击, 在 t 时刻【公开可知】⇒ 用未来日程不是前视, 是 ex-ante 公开信息。
★ 泄漏纪律: 只用【日程形状】(时间 + 代币量 / 总供给), 不用 unlockUsdChart(内嵌价格, 且可能事后修订)。
特征(6, 全部 ≤t 可知):
  ul_next7    = 未来 7 天解锁量 / 总供给      (即将到来的供给压力)
  ul_next30   = 未来 30 天解锁量 / 总供给
  ul_past7    = 过去 7 天解锁量 / 总供给      (刚被吸收的供给)
  ul_dtn      = 到下一次解锁的天数(log1p, 上限 180)
  ul_intens90 = 过去 90 天解锁量 / 总供给
  ul_cum      = 累计已解锁 / 总供给           (流通进度; 低=悬顶多)
未覆盖币 → NaN(塔式接入时掩码置零, 与 metrics 断层同一处置)。
"""
import numpy as np, json, glob, re, datetime as dt
PAN="/workspace/data/wide_dl_pm32_hz.npz"
d=np.load(PAN, allow_pickle=True); ts=d["ts"].astype(np.int64); sym=[str(x) for x in d["symbols"]]
base=[re.sub(r"(USDT|USDC)$","",s) for s in sym]
T,N=len(ts),len(sym)
rec={}
for f in glob.glob("/workspace/data/unlocks_raw/*.json"):
    r=json.load(open(f))
    for k in (r.get("gecko_id"), r.get("name"), f.split("/")[-1][:-5]):
        if k: rec.setdefault(str(k).upper().replace(" ","-"), r)
ALIAS={"BTC":"BITCOIN","ETH":"ETHEREUM","BNB":"BINANCECOIN","XRP":"RIPPLE","DOGE":"DOGECOIN",
 "SOL":"SOLANA","ADA":"CARDANO","TRX":"TRON","LTC":"LITECOIN","DOT":"POLKADOT","MATIC":"MATIC-NETWORK",
 "AVAX":"AVALANCHE","LINK":"CHAINLINK","UNI":"UNISWAP","ATOM":"COSMOS","FIL":"FILECOIN",
 "APT":"APTOS","ARB":"ARBITRUM","OP":"OPTIMISM","TIA":"CELESTIA","SEI":"SEI-NETWORK",
 "INJ":"INJECTIVE","STX":"BLOCKSTACK","IMX":"IMMUTABLE-X","RUNE":"THORCHAIN","GRT":"THE-GRAPH"}
FEATS=["ul_next7","ul_next30","ul_past7","ul_dtn","ul_intens90","ul_cum"]
X=np.full((T,N,len(FEATS)), np.nan, np.float32)
DAY=ts/86400000.0
hit=0
for j,b in enumerate(base):
    r = rec.get(b) or rec.get(ALIAS.get(b,""))
    if not r: continue
    ev=(r.get("metadata") or {}).get("events") or []
    rows=[]
    for e in ev:
        t0=e.get("timestamp"); nt=e.get("noOfTokens") or []
        amt=float(np.nansum([float(x) for x in nt if isinstance(x,(int,float))])) if nt else 0.0
        if t0 and amt>0: rows.append((float(t0)/86400.0, amt))
    if not rows: continue
    rows.sort(); et=np.array([x[0] for x in rows]); ea=np.array([x[1] for x in rows])
    tot=(r.get("supplyMetrics") or {}).get("maxSupply") or ea.sum()
    tot=float(tot) if tot else ea.sum()
    if tot<=0: continue
    hit+=1
    cs=np.cumsum(ea)
    for i in range(T):
        t=DAY[i]
        fut=(et>t)
        X[i,j,0]=ea[(et>t)&(et<=t+7)].sum()/tot
        X[i,j,1]=ea[(et>t)&(et<=t+30)].sum()/tot
        X[i,j,2]=ea[(et<=t)&(et>t-7)].sum()/tot
        X[i,j,3]=np.log1p(min(float(et[fut].min()-t),180.0)) if fut.any() else np.log1p(180.0)
        X[i,j,4]=ea[(et<=t)&(et>t-90)].sum()/tot
        X[i,j,5]=(cs[et<=t][-1]/tot) if (et<=t).any() else 0.0
print("覆盖 %d/%d 币"%(hit,N), flush=True)
cov=np.isfinite(X).all(2).mean()
print("逐格覆盖率 %.4f"%cov, flush=True)
np.savez("/workspace/data/unlocks_hourly.npz", X=X, feats=np.array(FEATS), ts=ts, symbols=np.array(sym))
print("UNLOCK_BUILD_DONE", flush=True)
