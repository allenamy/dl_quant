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
