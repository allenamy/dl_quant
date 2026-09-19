set -u
cd /Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FP3_devices
R=../FP3_receipts/venue_readonly_2026-09-19
echo "start $(date -u +%FT%TZ)"
python3 -c "import sys; sys.path.insert(0,'../../../multi_asset/exports/research/common'); import venue_quiet_window as Q; print(Q.require_quiet_window(60))" || exit 9
tail -1 ~/dl_quant_live/state/anchor_runs.log
/usr/bin/python3 -B ro_controls.py > $R/FLATTEN_CLOSURE_v43fresh_ro_controls_2026-09-19.txt 2>&1; echo "ro_controls rc=$?"
grep -q "consistent with a read-only key" $R/FLATTEN_CLOSURE_v43fresh_ro_controls_2026-09-19.txt || { echo "STOP: read-only negative control not confirmed"; exit 8; }
while read E T0 T1; do
  /usr/bin/python3 -B flatten_window_closure.py $T0 $T1 $R/FLATTEN_CLOSURE_v43fresh_$E.json $R/FLATTEN_CLOSURE_v43fresh_${E}_venue_trades.json --bnb-rows $R/INCOME_ALL_20260731_now.json --event $E > $R/FLATTEN_CLOSURE_v43fresh_$E.log 2>&1
  echo "$E rc=$? $(date -u +%TZ)"
done <<W
FLATTEN-20260821T121630Z 1787314570.9543638 1787329180.200428
FLATTEN-20260821T201600Z 1787343345.308213 1787357763.6213398
FLATTEN-20260826T124702Z 1787748333.642869 1787762283.433176
FLATTEN-20260906T084608Z 1788684263.67789 1788698342.895093
FLATTEN-20260909T164536Z 1788972245.856354 1788986342.424868
FLATTEN-20260912T124737Z 1789217147.803424 1789231143.365168
W
echo "end $(date -u +%FT%TZ)"
