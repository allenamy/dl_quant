#!/bin/bash
# setup_gate.sh — dl_monthly_gate: replay layout (= dl_monthly_wf/replay = health_check layout), device copies (w10_health.py bitwise; w10_seat2.py from seat_round2
# with ONE patch: PHIDYN_CLIP readable from env, default unchanged), and the equivalence receipts (CPU). Read-only on every source; writes only under dl_monthly_gate/.
set -e
G=/workspace/review_scratch/dl_monthly_gate; H=/workspace/review_scratch/health_check; S2=/workspace/review_scratch/seat_round2; W=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python
R=$G/replay; mkdir -p $G/logs $G/results $G/series $G/preds_model $R/logs $R/results
cp $H/w10_health.py $R/w10_health.py; cp $S2/check_equiv.py $R/check_equiv.py; cp $S2/w10_seat2.py $R/w10_seat2_orig.py
sed "s#^ROOT=/workspace/review_scratch/health_check; PY=#ROOT=$R; PY=#" $H/run_arm.sh > $R/run_arm.sh
# seat2 copy: PHIDYN_CLIP from env (PREREG §A3 asks clip [0.30, 0.60]; seat_round2 hardcodes (0.2, 0.8)); default path unchanged
sed 's#^PHIDYN_LOOK = 900; PHIDYN_CLIP = (0.2, 0.8)#PHIDYN_LOOK = 900; PHIDYN_CLIP = tuple(float(_x) for _x in os.environ.get("PHIDYN_CLIP", "0.2,0.8").split(","))   \# dl_monthly_gate: clip from env (default = seat_round2 value)#' $S2/w10_seat2.py > $R/w10_seat2g.py
echo "--- diff seat2 orig vs gate copy (expected: the PHIDYN_CLIP line only)"; diff $R/w10_seat2_orig.py $R/w10_seat2g.py || true
grep -n "^PHIDYN_LOOK" $R/w10_seat2g.py
for v in dev dev_alt; do
  d=$R/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs $d/f8_2026-08-22/preds
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do ln -sfn /workspace/port_w10/pod_backup_2026-08-21/$f $d/pod_backup_2026-08-21/$f; done
  if [ $v = dev ]; then ln -sfn /workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  else ln -sfn /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; fi
  ln -sfn /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy $d/f8_2026-08-22/preds/f10_V2MAIN_s42.npy
  ln -sfn /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy $d/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
done
echo "--- resolved targets vs health_check (must all be SAME)"
for v in dev dev_alt; do for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
  a=$(readlink -f $R/$v/pod_backup_2026-08-21/$f); b=$(readlink -f $H/$v/pod_backup_2026-08-21/$f); [ "$a" = "$b" ] && echo "SAME $v/$f" || echo "DIFF $v/$f mine=$a hc=$b"; done; done
sha256sum $R/w10_health.py $H/w10_health.py $S2/w10_seat2.py $R/w10_seat2_orig.py $R/w10_seat2g.py $R/check_equiv.py $H/masks/umask_UPIT.npz $H/calib/costb_fee_steady.json /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy | tee $R/logs/setup_sha256.txt
echo "SETUP_DONE $(date -u +%FT%TZ)"
# ── equivalence receipts: (i) w10_health baseline s42 vs health_check; (ii) w10_health baseline s2027 vs health_check; (iii) w10_seat2g default path (PHIDYN=0, default clip) vs (i) ──
cd $R; SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
bash run_arm.sh BASE_s42 prod w10_health.py $COMMON FSEED=42 > logs/BASE_s42.out 2>&1 &
bash run_arm.sh BASE_s2027 prod w10_health.py $COMMON FSEED=2027 > logs/BASE_s2027.out 2>&1 &
bash run_arm.sh SEAT2DEF_s42 prod w10_seat2g.py $COMMON FSEED=42 PHIDYN=0 > logs/SEAT2DEF_s42.out 2>&1 &
wait
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz $H/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz "gate BASE_s42 vs health_check M1_UPIT_prod_s42_ccal" >> logs/check_equiv.log 2>&1; echo "EQ1 rc=$?" >> logs/eq_chain.log
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz $H/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_ccal.npz "gate BASE_s2027 vs health_check M1_UPIT_prod_s2027_ccal" >> logs/check_equiv.log 2>&1; echo "EQ2 rc=$?" >> logs/eq_chain.log
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_SEAT2DEF_s42.npz dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz "w10_seat2g default path (PHIDYN=0, clip env default) vs w10_health BASE_s42" >> logs/check_equiv.log 2>&1; echo "EQ3 rc=$?" >> logs/eq_chain.log
cat logs/check_equiv.log | cut -c1-260; echo "EQ_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/eq_chain.log; cat logs/eq_chain.log
