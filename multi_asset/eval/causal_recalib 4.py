"""CAUSAL RECALIBRATION LAYER (Stage-0c) — deploy-side health/alpha module, ZERO GPU.

Implements the appendix D2(a)+a0+c3 spec UNIFIED with D5's trailing-β rescale. Every
quantity is strictly causal (≤ t, with a label-closure embargo for anything that
consumes realized y). Pre-registered FROZEN params (NO per-month tuning, ever):

  λ0 (tail floor)          = 0.35
  τ  (tail sigmoid temp)   = 0.05      -> gate sigmoid((rank-0.8)/τ)
  γ  (short×funding coeff)  = 0.30
  β̂ trailing window        = 30 days   (daily update, label-closed rows only)
  β̂ clip                    = [0.20, 1.60]
  rank trailing window     = 30 days   (|pred| distribution, no label needed)
  N_min (β̂ / rank warmup)  = 500 / 200 rows  (below -> identity, deploy warmup)
  funding tercile          = expanding window of settled 8h prints ≤ t (min 90)

THREE composable components (all applied to the deployed EMA no-peek q50 stream):
  (i)  β̂-rescale  : q1 = β̂_trail · q_tmp      -> drives realized β toward 1 (Pearson-
                     invariant within a day; fixes β/σ health). D5's rescale.
  (ii) tail-reweight: q_tmp = w · q, w = λ0 + (1-λ0)·σ((r-0.8)/τ), r = causal trailing
                     |q|-rank. Nonuniformly up-weights the high-|pred| tail (H1: the only
                     surviving drift signal). THIS is the within-day IC lever.
  (iii) c3 short×funding overlay: for q1<0 rows, q2 = q1·(1+γ·s), s∈{+1,0,-1} by the
                     tercile of the prior settled funding print (top tercile shorts WIN
                     -> amplify; bottom tercile shorts LOSE -> suppress). H5 structure.

Variant a0 (free diagnostic): gate on the trailing rank of prediction CONFIDENCE
(−(q90−q10) interval width) instead of |q|.

CALIBRATION metrics (P / β / σ, per-day-CLEAN + DENSE) are computed on the SAME npz
EMA preds and SAME aggregator caliber as multi_asset/eval/final_deliverable_l01.py
(mask-applied), so 'before' == the Stage-0a baseline table exactly. The c3 short-side
P&L test uses the real perp-book-mid bps returns from the Stage-0a backtest CSV.

Run:  PYTHONPATH=. python multi_asset/eval/causal_recalib.py \
         [--dir experiments_local/wfEMA] [--csv exports/final_l01/y600_backtest_dataset.csv]
"""
from __future__ import annotations
import numpy as np, os, csv, argparse
from scipy.stats import pearsonr, spearmanr
from scipy.special import expit

MONTHS = ["2025_08","2025_09","2025_10","2025_11","2025_12",
          "2026_01","2026_02","2026_03","2026_04","2026_05"]
HZ = 600 * 1_000_000            # label horizon (µs)
DAY = 86400 * 1_000_000         # µs/day

# ---- FROZEN pre-registered params (do NOT tune per month) --------------------
LAMBDA0   = 0.35
TAU       = 0.05
GAMMA     = 0.30
W_BETA    = 30 * DAY
W_RANK    = 30 * DAY
BETA_CLIP = (0.20, 1.60)
N_MIN_BETA = 500
N_MIN_RANK = 200
FUND_MIN_PRINTS = 90
# health / kill-gate bands
BETA_BAND = (0.7, 1.4)
SIG_MIN   = 0.02


# --------------------------------------------------------------------------- #
# caliber helpers (identical math to final_deliverable_l01.py)                 #
# --------------------------------------------------------------------------- #
def clean_idx(ts):
    o = np.argsort(ts); keep = []; last = -1e18
    for i in range(len(o)):
        if ts[o[i]] - last >= HZ:
            keep.append(o[i]); last = ts[o[i]]
    return np.array(keep, dtype=int)

