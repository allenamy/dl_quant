#!/usr/bin/env python3
"""Stop / start / status of the four producer-side launchd services, as a GATE with verdict lines (for release_gates.py, E-0926-A).
Same recipe as the 2026-09-25 v2c window's W1 / W5 (deploy_v2c_2026-09-25T1300Z/WINDOW_CHECKLIST.md), made fail-closed:
  stop   : wait (<= 60 s each) until com.hsy.combosnap / com.hsy.comboparity have no running pid (never interrupt a periodic job), then
           `launchctl bootout` shadowloop, combolive, combosnap, comboparity; then ASSERT: no launchd pid for any of the four, no process
           whose args contain shadow_loop_v3 / combo_stage / combo_live_daemon / combo_state_snapshot / combo_parity, no
           snap/.parity.lock, and ~/wide_shadow/shadow.lock absent or naming a dead pid.        verdict: PRODUCER_SERVICES STOPPED
  start  : `launchctl bootstrap` comboparity, combosnap, combolive, shadowloop (that order); then ASSERT within 60 s: shadowloop has a
           pid, shadow.lock names that live pid, its environment carries SHADOW_OFFSET_MIN=12, the process started at/after --after
           (UTC epoch), and loop.out's last line is a "next <slot>" line written after --after.            verdict: PRODUCER_SERVICES STARTED
  status : prints each label's pid (never changes anything).                                            verdict: PRODUCER_SERVICES STATUS
Never kills by name; only launchctl on these four labels. Any failed assertion ⇒ exit 1 with the reason."""
import json, os, re, subprocess, sys, time

UID = os.getuid(); HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
LABELS = ("com.hsy.shadowloop", "com.hsy.combolive", "com.hsy.combosnap", "com.hsy.comboparity")
PATS = ("shadow_loop_v3", "combo_stage", "combo_live_daemon", "combo_state_snapshot", "combo_parity")


def pid_of(label):
    p = subprocess.run(["launchctl", "print", f"gui/{UID}/{label}"], capture_output=True, text=True)
    if p.returncode != 0: return None                      # not loaded
    m = re.search(r"^\s*pid = (\d+)", p.stdout, re.M)
    return int(m.group(1)) if m else 0                     # loaded, not running


def alive(pid):
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return True


def procs():
    o = subprocess.run(["ps", "-A", "-o", "pid=,lstart=,args="], capture_output=True, text=True, check=True).stdout
    me = {os.getpid(), os.getppid()}
    return [l.strip() for l in o.splitlines() if any(p in l for p in PATS) and int(l.split()[0]) not in me]


def fail(msg): print(f"PRODUCER_SERVICES FAIL {msg}"); sys.exit(1)


def stop():
    for L in ("com.hsy.combosnap", "com.hsy.comboparity"):
        for _ in range(60):
            if not pid_of(L): break
            time.sleep(1)
        else: fail(f"{L} still running after 60 s — not interrupting a periodic job")
    for L in LABELS:
        r = subprocess.run(["launchctl", "bootout", f"gui/{UID}/{L}"], capture_output=True, text=True)
        print(f"bootout {L} rc={r.returncode} {r.stderr.strip()[:120]}")
    time.sleep(2)
    bad = {L: pid_of(L) for L in LABELS if pid_of(L)}
    if bad: fail(f"launchd pids remain {bad}")
    pr = procs()
    if pr: fail(f"producer processes remain {pr}")
    if os.path.lexists(f"{WS}/state/snap/.parity.lock"): fail("snap/.parity.lock present")
    lk = f"{WS}/shadow.lock"
    if os.path.lexists(lk):
        pid = int(open(lk).read().strip() or 0)
        if pid and alive(pid): fail(f"shadow.lock names a LIVE pid {pid}")
        print(f"shadow.lock stale (pid {pid} dead)")
    print("PRODUCER_SERVICES STOPPED n=4")


def start(after):
    for L in ("com.hsy.comboparity", "com.hsy.combosnap", "com.hsy.combolive", "com.hsy.shadowloop"):
        r = subprocess.run(["launchctl", "bootstrap", f"gui/{UID}", f"{HOME}/Library/LaunchAgents/{L}.plist"], capture_output=True, text=True)
        print(f"bootstrap {L} rc={r.returncode} {r.stderr.strip()[:120]}")
        if r.returncode != 0: fail(f"bootstrap {L} rc {r.returncode}")
    for _ in range(60):
        pid = pid_of("com.hsy.shadowloop")
        out = open(f"{WS}/loop.out").read().splitlines() if os.path.exists(f"{WS}/loop.out") else []
        if pid and os.path.exists(f"{WS}/shadow.lock") and open(f"{WS}/shadow.lock").read().strip() == str(pid) and out and out[-1].startswith("next "):
            break
        time.sleep(1)
    else: fail("shadowloop did not reach its 'next' line with a matching shadow.lock within 60 s")
    env = subprocess.run(["ps", "eww", "-p", str(pid)], capture_output=True, text=True).stdout
    if "SHADOW_OFFSET_MIN=12" not in env: fail("SHADOW_OFFSET_MIN=12 not in the new process environment")
    st = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    t0 = time.mktime(time.strptime(st, "%a %b %d %H:%M:%S %Y"))
    if t0 + 1 < after: fail(f"shadowloop pid {pid} started {st} (local) before --after")
    if os.path.getmtime(f"{WS}/loop.out") < after: fail("loop.out not written after --after")
    print(f"shadowloop pid {pid} started {st} (local); last loop.out line: {out[-1][:80]}")
    print(f"PRODUCER_SERVICES STARTED shadowloop_pid={pid} " + " ".join(f"{L.split('.')[-1]}={pid_of(L)}" for L in LABELS))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "stop": stop()
    elif cmd == "start": start(float(sys.argv[2]))
    elif cmd == "status": print("PRODUCER_SERVICES STATUS " + json.dumps({L: pid_of(L) for L in LABELS}))
    else: print(__doc__); sys.exit(2)
