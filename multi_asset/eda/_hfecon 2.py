#!/usr/bin/env python
"""HONEST after-fee economics across high-freq multi-asset horizons (y60/y180/y600).

Adapted from /tmp/econ_y600_ext.py (L/S book engine, hysteresis, fee accounting,
day-block bootstrap). Adaptations vs the y600-only original:
  - New export schema: panel_ref{ts,day,Y(raw y_h),CL,symbols} +
    fold_k_preds{pred(T,14), te_rows, te_days, resid_sigma(14,), horizon}.
    No mh_targets cache needed: Y IS the horizon-specific realized return.
  - Three horizons in one run; panel ts spacing = 180s for ALL (verified).
  - OVERLAP DISCIPLINE (the honest part). horizon = holding/return period:
      h=60  : Y is 60s fwd, grid 180s  => hold < grid, NO overlap, stride 1 (473 steps/day)
      h=180 : Y is 180s fwd, grid 180s => contiguous, NO overlap, stride 1 (473 steps/day)
      h=600 : Y is 600s fwd, grid 180s => ~3.33x overlap; stride 4 (720s) =>
              non-overlapping 600s holds (matches prior eval grid). ~118 steps/day.
    Per-step PnL = pos . Y_h_realized; non-overlap stepping avoids double-counting.
  - FROZEN-from-train idio vol = saved per-fold resid_sigma (NOT OOS-window vol).
  - Books: V0 full rebal / H hysteresis(EMA lam x no-trade band) /
           C conviction-gate(|z|>1 hold-until-opposite) / D directional tail book.
  - Weighting: rank, rank x |z| conviction, risk-parity (resid_sigma), directional.
  - Cost: turnover-explicit. tover=sum|dW| (per-leg notional traded);
          cost = fee_per_side * tover  (each leg pays one taker side). MAKER = fantasy.
  - TAKER fees {0.5,1,2,4} bps/side. Headline on taker.
  - per-FOLD net + sign-consistency (folds_pos/3); day-block bootstrap P(daily net>0).
CPU numpy only. Repo READ-ONLY. Writes /tmp/hfecon.json.
"""
import json
import numpy as np

BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
HORIZONS = {"y60": ("HF60_y", 60), "y180": ("HF180_y", 180), "y600": ("RAW_y600", 600)}
GRID_S = 180  # panel ts spacing (seconds), verified uniform
FEES = [0.5, 1.0, 2.0, 4.0]  # TAKER bps/side
HEADLINE_FEE = 2.0
B_BOOT = 5000
RNG = np.random.default_rng(42)
MIN_VALID = 5
SYMBOLS = ["btc", "eth", "sol", "bnb", "xrp", "dog", "ada", "link",
           "bch", "trx", "ltc", "dot", "fil", "etc"]
NA = len(SYMBOLS)


# ---------------- weight constructors ----------------
def rank_weights(p):
    """Demeaned rank weights, scaled to sum|w|=2 (gross leverage 1 per side)."""
    n = len(p)
    if n < 2:
        return np.zeros(n)
    r = np.empty(n)
    r[np.argsort(p, kind="mergesort")] = np.arange(n)
    w = 2.0 * r / (n - 1) - 1.0
    w -= w.mean()
    s = np.abs(w).sum()
    return w * (2.0 / s) if s > 0 else w * 0.0


def normalize(w):
    w = w - w.mean()
    s = np.abs(w).sum()
    return w * (2.0 / s) if s > 1e-12 else w * 0.0


def build_weights(pred_rows, scheme, sigma=None):
    """Target weights per decision row. scheme: rank | rank_conviction | risk_parity | directional."""
    nT = pred_rows.shape[0]
    W = np.zeros((nT, NA))
    for t in range(nT):
        p = pred_rows[t]
        v = np.isfinite(p)
        if v.sum() < MIN_VALID:
            continue
        pv = p[v]
        if scheme == "rank":
            w = rank_weights(pv)
        elif scheme == "rank_conviction":
            z = (pv - pv.mean()) / (pv.std() + 1e-12)
            w = normalize(rank_weights(pv) * np.abs(z))
        elif scheme == "risk_parity":
            w = normalize(rank_weights(pv) / sigma[v])
        elif scheme == "directional":
            # per-asset tail book: sign of cross-sectional z, only |z|>1, normalized gross to 2
            z = (pv - pv.mean()) / (pv.std() + 1e-12)
            w = np.zeros(len(pv))
            hit = np.abs(z) > 1.0
            w[hit] = np.sign(z[hit])
            s = np.abs(w).sum()
            w = w * (2.0 / s) if s > 0 else w
        else:
            raise ValueError(scheme)
        W[t, v] = w
    return W


