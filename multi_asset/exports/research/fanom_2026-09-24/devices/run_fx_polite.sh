#!/bin/bash
# FX stage 1 runner that YIELDS to dlarch (lead: "dlarch 优先, 你按门排队").
# Before each arm it waits for a TIGHTER threshold than my own floor (28000 MiB cgroup headroom, 6144 MiB /dev/shm),
# so I only consume real slack instead of racing dlarch down to the floor. memgate.sh honours tightening (verified:
# passing 999999 rejects with rc=9), and the floor still applies inside fx_pipe.sh.
# rc is captured DIRECTLY, never through a pipe.
set -u
D=/dev/shm/fresh_2026-09-23/devices
TIGHT_HEAD=28000
TIGHT_SHM=6144
MAX_WAIT_MIN=600
for arm in FX1 FX2 FX3; do
  for s in 42 2027; do
    waited=0
    while : ; do
      bash "$D/memgate.sh" "$TIGHT_HEAD" "$TIGHT_SHM" > /tmp/fxgate.log 2>&1
      rc=$?
      [ "$rc" -eq 0 ] && break
      if [ "$waited" -ge "$MAX_WAIT_MIN" ]; then
        echo "GIVING UP: tight gate never opened for $arm s$s after ${MAX_WAIT_MIN}m"; tail -2 /tmp/fxgate.log; exit 9
      fi
      [ $((waited % 20)) -eq 0 ] && { echo "$(date -u +%H:%M:%SZ) yielding to dlarch before $arm s$s:"; tail -1 /tmp/fxgate.log; }
      sleep 120; waited=$((waited + 2))
    done
    echo "===== $arm s$s (tight gate open after ${waited}m) ====="
    # ★ BUILD ON DEMAND. Pre-building all six arms up front parked ~2.4 GiB of /dev/shm and blocked MY OWN tight
    # gate for 1h40m -- I was queued behind my own artefacts, not behind dlarch. The combo is regenerable by
    # fa_fx.py in under a minute from pinned inputs, so it is built here, immediately before its run, and
    # fx_pipe.sh frees it again after the verified series is saved.
    NC=/dev/shm/news2_2026-09-23; FA=/dev/shm/fanom_2026-09-24
    env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B "$D/fa_fx.py" PATH,HOME,LC_CTYPE       "$arm" "$s" "$NC/work/combo_s$s" "$NC/work/NEWS_FEATURES.npz" "$FA/fx/FXRATE.npz" "$FA/fx/${arm}_s$s"       > "$FA/logs/fxbuild_${arm}_s${s}.log" 2>&1
    brc=$?
    if [ "$brc" -ne 0 ]; then echo "  combo build FAILED rc=$brc"; tail -3 "$FA/logs/fxbuild_${arm}_s${s}.log"; exit "$brc"; fi
    grep -hE "scaled_diagnostic|literal" "$FA/logs/fxbuild_${arm}_s${s}.log" | sed "s/^/  /"
    bash "$D/fx_pipe.sh" "$s" "$arm"
    rc=$?
    echo "  pipe_rc=$rc"
    [ "$rc" -ne 0 ] && { echo "STOPPING: $arm s$s failed rc=$rc"; exit "$rc"; }
  done
done
echo "ALL FX DONE"
ls -la /dev/shm/fanom_2026-09-24/receipts/SER_FX*.npz
