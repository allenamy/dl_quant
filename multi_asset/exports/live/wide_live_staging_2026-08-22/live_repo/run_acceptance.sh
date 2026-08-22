#!/bin/bash
# dl_quant_live — the single machine-checkable green/red statement for this repo.
#
# RULES (inherited from a day of earning them the hard way):
#   - any claim "the suites are green" must cite THIS script's output; never assemble the claim
#     by hand from parts — a claim about the whole, assembled by hand, drifts;
#   - never read this script's exit code through a pipe (a pipe reports the pipe's exit code);
#   - this runner has been verified to GO RED (swap in a failing suite): a runner that has never
#     been seen failing is itself an unverified claim.
#
# NOT in this list (deliberately, with reasons — not silently):
#   tests_production_signature  depends on pilot_daily (the T+1 shadow reporter), which stays on
#                               the research/server side until the report layer is ported. The
#                               production path of THIS repo is anchor_loop, covered by
#                               tests_signal_and_loop. Add the ported suite when it exists.
set -uo pipefail

_SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# ★ INTERPRETER IS PINNED, and not to bare `python3`.
# This machine has three: /usr/local/bin/python3 (3.14.4, NO torch — and torch has no 3.14 wheels
# yet), /opt/anaconda3 (3.7.6, torch 1.4.0 — far too old), and /usr/bin/python3 (3.9.6, torch
# 2.2.2 + numpy 1.26.4 + pandas 2.3.3). Bare `python3` resolves to the 3.14 one, which cannot run
# inference at all. Nothing needed installing; the requirement was to stop picking the wrong one.
# ★ the battery must run on the code ON DISK. Without this it runs under the system-wide bytecode
# cache, where 37 stale entries for this repo were measured — so "16/16 green" could be green about
# code that is not what is checked out. See ops/pyenv.sh.
. "$_SELF/ops/pyenv.sh"
PY="${ACCEPT_PY:-/usr/bin/python3}"
# ★ RECURSION MARKER. `tests_acceptance_entrypoints` proves both doors reach one statement by
# EXECUTING both doors — so once that suite is itself in the list, the battery calls a suite that
# calls the battery, without bound (measured 2026-07-27: 12 nested runners before it was killed).
# The suite reads this to know it is already inside a run and must not spawn another. It is an
# export, not an argument, precisely so every descendant sees it however it is invoked.
export ACCEPTANCE_INNER=1
LOGDIR="$_SELF/state/acceptance"
mkdir -p "$LOGDIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

