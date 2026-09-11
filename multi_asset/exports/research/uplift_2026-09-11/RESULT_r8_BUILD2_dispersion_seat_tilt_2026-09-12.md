> **创建:** 2026-09-12 | **Session:** b9646a9e (round 8, BUILD 2) | **状态:** VERDICT = REJECTED, 9/9 arms fail the frozen primary gate | **作废条件:** 新面板/新成本模型, 或在 2022-2024 之外找到 sigma<4.75 的独立样本

# BUILD 2 — condition the leg weight on the one mechanism-identified dispersion relationship

PREREG: `PREREG_r8_BUILD2_dispersion_seat_tilt_2026-09-12.md` (sha256 b4308fd79949d628…), frozen before
any arm was run. K = 9 declared up front. All 9 arms are reported. No arm was added after the fact.

## 0. GATES (all VERIFIED, bitwise)
| gate | result | receipt |
|---|---|---|
| GATE P, tilt device knobs-off vs archived A0, 4 cells (dyn/fix × s42/s2027), `d30_n2_c42_rec` AND `_W` | **PASS 4/4 bitwise** | `r8b2_receipts/GATE_P_r8.json` |
| GATE P2, null-feed device knobs-off, same 4 cells | **PASS 4/4 bitwise** | `R8_NULLS_DRIVE.json` |
| WIRING: null device fed the TRUE sigma (SHIFT0) == tilt device arm | **bitwise, both arms** | `R8_NULLS_DRIVE.json` |
| Internal causal sigma == the external LIVE gauge, 9138 anchors | **maxabs 0.0** | `R8_JUDGE.json.sigma_gauge_check` |

Device 1 `r8b2/w10_sleeve_tilt.py` sha256 `7dd6324acd361081…` = pinned `w10_sleeve.py` (`b88e35a46b93d712…`)
+ {TILT, TILT_TAU, TILT_K, TILT_LO, TILT_HI}. Device 2 `w10_sleeve_tilt2.py` `0ff501815bdc564f…` = device 1
+ TILT_SIG_NPZ (null feed only). Cost = fitted `r3k/costb_PWR_G230k.json` `295b4e7b462373e4…`.
ENV WHITELIST (E-0826-D), asserted on every env string of every run:
LEGS, CAL, WRULE, LOOK, MEMBERS_TOPN, FTRIM, PHI, UMASK_SCOPE, UMASK_NPZ, SLOW_NPY, FSEED, FPRED,
COSTB_JSON, OUT_TAG, W3FIX, TILT, TILT_TAU, TILT_K, TILT_SIG_NPZ (+ OMP/OPENBLAS/MKL_NUM_THREADS).
Nothing was trained this round, so no V2-class training flag applies. Every analysis script asserts an
EMPTY env whitelist. Caliber: g = net_ex/gross_total, bps per 4h anchor per unit gross; post-warm drop
900 (E-0911-A); cut 2026-08-30 20Z (E-0911-D); n = 9138.

## 1. THE MOTIVATING NUMBERS REPRODUCE, FIRST-HAND (step 1 of the brief)
Re-run with my device, knobs off, at the fitted cost, and asserted **bitwise** against the round-7 /
round-3 artifacts (`R8_DRIVE.json`, REPRO_PASS true, 4/4): A0 s42 & s2027 vs `r3k/arms/A0_PWR230k_s*`,
FUND vs `r7f2/…R7_LEGFUND_PWR_s42`, KING vs `r7f2/…R7_LEGKING_PWR_s42`.

| quantity | round 7 | mine (VERIFIED) |
|---|---|---|
| FUND leg (LEGS=001 PHI=0), sigma<4.75, mean g | −0.6089 CI95 [−1.1491,−0.0631] SR −1.522 | **−0.6089 CI95 [−1.1654,−0.0615] SR −1.5220**, n 4660 |
| KING leg (LEGS=100 PHI=0), sigma<4.75, mean g | +0.3818 CI95 [−0.6445,+1.4187] | **+0.3818 CI95 [−0.6353,+1.4148] SR +0.6921**, n 2334 |
| A0 non-inheritance, sigma<4.75 | −0.1548 CI95 [−0.708,+0.386] | **−0.1548 CI95 [−0.7063,+0.4213] SR −0.3732** |
| A0 unconditional | +0.634 CI95 [+0.161,+1.110] SR 1.291 | **+0.6342 CI95 [+0.1653,+1.1071] SR 1.2912** |
| A0 giveback 08-19..21 | SR −29.61 | **mean g −20.7548, SR −29.6065** |
CI bounds differ in the 3rd decimal because the bootstrap seed differs; point estimates are identical to
4 d.p. and every sign/exclusion is unchanged. **The premise is real: the seat is blind to the gauge** —
corr(sigma, w3_fund) = **−0.0361**; w3_fund averages **0.5555 when sigma<4.75** vs **0.5204 when
sigma≥4.75**; sigma-decile-1 w3_fund = **0.6834**. The seat gives the fund leg MORE weight when the fuel
is gone.

