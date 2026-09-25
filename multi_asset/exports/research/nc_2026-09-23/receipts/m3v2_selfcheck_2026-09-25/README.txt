nc_m3_selfcheck.py v2 update (B7 v2 gate (0), b80f52b39) — tests on a live v1 anchor (2026-09-25T00Z, 1790294400), read-only, 2026-09-25T04:40Z.
Commands (verbatim; cwd = multi_asset/exports/research/nc_2026-09-23/devices; S = scratchpad selfcheck_v2test):
  ~/wide_shadow/venv/bin/python -B nc_m3_selfcheck.py ~/cc_tmp/nc_20260923/package_NC 1790294400 --expect-version m3_beta_v1 --out $S/v1_1790294400.txt > /dev/null 2>&1; echo "v1-mode rc=$?"   → v1-mode rc=0
  ~/wide_shadow/venv/bin/python -B nc_m3_selfcheck.py ~/cc_tmp/nc_20260923/package_NC 1790294400 --out $S/v2_1790294400.txt > /dev/null 2>&1; echo "v2-mode rc=$?"   → v2-mode rc=3
GREEN (expect v1 on a v1 anchor): M3_SELFCHECK 1790294400 OK n=0 — incl. the new plan-row closures c1/c2/c3 (β_exec rebuilt from orders.jsonl
  target_w × book_gross reproduces the record exactly) and the (ii) tolerance inputs.
RED (expect v2 on a v1 anchor): MISMATCH n=5 — the four version assertions, plus "betas bit-identical" (7 names differ: the published v1
  betas were computed on the clipped storage, the v2 recompute reads rr — the ret5 defect itself). The version gate cannot pass on v1 objects.
