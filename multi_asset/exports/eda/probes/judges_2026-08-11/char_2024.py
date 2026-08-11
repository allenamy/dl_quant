import numpy as np, pandas as pd
f = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/funding_2024_series.csv"
d = pd.read_csv(f)
d["ts"] = pd.to_datetime(d["ts_ms"], unit="ms", utc=True)
d["day"] = d["ts"].dt.date; d["month"] = d["ts"].dt.strftime("%Y-%m")
g = d["gross_ret"].values; n = d["net_ret"].values
ann = np.sqrt(24*365)
print("HOURLY: n=%d  gross mean=%+.2e sd=%.2e Sh=%+.2f | net Sh=%+.2f" % (
    len(g), g.mean(), g.std(), ann*g.mean()/g.std(), ann*n.mean()/n.std()))
print("gross total sum=%+.4f  frac hours gross>0 = %.3f" % (g.sum(), (g>0).mean()))
# daily aggregation
dd = d.groupby("day")["gross_ret"].sum().sort_values()
print("\nDAILY gross: n_days=%d  frac days>0=%.3f  mean=%+.2e" % (len(dd), (dd>0).mean(), dd.mean()))
tot = dd.sum()
print("worst 5 days sum=%+.4f  (%.0f%% of total gross %.4f)" % (dd.head(5).sum(), 100*dd.head(5).sum()/tot if tot!=0 else 0, tot))
print("worst 10 days:", [ "%s %+.4f"%(str(k),v) for k,v in dd.head(10).items()])
# how much of the loss is from the worst days? cumulative loss concentration
neg = dd[dd<0].sort_values()
print("\ntotal NEGATIVE-day loss=%+.4f from %d down-days; worst 5 down-days = %.0f%% of loss" % (
    neg.sum(), len(neg), 100*neg.head(5).sum()/neg.sum()))
# monthly
mm = d.groupby("month")["gross_ret"].sum()
print("\nMONTHLY gross:")
for k,v in mm.items(): print("  %s %+.4f  %s" % (k, v, "+" if v>0 else "-"))
print("frac months gross>0 = %.2f (%d/%d)" % ((mm>0).mean(), (mm>0).sum(), len(mm)))
