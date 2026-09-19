> **创建:** 2026-09-19 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(只读普查代理, lead 入库) | **状态:** 十月 v4 月度链就绪普查 —— 结论: 今天不能跑, 且按现设计即使跑通也不移动两条模型腿的训练截止 | **作废条件:** 链装置或合同更新后重新普查

# October v4 retrain chain: readiness census (read-only)

> **Written:** 2026-09-19 ~05:30–06:30Z | **Method:** read-only. I read the git device dir `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/` (clean worktree; last device commit `f9f495507`), the four docs, STATE, and receipts. On pod2 I used only `ls`, `stat`, `sha256sum`, `ps`, `du`, `nvidia-smi`, and numpy metadata reads through stdin python. Nothing was launched, modified or killed. I ran no test battery. Battery counts below come from commit messages or docs, and no verdict-line log exists for the latest counts. Items marked **[code-read]** are predictions from reading the source. I did not execute them.

---

## 0. Bottom line

1. **The chain cannot be run for October today, and missing data is only part of the reason.** The October template has 20 `TODO_` keys, and none of their October files exist. In addition, reading the code turned up **eight structural conflicts**. In each one, a September-scoped device refuses or fails on October-shaped data. Each needs a design decision or prereg amendment and then approval (§6 B1–B8). Most were not on any open-question list I could find.
2. **Data:** nothing on pod2 reaches the required end. The furthest is the research `x0910` cache and tradability file, which end at 2026-09-11T00:00Z. The canonical cache, all panels, the masks and the funding data end between 2026-08-31 and 2026-09-01. The required 5m data runs through the bar closing at **2026-09-20T00:00Z**, and that bar cannot be downloaded before the 2026-09-19 daily archive is published on 09-20.
3. **Compute:** the GPU is idle (0 %, 2 MiB) and no chain process is running. Measured costs are about 1.6–1.7 GPU-hours and about 4.6 h of driver wall time. The month roll (data preparation) adds about 2–2.5 h including network fetches.

---

## 1. The 20 `TODO_` keys in `v4_month_2026-10.env.template` (sha `033f559a…`, mtime 09-18 19:53)

"Sept analogue" means the file the September contract uses. All paths below are on pod2 unless marked mac.

