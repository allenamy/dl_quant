> **创建:** 2026-09-11 (Track G agent, round 2) | **Session:** session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册 — 判据与 K 冻结先于任何数字 | **作废条件:** GATE P 不逐位通过, 或 v4 树/装置被推翻

# PREREG · Track G — EVENT AND STATE CONDITIONING sleeves, v4 caliber

## 0 GATE P (run and passed BEFORE any feature was built)
`/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`,
all six knobs unset, run in a fresh mirror tree `/workspace/uplift_2026-09-11/dev_v4ev/`
(pod_backup symlinked to dev_v4s's = meta `meta_newprod_v4.npz`, panel `wide_panel_4h_v2ext.npz`,
king `SLOW_v4.npy`), env verbatim from `run_v4_arms.sh` arm A0.
Result: `d30_n2_c42_rec` (10039,23) and `d30_n2_c42_W` (10039,829) are **sha256-identical** to the
archived `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}.npz` on all four arms. **GATE P PASS, bitwise.**

## 1 Device and readout (frozen)
- sleeve arm: `LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=<signal>` + COMMON
  `CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 UMASK_NPZ=masks/umask_UPIT_CRYPTO.npz
   COSTB_JSON=calib/costb_fee_steady.json SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy`
- readout `g = net_ex/gross_total`, judge_v4's frozen definition, bps/anchor per unit gross
- windows: full cycle 2022-01-31 -> 2026-08-31 (n=10039, the panel axis; stated explicitly),
  frozen 2025-03-01 -> 2026-08-10 20Z, 2024-on, ext 2026-08-11 -> 2026-08-31 (n=121 anchors)
- bootstrap: UTC-day block, 2000 resamples, `np.random.default_rng([20260905, k])`
- baseline A0 = the GATE P artifact (bitwise = archived)

## 2 Feature construction — CAUSAL, stated to the bar
5m source = `dlnative_5m_wide829_f16_holefix2.npz` ONLY (ch `ret5`, bar-STARTING convention).
Funding settlements from `/workspace/fund_aug.json.gz` (sha256 8a9e7715…), interval truth cross-checked
against panel `f_fund_iv`.
**Settlement-window drift** for a settlement at time S: `dr = prod(1+ret5)-1` over the 7 bars starting at
S-10m … S+20m, i.e. the window `[S-10m, S+25m)`.
**CAUSALITY RULE (the round-1 lesson applied):** at anchor E a settlement contributes only if
`S + 25min <= E`, i.e. `S <= E - 1800s`. Because settlements and anchors are both on :00 boundaries, the
newest usable settlement is at `E - 1h` at the latest. **No bar at or after E is ever read.**

### Arms (both signs unless stated)
Batch G1 — settlement-window state (K += 8)
- `SWDRIFT`  = dr of the newest usable settlement
- `SWRESID`  = dr - b_S * rn8, b_S = per-settlement-time cross-sectional OLS slope of dr on the
  8h-normalised settled rate rn8; the settlement-window move NOT explained by the funding transfer
- `SWRESID3` = mean of SWRESID over the last 3 usable settlements
- `SWABS`    = mean |dr| over the last 3 usable settlements (settlement-window turbulence)

Batch G2 — venue funding-state events (K += 4)
- `CAPPIN`   = fraction of the last 6 usable settlements with |raw rate| at/near the venue cap; the cap
  value is read off the atoms of the raw-rate histogram (a data-definition step, fixed before any book number)
- `IVSWITCH` = -log2(f_fund_iv[E] / f_fund_iv[E-42 anchors]); positive = the venue SHORTENED this name's
  funding interval in the last 7 days (a venue-declared stress state)

Batch G3 — listing event (K += 2)
- `LISTEVT`  = exp(-age/42), age = anchors since the name's first finite y4 in the v4 meta (era-synchronous,
  causal by construction). This is the EVENT form, distinct from Track D's YOUNGFUND universe SLICE.

Batch G4 — orthogonalised residual sleeves (K += 6)
- for the three G1-G3 arms with the highest full-cycle Sharpe (selection rule declared here, before the
  numbers), `signal' = rank(signal) - beta_i * rank(f_fund_ema_v1)`, beta_i = per-anchor OLS slope. Both signs.

**K_declared = 20.** Bonferroni level for S6 = 0.05/20 (two-sided 99.75%).

## 3 Gate S (identical to Track D's, so the two tracks are comparable)
- S1 standalone: full-cycle mean g > 0 AND annualised Sharpe >= 1.0
- S2 cross-regime: >= 4 of 5 year buckets (2022/2023/2024/2025/2026->08-31) mean g > 0
- S3 diversification: |corr(g_sleeve, g_A0)| <= 0.30 on BOTH the frozen window and 2024-on;
  the TASK's stricter bar (|corr| <= 0.25 on the FULL CYCLE) is reported separately and is what counts
- S4 portfolio value: 50/50 equal-gross blend with A0 raises full-cycle Sharpe by >= +0.20 and raises the
  worst year
- S5 resolution: full-cycle bootstrap CI95 excludes 0 AND |mean g| > 0.23 bps/anchor
- S6 multiple testing: leader must clear the Bonferroni(K=20) interval; otherwise EXPLORATORY
- S7 leakage: offset spectrum corr(signal rank at i, y4 at i+k), k in [-4,+4], must peak at k=0 with no
  larger |value| at k<0
- S8 carry decomposition (round-1 methodology (d)): report `carry_ex/net_ex`; an arm whose net is mostly
  carry belongs to the already-closed carry axis, not to alpha
- Placebos (mandatory for any arm reaching S5): per-anchor PERMUTED feature, and the orthogonalisation
  operator applied to a permuted rank

## 4 Non-arm measurements (reported, not gated, not part of K)
- (i) settlement-anchor phase: the 4h grid has 3 of 6 anchors coinciding with 8h settlement — report A0's
  net split by phase (a state diagnostic, not a sleeve)
- (ii) delisting: the last 180 anchors before a name's disappearance. ORACLE / non-causal by construction
  (we have no announcement archive); reported only to SIZE the prize, never as a deployable arm
- (iii) universe: what the names outside the frozen 450 contribute, via the device's own MEMBERS_TOPN /
  TRADE_TOPN separation
- (iv) venue-constraint states (-5022 / -2027): live executor logs only; the deliverable is the EVENT COUNT
  and the statement of whether it is backtestable at all

## 5 Declared in advance
- Nothing here promotes anything. `ELIGIBILITY_CONTRACT.json`'s `BUNDLE_export.approved_source_sha256` is an
  empty list, so every reading below is EXPLORATORY by construction.
- For every event arm the binding sample size is the NUMBER OF EVENTS, not the number of anchors; it is
  reported for each.
- A family with nothing in it is a real result.
