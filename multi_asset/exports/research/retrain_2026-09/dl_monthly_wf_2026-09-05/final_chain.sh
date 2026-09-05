#!/bin/bash
# final_chain.sh — dl_monthly_wf: waits for both restarted trainers (END lines) and the RNG-replay receipt, then runs the FINAL analysis pass:
# verify_artifacts → stitch → replay arms (mE60 withbase, mE1) → ic → leakcheck → judge → render → sha256 manifest.  All CPU. nohup bash final_chain.sh &
R=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python; cd $R || exit 2
while [ "$(grep -cE 'END\[E60-restart\]|END\[E1-restart\]' logs/commands.txt)" -lt 2 ] || ! grep -q "REPLAY_CHECK " logs/commands.txt; do sleep 30; done
echo "FINAL START $(date -u +%FT%TZ): final analysis pass on 20/20 folds per variant (dry-run outputs overwritten)" | tee -a logs/commands.txt >> replay/logs/commands.txt
$PY verify_artifacts.py > logs/verify_final.log 2>&1; echo "VERIFY rc=$? $(tail -1 logs/verify_final.log)" >> logs/commands.txt
[ $(grep -c "VERIFY OK" logs/verify_final.log) -eq 1 ] || { echo "FINAL ABORT: verify failed $(date -u +%FT%TZ)" >> logs/commands.txt; exit 1; }
$PY stitch.py mE60 mE1 > logs/stitch_final.log 2>&1; echo "STITCH rc=$?" >> logs/commands.txt
bash run_replay.sh mE60 withbase > logs/run_replay_mE60_final.log 2>&1; bash run_replay.sh mE1 > logs/run_replay_mE1_final.log 2>&1
$PY ic_monthly.py mE60 mE1 > logs/ic_final.log 2>&1; echo "IC rc=$?" >> logs/commands.txt
$PY leakcheck_monthly.py mE60 mE1 > logs/leakcheck_final.log 2>&1; echo "LEAKCHECK rc=$? (3 = gate-literal FAIL, see log)" >> logs/commands.txt
$PY judge_dl.py mE60 mE1 > logs/judge_final.log 2>&1; echo "JUDGE rc=$?" >> logs/commands.txt
$PY render_report.py > logs/render_final.log 2>&1; echo "RENDER rc=$?" >> logs/commands.txt
sha256sum pod_f10_train_monthly.py monthly_section.py trainer.diff stitch.py ic_monthly.py leakcheck_monthly.py judge_dl.py render_report.py verify_artifacts.py run_replay.sh launch_variant.sh replay_check.sh final_chain.sh \
  preds/f10_V2MAIN_mE60_s42.npy preds/f10_V2MAIN_mE1_s42.npy results/f10_V2MAIN_mE60_s42.json results/f10_V2MAIN_mE1_s42.json models/*.pt models/*_config.json preds_fold/*.npz \
  replay/w10_health.py replay/dev_alt/f8_2026-08-22/preds/*.npy replay/dev_alt/probe_artifacts/*.npz replay/results/judge_dl.json logs/ic_mE60_mE1.json logs/leakcheck_mE60_mE1.json REPORT_tables.md > SHA256SUMS.txt 2>/dev/null
echo "FINAL DONE $(date -u +%FT%TZ)" >> logs/commands.txt
