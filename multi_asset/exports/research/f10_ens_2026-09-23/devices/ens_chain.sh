#!/bin/sh
# ens_chain.sh — prereg 45aba1f3f steps 4-5 prep (pod2, CPU only). VERBATIM commands; stops at the first non-zero exit.
#   1. adapter spec for NEW_ENS (same fields as Stage 1's ADAPTER_SPEC_NEW_s42.json; only arm / data / the three NEW_ENS paths + shas differ)
#   2. Stage 1's ovn_adapter.py (17555e56, copied sha-equal): NEW_ENS combo -> certified CSR + bitwise round trip through bt_objb_targets
#   3. Stage 1's ovn_adapter_test.py (878331f6) on the NEW_ENS spec: baseline green, 5 mutations red as named
#   4. ens_make_config.py: RUN_CONFIG_F10ENS_NEW_ENS from Stage 1's NEW_s42 config (162239b6), leaf diff asserted
set -e
R=/dev/shm/f10_ens_2026-09-23; S=$R; C=$R/work/combo_ENS   # active root on /dev/shm: /workspace returned EDQUOT at 08:25Z
PY="env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B"
cd $R/devices
mkdir -p $S/targets $S/scratch
$PY -c "
import json,hashlib
def sha(p):
    h=hashlib.sha256(); h.update(open(p,'rb').read()); return h.hexdigest()
T=json.load(open('/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s42.json'))
assert sha('/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s42.json')=='c9d67e91949348fdfdb6eed18fc1abdf7f50c7ba1d2451945596b46261998364','Stage 1 spec != committed e6d8f6680 copy'
S=dict(T); S['arm']='NEW_ENS'; S['data']='f10_ens_2026-09-23 combo_ENS (ens_combo.py --f10 ens; F10 = equal-weight rank average of seeds 42 and 2027)'
S['scaled']={'npz':'$C/scaled_diagnostic.npz','sha256':sha('$C/scaled_diagnostic.npz')}
S['lit']={'npz':'$C/literal.npz','sha256':sha('$C/literal.npz')}
S['new_receipt']={'path':'$C/TARGET_RECEIPT.json','sha256':sha('$C/TARGET_RECEIPT.json')}
changed=sorted(k for k in set(S)|set(T) if S.get(k)!=T.get(k)); assert changed==['arm','data','lit','new_receipt','scaled'],changed
json.dump(S,open('$R/devices/ADAPTER_SPEC_NEW_ENS.json','w'),indent=1); print('SPEC written; changed keys vs NEW_s42 spec:',changed)
"
$PY ovn_adapter.py PATH,HOME,LC_CTYPE $R/devices/ADAPTER_SPEC_NEW_ENS.json $S/targets/TARGETS_NEW_ENS.npz $S/targets/TARGETS_NEW_ENS.json
$PY ovn_adapter_test.py PATH,HOME,LC_CTYPE $R/devices/ADAPTER_SPEC_NEW_ENS.json $S/scratch/adapter_test_ENS $R/receipts/OVN_ADAPTER_TEST_NEW_ENS.json
cp -p $S/targets/TARGETS_NEW_ENS.json $R/receipts/TARGETS_NEW_ENS.json
$PY ens_make_config.py PATH,HOME,LC_CTYPE /workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s42_2026-09-23.json 162239b6e397c0aa2b017109b90e59a5cd1b54227ccae6b2321045f977f4533b $S/targets/TARGETS_NEW_ENS.json $S/targets/TARGETS_NEW_ENS.npz $R/RUN_CONFIG_F10ENS_NEW_ENS_2026-09-23.json $R/receipts/ENS_CONFIG_DIFF.json
echo "ENS_CHAIN DONE"
