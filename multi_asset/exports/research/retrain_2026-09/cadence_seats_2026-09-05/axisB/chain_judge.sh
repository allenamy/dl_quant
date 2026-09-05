#!/bin/bash
# chain_judge.sh — after the queue finishes: equivalence check of all 8 R0 artifacts, then the frozen judge. Detached via nohup.
cd /workspace/review_scratch/cadence_seats/axisB
until grep -q RUN_ALL_DONE logs/run_all.out 2>/dev/null; do sleep 20; done
echo "chain: queue done $(date -u +%FT%TZ)"
grep -c "^END" logs/commands.txt; grep "^END" logs/commands.txt | grep -vc "rc=0"
/workspace/venv/bin/python check_equiv.py > logs/check_equiv.log 2>&1; tail -1 logs/check_equiv.log
/workspace/venv/bin/python judge_axisB.py > logs/judge.log 2>&1; echo "judge rc=$?"; tail -1 logs/judge.log
echo "CHAIN_JUDGE_DONE $(date -u +%FT%TZ)"
