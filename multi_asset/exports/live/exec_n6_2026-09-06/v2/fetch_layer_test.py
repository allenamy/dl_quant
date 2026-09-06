"""Standalone fetch-layer test for producer v2 (public API only, outside anchor windows): (1) klines for 450 symbols sequential vs 6-worker parallel
(same window ending at the 04Z anchor) — identical rows?, latency, errors; (2) bulk fundingRate 8h-window pagination vs per-symbol for 60 due names."""
import re, json, time, urllib.request, threading, concurrent.futures, os, sys, hashlib
S=os.path.dirname(os.path.abspath(__file__)); src=open(S+"/shadow_loop_v3_v2.py").read()
cls=src[src.index("class Fetcher:"):src.index("# ── bundle 加载")]
BASE="https://fapi.binance.com"; FETCH_BUDGET=int(os.environ.get("FETCH_BUDGET","480")); HTTP_TIMEOUT=10.0
ns={"time":time,"json":json,"urllib":urllib,"threading":threading,"BASE":BASE,"FETCH_BUDGET":FETCH_BUDGET,"HTTP_TIMEOUT":HTTP_TIMEOUT}; exec(cls, ns); Fetcher=ns["Fetcher"]
N=1788667200; out={"anchor":N}
xi=json.loads(urllib.request.urlopen(BASE+"/fapi/v1/exchangeInfo", timeout=15).read())
syms=sorted(x["symbol"] for x in xi["symbols"] if x.get("contractType")=="PERPETUAL" and x.get("quoteAsset")=="USDT" and x.get("status")=="TRADING")[:450]
q=lambda s: ("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": 52, "endTime": N*1000-1})
def run(workers):
    fx=Fetcher(); t0=time.time(); res={}
    if workers>1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for s,r in zip(syms, ex.map(lambda s: fx.get(*q(s), weight=1), syms)): res[s]=r
    else:
        for s in syms: res[s]=fx.get(*q(s), weight=1)
    dt=time.time()-t0; errs=sum(1 for r in res.values() if isinstance(r,dict))
    sha=hashlib.sha256(json.dumps({s:res[s] for s in syms if not isinstance(res[s],dict)}, sort_keys=True).encode()).hexdigest()[:16]
    return {"workers":workers,"seconds":round(dt,1),"req":fx.n_req,"err":errs,"weight_used":fx.weight_used,"rows_sha":sha, "per_req_ms": round(dt/len(syms)*1000,1)}
seq=run(1); print("klines sequential:", seq, flush=True)
time.sleep(max(0, 61-seq["seconds"]))  # next budget window
par=run(6); print("klines parallel x6:", par, flush=True)
out["klines"]={"seq":seq,"par6":par,"identical":seq["rows_sha"]==par["rows_sha"]}
# funding: bulk 8h window with pagination vs per-symbol (60 names that settled at N)
fx=Fetcher(); start=(N-8*3600+1)*1000; seen=set(); bulk={}; pages=0
while pages<6:
    r=fx.get("/fapi/v1/fundingRate", {"startTime": start, "endTime": N*1000+999, "limit": 1000}, weight=1); pages+=1
    if isinstance(r,dict): print("bulk err", r); break
    for row in r:
        k=(row["symbol"], int(row["fundingTime"]))
        if k in seen: continue
        seen.add(k); bulk.setdefault(row["symbol"],[]).append(row)
    if len(r)<1000: break
    start=int(r[-1]["fundingTime"])
print("bulk pages", pages, "rows", len(seen), "symbols", len(bulk), flush=True)
due=[s for s in syms if any(int(x["fundingTime"])//1000==N for x in bulk.get(s,[]))][:60]
mism=[]; t0=time.time()
for s in due:
    r=fx.get("/fapi/v1/fundingRate", {"symbol": s, "startTime": (N-8*3600+1)*1000, "endTime": N*1000+999, "limit": 100}, weight=1); time.sleep(0.25)
    a=[(int(x["fundingTime"]), x["fundingRate"], x.get("markPrice")) for x in r] if isinstance(r,list) else None
    b=sorted([(int(x["fundingTime"]), x["fundingRate"], x.get("markPrice")) for x in bulk.get(s,[])])
    if a!=b: mism.append((s,a,b))
print("funding parity: per-symbol vs bulk over", len(due), "due names; mismatches", len(mism), mism[:2], "elapsed", round(time.time()-t0,1), "s", flush=True)
out["funding"]={"bulk_pages":pages,"bulk_rows":len(seen),"bulk_symbols":len(bulk),"n_due_checked":len(due),"mismatches":len(mism)}
json.dump(out, open(S+"/fetch_layer_test.json","w"), indent=1); print("DONE", json.dumps(out))
