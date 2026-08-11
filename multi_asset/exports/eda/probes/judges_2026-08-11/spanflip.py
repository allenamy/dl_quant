import json, os
import numpy as np, pandas as pd
W = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
tab = json.load(open("/tmp/0c_span.json"))["table"]
names = ["ANKRUSDT","AXSUSDT","ENJUSDT","GMTUSDT","ONTUSDT","RVNUSDT","SKLUSDT",
         "STGUSDT","STORJUSDT","XTZUSDT","ZILUSDT"]
print("%-12s %6s %8s %7s %7s %14s" % ("symbol","表span","现算span","#8h","#4h","翻转还需"))
for s in names:
    p = os.path.join(W, s + "_funding.csv")
    if not os.path.exists(p):
        print("%-12s  (无 csv)" % s); continue
    d = pd.read_csv(p)
    iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").dropna()
    med = float(np.median(iv)); now = max(2, int(round(24.0 / max(med, 1.0))))
    n8 = int((iv == 8).sum()); n4 = int((iv == 4).sum())
    print("%-12s %6d %8d %7d %7d %14d" % (s, tab[s]["span"], now, n8, n4, max(0, n8 - n4)))
