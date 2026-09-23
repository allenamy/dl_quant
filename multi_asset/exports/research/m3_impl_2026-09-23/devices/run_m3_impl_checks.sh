#!/bin/bash
# M3 production implementation — the checks behind docs/IMPL_m3_beta_overlay_2026-09-23.md, VERBATIM as run on 2026-09-23 (Mac).
# Executor checkout: ~/cc_tmp/m3_impl_20260923/exec (branch m3-beta-overlay, commits 8725e7d + 11aa8d1 + c71ca7a + 4dd7d53 + 80ae104
# + b81c4cb + 5b3d89c, base b66257b, NOT pushed). Steps 1-8 ran on 4dd7d53; 80ae104 changes two comments only (run_c5_textual.sh);
# b81c4cb/5b3d89c = the round-10 review fixes (steps 11-14). The deliverable patch (step 9) is b66257b..5b3d89c.
# Producer copy:     ~/cc_tmp/m3_impl_20260923/producer_copy (excludes: ../PRODUCER_COPY_EXCLUDES.txt).
# Heavy steps (full battery, producer rehearsal) only in the quiet window [N+1:00, N+3:40] UTC.
set -u
M3=$HOME/cc_tmp/m3_impl_20260923
P=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_impl_2026-09-23

# 1. new executor suite (125 checks)
( cd $M3/exec && /usr/bin/python3 live/tests_beta_overlay.py > ../receipts/tests_beta_overlay_run10.log 2>&1; echo EXIT=$? )

# 2. producer suite (synthetic + read-only real cache + REQUIRED pair with the executor validator)
( cd $M3 && PYTHONDONTWRITEBYTECODE=1 M3_EXECUTOR_ROOT=$PWD/exec M3_REAL_ROLLING=$HOME/wide_shadow/state/rolling.npz \
    M3_REAL_SYMS=$PWD/producer_copy/fea171/xfer_syms.npz M3_REAL_UNIVERSE=$HOME/wide_shadow/state/target_live/1790150400.json \
    ~/wide_shadow/venv/bin/python producer_copy/fea171/tests_beta_overlay_producer.py > receipts/TESTS_BETA_OVERLAY_PRODUCER.log 2>&1; echo "EXIT=$?" )

# 3. strip receipt: every M3 insertion removed == b66257b blobs byte for byte
/usr/bin/python3 $P/devices/m3_strip_receipt.py $M3/exec b66257b $M3/receipts/M3_STRIP_RECEIPT_b66257b.json; echo "STRIP_EXIT=$?"

# 4. producer rehearsal in the parity sandbox (08Z anchor 1790150400): modified combo_stage vs the archived production target
( cd $M3 && M3_PRODUCER_COPY=$PWD/producer_copy DL_QUANT_LIVE_ROOT=$PWD/exec nice -n 10 \
    bash producer_copy/fea171/combosnap_m3/combo_parity_replay.sh 1790150400 $PWD/receipts/M3_PRODUCER_REHEARSAL_1790150400.json $PWD/parity_sb \
    > $PWD/receipts/M3_PRODUCER_REHEARSAL_1790150400.log 2>&1; echo "REPLAY_EXIT=$?" >> $PWD/receipts/M3_PRODUCER_REHEARSAL_1790150400.log )
#    expected: PARITY_MISMATCH why=['beta_overlay: present only in replay'], weights n_differing 0, max_abs_dw 0.0 (REPLAY_EXIT=2)

# 5. targeted existing suites: branch vs pristine b66257b worktree (git -C $M3/exec worktree add ../exec_base b66257b)
bash $M3/targeted/run_targeted.sh run2 > $M3/targeted/run2_summary.txt 2>&1

# 6. disk-mode independence sweep (off / shadow / on written into the clone's config, restored byte-identical)
bash $M3/targeted/disk_mode_sweep_v4.sh > $M3/targeted/disk_sweep_v4_summary.txt 2>&1

# 7. full offline battery (live state copied first; kernel sandbox; the same runner safe_commit uses)
rsync -a --exclude='/acceptance/' --exclude='quarantine/' --exclude='__pycache__/' --exclude='/pycache_void/' \
      --exclude='/*.log' --exclude='/*.out' --exclude='/anchor.lock' ~/dl_quant_live/state/ $M3/exec/state/
( cd $M3/exec && bash ops/run_acceptance_offline.sh > ../receipts/OFFLINE_BATTERY_4dd7d53.log 2>&1; echo "OFFLINE_EXIT=$?" >> ../receipts/OFFLINE_BATTERY_4dd7d53.log )

