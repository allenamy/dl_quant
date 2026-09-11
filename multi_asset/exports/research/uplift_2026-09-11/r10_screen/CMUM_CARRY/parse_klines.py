"""Parse 4h klines for both legs onto the pinned anchor axis. close price per anchor bar.
Binance futures kline columns: open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_vol,taker_buy_quote,ignore
CM klines: price in USD/coin, volume in CONTRACTS, quote_volume(=base_volume) in COIN."""
import os,glob,zipfile,json,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True); TS=Z["TS"]; N=len(TS)
pairs=[l.split() for l in open(W+"/raw_listings/pairs_all.txt") if l.strip()]
def read(d,sym):
    rows=[]
    for z in sorted(glob.glob(os.path.join(d,sym+"-*.zip"))):
        try: zf=zipfile.ZipFile(z)
        except Exception: continue
        txt=zf.read(zf.namelist()[0]).decode()
        for ln in txt.strip().split("\n"):
            if ln.startswith("open_time"): continue
            p=ln.split(",")
            if len(p)<9: continue
            try: rows.append((int(float(p[0])),float(p[4]),float(p[7]),float(p[5])))
            except Exception: pass
    if not rows: return None
    a=np.array(sorted(set(rows)),dtype=np.float64)
    return a
CMP=np.full((N,len(pairs)),np.nan); UMP=np.full((N,len(pairs)),np.nan)
CMV=np.full((N,len(pairs)),np.nan); UMV=np.full((N,len(pairs)),np.nan)
for k,(cmS,umS) in enumerate(pairs):
    for arr,P,V in ((read(W+"/dlk/cm",cmS),CMP,CMV),(read(W+"/dlk/um",umS),UMP,UMV)):
        if arr is None: continue
        t=(arr[:,0]/1000.0).astype(np.int64)
        idx=np.searchsorted(TS,t)
        good=(idx<N)&(idx>=0)
        ii=idx[good]; ok=TS[ii]==t[good]
        P[ii[ok],k]=arr[good][ok,1]; V[ii[ok],k]=arr[good][ok,2]
np.savez_compressed(W+"/klines_grid.npz",TS=TS,CMP=CMP,UMP=UMP,CMV=CMV,UMV=UMV,
    names=np.array([c for c,_ in pairs]),um=np.array([u for _,u in pairs]))
print("bars present CM %d UM %d of %d"%(np.isfinite(CMP).sum(),np.isfinite(UMP).sum(),CMP.size))
