# PREREG · GATE A — retire the backward-IC gate, freeze S7-R (echo-adjusted forward IC + constructive edge test)

> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 预注册, 规则冻结于本文 §4, 在任何新臂被判前生效 | **作废条件:** 若 §3 的机理数 a₁ 在新面板上改号, 或 §5 校准控制(CTRL_REV4 / CTRL_NULL)读数离开其声明带, 本规则作废重建
> **口径 PIN:** v4 chain 2026-09-09。回放轴 `review_scratch/health_check/dev_v4/pod_backup_2026-08-21/{wide_fea_hist_meta.npz, wide_panel_4h_hist_v2.npz}`, 宇宙 = members ∩ umask_UPIT_CRYPTO m1, 秩 = `scipy.stats.rankdata`(AVERAGE), 目标 = meta `y4`。秩 IC 对 log/simple 单调变换不变 ⇒ CAL 不进入本文任何数字。
> **GATE P:** PASS — `w10_dev.py` sha256 `b88e35a4…`(= `w10_sleeve.py`), knobs 全默认, 对 `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}.npz` 的 `d30_n2_c42_rec` 与 `d30_n2_c42_W` **四格 × 两数组全部逐位相等**(maxabs = 0)。收据: `r3_gates/GATE_P` 命令见 §8。

## §0 本文要回答的问题
S7("reject if backward IC dominates forward")已被连续三轮绕过。它当前判在役 DL 腿 FAIL(5.3×)、判 RESID_SHARPE 4.7×、判 Amihud sleeve 2.1×。本文先**测**(§2), 再**给机理**(§3), 再**冻结规则**(§4), 顺序固定。

## §1 装置
`r3_gates/devices/offspec.py` sha256 `64d4c346…` — 全 k = −5..+5 谱, 全 10039 锚, 无抽样。
`r3_gates/devices/echo.py` sha256 `e222289a…` / `echo2.py` `62f6186e…` — 回声分解 + UTC 日块 bootstrap 2000, rng `default_rng([20260905,k])`。
定义(冻结): `ic(k) = mean_i Spearman(S[i, m_i], y4[i+k, m_i])`。`y4[i]` = 从锚 i 交易的前瞻 4h 收益 ⇒ **k=0 = 前瞻 alpha, k=−1 = 刚收的那根 bar**。

