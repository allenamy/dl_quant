#!/bin/bash
# Rerun ONLY stats + ext, with the fixed invocation (lead go, 2026-09-24 02:0xZ).
# Upstream products are not touched; the manifest before/after proves it.
set -e
W=/dev/shm/news2_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs; R=$W/receipts/engine
NS=/dev/shm/news_2026-09-23; S1=/dev/shm/ovn_2026-09-23; B=/workspace/baseline_tables_2026-09-19
PV=/workspace/venv/bin/python
GATE=$D/news2_env_gate.py
LOG=$L/rerun_stats_ext.log
exec > >(tee -a $LOG) 2>&1
echo "==== rerun stats+ext $(date -u +%H:%M:%SZ) ===="

# lead req: estimate the write volume BEFORE writing.
echo "-- write-volume estimate (basis: the NEW_S equivalents) --"
echo "   NEWS_STATS.json  264,377 bytes  -> NEWS2_STATS.json expected same order, plus the env_per_step /"
echo "                                      engine-memory / shm-headroom blocks embedded verbatim, so budget ~0.5 MB"
echo "   NEWS_EXT.json      4,990 bytes  -> NEWS2_EXT.json  expected same order, ~5 KB"
echo "   total budget     < 1 MB against $(df -k /dev/shm | tail -1 | awk '{printf "%.2f", $4/1048576}') GiB free"
df -k /dev/shm | tail -1 | awk '{printf "   df free before: %.3f GiB\n", $4/1048576}'

# lead req 1: measured sha of the three imported devices, against the pins.
echo "-- the three imported devices: measured vs pinned --"
NEWS2_NEWS_DEVICES=$E $PV - <<'PYEOF'
import hashlib, os, sys
E = os.environ["NEWS2_NEWS_DEVICES"]
sys.path.insert(0, E)
import news_stats as NS
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
PIN = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
rows = [("news_stats.py", PIN)] + sorted(NS.DEV.items())
bad = 0
for f, pin in rows:
    got = sha(os.path.join(E, f))
    ok = got == pin
    bad += (not ok)
    print(f"   {f:18s} measured {got[:32]} pinned {pin[:32]} {'MATCH' if ok else 'MISMATCH'}")
print(f"   resolved dir: {E}")
print("   ALL THREE MATCH" if not bad else f"   {bad} MISMATCH -> refuse")
sys.exit(1 if bad else 0)
PYEOF

cd $E
echo "-- stats --"
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check stats $R/ENV_GATE_stats.json
set +e
env -i PATH=/usr/bin:/bin HOME=/root NEWS2_NEWS_DEVICES=$E nice -n 15 $PV -B news2_stats.py PATH,HOME,LC_CTYPE,NEWS2_NEWS_DEVICES \
  $S1/runs $NS/runs $W/runs $B/runs \
  $S1/receipts/BT_P_READING_OVN_OLD.json $S1/receipts/BT_P_READING_OVN_OLD_HOLD.json \
  $NS/receipts/engine/BT_P_READING_NEWS_s42.json $NS/receipts/engine/BT_P_READING_NEWS_s2027.json \
  $R/BT_P_READING_NEWS2_s42.json $R/BT_P_READING_NEWS2_s2027.json \
  $R/NEWS2_STATS.json > $L/chain_stats.log 2>&1
STATS_RC=$?
set -e
echo "   STATS_RC=$STATS_RC"
tail -4 $L/chain_stats.log
if [ $STATS_RC -ne 0 ]; then echo "STOP: stats rc=$STATS_RC, not running ext"; exit $STATS_RC; fi

echo "-- ext --"
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check ext $R/ENV_GATE_ext.json
set +e
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news2_ext.py PATH,HOME,LC_CTYPE $W/runs $B/runs $R/NEWS2_EXT.json > $L/chain_ext.log 2>&1
EXT_RC=$?
set -e
echo "   EXT_RC=$EXT_RC"
tail -3 $L/chain_ext.log

echo "-- actual write volume --"
for f in NEWS2_STATS.json NEWS2_EXT.json; do [ -f $R/$f ] && ls -l $R/$f | awk '{printf "   %s %s bytes\n", $NF, $5}'; done
df -k /dev/shm | tail -1 | awk '{printf "   df free after: %.3f GiB\n", $4/1048576}'

echo "-- lead req 2: upstream unchanged? --"
python3 $D/upstream_manifest.py $R/UPSTREAM_MANIFEST_POST.json
python3 - <<'PYEOF'
import json
R = "/dev/shm/news2_2026-09-23/receipts/engine"
a = json.load(open(f"{R}/UPSTREAM_MANIFEST_PRE.json"))
b = json.load(open(f"{R}/UPSTREAM_MANIFEST_POST.json"))
same = a["composite_digest"] == b["composite_digest"]
print(f"   pre  composite {a['composite_digest'][:32]} n_files {a['n_files']}")
print(f"   post composite {b['composite_digest'][:32]} n_files {b['n_files']}")
moved = sorted(k for k in set(a["entries"]) | set(b["entries"])
               if a["entries"].get(k) != b["entries"].get(k))
print("   UPSTREAM UNCHANGED" if same and not moved else f"   UPSTREAM CHANGED: {moved[:10]}")
PYEOF
echo "==== RERUN_DONE $(date -u +%H:%M:%SZ) ===="
