"""OKXRHO step-1 puller. ENV WHITELIST (E-0826-D) = EMPTY SET.
Public unauthenticated OKX endpoints only, sequential, 0.34s sleep (<=3 req/s).
Writes /workspace/r9okx/okx_raw.npz . Reads the pinned panel READ-ONLY for the symbol list."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import json, time, urllib.request, numpy as np, datetime as dt, sys, re

OUT="/workspace/r9okx"; os.makedirs(OUT,exist_ok=True)
SLEEP=0.34
def get(url,tries=4):
    for t in range(tries):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"research/1.0"}),timeout=25)
            return json.loads(r.read().decode())
        except Exception as e:
            if t==tries-1: return {"_err":repr(e)}
            time.sleep(1.2*(t+1))

# ---- panel symbols (READ ONLY) ----
P=np.load("/workspace/data/wide_panel_4h_v3splice.npz",allow_pickle=True)
psyms=[str(x) for x in P["symbols"]]
def base_of(s):
    assert s.endswith("USDT"), s
    b=s[:-4]
    for pre in ("1000000","100000","10000","1000"):
        if b.startswith(pre) and len(b)>len(pre): return [b, b[len(pre):]]
    return [b]

j=get("https://www.okx.com/api/v5/public/instruments?instType=SWAP"); time.sleep(SLEEP)
assert "_err" not in j, j
inst=[x for x in j["data"] if x.get("settleCcy")=="USDT" and x.get("ctType")=="linear" and x.get("state")=="live"]
okx_base={x["instId"].split("-")[0]: x["instId"] for x in inst}
pairs=[]
for s in psyms:
    for b in base_of(s):
        if b in okx_base: pairs.append((s, okx_base[b])); break
print("PANEL_SYMS",len(psyms),"OKX_USDT_LINEAR_LIVE",len(inst),"MATCHED",len(pairs),flush=True)

# ---- funding history ----
fund={}
t0=time.time(); nreq=1
for k,(s,iid) in enumerate(pairs):
    rows=[]; after=None
    for pg in range(6):
        u=f"https://www.okx.com/api/v5/public/funding-rate-history?instId={iid}&limit=100"
        if after: u+=f"&after={after}"
        r=get(u); nreq+=1; time.sleep(SLEEP)
        if "_err" in r: print("ERR",iid,r["_err"],flush=True); break
        d=r.get("data",[])
        if not d: break
        rows+=d; after=d[-1]["fundingTime"]
    if rows:
        # (ts_sec, realizedRate, interval_hours_from_response_spacing)
        ft=np.array([int(x["fundingTime"])//1000 for x in rows],np.int64)
        fr=np.array([float(x["realizedRate"]) for x in rows],np.float64)
        o=np.argsort(ft); ft=ft[o]; fr=fr[o]
        fund[s]=(ft,fr)
    if k%40==0: print(f"[{k}/{len(pairs)}] req={nreq} el={time.time()-t0:.0f}s",flush=True)
print("FUND_OK",len(fund),"REQ",nreq,"ELAPSED",round(time.time()-t0),flush=True)
np.savez_compressed(f"{OUT}/okx_funding_raw.npz",
    syms=np.array(sorted(fund)),
    **{f"ft_{s}":fund[s][0] for s in fund}, **{f"fr_{s}":fund[s][1] for s in fund},
    pairs=np.array([f"{a}|{b}" for a,b in pairs]),
    pulled_utc=np.array(dt.datetime.utcnow().isoformat()+"Z"))
print("WROTE funding",flush=True)
