C package step 1 (2026-09-25 06:4xZ). Commands (verbatim; cwd devices/, env NEWS2_WIDE=~/cc_tmp/news_20260923/producer_copy — the pre-NC producer copy treeNC6 was built from):
  ~/wide_shadow/venv/bin/python -B nc_derive_producer.py ~/cc_tmp/nc_20260923/treeNC6_regress --release --m3-v2   → rc=0; every output == treeNC6 (bitwise)
  ~/wide_shadow/venv/bin/python -B nc_derive_producer.py ~/cc_tmp/nc_20260923/treeNC7 --release --m3-v2 --durable → rc=0; shadow_loop 52baf979, combo_stage 12a76de8, + durable_io 34da08f8; others == treeNC6
  ~/wide_shadow/venv/bin/python -B test_c_durable_producer.py ~/cc_tmp/nc_20260923/treeNC6 ~/cc_tmp/nc_20260923/treeNC7 → TEST_C_DURABLE_PRODUCER PASS 17/17
    (P0 baseline equal bytes/arrays; P1 red controls: base atomic_write / _save_npz silent + damaged under truncate / empty, raise under enospc (measured);
     P2 durable raises DurableWriteError, target intact, no temp left, all three modes; P3 AST routing guard)
