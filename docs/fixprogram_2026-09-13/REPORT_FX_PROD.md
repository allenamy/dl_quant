> **创建:** 2026-09-13 15:3xZ | **Session:** FX-PROD (fix worker, team-lead dispatch; session b9646a9e) | **状态:** HANDOFF 16:27Z — P1/P6/P2/P6-M/P9 code+tests+parity committed; P5 device committed but NOT run; every section awaits independent review; nothing deployed | **作废条件:** a cited fx_prod commit is rewritten, or a cited receipt's sha changes without a new section here

# REPORT_FX_PROD — producer train/serve and funding-label fixes (FIXPROGRAM P1 P2 P5 P6 + P6-M, P9)

- Working copy (git): `/Users/haosiyu/cc_tmp/fx_prod`. b8917484 = byte-identical copy of the live producer stack (sha256 of every file in the commit message; blob-equal to the live files). Branch `fix/train-serve-parity-2026-09-13`. Commit chain: `FX_PROD/receipts/fx_prod_commit_chain.txt`.
- Fact table: `docs/fixprogram_2026-09-13/FX_PROD/FACT_TABLE_PROD.md`. Receipts: `FX_PROD/receipts/` (logs, P9, P6-M; `SHA256SUMS_round1.txt` written with the T6 guard). Diffs: `docs/receipts/fx_prod_P1.diff`, `fx_prod_P6.diff`, `fx_prod_P2.diff`, `fx_prod_P6M.diff`, `fx_prod_P9_evidence.diff`, stacked `fx_prod_stacked_b891748_69e8e22.diff` (sha256 861d36db…).
- Battery: `tests_fx_prod.py` (RED = primary evidence, must fail on b8917484 for a stated numeric reason; KEEP = must pass before and after; NEW = added mechanism). Red runs use a `git archive` export of b8917484 (`--code work/code_live_b8917484`). Every fix keeps all old lines (0 removed lines in every production diff) and the old battery `tests_target_live_output.py` stays ALL PASS (65).
- Real shapes only: frozen producer snapshots (SHA256SUMS verified), the in-service bundle and booster read-only, pod2 `ledger_full.npz` (bea6f575…), real anchors and ledger rows. Nothing written under `~/wide_shadow` or `~/dl_quant_live`; no venue API; bytecode writes disabled.
- Process deviation (disclosed): the fact table document was committed after the P1/P6/P2 code commits in the clone; the facts themselves were sent to the lead before each fix (13:3xZ, 14:30Z) and are repeated in each commit message.

---

## P1 — king column 80: serve the training definition (v0)
**Problem.** Booster 8d79186b was trained with column 80 = panel `f_fund_ema` (v0: raw rate, wall-clock HL 3d; `pod_panel_ext.py` L124–133, stored f16 by `pod_fea_ext.py`). The producer serves `fe_v` = the v1 state (rate×8/iv; `shadow_loop_v3.py` L336–349, L418). FACT 1.1–1.12.
**Red (b8917484, `RED_P1_on_b8917484.log`, rc 1).** Snapshot-forward replay at 09-12 12Z: KEEP P1-R0 king weights == live weights file bitwise; RED P1-R1 served X[:,76] ≠ float32(training v0) on 311/400 members, median served/v0 = 2.0 (4h), 5.89 (1h), 1.0 (8h); KEEP P1-N1 fund leg == live prev_rec.
**Fix (633d44b, +40/−0).** `FUND_COL80_V0 = True`; a v0 state carried beside v1 on the same rows with the same `a` (raw rate), cold-started only together with v1; served under the same 12h freshness and only when `v0.last_ts == v1.last_ts` (else 0, counted); `REFUSE_TO_START` when the flag is on and the state has no v0, or v0 is inconsistent with v1; bundle bootstrap reads `fund_ema_v0_state.json` only if listed in MANIFEST; `ema_v0` saved in the same atomic aux.json write; log event `fund_col80`. Fund leg / rank base / carry / FTRIM untouched.
**Tests (`GREEN_P1P6_at_d7df9a5.log`).** P1 9/9: R1 0/400 mismatching cells; R0 flag OFF == live bitwise; N2 ON vs OFF only column 76 differs (pred equal on the 89 rows where it is equal); N3 v0 recursion == training oracle for 525 names (bitwise); N4 missing v0 entry served 0 and not cold-started; N5 refusal paths; N6 save round-trip. Old battery ALL PASS (65).
**Migration (38223d8).** `migrations/p1_build_ema_v0.py` adds `ema_v0` to a copy of the state; gates G1 `ema_v0_problems == []`, G2 an independent v1 rebuild over the same rows with the stored labels reproduces the state's v1 (≤1e-12), G3 state rows ⊆ union. Dry run on the frozen live state 09-13 12Z: PASS, 525 names, 0 rate conflicts over 4,232,313 input rows, G2 0 bad (`receipts/p1m/`). Run again on the swap-time copy.
**Parity proofs:** see §Parity (all PASS).
**Unproven.** Book value (not claimed). King training f16 vs serving f32 on all 78 columns (P10, aud-prod).