## §2 测得的谱(全周期 10039 锚) — VERIFIED
| arm | −5 | −4 | −3 | −2 | −1 | **0** | +1 | +2 | +3 | +4 | +5 | \|ic(−1)\|/\|ic(0)\| | S7 as written |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LIVE_KING (SLOW v3) | −.0631 | −.0643 | −.0664 | −.0716 | −.1549 | **+.0625** | +.0502 | +.0439 | +.0406 | +.0383 | +.0358 | 2.48 | **FAIL** |
| LIVE_DL F10_A0_s42 | +.0260 | +.1593 | +.0660 | +.0633 | −.2229 | **+.0351** | +.0141 | +.0022 | −.0000 | +.0052 | +.0093 | 6.35 | **FAIL** |
| LIVE_DL F10_A0_s2027 | +.0370 | +.1423 | +.1046 | +.0074 | −.2500 | **+.0354** | +.0123 | +.0013 | +.0009 | +.0048 | +.0098 | 7.07 | **FAIL** |
| LIVE_FUND f_fund_ema_v1 | +.0068 | +.0063 | +.0054 | +.0046 | +.0057 | **+.0079** | +.0075 | +.0070 | +.0068 | +.0063 | +.0061 | 0.73 | PASS |
| XIB_LAG50 blended | +.0021 | +.0070 | +.0124 | +.0195 | +.0109 | **+.0142** | +.0139 | +.0127 | +.0119 | +.0115 | +.0113 | 0.77 | PASS |
| AMI sleeve ORTHLAG | −.0060 | +.0026 | +.0123 | +.0246 | +.0103 | **+.0129** | +.0130 | +.0116 | +.0108 | +.0105 | +.0101 | 0.80 | PASS |
| RESID_SHARPE s42 | −.0233 | −.0233 | −.0219 | −.0193 | −.0636 | **+.0115** | +.0071 | +.0054 | +.0042 | +.0049 | +.0031 | 5.52 | **FAIL** |
| RESID_SHARPE s2027 | −.0237 | −.0250 | −.0259 | −.0268 | −.0516 | **+.0068** | +.0029 | +.0019 | +.0011 | +.0013 | +.0011 | 7.59 | **FAIL** |
| TBF raw (known-bad) | +.0134 | +.0102 | +.0127 | +.0259 | +.0595 | **−.0027** | −.0008 | +.0004 | +.0011 | +.0005 | +.0024 | 21.7 | **FAIL** |
| LEG_REV24 (−f_rev_24h) | −.3379 | −.3223 | −.3149 | −.3139 | −.3124 | **+.0402** | +.0225 | +.0158 | +.0103 | +.0082 | +.0032 | 7.77 | **FAIL** |
| CTRL_MOM7 (legal trailing) | +.0932 | +.0925 | +.0929 | +.0944 | +.0953 | **−.0338** | −.0271 | −.0247 | −.0222 | −.0208 | −.0184 | 2.82 | **FAIL** |
| CTRL_REV4 (−f_rev_4h, 1 bar) | +.0031 | +.0080 | +.0161 | +.0244 | **−.9631** | **+.0395** | +.0172 | +.0089 | +.0040 | +.0080 | −.0047 | 24.4 | **FAIL** |
| CTRL_AMI_RAW (unlagged) | −.0117 | −.0043 | +.0042 | +.0135 | +.0253 | **+.0118** | +.0149 | +.0149 | +.0135 | +.0125 | +.0122 | 2.15 | **FAIL** |
| **CTRL_LEAK_XIB_FWD50** (deliberate leak) | −.0120 | −.0032 | +.0011 | +.0059 | +.0125 | **+.0213** | +.0120 | +.0137 | +.0135 | +.0123 | +.0115 | 0.59 | **PASS** ← |
| **CTRL_LEAK_FUND_FWD1** (deliberate leak) | +.0071 | +.0067 | +.0063 | +.0053 | +.0045 | **+.0057** | +.0079 | +.0075 | +.0070 | +.0068 | +.0063 | 0.80 | **PASS** ← |
| CTRL_NULL (per-anchor perm) | +.0005 | −.0004 | +.0004 | −.0015 | −.0001 | **+.0000** | −.0002 | +.0000 | +.0003 | +.0006 | +.0010 | — | PASS |
| CTRL_ORACLE (= y4) | −.0080 | −.0036 | −.0085 | −.0168 | −.0442 | **+1.0000** | −.0442 | −.0168 | −.0085 | −.0035 | −.0078 | 0.04 | PASS |

**S7 as written, measured operating characteristics: of the 13 CAUSAL arms in the table it rejects 10 — including 2 of the 3 in-service legs, the rev24 leg, and every raw price/flow feature (the 1-bar reversal CTRL_REV4 at 24.4×, REV24 at 7.8×, MOM7 at 2.8×, AMI_RAW at 2.15×, TBF at 21.7×). Of the 2 synthetic leaks it rejects 0. Detection rate on leakage 0/2; false-rejection rate on causal arms 10/13. The gate is ANTI-correlated with the thing it claims to detect.** That is the reason three rounds could not apply it: it has no discriminating power to apply.

Two corrections to the round-2 brief, both VERIFIED here:
1. **TBF is NOT sign-concordant.** Measured k=−1 = **+0.0595**, k=0 = **−0.0027** — signs DISCORD. The premise "sign-discordance separates RESID_SHARPE (mechanism) from TBF (lookahead)" is false. Sign discordance is common to both.
2. The brief's "accepted Amihud sleeve at 2.1×" is the **unlagged raw** Amihud (measured 2.15×). The sleeve actually admitted (`ORTHLAG`, orth of the one-anchor-lagged rank) reads **0.80×**.

## §3 机理 — why sign-discordance at k=−1 is admissible (and so is concordance)
The oracle arm measures the cross-sectional rank-autocorrelation of the traded return itself:
**a₁ = ic_oracle(−1) = −0.04424**, a₂ −0.01676, a₃ −0.00848, a₄ −0.00357, a₅ −0.00803 (full cycle).
Because a₁ < 0, **any** score loaded on the just-closed bar mechanically inherits a forward IC of the **opposite** sign, magnitude ≈ |ic(−1)·a₁|. Verification on the purest possible case, a one-bar reversal (CTRL_REV4, ic(−1) = −0.96307):
predicted echo = −0.96307 × −0.04424 = **+0.04261**; measured ic(0) = **+0.03946**. Agreement 7%.
⇒ `|ic(−1)|` measures the feature's **input window**; its **sign** measures momentum-vs-reversal loading. Neither is a statement about what was knowable at E. A 24h feature spreads that footprint over k = −1..−6 (REV24: −0.31 flat over −1..−5 ✓); a 1-bar feature concentrates it at k = −1 (REV4: |ic| 0.96 at −1, ≤0.024 elsewhere ✓); a 7d feature spreads it over 42 bars (MOM7: +0.093 flat ✓). All three are maximally legal and all three fail S7 as written.

