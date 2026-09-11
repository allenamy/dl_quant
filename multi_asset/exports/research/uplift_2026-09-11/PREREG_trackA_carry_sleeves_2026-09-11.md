# PREREG · TRACK A: stop paying carry you do not earn (v4 caliber)

> **created:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **status:** criteria FROZEN BEFORE ANY NUMBER | **void if:** the parity gate P fails, or the v4 basis paths change
> **caliber:** v4 chain 2026-09-09 ONLY. Replay tree `/workspace/review_scratch/health_check/dev_v4`, device `w10_health.py` (sha256 8684d9a9f43a8d15…), meta `meta_newprod_v4.npz` (RAW accounting), king `shadow_bundle_v4/slow_pred_pinned.npy`, F10 `f10_A0_s{42,2027}.npy` (in-service yearly OOS aligned to the v4 DL axis). CAL=log (NO expm1 — the pod lineage y4 is already Π(1+r5m)−1). Env verbatim = `run_v4_arms.sh` COMMON.
> **statistic:** g = net_ex / gross_total, bps/anchor per unit gross. Frozen window 2025-03-01 → 2026-08-10 20Z (3168 anchors). UTC-day block bootstrap, 2000 resamples, rng `default_rng([20260905, k])` — `boot()` copied verbatim from `judge_v4.py`. Bootstrap resolution on this window ≈ ±0.23 bps/anchor.
> **eligibility:** these arms are NOT candidates under `ELIGIBILITY_CONTRACT.json` (no BUNDLE_export gate exists). Every verdict below is EXPLORATORY / informational. A PROMOTE would need the physical export gate.

## GATE P — device parity (runs before any number)
`w10_sleeve.py` = `w10_health.py` + {LTRIM_TH, CDAMP, FTRIM_TH, SLEEVE}, all defaults off. Run it with the exact A0 dyn s42 env and SLEEVE=1; `d30_n2_c42_rec` and `d30_n2_c42_W` must be **bitwise identical** to the archived `w10_ablation_series_V4_A0_dyn_s42.npz`. Any difference ⇒ the device is void and no number from it may be quoted.
Second parity: the sleeve arrays must satisfy the identity Σ_sleeve pnl = pnl_ex, Σ carry = carry_ex, Σ cost = cost_ex per anchor to < 1e-7 (asserted in-device).

