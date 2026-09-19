"""ax_memguard.py v2 (axis_0919): start a heavy builder only when memory allows, run it unchanged, record its peak RSS — and YIELD if the shared
cgroup fills up while it runs. v1 (ax_memguard.r1_9e96e210.py) checked only at launch; the king run of 11:08Z was then OOM-killed at 11:16Z (cgroup
oom_kill 3 -> 4, the victim was that king process) after another agent's batch started at 11:12Z. v2 adds Q (quiet period) and Y (yield).
usage: python ax_memguard.py <receipt.json> <peak_GiB> -- <cmd> [args...]      (env passes through untouched; exit code = the child's, 76 = yielded)
Admission (all at the same check):
  H  host view (/proc/meminfo MemAvailable = `free -g` available): available - peak >= AX_MG_MARGIN_GIB (default 20)
  C  cgroup (memory.max; anon + shmem = non-reclaimable): max - used - peak >= margin_c, margin_c = min(MARGIN, max - peak - AX_MG_ALONE_GIB); for a
     builder whose peak leaves less than MARGIN even in an empty cgroup (king) this is "run alone": others' used <= ALONE (default 2 GiB)
  Q  C held on AX_MG_QUIET_N consecutive checks (default 1; king: 5 checks at 60 s)
Y (while the child runs, every 2 s): others = used - RSS(my child's process group); if others > max - peak - AX_MG_YIELD_GIB (default 0.5), the child's
  OWN process group (started with a new session; its pgid is recorded) gets SIGKILL and the run is recorded as YIELDED (exit 76) — so a later batch of
  another agent can never be the OOM victim of this run. Nothing else is ever signalled.
Every check is appended to the receipt; the child's peak RSS comes from getrusage(RUSAGE_CHILDREN)."""
import json, os, resource, signal, subprocess, sys, time
RPT = sys.argv[1]; PEAK = float(sys.argv[2]); assert sys.argv[3] == "--"; CMD = sys.argv[4:]
G = 1024 ** 3
MARGIN = float(os.environ.get("AX_MG_MARGIN_GIB", "20")); ALONE = float(os.environ.get("AX_MG_ALONE_GIB", "2")); YIELD = float(os.environ.get("AX_MG_YIELD_GIB", "0.5"))
POLL = int(os.environ.get("AX_MG_POLL_S", "60")); MAXW = int(os.environ.get("AX_MG_MAX_WAIT_S", str(6 * 3600))); QN = int(os.environ.get("AX_MG_QUIET_N", "1"))
def meminfo():
    d = {}
    for ln in open("/proc/meminfo"):
        k, v = ln.split(":"); d[k] = int(v.split()[0]) * 1024
    return d
def cg():
    mx = int(open("/sys/fs/cgroup/memory.max").read().strip())
    st = {ln.split()[0]: int(ln.split()[1]) for ln in open("/sys/fs/cgroup/memory.stat")}
    ev = {ln.split()[0]: int(ln.split()[1]) for ln in open("/sys/fs/cgroup/memory.events")}
    return mx, st["anon"] + st.get("shmem", 0), ev.get("oom_kill")
def top():
    out = subprocess.run(["ps", "-eo", "pid,pgid,rss,etime,args", "--sort=-rss"], capture_output=True, text=True).stdout.splitlines()[1:9]
    return [ln[:160] for ln in out if ln.split() and int(ln.split()[2]) > 262144]
def pgid_rss(pg):
    tot = 0
    for ln in subprocess.run(["ps", "-eo", "pgid,rss"], capture_output=True, text=True).stdout.splitlines()[1:]:
        a = ln.split()
        if len(a) == 2 and int(a[0]) == pg: tot += int(a[1]) * 1024
    return tot
state = {"cmd": CMD, "peak_GiB_declared": PEAK, "margin_GiB": MARGIN, "alone_GiB": ALONE, "yield_GiB": YIELD, "quiet_n": QN, "device": "ax_memguard.py v2", "checks": []}
def dump(): json.dump(state, open(RPT, "w"), indent=1)
t0 = time.time(); streak = 0
while True:
    mi = meminfo(); mx, used, oomk = cg()
    host_after = mi["MemAvailable"] / G - PEAK; margin_c = min(MARGIN, mx / G - PEAK - ALONE); cg_after = (mx - used) / G - PEAK
    ok = host_after >= MARGIN and cg_after >= margin_c; streak = streak + 1 if ok else 0
    state["checks"].append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "host_available_GiB": round(mi["MemAvailable"] / G, 2), "host_after_peak_GiB": round(host_after, 2),
                            "cgroup_max_GiB": round(mx / G, 2), "cgroup_used_anon_shmem_GiB": round(used / G, 2), "cgroup_after_peak_GiB": round(cg_after, 2), "margin_c_GiB": round(margin_c, 2),
                            "oom_kill_count": oomk, "ok": bool(ok), "quiet_streak": streak, "top_processes_over_256MiB": top()})
    state["state"] = "WAITING"; dump()
    if streak >= QN: break
    if time.time() - t0 > MAXW: state["state"] = "GAVE_UP_NOT_RUN"; dump(); sys.exit(75)
    time.sleep(POLL)
ts = time.time(); p = subprocess.Popen(CMD, start_new_session=True); pg = os.getpgid(p.pid)
state.update(state="RUNNING", child_pid=p.pid, child_pgid=pg, start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)), samples=[]); dump()
yielded = None; mine_max = 0.0; last = 0.0
while p.poll() is None:
    mx, used, oomk = cg(); mine = pgid_rss(pg); others = max(used - mine, 0); mine_max = max(mine_max, mine / G)
    if others / G > mx / G - PEAK - YIELD:
        os.killpg(pg, signal.SIGKILL); yielded = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "others_GiB": round(others / G, 2), "mine_GiB": round(mine / G, 2),
                                                   "limit_others_GiB": round(mx / G - PEAK - YIELD, 2), "top": top()}
        p.wait(); break
    if time.time() - last >= 30:
        state["samples"].append({"utc": time.strftime("%H:%M:%SZ", time.gmtime()), "used_GiB": round(used / G, 2), "mine_GiB": round(mine / G, 2), "others_GiB": round(others / G, 2)}); dump(); last = time.time()
    time.sleep(2)
rc = p.returncode; ru = resource.getrusage(resource.RUSAGE_CHILDREN); mx, used, oomk2 = cg()
state.update(state="YIELDED" if yielded else "DONE", rc=rc, yielded=yielded, wall_s=round(time.time() - ts, 1), waited_s=round(ts - t0, 1),
             peak_rss_GiB=round(ru.ru_maxrss / 1024 ** 2, 2), sampled_pgid_rss_max_GiB=round(mine_max, 2), oom_kill_before=state["checks"][-1]["oom_kill_count"], oom_kill_after=oomk2,
             end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
dump(); sys.exit(76 if yielded else rc)
