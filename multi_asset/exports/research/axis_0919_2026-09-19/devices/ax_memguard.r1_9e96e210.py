"""ax_memguard.py (axis_0919): start a heavy builder only when memory allows, then run it unchanged and record its peak RSS.
usage: python ax_memguard.py <receipt.json> <peak_GiB> -- <cmd> [args...]      (env passes through untouched; exit code = the child's)
Rule (lead 2026-09-19: pod memory is shared with the certified-production-path agent):
  H  host view (`free -g` "available", from /proc/meminfo MemAvailable): available - peak >= AX_MG_MARGIN_GIB (default 20)
  C  container view — the real OOM domain (cgroup memory.max, 61 GB): memory.max - anon(all processes in the cgroup) - peak >= margin_c, where
     margin_c = min(AX_MG_MARGIN_GIB, memory.max - peak - AX_MG_ALONE_GIB). For a builder whose peak leaves less than the margin even in an empty
     cgroup (king 50 GiB: 56.8 - 50.2 = 6.6 GiB < 20) the rule degenerates to "run ALONE": other anon <= AX_MG_ALONE_GIB (default 2).
  Both H and C must hold at launch; otherwise sleep AX_MG_POLL_S (60) and re-check, up to AX_MG_MAX_WAIT_S (default 6 h), then exit 75 (not run).
Every check (time, available, anon, top non-trivial processes) is appended to the receipt; the child's peak RSS comes from getrusage(RUSAGE_CHILDREN).
Nothing is ever killed."""
import json, os, resource, subprocess, sys, time
RPT = sys.argv[1]; PEAK = float(sys.argv[2]); assert sys.argv[3] == "--"; CMD = sys.argv[4:]
G = 1024 ** 3
MARGIN = float(os.environ.get("AX_MG_MARGIN_GIB", "20")); ALONE = float(os.environ.get("AX_MG_ALONE_GIB", "2"))
POLL = int(os.environ.get("AX_MG_POLL_S", "60")); MAXW = int(os.environ.get("AX_MG_MAX_WAIT_S", str(6 * 3600)))
def meminfo():
    d = {}
    for ln in open("/proc/meminfo"):
        k, v = ln.split(":"); d[k] = int(v.split()[0]) * 1024
    return d
def cg():
    mx = int(open("/sys/fs/cgroup/memory.max").read().strip())
    st = {ln.split()[0]: int(ln.split()[1]) for ln in open("/sys/fs/cgroup/memory.stat")}
    ev = {ln.split()[0]: int(ln.split()[1]) for ln in open("/sys/fs/cgroup/memory.events")}
    return mx, st["anon"], ev.get("oom_kill")
def top():
    out = subprocess.run(["ps", "-eo", "pid,pgid,rss,etime,args", "--sort=-rss"], capture_output=True, text=True).stdout.splitlines()[1:9]
    return [ln[:160] for ln in out if ln.split() and int(ln.split()[2]) > 262144]      # > 256 MiB
checks = []; t0 = time.time()
while True:
    mi = meminfo(); mx, anon, oomk = cg()
    host_after = mi["MemAvailable"] / G - PEAK
    margin_c = min(MARGIN, mx / G - PEAK - ALONE)
    cg_after = (mx - anon) / G - PEAK
    ok = host_after >= MARGIN and cg_after >= margin_c
    checks.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "host_available_GiB": round(mi["MemAvailable"] / G, 2), "host_after_peak_GiB": round(host_after, 2),
                   "cgroup_max_GiB": round(mx / G, 2), "cgroup_anon_GiB": round(anon / G, 2), "cgroup_after_peak_GiB": round(cg_after, 2), "margin_c_GiB": round(margin_c, 2),
                   "oom_kill_count": oomk, "top_processes_over_256MiB": top(), "start": bool(ok)})
    json.dump({"cmd": CMD, "peak_GiB_declared": PEAK, "margin_GiB": MARGIN, "alone_GiB": ALONE, "checks": checks, "state": "WAITING" if not ok else "STARTED"}, open(RPT, "w"), indent=1)
    if ok: break
    if time.time() - t0 > MAXW:
        json.dump({"cmd": CMD, "peak_GiB_declared": PEAK, "checks": checks, "state": "GAVE_UP_NOT_RUN"}, open(RPT, "w"), indent=1); sys.exit(75)
    time.sleep(POLL)
ts = time.time(); rc = subprocess.call(CMD); ru = resource.getrusage(resource.RUSAGE_CHILDREN)
mx, anon, oomk2 = cg()
json.dump({"cmd": CMD, "peak_GiB_declared": PEAK, "margin_GiB": MARGIN, "alone_GiB": ALONE, "checks": checks, "state": "DONE", "rc": rc,
           "wall_s": round(time.time() - ts, 1), "waited_s": round(ts - t0, 1), "peak_rss_GiB": round(ru.ru_maxrss / 1024 ** 2, 2),
           "oom_kill_before": checks[-1]["oom_kill_count"], "oom_kill_after": oomk2,
           "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)), "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(RPT, "w"), indent=1)
sys.exit(rc)
