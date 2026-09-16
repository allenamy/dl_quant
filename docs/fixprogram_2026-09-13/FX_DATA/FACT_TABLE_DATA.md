> **创建:** 2026-09-13 15:4xZ | **Session:** FX-DATA (fix worker, teammate of team-lead) | **状态:** 事实表, append-only by section; each section is committed before the red tests and before the fix code of its item | **作废条件:** a cited file sha changes (each row carries its sha16)

# FACT_TABLE_DATA — FX-DATA items (AUDIT_DATA bb8a2806 → FIXPROGRAM §4.3)

Conventions:
- `sha16` is the first 16 hex characters of the sha256 of the git HEAD blob (research repo), or of the pod2 file for `pod2:` rows.
- "Receipt" means an AUDIT_DATA receipt row (`docs/audit_pipeline_2026-09-13/devices_data/receipts/…`) or one of this program's receipts under `FX_DATA/receipts/`.
- Order disclosure for TRD-01: the SPEC was frozen at 73b59ec0 and the shared module plus builder were committed at 8ab0d769, both before this table. The module is a new definition; no existing eligibility code has been changed. The red tests and every rule fix come after this section's commit.

## §TRD — dead contracts admitted by research eligibility rules (TRD-01..05)

### TRD-A. Where each rule admits a contract (legacy code, the object the red tests must hit)

| # | Rule | File:line (sha16) | Code | Why a dead contract passes |
|---|---|---|---|---|
| A1 | Replay member set, `MEMBERS_TOPN=829` | `uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py:77-81` (9b8a6323); pod2 runtime `w10_sleeve.py` (b88e35a4) same lines | `_q = nan_to_num(qvk[_i], nan=-1.0) … _ord[_q[_ord] > -0.5]` | On frozen rows qvk (7-day mean log1p quote volume) is a finite 0, and 0 > −0.5 |
| A2 | Universe mask applied to members (`UMASK_SCOPE=m1`) | same file `:163-165` (legs), `:222-224` (run) | `m = m[_mk[m]]` | The mask row is U-PIT ∧ CRYPTO (A5/A6), which keeps a name for up to 2 months after death |
| A3 | Fund-leg rank base `FZB` | same file `:149-150` | `return xz(FE[j, :])[m]`: rank among every finite `f_fund_ema_v1` on the panel row | Funding records continue after death (AUDIT H5: 60,438 events), so the EMA stays finite |
| A4 | Trade set `sel` | same file `:244-245` | `ok = isfinite(y4[i, m]); sel = ok & (qv4h >= 2.5e5)` | Frozen close ⇒ y4 finite at 0. qv4h decays over 7 days (AUDIT TRD-03: 58/33/220/290/134 dead pairs selected per year) |
| A5 | U-PIT monthly row | `retrain_2026-09/health_check_2026-09-05/build_umask.py:46` (746700fd) | `elig = has & (age >= 30) & (vol30 > 0)` | vol30 over the 30 days before the month start is > 0 for the month after death |
| A6 | CRYPTO class filter | `retrain_2026-09/universe_crypto_2026-09-08/scripts/build_crypto_mask.py:11` (43ebca0d) | `underlyingType in ("COIN","INDEX") if s in CLS else True` | Delisted names are absent from today's exchangeInfo ⇒ unknown ⇒ kept |
| A7 | P2 TRADING proxy | `parity_replay_2026-09-12/phase2/devices/p2_prep_inputs.py:94-99` (a9216641); consumed at `p2_driver.py:153-154, 293` (dc4e6c85) | `TR24[:, j] = hi > lo` (≥ 1 settlement in (A−24h, A]); `st.base = sorted(set(tr) \| set(live))` | Settlements continue after death (AUDIT H5 P2 base proxy: 1.4/6.5/15.8/17.6/4.4 dead per anchor) |
| A8 | Panel `elig` | `retrain_2026-09/pod_panel_ext.py:40` (db7f0474) | `elig = (covr >= 0.95) & (v7 >= 1e-4)` | Frozen ret5 = 0 is finite ⇒ covr = 1; v7 stays ≥ 1e-4 until the 7-day window is mostly zeros |
| A9 | King member screen | `retrain_2026-09/v4_chain_2026-09-09/pod_fea_ext_clamp.py:37` (b9f9c728) | `ok = (covr >= 0.95) & (v7 >= 1e-4) & isfinite(y4)` | Same as A8; owner FX-MODEL (TRD-05) |
| A10 | DL member screen | `retrain_2026-09/v4_chain_2026-09-09/pod_dlw_targets_raw.py:107` (d7c52823) | `ok = (covr >= 0.95) & (vstd >= 1e-4) & isfinite(y4s)` | Same as A8; owner FX-MODEL (TRD-05) |
| A11 | T1 state member set | `uplift_r2_2026-09-13/T1/devices/t1_states.py:77-82` (d1dd994f) | `m = where(nan_to_num(QVK) > -0.5)`; `m = m[umask[u][m]]`; the umask row is carried forward if missing (UNI-03) | A1 + A2 |

### TRD-B. The A0 reference recipe (what the effect measurement must reproduce)

