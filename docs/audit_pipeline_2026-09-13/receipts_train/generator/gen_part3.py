# -*- coding: utf-8 -*-
# Part 3: register items TRN-13..TRN-29 and the closed-in-code list
from gen_part2 import R, item, C, T

item(id="TRN-13", layer="DOC (king cutoff labels)",
 title="(h) Documents still say the in-service booster is 'trained to 08-31'; it was fitted on label year < 2026. New v4 bundles would carry the right field",
 what_is_wrong=("The in-service booster 8d79186b was fitted with `tr = YRA < 2026` (last training anchor 2025-12-31T20Z). Its bundle config has only built_utc and generation. Three documents describe it as trained to 08-31. "
   "The v4 exporter writes king_train_end_utc, so the October bundle itself would not repeat the mislabel."),
 evidence=[
   "docs/PREREG_producer_parity_phase2_oos_2026-09-12.md L6 and L28 ('在役 booster(训练到 08-31)', '在役训练到 08-31 的 booster')",
   "docs/PREREG_producer_parity_replay_2026-09-12.md L36 ('训练到 08-31 的在役 booster'); docs/PLAN_fix_all_gaps_2026-09-12.md L18 ('在役模型训练到 08-31')",
   "~/wide_shadow/shadow_bundle/config.json 3a8422f3 provenance keys: built_utc 2026-09-01T06:00:37Z, generation v3_2026-09, base_ic, fold_ic_2024/2025, pinned_ic2026, pinned_sharpe_full_b (no training cutoff)",
   f"{T}/pod_export_bundle_v3.py L49 tr = YRA < 2026; {C}/pod_export_bundle_v4.py L263-266",
 ],
 status="DOC_STALE", affects=["reporting"], severity="P3",
 severity_reason="Misleads readers about what the live king has seen (E-0907-D family); no numeric effect.",
 recommended_action="Correct the three documents to 'fit on label year < 2026 (last training anchor 2025-12-31T20Z)'.",
 method="VERIFIED")

item(id="TRN-14", layer="DL (artifact metadata)",
 title="The live F10 numpy artifact claims trained_through 2026-08-30T20Z (pool end); the next numpy export would write the same kind of value",
 what_is_wrong="pod_f10_np_export.py writes the maximum anchor of the targets file as trained_through. The in-service refit's gradients ended about 2025-12 (85/15 split). The refit sidecar now separates label cutoff and pool end, but the numpy artifact the producer loads does not.",
 evidence=[
   "~/wide_shadow/fea171/f10_live_s42_np.npz 351ae26b: keys alpha,b0,b1,b2,mu,n_cols,sd_,trained_through,w0,w1,w2; trained_through 1788120000 = 2026-08-30T20:00Z",
   f"{T}/pod_f10_np_export.py 3e304c27 L26; in-service refit {T}/pod_f10_refit_ext.py ea3675b8 L90 cut 0.85, L122 trained_through = E_ts[tr_idx[-1]]",
   "docs/ERROR_LEDGER_2026-08-20.md E-0907-D (L495) and E-0907-H (pool end ≠ loss-window end)",
 ],
 status="OPEN_NOT_MEASURED", affects=["reporting"], severity="P3",
 severity_reason="No numeric effect; a known misleading-field pattern that has already produced one wrong conclusion (E-0907-D).",
 recommended_action="Numpy export copies trained_through_label_utc and trained_through_pool_end_utc from the refit sidecar and drops or renames the ambiguous key.",
 method="VERIFIED")

