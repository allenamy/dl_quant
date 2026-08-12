"""Robustness for AUDIT 2: is the pre-settlement funding-unwind structure (settle pre-IC -0.0102 vs
placebo -0.0027 on residual YR1) statistically real? per-year consistency + day-block bootstrap CI on
settle-minus-placebo. Decides OPEN (robust structure) vs CLOSE (noise). Appends to horizon_gap_audit.json."""
import json, numpy as np, pandas as pd
from scipy.stats import rankdata
M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
z = np.load(f"{M}/exports/wide_dl_full.npz", allow_pickle=True)
CH = z["CH"]; YR1 = z["YR1"].astype(np.float64); MEM = z["MEMBER110"].astype(bool)
ts = z["ts"].astype(np.int64)
dt = pd.to_datetime(ts, unit="ms", utc=True); hour = dt.hour.to_numpy(); yr = dt.year.to_numpy()
day = (ts // 86400000).astype(np.int64)
fund = np.where(MEM, CH[:, :, 0].astype(np.float64), np.nan)
T = CH.shape[0]


def pre_ic_anchors(anchor_rows):
    """per-anchor rank-IC(funding_t0, sum residual ret over pre-window [t0-4,t0])."""
    out_ic, out_day, out_yr = [], [], []
    for t0 in anchor_rows:
        b = np.where(MEM[t0] & np.isfinite(fund[t0]))[0]
        if b.size < 10:
            continue
        pre = np.nansum([YR1[t0 + k, b] for k in (-4, -3, -2, -1) if 0 <= t0 + k], axis=0)
        f = fund[t0, b]
        if np.size(pre) == b.size and np.std(f) > 1e-12 and np.std(pre) > 1e-12:
            out_ic.append(np.corrcoef(rankdata(f), rankdata(pre))[0, 1]); out_day.append(int(day[t0])); out_yr.append(int(yr[t0]))
    return np.array(out_ic), np.array(out_day), np.array(out_yr)


def boot(ic, days, n=3000, seed=0):
    rng = np.random.default_rng(seed); ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    bs = np.array([ic[np.concatenate([d2[u] for u in rng.choice(ud, len(ud), True)])].mean() for _ in range(n)])
    return round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)


s_ic, s_day, s_yr = pre_ic_anchors(np.where(hour % 8 == 0)[0])
p_ic, p_day, p_yr = pre_ic_anchors(np.where(hour % 8 == 4)[0])
years = [2022, 2023, 2024, 2025, 2026]
by_year = {y: dict(settle=round(float(s_ic[s_yr == y].mean()), 4), placebo=round(float(p_ic[p_yr == y].mean()), 4),
                   diff=round(float(s_ic[s_yr == y].mean() - p_ic[p_yr == y].mean()), 4)) for y in years}
# pooled + bootstrap CIs
res = dict(settle_pre_ic=round(float(s_ic.mean()), 4), settle_ci=boot(s_ic, s_day),
           placebo_pre_ic=round(float(p_ic.mean()), 4), placebo_ci=boot(p_ic, p_day),
           diff_pooled=round(float(s_ic.mean() - p_ic.mean()), 4), by_year=by_year,
           n_settle=len(s_ic), n_placebo=len(p_ic),
           sign_consistent_diff=bool(all(by_year[y]["diff"] < 0 for y in years)))
print(json.dumps(res, indent=1), flush=True)

# append to the audit json
p = f"{M}/exports/eda/horizon_gap_audit.json"
d = json.load(open(p)); d["audit2_8h_settlement"]["robustness_pre_unwind"] = res
json.dump(d, open(p, "w"), indent=1, default=str)
print("APPENDED robustness", flush=True)