def build_zscores(pred_rows):
    nT = pred_rows.shape[0]
    Z = np.full((nT, NA), np.nan)
    for t in range(nT):
        p = pred_rows[t]
        v = np.isfinite(p)
        if v.sum() >= MIN_VALID:
            pv = p[v]
            Z[t, v] = (pv - pv.mean()) / (pv.std() + 1e-12)
    return Z


# ---------------- book engine ----------------
def run_book(W, Z, Yrows, mode, lam=None, band=None):
    """Walk decision rows in time order. PnL/step = pos . Y (Y already h-fwd, non-overlap).
    mode: full | hyst (EMA target + no-trade band) | conv (|z|>1 hold-until-opposite).
    Returns gross_bps_per_step (T,), turnover (T,) where turnover=sum|dW|."""
    nT = W.shape[0]
    pos = np.zeros(NA)
    ema = np.zeros(NA)
    held = np.zeros(NA)  # held sign for conv book
    gross = np.zeros(nT)
    tover = np.zeros(nT)
    for t in range(nT):
        if mode == "full":
            tgt = W[t]
        elif mode == "hyst":
            ema = lam * ema + (1 - lam) * W[t]
            tgt = pos.copy()
            mv = np.abs(ema - pos) > band
            tgt[mv] = ema[mv]
        elif mode == "conv":
            z = Z[t]
            strong = np.isfinite(z) & (np.abs(z) > 1.0)
            held[strong] = np.sign(z[strong])
            held[~np.isfinite(z)] = 0.0
            mag = np.abs(W[t])
            tgt = held * mag
            s = np.abs(tgt).sum()
            tgt = tgt * (2.0 / s) if s > 1e-12 else tgt
        else:
            raise ValueError(mode)
        tover[t] = np.abs(tgt - pos).sum()
        pos = tgt
        yt = Yrows[t].copy()
        yt[~np.isfinite(yt)] = 0.0
        gross[t] = 1e4 * float(pos @ yt)
    return gross, tover


# ---------------- metrics ----------------
def summarize(gross, tover, days, fee):
    net = gross - fee * tover  # fee_per_side applied to each leg of |dW|
    ud = np.unique(days)
    dn = np.array([net[days == d].sum() for d in ud])
    sh = float(dn.mean() / dn.std() * np.sqrt(365)) if dn.std() > 0 else np.nan
    idx = RNG.integers(0, len(dn), size=(B_BOOT, len(dn)))
    return dict(net_bps_per_day=round(float(dn.mean()), 3),
                ann_sharpe=round(sh, 2) if np.isfinite(sh) else None,
                p_gt0=round(float((dn[idx].mean(axis=1) > 0).mean()), 3),
                turn_per_day=round(float(tover.sum() / len(ud)), 3))


def eval_config(name, books, fold_days, results):
    g = np.concatenate([b[0] for b in books])
    t = np.concatenate([b[1] for b in books])
    d = np.concatenate([fold_days[f] + f * 10**9 for f in range(3)])  # disjoint day ids per fold
    gm, tm = g.mean(), t.mean()
    entry = dict(gross_bps_per_step=round(float(gm), 4),
                 breakeven_fee_bps=round(float(gm / tm), 4) if tm > 0 else None,
                 turn_per_step=round(float(tm), 4))
    for fee in FEES:
        entry[f"fee_{fee}"] = summarize(g, t, d, fee)
    entry["per_fold"] = {}
    for f in range(3):
        gf, tf = books[f]
        entry["per_fold"][f"fold{f}"] = {
            "gross": round(float(gf.mean()), 4),
            **{f"fee_{fee}": summarize(gf, tf, fold_days[f], fee) for fee in FEES}}
    for fee in FEES:
        nets = [entry["per_fold"][f"fold{f}"][f"fee_{fee}"]["net_bps_per_day"] for f in range(3)]
        entry[f"folds_pos_{fee}"] = int(sum(n > 0 for n in nets))
        entry[f"per_fold_net_{fee}"] = [round(n, 2) for n in nets]
    results[name] = entry
    return entry


# ---------------- per-fold decision-row + data prep ----------------
def prep_fold(subdir, f, ts, day, Yc, stride):
    z = np.load(f"{BASE}/{subdir}/fold_{f}_preds.npz", allow_pickle=True)
    rs = z["resid_sigma"].astype(np.float64)
    pred_full = z["pred"].astype(np.float64)
    tr = np.sort(z["te_rows"])
    dd = day[tr]
    dec_rows = []
    for dv in np.unique(dd):
        rday = tr[dd == dv]
        rday = rday[np.argsort(ts[rday])]
        dec_rows.append(rday[::stride])  # thin by stride WITHIN day (non-overlap)
    dec = np.concatenate(dec_rows)
    dec = dec[np.argsort(ts[dec])]  # global time order for continuous book walk
    preds = pred_full[dec]
    return dict(dec=dec, preds=preds, days=day[dec], Y=Yc[dec], rs=rs)


