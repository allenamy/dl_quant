#!/bin/bash
# cf_legs rev 5 base-arm replays with the F10 dump over 09-19 00Z .. 09-27 00Z, in the 00Z quiet window (cf_legs itself enforces it per anchor)
until [ "$(date -u +%H%M)" -ge 0107 ] && [ "$(date -u +%H%M)" -lt 0300 ]; do sleep 60; done
F=~/Desktop/quant_research/multi_asset/exports/research/lossdecomp_2026-09-25/devices/cf_legs.py; echo "cf_legs sha $(shasum -a256 $F | cut -c1-16) $(date -u +%FT%TZ)"
S1=$(/usr/bin/python3 -c "print(','.join(str(a) for a in range(1789776000, 1789992000+1, 14400)))")
S2=$(/usr/bin/python3 -c "print(','.join(str(a) for a in range(1790020800, 1790222400+1, 14400)))")
S3=$(/usr/bin/python3 -c "print(','.join(str(a) for a in range(1790236800, 1790409600+1, 14400)))")
S4="1790452800,1790467200"
O1=~/cc_tmp/nc_20260923/mom_dump_old_$(date -u +%H%MZ); echo "O1=$O1"
~/wide_shadow/venv/bin/python -B $F ~/cc_tmp/news_20260923/producer_copy $O1 "$S1;$S2" --copy-extra fea171/f10_live_s42_np.npz --arms base --dump-f10 > $O1.log 2>&1; echo "old rc=$?"; tail -3 $O1.log | cut -c1-300
O2=~/cc_tmp/nc_20260923/mom_dump_nc_$(date -u +%H%MZ); echo "O2=$O2"
~/wide_shadow/venv/bin/python -B $F ~/cc_tmp/nc_20260923/treeNC7 $O2 "$S3;$S4" --arms base --dump-f10 > $O2.log 2>&1; echo "nc rc=$?"; tail -3 $O2.log | cut -c1-300
echo "MOM_DUMP_DONE $(date -u +%FT%TZ)"
