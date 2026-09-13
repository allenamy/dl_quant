> **创建:** 2026-09-13 09:3xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker T6) | **状态:** lead 告警(pod2 /workspace 配额 08:02:2xZ–08:03:1xZ 触顶, EDQUOT 写失败 / rc=120 静默退出)后的 T6 复核收据 | **作废条件:** 下列任一 sha 与 T6/SHA256SUMS 不符

# T6 · pod2 quota-window recheck

## What T6 wrote on pod2 around the window
| object | written (UTC) | state |
|---|---|---|
| `T6/devices/t6_inventory.py` | 07:44:29 | before window; sha `1b975ae0…` equal pod2 = local |
| `T6/receipts/INVENTORY_pod2.json` | 07:53:46 | before window; run printed SUMMARY, rc=0; sha `575f2413…` equal pod2 = local |
| `T6/devices/_scratch_tscheck.py` (exploratory ts-coverage check of 7 records) | scp right after the local copy was written at 08:03:56Z (local mtime); lead's audit places the pod2 write inside the quota window | run at the time printed all 11 expected lines and `rc=0`; wrote no output file; **deleted by T6 at 08:57Z** (`rm -f` in the pass-2 launch) |
| `T6/devices/t6_inventory_pass2.py`, `T6/receipts/INVENTORY_pass2_pod2.json` | 08:57:40 / 08:58:26 | after window; SUMMARY printed, rc=0; sha equal pod2 = local |
| `T6/FAMILY_T6.json`, `devices/t6_extract.py`, `receipts/T6_SERIES_s42.npz`, `T6_SERIES_s2027.npz`, `RECEIPT_T6_extract.json` | 09:13:22–09:13:39 | after window; SUMMARY printed, rc=0; sha equal pod2 = local |

No other T6 file on pod2 has an mtime in 08:00–08:05Z (`find … -printf %T`, 09:32:41Z).

## Re-creation and re-run of the scratch check (09:33:54Z)
- Free-space probe first: `dd bs=1M count=1 conv=fsync` into `T6/receipts/.ddprobe` → `dd_rc=0`, probe removed.
- Re-created `T6/devices/_scratch_tscheck.py` from the local scratchpad copy: sha256 `bece3baee02eef97aa0edbfbf8e2292bceacfacce17073457a28beb7ccad6b1d` on the Mac and on pod2.
- Re-run under `env -i PATH HOME LC_CTYPE`, `nice -n 10`, CPU (`nvidia-smi` 0 % / 2 MiB before and after): **rc=0** (`receipts/RECHECK_tscheck_rerun_rc.txt`), stderr **0 lines**, stdout 11 lines, sha256 `35d1d20f857dc541fa92590dedb6669c62f9a1e882ca321c2e168f5b5f1cef61`.
- The 08:04Z stdout, transcribed verbatim from the session transcript into `receipts/RECHECK_tscheck_original_stdout_0804Z.txt`, has the same sha256 `35d1d20f…`. `cmp` reports the files byte-identical.
- Independent cross-check against the later pass-2 receipt (08:58Z): W_FULL-missing counts 0 / 2422 / 1 / 11 / 0 / 1 / 1 for R8_P05_s42 / R8_S00_s42 / R4B1_XIB_fix_s42 / R5_BSLOPE_LAG / C2_N_s42 / SA_OIV / LAD_XIB_k021_s42 all agree (C2_N_s42's single missing anchor 2026-08-31 00Z lies after W_FULL). The scratch check only informed rule R3 (FAMILY_T6.md §2); every R3 decision in `FAMILY_T6.json` comes from pass-2, not from the scratch check.

## Input integrity through the window
- Pass-2 (08:57–08:58Z) opened all 1,280 v4-caliber record files with 0 errors.
- Extraction (09:13Z) asserted `sha256(file) == inventory sha (07:44–07:53Z)` for every one of the 221 canonical member files, and GATE-X re-hashed every member's g series. GATE-0 reproduced 8/8 published A0 numbers. None of this fails if an input had been truncated or rewritten in the window; all of it passed.

## Memory and exit codes
- cgroup `memory.max` read on pod2: 60,999,999,488 bytes. T6's largest in-memory objects on pod2 were ~12 MB (inventory JSON, 10,038 × 147 float64 matrix). Heavy computation ran on the Mac.
- No T6 run exited with rc=120 or silently: every pod2 and local run printed its SUMMARY line and rc=0.

## Second hazard found during this recheck: Mac-side silent empty reads (09:36–09:40Z)
- While writing this receipt, `shasum -a 256 … > SHA256SUMS` on the Mac stalled for more than 2 minutes and recorded **sha256(empty) = `e3b0c442…`** for `FAMILY_T6.json`, `receipts/T6_SERIES_s42.npz` and `receipts/T6_SERIES_s2027.npz`, with no error. The chained `shasum -c` then reported 2 of 29 entries not matching, and the command still exited 0 because a later command in the chain succeeded.
- Cause (observed, not assumed): the Mac data volume was **98 % full** (`df`: 466 Gi, 13 Gi free), and `ls -lO` showed six recently written T6 files flagged **`compressed,dataless`** (content evicted from local disk by the file provider behind `~/Desktop`). A read of a dataless file either blocks while it materializes or, as here, returns 0 bytes. At the same moment another worker's `shasum` on `docs/receipts/w2_readers_three_bucket.diff` had been stuck for 59 s.
- After materialization (`ls -lO` no longer shows `dataless`), every T6 file was re-hashed with `devices/t6_sha_guard.py`. That device refuses a file that is flagged dataless or whose bytes read differ from `st_size`. Results: `SUMMARY t6_sha_guard write n=30` rc=0 and `check n=30 mismatches=0` rc=0. The re-hashes equal the git blobs in HEAD `516c5ad2` for every committed file, and equal pod2 for the npz, inventory, extraction receipt, devices and re-run receipts. No committed T6 artifact is affected; only the uncommitted, interrupted `SHA256SUMS` was wrong, and it has been rewritten by the guard.
- Implication for any Mac-side receipt: a hash equal to `e3b0c442…` for a non-empty file, or a `shasum -c` "OK" computed during eviction, is not evidence. Hash only after checking `st_flags` and bytes-read == `st_size`.
