#!/bin/bash
# P4 item 1 -- MECHANISM, decisive design.
# Prior receipts say this same trainer on THIS pod was BITWISE reproducible on 2026-08-25
# (docs/PREREG_leg_ablation_2026-08-26.md §J: V2DET_s42 vs V2PAR_s42 bitwise True, Spearman 1.000000;
#  /workspace/logs/f10_V2PAR_s42.log 20:13Z and f10_V2DET_s42.log 20:44Z = SEQUENTIAL, one at a time),
# while round 3's REP42 (5 jobs at once) and the archived pair (2 jobs, written 1 s apart) do not agree.
# HYPOTHESIS: the divergence is CONCURRENCY-conditional, not intrinsic.
# Design (EPOCHS=1 -- enough, because divergence starts at the first optimiser step; labelled as a probe
# of the mechanism, not a book-layer recipe):
#   S1,S2        off,  run ONE AT A TIME        -> is a solo re-run bitwise reproducible?
#   C1,C2        off,  two launched TOGETHER    -> does 2-way contention break it?
#   C3..C7       off,  five launched TOGETHER   -> does 5-way (round-3's condition) break it?
#   W1,W2        cw,   two TOGETHER             -> does CUBLAS_WORKSPACE_CONFIG=:4096:8 alone repair it?
#   F1,F2        full, two TOGETHER             -> does full determinism repair it, and at what time cost?
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
cd $R
echo "=== PROBE_DRIVE start $(date -u +%FT%TZ)" >> logs/probe_drive.log
./train_probe.sh S1 off 1
echo "S1 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
./train_probe.sh S2 off 1
echo "S2 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
./train_probe.sh S3 full 1
echo "S3(full,solo) done $(date -u +%FT%TZ)" >> logs/probe_drive.log
for L in C1 C2; do ./train_probe.sh $L off 1 & done; wait
echo "C1C2 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
for L in C3 C4 C5 C6 C7; do ./train_probe.sh $L off 1 & done; wait
echo "C3..C7 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
for L in W1 W2; do ./train_probe.sh $L cw 1 & done; wait
echo "W1W2 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
for L in F1 F2; do ./train_probe.sh $L full 1 & done; wait
echo "F1F2 done $(date -u +%FT%TZ)" >> logs/probe_drive.log
echo "PROBE_DRIVE_DONE $(date -u +%FT%TZ)" >> logs/probe_drive.log
