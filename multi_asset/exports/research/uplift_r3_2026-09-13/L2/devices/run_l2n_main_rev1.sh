#!/bin/bash
# run_l2n_main_rev1.sh — re-run ONLY the S1 MAIN stage with l2n_judge_rev1.py (device swap approved by the lead 2026-09-27 06:4xZ:
# the one-line change DATA[s] = dict(np.load(...)) removes the per-anchor npz re-decompression that made MAIN ~31.6 h; rule, thresholds,
# seed streams unchanged; identity control IDENTITY_judge_rev1.json). The RESOLUTION receipt is not touched: it is pinned by sha below.
# Pre-write probe of 64 MiB on /workspace (EDQUOT, lead 06:1xZ). Markers on tmpfs with read-back; terminal '^STOP ' / '^DONE '.
set -u
D=/workspace/uplift_r3_2026-09-13/L2/devices; REC=/workspace/uplift_r3_2026-09-13/L2/receipts; S=/dev/shm/alloc_2026-09-26/l2n
LOG=$S/l2n_main_rev1.log; PY=/workspace/venv/bin/python
RES_SHA=c8633f5573a48e94df07c5e24909e0f1803d8a7cf4ba70a0d371291259bb28ef
JUDGE_SHA=2f54f1554d8d59fa25ea9651a1ddfe3c3cba6c9eb95076fcdcf7756081e32f3c
mkdir -p $S || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $S/PGID_main_rev1; [ "$(cat $S/PGID_main_rev1)" = "$PG" ] || exit 9
mark "START l2n_main_rev1 $(date -u +%FT%TZ) pgid=$PG"
[ "$(sha256sum $REC/RECEIPT_L2N_judge_RESOLUTION.json | cut -d' ' -f1)" = "$RES_SHA" ] || stop "resolution_receipt_sha_changed"
[ "$(sha256sum $D/l2n_judge_rev1.py | cut -d' ' -f1)" = "$JUDGE_SHA" ] || stop "judge_rev1_sha_mismatch"
[ -e $REC/RECEIPT_L2N_judge_MAIN.json ] && stop "main_receipt_already_exists"
P=$REC/.alloc_write_probe_$$
dd if=/dev/zero of=$P bs=1M count=64 conv=fsync status=none || { rm -f $P; stop "write_probe_64MiB_failed"; }
[ "$(stat -c %s $P)" = "67108864" ] || { rm -f $P; stop "write_probe_short"; }
rm -f $P || stop "write_probe_rm_failed"
mark "GATE_OK write_probe 64MiB"
W=PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS
cd $D || stop "no_devices"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
  nice -n 10 taskset -c 48-55 $PY -B l2n_judge_rev1.py $W MAIN > $S/l2n_judge_MAIN_rev1.log 2>&1 || stop "judge_main_rc"
grep -q '^L2N_JUDGE_MAIN VERDICT=' $S/l2n_judge_MAIN_rev1.log || stop "judge_main_verdict_line_missing"
# read-back: the receipt parses, carries the rev1 device sha, and its file sha matches the prefix the judge printed
$PY -B -c "
import json,hashlib,sys
p='$REC/RECEIPT_L2N_judge_MAIN.json'; b=open(p,'rb').read(); r=json.loads(b)
assert r['self_sha256']=='$JUDGE_SHA', r['self_sha256']; assert r['resolution_receipt_sha256']=='$RES_SHA'
pre=open('$S/l2n_judge_MAIN_rev1.log').read().strip().split()[-1]; assert hashlib.sha256(b).hexdigest().startswith(pre), pre
" || stop "main_receipt_readback_failed"
mark "VERDICT_OK $(tail -1 $S/l2n_judge_MAIN_rev1.log)"
mark "DONE $(date -u +%FT%TZ)"