def perday_clean(q, y, ts):
    """Return (mean per-day Pearson, list of per-day Pearsons)."""
    daykey = ts // DAY; rs = []
    for dk in np.unique(daykey):
        m = daykey == dk; k = clean_idx(ts[m])
        if len(k) > 20:
            qk = q[m][k]; yk = y[m][k]
            if qk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]
                if np.isfinite(r): rs.append(r)
    return (np.mean(rs) if rs else np.nan), rs

def dense_P(q, y):
    return pearsonr(q, y)[0] if q.std() > 1e-12 else np.nan

def beta_sigma(q, y):
    b = np.cov(y, q)[0, 1] / q.var() if q.var() > 1e-12 else np.nan
    sg = q.std() / (y.std() + 1e-12)
    return b, sg


def load_month(dir_, mk):
    f = f"{dir_}/wf_{mk}/fold_0/ema_test_preds.npz"
    if not os.path.exists(f): return None
    z = np.load(f, allow_pickle=True)
    pr = z["predictions"].astype(np.float64)
    q = pr[:, 1] if pr.ndim == 2 else pr
    spread = (pr[:, 2] - pr[:, 0]) if (pr.ndim == 2 and pr.shape[1] >= 3) else np.zeros_like(q)
    y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
    ysig = float(z["y_sigma"]) if "y_sigma" in z.files else 1.0
    ymed = float(z["y_median"]) if "y_median" in z.files else 0.0
    if "mask" in z.files:                     # Stage-0a hygiene: drop padded rows
        keep = z["mask"].astype(bool)
        q, y, ts, spread = q[keep], y[keep], ts[keep], spread[keep]
    return q, y, ts, spread, ysig, ymed


# --------------------------------------------------------------------------- #
# funding terciles (expanding, causal)                                         #
# --------------------------------------------------------------------------- #
def load_funding(path="data/funding/btcusdt_funding.csv"):
    if not os.path.exists(path): return None
    ft = []; fr = []
    with open(path) as fh:
        r = csv.DictReader(fh)
        for row in r:
            try:
                ft.append(int(row["fundingTime_ms"])); fr.append(float(row["fundingRate"]))
            except Exception:
                continue
    ft = np.array(ft, np.int64); fr = np.array(fr, np.float64)
    o = np.argsort(ft); return ft[o], fr[o]

def funding_sign(ts_us, fund):
    """s∈{+1,0,-1}: tercile of the last settled 8h funding print ≤ t, terciles from
    the expanding window of prints ≤ t (min FUND_MIN_PRINTS). Strictly causal."""
    if fund is None: return np.zeros(len(ts_us), np.int8)
    ft_ms, fr = fund; ts_ms = ts_us // 1000
    idx = np.searchsorted(ft_ms, ts_ms, side="right") - 1   # last print ≤ t
    s = np.zeros(len(ts_us), np.int8)
    for k in range(len(ts_us)):
        j = idx[k]
        if j < FUND_MIN_PRINTS: continue                    # warmup
        hist = fr[:j + 1]                                    # all prints ≤ t
        q33, q67 = np.quantile(hist, [1/3, 2/3])
        v = fr[j]
        if v >= q67:   s[k] = 1
        elif v <= q33: s[k] = -1
    return s


