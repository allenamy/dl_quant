> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册, 判据冻结先于任何条件化数字 | **作废条件:** G0 平价门失败, 或 v4 链定义被更正

# PREREG · Track F — regime-conditional BOOK FORM (v4 caliber)

## §0 Instrument and parity (G0) — ALREADY PASSED before any candidate number
Mirrored replay tree `/workspace/uplift_2026-09-11/trackF/dev_v4F/` (symlinks to the frozen dev_v4 inputs;
frozen artifacts never written). Device = byte copy of `w10_health.py` sha256
`8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d`.
G0: rerunning A0_dyn_s42 in the mirror must reproduce the frozen artifact BITWISE on
`d30_n2_c42_rec`, `d30_n2_c42_W`, `legs_{king,rev24,fund}`. **PASSED (maxabs 0.0 on all six arrays).**
Yearly reproduction of the v4 doc's A0 table from that artifact: 2022 +0.0357 / 2023 -0.6248 /
2024 +0.5597 / 2025 +0.7627 / 2026->08-10 +3.7313 bps/anchor/gross; frozen window +1.8937, Sharpe 3.043.

## §1 Regime definition — FROZEN, mechanism-first, ex-ante
Two axes, chosen for MECHANISM, not for fit:
- `sig_fund` = cross-sectional sd of the 8h-equivalent funding rate over the anchor's member set
  (bps). It is the raw material of the funding-momentum leg, which is ~77% of the deployed book.
- `disp24`  = cross-sectional sd of trailing 24h returns over the same member set. It is the raw
  material of ANY cross-sectional price leg: book P&L per anchor ~ IC x dispersion, while cost and
  carry are close to dispersion-independent.
