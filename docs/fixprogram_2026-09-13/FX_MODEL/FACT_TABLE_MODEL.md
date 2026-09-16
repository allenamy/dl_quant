> **创建:** 2026-09-16 03:5xZ | **Session:** FX-MODEL (fix worker, teammate of team-lead) | **状态:** 事实表, append-only by section; each section is committed before the red tests and before any fix code of its item | **作废条件:** a cited file sha changes (every row carries its sha16), or the pinned artifact shas in §0 change

# FACT_TABLE_MODEL — FX-MODEL items (AUDIT_DATA bb8a2806 FEA-01 / TIM-01 / UNI-01 / TRD-05, AUDIT_PROD 57f7e2be PROD-11; TRN-06 coordination)

Legend, used on every row:
- **VERIFIED** — read at the cited line, or computed by a device listed in §0.2 whose receipt is committed. Arithmetic identities over committed receipt counts are VERIFIED and say so.
- **INFERRED** — reasoning from verified facts; not measured.
- **NOT CHECKED** — stated so that nobody reads it as checked.

Conventions:
- `sha16` = first 16 hex of sha256. Research-repo files are hashed on the working tree at the stated commit; `pod2:` rows are hashed on pod2.
- This table answers the independent review's input-parity gate (`REVIEW_fixprogram_progress_2026-09-14.md`, commit 9f6384fb, file sha256 `cd3bdb88ac0e759e…`, §9 row "输入平价"): **per column** — clock, unit, dtype, mask, membership, normalisation, and the sha actually consumed; full support or a cell-by-cell account of the difference. A finite-intersection summary, a total correlation, or "same function name" is not accepted and is not used here.

## §0 Frozen objects

### §0.1 Pinned inputs (not rebuilt by me)

| Object | sha256 | Provenance |
|---|---|---|
| `tradability_v1.npz` | `54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302` | FX-DATA run 2; 2,501,576 bytes, 10,285 anchors × 829 names; device 066c3d74 / module a9fad82c / spec 99ae35e0. **Re-hashed by me 2026-09-16 03:3xZ** at `docs/fixprogram_2026-09-13/FX_DATA/artifacts/tradability_v1.npz` (commit `b4d60d73`): exact match, not an iCloud-evicted stub. VERIFIED |
| Funding-interval table | `366763a4` | FX-PROD P9 declared table; EXACT / LIKELY / undecided kept distinct. A LIKELY row is a guess, never a correction |
| Column-80 training caliber | v0 | FX-PROD ruling: training stays v0 for king and V2MAIN, serving is changed to match training. fx_prod clone `633d44b` (P1) / `15921c0` (P2); research `e0e49f8e`. **Committed and tested, NOT DEPLOYED** |

### §0.2 My own devices and receipts (commit chain `74cb2e66` → `a1c16b73` → `6b09524b`)

| File | sha16 | Role |
|---|---|---|
| `FX_MODEL/devices/fm_facts_code.py` | `e965501ea997a8ee` | Mac, read-only code anchors; 18 rows / 67 anchors, rc 0 |
| `FX_MODEL/devices/fm_facts_data.py` | `4d9df5565b0d3b6a` | pod2, read-only; computes no IC and no return |
| `FX_MODEL/receipts/FACTS_CODE.json` | `75fa15e6f31506b3` | rows C-FEA-1..6, C-TIM-1..6, C-UNI-1..2, C-TRD-1..3, C-P10-1 |
| `FX_MODEL/receipts/FACTS_DATA.json` | `9a7127d3846debce` | F1 / F2 / F3 / F4 / U1 / T1; pod2 15:07:59–15:08:54Z, rc 0 |
| `FX_MODEL/receipts/FACTS_CODE.attempt1_…overstated.json` | `7f72759d4d4123db` | withdrawn attempt-1 C-FEA-4 claim, kept |

### §0.3 Data objects cited below

