#!/bin/bash
# kf_gate0.sh -- device gates of the King improvement family that need no T_net (fresh2 2026-09-27; rule 4158f1521 §3 + revision-1 identity):
#  G0a  kf_train_king.py --label y4s (in-service path of the NEW trainer) A0 rs=0  => scores bitwise == in-service a10b8725 (mr_gates oof_equal)
#  G0b  known-answer of the KN code path: --label tnet with a synthetic T_NET whose funding term is 0 everywhere (T_NET = PRICE = y4s)
#       => scores bitwise == a10b8725, i.e. the tnet path changes nothing but the label
#  G0c  red: the same synthetic file with ONE T_net cell changed by 1 ulp => the trainer must refuse (T_net != y4s - F), no OOF written
set -uo pipefail
K=/workspace/kingfam_2026-09-27; D=$K/devices; PV=/workspace/venv/bin/python; G=$K/gate; MG=/dev/shm/mretrain_2026-09-26/devices/mr_gates.py
REF=/dev/shm/news2_2026-09-23/work/king/KING_OOF.npz; NEWT=/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $K/logs/kingfam.log; }
mkdir -p $G $K/logs; rm -rf $G/G0a $G/G0b $G/G0c
say "KF_GATE0_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
$PV - $NEWT $G <<'PY'
import sys, numpy as np, hashlib
T = np.load(sys.argv[1], allow_pickle=True); G = sys.argv[2]; y = T["y4s"].astype(np.float64); f = np.zeros_like(y); cov = np.ones(y.shape, bool)
np.savez(f"{G}/TNET_ZERO_FUND.npz", E_ts=T["E_ts"], symbols=T["symbols"], T_net=y - f, F=f, covered=cov)   # dlarch's T_NET format (1231f7f72)
t = y - f; i = np.flatnonzero(np.isfinite(t.ravel()))[1000]; t.ravel()[i] = np.nextafter(t.ravel()[i], 1.0)
np.savez(f"{G}/TNET_BAD_PRICE.npz", E_ts=T["E_ts"], symbols=T["symbols"], T_net=t, F=f, covered=cov)
print("synthetic T_NET written", y.dtype)
PY
Z=$(sha256sum $G/TNET_ZERO_FUND.npz | cut -c1-64); B=$(sha256sum $G/TNET_BAD_PRICE.npz | cut -c1-64)
cd $D
nice -n 12 $PV -B kf_train_king.py --out $G/G0a --arm A0 --rs 0 --label y4s > $G/G0a.log 2>&1 &
nice -n 12 $PV -B kf_train_king.py --out $G/G0b --arm A0 --rs 0 --label tnet --tnet $G/TNET_ZERO_FUND.npz --tnet-sha $Z > $G/G0b.log 2>&1 &
nice -n 12 $PV -B kf_train_king.py --out $G/G0c --arm A0 --rs 0 --label tnet --tnet $G/TNET_BAD_PRICE.npz --tnet-sha $B > $G/G0c.log 2>&1 &
wait
ok=1
for g in G0a G0b; do
  $PV -B $MG --dup $G/$g/KING_OOF.npz $REF $G/$g/VS_IN_SERVICE.json > $G/$g.cmp 2>&1
  grep -q "^MR_DUP PASS=True" $G/$g.cmp || ok=0; say "$g $(head -c 200 $G/$g.cmp)"
done
if grep -q "must be bitwise y4s - F" $G/G0c.log && [ ! -e $G/G0c/KING_OOF.npz ]; then say "G0c refused as expected"; else ok=0; say "G0c NOT refused"; fi
[ $ok -eq 1 ] && say "KF_GATE0 PASS" || say "KF_GATE0 FAIL"
