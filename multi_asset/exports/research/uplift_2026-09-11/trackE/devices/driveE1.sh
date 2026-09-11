#!/bin/bash
U=/workspace/uplift_2026-09-11; R=$U/runE.sh
P=0
launch(){ bash $R "$@" & P=$((P+1)); if [ $P -ge 6 ]; then wait; P=0; fi; }
for s in 42 2027; do
  for L in 30 60 120 190 380 570; do
    launch E1_L${L}_dyn_s$s LOOK=$L FSEED=$s FPRED=f10_A0_s$s.npy
  done
done
wait; P=0
# fix-seat invariance receipt
launch E1_L30_fix_s42 LOOK=30 FSEED=42 FPRED=f10_A0_s42.npy W3FIX=0.21,0,0.79
# E2 rules
for s in 42 2027; do
  launch E2_EQ_dyn_s$s WRULE=eq FSEED=$s FPRED=f10_A0_s$s.npy
  launch E2_RP_dyn_s$s SEATRULE=rp FSEED=$s FPRED=f10_A0_s$s.npy
  for lam in 25 50 75; do
    launch E2_SH${lam}_dyn_s$s SHRINK=0.$lam FSEED=$s FPRED=f10_A0_s$s.npy
  done
done
wait; P=0
# single-leg BOOK-layer runs (inputs for SEATRULE=book)
for s in 42 2027; do
  launch LEG_king_s$s LEGS=100 FSEED=$s FPRED=f10_A0_s$s.npy
  launch LEG_fund_s$s LEGS=001 FSEED=$s FPRED=f10_A0_s$s.npy
done
wait
grep -c "^END" $U/logs/commands.txt
grep "rc=[^0]" $U/logs/commands.txt | head
echo LAUNCH_E1E2_DONE
