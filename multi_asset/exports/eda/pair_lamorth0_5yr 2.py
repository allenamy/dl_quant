"""0C — per-year PAIRING verdict: lamorth0_5yr (K=6, lam_orth=0, 5-year calendar walk-forward) vs
QIM 5yr. Closes the verdict's 'mechanism unconfirmed at 5yr' flag. Recomputes honest ensemble resid
IC (z-mean of the 6 heads) per test year, pairs vs QIM, dynamic/static split. CPU-only.
Writes multi_asset/exports/eda/lamorth0_5yr_pairing.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
LAM = TR + "wideA_lamorth0_5yr"
QIM = TR + "wideA_qim_multiyear"
RNG = np.random.default_rng(0)
QIM_YEARLY = {2022: 0.0443, 2023: 0.0640, 2024: 0.0697, 2025: 0.0807, 2026: 0.0774}  # honest ensemble


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def load_panel(d):
    z = np.load(d + "/panel_ref.npz", allow_pickle=True)
    return dict(ts=z["ts"].astype(np.int64), member=z["member"].astype(bool), CL=z["CL"].astype(bool),
                YR=z["YR"].astype(np.float64), Yraw=z["Yraw"].astype(np.float64))


def comp_panel(scores, panel):
    T, N, K = scores.shape
    C = np.full((T, N), np.nan)
    member, CL, YR = panel["member"], panel["CL"], panel["YR"]
    rows = np.where((member & CL & np.isfinite(YR)).any(1))[0]
    for t in rows:
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


def ic_series(C, Ytgt, panel):
    member, CL = panel["member"], panel["CL"]
    ics = []
    for t in np.where(np.isfinite(C).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(Ytgt[t]) & np.isfinite(C[t]))[0]
        if base.size < 5:
            continue
        ic = np.corrcoef(rankdata(C[t, base]), rankdata(Ytgt[t, base]))[0, 1]
        if np.isfinite(ic):
            ics.append(ic)
    return np.array(ics)


def dyn_static(C, panel, nshuf=25):
    member, CL, YR = panel["member"], panel["CL"], panel["YR"]
    rows = np.where(np.isfinite(C).any(1))[0]
    idxs, yrank = [], []
    for t in rows:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(C[t]))[0]
        idxs.append(base if base.size >= 5 else None)
        yrank.append(rankdata(YR[t, base]) if base.size >= 5 else None)
    valid = [i for i in range(len(rows)) if idxs[i] is not None]
    tot = np.nanmean([np.corrcoef(rankdata(C[rows[i], idxs[i]]), yrank[i])[0, 1] for i in valid])
    Csub = C[rows]; shuf = []
    for _ in range(nshuf):
        Cs = Csub.copy()
        for a in range(C.shape[1]):
            fin = np.where(np.isfinite(Cs[:, a]))[0]
            if fin.size > 1:
                Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
        rep = []
        for i in valid:
            b = idxs[i]; v = np.isfinite(Cs[i, b])
            if v.sum() >= 5:
                rep.append(np.corrcoef(rankdata(Cs[i, b][v]), rankdata(YR[rows[i], b][v]))[0, 1])
        shuf.append(np.nanmean(rep))
    stat = float(np.nanmean(shuf))
    return float(tot), stat, float(tot - stat)


if __name__ == "__main__":
    print("panel md5: lamorth0_5yr", md5(LAM + "/panel_ref.npz"), "| QIM", md5(QIM + "/panel_ref.npz"), flush=True)
    panel = load_panel(LAM)
    ts_year = pd.to_datetime(panel["ts"], unit="ms", utc=True).year.to_numpy()
    rows = []
    for f in sorted(glob.glob(LAM + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); sc = z["scores"]; te = z["te_rows"]
        yrs = ts_year[te]; Y = int(np.bincount(yrs - yrs.min()).argmax() + yrs.min())
        C = comp_panel(sc, panel)
        keep = np.zeros(panel["Yraw"].shape[0], bool); keep[te] = True; C[~keep] = np.nan
        ens = ic_series(C, panel["YR"], panel); raw = ic_series(C, panel["Yraw"], panel)
        tot, stat, dyn = dyn_static(C, panel)
        qim = QIM_YEARLY.get(Y, float("nan"))
        rows.append(dict(year=Y, K=sc.shape[2], lamorth0_ens_ic=round(float(ens.mean()), 4),
                         lamorth0_ic_ir=round(float(ens.mean() / ens.std() * np.sqrt(len(ens))), 2),
                         lamorth0_raw_ic=round(float(raw.mean()), 4),
                         qim_ens_ic=qim, delta=round(float(ens.mean()) - qim, 4),
                         dyn_share=round(dyn / tot, 3) if tot else None, dynamic=round(dyn, 4)))
        print(f"[{Y}] lamorth0_5yr ens={ens.mean():+.4f} (IR {rows[-1]['lamorth0_ic_ir']}) vs QIM {qim:+.4f} "
              f"delta={rows[-1]['delta']:+.4f} | dyn share {rows[-1]['dyn_share']}", flush=True)
    lam_mean = float(np.mean([r["lamorth0_ens_ic"] for r in rows]))
    qim_mean = float(np.mean([QIM_YEARLY[r["year"]] for r in rows]))
    verdict = dict(
        title="lamorth0_5yr vs QIM per-year pairing (mechanism confirm at 5yr)", created="2026-07-12",
        auditor="0C", per_year=rows, lamorth0_5yr_mean=round(lam_mean, 4), qim_5yr_mean=round(qim_mean, 4),
        mean_delta=round(lam_mean - qim_mean, 4),
        conclusion=("CONFIRMS mechanism at 5yr scale IF |per-year deltas| within seed noise (~0.01) and "
                    "means match: lam_orth=0 K-head reproduces QIM's 5yr profile -> the ~2x edge is the "
                    "orthogonality-penalty removal, pinball head neutral. (Fill after run.)"))
    json.dump(verdict, open(EDA + "lamorth0_5yr_pairing.json", "w"), indent=2, default=str)
    print(f"\nMEAN: lamorth0_5yr {lam_mean:+.4f} vs QIM {qim_mean:+.4f} (delta {lam_mean-qim_mean:+.4f})", flush=True)
    print("SAVED " + EDA + "lamorth0_5yr_pairing.json", flush=True)
