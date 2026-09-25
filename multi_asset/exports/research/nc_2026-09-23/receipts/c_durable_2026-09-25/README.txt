C package step 1 (2026-09-25 06:4xZ). Commands (verbatim; cwd devices/, env NEWS2_WIDE=~/cc_tmp/news_20260923/producer_copy — the pre-NC producer copy treeNC6 was built from):
  ~/wide_shadow/venv/bin/python -B nc_derive_producer.py ~/cc_tmp/nc_20260923/treeNC6_regress --release --m3-v2   → rc=0; every output == treeNC6 (bitwise)
  ~/wide_shadow/venv/bin/python -B nc_derive_producer.py ~/cc_tmp/nc_20260923/treeNC7 --release --m3-v2 --durable → rc=0; shadow_loop 52baf979, combo_stage 12a76de8, + durable_io 34da08f8; others == treeNC6
  ~/wide_shadow/venv/bin/python -B test_c_durable_producer.py ~/cc_tmp/nc_20260923/treeNC6 ~/cc_tmp/nc_20260923/treeNC7 → TEST_C_DURABLE_PRODUCER PASS 17/17
    (P0 baseline equal bytes/arrays; P1 red controls: base atomic_write / _save_npz silent + damaged under truncate / empty, raise under enospc (measured);
     P2 durable raises DurableWriteError, target intact, no temp left, all three modes; P3 AST routing guard)
step 2 (06:5xZ): snapshot retention added to --durable: fea171/combosnap/snap_retention.py (8833da2c) + combo_state_snapshot.sh (0a0b8401; the find -mtime +21 rm -rf line replaced)
  + combosnap/combo_parity_replay.sh (7fa0881a; refuses RETENTION_TRIMMED snapshots by name), edits on the pinned production sources 58e58bd1 / d49cd834.
  Rebuild (same env): --release --m3-v2 → treeNC6_regress2 == treeNC6 on every source file (only treeNC6's stale __pycache__ differs);
  --release --m3-v2 --durable → treeNC7 (receipt + SHA256SUMS here). test_snap_retention 14/14 PASS (R6 red control: the former rule deletes aux.json
  and the small files); test_c_durable_producer re-run on the rebuilt treeNC7: PASS.
gate 3' treeNC6 (base) vs treeNC7 (v2 + durable), 06:54–07:03Z: `~/wide_shadow/venv/bin/python ~/cc_tmp/nc_20260923/src/nc_v2_nonbeta_gate.py ~/cc_tmp/nc_20260923/treeNC6 ~/cc_tmp/nc_20260923/treeNC7 /Users/haosiyu/cc_tmp/nc_20260923/v2gate_NC6vsNC7_20260925T0654Z`
  → gate rc=0 · ARR_EQ_SELFTEST 9/0 · NC_V2_NONBETA_GATE PASS anchors=6 — every compared output bitwise identical incl. meta_json (no provenance change),
    target_live non-beta keys differing [] (weights_sha included), betas differing 0 (v2 == v2). Key-output sha pairs listed; sandboxes deleted after.
