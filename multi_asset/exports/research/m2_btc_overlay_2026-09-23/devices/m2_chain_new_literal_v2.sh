#!/bin/bash
# m2_chain_new_literal.sh (v2: the two seeds in parallel; v1 PGID 2217487 was stopped while still waiting, before it launched anything) — waits for the OLD literal launcher (its log's EXIT line), then runs, one after another:
#  NEW s42 / s2027 literal route, MAIN reading only (declared resource deviation: executor-path diagnostic already shows non-delivery;
#  cost cells not run => H2.4 not computable for the literal NEW route), full window, seeds 0..31, via bt_launch --smoke (same path content);
#  NEW zero-hedge hook controls, seed 0 (compared later against Stage 1's NEW base seed 0).
R=/dev/shm/m2_btc_overlay_2026-09-23; DEV=/workspace/baseline_tables_2026-09-19/devices_v3; P=/workspace/venv/bin/python
SEEDS=$(seq -s, 0 31)
until grep -q "^EXIT" $R/logs/bt_launch_full_m2old.log; do sleep 60; done
echo "start $(date -u +%FT%TZ)" >> $R/logs/chain_new_literal.log
for s in s42 s2027; do (
  (cd $DEV && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2_NEW_${s}_2026-09-23.json --smoke 2022-06-30T00:00:00Z 9139 $SEEDS "OVN_NEW_${s}M2|scaled|rule|raw|UAFE" new_${s}_lit_main > $R/logs/bt_launch_new_${s}_lit_main.log 2>&1; echo "EXIT $?" >> $R/logs/bt_launch_new_${s}_lit_main.log)
  (cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2h0_NEW_${s}_2026-09-23.json --smoke 2022-06-30T00:00:00Z 9139 0 "OVN_NEW_${s}M2H0|scaled|rule|raw|UAFE" m2h0_new_${s} > $R/logs/m2h0_new_${s}.log 2>&1; echo "EXIT $?" >> $R/logs/m2h0_new_${s}.log)
) & done; wait
echo "end $(date -u +%FT%TZ)" >> $R/logs/chain_new_literal.log
