"""STEP 1 (a) done properly: a COIN-M contract that emits klines with ZERO volume is NOT tradable.
Binance keeps publishing bars with a FROZEN last price after a contract goes dormant -> a naive
basis builder reads a huge fake alpha. Gate on realised volume."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TS=Z["TS"];names=[str(x) for x in Z["names"]];ums=[str(x) for x in Z["um"]]
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"]
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
win=(TS>=TS[0])&(TS<=CM_END); NW=win.sum()
cmq=np.where(np.isfinite(CMV)&np.isfinite(CMP),CMV*CMP,0.0)   # USD per 4h bar on the COIN-M leg
res=[];print(f"{'name':16s}{'bars':>6s}{'trade_bars':>11s}{'%live':>7s}{'medUSD/4h':>12s}{'p25USD':>11s}{'last_trade_bar':>22s}{'%live_2026':>11s}")
LAST=[];ALIVE=[]
for k,nm in enumerate(names):
    live=(cmq[:,k]>0)&win
    y26=win&(TS>=int(dt.datetime(2026,1,1,tzinfo=dt.timezone.utc).timestamp()))
    v=cmq[live,k]
    lt=dt.datetime.utcfromtimestamp(TS[live][-1]) if live.sum() else None
    pct=100*live.sum()/NW; p26=100*(live&y26).sum()/max(1,y26.sum())
    res.append(dict(name=nm,um=ums[k],trade_bars=int(live.sum()),pct_live=float(pct),
        med_usd_4h=float(np.median(v)) if len(v) else 0.0,p25_usd_4h=float(np.percentile(v,25)) if len(v) else 0.0,
        last_trade_bar=str(lt),pct_live_2026=float(p26)))
for r in sorted(res,key=lambda z:-z["pct_live_2026"]):
    print(f"{r['name']:16s}{NW:6d}{r['trade_bars']:11d}{r['pct_live']:7.1f}{r['med_usd_4h']:12.0f}{r['p25_usd_4h']:11.0f}{r['last_trade_bar']:>22s}{r['pct_live_2026']:11.1f}")
for TH in (50,80,90):
    a=[r["name"] for r in res if r["pct_live_2026"]>=TH]
    print(f"\nCOIN-M names TRADING in >={TH}% of 2026 4h bars: {len(a)}  {a}")
for CAP in (1e4,5e4,2.5e5):
    a=[r["name"] for r in res if r["pct_live_2026"]>=80 and r["med_usd_4h"]>=CAP]
    print(f"...and median COIN-M USD volume/4h >= ${CAP:,.0f}: {len(a)}  {a}")
json.dump(res,open(W+"/STEP1d_tradability.json","w"),indent=1)