| # | Key (template line) | Artifact needed | October artifact exists? | Nearest existing artifact (path · mtime · extent) | Producer |
|---|---|---|---|---|---|
| 1 | `CACHE` (L9) | 5m cache = holefix2 canon plus an **append-only** roll (TRN-16), ending **exactly** at ts 2026-09-20T00:00Z (496,225 rows) | **No** | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz` · 09-09 02:27 · 490,753 rows, 2022-01-01T00:00Z→**2026-09-01T00:00Z**, sha `1d7f459d`. Research extension `…_holefix2_x0910.npz` · 09-11 15:07 · 493,633 rows →**2026-09-11T00:00Z**, sha `8115299410cd`, built append-only (BW-1 bitwise PASS, `uplift_2026-09-11/r6/RECEIPT_cache_merge.json`) | No chain builder. `retrain_2026-09/pod_merge_cache_ext.py` is hard-coded (base `_fresh`, output `_ext` = forbidden lineage, IDX 08-21..09-01). The research `r6_merge_cache.py` (base and output settable by env, IDX end hard-coded 09-11) is archived in git at `multi_asset/exports/research/uplift_2026-09-11/r6_devices/`. Needs network (§2) |
| 2 | `PANEL_SPLICE` (L10) | v3splice panel extended to the new axis. The panel ends 20 h, i.e. 5 anchors, before the axis end by construction (TRN-17, driver L405–407) | **No** | `/workspace/data/wide_panel_4h_v3splice.npz` · 09-01 05:55 · 14,425 rows, 2020-01-31→**2026-08-31T00:00Z** | `pod_panel_splice.py` (git) writes the **fixed** paths `/workspace/data/wide_panel_4h_v3splice.npz` and `/workspace/fund_state_canoncont.json`, so running it would overwrite September's receipted files. `r6_panel_splice.py` has the fetch-time funding-interval defect (memory `x0910_fund_iv_interval_mismatch`: 547 `f_fund_iv` cells across 23 names wrong) |
| 3 | `PANEL_KING` (L11) | v2ext panel extended | **No** | `/workspace/data/wide_panel_4h_v2ext.npz` · 09-01 05:30 · 10,039 rows, 2022-01-31→**2026-08-31T00:00Z**. The interval-corrected research panel `/workspace/uplift_r2_2026-09-13/T5d/panel/wide_panel_4h_v2ext_x0910_ivfix.npz` exists (I did not inspect it) | `pod_panel_ext.py` (default output overwrites v2ext) plus splice |
| 4 | `HOLE_CELLS` (L13) | Fill geometry for the October cache | **No** | `/workspace/review_scratch/holefix2_cells.npz` · 09-09 03:03 · 1,422,720 cells, 2022-02-26T00:05Z→2026-09-01T00:00Z. The last run covers rows 490465–490752 = **all 798 symbols × 288 rows of 2026-08-31**. Its neighbourhood is [490417, 499392] ≈ 08-30 20:05Z → **10-01 00:00Z** | `v4_hole_cells.py` is hard-coded (compares holefix2 with `_ext` and writes to the review_scratch path). If the roll adds no new fills the September geometry is reusable, but no month-generic producer exists |
| 5 | `BUNDLE_BASE` (L27) | The previous generation's own fold-IC json, re-established each month | **No** | `/workspace/slow_scorer_v4base.json` · 09-09 03:07 · sha `dce6a228` (= contract `approved_baseline.bundle_base_sha256`) · content 2024 .0548 / 2025 .063 / 2026 .0571, which are the **v3** own fold ICs | Manual (RUNBOOK §1). The in-service generation is still v3, so which generation counts as "previous" is open (§6 B9) |
| 6 | `EXPORT_PANEL` (L28) | Same file as #2 | No | as #2 | as #2 |
| 7 | `EMA_STATE_JSON` (L29) | Funding-EMA state at the new splice cut | **No** | `/workspace/fund_state_canoncont.json` · 09-01 05:55 | Written by `pod_panel_splice.py` (fixed path) |
| 8 | `LIVE_PINS` (L31) | Re-copied from the in-service bundle config | **No** | `/workspace/live_pins.json` · 09-01 03:41 · sha `fd27fe48` (= approved). **The in-service mac `~/wide_shadow/shadow_bundle/config.json` `symbols_live` (450) and `keep_names` (78) are content-identical to this file** (hash of `json.dumps` equal) | Manual copy. TRN-15 (contract) says the October pins must be approved per month |
| 9 | `FUND_AUG` (L32) | Funding REST tail through ≥2026-09-20T00:00Z | **No** | `/workspace/fund_aug.json.gz` · 09-01 02:30 · 2021-12-01→**2026-09-01T02:00Z**, 827 symbols. Research `r6/dl/r6_fund_sep.json.gz` covers 08-29→09-11 15:00 but carries fetch-time intervals | `fund_pull_pod.py` (git; writes the fixed `/workspace/fund_aug.json.gz`, so it would overwrite) or `r6_fetch_funding.py` (public `fapi.binance.com/fapi/v1/fundingRate`). Needs network |
| 10 | `LEGS_PANEL` (L36) | Same file as #2 | No | as #2 | as #2 |
| 11 | `SIGNAL_RECEIPT` (L45) | `S_BITWISE_signal` v2 receipt for arm A1 on this month's panel and FEMAT | **No** | September used `/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json`, a v1-shape receipt with no self_sha, arm or inputs | `gate_signal_parity_v2.py` (env `SIG_PANEL SIG_FEMAT SIG_ARM V4CHAIN_DIR SIGGATE_OUT`). It needs an October FEMAT. The existing `/workspace/fx_data_2026-09-13/out/inject/femat_f_fund_ema_v1_tradable_W24H.npz` is on the panel axis ending 08-31T00Z |
| 12 | `MEMBER_MASK` (L61) | tradable ∧ live mask on the cache 4h grid through 09-20T00Z | **No** | `/workspace/fp2_2026-09/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz` · 09-18 08:52 · 10,225 rows →**2026-09-01T00:00Z**. It was built by build-side sha `0704cde5`, which the contract has since superseded with `a369e1c0` | Chain outside the driver: 1h klines (`/workspace/fx_data_2026-09-13/t7_klines_1h`, ends **2026-08-31T23:00Z**) → `fx_trd_build.py` → `tradability_v1.npz` (exists on x0910: ts5 →2026-09-11T00:00Z) → `fp2_member_mask_build.py` → `v4_member_mask_liveness.py`. All are ad hoc `run*.sh` scripts in `/workspace/fx_data_2026-09-13/` |
| 13 | `UMASK_NPZ` (L65) | Evaluation umask (UPIT_CRYPTO ∧ tradable W24H) on the new panel axis | **No** | `/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz` · 09-16 04:25 · 10,039 rows →2026-08-31T00:00Z · sha `3badc4b6` | `fx_trd01_inject.py` (inputs: tradability, v2ext panel, `health_check/masks/umask_UPIT_CRYPTO.npz`, which also ends 08-31T00Z). **Needs a per-month approval: `approved_controls_refs["2026-10"]` is `null`** |
| 14–16 | `CONTROLS_REF_KING_FEA / _KING_META / _DL_TARGETS` (L69–71) | The previous month's king features, meta and RAW targets, approved per month | September's exist | `/workspace/data/wide_fea_v4.npy` `268f6c9c`, `…_meta.npz` `12ea42c4`, `/workspace/dlw_v4raw/data/dlw_targets.npz` `d1976cf6`. These equal the approved 2026-09 refs. The targets file's mtime is 09-12 15:17 (rewritten by a `chain_v4_data` run logged in `review_scratch/chain_v4_data.log`), but it is bitwise equal to the approved sha | Whatever is chosen must be approved into `month_contract_rulings.CONTROLS_REF_identity.approved_controls_refs["2026-10"]`, which is **null**. Also see §3: `fp2_controls.py` cannot PASS on October data |
| 17 | `PREV_SHA_JSON` (L78) | `{path: sha}` of the previous month's 8 ROLLED artifacts | **No** | none | `mk_prev_sha_record.py <prev env> <out>`. **Defect: L18 reads `os.stat().st_flags`, which does not exist on Linux (pod2 venv: `hasattr → False`), so it raises AttributeError on pod2, where the files live.** The declared `PREV_MONTH_ENV=/workspace/review_scratch/v4_month_2026-09.env` (L77) is **missing on pod2** |
| 18 | `PREV_DLW_CLIP` (L83) | Previous month's CLIP targets and fea82 (STEP1 B reference) | September's exist | PREREG §2 says `/workspace/dlw_hf3` (targets `720f03a4`, 09-09 02:29, 10,212 anchors →08-31T20Z) | — (reference choice, §6 B4) |
| 19 | `PREV_F8` (L84) | Previous month's fea89 | September's exist | `/workspace/f8_v4/data/f8_fea89.npz` · 09-09 03:03 | — |
| 20 | `PREV_KING_FEA` (L85) | Previous month's clamped king features | September's exist | `/workspace/data/wide_fea_v4.npy` (v1 builder, unmasked, 10,182 anchors from **2022-01-08**) | — |

**Non-`TODO_` keys that also block or need action:**
- `MONTHS_ALL` (L20) includes `202609`. Once the axis ends 2026-09-19T20Z, `v4_months.py` refuses it. I verified this locally in pure Python: `declared MONTHS_ALL contains month(s) [202609] that are not complete…`. The driver runs this check only at the **mwf** stage (driver L422), about 3–4 h into a run.
- `RAW_PATCH=$R/raw_patch.npz` also needs `$R/raw_patch.manifest.json`, and the cache stage requires `RAW_PATCH_COVERAGE` PASS (driver L258–266). The September patch covers 952 bars, 2022-05-11→2026-08-24. Applied to the x0910 cache it FAILs and names AKE/BULLA/WOO (`FX_TRAIN/STATE_PAUSE.md`).
- `HC=$R/health_check` needs an isolated dev-tree copy containing `masks/umask_UPIT_CRYPTO.npz`, `calib/costb_fee_steady.json` (`9349ca63`) and the four A0 books. It does not exist.
- `PREV_BUNDLE=/workspace/shadow_bundle_v4` (L73) is the September v4 export, which was never deployed. The in-service bundle is v3: booster `8d79186b` on mac, pinned in `dl_quant_live/config/book.json`, which equals pod `/workspace/shadow_bundle_v3/slow2026.txt`.
- Preflight also requires `$R/v4_gates/ROLL_PATHS.json`, a PASS receipt from `v4_gate_roll_paths.py` bound to this contract's sha (driver L117–141). Check P3 fails for rolled keys outside `$R`, and the template places CACHE, the panels, FUND_AUG and EMA_STATE_JSON under `/workspace/...`.

---

## 2. Data freshness on pod2, against the required end

**Which rule applies.** PREREG_october_decision_profile §2 sets UB = axis end − 24 h, and axis end = **2026-09-19T20:00Z** (10,326 anchors). The DL targets builder keeps an anchor E only if E+48 ≤ TT−1 (`pod_dlw_targets_raw_v2.py` L7: "锚行 E = ts%14400==0 且 E≥576 且 E+48≤TT−1", i.e. anchor rows need 48 later 5m rows). September confirms this: cache end 09-01T00:00Z gave axis end 08-31T20Z. So the cache must end at the **bar closing 2026-09-20T00:00Z**. Data through 09-20T20Z is not needed.

No builder has an axis-cap env, so a longer cache produces a longer axis. The prereg §6 then refuses a length other than 10,326. **The cache must be cut at exactly 2026-09-20T00:00Z.**

| Input | Last timestamp on pod2 | Reaches 09-20T00Z? |
|---|---|---|
| 5m cache holefix2 (canon) | 2026-09-01T00:00Z | No |
| 5m cache holefix2_x0910 (research) | 2026-09-11T00:00Z | No |
| 5m daily kline zips `wide_multisrc/klines5m_daily` | 2026-08-30 (08-31 `.404` as of 09-01) | No |
| r6 downloaded daily klines `uplift_2026-09-11/r6/dl/klines` | 2026-09-10 | No |
| funding monthly zips `wide_multisrc/funding` | 2026-07 (08 `.404`) | No |
| `fund_aug.json.gz` | 2026-09-01T02:00Z | No |
| premidx daily | 2026-08-30 | No |
| `raw_patch.npz` | 2026-08-24T13:00Z (952 bars) | No (must also cover new clipped bars) |
| `holefix2_cells.npz` | 2026-09-01T00:00Z | No |
| `wide_panel_4h_v3splice.npz` | 2026-08-31T00:00Z | No |
| `wide_panel_4h_v2ext.npz` | 2026-08-31T00:00Z | No |
| `wide_fea_v4.npy` / `_meta.npz` | 10,182 anchors, 2022-01-08→2026-08-31T20Z | No |
| `dlw_v4raw` / `dlw_hf3` targets | 10,212 anchors →2026-08-31T20Z | No |
| `f8_v4` fea89 / legs | →2026-08-31T20Z | No |
| `f8_ext` legs (LEGS_OLD) / `dlw_ext` | →2026-08-30T20Z | n/a (old rows are kept) |
| A0 F10 preds `f8_ext/preds/f10_V2MAIN_s{42,2027}.npy` | last finite row = 2026-08-30T20Z | **No, and nothing in the chain extends them** |
| A0 king `shadow_bundle_v3/slow_pred_pinned.npy` | 2026-08-30T20Z | No |
| `meta_newprod_v4.npz` (REF_META) | September axis | n/a |
| 1h klines `t7_klines_1h` | 2026-08-31T23:00Z | No |
| `tradability_v1.npz` | 2026-09-11T00:00Z | No |
| umask tradable W24H / UPIT_CRYPTO | 2026-08-31T00:00Z | No |
| member mask tradable ∧ live | 2026-09-01T00:00Z | No |
| `live_pins.json`, `slow_scorer_v4base.json` | 09-01 / 09-09 (content only) | n/a (per-month re-establish and approve) |

**Where fresh 5m data comes from.**
- Klines: `r6_fetch_klines.py` fetches `https://data.binance.vision/data/futures/um/daily/klines` at ≤4 req/s with an anchor-window guard. Its DAYS list is hard-coded to 08-31..09-10. The git alternative is `retrain_2026-09/pod_extend_vision.py`, which takes `EXT_DAYS` from env but writes into the shared `wide_multisrc` tree.
- Merge: `r6_merge_cache.py`, append-only.
- Funding: `r6_fetch_funding.py` or `fund_pull_pod.py` (`fapi.binance.com`, public, no key).
- 1h klines: `t7_s1_perp_klines_pull.py` (receipt `/workspace/fx_data_2026-09-13/PERP_KLINES_RECEIPT.json`).
- **All of these need outbound network access from pod2.** On 09-11 it worked: 8,778 zips OK, 341 × 404, 0 errors.
- **Timing constraint:** the 2026-09-19 daily archive, which holds the 23:55 bar, is only published after the day ends. I did not verify the exact publication time.
- The month-roll driver TRN-01 is **unfinished**. Only `v4_gate_roll_paths.py` was delivered (`47dc2916`, "未经 lead 验证", i.e. not yet verified by the lead). FIXPROGRAM L69 records that the git roll builders hard-code September paths.

