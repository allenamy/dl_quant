#!/bin/bash
# FRESH chain stage 2: the paired comparison against NEW_S. Runs only once BOTH arms' engine runs and R-P readings exist.
# 1. red/green test of the R-P run selection on the REAL receipts of this comparison (baseline green first, then every mutation refused)
# 2. fresh_stats.py  — F1..F5 verdict
# 3. fresh_ext.py    — describe-only extension segment
# 4. fresh_report.py — the prereg §3/§4 report-only tables
set -e
W=/dev/shm/fresh_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs
N=/dev/shm/news_2026-09-23
PV=/workspace/venv/bin/python
step() { echo "$(date -u +%H:%M:%S) START $1" >> $L/chain.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" >> $L/chain.log; }
step wait_news_readings
while [ ! -f $N/receipts/engine/BT_P_READING_NEWS_s2027.json ] || [ ! -f $N/receipts/engine/BT_P_READING_NEWS_s42.json ]; do sleep 60; done
while ! grep -q "DONE readings" $N/logs/chain.log; do sleep 60; done
done_ wait_news_readings
cp -p $D/fresh_stats.py $D/test_fresh_stats_rp.py $D/fresh_ext.py $D/fresh_report.py $E/
cd $E
step rp_test
cat > $W/scratch/rp_cases_real.json <<EOF
[
 {"name":"FRESH_s42","receipt":"$W/receipts/engine/BT_P_READING_FRESH_s42.json","dir":"$W/runs/FRESH_s42_scaled_rule_raw_UAFE","want":null},
 {"name":"NEWS_s42","receipt":"$N/receipts/engine/BT_P_READING_NEWS_s42.json","dir":"$N/runs/NEWS_s42_scaled_rule_raw_UAFE","want":null},
 {"name":"FRESH_s2027","receipt":"$W/receipts/engine/BT_P_READING_FRESH_s2027.json","dir":"$W/runs/FRESH_s2027_scaled_rule_raw_UAFE","want":null},
 {"name":"NEWS_s2027","receipt":"$N/receipts/engine/BT_P_READING_NEWS_s2027.json","dir":"$N/runs/NEWS_s2027_scaled_rule_raw_UAFE","want":null}
]
EOF
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B test_fresh_stats_rp.py PATH,HOME,LC_CTYPE $W/scratch/rp_cases_real.json $W/receipts/TEST_FRESH_STATS_RP_real.json > $L/chain_rptest.log 2>&1
done_ rp_test
step stats
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B fresh_stats.py PATH,HOME,LC_CTYPE \
  $N/runs $W/runs \
  $N/receipts/engine/BT_P_READING_NEWS_s42.json $N/receipts/engine/BT_P_READING_NEWS_s2027.json \
  $W/receipts/engine/BT_P_READING_FRESH_s42.json $W/receipts/engine/BT_P_READING_FRESH_s2027.json \
  $N/configs/RUN_CONFIG_NEWS_s42_2026-09-23.json $N/configs/RUN_CONFIG_NEWS_s2027_2026-09-23.json \
  $W/configs/RUN_CONFIG_FRESH_s42_2026-09-23.json $W/configs/RUN_CONFIG_FRESH_s2027_2026-09-23.json \
  $W/receipts/engine/FRESH_STATS.json > $L/chain_stats.log 2>&1
done_ stats
step ext
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B fresh_ext.py PATH,HOME,LC_CTYPE $W/runs $N/runs $W/receipts/engine/FRESH_EXT.json > $L/chain_ext.log 2>&1
done_ ext
step report
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B fresh_report.py PATH,HOME,LC_CTYPE $W $N $W/receipts/engine/FRESH_REPORT.json > $L/chain_report.log 2>&1
done_ report
echo "CHAIN2_DONE" >> $L/chain.log
