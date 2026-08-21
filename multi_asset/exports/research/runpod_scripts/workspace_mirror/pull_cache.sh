#!/bin/bash
for i in $(seq 1 200); do
  scp -o ConnectTimeout=8 -o StrictHostKeyChecking=no -P 31999 root@212.50.244.62:/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/dlnative_5m_cache.npz /workspace/data/ && echo PULL_OK && break
  sleep 90
done
