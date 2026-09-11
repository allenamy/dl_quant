#!/bin/bash
# OKXRHO arms. Every run is `env -i` + an explicit, enumerated whitelist (E-0826-D).
set -e
H=/workspace/review_scratch/health_check
D=/workspace/r9okx/dev
UP=$H/masks/umask_UPIT_CRYPTO.npz
CB=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json     # fitted cost model (brief §4)
COMMON="OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 LEGS=001 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 PHI=0 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
cd $D
run () {  # run <TAG> <FTRIM> [FEMAT]
  TAG=$1; FT=$2; FM=$3
  EXTRA=""; [ -n "$FM" ] && EXTRA="FEMAT_NPZ=$FM"
  echo "CMD[$TAG] env -i $COMMON FTRIM=$FT $EXTRA OUT_TAG=$TAG /workspace/venv/bin/python ../w10_health.py" >> /workspace/r9okx/commands.txt
  env -i $COMMON FTRIM=$FT $EXTRA OUT_TAG=$TAG /workspace/venv/bin/python ../w10_health.py > $D/logs/$TAG.log 2>&1
  grep -E "^(CONFIG_HEALTH|UMASK|FEMAT|RECEIPT_EX d30|DONE)" $D/logs/$TAG.log | cut -c1-220
}
run R9_BINPANEL_fund     zero
run R9_BINPANEL_fund_nt  off
run R9_BINWARM_fund      zero /workspace/r9okx/femat_BINWARM.npz
run R9_BINCOLD_fund      zero /workspace/r9okx/femat_BINCOLD.npz
run R9_BINCOLD_fund_nt   off  /workspace/r9okx/femat_BINCOLD.npz
run R9_OKX_fund          zero /workspace/r9okx/femat_OKX.npz
run R9_OKX_fund_nt       off  /workspace/r9okx/femat_OKX.npz
echo ALL_ARMS_DONE