| Object | sha16 | Note |
|---|---|---|
| `pod2:/workspace/data/wide_panel_4h_v1.npz` | `f14bc33d78b24929` | canonical v1; axis 2020-01-31 00Z .. 2026-08-15 00Z, 14,329 rows |
| `pod2:/workspace/data/wide_panel_4h_v2ext.npz` | `5e67c0559daa904d` | 829-name extended; axis 2022-01-31 00Z .. 2026-08-31 00Z, 10,039 rows |
| `pod2:/workspace/data/wide_panel_4h_v3splice.npz` | `c5d10f6ae31fa3f9` | the panel the DL builder consumed; axis 2020-01-31 00Z .. 2026-08-31 00Z, 14,425 rows |
| `pod2:/workspace/live_pins.json` | `fd27fe485417d307` | `symbols_live`, 450 names (COIN 449 + INDEX 1) |
| `pod2:/workspace/dlw_ext/data/dlw_fea82.npz` | `9bc111a47cee54fc` | **in-service** DL features |
| `pod2:/workspace/dlw_v4raw/data/dlw_fea82.npz` | `40608701cad1aea1` | v4 candidate DL features |
| `pod2:/workspace/dlw_ext/data/dlw_targets.npz` | `31d043e8f160a1d4` | in-service DL targets |
| `pod2:/workspace/f8_ext/data/f10v2_legs.npz` | `facf53f7355da98f` | in-service legs (Z24 / ZFD / WL) |
| `pod2:/workspace/f8_v4/data/f10v2_legs.npz` | `c535decd6524b091` | v4 legs |
| `~/wide_shadow/fea171/f10_live_s42_np.npz` | `351ae26bd6b4a203` | **in-service DL weights**, carries `mu` / `sd_` |

---

## §1 FEA-01 — the DL funding columns were built from a panel whose support is the 2026-08 live list

**AUDIT_DATA severity P1.** Statement of the defect, in one sentence: fea82 columns 80 and 81 were built from a panel whose funding support is exactly the 450 names of the 2026-08 live list, so for every 2022–2025 training row the presence of a funding value is a fact about 2026 — and the builder writes the absent values as a hard `0.0` that is indistinguishable from a true zero.

### §1.1 Per-column parity — training vs serving, on the seven axes

Columns in scope: **col 80 = `fund_ema`**, **col 81 = `fund_now`** of `dlw_fea82.npz`. There is no availability column; 82 = 40 VAL × 2 (value, rank) + 2 funding (`pod_dlw_features_ext.py:76` asserts `NF == 82`).

| Axis | Training (what the model was fit on) | Serving (what production scores) | Same? | Status |
|---|---|---|---|---|
| **sha actually consumed** | `F171_PANEL` = `wide_panel_4h_v3splice.npz` `c5d10f6ae31fa3f9`. Recorded by the builder itself into `dlw_features_report.json` as `panel_sha256` for **both** `dlw_ext` (in-service) and `dlw_v4raw` | The producer's own EMA state and funding ledger tail; no panel file | **no** | VERIFIED — `chain_v4_monthly.sh:139` (`c80303b55c5aa229`); builder reports read read-only on pod2 |
| **clock** | panel row `j = pw_row[E_ts[i]]`, i.e. the scored anchor's own row | the scored anchor's own row, built at the anchor | same row index | VERIFIED — `pod_dlw_features_ext.py:90` (`e86725cc2768bb62`); `combo_stage.py:134-148` (`b5c698f9d1ee9acb`) |
| **unit** | panel `f_fund_ema` = **v0** (raw per-settlement rate, wall-clock HL-3d EMA, stale > 12 h → 0); col 81 = raw last rate | col 80 = producer's **v1** EMA state; col 81 = raw last rate | **col 80 no, col 81 yes** | VERIFIED — the v0/v1 split is P1/P2 (T4/T4b). FX-PROD's fix makes serving v0; **not deployed** |
| **dtype** | `np.float16` — `X = np.zeros((n_pairs, 82), np.float16)` | `float32`/`float64` through `M["mu"]`, `M["sd_"]` | **no** | VERIFIED — `pod_dlw_features_ext.py:78`; `combo_stage.py:165` |
| **mask / support** | funding exists for exactly the **450** live_pins names on the splice prefix (≤ 2026-08-15 00Z); everything else is `0.0` | production only ever scores live names, so its own support is the live list by construction | **this is the defect** | VERIFIED — §1.2 |
| **membership** | DL targets pick members on trailing rows **[E−2016, E−1]**; DL features and the producer use **[E−2015, E]** | producer members include row E | **no** (one bar) | VERIFIED — C-TIM-5; `pod_dlw_targets_raw.py:88` (`d7c528231f009029`). **Shared row with TIM-01; a separate intervention — see §1.6(iii)** |
| **normalisation** | per-fold `mu`/`sd` recomputed inside the trainer from a subsample of that fold's training rows | `mu`, `sd_` shipped inside `f10_live_s42_np.npz` | operator order same, values fold-specific | VERIFIED — §1.3 |

### §1.2 The support defect, with a full-support account of the difference

