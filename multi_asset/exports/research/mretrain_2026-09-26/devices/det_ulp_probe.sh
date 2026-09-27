#!/bin/bash
# det_ulp_probe.sh -- DESCRIPTIVE ONLY (lead, rule §7 follow-up; not a gate): is the last-ulp leaf_value difference between two A0 rs=0
# King trainings caused by LightGBM's non-deterministic multithreading? A scratch copy of mr_train_king.py whose ONLY change is
# deterministic=True added to params (same n_jobs=8) is trained twice CONCURRENTLY (as A0 and its duplicate were in run 1),
# models kept; then model texts, P arrays, and P vs the in-service a10b8725 P are compared. Family devices are not modified.
set -uo pipefail
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; PV=/workspace/venv/bin/python; O=/workspace/mretrain_2026-09-26/det_probe
rm -rf $O; mkdir -p $O
sed 's/n_jobs=8, verbose=-1, random_state=args.rs)/n_jobs=8, verbose=-1, random_state=args.rs, deterministic=True)/' $D/mr_train_king.py > $O/mr_train_king_det.py
diff $D/mr_train_king.py $O/mr_train_king_det.py > $O/DIFF.txt; [ "$(grep -c '^[<>]' $O/DIFF.txt)" = 2 ] || { echo "DET_PROBE FAIL scratch diff is not the one params line"; exit 1; }
cp $O/mr_train_king_det.py $D/_det_probe_king.py   # must sit in devices/ (it inserts news2 devices on sys.path by absolute path; cwd irrelevant)
cd $D
nice -n 15 $PV -B _det_probe_king.py --out $O/d1 --arm A0 --rs 0 --keep-models > $O/d1.log 2>&1 &
nice -n 15 $PV -B _det_probe_king.py --out $O/d2 --arm A0 --rs 0 --keep-models > $O/d2.log 2>&1 &
wait; rm -f $D/_det_probe_king.py
grep -q KING_DONE $O/d1.log && grep -q KING_DONE $O/d2.log || { echo "DET_PROBE FAIL training did not finish"; exit 1; }
$PV - $O $R /dev/shm/news2_2026-09-23 <<'PY'
import sys, glob, os, hashlib, numpy as np, json
O, R, N = sys.argv[1:4]
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
out = {"models_det1_vs_det2": {}, "models_det_vs_default_A0": {}}
for p in sorted(glob.glob(f"{O}/d1/king_*.txt")):
    b = os.path.basename(p); out["models_det1_vs_det2"][b] = h(p) == h(f"{O}/d2/{b}")
    out["models_det_vs_default_A0"][b] = h(p) == h(f"{R}/arms/A0_m0/work/king/{b}")
P1, P2 = np.load(f"{O}/d1/KING_OOF.npz")["P"], np.load(f"{O}/d2/KING_OOF.npz")["P"]; Pr = np.load(f"{N}/work/king/KING_OOF.npz")["P"]
out["P_det1_eq_det2"] = P1.tobytes() == P2.tobytes(); out["P_det_eq_in_service"] = P1.tobytes() == Pr.tobytes()
fin = np.isfinite(P1) & np.isfinite(Pr); out["P_det_vs_in_service_max_abs"] = float(np.abs(P1[fin] - Pr[fin]).max()) if fin.any() else None
out["P_det_vs_in_service_n_diff"] = int((P1[fin] != Pr[fin]).sum())
json.dump(out, open(f"{O}/DET_PROBE.json", "w"), indent=1); print("DET_PROBE DONE", json.dumps(out), flush=True)
PY
