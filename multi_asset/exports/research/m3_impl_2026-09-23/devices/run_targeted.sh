#!/bin/bash
# Targeted suites on the M3 branch AND on the pristine b66257b worktree (same interpreter, same env). Exit codes read directly (no pipes).
set -u
M3=$HOME/cc_tmp/m3_impl_20260923
OUT=$M3/targeted/$1; mkdir -p "$OUT"
SUITES="live/tests_external_book.py live/tests_signal_and_loop.py live/tests_book_reshape.py live/tests_venue_cap_clamp.py live/tests_binance_executor.py live/tests_chase_experiment_wiring.py live/tests_chase_policy.py live/tests_watchdog.py live/tests_neutrality_check.py live/tests_neutrality_price.py live/tests_imports.py live/tests_static_names.py ops/gate_coverage.py ops/guard_reach.py live/tests_guard_reach.py live/tests_per_name_stop.py live/tests_proportional_response.py live/tests_orphan_position.py live/tests_readers_three_bucket.py live/tests_offschedule_held_book.py live/tests_book_observability.py live/tests_reduce_only_clamp.py live/tests_exit_ledger.py live/tests_gross_ladder_retired.py live/tests_arm_margin_scope.py live/tests_request_identity_unknown.py live/tests_transport_resilience.py live/tests_topup_leg_fill.py live/tests_reject_topup.py live/tests_flatten_ladder.py live/tests_beta_overlay.py"
for tree in exec_base exec; do
  for s in $SUITES; do
    [ -f "$M3/$tree/$s" ] || { echo "$tree $s ABSENT"; continue; }
    log="$OUT/${tree}__$(echo $s | tr / _).log"
    ( cd "$M3/$tree/$(dirname $s)" && /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=$HOME LIVE_MODE=DRY_RUN PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 nice -n 10 /usr/bin/python3 "$(basename $s)" ) > "$log" 2>&1
    echo "$tree $s EXIT=$?"
  done
done
