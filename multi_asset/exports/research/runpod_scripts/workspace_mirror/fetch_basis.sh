#!/bin/bash
cd /workspace
for k in premiumIndexKlines markPriceKlines indexPriceKlines spotKlines1hM perpKlines1hM; do
  echo "=== [$(date -u +%H:%M:%SZ)] $k ==="
  python3 rp_basis.py "$k"
done
echo "=== 基差族全部完成 $(date -u) ==="
