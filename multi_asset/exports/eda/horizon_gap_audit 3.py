"""0C horizon-gap audit — 0.5-24h mid-freq band, the two untested cells: sub-4h (0.5-2h) and
8h funding-settlement clock. Cheap CPU, uses existing products (king_pred + wide_dl_full).
Writes exports/eda/horizon_gap_audit.json.

AUDIT 1 (sub-4h coverage): is king (4h) already the strongest 1h signal? king_pred vs Y1 rank-IC
  per year, head-to-head vs a dedicated 1h Ridge-on-32ch walk-forward baseline. + turnover econ.
AUDIT 2 (8h funding-settlement event study): event-time return structure around 00/08/16 UTC
  settlement, stratified by funding, on raw Y1 AND funding-residualized YR1, vs a placebo clock
  (hour%8==4). + intraday session scan.
"""
import json, numpy as np, pandas as pd
from scipy.stats import rankdata

M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
z = np.load(f"{M}/exports/wide_dl_full.npz", allow_pickle=True)
CH = z["CH"].astype(np.float32)            # (T,N,32)
Y1 = z["Y1"].astype(np.float64); YR1 = z["YR1"].astype(np.float64)
Y4 = z["Y4"].astype(np.float64)
CL1 = z["CL1"].astype(bool); CL4 = z["CL4"].astype(bool); MEM = z["MEMBER110"].astype(bool)
ts = z["ts"].astype(np.int64); chn = list(z["ch_names"])
king = np.load(f"{M}/exports/eda/king_pred_panel.npz", allow_pickle=True)["king_pred"].astype(np.float64)
T, N, C = CH.shape
dt = pd.to_datetime(ts, unit="ms", utc=True)
year = dt.year.to_numpy(); hour = dt.hour.to_numpy()
years = [2022, 2023, 2024, 2025, 2026]
MB = 5
OUT = {"title": "horizon gap audit (sub-4h + 8h settlement clock)", "created": "2026-07-19", "auditor": "0C"}


def xsec_ic(pred, tgt, mask):
    """mean per-ts cross-sectional rank-IC over rows where mask & finite(pred,tgt)."""
    ics = []
    for t in np.where(mask.any(1))[0]:
        b = np.where(mask[t] & np.isfinite(pred[t]) & np.isfinite(tgt[t]))[0]
        if b.size >= MB and np.std(pred[t, b]) > 1e-12 and np.std(tgt[t, b]) > 1e-12:
            ics.append(np.corrcoef(rankdata(pred[t, b]), rankdata(tgt[t, b]))[0, 1])
    return (np.array(ics)), (float(np.mean(ics)) if ics else np.nan)


def ic_by_year(pred, tgt, gridmask):
    out = {}
    for y in years:
        m = gridmask & (year == y)[:, None]
        _, v = xsec_ic(pred, tgt, m)
        out[y] = round(v, 4) if np.isfinite(v) else None
    return out


# ============================ AUDIT 1: sub-4h coverage ============================
print("AUDIT 1: sub-4h coverage ...", flush=True)
kingmask4 = CL4 & MEM & np.isfinite(king)   # where king exists (its 4h anchors)
A1 = {}
A1["king@Y4_native_CL4"] = ic_by_year(king, Y4, kingmask4)      # native 4h (reference)
A1["king@Y1_CL4"] = ic_by_year(king, Y1, kingmask4)            # does 4h-king predict next 1h?
A1["king@YR1_CL4"] = ic_by_year(king, YR1, kingmask4)          # residual 1h

# dedicated 1h Ridge-on-32ch, expanding walk-forward. per-ts xsec-standardize features + demean y.
# standardize CH per-ts cross-sectionally (vectorized), overwrite to save RAM.
print("  standardizing CH per-ts xsec ...", flush=True)
CHs = CH.astype(np.float32).copy()
valid_cell = MEM & CL1 & np.isfinite(Y1) & np.isfinite(CH).all(2)
mf = MEM.astype(np.float32)
for c in range(C):
    x = CHs[:, :, c]
    x = np.where(MEM, x, np.nan)
    mu = np.nanmean(x, axis=1, keepdims=True); sd = np.nanstd(x, axis=1, keepdims=True)
    CHs[:, :, c] = np.where(np.isfinite(x) & (sd > 1e-9), (x - mu) / (sd + 1e-9), 0.0).astype(np.float32)
Y1d = np.where(MEM, Y1, np.nan)
Y1d = Y1d - np.nanmean(Y1d, axis=1, keepdims=True)   # per-ts demean target

ALPHA = 20.0
ridge_pred = np.full((T, N), np.nan)
for ty in years:
    tr = valid_cell & (year < ty)[:, None]
    tri, trj = np.where(tr)
    if tri.size < 5000:
        continue
    X = CHs[tri, trj, :].astype(np.float64); yv = Y1d[tri, trj]
    ok = np.isfinite(yv)
    X, yv = X[ok], yv[ok]
    XtX = X.T @ X + ALPHA * np.eye(C); beta = np.linalg.solve(XtX, X.T @ yv)
    te_rows = np.where((year == ty))[0]
    for t in te_rows:
        b = np.where(MEM[t] & np.isfinite(CHs[t]).all(1))[0]
        if b.size:
            ridge_pred[t, b] = CHs[t, b, :].astype(np.float64) @ beta