SUITES=(
  "tests_imports:$_SELF/live/tests_imports.py"
  "drift_gate:$_SELF/ops/check_upstream_drift.py"
  "tests_binance_broker:$_SELF/live/tests_binance_broker.py"
  "tests_binance_executor:$_SELF/live/tests_binance_executor.py"
  "tests_binance_funding:$_SELF/live/tests_binance_funding.py"
  "tests_watchdog:$_SELF/live/tests_watchdog.py"
  "tests_pilot_log:$_SELF/live/tests_pilot_log.py"
  "tests_signal_and_loop:$_SELF/live/tests_signal_and_loop.py"
  "tests_entrypoint_wiring:$_SELF/live/tests_entrypoint_wiring.py"
  "tests_telegram_notify:$_SELF/live/tests_telegram_notify.py"
  "tests_inference_parity:$_SELF/live/tests_inference_parity.py"
  "tests_panel_build:$_SELF/live/tests_panel_build.py"
  "tests_risk_budget:$_SELF/live/tests_risk_budget.py"
  "tests_harvest_ema:$_SELF/live/tests_harvest_ema.py"
  "tests_manifest_consistency:$_SELF/live/tests_manifest_consistency.py"
  "tests_channel_causality:$_SELF/live/tests_channel_causality.py"
  # ★ the only STATIC suite here. Added 2026-08-04 after a `NameError` ran on every anchor for 16h
  #   with this battery green throughout: the raise sat after the file write, a broad `except`
  #   caught it, and the log line it produced ("falling back to the existing preds file") was FALSE.
  #   A defect whose entire symptom is a log line has no behavioural signature — see that file's
  #   docstring. Requires pyflakes; a MISSING linter makes it RED, never skipped.
  "tests_static_names:$_SELF/live/tests_static_names.py"
  "tests_factor_health:$_SELF/live/tests_factor_health.py"
  "tests_state_root:$_SELF/live/tests_state_root.py"
  "tests_nosleep:$_SELF/live/tests_nosleep.py"
  "tests_venue_fills:$_SELF/live/tests_venue_fills.py"
  "tests_artifact_assertions:$_SELF/live/tests_artifact_assertions.py"
  "metrics_freeze:$_SELF/ops/check_metrics_freeze.py"
  "gate_coverage:$_SELF/ops/gate_coverage.py"
  # ── 2026-07-27 defect batch [a][b][c][d'][e][f][g][h][i][j]: the red->green evidence for the
  # batch has to live in the thing that makes the claim, not in a report someone typed.
  "tests_trip_page:$_SELF/live/tests_trip_page.py"
  "tests_topup_leg_fill:$_SELF/live/tests_topup_leg_fill.py"
  "tests_flatten_ladder:$_SELF/live/tests_flatten_ladder.py"
  "tests_readback_universe:$_SELF/live/tests_readback_universe.py"
  "tests_market_maxqty:$_SELF/live/tests_market_maxqty.py"
  "tests_flatten_rows:$_SELF/live/tests_flatten_rows.py"
  "tests_scoped_writes:$_SELF/live/tests_scoped_writes.py"
  "tests_m4_rowtype:$_SELF/live/tests_m4_rowtype.py"
  "tests_ghost_rows:$_SELF/live/tests_ghost_rows.py"
  # ★ the one-statement property must itself be IN the statement, or it is a claim about the
  # battery made from outside the battery — the exact shape this batch is repairing.
  "tests_drift_gate:$_SELF/live/tests_drift_gate.py"
  "tests_persistence_and_dust:$_SELF/live/tests_persistence_and_dust.py"
  "tests_read_failure_visibility:$_SELF/live/tests_read_failure_visibility.py"
  "tests_acceptance_entrypoints:$_SELF/live/tests_acceptance_entrypoints.py"
  # ── 2026-07-27 night batch: scorer subject selection / cond6 anchor granularity / venue error
  # classification / §2.5.9 rehearsal anchors. Same rule as the [a]-[j] batch above: the red->green
  # evidence lives in the thing that makes the claim.
  "tests_score_anchor_selection:$_SELF/live/tests_score_anchor_selection.py"
  "tests_cond6_eligibility:$_SELF/live/tests_cond6_eligibility.py"
  "tests_venue_error_classification:$_SELF/live/tests_venue_error_classification.py"
  "tests_rehearsal_anchor:$_SELF/live/tests_rehearsal_anchor.py"
  # B30: §4-5b/§4-7 compare positions, not prices. The suite replays the 2026-07-27T16:18:34Z
  # trip from the production rows, with the reverse control (a missing fill must still fire).
  "tests_reconcile_qty_caliber:$_SELF/live/tests_reconcile_qty_caliber.py"
  # B23/B24/B25 batch: funding pagination, the inter-anchor readback blind spot, and the
  # protective-flatten row spec.
  "tests_flatten_record:$_SELF/live/tests_flatten_record.py"
  "tests_fill_collection_gap:$_SELF/live/tests_fill_collection_gap.py"
  # B26b: the repair for what B26a detects — the executions are still in userTrades.
  "tests_fill_backfill:$_SELF/live/tests_fill_backfill.py"
  "tests_universe_guard:$_SELF/live/tests_universe_guard.py"
  # B27: the CENSUS of artifacts that decide a prediction, and the first reader MANIFEST ever had.
  "tests_frozen_inputs:$_SELF/live/tests_frozen_inputs.py"
  # B31: §4-2/§4-4 read the day's LAST equity snapshot — a once-per-day row is captured
  # before the day happens, and on 2026-07-28 it left both stop-losses blind for the day.
  "tests_nav_staleness:$_SELF/live/tests_nav_staleness.py"
  # B33: the order leg's `avg_fill_px` had no producer on the child-fill path, so a top-up that
  # filled normally became `execution_of_unknown_size` and tripped §4-5b/§4-7 (2026-07-28
  # 08:01:24Z). Producer fix; the suite carries its own mutation controls.
  "tests_avgpx_backfill:$_SELF/live/tests_avgpx_backfill.py"
  # B34: four guards that reported a number they could not have measured — §4-3 with no coverage
  # term, the emergency exit's fee summed with no counter, the markout backfill capped 3.8x under
  # supply and starving its older days, and a readable quantity with an unreadable amount folding
  # to 0.0 in the top-up's sizing input.
  "tests_guard_coverage:$_SELF/live/tests_guard_coverage.py"
  # §4-5e + the halted-but-holding blind spot: the eligibility predicate assumed HALTED => FLAT,
  # and 2026-07-27T00:01Z was halted while holding 21,424 USDT. Runs on the REAL ledger, read-only.
  "tests_position_break_blindspot:$_SELF/live/tests_position_break_blindspot.py"
  # the numerator of §4-2/§4-4: income paging + a truncated day is UNKNOWN, never a small loss.
  "tests_numerator_honesty:$_SELF/live/tests_numerator_honesty.py"
  # [R1] the cache-vs-venue notice pages for POSITION differences, not for price movement.
  "tests_reconcile_severity:$_SELF/live/tests_reconcile_severity.py"
  # [R2] fee_all_usdt was structurally True (2844/798/never False) and had zero consumers.
  "tests_fee_asset_detection:$_SELF/live/tests_fee_asset_detection.py"
  # [B27] the pinned union makes universe_guard a COLUMN-SET tripwire, not a rotation check.
  # The pin and the wording must land together, so one suite holds both.
  "tests_universe_tripwire:$_SELF/live/tests_universe_tripwire.py"
  # S batch (0C signal audit): the orphan-position hole, the frozen data frontier, and a
  # liveness floor that passed 4 of 6 dead heads.
  "tests_orphan_position:$_SELF/live/tests_orphan_position.py"
  "tests_frontier_staleness:$_SELF/live/tests_frontier_staleness.py"
  "tests_head_liveness:$_SELF/live/tests_head_liveness.py"
  # sizing policy: constant LEVERAGE replaces constant exposure; every limit that hung off the
  # old denominator moves with it, by a frequency-preserving restatement.
  "tests_sizing_policy:$_SELF/live/tests_sizing_policy.py"
  # [T1] the last cell of the write-back matrix: (top-up leg, AMOUNT). Found by a real trip.
  "tests_notional_backfill:$_SELF/live/tests_notional_backfill.py"
  # [T2] the third quota: raw requests per IP, which is the one that banned us at 12:00Z.
  "tests_request_budget:$_SELF/live/tests_request_budget.py"
  "tests_halt_evidence:$_SELF/live/tests_halt_evidence.py"
  "tests_threshold_roles:$_SELF/live/tests_threshold_roles.py"
  "tests_cond3_worst_selector:$_SELF/live/tests_cond3_worst_selector.py"
  "tests_halt_verdict_states:$_SELF/live/tests_halt_verdict_states.py"
  "tests_flatten_cancels_first:$_SELF/live/tests_flatten_cancels_first.py"
  "tests_stuck_position_ack:$_SELF/live/tests_stuck_position_ack.py"
  "tests_reprice_day:$_SELF/live/tests_reprice_day.py"
  "tests_alert_tiers_live:$_SELF/live/tests_alert_tiers_live.py"
  "tests_gap_observer:$_SELF/live/tests_gap_observer.py"
  "tests_live_install_ritual:$_SELF/live/tests_live_install_ritual.py"
  "tests_live_state_root:$_SELF/live/tests_live_state_root.py"
  "tests_setup_live_account:$_SELF/live/tests_setup_live_account.py"
  "tests_live_dry_pass:$_SELF/live/tests_live_dry_pass.py"
  "tests_stale_order_sweep:$_SELF/live/tests_stale_order_sweep.py"
  "tests_venue_rate_authority:$_SELF/live/tests_venue_rate_authority.py"
  "tests_filters_cache_per_mode:$_SELF/live/tests_filters_cache_per_mode.py"
  "tests_rate_backstop_window:$_SELF/live/tests_rate_backstop_window.py"
  "tests_alarm_redelivery:$_SELF/live/tests_alarm_redelivery.py"
  "tests_a2_withdrawal_gate:$_SELF/live/tests_a2_withdrawal_gate.py"
  "tests_readiness_filters_path:$_SELF/live/tests_readiness_filters_path.py"
  "tests_unseal_rehearsal_halt:$_SELF/live/tests_unseal_rehearsal_halt.py"
  "tests_cancel_ban_resilience:$_SELF/live/tests_cancel_ban_resilience.py"
  "tests_book_weights_effective:$_SELF/live/tests_book_weights_effective.py"
  "tests_request_accounting:$_SELF/live/tests_request_accounting.py"
  "tests_anchor_skip_visible:$_SELF/live/tests_anchor_skip_visible.py"
  "tests_env_loading:$_SELF/live/tests_env_loading.py"
  "tests_review_anchor_scoping:$_SELF/live/tests_review_anchor_scoping.py"
  "tests_param_encoding:$_SELF/live/tests_param_encoding.py"
  "tests_sheet_subject:$_SELF/live/tests_sheet_subject.py"
  "tests_fills_supersede:$_SELF/live/tests_fills_supersede.py"
  "tests_neutrality_check:$_SELF/live/tests_neutrality_check.py"
  "tests_book_reshape:$_SELF/live/tests_book_reshape.py"
  "tests_reduce_only_reject:$_SELF/live/tests_reduce_only_reject.py"
  "tests_neutrality_price:$_SELF/live/tests_neutrality_price.py"
  "tests_exit_ledger:$_SELF/live/tests_exit_ledger.py"
  "tests_ops_flag_safety:$_SELF/live/tests_ops_flag_safety.py"
  "tests_reject_topup:$_SELF/live/tests_reject_topup.py"
  "tests_disposition_matrix:$_SELF/live/tests_disposition_matrix.py"
  "tests_alarm_digest:$_SELF/live/tests_alarm_digest.py"
  "tests_redelivery_settles:$_SELF/live/tests_redelivery_settles.py"
  "tests_daily_summary:$_SELF/live/tests_daily_summary.py"
  # ★ TWO suites for one feature, deliberately. `chase_policy` proves the rule decides correctly
  #   given a residual set; `chase_experiment_wiring` proves topup() ever ASKS it and that a
  #   withheld name leaves a row. Every defect this repo has paid for lived in the second gap.
  "income_callers:$_SELF/ops/income_callers.py"
  "guard_reach:$_SELF/ops/guard_reach.py"
  "tests_guard_reach:$_SELF/live/tests_guard_reach.py"
  "tests_readout_gate:$_SELF/live/tests_readout_gate.py"
  "tests_break_decomposition:$_SELF/live/tests_break_decomposition.py"
  # B, wired 2026-08-03. TWO suites for one feature, deliberately and for the usual reason:
  # `break_split_gate` is the PRE-REGISTERED spec and proves `decide` decides correctly;
  # `break_split_wiring` proves anything ever ASKS it, that the answer reaches the halt, and that
  # the guard kept every class it was narrowed from. Every defect this repo has paid for lived in
  # the second gap.
  "tests_break_split_gate:$_SELF/live/tests_break_split_gate.py"
  "tests_break_split_wiring:$_SELF/live/tests_break_split_wiring.py"
  "tests_chase_release_check:$_SELF/live/tests_chase_release_check.py"
  "tests_residual_vector:$_SELF/live/tests_residual_vector.py"
  "tests_chase_policy:$_SELF/live/tests_chase_policy.py"
  "tests_chase_experiment_wiring:$_SELF/live/tests_chase_experiment_wiring.py"
  # king leg cadence 4h->8h (PROPOSAL_king_cadence_8h_2026-08-09, user ruling 2026-08-09).
  # ★ The list is EXPLICIT, not globbed — so a new suite that is not added here runs green in
  #   isolation and is never run by the battery. That happened to this very suite: it passed
  #   standalone while ACCEPTANCE reported 113/113 without it. A guard the battery does not run
  #   is not a guard.
  "tests_king_cadence:$_SELF/live/tests_king_cadence.py"
  # k 窗口 900->180 (PROPOSAL_k_window_shorten_2026-08-10, 用户授权 2026-08-10)
  "tests_k_window:$_SELF/live/tests_k_window.py"
  # 中性保持型免交易带 b=0.002 (PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)
  "tests_neutral_band:$_SELF/live/tests_neutral_band.py"
  # #55 逐锚实现 IC 监视器 (尺子审计最大结构缺口的补件, 与 α=0.05 深平滑同批)
  "tests_ic_monitor:$_SELF/live/tests_ic_monitor.py"
  # 场外死人开关 ping 守卫 (healthchecks, 用户提供 URL 2026-08-11; 无门版曾在电池 DRY 运行里发 ping)
  "tests_deadman_ping:$_SELF/live/tests_deadman_ping.py"
  "tests_per_name_stop:$_SELF/live/tests_per_name_stop.py"
  # ε-赌博机挂单深度实验 (PREREG f657efde, 用户批准 2026-08-12; 反事实唯一路径)
  "tests_placement_bandit:$_SELF/live/tests_placement_bandit.py"
  # ★ 守卫口径性质测试 (DESIGN_optimization_path_2026-08-21 §2.2; ERROR_LEDGER E-0821-A): 每个 §4 守卫量
  #   从账户真值手推 + 三性质(日切分/入金/未实现跨日)各带会红变异体 — 2026-08-21 12:16Z 误触发的结构性修复:
  #   五个套件曾用"盈亏列动 nav 不动"的夹具全绿地钉住错口径; 本套件的夹具全部由账户恒等式生成。
  "tests_guard_calibers:$_SELF/live/tests_guard_calibers.py"
  # ★ 外部书适配器 (DESIGN_wide_live_deployment_2026-08-22 §1/§3.2): 宽书签名目标文件 → 目标向量;
  #   读取/校验/换算/过滤/告警 + internal 逐位不变 + per_name_stop profile 切换; 每条有会红变异体。
  "tests_external_book:$_SELF/live/tests_external_book.py"
)

