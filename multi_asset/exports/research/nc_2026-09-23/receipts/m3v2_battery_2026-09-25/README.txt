Executor full battery on the isolated M3 v2 clone ~/cc_tmp/m3v2_exec_20260925 (local commit dd486af on 5d3029c, NOT pushed), 2026-09-25 05:16–05:34Z.
Command (verbatim): zsh <scratchpad>/run_battery_m3v2.sh > <scratchpad>/run_battery_m3v2.out 2>&1   (script copied here; asserts HEAD dd486af + no tracked
  modification, rsync of ~/dl_quant_live/state/ with the A4 excludes, then `bash ops/run_acceptance_offline.sh` in the clone)
  → rsync rc=0 05:16:16 · battery rc=1 05:34:17 · "ACCEPTANCE: NOT GREEN" · OFFLINE_ACCEPTANCE_EXIT: 1 · 158 suites listed
  → the only non-zero suite: tests_disposition_matrix = 1 (two ★★★ assertions on ledger fact A1790267040 = 2026-09-24T16:24Z, the halted anchor of the STG
    trip that executed under the user's "16Z reduce only" ruling: 1 submit / 1 fill, terminal vocabulary incl. partial_expired). tests_beta_overlay = 0.
  → dd486af vs 5d3029c touches only live/beta_overlay.py, live/tests_beta_overlay.py, ops/producer_release/20260925_m3v2/*; the red suite imports
    order_disposition / pilot_log / reconcile (unchanged). Baseline battery on a 5d3029c worktree with the same state copy: see baseline file when done.
BASELINE (same tree state): 5d3029c worktree ~/cc_tmp/m3v2_exec_base_5d3029c (git worktree add at 5d3029c), state rsynced FROM THE V2 CLONE's state/ with the A4
  excludes (05:34:55–59Z) so both runs read the same ledger; `bash ops/run_acceptance_offline.sh` → baseline battery rc=1 06:10:22 · NOT GREEN ·
  OFFLINE_ACCEPTANCE_EXIT: 1 · 158 suites · the only non-zero suite: tests_disposition_matrix = 1 (same two ★★★ assertions, same ledger fact A1790267040).
  Per-suite exit table base vs v2: IDENTICAL on all 158 suites; disposition_matrix OK/FAIL lines identical ⇒ the red is a ledger fact, independent of M3 v2.
  (baseline run was blocked ~17 min in tests_drift_gate: ops/check_upstream_drift.py reading an iCloud placeholder of the research repo; passed once delivered.)
v2 + B (clone HEAD 6cc11cc = dd486af + a777f86 B-2 + 742706c B-5 + 263f782 re-vendor + 6cc11cc B-1), same state copy (05:16Z rsync), 06:35–06:53Z:
  `bash ops/run_acceptance_offline.sh` → B battery rc=1 06:53:38 · NOT GREEN · 160 suites · non-zero: drift_gate = 1, tests_drift_gate = 1 (its
  "states its DENOMINATOR" cell runs the guard on the real upstream) — BOTH from the vendored-upstream patch being HELD (E-0925-D): the research repo's
  engine/live is still the pre-B-2 bytes while the clone's manifest expects 8bde2f8dc. Proof: the clone's guard against the STAGED upstream (the six files
  extracted from 8bde2f8dc) → "no drift across 6 vendored modules (declared A-set 6, all covered)" rc=0. tests_disposition_matrix = 0 now (B-1),
  tests_durable_io = 0, tests_beta_overlay = 0. Logs archived at ~/cc_tmp/battery_logs_archive/m3v2B_6cc11cc_20260925T0635Z/.
