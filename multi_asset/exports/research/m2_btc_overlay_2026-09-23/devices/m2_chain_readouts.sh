#!/bin/bash
# m2_chain_readouts.sh — runs each remaining M2 readout / control comparison as soon as its inputs exist (run through bash: /dev/shm is noexec).
R=/dev/shm/m2_btc_overlay_2026-09-23; C=/workspace/baseline_tables_2026-09-19/runs; B=/dev/shm/ovn_2026-09-23/runs; P=/workspace/venv/bin/python
DO=/workspace/m2_btc_overlay_2026-09-23/work/targets/M2DIAG_A0_main_M2.npz
E="env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B"
cd $R/devices
ro() { $E m2_readout.py "$@" ; }
cp_old() { local arm=$1 o=""; for c in fee_x1.25 slip_x1.5 fill_x0.9; do o="$o${o:+,}$c=$C/OBJB_A0_scaled_rule_raw_UAFE_$c:$R/runs/${arm}_scaled_rule_raw_UAFE_$c"; done; echo "$o"; }
cp_new() { local s=$1 o=""; for c in fee_x1.25 slip_x1.5 fill_x0.9; do o="$o${o:+,}$c=$B/OVN_NEW_${s}_scaled_rule_raw_UAFE_$c:$R/runs/OVN_NEW_${s}M2H_scaled_rule_raw_UAFE_$c"; done; echo "$o"; }
log() { echo "$(date -u +%FT%TZ) $*" >> $R/logs/chain_readouts.log; }
( until grep -q "^EXIT" $R/logs/bt_launch_full_m2h.log; do sleep 30; done
  ro OLD_H_hook $C/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0M2H_scaled_rule_raw_UAFE "$(cp_old OBJB_A0M2H)" $DO $R/receipts/M2_READOUT_OLD_H.json > $R/logs/readout_OLD_H.log 2>&1; log "OLD_H rc=$?" ) &
( until grep -q "^EXIT" $R/logs/bt_launch_full_m2old.log; do sleep 30; done
  ro OLD_L_literal $C/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0M2_scaled_rule_raw_UAFE "$(cp_old OBJB_A0M2)" $DO $R/receipts/M2_READOUT_OLD_L.json > $R/logs/readout_OLD_L.log 2>&1; log "OLD_L rc=$?"
  $E m2_path_compare.py $R/runs/OBJB_A0_scaled_rule_raw_UAFE $C/OBJB_A0_scaled_rule_raw_UAFE $(seq -s, 0 31) $R/receipts/M2_BASE_CONTROL_vs_certified_A0.json > $R/logs/base_control_compare.log 2>&1; log "base_control rc=$?" ) &
( until [ -f $B/OVN_NEW_s42_scaled_rule_raw_UAFE_fill_x0.9/AGG_OVN_NEW_s42_scaled_rule_raw_UAFE_fill_x0.9.json ]; do sleep 30; done
  ro NEW_s42_H_hook $B/OVN_NEW_s42_scaled_rule_raw_UAFE $R/runs/OVN_NEW_s42M2H_scaled_rule_raw_UAFE "$(cp_new s42)" $R/work/targets/M2DIAG_NEW_s42_M2.npz $R/receipts/M2_READOUT_NEW_s42_H.json > $R/logs/readout_NEW_s42_H.log 2>&1; log "NEW_s42_H rc=$?" ) &
( until grep -q "^end" $R/logs/chain_new_literal.log 2>/dev/null; do sleep 30; done
  for s in s42 s2027; do
    ro NEW_${s}_L_literal_main_only $B/OVN_NEW_${s}_scaled_rule_raw_UAFE $R/runs_smoke/new_${s}_lit_main/OVN_NEW_${s}M2_scaled_rule_raw_UAFE "" $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/receipts/M2_READOUT_NEW_${s}_L.json > $R/logs/readout_NEW_${s}_L.log 2>&1; log "NEW_${s}_L rc=$?"
    $E m2_path_compare.py $R/runs_smoke/m2h0_new_${s}/OVN_NEW_${s}M2H0_scaled_rule_raw_UAFE $B/OVN_NEW_${s}_scaled_rule_raw_UAFE 0 $R/receipts/M2H0_CONTROL_NEW_${s}_vs_stage1_base.json > $R/logs/m2h0_new_${s}_compare.log 2>&1; log "M2H0_NEW_${s} compare rc=$?"
  done ) &
wait; log "all done"