# ★ registration guard: every live/tests_*.py must appear above. Catches the omission that this
#   very line was added because of, instead of relying on whoever adds the next suite remembering.
#   Deliberate exclusions live HERE, each with its reason, so "not registered" and "registered
#   as excluded" are different states. tests_production_signature is the pre-existing one (see the
#   header, line 12): it depends on the pilot_daily T+1 reporter, which has not been ported.
_EXCLUDED=(
  "tests_production_signature"   # depends on pilot_daily (not ported) — header line 12
)
_missing_reg=""
for f in "$_SELF"/live/tests_*.py; do
  b="$(basename "$f" .py)"
  case " ${SUITES[*]} " in *"$b:"*) continue ;; esac
  case " ${_EXCLUDED[*]} " in *" $b "*) continue ;; esac
  _missing_reg="$_missing_reg $b"
done
if [ -n "$_missing_reg" ]; then
  echo "ACCEPTANCE: REFUSING — suite file(s) exist but are not registered:$_missing_reg"
  exit 1
fi

overall=0
printf '%-28s %-6s %s\n' "SUITE" "EXIT" "LOG"
printf '%s\n' "----------------------------------------------------------------"
for entry in "${SUITES[@]}"; do
  name="${entry%%:*}"; path="${entry#*:}"
  log="$LOGDIR/${STAMP}_${name}.log"
  if [ ! -f "$path" ]; then
    printf '%-28s %-6s %s\n' "$name" "MISSING" "$path"
    overall=1; continue
  fi
  ( cd "$(dirname "$path")" && "$PY" "$(basename "$path")" ) > "$log" 2>&1
  ec=$?
  printf '%-28s %-6s %s\n' "$name" "$ec" "$log"
  [ "$ec" -ne 0 ] && overall=1
done
printf '%s\n' "----------------------------------------------------------------"
if [ "$overall" -eq 0 ]; then
  echo "ACCEPTANCE: ALL GREEN (${#SUITES[@]}/${#SUITES[@]} suites exit 0)"
else
  echo "ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)"
fi
exit $overall
