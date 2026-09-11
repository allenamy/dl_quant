#!/bin/bash
# ROUND 5 / ANGLE 3 -- HOMOGENEOUS in-service-object seed draws.
# Object = V2=1 composed chain (pod_f10_train_ext.py L92-95, L214-217) = what pod_f10_refit_ext.py hardwires
# for the deployed leg. r3_xib/train_seeds.sh omitted V2 => trained a DIFFERENT object (round 4, E-0826-D recurrence).
# ENV WHITELIST (all 17 reads of os.environ in pod_f10_train_ext.py sha 93cc2cdf...) ARE SET EXPLICITLY,
# none left to a default, so the object is fully pinned by this line:
#   F10_DLW F10_OUT SEED ARM COST LDD AFIX LDC CTXA REC PLE EPOCHS LR NCOL EXTRA LPP V2
set -u
R=/workspace/uplift_2026-09-11/r5_seeds
S=$1
mkdir -p $R/f8_s$S/preds $R/f8_s$S/results $R/f8_s$S/models
ln -sfn /workspace/f8_ext/data $R/f8_s$S/data
env V2=1 ARM=V2MAIN SEED=$S COST=3.52 LDD=0.25 AFIX=0 LDC=0.0 CTXA=0 REC=0 PLE=0 \
    EPOCHS=15 LR=3e-4 NCOL=167 EXTRA= LPP=0.0 \
    F10_DLW=/workspace/dlw_ext F10_OUT=$R/f8_s$S \
    /workspace/venv/bin/python /workspace/pod_f10_train_ext.py > $R/logs/train_s$S.log 2>&1
echo "TRAIN_RC[s$S,V2=1,fullwhitelist]=$? $(date -u +%FT%TZ)" >> $R/logs/train_status.txt
