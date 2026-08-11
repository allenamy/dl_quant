import pandas as pd, numpy as np
from scipy import stats

CSV = "/Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv"
df = pd.read_csv(CSV)
df["dt"] = pd.to_datetime(df["datetime_utc"])
df = df.sort_values("timestamp_ms").reset_index(drop=True)
df["date"] = df["dt"].dt.date
df["day_of_month"] = df["dt"].dt.day

# ---- CLEAN subsample: within each day keep rows >=600s apart (greedy) ----
def clean_mask(ts_ms):
    ts = ts_ms.values
    keep = np.zeros(len(ts), bool)
    last = -np.inf
    for i, t in enumerate(ts):
        if t - last >= 600_000:
            keep[i] = True
            last = t
    return keep

mask = np.concatenate([clean_mask(g["timestamp_ms"]) for _, g in df.groupby("date", sort=True)])
# groupby(sort=True) on date of a sorted df preserves original order within groups; rebuild carefully:
df["keep"] = False
for _, g in df.groupby("date"):
    df.loc[g.index, "keep"] = clean_mask(g["timestamp_ms"])
cl = df[df["keep"]].copy()
print(f"rows total={len(df)} clean={len(cl)}  months={sorted(df['month'].unique())}")

def ic(g, px="y_pred_raw", yx="y_true_ret_bps"):
    if len(g) < 20 or g[px].std() == 0 or g[yx].std() == 0: return np.nan
    return g[px].corr(g[yx])

# anchor caliber: per-day-CLEAN pooled (raw and demeaned)
for px, yx, tag in [("y_pred_raw","y_true_ret_bps","raw"),("y_pred_demeaned","y_true_demeaned_bps","demeaned")]:
    daily = cl.groupby("date").apply(lambda g: ic(g,px,yx), include_groups=False)
    print(f"per-day-CLEAN pooled mean ({tag}): {daily.mean():.4f}  n_days={daily.notna().sum()}")

PX, YX = "y_pred_raw", "y_true_ret_bps"   # will switch if demeaned matches 0.0387 anchor
daily = cl.groupby(["month","date","day_of_month"]).apply(lambda g: ic(g,PX,YX), include_groups=False).rename("ic").reset_index()
dailyD = cl.groupby(["month","date","day_of_month"]).apply(lambda g: ic(g,"y_pred_demeaned","y_true_demeaned_bps"), include_groups=False).rename("ic").reset_index()

