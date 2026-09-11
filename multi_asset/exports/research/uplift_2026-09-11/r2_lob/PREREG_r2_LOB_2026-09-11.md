> **创建:** 2026-09-11 | **Session:** round-2 LOB sleeve hunt | **状态:** PREREG (frozen before any performance number) | **作废条件:** v4 caliber pin changes, or /workspace/lob_npz is rebuilt

# PREREG — Round 2, microstructure / order-book sleeve family

## GATE P (run BEFORE anything)
`/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 b88e35a46b93d712, all six knobs off, cwd
`/workspace/uplift_2026-09-11/dev_v4s`, env = COMMON of run_v4_arms.sh. Must reproduce
`/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}.npz`
`d30_n2_c42_rec` AND `d30_n2_c42_W` bitwise. **RESULT: PASS, 4/4, rec+W+S0_rec all True, shape (10039,23).**

## Data surface
`/workspace/lob_npz` 811 files, 28 GB. Schema `ts`(int64, ~30 s), `lnot`(n,12) float16, `ldep`(n,12), `bands`
= [-5,-4,-3,-2,-1,-0.2,0.2,1,2,3,4,5] (% from mid). VERIFIED: `lnot` is **cumulative** log notional out to |d|%
(monotone in |d| on 100% of sampled rows, min increment >= 0, 4 symbols x 750 rows).
VERIFIED: `lnot - ldep` = log(price) => `ldep` carries no information beyond `lnot`; only `lnot` is used.
VERIFIED: raw ts span 2023-01-01 00:06:05Z .. 2026-08-23 23:59:32Z => **there is no 2022 LOB data at all**.
VERIFIED: the +-0.2% touch band is NaN for a price/tick-dependent subset of names (BTC 0.00, FTM 0.00, ZRX 0.16,
AZTEC 1.00) => the touch band is NOT usable as a universal cross-sectional feature; its missingness is itself a
relative-tick-size tilt. The touch band is DROPPED from the prereg.

## What round 1 already closed in this family (do not repeat)
LOBIMB1 / LOBIMB5 / LOBIMB1D (7d innovation of the ratio) / LOBSLOPE = no alpha; LOBDEPTH (level) works but
corr 0.79-0.83 with amihud/asz = the same liquidity bet. All four were **window-mean statistics over [E-3600, E)**.
Round 2's hypothesis: the unexploited part of the book is the **time dimension inside the bar** (instability,
drift) and the **per-side shape** (asymmetric decay), not another window mean of a level.

## K DECLARATION — K = 24, declared before looking
8 feature families x 2 signs = 16 raw book-layer arms, + up to 8 per-anchor-orthogonalised arms (best sign only).
Bonferroni reported at K=24 (two-sided 95% => per-arm alpha 0.00208, z = 3.08) and also at K=8 (families).
Placebos are not candidates and are not counted in K.

## Window convention (locked)
Bar W(i) = [E_i - 14400, E_i) — the full 4h bar ending AT the anchor, causal, decision made at E_i.
Halves H1 = [E_i-14400, E_i-7200), H2 = [E_i-7200, E_i).
Guards: n(W) >= 120 (of an expected 480 at 30 s), n(H1) >= 40, n(H2) >= 40, else NaN.
LAG variants (feature value taken from anchor i-1) are produced by a pure shift and are tested only for
families that clear the raw screen — this is the round-1 Amihud intervention.

## The 8 families (locked definitions; Nd = expm1(clip(lnot,0,60)), S_d = N(-d)+N(+d))
per-row: r1 = log S_1 ; imb = (N(-1)-N(+1))/S_1 ; sl = [lnot(-5)-lnot(-1)] - [lnot(+5)-lnot(+1)] ;
cx = log S_4 - 2 log S_2 + log S_1 ; rb = log N(-1) ; ra = log N(+1)
1. **LDVOL**   = std(r1 over W)                       — liquidity instability / book fragility
2. **LIVOL**   = std(imb over W)                      — quote flicker (instability of imbalance, not its mean)
3. **LSLASY**  = mean(sl over W)                      — per-side depth-decay asymmetry, scale-free
4. **LDTREND** = mean(r1|H2) - mean(r1|H1)            — depth building vs draining inside the bar
5. **LCONVX**  = mean(cx over W)                      — book convexity at 1/2/4%
6. **LDINNOV** = mean(r1|W) - trailing-42-anchor causal mean of mean(r1|W), window [i-42, i) exclusive, >=10 finite
7. **LIMBINN** = [mean(rb|W) - trail42(rb)] - [mean(ra|W) - trail42(ra)]  — per-side depth innovation difference
8. **LDVOLR**  = LDVOL - trailing-42-anchor causal mean of LDVOL          — instability innovation

## Screen, in order (round-1 methodology (a)-(h), no step skipped)
(a) causal build as above; (b) per-anchor cross-sectional orthogonalisation against rank(f_fund_ema_v1);
(c) two placebos per admitted arm: per-anchor permuted feature, and the orthogonalisation operator on a permuted
rank; (d) net_ex = pnl_ex - carry_ex - cost_ex on every arm, report carry_ex/net_ex; (e) forward vs backward
rank-IC at k = 0, -1, -2; (f) per-year signs, monotone dose, windows {LOBFULL, frozen, 2024on, 2026-08-11..08-23};
(g) corr to A0 on the LOB-common span AND corr to ORTH_f_amihud_24h; (h) Bonferroni at K=24.

## SPAN RULE (forced by the data, declared before results)
No LOB feature can be evaluated on the 2022-01-31..2026-08-31 full cycle. The primary span for this family is
**LOBFULL = first anchor with usable LOB breadth .. 2026-08-10 20Z**, and A0 is re-measured on the SAME span for
every correlation and every comparison. The out-of-fit stress window is truncated at 2026-08-23 (raw data end),
n < 121. Any Sharpe quoted for this family is a SHORT-SPAN Sharpe and is labelled as such.

## ADMISSION BAR (frozen before results)
standalone Sharpe >= 1.5 on LOBFULL, |corr to A0 on LOBFULL| <= 0.25, |corr to ORTH_amihud| <= 0.40,
carry_ex/net_ex <= 0.40, both placebos <= 0, fwd IC(k=0) >= bwd IC(k=-1), >= 4/4 usable years positive,
CI95 of the full-span mean excludes 0.
