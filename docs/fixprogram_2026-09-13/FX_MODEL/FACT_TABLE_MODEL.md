> **创建:** 2026-09-16 03:5xZ | **Session:** FX-MODEL (fix worker, teammate of team-lead) | **状态:** 事实表, append-only by section; each section is committed before the red tests and before any fix code of its item | **作废条件:** a cited file sha changes (every row carries its sha16), or the pinned artifact shas in §0 change

# FACT_TABLE_MODEL — FX-MODEL items (AUDIT_DATA bb8a2806 FEA-01 / TIM-01 / UNI-01 / TRD-05, AUDIT_PROD 57f7e2be PROD-11; TRN-06 coordination)

Legend, used on every row:
- **VERIFIED** — read at the cited line, or computed by a device listed in §0.2 whose receipt is committed. Arithmetic identities over committed receipt counts are VERIFIED and say so.
- **INFERRED** — reasoning from verified facts; not measured.
- **NOT CHECKED** — stated so that nobody reads it as checked.

Conventions:
- `sha16` = first 16 hex of sha256. **Research-repo rows cite the git blob at commit `fc262f79`** (`git show fc262f79:<path> | shasum -a 256`), not the mutable working tree — see §0.4 for why. `pod2:` rows are hashed on pod2, with the sha asserted inside the reading command where one is quoted.
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

### §0.4 Citation stability — two cited files are under concurrent edit

