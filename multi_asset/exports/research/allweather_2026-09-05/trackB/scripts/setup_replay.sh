#!/bin/bash
# setup_replay.sh — Track B: replay layout = dl_monthly_gate/replay = health_check layout (prod caliber dev_alt), device w10_health.py copied bitwise from
# health_check, run_arm.sh re-rooted; equivalence receipts BASE_s42 / BASE_s2027 vs health_check M1_UPIT_prod_s{42,2027}_ccal (CPU).
# Read-only on every source; writes only under allweather_trackB/replay/.
set -e
B=/workspace/review_scratch/allweather_trackB; G=/workspace/review_scratch/dl_monthly_gate; H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python
R=$B/replay; mkdir -p $R/logs $R/results
cp $H/w10_health.py $R/w10_health.py; cp $G/replay/check_equiv.py $R/check_equiv.py
sed "s#^ROOT=/workspace/review_scratch/dl_monthly_gate/replay; PY=#ROOT=$R; PY=#" $G/replay/run_arm.sh > $R/run_arm.sh
grep -n "^ROOT=" $R/run_arm.sh
for v in dev_alt; do
  d=$R/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs $d/f8_2026-08-22/preds
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do ln -sfn /workspace/port_w10/pod_backup_2026-08-21/$f $d/pod_backup_2026-08-21/$f; done
  ln -sfn /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  ln -sfn /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy $d/f8_2026-08-22/preds/f10_V2MAIN_s42.npy
  ln -sfn /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy $d/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
done
echo "--- resolved targets vs health_check (must all be SAME)"
for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
  a=$(readlink -f $R/dev_alt/pod_backup_2026-08-21/$f); b=$(readlink -f $H/dev_alt/pod_backup_2026-08-21/$f); [ "$a" = "$b" ] && echo "SAME dev_alt/$f" || echo "DIFF dev_alt/$f mine=$a hc=$b"; done
sha256sum $R/w10_health.py $H/w10_health.py $R/check_equiv.py $H/masks/umask_UPIT.npz $H/calib/costb_fee_steady.json /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy /workspace/f8_ext/preds/f10_V2MAIN_s42.npy /workspace/f8_ext/preds/f10_V2MAIN_s2027.npy | tee $R/logs/setup_sha256.txt
echo "SETUP_DONE $(date -u +%FT%TZ)"
cd $R; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
bash run_arm.sh BASE_s42 prod w10_health.py $COMMON FSEED=42 > logs/BASE_s42.out 2>&1 &
bash run_arm.sh BASE_s2027 prod w10_health.py $COMMON FSEED=2027 > logs/BASE_s2027.out 2>&1 &
wait
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz $H/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz "trackB BASE_s42 vs health_check M1_UPIT_prod_s42_ccal" >> logs/check_equiv.log 2>&1; echo "EQ1 rc=$?" >> logs/eq_chain.log
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz $H/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_ccal.npz "trackB BASE_s2027 vs health_check M1_UPIT_prod_s2027_ccal" >> logs/check_equiv.log 2>&1; echo "EQ2 rc=$?" >> logs/eq_chain.log
cut -c1-220 logs/check_equiv.log; echo "EQ_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/eq_chain.log; cat logs/eq_chain.log
