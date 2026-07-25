"""0C — three-leg book assembly analysis (CPU-only). Inter-leg daily-return correlation,
portfolio net Sharpe, DL-weight sensitivity, xattn overlay pre-check.
Writes multi_asset/exports/eda/book_assembly_raw.json.

Legs (aligned to DAILY net return; different native rebalance freq/universe/cost -- documented):
  (a) FUNDING  : 14 mega-caps, 1h rebalance, rank-L/S net@2bps, from fold_*_preds_fund_ema_h3600.
  (b) DL_QIM   : 110 wide, 4h rebalance, rank-L/S net@5bps, from QIM 5yr fold_2(2024)+fold_3(2025).
  (c) SIZE     : 110 wide, 1h rebalance, existing book2_returns size_net (tiered cost).
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

E = "multi_asset/exports/eda/"
TR = "multi_asset/exports/train/"
ANN_D = np.sqrt(365.0)


def unit_of(ts):
    t = int(ts[0]); return "ns" if t > 1e17 else ("us" if t > 1e14 else ("ms" if t > 1e11 else "s"))


def days_idx(ts):
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit=unit_of(ts), utc=True).floor("D")


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean()
    s = np.abs(r).sum(); return r / s * 2.0 if s > 0 else r


# ---------------- leg (a) FUNDING ----------------
def leg_funding(cost_bps=2.0):
    pr = np.load(E + "panel_ref_fund_ema_h3600.npz", allow_pickle=True)
    ts = pr["ts"].astype(np.int64); Y = pr["Y"].astype(np.float64); CL = pr["CL"].astype(bool)
    T, N = Y.shape
    pred = np.full((T, N), np.nan)
    for f in sorted(glob.glob(E + "fold_*_preds_fund_ema_h3600.npz")):
        z = np.load(f); pred[z["te_rows"]] = z["pred"][z["te_rows"]]
    rows = np.sort(np.where(np.isfinite(pred).any(1) & CL.any(1))[0])
    dser = {}; prevw = np.zeros(N); dd = days_idx(ts)
    print("  funding Y scale: std", np.nanstd(Y[CL]), "median|Y|", np.nanmedian(np.abs(Y[CL])))
    for t in rows:
        v = np.where(CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t]))[0]
        if v.size < 5:
            continue
        w = np.zeros(N); w[v] = rank_weights(pred[t, v])
        gross = float((w * np.nan_to_num(Y[t])).sum())
        turn = np.abs(w - prevw).sum()
        net = gross - turn * (cost_bps * 1e-4)
        dser[dd[t]] = dser.get(dd[t], 0.0) + net
        prevw = w
    s = pd.Series(dser).sort_index(); s.name = "funding"
    return s


# ---------------- leg (b) DL_QIM ----------------
def comp_row(sc_t, base):
    K = sc_t.shape[1]; comp = np.zeros(base.size); nk = 0
    for k in range(K):
        col = sc_t[base, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return comp / nk if nk else None


def leg_dl(cost_bps=5.0):
    pr = np.load(TR + "wideA_qim_multiyear/panel_ref.npz", allow_pickle=True)
    ts = pr["ts"].astype(np.int64); member = pr["member"].astype(bool)
    CL = pr["CL"].astype(bool); Yraw = pr["Yraw"].astype(np.float64)
    T, N = Yraw.shape; dd = days_idx(ts)
    P = np.full((T, N), np.nan)
    for f in sorted(glob.glob(TR + "wideA_qim_multiyear/fold_*_head_scores.npz")):
        z = np.load(f); sc = z["scores"]
        for t in z["te_rows"]:
            base = np.where(member[t] & CL[t] & np.isfinite(Yraw[t]))[0]
            if base.size >= 10:
                c = comp_row(sc[t], base)
                if c is not None:
                    P[t, base] = c
    rows = np.sort(np.where(np.isfinite(P).any(1))[0])
    dser = {}; prevw = np.zeros(N)
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(N); w[v] = rank_weights(P[t, v])
        gross = float((w * np.nan_to_num(Yraw[t])).sum())
        turn = np.abs(w - prevw).sum()
        net = gross - turn * (cost_bps * 1e-4)
        dser[dd[t]] = dser.get(dd[t], 0.0) + net
        prevw = w
    s = pd.Series(dser).sort_index(); s.name = "dl_qim"
    return s


# ---------------- leg (c) SIZE ----------------
def leg_size():
    b = np.load(E + "book2_returns.npz", allow_pickle=True)
    ts = b["ts"].astype(np.int64); v = b["size_net"].astype(float); dd = days_idx(ts)
    m = np.abs(v) > 0
    s = pd.Series(v[m], index=dd[m]).groupby(level=0).sum(); s.name = "size"
    return s


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * ANN_D) if x.std() > 0 else np.nan


def worst_month(s):
    m = s.groupby(s.index.to_period("M")).sum()
    return float(m.min()), str(m.idxmin())


def pair_corr(a, b):
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(j) < 10:
        return None
    return dict(n_days=int(len(j)), corr=round(float(j.iloc[:, 0].corr(j.iloc[:, 1])), 3),
                start=str(j.index.min().date()), end=str(j.index.max().date()))


def rolling_corr(a, b, win=60):
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(j) < win + 10:
        return None
    rc = j.iloc[:, 0].rolling(win).corr(j.iloc[:, 1]).dropna()
    return dict(mean=round(float(rc.mean()), 3), std=round(float(rc.std()), 3),
               min=round(float(rc.min()), 3), max=round(float(rc.max()), 3), win=win)


# ---------------- xattn overlay pre-check ----------------
def xattn_precheck():
    prq = np.load(TR + "wideA_qim_multiyear/panel_ref.npz", allow_pickle=True)
    member = prq["member"].astype(bool); CL = prq["CL"].astype(bool)
    Yraw = prq["Yraw"].astype(np.float64)
    out = []
    qf = sorted(glob.glob(TR + "wideA_qim_multiyear/fold_*_head_scores.npz"))
    xf = sorted(glob.glob(TR + "wideA_multiyear_xattn/fold_*_head_scores.npz"))
    yr_of = pd.to_datetime(prq["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    for qff, xff in zip(qf, xf):
        zq = np.load(qff); zx = np.load(xff)
        te = zq["te_rows"]
        scq = zq["scores"]; scx = zx["scores"]        # hoist: avoid per-t npz re-decompression
        Y = int(np.bincount(yr_of[te] - yr_of[te].min()).argmax() + yr_of[te].min())
        cors = []
        for t in te:
            base = np.where(member[t] & CL[t] & np.isfinite(Yraw[t]))[0]
            if base.size < 10:
                continue
            cq = comp_row(scq[t], base); cx = comp_row(scx[t], base)
            if cq is None or cx is None:
                continue
            c = np.corrcoef(rankdata(cq), rankdata(cx))[0, 1]
            if np.isfinite(c):
                cors.append(c)
        out.append(dict(year=Y, mean_xsec_rankcorr=round(float(np.mean(cors)), 3), n_ts=len(cors)))
    return out


if __name__ == "__main__":
    print("building legs...", flush=True)
    a = leg_funding(); b = leg_dl(); c = leg_size()
    print(f"  funding: {len(a)}d {a.index.min().date()}..{a.index.max().date()} Sharpe {sharpe(a):.2f}", flush=True)
    print(f"  dl_qim : {len(b)}d {b.index.min().date()}..{b.index.max().date()} Sharpe {sharpe(b):.2f}", flush=True)
    print(f"  size   : {len(c)}d {c.index.min().date()}..{c.index.max().date()} Sharpe {sharpe(c):.2f}", flush=True)

    # pairwise corr (max common window) + rolling
    pairs = dict(funding_dl=pair_corr(a, b), funding_size=pair_corr(a, c), dl_size=pair_corr(b, c))
    roll = dict(dl_size=rolling_corr(b, c, 60), funding_dl=rolling_corr(a, b, 30),
                funding_size=rolling_corr(a, c, 30))
    print("PAIR CORR:", json.dumps(pairs), flush=True)

    # 3-way joint window
    J = pd.concat([a, b, c], axis=1, join="inner").dropna()
    J.columns = ["funding", "dl", "size"]
    print(f"JOINT window {J.index.min().date()}..{J.index.max().date()} n_days {len(J)}", flush=True)
    legsharpe = {k: round(sharpe(J[k]), 2) for k in J.columns}
    legwm = {k: worst_month(J[k]) for k in J.columns}
    vol = {k: float(J[k].std()) for k in J.columns}

    def port(weights):
        w = np.array([weights[k] for k in J.columns])
        p = (J.values * w).sum(1)
        p = pd.Series(p, index=J.index)
        wm, wmm = worst_month(p)
        return dict(weights={k: round(weights[k], 3) for k in J.columns}, sharpe=round(sharpe(p), 2),
                    worst_month=round(wm, 5), worst_month_id=wmm,
                    ann_ret_bps=round(float(p.mean() * 365 * 1e4), 1))

    ew = {k: 1 / 3 for k in J.columns}
    ivw = {k: (1 / vol[k]) for k in J.columns}; sv = sum(ivw.values()); ivw = {k: ivw[k] / sv for k in ivw}
    portfolios = dict(equal_weight=port(ew), inverse_vol=port(ivw))

    # DL-weight sensitivity: DL in {0.2,0.4,0.6}, rest split funding/size by inverse-vol
    sens = {}
    for wdl in (0.2, 0.4, 0.6):
        rest = 1 - wdl
        iv_fs = {k: 1 / vol[k] for k in ["funding", "size"]}; s2 = sum(iv_fs.values())
        wts = {"dl": wdl, "funding": rest * iv_fs["funding"] / s2, "size": rest * iv_fs["size"] / s2}
        sens[str(wdl)] = port(wts)

    xchk = xattn_precheck()
    print("XATTN precheck:", json.dumps(xchk), flush=True)

    result = dict(
        title="Three-leg book assembly (0C)", created="2026-07-12", auditor="0C",
        alignment_note=("legs aligned to DAILY net return (sum of intra-day per-rebalance net). Native "
                        "caliber differs: funding=14 mega-cap 1h net@2bps; dl_qim=110 wide 4h net@5bps "
                        "(QIM 5yr fold2/3); size=110 wide 1h book2 tiered-cost. Correlation is scale-invariant; "
                        "portfolio uses inverse-vol so scale cancels. 3-way JOINT window limited to funding OOS."),
        leg_single=dict(sharpe_full_window=dict(funding=round(sharpe(a), 2), dl_qim=round(sharpe(b), 2), size=round(sharpe(c), 2)),
                        window=dict(funding=[str(a.index.min().date()), str(a.index.max().date())],
                                    dl_qim=[str(b.index.min().date()), str(b.index.max().date())],
                                    size=[str(c.index.min().date()), str(c.index.max().date())])),
        pairwise_corr=pairs, rolling_corr=roll,
        joint_window=dict(start=str(J.index.min().date()), end=str(J.index.max().date()), n_days=int(len(J)),
                          leg_sharpe=legsharpe, leg_worst_month=legwm),
        portfolios=portfolios, dl_weight_sensitivity=sens,
        xattn_overlay_precheck=xchk)
    json.dump(result, open(E + "book_assembly_raw.json", "w"), indent=2, default=str)
    print("SAVED " + E + "book_assembly_raw.json", flush=True)
