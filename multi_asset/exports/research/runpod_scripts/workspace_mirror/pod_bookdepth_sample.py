"""bookDepth 抽样: 30 名(各tier 10)× 近5日 → spread/depth 分tier先验(T2/T3 成本假设的免钱实测).
data.binance.vision futures/um/daily/bookDepth: 每日 zip, 列=timestamp,percentage,depth,notional(1%,±档).
"""
import io, csv, json, time, zipfile, urllib.request, socket, os
import numpy as np
import sys; sys.path.insert(0, "/workspace")
socket.setdefaulttimeout(30)
MT = np.load("/workspace/data/wide_fea_v1_meta.npz", allow_pickle=True)
qvk = MT["qvk"]; members = MT["members"]
Z = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
syms = [str(s) for s in Z["symbols"]]
i = len(MT["E_ts"]) - 2
m = members[i]
qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
order = m[np.argsort(-qv4h)]
t1 = [syms[j] for j in order[:60] if qv4h[list(m).index(j)] >= 5e6][:10] if False else [syms[j] for j in order[:10]]
mid = [syms[j] for j in order[len(order)//3: len(order)//3+10]]
tail = [syms[j] for j in order[-40:-30]]
DAYS = ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14"]
out = {}
for grp, lst in (("T1", t1), ("T2", mid), ("T3", tail)):
    stats = []
    for s in lst:
        for d in DAYS:
            u = f"https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip"
            p = f"/tmp/bd_{s}_{d}.zip"
            try:
                urllib.request.urlretrieve(u, p)
                zf = zipfile.ZipFile(p)
                with zf.open(zf.namelist()[0]) as fh:
                    rd = csv.reader(io.TextIOWrapper(fh))
                    hdr = next(rd)
                    for row in rd:
                        try:
                            pct = float(row[1]); notion = float(row[3])
                            if abs(abs(pct) - 1.0) < 1e-6:
                                stats.append(notion)
                        except Exception: continue
                os.remove(p)
            except Exception:
                continue
    if stats:
        a = np.array(stats)
        out[grp] = {"n": len(a), "depth1pct_median_usd": float(np.median(a)),
                    "depth1pct_p25": float(np.percentile(a, 25))}
        print(f"[{grp}] ±1%档深度: 中位 ${out[grp]['depth1pct_median_usd']/1e3:.0f}k P25 ${out[grp]['depth1pct_p25']/1e3:.0f}k (n={len(a)})", flush=True)
json.dump(out, open("/workspace/bookdepth_sample.json", "w"), indent=1)
print("BOOKDEPTH_DONE", flush=True)
