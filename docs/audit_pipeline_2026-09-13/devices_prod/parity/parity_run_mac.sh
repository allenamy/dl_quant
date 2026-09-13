#!/bin/bash
# parity_run_mac.sh -- verbatim Mac launcher for AUDIT_PROD parity devices (production interpreter ~/wide_shadow/venv, nice 10, env -i whitelist, no bytecode writes).
# Refuses to start inside a producer anchor window (UTC hour in 00/04/08/12/16/20 and minute 10..55).
# Usage: bash docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_run_mac.sh <king|f10|checks>
set -u
D=/Users/haosiyu/Desktop/quant_research/docs/audit_pipeline_2026-09-13
R=$D/receipts_prod
H=$(date -u +%H); M=$(date -u +%M)
case "$H" in 00|04|08|12|16|20) if [ "$((10#$M))" -ge 10 ] && [ "$((10#$M))" -le 55 ]; then echo "REFUSE: anchor window $H:$M UTC"; exit 9; fi;; esac
PY=/Users/haosiyu/wide_shadow/venv/bin/python
WL=PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,__CF_USER_TEXT_ENCODING
run() {
  local name=$1; shift
  nice -n 10 env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu OMP_NUM_THREADS=4 $PY -B $D/devices_prod/parity/$name.py $WL "$@" > $R/${name}_stdout.log 2>&1
  local rc=$?; echo "EXIT rc=$rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $R/${name}_stdout.log; return $rc
}
case "$1" in
  king) run parity_king ;;
  f10) run parity_f10 ;;
  checks) run prod_target_checks ;;
  *) echo "unknown mode $1"; exit 2 ;;
esac
