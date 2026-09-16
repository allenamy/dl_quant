> **创建:** 2026-09-16 05:0xZ | **Session:** FX-MODEL (fix worker, teammate of team-lead) | **状态:** **FROZEN 2026-09-16 05:1xZ** on the lead's instruction — this file's own sha256 is recorded in the freezing commit message (a file cannot contain its own hash). No model-layer or book-layer number of this experiment existed at the freeze. | **作废条件:** a pinned input sha in §3 changes, or an `AMENDMENT_<n>` is committed stating its reason BEFORE the numbers it affects

# PREREG — what fixing the model inputs does (FEA-01 · TIM-01 · TRN-06), three arms, King and DL split

Owner: FX-MODEL. Covers **TRN-06** by agreement with fx-train (recorded in `FX_MODEL/STATE_PAUSE.md` §7 / commit `126b369c`): FX-MODEL writes the single prereg; fx-train keeps TRN-10, TRN-11 and the chain wiring.

Binding authority for the design: the independent review `docs/REVIEW_fixprogram_progress_2026-09-14.md` (commit `9f6384fb`, file sha256 `cd3bdb88ac0e759e…`) §3.3 and §9, and the lead's ruling FIXPROGRAM §12.3-5.

---

## §0 Freeze discipline

### §0.1 Freeze
This file is **FROZEN** as of the commit that changed its 状态 line above; that commit message records this file's sha256 as frozen. Nothing further is added: a prereg that keeps growing is a prereg being tuned. Every change made between the draft and this freeze was a **constraint discovered**, not a design change wanted — the seed whitelist divergence (§4), the arm-B checkpoint asymmetry (§2.1), and the three additions the lead required (§9.5, §11, and fx-train's review of §7–§8). No estimand, arm, fold, seed, threshold or judgement rule may change after that without a numbered `AMENDMENT_<n>` committed **before** the numbers it affects, stating the reason. Restating a pre-registered criterion in clearer words is not an amendment; changing what it selects is.

### §0.2 What I have already seen — declared, not assumed absent
The CFG-06 precedent (FIXPROGRAM §12.4) is that an unverified "nobody has looked" claim is worse than a disclosed reading. Everything FX-MODEL has computed on this axis before this freeze:

| Seen | Value | Layer | Receipt |
|---|---|---|---|
| Funding support sets and cell-level v1 vs v2ext agreement | 450 vs 825 names; on common cells **bitwise equal**, max\|Δ\| 0.0 | panel | `FACTS_DATA.json` F1/F4 |
| Share of DL member pairs with funding 0 while v2ext finite | 34.15 / 33.96 / 33.63 / 24.72 / 13.94% | input | F2 |
| King clock score skew, same booster, same members | Spearman median 0.9865 / 0.9866 | **score** | T1 |
| King member-set difference under the two clocks | 206 of 10,182 anchors | membership | T1 |
| Non-crypto member share | 7.2639% of 2026 | membership | U1 |
| Dead-member and forward-removal counts | 255/126/1,250/762/304 and 33/3/1/3/3 | membership | AUDIT_DATA TRD-05, fx-train |
| King axis starts at E = 2016; 30 early anchors absent | 30 anchors | membership | §3.0 of FACT_TABLE_MODEL |
| Red tests on the legacy builders | 8/8 RED_CORRECT | input | `RED_BUILDERS.json` |
| New-builder legacy arms reproduce the bases | bitwise PASS (X 1,308,638 cells; FEA 1,134,880 cells) | input | `NEWBUILDER_CONTROL.json`, `KING_CONTROL.json` |
| Input-layer effect of the funding fix | **606 cells** changed on the fixture | input | `NEWBUILDER_CONTROL.json` C3 |
| Input-layer effect of the king knobs | +2 / +0 / +30 anchors | input | `KING_CONTROL.json` K3 |
| **UNI-01 inverse pairs (run after this section was drafted, 2026-09-16 04:4xZ)** | returns ρ −0.987; **score-rank ρ +0.06 / +0.27**; opposite-leg 0.364 / 0.255 vs null 0.479; gross share ~0.5% | **score / rank-z** | `UNI01_PAIRS.json` |
| UNI-01 counterfactual: drop non-crypto | normalised rank displacement median 0.0062, p95 0.0445 | rank-z | `UNI01_PAIRS.json` |

