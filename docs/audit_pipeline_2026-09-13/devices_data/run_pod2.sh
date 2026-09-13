#!/bin/bash
# run_pod2.sh -- AUDIT_DATA 2026-09-13: the exact commands used to run devices A-D on pod2 (CPU only, nice 19, read-only on every dataset).
# Outputs only under /workspace/aud_data_2026-09-13/ (receipts are KB-sized JSON). Never touches PIDs 333197 / 339489 or any P2 process.
# Run from the Mac repo root:  bash docs/audit_pipeline_2026-09-13/devices_data/run_pod2.sh <A|B|C|D>
set -euo pipefail
R=/workspace/aud_data_2026-09-13
HERE=docs/audit_pipeline_2026-09-13/devices_data
case "${1:?device letter}" in
  sync) ssh pod2 "mkdir -p $R/devices $R/receipts $R/logs"
        scp -q $HERE/ad_inventory.py $HERE/ad_funding_iv.py $HERE/ad_cache_members.py $HERE/ad_panel_holes.py $HERE/ad_batch2.py $HERE/ad_batch3.py $HERE/ad_tradability.py pod2:$R/devices/
        scp -q multi_asset/exports/research/retrain_2026-09/universe_crypto_2026-09-08/venue_class_20260908.json pod2:$R/devices/
        ssh pod2 "cd $R/devices && sha256sum ad_inventory.py ad_funding_iv.py ad_cache_members.py ad_panel_holes.py ad_batch2.py ad_batch3.py ad_tradability.py venue_class_20260908.json" ;;
  A) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_inventory.py receipts/AD_A_inventory.json > logs/AD_A_inventory.log 2>&1; echo rc=\$? >> logs/AD_A_inventory.log" ;;
  B) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_funding_iv.py receipts/AD_B_funding_iv.json > logs/AD_B_funding_iv.log 2>&1; echo rc=\$? >> logs/AD_B_funding_iv.log" ;;
  C) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_cache_members.py receipts/AD_C_cache_members.json devices/venue_class_20260908.json > logs/AD_C_cache_members.log 2>&1; echo rc=\$? >> logs/AD_C_cache_members.log" ;;
  D) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_panel_holes.py receipts/AD_D_panel_holes.json > logs/AD_D_panel_holes.log 2>&1; echo rc=\$? >> logs/AD_D_panel_holes.log" ;;
  F) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_batch2.py receipts/AD_F_batch2.json > logs/AD_F_batch2.log 2>&1; echo rc=\$? >> logs/AD_F_batch2.log" ;;
  G) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_batch3.py receipts/AD_G_batch3.json > logs/AD_G_batch3.log 2>&1; echo rc=\$? >> logs/AD_G_batch3.log" ;;
  H) ssh pod2 "cd $R && nohup env -i PATH=/usr/bin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 /workspace/venv/bin/python -B devices/ad_tradability.py receipts/AD_H_tradability.json > logs/AD_H_tradability.log 2>&1; echo rc=\$? >> logs/AD_H_tradability.log" ;;
  E) python3 $HERE/ad_consumers_scan.py "$(pwd)" $HERE/receipts/AD_E_consumers_matrix.json ;;
  fetch) scp -q "pod2:$R/receipts/*.json" "pod2:$R/logs/*.log" $HERE/receipts/ ;;
esac
