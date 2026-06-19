# DECISIVE BASIS TEST — does the basis/cross-venue feature set recover the spot→perp residual and lift perp IC?

> **Created:** 2026-06-19 | **Session:** decisive-basis-test | **Status:** in-progress
> **Workflow:** code LOCAL (`/Users/haosiyu/Desktop/quant_research`, branch `multi-asset`) → run on `jpline`.
> **Verdict discipline:** report NUMBERS at each gate; no GO/NO-GO declaration.

## Mechanism under test (verified)
`perp_y ≈ spot_y` (corr 0.999). The residual `r = perp_y − spot_y` is tiny
(~0.2–0.4% of perp variance, std ~9.6e-5 vs perp_y ~2.1e-3) but is reportedly
−0.27 correlated with a spot-trained model's q50, halving spot→perp transfer
(spot ~0.024 → perp ~0.008 choppy). Question: do basis/cross-venue features that
predict `r` lift perp from ~0.008 back toward/above 0.024?

Correct leak-free target = `data/npz_spot2perp_clean` (== `data/npz_perp_target_v2`,
byte-identical). Inputs = `data/npz_spot` (spot-64 X + X_raw + regime_prior + ts).

---

## Step 0 — trainer fix (`multi_asset/train/train_dual_lob.py`)

- `ema_decay` default = **0.999** (was already 0.999 in the committed file; the
  degradation to 0.995 lived only in the *configs* `perp_base_roll`/`perp_dualsrc_roll`
  — my new fold-0 configs all use 0.999).
- σ-gate fallback (when NO epoch reaches σŷ/σy ≥ 0.02):
  - **best_model.pt** = RAW best-composite over ALL epochs (was already correct).
  - **ema_best.pt** = best-composite over **WARMED** EMA epochs only
    (`epoch ≥ ema_warmup_epochs = max(2, warmup_epochs)`), so a flukey high
    composite at the init-dominated **epoch 1** EMA (flat, σ~0) is NEVER persisted
    (the bug: prior run saved EMA epoch-1, flat). If no warmed EMA epoch exists,
    fall back to the **RAW best** (spec).
  - Records `ckpt_provenance.{best_source, ema_source}` + saved σ in metrics.json.
- Confirmed `train_dual_lob` runs plain REG_arch (`use_perp_residual` absent ⇒
  OFF, byte-identical to `DualPathLOBModelV3`), 64 feats, d_prior=6.
- **Smoke test (3 ep × 8 steps): PASS** — exit 0; fallback fired correctly:
  `best_model.pt` = RAW best @ ep1, `ema_best.pt` = WARMED EMA @ **ep2** (NOT ep1).
  Forward ran with `perp_a=+0.0000` (no perp residual).

---

## GATE A — trainer sanity: spot→spot choppy (MUST ≈ 0.022–0.025) — PASS (val)
Config `configs/v5push/perp_gateA_spot2spot_choppy.json` (npz_spot, spot y_600,
test 2026-01, train 400d/val 60d/embargo 1, EMA 0.999, preload=true, ep25, pat10).

**RESULT (val caliber): PASS.** Best raw val Pearson peaked **+0.0259** (S +0.0287,
C +0.0273, sigR 0.034, β 0.73–0.82) at ep7–8 — matches reg_arch_spot_roll2026
fold-0 reference (0.0247). EMA converging (C +0.0183 @ ep10). ⇒ the FIXED trainer
reproduces the proven spot→spot signal; Step-0 degradation is resolved. Test-set
`perp_battery` (dense+clean, EMA+BEST) confirming via the autonomous orchestrator
(`logs/orchestrate.log`).

---

## Step 2 — perp baseline: spot-64 → correct perp target (expect ≈ 0.008–0.012)
Config `configs/v5push/perp_baseline_choppy.json` (== Gate A but npz=
`data/npz_spot2perp_clean`, ep12). Choppy fold-0.