CFGS = [
    ("V0_rank_full", "rank", "full", None, None),
    ("H_rank_l0.90_b0.10", "rank", "hyst", 0.90, 0.10),
    ("H_rank_l0.90_b0.15", "rank", "hyst", 0.90, 0.15),
    ("H_rank_l0.97_b0.10", "rank", "hyst", 0.97, 0.10),
    ("H_rank_l0.97_b0.15", "rank", "hyst", 0.97, 0.15),
    ("Hconv_l0.97_b0.15", "rank_conviction", "hyst", 0.97, 0.15),
    ("C_convgate_rank", "rank", "conv", None, None),
    ("C_convgate_conv", "rank_conviction", "conv", None, None),
    ("D_directional_hyst", "directional", "hyst", 0.97, 0.15),
    ("D_directional_full", "directional", "full", None, None),
    ("RP_riskparity_full", "risk_parity", "full", None, None),
    ("RP_riskparity_hyst", "risk_parity", "hyst", 0.97, 0.15),
]


def main():
    results = {"meta": {"fees_taker_bps_per_side": FEES, "headline_fee": HEADLINE_FEE,
                        "grid_s": GRID_S, "n_folds": 3, "b_boot": B_BOOT,
                        "cost_model": "fee_per_side * sum|dW| (each leg one taker side); maker NOT modeled"},
               "horizons": {}}
    for hname, (subdir, h) in HORIZONS.items():
        ref = np.load(f"{BASE}/{subdir}/panel_ref.npz", allow_pickle=True)
        ts = ref["ts"].astype(np.int64)
        day = ref["day"].astype(np.int64)
        Y = ref["Y"].astype(np.float64)
        CL = ref["CL"]
        Yc = Y.copy()
        Yc[~CL] = np.nan

        stride = 1 if h <= GRID_S else int(np.ceil(h / GRID_S))
        note = ("contiguous, no overlap" if h == GRID_S else
                ("hold<grid, no overlap" if h < GRID_S else
                 f"{h}s on {GRID_S}s grid -> stride {stride} ({stride*GRID_S}s), non-overlapping"))

        folds = {f: prep_fold(subdir, f, ts, day, Yc, stride) for f in range(3)}
        # precompute weights + zscores per fold per scheme
        wcache = {}
        zcache = {}
        for f in range(3):
            p = folds[f]["preds"]
            wcache[f] = {s: build_weights(p, s, sigma=folds[f]["rs"])
                         for s in ("rank", "rank_conviction", "risk_parity", "directional")}
            zcache[f] = build_zscores(p)
        fold_days = {f: folds[f]["days"] for f in range(3)}
        spd = {f: int(np.median([np.sum(folds[f]["days"] == dv)
                                 for dv in np.unique(folds[f]["days"])])) for f in range(3)}
        align = [dict(fold=f, n_dec=int(len(folds[f]["dec"])), steps_per_day=spd[f],
                      Y_valid_frac=round(float(np.isfinite(folds[f]["Y"]).mean()), 4),
                      resid_sigma_bps=[round(float(x) * 1e4, 2) for x in folds[f]["rs"]])
                 for f in range(3)]

        hres = {"horizon_s": h, "stride": stride, "overlap_note": note,
                "steps_per_day": spd, "align": align, "configs": {}}
        for cname, scheme, mode, lam, band in CFGS:
            books = [run_book(wcache[f][scheme], zcache[f], folds[f]["Y"], mode, lam, band)
                     for f in range(3)]
            eval_config(cname, books, fold_days, hres["configs"])
        results["horizons"][hname] = hres
        print(f"[{hname}] stride={stride} spd={spd} {note}")
        for cname, *_ in CFGS:
            e = hres["configs"][cname]
            r2 = e[f"fee_{HEADLINE_FEE}"]
            print(f"  {cname:<22} gross/step {e['gross_bps_per_step']:+.4f} "
                  f"BE {str(e['breakeven_fee_bps']):>8} turn/step {e['turn_per_step']:.3f} | "
                  f"@2bps {r2['net_bps_per_day']:+7.2f}/d Sh {str(r2['ann_sharpe']):>6} "
                  f"P {r2['p_gt0']:.2f} folds+ {e['folds_pos_2.0']}/3")

    with open("/tmp/hfecon.json", "w") as fh:
        json.dump(results, fh, indent=1)
    print("wrote /tmp/hfecon.json")


if __name__ == "__main__":
    main()
