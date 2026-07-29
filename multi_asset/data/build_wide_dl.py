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
import os.path as _p
import sys as _sys
import numpy as np
_sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))  # runnable w/o PYTHONPATH
_sys.path.insert(0, _p.join(_p.dirname(_p.dirname(_p.abspath(__file__))), "exports", "eda"))
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
        # STANDARDIZE columns before the ridge-OLS so the (tiny) ridge shrinks all baselines
        # UNIFORMLY — otherwise a large-scale/heavy-tailed col (funding_ema) is under-shrunk and
        # leaves a residual loading (0C leak-audit found 0.042 on funding_ema). Scaling is a
        # per-col invertible transform, so residual-orthogonality to the standardized cols ==
        # orthogonality to the raw cols -> airtight incremental-over-[funding+zoo].
        sd = Xt.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
        Xt = Xt / sd
        # ridge-stabilised OLS (k small vs n~110): beta = (X'X + lam I)^-1 X'y
        XtX = Xt.T @ Xt + 1e-6 * np.eye(Xt.shape[1])
        beta = np.linalg.solve(XtX, Xt.T @ y)
        R[t, v] = (y - Xt @ beta).astype(np.float32)
    return R


def build(panel=PANEL, outpath=OUT, caliber=None, caliber_why=None):
    """`caliber` is the CALLER'S DECLARATION of which funding caliber this build is meant to produce
    ("as_trained" / "corrected"), written into the output as a stamp the artifact carries.

    ★ IT IS DECLARED, NOT DETECTED, AND THAT IS THE POINT (0C 2026-07-29). This function cannot
      determine the caliber from its own inputs — the funding dimension comes from the raw panel's
      `FUND_EMA` upstream. If it stamped what it MEASURED, the gate below would compare a
      measurement against itself and pass forever: a tautology wearing a guard's clothes. The stamp
      says what the caller INTENDED; `assert_funding_dim` measures what came out; the two must
      agree. That disagreement is the entire detector — it is how a silent upstream re-calibering
      (e.g. a rebuilt `wide_panel_full.npz` carrying the 2026-07-25 fix into a live splice that is
      supposed to stay as-trained) becomes visible instead of invisible.
    """
    import panel_caliber_stamp as _PCS                      # noqa: E402 (path set at import below)
    if caliber not in _PCS.CALIBERS:
        raise SystemExit(
            f"[wide_dl] REFUSING TO BUILD: caliber must be declared as one of {_PCS.CALIBERS}, got "
            f"{caliber!r}.\n"
            f"  The panel this writes is a FROZEN MODEL'S INPUT. Which funding caliber it carries "
            f"decides whether the heads are fed the distribution they were fitted on, and this "
            f"build cannot infer that from its own arguments — the caller is the only party that "
            f"knows what it is producing.\n"
            f"  Pass caliber='as_trained' (matching the frozen heads) or 'corrected' (the "
            f"settlement-interval-normalised factor leg), plus caliber_why explaining which and "
            f"why. See exports/eda/panel_caliber_stamp.py.")
    if not caliber_why:
        raise SystemExit("[wide_dl] REFUSING TO BUILD: caliber_why is required — a stamp without a "
                         "reason is a label, and the reason is what lets a later reader tell a "
                         "deliberate state from a leftover.")
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
    # the caliber stamp travels INSIDE the artifact — see the docstring: declared here, measured by
    # the gate below, and the two are required to agree.
    out.update(_PCS.make(caliber, f"{_p.basename(__file__)}::build", caliber_why))
    with open(outpath, "wb") as f:
        np.savez(f, **out)
    print(f"[wide_dl] T={T} N={N} C={CH.shape[2]} chans -> {outpath}", flush=True)
    print(f"[wide_dl] caliber stamp: DECLARED {caliber} ({caliber_why})", flush=True)
    print(f"  channels: {ch_names}", flush=True)

    # ---- HARD GATE: funding settlement-interval dimension regression check ----
    # funding_ema stores a per-settlement rate; 4h- and 8h-settled coins coexist, and the engine
    # rank-centres the funding cross-section. Rank-centring removes individual scale but NOT a
    # group-level shift, so an un-normalised rate silently biases the 4h cohort to one side --
    # and xsr_fund (derived here from funding_ema) carries the identical artifact. "Fixing the
    # source fixes the derived channel" is an assumption about this build graph, so it is CHECKED,
    # not trusted. Non-zero exit deliberately breaks the build.
    import subprocess
    rc = subprocess.call([_sys.executable,
                          _p.join(_p.dirname(_p.dirname(_p.abspath(__file__))),
                                  "exports", "eda", "assert_funding_dim.py"),
                          "--panel", outpath])
    if rc != 0:
        raise SystemExit(f"[wide_dl] FUNDING DIMENSION GATE FAILED (exit {rc}) on {outpath} — "
                         "panel NOT fit for use. See exports/eda/assert_funding_dim_result.json; "
                         "fix is rate*(8/interval_h_of_that_row) BEFORE the EMA in "
                         "data/build_wide_panel.py.")
    print("[wide_dl] funding-dimension gate PASSED", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("panel", nargs="?", default=PANEL)
    ap.add_argument("outpath", nargs="?", default=OUT)
    # ★ REQUIRED, no default. A default here would be a path rule wearing a flag: whoever runs this
    # from a shell is exactly the caller who might be rebuilding the training panel, and that is the
    # rebuild that must never inherit an expectation it was not asked to satisfy.
    ap.add_argument("--caliber", required=True, choices=["as_trained", "corrected"],
                    help="which funding caliber THIS build is meant to produce (stamped into the "
                         "output; the gate then measures whether it did)")
    ap.add_argument("--caliber-why", required=True,
                    help="why this build carries that caliber (recorded in the stamp)")
    a = ap.parse_args()
    build(panel=a.panel, outpath=a.outpath, caliber=a.caliber, caliber_why=a.caliber_why)
