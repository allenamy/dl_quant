import json, time, numpy as np, sys
sys.path.insert(0, "/workspace")
exec(open("/workspace/pod_turnover_window.py").read().split("T = np.array(rows)")[0])   # 复用: 得到 rows=(ts,turnover,gross,sel,k)
T = np.array(rows); gts = {int(t): g for t, tr, g, s, k in rows}
arr = np.load("/workspace/exports_train/nets_histv2_-30_2_42.npy")
ts = arr[:, 0].astype(int); net = arr[:, 1]
g = np.array([gts.get(int(t), np.nan) for t in ts]); ok = np.isfinite(g) & (g > 0.2) & np.isfinite(net)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts])
res = {}
for y0 in (2022, 2024):
    m = ok & (yrs >= y0); pu = net[m] / g[m]          # 每单位 gross 的净 bps/锚
    for shr in (1.0, 0.55):
        x = pu - pu.mean() * (1 - shr)
        rng = np.random.RandomState(11); L_ = 180; nb = len(x)//L_; NY = 2190; nbk = NY//L_ + 1
        out = {"n": int(m.sum()), "mean_per_gross": round(float(pu.mean()),3), "sd_per_gross": round(float(pu.std()),2)}
        for G in (2.0, 3.0, 3.5):
            hit = 0; ann = []
            for _ in range(2000):
                idx = rng.randint(0, nb, nbk); path = np.concatenate([x[i*L_:(i+1)*L_] for i in idx])[:NY] * G / 1e4
                cum = np.cumprod(1 + path); dd = cum/np.maximum.accumulate(cum) - 1; hit += dd.min() <= -0.25; ann.append(cum[-1]-1)
            out[f"gross{G}"] = {"P_hit_-25%": round(hit/2000, 3), "ann_median": round(float(np.median(ann)), 3), "ann_p5": round(float(np.percentile(ann,5)),3)}
        res[f"y{y0}_shr{shr}"] = out; print(f"wide_constgross y{y0} shr{shr}", json.dumps(out), flush=True)
json.dump(res, open("/workspace/lev_wide_constgross.json", "w"), indent=1)
