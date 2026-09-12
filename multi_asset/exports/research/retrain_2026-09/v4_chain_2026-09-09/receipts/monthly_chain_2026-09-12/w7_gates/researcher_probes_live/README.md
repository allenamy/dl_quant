> **创建:** 2026-09-12 | **Session:** W7 | **状态:** receipt | **作废条件:** 装置目录任一被引文件 sha 改变

The independent researcher's two probe scripts (codex_batch_incident_review_2026-09-12/retrain/probe_retrain_contracts.py, probe_w7.py; 13 + 8 cells) re-run by W7
against the LIVE device dir after B-R1/B-R3/B-R4/R5 (patched copies here: `C` points at the live dir; probe_w7 locates the [R] fixture functions by NAME
instead of line numbers). `as_expected` in these JSONs is judged against the researcher's ORIGINAL expectations, so `as_expected: false` == the cell FLIPPED.
Flipped by W7: W3_refit_subset_dispatches_without_upstream_receipts (True→False), W3_omitted_SEEDS_inherited_ACCEPTED (0→4), W3_CLIP_command_inherits_ambient_RAW_PATCH
('stale-inherited-patch'→ the researcher's mock loses PROBE_LOG under env -i and logs nothing; W7's own [S] cell shows DLWT_RAW_PATCH='' for the CLIP call),
W7_NONE_positive_without_any_builder_or_preflight_identity (PASS→REFUSED clamp_builder_identity), W7_entire_new_tail_NaN_still_PASS_boundary (PASS→FAIL; in the
researcher's env the refusal fires first for the missing pin — the tail_quality reason is shown in [S] with the pin present).
Flipped by W4 (concurrent judge_v4.py / v4_gate_common.py edits, NOT W7): W4_changed_receipt_extra_omitted_by_caller_ACCEPTED (True→False).
Unchanged: F9_* (5), W4_omitted/changed_static (2), W3_omitted_SEEDS_clean_env_rejected, W7_STEP1/STEP2_extension_positive, W7_NONE_changed_common_cell_negative
(still False, now via the refusal), W7_candidate_as_reference_negative, W7_real_contract_refuses_STEP1/STEP2_unapproved.
