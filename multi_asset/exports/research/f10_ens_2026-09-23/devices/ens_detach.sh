#!/bin/bash
# ens_detach.sh LABEL -- CMD...  : run CMD detached in its own session (setsid); log to logs/LABEL.log (+ EXIT line); PGID to logs/LABEL.pgid
R=/dev/shm/f10_ens_2026-09-23
L=$1; shift; [ "$1" = "--" ] && shift
cd $R/devices
setsid bash -c 'echo $$ > '"$R/logs/$L.pgid"'; "$@" > '"$R/logs/$L.log"' 2>&1; echo "EXIT $?" >> '"$R/logs/$L.log" _ "$@" < /dev/null > /dev/null 2>&1 &
disown
sleep 1
echo "LAUNCHED $L PGID=$(cat $R/logs/$L.pgid)"
