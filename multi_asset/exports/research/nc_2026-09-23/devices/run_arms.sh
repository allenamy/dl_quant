#!/bin/bash
# 8 single-family arm viability runs (+ release tree), one at a time, CPU only, after news2's engine step (lead rule).
# Guards: a lock (one run at a time; the 02:04Z and 02:06Z runs overlapped and shared a log/receipt), /dev/shm free >= 1.0 GiB measured
# before start, ABSOLUTE tree paths (relative arm paths were joined twice inside the mini pipeline: arms/D4/fea171/arms/D4/...),
# a per-run log and receipt name; each arm's scratch (~90 MB) is removed by the device and again here.
set -u
W=/dev/shm/nc_2026-09-23; MIN=1048576; TAG=$(date -u +%Y%m%dT%H%MZ)
LOCK=$W/logs/arms.lock
if ! mkdir $LOCK 2>/dev/null; then echo "REFUSED: another arm run holds $LOCK"; exit 9; fi
trap 'rmdir $LOCK' EXIT
free() { df -k /dev/shm | tail -1 | awk '{print $4}'; }
echo "$(date -u +%H:%M:%SZ) tag $TAG; /dev/shm free before: $(awk "BEGIN{printf \"%.2f\", $(free)/1048576}") GiB"
[ "$(free)" -ge $MIN ] || { echo "REFUSED: /dev/shm free below 1.0 GiB"; exit 8; }
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NC_W=$W NC_WS=$W/ws NC_CFG=$W/inputs/bundle_config.json CUDA_VISIBLE_DEVICES=
cd $W
A=$W/arms
nice -n 10 /root/news_2026-09-23_env/venv314/bin/python -u devices_arm/nc_arm_viability.py receipts/ARM_VIABILITY_NC_$TAG.json 1789660800 \
  release=$W/tree base=$A/base D4=$A/D4 D5=$A/D5 D6=$A/D6 D7=$A/D7 D8=$A/D8 D9=$A/D9 D14=$A/D14
rc=$?
echo "$(date -u +%H:%M:%SZ) rc=$rc; receipt receipts/ARM_VIABILITY_NC_$TAG.json; /dev/shm free after: $(awk "BEGIN{printf \"%.2f\", $(free)/1048576}") GiB"
rm -rf $W/scratch/armviab_*
exit $rc
