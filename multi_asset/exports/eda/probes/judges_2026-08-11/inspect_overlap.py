import numpy as np, pandas as pd, glob
E = "multi_asset/exports/eda/"
TR = "multi_asset/exports/train/"


def unit_of(ts):
    t = int(ts[0]); return "ns" if t > 1e17 else ("us" if t > 1e14 else ("ms" if t > 1e11 else "s"))


def days_of(ts):
    u = unit_of(ts)
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit=u, utc=True).floor("D")


# funding test days
pr = np.load(E + "panel_ref_fund_ema_h3600.npz", allow_pickle=True)
fts = pr["ts"].astype(np.int64)
fdays_all = days_of(fts)
fte = set()
for f in sorted(glob.glob(E + "fold_*_preds_fund_ema_h3600.npz")):
    z = np.load(f)
    fte |= set(fdays_all[z["te_rows"]].tolist())
fte = pd.DatetimeIndex(sorted(fte))
print("FUNDING test days:", fte.min().date(), "->", fte.max().date(), "n_days", len(fte))

# book2 size days (nonzero)
b = np.load(E + "book2_returns.npz", allow_pickle=True)
bts = b["ts"].astype(np.int64); bdays = days_of(bts)
snz = np.abs(b["size_net"].astype(float)) > 0
sdays = pd.DatetimeIndex(sorted(set(bdays[snz].tolist())))
print("SIZE days:", sdays.min().date(), "->", sdays.max().date(), "n_days", len(sdays))

# QIM 5yr test days (fold_2=2024, fold_3=2025 cover overlap)
prq = np.load(TR + "wideA_qim_multiyear/panel_ref.npz", allow_pickle=True)
qts = prq["ts"].astype(np.int64); qdays_all = days_of(qts)
qte = set()
for f in sorted(glob.glob(TR + "wideA_qim_multiyear/fold_*_head_scores.npz")):
    z = np.load(f); qte |= set(qdays_all[z["te_rows"]].tolist())
qte = pd.DatetimeIndex(sorted(qte))
print("QIM test days:", qte.min().date(), "->", qte.max().date(), "n_days", len(qte))

# 3-way day intersection
inter = fte.intersection(sdays).intersection(qte)
print("3-WAY overlap days:", (inter.min().date() if len(inter) else None), "->",
      (inter.max().date() if len(inter) else None), "n_days", len(inter))

# xattn vs QIM panel alignment (for pre-check)
import hashlib
def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]
print("QIM 5yr panel md5", md5(TR + "wideA_qim_multiyear/panel_ref.npz"))
print("xattn 5yr panel md5", md5(TR + "wideA_multiyear_xattn/panel_ref.npz"))
print("xattn 5yr folds:", [f.split("/")[-1] for f in sorted(glob.glob(TR + "wideA_multiyear_xattn/fold_*_head_scores.npz"))])
