#!/bin/bash
# cf_legs rev 4 --arms no_ema over segment 1 and segment 2 (same trees / copy-extra as their rev-3 runs), sequential.
F=~/Desktop/quant_research/multi_asset/exports/research/lossdecomp_2026-09-25/devices/cf_legs.py; echo "cf_legs sha $(shasum -a256 $F | cut -c1-16) $(date -u +%FT%TZ)"
SEG1=$(/usr/bin/python3 -c "print(','.join(str(a) for a in range(1789646400, 1789992000+1, 14400)))")
OUT1=~/cc_tmp/nc_20260923/cf_noema_seg1_$(date -u +%H%MZ); echo "OUT1=$OUT1"
~/wide_shadow/venv/bin/python -B $F ~/cc_tmp/news_20260923/producer_copy $OUT1 "$SEG1" --tree-at 1789646400=$HOME/cc_tmp/nc_20260923/tree_old_prefp26b --copy-extra fea171/f10_live_s42_np.npz --arms no_ema > $OUT1.log 2>&1; echo "seg1 cf rc=$?"; tail -4 $OUT1.log | cut -c1-400
SEG2=$(/usr/bin/python3 -c "print(','.join(str(a) for a in range(1790020800, 1790222400+1, 14400)))")
OUT2=~/cc_tmp/nc_20260923/cf_noema_seg2_$(date -u +%H%MZ); echo "OUT2=$OUT2"
~/wide_shadow/venv/bin/python -B $F ~/cc_tmp/news_20260923/producer_copy $OUT2 "$SEG2" --copy-extra fea171/f10_live_s42_np.npz --arms no_ema > $OUT2.log 2>&1; echo "seg2 cf rc=$?"; tail -4 $OUT2.log | cut -c1-400
echo "NOEMA_DONE $(date -u +%FT%TZ)"