**(a) The support sets.** On the splice prefix (≤ cut 2026-08-15 00Z), the funding columns' support is exactly `live_pins.symbols_live`:

| Column | v1 names with any finite | v2ext names with any finite | v1 set == live_pins | splice rows ≤ cut bitwise == v1 |
|---|---|---|---|---|
| `f_fund_ema` | 450 | 825 | **true** (both symmetric differences empty) | **true** |
| `f_fund_ema_v1` | 450 | 825 | **true** | **true** |
| `f_fund_now` | 450 | 825 | **true** | **true** |

VERIFIED — FACTS_DATA F1. This set identity, not the ratio in (c), is what establishes the look-ahead: the support *is* the later live list.

**(b) Cell-by-cell on the common support — the difference is coverage, not values.** Over the 9,943 common anchors (2022-01-31 00Z .. 2026-08-15 00Z) restricted to the 450 live names, 4,474,350 cells:

| Column | finite v1 | finite v2ext | finite both | v1-only | **v2ext-only** | exact-equal share | max\|Δ\| |
|---|---|---|---|---|---|---|---|
| `f_fund_ema` (col 80 source) | 2,168,927 | 2,172,667 | 2,168,927 | **0** | 3,740 | **1.0** | **0.0** |
| `f_fund_now` (col 81 source) | 2,168,927 | 2,172,667 | 2,168,927 | **0** | 3,740 | **1.0** | **0.0** |
| `f_fund_ema_v1` (not a model input) | 2,168,927 | 2,172,667 | 2,168,927 | 0 | 3,740 | 0.999851 | 0.005107 |

VERIFIED — FACTS_DATA F4. This is the full-support account the review demands, not a correlation: on every cell where both panels have a value, the two funding columns that feed the model are **bitwise identical**, `v1_only = 0`, and the only asymmetry is 3,740 cells finite in v2ext alone. **So the rebuild changes which cells have a value; on cells that already had one it changes nothing.**

**(c) How many cells the rebuild would fill.** Zero in fea82 while v2ext has a finite value, by year:

| Year | `dlw_v4raw` zero / v2ext-finite denominator | share | `dlw_ext` (in-service) | share | cells that stay 0 after the fix |
|---|---|---|---|---|---|
| 2022 | 97,546 / 285,622 | 34.15% | 96,006 / 280,290 | 34.25% | 0 |
| 2023 | 139,361 / 410,358 | 33.96% | 139,361 / 410,358 | 33.96% | 0 |
| 2024 | 202,279 / 601,406 | 33.63% | 202,279 / 601,406 | 33.63% | 0 |
| 2025 | 210,066 / 849,694 | 24.72% | 210,066 / 849,694 | 24.72% | 117 |
| 2026 | 80,970 / 581,016 | 13.94% | 80,066 / 580,611 | 13.79% | 177 |

Col 81 is slightly higher throughout (34.49 / 34.20 / 33.83 / 24.88 / 14.76% on v4raw) because `f_fund_now` can be absent where the EMA is present. VERIFIED — FACTS_DATA F2; **both** lineages printed, not one.

Two things this table does **not** say, and the rows that guard them:
- The denominator excludes pairs where v2ext has no row at all — **22,892 in 2022** (168 anchors, v2ext's axis starts 2026 rows later than the splice's) and **2,000 in 2026** (5 anchors). On those pairs no comparison is possible: **NOT CHECKED**, not "zero-verified".
- The numerator counts "exactly 0 here and finite in v2ext", which also admits genuine and float16-quantised zeros. It is an **upper bound** on cells the rebuild would change. The look-ahead fact stands on (a), not on this ratio — this is review narrowing (i), carried in §1.6.

**(d) Why "absent" is unrecoverable from the artifact.** The builder collapses three distinct situations into the same float16 `0.0` token:

```
pod_dlw_features_ext.py:78   X = np.zeros((n_pairs, NF), np.float16)
pod_dlw_features_ext.py:90   j = pw_row.get(int(E_ts[i]))
pod_dlw_features_ext.py:94   X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0)
```
1. no panel row for the anchor (`j is None`) → the whole anchor's funding is 0;
2. per-cell NaN (the name is outside the 450) → 0;
3. a genuine zero funding rate → 0.

**Positive control that the stored columns are exactly this function of the panel:** stored cols 80/81 == `float16(nan_to_num(splice))` with **0 mismatches** on 5,506,578 cells (`dlw_v4raw`) and 5,491,114 cells (`dlw_ext`). VERIFIED — FACTS_DATA F2. Consequence for the fix: the availability bit cannot be recovered from fea82 and must be rebuilt from the panel (or from trades, TRD-01); a different *fill value* would not fix it, because the information was destroyed at write time.