---

## 3. Monthly gate sources (STEP1/STEP2 `_m`)

**They exist and match their approval objects.** Measured today:
- `v4_gate_step1_m.py` = `79950786…`
- `v4_gate_step2_m.py` = `d99a9109…`

Both are in `ELIGIBILITY_CONTRACT.json` (now `593b518b…`) under `gates.STEP1/STEP2.approved_source_sha256`. They were approved by user word on 2026-09-18 ("按最佳建议来", roughly "go with the best recommendation"). The same approval covered the TRN-16 global fea89 builder, `PREV_KING_FEA_UNCLAMPED=NONE`, the TRN-15 mechanism, and the MEMBER_LIVENESS gate (`9ee4d4c3`). **The gate-source approval is no longer open.** `docs/RESULT_live_expectation_correct_caliber_2026-09-19.md` L151 still lists it as awaiting a ruling, which is stale.

**How they have been tested.**
- Synthetic fixtures: sections [R]/[S]/[T]/[U] of `tests_pipeline_gates.py`. The latest claimed count is "pipeline_gates 492" (commit `f9f495507` message). I found no committed verdict-line log for that count.
- Real data, **September only** (pod2, 09-12/09-13): STEP1_m PASS=false, which is expected under AMENDMENT 3 (trend_288); STEP2_m PASS=true with `tail_quality` 6 tail anchors, ff 0.9756.
- **Never run on October data, on masked builds, or on v2-builder builds.**

