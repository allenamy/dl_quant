#!/usr/bin/env python3
"""k2_materialize.py — the Mac data volume is ~98 % full and iCloud evicts Desktop files to APFS 'dataless' stubs (T6 rule, STATE 09:4xZ).
Before a hash-guarded run, ask iCloud to download every input (`brctl download`) and wait until no input carries the dataless flag.
Reads nothing itself; the consuming device still refuses any dataless or short read. Usage: python3 k2_materialize.py [timeout_s]"""
import os, sys, stat, glob, time, subprocess
SF = getattr(stat, "SF_DATALESS", 0x40000000)
REPO = "/Users/haosiyu/Desktop/quant_research"; RS = REPO + "/multi_asset/exports/research"; R2 = RS + "/uplift_r2_2026-09-13"; R3 = RS + "/uplift_r3_2026-09-13"
V4 = RS + "/retrain_2026-09/v4_chain_2026-09-09"; FX = REPO + "/docs/fixprogram_2026-09-13/FX_EVAL"
PATHS = (glob.glob(FX + "/*.py") + glob.glob(FX + "/*.json") + glob.glob(FX + "/*.md") + glob.glob(FX + "/*.txt") + glob.glob(RS + "/common/*.py")
         + [R2 + p for p in ("/T4/devices/t4_judge.py", "/T5c/devices/t5c_bridge.py", "/T5b/devices/t5b_q1.py", "/T5b/devices/t5b_exec.py", "/T5/devices/t5_addendum_h2b.py",
                             "/T2/devices/t2_judge.py", "/T1/devices/t1_judge.py", "/T8/devices/t8_judge.py", "/T5d/devices/t5d_bridge.py",
                             "/T4/receipts/RECEIPT_T4_judge.json", "/T2/receipts/RECEIPT_T2_judge.json", "/T5c/receipts/pod2/RECEIPT_T5c_bridge.json", "/T5d/receipts/pod2/RECEIPT_T5d_bridge.json",
                             "/T5b/receipts/RECEIPT_T5b_q1.json", "/T5b/receipts/RECEIPT_T5b_exec.json", "/T5/receipts/pod2/RECEIPT_T5_addendum1_h2b.json", "/T1/receipts/pod2/RECEIPT_T1_judge.json",
                             "/T8/receipts/pod2/RECEIPT_T8_judge.json", "/T8/receipts/pod2/RECEIPT_T8_fit.json", "/T8/receipts/pod2/RECEIPT_T8_build.json", "/T3/receipts/PASSIVE_REV.json")]
         + glob.glob(R2 + "/T8/receipts/pod2/RECEIPT_T8_null_*.json")
         + [RS + "/parity_replay_2026-09-12/phase2/devices/p2_s2_lib.py", RS + "/parity_replay_2026-09-12/devices/materiality_probe_v2.py", RS + "/parity_replay_2026-09-12/receipts/MATERIALITY_v2_dg_1788624000_1789200000.json",
            R3 + "/L2/devices/l2_b_common.py", R3 + "/L4/receipts/pod2/RECEIPT_L4_run.json", R3 + "/L4b/receipts/pod2/RECEIPT_L4b_marks.json", R3 + "/L4/RESULT_L4.md", R3 + "/L4b/RESULT_L4b.md",
            V4 + "/judge_v4.py"] + [V4 + "/receipts/" + f for f in ("JUDGE_v4.json", "JUDGE_v4_g3_s2027.json", "JUDGE_v4e_hardened.json", "JUDGE_v4e_informational.json")]
         + [REPO + "/docs/" + f for f in ("RESULT_v4_chain_retrain_quantify_2026-09-09.md", "STATUS_three_questions_2026-09-12.md", "RULINGS_requested_2026-09-12.md", "RUNBOOK_monthly_retrain_2026-10.md")])
timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
missing = [p for p in PATHS if not os.path.exists(p)]
if missing: print("MISSING", missing); sys.exit(2)
dl0 = [p for p in PATHS if os.stat(p).st_flags & SF]
for p in dl0: subprocess.run(["brctl", "download", p], capture_output=True)
t0 = time.time()
while True:
    dl = [p for p in PATHS if os.stat(p).st_flags & SF]
    if not dl or time.time() - t0 > timeout: break
    time.sleep(3)
print("SUMMARY k2_materialize inputs=%d dataless_at_start=%d still_dataless=%d waited=%.0fs %s" % (len(PATHS), len(dl0), len(dl), time.time() - t0, [os.path.relpath(p, REPO) for p in dl][:5]))
sys.exit(0 if not dl else 1)