### §1.3 Normalisation — the axis that decides whether arm B is possible

This was the one NOT CHECKED row when the track paused. It is now VERIFIED, and it constrains the prereg.

**(a) The rule is the same three lines in every trainer, and it is RNG-free.**

| Recipe | File (sha16) | Lines |
|---|---|---|
| monthly walk-forward (v4 chain) | `pod_f10_train_monthly_v4.py` (`fd5707bd3acccdbb`) | 329–334 |
| monthly walk-forward (in-service lineage) | `pod2:…/dl_monthly_wf/pod_f10_train_monthly.py` (`7bb39f8d93f2daf7`) | 323–328 |
| live refit | `base_pod_f10_refit_ext.py` (`ea3675b8012ea266`) | 90–93 |

```
cut = int(len(tr_idx) * 0.85); tr1 = tr_idx[:cut]
rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
XS = XT[rowsel[::3]]
mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6
```
Calibration rows = every 7th training anchor, then every 3rd member row of those anchors. In the monthly trainer this block **precedes** `torch.manual_seed(SEED); np.random.seed(SEED)` (v4 L336) and uses no RNG, so `mu`/`sd` is a **deterministic pure function of (tr_idx, ST, XT)**. VERIFIED by reading.

**(b) `nan_to_num` runs before the mean and std.** Combined with §1.2(d), the spurious zeros are *inside* the calibration statistics of every fold. VERIFIED.

**(c) Operator order is identical on all three paths** — standardise, clip to ±5, then zero the NaN:

| Path | Line | Code |
|---|---|---|
| monthly train | `pod_f10_train_monthly_v4.py:200` | `x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)` then `torch.nan_to_num(x)` |
| refit | `base_pod_f10_refit_ext.py:58` | same |
| numpy export gate | `pod_f10_np_export.py:34` (`3e304c27606d3c12`) | `xz = np.nan_to_num(np.clip((XL - mu) / sdv, -5, 5))` |
| **production** | `combo_stage.py:165` (`b5c698f9d1ee9acb`) | `xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))` |

Production carries an explicit E-0826 note at `combo_stage.py:163-164` recording that the order was corrected to match training. So on this axis train and serve **agree**. VERIFIED.

**(d) The asymmetry that matters: which checkpoints carry their `mu`/`sd`.**

| Artifact | What is saved | `mu`/`sd` inside? |
|---|---|---|
| live refit `models/f10_live_s{SEED}.pt` | `{"state_dict", "mu", "sd", "alpha", "seed", "n_cols", "va_curve", "best_va", "trained_through", "recipe"}` (`base_pod_f10_refit_ext.py:120`) | **yes** |
| production `f10_live_s42_np.npz` (`351ae26bd6b4a203`) | `{w0,b0,w1,b1,w2,b2,mu,sd_,alpha,n_cols,trained_through}` (`pod_f10_np_export.py:2`) | **yes** |
| monthly fold `models/{TAG}_{YM}.pt` | `best_state` only (`pod_f10_train_monthly_v4.py:435`, `pod_f10_train_monthly.py:424`) | **no** |
| monthly fold `models/{TAG}_{YM}_config.json` | recipe + input shas + fold bounds | **no** |
| in-service yearly walk-forward | **no fold checkpoint at all** | n/a |

VERIFIED three ways, not one: by reading the save lines; by enumerating the keys of a real checkpoint — `pod2:…/dl_monthly_wf/models/mE1_202608.pt` (`15ad9b2346b1b6ec`) has keys exactly `['a','f.0.weight','f.0.bias','f.3.weight','f.3.bias','f.6.weight','f.6.bias']`, `has_mu False has_sd False`; and by enumerating the 36 config keys, none of which is `mu`/`sd`. And `pod2:/workspace/f8_ext/models/` contains only `f10_live_s42.pt`, `f10_live_s2027.pt` and their `_np.npz` exports — confirming T4b's finding that the in-service yearly trainer `pod_f10_train_ext.py` (`93cc2cdf`) saved no fold models.

**(e) What this does to the three-arm design.**

