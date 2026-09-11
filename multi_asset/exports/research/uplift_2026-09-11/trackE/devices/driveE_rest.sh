#!/bin/bash
U=/workspace/uplift_2026-09-11; R=$U/runE.sh
J=0
launch(){ local tag=$1; shift; if [ -f $U/artifacts/w10_ablation_series_$tag.npz ]; then return; fi; bash $R $tag "$@" & J=$((J+1)); if [ $J -ge 8 ]; then wait; J=0; fi; }
for s in 42 2027; do
  launch E2_EQ_dyn_s$s WRULE=eq FSEED=$s FPRED=f10_A0_s$s.npy
  launch E2_RP_dyn_s$s SEATRULE=rp FSEED=$s FPRED=f10_A0_s$s.npy
  for lam in 25 50 75; do launch E2_SH${lam}_dyn_s$s SHRINK=0.$lam FSEED=$s FPRED=f10_A0_s$s.npy; done
  launch LEG_king_s$s LEGS=100 FSEED=$s FPRED=f10_A0_s$s.npy
  launch LEG_fund_s$s LEGS=001 FSEED=$s FPRED=f10_A0_s$s.npy
done
wait; J=0
for s in 42 2027; do
  for ph in 0.00 0.25 0.35 0.55 0.65; do
    launch E3_PHI${ph}_dyn_s$s PHI=$ph FSEED=$s FPRED=f10_A0_s$s.npy
    launch E3_PHI${ph}_fix_s$s PHI=$ph FSEED=$s FPRED=f10_A0_s$s.npy W3FIX=0.21,0,0.79
  done
done
wait
echo DRIVE_REST_DONE $(ls $U/artifacts/ | grep -c series)