## P6 — bundle bootstrap: seed labels and EMA alignment
**Problem.** A state reset loads the seed with its stored interval labels and the exported EMA with no consistency check (L198–205). The 08-16 seed carries 545 rows labelled by the fund_aug current-interval dict with an EMA exported on the same labels; the in-service v3 bundle's EMA sits at 08-31 00Z for 448/450 names while its seed runs to 09-01 00Z, and it labels ONG 08-25 08Z 2.0 against the exchange-evidenced 4. FACT 6.1–6.8.
**Design correction (approved 13:4xZ).** The first specification ("re-derive from gaps") would corrupt the zip-declared switch rows (GWEI 07-22 12Z zip iv 4 rate 5.000e-05 after a 1h gap; ESPORTS 07-29 20Z, T 07-25 04Z). Labels are re-derived only by rules that equal the zip on every scored row of full history (FACT 9.2).
**Red (`RED_P6_on_b8917484_v2.log`, rc 1).** R1 08-16 bundle loads silently; R2 ONG-corrected v3 bundle leaves 448 names' EMA at 08-31 00Z (worst |dAcc| 6.6e-3 vs the recursion over the missing seed rows); R3 in-service v3 loads silently; K1 switch rows keep 4.0 (OK).
**Fix (d7df9a5, +105/−0).** `declared_interval_exact` (steady / cap 4h|8h→1h at |rate| 0.02 / last 1h before a 2–3h gap / interest signature); `seed_rederive`: repairs exact contradictions and names them, keeps unresolved disagreements and names them, refuses when the exact linear impact of repairs on the bundle EMA exceeds 1e-9, requires EMA (v1 and v0) on a seed row and catches them up over later seed rows, refuses name-set mismatches; bootstrap logs `seed_iv_rederived`. Also the loader-side guard for aud-train (d) `AUG_IV.get` (builder call sites passed to fx-train).
**Tests.** P6 8/8: R1 refused naming ACE/BANK/DEXE/ERA/PROM; R2 all 450 EMAs at the seed end, bitwise equal to the recursion; R3 refused naming ONG (impact 6.0e-7); K1; N1 log; N2 a real 4h row relabelled 1.0 with impact 4.3e-10 loads and is repaired; N3 catch-up only from a seed row; N4 v0 caught up == training oracle (450 names).
**Consequence for operations.** A state reset from the in-service v3 bundle now refuses to start until the bundle is re-exported with consistent labels and a v0 state (R1 / fx-train).

## P2 — V2MAIN funding panel
**Problem.** `combo_stage.py` L134–146 (identical in `sidecar_blend.py`) fill the panel's `f_fund_ema` with v1 while F10 mu/sd are on v0; no 12h freshness on either funding column; combo and sidecar share `fea171/mini` with a cache check on the anchor only. FACT 2.1–2.7.
**Red (`RED_P2_on_b8917484.log`, rc 1).** R0 live-identical device reproduces live target_live and target_combo (L∞ 0.0, OK); R1 panel ≠ v0 on 311/400 members (median 2.0); R2 a real member made stale keeps −1.30e-05 / 5.0e-05; R3 v1-built cache reused; K1 FTRIM unchanged (OK).
**Fix (15921c0, combo +38, sidecar +37, −0).** `V2MAIN_FUND_COL80_V0`: v0 when consistent with v1, else 0 counted; no `ema_v0` in the state ⇒ v1 fallback recorded as `col80 = v1_fallback` (no abort, no book-level response). `V2MAIN_FUND_FRESH_12H`: both columns 0 when stale. `mini/data/fund_caliber.json` tag; cached mini reused only on an exact tag match. `fund_caliber` recorded in target_combo, target_blend and combo_live_status.
**Tests (`GREEN_P2_try1.log`).** P2 9/9 incl. N3: v1-fallback vs v0 runs differ only in F82 column 80 (311/400 rows), F82 other columns and F89 bitwise equal; N4 sidecar writes the same panel and tag.

## P6-M / P9-M — exact correction of mislabelled settlements in the live state (offline)
**Fund-leg effect of D17 correction at 09-13 12Z (`receipts/p6m/P6M_fundz_impact_09-13T12Z.log`):** fund z Spearman 0.9999927, 12 of 400 members change rank (PROM −0.0192, ERA −0.0038, ten names by one rank step 0.0019), 2 decile changes. P9 exact rows: no rank change.
**Tool (69e8e22)** `migrations/fund_label_ema_correction.py`; tests P6M 4/4 (`GREEN_P6M_worktree.log`). Control NONE: an independent full-history rebuild with the stored labels reproduces the frozen live v1 EMA bitwise for 525/525 names. D17 class: 533 rows / 5 names, dacc PROM −4.096e-06 (5.12% of acc), ERA −3.00e-07, BANK −1.72e-07, DEXE −5.14e-07, ACE −7.57e-07; corrected == rebuild (1.3e-18). P9 exact producer-appended class: 63 rows (ONG 08-25 08Z; 61 cold-start first rows 07-26 08Z; GRVT 07-31 12Z), dacc ≤ 3.7e-9; corrected == rebuild (6.9e-18). Receipts `FX_PROD/receipts/p6m/`. Fund-leg effect of applying it is to be measured as a separate replay arm, not mixed into the P1/P2 one-place proof.