**What the prereg requires before use.**
- §6.1 user approval: done.
- The independent researcher review of §1–§3: every contract entry says "review requested (post-hoc)", and I found no completed review receipt.
- The `NONE` condition, which the gate enforces through `PREV_CLAMP_BUILDER_SHA256`.
- The §3.4 known risk (reference-tail label completion) is unverified.

**Blockers still present [code-read], each independent of missing data.**
1. **The `_m` gates are not mask-aware** (0 occurrences of "mask" in either file). The October template requires `MEMBER_MASK` plus the v2 builders, and preflight refuses a post-September month without them (driver L199–201). Against the unmasked September references that PREREG §2 specifies (`/workspace/dlw_hf3`, `/workspace/f8_v4`, `/workspace/data/wide_fea_v4.npy`), removed members differ outside the hole neighbourhood, so `members_diff_rows_outside_neigh > 0` and the gates FAIL. The FP2 mask-aware variants (`fp2_gate_step1/2.py`) are contract-scoped to `V4_MONTH=2026-09, R=/workspace/fp2_2026-09`, "NOT inherited by 2026-10 increments".
2. **STEP2_m conflicts with the v2 king builder.** v2 starts the king axis at 2022-01-03 (E_row 576) instead of 01-08 (E_row 2016).
   - Against the v1 September reference, 30 early anchors are "only in candidate" and fall outside the neighbourhood. They are not tail-exempt (PREREG §3.4), so `anchors_only_v4_outside_neigh=30` and the gate FAILs.
   - Against a v2-built reference (the FP2 or FP3-live roots), the common axis starts at 576, so `n_first138 = (8640−576)/48 = 168 ≠ 138` (step2_m L69, L132) and the gate FAILs.
   - PREREG §4 says such a change "合法地红, 须重新预注册而不是改数" (is legitimately red and needs a new prereg, not a changed number).