**None of these is a model-layer or book-layer number on the contrast this prereg judges.** The two UNI-01 rows are score/rank-layer readings on a **different axis** — UNI-01 is held fixed in every arm below (§9), so they are not a reading on any arm. They are listed because they were computed after this section was first drafted, and a freeze declaration that silently excludes later work is the CFG-06 failure. The two "effect" rows are cell and anchor counts on a synthetic fixture, and both receipts label them as such in the artifact itself. The score-layer row (T1) is a clock contrast on a **fixed** booster with no label — it is not any arm below. I have seen **no** OOF IC, no P&L and no book reading for any arm.

Prior beliefs I am **withdrawing** so they cannot act as an unstated hypothesis: my pause note said "a lower OOF IC after FEA-01 is expected, because the flag carries forward information". The review's narrowing (i) shows the evidence does not support predicting a direction — the per-year Spearman of the flag is **sign-inconsistent** (−0.0031 / +0.0018 / −0.0041 / +0.0059 / −0.0079). **This prereg predicts no direction.**

---

## §1 The question, stated so it can fail

> When the model inputs are corrected, does the resulting model produce a **better book**, on the accounting caliber, out of sample, with an interval that excludes the equivalence band?

Not "do the scores change" — we already know they do, and the review is explicit that a score correlation is neither a return IC nor evidence of lost alpha. The judged object is the **book**, with the score layer reported as a secondary, clearly-labelled reading.

---

## §2 Arms — three, not two; King and DL split, plus a combined arm

Per review §9 and §3.3. For each model family (King, DL) and for the combination:

| Arm | Input | Model | Normalisation |
|---|---|---|---|
| **A** | old (as trained in September) | old checkpoint | the checkpoint's own, as trained |
| **B** | **new** | **old checkpoint, weights frozen** | **training-time mu/sd, feature order and support all frozen together** |
| **C** | **new** | **retrained on the new input** | each fold's own mu/sd, computed by the trainer's own rule |

Arms, named for the record:

| id | family | input change |
|---|---|---|
| `KA` / `KB` / `KC` | King | TIM-01 clock aligned to serving (`FMK_CLOCK=serve_E`) |
| `DA` / `DB` / `DC` | DL | FEA-01 funding rebuilt from the full-coverage panel (`FMF_PANEL` = the 829-name panel, `FMF_FUND_FILL=legacy_zero`) |
| `XA` / `XB` / `XC` | combined | both of the above together |

**Explicitly not accepted, and not run**: running the in-service model forward over its own training span, or comparing two old predictions that share the same bias. Both are named in review §9 as inadmissible substitutes.

### §2.1 Arm B is conditional on a control that may fail
A fixed-checkpoint forward diagnosis must freeze weights, training-time mu/sd, feature order and support **together** (review §3.3). The facts, from `FACT_TABLE_MODEL.md` §1.3:

- **DL**: the monthly walk-forward fold checkpoints store a **bare state_dict** — no mu/sd, and none in their config. The in-service refit does carry mu/sd but is trained through 2026-08-30, so it cannot be the out-of-sample forward model.
- **King**: LightGBM is fit on raw features, so there is **no normalisation to freeze** — the objects to freeze are the feature order (`PINS["keep_names"]`, asserted at `pod_export_bundle_v4.py:47`) and the support. Only the shipped 2026 booster was saved; the 2024/2025 fold boosters were never written to disk.

Both families therefore require **reconstruction**, and reconstruction is inadmissible until certified:

> **GATE B-REPRO.** For each fold, recompute the training-time mapping on the **OLD** input by re-running the trainer's own calibration lines, then score the OLD input through the saved checkpoint. The result must reproduce that fold's stored OOF predictions — DL to the trainer's own asserted tolerance (`test_vs_all_maxdiff` ≤ 1e-5, `pod_f10_train_monthly_v4.py:433`), King bitwise on the stored `PRED`.
> **If GATE B-REPRO fails for a family, arm B is NOT AVAILABLE for that family and will be reported as unavailable. It will not be substituted, approximated, or replaced by the refit checkpoint.**