item(id="TRN-15", layer="EXPORT (gate baseline)",
 title="The export gate pins September's BUNDLE_BASE and LIVE_PINS by sha, while the October template requires new files: an unlisted approval blocks October's export stage",
 what_is_wrong=("E2b requires LIVE_PINS and BUNDLE_BASE to be byte-identical to the approved baseline in the contract. RUNBOOK §1 and the October template require a newly established base json (the previous generation's own fold IC) and a re-copied pins file. "
   "So October's export either fails E2b by construction, or the operator reuses September's base json against the runbook, or someone amends approved_baseline — which is not on any pending-approval list."),
 evidence=[
   f"{C}/v4e_gate_export_v2.py d63f4ec3 L182-184: sp_ = sha256_file(E[\"LIVE_PINS\"]); sb = sha256_file(E[\"BUNDLE_BASE\"]); chk(\"E2b_pins_identity\", sp_ == cx.ab[\"live_pins_sha256\"] and sb == cx.ab[\"bundle_base_sha256\"], ...)",
   f"{C}/ELIGIBILITY_CONTRACT.json 1188267a gates.BUNDLE_export.approved_baseline: bundle_base_sha256 dce6a228543b…, live_pins_sha256 fd27fe485417…",
   f"{C}/v4_month_2026-10.env.template L26-27 'base = the previous generation's OWN fold IC json … re-established every month' BUNDLE_BASE=/workspace/TODO_slow_scorer_v4base_2026-10.json; L30-31 LIVE_PINS re-copied",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L111 '基线 json 每月重立'",
   "September export base IC 0.0548 / 0.0630 / 0.0571 vs September v4 own fold IC 0.0544 / 0.0609 / 0.0573 (receipts/monthly_chain_2026-09-12/pod2_king_legs/export_v4.log)",
 ],
 status="PENDING_USER_DECISION", affects=["future_retrain"], severity="P2",
 severity_reason="Fails closed (no bad bundle passes), but it stops October at export and the required ruling is not listed anywhere.",
 recommended_action="Decide before running: reuse September's base json and pins byte-identically (and say so in §0★), or amend approved_baseline with the October shas under the user's word.",
 method="VERIFIED (code); October outcome INFERRED")

item(id="TRN-16", layer="GATE (fea89 trend)",
 title="Frozen STEP1 fails on September data (global-cumsum trend_288); October's references were built under that failure and STEP1_m can pass only if the cache prefix is byte-unchanged",
 what_is_wrong=("fea89's trend_288/trend_2016 use full-axis cumulative sums; any upstream edit changes values far downstream and dead names flip NaN/finite. The frozen STEP1 therefore FAILS on September data, and the AMENDMENT 3 exception reading was withdrawn. "
   "September's DL products (October's PREV_* references) were built by that builder. October's STEP1_m compares the two months on the common axis; it can pass only if the cache prefix is untouched — replacing the holefix2-filled 2026-08-31 day with the now-available vendor archive, or any new prefix fill, would make it fail outside hole neighbourhoods. "
   "The stable local-trend builder (G1/G2 PASS, book effect (C)) awaits the user's word; the October template still points BUILDER_FEA89 at the global builder."),
 evidence=[
   "docs/PREREG_fea89_stable_trend_and_closure_gate_2026-09-09.md L6 (pod_f8_build_ext.py L204–L216 global cumsum; 31,059 NaN flips), L30-31 (stable builder G2 PASS; global builder FAIL 53,425 cells / 247 anchors on trend_288)",
   "docs/PREREG_v4_gates_monthly_2026-09-12.md §7.4: STEP1_m on September data rc 3, PASS=false, 78/0 fields vs the 09-09 archive; DESIGN §6.2 driver stops FAIL_gate_require_step1",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L59 (iv) '九月数据上 STEP1 字面 FAIL(trend_288 全局累积和 … 稳定 trend 候选待用户字)'",
   f"{C}/v4_month_2026-10.env.template L47 BUILDER_FEA89=/workspace/pod_f8_build_ext.py (f606bffa, global builder)",
   "multi_asset/exports/research/uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md §2: 2026-08-31 cache day was holefix2-filled (229,824 cells / 798 symbols); vendor daily archive now 200",
 ],
 status="PENDING_USER_DECISION", affects=["future_retrain"], severity="P2",
 severity_reason="Fails closed, but October may stop at the gates for a reason unrelated to October's data quality; the ruling decides which fea89 October trains on.",
 recommended_action="Rule on the stable-trend builder before October; if kept global, make the month roll strictly append-only and record that choice in the month contract.",
 method="VERIFIED (September); October outcome INFERRED")

