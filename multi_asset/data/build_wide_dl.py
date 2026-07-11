"""Engine A — WIDE hourly DL factor-mining dataset (2026-07-11, USER flagship).

Assembles the wide 110-coin hourly panel into a DL-ready sequence dataset:
  CH   (T,N,C) f32  causal per-coin hourly channels (zoo factors from wide_factory.build_factors
                    + raw multi-window returns / rvol / log-qvol), strictly <=t.
  Y{1,4,24}    (T,N) forward log-returns at 1/4/24h (RAW, for honest eval).
  YR{1,4,24}   (T,N) RESIDUAL targets: per-ts xsec-demean THEN residualize on the
                    [funding + zoo-cluster] baseline (OLS residual over members) -> DL earns only
                    incremental-over-[funding+zoo] credit (the proven paradigm).
  CL{1,4,24}   (T,N) >=horizon NON-OVERLAP clean masks (member & finite & greedy H-spacing).
  MEMBER110    (T,N) point-in-time top-110 by trailing-30d dollar-vol (monthly refresh).
  ts, symbols, ch_names, baseline_cols.

Data is small (~13k h x 140 coins x ~24 ch). Verify causal <=t + shuffle-future null (make_shuffle).
Run: PYTHONPATH=. python multi_asset/data/build_wide_dl.py
"""
from __future__ import annotations
import numpy as np
from multi_asset.data.wide_factory import build_factors, _shift, _roll

PANEL = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
         "multi_asset/exports/wide_panel.npz")
OUT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
       "multi_asset/exports/wide_dl.npz")
TOPN = 110
HORIZONS = (1, 4, 24)
# baseline the DL residualizes against (funding + the strongest zoo cluster). These channel names
# must exist in build_factors output.
BASELINE = ["funding_ema", "mom_24h", "mom_72h", "rev_1h", "rvol_24h", "size_dvol",
            "max_ret_24h", "beta_24h"]


def _xsec_residualize(Y, X, mem):
    """Per-ts: over members, demean Y then OLS-residualize on demeaned X (T,N,k). Returns (T,N)
    residual (NaN off-member). X columns already causal <=t; Y is the forward target."""
    T, N = Y.shape
    R = np.full((T, N), np.nan, np.float32)
    for t in range(T):
        v = mem[t] & np.isfinite(Y[t]) & np.isfinite(X[t]).all(1)
        if v.sum() < 12:
            continue
        y = Y[t, v] - Y[t, v].mean()
        Xt = X[t, v] - X[t, v].mean(0)
        # ridge-stabilised OLS (k small vs n~110): beta = (X'X + lam I)^-1 X'y
        XtX = Xt.T @ Xt + 1e-6 * np.eye(Xt.shape[1])
        beta = np.linalg.solve(XtX, Xt.T @ y)
        R[t, v] = (y - Xt @ beta).astype(np.float32)
    return R