| # | Fact | Source (sha16) |
|---|---|---|
| B1 | A0 device = pod2 `/workspace/uplift_2026-09-11/w10_sleeve.py` b88e35a4, run with cwd `r3k/dev` | `uplift_2026-09-11/r3k_impact/r3k_reprice3.py:13,41-48,55` (c069cf8a) |
| B2 | A0 env = `LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=…/masks/umask_UPIT_CRYPTO.npz SLOW_NPY=…/king_v4/SLOW_v3_on_v4axis.npy FSEED=s FPRED=f10_A0_s{s}.npy COSTB_JSON=r3k/costb_PWR_G230k.json OUT_TAG=A0_PWR230k_s{s}` | `r3k_reprice3.py:41-48,55` |
| B3 | Tree links: `pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz → /workspace/data/wide_panel_4h_v2ext.npz` (5e67c055); `wide_fea_hist_meta.npz → refute_C6_2/altrun/meta_newprod_v4.npz` (0e3c09ac); `dlw_2026-08-22 → /workspace/dlw_v4raw`; `f8_2026-08-22 → health_check/dev_v4/f8_2026-08-22` | pod2 `ls -la r3k/dev` (15:0xZ today) |
| B4 | Archived arms: `r3k/arms/A0_PWR230k_s42.npz` 352ac36f, `_s2027.npz` aa44e18f; keys cols/rec/W/config_json | pod2 |
| B5 | Mask `umask_UPIT_CRYPTO.npz` 47d87b51, axis = the v2ext panel ts (10,039 anchors, 2022-01-31 → 2026-08-31 00Z) | AUDIT_DATA §6 |
| B6 | Judge estimator: g = net_ex / gross_total; W_FULL n = 10038, W_ALPHA n = 9138 (skip 900), KING_LIVE (2024+) n = 5838; UTC-day block bootstrap 2000 `default_rng([20260905,k])`; A0 W_ALPHA mean g = 0.6341957 | `uplift_2026-09-11/r18_foundation/devices/r18_judge.py:32-52,63-72,83-96` |
| B7 | Names that leave `m` are **not** force-exited: `_nonsel` covers only `m[~sel]`. Their `sm` decays by EMA with the band; price, carry and cost are booked only on `m` | `w10_sleeve_r18.py:258-268, 320-331` |

### TRD-C. Data facts behind the definition

| # | Fact | Source |
|---|---|---|
| C1 | Cache channel 4 is `log_cnt = log1p(kline count).clip(0, 20)`, float16; bars are labelled by close time (`open_time + 5 min`) | `retrain_2026-09/pod_merge_cache_ext.py:24,32`; `caliber_program_2026-09-09/holefix2_daily.py:43,46` |
| C2 | holefix2 filled holes from official daily archives with the same channel math (pre-existing cells bitwise unchanged), so filled bars carry true counts | `holefix2_daily.py:36-58`; `holefix2_daily.log` (390910/390910 bitwise, 487,969 fills) |
| C3 | After death: 13,770,575 untraded rows with ret5 == 0, log_qv == 0, cpos/tbf NaN; 156 contracts; 129 still writing in the x0910 tail | AUDIT `AD_H_tradability.json` H1 |
| C4 | Third-party count source: T7 1h perp klines (`count` column), 362 symbols, receipt `PERP_KLINES_RECEIPT.json` (device 1b1a07a3), 72,468 zero-count hours | `/Users/haosiyu/cc_tmp/krw_pull/checks/PERP_KLINES_RECEIPT.json` |
| C5 | Production base = exchangeInfo TRADING perpetual USDT ∪ pinned live names | `~/wide_shadow/shadow_loop_v3.py:315-317` (e9c98374) via AUDIT TRD-02 |

### TRD-D. Built-artifact receipts (appended after `fx_trd_build.py` ran; see FX_DATA/receipts/RECEIPT_fx_trd_build.json)

**Run 1 (15:13–15:15Z, device ab02564f, module a9fad82c) ended rc=1 at its last step.** Log: `receipts/fx_trd_build_run1_rc1_writer_bug.log`.
- Cause: the deterministic npz writer passed 0-d scalars through `np.ascontiguousarray`, which returns shape (1,). The `Artifact.load` reload roundtrip then refused the file with a spec mismatch.
- The written `out/trd/tradability_v1.npz` (pod2, sha16 b84f324d) is **INVALID** and must not be consumed. The module itself refuses it.
- No receipt JSON was written. The writer is fixed in the same commit as this row. Run 2 is pending (paused by lead, 15:2xZ).
- The checks below were printed by run 1 **before** the write. They are PROVISIONAL until run 2 reproduces them into a receipt.

| # | Reading (run 1 log, provisional) |
|---|---|
| D1 | P: axes equal; x0910 prefix == holefix2 on log_cnt **and** ret5 (bitwise); spacing census {300 s: 493,632}, no gaps; min positive log_cnt 0.69336 (= float16 log1p(1)), max 13.99 |
| D2 | Cells: TRADED 153,569,514 · UNTRADED 15,881,719 · NODATA 239,770,524. TRADED with NaN ret5: 840 (first bars). UNTRADED with ret5 == 0 exactly: 15,881,718 of 15,881,719; the remaining 1 has NaN ret5; 0 non-zero ⇒ every untraded bar is a frozen close |
| D3 | 4h grid 10,285 anchors × 829. TRADABLE cells W24H 3,208,920 · W4H 3,208,062 |
| D4 | R: 5m rolling flag == anchor state at every on-grid anchor (W24H, W4H) |
| D5 | D: independent bisect implementation, 123,820 cells, 0 mismatches (both windows) |
| D6 | T7 third-party control: 362 symbols, 7,638,831 hours compared. Traded-in-hour agreement is **100%** (7,566,867 both traded + 71,964 both zero; 0 disagreements either way); 504 hours where the cache has no data but T7 has a row |
| D7 | Census 2022 (W24H): dead_after name-anchors 17,380; lag (TRADABLE ∧ dead) 84; UNTRADED ∧ dead 2,893; UNTRADED but trades again later 1,911. W4H lag 14. Other years are in the log line truncated at 600 chars; the full table goes into the run 2 receipt |

### TRD-D2. Run 2 of the builder (rc=0) and the census verification — authoritative; supersedes the PROVISIONAL rows of §TRD-D

**Order disclosure.** The builder was already committed (`8ab0d769`, writer fix in `30c635e6`). `fx_trd_verify.py` was committed at `fe49fc86` and `fx_trd_probe_ret5nan.py` at `3df68676` (amended at `062b5594`), each **before** the run that produced its receipt. Run 1's literal command line was never recorded — `STATE_PAUSE.md` paraphrased it — so `receipts/run2_fx_trd_build.sh` (sha16 `a63e2935`) is the authoritative transcription for this artifact; `run3_fx_trd_verify.sh` (`8919caa6`) and `run4_fx_trd_probe.sh` (`44e9cbb1`) likewise.