# --------------------------------------------------------------------------- #
# CAUSAL recalibration (daily update, strictly ≤ t)                            #
# --------------------------------------------------------------------------- #
def recalibrate(q, y, ts, spread, gate="absq", fund=None, use_c3=True):
    """All inputs already sorted by ts (global stream across months).
    Returns dict with q_ab (i+ii), q_abc (i+ii+iii), and diagnostics."""
    n = len(q)
    score = np.abs(q) if gate == "absq" else -spread   # a0: confidence = narrow interval
    day = ts // DAY
    udays = np.unique(day)

    # ---- pass 1: tail-reweight factor w (causal trailing rank of `score`) ----
    w = np.ones(n)
    for ud in udays:
        T0 = ud * DAY
        lo = np.searchsorted(ts, T0 - W_RANK, side="left")
        hi = np.searchsorted(ts, T0, side="left")           # rows strictly before day
        cur = np.where(day == ud)[0]
        if hi - lo < N_MIN_RANK:
            continue                                        # warmup -> w=1
        strail = np.sort(score[lo:hi])
        r = np.searchsorted(strail, score[cur], side="right") / (hi - lo)
        w[cur] = LAMBDA0 + (1 - LAMBDA0) * expit((r - 0.8) / TAU)
    q_tmp = w * q

    # ---- pass 2: trailing-30d causal β̂ on q_tmp (label-closed rows only) -----
    beta_hat = np.ones(n)
    for ud in udays:
        T0 = ud * DAY
        lo = np.searchsorted(ts, T0 - W_BETA, side="left")
        hi = np.searchsorted(ts, T0 - HZ, side="right")     # label closed: ts_j+600s ≤ T0
        cur = np.where(day == ud)[0]
        if hi - lo >= N_MIN_BETA:
            qb = q_tmp[lo:hi]; yb = y[lo:hi]
            if qb.var() > 1e-12:
                bh = np.cov(yb, qb)[0, 1] / qb.var()
                beta_hat[cur] = float(np.clip(bh, *BETA_CLIP))
    q1 = beta_hat * q_tmp                                    # (i)+(ii)

    # ---- pass 3: c3 short×funding overlay -----------------------------------
    s = funding_sign(ts, fund) if use_c3 else np.zeros(n, np.int8)
    q2 = q1.copy()
    if use_c3:
        short = q1 < 0
        q2[short] = q1[short] * (1 + GAMMA * s[short])
    return dict(q_ab=q1, q_abc=q2, w=w, beta_hat=beta_hat, fund_sign=s)


# --------------------------------------------------------------------------- #
# bootstrap                                                                    #
# --------------------------------------------------------------------------- #
def month_daylift_bootstrap(per_month_days_before, per_month_days_after, B=5000, seed=0):
    """Stratified (by-month) day-block bootstrap of the pooled cd-CLEAN lift.
    per_month_days_*: dict mk -> list of per-day Pearson. Returns (point_lift, P(lift≤0))."""
    rng = np.random.default_rng(seed)
    mks = [m for m in per_month_days_before if per_month_days_before[m] and per_month_days_after[m]]
    # point estimate: pooled = mean over months of (mean over days)
    pt = np.mean([np.mean(per_month_days_after[m]) - np.mean(per_month_days_before[m]) for m in mks])
    le = 0
    for _ in range(B):
        mm = []
        for m in mks:
            nb = len(per_month_days_before[m]); na = len(per_month_days_after[m])
            bi = rng.integers(0, nb, nb); ai = rng.integers(0, na, na)
            mm.append(np.mean(np.asarray(per_month_days_after[m])[ai]) -
                      np.mean(np.asarray(per_month_days_before[m])[bi]))
        if np.mean(mm) <= 0: le += 1
    return pt, le / B


def day_cluster_t(vals, days):
    """t-stat of daily-mean(vals) vs 0, clustering by day (each day = one obs)."""
    vals = np.asarray(vals); days = np.asarray(days)
    dm = np.array([vals[days == d].mean() for d in np.unique(days)])
    if len(dm) < 2 or dm.std(ddof=1) == 0: return np.nan, len(dm)
    return dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm)


