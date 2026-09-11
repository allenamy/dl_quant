"""ENV WHITELIST (E-0826-D) = EMPTY SET. First-hand probe of OKX public endpoints depth."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","OKX_KEY","HTTP_PROXY","HTTPS_PROXY")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import json, time, urllib.request, datetime as dt

def get(url, tries=3):
    for t in range(tries):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"research/1.0"}), timeout=25)
            return json.loads(r.read().decode())
        except Exception as e:
            if t==tries-1: return {"_err":repr(e)}
            time.sleep(1.5)

out={}
# 1 instruments
j=get("https://www.okx.com/api/v5/public/instruments?instType=SWAP")
if "_err" in j: out["instruments"]=j
else:
    d=j.get("data",[])
    usdt=[x["instId"] for x in d if x.get("settleCcy")=="USDT" and x.get("ctType")=="linear"]
    out["instruments"]={"code":j.get("code"),"n_swap":len(d),"n_usdt_linear":len(usdt),"sample":usdt[:8]}
    open("/tmp/okx_instruments.json","w").write(json.dumps(usdt))
time.sleep(0.35)

# 2 funding-rate-history depth for BTC: page back with `after`
def fr_depth(inst):
    rows=[]; after=None; pages=0
    while pages<40:
        u=f"https://www.okx.com/api/v5/public/funding-rate-history?instId={inst}&limit=100"
        if after: u+=f"&after={after}"
        j=get(u)
        if "_err" in j: return {"_err":j["_err"],"pages":pages,"n":len(rows)}
        d=j.get("data",[])
        if not d: break
        rows+=d; after=d[-1]["fundingTime"]; pages+=1
        time.sleep(0.35)
    if not rows: return {"n":0}
    ft=sorted(int(r["fundingTime"]) for r in rows)
    iv=sorted(set(r.get("fundingRate") and r.get("realizedRate") and 1 or 1 for r in rows))
    ivs=sorted(set((int(r["fundingTime"])-int(rr["fundingTime"]))//3600000 for r,rr in zip(rows[:-1],rows[1:])))
    return {"n":len(rows),"pages":pages,"oldest":dt.datetime.utcfromtimestamp(ft[0]/1000).isoformat()+"Z",
            "newest":dt.datetime.utcfromtimestamp(ft[-1]/1000).isoformat()+"Z",
            "gap_hours_seen":ivs[:6],"keys":sorted(rows[0].keys())}
for inst in ["BTC-USDT-SWAP","SOL-USDT-SWAP","WLD-USDT-SWAP"]:
    out[f"funding_{inst}"]=fr_depth(inst)

# 3 candles depth: history-candles 4H
def cd_depth(inst,bar="4H"):
    rows=[]; after=None; pages=0
    while pages<25:
        u=f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar={bar}&limit=100"
        if after: u+=f"&after={after}"
        j=get(u)
        if "_err" in j: return {"_err":j["_err"],"pages":pages,"n":len(rows)}
        d=j.get("data",[])
        if not d: break
        rows+=d; after=d[-1][0]; pages+=1
        time.sleep(0.35)
    if not rows: return {"n":0}
    ts=sorted(int(r[0]) for r in rows)
    return {"n":len(rows),"pages":pages,"oldest":dt.datetime.utcfromtimestamp(ts[0]/1000).isoformat()+"Z",
            "newest":dt.datetime.utcfromtimestamp(ts[-1]/1000).isoformat()+"Z","ncols":len(rows[0])}
out["candles_BTC_4H"]=cd_depth("BTC-USDT-SWAP")
print(json.dumps(out,indent=1))
