"""RunPod 侧多源原始数据拉取 —— 高并发摊薄小文件开销(16 vCPU ⇒ 32 线程)。
只增不删; 原子写; 已存在跳过。用法: rp_fetch.py <kind> <days>
kind ∈ {metrics, bookDepth, aggTrades, liquidationSnapshot, klines1h, spotKlines1h}"""
import io,os,sys,time,zipfile,datetime as dt,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
KIND=sys.argv[1]; DAYS=int(sys.argv[2]) if len(sys.argv)>2 else 1160
OUT=f"/workspace/data/raw/{KIND}"; os.makedirs(OUT,exist_ok=True)
SYMS=[s.strip() for s in open("/workspace/data/universe.txt")] if os.path.exists("/workspace/data/universe.txt") else []
END=dt.date(2026,8,5); DATES=[(END-dt.timedelta(days=i)).isoformat() for i in range(DAYS)]
URL={"metrics":"futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip",
     "bookDepth":"futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip",
     "aggTrades":"futures/um/daily/aggTrades/{s}/{s}-aggTrades-{d}.zip",
     "liquidationSnapshot":"futures/um/daily/liquidationSnapshot/{s}/{s}-liquidationSnapshot-{d}.zip",
     "klines1h":"futures/um/daily/klines/{s}/1h/{s}-1h-{d}.zip",
     "spotKlines1h":"spot/daily/klines/{s}/1h/{s}-1h-{d}.zip"}[KIND]
def one(a):
    s,d=a; p=f"{OUT}/{s}-{d}.csv"
    if os.path.exists(p) and os.path.getsize(p)>50: return "skip"
    u="https://data.binance.vision/data/"+URL.format(s=s,d=d)
    for _ in range(2):
        try:
            with urllib.request.urlopen(u,timeout=60) as r: raw=r.read()
            if len(raw)<100: return "empty"
            z=zipfile.ZipFile(io.BytesIO(raw))
            with open(p+".part","wb") as f: f.write(z.read(z.namelist()[0]))
            os.replace(p+".part",p); return "ok"
        except urllib.error.HTTPError as e:
            if e.code==404: return "404"
            time.sleep(1)
        except Exception: time.sleep(1)
    return "fail"
jobs=[(s,d) for s in SYMS for d in DATES]
t0=time.time(); c={"ok":0,"skip":0,"404":0,"fail":0,"empty":0}
with ThreadPoolExecutor(max_workers=32) as ex:
    for i,r in enumerate(ex.map(one,jobs),1):
        c[r]=c.get(r,0)+1
        if i%2000==0:
            el=time.time()-t0
            print(f"  {i:,}/{len(jobs):,} {c} {el/60:.1f}min 剩 {(len(jobs)-i)*el/i/60:.0f}min",flush=True)
print(f"{KIND} 完成: {c} 用时 {(time.time()-t0)/60:.1f}min  {OUT}")