Caught by re-auditing every cited sha at 04:3xZ (the check this table's 作废条件 asks for). Two files I cite were **modified in the working tree by FX-TRAIN while I was writing**, after I had hashed them:

| File | sha16 I cite (= blob at `fc262f79`) | worktree sha16 at 04:3xZ | my cited lines still valid? |
|---|---|---|---|
| `chain_v4_monthly.sh` | `c80303b55c5aa229` | `b1dcf771e04e3be8` (+4 −1) | **yes** — L139 and L148 re-read verbatim, the edit is elsewhere |
| `pod_legs_v4b.py` | `8c33a2305c38a148` | `ff6dccad6646058a` (+36 −2) | **no** — line 22 now reads `if MAX_NO_PANEL < 0:`; the ZFD build line has moved |

Consequences, recorded rather than patched over:
- Every research-repo sha16 in this table is the **committed blob**, and all 21 cited files were re-hashed against it at 04:3xZ with **0 mismatches** once this convention is applied. No cited file is an iCloud-evicted stub.
- **§1.4(c)'s line citation `pod_legs_v4b.py:22` is valid only for blob `8c33a2305c38a148`.** Against FX-TRAIN's TRN-17 version the latent ZFD site has moved and must be re-located before that row is used as an input to anything.
- **FX-TRAIN's TRN-17 change corroborates §1.4(b)'s 2,000-cell term and supplies its mechanism.** Their comment states the structural reason the frontier anchors have no panel row: *"the panel is structurally 5 anchors short of the king/DL axis (panels need E+288 <= TT, the axis needs E+48; 288−48 = 240 rows = 20 h = 5 four-hour anchors)"*. **5 anchors × 400 members = 2,000**, exactly the term I decomposed from the receipt counts. Their change turns the builder's printed line into a declared bound (`LEGS_MAX_NO_PANEL`, required env) that refuses **before** `np.savez`, and separately refuses any no-panel anchor at or before the panel end as an interior hole. That closes §1.5's concern that the condition is unobservable after the legs stage; it does not change any count in §1.4.

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
| **chain state** | none — training is stateless across anchors | `state_H_f10_<A>.npz`, whose **last writer on 128/129 anchors is the sidecar `sidecar_blend.py`**, not `combo_stage` (FX-PROD P12, ±1.0 s; **79/129** writes land *after* the executor's first read at N+24:00) | **no** | VERIFIED (FX-PROD receipt). **A replay that recomputes this state with `combo_stage` code differs from live BY CONSTRUCTION** (= P2's 96 names at 2.63e-8). For anything touching the F10 chain state, "same code ⇒ same state" is false |

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
| O3 | `seed_fold = YM + SEED` on every fold | **VERIFIED 2026-09-16** | All 40 fold configs enumerated on pod2: `seed_fold == fold + 42` holds for every one, and the source line is `torch.manual_seed(SEED + YM); np.random.seed(SEED + YM)`. **And a constraint found with it**: `pod_f10_train_monthly.py` (`7bb39f8d`) carries an E-0826-D env whitelist asserting **`SEED == 42`**, so the in-service-lineage trainer cannot run a second seed; `pod_f10_train_monthly_v4.py` (`fd5707bd`) asserts `SEED in (42, 2027)` and uses a **constant** per-fold seed instead. The two recipes therefore differ on both the seed set and the seeding rule — see PREREG §4. |
| O4 | Arm-B reconstruction control (§1.3(e)) | **NOT CHECKED** | Must pass before any arm-B number is quoted; a failure is reportable, not substitutable |
| O5 | Effect of the rebuild on F10 predictions and on the book | **NOT MEASURED** | That is the prereg's job, not this table's |
| O6 | Which export run produced the in-service `f10_live_s42_np.npz`, and whether its V1 gate passed | **NOT CHECKED** | TRN-28: the npz is written before the verdict, so its existence proves nothing. Required before it is any arm's input |

### §1.6 Narrowings carried from the independent review

1. **(i)** G2's with/without-support forward-return gaps **+0.77 / +0.46 / +1.07 / +2.78 / +3.19 bps per 4 h** (naive t 0.9 / 0.7 / 1.8 / 3.3 / 1.8) are **descriptive between-group differences**; the naive t does not handle persistent membership or time dependence. The per-year Spearman is **−0.0031 / +0.0018 / −0.0041 / +0.0059 / −0.0079** — **inconsistent in sign**. Therefore: I do **not** assert the model turned this information into returns, and I do **not** predict that OOF IC falls after the fix. My pause note's line "a lower OOF IC after FEA-01 is expected" is **withdrawn**; the prereg will state the direction as undetermined.
2. **(ii)** The funding-leg ZFD artefacts are **not the same zero-coverage population** — already withdrawn at `a1c16b73`, and §1.4 now gives the actual mechanism.
3. **(iii)** Non-crypto externals (~7.26% of 2026 training, UNI-01), the DL membership clock (E−1 train vs E serve, §1.1), and future-y-finite membership filtering (TRD-05 / TRN-06) are **separate interventions**. Changing them together with the funding rebuild makes "the funding fix's effect" unidentifiable, so each gets its own arm or is held fixed. The membership row appears in §1.1 because it decides *which pairs the funding fix touches*, not because it is part of the funding fix.
4. On king (TIM-01, §2 when written): the clock/label difference is a **definition** difference. The review's anchor-bar impulse test on the original label statement shows only E's return reaching the label. It must **not** be written as "the model peeked at future prices". King parity numbers **0.9353434309 median / 0.7601561963 min** (32 anchors), clock-only **0.98434**, ranking-universe-only **0.94700** are **different contrasts and are not additive alpha losses**.

---

## §2 TIM-01 — the king training clock and the king label are each one bar earlier than production

**AUDIT_DATA severity P1.** In one sentence: king training fits *(data through E−1) → (returns from E)*, while production applies *(data through E) → (returns from E+1)*. Both halves are internally contiguous and causal; they are **shifted one 5-minute bar relative to each other**. This is a definition difference, not a peek at future prices — see §2.3.

### §2.1 Per-column parity — king features, members and label

| Axis | Training (`pod_fea_ext_clamp.py`, `b9f9c72816241715`) | Serving (`shadow_loop_v3.py`, `e9c9837412130884`) | Same? | Status |
|---|---|---|---|---|
| **feature clock** | rows **[E−w, E−1]**, last input bar **E−1** (L48–53) | rows **[E−w+1, E]**, last input bar **E** (L358) | **no**, one bar | VERIFIED |
| **member-stat clock** | rows **[E−2016, E−1]** (L28–32) | rows **[E−2015, E]** (L365, L371) | **no**, one bar | VERIFIED |
| **label clock** | rows **[E, E+47]** (L33–34) | live accounting rows **[E+1, E+48]** | **no**, one bar | VERIFIED |
| **clamping of the member window** | `covr` clamped (L29); **n7 / qvm / m7 / v7 use an unclamped `E−2016`** (L28, 30, 31, 32) | `max(ai+1−2016, 0)`, always clamped | **no** | VERIFIED — §2.5(a) |
| **unit** | col 80 v0, col 81 raw | col 80 v1, col 81 raw | col 80 **no** | VERIFIED — P1 (T4); FX-PROD fix not deployed |
| **dtype** | stored `np.float16` (L67) | `float32` | **no**, immaterial | VERIFIED — P10, 0 deciles changed 47/47 |
| **membership universe** | top 400 of all 829 cache names | top 400 of the live 450 | **no** | VERIFIED — PROD-02 / PROD-11, §3 |
| **normalisation** | **none** — LightGBM is fit on raw features | none | **yes (vacuously)** | VERIFIED — §2.8 |
| **feature order / support** | 82 builder columns; the export keeps all but the `ret5_sum_48` / `ret5_sum_288` families (L46) and asserts the kept order equals the live pins (L47) | the 78 served columns | asserted equal | VERIFIED — `pod_export_bundle_v4.py:46-47` (`42555a37c0cd3a7e`); 78 served / 4 not served per AUDIT_PROD |
| **sha actually consumed** | `PANEL_IN = PANEL_KING` = **v2ext**, not the splice | producer's own state | — | VERIFIED — `chain_v4_monthly.sh:148`. **King is outside FEA-01** |

### §2.2 The exact windows, with the prefix-sum semantics spelled out

`cs_pair` builds cumulative sums with a **leading zero row** (`pod_fea_ext_clamp.py:13-17`), so `CS[b] − CS[a]` is the sum over rows **[a, b−1]**. Reading the sites with that in hand:

| Quantity | Code | Rows |
|---|---|---|
| builder feature window | `s_[E] − s_[Ew]`, `Ew = max(E−w, 0)` (L48–53) | **[E−w, E−1]** |
| builder member stats | `qv_f[E] − qv_f[E−2016]` (L28) | **[E−2016, E−1]** |
| builder label `y4` | `CS["ret5"][0][E+48] − CS["ret5"][0][E]` (L34) | **[E, E+47]** |
| producer feature window | `CDf[max(ai+1−w, 0):ai+1]` (L358) | **[E−w+1, E]** |
| producer member stats | `CDf[max(ai+1−2016, 0):ai+1]` (L365, L371) | **[E−2015, E]** |

**Bar E is the bar that closes exactly at the anchor.** The producer enforces this: it requests `endTime = anchor*1000 − 1` (L280) and rejects any kline with `close_s > anchor` (L285–286). So bar E's return is already realised at decision time, and the producer's inclusion of it is causal.

### §2.3 Why this is a definition shift and not leakage

- **In training**: features end at row E−1, the label begins at row E. Contiguous, no overlap. The label is causal with respect to the features it is fit against.
- **In serving**: features end at row E, the accounting return begins at row E+1. Contiguous, no overlap. Also causal.
- The two are simply **offset by one bar**. The independent review's anchor-bar impulse test on the original label statement confirms the mechanism: set only E's return to ±10% and the label reads ±10% while the true four hours after E read 0 — because row E is the label's **first summand**, not because anything future leaked in.
- **Required wording**: the fitted relation is *(data ≤ E−1) → (returns from E)*; the applied relation is *(data ≤ E) → (returns from E+1)*. It must **not** be written as "the model peeked at future prices". The mechanism by which scores move is that these are two different conditional relations whenever 5-minute returns have any short-horizon autocorrelation — not leakage.

### §2.4 Label maturity and embargo — the row the prereg needs

| Object | Label rows | Completes at | Source |
|---|---|---|---|
| king training label `y4` | [E, E+47] | **A + 3h55m** | `pod_fea_ext_clamp.py:33-34` |
| clock-aligned builder label | [E+1, E+48] | A + 4h | `pod_fea_ext_e.py:36-37` |
| DL target `y4s` | [E+1, E+48] | A + 4h | `pod_dlw_targets_ext.py` L93 (accounting caliber) |

- **King folds are yearly, and there is zero embargo.** `tr = YRA < 2026; te = YRA == 2026` for the shipped booster, and `tr_ = YRA < YV; te_ = YRA == YV` for the 2024 / 2025 legs folds (`pod_export_bundle_v4.py:63,74`). The last training anchor of a fold is 12-31 20:00Z, whose label runs to 23:55Z; the first test anchor is 01-01 00:00Z. So there is **no overlap — but no embargo either**, a 5-minute gap under the current label and a 0-minute gap under the aligned one. VERIFIED. This is not by itself a defect at yearly granularity; it is a fact the prereg must state, because the DL side is different:
- **The DL monthly trainer has an explicit embargo and a printed causality assert**: `EMBM ∈ {60, 1}` with `assert max_tr < first_te − EMBM and max_label_end <= cutoff`, using `max_label_end = E_ts[max_tr] + 48*300` = A + 4h (`pod_f10_train_monthly_v4.py:324-327`). That bound is **exact for DL** and **conservative for king** (A+4h > A+3h55m).
- **The exporter's provenance record misstates the king label end by 5 minutes**: it writes `king_train_last_label_end_utc = _king_train_end + 4*3600` (L264, printed at L66), i.e. A + 4h, while the clamp builder's label actually ends at A + 3h55m. Conservative in the safe direction, but it is **not the builder's definition** — another instance of a register carrying the DL clock where the king clock was meant. VERIFIED.
- **King's gradient stops at label-year < 2026** (L15-16, L63): the monthly export rebuilds the 2026 fold and does not move this cutoff.
- **★ `trained_through` is none of the three things a reader assumes** (FX-TRAIN TRN-14, folded 2026-09-16). The deployed `f10_live_s42_np.npz` carries `trained_through = 2026-08-30T20:00Z`, and that value is `max(E_ts)` of `dlw_targets.npz` — **the data-axis end**. It is **not** the training-pool end and **not** the label cutoff. The file that ships therefore carries the one of the three that is **furthest from what the optimiser actually saw**. And the in-service checkpoint has **no sidecar**, so it can never be re-bound: **"the in-service DL leg was trained through X" has no file-level evidence today, only refit logs.** Any cutoff statement must name which quantity it means:

| quantity | what it is | where it is recorded |
|---|---|---|
| data-axis end | `max(E_ts)` of the targets | `trained_through` in the deployed npz — **this is the one that ships** |
| training-pool end | last anchor whose row entered the fit | DL: `max_train_idx` in each fold config. King: `_king_train_end` (`pod_export_bundle_v4.py:64`) |
| label cutoff | when the last training label finished maturing | DL **A+4h**; King **A+3h55m** — and the exporter records A+4h, previous bullet |

- **★ The deployable npz is written BEFORE its own gate verdict** (FX-TRAIN TRN-28, P1 — **verified by me at the line, not taken on report**). `pod_f10_np_export.py` computes `ok = rho >= 0.99999 and mx <= 1e-5` at **L55**, writes `{OUT}/models/f10_live_s{SEED}_np.npz` at **L56-57 unconditionally**, prints PASS/FAIL at L58, and only then exits 0 or 3 at L59. The default `F10_OUT` is the in-service artifact path. **A FAILED gate still leaves a complete, loadable model on the live path, overwriting the previous one.** Consequence: **the existence of `f10_live_s42_np.npz` is not evidence that its parity gate passed** — open row **O6**.

### §2.5 Same-family sites

**(a) The unclamped member-statistic window wraps on exactly 30 anchors.** `n7`, `qvm`, `m7`, `v7` index `E − 2016` with no clamp (L28, 30, 31, 32) while `covr` is clamped (L29). Since `grid` is filtered to `E ≥ 576`, every anchor with `E < 2016` indexes negatively, and a negative index into the leading-zero prefix-sum array wraps to the **cache tail**.

Measured on the in-service cache axis (`dlnative_5m_wide829_f16_ext.npz`, read-only, `ts` member only): axis 2022-01-01 00:00Z .. 2026-09-01 00:00Z, 490,753 bars, grid spacing uniformly 48 with no gaps, 10,213 anchors at `E ≥ 576`. Anchors with `E < 2016`: **exactly 30**, `E = 576, 624, …, 1968` = **2022-01-03 00:00Z .. 2022-01-07 20:00Z**. VERIFIED (measured this session).

> **[ORIGINAL TEXT, KEPT VERBATIM — SUPERSEDED BY THE CORRECTION BELOW, 2026-09-16 04:2xZ]**
> Those 30 anchors' member screen (`v7 >= 1e-4`) and top-400 ranking (`qvm`) are therefore computed from wrapped statistics. **Independent corroboration from my own receipt**: FACTS_DATA T1 records that the clock-aligned builder — which clamps via `LO7 = max(HI−2016, 0)` — *adds exactly two anchors*, **2022-01-07 16:00Z and 2022-01-07 20:00Z** (`E = 1920, 1968`), both inside the wrap window, and removes none. That is the expected signature: clamping repairs the statistics so two more early anchors pass the `len(m) >= 50` screen.
>
> Blast radius: 30 of 10,213 anchors = 0.29%, all in the first week of the axis. **NOT CHECKED**: whether those 30 anchors' member sets differ materially, beyond the two added anchors already counted.

**CORRECTION (2026-09-16 04:2xZ, measured while writing §3; the row above understated the effect).** The wrap does not leave those 30 anchors in the axis with corrupted statistics — it **removes all 30 from the king training axis entirely**. Measured read-only on pod2 with input shas asserted (`wide_fea_v4_meta.npz` `12ea42c4557093f1`, `dlw_v4raw/data/dlw_targets.npz` `d1976cf6246cdc25`, cache `ts` member):

| | anchors | first anchor | anchors with `E < 2016` |
|---|---|---|---|
| king meta (`pod_fea_ext_clamp.py`, unclamped) | 10,182 | **2022-01-08 00:00Z (= E 2016 exactly)** | **0** |
| DL targets (`pod_dlw_targets_raw.py`, clamped) | 10,212 | 2022-01-03 00:00Z (= E 576) | 30 |

In DL and not in king: **exactly 30**, cache rows `E = 576, 624, …, 1968`, i.e. **precisely the wrap window**. In king and not in DL: 0. This is the same 30 that AUDIT_DATA **TRD-05 records as `anchors_off_king_axis: 30`** for DL 2022, from an independent receipt — the two now have a mechanism.

**The three-way behaviour is fully explained, and the deciding term is `covr`'s divisor, not `len(m) >= 50`:**

| Builder | `E−2016` handling | `covr` divisor | Early anchors kept |
|---|---|---|---|
| **K** `pod_fea_ext_clamp.py` | **unclamped** ⇒ negative index wraps to the cache tail | constant 2016 | **0 of 30** — wrapped statistics fail the screen |
| **E-version** `pod_fea_ext_e.py` | clamped `LO7 = max(HI−2016, 0)` | **still the constant 2016** | **2 of 30** |
| **D** `pod_dlw_targets_raw.py` | clamped `S = max(E−TRAIL, 0)` | **actual window length** `max(E−S, 1)` (L90) | **30 of 30** |

The E-version keeps exactly 2 because with a clamped window of only `E+1` rows and `covr` still divided by the constant 2016, `covr ≤ (E+1)/2016`, so `covr >= 0.95` needs `E >= 1915.2`; the only grid values in [1915, 2016) are **1920 and 1968**. That is arithmetically the two anchors T1 observed — so my original attribution of those two to the `len(m) >= 50` screen was **wrong**; the binding gate is `covr`. D keeps all 30 because it divides by the true window length.

Blast radius, corrected: the king axis is **missing its first 5 days** (2022-01-03 00:00Z .. 2022-01-07 20:00Z), 30 of 10,212 possible anchors = 0.29%; and the king and DL training axes disagree there by construction. **VERIFIED.** Command transcribed in §3.0.

**(b) The DL targets' member clock is a third window.** DL targets choose members on rows **[E−2016, E−1]** while DL features and the producer use **[E−2015, E]** (C-TIM-5, `pod_dlw_targets_raw.py:88`). So within one DL training row the member screen and the features are on different clocks. VERIFIED. This is the row shared with FEA-01 §1.1 and is a **separate intervention**.

### §2.6 Measured skew, and the contrast discipline

**Clock-only contrast** (same booster, same members, features on [E−w, E−1] vs [E−w+1, E]), 2024..2026-08, common members — FACTS_DATA T1:

| Booster | anchors | Spearman median | p5 | min | top-decile overlap median | p5 | max\|Δ\|/sd median |
|---|---|---|---|---|---|---|---|
| v4 `slow2026` (`f23657710f3a6d00`) | 5,844 | **0.9865** | 0.9709 | 0.8794 | 0.8846 | 0.80 | 1.2249 |
| in-service `8d79186b` | 5,844 | **0.9866** | 0.9709 | 0.8725 | 0.8889 | 0.8077 | 1.2532 |

By year (v4 / in-service Spearman median): 2024 **0.9905 / 0.9899** (2,196 anchors, mean 273.9 members), 2025 **0.9856 / 0.9861** (2,190, 388.0), 2026 **0.9827 / 0.9834** (1,458, 399.9). The skew is *larger* in the recent years, where the member count is larger.

Member sets under the two clocks differ on **206 of 10,182 common anchors**; 193 pairs only-old, 205 only-new; the new clock adds the two anchors of §2.5(a) and drops none.

**Contrast discipline — these numbers are not additive.** The independently reproduced figures are different contrasts:

| Contrast | Median | Source |
|---|---|---|
| served matrix re-fed to the booster vs recorded scores | **47/47 anchors bitwise equal** | review §3.1 |
| stored research inputs vs served inputs, common members (**total**) | **0.9353434309** (min 0.7601561963), 32 anchors | review §3.1, AUDIT_PROD PROD-03 |
| **clock only** | 0.98434 | review §3.1 |
| **ranking universe only** | 0.94700 | review §3.1 |

0.9353 / 0.98434 / 0.94700 are **different contrasts and must not be added or decomposed into "how much alpha each cost"**. The total also carries the column-80 unit (PROD-04). None of these is a return IC, and none of them demonstrates the absence of predictive power.

### §2.7 The clock-aligned builder already exists and is a clean control

`pod_fea_ext_e.py` (`2cfc98609a99167b`) is `pod_fea_ext_clamp.py` **verbatim with only the clock changed** — `HI = E+1` as a half-open upper bound, `LO7 = max(HI−2016, 0)`, label rows [E+1, E+48], and `grid + 49 <= TT`. I diffed the two files this session: every other line is identical. This is exactly the shape queue item 3 asks for — one builder, one knob, and the legacy setting must reproduce the old artifact bitwise.

Its previous verdict is **not** a verdict on the clock: it passed its parity gate and failed the **export guard by rule**, Sharpe 2.260 against a threshold of 2.27, on a guard whose sampling error is about ±0.6 (AUDIT_DATA TIM-01, HANDOFF_round2_b0a573a1 L68). A ±0.6-noise guard cannot resolve a 0.01 difference. The prereg must judge this with a CI-based book judge under the frozen δ, not that guard.

### §2.8 Arm B for king is a different problem from arm B for DL

- **King has no feature normalisation.** LightGBM is fit on raw features (`pod_export_bundle_v4.py:67-68`), so the review's "freeze the training-time mu/sd" constraint is **vacuous for king**. What must be frozen instead is the **feature order and support** — the export asserts `[names[k] for k in keep] == PINS["keep_names"]` (L47), and that assertion is the object to hold fixed.
- **Only the shipped booster is saved.** `gbm` (fit on label-year < 2026) is written to `slow2026.txt`; the 2024 and 2025 fold boosters are the local variable `g2` and are **never saved** (L75-76). So king's historical OOF has the same problem as the DL monthly folds: the checkpoint that produced it does not exist. LightGBM fits are deterministic given identical data and parameters, so the same pattern applies — reconstruct, then certify with a positive control that reproduces the stored `PRED` before any arm-B number is quoted, and report a failure rather than substitute.
- **King OOF exists only where the forward label is finite.** `ok = np.isfinite(yv)` gates the training rows (L55-56) and `PRED[a, m[okm]] = pv[sel]` gates the predictions (L81). This is AUDIT_DATA D3 and the TRN-06 axis, pinned at the line. VERIFIED.

### §2.9 Open rows for TIM-01

| # | Row | Status | How it closes |
|---|---|---|---|
| T-O1 | Material effect of the 30 wrapped anchors beyond the 2 added | **NOT CHECKED** | Cheap; batch with the TRD-05 pod2 pass |
| T-O2 | Arm-B reconstruction control for king (reproduce stored `PRED`) | **NOT CHECKED** | Must pass before any king arm-B number |
| T-O3 | Book-layer effect of the clock | **NOT MEASURED** | The prereg's job; the old ±0.6-noise guard does not count as a verdict |
| T-O4 | Whether `pod_fea_ext_e.py` reproduces the clamp artifact bitwise under a legacy knob | **NOT CHECKED** | It is currently a separate file, not a knob; queue item 3 turns it into one |

### §2.10 Registered as its own item — the exporter writes the DL clock into a king field

Split out of §2.4 at the lead's instruction, because it is a separate fixable defect with the **same morphology as TIM-01 itself** (a register carrying the wrong clock), not a footnote to it.

| field | id proposed | severity |
|---|---|---|
| `king_train_last_label_end_utc` | **FXM-TIM-PROV-1** | P3 — conservative in direction, but it is provenance a reader will trust |

**Fact.** `pod_export_bundle_v4.py:264` writes `king_train_last_label_end_utc = _king_train_end + 4 * 3600`, i.e. **A + 4h**, and L66 prints the same. The clamp builder's king label is rows [E, E+47], which ends at **A + 3h55m**. So the bundle's own provenance states the **DL/accounting** label end in a field named for the **king** label. It is 5 minutes late, i.e. conservative for embargo purposes — but it is not the builder's definition, and a reader reconstructing the king cutoff from the bundle gets the wrong quantity. Compounding it, §2.4 now records that the deployed DL npz's `trained_through` is a **third** quantity again (the data-axis end).

**Red test suggested** (for whoever takes it; it is red on the current code for the right reason, and it is a value assertion, not a crash):
> Build a bundle from a fixture whose king label window is unambiguous, then assert `meta["king_train_last_label_end_utc"] == _king_train_end + 47 * 300` (A + 3h55m, the clamp builder's actual label end). The current exporter writes `+ 48 * 300` and the assertion fails on a **value**. A stronger variant asserts the field is derived from the **builder's own label window constant** rather than a literal, so the field cannot silently drift again if the clock knob changes — which it will, since `fm_king_fea_asof.py` makes the label window a knob (`FMK_CLOCK`), and under `serve_E` the correct value becomes A + 4h and the current literal would become accidentally right for the wrong reason.

**Not fixed by me**: it is exporter provenance, it belongs with whoever owns the bundle exporter, and changing it is a behaviour change outside my item. Registered here with its fact and its test so it is not rediscovered.

## §3 PROD-11 — three different member rules, and why "align training to production" is the wrong fix

**AUDIT_PROD severity P3, status `VERIFIED_IMMATERIAL` — that label is scoped to 147 recent anchors and I do not carry it to history.** In one sentence: production selects the top 400 of the live 450, king and DL training select the top 400 of all 829 cache names, and the replay selects a third population of 373 — but the live 450 is a 2026-08 object, so "make training match production" would put the FEA-01 look-ahead defect on the membership axis.

### §3.0 Devices, receipts, and the command I ran

aud-prod's device, opened before use (E-0826): `docs/audit_pipeline_2026-09-13/devices_prod/members/members_audit.py` (`7bc0a664158004ed`), 352 lines, receipt `receipts_prod/members_audit.json` (`eb8d5da70fd90d12`). It reproduces the P / K / D / R rules verbatim, asserts an env whitelist and every input sha, and reports six gates — **all six pass**, including `V3` (the K rule reproduces the stored king-meta members) and `V4` (the D rule reproduces the stored DL-target members). Its numbers below are therefore usable; its *scope* is not transferable, see §3.3.

My own read for §2.5(a) and §3.3, run read-only on pod2 2026-09-16 04:2xZ, command transcribed:

```
ssh pod2 'nice -n 19 python3 -c "
import numpy as np, hashlib, time
def sha(p):
    h=hashlib.sha256()
    with open(p,\"rb\") as f:
        for b in iter(lambda: f.read(1<<24), b\"\"): h.update(b)
    return h.hexdigest()
KM=\"/workspace/data/wide_fea_v4_meta.npz\"; DT=\"/workspace/dlw_v4raw/data/dlw_targets.npz\"; C=\"/workspace/data/dlnative_5m_wide829_f16_ext.npz\"
assert sha(KM)==\"12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51\", \"kmeta sha\"
assert sha(DT)==\"d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8\", \"dlw sha\"
K=np.load(KM,allow_pickle=True); D=np.load(DT,allow_pickle=True)
ke=K[\"E_ts\"].astype(np.int64); de=D[\"E_ts\"].astype(np.int64)
CTS=np.load(C,allow_pickle=True)[\"ts\"].astype(np.int64)
row={int(t):i for i,t in enumerate(CTS)}
f=lambda t: time.strftime(\"%Y-%m-%dT%H:%MZ\", time.gmtime(int(t)))
only_d=np.setdiff1d(de,ke); only_k=np.setdiff1d(ke,de)
print(\"king anchors\",len(ke),\"first\",f(ke[0]),\"| dl anchors\",len(de),\"first\",f(de[0]))
print(\"in DL not in king:\",len(only_d),\" in king not in DL:\",len(only_k))
rd=[row.get(int(t)) for t in only_d]
print(\"their cache rows E:\",rd[:40])
print(\"all E<2016?\", all(r is not None and r<2016 for r in rd))
print(\"first/last:\", f(only_d[0]), f(only_d[-1]) if len(only_d) else None)
ka=[row[int(t)] for t in ke if int(t) in row]
print(\"king anchors with E<2016:\", sum(1 for r in ka if r<2016), \"min king E:\", min(ka))
"'
```
Both sha assertions passed (so neither artifact had moved). Cgroup checked first: 40.9 GB used of 56.8 GB. No GPU used.

### §3.1 The three member rules, per column — read from the code, not from prose

| Axis | **P** production `shadow_loop_v3.py:365-377` | **K** king training `pod_fea_ext_clamp.py:28-39` | **D** DL training `pod_dlw_targets_raw.py:88-110` |
|---|---|---|---|
| window rows | **[E−2015, E]**, clamped | **[E−2016, E−1]**, `covr` clamped / rest **unclamped** | **[E−2016, E−1]**, clamped (`S = max(E−TRAIL, 0)`) |
| `covr` divisor | constant **2016** (L367) | constant **2016** (L29) | **actual window length** `max(E−S, 1)` (L90) |
| `qvm` divisor | finite **lqv** count (L373) | finite **lqv** count `n7` (L28, 30) | finite **ret5** count `nfin` (L89, 91) |
| `v7` divisor | finite **ret5** count (L369-370) | finite **lqv** count `n7` (L32) — numerator is ret5 sums | finite **ret5** count `nfin` (L93) |
| forward-label term | **none** | `isfinite(y4)` over rows **[E, E+47]** (L37) | `isfinite(y4s)` over rows **[E+1, E+48]** (L107) |
| universe | the **450** names the producer fetches | **829** cache names | **829** cache names |
| dtype | float32 | float64 | float64 |
| cut | top **400** by `qvm` (L376-377) | top **400** by `qvm` (L39) | top **400** by `qvm` (L109-110) |

So the rules differ on **seven** axes, not one. That the *outcome* differs on only one of them in a recent window is a measured materiality result (§3.2), not a statement that the rules agree.

### §3.2 What aud-prod measured, exactly

147 anchors, 2026-08-17 .. 2026-09-10. Symmetric difference of the 400-name member sets, one factor changed at a time:

| Step | median symdiff | mean | max |
|---|---|---|---|
| universe → live 450 (`K1_live450` / `D1_live450`) | **164** | 165.40 | 176 |
| drop the forward-label term (`K2` / `D2`) | **0** | 0 | **0** |
| serving clock (`K3` / `D3`) | 0 | 0.0952 | **2** |
| production divisor (`K4` / `D4`) | **0** | 0 | 0 |
| float32 (`K5` / `D5`) | **0** | 0 | 0 |

One-at-a-time against P directly gives the same picture (`P_univ829_vs_P` median 164; look-ahead, divisor and float64 all 0; clock max 2). Set overlaps on the same window: P vs K and P vs D both have intersection median **318 / 400**, each side 82 unique, **Jaccard median 0.659751**; and **every one of those 82 names is outside the live 450** (`K_not_P_outside_live450` median 82). K vs D: intersection **400**, symdiff **0** on all 147 anchors. The qvm gap at the top-400 cut has median **0.00444**. The A0 replay is a third population: 373 names, intersection with P median **332**, `P_not_R` median 68.

**So in that window the universe is the entire difference — and the other six axes are individually immaterial there.** That is a real and useful result. It is also the *only* window it covers.

### §3.3 Where that label stops, measured

The audit's own recommendation says "Keep TRN-06 open for history; no action for the recent window", and its severity note says "periods with delistings not covered". Two concrete places where the recent-window conclusion does not hold:

1. **K and D are not the same member rule in history.** `KD` symdiff is 0 on all 147 recent anchors, but the two axes differ by **exactly 30 anchors in 2022**: the king meta starts at 2022-01-08 00:00Z with **zero** anchors at `E < 2016`, while the DL targets start at 2022-01-03 00:00Z and carry all 30. Mechanism and receipts in §2.5(a) — it is the unclamped `E−2016` in K against D's clamped `S` plus D's true-window `covr` divisor. So "king and DL training members are identical sets" is **window-scoped**, and the divisor axis that measures 0 in the recent window is exactly the axis that removes 5 days of king history.
2. **The forward-label term measures 0 only where nothing dies.** `K2`/`D2` are 0 on 147 anchors with no delistings. AUDIT_TRAIN's TRN-06 channel counts, reported by fx-train, are forward-finite removals of **33 / 3 / 1 / 3 / 3** pairs per year and dead-but-kept members with label exactly 0 of **255 / 126 / 1,250 / 762 / 304** per year (TRD-05). Small, but not zero, and not inside the measured window.

### §3.4 The decision this forces — and the trap in it

**"Production members = top 400 of the live 450" cannot be applied to history.** `live_pins.json` (`fd27fe485417d307`) is a 2026-08 object. Restricting 2022–2025 training rows to those 450 names would make membership a function of a later list — **the FEA-01 defect, moved from the funding columns to the member screen**. A fix that "aligns training to production" by back-applying the live list is therefore not a fix; it is the same error on another axis. This is stated here so that no implementer reads PROD-11's "the whole difference is the universe" as an instruction to adopt the live list.

The genuine choice, which the prereg must make explicitly and which is **PENDING**:

| Option | Rule | Look-ahead? | Notes |
|---|---|---|---|
| (a) status quo | top 400 of all 829 | no (the 829 axis is fixed, not future-derived) but includes dead contracts (TRD-02/05) and non-crypto (UNI-01) | today's training |
| (b) PIT universe | top 400 of `U-PIT ∧ CRYPTO` | no | the mask the replay and judge already use (C-UNI-2, `build_crypto_mask.py`; unknown class kept) |
| (c) PIT ∧ tradable | (b) further gated by `tradability_v1.npz` `54d409d0…` | no | uses the pinned FX-DATA artifact; note FXR-DATA-1 — tradability is a *past-activity* proxy, admissible as a labelled screen, **not** as a settlement truth |
| (d) live 450 | top 400 of the live list | **YES — do not do this** | reproduces FEA-01 on the membership axis |

Whichever is chosen, it is a **separate intervention from the funding rebuild** (review narrowing iii) and must be its own arm or held fixed.

### §3.5 Open rows for PROD-11

| # | Row | Status | How it closes |
|---|---|---|---|
| P-O1 | Member-rule divergence over full history (not 147 anchors) | **NOT CHECKED** for all axes except the 30-anchor K/D case in §2.5(a) | One read-only pass over the stored metas, batched with TRD-05 |
| P-O2 | Universe choice (a)/(b)/(c) | **PENDING — prereg decision** | Named in the prereg before any number |
| P-O3 | Whether option (b) or (c) changes the top-400 cut materially in delisting-heavy periods | **NOT MEASURED** | Needs the tradability artifact joined to the member axes |
| P-O4 | PROD-11's own `VERIFIED_IMMATERIAL` label | **scope-limited, not carried** | Keep as "immaterial on 2026-08-17..09-10, 147 anchors, no delistings" |

## §4 UNI-01 — the training member screens have no asset-class filter, and the 2026 additions are not just "non-crypto"

**AUDIT_DATA severity P2.** The king and DL member screens are coverage, volatility, forward-label and top-400-by-volume — **no class term anywhere** (`pod_fea_ext_clamp.py:37`, `pod_dlw_targets_raw.py:107`). The replay and the judge do apply a class mask (`build_crypto_mask.py:11` (`43ebca0dff2c0bf2`), C-UNI-2: `underlyingType ∈ {COIN, INDEX}`, unknown class **kept**). So training and evaluation run on different populations, and the gap is growing.

### §4.1 Size of the population gap

From FACTS_DATA U1 (venue class snapshot `fa9196a34ce92028`), member pairs by year — king v4 meta and DL v4raw targets are **identical on this axis**:

| Year | king pairs | non-crypto pairs | share | anchors with non-crypto | unknown-class pairs |
|---|---|---|---|---|---|
| 2022 | 304,434 | 0 | 0 | 0 | 25,024 |
| 2023 | 410,358 | 0 | 0 | 0 | 23,296 |
| 2024 | 601,406 | 0 | 0 | 0 | 13,836 |
| 2025 | 849,811 | 24 | 2.8e-05 | 24 | 5,051 |
| **2026** | 583,200 | **42,363** | **7.2639%** | **1,458 (all of them)** | 344 |

Axis totals: 149 non-crypto symbols and 31 unknown-class symbols on the 829 axis; **80 non-crypto symbols actually appear as members**. `live_pins` is COIN 449 + INDEX 1, so production scores none of them. VERIFIED.

Note the unknown-class column: the CRYPTO mask **keeps** unknown names, so 25,024 pairs in 2022 are admitted by a rule that has not actually classified them. **NOT CHECKED**: what those 31 unknown symbols are.

### §4.2 What the 80 names actually are — this is not only a "class" question

Reading the symbol list rather than the class counter turns up three structures that matter more than the 7.26% headline:

**(a) Two leveraged inverse *pairs* on the same underlying.** `SOXLUSDT` / `SOXSUSDT` (3× long / 3× short semiconductors) and `TQQQUSDT` / `SQQQUSDT` (3× long / 3× short Nasdaq-100) are all members. `QQQUSDT` and `SPYUSDT` are members too, so the Nasdaq-100 exposure appears at three different leverages. VERIFIED (symbol list).

> **[ORIGINAL TEXT, KEPT VERBATIM — ITS CONSEQUENCE WAS REFUTED BY MEASUREMENT, 2026-09-16 04:4xZ]**
> Why this matters for **this** model specifically: the book is a cross-sectional rank. Two names whose returns are near-exact negatives of each other sit at opposite ends of the ranking on every anchor where the underlying moves, **by construction and not because of any signal**. A rank-neutral book then systematically holds one long and one short — which is a levered directional bet on semis or on the Nasdaq, not a cross-sectional alpha, and the two legs are each 3× levered so they do not net to zero underlying exposure. **INFERRED — the mechanism is not measured.** Cheap check, named here so it is falsifiable: the per-anchor rank correlation of `SOXL` vs `SOXS` (and `TQQQ` vs `SQQQ`) scores and the realised return correlation of the pairs; if the mechanism is real the score ranks are strongly anti-correlated and the pair appears in opposite book legs at a high rate.

**MEASURED, and the consequence is REFUTED** (device `fm_uni01_inverse_pairs.py` `aea55fd8164c6ab3`, receipt `UNI01_PAIRS.json`, pod2 read-only, rc 0, input shas asserted). The check was pre-named above; it ran, and it went against the hypothesis.

| pair | realised return ρ | **score-rank ρ** | **opposite-leg rate** | gross share (median) | anchors both members |
|---|---|---|---|---|---|
| SOXL \| SOXS | **−0.9871** | **+0.0642** | **0.364** | 0.0052 | 239 |
| TQQQ \| SQQQ | **−0.9862** | **+0.2711** | **0.2548** | 0.0047 | 259 |
| *null: 40 random CRYPTO pairs* | +0.1695 | −0.0313 [p5 −0.465, p95 +0.268] | **0.4792** [p5 0.337, p95 0.657] | 0.0052 | — |
| ref QQQ \| SPY (same direction) | +0.8453 | +0.4923 | 0.0777 | 0.0079 | 682 |
| ref TQQQ \| QQQ (same direction) | +0.9708 | +0.1072 | 0.2029 | 0.0064 | 340 |

**What holds and what does not:**
- **The premise holds.** The pairs really are near-exact return inverses: ρ = −0.9871 and −0.9862.
- **The consequence does not.** If the book systematically put one long and the other short, the opposite-leg rate would sit well **above** 0.5 and the score ranks would be strongly **negative**. Both are the other way: score ranks are weakly **positive** (+0.06, +0.27) and the opposite-leg rates (0.364, 0.2548) are **below the null median of 0.4792** — 0.2548 is below the null's 5th percentile. **The model puts these pairs on the SAME leg more often than two random crypto names.**
- **The reference pairs explain why.** Across all four pairs, whether realised returns are +0.97 or −0.99, the score correlation is weakly **positive** and the names tend to land on the same leg. That is the signature of the model scoring the equity-perp cluster on **shared characteristics** — they are all equity perps with similar microstructure — rather than on a signed directional forecast. The rank construction does not inherit the return anti-correlation, because the score is not a signed return forecast.
- **So the residual concern changes shape, and is not the one I stated.** It is not a levered offsetting directional bet. It is that a cluster of names is scored **alike** while its returns move **oppositely**, which would damage rank-IC on those names rather than create directional exposure. That is a different, smaller and still **unmeasured** concern; it is not asserted here.
- **Scope, which the 7.26% headline hides.** These four names are members far less often than the class share suggests: SOXS 239, SQQQ 259, TQQQ 340, SOXL 610, SPY 682, QQQ 844 of 1,458 anchors in 2026. Each pair's gross share is ~0.5%, indistinguishable from the null's 0.0052.

**(a′) Counterfactual, reading (5)** — dropping every non-crypto name from the member sets (mean **29.06** names removed per anchor across all 1,458 anchors of 2026) moves the surviving names' normalised rank position by median **0.0062**, p95 **0.0445**, max **0.1061** over 540,837 cells; median per-anchor max \|Δz\| **0.0163**. **Raw z / rank layer only — must not be quoted as a book-layer effect.**

**(b) Six commodity perps** — `XAUUSDT`, `XAGUSDT`, `CLUSDT`, `BZUSDT`, `COPPERUSDT`, `NATGASUSDT` — and equity/ETF perps whose underlyings trade on **exchange hours, not 24/7**. VERIFIED (symbol list). The 4-hour label for those names during a closed cash session is a structurally different process from a crypto perp's. **NOT MEASURED** — and it is the same family as TRD-01's frozen rows (a return that is near-zero for a reason unrelated to the signal). Cheap check: realised 4h return variance for these names by UTC hour-of-day and by weekday vs weekend, against a crypto control.

**(c) Pre-IPO / private-company perps** — `ANTHROPICUSDT`, `OPENAIUSDT`, `SPCXUSDT`, `MINIMAXUSDT` are members. These have no continuously-traded underlying at all. VERIFIED (symbol list); consequences NOT MEASURED.

`EWYUSDT` (Korea ETF) is also a member — worth a note for whoever picks up the T7 KRW-premium axis later, since it is a same-underlying instrument already inside the training universe.

### §4.3 Why UNI-01 is not simply "apply the CRYPTO mask"

The obvious fix — apply the class filter the replay already uses — is option (b) of §3.4 and is sound on the look-ahead axis (the class snapshot is a property of the instrument, not of a future list). Two cautions to carry into the prereg:

1. The venue class snapshot `fa9196a34ce92028` is **one snapshot dated 2026-09-08**. Using it to classify 2022–2025 rows is defensible because instrument class does not change, but it is still a later-dated artifact and must be declared as such, not assumed PIT. **NOT CHECKED**: whether any symbol's class differs from what it would have been at the time.
2. The mask keeps unknown-class names, so applying it does **not** remove the 25,024 unknown 2022 pairs. Whoever adopts it should say whether unknown means keep or drop, and that is a choice, not a fact.

This is a **separate intervention** from the funding rebuild and the clock (review narrowing iii).

### §4.4 Open rows for UNI-01

| # | Row | Status | How it closes |
|---|---|---|---|
| U-O1 | The leveraged-inverse-pair mechanism (a) | **MEASURED 2026-09-16 — consequence REFUTED** | Premise holds (returns ρ −0.987) but the book does NOT hold them on opposite legs: score ρ +0.06/+0.27, opposite-leg rate 0.364/0.255 vs a null median of 0.479. Receipt `UNI01_PAIRS.json`. The residual concern is different and unmeasured: the cluster is scored alike while its returns move oppositely. |
| U-O2 | Closed-hours return process for (b) | **NOT MEASURED** | Return variance by hour-of-day and weekday vs weekend, crypto control |
| U-O3 | Identity of the 31 unknown-class symbols | **NOT CHECKED** | One read of the class snapshot |
| U-O4 | Whether the class snapshot is PIT-safe per symbol | **NOT CHECKED** | Declare as a later-dated artifact until checked |
| U-O5 | Model/book effect of excluding them | **NOT MEASURED** | Prereg arm, held separate from the funding rebuild |

## §5 TRD-05 (+ TRN-06) — dead contracts enter training with a label of exactly 0, and the two channels are different

**AUDIT_DATA severity P3** (at most 0.21% of member pairs). Recorded here because it is the population half of TRN-06, whose prereg I own.

### §5.1 Why a dead contract passes the training screens

The screens decide tradability from the **share of finite `ret5` bars**, and a delisted contract's frozen rows are finite `0`, not NaN (AUDIT_DATA TRD-01: 156 dead perps write 13.77M frozen rows with return exactly 0):

| Term | King (`pod_fea_ext_clamp.py`) | DL (`pod_dlw_targets_raw.py`) | Why a dead name passes |
|---|---|---|---|
| `covr >= 0.95` | L29 | L90, L107 | frozen rows are finite ⇒ coverage stays 1.0 |
| `v7 >= 1e-4` | L32, L37 | L93, L107 | only fails once the trailing window is mostly frozen — about 7 days |
| forward label finite | `isfinite(y4)` L37 | `isfinite(y4s)` L107 | a frozen forward window sums to exactly 0, which **is** finite |
| top-400 by `qvm` | L39 | L109-110 | trailing volume decays over the same ~7 days |

VERIFIED — C-TRD-1. Production does not have this problem for a different reason, not a better rule: its base is `exchangeInfo … status == "TRADING"` unioned with the pinned live list (`shadow_loop_v3.py:315-317`), so dead contracts are absent from the universe entirely; its member screen itself is trailing-only, with no forward term (`shadow_loop_v3.py:374`, C-TRD-3).

### §5.2 The counts, and the two channels are not the same population

fx-train asked me to report both channels in the TRN-06 prereg; they are different things and must not be summed:

| Channel | 2022 | 2023 | 2024 | 2025 | 2026 | What it is |
|---|---|---|---|---|---|---|
| **A. dead-but-kept members, label exactly 0** | 255 | 126 | 1,250 | 762 | 304 | rows that *are* in training, with a label that is zero for a non-signal reason |
| **B. forward-finite removals** | 33 | 3 | 1 | 3 | 3 | rows *excluded* by the `isfinite(label)` term |
| Z24 (dead within 24 h), label exactly 0 | 324 | 108 | 1,214 | 650 | 81 | king meta |

Channel A is VERIFIED from AUDIT_DATA TRD-05 (`AD_H_tradability.json H4_training_rows`), and king and DL report **identical** A counts every year. Channel B is fx-train's report, recorded here as received. Largest A share is 0.21% of member pairs.

**They point in opposite directions.** Channel B is the *look-ahead* term — a training row is dropped because of a property of the future, which is the TRN-06 defect proper. Channel A is a *contamination* term — the row is kept and teaches the model that a dead name returns 0. Removing B (to make membership trailing-only, matching production) **increases** A unless a tradability screen is added at the same time. That coupling is the substance of the TRN-06 prereg and is why the two channels get separate arms.

### §5.3 What the loss does with a non-finite label

- DL trainer and refit: `YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0))` — a non-finite label is booked as a **0 return** inside the book loss (C-TRD-2, `pod_f10_train_monthly_v4.py:131`). So "excluded from membership" and "included with a zero label" are not the same intervention, and the trainer already does the latter for any NaN that survives.
- King exporter: trains only on finite labels and writes OOF predictions **only** on finite-label members (`pod_export_bundle_v4.py:55-56, 81`) — AUDIT_DATA D3. So the king OOF series carries the look-ahead availability mask in its very support, which is the same shape of defect as FEA-01 and must be declared wherever king OOF is used as an input.

### §5.4 The pinned artifact, and what is still open

The tradability artifact is pinned and verified present (§0.1): `tradability_v1.npz` `54d409d0…`, 10,285 anchors × 829 names, tradable(A) ⇔ at least one traded bar (`log_cnt > 0`) in (A−24h, A]. Its own limitation is registered as **FXR-DATA-1**: past activity is an admissible labelled screen, **not** a settlement truth, and exit P&L stays explicitly unknown. Nothing in §5 treats it as truth.

| # | Row | Status | How it closes |
|---|---|---|---|
| D-O1 | Join the pinned artifact to the king/DL member axes — how many member pairs are non-tradable at their own anchor | **NOT MEASURED** | A committed read-only device; the audit used its own H4 definition, so this is a two-instrument cross-check, not a repeat |
| D-O2 | Whether removing channel B raises channel A, and by how much | **NOT MEASURED** | Prereg arm (TRN-06) |
| D-O3 | King OOF support carries the look-ahead mask | **VERIFIED**, consequence NOT MEASURED | Declare at every use of king OOF |


### P10 (closed here, no section)
King training features are stored float16 and cast to float32 at fit (`pod_fea_ext_clamp.py:67`, `b9f9c72816241715`); the producer builds float32 from a float32 view of its float16 cache. **aud-prod measured it**: a float16 cast of served king features changes 0 deciles on 47/47 anchors, min Spearman 0.99996 (`receipts_prod/parity_king.json`, `9dbba68b`; AUDIT_PROD PROD-05). **No fix justified.** I did not re-measure; this row is VERIFIED-by-citation, and the scope limit is theirs: recent anchors, served inputs.
