"""Approach-C floor: project the PROVEN single-asset BTC model onto alts.
 yhat_alt = beta_i * yhat_BTC(single-asset REG_arch). Eval per-asset Pearson+Spearman
on the overlap period. This is the baseline every multi-asset model must beat.

Single-asset BTC preds: exports/reg_arch_standalone_eval/fold_{0,1,2}_test_preds.npz
  keys: predictions (N,3) z-space [q10,q50,q90], targets, timestamps (us), y_sigma, y_median.
Cache alt y: panel_cache/<sym>.npz  y (raw fwd-600 logret), ts (ns), clean600.
"""
import numpy as np, json, os.path as p, glob
from scipy.stats import pearsonr, spearmanr

PREDS = "/mnt/storage/private/work_hsy/quant_research_multi_asset/_sa_btc_preds"  # pushed here
CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
ALTS = ["bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada","bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]

# load single-asset BTC q50 in return units, ts in ns
btc_ts, btc_yhat = [], []
for f in sorted(glob.glob(p.join(PREDS, "fold_*_test_preds.npz"))):
    d = np.load(f)
    q50 = d["predictions"][:,1]*float(d["y_sigma"]) + float(d["y_median"])
    ts_ns = d["timestamps"].astype(np.int64) * 1000   # us -> ns
    msk = d["mask"].astype(bool) if "mask" in d else np.ones(len(q50),bool)
    btc_ts.append(ts_ns[msk]); btc_yhat.append(q50[msk])
btc_ts = np.concatenate(btc_ts); btc_yhat = np.concatenate(btc_yhat)
btc_ts = btc_ts.astype(np.int64); order = np.argsort(btc_ts); btc_ts, btc_yhat = btc_ts[order], btc_yhat[order]
btc_map = dict(zip(btc_ts.tolist(), btc_yhat.tolist()))
import pandas as pd
print(f"single-asset BTC preds: n={len(btc_ts)}, ts {pd.Timestamp(int(btc_ts[0]))} .. {pd.Timestamp(int(btc_ts[-1]))}")

# BTC cache y for beta estimation + alignment check
dbtc = np.load(p.join(CACHE,"bnfbtc.npz")); btc_cache_ts=dbtc["ts"]; btc_cache_y=dbtc["y"]
# alignment: how many cache BTC ts match single-asset pred ts exactly?
inter = np.intersect1d(btc_cache_ts, btc_ts)
print(f"exact ts overlap (cache BTC vs SA preds): {len(inter)} "
      f"(cache n={len(btc_cache_ts)}, in overlap window)")
if len(inter) < 1000:
    # try nearest within 1s
    print("few exact matches — checking nearest-second alignment...")
    sa_sec = set((btc_ts//1_000_000_000).tolist())
    cache_sec = (btc_cache_ts//1_000_000_000)
    near = np.isin(cache_sec, list(sa_sec)).sum()
    print(f"  nearest-second overlap: {near}")

# nearest-window alignment (different 180s grid origins) via merge_asof, tol 90s
import pandas as pd
TOL = 90 * 1_000_000_000   # 90s in ns
sa = pd.DataFrame({"ts": btc_ts, "yhat_btc": btc_yhat}).sort_values("ts")
btc_y_df = pd.DataFrame({"ts": btc_cache_ts.astype(np.int64), "btc_y": btc_cache_y}).sort_values("ts")
results={}
for s in ["bnfbtc"]+ALTS:
    d=np.load(p.join(CACHE,f"{s}.npz"))
    alt = pd.DataFrame({"ts": d["ts"].astype(np.int64), "y": d["y"], "clean": d["clean600"]}).sort_values("ts")
    # match alt windows to nearest SA BTC pred within 90s
    mg = pd.merge_asof(alt, sa, on="ts", direction="nearest", tolerance=TOL).dropna(subset=["yhat_btc"])
    # attach contemporaneous cache BTC y for beta
    mg = pd.merge_asof(mg, btc_y_df, on="ts", direction="nearest", tolerance=TOL).dropna(subset=["btc_y"])
    mg = mg[mg["clean"].astype(bool) & np.isfinite(mg["y"])]
    if len(mg) < 500:
        results[s]={"error":f"insufficient overlap ({len(mg)})"}; continue
    if s=="bnfbtc":
        P=pearsonr(mg["yhat_btc"],mg["y"])[0]; S=spearmanr(mg["yhat_btc"],mg["y"])[0]
        results[s]={"P":round(float(P),4),"S":round(float(S),4),"n":int(len(mg)),"note":"SA-BTC-pred vs cache-BTC-y sanity (expect ~0.065/0.072)"}
        continue
    beta = float(np.cov(mg["y"], mg["btc_y"])[0,1]/np.var(mg["btc_y"]))
    yhat_alt = beta * mg["yhat_btc"].values
    P=pearsonr(yhat_alt, mg["y"])[0]; S=spearmanr(yhat_alt, mg["y"])[0]
    results[s]={"beta":round(beta,3),"P":round(float(P),4),"S":round(float(S),4),"n":int(len(mg))}

valid=[r for s,r in results.items() if s!="bnfbtc" and "P" in r]
summary={"analysis":"approach_C_beta_projection_floor","preds_dir":PREDS,
         "btc_sanity":results.get("bnfbtc"),
         "avg_alt_P":round(float(np.mean([r["P"] for r in valid])),4) if valid else None,
         "avg_alt_S":round(float(np.mean([r["S"] for r in valid])),4) if valid else None,
         "per_alt":results}
json.dump(summary, open(p.join(CACHE,"..","eda","approach_c_floor.json"),"w"), indent=2)
print(json.dumps(summary, indent=2))
