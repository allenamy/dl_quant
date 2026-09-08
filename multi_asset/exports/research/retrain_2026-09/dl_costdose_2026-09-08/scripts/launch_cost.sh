#!/bin/bash
# launch_cost.sh <ARM: C2_85|C4_85|C2_FULL|C4_FULL|SELFCHK> <shard> <MONTHS csv>
ARM=$1; K=$2; M=$3; B=/workspace/review_scratch/costdose; PY=/workspace/venv/bin/python
mkdir -p $B/logs; cd $B || exit 2
case $ARM in
  C2_85)   KN="COST=7.04 TRAIN_FRAC=0.85 BEST_EP_FIX=7"; TAG=mE1c2f85 ;;
  C4_85)   KN="COST=14.08 TRAIN_FRAC=0.85 BEST_EP_FIX=7"; TAG=mE1c4f85 ;;
  C2_FULL) KN="COST=7.04 TRAIN_FRAC=1.0 BEST_EP_FIX=7";  TAG=mE1c2full ;;
  C4_FULL) KN="COST=14.08 TRAIN_FRAC=1.0 BEST_EP_FIX=7"; TAG=mE1c4full ;;
  SELFCHK) KN="COST=3.52 TRAIN_FRAC=0.85 BEST_EP_FIX=7"; TAG=mE1cX7 ;;
  *) echo "bad arm $ARM"; exit 2 ;;
esac
O=$B/$ARM/shard$K; mkdir -p $O
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MWF_TAG=$TAG $KN MONTHS=$M $PY $B/pod_f10_train_monthly_costdose.py"
T0=$(date +%s); echo "CMD[$ARM shard$K] $(date -u +%FT%TZ) : $CMD" >> logs/commands.txt
$CMD > logs/train_${ARM}_shard$K.log 2>&1 & P=$!; echo "PID[$ARM shard$K] $P $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$ARM shard$K] $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 ))s folds $(ls $O/preds_fold/ 2>/dev/null | wc -l)" >> logs/commands.txt
exit $rc
