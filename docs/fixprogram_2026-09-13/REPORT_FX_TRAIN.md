> **创建:** 2026-09-13 15:1xZ | **Session:** FX-TRAIN (fix worker, team-lead dispatch; session b9646a9e) | **状态:** 执行中 — one section per item, appended as each item's commit chain lands; independent review pending for every section | **作废条件:** a cited commit is reverted, or a cited file's sha changes without a new section here

# REPORT_FX_TRAIN — October retrain chain fixes (AUDIT_TRAIN 7e1ecf9a)

Fact table: `docs/fixprogram_2026-09-13/FX_TRAIN/FACT_TABLE_TRN.md` (sections are committed before the code of the item they describe).
Device dir: `C/` = `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`. Chain test logs: `C/receipts/fx_train_2026-09-13/`. Fact-table devices and pod2 receipts: `docs/fixprogram_2026-09-13/FX_TRAIN/{devices,receipts}/`.
Method for every code item: pre-fix source archived beside the current one as `<name>.r<N>_<sha8>.<ext>`; a new test block runs pre-fix (RED) and fixed (GREEN) on the same input in one run; the block is also run standalone against a pristine copy of the pre-fix directory to show the red is for the right reason; full suite re-run; `fx_ast_retention.py` proves every old top-level test statement is retained verbatim and in order.

Baseline (before any FX-TRAIN change): pristine copy of C/ at the audited shas (111 files, 0 mismatches vs `receipts_train/SHA256SUMS_v4_chain_dir.txt`) — `tests_pipeline_gates.py` a3af858d **ALL PASS (392 checks), rc 0**, 14:43:08Z-14:50:50Z (`C/receipts/fx_train_2026-09-13/baseline/baseline_tests_392.log`). A first attempt without the parent file `T/pod_export_bundle_v3.py` failed the [H] exporter-regeneration cell on a missing fixture (FileNotFoundError); kept as `baseline_tests_attempt1_missing_parent_v3.log`, not a finding.

---

## TRN-19 — bare parser output line exported as `R=R` (+ sibling: the dryrun negative control trusted its interpreter's rc 0)

**Problem.** `load_month_env` re-validates the parser's output in bash after rc 0, but splits each line with `${line%%=*}` / `${line#*=}`; a line with no `=` gives key == value == the line, so a bare `R` passed every check and was exported as `R=R` (FACT_TABLE 19.1-19.7). Needs a broken or substituted `$PY` (the real parser always prints `KEY=VALUE`). The red run found a sibling in the same family: the dryrun negative control (a) used the derivation program's rc 0 as the only evidence that every derived path lies under its empty root, and (b) used its receipt program's rc 0 as its verdict without checking the receipt exists (FACT_TABLE 19.8-19.9).

**Fix.**
- `C/chain_lib.sh` 4ee217e1 → 1add6df7: one guard before the split — `case $line in *=*) ;; *) … die month_env_parser_output_<file> 4 ;; esac`. Nothing else in the loader changed.
- `C/chain_v4_monthly_dryrun.sh` 407aa438 → 1d6ae66a: (a) after derivation, bash (no interpreter) re-checks every derived line: KEY=VALUE, a registered key exactly once, all keys present, `R == <scratch>/root`, `PY ==` the chosen interpreter, every non-label key under `<scratch>/root/`; any violation ⇒ rc 2, driver not run; (b) rc 0 of the receipt program counts only if `dryrun_receipt.json` exists and says `"PASS": true`, else rc 1.
- Pre-fix sources archived: `C/chain_lib.r3_4ee217e1.sh`, `C/chain_v4_monthly_dryrun.r3_407aa438.sh` (bytes = the committed pre-fix versions; the [V] block asserts both shas).

**Tests.** New block [V] TRN-19 in `C/tests_pipeline_gates.py` (14 cells; every cell runs pre-fix and fixed on the same input):
- V1 (reviewer's exact probe) stub interpreter prints 45 valid lines + bare `R` ⇒ pre-fix rc 0, MONTH_ENV_OK, `R=R`; fixed rc 4 `FAIL_month_env_parser_output`, names the missing `=`, no MONTH_ENV_OK.
- Neighbours: bare `SEEDS` (pre-fix rc 0 `SEEDS=SEEDS`; fixed rc 4); 46 lines + bare unregistered word (both rc 4; fixed names the missing `=`); 46 lines + `=R` (both rc 4, character-class check unchanged).
- Positives: a stub printing exactly the true 46 lines ⇒ both rc 0 with the identical exported environment; the real parser on the September contract and the October template ⇒ both rc 0, identical environment.
- Inheritor: the dryrun with the bare-R interpreter ⇒ fixed rc 2 before any driver run.
- Static: the `*=*` guard is the code line immediately before the only split.
- Sibling V9: interpreter prints a contract whose paths point below a never-created foreign root as the "derived env" ⇒ pre-fix dryrun ran the DRIVER against it and exited rc 0; fixed rc 2 `derived env REFUSED` naming R, driver not run. V10: interpreter exits 0 from the receipt program without writing a receipt ⇒ pre-fix rc 0 with no receipt; fixed rc 1. Positive: the real interpreter ⇒ both dryruns DRYRUN_PASS rc 0.
- No cell can write anywhere real: every stub path lies below a temp dir that is never created (E-0912-B rule); the one real-interpreter dryrun derives its env under a temp root.

**Red evidence (for the right reason).** The [V] block run standalone against a pristine pre-fix copy (both "old" and "current" = pre-fix): **7 FAIL / 7 OK**, rc 1 — V1/V2 fail because the loader accepts the bare key (rc 0), V3 because the refusal names the unregistered key, not the missing `=`, V7/V9 because the dryrun exits rc 0 and runs the driver, V10 because it exits rc 0 with no receipt, V8 because the guard line does not exist; the snapshot, setup, `=R` and positive cells pass. No crash, no missing fixture (`V_trn19_on_PRE_fix_RED.log`). Same on pod2 (bash 5.1.16): 7 FAIL / 14 (`V_trn19_pod2_pre.log`).

**Green.** Block on the fixed sources: **ALL PASS (14)** on the Mac (bash 3.2) and on pod2 (bash 5.1.16) (`V_trn19_on_FIXED_GREEN.log`, `V_trn19_pod2_fixed.log`). Full suite on the fixed copy: **ALL PASS (406 checks) = 392 + 14, rc 0**, 14:57:59Z-15:04:53Z, source shas identical at start and end (tests 31cd958c…, chain_lib 1add6df7…, dryrun 1d6ae66a…) (`tests_full_trn19_fixed.log`). AST retention vs a3af858d: 174/174 old top-level statements retained verbatim and in order, 0 changed, 7 added (`ast_retention_trn19.json`).

**Positive control on real data.** Not applicable beyond the positive cells: the change touches only the parser-output re-validation and the negative control; both delivered contracts load to the identical environment under pre-fix and fixed sources, and the real-interpreter dryrun passes unchanged.

**Not proven / boundary.**
- An interpreter that lies consistently (returns a well-formed foreign contract to the driver's own `load_month_env` and exits 0 from every gate program) can still direct the driver at arbitrary paths; no bash-level check removes that. Interpreter identity is not pinned anywhere in the chain (preflight records `PY` by path only).
- Not exercised by a real month run through the driver (none is possible before the October inputs exist).
