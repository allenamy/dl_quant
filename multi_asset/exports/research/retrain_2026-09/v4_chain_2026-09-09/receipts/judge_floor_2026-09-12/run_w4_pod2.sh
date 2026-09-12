#!/bin/bash
# W4 judge-floor 11->28 control on pod2, CPU only (DESIGN_judge_floor_28_2026-09-12.md §2 D6: three cells + old code red).
# Isolated under /workspace/uplift_2026-09-11/w4_judge_floor/; reads the frozen review_scratch HC and the applied infra2/v4chain copy, writes neither.
# Cells, all on the SAME real A1 v2 receipt and the SAME 28-name entry built from its inputs_path:
#   old_full28          archived v4_gate_common (7b6d49a3, floor 11) + all 28 declared      -> expected ELIGIBLE, "registered floor BUNDLE_export=11"
#   old_omit_slowpred   archived common + bundle/slow_pred_pinned.npy left undeclared       -> expected STILL ELIGIBLE (the defect: old code red)
#   new_full28          round-6 common (floor 28) + all 28 declared                          -> expected ELIGIBLE, floor=28, 28 inputs verified, 0 PROMOTE (A1 is (C))
#   new_omit_slowpred   round-6 common + bundle/slow_pred_pinned.npy left undeclared         -> expected NOT eligible ("omitted registered input(s)")
#   new_omit_contract   round-6 common + eligibility_contract left undeclared                -> expected NOT eligible
set -u
W=/workspace/uplift_2026-09-11/w4_judge_floor
SRC=/workspace/uplift_2026-09-11/infra2/v4chain
REC=/workspace/uplift_2026-09-11/r20_gate_closure/receipts/pod2_applied/BUNDLE_export_v2_A1_applied.json
HC=/workspace/review_scratch/health_check
PY=/workspace/venv/bin/python; $PY -c "import numpy" 2>/dev/null || PY=python3
mkdir -p $W/device_old $W/device_new $W/out
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $W/out/gpu_before.txt; date -u +%FT%TZ >> $W/out/gpu_before.txt
ps -o pid,etime,cmd -p 333197,339489 | cut -c1-140 > $W/out/pids_before.txt
cp $SRC/judge_v4.py $SRC/ELIGIBILITY_CONTRACT.json $SRC/v4_gate_common.py $W/device_old/
cp $SRC/judge_v4.py $SRC/ELIGIBILITY_CONTRACT.json $W/device_new/; cp $W/v4_gate_common.NEW.py $W/device_new/v4_gate_common.py
sha256sum $W/device_old/* $W/device_new/* $REC $W/v4_gate_common.NEW.py > $W/out/SHA256SUMS.txt
$PY - <<EOF
import json
r = json.load(open("$REC"))
full = {k: r["inputs_path"][k] for k in r["registered_inputs"]}   # all 28; the judge re-binds the 4 book_* to the same HC paths
json.dump({"A1": {"receipt": "$REC", "inputs": full}}, open("$W/ELIG_A1_full28.json", "w"), indent=1)
for tag, omit in (("slowpred", "bundle/slow_pred_pinned.npy"), ("contract", "eligibility_contract")):
    json.dump({"A1": {"receipt": "$REC", "inputs": {k: v for k, v in full.items() if k != omit}}}, open(f"$W/ELIG_A1_omit_{tag}.json", "w"), indent=1)
print("entries written; n_full =", len(full))
EOF
run(){ # name device elig
  echo "=== $1 ($2, $3) $(date -u +%FT%TZ)"
  ( cd $W && JUDGE_HC=$HC JUDGE_OUT=$W/out/JUDGE_$1.json JUDGE_ELIGIBILITY=$W/$3 $PY -B $W/$2/judge_v4.py > $W/out/judge_$1.log 2>&1; echo "rc=$?" >> $W/out/judge_$1.log )
  grep -E "^rc=|eligibility\[A1\]|^eligibility:" $W/out/judge_$1.log | cut -c1-420
}
run old_full28 device_old ELIG_A1_full28.json
run old_omit_slowpred device_old ELIG_A1_omit_slowpred.json
run new_full28 device_new ELIG_A1_full28.json
run new_omit_slowpred device_new ELIG_A1_omit_slowpred.json
run new_omit_contract device_new ELIG_A1_omit_contract.json
$PY - <<EOF
import json, glob, os
for p in sorted(glob.glob("$W/out/JUDGE_*.json")):
    j = json.load(open(p)); v = j["verdicts"]
    print(os.path.basename(p), "| eligible_arms", j["eligible_arms"], "| A1 ok", j["eligibility_by_arm"]["A1"]["ok"], "| n_verdicts", len(v),
          "| n_PROMOTE", sum(x == "(A) PROMOTE" for x in v.values()), "| A1-A0", v.get("A1-A0|dyn"), v.get("A1-A0|fix"), "| contract", j["contract"]["sha256"][:12])
EOF
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > $W/out/gpu_after.txt; date -u +%FT%TZ >> $W/out/gpu_after.txt
ps -o pid,etime,cmd -p 333197,339489 | cut -c1-140 > $W/out/pids_after.txt
$PY -V > $W/out/python_version.txt 2>&1; $PY -c "import numpy; print('numpy', numpy.__version__)" >> $W/out/python_version.txt
cat $W/out/gpu_before.txt $W/out/gpu_after.txt $W/out/python_version.txt
echo W4_DONE