The DL calibration is RNG-free and precedes seeding, so exact reconstruction is expected; that expectation is not a licence to skip the gate.

### §2.2 Naming discipline, pre-committed
If mu/sd is recomputed on the **new** data, that is **a different intervention on the input mapping** and will be named `B'` (arm B-prime), reported separately, and never described as "only the raw features changed". Arm C may use its own per-fold mu/sd because it is a training arm.

---

## §3 Pinned inputs

| Object | sha256 | Role |
|---|---|---|
| `tradability_v1.npz` | `54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302` | TRN-06 arm only; states `0 NODATA / 1 UNTRADED / 2 TRADABLE` (`common/tradability.py:24`) |
| `wide_panel_4h_v3splice.npz` | `c5d10f6ae31fa3f9…` | the OLD funding source |
| `wide_panel_4h_v2ext.npz` | `5e67c0559daa904d…` | the NEW funding source (825-name coverage) |
| `dlw_ext/data/dlw_fea82.npz` | `9bc111a47cee54fc…` | the OLD DL features (the fold configs name this sha) |
| in-service king booster | `8d79186b6380132c…` | |
| v4 king booster | `f23657710f3a6d00…` | |
| Column-80 caliber | **v0** | FX-PROD ruling; training stays v0 |

Builders, with their legacy arms already certified bitwise:

| Builder | sha256 | Legacy-arm control |
|---|---|---|
| `fm_dlw_features_fund.py` | `3327c007d1199bcf…` | `NEWBUILDER_CONTROL.json` C2 PASS |
| `fm_king_fea_asof.py` | `25beff11835755e4…` | `KING_CONTROL.json` K2 PASS |
| `fm_dlw_targets_asof.py` | *to be built; knobs named in §8* | its own control must PASS before use |

---

## §4 Folds, seeds, label maturity, embargo

- **DL folds**: the 20 monthly walk-forward folds `202501 … 202608`, tag `mE1` (embargo 1 anchor). The `mE60` tag is a **sensitivity column only**, not a second primary reading.
- **King folds**: the yearly folds the exporter defines — 2024, 2025, 2026. King has **zero embargo** (`tr_ = YRA < YV; te_ = YRA == YV`); that is a fact of the existing design, is stated here, and is **not** changed by this experiment.
- **Seeds and the trainer this constrains us to** (established 2026-09-16, before the freeze — this corrected an earlier draft that simply said "42 and 2027"):

