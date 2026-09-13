#!/bin/zsh
# members_stage.sh -- AUDIT_PROD item 3: stage inputs to pod2 (copy + remote sha verification only; no statistic).
# Verbatim use (Mac, outside anchor windows):  zsh docs/audit_pipeline_2026-09-13/devices_prod/members/members_stage.sh
set -eu
R=/Users/haosiyu/Desktop/quant_research; D=$R/docs/audit_pipeline_2026-09-13/devices_prod/members; S=/Users/haosiyu/cc_tmp/aud_prod/members/stage
SNAP=$R/multi_asset/exports/research/uplift_r2_2026-09-13/T4/private/snapshot_1789272000/state/rolling.npz
P=/workspace/aud_prod_2026-09-13/members
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B $D/members_stage.py PATH,HOME,LC_CTYPE,CPATH,LIBRARY_PATH,MANPATH,SDKROOT,__CF_USER_TEXT_ENCODING
ssh pod2 "mkdir -p $P/stage $P/receipts $P/device"
scp -q $S/config.json $S/prod_members.npz $S/prod_prev_rec_1789272000.json $S/manifest.json pod2:$P/stage/
scp -q $SNAP pod2:$P/stage/snapshot_rolling_1789272000.npz
scp -q $D/members_audit.py $D/members_run_pod2.sh pod2:$P/device/
ssh pod2 "cd $P && sha256sum stage/* device/*" > $S/remote_sha256.txt
/usr/bin/python3 - <<PY
import json
man = json.load(open("$S/manifest.json")); rem = {}
for ln in open("$S/remote_sha256.txt"):
    d, p = ln.split(); rem[p.split("/")[-1]] = d
exp = dict(man["staged"]); exp["snapshot_rolling_1789272000.npz"] = exp.pop("snapshot_rolling.npz")
bad = {k: (v[:16], rem.get(k, "MISSING")[:16]) for k, v in exp.items() if rem.get(k) != v}
import hashlib
for fn in ("members_audit.py", "members_run_pod2.sh"):
    loc = hashlib.sha256(open("$D/" + fn, "rb").read()).hexdigest()
    if rem.get(fn) != loc: bad[fn] = (loc[:16], rem.get(fn, "MISSING")[:16])
out = {"stage_manifest": man, "remote_sha256": rem, "mismatches": bad, "PASS": not bad}
json.dump(out, open("$R/docs/audit_pipeline_2026-09-13/receipts_prod/members_stage.json", "w"), indent=1)
print("STAGE_VERIFY", "PASS" if not bad else "FAIL", bad)
PY
