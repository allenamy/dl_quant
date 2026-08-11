import pandas as pd, numpy as np
from scipy import stats

CSV = "/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv"
df = pd.read_csv(CSV)
df["dt"] = pd.to_datetime(df["datetime_utc"])
df = df.sort_values("timestamp_ms").reset_index(drop=True)
df["date"] = df["dt"].dt.date
df["day_of_month"] = df["dt"].dt.day

def clean_mask(ts_ms):
    ts = ts_ms.values; keep = np.zeros(len(ts), bool); last = -np.inf
    for i, t in enumerate(ts):
        if t - last >= 600_000: keep[i] = True; last = t
    return keep
df["keep"] = False
for _, g in df.groupby("date"):
    df.loc[g.index, "keep"] = clean_mask(g["timestamp_ms"])
cl = df[df["keep"]].copy()

def icp(g):
    return g["y_pred_raw"].corr(g["y_true_ret_bps"]) if len(g)>=20 else np.nan
def ics(g):
    return g["y_pred_raw"].corr(g["y_true_ret_bps"], method="spearman") if len(g)>=20 else np.nan

daily = cl.groupby(["month","date","day_of_month"]).apply(
    lambda g: pd.Series({"ic": icp(g), "ics": ics(g)}), include_groups=False).reset_index()
DRIFT = {"2026_01","2026_02","2026_03","2026_04","2026_05"}

def fe_slope(sub, col="ic"):
    s = sub.dropna(subset=[col]).copy()
    s["y"] = s[col] - s.groupby("month")[col].transform("mean")
    s["x"] = s["day_of_month"] - s.groupby("month")["day_of_month"].transform("mean")
    r = stats.linregress(s["x"], s["y"])
    return r.slope, r.stderr, r.pvalue, len(s)

drift = daily[daily.month.isin(DRIFT)]
print("== drift-month FE slope, leave-one-month-out (Pearson) ==")
for drop in [None]+sorted(DRIFT):
    sub = drift if drop is None else drift[drift.month != drop]
    sl, se, p, n = fe_slope(sub)
    print(f"drop={str(drop):8s} slope={sl:+.5f} se={se:.5f} p={p:.3f} 30d={sl*30:+.4f} n={n}")

print("\n== drift-month FE slope, Spearman caliber ==")
sl, se, p, n = fe_slope(drift, "ics")
print(f"all-drift: slope={sl:+.5f} p={p:.3f} 30d={sl*30:+.4f}")
for drop in sorted(DRIFT):
    sl, se, p, n = fe_slope(drift[drift.month != drop], "ics")
    print(f"drop={drop}: slope={sl:+.5f} p={p:.3f} 30d={sl*30:+.4f}")

print("\n== non-drift Spearman slope ==")
nd = daily[~daily.month.isin(DRIFT)]
sl, se, p, n = fe_slope(nd, "ics")
print(f"non-drift: slope={sl:+.5f} p={p:.3f} 30d={sl*30:+.4f}")

# half-month split (coarser, robust): first-half vs second-half mean per-day IC per month
print("\n== first-half (day<=15) vs second-half per-day-CLEAN IC ==")
daily["half"] = np.where(daily.day_of_month<=15, "H1","H2")
hm = daily.pivot_table(index="month", columns="half", values="ic", aggfunc="mean")
hm["d"] = hm["H2"]-hm["H1"]
print(hm.round(4).to_string())
d_drift = hm.loc[hm.index.isin(DRIFT), "d"]; d_nd = hm.loc[~hm.index.isin(DRIFT), "d"]
print(f"drift mean H2-H1: {d_drift.mean():+.4f} (t={d_drift.mean()/(d_drift.std()/np.sqrt(len(d_drift))):+.2f}, n={len(d_drift)})")
print(f"non-drift mean H2-H1: {d_nd.mean():+.4f} (t={d_nd.mean()/(d_nd.std()/np.sqrt(len(d_nd))):+.2f}, n={len(d_nd)})")

# quantify what an online model could recover in drift months if slope were causal
sl_all, _, _, _ = fe_slope(drift)
print(f"\nIf drift slope causal: mean staleness 15.5d -> ~1d saves {sl_all*(-14.5):+.4f} IC in drift months")
print(f"drift-month mean per-day-CLEAN IC: {drift['ic'].mean():.4f}; target 0.08 gap: {0.08-drift['ic'].mean():.4f}")