DRIFT = {"2026_01","2026_02","2026_03","2026_04","2026_05"}
daily["drift"] = daily["month"].isin(DRIFT)
daily["week"] = ((daily["day_of_month"]-1)//7 + 1).clip(upper=5)
dailyD["drift"] = dailyD["month"].isin(DRIFT)
dailyD["week"] = ((dailyD["day_of_month"]-1)//7 + 1).clip(upper=5)

print("\n==== 1) per-month IC by test-week (per-day-CLEAN mean, raw) ====")
pt = daily.pivot_table(index="month", columns="week", values="ic", aggfunc="mean")
pt["n_days"] = daily.groupby("month")["ic"].count()
print(pt.round(4).to_string())

print("\n==== 2) pooled decay: IC vs day-of-month ====")
for lab, sub in [("ALL", daily), ("drift(2026)", daily[daily.drift]), ("non-drift(2025)", daily[~daily.drift])]:
    wk = sub.groupby("week")["ic"].agg(["mean","std","count"])
    wk["se"] = wk["std"]/np.sqrt(wk["count"])
    print(f"-- {lab} weekly means:")
    print(wk.round(4).to_string())
    # regression per-day IC ~ day_of_month with month fixed effects (demean within month)
    s = sub.dropna(subset=["ic"]).copy()
    s["ic_dm"] = s["ic"] - s.groupby("month")["ic"].transform("mean")
    s["dom_dm"] = s["day_of_month"] - s.groupby("month")["day_of_month"].transform("mean")
    res = stats.linregress(s["dom_dm"], s["ic_dm"])
    print(f"   slope(IC per day, month-FE): {res.slope:+.5f}  se={res.stderr:.5f}  t={res.slope/res.stderr:+.2f}  p={res.pvalue:.3f}  n_days={len(s)}")
    print(f"   => implied IC change over 30d: {res.slope*30:+.4f}")

print("\n==== per-month slopes (raw) ====")
rows=[]
for m, g in daily.dropna(subset=["ic"]).groupby("month"):
    r = stats.linregress(g["day_of_month"], g["ic"])
    rows.append((m, r.slope, r.stderr, r.slope*30, g["ic"].mean(), len(g)))
sl = pd.DataFrame(rows, columns=["month","slope","se","d30","meanIC","n"])
print(sl.round(4).to_string(index=False))
print(f"drift months mean slope*30: {sl[sl.month.isin(DRIFT)]['d30'].mean():+.4f} | non-drift: {sl[~sl.month.isin(DRIFT)]['d30'].mean():+.4f}")

print("\n==== 3) month-boundary jump: last-3-days of M vs first-3-days of M+1 ====")
months = sorted(daily["month"].unique())
rows=[]
for a, b in zip(months[:-1], months[1:]):
    # only adjacent calendar months
    ya, ma = map(int, a.split("_")); yb, mb = map(int, b.split("_"))
    adjacent = (yb*12+mb) - (ya*12+ma) == 1
    ga = daily[daily.month==a]; gb = daily[daily.month==b]
    last3 = ga.nlargest(3,"day_of_month")["ic"].mean()
    first3 = gb.nsmallest(3,"day_of_month")["ic"].mean()
    # pooled-corr version too (more stable): pool clean rows of those days
    la_days = ga.nlargest(3,"day_of_month")["date"]; fb_days = gb.nsmallest(3,"day_of_month")["date"]
    pl = ic(cl[cl.date.isin(la_days)]); pf = ic(cl[cl.date.isin(fb_days)])
    rows.append((a,b,adjacent,last3,first3,first3-last3,pl,pf,pf-pl))
bd = pd.DataFrame(rows, columns=["M","M+1","adjacent","last3_dayIC","first3_dayIC","jump_dayIC","last3_pooled","first3_pooled","jump_pooled"])
print(bd.round(4).to_string(index=False))
adj = bd[bd.adjacent]
print(f"\nADJACENT boundaries only (n={len(adj)}): mean jump dayIC {adj['jump_dayIC'].mean():+.4f} (t={adj['jump_dayIC'].mean()/(adj['jump_dayIC'].std()/np.sqrt(len(adj))):+.2f}), pooled {adj['jump_pooled'].mean():+.4f}")
adj_d = adj[adj["M+1"].isin(DRIFT)]
adj_n = adj[~adj["M+1"].isin(DRIFT)]
print(f"  into drift months (n={len(adj_d)}): dayIC jump {adj_d['jump_dayIC'].mean():+.4f} | into non-drift (n={len(adj_n)}): {adj_n['jump_dayIC'].mean():+.4f}")

# null: within-month random 3-day-block deltas, to size boundary jump
print("\n==== null scale: within-month, |mean(3-day block) - mean(prev 3-day block)| ====")
deltas=[]
for m,g in daily.dropna(subset=["ic"]).groupby("month"):
    v = g.sort_values("day_of_month")["ic"].values
    for i in range(0, len(v)-6, 3):
        deltas.append(np.mean(v[i+3:i+6])-np.mean(v[i:i+3]))
deltas=np.array(deltas)
print(f"within-month 3d-block delta: mean {deltas.mean():+.4f} std {deltas.std():.4f} n={len(deltas)}")

print("\n==== same analyses on DEMEANED caliber (sanity) ====")
s = dailyD.dropna(subset=["ic"]).copy()
s["ic_dm"] = s["ic"] - s.groupby("month")["ic"].transform("mean")
s["dom_dm"] = s["day_of_month"] - s.groupby("month")["day_of_month"].transform("mean")
res = stats.linregress(s["dom_dm"], s["ic_dm"])
print(f"ALL slope (demeaned caliber, month-FE): {res.slope:+.5f} p={res.pvalue:.3f} => 30d {res.slope*30:+.4f}")
for lab, sub in [("drift", s[s.drift]), ("non-drift", s[~s.drift])]:
    r2 = stats.linregress(sub["dom_dm"], sub["ic_dm"])
    print(f"  {lab}: slope {r2.slope:+.5f} p={r2.pvalue:.3f} => 30d {r2.slope*30:+.4f}")
