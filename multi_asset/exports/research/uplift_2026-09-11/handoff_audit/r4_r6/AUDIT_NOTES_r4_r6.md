# Handoff audit working notes — block: rounds 4-6 (nondeterminism / fixed seat / new data / coverage / replay-vs-realized)
> Created 2026-09-12 by the handoff auditor. READ-ONLY session. Nothing outside this directory was created or modified.
> Every "VERIFIED" line below was checked in this session against a file named on the line. "INFERRED" = reasoning.

## 0. sha256 recomputed this session (all on local repo copies)
| object | recomputed sha256 | claim | verdict |
|---|---|---|---|
| trackA/w10_sleeve.py (= r13_A_halfscale/, r12_smoothing/devices/, r2_sleeve/devices/ — 4 identical copies) | b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650 | pinned b88e35a46b93d712 | MATCH |
| r3k_impact/costb_PWR_G230k.json (= r13_A_halfscale/, r10_screen/CMUM_CARRY/pin/) | 295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53 | 295b4e7b462373e4 | MATCH |
| PREREG_r6_coverage_extension_and_live_reconciliation_2026-09-11.md | 7dff6b0bf346aac77771993f1caf546fc1ebe797526d17c35cdbe79262b0e882 | same in RECEIPT_PREREG_FREEZE_r6_2026-09-11.json AND in RECON_r6 + both r6 RESULT docs | MATCH |
| r6j/R6J_judge.py | 6cde513e424b75a5f3a3bb0ad56d5f9569a4391b08b9af45154c5edb6fd34052 | receipt meta.self_sha256 | MATCH |
| r6j/R6J_nulls.py | e3919d71f1ea42cb71da60bee1f15050e684a64afc179a23cf738186de6a81b0 | receipt meta.self_sha256 | MATCH |
| r6j/R6J_conc.py | b1ccb56065d6355f8da817db9d641a0eebcce03fc4e0ad0ac30e3e8d9374483d | receipt meta.self_sha256 | MATCH |
| judge1_r6/j1_fee_fix.py | a23dca31acde6065ac9a418480a930fce868dcea6c57262844b215b22bef2d03 | j1_fee_usd.json meta | MATCH |
| judge1_r6/j1_realized.py | 4096fbbc91e6488ca5508341ffefe5e5b668d5d5742a443356ea545c09f8c231 | j1_realized.json meta | MATCH |
| judge1_r6/j1_slice.npz | f85ba016af93fc01... | doc §8 "f85ba016af93fc01" | MATCH |
| r5_angle2/w10_sleeve_w3seq.py | 4836245c1d570881ddadc16fc2ad2cbf1fb33c0ee51005b77999c606b2888fa8 | A2_CROSS_GATES.device_copy_sha256 | MATCH |
| r5_seeds/device/* (9 files) | see DEVICE_SHAS.txt | all 9 | MATCH (setup_tree.py present on disk but NOT listed in the receipt) |

**ZERO sha mismatches found.** Caveat that matters more than the matches: nearly every sha the block's
documents quote (preds arrays, arms npz, meta/panel/dlw npz, w10_seatladder.py f5dc76fb…, SLOW arrays
647673183e6af44a / dde19142d017c37d) names a file that exists only on pod2 `/workspace`. Those are
NOT RECOMPUTABLE from this repo. The repo can verify the *judges*, not the *inputs*.

## 1. Window arithmetic, established from receipts (not narrative)
Device axis (r6j/RECEIPT_r6j_R6J_JUDGE2.json meta.axis): n=10039, first 2022-01-31 00Z, last 2026-08-31 00Z.
- 10039 − 1 (the single 08-31 00Z row) = **10038** = W_TAIL.
- 10038 − 900 warm = **9138** = W_ALPHA. Confirmed independently by RESULT_r6_judge2 §3 ("W3_FULLCYCLE_ext 9138").
- rows ≤ 2026-08-10 20Z = 9918; 9918 − 900 = **9018** = the window every r4 / r5 number uses.
- 10039 − 900 = **9139** = the "FULL_all" window used by r5_newdata3's receipt and by ship1_receipts.
⇒ r4 / r5 "FULL post-warm" is 120 anchors SHORTER than W_ALPHA. 9139 is one anchor LONGER than W_ALPHA and
that one extra anchor (2026-08-31 00Z) is past the E-0911-D coverage ceiling.

## 2. Facts I verified directly in the pinned device source (trackA/w10_sleeve.py, sha b88e35a4…)
- **L182** `if p < LOOK: return np.array([1/3]*3)` — E-0911-A confirmed, and it returns BEFORE the
  `LEGS != "111"` masking block (L197-201), so the first 900 anchors carry a rev24 weight of 1/3 even at LEGS=101.
- **L267** `_zf = (_w3f[0]*np.nan_to_num(xz(F10P[i,m])) + …)` — E-0911-D mechanism confirmed: past the last
  finite F10 row the model leg silently becomes 0 and the F10 chain replays a 2-leg book. No exception, no signature.
- **L27-28** `W3FIX` single-value whitelist assert `== "0.21,0,0.79"` — as ANGLE-1/ANGLE-3 describe.
- **L17** `CAL = os.environ.get("CAL", "simple")` and **L166** `if CAL=="simple": _yy = np.expm1(_yy)` —
  the device's DEFAULT accounting is the E-0904-F-forbidden expm1 branch. Every run must pass CAL=log explicitly.
  All RUN_ENV/GATE receipts I opened in this block do record CAL=log.

## 3. E-0911-C fee correction — recomputed by me from judge1_r6/j1_fee_usd.json
| window | corrected fee USD | naive sum USD | corrected/naive | understatement as % of CORRECTED bill | bps of notional |
|---|---|---|---|---|---|
| W4 2026-08-01..09-10 | 376.62 | 250.25 | 1.505× | 33.6% | 2.772 |
| W5 2026-08-26 04Z..09-10 | 316.68 | 232.59 | 1.362× | 26.6% | 2.875 |
| SEP 2026-09-01..09-10 | 295.84 | 232.56 | 1.272× | 21.4% | 2.962 |
Reproduces RESULT_r6_judge1 §6 exactly. Reconciliation with the later round: RESULT_r11 §3 reports
corrected 2.7847 vs naive 1.9629 bps/unit traded ⇒ 29.5% understatement of the corrected bill, **on r11's own
window** — it sits between my W5 (26.6%) and W4 (33.6%). The two figures are the SAME defect on DIFFERENT
windows; they are not in conflict. "about 50%" is the same thing expressed against the naive denominator (W4).

## 4. fills dedupe — first-wins vs last-wins
`~/dl_quant_live/ops/backfill_markout.py` (read-only) states the log is append-only, the completed row is a NEW
row for the same trade_id, and `pilot_metrics.dedupe_fills` collapses **last-wins**; `_complete()` builds the new
row as `row = dict(f)` (full copy) plus mark fields.
Both block devices dedupe **first-wins**: `judge1_r6/j1_realized.py` L78-81 and `refute_r6/r6_fee_dedupe.py`
(`if tid in seen: continue`). Deviation is real. Blast radius, established from the producing code: because the
backfilled row is a verbatim copy plus mark fields, commission / fill_notional / price are identical, so the
block's fee, turnover and timing numbers are unaffected. It WOULD silently drop every backfilled +60s mark for
any markout-based statistic — i.e. exactly the instrument at the centre of the unresolved cost dispute.

## 5. Turnover unit trap — the brief's own conversion does not close
ship1_receipts/SHIP1_A0_accounting.json (A0 dyn s42, n=9139): turnover 0.030315, gross_total 0.695654.
- ratio of means = 0.030315 / 0.695654 = **0.043578** (this is what "×1.4375" produces)
- RESULT_r5_angle1 §3 quotes the normalised dyn turnover as **0.05402** (and fix 0.01926) — that is 1.7822× the raw,
  i.e. a mean-of-per-anchor-ratios, not a ratio of means.
⇒ The two numbers in the brief (0.03032 → 0.0540270) are NOT related by the stated factor 1.4375. A reviewer who
converts with 1.4375 lands on 0.0436 and will not reproduce ANGLE-1. Both calibers appear inside this block:
RESULT_r5_angle1 §3 uses the normalised one; RESULT_r5_angle3 §8, RESULT_r5_newdata2 §6 and every
r5_newdata3 table use the RAW one (0.03037 / 0.03084 / 0.01603 / 0.0160). Neither document says which it is using.

## 6. A0 "incumbent level" — five different numbers in this block
| value | window / cost | receipt |
|---|---|---|
| 1.4150 | n=9018 (≤08-10 20Z), fitted PWR | r4_nondet RESULT_P4_book, r5_seeds JUDGE_R5_6, r5_newdata3 A0_headline_check, r5_basis SUMMARY |
| 1.2947 | n=9139 (≤08-31 00Z), fitted PWR | r5_newdata3/A0_headline_check.json — **computed in round 5, never quoted in the round-5 document** |
| 1.291 / 1.2912 | n=9138 = W_ALPHA, fitted PWR | RESULT_r6_judge2 §4.1 / CLOSEOUT §? |
| 1.4025 | n=9139, cheap (fee_steady) cost | ship1_receipts/SHIP1_A0_accounting.json |
| 1.6039 | n=7835 (LOB coverage subset), fitted PWR | r5_lob/RESULT_SUMMARY.json _meta |
plus the caliber pin's frozen-window A0 = +1.894 bps / Sharpe 3.04 (STD cost), vs r4/r5's frozen A0 = 1.8267 / 2.9357 (PWR cost).

## 7. Documents with NO machine receipt anywhere in the repo
- **RESULT_r5_angle1_fixed_seat** — every artifact it cites (w10_seatladder.py f5dc76fb…, seatladder/GATE_P_ladder.json,
  ANGLE1_LADDER_RESULT.json, ANGLE1_NULLS_RESULT.json, ANGLE1_NULLS_A0CTRL_RESULT.json, ANGLE1_seat_anatomy.json)
  is pod-only. `find` over the whole programme returns only the .md itself.
- **RESULT_r5_newdata2_liq_oi** — all receipts are `/workspace/uplift_2026-09-11/r5_oi/receipts/*`; no r5_oi directory exists locally.
- ANGLE-1's live-seat distribution ("98 combo-era anchors, median 0.2242, 53% inside 0.21±0.02") has no receipt;
  the one live-seat receipt that does exist (r5_angle2/LIVE_SEAT_PROBE.json) reports a DIFFERENT quantity
  (51 recomputable anchors from leg_returns_live.json, masked king min 0.2999 / median 0.3251, frac ≤0.21 = 0.000).
  They are reconcilable (deployed w3_masked history vs a recompute off today's leg returns) but a reviewer will
  read them as contradictory unless told.

## 8. Two tracks with receipts and no write-up anywhere
- **r5_lob** = "R5 NEW DATA 4 — the order book in PRICE space", K=16 declared, verdict "ZERO ADMISSIONS",
  own prereg inside the directory, verbatim per-arm commands in commands.txt (best re-run hygiene in the block).
  No RESULT document at top level; the string "BTILT"/"price space"/"NEW DATA 4" appears in NO top-level .md,
  including CLOSEOUT §3 ("what was tested — full account").
- **r5_angle2** = the SCORE-vs-WEIGHT cross decomposition (A2_CROSS.json, A2_LADDER.json, A2_CROSS_GATES.json,
  GATE_P_r5a2.json with the block's only explicit env_whitelist + env_defaulted split). No document mentions it.

## 9. E-0826-D (env whitelist in the artifact) compliance, per receipt
- Full per-arm env inside the receipt: judge1_r6/RECON_r6…json, r6j/RECEIPT_r6j_R6J_JUDGE2.json,
  r5_lob/RESULT_SUMMARY.json + commands.txt (verbatim command lines), r5_basis_receipts/GATE_PS.json (verbatim cmd),
  r5_basis_receipts/RUN_ENV_{arms,nulls}.json (set keys only), r5_angle2/GATE_P_r5a2.json (set AND defaulted),
  ship1_receipts/SHIP1_A0_accounting_PWR.json (whitelist + device config_json).
- **No env anywhere in the receipt**: all of r4_nondet/receipts, all of r4p3, all of r5_seeds/receipts,
  all of r5_newdata3, r6j NULLS/CONC, refute_r6. For those the env is recoverable only from the archived driver code.
- Sharpest instance: round 4's whole finding is "the env that selects the training object is not in the product
  json", and round 4's own receipts carry no env block. Its `train_v2.sh` sets 10 env keys for a trainer that
  ANGLE-3 §6 documents as having **17** os.environ read points — 7 were left on defaults in the very replication
  that diagnosed default-driven object substitution. (It still reproduced bitwise, so no number is wrong.)

## 10. The "replay is pessimistic" characterisation
Appears in RESULT_r6_judge1 at the §0 headline, §3 (H-A label), §4 ("错的方向已知: 回放偏悲观"), §4 reconciliation,
and §4's planning sentence ("1.42 若有偏, 偏保守"). It is pre-baked into PREREG_r6 §4.3 as the name of hypothesis H-A.
The same document's §1 states the correct reading ("回放系统性地高估幅度约 15–27%").
CLOSEOUT_uplift_program_2026-09-12 line 24 explicitly retracts it: slope CI upper < 1 in all four tests means the
replay amplifies magnitude in BOTH directions; the live window merely happened to be a losing one.
The retraction was never back-annotated into RESULT_r6_judge1, and the planning sentence ("1.42 is conservative")
is the one place where the error is load-bearing: 1.42 is a positive Sharpe, and compression of magnitude cuts it down.
The intercept +0.509 is estimated on a window whose mean replay g is −0.737; extrapolating it to a +1.9 bps regime
is not supported by the fit.

## 11. Cost-model dispute — what my block contributes
RESULT_r6_judge1 §3 (receipt judge1_r6/j1_decomp.json, W5 n=75): realized (fee + timing) − replay cost =
**+0.2767 bps/anchor, CI95 [+0.075, +0.653]** (s2027 +0.2795 [+0.076, +0.699]); replay cost −0.1226 vs realized +0.1541.
TIMING alone = **+0.2992 [+0.009, +0.688]** (maker slippage is a negative cost). That is a first-hand, live,
intention-to-treat-shaped measurement saying the fitted model **over-charges** this book — the opposite sign to the
markout instrument's claim that the model is 1.7071× (CLOSEOUT A-3) or 3.2167× (brief) too cheap.
First-order effect of a 3.2167× repricing on this block's headline verdicts (INFERRED, linear in cost_ex):
- A0 dyn full-cycle: net g 0.6890 → 1.3266 − 0.4694 − (0.1682×3.2167 = 0.5410) = **0.3162**, Sharpe ≈ 1.415 → **≈0.65**.
- XIB_LAG50 − A0 (the round-5 survivor): Δcost grows ≈ 0.0267 → 0.0860 ⇒ Δg 0.4029 → **≈0.344**. Verdict UNCHANGED.
- r5 basis FBSLOPE_NOLAG: cost 1.1746 → 3.778 ⇒ mean g 0.5473 → **≈ −2.06**. NEAR_MISS → dead.
- r5 newdata2 arms, r5_lob arms: already rejected; repricing deepens.
- r5_newdata3 staleness: stale rosters carry HIGHER turnover (0.0160 → 0.0231), so repricing makes staleness
  look worse ⇒ the monthly-refresh recommendation strengthens.
- r4: sd across draws is 0 at any cost ⇒ untouched.
