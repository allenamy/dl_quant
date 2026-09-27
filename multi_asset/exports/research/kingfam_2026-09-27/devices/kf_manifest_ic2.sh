#!/bin/bash
# kf_manifest_ic2.sh -- process executor (§10-f) replacing kf_manifest_ic.sh after the lead's ruling (rule §5 addendum 1: ΔIC paired by
# member, A0 m1..m7 trained with the in-service recipe, only random_state changed). Steps, all in this process:
#  1. wait for the KN/A1 training (PGID from PGID_train.json) to end with a line-anchored KF_TRAIN_DONE arms=KN A1 (STOP / PGID gone => STOP)
#  2. train A0 m0..m7 + A0_m0_dup with kf_train_family2.sh A0 (after KN/A1, so it cannot slow them), same checks (dup bitwise)
#  3. A0_m0 scores must be bitwise the in-service scores (P sha ea78c2f6...)
#  4. MANIFEST_IC.json in dlarch's format with arms KN, A1, A0 (8 each; A0 m0 = the in-service file itself), dups separate,
#     every sha re-hashed now and checked against the per-run manifests, then "KF_MANIFEST_IC_DONE path sha=" (dlarch's IC device binds it).
set -uo pipefail
K=/workspace/kingfam_2026-09-27; LG=$K/logs/kingfam.log; D=$K/devices
REF=/dev/shm/news2_2026-09-23/work/king/KING_OOF.npz; REF_P=ea78c2f6bf3ffd0a850321ea20c8fe95d0301f46db6494a1c608365a8ccd2870
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "KF_MANIFEST_IC STOP: $*"; exit 1; }
echo "{\"what\":\"kf_manifest_ic2.sh\",\"pgid\":\"$(ps -o pgid= -p $$ | tr -d ' ')\"}" > $K/logs/PGID_manifest_ic.json
say "KF_MANIFEST_IC2_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
G=$(python3 -c "import json;print(json.load(open('$K/logs/PGID_train.json'))['pgid'])")
term() { grep -E "^\S+ (STOP|KF_TRAIN_DONE arms=KN A1)" $LG | awk '$1 >= "2026-09-27T02:39"' | tail -1; }
while :; do
  L=$(term); [ -n "$L" ] && break
  ps -o pid= -g $G > /dev/null 2>&1 || { sleep 5; L=$(term); [ -n "$L" ] && break; stop "KN/A1 training PGID $G gone without a terminal line"; }
  sleep 30
done
echo "$L" | grep -q "KF_TRAIN_DONE arms=KN A1" || stop "KN/A1 training ended with [$L]"
bash $D/kf_train_family2.sh A0 > $K/logs/train_family_A0.out 2>&1 || stop "A0 member training failed (see $K/logs/train_family_A0.out)"
grep -qE "^\S+ KF_TRAIN_DONE arms=A0 " $LG || stop "A0 training printed no KF_TRAIN_DONE"
grep -q "\"P\": \"$REF_P\"" $K/arms/A0_m0/KING_IDENTITY.json || stop "A0_m0 scores are not the in-service scores"
say "A0_m0 scores == in-service (P $REF_P)"
python3 - $K $REF <<'PY' || stop "manifest conversion failed"
import sys, json, hashlib, os
K, REF = sys.argv[1:3]; sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
out = {"arms": {}, "dups": {}, "writer": "kf_manifest_ic2.sh (fresh2)", "pairing": "rule 4158f1521 section 5 addendum 1: ΔIC_k = IC(arm m_k) − IC(A0 m_k)", "sources": {}}
for src_name, arms in (("MANIFEST_KN_A1.json", ("KN", "A1")), ("MANIFEST_A0.json", ("A0",))):
    src = f"{K}/{src_name}"; man = json.load(open(src)); out["sources"][src] = sha(src)
    for arm in arms:
        out["arms"][arm] = []
        for m in range(8):
            e = man[f"{arm}_m{m}"]; h = sha(e["oof"]); assert h == e["oof_sha256"], (arm, m)
            path, hh = e["oof"], h
            if arm == "A0" and m == 0: path, hh = REF, sha(REF)   # the in-service file itself (scores checked bitwise equal above)
            out["arms"][arm].append({"path": path, "sha256": hh, "random_state": m})
        d = man[f"{arm}_m0_dup"]; h = sha(d["oof"]); assert h == d["oof_sha256"]
        out["dups"][arm] = {"path": d["oof"], "sha256": h, "check": f"{K}/arms/{arm}_m0_dup/DUP_CHECK.json", "note": "determinism only (revision 1); not a member"}
p = f"{K}/MANIFEST_IC.json"; json.dump(out, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p); print(p, sha(p))
PY
say "KF_MANIFEST_IC_DONE $K/MANIFEST_IC.json sha=$(sha256sum $K/MANIFEST_IC.json | cut -c1-64)"