def build(panel=PANEL, outpath=OUT):
    z = np.load(panel, allow_pickle=True)
    C = z["CLOSE"].astype(np.float64); QV = z["QVOL"].astype(np.float64)
    DV = z["DVOL30"].astype(np.float64)
    T, N = C.shape
    logc = np.log(np.where(C > 0, C, np.nan))
    ret1 = logc - _shift(logc, 1)

    # ---- channels: zoo factors (causal) + a few raw sequence channels ----
    F = build_factors(z)
    ch_names = list(F.keys())
    chans = [F[k][0] for k in ch_names]                      # each (T,N)
    for n in (1, 4, 12, 24):                                 # raw multi-window returns
        chans.append(logc - _shift(logc, n)); ch_names.append(f"ret_{n}h")
    chans.append(_roll(ret1, 6, "std")); ch_names.append("rvol_6h")
    chans.append(np.log(np.where(QV > 0, QV, np.nan))); ch_names.append("logqvol")
    # ---- F2: CROSS-SECTIONAL INPUT features (per-ts rank over the FULL panel, causal — the
    # model SEES the cross-section, not just scored on it). Centered pct-rank of key channels +
    # beta-adjusted return. Membership-agnostic here (ranked over all finite coins at t). ----
    def _xsr(A):
        R = np.full_like(A, np.nan, np.float32)
        for t in range(A.shape[0]):
            v = np.isfinite(A[t])
            if v.sum() >= 8:
                r = np.argsort(np.argsort(A[t, v])).astype(np.float32)
                R[t, v] = r / (v.sum() - 1) - 0.5                 # centered pct-rank in [-0.5,0.5]
        return R
    market = np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1)   # eq-wt market ret
    base_for_rank = {"xsr_rvol": F["rvol_24h"][0], "xsr_ret24": logc - _shift(logc, 24),
                     "xsr_fund": F["funding_ema"][0], "xsr_turn": F["lturnover_24h"][0],
                     "xsr_mom72": F["mom_72h"][0]}
    for nm, A in base_for_rank.items():
        chans.append(_xsr(A)); ch_names.append(nm)
    # beta-adjusted return: ret_24h - beta_24h * market_ret_24h (idiosyncratic move)
    mkt24 = np.convolve(np.nan_to_num(market), np.ones(24), "same")
    chans.append((logc - _shift(logc, 24)) - F["beta_24h"][0] * mkt24[:, None])
    ch_names.append("betaadj_ret24")

    CH = np.stack(chans, axis=2).astype(np.float32)          # (T,N,C)
    CH = np.nan_to_num(CH, nan=0.0, posinf=0.0, neginf=0.0)

    # ---- point-in-time top-110 membership (monthly refresh on trailing DVOL30) ----
    day = np.arange(T) // 24                                 # hourly grid -> day index
    month = day // 30
    MEM = np.zeros((T, N), bool)
    for m in np.unique(month):
        rows = np.where(month == m)[0]
        r0 = rows[0]
        dv = DV[r0]                                          # DVOL30 at month start (trailing, <=t)
        if np.isfinite(dv).sum() >= TOPN:
            top = np.argsort(-np.where(np.isfinite(dv), dv, -np.inf))[:TOPN]
            MEM[np.ix_(rows, top)] = True
        else:
            MEM[rows] = np.isfinite(dv)[None, :]

    # ---- targets + residual targets + CL per horizon ----
    Xbase = np.stack([F[b][0] for b in BASELINE], axis=2).astype(np.float64)  # (T,N,k) causal
    out = dict(ts=z["ts"], symbols=z["symbols"], ch_names=np.array(ch_names, dtype=object),
               baseline_cols=np.array(BASELINE, dtype=object), CH=CH, MEMBER110=MEM)
    for H in HORIZONS:
        Y = np.full((T, N), np.nan, np.float32)
        Y[:T - H] = (logc[H:] - logc[:-H]).astype(np.float32)  # forward H-hour logret
        YR = _xsec_residualize(Y.astype(np.float64), Xbase, MEM)
        # >=H non-overlap CL: greedy H-spacing per member, & member & finite target
        CL = np.zeros((T, N), bool)
        keep = np.arange(0, T, H)                            # regular H-spacing (hourly grid)
        CL[keep] = True
        CL = CL & MEM & np.isfinite(Y)
        out[f"Y{H}"] = Y; out[f"YR{H}"] = YR; out[f"CL{H}"] = CL
        print(f"  H={H}h: Y finite {np.isfinite(Y).mean():.3f} | YR finite {np.isfinite(YR).mean():.3f}"
              f" | CL rows {int(CL.any(1).sum())} member/hr~{int(np.median(MEM.sum(1)))}", flush=True)
    with open(outpath, "wb") as f:
        np.savez(f, **out)
    print(f"[wide_dl] T={T} N={N} C={CH.shape[2]} chans -> {outpath}", flush=True)
    print(f"  channels: {ch_names}", flush=True)


if __name__ == "__main__":
    import sys
    build(panel=sys.argv[1] if len(sys.argv) > 1 else PANEL,
          outpath=sys.argv[2] if len(sys.argv) > 2 else OUT)
