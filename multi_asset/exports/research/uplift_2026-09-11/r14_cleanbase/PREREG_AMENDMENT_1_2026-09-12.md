> **created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** AMENDMENT 1 to PREREG sha 89ba6e7d87d79866d78f7a95400ee13b21b7d0d511dfc82f6ce7b509ca956fe7 | **invalidated by:** the parent prereg being invalidated

# PREREG AMENDMENT 1 — arm A12 (XIB_LAG50) was the WRONG FILE. Identity corrected; K unchanged.

## What happened

The parent prereg named A12 as "XIB_LAG50 (r13A archived arm, `XIB_LAG50_s42__REAL.npz`)". I picked that
file because of its name. Its `config_json` shows `FEMAT_NPZ = r3_placebo/dev/sig/XIB_LAG50_s42__REAL.npz`
— it is the **placebo family's REAL arm**, a re-derivation of the signal built for the r3 placebo battery.

The arm the programme's `rho = 0.8891` claim is actually about is the **r3 XIB screen's own arm**,
`r3_xib/arms/w10_ablation_series_R3_XIBLAG50_dyn_s42.npz` (`FEMAT_NPZ = r3_xib/dev/sig/XIBLAG50.npz`),
correlated against that screen's own fee-plane control `R3_A0_dyn_s42`.

This was caught by the reconciliation device `devices/r14_xib_recon.py`, which was run BECAUSE my A12
rho did not reproduce the archived number — the desk's "two instruments disagree -> reconcile first" rule.
It is the E-0825-H form (semantics inferred from a filename), committed by me, in this round.

## The correction

- **A12 := `R3_XIBLAG50_dyn_s42`** (pod2 sha `d364e00313959ad9ed8dab9bc2814015c12f34649e667f2cbd3331543bb3fa5b`),
  carried into the repo as `receipts/r14_XIB_r3screen_s42.npz`.
- The mis-picked arm is reported as a **DISCLOSURE row named `XIB_LAG50_placeboREAL`**, OUTSIDE SET A.
  It is not counted in any SET A distribution, band count, or median.
- **K is unchanged at 41.** No candidate is added; one candidate's file identity is corrected.
- Every threshold and every band in the parent prereg §6 stands unchanged.

## Disclosure of what was seen before the amendment

The wrong-file rho values had already been computed when the error was found:
`XIB_LAG50_placeboREAL` rho_FULL +0.8555, rho_CLEAN +0.8790, band REWEIGHTING on both samples. The
correction therefore cannot change the band of A12 in a way that was chosen: both files sit far above the
0.60 line. Recorded so the amendment cannot be read as threshold-shopping.
