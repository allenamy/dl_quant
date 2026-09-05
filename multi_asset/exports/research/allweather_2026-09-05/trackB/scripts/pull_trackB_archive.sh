#!/bin/bash
# pull_trackB_archive.sh — copy every non-array Track B product from pod2 into the research archive and verify sha against the pod-side list.
set -e
A=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/allweather_2026-09-05/trackB
ssh pod2 'set -e; B=/workspace/review_scratch/allweather_trackB; T=/tmp/tbx; rm -rf $T; mkdir -p $T/fits $T/results $T/logs $T/logs/partial_20260905T1508 $T/replay/logs $T/replay/dev_alt/logs $T/replay/dev_alt/probe_summary $T/scripts $T/part0_verify
cd $B; cp f8_out/results/*.json $T/fits/; cp results/*.json results/*.md $T/results/; cp logs/*.log logs/*.out logs/commands.txt logs/commands.txt.raw_20260905T1640 logs/patch_sha256.txt logs/stage.log $T/logs/ 2>/dev/null || true; cp logs/partial_20260905T1508/* $T/logs/partial_20260905T1508/
cp replay/logs/* $T/replay/logs/; cp replay/dev_alt/logs/*.log $T/replay/dev_alt/logs/; cp replay/dev_alt/probe_artifacts/*.json $T/replay/dev_alt/probe_summary/
cp pod_f10_train_dro.py pod_f10_train_dro.rebuilt.py make_patch.py patch.diff launch_train.sh setup_replay.sh run_replay_arms.sh stage_preds.py identity_check.py leakcheck_yearly.py score_trackB.py judge_trackB.py check_shard_artifacts.py $T/scripts/; cp replay/w10_health.py replay/check_equiv.py replay/run_arm.sh $T/scripts/
cp part0_verify/* $T/part0_verify/ 2>/dev/null || true
sha256sum f8_out/preds/*.npy f8_out/partial_20260905T1508/*.npy replay/dev_alt/f8_2026-08-22/preds/f10_trackB_*.npy replay/dev_alt/probe_artifacts/w10_ablation_series_*.npz /workspace/f8_ext/preds/f10_V2MAIN_s42.npy /workspace/f8_ext/preds/f10_V2MAIN_s2027.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/pod_f10_train_ext.py pod_f10_train_dro.py replay/w10_health.py > $T/POD_SHA256SUMS_arrays_and_devices.txt
cd $T && find . -type f ! -name POD_SHA256SUMS_arrays_and_devices.txt | sort | xargs sha256sum > POD_SHA256SUMS_archived_files.txt && tar czf - .' | tar xzf - -C $A
cd $A; n_ok=0; n_bad=0; while read -r h p; do if [ -f "$p" ]; then [ "$(shasum -a 256 "$p" | cut -d' ' -f1)" = "$h" ] && n_ok=$((n_ok+1)) || { n_bad=$((n_bad+1)); echo "MISMATCH $p"; }; fi; done < POD_SHA256SUMS_archived_files.txt
echo "archived-vs-pod sha: ok=$n_ok mismatch=$n_bad (the list file itself is the expected 1 mismatch)"; find . -type f | wc -l; du -sh .