## GATE A — the deciding question (task item 2)
Sleeves: side(long/short) × current 8h-equivalent funding rate rn8 ∈ {≤−30bp, (−30,−10], (−10,0), [0,10), [10,30), ≥30bp, no quote} = 14 cells, classified per anchor on the **ex-caliber** book weights `smr` (the judge's numerator).
A sleeve is declared **CARRY-NEGATIVE** (i.e. shrinking it is free money) only if, on the frozen window, its own net contribution (pnl − carry − cost)/gross_total has a 95% block-bootstrap CI **entirely below 0 on BOTH seeds**. Anything else is reporting only.
**Falsifier of the whole track:** if for every sleeve the price alpha and the carry move together (|Δpnl| ≈ |Δcarry| when the sleeve is removed), then carry is *priced in* and Track A has no free money in it — say so.

## GATE B — book-variant admission (task item 3)
Arms (all dynamic seat, both seeds, dev_v4, everything else = A0):
- `NOFTRIM` FTRIM=off (the live FTRIM removed)
- `FT30` FTRIM_TH=−0.0030, `FT05` FTRIM_TH=−0.0005 (dose response on the live lever)
- `LT10/LT30/LT50` LTRIM_TH = 10/30/50 bp per 8h (long-side mirror: zero the longs that PAY the most carry)
- `CD05/CD1/CD2` CDAMP = 0.5/1/2 (alpha-per-unit-carry sizing: z ÷ (1 + λ·max(0, sign(z)·rn8)/10bp))
An arm is **ADMITTED** only if ALL hold:
1. Δg (arm − A0), frozen window, dynamic seat: 95% CI **lower bound > 0 on BOTH seeds**;
2. point estimate **> +0.23** bps/anchor/gross (the bootstrap resolution — smaller is not a result);
3. per-year Δg ≥ −0.30 bps/anchor for each of 2023 / 2024 / 2025 / 2026→08-10;
4. turnover_mean rises by ≤ +25% relative to A0 (cost is already inside net, this bounds capacity risk);
5. multiple testing: K = 9 arms are tested; the admission claim must name K and survive it. A result on one seed only is UNDECIDED, never "non-inferior".
Anything failing 1 or 2 is **NOT ADMITTED**. "CI contains 0" is reported as (C) UNDECIDED, never as equivalence.

## GATE C — FTRIM re-verdict at v4 (task items 4 and 5)
Report Δ(FTRIM=zero − FTRIM=off) at v4 caliber on the frozen window, both seats, both seeds, with the three-way mechanism split Δnet_ex = Δpnl_ex − Δcarry_ex − Δcost_ex (identity asserted). Verdict letters (A)/(B)/(C) per the judge's frozen rule.
Pre-registered reading: if Δcarry ≈ Δpnl (the carry saved equals the price P&L given up), then FTRIM is a **wash** and the 2026-08-30 DNR on the −10bp axis stands at v4 for the mechanism reason, not the sample reason. If Δnet CI is below 0, FTRIM is **live and negative** and that is a finding about the deployed book.

## Complexity budget
Every arm is ONE line of code at the z layer with ONE whitelisted constant. No new data, no new model, no new state. Leakage surface: `rn8` at anchor j is the last settled rate with fundingTime ≤ anchor (`pod_panel_ext.py` L153 searchsorted side="right" −1), the same object the live producer reads (`shadow_loop_v3.py` L296-321) — already causally audited in `PREREG_deploy_ftrim_2026-09-02` §7. No new leakage surface is introduced.

## AMENDMENT 1 (written after GATE A/B/C round 1, BEFORE the round-2 numbers)
Round 1 produced two facts that define two new arms. Both are **declared extensions of an already-registered family**, not a re-choice of the gate: GATE B is unchanged and K rises from 9 to 11.
1. **The FTRIM threshold dose-response is monotone** (NOFTRIM −0.11 < FT30 −0.05 < A0(−10bp) 0 < FT05 +0.05, both seeds, same sign in 2022/2023/2026). The family's shallow end has not been probed. New arm **`FT00`** = FTRIM_TH −0.00001 (trim EVERY short whose current funding is negative). Registered because the dose curve, not the level, points there.
2. **GATE A shows FTRIM's z-layer implementation is leaky**: the sleeves FTRIM is designed to empty still hold 2.41% of gross (S|≤−30bp 0.72% + S|−30..−10 1.69%) because the EMA (α 0.1) and the 2.5e-4 band leave a decaying residue — exactly what `PREREG_deploy_ftrim_2026-09-02` §8 predicted and accepted. S|−30..−10 is one of only two economically real carry-negative sleeves. New arm **`FTPOS`** = the same rule enforced at the POSITION layer (after the king/F10 blend `smb`, zero the residual short positions in the band and rescale to preserve L1 gross; the exit is traded and its cost priced). This is deployment-equivalent to an executor-side overlay.
Both arms are judged by the unmodified GATE B. Neither may be called an improvement on a point estimate inside ±0.23.

## AMENDMENT 2 (written after round 2, BEFORE the round-3 numbers)
`FT00` (trim every short whose CURRENT funding is negative) is positive in 5/5 disjoint calendar windows on both seeds, but fails GATE B clause 4: turnover +29% (limit +25%). The mechanism of that turnover is mechanical, not economic — a name whose rate sits near 0 crosses the boundary every settlement and is re-entered/re-exited. Registered fix, same family, one line:
- **`FT00S`** = the same rule on a CAUSAL trailing mean of the 8h-equivalent rate over the previous RNSM=6 panel rows (24h), i.e. trim shorts whose 24h-mean funding is negative. Strictly causal (rows ≤ j, the same rows the live producer already has).
- **`FT00_fix`** = FT00 at the fixed live seat 0.21/0/0.79, as a seat-robustness read only (the live book uses the dynamic seat; this is not the judged contrast).
GATE B is unchanged; K rises to 13. A one-clause fix to a gate that the arm already failed is NOT a re-choice of the gate — the gate's four clauses and the ±0.23 resolution floor stand exactly as written.
