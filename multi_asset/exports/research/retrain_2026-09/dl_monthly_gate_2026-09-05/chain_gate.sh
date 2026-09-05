#!/bin/bash
# chain_gate.sh — dl_monthly_gate full chain: setup+equivalence (CPU) ‖ inference re-derivation (GPU, inference only) → simulate mE1/mE60 → replay arms → judge → render → sha manifest
G=/workspace/review_scratch/dl_monthly_gate; PY=/workspace/venv/bin/python; cd $G || exit 2
echo "CHAIN START $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) other_train_procs=$(pgrep -f pod_f10_train | grep -vc $$)" >> logs/commands.txt
echo "CMD[setup] $(date -u +%FT%TZ): bash setup_gate.sh" >> logs/commands.txt; bash setup_gate.sh > logs/setup_gate.log 2>&1 & SP=$!
echo "CMD[infer] $(date -u +%FT%TZ): TAGS=mE1,mE60 $PY infer_fold_models.py (GPU inference only)" >> logs/commands.txt; TAGS=mE1,mE60 $PY infer_fold_models.py > logs/infer_fold_models.log 2>&1; echo "END[infer] rc=$? $(date -u +%FT%TZ) $(tail -1 logs/infer_fold_models.log | cut -c1-160)" >> logs/commands.txt
wait $SP; echo "END[setup] rc=$? $(date -u +%FT%TZ) $(cat replay/logs/eq_chain.log | tr "\n" " ")" >> logs/commands.txt
for T in mE1 mE60; do echo "CMD[simulate $T] $(date -u +%FT%TZ): $PY simulate_gates.py $T" >> logs/commands.txt; $PY simulate_gates.py $T > logs/simulate_$T.log 2>&1; echo "END[simulate $T] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt; done
echo "CMD[replay] $(date -u +%FT%TZ): bash run_gate_replay.sh" >> logs/commands.txt; bash run_gate_replay.sh > logs/run_gate_replay.log 2>&1; echo "END[replay] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt
echo "CMD[judge] $(date -u +%FT%TZ): $PY judge_gate.py" >> logs/commands.txt; $PY judge_gate.py > logs/judge_gate.log 2>&1; echo "END[judge] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt
$PY render_gate_report.py > logs/render.log 2>&1; echo "END[render] rc=$? $(date -u +%FT%TZ)" >> logs/commands.txt
sha256sum *.py *.sh preds_model_manifest.json results/*.json series/*.npy preds_model/*.npz replay/w10_health.py replay/w10_seat2g.py replay/w10_seat2_orig.py replay/dev_alt/f8_2026-08-22/preds/f10_gate_*.npy replay/dev_alt/probe_artifacts/*.npz REPORT_tables.md > SHA256SUMS.txt 2>/dev/null
echo "CHAIN DONE $(date -u +%FT%TZ)" >> logs/commands.txt