- The in-service checkpoint `f10_live_s42_np.npz` **does** carry `mu`/`sd`, but its `trained_through` is 1788120000 = 2026-08-30 20:00Z, i.e. a refit over everything. Running it forward over that span is exactly the alternative the review refuses ("现用模型跑其训练区間历史", §9). **It cannot be the arm-B model.**
- The genuinely out-of-sample checkpoints are the **20 monthly folds × 2 embargo tags** at `pod2:/workspace/review_scratch/dl_monthly_wf/models/`, spanning 202501..202608 — and those are exactly the ones with no stored `mu`/`sd`.
- Because the calibration is deterministic and RNG-free (a), the fold's training-time `mu`/`sd` is **exactly reconstructible** by re-running those three lines on the **old** fea82 with that fold's own `tr_idx`. The fold config names every input sha needed: `fea82_sha256 = 9bc111a47cee54fc` (= the in-service fea82), `targets_sha256 = 31d043e8f160a1d4`, `fea89_sha256 = bebf272031549970`, `legs_sha256 = facf53f7355da98f`, `self_sha256 = 7bb39f8d93f2daf7`. VERIFIED by reading `mE1_202608_config.json`.
- **This reconstruction is not usable until it is certified.** Required positive control, to be prereg'd: reconstructed `mu`/`sd` on the old features + the saved fold `state_dict` + old features must reproduce that fold's stored `preds_fold/{TAG}_{YM}.npz` `P` array, to the trainer's own declared tolerance (`test_vs_all_maxdiff`, asserted ≤ 1e-5 at `pod_f10_train_monthly_v4.py:433`). **If the control fails, arm B on monthly folds is not available and I will report that rather than substitute anything.**
- **Naming discipline, per the review:** arm B = new raw features, **old mapping held fixed** (reconstructed training-time `mu`/`sd`, feature order, support, weights). Arm C may use each fold's own new `mu`/`sd`. Recomputing `mu`/`sd` on the new data inside arm B would be a *different intervention on the input mapping* and would not be called "only the raw features changed".
- Note the estimand honestly: because of (b), arm B feeds corrected funding values through a `mu`/`sd` calibrated on a distribution containing the spurious zeros, and the ±5 clip can bind on cells that were previously 0. That mis-calibration is **not a flaw in arm B — it is arm B's estimand** (what the deployed mapping does when the input is corrected), and it is precisely why B and C must be reported separately.

**(f) Seeds.** `mE1_202608_config.json` reports `seed_fold = 202650` for fold 202608 — a per-fold seed, not a constant. The v4 variant carries an opposite note at `pod_f10_train_monthly_v4.py:336` (`mE1_constseed`, addendum §11: constant init/shuffle seed for every fold). **The two recipes differ on seeding**; the prereg must name which recipe it runs and quote its rule. NOT CHECKED: whether `seed_fold = YM + SEED` holds on every fold (one observation is consistent with it).

### §1.4 The latent site (legs ZFD) — corrected, and the residual now decomposed

`a1c16b73` withdrew my attempt-1 over-extension before the rerun. The corrected statement, which matches review narrowing (ii):

**(a) The stored legs are copies, so the feature defect does not extend to them.** `pod_legs_v4b.py` (`8c33a2305c38a148`) copies each old anchor's row verbatim from the in-service legs and builds only new anchors from the splice panel. Its own assertion `"old rows not verbatim"` enforces this. Stored ZFD is finite wherever v2ext `f_fund_ema_v1` is finite: **0 misses in 2023, 2024, 2025** in both lineages. VERIFIED — FACTS_DATA F3.

**(b) The residual misses decompose exactly.** This closes the row my pause note left as a presumed cause, by arithmetic identity over committed counts — no new run.

*2022, v4 legs:* cells 308,514, ZFD finite 303,159 ⇒ 5,355 NaN, of which 5,332 have v2ext-v1 finite.
- in-service legs 2022 cells = 303,182, ZFD finite = **303,159** (the identical count — the copy).
- 308,514 − 303,182 = **5,332** = exactly `zfd_nan_v2ext_v1_finite`.
- 303,182 − 303,159 = 23 = the in-service rows' own NaN, all inside the 22,892 no-v2ext-row region.
⇒ **the 2022 misses are exactly the v4 member pairs that are not in-service member pairs**, i.e. slots the copied rows never had. VERIFIED (count identity).

