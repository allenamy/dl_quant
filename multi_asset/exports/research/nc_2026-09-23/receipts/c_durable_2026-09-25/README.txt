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
E3 timing, treeNC6 vs treeNC7 (same 6 anchors 1790121600..1790193600 as the NC5 E3, same inputs --fetch-measured 36.72 --backfill-measured 14.5
--backfill-k 10, seed pack 600d760e), 07:09–07:31Z:
  cd devices; for T in treeNC6 treeNC7: ~/wide_shadow/venv/bin/python -B nc_timing_gate.py ~/cc_tmp/nc_20260923/$T <out> --seed-pack ~/cc_tmp/nc_20260923/seed_pack_0919.npz --anchors 1790121600,...,1790193600 --fetch-measured 36.72 --backfill-measured 14.5 --backfill-k 10
  → both NC_TIMING_GATE PASS (7/7 runs ok). The durable increment, measured (p50 / max over the 6 ordinary anchors):
     state_save    NC6 4.947 / 5.327 s  → NC7 5.102 / 5.410 s   (+0.155 s p50; rolling.npz 78 MB built in memory, fsync, read back)
     target_write  NC6 0.006 / 0.008 s  → NC7 0.041 / 0.065 s   (+0.035 s p50; fsync + read-back of the signed target + sidecar)
     producer total NC6 6.74 / 7.66 s   → NC7 6.99 / 7.77 s     (+0.26 s p50)
     combo wall    NC6 39.11 / 41.40 s  → NC7 38.74 / 39.79 s   (difference inside run-to-run noise)
     gate slack (combo done vs N+19:35)  NC6 105.6 s → NC7 107.2 s (worst-backfill slack likewise); the increment is ~0.3 s of ~106 s.
Release / rollback ORDER rehearsal (lead review of DEPLOY_v2_durable §3), 07:4xZ:
  /usr/bin/python3 -B devices/test_release_order_drift.py ~/cc_tmp/m3v2_exec_20260925 5d3029c 6cc11cc 8bde2f8dc ~/Desktop/quant_research <R>/RELEASE_ORDER_DRIFT.json → rc=0
  O1 old guard vs unpatched upstream rc=0 "no drift across 5" · O2 old guard vs PATCHED rc=1 DRIFT (rollback in the wrong order blocks itself)
  N1 new guard vs patched rc=0 "no drift across 6" · N2 new guard vs UNPATCHED rc=1 DRIFT (forward in the wrong order)  ⇒ RELEASE_ORDER_DRIFT PASS
