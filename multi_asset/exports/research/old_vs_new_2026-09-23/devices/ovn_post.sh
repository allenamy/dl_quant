#!/bin/sh
# ovn_post.sh — OVN Stage 1 post-run chain (pod2, CPU only); AMENDMENT 1 arm OLD_HOLD included. VERBATIM commands; stops at the first non-zero exit.
#   1. reading-P / P2 configs for each arm: the certified bt_p_config_for.py copies the FROZEN A0 P / P2 configs byte for byte (p_reading and
#      p2_reading blocks asserted identical) and changes only which run directories are read
#   2. R-P (bt_p_reading.py a7cb9c4d) and R-P2 (bt_p2_reading.py fa67ae29, bt_agg 43fe1092) per arm — report only
#   3. prereg statistics + verdict (ovn_stats.py) and the describe-only extension (ovn_ext.py)
set -e
R=/workspace/old_vs_new_2026-09-23; S=/dev/shm/ovn_2026-09-23; B=/workspace/baseline_tables_2026-09-19
PY="env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B"
cd $R/devices
for a in "OLD:OBJB_A0:RUN_CONFIG_OVN_OLD_2026-09-23.json" "OLD_HOLD:OVN_OLD_HOLD:RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json" "NEW_s42:OVN_NEW_s42:RUN_CONFIG_OVN_NEW_s42_2026-09-23.json" "NEW_s2027:OVN_NEW_s2027:RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json"; do
  ARM=$(echo $a | cut -d: -f1); PFX=$(echo $a | cut -d: -f2); CFG=$(echo $a | cut -d: -f3)
  $PY bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_Preading_A0_2026-09-20.json  $R/$CFG $PFX $S/runs "OVN $ARM" $R/RUN_CONFIG_Preading_OVN_$ARM.json
  $PY bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_P2reading_A0_2026-09-20.json $R/$CFG $PFX $S/runs "OVN $ARM" $R/RUN_CONFIG_P2reading_OVN_$ARM.json
  $PY bt_p_reading.py  PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_OVN_$ARM.json  $S/receipts/BT_P_READING_OVN_$ARM.json
  $PY bt_p2_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_P2reading_OVN_$ARM.json $S/receipts/BT_P2_READING_OVN_$ARM.json
done
$PY ovn_stats.py PATH,HOME,LC_CTYPE $S/runs $B/runs $S/receipts/OVN_STATS.json
$PY ovn_ext.py   PATH,HOME,LC_CTYPE $S/runs $B/runs $S/receipts/OVN_EXT.json
echo "OVN_POST DONE"