| # | Fact | Receipt |
|---|---|---|
| D8 | **Run 2, rc=0**, 2026-09-16T02:57–02:59Z, 140.0 s. Device `066c3d74` (writer fix), module `a9fad82c`, spec `99ae35e0`, numpy 2.4.6. Env exactly the 6 whitelisted vars + `LC_CTYPE`; the receipt carries `env` and `argv` verbatim | `receipts/RECEIPT_fx_trd_build.json` (`cc66f8be`), `receipts/fx_trd_build_run2.log` |
| D9 | **Artifact** `tradability_v1.npz` sha256 **`54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302`**, 2,501,576 bytes, 16 keys, anchor grid 2022-01-01T00:00Z → 2026-09-11T00:00Z (10,285 anchors), `reload_roundtrip: true`. Committed at `FX_DATA/artifacts/tradability_v1.npz`; pod2 copy `/workspace/fx_data_2026-09-13/out/trd/tradability_v1.npz` | same |
| D10 | Every run-1 pre-write reading (P / A / R / D / C / T7) reproduced **line for line** in run 2 — the two logs differ only in elapsed seconds. The run-1 artifact `b84f324d` stays on pod2 quarantined as `out/trd/INVALID_run1_tradability_v1.npz.b84f324d` (sha unchanged) | both logs |
| D11 | Inputs pinned: holefix2 `1d7f459dee434ec4…`, x0910 `8115299410cd5e8d…`; identical to the audit's holefix2 input sha | `RECEIPT_fx_trd_build.json`, `RECEIPT_fx_trd_verify.json` |

**Verification run 3 (`fx_trd_verify.py` `2715658c`, rc=0, 125 checks, 0 failed), against the committed audit receipt `AD_H_tradability.json` (`529df8b3`).** The audit device and the SPEC do **not** share a definition or an axis: `ad_tradability.py` gates every bar state on `isfinite(ret5)` and stops at holefix2 (2026-09-01), while the SPEC reads `log_cnt` only and runs to 2026-09-11. Equal counts are therefore not evidence of equal sets, and each row below is a set or key-by-key comparison, not a count match.

| # | Check | Result |
|---|---|---|
| D12 | **V1** — the audit's H1 recomputed with the audit's own expressions on its own axis, compared key by key (a key present in the receipt and missing from the recomputation is a failure, not a skip): `TT` 490,753 · `cache_end` 2026-09-01T00:00Z · `symbols_with_trades` **825** · `symbols_dead_inside_cache` **156** · post-death signature **13,770,575** rows with `ret5==0`, `log_qv==0`, `cpos` NaN and `tbf` NaN all 13,770,575 · 5 by-year rows · 4 zero-trade-run keys · all 40 `top_symbols_post_death_rows` entries | all equal |
| D13 | **V2** — SPEC vs audit on the same prefix: SPEC-TRADED-not-audit **840**, SPEC-UNTRADED-not-audit **1**, audit-not-SPEC **0** in both directions (the SPEC is a strict superset by construction; a non-zero here would be a real disagreement). `last_traded` row differs for **0 of 829** names. The SPEC dead set at the audit's own threshold **equals** the audit dead set (symmetric difference empty) | as stated |
| D14 | **V3** — the artifact ties to that recomputation: `traded5_bits` and `nodata5_bits` on the holefix2 prefix equal the SPEC bar states **bitwise**; `last_traded_ts` equals the prefix value for all **160** names that do not trade in the x0910 tail (669 do) | bitwise equal |
| D15 | **V4** — dead-name **SETS** compared name by name: artifact (union axis, last trade < 2026-09-10T00:00Z) vs audit (holefix2, last trade < 2026-08-31T00:00Z) — **156 = 156 and identical**, symmetric difference empty in both directions. No contract joined the dead set between the two cache ends | identical |
| D16 | **V5** — H5 reproduced from the **artifact's own** `last_traded_ts` over the audit's dead names and the same three funding sources (`wide_multisrc/funding/*.zip` ∪ `fund_aug.json.gz` ∪ `r6_fund_sep.json.gz`): **60** names with settlements after death, **60,438** events (zip 58,509 / aug 60,188 / sep 328), 5 by-year keys, all 40 `per_symbol` entries equal | all equal |
| D17 | **V6** — the artifact's own union-axis census: **14,142,095** post-death untraded rows, **all** with `ret5` exactly 0 (0 NaN, 0 non-zero finite). Difference vs the audit's 13,770,575 is **371,520**, which equals `AD_H.H1_x0910_tail.untraded_rows_of_those` exactly = 129 already-dead names × 2,880 tail rows. The reconciliation has no residual term | `RECEIPT_fx_trd_verify.json` (`1c3ee363`) |

**Probe run 5 (`fx_trd_probe_ret5nan.py` `dce683ce`, rc=0)** — what the 841 definition-difference cells of D13 actually are:

| # | Fact | Receipt |
|---|---|---|
| D18 | 841 cells have a SPEC bar state but no finite `ret5` = **826** "first bar of that symbol's data" + **15** "first bar after a NODATA gap" + **0** anything else. 840 are TRADED, 1 is UNTRADED (BTCSTUSDT). Every one is a bar with no immediately preceding bar, so a return cannot be formed — which is the case SPEC §1 named when it excluded `ret5` from the definition | `receipts/RECEIPT_fx_trd_probe_ret5nan.json` (`65e36e53`) |
| D19 | 826 and not 829 because **BZRXUSDT, DOTECOUSDT, LENDUSDT have no data bar at all** on this axis (named, not inferred from 829−826); **BTCSTUSDT** has data but never trades. Smallest data-bar count among names that have data: **7,339** bars (≈25.5 days) | same |

**What is still not closed for TRD-01.** The artifact exists and reconciles with the audit census; no eligibility rule has been changed yet. Remaining: the red tests on the legacy rules A1–A11, the injection artifacts, the A0 four-arm effect measurement of SPEC §7, and the D1 equivalence label. TRD-03 closes with that label, not with this receipt.

## §TRD-02 — fund rank base and P2's TRADING proxy under the causal flag

