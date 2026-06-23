#!/usr/bin/env python
"""TAIL-MAGNITUDE production economics for the HF180R y180 signal.

Question answered: long-short base + operate ONLY on the large-|prediction| tail
(magnitude-band filter) + holding/min-hold + signal-reversal exit (single-side
directional books too) — what net-of-fee Sharpe?

Extends _hfecon_prod.py (reuses _hfecon.py rank engine, fee model, day-block
bootstrap Sharpe-CI, per-fold sign-consistency). ADDS, exactly per the spec:

  1. TAIL / magnitude-band FILTER: per timestamp, among valid assets keep only the
     names whose |pred| is in the top-q fraction cross-sectionally (q in {0.10,0.20,
     0.30,0.50}); the rest are flat. (Absolute |z|>1 band == existing 'directional'.)
     Filter is applied BEFORE weight construction; selection on RAW |pred| (the model
     deliverable). q is computed per-row on the count of valid assets (>= ceil(q*Nvalid),
     at least 1 per side for single-side, at least 2 total for L/S).
  2. BOOK VARIANTS on the tail names:
       ls_tail        : cross-sectional rank, demeaned, gross|w|=2 (L/S, both legs)
       ls_tail_conv   : rank x |z| conviction, demeaned, gross|w|=2
       long_only      : only positive-pred tail names, gross|w|=1 (one side)
       short_only     : only negative-pred tail names, gross|w|=1 (one side)
     Weighting within a side: equal (sign book) OR conviction (|z|). Reported both.
  3. HOLDING / min-hold: K in {1,3,10,30} bars (1 bar=180s). A non-zero position
     cannot be changed until K bars elapsed since its last trade for that asset.
  4. SIGNAL-REVERSAL EXIT: hold a position through same-sign-in-band bars; close ONLY
     when the sign flips OR the name leaves the tail band (conviction exits). NOT every
     bar. Combined with min-hold floor (cannot exit before K even on reversal -> the
     reversal request is latched and applied at the first allowed bar).
  5. FEES: maker {0.5,1,2} bps/side (cost = fee*sum|dW|). Universes FULL14 + LIQUID5.
  6. Calibration: rank/sign/conviction books are isotonic-calib-invariant (monotone
     map preserves cross-sectional order + sign); calib.json beta-rescale would only
     scale magnitudes, leaving rank/sign/tail-membership/turnover unchanged. So results
     hold for the calibrated signal too (noted, not re-run).

REPORT per config: net Sharpe + day-block bootstrap 95% CI, net bps/day, gross bps/day,
turnover/day, breakeven fee, per-fold sign-consistency (x/3). Headline = single highest
net-Sharpe config that is honest (CI, 3/3, fee, subset, P&L scale).

CPU numpy only. Read-only inputs. Writes /tmp/hfecon_tail.json.
"""
import json, types
import numpy as np

SRC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/eda/_hfecon.py"
eng = types.ModuleType("eng")
exec(compile(open(SRC).read(), SRC, "exec"), eng.__dict__)

BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
SUBDIR = "HF180R"
H = 180
GRID_S = 180
SYMBOLS = eng.SYMBOLS
LIQUID5 = ["btc", "eth", "sol", "bnb", "xrp"]
LIQ_IDX = np.array([SYMBOLS.index(s) for s in LIQUID5])
FEES = [0.0, 0.5, 1.0, 2.0]   # MAKER bps/side (maker-fill optimistic, stated)
TAILS = [0.10, 0.20, 0.30, 0.50, 1.00]  # 1.00 = no tail filter (reference)
KS = [1, 3, 10, 30]                      # min-hold bars (1 bar = 180s)
BOOKS = ["ls_tail", "ls_tail_conv", "long_only", "long_only_conv",
         "short_only", "short_only_conv"]
B_BOOT = 5000
RNG = np.random.default_rng(42)


