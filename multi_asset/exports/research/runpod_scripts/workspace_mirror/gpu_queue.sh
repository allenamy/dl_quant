#!/bin/bash
# 10h 自驱动 GPU 队列(PREREG_ssl_pretrain 分支预写) — 阶段行以 STAGE:/VERDICT: 开头供监视器
export PYTHONPATH=/workspace/code
P=/workspace/data/wide_dl_pm32_hz.npz
P53=/workspace/data/wide_dl_53ch.npz
CR=/workspace/champion_run.sh
PE="--pretrained_encoder /workspace/exports_train/ssl_enc32/fold_{fold}_encoder.pt"
echo "STAGE:WAIT_ARMA $(date -u +%H:%M)"
while ! grep -q ARMA_ALL_DONE /workspace/ssl_armA.log 2>/dev/null; do
  grep -q Traceback /workspace/ssl_armA.log 2>/dev/null && { echo 'STAGE:ARMA_ERROR'; break; }
  sleep 60
done
V=$(python3 /workspace/branch_judge.py | tee /dev/stderr | grep BRANCH | cut -d: -f2)
echo "VERDICT:ARMA:$V $(date -u +%H:%M)"
if [ "$V" = PASS ]; then
  bash $CR $P 4 3037 ssl32_yr4_s3037 conformer $PE --enc_lr_mult 0.3 && echo STAGE:S3037_DONE
  python3 /workspace/pretrain_ssl.py $P53 /workspace/exports_train/ssl_enc53 6 42 && echo STAGE:PRE53_DONE
  bash $CR $P53 4 42 ssl53_yr4_s42 conformer --pretrained_encoder '/workspace/exports_train/ssl_enc53/fold_{fold}_encoder.pt' --enc_lr_mult 0.3 && echo STAGE:ARMB_DONE
  bash $CR $P 4 42 ssl32lr1_yr4_s42 conformer $PE --enc_lr_mult 1.0 && echo STAGE:LR1_DONE
  python3 /workspace/pretrain_ssl.py $P /workspace/exports_train/ssl_enc32d 12 42 &&   bash $CR $P 4 42 ssl32d_yr4_s42 conformer --pretrained_encoder '/workspace/exports_train/ssl_enc32d/fold_{fold}_encoder.pt' --enc_lr_mult 0.3 && echo STAGE:DEEP_DONE
elif [ "$V" = MARGINAL ]; then
  bash $CR $P 4 42 ssl32lr1_yr4_s42 conformer $PE --enc_lr_mult 1.0 && echo STAGE:LR1_DONE
  python3 /workspace/pretrain_ssl.py $P /workspace/exports_train/ssl_enc32d 12 42 &&   bash $CR $P 4 42 ssl32d_yr4_s42 conformer --pretrained_encoder '/workspace/exports_train/ssl_enc32d/fold_{fold}_encoder.pt' --enc_lr_mult 0.3 && echo STAGE:DEEP_DONE
else
  bash $CR $P 4 42 sslfrz_yr4_s42 conformer $PE --enc_lr_mult 0.0 && echo STAGE:FROZEN_DIAG_DONE
fi
echo "STAGE:QIM_START $(date -u +%H:%M)"
bash $CR $P 4 42 qim_yr4_s42 conformer --qim --n_quantiles 25 && echo STAGE:QIM42_DONE
bash $CR $P 4 2027 qim_yr4_s2027 conformer --qim --n_quantiles 25 && echo STAGE:QIM2027_DONE
echo "STAGE:QUEUE_EXHAUSTED $(date -u +%H:%M) — GPU idle, 无自动新任务(纪律: 不烧空转)"