## P9 — live append-path interval labels (rulings 15:1xZ: August zips approved; direction (a) hybrid + (c) monthly zip reconciliation; (b) recorder candidate only)
**Problem.** Step 4 labels each appended settlement by its backward gap (L341–342; a ledger's first row 8.0). The declared interval is the schedule in force at the settlement (FACT 9.1), so schedule transitions and cold-start first rows are mislabelled, inflating or deflating rn = rate×8/iv in the v1 EMA (fund leg) and, while the row is the latest, FTRIM rn8.
**Evidence.**
- Table (`receipts/p9/TABLE_LOCATION.txt`): August monthly zips pulled on pod2 by the committed device 86a52e3 (≤5 req/s, in-memory sha, 680 files, 152 × 404, 0 checksum mismatches; manifest 02647116…) and folded in (d49f1ef): 103,649 August rows, 0 rate and 0 label conflicts with the existing sources; exact rules stay 100% with August added (steady 2,625,081/2,625,083; interest signature 694/694 + 423/423 edge; cap 174/174 + 27/27; last 1h before 2–3h gap 53/53 + 44/44). Table sha 366763a4….
- August verdict on the producer's own rows (≥ 08-16): exactly 2 mismatches — ONG 08-25 08Z (stored 2.0, zip 4) and COTI 08-31 20Z (stored 1.0, zip 4). The other 535 August mismatches are the D17 seed rows (P6-M). T 09-06 00Z, SKR 09-07 20Z unresolved until the September zip; ZKC 09-02 20Z / SOPH 09-11 12Z likely 4.
- Rule evaluation on 2.52M zip rows 2020–2026-07 (pod2, `receipts/p9/P9_rule_eval_v4.json` 7c907c09…; devices committed before each run: v2 26b8dd8, v3 76b4aed, v4 85e02ce):

| rule | final mislabels | at-anchor mislabels | FTRIM flips | anchor×name cells with EMA error >1% |
|---|---|---|---|---|
| (i) backward gap (today) | 1047 | 1032 | 58 | 73,484 |
| (iii) fundingInfo for the latest row | 491 | 476 | 16 | 47,656 |
| executor `derive_interval_h` (3-point median, retro) | 283 | 476 | 16 | 10,814 |
| H (hybrid (a)) | 350 | 1032 | 58 | 16,310 |
| **H2 (hybrid (a) + adjacent-schedule rule) — implemented** | **100** | 1032 | 58 | **8,205** |
| Hfi (hybrid + fundingInfo append label) — candidate | 193 | 372 | 16 | 10,228 |

  v2 showed an append-time interest signature over all intervals is not exact (543/1,473,912 wrong), so it is not used. Hfi needs a new live fundingInfo read; registered with (b) as a candidate pending a positive control.
**Red (`logs/RED_P9_on_85e02ce.log`, rc 1; producer funding step replayed on the real append anchors and the next anchor with the spliced real cache).** ONG 08-25 08Z label 2.0; ZKC 09-02 20Z and SOPH 09-11 12Z label 2.0 = snap(3h), not an adjacent schedule; cold start ILVUSDT at 09-04 00Z first row 8.0 (zip 4); neighbours and the ONG 08-26 20Z cap row KEEP OK; COTI/T/SKR not logged (NEW absent).
**Fix (b90f1b8, +45/−0).** `FUND_IV_RERESOLVE = True`; `resolve_appended_intervals`: rows that just gained a forward neighbour are judged by `declared_interval_exact`; resolved and different ⇒ relabel and `acc += a_k·rate·(8/new−8/old)·0.5^((t_last−t_k)/3d)` (exact); unresolved with a label that is not an adjacent schedule ⇒ forward schedule (tagged `likely_forward_schedule`); other unresolved transitions kept and logged with candidates; cold-start first row by steady forward gap with a_0 = 1. The latest row keeps its gap label at the anchor, so at-anchor behaviour and FTRIM equal today by construction. Log event `fund_iv_resolved`.
**Tests (`logs/GREEN_P9P1P6_at_b90f1b8.log`).** P9 14/14 (ONG, ZKC, SOPH → 4.0 and ILV first row → 4.0, each with v1 EMA equal to a rebuild using the ledger labels to 1e-15; COTI/T/SKR logged unresolved [1, 4]; neighbours and cap row unchanged), P1 9/9, P6 8/8 (31 cells); old battery ALL PASS (65).
**(c) Monthly reconciliation — built and run on August (tool 61a55bc + dfd3b0b; receipt `receipts/p6m/RECEIPT_fund_label_ema_correction_P9_zips2026-08.json`, tool 1cbeca90…, output 2f18f8f5…; log `receipts/logs/p6m_P9_zips2026-08.log`).** `--zip-dir` adds each pulled month's `funding_interval_hours` as an exact label (per-file sha checked against the pull manifest). calc_time is keyed to the nearest settlement hour: 16 August rows carry calc_time 1 s past the hour (AAPL, AMAT, BX, EBAY, GLW, HYUNDAI, IBM, KLAC, LLY, MSFT, NVO, SKHYNIX, STRC ×2, V, WMT — none in the 525-name state; the first run with floor keys, 61a55bc, gave the same corrections); rows > 60 s off are listed and unused (0).
  - Red → green on the frozen live state 09-13 12Z, class P9: without the zips (69e8e22, receipt …_P9.json) 63 rows, COTI 08-31 20Z not corrected; with the August zips 65 rows — **COTI 08-31 20Z 1→4 (dacc +2.093e-6, 0.42% of |acc|)** and **DOS 08-11 16Z 8→4 (dacc −7.260e-7, 0.70%)**: DOS's first settlement (first row of its August zip; absent from the 08-16 seed and from the pre-M1 ledger), cold-started by the producer at M1 (09-04) with the first-row default 8 — the same family as the 61 cold-start rows of 07-26 08Z and ILV (P9 red test); without a July zip label the tool had no exact source for a row with no predecessor. Positive control unchanged: independent rebuild vs corrected acc max 6.9e-18 over 525 names.
  - Class D17 with the zips: 534 rows (was 533); every one of the 533 steady-rule labels equals the zip label, and ERA 08-06 16Z (4→1, dacc −1.3e-9) is added by the zip.
  - The swap-time migration uses `--classes D17,P9 --zip-dir <all pulled months>` (599 rows on the frozen state).
**Unproven.** At-anchor labels and FTRIM for transition rows (58 flips over 6.6 years under today's and H2's append label); Hfi and the pre-settlement recorder are not implemented.

## Parity — P1/P2 on the Phase-1 device (driver c2cdfa7 + fix d620f6e; code export 15921c0; judge `receipts/replay/FX_PARITY_JUDGE.json`)
Chain: 41 anchors 09-05 16Z → 09-12 08Z, start state inverted from the frozen T4 snapshot as Phase 1; ema_v0 seeded from full history in both arms. Snapshot: 09-12 12Z / 16Z / 20Z from the producer's close-of-anchor snapshots. Arms: OFF = FUND_COL80_V0, V2MAIN_FUND_COL80_V0, V2MAIN_FUND_FRESH_12H flipped False by once-only replacements; ON = as committed. Receipts `receipts/replay/` (rec .npy files not committed; sha in `REC_NPY_SHA256_not_committed.txt`).
- **(a) OFF reproduces production — PASS.** Chain 41/41: king X, pred and weights npz bitwise equal to the production-code device run of T4 (recs 942d20a9…, receipt 7c8e2e8f…, device 4d3bc157…); king L∞ vs live ≤ 9.31e-10 (Phase-1 envelope), step-6 leg-return entries equal, combo target_live L∞ equal to the production run at every anchor (max 1.1254e-4 = the known historical combo residual). Snapshot 3/3: king L∞ 0.0 with content sha equal, combo target_live 0.0, target_combo 0.0.
- **(b) one place — PASS.** Chain 41/41 and snapshot 3/3: members equal; king X columns ≠ 76 bitwise; pred equal on rows whose column 76 is equal; F82 columns ≠ 80 bitwise (column 81 included); F89 bitwise; pair axis equal. Column 76 / F82 column 80 differ on 12,787 of 16,400 chain rows.
- **(c) deltas ON − OFF.** Chain: king score Spearman median 0.9950 (min 0.9864); combo target_live L∞ median 3.5e-4 (max 4.8e-4), normalised L1 median 0.0110 (max 0.0155), correlation median 0.99986 (min 0.99976), gross ratio 1.0007; V2MAIN f10 Spearman median 0.9992; king target normalised L1 median 0.0116; masked king seat at 09-12 08Z 0.367556 vs 0.367264. Snapshot (one step from live state): combo L1 ≈ 0.002, L∞ ≈ 1.5e-4, correlation 0.99998. No book value is claimed.
- **V0P — PASS, no exceptions.** Served v0 (ON king column 76 on fresh members) vs the training panel `f_fund_ema` (x0910, fa284e5b…) on 27 anchors / 10,800 cells: median relative difference 0.0, 100% ≤ 1e-3, 99.94% ≤ 1e-6, max 9.95e-6. T4's exceptions (DEXE/GWEI/EPIC) came from its short-history v0 feed and vanish with the full-history bootstrap.
- Producer window: runs ended 15:43Z (chain) and 15:51Z (snapshot); STOP/CONT guards armed and exited unused (`receipts/replay/guard_*.log`). First snapshot attempt failed on two driver bugs (relative symlink target; sums self-entry), fixed in d620f6e and rerun; attempt logs kept.

## Lead ruling recorded (FIXPROGRAM §6, 09-13 ~16:2xZ): column-80 caliber
Live fix = P1 + P2. King and V2MAIN serve column 80 with the training definition v0 under the already-deployed boosters; this is a defect fix and needs no retrain. For future retrains, keeping v0 or switching to interval-normalised v1 is a recipe choice, not a defect fix. FX-MODEL will pre-register paired v0-consistent and v1-consistent arms; until that verdict, October exports stay v0-consistent.

## P5 — seat king rows (device committed, NOT run)
- Decision (consistency): rescore only the live-appended king rows, 08-31 00Z → state's last anchor (81 rows on 09-13 12Z). They were scored with column 80 = v1. Keep the booster that scored each anchor, read from the log `signal.booster_sha`: 29ffaf58 through 09-01 04Z, 8d79186b from 09-01 08Z. Only the caliber changes. The 869 seeded rows (v3 exporter, v0) and the fund and rev24 rows stay untouched. Also replace `aux.prev_rec.legz.king`, the vector that books the first post-swap step-6 row.
- Device `migrations/p5_rescore_seat_king.py` (80cd6aa, 5b3a056). Its SERVED arm must reproduce every recorded king row and prev_rec king vector bitwise; if not, rc 2 and no output. The earlier draft hard-coded the booster switch at 08-31 20Z; that was wrong against the log and is fixed in 80cd6aa.
- Swap tooling: `migrations/swap_state_compose_check.py` (bba6b8f), `migrations/swap_load_test.py` (8de133c), dry-run driver `migrations/swap_dryrun_frozen_20260913.sh` (f289fc0). Swap plan DRAFT: `FX_PROD/SWAP_PLAN_FX_PROD.md`.
- **Not run.** The dry run on the frozen 09-13 12Z state was scheduled for 16:51Z. It was cancelled before its first step at the lead's handoff order (16:27Z). No P5 number exists. Next command: `/bin/bash migrations/swap_dryrun_frozen_20260913.sh` in `/Users/haosiyu/cc_tmp/fx_prod`, at ≥ HH+1:05 after an anchor and outside anchor windows (the driver refuses otherwise). Output goes to `work/swapdry/run_dry.log`; it needs roughly 30 min on the Mac, not measured.

## Queue / state at handoff (16:27Z)
- PROD-27 (silent combo skip; AUDIT_PROD 57f7e2be): received, not started. No fact table, no code.
- pod2 quota exhaustion at 15:51Z: the August zip pull had already finished. `receipts/p9/pull_2026-08.log` ends with its SUMMARY: 832/832 requests, 680 × 200, 152 × 404, checksum_mismatch 0, manifest 02647116…. At 16:04–16:11Z on the Mac, the correction tool re-hashed all 680 files against the manifest sha and the assert passed. No file needs a re-fetch; nothing was resumed.
- P11 (king train members 829 vs production 450): not visible in this harness. The FX replays score the production 450-name set only, so there is no evidence here.
- FX-DATA answer, exact vs likely rows: `receipts/p9/EXACT_VS_LIKELY.md`.
- Stack diff: `docs/receipts/fx_prod_stack.diff` = `git diff b891748..afd94a2` (0 removed lines), sha256 3294f16841678eb6a124338f4cb59f9d2f851dcf097cb29c76198c2521b6e964. afd94a2 adds a refusal to the dry-run driver inside anchor windows and before HH+1:05 (the lead's 17:05Z rule), plus a before/after listing of the read-only live bundle dirs. Commit chain: `FX_PROD/receipts/fx_prod_commit_chain.txt`.

## Unproven boundaries (at handoff)
- No book value is claimed for P1/P2; only (c) deltas are reported.
- P5 has not run (see above). The swap plan is a draft, not dry-run, and not executed.
- At-anchor labels and FTRIM on transition rows are unchanged under H2 (58 flips over 6.6 years). Hfi and the pre-settlement recorder are not implemented.
- T 09-06 00Z and SKR 09-07 20Z stay unresolved until the September zip. COTI and DOS are corrected only by the monthly reconciliation migration, not by the live code.
- A bundle reset with the new code refuses until the bundle is re-exported with a v0 state and corrected seed labels.
- King f16 train vs f32 serve (P10) was closed by aud-prod, not by this item.


---
## PROD-27 事实表 + 红测试(克隆 d4d211a; 研究仓 7a4e2848 / 0d5132f8; lead 逐字转录 2026-09-16 03:2xZ)

**更正一个常数(改数字, 先说)**: 执行器**不是** N+23 读。`config/book.json` `external_book.anchor_offset_min = 24`, `poll_grace_min = 5` ⇒ **N+24:00 首读, 每约 15 s 重试至 N+29:00**; 其 `_timing` 注记录 23→24 的变更发生在 **2026-08-27 05:2xZ**, 原因正是 combo 写入只剩 34 s。AUDIT_PROD PROD-27 写 N+24 是对的; **CLAUDE.md 仍写 N+23, 自 08-27 起过时**(K4; lead 已于 01cbbc5a 更正)。工作者首轮普查曾用 1380, 报数前已改为 1440。

**AUDIT_PROD 的「最小余量 9 s」是响的那道门, 不是静默的那道。** 三道门在三个时刻:
| 门 | 判据 | 位置 | 实测余量 |
|---|---|---|---|
| **G1** 守护跳过 | `NOW-A > 1355` | `combo_live_daemon.sh` L27 | **最小 49.1 s**, 中位 108.8(124 个非重启锚)—— **静默的那道** |
| **G2** stage bail | `A+1360`(在 171 特征管线**之后**评估) | `combo_stage.py` L321-323 | **最小 9 s** ⇒ 复现审计的数字 ⇒ **审计测的是 G2** |
| **G3** 执行器首读 | N+24:00 | `config/book.json` | 最小 88.3 s |
⇒「约 10 s 的变慢会把该锚切成 king 形态」这句**对**, 但机制是**会页报**的那条路径; 静默那条由生产者落地时刻决定, 历史上响过一次。另: 守护的 1355 判据在 aux/rolling 落定循环(L32-36, 可烧约 150 s)**之前**评估 ⇒ 1354 s 过门的运行可能在约 1500 s 才启动 `combo_stage`, 于是走「过硬截止」而非跳过。

**新发现 1(登记 PROD-31, P1)· 2026-08-29 20:00Z 根本没有生产者文件**: 生产者 16:21Z 打印 `next 2026-08-29T20:16:00Z in 14061s` 后无输出, 直到 23:28:01Z 重启; 20Z 那次运行从未完成。守护的守卫是 `[ -f "$TL" ]` ⇒ **循环体从不执行: 无页报、无日志行、`combo_live_last_anchor` 都不推进**。执行器 N+24:00→N+29:00 **轮询 21 次全 `{ok:false, reason:"missing"}`**, **整锚 HOLD**(「held existing positions; no orders」, `anchors_row: false`)。FX-EXEC2 的账本扫描(缺槽 08-25 16Z / 08-29 20Z / 09-02 00Z / 09-09 12Z)与 AUDIT_PROD L276 独立佐证。**比本项命名的「静默跳过」更严重: 书冻结了一整锚而两侧都不出声。**
08-30 00Z 是同一次事故的尾巴: Mac 于 08-29 23:28:01Z 重启(`loop.out.pre_reboot_20260830`; `combo_live_daemon.log` 同秒被截为 0), 重启后的生产者在 **N+24:27.8** 写出(过 G1 112.8 s), 守护静默跳过, 执行器第 3 次尝试在文件 3.3 s 龄时取到 king 文件并交易。

**新发现 2(登记 PROD-32, P1)· 这个守护的全部告警路径在生产中从未被执行过**: 125 个锚的 `combo_live.log` 里 **0 条 PAGE、0 条 `skip aux-not-settled`、0 条 `COMBO_LIVE ABORT`**。有记录的 combo 页报只有 `notify_audit.jsonl` 里 4 行, 全部来自 2026-08-26 开机手工跑, **且第一行返回 `status: NOT_CONFIGURED`**(没有 token 到达通知器), 之后是一次通道自检与一次 `DELIVERED`。所以 `combo_stage._page` 只有一次来自手工跑的投递证明, 守护自己的 `page()`(另一段 heredoc)**一次都没有**。更糟: `_page` 把任何异常吞成一行 `PAGE_FAIL` 后返回, `_bail` 照样退 3, 守护又因在 runlog 里看见 `COMBO_LIVE ABORT` 而**故意不页报**(L43)⇒ **bail 撞上坏通道 = 端到端静默**。

**没有朝截止漂移**: 125 锚 OLS 显示生产者落地 **−0.80 s/锚(−4.8 s/日)**, combo 写入 −0.67 s/锚 ⇒ 余量在**变宽**。G1 周最小值 W35..W38 = **−112.8(那次重启)/ 55.0 / 54.8 / 103.0**。延迟预算: 生产者落地中位 1246.2 / p90 1294.3(主导项与主导方差), 守护 settle+poll 中位 8.4 s(150 s 预算从未接近耗尽), stage 运行中位 32.2 / 最大 74.2。⇒ **余量告警必须是逐锚余量的「水平规则」, 不能做斜率外推**, 否则永远不会在它该抓的事情之前响。

**三条小事实**: (a) `combo_live_status.json` 是**单槽可变文件**, 两条静默分支上都保留上一锚的 `{"ok": true}` ⇒ 读者不比对 `status["anchor"]` 就被告知「上次成功」(登记 PROD-33); (b) 排练模式写进**实盘状态树** —— `combo_stage.py` L340 用 `WS` 而非 `_outdir` 备份, 所以 08-26 00Z 有 king 备份却没有 combo 运行, 「有备份 ⇒ 跑过 combo」的朴素判据误计(登记 PROD-34); (c) 前向写是两步原子(json 后 `.sha256`), 而**回滚路径完全不原子**(两次 `shutil.copy2` 原地覆盖执行器正在读的文件); 两个窗口都在亚秒且被读者重试兜住, 均未观察到, 记录在案。

**一条按指令不动的事实(= PROD-30, 归 lead)**: G1(1355)与 G2(1360)仍按**已退役的 N+23:00** 标定, 08-27 读取改到 N+24:00 时没有同步 ⇒ **G1 比执行器首读早 85 s 关门, G2 早 80 s**。

**方法**: 用任何数字之前先做仪器正控 —— king 备份 mtime 等于生产者自己的 `written_utc` 字段, **124/124** 在该字段 1 s 截断内, 且 124 份备份都带 `producer: shadow_loop_v3`; 第二仪器 = 执行器逐锚的 `phase_A.external_book.producer`, **123 个覆盖锚上 0 处不一致**。**工作者自报一处中途错误**: 首轮交叉核对按锚为键让后到的行覆盖先到的行, 把 **673 条 DRY_RUN 电池行**混进实盘人口, 造出 17 个虚假的 stale/HOLD 锚; 按 mode 过滤后只剩一个真的(08-29 20Z)。该错误的产物没有进入任何报告。

**红测试**: `fx/prod27_sandbox.py` 通过 `date`/`sleep` 的 PATH 垫片与桩 venv python **逐字节驱动** `combo_live_daemon.sh`(sha 72f78d1e, 在 b891748 / afd94a2 / 实盘三处相同), 页报出不了机器, 不读写 `~/wide_shadow` 或 `~/dl_quant_live`。`tests_fx_prod.py P27` rc=1, 日志 `work/prod27/logs/RED_P27_on_afd94a2.log`:
- **RED S1** 生产者迟到 ⇒ 0 日志行 / 0 页报 / 0 记录(夹具 KEEP 证明分支确实跑了: last_anchor 推进)
- **RED S2** 无生产者文件 ⇒ 0 日志行 / 0 页报(夹具 KEEP 证明循环体从未执行)
- **RED S4b** 唯一存在的那条页报不带计数、不带 `margin_s`
- **RED S5** stage ABORT 之后没有「留在原地的是哪个形态」的逐锚记录
- **KEEP S3** 正常路径仍恰好调用 combo_stage 一次; **KEEP S4** aux/rolling 页报仍恰好一次; **KEEP S1b** 跳过不重写书

---
## P12 · `state_H_f10_<A>.npz` 的第二写者(克隆 bdb9e1f; 只测不修, 按裁定; lead 逐字转录)

**写者 = 侧车。** `state_H_f10_<A>.npz` 的**最后写者**是 `sidecar_blend.py`(由 `com.hsy.sidecar` PID 801 运行), **128/129 锚**。归因**按区间**而非按推断: 每个候选写者的运行窗取自它自己的守护日志(完成戳减去该次运行最后一个 `[ Xs]` 戳, ±2 s), 文件 mtime 落在其一、其二、两者皆是或皆非 —— 「皆非」报为 **UNATTRIBUTED, 不分配**。结果: `mtime − sidecar finish` 每个可归因行都在 **±1.0 s** 内; `mtime − combo finish` 为 **+122..+235 s, 中位 +168 s** —— 与 P2 的「kc/fc 之后约 2 分钟」精确吻合。唯一未归因的一份是 2026-08-26 00:00Z, 写于 N+8664 s, 即开机手工跑(与 `notify_audit` 里 now−anchor 8597/8664 s 的行同一次)。

**对链的含义**: `combo_stage` 写这个状态, 侧车约 168 s 后覆写 ⇒ **`combo_stage` 自己的 F-10 链状态每锚都被丢弃**, A+1 的暖启是**侧车的重算**, 不是产出被交易之书的那次运行。**任何用 `combo_stage` 代码重算该状态的回放都按构造与实盘不同** —— 即 P2 测到的 96 名 2.63e-8。且 **129 锚中 79 次侧车写入落在执行器首读 N+24:00 之后**(侧车完成中位 N+24:20)。

**PROD-29 应重定级(lead 已于 4f86635a 执行)**: 审计称侧车为「第二、非原子写者」并评 VERIFIED_IMMATERIAL / P3, 理由是「潜伏; 观察到 0 次碰撞」。**碰撞计数是错的检验: 没有碰撞是因为侧车每锚都赢。** 它也不是「只读」—— 自己的文件头写着「只读侧车」, 而事实上它是该实盘链状态在全部 129 锚上的唯一有效写者。工作者未擅自改他人审计行, 交由 lead。

**缺前驱的代价, 付过一次, 并且接回 PROD-27**: `state_H_f10_1788033600.npz`(2026-08-29 20Z)**不存在**, 因为那个锚什么都没产出(即上文的静默案)。于是 **2026-08-30 00Z 以 `h_source: "king_fallback"` 运行, `self_parity_maxdw` 6.58e-3**, 而其余每个锚是 ~2.3–3.2e-10 ⇒ **136 份 `target_blend` 文件里唯一一次 king_fallback, 且自平价差七个数量级**。**`h_source` 上没有任何页报。** 同一个锚上 `combo_stage` 又静默跳过, 所以那份链状态**只由侧车写成** —— 这也是 08-30 00Z 的链状态得以存在的唯一原因。**08-29 20Z 的生产者失败就这样无形地传进了下一锚的 F-10 状态; 两个静默缺陷是同一次事故的两截。**

**另一条机制, 由重启触发(登记 PROD-35)**: 侧车的 `LAST` 是内存 shell 变量(`sidecar_daemon.sh` L4)⇒ 重启后它按 `ls -t target_live/*.json | head -1` 重新处理一个**过去的**锚, 并在数小时后覆写该锚的链状态。四次: 08-24 08Z(+2.84 h)· 08-29 16Z(+7.50 h, 08-29 23:28Z 重启)· 08-30 04Z(+1.09 h)· 09-14 12Z(+3.79 h, 09-14 15:43Z 重启)。**查过最明显的担忧 —— 重跑是否拉进了锚后市场数据 —— 没有**: 四次都 0.8–2.4 s 且日志无「171 管线」重建, 即各自复用了自己锚的 `mini/cache.npz`(11 次确实重建的慢跑耗时 33–49 s: 十个 combo 之前的开机锚, 加上 08-30 00Z 因 combo 跳过而无缓存)。**不主张该机制在一般情形下安全**(缓存检查只按锚), 只主张它尚未误发。四次里有两次确实把「事后数小时重写的状态文件」喂给了随后的实盘锚: **08-30 04Z → 08-30 08Z**, **09-14 12Z → 09-14 16Z**, 两者 `h_source: own`。

**收据**: `FACT_TABLE_PROD.md` §P12(12.1–12.8); 普查 `FX_PROD/receipts/p12/P12_CENSUS.json`(sha **2bbd9c8c**); 装置 `fx/p12_state_h_census.py`。PROD-27 侧: `receipts/prod27/PROD27_CENSUS.json`(1a35f149)· `receipts/prod27/RED_P27_on_afd94a2.log`(4806474f)。叠加 diff 重生成 `docs/receipts/fx_prod_stack.diff` = `b891748..bdb9e1f`, **0 删除行**, sha `b22fb3a4…`。

**另**: `b891748` 仍与 13 个实盘生产文件及三个在役 plist **逐字节相同**(重启后复核), 但 **AUDIT_PROD PROD-28 已过期** —— 它是对 PID 10900 / 30944 / 30943 验的, 而 09-14 15:43:56Z 重启后三守护为 797 / 801 / 812(15:45:14Z 起)。OPS-01 / OPS-02 挺过重启: `launchctl print-disabled gui/501` 仍显示 `com.hsy.sigma_ladder => disabled` 与 `com.hsy.execprobe2 => disabled`, 两个 plist 都没回到 `~/Library/LaunchAgents/`。

---
## FXR-PROD-1 · 资金费迁移可双算且控制失败不阻断(独立复审 P1; lead 逐字转录 2026-09-16 04:2xZ)

**红, 在真实形状上**(不是夹具)—— 把迁移重跑在它**自己的修正输出**上, 这正是每月常规对账每个月对一份状态副本所做的事。对着复审点名的那份文件(sha `1cbeca90…`, 已确认与复审所引的逐字节相同):

| | 首次运行 | 修复前重跑 |
|---|---|---|
| 修正被应用 | 534 + 65 | **599 条全部重做**(D17 534 + P9 65) |
| 存储标签冲突 | 0 | **598**(复审的夹具只显示 1) |
| 控制 `max_abs` | 6.94e-18 | **4.0958e-06**, `n_gt_1e12` **70**, `n_gt_1e9` **17** |
| 退出码 | 0 | **0** |
| 状态文件 | 发布 | **5.1 MB `aux.corrected.json` 照常发布** |

**这个工具用三种彼此独立的方式检测到了问题, 然后带着成功码把结果发布了出去。**

**修复**(`migrations/fund_label_ema_correction.py`), 对照 lead 的合同:
- **(a) 增量相对「输入吸收了什么」** —— 输入状态自己的账本尾部现在对它持有的行**具权威**; 冻结账本只补充已经离开尾部的行。此前是冻结源先加载、`setdefault` 钉死它们的陈旧标签。
- **(b) 冲突被拒绝或被显式解决** —— 每处分歧都分型: `frozen_vs_frozen` 与 `rate_differs` 拒绝; 输入标签只在**有出处**时接受(等于声明值, 或来自另一个冻结源), 否则拒绝。
- **(c) 控制闸住发布** —— 控制**总是**运行(`--control` 保留只为调用点兼容), 输出写 `.tmp`, 可用文件名只在六道门全过之后经 `os.replace` 出现; 否则删除临时文件并 **退出 2**。

**已验证**:
- **G1 / K1-K2(回归)**: 修复后的工具在原输入上 → `aux.corrected.json` sha **`fc3125ad282584bf` —— 与修复前的输出逐字节相同**。同样 599 条修正, 同样控制 `6.938893903907228e-18`, 六门全绿。**一次性迁移未被触碰。**
- **G2 / R1-R1b(红案)**: 598 条尾内重复计数被消除(D17 534 → **0**, 598 条全部被识别为**已吸收**, 0 条不可解释)。唯一残留是一条**尾外**行(ONG, dacc −3.4e-08), 其标签状态无法承载 —— 被正控抓住, `PASS=False`, **rc 2, 不写文件**。
- **N3**: 598 条带出处解决, **0 条不可解释**。**N1**: 尾外修正在无显式旗标时被拒, `rc 2`, 无文件。
- **未移除任何断言或门**: 被删的 9 行恰好是语义被本次修复替换的那几行; 对 diff 的移除侧 grep `assert|need(|gate` 为空。

**一个值得点明而非夸大的设计点**: 我**做不到**让重跑成为字面上的 no-op, 原因是结构性的 —— 一条已经离开账本尾部的结算在状态里**不带标签**, 而修订标记帮不上忙, 因为 `shadow_loop_v3.py::save()` 写的是**固定键集**, 下一个锚就会把它丢掉。所以尾外修正现在默认拒绝, 置于显式的 `--allow-out-of-tail` 之后: **一次性换装迁移会传它**(它恰好有 1 条这样的行), **每月常规作业绝不传**, 而且即便被传, **控制仍是兜底**。Swap plan §2 步骤 3 与 §7 现在明写这一点。
> **lead 追加(§16.1)**: 由此得到一条通用否决理由 —— **任何把「我已吸收到哪一版 / 哪些行」写进生产者状态的方案, 都会被 `save()` 的固定键集静默抹掉。** 这不只是本项的限制, 是一整类设计的否决。

---
## PROD-28 重取 · 运行中代码 ↔ 盘上代码(lead 批准并要求; 逐字转录)

**10/10 文件 `DISK_IS_RUNNING_CODE`, 0 unknown**; bundle `MANIFEST.json` `af61d597` **8/8 相符**。方法学按要求写明: **「mtime 早于进程启动」是全部主张, `lsof` 只作佐证, `git HEAD` 故意不用**。
**我的装置犯了它存在就是为了抓的那一类缺陷**: 它找的是 `MANIFEST`, 而文件叫 `MANIFEST.json`, 于是报 `bundle_mismatch=None`(缺字段就跳过同族)。现在**清单缺失或 0 条目即硬退出**。事实 F28.5 记录了对 `b891748` 的比对**连同其取证方法**。

---
## P5 · 换装 dry run · 装载条件(逐字转录)

- **换装 dry run 完成**: 各步 rc=0, `LIVE_RO unchanged`, 5m29s。**占用 24 MB**(p5 9M / corr 5M / compose 5M / p1 4.9M)—— 「先量再跑」在程序上是对的, 但真实成本可忽略, 记下来以免下次把它当重活。**另**: 我先修了该驱动里一个真实缺口 —— 它的锚窗兜底**只覆盖 20Z**, 于是一次超时运行会无守卫地进入下一个锚(克隆 `0719874`)。
- **P5 通过门**: **81/81 已记录行逐位复现**, `max_abs_diff 0.0`; 席位 w3m king 0.382095 → 0.384765。
- **P1 迁移**: 525 名, 0 冲突。
- **装载测试经验性地确认了 lead 的部署条件**: 新码遇未迁移状态给出 **`REFUSE_TO_START: FUND_COL80_V0 but state has no ema_v0`** —— 这是实测的拒启字符串, 已钉进 swap plan(部署不能只换 `.py`)。

**一次自报的工具错误**: 又被 zsh 不分词咬到 —— `$PY` 从未执行, 而 `rc=$?` 读到的是 `tail` 的状态, 于是一次**失败的验证报出 `RC=0`**; 靠**读输出**抓住, 记忆条目已补上这第二种形态。(**lead 追加规则**: `rc=$?` 必须紧跟被测命令, 中间不得隔管道或 `tail`; 有管道就用 `PIPESTATUS` / `pipestatus`。)