A1["ridge1h@Y1_CL1"] = ic_by_year(ridge_pred, Y1, CL1 & MEM)      # dedicated 1h, full grid (opportunity)
A1["ridge1h@Y1_CL4_headtohead"] = ic_by_year(ridge_pred, Y1, kingmask4)  # same anchors as king
A1["ridge1h@YR1_CL1"] = ic_by_year(ridge_pred, YR1, CL1 & MEM)


def poolmean(d):
    v = [x for x in d.values() if x is not None]
    return round(float(np.mean(v)), 4) if v else None


A1["_pooled"] = {k: poolmean(v) for k, v in A1.items()}
OUT["audit1_sub4h"] = A1
print("  A1 pooled:", A1["_pooled"], flush=True)

# ============================ AUDIT 2: 8h settlement clock ============================
print("AUDIT 2: 8h settlement event study ...", flush=True)
fund = np.where(MEM, CH[:, :, 0].astype(np.float64), np.nan)   # funding_ema, signed
settle_rows = np.where((hour % 8 == 0))[0]
placebo_rows = np.where((hour % 8 == 4))[0]


def event_study(anchor_rows, tgt, label):
    """event-time avg return curve grouped by funding tercile, + rank-IC(funding, windowed ret)."""
    ks = list(range(-4, 5))
    curves = {"hi": {k: [] for k in ks}, "lo": {k: [] for k in ks}, "all": {k: [] for k in ks}}
    ic_pre, ic_post = [], []     # rank-IC(funding_t0, sum ret over [t0-4,t0]) and [t0,t0+4]
    for t0 in anchor_rows:
        b = np.where(MEM[t0] & np.isfinite(fund[t0]))[0]
        if b.size < 10:
            continue
        f = fund[t0, b]; q = rankdata(f) / len(f)
        hi = b[q >= 0.7]; lo = b[q <= 0.3]
        for k in ks:
            tk = t0 + k
            if 0 <= tk < T:
                curves["all"][k].append(float(np.nanmean(tgt[tk, b])))
                if hi.size: curves["hi"][k].append(float(np.nanmean(tgt[tk, hi])))
                if lo.size: curves["lo"][k].append(float(np.nanmean(tgt[tk, lo])))
        # windowed cumulative returns
        pre = np.nansum([tgt[t0 + k, b] for k in (-4, -3, -2, -1) if 0 <= t0 + k], axis=0)
        post = np.nansum([tgt[t0 + k, b] for k in (0, 1, 2, 3) if t0 + k < T], axis=0)
        if np.std(f) > 1e-12:
            if np.size(pre) == b.size and np.std(pre) > 1e-12:
                ic_pre.append(np.corrcoef(rankdata(f), rankdata(pre))[0, 1])
            if np.size(post) == b.size and np.std(post) > 1e-12:
                ic_post.append(np.corrcoef(rankdata(f), rankdata(post))[0, 1])
    curve = lambda g: {k: round(float(np.nanmean(v) * 1e4), 3) if v else None for k, v in curves[g].items()}  # bps
    return dict(n_anchors=int(len(anchor_rows)), curve_hi_bps=curve("hi"), curve_lo_bps=curve("lo"),
                ic_funding_vs_preRet=round(float(np.nanmean(ic_pre)), 4), n_pre=len(ic_pre),
                ic_funding_vs_postRet=round(float(np.nanmean(ic_post)), 4), n_post=len(ic_post))


A2 = {}
A2["settle_rawY1"] = event_study(settle_rows, Y1, "settle_raw")
A2["placebo_rawY1"] = event_study(placebo_rows, Y1, "placebo_raw")
A2["settle_residYR1"] = event_study(settle_rows, YR1, "settle_resid")
A2["placebo_residYR1"] = event_study(placebo_rows, YR1, "placebo_resid")

# intraday session scan: cross-sectional dispersion + funding-IC by UTC session bucket
sess = {"asia_0_8": (hour >= 0) & (hour < 8), "eu_8_16": (hour >= 8) & (hour < 16), "us_16_24": (hour >= 16)}
sess_scan = {}
for name, hm in sess.items():
    m = MEM & CL1 & hm[:, None]
    _, ic_f = xsec_ic(fund, YR1, m)
    disp = []
    for t in np.where(m.any(1))[0][::6]:
        b = np.where(m[t] & np.isfinite(Y1[t]))[0]
        if b.size >= MB: disp.append(float(np.std(Y1[t, b])))
    sess_scan[name] = dict(funding_ic_vs_YR1=round(ic_f, 4) if np.isfinite(ic_f) else None,
                           xsec_ret_disp_bps=round(float(np.nanmean(disp) * 1e4), 2) if disp else None)
A2["intraday_session_scan"] = sess_scan
OUT["audit2_8h_settlement"] = A2
print("  A2 settle ic_pre/post:", A2["settle_rawY1"]["ic_funding_vs_preRet"], A2["settle_rawY1"]["ic_funding_vs_postRet"],
      "| placebo:", A2["placebo_rawY1"]["ic_funding_vs_preRet"], A2["placebo_rawY1"]["ic_funding_vs_postRet"], flush=True)
print("  A2 resid settle ic_pre/post:", A2["settle_residYR1"]["ic_funding_vs_preRet"], A2["settle_residYR1"]["ic_funding_vs_postRet"], flush=True)

json.dump(OUT, open(f"{M}/exports/eda/horizon_gap_audit.json", "w"), indent=1, default=str)
print("SAVED horizon_gap_audit.json", flush=True)