Device `FX_DATA/devices/fx_trd02_base.py` (`9abc0b90`), committed at `c7eae225` **before** it ran. Run 6, rc=0, 54 s, `receipts/run6_fx_trd02.sh` (`44f8bbba`). Receipt `receipts/RECEIPT_fx_trd02_base.json` (`5981b61e`); per-anchor series `FX_DATA/artifacts/trd02_base_series.npz` sha256 **`1e85aaf686702556e961f8f1143f19143730ad38cae8eb6d1a56e19c2cde0fc9`** (236,760 bytes, both axes).

**Positive control first (37 checks, 0 failed).** The audit's H3 and `H5.P2_base_proxy_on_king_axis` were reproduced with the audit's own definitions — including rebuilding `Z24` from `ret5` exactly as `ad_tradability.py` does — to the last digit (`base_mean` 145.96119402985076 / 199.00502283105024 / 296.4690346083789 / 464.2365296803653 / 596.7116311080523; `base_DEAD_mean` 1.4432835820895522 / 6.519178082191781 / 15.824681238615664 / 17.497260273972604 / 4.263592567102546; `base_DEAD_max` 5/8/26/41/10; the P2 proxy block likewise). The device exits 1 before printing any new number if any of these differs.

| # | Fact (v2ext panel axis = the A0 / umask axis, 10,039 anchors; the king-meta axis gives the same values on its 10,177 panel-covered anchors) |
|---|---|
| E1 | **The causal contamination is larger than the descriptive one the audit reported.** Names in the fund rank base with no trade in (A−24h, A], mean per anchor: **3.42 / 9.07 / 19.81 / 20.81 / 5.59** (2022–26), max 8 / 11 / 32 / 48 / 14, share of the base **2.34% / 4.56% / 6.68% / 4.48% / 0.94%**. The audit's DEAD mean was 1.44 / 6.52 / 15.82 / 17.50 / 4.26 and its Z24 mean 3.30 / 8.68 / 17.47 / 18.11 / 0.75. `¬tradable` is the union of the UNTRADED and NODATA anchor states, which is the causal condition; DEAD (never trades again) and Z24 (has data, no trade) each miss part of it |
| E2 | The split matters by era: of the untradable names in the base, **UNTRADED** 3.30 / 8.68 / 17.47 / 18.11 / **0.75** and **NODATA** 0.12 / 0.40 / 2.34 / 2.69 / **4.84**. In 2026 the contamination is almost entirely NODATA — names on the frozen 829 axis that have stopped writing rows altogether — which is exactly the class the audit's Z24 cannot see |
| E3 | **P2's settlement proxy is contaminated at the same rate**: base 145.97 / 199.01 / 296.48 / 464.31 / 596.80, untradable in it 3.42 / 9.08 / 19.82 / 20.84 / 5.59, max 8 / 11 / 32 / 48 / 14. The proxy base and the FZB base are within 0.1 names of each other at every year, so the two contaminations are the same population, not two independent ones |
| E4 | **Inside the A0 member set** (MEMBERS_TOPN=829 qvk ranking ∩ m1 umask row): members 141.1 / 178.9 / 265.8 / 403.5 / 425.5, of which untradable **2.20 / 0.39 / 3.54 / 5.14 / 6.25** per anchor (max 7 / 1 / 13 / 11 / 16) |
| E5 | **Mechanism size, raw z.** Dropping the untradable names from the base moves the rank position of essentially every live member: `n_z_moved` per anchor **132.6 / 178.1 / 261.7 / 397.9 / 418.6** against member counts of 141 / 179 / 266 / 404 / 426. Mean \|Δz\| over live members **0.0106 / 0.0197 / 0.0265 / 0.0201 / 0.0027**; the largest per-anchor \|Δz\| in each year is 0.053 / 0.060 / 0.097 / 0.097 / 0.010, on a z that spans [−0.5, +0.5]. Members that leave the base entirely (their own z becomes undefined): 1.09 / 0.39 / 3.45 / 2.73 / 0.12 per anchor |
| E6 | **E5 is not a book effect and must not be quoted as one.** `legs()` applies `nan_to_num`, then `z -= z[ok].mean()`, then normalises by `g = Σ\|z\|`; a rank shift that is close to uniform largely survives none of that. The book-level number is the paired A0 `TB` / `TF` arm of SPEC §7 on the unmodified device, not this table |

**Status.** TRD-02's measurement half is done and P2 has its deviation series. The fix half (drop untradable names from `FZB` and from P2's base proxy) is carried by the SPEC §7 arms and by P2's own certified replay; neither is run yet, so TRD-02 stays OPEN.

## §TRD-04 — cross-sectional state variables recomputed with the causal flag

Device `FX_DATA/devices/fx_trd04_states.py` (`b36b6e09`), committed at `526cd559` **before** it ran, with its comparison rule frozen in its own docstring. Run 7, rc=0, 453 s, `receipts/run7_fx_trd04.sh` (`e7a1fc02`). Receipt `RECEIPT_fx_trd04_states.json` (`aeccaa8f`); series `FX_DATA/artifacts/trd04_states_series.npz` sha256 **`e3554dd7f36218b38b8feb194095dc85ca0f7c7cd11add9bd20c66f8631c7b4f`** (control and treated matrices for all three instruments).

