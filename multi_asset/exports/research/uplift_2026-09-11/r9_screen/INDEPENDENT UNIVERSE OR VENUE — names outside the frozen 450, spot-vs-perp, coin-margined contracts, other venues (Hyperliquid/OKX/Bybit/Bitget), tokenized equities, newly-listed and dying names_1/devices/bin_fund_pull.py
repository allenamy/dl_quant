"""Binance fundingRate monthly archives for the OKX overlap window (cold-start control).
ENV WHITELIST (E-0826-D) = EMPTY SET. Source: data.binance.vision static CDN, anonymous, no credentials.
User ruling STATE.md L196 (2026-09-05) exempts this CDN from the <=4 req/s rule on pod2. 8 concurrent used."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import io,zipfile,urllib.request,numpy as np,datetime as dt,json
from concurrent.futures import ThreadPoolExecutor
OUT="/workspace/r9okx"; os.makedirs(OUT,exist_ok=True)
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
psyms=[str(x) for x in P["symbols"]]
MONTHS=["2026-05","2026-06","2026-07","2026-08"]
def one(s):
    rows=[]
    for mo in MONTHS:
        u=f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{mo}.zip"
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"research/1.0"}),timeout=40).read()
            z=zipfile.ZipFile(io.BytesIO(b)); n=z.namelist()[0]
            for ln in z.read(n).decode().splitlines():
                p=ln.split(",")
                if not p or not p[0].strip() or not p[0].strip()[0].isdigit(): continue
                rows.append((int(p[0]), float(p[2]), float(p[1])))  # calc_time_ms, last_funding_rate, interval_h
        except Exception:
            pass
    if not rows: return s,None
    rows.sort()
    ft=np.array([r[0]//1000 for r in rows],np.int64); fr=np.array([r[1] for r in rows]); iv=np.array([r[2] for r in rows])
    _,k=np.unique(ft,return_index=True)
    return s,(ft[k],fr[k],iv[k])
res={}
with ThreadPoolExecutor(8) as ex:
    for s,v in ex.map(one,psyms):
        if v is not None: res[s]=v
print("BIN_FUND_OK",len(res),flush=True)
np.savez_compressed(f"{OUT}/bin_funding_raw.npz", syms=np.array(sorted(res)),
    **{f"ft_{s}":res[s][0] for s in res}, **{f"fr_{s}":res[s][1] for s in res}, **{f"iv_{s}":res[s][2] for s in res},
    pulled_utc=np.array(dt.datetime.utcnow().isoformat()+"Z"), months=np.array(MONTHS))
print("WROTE",flush=True)
