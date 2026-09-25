Gate 3' (nc_v2_nonbeta_gate.py) — runs of 2026-09-25, 05:00Z quiet window.
run 1 (armed background task; device 3db67fca as committed in 4f8529505):
  OUT=~/cc_tmp/nc_20260923/v2gate_$(date -u +%Y%m%dT%H%MZ); ~/wide_shadow/venv/bin/python ~/cc_tmp/nc_20260923/src/nc_v2_nonbeta_gate.py ~/cc_tmp/nc_20260923/treeNC5 ~/cc_tmp/nc_20260923/treeNC6 $OUT > $OUT.log 2>&1
  → started 05:00:03Z · "gate rc=1 05:01:26" · NO verdict line: the comparator crashed on the first anchor (1790236800) at dlw_targets.npz key
    `members` (object array of ragged index arrays; np.array_equal → "truth value of an array ... ambiguous"). INSTRUMENT defect, not a reading.
    Log: run1_v2gate_20260925T0500Z_CRASHED.log.
fix (this commit): arr_eq = bitwise raw-bytes comparison (NaN payload and -0.0 count), object arrays element by element; comparator self-test
  (9 cases: 3 identical must pass, 6 planted differences must be caught) runs first and refuses the gate if wrong. Criterion UNCHANGED:
  every array of the three mini files, meta_json included, must be bitwise equal. NEW report-only field: when meta_json differs, the differing
  JSON fields are listed by name with both values (does not change the verdict).
Measured on run 1's already-built sandboxes of anchor 1790236800 with the fixed comparator (before rerun): dlw_targets.npz identical;
  dlw_fea82.npz and f8_fea89.npz differ ONLY in meta_json (X, pair_a, pair_s, names identical): fields self_sha256 (the feature device files
  changed by the v2 edits), cache_sha256 (the mini cache file: v2 writes ch0 = NaN by design) and, in f8, fea82_sha256 (sha of the dlw file,
  which differs through its meta_json). Under the literal criterion this anchor therefore FAILS; whether provenance-only meta differences are
  acceptable is the lead's ruling, not mine.
