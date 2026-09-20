#!/bin/bash
# memsample.sh PGID OUT : every 5 s, cgroup anon/shmem/file, memory PSI, and per-process Pss / Private_Dirty of the process group
PG=$1; OUT=$2
while true; do
  now=$(date -u +%H:%M:%S)
  cg=$(awk '$1=="anon"||$1=="shmem"||$1=="file"{printf "%s=%.2fG ", $1, $2/2^30}' /sys/fs/cgroup/memory.stat)
  psi=$(head -1 /proc/pressure/memory | awk '{print $2}')
  tot=0; n=0; det=""
  for p in $(ps -eo pid=,pgid= | awk -v g=$PG '$2==g{print $1}'); do
    if [ -r /proc/$p/smaps_rollup ]; then
      pss=$(awk '$1=="Pss:"{print $2}' /proc/$p/smaps_rollup); pd=$(awk '$1=="Private_Dirty:"{print $2}' /proc/$p/smaps_rollup)
      tot=$((tot+pss)); n=$((n+1)); det="$det $p:pss=$((pss/1024))M,pd=$((pd/1024))M"
    fi
  done
  echo "$now $cg psi_$psi procs=$n ownPss=$((tot/1024))M |$det" >> $OUT
  [ $n -eq 0 ] && break
  sleep 5
done
