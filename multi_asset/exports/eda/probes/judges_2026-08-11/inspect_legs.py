import numpy as np, pandas as pd, glob
E = "multi_asset/exports/eda/"


def unit_of(ts):
    t = int(ts[0])
    return "ns" if t > 1e17 else ("us" if t > 1e14 else ("ms" if t > 1e11 else "s"))


def dt(ts):
    u = unit_of(ts)
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit=u, utc=True)


pr = np.load(E + "panel_ref_fund_ema_h3600.npz", allow_pickle=True)
ts = pr["ts"].astype(np.int64)
u = unit_of(ts)
tf = dt(ts)
div = {"ns": 6e10, "us": 6e7, "ms": 6e4, "s": 60}[u]
print("funding unit", u, "ts", tf[0].date(), "->", tf[-1].date(), "n", len(ts),
      "gap_min", int(np.median(np.diff(ts)) / div))
syms = [str(s) for s in pr["symbols"]]
print("funding N", len(syms), syms)
print("Y shape", pr["Y"].shape, "CL rows", int(pr["CL"].any(1).sum()),
      "member/hr med", int(np.median(pr["CL"].sum(1))))
for f in sorted(glob.glob(E + "fold_*_preds_fund_ema_h3600.npz")):
    zz = np.load(f)
    print(" ", f.split("/")[-1], "keys", list(zz.keys()), "pred", zz["pred"].shape,
          "te_rows", len(zz["te_rows"]))
