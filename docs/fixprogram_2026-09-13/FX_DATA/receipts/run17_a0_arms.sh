#!/bin/sh
# FX-DATA TRD-01 step C run 17 (2026-09-16): the SPEC section 7 A0 arms on the UNMODIFIED device.
# Device /workspace/uplift_2026-09-11/w10_sleeve.py sha b88e35a4; recipe copied from r3k_reprice3.py BOOK + FSEED/FPRED + COSTB.
# cwd is a tree of symlinks with the same targets as r3k/dev (verified link by link), so nothing is written into the r3k round.
set -e
FX=/workspace/fx_data_2026-09-13
DEV=/workspace/uplift_2026-09-11/w10_sleeve.py
HC=/workspace/review_scratch/health_check
R3K=/workspace/uplift_2026-09-11/r3k
K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
INJ=$FX/out/inject
mkdir -p $FX/out/arms $FX/a0dev/logs $FX/a0dev/probe_artifacts
cd $FX/a0dev
for SEED in 42 2027; do
  for ARM in C0 TU TB TF TF4; do
    case $ARM in
      C0)  UM=$HC/masks/umask_UPIT_CRYPTO.npz;          FM="" ;;
      TU)  UM=$INJ/umask_UPIT_CRYPTO_tradable_W24H.npz; FM="" ;;
      TB)  UM=$HC/masks/umask_UPIT_CRYPTO.npz;          FM=$INJ/femat_f_fund_ema_v1_tradable_W24H.npz ;;
      TF)  UM=$INJ/umask_UPIT_CRYPTO_tradable_W24H.npz; FM=$INJ/femat_f_fund_ema_v1_tradable_W24H.npz ;;
      TF4) UM=$INJ/umask_UPIT_CRYPTO_tradable_W4H.npz;  FM=$INJ/femat_f_fund_ema_v1_tradable_W4H.npz ;;
    esac
    TAG=${ARM}_PWR230k_s${SEED}
    if [ -f "$FX/out/arms/$TAG.npz" ]; then echo "$TAG skip"; continue; fi
    if [ -n "$FM" ]; then FMARG="FEMAT_NPZ=$FM"; else FMARG="FX_DATA_ARM=$ARM"; fi
    env -i \
      PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
      HOME=/root \
      OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3 \
      LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 \
      UMASK_SCOPE=m1 UMASK_NPZ=$UM SLOW_NPY=$K3 \
      FSEED=$SEED FPRED=f10_A0_s${SEED}.npy \
      COSTB_JSON=$R3K/costb_PWR_G230k.json OUT_TAG=$TAG \
      $FMARG \
      nice -n 19 /workspace/venv/bin/python $DEV > $FX/a0dev/logs/$TAG.log 2>&1
    SRC=$FX/a0dev/probe_artifacts/w10_ablation_series_$TAG.npz
    [ -f "$SRC" ] || { echo "MISSING $SRC"; exit 3; }
    /workspace/venv/bin/python $FX/devices/fx_pack_arm.py "$SRC" "$FX/out/arms/$TAG.npz"
    rm -f "$SRC"
    echo "$TAG done"
  done
done
echo ALL_ARMS_DONE
