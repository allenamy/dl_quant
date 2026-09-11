"""R5 NEW-DATA acquisition. data.binance.vision BULK ARCHIVES ONLY (no REST, no signed endpoint, no credentials).
Families: premiumIndexKlines/1h  (the PREMIUM INDEX = spot-perp basis, Binance USDT-perp)
          fundingRate            (realised funding settlements, with true settlement timestamps)
Coverage driven by the panel: for each symbol, the months in which wide_panel_4h_v2ext.npz has a finite
f_fund_now, widened by one month on each side. Downloads run on pod2 (a GPU box), NOT on any machine that
touches the trading API. Concurrency 10, static CDN, no auth."""
import os, sys, json, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
R="/workspace/uplift_2026-09-11/r5_basis"
FAM=sys.argv[1]   # prem | fund
INFO=json.load(open(R+"/sym_months.json"))
def months(a,b):
    y0,m0=map(int,a.split("-")); y1,m1=map(int,b.split("-"))
    # widen by one month each side
    m0-=1
    if m0==0: y0-=1; m0=12
    m1+=1
    if m1==13: y1+=1; m1=1
    out=[]
    y,m=y0,m0
    while (y,m)<=(y1,m1):
        out.append("%04d-%02d"%(y,m))
        m+=1
        if m==13: y+=1; m=1
    return out
jobs=[]
for s,v in INFO.items():
    if not v: continue
    for mm in months(v[0],v[1]):
        if FAM=="prem":
            url="https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/%s/1h/%s-1h-%s.zip"%(s,s,mm)
            dst=R+"/raw/prem/%s/%s-1h-%s.zip"%(s,s,mm)
        else:
            url="https://data.binance.vision/data/futures/um/monthly/fundingRate/%s/%s-fundingRate-%s.zip"%(s,s,mm)
            dst=R+"/raw/fund/%s/%s-fundingRate-%s.zip"%(s,s,mm)
        jobs.append((url,dst))
print("FAM",FAM,"jobs",len(jobs),flush=True)
ok=[0]; miss=[0]; err=[0]; t0=time.time()
def get(j):
    url,dst=j
    if os.path.exists(dst): ok[0]+=1; return
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=45) as r: b=r.read()
            with open(dst+".tmp","wb") as f: f.write(b)
            os.replace(dst+".tmp",dst); ok[0]+=1; return
        except urllib.error.HTTPError as e:
            if e.code==404: miss[0]+=1; return
            time.sleep(1.0+attempt)
        except Exception: time.sleep(1.0+attempt)
    err[0]+=1
with ThreadPoolExecutor(max_workers=10) as ex:
    for i,_ in enumerate(ex.map(get,jobs)):
        if i%2000==0: print(i,"ok",ok[0],"404",miss[0],"err",err[0],"%.0fs"%(time.time()-t0),flush=True)
print("DONE",FAM,"ok",ok[0],"404",miss[0],"err",err[0],"%.0fs"%(time.time()-t0),flush=True)