# ---------------- tail-filtered weight builder ----------------
def tail_weights(pred_rows, book, q, min_valid):
    """Per-row target weights after top-q |pred| tail filter.

    book: ls_tail | ls_tail_conv | long_only[_conv] | short_only[_conv]
    q   : keep top-q fraction by |pred| cross-sectionally (1.0 = keep all valid).
    Returns (W (nT,NA), SIGN (nT,NA) latched-desired sign, INBAND (nT,NA) bool).
    Gross |w| normalized to 2 for L/S (both legs), 1 for single-side.
    """
    nT = pred_rows.shape[0]
    NA = pred_rows.shape[1]
    W = np.zeros((nT, NA))
    SGN = np.zeros((nT, NA))
    INB = np.zeros((nT, NA), dtype=bool)
    conv = book.endswith("_conv")
    for t in range(nT):
        p = pred_rows[t]
        v = np.isfinite(p)
        nv = int(v.sum())
        if nv < min_valid:
            continue
        idxv = np.where(v)[0]
        pv = p[idxv]
        ap = np.abs(pv)
        # tail membership: top-q by |pred| among valid
        if q >= 1.0:
            keep = np.ones(nv, dtype=bool)
        else:
            k = max(1, int(np.ceil(q * nv)))
            thr = np.sort(ap)[nv - k]            # k-th largest
            keep = ap >= thr
        # cross-sectional z over the FULL valid set (demean ref = all valid names)
        mu = pv.mean(); sd = pv.std() + 1e-12
        z = (pv - mu) / sd
        sgn = np.sign(z)
        sgn[sgn == 0] = 0.0
        inband = keep & (sgn != 0)
        SGN[t, idxv] = sgn * inband
        INB[t, idxv] = inband
        # ---- book construction on tail-kept names ----
        w = np.zeros(nv)
        if book.startswith("ls_tail"):
            kept = inband
            if kept.sum() < 2:        # need both-ish sides; if <2 names, skip
                continue
            pk = pv[kept]
            rk = eng.rank_weights(pk)         # demeaned rank within kept set
            if conv:
                rk = rk * np.abs(z[kept])
            ww = rk - rk.mean()
            s = np.abs(ww).sum()
            ww = ww * (2.0 / s) if s > 1e-12 else ww * 0.0
            w[kept] = ww
        elif book.startswith("long_only"):
            sel = inband & (sgn > 0)
            if sel.sum() < 1:
                continue
            mag = np.abs(z[sel]) if conv else np.ones(int(sel.sum()))
            s = mag.sum()
            w[sel] = (mag / s) if s > 0 else 0.0   # gross 1 long
        elif book.startswith("short_only"):
            sel = inband & (sgn < 0)
            if sel.sum() < 1:
                continue
            mag = np.abs(z[sel]) if conv else np.ones(int(sel.sum()))
            s = mag.sum()
            w[sel] = -(mag / s) if s > 0 else 0.0  # gross 1 short
        W[t, idxv] = w
    return W, SGN, INB


# ---------------- reversal-exit + min-hold book walk ----------------
def run_reversal_minhold(W, SGN, INB, Yrows, K):
    """Hold through same-sign-in-band; rebalance toward W only when an asset's desired
    sign FLIPS or it leaves the band (INB False). Min-hold K: an asset's position is
    frozen for K bars after its last trade; a reversal/exit that arrives during the
    freeze is latched and executed at the first allowed bar.

    Within a held same-sign episode we do NOT chase magnitude drift (turnover-reducer):
    we only re-size to the current target at the bar we actually trade (entry / flip /
    exit / re-entry). pos . Y is the realized PnL per bar.
    """
    nT, NA = W.shape
    pos = np.zeros(NA)
    held_sign = np.zeros(NA)               # sign currently held (0 = flat)
    last_trade = -np.ones(NA, dtype=int) * 10**9
    gross = np.zeros(nT); tover = np.zeros(nT)
    for t in range(nT):
        des_sign = SGN[t]                  # desired sign this bar (0 if not in band)
        inb = INB[t]
        tgt = pos.copy()
        can = (t - last_trade) >= K        # min-hold elapsed?
        for a in range(NA):
            if not can[a]:
                continue                   # frozen -> keep pos
            hs = held_sign[a]
            ds = des_sign[a]
            if hs == 0:
                # flat: open if name now in band with a sign
                if inb[a] and ds != 0:
                    tgt[a] = W[t, a]
                    held_sign[a] = ds
                # else stay flat
            else:
                # currently holding hs
                if (not inb[a]) or ds == 0:
                    tgt[a] = 0.0           # band-exit -> close
                    held_sign[a] = 0.0
                elif ds != hs:
                    tgt[a] = W[t, a]       # sign flip -> reverse to new side
                    held_sign[a] = ds
                else:
                    # same sign, still in band -> HOLD (no rebalance, no turnover)
                    pass
        dW = np.abs(tgt - pos)
        moved = dW > 1e-9
        last_trade[moved] = t
        tover[t] = dW.sum()
        pos = tgt
        yt = Yrows[t].copy(); yt[~np.isfinite(yt)] = 0.0
        gross[t] = 1e4 * float(pos @ yt)
    return gross, tover


