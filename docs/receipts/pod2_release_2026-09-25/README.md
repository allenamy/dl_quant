> **创建:** 2026-09-25 04:55Z | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **状态:** 释放收据(lead 裁定 04:5xZ: 本轮 /workspace 只释放 lead_tamper_check) | **作废条件:** 无(历史收据)

# pod2 release 2026-09-25 — /workspace/lead_tamper_check

Owner: lead (2026-09-20 tamper-check fixture, C0–C5). Receipts of that check are already in the repo
(`baseline_tables_2026-09-19/receipts/pod2/receipts/BT_GATE_TAMPER_TEST.json`; FP3 `tamper_battery.py` builds its own fixture and can rerun).
Before deletion: no process had it open (ps / fd scan 04:45Z); 93 files, 3,116,760,000-ish bytes (du 3,002 MiB).

Archived here BEFORE deletion:
- `lead_tamper_check_SHA256SUMS.txt` (sha256 1a05a381…): sha256 of all 93 files (pod2, `find . -type f -print0 | sort -z | xargs -0 sha256sum`).
- `lead_tamper_check_small_files/`: the 56 files < 1000 KiB (NEWGATE_*.json/log, cfg_*.json, AGG/PATH *.json), via tgz sha256 1ea98b3a…;
  each extracted file re-verified against the manifest on the Mac: ok=56 bad=0.
- NOT archived (sha only): 37 files ≥ 1000 KiB — price_tampered.npy (2,945,569,768 B), ledger_tampered.npz (56,625,076 B), 35 AGG/PATH *.npz.

Commands (verbatim):
  ssh pod2 'mkdir -p /root/release_20260925 && cd /workspace/lead_tamper_check && date -u +%T && nice -n 10 find . -type f -print0 | sort -z | xargs -0 nice -n 10 sha256sum > /root/release_20260925/lead_tamper_check_SHA256SUMS.txt; echo "sha rc=$?"; …'   → sha rc=0, 93 lines
  ssh pod2 'cd /workspace/lead_tamper_check && find . -type f -size -1000k -print0 | sort -z | tar --null -T - -czf /root/release_20260925/lead_tamper_check_small_files.tgz; …'   → tar rc=0, 56 entries
  (first tar attempt used `-size -1M`, which find rounds up to whole MiB ⇒ matched only empty files ⇒ 0 entries; caught by the entry count, redone)
  scp -q pod2:/root/release_20260925/lead_tamper_check_SHA256SUMS.txt pod2:/root/release_20260925/lead_tamper_check_small_files.tgz <here>/ ; tar -xzf … ; per-file sha check → ok=56 bad=0

## Deletion and measured result
  ssh pod2 'date -u +%T; ls -d /workspace/lead_tamper_check && …; rm -rf /workspace/lead_tamper_check; echo "rm rc=$?"; ls -d /workspace/lead_tamper_check 2>&1'
    → 04:54:22 · rm rc=0 · "No such file or directory". Released: 3,002 MiB (du -B1M at 04:50Z), 93 files.
  Quota probe (/root/release_20260925/quota_probe.py on pod2: 1 GiB os.urandom written in 16 MiB chunks with md5 while writing, fsync,
  re-read md5, then removed):
  ssh pod2 '… nice -n 10 /workspace/venv/bin/python -B quota_probe.py /workspace/.c4_quota_probe_20260925.bin 1073741824; echo "probe rc=$?"'
    → QUOTA_PROBE path=/workspace/.c4_quota_probe_20260925.bin requested=1073741824 written_by_writer=1073741824 write_error=None
      size_on_disk=1073741824 md5_written=20056f3c6ba89115536800eeffb582ac md5_readback=20056f3c6ba89115536800eeffb582ac OK=True secs=7.1
    → probe removed: True · probe rc=0
  Reading: ≥ 1 GiB writable without truncation after the release (measured). "≈ 3 GiB free" = dlarch's earlier 128 MiB + 3,002 MiB
  (INFERRED, not probed — a larger probe would compete with dlarch's writes). No pre-release probe of my own.

# /dev/shm/nc_2026-09-23 — KEPT (lead ruling (a1), 2026-09-25 ~04:57Z)
The five nc_prep products in work/ (axes, cache_crypto, R_crypto, boundary, fund_state) are the old-axis bitwise regression reference of
the live-parity extension (DESIGN_live_parity_binance_vision_2026-09-24 §2 L61–66); news2's ladder devices also point NC_W here.
Kept in place; manifest of all 324 files taken 04:56:17Z on pod2 (`find . -type f -print0 | sort -z | xargs -0 nice -n 10 sha256sum`,
sha rc=0) → `nc_2026-09-23_SHA256SUMS.txt`. The five reference files:
  ec7723c4… work/axes.npz · 7d22ca41… work/cache_crypto.npy · 16458cab… work/R_crypto.npy · 2e487eb5… work/boundary.npz · a12a8ed3… work/fund_state.npz
  (plus 3c886a2b… work/NC_FEATURES.npz and 9bc9adaf… work/members_hist_all.npz, 3-way hardlinks with news2 / pnoise).

# /dev/shm/ovn_2026-09-23/runs — RELEASED (lead ruling ~07:0xZ: news2 and fresh checked by reference path, not by name; neither queued task reads it)
Before deletion: 1386 files, 7263 MB (`du -sm`); sha256 of every file → `ovn_runs_SHA256SUMS.txt` (sha a2abd37b…), taken 07:04:47–07:05:08Z on pod2
(`cd /dev/shm/ovn_2026-09-23 && nice -n 10 find runs -type f -print0 | sort -z | xargs -0 nice -n 10 sha256sum`, sha rc=0).
No process had it open or as cwd (fd / cwd scan). The rest of ovn_2026-09-23 (receipts 44M, targets 115M, scratch) is NOT touched.
Deleted 07:05:35Z: `rm -rf /dev/shm/ovn_2026-09-23/runs` → rm rc=0, path gone. Measured (cgroup memory.stat / df -B1M /dev/shm):
| | before (07:04:47Z) | after (07:05:38Z) | released |
|---|---|---|---|
| cgroup shmem | 28,159,365,120 B | 20,543,676,416 B | 7,615,688,704 B (7.09 GiB) |
| /dev/shm used | 26,840 MiB (94%) | 19,577 MiB (69%) | 7,263 MiB |
| /dev/shm free | 1,772 MiB | 9,035 MiB | |
