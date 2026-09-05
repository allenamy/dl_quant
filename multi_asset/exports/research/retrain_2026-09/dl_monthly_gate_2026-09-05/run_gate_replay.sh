#!/bin/bash
# run_gate_replay.sh — dl_monthly_gate step 3/4: replay every arm series through the verified device in the health-check main-arm form
# (U-PIT · m1 · FTRIM zero · msharpe 900 · PHI 0.45 · live fee tiers · d30_n2_c42; prod caliber), FSEED=42 (monthly models exist for seed 42 only; the yearly
# baseline also with FSEED=2027 = BASE_s2027 from setup). PHIDYN arm (PREREG §A3): w10_seat2g.py PHIDYN=1 PHIDYN_CLIP=0.3,0.6 on the R1 series; plus the same
# device with PHIDYN=0 on the R1 series as its own equivalence receipt vs the w10_health R1 run.   usage: bash run_gate_replay.sh
G=/workspace/review_scratch/dl_monthly_gate; R=$G/replay; H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python; cd $R || exit 2
SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for TAG in mE1 mE60; do for ARM in R0 R1 R2 R3 R4; do
  [ -f dev_alt/f8_2026-08-22/preds/f10_gate_${TAG}_${ARM}_s42.npy ] || { echo "missing series $TAG $ARM"; exit 3; }
  bash run_arm.sh G_${TAG}_${ARM} prod w10_health.py $COMMON FPRED=f10_gate_${TAG}_${ARM}_s42.npy > logs/G_${TAG}_${ARM}.out 2>&1 &
done; done
bash run_arm.sh G_mE1_R1_phidyn prod w10_seat2g.py $COMMON FPRED=f10_gate_mE1_R1_s42.npy PHIDYN=1 PHIDYN_CLIP=0.3,0.6 > logs/G_mE1_R1_phidyn.out 2>&1 &
bash run_arm.sh G_mE1_R1_seat2def prod w10_seat2g.py $COMMON FPRED=f10_gate_mE1_R1_s42.npy PHIDYN=0 > logs/G_mE1_R1_seat2def.out 2>&1 &
bash run_arm.sh G_mE1_R0_phidyn prod w10_seat2g.py $COMMON FPRED=f10_gate_mE1_R0_s42.npy PHIDYN=1 PHIDYN_CLIP=0.3,0.6 > logs/G_mE1_R0_phidyn.out 2>&1 &
wait
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_G_mE1_R1_seat2def.npz dev_alt/probe_artifacts/w10_ablation_series_G_mE1_R1.npz "w10_seat2g PHIDYN=0 on the R1 series vs w10_health R1" >> logs/check_equiv.log 2>&1; echo "EQ4 rc=$?" >> logs/eq_chain.log
tail -1 logs/check_equiv.log | cut -c1-200
sha256sum dev_alt/probe_artifacts/w10_ablation_series_*.npz dev_alt/f8_2026-08-22/preds/f10_gate_*.npy >> logs/replay_sha256.txt
echo "REPLAY_DONE $(date -u +%FT%TZ)" >> logs/replay_chain.log; grep -c "END\[" logs/commands.txt
