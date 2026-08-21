"""基差族拉取 —— 用【月度】归档, 请求数比日度少 30 倍。
族: premiumIndexKlines(基差直接量) / markPriceKlines / indexPriceKlines / spot klines(场内对照)
★ 独立脚本, 不改正在运行的 fetch_all.sh / rp_fetch.py。"""
import io,os,sys,time,zipfile,datetime as dt,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
KIND=sys.argv[1]
URL={"premiumIndexKlines":"futures/um/monthly/premiumIndexKlines/{s}/1h/{s}-1h-{m}.zip",
     "markPriceKlines":   "futures/um/monthly/markPriceKlines/{s}/1h/{s}-1h-{m}.zip",
     "indexPriceKlines":  "futures/um/monthly/indexPriceKlines/{s}/1h/{s}-1h-{m}.zip",
     "spotKlines1hM":     "spot/monthly/klines/{s}/1h/{s}-1h-{m}.zip",
     "perpKlines1hM":     "futures/um/monthly/klines/{s}/1h/{s}-1h-{m}.zip",
     "fundingRate":       "futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"}[KIND]
OUT=f"/workspace/data/raw/{KIND}"; os.makedirs(OUT,exist_ok=True)
SYMS=[s.strip() for s in open("/workspace/data/universe.txt") if s.strip()]
MONTHS=[]
y,m=2021,1
while (y,m)<=(2026,7):
    MONTHS.append(f"{y:04d}-{m:02d}"); m+=1
    if m>12: m=1; y+=1
def one(a):
    s,mo=a; p=f"{OUT}/{s}-{mo}.csv"
    if os.path.exists(p) and os.path.getsize(p)>50: return "skip"
    u="https://data.binance.vision/data/"+URL.format(s=s,m=mo)
    for _ in range(2):
        try:
            with urllib.request.urlopen(u,timeout=90) as r: raw=r.read()
            z=zipfile.ZipFile(io.BytesIO(raw))
            with open(p+".part","wb") as f: f.write(z.read(z.namelist()[0]))
            os.replace(p+".part",p); return "ok"
        except urllib.error.HTTPError as e:
            if e.code==404: return "404"
            time.sleep(1)
        except Exception: time.sleep(1)
    return "fail"
jobs=[(s,mo) for s in SYMS for mo in MONTHS]
print(f"[{KIND}] {len(SYMS)} 币 × {len(MONTHS)} 月 = {len(jobs):,} 请求 (日度需 {len(SYMS)*1160:,})",flush=True)
st={"ok":0,"skip":0,"404":0,"fail":0}; t0=time.time()
with ThreadPoolExecutor(max_workers=48) as ex:
    for i,r in enumerate(ex.map(one,jobs),1):
        st[r]+=1
        if i%1000==0: print(f"  {i:,}/{len(jobs):,} {st} {(time.time()-t0)/60:.1f}min",flush=True)
print(f"[{KIND}] 完成 {st} 用时 {(time.time()-t0)/60:.1f}min",flush=True)
