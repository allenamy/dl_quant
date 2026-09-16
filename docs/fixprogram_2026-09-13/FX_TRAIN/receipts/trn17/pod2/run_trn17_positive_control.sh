#!/bin/bash
# FX-TRAIN TRN-17 positive control: rerun the legs builder on SEPTEMBER's real inputs (read-only) with the fixed source and the
# archived pre-fix source, into MY sandbox, and compare both outputs bitwise with the September product /workspace/f8_v4/data/f10v2_legs.npz.
# Writes only under /workspace/fx_train_2026-09-13/. Nothing in /workspace/f8_v4 or /workspace/data is touched.
set -o pipefail
DEV=/workspace/fx_train_2026-09-13/trn17_dev; OUTD=/workspace/fx_train_2026-09-13/receipts/trn17; PY=/workspace/venv/bin/python
mkdir -p $OUTD $DEV/out
echo "START $(date -u +%FT%TZ)"
sha256sum $DEV/pod_legs_v4b.py $DEV/pod_legs_v4b.r1_8c33a230.py
PROT="/workspace/f8_v4/data/f10v2_legs.npz /workspace/data/wide_panel_4h_v3splice.npz /workspace/f8_ext/data/f10v2_legs.npz"
nice -n 19 sha256sum $PROT | tee $OUTD/protected_sha_before.txt
E="LEGS_TG=/workspace/dlw_v4raw/data/dlw_targets.npz LEGS_META=/workspace/data/wide_fea_v4_meta.npz LEGS_PRED=/workspace/shadow_bundle_v4/slow_pred_pinned.npy LEGS_OLD=/workspace/f8_ext/data/f10v2_legs.npz LEGS_PANEL=/workspace/data/wide_panel_4h_v3splice.npz"
nice -n 19 env -i PATH=/usr/bin:/bin HOME=/root $E LEGS_OUT=$DEV/out/legs_fixed.npz LEGS_MAX_NO_PANEL=5 $PY $DEV/pod_legs_v4b.py 2>&1 | tee $OUTD/legs_fixed.log
echo "FIXED rc=${PIPESTATUS[0]}"
nice -n 19 env -i PATH=/usr/bin:/bin HOME=/root $E LEGS_OUT=$DEV/out/legs_prefix.npz $PY $DEV/pod_legs_v4b.r1_8c33a230.py 2>&1 | tee $OUTD/legs_prefix.log
echo "PREFIX rc=${PIPESTATUS[0]}"
nice -n 19 env -i PATH=/usr/bin:/bin HOME=/root $E LEGS_OUT=$DEV/out/legs_bound4.npz LEGS_MAX_NO_PANEL=4 $PY $DEV/pod_legs_v4b.py 2>&1 | tee $OUTD/legs_bound4.log
echo "BOUND4 rc=${PIPESTATUS[0]}"
ls -la $DEV/out | tee $OUTD/out_listing.txt
$PY - <<'PYEOF' 2>&1 | tee $OUTD/compare.txt
import numpy as np, json, os
REF="/workspace/f8_v4/data/f10v2_legs.npz"
out={}
for tag,p in (("fixed","/workspace/fx_train_2026-09-13/trn17_dev/out/legs_fixed.npz"),
              ("prefix","/workspace/fx_train_2026-09-13/trn17_dev/out/legs_prefix.npz"),
              ("bound4","/workspace/fx_train_2026-09-13/trn17_dev/out/legs_bound4.npz")):
    if not os.path.exists(p): out[tag]="ABSENT (refused)"; continue
    a,b=np.load(p,allow_pickle=True),np.load(REF,allow_pickle=True)
    out[tag]={k:bool(np.array_equal(a[k],b[k],equal_nan=True)) for k in ("Z24","ZFD","WL","E_ts")}
    m=json.loads(str(a["meta_json"])); out[tag]["meta_no_panel_bound"]=m.get("no_panel_bound"); out[tag]["meta_panel_end_utc"]=m.get("panel_end_utc")
    out[tag]["n_no_panel"]=len(m.get("new_rows_without_panel_row",[]))
print(json.dumps(out,indent=1))
PYEOF
nice -n 19 sha256sum $PROT | tee $OUTD/protected_sha_after.txt
echo "END $(date -u +%FT%TZ)"
