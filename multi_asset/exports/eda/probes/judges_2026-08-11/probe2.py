import numpy as np
D=np.load("/workspace/data/prod3.npz",allow_pickle=True)
G=np.load("/workspace/data/ohlcv_grid.npz",allow_pickle=True)
rows=D["rows"]; P3=D["C3"]
QV=G["QVOL"].astype(np.float64)[rows]
prod_lq=P3[:,:,2]
mine0=~(QV>0); prod1=prod_lq!=0
hole=mine0&prod1
print(f"覆盖洞(产有我无): {hole.sum():,} 格 / 产有值 {prod1.sum():,} = {hole.sum()/max(prod1.sum(),1)*100:.2f}%")
ts=np.asarray(G["ts"]).astype(np.int64)[rows]
import datetime as dt
yr=np.array([dt.datetime.fromtimestamp(int(t)/1000,dt.timezone.utc).year for t in ts])
for y in sorted(set(yr)):
    m=yr==y
    print(f"  {y}: 洞 {hole[m].sum():,} / 产有值 {prod1[m].sum():,}")