## 2. THE CONSTRUCTION
After the msharpe seat returns w3: `w_fund ← w_fund · f(sigma_i)`, `w3 ← w3/Σw3` (LEGS=101 ⇒ the freed
weight goes to king). sigma_i = 1e4 × population sd of the finite 8h-equivalent **settled** funding rates
over the same masked member set the book ranks at anchor i — strictly causal, and verified equal to the
round-7 LIVE gauge to **maxabs 0.0** over all 9138 anchors. tau = 4.75 is INHERITED from round 7 (it was
profiled in-sample there; recorded as a hole). LOOK stays 900. Gross is untouched.

## 3. VERDICT: ALL NINE ARMS FAIL THE PRIMARY GATE
Primary gate (a): theta = year-FE mean of d, Bonferroni K=9 ⇒ 99.44% CI must exclude 0, AND ≥4/5 years
positive. **No arm clears it. No arm clears even an UNcorrected 95% CI on theta.**

| arm | f | Δg | Δg CI95 | theta | theta CI 99.44% | yr+ | ΔSharpe | (b) held-out | (c) giveback |
|---|---|---|---|---|---|---|---|---|---|
| S00 | step κ=0 | +0.2516 | [+0.0221,+0.4887] | +0.2104 | **[−0.1033,+0.5501]** | 4 | +0.5865 | +0.1793 (3/120 active) | +1.3090 |
| S25 | step κ=.25 | +0.0185 | [−0.0753,+0.1107] | +0.0144 | [−0.1012,+0.1356] | 2 | +0.0211 | +0.1349 (3/120) | +0.8708 |
| S50 | step κ=.50 | +0.0016 | [−0.0534,+0.0581] | −0.0008 | [−0.0697,+0.0717] | 2 | −0.0028 | +0.0456 (3/120) | +0.5332 |
| S75 | step κ=.75 | −0.0004 | [−0.0297,+0.0283] | −0.0032 | [−0.0409,+0.0350] | 3 | −0.0027 | +0.0506 (3/120) | +0.2283 |
| R00 | ramp fl 0 | +0.0192 | [−0.0420,+0.0803] | +0.0141 | [−0.0600,+0.0892] | 3 | +0.0299 | +0.0192 (3/120) | +0.0480 |
| R25 | ramp fl .25 | +0.0129 | [−0.0442,+0.0704] | +0.0088 | [−0.0589,+0.0803] | 3 | +0.0176 | +0.0192 (3/120) | +0.0480 |
| R50 | ramp fl .50 | +0.0123 | [−0.0309,+0.0548] | +0.0100 | [−0.0433,+0.0641] | 3 | +0.0187 | +0.0187 (3/120) | +0.0510 |
| P05 | pow p=0.5 | +0.0538 | [−0.0131,+0.1202] | +0.0538 | [−0.0512,+0.1557] | 3 | +0.0719 | **−0.4518 (120/120)** | **−1.4332** |
| P10 | pow p=1.0 | +0.0703 | [−0.0135,+0.1511] | +0.0703 | [−0.0542,+0.1910] | 3 | +0.0910 | **−0.5318 (120/120)** | **−2.0760** |
(full-axis reading; the paired-on-intersection reading is in `R8_JUDGE.json` and differs only for S00.)

### (b) HELD OUT — fit through 2026-08-10 20Z, predict 2026-08-11..08-30 20Z (n=120)
| family | in-sample pick | prediction | realisation | sign |
|---|---|---|---|---|
| S | S00 | +0.0971 | +0.1793 CI95 [−0.1119,+0.5231] | agrees, but on **3 active anchors of 120** — no power |
| R | R00 | +0.0192 | +0.0192 CI95 [−0.0065,+0.0493] | agrees, same 3 anchors — no power |
| P | P10 | **+0.0783** | **−0.5318** CI95 [−1.2946,+0.2276] | **WRONG SIGN, −0.61 bps/anchor** (s2027: **−1.0789**) |
The only family with power on the held-out window is P, and it fails with the wrong sign — the same
failure mode, in the same window, as round 7's pooled curve.

### (c) GIVEBACK — the P family makes it worse, exactly like XIB_LAG50
P05 −1.4332, P10 −2.0760 (ΔSharpe −1.41 / −2.33), replicating at s2027 (P10 −1.6309). S/R read positive
but on **2 active anchors of 18** — that is not a pass, it is an inert tilt.