# --------------------------------------------------------------------------- #
# c3 short-side P&L test (real perp-mid bps from the Stage-0a backtest CSV)    #
# --------------------------------------------------------------------------- #
def c3_pnl_test(csv_path, fund):
    if not os.path.exists(csv_path):
        print(f"  [c3] backtest CSV missing ({csv_path}) — skipping P&L test."); return
    ts_ms = []; pred = []; ytr = []; mon = []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            if not row["month"].startswith("2026"): continue
            ts_ms.append(int(row["timestamp_ms"])); pred.append(float(row["y_pred_raw"]))
            ytr.append(float(row["y_true_ret_bps"])); mon.append(row["month"])
    if not ts_ms:
        print("  [c3] no 2026 rows in CSV — skipping."); return
    ts_ms = np.array(ts_ms, np.int64); pred = np.array(pred); ytr = np.array(ytr)
    ts_us = ts_ms * 1000; day = ts_us // DAY
    s = funding_sign(ts_us, fund)
    short = pred < 0
    pnl_short   = -ytr[short]                              # unit short PnL (bps)
    pnl_gated   = -ytr[short] * (1 + GAMMA * s[short])     # funding-gated short book
    pnl_margin  = -ytr[short] * (GAMMA * s[short])         # gate's incremental contribution
    dshort = day[short]
    t_raw, nd = day_cluster_t(pnl_short, dshort)
    t_gate, _ = day_cluster_t(pnl_gated, dshort)
    t_marg, _ = day_cluster_t(pnl_margin, dshort)
    print("\n=== c3 SHORT×FUNDING P&L (2026, real perp-mid bps, day-clustered) ===")
    print(f"  short rows={short.sum()} over {nd} days | funding sign: +1={np.sum(s[short]==1)} "
          f"0={np.sum(s[short]==0)} -1={np.sum(s[short]==-1)}")
    print(f"  raw short book   mean={pnl_short.mean():+.4f}bps  day-t={t_raw:+.2f}")
    print(f"  GATED short book mean={pnl_gated.mean():+.4f}bps  day-t={t_gate:+.2f}   <- kill-gate stat")
    print(f"  gate marginal    mean={pnl_margin.mean():+.4f}bps day-t={t_marg:+.2f}   (isolates the funding gate)")
    # H5 replication: short-DECILE, F3-F1 return by funding tercile
    dec = pred <= np.quantile(pred, 0.10)
    f3 = dec & (s == 1); f1 = dec & (s == -1)
    if f3.sum() > 5 and f1.sum() > 5:
        diff = ytr[f3].mean() - ytr[f1].mean()
        # day-clustered t of (F3 - F1): use per-day means difference
        d3 = {d: ytr[f3 & (day == d)].mean() for d in np.unique(day[f3])}
        d1 = {d: ytr[f1 & (day == d)].mean() for d in np.unique(day[f1])}
        common = sorted(set(d3) & set(d1))
        if len(common) >= 2:
            dd = np.array([d3[d] - d1[d] for d in common])
            tdd = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd))) if dd.std(ddof=1) > 0 else np.nan
            print(f"  H5 short-decile F3-F1 return diff={diff:+.3f}bps  day-t={tdd:+.2f} (n_days={len(common)})")
    verdict = "PASS" if (np.isfinite(t_gate) and t_gate >= 1.5) else "KILL"
    print(f"  --> c3 literal gate (gated-book day-t={t_gate:+.2f} vs 1.5): {verdict}")
    print(f"  --> c3 HONEST test (does the funding gate ADD value?): marginal day-t="
          f"{t_marg:+.2f}  -> {'gate adds' if (np.isfinite(t_marg) and t_marg>=1.5) else 'gate does NOT add (≤0 => HARMS)'}")
    return t_gate, t_marg


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="experiments_local/wfEMA")
    ap.add_argument("--csv", default="exports/final_l01/y600_backtest_dataset.csv")
    ap.add_argument("--funding", default="data/funding/btcusdt_funding.csv")
    a = ap.parse_args()

    fund = load_funding(a.funding)
    print(f"=== CAUSAL RECALIB (Stage-0c) dir={a.dir} | funding={'loaded' if fund else 'MISSING'} ===")
    print(f"    FROZEN params: λ0={LAMBDA0} τ={TAU} γ={GAMMA} Wβ=30d clip={BETA_CLIP} "
          f"Nmin(β/rank)={N_MIN_BETA}/{N_MIN_RANK}")

    # ---- load + build global time-ordered stream -----------------------------
    per = {}
    for mk in MONTHS:
        L = load_month(a.dir, mk)
        if L is None: print(f"  {mk}: MISSING"); continue
        per[mk] = L
    if not per: print("NO DATA"); return
    q = np.concatenate([per[m][0] for m in per])
    y = np.concatenate([per[m][1] for m in per])
    ts = np.concatenate([per[m][2] for m in per])
    spread = np.concatenate([per[m][3] for m in per])
    mon = np.concatenate([[m] * len(per[m][0]) for m in per])
    o = np.argsort(ts, kind="stable")
    q, y, ts, spread, mon = q[o], y[o], ts[o], spread[o], mon[o]

    variants = {
        "a  (|q|-rank tail + β̂)": recalibrate(q, y, ts, spread, gate="absq", fund=fund, use_c3=False),
        "a+c3 (FULL recalib)":     recalibrate(q, y, ts, spread, gate="absq", fund=fund, use_c3=True),
        "a0 (spread-rank tail)":   recalibrate(q, y, ts, spread, gate="spread", fund=fund, use_c3=False),
    }

    # ---- per-month + pooled report per variant -------------------------------
    for vname, rc in variants.items():
        after_key = "q_abc" if "c3" in vname else "q_ab"
        qafter = rc[after_key]
        print(f"\n=== VARIANT: {vname}  [after = {after_key}] ===")
        print(f"{'month':8s} | {'cdC-bef':>8s} {'cdC-aft':>8s} {'Δcd':>7s} | "
              f"{'DEN-bef':>7s} {'DEN-aft':>7s} {'Δden':>7s} | {'β-bef':>6s} {'β-aft':>6s} | "
              f"{'σ-bef':>6s} {'σ-aft':>6s}")
        pmd_bef = {}; pmd_aft = {}; rows = []
        for mk in [m for m in MONTHS if m in per]:
            mm = mon == mk
            qb, yb, tb = q[mm], y[mm], ts[mm]; qa = qafter[mm]
            cb, dbef = perday_clean(qb, yb, tb); ca, daft = perday_clean(qa, yb, tb)
            Db = dense_P(qb, yb); Da = dense_P(qa, yb)
            bb, sgb = beta_sigma(qb, yb); ba, sga = beta_sigma(qa, yb)
            pmd_bef[mk] = dbef; pmd_aft[mk] = daft
            rows.append((mk, cb, ca, Db, Da, bb, ba, sga))
            print(f"{mk:8s} | {cb:+8.4f} {ca:+8.4f} {ca-cb:+7.4f} | "
                  f"{Db:+7.4f} {Da:+7.4f} {Da-Db:+7.4f} | {bb:+6.2f} {ba:+6.2f} | "
                  f"{sgb:6.3f} {sga:6.3f}")
        cb_pool = np.mean([r[1] for r in rows]); ca_pool = np.mean([r[2] for r in rows])
        Db_pool = np.mean([r[3] for r in rows]); Da_pool = np.mean([r[4] for r in rows])
        pt, ple = month_daylift_bootstrap(pmd_bef, pmd_aft)
        print(f"{'POOLED':8s} | {cb_pool:+8.4f} {ca_pool:+8.4f} {ca_pool-cb_pool:+7.4f} | "
              f"{Db_pool:+7.4f} {Da_pool:+7.4f} {Da_pool-Db_pool:+7.4f} |")
        print(f"  cd-CLEAN pooled lift={ca_pool-cb_pool:+.4f} | day-block bootstrap P(lift≤0)={ple:.3f}")
        # kill-gate verdicts (headline = the FULL a+c3 variant)
        month_floor_drop = min([r[2] - r[1] for r in rows])   # most negative month Δcd
        beta_out = sum(not (BETA_BAND[0] <= r[6] <= BETA_BAND[1]) for r in rows)
        sig_bad  = sum(r[7] < SIG_MIN for r in rows)
        print(f"  worst month Δcd={month_floor_drop:+.4f} | months β∉[0.7,1.4]: {beta_out} | months σ<0.02: {sig_bad}")
        if "FULL" in vname:
            fails = []
            if (ca_pool - cb_pool) < 0.004: fails.append(f"pooled lift {ca_pool-cb_pool:+.4f}<+0.004")
            if month_floor_drop < -0.002:   fails.append(f"month floor drop {month_floor_drop:+.4f}<-0.002")
            if ple > 0.10:                  fails.append(f"P(lift≤0)={ple:.3f}>0.10")
            if beta_out > 1:                fails.append(f"{beta_out} months β∉[0.7,1.4] (>1)")
            print(f"  ===> RECALIB KILL-GATE: {'PASS' if not fails else 'KILL — ' + '; '.join(fails)}")

    # ---- c3 short-side P&L test (real bps) -----------------------------------
    c3_pnl_test(a.csv, fund)
    print("\nDONE_RECALIB.")


if __name__ == "__main__":
    main()