**No legacy code was retyped and none was edited.** For T1 and r19 the original source text is read from disk, the relevant node is extracted with `ast.get_source_segment` and executed verbatim (the receipt carries each node's `ast.dump` sha); for T8 the module is imported and its own `features_row` is called. The treatment is injected into the array each instrument reads its members *from* — T1: `QVK ← NaN` on untradable cells; T8: `D["U"] ← U ∧ tradable`; r19: `members[i]` restricted to tradable.

| # | Fact | Receipt |
|---|---|---|
| F1 | **Positive controls, all three bitwise.** T1 reproduces the stored `T1_states.npz` (10,099 anchors × 18 cols, 181,782 cells); T8 reproduces `T8_data.npz` `F_42` and `F_2027` (10,038 × 24 each); r19 reproduces `regime_vars_fixed.npz` (10,039 × 16, 160,624 cells). The device exits 1 without a treatment number if any control fails | `RECEIPT_fx_trd04_states.json` checks `A/B/C.*positive_control_bitwise` |
| F2 | **T1** — `ts`, `k_meta`, `j_panel`, `umask_carried`, `BTC24`, `BTC72` are UNCHANGED bitwise. Every other column CHANGED, at 6,456 of 10,099 anchors for the return-based columns and 4,670 for the funding ones. Sizes as max \|Δ\| ÷ the column's own cross-anchor σ: **DISP72 8.66** · **PUMPSPR72 3.23** · **SIGF 1.32** · MUF 0.86 · PUMP72 0.59 · DISP24 0.40 · BREADTH24 0.15 · BREADTH72 0.14. Median \|Δ\| over changed rows is 1–2 orders smaller, so the contamination is a **tail** phenomenon, not a level shift | same |
| F3 | **T8** — `BTC4/24/72` and `TR1/TR6/TR42` UNCHANGED; the other 18 columns CHANGED at ~6,400 of 10,038 anchors (the funding ones at 4,670–4,749). Max \|Δ\| ÷ σ: **TKR24 2.64** · **SIGF 1.32** · **DMUF24 1.31** · **DSIGF24 1.31** · MUF 0.86 · DISP4 0.67 · ALT72 0.55 · CSR72 0.54. Universe cells dropped: 33,386 of 2,761,057 true cells (1.21%) | same |
| F4 | **r19 is an order of magnitude less affected**: only 1,180–1,285 of 10,039 anchors change, and **no** column exceeds 0.14 × σ (`sig_fund` 0.058, `disp24` 0.132, `breadth_up` 0.113, `young30` 0.007). The reason is the member rule, not the axis: r19 uses the META `members[i]` list, T1 and T8 use "every name with a finite qvk". **The damage scales with how permissive the member rule is** | same |
| F5 | **The audit's stated direction is wrong in the tail.** AUDIT_DATA TRD-04 says "the direction is toward lower breadth and lower dispersion" (frozen zeros compress the cross-section). At the anchors that move most, the sign is the opposite: at **2025-05-02 12:00Z** T1's `DISP72` is **0.4818 with the dead names and 0.0751 without** — an 84% drop — because **ALPACAUSDT**, whose last trade was 2025-04-30T09:05Z and whose anchor state is UNTRADED, carries a trailing 72 h compounded return of **+934%** (its real pre-delisting squeeze). A contract nobody could trade at the decision time was setting the instrument's dispersion reading. Member count at that anchor 385 → 379, so this is not a small-sample artefact of the injection | `RECEIPT_fx_trd04_probe_outliers.json` (`95c50dc7`), device `0c7e679a` committed at `f3f5f242`, run 8 `131f528b` |
| F6 | **The SIGF outlier is a name with no market data at all.** At **2023-02-11 08:00Z** T1's `SIGF` is **17.62 with / 4.78 without** — a 3.7× reading — from a single name, **BNXUSDT**, whose anchor state is **NODATA** (no 5m rows in the window) yet which carries `f_fund_now` = **−205.7 bps** 8h-equivalent on the panel row, and whose qvk is finite so it passes the member rule. Neither of the audit's two flags can see it: `Z24` requires finite `ret5` in the window, and `DEAD` requires the name never to trade again (BNXUSDT traded until 2025-03-17). **Only the tradable flag catches this class.** It also says a panel funding value exists for a name with no market data on that row — relevant to the FND items | same |
| F7 | **No equivalence label is issued from the data layer.** AUDIT_DATA's action ("if nothing moves beyond resolution, record VERIFIED_IMMATERIAL") cannot be followed as written: under FIXPROGRAM §0 item 8 that label may only come from `equivalence_labels.py` with a pre-frozen δ, and `DELTA_TABLE_K2.json` has no δ in state-variable units. Magnitudes are reported here; the label belongs to whoever re-runs T1 / T8 / r19 on the treated columns | device docstring, frozen before the run |

**Status.** TRD-04 is **measured, not closed**. What remains is a decision that is not the data layer's: T1, T8 and r19 own whether to re-run their readings on the treated state columns. The treated matrices are in the committed series npz, so none of them has to recompute anything.

## §RET-02 — the clipped-bar index is now committed, with a guard any device can call

AUDIT_DATA RET-02's action is "swap to raw_patch-corrected returns **or assert no bound bar in the window**, per device, when each is next reused". Neither half could be carried out from a committed device, because the index of clipped bars existed only on pod2. It is now `multi_asset/exports/research/common/data/bound_bars_ret5_x0910.npz` with the loader `common/bound_bars.py` and its battery `common/tests_bound_bars.py`.

| # | Fact | Source |
|---|---|---|
| G1 | The index is `r6_raw_patch_ext.py`'s output, sha256 **`94e8e8c119ea719a4ed1544813d433d00c39148a8e916018435ac10402a6f149`**, which is the `out_sha256` in the committed `r6_RECEIPT_raw_patch.json` — 952 cells inherited from `review_scratch/raw_patch.npz` plus 3 new (AKEUSDT 2026-09-02 21:45Z, BULLAUSDT 2026-09-05 03:00Z, WOOUSDT 2026-09-06 01:35Z) | `uplift_2026-09-11/r6_RECEIPT_raw_patch.json`; builder committed at `r6_devices/r6_raw_patch_ext.py` (`808d2f66`) by LIN-01 |
| G2 | **955 clipped cells, 440 symbols, 2022-05-11T13:10Z .. 2026-09-06T01:35Z.** By year **33 / 6 / 13 / 832 / 71** (2022–26) — 2025 carries 87% of them. Both signs (460 positive, 495 negative); raw values from **−0.951 to +3.678** against a stored ±0.300048828125. Worst symbols: LUNAUSDT 16, HIPPOUSDT 9, NAORISUSDT / TACUSDT / TANSSIUSDT / VELVETUSDT 8 | `bound_bars_ret5_x0910.npz`, censused in this commit |
| G3 | The module refuses the two ways this defect returns: there is **no default window** (`window=` is required and one of three stated conventions) and **no default sha** (`expected_sha256=` is required, 64 hex). A query whose window ends past `COVERAGE_END` = 2026-09-11T00:00Z **raises** rather than answering "clean" for bars the index never saw | `common/bound_bars.py` |
| G4 | Battery **20/20 green**, and a **mutation check**: the window default, the sha default, the coverage check, the `assert_clean` raise and the sha comparison were each removed on a scratch copy, and each time exactly the intended cell went red (5/5), with the restored file green again. A green battery on its own would only have proved old defects absent | `receipts/RET02_bound_bars_battery.log` |

**Status.** RET-02 is **not closed**: the eight devices AUDIT_DATA names (r14, r21, r12_mon, `event_state/build_sett_v4`, s12, `smooth_latency_core`, `materiality_probe_v2`, r13/beta) still read the clipped channel and their per-device exposure is still unmeasured. What changed is that each owner can now discharge the audit's action from a committed device in two lines — `BoundBars.load(expected_sha256=...)` then `assert_clean(symbols, lo, hi, window=...)` — instead of going to pod2. FX-TRAIN's TRN-02 coverage gate reads the same index.

## §EVL-01 — the CAL default: how big the trap is if it ever fires

AUDIT_DATA closes EVL-01 as `VERIFIED_IMMATERIAL` — "a latent trap; no affected run found". That is half the statement. Nobody had written down what it would cost if it fired, in the unit the programme judges book changes in. Device `FX_DATA/devices/fx_evl01_cal.py` (`146f2774`), run 11, rc=0, `receipts/run9_fx_evl01.sh` (`3fbdf464`), receipt `RECEIPT_fx_evl01_cal.json` (`bdcc0679`).

| # | Fact | Source |
|---|---|---|
| H1 | **The census is 54 files at HEAD, not 21 and not 33.** Every one reads exactly `os.environ.get("CAL", "simple")` — no other default exists in the tree. The audit's 21 is correct **under its own scope**: restricting to files first committed on or after 2026-09-09 gives exactly 21, reproduced file by file. Three of the 54 were first committed in 2026-08 and 51 in 2026-09. **My own earlier figure of 33, recorded in FIXPROGRAM §6, was wrong** — it was neither the HEAD count nor the audit's scope | `git grep` at HEAD; per-file first-commit dates |
| H2 | **No run since 09-09 recorded `CAL: simple`.** Across the whole repo `"CAL": "log"` appears 988 times, `"CAL": "prod"` 12, and `"CAL": "simple"` 27 — the last in 14 files, **all first committed 2026-09-04 or 2026-09-05**, all inside `retrain_2026-09/pod_port_2026-09-04/` and `retrain_2026-09/review_caliber_wf/` and `second_instrument_rebuild_2026-09-05/pod_logs/`, i.e. the caliber-review work whose subject was the caliber choice itself (E-0904-F). The audit's "none since 09-09" therefore holds, and the pre-09-09 occurrences are in directories where `simple` was the thing being studied. **Whether any of those 09-04/05 `simple` numbers still circulates as a current result is a knowledge-base question, handed to K4, not settled here** | `git grep` at HEAD, per-file first-commit dates |
| H3 | **Positive control, twice corrected, finally green with a 55× margin.** Rebuilding the A0 arm's own `pnl` (col 2) and `pnl_ex` (col 19) from the stored `W` and the meta `y4` agrees to **8.09e-6 / 8.61e-6 bps absolute**, which is **0.018** of the derived float32-storage bound `8·eps32·Σ\|w[m]·yv\|·1e4`. Both earlier attempts are archived red: run 9 (`fx_evl01_run9_rc1_wrong_control.log`) assumed `pnl_ex = Σ_j W[k,j]·y4[i,j]` and was refused at a relative error of 3.17 — the stored `W` is the **pre-reshape** `sm`, both channels are already in bps, and both sum over the **member set only**; run 10 (`fx_evl01_run10_rc1_float32_criterion.log`) used a relative test that blows up where the recorded pnl is near zero | `RECEIPT_fx_evl01_cal.json` checks `P.*` |
| H4 | **If the trap fires, the price channel moves by 6.5–7.2× the material band.** With the weights held at the CAL=log arm, mean Δ over W_ALPHA is **+0.327 bps/anchor/unit gross (seed 42)** and **+0.359 (seed 2027)** against the D1 δ of **0.05**. **91.2% of individual anchors exceed δ.** W_FULL means are +0.089 / +0.118 | same |
| H5 | **It is not a uniform bias, and the sign flips by era.** Per-year means (seed 42): **−1.13 / +0.02 / −0.32 / −0.02 / +2.66** (2022–26); medians are negative in every year (−0.10 / −0.05 / −0.30 / −0.34 / **+1.21** in 2026). `expm1(y) − y ≈ y²/2` is always positive, so the sign of the book effect is the sign of the signed weight on the names with the largest \|y\|: a negative median means the large squared moves usually sit on the **short** side. The worst single anchors are 2022-06-07 20:00Z (**−1778 bps**), 2026-07-01 16:00Z (+760), 2024-01-03 12:00Z (+273), 2025-11-06 20:00Z (+201) | same |
| H6 | **This is the accounting channel only and is a lower bound on the trap.** `CAL` also enters `legs()`, whose leg returns set the msharpe seat weights over LOOK=900, so a real CAL=simple run would carry different `W` as well. Measuring that needs a paired arm run, which this device does not do. Reported for both weight conventions: with the pre-reshape `sm` the W_ALPHA mean is +0.208 bps (seed 42) against +0.327 with `smr` | same |

**Status.** The audit's `VERIFIED_IMMATERIAL` describes **exposure** (no affected run since 09-09), and that half re-verified. **Consequence is not immaterial**: 6.5× δ on the mean and 91% of anchors over δ. The audit's action ("make CAL required or default to log") is **not actionable by FX-DATA as written** and is put to the lead: the A0 reference of SPEC §7 pins `w10_sleeve.py` at sha **b88e35a4 unmodified**, and 54 committed devices carry self-shas inside receipts, so editing the default would break a frozen spec and invalidate reproduction-by-path for every one of them. The options are (a) leave the archives and require `CAL` only in new devices, (b) re-pin SPEC §7 to an edited device, (c) a launch-side guard. This is a lead ruling, not a data-layer choice.

## §UNI-03 — the September universe-mask row, built and diffed

AUDIT_DATA UNI-03's action is "build a September mask row with the same monthly rule when September is rolled". Device `FX_DATA/devices/fx_uni03_sep_mask.py` (`e14df41a`), committed before each of its runs; run 14, rc=0, 5/5 checks, `receipts/run12_fx_uni03.sh` (`d1b6e5c7`), receipt `RECEIPT_fx_uni03_sep_mask.json` (`08bf49d4`).

**No new cache lineage was needed.** `dlnative_5m_wide829_f16_ext.npz` — the cache the committed mask was built from — ends exactly at 2026-09-01T00:00Z, which **is** the first September anchor, and the rule's window is the 8640 bars strictly before it. The September row is the same rule on the same cache one month on, not an extrapolation.

| # | Fact | Receipt |
|---|---|---|
| J1 | **Positive control bitwise on both masks**: all 56 committed monthly rows of `umask_UPIT.npz` rebuilt from the cache with zero differing cells, and `umask_UPIT_CRYPTO.npz` likewise after the class filter (31 symbols absent from the 2026-09-08 exchangeInfo snapshot, kept per `build_crypto_mask.py`). The device refuses to write a September row if either fails | checks `A.upit_rebuilt_bitwise`, `A.crypto_rebuilt_bitwise` |
| J2 | **The 2026-09 row**: anchor 2026-09-01T00:00Z, 8640 bars used, 826 listed, 676 eligible, top 449, 449th-name trailing-30d volume **57.53 M USD** (August: 53.19 M). CRYPTO allowed **375** names (August 373) | `B_september_row` |
| J3 | **Against the carried-forward August row: 60 names added, 58 dropped** — 118 name-cells out of an allowed set of 373, **31.6%** | `C_difference` |
| J4 | **For scale, that is about 1.5× normal monthly churn.** Median month-over-month churn in the CRYPTO allowed set over the last 12 months is **40 added / 41 dropped** (2026-03 → 08: 39/41, 41/50, 54/59, 43/55, 34/54, 49/76). So most of the September difference is the ordinary monthly turnover any carry-forward would incur, and September is a somewhat heavier month — **not** a September-specific anomaly | `C_monthly_churn_for_scale` |
| J5 | **No entrant falls into the "unknown class ⇒ kept" branch**: every one of the 60 added names is present in the 2026-09-08 exchangeInfo snapshot, so none is admitted by the fallback | `D_unknown_class_among_entrants` = [] |
| J6 | **Boundary, and I got it wrong twice before fixing it.** The x0910 panel axis extends past the committed mask by **60** anchors, but **5 of them (2026-08-31 04:00Z .. 20:00Z) are still August** and the monthly rule assigns a row by calendar month. Runs 12 and 13 wrote the September row over those five. The true September anchor count is **55**. Rows are now assigned by the anchor's calendar month with an assertion covering the August tail, and the superseded artifact sha `023adc09` must not be used | `C_difference.still_august_anchors`, check `W.august_tail_anchors_keep_the_august_row` |
| J7 | **Outputs**, on the x0910 panel axis (10,099 anchors), prefix bitwise identical to the committed mask: `umask_UPIT_x0910_sep.npz` **`66e21c8957a04ea853fa8e87e96262df31ce9d4928aac923bf083c40772914a6`**, `umask_UPIT_CRYPTO_x0910_sep.npz` **`de7c34d79d7047e34f577abd2ef825554e064193fda757f6857e352596e0e77b`**. Both committed under `FX_DATA/artifacts/` | `outputs`, check `W.august_prefix_unchanged` |

**Status.** The row exists and the approximation is sized. **UNI-03 is not closed by this**: no existing September reading has been re-run on the real row, and that is the owners' call — T2 d4, T5c/T5d and `t1_states.py` (which carries the mask forward in the same way, `t1_states.py:78-81`). October's roll should use the same device rather than carrying August or September forward again.

## §FND — the settlement-interval family (FND-01 / FND-02 / FND-03), facts before code

The audit already **measured** FND-01 (`AD_B_funding_iv.json`, device `f6d58b2b`, committed before its run); this section adds what the register does not yet have: the code shape shared by all three, the full site census in git, and the boundary between what FX-DATA rebuilds and what belongs to a suspended secondary axis. No number below is new — every one is either read off committed code or cited from the audit receipt.

### FND-A. One resolver, three failure modes

Every funding builder in this lineage resolves a row's settlement interval the same way (`pod_panel_ext.py` L104-120, `pod_panel_splice.py` L60-73, `r6_panel_splice.py` L82-91):

```
iv_full = declared-if-present  ->  else spacing (round(diff(ft)/3600), kept only if 0 < dt <= 24)
        ->  else 8.0           ->  then snapped to ALLOWED = {1, 2, 4, 6, 8}
rate_nf = fr * (8.0 / iv_full)                      # the v1 EMA input
```

| # | Fact | Source |
|---|---|---|
| K1 | The precedence is **explicit-over-spacing**, and "explicit" is read from a **per-symbol** map, not a per-settlement column: `rows.append((ts, rate, AUG_IV.get(s, np.nan)))` / `SEP_IV.get(s, np.nan)`. One symbol therefore gets one interval for its whole API segment | `pod_panel_ext.py:105`, `pod_panel_splice.py:60-61`, `r6_devices/r6_panel_splice.py:82` |
| K2 | **FND-01 fires only in r6 because only r6's source fills the map.** `fund_aug.json.gz` was written with `"intervals": {}` (`fund_pull_pod.py:28`; AD_A confirms `intervals_n: 0`), so `AUG_IV` is empty and the August API rows fall through to spacing. `r6_fund_sep.json.gz` was written by `r6_fetch_funding.py` from a single `/fapi/v1/fundingInfo` read at 2026-09-11, so `SEP_IV` is full and wins over spacing for every September row. **Same code, different data** — which is why the audit calls the pattern a latent trap for any future pull that fills `intervals` | `fund_pull_pod.py:28`; `AD_A_inventory.json`; `r6_devices/r6_fetch_funding.py:33-34,69` |
| K3 | `r6_panel_splice.py`'s own header (L13) says the block is "copied VERBATIM from `pod_panel_splice.py` L83-L102". **Checked, not assumed**: the git copy of `pod_panel_splice.py` is byte-identical to the pod2 copy (sha `a9c29141985f11ad…` both sides) and carries the same `AUG_IV.get(s)` + explicit-over-spacing shape. The claim holds structurally | both files, hashed this session |
| K4 | **The site census in git is 14 files, not the "three `AUG_IV.get` sites" FIXPROGRAM §4.2 records**: `pod_panel_ext.py` (`db7f0474`), `pod_panel_splice.py` (`a9c29141`), `pod_export_bundle_v3.py` (`c210bac6`), `pod_femat_build.py` (`1709bd25`), `v4_chain_2026-09-09/pod_export_bundle_v4.py` (`42555a37`) and its `.r1_23b1a5c7` variant, `second_instrument_rebuild_2026-09-05/patched/pod_panel_ext.py` (`1a2614a6`), `runpod_scripts/workspace_mirror/pod_panel_ext.py` (same blob as the canonical, `db7f0474`), `runpod_scripts/workspace_mirror/pod_export_shadow_bundle.py` (`b3c2a3aa`), `r6_devices/r6_panel_splice.py` (`cccc5b6b`), plus the four T5d devices that implement the **correction** rather than the defect. Any fix must cover the whole family, and the mirrors mean one blob appears at two paths | `git grep -l 'AUG_IV\.get\|SEP_IV\.get'` over `multi_asset/` |
| K5 | The first settlement row of every symbol has no predecessor, so `dv[0]` is NaN and the resolver falls to the **8.0 default** — the same cold-start first-row-default-8 family FIXPROGRAM P9/P6′ describes (07-26 08Z ×61, DOS 08-11 16Z, ILV 09-04) | `pod_panel_ext.py:118-119` and the same lines in the other two |

### FND-B. What is already measured, and by whom

| # | Fact | Source |
|---|---|---|
| K6 | FND-01's size is **not** an open question: the x0910 tail has **547 wrong interval cells over 23 symbols** (IOST 1h for true 8h; SKR/T/SOPH/ZKC/COTI 4h for true 1h; six tokenised-stock perps 4h for 8h), corrected `f_fund_ema_v1` differs by up to **0.0115** with **844 cells above 1e-6**, per-anchor Spearman ≥ **0.9911**, and **47 FTRIM class flips on 38 anchors**. The incumbent prefix is clean (0 mismatches), and the audit's replica of the r6 rule reproduced the panel tail exactly (iv cells not reproduced 0, EMA maxabs 0.0) | `AD_B_funding_iv.json` `panels.v2ext_x0910`, `PC2` |
| K7 | **4 of those 547 sit exactly on P9's switch rows** (COTI 08-31 20Z, ZKC 09-02 20Z, T 09-06 00Z, SKR 09-07 20Z), where the pull-time value is probably the declared one and *spacing* is the wrong reference — so the true count is **543-547**, and a rebuild that uses spacing as truth would re-introduce an error on exactly those rows | AUDIT_DATA FND-01 caveat + FIXPROGRAM P9 |
| K8 | **A corrected panel already exists**: `T5d/devices/t5d_ivfix_panel.py` (`63c16a68`) rebuilds the event stream with r6's own code, requires pass 1 to equal the x0910 panel **bitwise** (gate G-R6), then replaces `iv_full` with `iv_true` = producer-ledger interval where the settlement is in the ledger, else the timestamp gap snapped to ALLOWED. Its `iv_true` is therefore **not** P9-aware: on K7's switch rows it still falls back to spacing | `t5d_ivfix_panel.py` header and L26-33 |
| K9 | FND-02 is the same resolver on the **canonical** panel: interval matches (zip column, else spacing) on all **3,263,922** compared cells, and spacing agrees with the archive column on **2,522,533 of 2,523,179** zip rows — the **646** disagreements are consistent with P9 switch rows but were **not classified row by row**. So the mislabel exists unmeasured wherever a panel row came from the API rather than a zip: the 2026-08 rows of v2ext/v3splice and every x0910 September row | `AD_B_funding_iv.json` `PC1`, `panels.v2ext` |
| K10 | FND-03 is **138 cells**, all 2026-08-01..08-14, five names (DEXE, ERA, BANK, PROM, ACE), stored 4h against a true 1-2h — the same rows P2 traced to the 08-16 bundle seed (D17). Its builder is on jpline and unverifiable from here | `AD_B_funding_iv.json` `panels.v3splice`; AUDIT_DATA FND-03 |

### FND-C. Scope boundary — what FX-DATA will and will not do

FND-01's registered action has two halves and they sit on different sides of the main/secondary line the user drew.

- **Mine (main)**: build one shared, P9-aware interval resolver and rebuild the x0910 funding tail with it, as a **new** artifact beside the old, with the G-R6-style bitwise positive control first (reproduce the incumbent tail with the incumbent rule before changing anything). Precedence: **zip-declared per settlement row > P9 exact label > spacing, switch-row-aware > flagged `unresolved`, never a pull-time per-symbol map.** K7 is the reason the P9 tier must sit above spacing rather than beside it.
- **Not mine (secondary, suspended by the user's 14:13Z ruling)**: re-running T1 D2, the September carry readings, or T5c/T5d on the corrected panel. That is T5d-R and T1 LIVE_D2.
- **Not mine (FX-TRAIN, TRN-07)**: retiring the `AUG_IV`/`SEP_IV` pattern in the October chain. K4 says the family is 14 files, not 3; FX-TRAIN needs that count.
- **Blocked**: the rebuild consumes FX-PROD's P9 declared-interval table (`366763a4`), and I will not build on a table whose status I have not re-confirmed with its owner. Asked 2026-09-16; unanswered at the time of writing.