# 8. the 20260922 producer release's own unittest modules, re-run with the M3 combo_stage swapped in (base = unchanged copy)
#    (copies under the session scratchpad: relcheck/base = ops/producer_release/20260922, relcheck/m3 = same + M3 combo_stage.py
#     + beta_overlay_producer.py)
# for tree in base m3; do for t in tests_combo_publication_boundary tests_producer_publication tests_combo_runtime_roots \
#     tests_combo_daemon_deadline tests_producer_observability tests_producer_generation tests_producer_input_parity \
#     tests_feature_cache_identity; do ( cd relcheck/$tree && /usr/bin/env -i PATH=/usr/bin:/bin HOME=$HOME PYTHONDONTWRITEBYTECODE=1 \
#     TMPDIR=<scratch> ~/wide_shadow/venv/bin/python -m unittest -q $t ); done; done

# 9. the deliverable patch (= git diff b66257b 5b3d89c) and its fresh-clone check (tree must equal 5b3d89c^{tree})
( cd $M3/exec && git diff b66257b 5b3d89c > $P/executor_m3_b66257b.patch && shasum -a 256 $P/executor_m3_b66257b.patch \
  && git diff --name-only b66257b 5b3d89c | while read f; do printf "%s  %s\n" "$(git show "5b3d89c:$f" | shasum -a 256 | cut -d' ' -f1)" "$f"; done > $P/EXECUTOR_FILES_SHA256.txt )
V=$M3/verify_5b3d89c; rm -rf "$V"; git clone -q ~/dl_quant_live "$V"; git -C "$V" remote set-url origin https://github.com/allenamy/dl_quant_live.git
git -C "$V" checkout -q b66257b && git -C "$V" apply --check "$P/executor_m3_b66257b.patch" && git -C "$V" apply "$P/executor_m3_b66257b.patch" && echo APPLY_OK
( cd "$V" && shasum -a 256 -c "$P/EXECUTOR_FILES_SHA256.txt" | awk '{print $2}' | sort | uniq -c )     # 18 OK
git -C "$V" add -A && echo "clone_tree=$(git -C "$V" write-tree) branch_tree=$(git -C $M3/exec rev-parse '5b3d89c^{tree}')"   # equal
#    negative control: a stray non-M3 edit in a stripped file must turn the receipt DIFFERENT (exit 1), then restore
/usr/bin/python3 $P/devices/m3_strip_receipt.py "$V" b66257b "$V/../M3_STRIP_RECEIPT_verify_5b3d89c.json"; echo "STRIP_EXIT=$?"

# 10. commit 80ae104 (comment-only): compiled-code identity + the source-text suites (NOT tests_acceptance_entrypoints)
#     ⚠ HISTORICAL, DO NOT RE-RUN AS IS: it runs single executor suites outside ops/run_acceptance_offline.sh, which E-0923-D
#     now forbids (every executor suite, single ones included, only through the offline runner). Kept verbatim as the record.
bash $P/devices/run_c5_textual.sh > $M3/receipts/c5_summary.txt 2>&1

# 11. round-10 counterexamples (R10-A01 leverage, R10-A02 frozen net) on the pre-fix and the fixed module (pure module only)
for v in 80ae104 b81c4cb; do git -C $M3/exec show $v:live/beta_overlay.py > $M3/receipts/r10/beta_overlay_$v.py
  env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 $P/devices/r10_counterexamples.py $M3/receipts/r10/beta_overlay_$v.py $v \
    > $M3/receipts/r10/R10_COUNTEREXAMPLES_$v.log 2>&1; echo "EXIT=$?" >> $M3/receipts/r10/R10_COUNTEREXAMPLES_$v.log; done   # 80ae104 exit 1, b81c4cb exit 0

# 12. the leverage budget decision table (numbers read from the commit's config / watchdog source)
/usr/bin/python3 $P/devices/leverage_budget_table.py $M3/exec b81c4cb $M3/receipts/r10/LEVERAGE_BUDGET_TABLE_b81c4cb.json

# 13. full offline battery on the final commit (ONLY through ops/run_acceptance_offline.sh — E-0923-D; quiet window; state copied first)
rsync -a --exclude='/acceptance/' --exclude='quarantine/' --exclude='__pycache__/' --exclude='/pycache_void/' \
      --exclude='/*.log' --exclude='/*.out' --exclude='/anchor.lock' ~/dl_quant_live/state/ $M3/exec/state/
( cd $M3/exec && bash ops/run_acceptance_offline.sh > ../receipts/OFFLINE_BATTERY_5b3d89c.log 2>&1; echo "OFFLINE_EXIT=$?" >> ../receipts/OFFLINE_BATTERY_5b3d89c.log )

# 14. beta parity (R10 A.4-5): see $P/beta_parity/RUN_COMMANDS.sh (pod2 for the certified table; a COPY of the producer cache locally)