| trainer | sha256 | seed whitelist | per-fold RNG | data dirs pinned to |
|---|---|---|---|---|
| in-service lineage `pod_f10_train_monthly.py` | `7bb39f8d93f2daf7…` | **`SEED == 42` only** | `manual_seed(SEED + YM)` — **varies per fold** | `dlw_ext` / `f8_ext` (hard) |
| v4 chain `pod_f10_train_monthly_v4.py` | `fd5707bd3acccdbb…` | **`SEED in (42, 2027)`** | `manual_seed(SEED)` — **constant every fold** (`mE1_constseed`, addendum §11) | `V4_DLW_RAW` / `V4_F8`, **env-overridable by design** |

  Both assertions are deliberate E-0826-D env whitelists. Consequences, pre-committed:
  1. **Two-seed arms run on the v4 chain trainer only.** The in-service-lineage trainer cannot take seed 2027 without a trainer change, and trainer changes belong to fx-train, not to me. I will not widen an E-0826-D whitelist to make an experiment fit.
  2. So arms `DA/DB/DC` and `XA/XB/XC` use **`pod_f10_train_monthly_v4.py`**, with `V4_DLW_RAW` / `V4_F8` pointed at this experiment's output dirs — which that trainer supports by design, unlike the hard-pinned one.
  3. **The two trainers disagree on the fold seeding rule, so "seed 42" is two different objects.** In-service lineage: `manual_seed(SEED + YM)`, varying per fold. v4 chain: `manual_seed(SEED)`, constant every fold. **Readings from the two recipes are never pooled, never averaged and never presented as replications of each other.** Whichever is used quotes its own rule in the receipt. This is a rule of this prereg, not a caveat.
  3a. On widening a whitelist to make an arm fit, stated once and binding: **if the in-service lineage is to take a second seed, that is a trainer change with its own review — not something I do quietly to keep an arm alive.**
  4. Verified across all 40 fold configs: `seed_fold == fold + 42` holds everywhere for the in-service lineage, i.e. its published OOF is a **per-fold-seeded** object.

  Results are reported **per seed**. Multi-seed ensembling and any post-hoc selection across seeds are forbidden (user's hard rule). Before any multi-seed claim the device must first assert the two runs share an identical `self_sha256`.
- **Label maturity, respected explicitly**:

| Object | label rows | completes at |
|---|---|---|
| King legacy label | [E, E+47] | **A + 3h55m** |
| King aligned label | [E+1, E+48] | A + 4h |
| DL label `y4s` | [E+1, E+48] | A + 4h |

The DL trainer's causality assert uses `E_ts + 48*300` = A + 4h, which is exact for DL and conservative for King. **The king exporter's provenance field `king_train_last_label_end_utc` records A + 4h while the legacy label actually ends at A + 3h55m**; the 5-minute overstatement is conservative and is recorded, not silently adopted.
- **Caliber**: accounting caliber is `pod_dlw_targets_ext.py` L93 `y4s = Π(1+r) − 1`. Returns are **never** recomputed from the 5m cache `ret5` channel (hard-clipped at ±0.30). Caliber binds to the panel file, not the variable name (E-0904-F).

---

## §5 Estimand and judgement rule — frozen before any number

**Primary estimand.** Per arm pair (B−A, C−A, and C−B), the difference in **book return in bps per anchor per unit gross**, on the accounting caliber, net of fee, over the fold-out-of-sample anchors only.

**Judgement.** By the shared module `multi_asset/exports/research/common/equivalence_labels.py` (`ab651754208e62a9`) with the programme's frozen δ:

- **Book layer: δ = 0.05 bps/anchor/gross** (FIXPROGRAM §4.1 D1). One δ per unit per programme.
- A no-difference verdict may be issued **only** by the equivalence band. CI ∋ 0, or a point estimate inside the band whose interval leaves it, ⇒ **INCONCLUSIVE / NOT ESTABLISHED**, never "NOT MATERIAL".
- A LOSS label only where that book's realised mean is < 0.

**Secondary, clearly labelled, never the decision**: per-asset Pearson and cross-sectional rank IC at the score layer, with ΔIC δ = 0.003 (score layer only; explicitly **not** a book-layer economic criterion). Collapse guard σŷ/σy ≥ 0.02.

**Uncertainty.** The 4-hour label over a 4-hour anchor grid does not overlap, so plain day-block bootstrap is admissible; the sampling unit is the **UTC day block**, and the interval is reported with its unit named. Where any reading is made on an overlapping-horizon quantity, the calibration in `overlapping_24h_target_inference_calibration` applies instead.

**Replay readings carry their label.** Any book reading from the research replay is labelled **"uncertified replay"** unless it comes from the certified production-path device; §12.2 of FIXPROGRAM and the S2 precedent apply.

**Ranking is not net.** A score-layer admission is necessary and not sufficient; the book-layer net interval decides (five cases on file).

---

## §6 Leak and sanity checks — all must pass before any arm is read

1. shuffle-future control;
2. offset spectrum peaked at 0;
3. zero out-of-fold leakage;
4. per-fold causality assert printed (the trainer already does this);
5. **GATE B-REPRO** (§2.1) for arm B;
6. legacy-arm bitwise control for every builder used (§3);
7. σŷ/σy ≥ 0.02 collapse guard.

---

## §7 TRN-06 — the population axis, two channels, two arms

The two channels are **different populations and must not be summed** (`FACT_TABLE_MODEL.md` §5.2):

- **Channel B, look-ahead**: membership currently requires `isfinite(y4s)`, so a property of the future decides whether a row is trained on. Red test `R-TRD-1` demonstrates it interventionally: two caches identical on every row ≤ E, differing only after the anchor, produce different member sets.
- **Channel A, contamination**: a delisted contract's frozen rows are finite `0`, so it stays a member with a label of exactly 0. Red test `R-TRD-2`.

**Removing B without a tradability screen makes A worse.** Therefore two arms, not one:

| id | change |
|---|---|
| `T1` | `FMT_FORWARD_TERM=trailing_only` — membership becomes trailing-only, matching production |
| `T2` | `T1` **and** `FMT_TRADABLE=<tradability_v1.npz>` — trailing-only plus the tradability screen |

Reported jointly so the coupling is visible. The tradability artifact is used as a **labelled admission screen only, never as a settlement truth** (FXR-DATA-1): exit P&L for a dead contract stays explicitly unknown.

---

## §8 `fm_dlw_targets_asof.py` — knobs named in advance

| knob | values | legacy value |
|---|---|---|
| `FMT_MEMBER_CLOCK` | `legacy_Em1` \| `serve_E` | `legacy_Em1` (rows [E−2016, E−1]) |
| `FMT_FORWARD_TERM` | `legacy_isfinite` \| `trailing_only` | `legacy_isfinite` |
| `FMT_TRADABLE` | `off` \| `<path>` (+ required `FMT_TRADABLE_SHA`, asserted) | `off` |

All required, no defaults. The legacy combination must reproduce `pod_dlw_targets_raw.py`'s output bitwise before the builder is used for anything.

---

## §9 Out of scope — separate interventions, deliberately not bundled

Review narrowing (iii): changing these together with the funding rebuild makes the funding fix's effect unidentifiable. Each is held **fixed at its legacy value** in every arm above, and gets its own prereg if pursued:

1. **UNI-01** non-crypto members (~7.26% of 2026), including the two leveraged inverse pairs SOXL/SOXS and TQQQ/SQQQ;
2. the **availability bit** as a new input column (widens 82 → 84);
3. the **member universe** choice (829 vs U-PIT∧CRYPTO vs live-450) — and note **live-450 is forbidden**: back-applying the 2026-08 list to history reproduces FEA-01 on the membership axis;
4. `FMK_MEMBER_CLAMP` and `FMK_COVR_DIV` — held at legacy in the `K*` arms; the K3 reading shows they are two distinct interventions (+2 / +0 / +30);
5. the column-80 v0/v1 serving change (FX-PROD's P1/P2, committed not deployed);
6. `nan_preserve` as a fill rule — a real knob (§ FACT_TABLE §1.3(b)) but a third arm, reported separately if run.

---

## §9.5 A known prior from the independent researcher — declared before the fact, with what would contradict it

Recorded at the lead's instruction so it cannot later be produced as a surprise, and so the reaction to a disagreement is fixed **in advance**.

**Their result** (interventional, their prereg `7fbb57ab` frozen first; 18 models = 3 arms × 3 folds × 2 seeds; 400 trees, 78 inputs, 60-anchor embargo), on the OLD / REPAIRED / ZERO contrast of the funding columns:
- **Repairing the funding columns buys no stable ranking gain** — 5 of 6 rows have CIs spanning zero, row-wise between **−0.0013 and +0.0006**.
- **Zeroing both columns entirely costs only about 0.002 IC.**

**Their own scope limitation, carried verbatim rather than paraphrased away**: that is a **King structure run on DLW features, with features that include E and a target at E+4h** — it is **"not a replay of the original exporter's clock/label"**. So it is **not the same contrast** as arms `DA/DB/DC` here, and the two must not be pooled or treated as replications of each other.

**Why it is written here, and what it does NOT license.** It is **not** a target to steer toward. Its purpose is the opposite:

> **If this experiment measures a funding-fix effect far larger than theirs, that is a contradiction between two instruments and is a reason to STOP and reconcile them — not a good-news result to publish.** On such a disagreement the required action is: report both readings and their receipts, state that they are different contrasts, and identify which of (clock, feature support, target window, fold structure, embargo, seed rule) differs, **before** any interpretation is offered.

Equally pre-committed, so the rule cannot be applied only when convenient: a result **consistent** with theirs — a small effect whose interval spans zero — is **not** evidence that the input defect does not matter. It is evidence about ranking gain at the score layer under their configuration. FEA-01's justification was never "it will raise IC"; it is that a future-derived availability flag has no business in training inputs.

## §10 Stopping and failure rules

- If **GATE B-REPRO** fails for a family, that family's arm B is reported **UNAVAILABLE**, with the failure numbers. No substitute.
- If any leak check in §6 fails, **no arm is read** until it passes; the failure is reported.
- If a builder's legacy-arm control fails, that builder is not used.
- A null result is a result. "No difference beyond δ" will be reported as such, and the programme does not acquire a new arm in order to find an effect.
- GPU: only when free, never preempting; queue and announce first; never touch PIDs 333197 / 339489.

---

## §11 What this experiment cannot answer

Stated now so it is not claimed later:

- It cannot establish the strategy's historical level or Sharpe. The review's central finding stands: no evidence chain yet satisfies *point-in-time data ∧ train/serve same definition ∧ per-fold out-of-sample ∧ continuous whole-book production parity ∧ closed exit accounting* simultaneously. This prereg addresses the second of those five, and only for two inputs.
- It cannot attribute any live P&L. The replay is not the live book.
- With 20 monthly DL folds and 3 yearly king folds, small book-layer effects will not be resolvable; the δ band, not the p-value, states what counts.
- **It says nothing about whether the non-crypto names hurt the book, because they are still in it.** §9 holds UNI-01 at its legacy value, so every arm above is measured with the two 3× inverse pairs (SOXL/SOXS, TQQQ/SQQQ) and all 80 non-crypto member names **still in the training population**. That is the right choice for identifiability — one intervention at a time — but it has a cost that must not be lost: **this experiment must never be cited as evidence that the universe is fine.**
  **Two facts settled 2026-09-16 that bound this reservation precisely:**
  - **The independent researcher's cash book excludes EQUITY perps**, using the **same class snapshot** (`fa9196a3…`) we use; the 149 names it excludes equal our `noncrypto_symbols_on_axis: 149` **exactly**, and rebuilding our UPIT_CRYPTO from it gives **difference 0**. The suspicion that their book holds tokenized stocks is **withdrawn**. **But their training also runs on the 829 axis, and no class filter is applied to the F10 or King member screens on either side** — so **UNI-01's training-side defect holds for both instruments**, and it is a training-population issue, not a book-holdings issue.
  - **The contaminated training year is the one carrying the headline.** Our non-crypto share by year is 0 / 0 / 0 / 2.8e-05 / **0.072639**, i.e. 7.26% of 2026 king-meta member pairs across **all 1,458 anchors** — and the strong half of their 608-day window is **2026 (Sharpe 4.208)**. That does **not** make 4.208 wrong, and the mechanism is indirect (rank labels shift; the book still cannot hold those names). It is a **testable reservation attached to a specific sub-period**, and reading (5) is its direct measurement: removing the non-crypto names (mean **29.06** per anchor) moves surviving names' normalised rank by median **0.0062**, p95 **0.0445**, max 0.1061 — small but not zero, at the **raw z/rank layer only**. Whether that propagates to the book is **not measured and not claimed**.

  Note also what the 2026-09-16 measurement did and did not settle. It **refuted** the mechanism I had inferred: the book does *not* hold the inverse pairs on opposite legs (score-rank ρ **+0.06 / +0.27**, opposite-leg rate **0.364 / 0.255**, both *below* the null median **0.479**), even though the pairs really are near-exact return inverses (ρ −0.987). What it leaves open is a **different and unmeasured** concern — the equity-perp cluster is scored *alike* while its returns move *oppositely*, which would damage rank-IC on those names rather than create directional exposure. **Neither the refuted mechanism nor the open one is tested by any arm in this prereg.**
