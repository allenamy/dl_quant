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
run 2 (fixed comparator 7797a334; 05:03:17–05:11:25Z; OUT=~/cc_tmp/nc_20260923/v2gate_20260925T0503Z, same command as run 1):
  → ARR_EQ_SELFTEST cases=9 wrong=0 [] · NC_V2_NONBETA_GATE FAIL anchors=6 · gate rc=1. On all 6 anchors: target_combo / state_H_kc / state_H_fc /
    dlw_targets identical, target_live non-beta keys differing [] (written_utc excluded by the code), dlw_fea82 / f8_fea89 differ only in meta_json.
REVISION 1 (lead rulings ~05:10Z and ~05:15Z, w1) — nc_v2_nonbeta_gate_rev1.py, committed BEFORE judging run 2's sandboxes: closed meta_json
  exclusions {self_sha256, cache_sha256, f8 fea82_sha256}, each mapped to its v2 change; mini cache equal except v2 ch0 all NaN; every other
  field / array / target_combo bytes / target_live non-beta key bitwise, plus ONE closed target_live exclusion `written_utc` (well-formed UTC
  inside that sandbox's run window); ch0 AST census over the executed code (T1 whitelist); two verdict lines (FAIL_LITERAL/PASS_LITERAL and REV1).
  Declaration ≠ implementation found: the gate code (4f8529505) excluded written_utc while its docstring said "every key except beta_overlay";
  docstring corrected in this commit (code unchanged in behaviour).
REV1 judgement (commit 30de22823 rule; 05:14:04Z):
  cd devices; ~/wide_shadow/venv/bin/python -B nc_v2_nonbeta_gate_rev1.py ~/cc_tmp/nc_20260923/treeNC5 ~/cc_tmp/nc_20260923/treeNC6 ~/cc_tmp/nc_20260923/v2gate_20260925T0503Z ../receipts/m3v2_gate3prime_2026-09-25/NC_V2_NONBETA_GATE_REV1.json > ../receipts/m3v2_gate3prime_2026-09-25/rev1_stdout.log 2>&1; echo "rev1 rc=$?"
  → rev1 rc=1 · items 1/2 PASS on all 6 anchors (literal FAIL, rev1 PASS per anchor) · item 3 FAIL:
    "item3 ch0 census over 16 executed files: 14 channel-0 subscripts, non-whitelisted 2
     [('fea171/combo_stage_t3c_candidate.py', '_r5 = RD[:, _jb, 0].astype(np.float64)', 55), ('fea171/sidecar_blend.py', '_r5 = RD[:, _jb, 0].astype(np.float64)', 52)]"
  → NC_V2_NONBETA_GATE FAIL_LITERAL anchors=6 · NC_V2_NONBETA_GATE_REV1 FAIL anchors=6 written_utc_ruling=w1 out_sha256=ef2feb2d…
  Facts gathered AFTER the verdict (not changing it): both files are stale copies of the pre-v2 combo code (sidecar_blend.py 08-26, "combo_stage =
  sidecar_blend full text + combo"; combo_stage_t3c_candidate.py 09-04); sidecar_blend reads rolling.npz `data` (the clipped float16 storage)
  directly, i.e. it IS the ret5 defect class; it is run only by fea171/sidecar_daemon.sh, which is not running (no process; last log line
  "ran for 1790222400.json rc=0 Thu Sep 24 04:21:07 UTC 2026"); no launchd service or script references either file (launchd: combolive →
  combo_live_daemon.sh, shadowloop → shadow_loop_v3.py, combosnap, comboparity); target_blend is read by nothing in dl_quant_live.
  My own defect exposed by this: test_m3_v2_ret5.py T1 censused only the files of the v2 TREE (the changed files), not the producer's full
  fea171 as installed — an instance-shaped census; rev1's wider scope caught what T1 could not.
Lead ruling k1 (~05:16Z): not k2 (whitelisting after seeing data = changing the criterion). (1) at the v2 two-sided deploy, move
fea171/sidecar_blend.py, fea171/combo_stage_t3c_candidate.py, fea171/sidecar_daemon.sh into an archive directory inside the producer tree
(not deleted), after a reference census (imports / scripts / launchd plists / cron / launch commands in docs), receipts committed; (2) gate 3'
REVISION 2 = census scope of T1 and rev1 becomes "the producer's full installed code set + the tree overlay" (with my self-reported defect:
T1's scope was instance-shaped), re-judged in the deploy sandbox with the moved layout before deploying; (3) ret5-class note: sidecar_blend
reads the clipped ch0; its last run was 2026-09-24 04:21Z (before the NC release), the daemon has been stopped since, so NC-era live trading
is unaffected (also recorded in docs/ERROR_LEDGER_2026-08-20.md under E-0924-B).
