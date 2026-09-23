#!/bin/zsh
# R10 A.4-5 「β 原始价 vs f16 裁剪」数值验证 — the commands run on 2026-09-23 (13:2x-13:4xZ), in order, copied from the session transcript.
# Read-only on ~/wide_shadow (copies only), ~/dl_quant_live untouched, no exchange call. Local: /usr/bin/python3 (3.9.6, numpy 1.26.4).
# pod2: /workspace/venv/bin/python (3.11.10, numpy 2.4.6), CPU only, writes only under /workspace/m3_beta_parity_2026-09-23/.
set -e
IN=/Users/haosiyu/cc_tmp/m3_impl_20260923/beta_parity/inputs          # rolling_copy.npz was placed here by the caller (13:20Z copy, sha 73018d36…51e3)
OUT=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_impl_2026-09-23/beta_parity

# 0. input copies (read-only sources)
cp -p /Users/haosiyu/wide_shadow/fea171/xfer_syms.npz $IN/xfer_syms.npz
mkdir -p $IN/target_live; cd /Users/haosiyu/wide_shadow/state/target_live/; for A in $(/usr/bin/python3 -c "print(' '.join(str(a) for a in range(1789315200,1789776001,14400)))"); do cp -p $A.json $A.json.sha256 $IN/target_live/; done
cp -p /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3b_2026-09-23/devices/m2_lib.py $OUT/devices/m2_lib.py   # sha 93f8e760… (== m2_btc_overlay_2026-09-23/devices/m2_lib.py)

# 1. stage 1 — PRODUCTION betas (beta_overlay_producer.compute on the cache copy) + revision check vs ~/wide_shadow/state/snap (read-only)
cd $OUT && /usr/bin/python3 -B devices/s1_prod_betas_local.py $OUT 2>&1 | tee work/S1_prod_local.log

# 2. the cache clip-cell list handed to pod2
cd $OUT && /usr/bin/python3 -B -c "
import numpy as np, json
z=np.load('work/S1_prod_local.npz')
syms=[str(s) for s in z['cache_syms']]
cells=[[int(t), syms[int(c)]] for t,c in zip(z['clip_ts'], z['clip_col'])]
json.dump(cells, open('work/clip_cells.json','w'))
print(len(cells), cells[:20])
"
scp -q devices/s2_eval_betas_pod2.py devices/m2_lib.py work/clip_cells.json pod2:/workspace/m3_beta_parity_2026-09-23/

# 3. stage 2 — EVALUATION betas on pod2 (m2_lib.bars_4h + betas_at on price_full_raw_x0918r; recorded PID 2286531, exited 0)
ssh pod2 'cd /workspace/m3_beta_parity_2026-09-23 && nohup env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B s2_eval_betas_pod2.py PATH,HOME,LC_CTYPE /workspace/m3_beta_parity_2026-09-23/out /workspace/m3_beta_parity_2026-09-23/clip_cells.json > s2.log 2>&1 < /dev/null & echo PID=$! | tee s2.pid; date -u'
cd $OUT/work && scp -q pod2:/workspace/m3_beta_parity_2026-09-23/out/S2_eval_pod2.npz pod2:/workspace/m3_beta_parity_2026-09-23/out/S2_eval_pod2.json pod2:/workspace/m3_beta_parity_2026-09-23/s2.log . && mv s2.log S2_eval_pod2.log

# 4. stage 3 — comparison (local)
cd $OUT && /usr/bin/python3 -B devices/s3_compare_local.py $OUT 2>&1 | tee work/S3_compare_local.log
