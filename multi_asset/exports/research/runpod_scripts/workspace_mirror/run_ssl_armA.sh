#!/bin/bash
# W5/#47 臂A 整链: SSL 预训练(逐折因果) -> 冠军 finetune 双种子(PREREG_ssl_pretrain 冻结)
set -e
export PYTHONPATH=/workspace/code
P=/workspace/data/wide_dl_pm32_hz.npz
echo "[armA] panel sha=$(sha256sum $P | cut -c1-16)"
python3 /workspace/pretrain_ssl.py $P /workspace/exports_train/ssl_enc32 6 42
echo PRETRAIN_DONE
bash /workspace/champion_run.sh $P 4 42 ssl32_yr4_s42 conformer   --pretrained_encoder '/workspace/exports_train/ssl_enc32/fold_{fold}_encoder.pt' --enc_lr_mult 0.3
echo FT_S42_DONE
bash /workspace/champion_run.sh $P 4 2027 ssl32_yr4_s2027 conformer   --pretrained_encoder '/workspace/exports_train/ssl_enc32/fold_{fold}_encoder.pt' --enc_lr_mult 0.3
echo FT_S2027_DONE
echo ARMA_ALL_DONE
