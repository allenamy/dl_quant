#!/usr/bin/env python3
"""P1: data-availability probe (public endpoints, <=1 req/s). For anchors listed in ANCHORS (epoch s), at N+10s query klines
(endTime=N-1ms) for KL symbols, and at N+20s/+45s/+75s/+120s/+240s query fundingRate for FR symbols; log presence of the N row."""
import json, time, urllib.request, sys, os
BASE="https://fapi.binance.com"; OUT=os.path.dirname(os.path.abspath(__file__))+"/probe_log.jsonl"
FR=json.loads(os.environ["FR_SYMS"]); KL=json.loads(os.environ["KL_SYMS"]); ANCHORS=[int(x) for x in os.environ["ANCHORS"].split(",")]
def get(path, params):
    q="&".join(f"{k}={v}" for k,v in params.items()); t0=time.time()
    try:
        with urllib.request.urlopen(f"{BASE}{path}?{q}", timeout=10) as r: return json.loads(r.read()), r.headers.get("X-MBX-USED-WEIGHT-1M"), time.time()-t0
    except Exception as e: return {"_err": str(e)[:100]}, None, time.time()-t0
def log(d): open(OUT,"a").write(json.dumps(d)+"\n")
for N in ANCHORS:
    wait=N+10-time.time()
    if wait>0: time.sleep(wait)
    if time.time()>N+600: log({"anchor":N,"skip":"too late"}); continue
    # klines at N+10s
    for s in KL:
        r,w,lat=get("/fapi/v1/klines",{"symbol":s,"interval":"5m","limit":3,"endTime":N*1000-1})
        last_close=(int(r[-1][0])+300000)//1000 if isinstance(r,list) and r else None
        log({"anchor":N,"t_after":round(time.time()-N,1),"kind":"kline","symbol":s,"last_bar_close":last_close,"has_bar_closing_at_N":(last_close==N),"weight":w,"lat":round(lat,2)}); time.sleep(1.0)
    for dt in (20,45,75,120,240):
        wait=N+dt-time.time()
        if wait>0: time.sleep(wait)
        for s in FR:
            r,w,lat=get("/fapi/v1/fundingRate",{"symbol":s,"startTime":(N-9*3600)*1000,"endTime":N*1000+999,"limit":20})
            fts=[int(x["fundingTime"])//1000 for x in r] if isinstance(r,list) else []
            log({"anchor":N,"t_after":round(time.time()-N,1),"kind":"funding","symbol":s,"has_N_row":(N in fts),"last_ft":(max(fts) if fts else None),"n":len(fts),"weight":w,"lat":round(lat,2),"err":(r.get("_err") if isinstance(r,dict) else None)}); time.sleep(1.0)
log({"done":True,"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