3. **The `NONE` builder-identity check certifies the wrong builder.** It checks `pod_fea_ext_clamp.py` (v1, `b9f9c728`). That file is always in DEV_FILES, so the check passes trivially, while the October king features are built by `pod_fea_ext_clamp_v2.py` (`7b8b843d`).
4. **The checks are blind on the new data.** The 08-31 hole run's neighbourhood extends to row 499392 ≈ 2026-10-01, so every October-new anchor is "in neighbourhood" as well as tail-exempt. On new data the gates only check STEP1 part A and the 0.90 finite-cell floor.

**What is blocked on a user ruling versus merely not done.**
- Ruling needed: whether and how to re-register the gates for mask plus v2 builders (items 1–2), and which month is "previous" (§6 B4).
- Not done: a real-data run of the gates on an October build (impossible until data exists), and the §1–§3 researcher review receipt.

---

## 4. Controls: last results, and what has run end-to-end

| Control | Last run | Result | Receipt |
|---|---|---|---|
| Empty-root negative control `chain_v4_monthly_dryrun.sh`, October template | 2026-09-17 04:10Z (mac) | `DRYRUN_PASS driver_rc=3 stopped_at=FAIL_preflight_rc_3 training_launched=0` | `docs/fixprogram_2026-09-13/receipts/FP2_tests_20260917/dryrun_negative_control_october_template.log`. The inner receipt sits in this session's scratchpad `dr_t/`. Not re-run after the 09-18/19 driver and template changes; [P] claims a re-run inside each battery |
| Same, pod2 | 2026-09-12 | `DRYRUN_PASS … 33 missing` | `receipts/monthly_chain_2026-09-12/pod2_dryrun/dryrun_receipt.json` |
| Real-env dryrun `V4_DRYRUN=1` | 2026-09-18 07:30Z, **September FP2 env** | PREFLIGHT PASS 30/30/**3**, then `FAIL_dryrun_guard_cache_would_launch` rc 9 | `docs/fixprogram_2026-09-13/FP3_receipts/chain_negctl_2026-09-18/negctl.log`. RUNBOOK 修订 8 ② says it does not count for October. It predates the 4th approval (MEMBER_LIVENESS). **Never run with an October env** |
| September positive control of the driver (`V4_STAGES=preflight,gates`) | 2026-09-12 | preflight PASS. STEP1 FAIL (78 fields, 0 diffs), STEP2 PASS (31/0), driver rc 3 `FAIL_gate_require_step1` | DESIGN §6.2, `receipts/monthly_chain_2026-09-12/pod2_root/` |
| king + legs CPU control | 2026-09-12 | 6 of 8 bundle files bitwise equal; legs 10206/10212 old rows bitwise, 2023 king seat 0.5865 | DESIGN §6.5 |
| `_m` gate controls on September data | 09-12 / 09-13 | see §3 | `w7_gates/`, `round3_2026-09-13/`, `round4_2026-09-13/` |

**End-to-end on real data.**
- FP2-8 (09-17, September data, root `/workspace/fp2_2026-09`, FP2 contract and FP2 gate variants) ran every later stage **one stage at a time**, via `chain_fp2_run.sh` calling `chain_v4_monthly.sh V4_STAGES=<stage>`. The sequence: data → controls (1 FAIL, then PASS) → gates → king → legs → mwf (first try rc 137, a self-inflicted kill) → refit → np_export (1 FAIL, E-0917-B) → arms → a0rerun → judge → export (FAIL, then PASS on variant rev3) → member_rule → per_year → decision **NO_SWAP (G1 UNDECIDED)**.
- No single `V4_STAGES=all` run has ever completed. The FP2 root holds only `MONTHLY_STAGES_DONE.json` with DONE=false.
- **The current driver (`c224304c`, reordered to 17 stages, with the liveness gate and controls ports of 09-18/19) has never run on real data.** The pod2 copy is stale (`7e46a56a`, 09-17 15:57).
- FP3-live (09-18) re-ran data → mwf → refit → np_export with ad hoc `run_*.sh` scripts, not the driver.

---

## 5. Wall time, GPU hours, disk

These are measured times from pod2 logs: FP2-8 on 09-17, FP3-live on 09-18, and r6 on 09-11.

| Stage | Wall time | GPU? | Source |
|---|---|---|---|
| Network: 5m klines, 11 days × 829 names | ~38 min (14:22→15:00Z) | no | r6 `logs/fetch_klines.log`. The October roll needs 20 days, or 9 more on top of r6's download |
| Network: funding REST, 676 names | ~4 min | no | r6 `super.log` |
| Cache merge / coverage v2 / BW-1 | 3 min / 0.7 min / 1.7 min | no | r6 `chain.log` |
| Panel build / splice v2ext / splice v3splice | ~7 / 11 / 13.5 min | no | r6 `resume*.log` |
| preflight / cache stage | ~1 min each | no | FP2 logs |
| data stage (RAW 26, CLIP 16, fea82 2.6, fea89 8.3, king 20.7) | **73 min** (FP3-live rebuild was faster: targets 3.5, king 6.3) | no | `fp2_2026-09/chain_fp2_stage_data.log` |
| controls (`fp2_controls.py`, must run alone) | **83 min** (4,963 s) | no | `fp2_controls.log` |
| gates | ~8 min | no | FP2 |
| king export / legs | 7 min / 26 s | no | FP2 |
| mwf RAW, 20 folds, 4 shards sharing one GPU | **~41 min per seed → ~82 min** for s42 + s2027 | yes | FP2 s2027 10:46→11:26; FP3 12:23→13:45 |
| refit FIX7 | 437 s + 443 s ≈ **15 min** | yes | `chain_fp2_stage_refit.log` |
| np_export / arms / a0rerun / judge / export | <1 / 0.8 / 0.5 / 0.1 / 0.4 min | minor | FP2 |
| member_rule / per_year / decision | 3.5 min / 3 s / ≤30 s | no | FP2 |
| **Driver total** | **≈4.6 h** (≈3.3 h without controls) | **≈1.6–1.7 GPU-h** | RUNBOOK's "≈5.5 h" was the 09-09 four-chain RAW/CLIP × 2 seeds sequential run |
| **Month roll (data preparation)** | **≈2–2.5 h** (r6 took 2 h 11 min for 11 days including retries), plus the tradability/umask/mask chain (not timed) | no | — |

**Hardware.** GPU: RTX PRO 4500 Blackwell, 32 GB, idle. CPU: 64 cores. Container `memory.max` = 60,999,999,488 B (61 GB). The king builder peaks at 50–58 GB and must run alone (RUNBOOK 修订 9).

**Disk.**
- `du -sh /workspace` = **505 GB**. `df` shows the shared MooseFS (549 TB free), not the per-pod quota.
- **The quota is not observable read-only.** It was hit on 09-05 (at 263 GB) and again on 09-13. The t7 receipt recorded `free_GiB_end 12.25` on 09-13T14:25Z. I don't know how that was measured.
- Sizes: FP2 root 16 GB, FP3-live 4.4 GB, `/workspace/data` 27 GB. An October root plus a new cache and panels needs roughly 20 GB (my estimate).
- **Run a quota write probe before starting.** That is not a read-only action, so I did not do it.

---

## 6. Minimum ordered steps from today to an October judge/decision receipt

Legend:
- (a) can be done now without a user decision.
- (b) needs a user decision. Questions quoted from docs are marked "quoted"; the others are my phrasing of newly found conflicts.
- (c) blocked by missing data or time.

**Rulings and designs needed before any October build is worth doing**
- **B1 (b)** Permission to build the October env. Quoted from `HANDOFF_review_2026-09-19_fills_caliber_and_ic.md` §7 item 4: "十月月合同 env 构建放行 + `approved_controls_refs["2026-10"]` 逐 sha 批准" (release to build the October month-contract env, plus per-sha approval of `approved_controls_refs["2026-10"]`).
- **B2 (b, mine)** Fold coverage versus UB. `v4_months` admits only complete months, so the fold set stays 202501..202608. No step produces F10 predictions for 2026-09-01..09-18: A1's mwf does not, A0's `f8_ext` preds end 08-30T20Z, and A0 king v3 ends 08-30T20Z. The prereg's UB of 09-18T20Z therefore has model legs missing on its last ~108 anchors, and prereg §6 forbids falling back to a smaller UB. A design is needed: a partial-month fold, forward scoring of the in-service models, or an amendment.
- **B3 (b, mine)** The 2026-09-01T00:00Z anchor [code-read]. All 798 names × 288 rows of 08-31 are hole-filled. TRN-16 forbids replacing them, and the liveness rule treats hole-filled cells as not real, so the 24 h window of anchor 09-01T00Z has no live name. The member mask is then all-False, and the builders drop the anchor because members fall below `MIN_MEM` (`pod_dlw_targets_raw_v2.py` L154). The result would be an axis of 10,325 with W_ALPHA/KING_LIVE counts of 9,251/5,951 (computed locally), which prereg §6 refuses (it requires 10,326 and 9,252/5,952).
- **B4 (b, mine)** Which September build is the "previous month" for `PREV_MONTH_ENV/PREV_SHA_JSON/PREV_DLW_CLIP/PREV_F8/PREV_KING_FEA/CONTROLS_REF_*`. The candidates are Sept v4 (`review_scratch`, unmasked v1), FP2 (`fp2_2026-09`, tradable mask) and FP3-live (`fp3_live_2026-09`, tradable ∧ live, ad hoc and not a contract). Combined with §3 items 1–2, **no choice makes STEP2_m pass with the v2 king builder.** This needs re-registered month gates (mask-aware, v2 axis) plus approval.
- **B5 (b, mine)** Controls stage. `fp2_controls.py` checks K3 (L120: extra anchors must lie exactly in E_row [576, 2016)) and D1 (L129: targets bitwise equal to September). It **FAILs by construction** on an extended axis. It runs in `V4_STAGES=all` and dies with `controls_verdict_FAIL`. It needs a monthly controls device or a ruling that removes it from the October path.
- **B6 (b)** Decision profile. PREREG_october §「落地方式」 says to change only `PROFILE_MONTH`, `UB` and the counts. However, `fp2_decision.py` is still `PROFILE_MONTH="2026-09"` (L37–39) and is **hard-bound to `fp2_gate_step1.py`**: L156–165 set `expected_self_sha` to that file and call `bind_variant` with scope 2026-09 @ `/workspace/fp2_2026-09`. With `_m` gates it returns UNAVAILABLE. The cost requirement (§4/§8.4: a normal-population measured cost plus a three-cell sensitivity table) is implemented nowhere. Arms read a single `calib/costb_fee_steady.json`, which the export gate pins at `9349ca63`.
- **B7 (b)** Export baseline. TRN-15's "per-month approval" is `mechanism_approved: true` but **not implemented**. `v4e_gate_export_v2.py` (approved `d63f4ec3`) reads one `approved_baseline` (L101–106, E2b L183), which holds September's pins, base, umask `3badc4b6`, costb and A0 books. Contract `october_shas`: "NOT YET". The dyn-only variant `v4e_gate_export_fp2dyn.py` is scoped to September, so under the tradable umask the fix-seat K6 failure recorded for FP2-8 is expected again.
- **B8 (b)** Per-month approvals once the artifacts exist. Quoted from RUNBOOK 修订 9: "十月的掩码/参照件/pins/基线实物尚不存在…每一样都要单独一次用户字" (the October masks, reference builds, pins and baseline don't exist yet; each needs its own user word). Covered: `approved_controls_refs["2026-10"]` (three refs plus UMASK_NPZ), pins, base, and A0 books.
- **B9 (b, mine)** `PREV_BUNDLE`/A0 identity. The template points at never-deployed `shadow_bundle_v4`, while in service is `shadow_bundle_v3` (`8d79186b`). This determines what "A0 = in service" means for October.

**Engineering that can proceed now**
- **E1 (a)** Sync the git device dir to the pod `D` and verify by sha. RUNBOOK §0★ step 0 / 修订 3 say to copy the whole directory; verify with `python3 v4_gate_common.py sha <file>` and `SHA256SUMS*` from `make_sha_manifest.py`. The pod copy is stale (contract `8643c56f` vs git `593b518b`; driver `7e46a56a` vs `c224304c`; liveness gate `ae440347` superseded). `/workspace/pod_env_bootstrap.sh` (RUNBOOK step 0) is absent on the pod, although the venv already works: py 3.11.10, numpy 2.4.6, torch 2.11+cu128 with CUDA OK, lightgbm 4.7.
- **E2 (a)** Fix `mk_prev_sha_record.py` L18 (`st_flags`) so it runs on Linux, then place the chosen September contract on the pod.
- **E3 (a)** Finish TRN-01 as month-generic roll builders. Required properties:
  - Append-only, with the cache cut at exactly 2026-09-20T00:00Z.
  - Hole cells, raw patch plus manifest (`v4_rawpatch_manifest.py`).
  - Panels using ledger or declared intervals rather than fetch-time `iv` (TRN-07 / x0910 defect).
  - EMA state and `FUND_AUG`; tradability → umask/FEMAT → member mask; `HC` tree with an extended UPIT mask; pins; base json.
  - Nothing may write to September paths (see `v4_gate_roll_paths.py` docstring).
- **E4 (c)** Fetch data after the 2026-09-19 daily archives are published (09-20 UTC or later): 5m klines, 1h klines and funding REST (network, public endpoints). Then build the October artifacts (≈2–2.5 h).
- **E5 (a, after B1–B9 and E4)** Fill `v4_month_2026-10.env`, including a corrected `MONTHS_ALL`. Pre-check with `python3 v4_months.py check <DLW_RAW>/data/dlw_targets.npz <MONTHS_ALL>`. Produce `$R/v4_gates/ROLL_PATHS.json` with `v4_gate_roll_paths.py` (env `V4_MONTH_ENV ROLL_PREV_MONTH_ENV ROLL_OUT ROLL_PREV_SHA_JSON`; `ROLL_ALLOW_OUTSIDE_ROOT` for any key left outside `$R`) and `PREV_SHA_JSON` (`python3 mk_prev_sha_record.py <上月合同> <out.json>`, RUNBOOK 修订 7-1). Produce `SIGNAL_RECEIPT` with `gate_signal_parity_v2.py`.
- **E6 (a)** Empty-root negative control: `bash $D/chain_v4_monthly_dryrun.sh $D/v4_month_2026-10.env`. It must print `DRYRUN_PASS` (RUNBOOK 修订 3).
- **E7 (after B8 approvals)** This month's negative control: `V4_DRYRUN=1 bash $D/chain_v4_monthly.sh $D/v4_month_2026-10.env`. It must print `PREFLIGHT PASS … approvals=4/4` and then `FAIL_dryrun_guard_cache_would_launch` rc 9 (RUNBOOK 修订 8 table row 4).
- **E8 (a)** Check memory: `cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.events` (修订 9). Run a disk quota probe. Then run `bash $D/chain_v4_monthly.sh $D/v4_month_2026-10.env` (修订 3). DESIGN §7 (ii) advises advancing stage by stage with `V4_STAGES=` subsets, reading each receipt. Success means `$R/v4_gates/DECISION_FP2.json` and `MONTHLY_DONE.json` exist. Without the decision receipt the driver refuses `MONTHLY_DONE` (`FAIL_monthly_done_without_decision_receipt`).
- **E9 (b)** Any swap happens only after a user word on the specific bundle sha. The `booster_sha_pin` must change in the same quiet window (修订 10).

---

## 7. Anything suspicious

1. **Six stale wait loops on pod2 since 2026-09-11 (7+ days), sleeping every 15–30 s. I did not touch them.**
   - PIDs 220770, 223786 and 227856 run `until ! pgrep -f "python drive3.py"`. That pattern matches the loops' own command lines, so they can never exit.
   - PIDs 225412, 228443 and 230774 run `until ssh pod2 "grep -q …"`, i.e. they ssh from pod2 to itself.
   - The known paused codex collectors 333197 and 339489 (state `Tl`) are also present.
2. **A stale `MONTHLY_DONE.json` with `"DONE": true, "stages": "preflight"`** sits at `/workspace/w3_monthly_chain_2026-09-12/root_run1/v4_gates/`, left by the 09-12 pre-fix driver. A reader that globs for MONTHLY_DONE would be misled.
3. **Template values that point at September or at wrong objects:**
   - `MONTHS_ALL` includes 202609 (inadmissible).
   - `PREV_MONTH_ENV` → `/workspace/review_scratch/v4_month_2026-09.env` (missing).
   - `PREV_BUNDLE` = v4 (not in service).
   - `REF_META`, `PREV_META`, `LEGS_OLD`, `DLW_EXT` and `F8_EXT` are September or yearly objects.
   - The rolled keys sit outside `$R`, so ROLL_PATHS check P3 fails.
   - `ROLL_ALLOW_OUTSIDE_ROOT` is read from the **ambient** environment by the driver (L96). It is not a contract key, which is the same class as R15-C1.
4. **Gate and decision sources frozen to September objects:**
   - `fp2_decision.py`: PROFILE_MONTH, FORMAL UB 2026-08-30T20Z, and the FP2-variant binding.
   - `fp2_controls.py`: K3/D1 compare against "September".
   - `v4e_gate_export_v2.py`: a single September `approved_baseline`.
   - `pod_export_bundle_v4.py`: hard-coded `2026-08-01` (L172), `parity_signals_aug.json` (L183), and king booster trained only on `YRA < 2026` (L63).
   - F10 refit label cutoff is 2025-12-16T20Z (refit logs).
   - So the "monthly retrain" does not move either deployable model's gradient cutoff.
5. **Month-roll builders in git hard-code September outputs** and would overwrite September's receipted files: `pod_panel_splice.py`, `fund_pull_pod.py`, `pod_merge_cache_ext.py`, `make_raw_patch.py` and `v4_hole_cells.py`. The r6 versions hard-code a 2026-09-10 frontier, and `r6_panel_splice.py` has the fetch-time interval defect.
6. **The PREREG_v4_gates_monthly invalidation condition has literally fired.** It names `v4_gate_common.py f8f4fc0e…`, and that file has since changed to `24e813f1`, then `a1d41044`, then `cc1492d3` (today). The docs I checked contain no amendment that explicitly addresses this.
7. **The STEP2_m `NONE` identity check is bound to the v1 clamp builder** while October builds with v2 (§3 item 3).
8. **The hole neighbourhood covers the whole new month** (08-30 20:05Z → about 10-01), so reference comparisons exempt all October-new anchors (§3 item 4).
9. **Stale "needs ruling" lines.** `RESULT_live_expectation_correct_caliber_2026-09-19.md` L151 still lists "STEP1/STEP2 月度门源码与合同批准" (monthly gate sources and contract approval) and "FP2-8 处置" (FP2-8 disposition) as needing rulings. The contract (09-18) and STATE L27 (09-18 05:0xZ, "AMENDMENT 11 维持 NO_SWAP…十月链按修复后口径跑再判", i.e. keep NO_SWAP and re-judge on the October chain) already record those decisions.
10. **Missing referenced document.** PREREG_october §6 refers to "件二" (item two), and no such document was found.
11. **dlw_v4raw targets mtime.** `/workspace/dlw_v4raw/data/dlw_targets.npz` was rewritten on 09-12 15:17 by a `chain_v4_data` run (`review_scratch/chain_v4_data.log`). Its sha is still the approved `d1976cf6`, so no harm, but the file's mtime no longer reflects its 09-09 origin.