*2026, v4 legs:* cells 583,200, ZFD finite 571,964 ⇒ 11,236 NaN = **2,000 + 8,365 + 871**:
- **2,000** — the 5 new 2026-08-31 anchors with no v3splice panel row. The builder **declares this itself** and prints the list (`new_rows_without_panel_row`; the splice axis ends 2026-08-31 00Z). Self-reported, not a hidden defect.
- **871** — the in-service legs' own NaN on the shared anchors, present in both lineages.
- **8,365** — v4 member cells absent from the copied v3-lineage rows. **Independently corroborated**: AUDIT_DATA OOF-01 measured the A0 legs / v4 meta member-list difference at exactly **8,365 cells** (`pred_cells_outside_dlw_v4raw_members`) from a different receipt and a different device.
⇒ same mechanism as 2022 plus a declared panel-axis edge. VERIFIED (count identity, two instruments).
**NOT CHECKED:** cell-level identity of the 8,365 (the counts match; I have not asserted the same cells).

**(c) The latent path remains latent.** `pod_legs_v4b.py:22` *would* build a new row's ZFD from the splice `f_fund_ema_v1` (450-name support) if an anchor were new. In the September contract only 6 anchors are new, 5 of which have no panel row at all. So FEA-01's support defect has **not** propagated into the stored fund leg. The feature-column defect must not be written up as "the fund leg is broken".

### §1.5 Open rows for FEA-01

| # | Row | Status | How it closes |
|---|---|---|---|
| O1 | Cells where v2ext has no row (22,892 in 2022, 2,000 in 2026) | **NOT CHECKED** | Needs a third source (settlement stream); the rebuild must keep them explicitly unknown, not zero |
| O2 | Cell-level identity of the 8,365 legs cells | **NOT CHECKED** | Optional; counts already agree across two instruments |
| O3 | `seed_fold = YM + SEED` on every fold | **NOT CHECKED** | Enumerate the 40 configs when the prereg is drafted |
| O4 | Arm-B reconstruction control (§1.3(e)) | **NOT CHECKED** | Must pass before any arm-B number is quoted; a failure is reportable, not substitutable |
| O5 | Effect of the rebuild on F10 predictions and on the book | **NOT MEASURED** | That is the prereg's job, not this table's |

### §1.6 Narrowings carried from the independent review

1. **(i)** G2's with/without-support forward-return gaps **+0.77 / +0.46 / +1.07 / +2.78 / +3.19 bps per 4 h** (naive t 0.9 / 0.7 / 1.8 / 3.3 / 1.8) are **descriptive between-group differences**; the naive t does not handle persistent membership or time dependence. The per-year Spearman is **−0.0031 / +0.0018 / −0.0041 / +0.0059 / −0.0079** — **inconsistent in sign**. Therefore: I do **not** assert the model turned this information into returns, and I do **not** predict that OOF IC falls after the fix. My pause note's line "a lower OOF IC after FEA-01 is expected" is **withdrawn**; the prereg will state the direction as undetermined.
2. **(ii)** The funding-leg ZFD artefacts are **not the same zero-coverage population** — already withdrawn at `a1c16b73`, and §1.4 now gives the actual mechanism.
3. **(iii)** Non-crypto externals (~7.26% of 2026 training, UNI-01), the DL membership clock (E−1 train vs E serve, §1.1), and future-y-finite membership filtering (TRD-05 / TRN-06) are **separate interventions**. Changing them together with the funding rebuild makes "the funding fix's effect" unidentifiable, so each gets its own arm or is held fixed. The membership row appears in §1.1 because it decides *which pairs the funding fix touches*, not because it is part of the funding fix.
4. On king (TIM-01, §2 when written): the clock/label difference is a **definition** difference. The review's anchor-bar impulse test on the original label statement shows only E's return reaching the label. It must **not** be written as "the model peeked at future prices". King parity numbers **0.9353434309 median / 0.7601561963 min** (32 anchors), clock-only **0.98434**, ranking-universe-only **0.94700** are **different contrasts and are not additive alpha losses**.

---

## §2 TIM-01 — NOT YET WRITTEN
## §3 PROD-11 — NOT YET WRITTEN
## §4 UNI-01 — NOT YET WRITTEN
## §5 TRD-05 (+ TRN-06 coordination) — NOT YET WRITTEN

### P10 (closed here, no section)
King training features are stored float16 and cast to float32 at fit (`pod_fea_ext_clamp.py:67`, `b9f9c72816241715`); the producer builds float32 from a float32 view of its float16 cache. **aud-prod measured it**: a float16 cast of served king features changes 0 deciles on 47/47 anchors, min Spearman 0.99996 (`receipts_prod/parity_king.json`, `9dbba68b`; AUDIT_PROD PROD-05). **No fix justified.** I did not re-measure; this row is VERIFIED-by-citation, and the scope limit is theirs: recent anchors, served inputs.