## §4 冻结规则 — GATE S7-R (replaces S7)
An arm passes S7-R iff **all three** hold, evaluated on the primary window of `PREREG_gateB_primary_window_2026-09-11.md`, in the arm's traded sign:

**R1 — ECHO-ADJUSTED FORWARD IC.** Per anchor i, residualise the target: regress `rank(y4[i])` cross-sectionally on `rank(y4[i−1..i−5])` over the same member set; call the residual ỹ_i. Define `xic = mean_i corr(rank(S_i), ỹ_i)`.
**PASS requires the UTC-day block-bootstrap (2000 resamples, rng `default_rng([20260905,k])`) lower bound of `xic` > 0 at the arm's declared Bonferroni level.** M = 5 lags, declared before measurement. (Mean R² of `rank(y4[i])` on the five past-bar ranks = **0.0782**.)

**R2 — ERA STABILITY.** `xic` computed separately on pre-2025 and 2025-on halves of the primary window must (a) share sign and (b) have the later point estimate ≥ 25% of the earlier, on **every** seed of the arm.

**R3 — EDGE (the leakage clause, constructive).** Before measurement declare, for every input, the last panel row the code reads, as an anchor offset `e` (`e=0` = the row at E). **Any `e > 0` rejects.** The spectrum then *falsifies a wrong declaration*, but only where it can: **if and only if `max_{k≤−1}|ic(k)| > |ic(0)|` (the arm is return-loaded), require `argmax_k |ic(k)| ≤ e−1` over all k ∈ [−5,+5].** Where the condition does not hold the spectrum carries no alignment information and R3's spectrum half is declared **N/A** in writing.

**Declared, permanent blind spot of R3 (named, not closed).** For an arm with `e = 0` and no dominant backward footprint, the offset spectrum *cannot* separate one-anchor look-ahead from genuine one-bar-ahead alpha: the synthetic leak `CTRL_LEAK_XIB_FWD50` (identical construction to XIB_LAG50, Amihud window shifted **across** the anchor) reads ic(0) **+0.0213** vs the honest arm's **+0.0142**, xic **+0.0235** vs **+0.0151**, and passes every spectrum-based test. For such arms the leakage defence **must** be the shuffle-future test, folds-out = 0, and a code audit of the last row read — never the offset spectrum. `CTRL_LEAK_FUND_FWD1` *is* caught by R3 (argmax at k = +1 > e−1 = −1).

## §5 校准收据(size / power of R1) — VERIFIED
| control | ic(0) | echo(1st order) | **xic** | xic CI95 | reads |
|---|---|---|---|---|---|
| CTRL_NULL (per-anchor perm) | −0.00032 | −0.00000 | **−0.00037** | [−0.00177,+0.00097] | size = 0 ✓ |
| CTRL_REV4 (pure lag-1 reversal) | +0.03800 | +0.04038 | **−0.00336** | [−0.00386,−0.00288] | pure echo stripped to 0 ✓ |
| CTRL_ORACLE (= y4) | +1.00000 | +0.00226 | **+0.96054** | [+0.95956,+0.96153] | full power ✓ |

## §6 应用本规则的结果(本轮所有臂) — VERIFIED
Bonferroni K declared **= 4** (the four arms under judgement: XIB_LAG50, AMI_SLEEVE_ORTHLAG, RESID_SHARPE s42, RESID_SHARPE s2027). In-service legs and controls are reported, not judged.
`xic` [CI95], primary window = FULLCYCLE post-warm (§ PREREG gate B):

