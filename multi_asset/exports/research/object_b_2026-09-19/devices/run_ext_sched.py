#!/usr/bin/env python3
"""Extension chain A0_ext (AMENDMENT 6) scheduler, beside run_sched.py (which keeps A0_main P3 and V4_main and their targets). Written after the
17:35Z admission bug (the extension's P1 was admitted on the same pre-allocation memory snapshot as the v4 arm; stopped by its PGID).
Admission uses a STATIC projection of every running stage's need (A0_main P3 6.2; V4_main P2 6.2 + 11 x 1.7, P3 6.2) together with the live
unreclaimable memory: max(static, live) + own need <= OWN_CAP (32 GB) and the container keeps >= 20 GiB free; CPU cores in use + own <= 13.
  e1  A0_ext P1 (OBJB_DATA=x0918r)                   need 6.2, 1 core
  e2  A0_ext P2,P3 --reuse-p2 A0_main (fast, 4 w)    need 6.2 + 4 x 1.7, 4 cores (then 1)
  then targets A0_ext and EXT-REPRO (A0_ext vs A0_main; A0_main's P3 must have finished).
Every check and action is appended to receipts/SCHED_LOG.jsonl (tag "ext"). Stops nothing; kills nothing."""
import os, sys, json, time, subprocess, re

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_sched as RS

R, LG = RS.R, RS.LG
A0LOG, V4LOG, E1LOG, E2LOG = f"{LG}/launch_A0_main.log", f"{LG}/launch_V4_main.log", f"{LG}/launch_A0_ext_P1.log", f"{LG}/launch_A0_ext_P23.log"
OWN_CAP, CPU_CAP, V4W, W_GB, PARENT = 32.0, 13, int(os.environ.get("V4_W", "11")), 1.7, 6.2
AXE = RS.AXE; FAST = {"OBJB_FAST": "1"}


def log(**kw): RS.log(sched="ext", **kw)


def state():
    a0_done = RS.has(A0LOG, r"^LAUNCH_DONE"); v4_p2 = RS.has(V4LOG, r"^P2 \{"); v4_done = RS.has(V4LOG, r"^LAUNCH_DONE")
    static = (0 if a0_done else PARENT) + (0 if v4_done else (PARENT if v4_p2 else PARENT + V4W * W_GB))
    cores = (0 if a0_done else 1) + (0 if v4_done else (1 if v4_p2 else V4W))
    return a0_done, v4_p2, v4_done, static, cores


def admit(step, need, cores_need, extra_static=0.0, extra_cores=0):
    a0_done, v4_p2, v4_done, static, cores = state(); u = RS.unrec(); base = max(static + extra_static, u); proj = base + need
    ok = proj <= OWN_CAP and RS.CAP - proj >= RS.FREE_MIN and cores + extra_cores + cores_need <= CPU_CAP
    log(ev="mem_check", step=step, static_running_GiB=round(static + extra_static, 2), unreclaimable_now_GiB=round(u, 2), own_need_GiB=need,
        projected_GiB=round(proj, 2), free_at_projected_GiB=round(RS.CAP - proj, 2), cores_in_use=cores + extra_cores, own_cores=cores_need, ok=ok)
    return ok


def main():
    log(ev="start", pid=os.getpid(), pgid=os.getpgid(0))
    e1 = e2 = None; done = set(); last_check = 0
    while True:
        time.sleep(60)
        if e1 is None and time.time() - last_check >= 300:
            last_check = time.time()
            if admit("A0_ext P1", PARENT, 1):
                e1 = RS.launch("A0_ext P1", ["b_launch.py", "--tag", "A0_ext", *AXE, "--workers", "4", "--stages", "P1"], {"OBJB_DATA": "x0918r", **FAST}, E1LOG, "w")
        if e1 is not None and e1.poll() is not None and "e1" not in done:
            done.add("e1"); log(ev="done", name="A0_ext P1", rc=e1.returncode)
            if e1.returncode != 0: log(ev="FAILED", name="A0_ext P1"); break
            subprocess.run(["cp", "-p", f"{R}/receipts/RUN_CONFIG_A0_ext.json", f"{R}/receipts/RUN_CONFIG_A0_ext_P1.json"])
        if "e1" in done and e2 is None and time.time() - last_check >= 120:
            last_check = time.time()
            if admit("A0_ext P2,P3 4 workers", PARENT + 4 * W_GB, 4):
                e2 = RS.launch("A0_ext P2,P3 4w", ["b_launch.py", "--tag", "A0_ext", *AXE, "--workers", "4", "--stages", "P2,P3", "--reuse-p2", "A0_main"],
                               {"OBJB_DATA": "x0918r", **FAST}, E2LOG, "w")
        if e2 is not None and e2.poll() is not None and "e2" not in done:
            done.add("e2"); log(ev="done", name="A0_ext P2,P3", rc=e2.returncode)
            if e2.returncode != 0: log(ev="FAILED", name="A0_ext P2,P3"); break
            RS.run_small("targets A0_ext", ["b_targets.py", "A0_ext"], {"OBJB_DATA": "x0918r"}, f"{LG}/targets_A0_ext.log")
        if "e2" in done and "repro" not in done and RS.has(A0LOG, r"^LAUNCH_DONE"):
            RS.run_small("EXT-REPRO A0_ext vs A0_main", ["ext_repro_check.py", "A0_main", "A0_ext"], {}, f"{LG}/ext_repro_A0_ext.log"); done.add("repro")
            log(ev="END", done=sorted(done)); break


if __name__ == "__main__":
    main()
