"""0C — build + feasibility-check the KING-PRED panel (strictly OOS) for supplementary-factor
orthogonalization. Each ts uses ONLY its own test-fold's honest-ensemble composite. Reports coverage,
overlap, gaps. Saves exports/eda/king_pred_panel.npz {ts, king_pred (T,N), member, CL, YR, Yraw, day}.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
XK = TR + "wideA_lamorth0_xattn_5yr"


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


if __name__ == "__main__":
    pr = np.load(XK + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]
    yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    T, N = Yraw.shape
    King = np.full((T, N), np.nan, np.float32)
    fold_cover = {}
    overlap = 0
    for f in sorted(glob.glob(XK + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); te = z["te_rows"]
        Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
        C = comp_panel(z["scores"], member, CL, YR)
        m = np.isfinite(C)
        overlap += int((m & np.isfinite(King)).sum())     # rows already filled by another fold
        King[m] = C[m].astype(np.float32)
        fold_cover[Y] = dict(te_rows=int(len(te)), ts_with_pred=int(m.any(1).sum()),
                             date0=str(pd.Timestamp(ts[te.min()], unit="ms").date()),
                             date1=str(pd.Timestamp(ts[te.max()], unit="ms").date()))
    cov_rows = np.where(np.isfinite(King).any(1))[0]
    # coverage by year vs the panel's full span
    yrs_all = sorted(set(yr.tolist()))
    cov_by_year = {int(y): int(np.isfinite(King[yr == y]).any(1).sum()) for y in yrs_all}
    tot_by_year = {int(y): int((yr == y).sum() // 24) for y in yrs_all}   # ~days
    # cross-sectional density where covered
    dens = np.isfinite(King[cov_rows]).sum(1)
    np.savez(EDA + "king_pred_panel.npz", ts=ts, king_pred=King, member=member, CL=CL,
             YR=YR.astype(np.float32), Yraw=Yraw.astype(np.float32), day=day, year=yr)
    report = dict(
        panel_shape=[int(T), int(N)],
        span=[str(pd.Timestamp(ts[0], unit="ms").date()), str(pd.Timestamp(ts[-1], unit="ms").date())],
        fold_coverage=fold_cover, cross_fold_overlap_cells=overlap,
        covered_ts_rows=int(len(cov_rows)),
        covered_date_range=[str(pd.Timestamp(ts[cov_rows.min()], unit="ms").date()),
                            str(pd.Timestamp(ts[cov_rows.max()], unit="ms").date())],
        coverage_by_year_ts=cov_by_year,
        median_xsec_density=int(np.median(dens)),
        gap_note="2021 has NO OOS king-pred (never a test year — only trains 2022). king-pred panel = OOS test span 2022→2026H1.")
    json.dump(report, open(EDA + "king_pred_panel_report.json", "w"), indent=2, default=str)
    print(json.dumps(report, indent=2))
    print("SAVED king_pred_panel.npz + report")