# ---------------- fold prep (mirror _hfecon_prod) ----------------
def prep_fold(f, ts, day, Yc, stride, col_idx):
    z = np.load(f"{BASE}/{SUBDIR}/fold_{f}_preds.npz", allow_pickle=True)
    pred_full = z["pred"].astype(np.float64)[:, col_idx]
    tr = np.sort(z["te_rows"])
    dd = day[tr]
    dec_rows = []
    for dv in np.unique(dd):
        rday = tr[dd == dv]
        rday = rday[np.argsort(ts[rday])]
        dec_rows.append(rday[::stride])
    dec = np.concatenate(dec_rows)
    dec = dec[np.argsort(ts[dec])]
    return dict(dec=dec, preds=pred_full[dec], days=day[dec], Y=Yc[dec][:, col_idx])


# ---------------- metrics ----------------
def boot_sharpe_ci(dn):
    if len(dn) < 3 or dn.std() == 0:
        return None, None
    idx = RNG.integers(0, len(dn), size=(B_BOOT, len(dn)))
    samp = dn[idx]
    mu = samp.mean(axis=1); sd = samp.std(axis=1)
    sh = np.where(sd > 0, mu / sd * np.sqrt(365), np.nan)
    sh = sh[np.isfinite(sh)]
    if len(sh) == 0:
        return None, None
    return round(float(np.percentile(sh, 2.5)), 2), round(float(np.percentile(sh, 97.5)), 2)


def summarize(gross, tover, days, fee):
    net = gross - fee * tover
    ud = np.unique(days)
    dn = np.array([net[days == d].sum() for d in ud])
    gd = np.array([gross[days == d].sum() for d in ud])
    sh = float(dn.mean() / dn.std() * np.sqrt(365)) if dn.std() > 0 else None
    lo, hi = boot_sharpe_ci(dn)
    if len(dn) >= 1:
        idx = RNG.integers(0, len(dn), size=(B_BOOT, len(dn)))
        pg = round(float((dn[idx].mean(axis=1) > 0).mean()), 3)
    else:
        pg = None
    return dict(net_bps_day=round(float(dn.mean()), 3),
                gross_bps_day=round(float(gd.mean()), 3),
                ann_sharpe=round(sh, 2) if sh is not None else None,
                sharpe_ci95=[lo, hi], p_gt0=pg,
                turn_day=round(float(tover.sum() / len(ud)), 3))


def eval_cfg(books, fold_days):
    g = np.concatenate([b[0] for b in books])
    t = np.concatenate([b[1] for b in books])
    d = np.concatenate([fold_days[f] + f * 10**9 for f in range(3)])
    gm, tm = g.mean(), t.mean()
    e = dict(gross_bps_step=round(float(gm), 5),
             breakeven_fee_bps=round(float(gm / tm), 4) if tm > 1e-9 else None,
             turn_step=round(float(tm), 4))
    for fee in FEES:
        e[f"fee_{fee}"] = summarize(g, t, d, fee)
    e["per_fold"] = {}
    for f in range(3):
        gf, tf = books[f]
        e["per_fold"][f"f{f}"] = {str(fee): summarize(gf, tf, fold_days[f], fee)["net_bps_day"]
                                  for fee in FEES}
    for fee in FEES:
        nets = [e["per_fold"][f"f{f}"][str(fee)] for f in range(3)]
        e[f"folds_pos_{fee}"] = int(sum(n > 0 for n in nets))
    return e