Both are computed at anchor i from panel row j(i) only (funding known at the anchor; `f_rev_24h`
is the trailing 24h return already used as the reversal leg's score). No forward data.
**Label**: L(i) in {LL, LH, HL, HH} by comparing each variable to its EXPANDING-WINDOW median over
anchors strictly before i (burn-in 2190 anchors = 1 year; before that the label is `WARM`).
Parameter budget: 2 variables, 2 thresholds, and the thresholds are not chosen — they are the
running median. No tuning knob is fitted to returns.

## §2 Candidate forms — FROZEN LIST (K = 4 candidates; multiple-testing correction stated)
- **R0 = A0** (in-service form): LEGS=101, trailing-900-anchor msharpe seat, PHI=0.45, FTRIM=zero.
- **R1 REGIME SEAT**: identical to A0 except the seat window is "the most recent 900 PAST anchors
  carrying the CURRENT regime label" instead of the most recent 900 past anchors. Mechanism: leg
  efficacy is a function of market state; a calendar window is a lagging proxy for state.
- **R2 REGIME SEAT + rev24 restored** (LEGS=111 under the R1 seat): lets the regime seat switch the
  reversal leg on in the states where it earned, and off elsewhere (max(sharpe,0) does this).
- **R3 REGIME HORIZON**: EMA coefficient 0.10 -> 0.20 in the HIGH-`disp24` states, 0.10 elsewhere
  (a faster book where dispersion pays for the turnover), seat unchanged from A0.
- **R4 = R1 + R3** (only if both R1 and R3 individually clear G2).
K = 4 pre-declared candidates (R4 conditional). Bonferroni-corrected two-sided alpha = 0.05/4 = 0.0125,
i.e. a candidate's A-verdict needs the 98.75% block-bootstrap interval of (candidate - A0) above 0.

## §3 Acceptance gates — FROZEN BEFORE THE NUMBERS
Judged with the frozen judge definition: g = net_ex/gross_total, bps/anchor/unit gross, arm
`d30_n2_c42`, CRYPTO m1 mask, UTC-day block bootstrap 2000 resamples, base seed 20260905 with
substream [20260905, k]. Both DL seeds s42 and s2027.
- **G1 RESOLUTION**: point estimate of (candidate - A0) on the frozen window 2025-03-01 -> 2026-08-10 20Z
  must exceed +0.23 bps/anchor (the window's bootstrap resolution). Below that it is NOT a result.
- **G2 SIGNIFICANCE**: the Bonferroni 98.75% CI lower bound of (candidate - A0) on the frozen window
  must be > 0 on BOTH seeds. (A) otherwise (C) UNDECIDED — never "non-inferior".
- **G3 CROSS-REGIME (the user's actual ask, PRIMARY for Track F)**: all of
  (a) no negative year in 2022, 2023, 2024, 2025, 2026->08-10 at v4 caliber;
  (b) Sharpe on 2024-01 -> 2026-08-10 20Z strictly greater than A0's 2.47;
  (c) frozen-window Sharpe >= 3.0;
  (d) the WORST calendar year's annualised Sharpe >= 1.0.
  G3 is reported with SE(annualised Sharpe) ~ sqrt(2190/N).
- **G4 LEAKAGE**: (i) every regime label at anchor i is a function of panel rows <= i only —
  asserted by recomputing the label series after randomly permuting all panel rows > i and
  requiring the label at i to be bitwise unchanged; (ii) the seat at anchor i uses only leg
  returns with index < i; (iii) expanding medians use strictly < i.
- **G5 HONESTY**: 2022-2023 are the years the regime rule has the least burn-in; the rule's
  in-sample/out-of-sample split is reported as: labels and seats are walk-forward by construction,
  but the CHOICE of the two regime variables was made after seeing the A0 yearly table, so the
  whole-history number is quoted as SEMI-OUT-OF-SAMPLE and a strict hold-out is reported separately
  (rule frozen on 2022-2024, evaluated on 2025-01-01 -> 2026-08-10 only).
- A candidate that clears G1+G2 but fails G3 is reported as an uplift candidate, NOT as a Track F
  answer. A candidate that fails G1 is reported as NOT A RESULT regardless of its Sharpe.

## §4 What would falsify Track F's premise
If, per regime cell, NO available form (any leg subset, either horizon, either seat rule) has a
positive mean g with a CI excluding 0, then that cell has no profitable form in the current arsenal
and it caps the cross-regime Sharpe. Naming those cells is a deliverable in its own right and is
reported even if every candidate fails.

## §5 AMENDMENT 1 (written BEFORE any candidate book-layer number is read)
Diagnostic finding that forces an amendment (receipt: coverage scan of
`/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy`, `SLOW_v4.npy` and
`dev_alt/pod_backup_2026-08-21/slow_pred_hist_oos.npy` -> `/workspace/shadow_bundle_v3/slow_pred_pinned.npy`):
**the king OOS prediction file has ZERO finite values in 2022 and 2023** (anchors with >=10 finite
names: 0 in 2022, 0 in 2023; 2196/2190/1452 in 2024/2025/2026). The DL (F10) prediction file is zero
in 2022 and present from 2023. In the replayed book the DL leg sits in the KING SLOT and carries the
KING SEAT weight `w3_king`; with king's leg returns identically 0 in 2022-23 the msharpe seat sets
`w3_king -> 0`, which silences the DL leg as well. Consequence: the v4 A0 yearly rows for 2022 and
2023 are NOT the in-service three-source form — they are the funding leg essentially alone.
Two candidates are therefore ADDED to §2 before any of their numbers are read:
- **F1 DECOUPLED DL SEAT**: `SEATF10=1` (the device's existing T1 knob) — the DL book gets its own
  msharpe seat from its own leg returns instead of borrowing king's. Mechanism: a leg's weight must
  depend on that leg's own evidence; coupling it to another leg's seat makes the leg unavailable
  exactly when the other leg is unavailable.
- **F1R = F1 + the R1 regime seat.**
K becomes 6 (R1, R1b(LOOK_R=300 sensitivity), R2, R3, F1, F1R; R4 dropped). Bonferroni two-sided
alpha = 0.05/6 = 0.00833 -> the A-verdict needs the 99.17% bootstrap interval of (candidate - A0)
above 0 on both seeds. All other gates in §3 are unchanged.
