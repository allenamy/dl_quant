#!/bin/bash
# setup_replay.sh — dl_monthly_wf: reproduce the health_check replay device layout under /workspace/review_scratch/dl_monthly_wf/replay/
# (device w10_health.py copied bitwise; dev = log caliber meta, dev_alt = prod caliber meta; f8_2026-08-22/preds is a REAL directory so that the
# monthly prediction files can sit next to symlinks of the original yearly-fold files). Read-only on every source; writes only under replay/.
# Then launches the two equivalence receipts (CPU): (i) default path log caliber vs axisB R0_pinned_log_s42, (ii) the primary prod arm vs
# health_check M1_UPIT_prod_s42_ccal (bitwise, incl. config: UMASK_NPZ / COSTB_JSON read from health_check's own files).
set -e
R=/workspace/review_scratch/dl_monthly_wf/replay; H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python
mkdir -p $R/logs $R/results $R/calib $R/masks
cp $H/w10_health.py $R/w10_health.py; cp $H/check_equiv.py $R/check_equiv.py
cp $H/calib/costb_fee_steady.json $R/calib/; cp $H/masks/umask_UPIT.npz $H/masks/btc_rv30.npz $H/masks/regime_series.npz $R/masks/
sed "s#^ROOT = \"/workspace/review_scratch/health_check\"#ROOT = \"$R\"#" $H/health_metrics.py > $R/health_metrics.py
sed "s#^ROOT=/workspace/review_scratch/health_check; PY=#ROOT=$R; PY=#" $H/run_arm.sh > $R/run_arm.sh
echo "--- diff health_metrics (expected: ROOT line only)"; diff $H/health_metrics.py $R/health_metrics.py || true
echo "--- diff run_arm (expected: ROOT line only)"; diff $H/run_arm.sh $R/run_arm.sh || true
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
for v in dev dev_alt; do
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do
    a=$(readlink -f $R/$v/pod_backup_2026-08-21/$f); b=$(readlink -f $H/$v/pod_backup_2026-08-21/$f); [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a hc=$b"; done
  a=$(readlink -f $R/$v/dlw_2026-08-22/data/dlw_targets.npz); b=$(readlink -f $H/$v/dlw_2026-08-22/data/dlw_targets.npz); [ "$a" = "$b" ] && echo "SAME $v/dlw_targets -> $a" || echo "DIFF $v/dlw_targets mine=$a hc=$b"
  a=$(readlink -f $R/$v/f8_2026-08-22/preds/f10_V2MAIN_s42.npy); b=$(readlink -f $H/$v/f8_2026-08-22/preds/f10_V2MAIN_s42.npy); [ "$a" = "$b" ] && echo "SAME $v/f10_V2MAIN_s42 -> $a" || echo "DIFF $v/f10_V2MAIN_s42 mine=$a hc=$b"
done
echo "--- sha256 of device + inputs"
sha256sum $R/w10_health.py $H/w10_health.py $H/masks/umask_UPIT.npz $H/calib/costb_fee_steady.json /workspace/shadow_bundle_v3/slow_pred_pinned.npy /workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz /workspace/data/dlw_targets.npz | tee $R/logs/setup_sha256.txt
nproc; echo "SETUP_DONE $(date -u +%FT%TZ)"
# ── equivalence receipts (CPU, background) ──
cat > $R/eq_chain.sh <<'EOF'
#!/bin/bash
R=/workspace/review_scratch/dl_monthly_wf/replay; H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python; cd $R
SLOW=/workspace/shadow_bundle_v3/slow_pred_pinned.npy; UP=$H/masks/umask_UPIT.npz; CB=$H/calib/costb_fee_steady.json
COMMON="LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
bash run_arm.sh eq_pinned_log_s42 log w10_health.py LEGS=101 CAL=log SLOW_NPY=$SLOW WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero > logs/eq_pinned_log_s42.out 2>&1 &
bash run_arm.sh BASE_M1_UPIT_prod_s42_ccal prod w10_health.py $COMMON FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/BASE_M1_UPIT_prod_s42_ccal.out 2>&1 &
wait
$PY check_equiv.py dev/probe_artifacts/w10_ablation_series_eq_pinned_log_s42.npz /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz "dl_monthly_wf device default path (log) vs axisB R0_pinned_log_s42" >> logs/check_equiv.log 2>&1; echo "EQ1 rc=$?" >> logs/eq_chain.log
$PY check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz $H/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz "dl_monthly_wf baseline arm (prod, yearly FPRED) vs health_check M1_UPIT_prod_s42_ccal" >> logs/check_equiv.log 2>&1; echo "EQ2 rc=$?" >> logs/eq_chain.log
echo "EQ_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/eq_chain.log
EOF
nohup bash $R/eq_chain.sh > $R/logs/eq_chain.out 2>&1 &
echo "EQ_CHAIN_LAUNCHED pid $!"
