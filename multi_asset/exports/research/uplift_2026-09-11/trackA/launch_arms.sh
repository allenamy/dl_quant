#!/bin/bash
U=/workspace/uplift_2026-09-11; R=$U/run_uplift.sh
for s in 42 2027; do
  $R A0_dyn_s$s      $s FTRIM=zero SLEEVE=1 &
  $R NOFTRIM_dyn_s$s $s FTRIM=off  SLEEVE=1 &
  $R FT30_dyn_s$s    $s FTRIM=zero FTRIM_TH=-0.0030 SLEEVE=1 &
  $R FT05_dyn_s$s    $s FTRIM=zero FTRIM_TH=-0.0005 SLEEVE=1 &
  $R LT10_dyn_s$s    $s FTRIM=zero LTRIM_TH=0.0010 SLEEVE=1 &
  $R LT30_dyn_s$s    $s FTRIM=zero LTRIM_TH=0.0030 SLEEVE=1 &
  $R LT50_dyn_s$s    $s FTRIM=zero LTRIM_TH=0.0050 SLEEVE=1 &
  $R CD05_dyn_s$s    $s FTRIM=zero CDAMP=0.5 SLEEVE=1 &
  $R CD1_dyn_s$s     $s FTRIM=zero CDAMP=1.0 SLEEVE=1 &
  $R CD2_dyn_s$s     $s FTRIM=zero CDAMP=2.0 SLEEVE=1 &
  wait
done
echo LAUNCH_DONE