| arm | xic FULLCYCLE | xic pre-2025 | xic 2025-on | R1 | R2 | R3 | S7-R |
|---|---|---|---|---|---|---|---|
| LIVE_KING | +.0511 [+.0486,+.0537] | +.0446 | +.0552 | pass | pass | e=0, argmax −1 ✓ | **PASS** |
| LIVE_DL F10 s42 | +.0270 [+.0249,+.0291] | +.0387 | +.0124 | pass | 0.32 ≥ 0.25 pass (**thin margin — see §7-4**) | e=0, argmax −1 ✓ | **PASS** |
| LIVE_FUND | +.0092 [+.0071,+.0113] | +.0062 | +.0138 | pass | pass | not return-loaded → N/A | **PASS** |
| XIB_LAG50 | +.0151 [+.0128,+.0172] | +.0170 | +.0122 | pass | 0.71 pass | e=0 (the fund half reads row j), argmax −2 ≤ −1 ✓ | **PASS** |
| AMI_SLEEVE_ORTHLAG | +.0128 [+.0105,+.0148] | +.0184 | +.0039 [+.0008,+.0074] | pass | 0.21 **< 0.25 FAIL** | e=0 (orth uses row j), argmax −2 ≤ −1 ✓ | **FAIL (R2)** |
| RESID_SHARPE s42 | +.0090 [+.0064,+.0117] | +.0225 | **−.0079 [−.0115,−.0043]** | pass | **sign flip, CI excludes 0 → FAIL** | e=0, argmax −1 ✓ | **FAIL (R2)** |
| RESID_SHARPE s2027 | +.0053 [+.0025,+.0082] | +.0250 | **−.0193 [−.0231,−.0154]** | pass | **sign flip, CI excludes 0 → FAIL** | e=0, argmax −1 ✓ | **FAIL (R2)** |
| TBF_ema08 (round-2 form) | +.0039 [+.0021,+.0057] | +.0055 | +.0014 [−.0009,+.0037] | pass | 0.25 boundary, 2025-on CI∋0 **FAIL** | e=0, argmax −4 ≤ −1 ✓ | **FAIL (R2)** |
| TBF_raw | +.0031 [+.0015,+.0048] | +.0011 [−.0013,+.0034] | +.0063 | pass | pre-era CI∋0 **FAIL** | e=0, argmax −1 ✓ | **FAIL (R2)** |

## §7 三个必须说出口的结论
1. **(i) 杀 TBF: 做到了, 但不是靠谱形。** R1(水平)**不杀** TBF_raw(xic +0.0031, CI 不含 0)。TBF 死在 **R2 era 稳定性**。**没有任何静态偏移谱规则能杀 TBF, 因为 TBF 根本不是泄漏案例**; 第一轮"S7 杀了 TBF"是**用错的仪器得到了对的判决**。这必须记在错题集里。
2. **(iii) 修好的规则放行在役 DL 腿** — xic +0.0270 CI [+0.0249,+0.0291], R3 的 argmax 在 k=−1(= 因果边 e=0 所要求的位置)。它的 −0.2229@k=−1 **不是缺陷, 是一个合法 edge-0 特征必须出现的前沿**。同样放行 king(+0.0511)与 fund(+0.0092)。**在役书三条腿在修好的门下全部通过。**
3. **规则代价是对称的, 且它咬掉了两个活口。** 同一条 R2 把 **AMI_SLEEVE_ORTHLAG**(0.21 < 0.25)和 **RESID_SHARPE 两个种子**(2025-on 显著为负)判 FAIL。本规则不是为放行候选而造的。
4. **R2 的 0.25 门槛是我选的, 且在役 DL 腿的余量很薄(0.32)。** 这是本规则最脆的一格: 若门槛定在 0.35, 在役 DL 腿会 FAIL, 而那将是"关于在役书的发现"而不是可以调走的参数。我把 0.25 写死在这里, 并把这一格登记为**已声明的敏感点**, 任何以后想动它的人必须先解释为什么不是在事后挑门槛。

## §8 复跑命令(逐字)
```
# GATE P
ssh pod2; cp /workspace/uplift_2026-09-11/w10_sleeve.py /workspace/uplift_2026-09-11/r3_gates/w10_dev.py
C=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
S=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="CAL=log LEGS=101 PHI=0.45 LOOK=900 WRULE=msharpe MEMBERS_TOPN=829 FTRIM=zero UMASK_SCOPE=m1 \
 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz COSTB_JSON=$C SLOW_NPY=$S"
for s in 42 2027; do
  /workspace/uplift_2026-09-11/r3_gates/run.sh GP_dyn_s$s  $COMMON FSEED=$s FPRED=f10_A0_s$s.npy
  /workspace/uplift_2026-09-11/r3_gates/run.sh GP_fix_s$s  $COMMON FSEED=$s FPRED=f10_A0_s$s.npy W3FIX=0.21,0,0.79
done
# spectra and echo
/workspace/venv/bin/python /workspace/uplift_2026-09-11/r3_gates/offspec.py
/workspace/venv/bin/python /workspace/uplift_2026-09-11/r3_gates/echo2.py
```
