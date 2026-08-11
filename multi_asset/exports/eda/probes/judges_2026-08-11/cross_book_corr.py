"""Cross-book correlation: Book-1 (funding+M0 blend, 14 mega-cap) vs Book-2 (wide SIZE/combined) returns,
aligned by hour. The diversification claim (expected ~0)."""
import sys, numpy as np
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"; sys.path.insert(0, MA)
from multi_asset.eval.portfolio_scorecard import load_panel, blend, book_stats

F = load_panel("fund_ema_h3600", MA+"/multi_asset/exports/train")
Y, CL, ts, day = F["Y"], F["CL"], F["ts"].astype(np.int64), F["day"].astype(np.int64)
funding = F["pred"]; M0 = load_panel("fund_resid_h3600", MA+"/multi_asset/exports/train")["pred"]
comb = blend([funding, M0], Y, CL)

# Book-1 return series (blend, operating alpha, net@2bps)
st = book_stats(comb, Y, CL, ts, day, 3600, cost_bps=2.0)
b1_ts_ns, b1_net = st["ret_series"]
b1_ts_ns = b1_ts_ns.astype(np.int64)
b1_hour = (b1_ts_ns // 3_600_000_000_000)                    # ns -> absolute hour bucket

# Book-2 return series
z = np.load(MA+"/multi_asset/exports/eda/book2_returns.npz", allow_pickle=True)
print("book2 keys:", z.files)
b2_ts = z["ts"].astype(np.int64); _u = 3_600_000_000_000 if b2_ts[0]>1e17 else (3_600_000_000 if b2_ts[0]>1e14 else (3_600_000 if b2_ts[0]>1e11 else 3600)); b2_hour = b2_ts // _u; print("book2 ts[0]",b2_ts[0],"hour-unit",_u)
def series(name): return dict(zip(b2_hour.tolist(), z[name].tolist()))

# align Book-1 (aggregate any multiple b1 rows per hour by sum) to Book-2 hourly
from collections import defaultdict
b1h = defaultdict(float)
for h, r in zip(b1_hour.tolist(), b1_net.tolist()):
    b1h[h] += r
for col in ["combined_net", "size_net"]:
    b2h = series(col)
    common = sorted(set(b1h) & set(b2h))
    if len(common) < 30:
        print(f"{col}: too few common hours ({len(common)})"); continue
    a = np.array([b1h[h] for h in common]); b = np.array([b2h[h] for h in common])
    r = float(np.corrcoef(a, b)[0, 1])
    print(f"CROSS-BOOK CORR  Book1(blend) vs Book2({col}) = {r:+.3f}  (n_common_hours={len(common)})")
print("DONE")