**RESULT:** _AUTONOMOUS — running after Gate A via the detached orchestrator
(`/tmp/orchestrate_decisive.sh`, PPID=1); number lands in `logs/orchestrate.log`._
Ridge analog (lastts spot64 → clean perp_y, walk-forward): **+0.0084 choppy** /
−0.0057 strong — the spot→perp transfer level (the residual r mis-signed by the
spot signal halves it from the ~0.022 spot number). σ expected low (fallback may
fire — the trainer now records ckpt_source + saved σ).

---

## Step 3 — basis / cross-venue feature design + Ridge gate (vs residual r AND perp_y)

### Feature design (mechanism-grounded, ≤t, computed as 600-step sequences)
Built two routings (prior session's `build_dualsrc_npz.py`, RevIN-aware):
- **DIFFERENCED / flow → x_feat (RevIN-safe, ~zero-mean):** `div_cumflow30`,
  `div_microprice`, `div_netflow_z`, `basis_ema_dev` (basis − causalEMA60),
  `basis_mom` (300s).
- **LEVEL → regime_prior FiLM (un-normalized; RevIN would destroy levels):**
  `basis_bps`, `basis_z` (causal 30-min), `spread_ratio`, `div_obi_L5_level`.
Caches on disk: `data/npz_dualsrc` (X 69ch + regime_prior 10col, base = clean
perp target, 730 days 2024-06→2026-05). Also `data/basis_cache` (4 basis factors
at pred-index) + `data/lastts_cache` (spot_last/perp_last 64 each).

### Ridge gate vs the RESIDUAL r  (`multi_asset/eda/perpY_basis_residual_gate.py`)
Leak-free, CLEAN caliber (stride≥600), walk-forward, per regime.

**CHOPPY (151 days, N_clean=17,969; r_var/perp_var=0.0022; corr(spot_y,perp_y)=0.9989):**

| factor | vs r (P / S) | vs perp_y (P / S) |
|---|---|---|
| basis_bps | −0.442 / −0.457 | −0.006 / −0.008 |
| basis_z | **−0.553** / −0.595 | +0.003 / −0.009 |
| basis_mom | −0.412 / −0.436 | +0.011 / −0.003 |
| basis_ema_dev | −0.503 / −0.532 | +0.009 / −0.009 |
| ps_obi_diff_L5 | +0.269 / +0.313 | +0.002 / +0.006 |
| ps_microdev_diff | +0.018 / −0.082 | −0.004 / +0.017 |
| ps_cumflow_diff | −0.056 / −0.070 | −0.016 / +0.006 |
| spot_flow_lead | +0.006 / +0.018 | +0.017 / +0.006 |
| perp_spot_vol_r | −0.012 / +0.013 | −0.007 / −0.005 |
| perp_spot_spr_r | −0.024 / +0.309 | +0.017 / −0.002 |

- **Multivariate Ridge r-IC (walk-forward, pooled OOS):**
  basis4 vs r = **+0.5724** (S +0.615) | xvenue6 = +0.262 | all10 = **+0.5732**.
  Same factors **vs perp_y**: basis4 = −0.015, xvenue6 = +0.012, all10 = −0.004.
- Null band (97.5pct |r-IC|) = 0.019 → all10 |r-IC| 0.573 ≫ band (**not noise**).
- Shift sentinel: basis4 r-IC unshifted +0.572, **+600s-shifted +0.226** (shift
  HURTS ⇒ unshifted alignment is causal-correct, **leak-free**).

**STRONG (58 days, N_clean=6,902; r_var/perp_var=0.0018; corr 0.9991):**
basis4 vs r = **+0.5862** (S +0.582) | xvenue6 = +0.347 | all10 = +0.5855.
vs perp_y: basis4 −0.026, all10 −0.042. Null 0.032 → 0.586 ≫ band. Shift
sentinel +0.586 → +0.324 (leak-free).

### The crux: r-prediction is excellent, but does it lift perp_y?
Direct Ridge on perp_y (lastts spot-64 caliber):
| | spot64→perp_y | +basis4 (JOINT) | ΔP |
|---|---|---|---|
| CHOPPY | +0.0084 | +0.0071 | **−0.0013** |
| STRONG | −0.0057 | −0.0112 | **−0.0055** |

**JOINT mixing of basis into the perp_y regression HURTS.** But the
mechanistically-correct **two-stage / ADDITIVE** form (`perp_ŷ = spot_ŷ + basis_r̂`):
| | spot64→perp_y | +ORACLE true r (ceiling) | +basis_r̂ (additive) |
|---|---|---|---|
| CHOPPY | +0.0084 | +0.0178 | **+0.0158** |
| STRONG | −0.0057 | −0.0068 | −0.0123 |

→ **Choppy: additive basis lifts perp 0.0084 → 0.0158 (+0.0074, ~89% of the
oracle ceiling 0.0178).** Strong lastts baseline is itself broken (−0.006), and
even the oracle barely moves it, so r-recovery can't help there at this caliber.

**Mechanism conclusion:** basis genuinely carries r (0.57 Ridge IC, leak-free),
but r is only ~0.2% of perp variance, so the absolute perp lift is bounded to
~+0.01 even with a near-perfect r̂, AND it only materializes when the model
**adds** the basis residual to the spot prediction — feeding basis as ordinary
(joint-mixed) input features HURTS. Routing is decisive.

---

## GATE B (decisive) — perp + basis (DL) vs perp baseline

Configs: `perp_dualsrc_choppy.json` (spot64 + 5 div channels in x_feat + 4 LEVEL
via FiLM d_prior 10; RevIN-fixed) and `perp_basis_choppy.json` (npz_dualbasis,
4 basis-seq channels joint, d_prior 6) — both vs `perp_baseline_choppy.json`.
EMA 0.999, fixed trainer, choppy fold-0, ep12.

**RESULT:** _AUTONOMOUS — running after Gate A + Step 2 via the detached
orchestrator; dense+clean Pearson/σ/β land in `logs/orchestrate.log` +
`logs/{gateB_dualsrc,gateB_basis}.log`._

**Prediction from the (model-independent, decisive) Step-3 Ridge gate:** at the
linear caliber, JOINT-mixing basis into the perp_y regression HURT (ΔP −0.0013
choppy); only the ADDITIVE form lifted it (+0.0074 → 0.0158, ~89% of the 0.0178
oracle ceiling). The DL `dualsrc` config routes the differenced channels JOINTLY
(x_feat → GDCN-mixed) and the basis LEVELS via FiLM (modulation, the closest the
graph gets to additive). So the DL Gate B is **expected to lift perp only
marginally if at all** (bounded by r ≈ 0.2% of perp variance ⇒ ceiling ~+0.01);
a clean additive **residual head** (basis → r̂ added to the spot q50) would be the
architecture to realize the full +0.0074 — a recommended follow-up, not in scope.
The DL numbers will confirm or refute this.

> Note on prior attempts: the previous DL dual-source roll (`perp_dualsrc_roll`/
> `perp_roll_dualbasis`, ema 0.995) was **never completed — OOM rc=137** at fold 0
> (preload=true @ 605 days). My fold-0 configs use 400 days (fits) + the fixed
> trainer. A data bug noted: `npz_dualsrc` X ch64/65 (div_cumflow30, div_microprice)
> are all-zero on some days (e.g. 2026-01-15) — but these are weak r-predictors
> (−0.056 / +0.018 vs r); the dominant basis signal (ch67/68 + FiLM levels) is intact.

---

## Honest observation (so far)
The basis **does** recover the residual the spot model mis-signs (r-IC 0.57,
leak-free, both regimes) — far above the ~0.2–0.3 expected. BUT the perp lift is
structurally capped near **+0.01** (choppy 0.008 → ~0.016 at Ridge additive
caliber) because r is a vanishing fraction of perp variance, and ONLY via an
additive/residual structure — joint feature-mixing hurts. The DL Gate B asks
whether the conformer (basis-as-x_feat + FiLM levels) can realize the additive
gain the linear joint-Ridge could not.