### (d) TURNOVER-MATCHED NULLS (permutation placebo NOT used — it is defective)
Nulls = SHIFT101/503/1009 and 3 circular rotations of the **sigma series**, which preserve the tilt
multiplier's marginal distribution and lag-1 persistence (hence its turnover: real S00 1.1436× vs nulls
1.1444–1.2887×; real P10 0.9929× vs nulls 0.9870–1.0608×) and destroy only time alignment.
Both real arms beat all 6 nulls on Δg, theta AND pnl_ex (gross) — but **6 nulls floor the empirical p at
1/7 = 0.1429**, far above the corrected alpha of 0.00556. The nulls do not confirm; they fail to refute.
Worse, they show *what* the effect is: **P10 real +0.0703 vs SHIFT503 +0.0658 — 94% of it survives
shifting the sigma series 503 anchors (≈84 days).** S00 real +0.2516 vs SHIFT1009 +0.1303 — half of it
survives a 168-day shift. That is a slow level/era component, not time-aligned dispersion information.

## 4. WHAT IT COSTS (brief item 4)
| arm | marginal turnover vs A0 (L1/anchor) | turnover ratio | Δcost_ex (bps/anchor) | Δg in sigma≥4.75 (the good states) |
|---|---|---|---|---|
| S00 | +0.004967 | 1.1436× | +0.0410 | −0.0017 [−0.1451,+0.1396] |
| S25 | +0.002172 | 1.0717× | +0.0200 | **−0.0271** [−0.1126,+0.0547] |
| S50 | +0.001324 | 1.0437× | +0.0110 | **−0.0208** [−0.0754,+0.0324] |
| R00 | +0.001380 | 1.0455× | +0.0119 | +0.0084 [−0.0347,+0.0533] |
| P10 | −0.000216 | 0.9929× | +0.0031 | **+0.1314** [+0.0035,+0.2623] |
A0 baseline turnover 0.03032 L1/anchor, cost 0.1675 bps/anchor. The brief's object — *helps in the bad
states, costs nothing in the good ones* — is not what any arm is. S25/S50 shave the good states by
0.021–0.027 to buy 0.023–0.062 in the bad ones: a wash inside the noise. P05/P10 are the **opposite** of
the designed object: their entire gain is in HIGH dispersion (+0.12/+0.13, the only regime CI in the
whole grid that excludes zero) and they are flat in LOW dispersion (−0.011/+0.012), i.e. they do not
touch the identified fund-leg weakness at all.

## 5. THE TWO THINGS THAT KILL IT
**(i) S00 — the best-looking arm — is not a leg tilt. It is gross timing.** κ=0 sets w_fund→0 below tau;
whenever the msharpe seat ALSO has w_king=0 (king trailing Sharpe ≤ 0) the whole w3 vector is zero and
the device holds **no book at all**. That happens on **2422 of 9138 anchors = 26.5%**, and all 2422 are
in the sigma<4.75 set. Its full-axis Δg +0.2516 is earned mostly by being flat, not by re-weighting:
A0's mean g on those anchors is negative. Pairing on the intersection instead silently conditions on
"the king seat was positive" (that reading gives +0.0986). Gross timing is refuted three times over
396 variants, OOS mean dSharpe −0.0502, one-sided 95% UB −0.0398. **S00 is disqualified on
construction**, not on its CI — and its CI fails anyway.

**(ii) The tilt is an era bet with no sample where it matters.** n(sigma<4.75) by year: 2022 730/1110,
2023 1596/2190, 2024 1747/2196, 2025 521/2190, **2026 66/1452 (4.5%)**. S00's full-axis per-year Δg is
2022 +0.0085, **2023 +0.6751, 2024 +0.3636**, 2025 +0.0078, **2026 −0.0028**. The entire effect is
2023-2024. In 2026 — the regime the book actually trades — the construction is worth −0.0028 bps/anchor.
The held-out window has 3 active anchors of 120 and the giveback 2 of 18, so the two tests the desk
demanded cannot be answered for the S and R families at all. This was written into the prereg §6 BEFORE
any arm ran, so it is a structural limit, not a post-hoc excuse.

## 6. VERDICT
**REJECTED.** 9/9 arms fail gate (a) at Bonferroni K=9 and none clears an uncorrected 95% CI on theta.
Family P additionally fails (b) with the wrong sign in both seeds and fails (c) by deepening the
giveback. Families S and R are inert in both (b) and (c). The one arm with a headline number is a
26.5%-of-the-time flat-the-book rule, i.e. the closed gross-timing axis wearing a leg-tilt wrapper.
**This does not change round 7's conclusion. A cross-regime Sharpe significantly above 3.0 is still not
attainable on current evidence, and the planning number remains A0's +0.634 bps/anchor, Sharpe 1.291,
+27.8% of NAV/yr at 2.0×.**
No variant was chosen after the fact; no arm is proposed for promotion; nothing was written to
`~/dl_quant_live` or `~/wide_shadow`.