item(id="TRN-17", layer="DL (legs at the data frontier)",
 title="E-0911-B recurs every month: the last 5 anchors of the axis have no panel row, so legs rows go dead (WL 1/3) and king fund columns are NaN, with only a printed warning",
 what_is_wrong=("The panels require E+288 <= TT while the king/DL axis requires E+48 <= TT, so the panel is always 5 anchors short at the frontier (r6: 'structural, recurs at every extension frontier'). "
   "pod_legs_v4b.py leaves Z24/ZFD NaN for rows without a panel row and prints their list; the trainer maps NaN to 0, so on those anchors the DL book has no rev24/fund legs and the seat is the untrained [1/3,1/3,1/3]. "
   "For October that is at least 2026-09-30 04Z–20Z (202609 test month, refit validation slice, judge windows); if LEGS_PANEL is not extended at all, all September rows."),
 evidence=[
   f"{C}/pod_legs_v4b.py 8c33a230 L21-22 z24/zfd filled only `if j is not None`; L51-52 prints 'new rows without a panel row (Z24/ZFD NaN by construction)' (no assert)",
   f"{C}/pod_f10_refit_v4.py L37-39 np.nan_to_num(L[\"Z24\"], nan=0.0), L[\"ZFD\"] nan=0.0, L[\"WL\"] nan=1/3",
   f"{C}/pod_fea_ext_clamp.py L79-82 fund columns written only when the panel has the anchor (else left NaN)",
   "multi_asset/exports/research/uplift_2026-09-11/RESULT_r6_coverage_extension_2026-09-11.md §1 (E-0911-B: 2026-08-31 04Z–20Z legs Z24/ZFD 0 finite, WL [1/3,1/3,1/3]; king fund_ema finite frac 0.0000) and L286 ('E-0911-B 是结构性的 … 每一次延展的前沿上复发')",
   f"{C}/chain_v4_monthly.sh L209-216 checks only LEGS_V4B_DONE and the 2023 king seat",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_eval", "future_retrain"], severity="P2",
 severity_reason="Silent every month on the frontier anchors that feed the newest fold test and the judge extension windows; bounded to a few anchors unless the panel is not extended.",
 recommended_action="Align the panel and axis truncation rules, or cut every decision window and fold test at the last anchor that has a panel row; make pod_legs_v4b.py fail when a new in-axis row lacks a panel row.",
 method="VERIFIED")

item(id="TRN-18", layer="SWAP (acceptance)",
 title="The swap step's acceptance cannot catch caliber splits (A2 resets to the reference every anchor), cites void sections, and has no producer-path score parity",
 what_is_wrong=("acceptance.py A2 advances the comparison with the reference weights each anchor (H = ref) and passes on median weight correlation >= 0.99; both vectors share 0.9·H, so input-scale errors such as TRN-04/05 pass. "
   "RUNBOOK §0★ step 8 points to the verbs of §3-3/§4-8, which are marked void. There is no raw-score parity of the new booster or the new numpy DL model on the producer's feature path, and the continuous-parity device (parity_replay_2026-09-12) is not part of the swap."),
 evidence=[
   "~/wide_shadow/acceptance.py 2149b64c L165 `H = ref  # 每锚对照后用参考轨迹前进(隔离单锚误差, 不累积)`; L167 report(\"A2_frozen_parity\", med >= 0.99 and len(cors) >= 60, ...)",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L23 step 8 '同 §3-3 / §4-8 的动词'; L130, L148 void banners",
   "STATE.md (line ~57): reviewer 0dfc0d87 ② accepted — '旧 A2 是单步平价(acceptance.py L165 H=ref), 合成翻倍反例仍过'",
   "memory king-fund-ema-feature-train-v0-serve-v1 L17: 'Shadow acceptance A2 could not catch it'",
 ],
 status="OPEN_NOT_MEASURED", affects=["live_trading"], severity="P2",
 severity_reason="The last check before live money is known to be blind to the defect class this audit finds reintroduced.",
 recommended_action="Write a v4 swap checklist inside §0★ (backup, atomic swap, seat seeding, producer-path raw-score parity for booster and numpy model, N-anchor continuous parity, first-anchor acceptance) and stop treating A2 as a pass criterion.",
 method="VERIFIED")

item(id="TRN-19", layer="CHAIN (contract loader)",
 title="Reviewer P3 confirmed on the current source: a parser output line without '=' (bare `R`) is exported as R=R, and no negative control exists",
 what_is_wrong=("After the Python parser exits 0, Bash re-validates each output line with `${line%%=*}` / `${line#*=}`. A line with no '=' yields key R and value R, passes the registered-key and literal-character checks, and is exported as R=R. "
   "The suite has a control for a value outside the grammar but none for a bare key. The real parser always prints key=value, so this needs a faulty interpreter to trigger."),
 evidence=[
   f"{C}/chain_lib.sh 4ee217e1 L147 `k=${{line%%=*}}; v=${{line#*=}}`; L148-151 checks; L157 `export \"${{line%%=*}}=${{line#*=}}\"`; L131 real parser prints k + \"=\" + resolved[k]",
   f"{C}/tests_pipeline_gates.py a3af858d L1602-1603: only 'parser that exits 0 but emits a single key whose value is outside the grammar ⇒ rc 4'",
   ".claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round4_code_review_2026-09-13/retrain/RESULT.md §2 (parser_bare_registered_key_OUTPUT_ACCEPTED: stub parser, loader rc 0, PARSED_R=<R>); reviewer's frozen chain_lib sha = current 4ee217e1",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain"], severity="P3",
 severity_reason="Second-line defence only; requires a broken or substituted interpreter.",
 recommended_action="Before splitting: `case $line in *=*) ;; *) die month_env_parser_output_$(basename \"$f\") 4 ;; esac`; add a [U] cell with a stub PY emitting a bare `R` (expect rc 4, no MONTH_ENV_OK) run against the current and pre-fix chain_lib.",
 method="VERIFIED (code read; not re-executed)")

item(id="TRN-20", layer="REPRO (environment)",
 title="The env allowlist covers only the data stage; judge/export knobs that loosen gates are read from the operator's shell, and the driver ignores the judge's exploratory flag",
 what_is_wrong=("Only data-stage children run under env -i. King export, legs, mwf, refit, arms, judge and export inherit the shell. BUNDLE_GUARD_LO/HI (exporter guard band), JUDGE_ALLOW_PARTIAL / JUDGE_REPRO_TOL / JUDGE_N_FROZEN (judge) and FORCE / BEST_EP_FLOOR (trainer) are read from it. "
   "Some fail closed (trainer effective-value whitelist; the export gate refuses a band or N_FROZEN that differs from the contract). JUDGE_REPRO_TOL loosens the reproduction gate, and JUDGE_ALLOW_PARTIAL makes the judge exploratory while the driver still writes JUDGE_V4_DONE and MONTHLY_DONE."),
 evidence=[
   f"{C}/chain_v4_monthly.sh L130-148 env -i only in the data stage; L191-192, L207, L250, L281, L300 plain env; L282-283 judge checked only by marker",
   f"{C}/pod_export_bundle_v4.py L179 BUNDLE_GUARD_LO/HI from env; {C}/judge_v4.py L59-63 JUDGE_ALLOW_PARTIAL / JUDGE_REQUIRE_W / JUDGE_STRICT_BOOK, L150 JUDGE_N_FROZEN, L279 JUDGE_REPRO_TOL; {C}/pod_f10_train_monthly_v4.py L277-278 FORCE / BEST_EP_FLOOR",
   f"{C}/v4e_gate_export_v2.py L107-110 refuses env thresholds that disagree with the contract",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain", "future_eval"], severity="P3",
 severity_reason="Needs a polluted operator shell; partly fail-closed.",
 recommended_action="Run every non-GPU stage under env -i with an allowlist; unset JUDGE_*, BUNDLE_GUARD_*, FORCE, BEST_EP_FLOOR, MONTHS before GPU dispatch; refuse a judge JSON with exploratory=true.",
 method="VERIFIED")

item(id="TRN-21", layer="REPRO (king recipe)",
 title="King recipe declares subsample=0.8 but bagging never runs (bagging_freq 0); training is non-deterministic by configuration",
 what_is_wrong="LightGBM only bags rows when bagging_freq > 0. The saved in-service booster records bagging_fraction 0.8 with bagging_freq 0, so row subsampling has never happened in any generation. deterministic is 0 with 100 threads; the chain absorbs that with |ΔIC| tolerances rather than bitwise parity.",
 evidence=[
   f"{C}/pod_export_bundle_v4.py L67-68 LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1)",
   "~/wide_shadow/shadow_bundle/slow2026.txt 8d79186b L7706 [num_threads: 100], L7707 [seed: 0], L7708 [deterministic: 0], L7715 [bagging_fraction: 0.8], L7718 [bagging_freq: 0], L7721 [feature_fraction: 0.8]",
   "LightGBM Parameters docs (context7): 'To effectively enable bagging, the bagging_freq parameter must also be set to a non-zero value'",
   "receipts/monthly_chain_2026-09-12 (DESIGN §6.5): 6 of 8 bundle files bitwise equal to 09-09; slow_pred_pinned.npy bitwise equal; slow2026.txt differs in tree_sizes text",
 ],
 status="VERIFIED_IMMATERIAL", status_resolution="Same effective recipe (no bagging) in every generation; predictions reproduced bitwise in the 09-12 control.",
 affects=["reporting"], severity="P3", severity_reason="Declared recipe differs from the effective one; no drift between research and production because both use this exporter.",
 recommended_action="Either set subsample_freq=1 under a preregistration (recipe change) or record the effective parameters and LightGBM version in provenance.",
 method="VERIFIED")

item(id="TRN-22", layer="REPRO (self-report)",
 title="E-0907-G recurs: the October trainer's results claim per-fold seeds SEED+YM while the code uses the constant SEED",
 what_is_wrong="The v4 trainer was generated from the base copy that still carries the false fold_rule.rng string; ledger E-0907-G fixed it only in the full-window patch.",
 evidence=[
   f"{C}/pod_f10_train_monthly_v4.py fd5707bd L272 comment 'per-fold RNG: torch.manual_seed(SEED + YM)'; L295 \"rng\": \"torch.manual_seed(SEED+YM); np.random.seed(SEED+YM) per fold\"; L336 torch.manual_seed(SEED); np.random.seed(SEED)   # mE1_constseed",
   f"{C}/make_v4_scripts.py L8 generator base /workspace/review_scratch/allweather_trackB/pod_f10_train_monthly_earlystop.py (archived as base_pod_f10_train_monthly_earlystop.py 55ee8382)",
   "docs/ERROR_LEDGER_2026-08-20.md E-0907-G (zero numeric effect; string false)",
 ],
 status="VERIFIED_IMMATERIAL", status_resolution="Zero numeric effect per E-0907-G (seed_fold and env_given.SEED record the real seed).",
 affects=["reporting"], severity="P3", severity_reason="A false receipt on the seed axis; readers of the string alone get the wrong answer.",
 recommended_action="Fix the emitted string and comment in make_v4_scripts.py; add an AST test that the rng string matches the seeding call.",
 method="VERIFIED")

item(id="TRN-23", layer="REPRO (provenance / single source)",
 title="Provenance gaps: git single-source copy of the base trainer is a different file; external builder shas are recorded, not asserted; bundle provenance has no shas; merge does not assert fold identity; pod2 run copy is stale",
 what_is_wrong=("(1) retrain_2026-09/pod_f10_train_ext.py in git is f3c1e3cf (the L1SM variant), not the 93cc2cdf base that the v4 trainer header and T4b cite and that pod2 holds (its git copy lives under allweather_2026-09-05/trackB/scripts/). "
   "(2) BASE_TRAINER, BUILDER_FEA82 and BUILDER_FEA89 are hashed by preflight but never compared with expected values (today pod2 == git for both builders). "
   "(3) The bundle's config.json lists input paths but no input shas and no exporter sha (the month root's deps pins and the export-gate receipt do carry them). "
   "(4) merge_mwf_v4b.py records each fold's self_sha256 but does not assert it equals the dispatched trainer; the trainer resumes finished folds without checking legs/source identity (DESIGN §7 (v)). "
   "(5) pod2's /workspace/review_scratch is the September legacy run copy, and /workspace/pod_env_bootstrap.sh named in §0★ step 0 is absent."),
 evidence=[
   "receipts_train/SHA256SUMS_retrain_scripts_and_docs.txt: retrain_2026-09/pod_f10_train_ext.py f3c1e3cf…; allweather_2026-09-05/trackB/scripts/pod_f10_train_ext.py 93cc2cdf…; pod2 /workspace/pod_f10_train_ext.py 93cc2cdf (pod2 receipt); git log 8d6d8faa 'PREREG L1SM … 装置f3c1e3cf3afc'",
   f"{C}/pod_f10_train_monthly_v4.py L263 'byte-identical to /workspace/pod_f10_train_ext.py (sha256 93cc2cdf…)', L288-289 base_sha256 recorded",
   f"{C}/chain_v4_monthly.sh L62-65 external_sha256 recorded only; {C}/pod_export_bundle_v4.py L258-269 provenance (paths, no shas)",
   f"{C}/merge_mwf_v4b.py L29-35 (asserts seed/embargo/causality/rule/GATE; records self_sha256 without comparison); {C}/pod_f10_train_monthly_v4.py L318-320 _done resume",
   "pod2 receipt: review_scratch chain_lib ffbb89b8, v4_gate_common 7b6d49a3, contract 3299dc97, exporter b5b6cd19, trainer 2147a7dd, refit 2e9c999b, merge 9f8c2b93, judge 7f1aa5d6; chain_v4_monthly.sh / v4_gate_step{1,2}_m.py / v4e_gate_export_v2.py absent; /workspace/pod_env_bootstrap.sh absent",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain", "reporting"], severity="P3",
 severity_reason="None changes a number today; each weakens the ability to prove later which code produced an artifact.",
 recommended_action="Restore the 93cc2cdf file under retrain_2026-09/pod_f10_train_ext.py (rename the L1SM variant) or pin BASE_TRAINER's sha in the contract; add expected-sha keys for the two external builders; add exporter sha and input shas to config.json provenance; assert fold self_sha/legs_sha in merge.",
 method="VERIFIED")

item(id="TRN-24", layer="EVAL (judge / signal receipt / naming)",
 title="Judge windows end at 2026-08-31, so October's new month is never read; SIGNAL_RECEIPT is required before it can exist; September predictions land in a file named SLOW_v3_on_v4axis",
 what_is_wrong=("(1) judge_v4.py's windows are literals ending 2026-08-31; October's month appears in no judge reading (the frozen verdict is unaffected). "
   "(2) Preflight requires SIGNAL_RECEIPT to exist before any stage, while the template says it is produced for this month's arm before export; for A1 the export gate marks E7 not applicable, so the file only has to exist. "
   "(3) With the October template, build_dev_v4.py writes September's v4 predictions into SLOW_v3_on_v4axis.npy."),
 evidence=[
   f"{C}/judge_v4.py L55-58 FROZEN = (2025-03-01, 2026-08-10 20Z), EXT = (2025-03-01, 2026-08-31 20Z), '08-31 (6)' window",
   f"{C}/chain_v4_monthly.sh L49 PF_INPUTS includes SIGNAL_RECEIPT; {C}/v4_month_2026-10.env.template L44-45; {C}/v4e_gate_export_v2.py L378 E7 not applicable without FEMAT",
   f"{C}/build_dev_v4.py L46-47 (PREV_BUNDLE pinned PRED aligned → SLOW_v3_on_v4axis.npy); template L55-56 PREV_BUNDLE=/workspace/shadow_bundle_v4, PREV_META=wide_fea_v4_meta.npz",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_eval", "reporting"], severity="P3",
 severity_reason="Reading gaps and naming hazards (E-0825-H); no verdict changes.",
 recommended_action="Derive the judge's extension windows from the axis end (keep FROZEN fixed); make SIGNAL_RECEIPT conditional on a FEMAT-injected arm; rename the reference SLOW file to a generation-neutral name.",
 method="VERIFIED")

item(id="TRN-25", layer="CHAIN (integration)",
 title="Seven of the driver's eleven stages (cache, data, mwf, refit, arms, judge, export) have never run through the driver on real data; current sources of trainer, refit, exporter, merge, launcher, build_dev and run_v4_arms have never run on real data",
 what_is_wrong="Real-data runs through the driver were limited to preflight+gates (frozen September gates) and king+legs on isolated September roots. Older versions of the business stages ran in the 09-09 legacy chain. The reviewer's five (mwf/refit/arms/judge/export) remain unexercised end to end; cache and data were only exercised on synthetic or legacy paths.",
 evidence=[
   "receipts/monthly_chain_2026-09-12/pod2_root/chain_v4_monthly.log (stages=preflight,gates; FAIL_gate_require_step1); pod2_king_legs/chain_v4_monthly.log (stages=king,legs; MONTHLY_STAGES_DONE)",
   "docs/DESIGN_v4_monthly_chain_2026-09-12.md §7 (ii); reviewer round-4 RESULT §3 '真实mwf/refit/arms/judge/export尚未跑通'",
   "receipts/PROVENANCE_v4_chain.json scripts (09-09): trainer 2147a7dd, exporter 23b1a5c7, refit 2e9c999b, legs pod_legs_v4 91330c06",
 ],
 status="OPEN_NOT_MEASURED", affects=["future_retrain"], severity="P2",
 severity_reason="The design fails closed, so the likely cost is a stalled October run rather than a silent bad bundle.",
 recommended_action="Before October, rehearse mwf→export once on an isolated root with September data and a reduced month set (one shard, one seed), reading every receipt; resolve TRN-16 (or use a waived STEP1 copy for the rehearsal only).",
 method="VERIFIED")

item(id="TRN-26", layer="APPROVALS",
 title="Pending approvals before October can run to export: STEP1_m 79950786…, STEP2_m d99a9109…, NONE clamp switch, and an unlisted export-baseline ruling; plus recipe/caliber rulings",
 what_is_wrong="The contract approves only the frozen September gate sources; the month-generic gates and several October-specific switches need the user's word. The export-baseline ruling (TRN-15) is on no existing list.",
 evidence=[
   f"{C}/ELIGIBILITY_CONTRACT.json 1188267a: gates.STEP1.approved_source_sha256 = [278fdce611e9…]; gates.STEP2.approved_source_sha256 = [db7ab3561f97…]",
   "docs/PREREG_v4_gates_monthly_2026-09-12.md §7.11 E5: real contract 'REQUIRE_FAIL … d99a910951e0 is not an APPROVED source'; AMENDMENT 3 '★ 批准对象再次变更 … d99a9109'",
   f"{C}/v4_month_2026-10.env.template L63-68 (NONE + PREV_CLAMP_BUILDER_SHA256 b9f9c728)",
 ],
 status="PENDING_USER_DECISION", affects=["future_retrain"], severity="P2",
 severity_reason="Blocks October by design until ruled.",
 recommended_action="Present the list in AUDIT_TRAIN.md §1.3 to the user as one decision sheet, with d99a9109 (not 0fe5ec55/b2f9cfd4) as the STEP2_m object.",
 method="VERIFIED")

item(id="TRN-27", layer="DOC (runbook)",
 title="RUNBOOK_2026-10 never names the current STEP2_m approval object d99a9109; it asks for 0fe5ec55 (修订 4) and b2f9cfd4 (修订 5), and its device sha table is stale",
 what_is_wrong="A user following the runbook text would approve a superseded red-control snapshot. The §0★ device sha table and the October template comment are also out of date.",
 evidence=[
   "grep 'd99a9109' docs/RUNBOOK_monthly_retrain_2026-10.md → 0 matches",
   "docs/RUNBOOK_monthly_retrain_2026-10.md L62 (STEP2_m sha 0fe5ec5573f3…), L76 (合同批准 … 增补 0fe5ec55…), L91 (→ b2f9cfd4…); L10 device sha table (chain_lib ffbb89b8 …; current chain_lib 4ee217e1, chain_v4_data 2369a87d, chain_v4_gpu3 16bfdb7e)",
   f"{C}/v4_month_2026-10.env.template L50 names 0fe5ec55; docs/DESIGN_v4_monthly_chain_2026-09-12.md §10.5 '陈旧注释(未改 …)'",
 ],
 status="DOC_STALE", affects=["reporting"], severity="P2",
 severity_reason="The decision document for a pending user ruling names the wrong object; preflight would still refuse (fails closed) but a ruling would be wasted.",
 recommended_action="Add 修订 6 to §0★ naming d99a9109 as the only STEP2_m approval object and 455e3df4/0fe5ec55/b2f9cfd4 as red-control snapshots; refresh or delete the sha table.",
 method="VERIFIED")

item(id="TRN-28", layer="DOC (routing)",
 title="CLAUDE.md routes 月度重训 to the superseded September runbook, which is still marked 待执行",
 what_is_wrong="The session-start routing table points to RUNBOOK_monthly_retrain_2026-09.md (08-19, pre-v4 procedure: pod_export_shadow_bundle.py, unclamped features). The operative document is RUNBOOK_monthly_retrain_2026-10.md §0★. This audit's own brief started from the old file.",
 evidence=[
   "CLAUDE.md L47 '| 月度重训 | `docs/RUNBOOK_monthly_retrain_2026-09.md` |'",
   "docs/RUNBOOK_monthly_retrain_2026-09.md L3 '状态: 待执行(pod 资源到位后)'; docs/RUNBOOK_monthly_retrain_2026-10.md L3-L10 (§0★ supersedes)",
 ],
 status="DOC_STALE", affects=["future_retrain", "reporting"], severity="P2",
 severity_reason="New sessions are routed to an obsolete procedure for a real-money model change.",
 recommended_action="Route 月度重训 to RUNBOOK_monthly_retrain_2026-10.md §0★ and mark the September runbook superseded in its header.",
 method="VERIFIED")

item(id="TRN-29", layer="DOC (memory)",
 title="Memory says the r20 v2 export gate is 'PROPOSED 未应用'; the chain contract shows it APPLIED on 2026-09-12T09:04:39Z",
 what_is_wrong="The memory note and its MEMORY.md index line predate the application; the contract's BUNDLE_export gate approves d63f4ec3 and the judge floor is the v2 gate's 28-name closure.",
 evidence=[
   f"{C}/ELIGIBILITY_CONTRACT.json 1188267a status 'APPLIED 2026-09-12 (user word 09-12: …); was PROPOSED2 01692565…', applied_utc 2026-09-12T09:04:39Z; gates.BUNDLE_export.approved_source_sha256 [d63f4ec3f9e6…]",
   f"{C}/v4_gate_common.py 24e813f1 L72-78 (BUNDLE_export floor = 28 names of the v2 gate)",
   "memory export_gate_v2_falsifiability_closure_2026_09_12 description '(NOT APPLIED, user ruling pending)'; MEMORY.md line 'r20 出口门 v2 可证伪性收口 09-12 (PROPOSED 未应用)'",
 ],
 status="DOC_STALE", affects=["reporting"], severity="P3",
 severity_reason="Misstates gate status to future sessions; no effect on the chain.",
 recommended_action="Update the memory note and index line to 'APPLIED 2026-09-12T09:04:39Z (contract 1188267a)'.",
 method="VERIFIED")

CLOSED = [
 ("R1 refit silent defaults (dlw_ext/f8_ext/argmax)", f"{C}/pod_f10_refit_v4.py L12-17 required env, refusal before torch import"),
 ("R2 hardcoded fold-month whitelist 202501..202608", f"{C}/pod_f10_train_monthly_v4.py L302-305 (v4_months), merge_mwf_v4b.py L19"),
 ("R3″ king export must precede legs; legs use this month's PRED", f"{C}/chain_v4_monthly.sh L184-217"),
 ("R4 generation label constant; exporter default output dir (E-0912-B)", f"{C}/pod_export_bundle_v4.py L21-27, L259, L263-266"),
 ("B-R3 CLIP targets inheriting a patch / ambient builder env", f"{C}/chain_v4_monthly.sh L130-148 (env -i, DLWT_RAW_PATCH= empty)"),
 ("R5 legacy September chain scripts runnable", "chain_v4_data.sh L6, chain_v4_gpu3.sh L9, chain_v4s_gpu.sh L12, chain_king_e.sh L4, chain_v4_post_export.sh L9: V4_LEGACY_OK guard"),
 ("D1 refit sidecar identity (null locators)", f"{C}/chain_lib.sh prereq_refit_sidecar (reviewer round 4: VERIFIED CLOSED); driver L263"),
 ("D3 month contract sourced by Bash", f"{C}/chain_lib.sh L25-165 data-grammar parser (except TRN-19); dryrun 407aa438 L27 load_month_env \"$SRC\""),
 ("D2 / AMENDMENT 3 member index dtype", f"{C}/v4_gate_step2_m.py d99a9109 L115-122 (kind in 'iu' before 1-D/range/unique)"),
 ("E-0909-A negative-index wrap in king features", f"{C}/pod_fea_ext_clamp.py L48, L55 np.maximum(E - w, 0)"),
 ("AMENDMENT 5 legs all-row recompute", f"{C}/pod_legs_v4b.py L43-49 (old rows verbatim, asserted); driver L210-216 (2023 king seat >= 0.4)"),
 ("E-0912-B test cells running real writers", f"{C}/tests_pipeline_gates.py L946 static rule (run_sandboxed)"),
 ("refit trained_through ambiguity (sidecar)", f"{C}/pod_f10_refit_v4.py L140-147 trained_through_label_utc / pool_end / tr1_end"),
 ("king bundle training-cutoff label", f"{C}/pod_export_bundle_v4.py L263-266 king_train_end_utc"),
]