def run_universe(uname, col_idx):
    ref = np.load(f"{BASE}/{SUBDIR}/panel_ref.npz", allow_pickle=True)
    ts = ref["ts"].astype(np.int64); day = ref["day"].astype(np.int64)
    Y = ref["Y"].astype(np.float64); CL = ref["CL"]
    Yc = Y.copy(); Yc[~CL] = np.nan
    stride = 1 if H <= GRID_S else int(np.ceil(H / GRID_S))
    folds = {f: prep_fold(f, ts, day, Yc, stride, col_idx) for f in range(3)}
    eng.NA = len(col_idx)
    min_valid = 3 if len(col_idx) <= 6 else 5
    eng.MIN_VALID = min_valid
    fold_days = {f: folds[f]["days"] for f in range(3)}
    spd = {f: int(np.median([np.sum(folds[f]["days"] == dv)
                             for dv in np.unique(folds[f]["days"])])) for f in range(3)}
    out = {"universe": uname, "n_assets": len(col_idx), "stride": stride,
           "steps_per_day": spd, "min_valid": min_valid, "configs": {}}
    for book in BOOKS:
        for q in TAILS:
            # precompute tail weights per fold once per (book,q)
            wcache = {}
            for f in range(3):
                wcache[f] = tail_weights(folds[f]["preds"], book, q, min_valid)
            for K in KS:
                cname = f"{book}__q{int(q*100):03d}__K{K:02d}"
                books = []
                for f in range(3):
                    W, SGN, INB = wcache[f]
                    b = run_reversal_minhold(W, SGN, INB, folds[f]["Y"], K)
                    books.append(b)
                out["configs"][cname] = eval_cfg(books, fold_days)
    return out


def main():
    results = {"meta": {"signal": SUBDIR, "horizon_s": H,
                        "fees_maker_bps_per_side": FEES,
                        "cost_model": "fee_per_side * sum|dW| (each leg one MAKER side); maker-fill optimistic",
                        "tails_top_frac": TAILS, "minhold_bars": KS, "books": BOOKS,
                        "bar_seconds": GRID_S, "liquid5": LIQUID5, "b_boot": B_BOOT,
                        "exit_rule": "reversal-exit: hold same-sign-in-band, close on sign-flip OR band-exit; min-hold K latches early reversals",
                        "calib_note": "rank/sign/conviction + tail membership are isotonic-calib-invariant; calib.json beta-rescale leaves them unchanged"},
               "universes": {}}
    for uname, idx in [("FULL14", np.arange(14)), ("LIQUID5", LIQ_IDX)]:
        print(f"\n===== UNIVERSE {uname} (n={len(idx)}) =====", flush=True)
        u = run_universe(uname, idx)
        results["universes"][uname] = u
        # compact print: show best-by-Sharpe per book at fee 1.0
        print(f"  {'config':<26} {'turn/d':>8} {'g_bps/d':>8} | "
              f"{'@0.5':>7} {'@1':>7} {'@2':>7} | {'Sh@1':>7} {'CI95@1':>16} {'f+@1':>5} BE")
        for cname, e in sorted(u["configs"].items()):
            f05 = e["fee_0.5"]; f1 = e["fee_1.0"]; f2 = e["fee_2.0"]
            ci = f1["sharpe_ci95"]
            print(f"  {cname:<26} {f1['turn_day']:>8.2f} {f1['gross_bps_day']:>+8.2f} | "
                  f"{f05['net_bps_day']:>+7.2f} {f1['net_bps_day']:>+7.2f} {f2['net_bps_day']:>+7.2f} | "
                  f"{str(f1['ann_sharpe']):>7} {str(ci):>16} {e['folds_pos_1.0']}/3 "
                  f"{str(e['breakeven_fee_bps'])}")
    with open("/tmp/hfecon_tail.json", "w") as fh:
        json.dump(results, fh, indent=1)
    print("\nwrote /tmp/hfecon_tail.json")


if __name__ == "__main__":
    main()
