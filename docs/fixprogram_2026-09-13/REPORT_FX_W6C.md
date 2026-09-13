> **创建:** 2026-09-13 16:0xZ(lead 转录) | **Session:** FX-W6C(teammate fx-w6c)撰文 / lead 落盘 | **状态:** EXE-01 克隆内完成, **未部署**; ALM-02 / flow-day / 平仓行时间戳待续 | **作废条件:** 克隆分支任一提交被改写; 或 ef60f85 以外运行树被部署
> **落盘说明**: 子代理工具约定「以文本交回、不写报告文件」⇒ lead 逐字转录 FX-W6C 消息, 未改事实、数字或措辞(原文英文保留)。

# REPORT · FX-W6C · EXE-01 watchdog proportional response

EXE-01 done in the clone, NOT deployed.

## CHAIN (clone /Users/haosiyu/cc_tmp/fx_w6c, branch fix/exe01-proportional-response, base ef60f85)
- f0d4eac step 1: W6(c) verbatim (sha 15d29d99 verified; one hunk offset 28 in ops/gate_coverage.py). Its suites 50/50 + 43, rc 0. Kept only to show what was reviewed.
- f99dc80 step 2: response-level proportionality gate replacing W6(c)'s kind-specific partition.
- b3c5fc2 step 3: local response survives the next anchor; scan-battery regression; ledger ruler split.
- Stacked diff docs/receipts/fx_w6c.diff = git diff ef60f85 b3c5fc2 -- . ':!state': 15 files +1438 -15, 142,114 bytes, sha256 d4a6d1036309c7ec2491df774dc19b959706ab605ead9449c9cfbd8cf500f8b0.
- Research commits: 49fea5f2 (fact table + devices + receipts, before executor code), b750a5d4 (diff, scan battery, B14 red, fact table §11), ff77d8ed (final battery).

## WHAT IT DOES (fact table docs/fixprogram_2026-09-13/FX_W6C/FACT_TABLE_W6C.md)
- Each watchdog trigger carries a scope at its append site. §4-5b and §4-7 drift name reconcile.latest; §4-5e names unauth_names only when split_unauth's per-name clause alone fired. Every other trigger, including future ones, is book-level by absence.
- proportional_gate: ladder when the switch is off, any book-level trigger fired, a named trigger has no names, names > 5, or known doubt > 2% of anchors.target_gross (readback gross is the fallback only). Otherwise LOCAL, with every unknown named.
- Thresholds are code constants 5 / 0.02. The switch is config/book.json watchdog_proportional_response.enabled=true; missing or unreadable reads as ON.
- Local action: halt opening → cancel resting orders on the named names → flatten those names' WHOLE venue positions reduce-only from broker.positions(), re-read ×3, never another symbol, never the reduce-only key → exec recovery → rows (flatten_scope local) + readback → ALARM HIGH/CRITICAL.
- State kind proportional_local, book_flattened false, tripped_at set; a standing trip is never overwritten.
- reconcile doubt_usdt = |residual| or Σ|intended| over EVERY unquantifiable row of the name (review C9 closed by construction).
- Readers: run_anchor pages it off-box + local_response_receipt.json; assert_anchor_artifacts #7 covers it; resume_from_trip.sh and unseed refuse while it would fire; harvest_reset_required and resume keep the EMA for that kind.
- anchor_loop writes anchors.halt_kind=proportional_local for that halt only; position_break judges such a no-submission anchor as halted_book_held.
- tests_disposition_matrix splits local batches by the rows' column (68→71).
- watchdog.py names no anomaly kind, so the ef60f85 blind-spot pins hold verbatim.

## WHY WIDER THAN R-14's TEXT (to confirm with the reviewer)
- On the live record, 5 of 10 whole-book flattens were name-scoped, and 4 of those were two-name events at 0.42–1.84% of gross: 08-01 and 09-12 (our instruments), 08-21 and 08-26 (real two-name changes).
- W6(c)'s self-consistency criterion would have covered only 09-12.
- The local action flattens the whole named positions, so it never sizes from the doubted ledger.
- 09-09 stays LADDER (52 names > 5; the doubt sum 1.085% would have passed). Cell B12 asserts this on the receipt's name sets.

## RED → GREEN
- New suite on ef60f85: 15/54, rc=1, reached its summary line. The headline shows all 100 names flattened on a 1-name 0.3% anomaly. The 15 greens are ladder-expected neighbours plus controls.
- f99dc80: 56/56.
- B14 chain cells on f99dc80: 57/59, rc=1. The next halted anchor tripped via §4-5e flat_intent_legacy at 99% of gross.
- b3c5fc2: 59/59.
- Neighbours: names 4/5/6; 1,999/2,000/2,001 USDT of 100k; union 2+3 vs 3+3; §4-2 and §4-5a beside a named set; unknown doubt; unknown gross; readback fallback; known 2.5% beside an unknown; C9 swap; next anchor with vs without the marker.
- Negative controls: §4-2 day loss, §4-4b leverage, §4-5a outage and §4-5c account-side each flatten all 100 names with reduce-only set. Green on both trees.
- 09-12 replay on trip-time runtime 918559f: LOCAL, 2 names, doubt 1,524.32 = 0.6473% of 235,497.44.

## BATTERY
- Scan f99dc80 (15:14:11–15:33:42Z): "ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)", rc=1. Reds: env_loading (no .env); entrypoint_wiring (nosleep cell; the same FAIL on ef60f85 at 15:36Z); flatten_cancels_first (my regression: _local_response repeated the ladder's mutation-pinned source line; renamed in b3c5fc2).
- FINAL b3c5fc2 (tree 057449db, 15:40:46–15:57:55Z, head unchanged, 0 tracked changes, no .env): "ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)", battery rc=1. 136 rows, 135 rc 0; the only red is tests_env_loading (4 TELEGRAM-on-import cells). Not all green.

## FINDINGS FOR THE LEAD
1. The lead's premise "positions unreadable across the book reach the full ladder" is false on ef60f85, and unchanged here (probe + cell B13): no newest readback → not tripped and NOT blind (stale state); no readback at all → blind, and the resume gate refuses; NaN notionals → clean.
2. F-I6, not measured: an off-schedule run with a held book and no submission has the same flat-intent exposure. It could flatten the whole book.
3. F-I5, pre-existing: flatten rows and the post-flatten readback get different anchor_ts, so §4-5e never judges a flatten anchor.
4. W6(c) as written had the F-I1 next-anchor exposure too.

## NOT CHECKED
- venue behaviour of reduce-only market exits under -4400 / price protection
- off-box delivery (static pin only)
- resume/unseed end to end (network probe; refusal static, EMA snippet executed)
- a real DRY anchor writing halt_kind
- re-entry and halt tracking cost
- 2%/5 calibration (post-incident policy)

## DEPLOY NOTES
- Overlaps fx-exec on reconcile.py, assert_anchor_artifacts.py, gate_coverage.py, run_acceptance.sh (notice sent).
- book.json sha changes. Rollback = enabled:false (cell A7).
- First-anchor check: last_eval has proportional_response (route none) and local_responses []; phase_A watchdog_halt has state_kind; matrix 71/71.

## CLEANUP
fx_w6c_918559f, fx_w6c_f99 and the snapshot are deleted, and base's state is removed. fx_w6c_base (code only) is kept for the ALM-02 and flow-day red runs. ALM-02 is next: fact + red on ef60f85 already done (0/6, right reasons).
