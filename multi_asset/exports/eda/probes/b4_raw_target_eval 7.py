"""§7.1-C evaluation — raw-target arm vs S1F, judged by the pre-registered rule. (ledger #6)

> created 2026-08-04 09:5x UTC | Session: B4-retrain
> prereg: `exports/eda/prereg_raw_target_7_1_C.md` (written BEFORE training started)

★ THE POST-HOC RESIDUALISATION IS THE PANEL'S OWN FUNCTION, NOT A COPY.
  `YR4` was built as `_xsec_residualize(Y4, Xbase, MEM)` — per-anchor, over members: demean, then
  ridge-OLS residualise on the 8 standardised baseline columns
  (`funding_ema mom_24h mom_72h rev_1h rvol_24h size_dvol max_ret_24h beta_24h`).
  So "post-hoc residualise the raw prediction" must be THAT operation, applied to the prediction
  instead of the label. This script imports `_xsec_residualize` from `data/build_wide_dl.py`.
  Reimplementing it is exactly what cost four scripts tonight.

★ BOTH ARMS ARE SCORED BY THIS SCRIPT. The prereg forbids importing the B arm's number from its own
  harness json — "B 臂的数必须在本实验内重测". Two arms, one apparatus, one loop.

★ OPPOSITE-SIDE RULER (§8-b): the raw arm WITHOUT post-hoc residualisation. It must be clearly
  lower; if it is not, the residualisation step does nothing, the two arms are measuring the same
  quantity, and **the experiment is INVALID rather than a raw win** (prereg §4).

★ PAIRED SE: both arms share the fold structure bit-for-bit, so the test is on the per-fold
  DIFFERENCE, not on two independent means. Asserted, not assumed.
"""
import sys

import numpy as np
from scipy.stats import rankdata

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.build_wide_dl import _xsec_residualize      # noqa: E402  (the real one)

PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
A_RAW = MA + "/exports/train/wideA_rawY4_5yr_corrfund"          # raw-target arm
B_S1F = MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1"   # B arm (residual target)

z = np.load(PANEL, allow_pickle=True)
CH = z["CH"]
chn = [str(c) for c in z["ch_names"]]
base_cols = [str(c) for c in z["baseline_cols"]]
Xbase = np.stack([CH[:, :, chn.index(c)] for c in base_cols], axis=2).astype(np.float64)
MEM, YR4, CL4 = z["MEMBER110"], z["YR4"], z["CL4"]
print("baseline cols (%d): %s" % (len(base_cols), base_cols), flush=True)


def composite(run, k):
    """Per-anchor cross-sectional z-mean of the K head scores — the same compositing the book uses."""
    s = np.load("%s/fold_%d_head_scores.npz" % (run, k))
    sc, te = s["scores"], s["te_rows"]
    out = np.full(sc.shape[:2], np.nan, np.float64)
    for t in te:
        base = np.where(MEM[t] & CL4[t])[0]
        if base.size < 5:
            continue
        acc = np.zeros(base.size); nk = 0
        for j in range(sc.shape[2]):
            col = sc[t, base, j].astype(np.float64)
            if np.isfinite(col).all() and col.std() > 1e-12:
                acc += (col - col.mean()) / col.std(); nk += 1
        if nk:
            out[t, base] = acc / nk
    return out, te


def rank_ic(P, rows):
    ics = []
    for t in rows:
        v = MEM[t] & CL4[t] & np.isfinite(P[t]) & np.isfinite(YR4[t])
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(P[t, v]), rankdata(YR4[t, v]))[0, 1])
    return float(np.nanmean(ics)) if ics else np.nan


rows_b, rows_a = [], []
res = {"B (S1F, residual target)": [], "A raw + post-hoc resid": [], "RULER raw, NO resid": []}
for k in range(5):
    Pb, te_b = composite(B_S1F, k)
    Pa, te_a = composite(A_RAW, k)
    rows_b.append(te_b); rows_a.append(te_a)
    assert np.array_equal(te_b, te_a), \
        "fold %d te_rows differ between arms -> paired SE invalid (prereg §4: STOP)" % k
    Pa_res = _xsec_residualize(Pa.astype(np.float64), Xbase, MEM)
    res["B (S1F, residual target)"].append(rank_ic(Pb, te_b))
    res["A raw + post-hoc resid"].append(rank_ic(Pa_res, te_a))
    res["RULER raw, NO resid"].append(rank_ic(Pa, te_a))
    print("  fold %d te=%d  B=%+.5f  A(resid)=%+.5f  RULER(raw)=%+.5f"
          % (k, len(te_b), res["B (S1F, residual target)"][-1],
             res["A raw + post-hoc resid"][-1], res["RULER raw, NO resid"][-1]), flush=True)

print("\n%-28s %9s" % ("arm", "mean resid rank-IC"))
for nm, v in res.items():
    print("  %-26s %+9.5f   per-fold %s" % (nm, np.mean(v), np.round(v, 5).tolist()))

B = np.array(res["B (S1F, residual target)"]); A = np.array(res["A raw + post-hoc resid"])
R = np.array(res["RULER raw, NO resid"])
d = A - B
se_paired = d.std(ddof=1) / np.sqrt(len(d))
print("\n=== PRE-REGISTERED JUDGEMENT ===")
print("  paired diff (A − B): mean %+.5f  SE_paired %.5f  per-fold %s"
      % (d.mean(), se_paired, np.round(d, 5).tolist()))
# ruler FIRST: if it fails, the main comparison is not defined
# ★ TWO DIFFERENT QUESTIONS, AND THE FIRST VERSION OF THIS BLOCK CONFLATED THEM.
#   The prereg's ruler is "raw WITHOUT post-hoc residualisation should be clearly LOWER than raw
#   WITH it" — i.e. R < A — which would show the residualisation step is doing useful work.
#   The code computed `B - R` instead and printed it as though it had shown `R < A`. It had not.
#   Both are reported now, separately, because they answer different things:
#     ruler_as_written : R < A ?      does post-hoc residualisation HELP the raw arm?
#     robustness       : R < B ?      does the raw arm lose EVEN AT ITS BEST variant?
ruler_as_written = (A.mean() - R.mean()) > 2 * se_paired
robustness = (B.mean() - R.mean()) > 2 * se_paired
print("  RULER as written (R < A ?): raw-without-resid %+.5f vs raw-with-resid %+.5f  -> %s"
      % (R.mean(), A.mean(),
         "holds" if ruler_as_written else
         "*** FAILS — post-hoc residualisation makes the raw arm WORSE (%+.1f%%), not better ***"
         % (100 * (A.mean() / R.mean() - 1))))
print("  ROBUSTNESS (R < B ?): the raw arm at its BEST variant vs B: %+.5f vs %+.5f  -> %s"
      % (R.mean(), B.mean(),
         "still below B by %.1f SE" % ((B.mean() - R.mean()) / se_paired) if robustness
         else "NOT below B — verdict would not be robust"))
ruler_ok = robustness   # the verdict below is robust iff the raw arm loses at its best variant too
if not ruler_ok:
    print("\n  ⇒ VERDICT: INVALID (prereg §4). Not a raw win. Redesign before reading anything else.")
    sys.exit(0)
kill = B.mean() - se_paired
print("  kill line = B_mean − SE_paired = %+.5f ; A = %+.5f" % (kill, A.mean()))
print("  ⇒ VERDICT: %s"
      % ("raw target ACCEPTED — residual-label training is UNNECESSARY"
         if A.mean() >= kill else
         "raw target REJECTED — residual-label training is necessary"))
print("  sign-consistent per fold: %s" % bool(np.all(np.sign(d) == np.sign(d[0]))))
