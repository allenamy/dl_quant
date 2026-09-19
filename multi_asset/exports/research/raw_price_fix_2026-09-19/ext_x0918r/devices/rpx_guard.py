#!/usr/bin/env python3
"""rpx_guard.py — run one R5-02 extension step on the shared pod2 only when it cannot disturb the queued stream-D king job, then hand the step to
stream D's memory guard (ax_memguard.py v2, sha pinned) for the 20-GiB-after-peak admission and the yield watchdog.

usage: python rpx_guard.py <guard_receipt.json> <peak_GiB> -- <cmd> [args...]        (exit code = the step's; 75 = gave up waiting)
Pre-admission (every POLL s, all conditions at the same check; each check appended to the receipt):
  K1  no process of the king job's process group (KING_PGID) other than its bash driver and its ax_memguard.py is alive
      (= the king builder / r10 meta / r11 proof is not running);
  K2  if the king group is still alive (queued): its newest memguard receipt's (logs/mem_*.json by mtime) last check has quiet_streak == 0, and the cgroup's non-reclaimable use
      (anon + shmem) is >= ALONE + KSLACK GiB — i.e. other agents already hold more than the king's "run alone" limit, so a short step of mine
      cannot be what delays its quiet period;
  M   host MemAvailable - peak >= 20 GiB and cgroup max - (anon + shmem) - peak >= 20 GiB (checked again, identically, by ax_memguard).
Then: python ax_memguard.py <guard_receipt>.memguard.json <peak> -- <cmd>  (AX_MG_* defaults: margin 20, quiet 1, yield 0.5 GiB).
Never signals any process itself; ax_memguard only ever kills the process group it started (mine).
"""
import json, os, subprocess, sys, time, hashlib
RPT = sys.argv[1]; PEAK = float(sys.argv[2]); assert sys.argv[3] == "--"; CMD = sys.argv[4:]
KING_PGID = int(os.environ.get("RPX_KING_PGID", "1274556"))
KING_LOGDIR = os.environ.get("RPX_KING_LOGDIR", "/workspace/axis_0919/x0918r/logs")          # the newest mem_*.json there = the king chain's current guard
MEMGUARD = ("/workspace/axis_0919/devices/ax_memguard.py", "689f72e60337040337297db1990b223e292c61875971d8368d96b52c838fdb09")
PY = "/workspace/venv/bin/python"; G = 1024 ** 3
ALONE, KSLACK, MARGIN = 2.0, 2.0, 20.0; POLL = 60; MAXW = int(os.environ.get("RPX_MAX_WAIT_S", str(8 * 3600)))


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def cg():
    mx = int(open("/sys/fs/cgroup/memory.max").read().strip())
    st = {ln.split()[0]: int(ln.split()[1]) for ln in open("/sys/fs/cgroup/memory.stat")}
    return mx, st["anon"] + st.get("shmem", 0)
def avail():
    for ln in open("/proc/meminfo"):
        if ln.startswith("MemAvailable:"): return int(ln.split()[1]) * 1024
def king_procs():
    out = subprocess.run(["ps", "-eo", "pid,pgid,rss,args"], capture_output=True, text=True).stdout.splitlines()[1:]
    return [ln.strip()[:200] for ln in out if len(ln.split()) >= 4 and int(ln.split()[1]) == KING_PGID]


assert sha(MEMGUARD[0]) == MEMGUARD[1], "ax_memguard.py changed"
state = dict(device="rpx_guard.py", self_sha256=sha(os.path.abspath(__file__)), cmd=CMD, peak_GiB=PEAK, king_pgid=KING_PGID, king_logdir=KING_LOGDIR, checks=[])
def dump(): json.dump(state, open(RPT, "w"), indent=1)
t0 = time.time()
while True:
    kp = king_procs(); busy = [p for p in kp if not (p.split(None, 3)[3].startswith("bash ") or "ax_memguard.py" in p)]
    ks = None
    logs = sorted((os.path.join(KING_LOGDIR, f) for f in os.listdir(KING_LOGDIR) if f.startswith("mem_") and f.endswith(".json")), key=os.path.getmtime) if os.path.isdir(KING_LOGDIR) else []
    if kp and logs:
        try:
            kl = json.load(open(logs[-1])); last = kl["checks"][-1] if kl.get("checks") else {}
            ks = dict(log=logs[-1], state=kl.get("state"), last_utc=last.get("utc"), quiet_streak=last.get("quiet_streak"), ok=last.get("ok"))
        except Exception as e:
            ks = dict(error=repr(e))
    mx, used = cg(); av = avail()
    k1 = not busy
    k2 = (not kp) or (ks is not None and ks.get("state") == "WAITING" and ks.get("quiet_streak") == 0 and used / G >= ALONE + KSLACK)
    m = av / G - PEAK >= MARGIN and (mx - used) / G - PEAK >= MARGIN
    ok = k1 and k2 and m
    state["checks"].append(dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), king_group_alive=bool(kp), king_busy=busy, king_guard=ks,
                                cgroup_max_GiB=round(mx / G, 2), cgroup_anon_shmem_GiB=round(used / G, 2), host_available_GiB=round(av / G, 2), K1=k1, K2=k2, M=m, ok=ok))
    state["state"] = "WAITING"; dump()
    if ok: break
    if time.time() - t0 > MAXW: state["state"] = "GAVE_UP_NOT_RUN"; dump(); sys.exit(75)
    time.sleep(POLL)
state["state"] = "HANDED_TO_AX_MEMGUARD"; dump()
rc = subprocess.run([PY, MEMGUARD[0], RPT[:-5] + ".memguard.json" if RPT.endswith(".json") else RPT + ".memguard.json", str(PEAK), "--"] + CMD).returncode
state.update(state="DONE", rc=rc, end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())); dump(); sys.exit(rc)
