#!/usr/bin/env python3
"""Object B scheduler v5 (17:5xZ). Lead: A0 is the critical path (the baseline-tables agent waits for the A0 targets).
Measured 17:50-17:53Z: A0_main P3 takes 1.9 s/anchor with the v4 arm's 11 scorers running and 1.27 s/anchor with them paused (SIGSTOP test,
logged). So the v4 scoring is stopped by its PGID (its shards are kept; P2 resumes by skipping every anchor already in any shard) and relaunched
the moment A0_main has finished, with as many workers as memory and CPU allow. Meanwhile only light stages run beside A0_main P3.
Replaces run_sched.py (main) and run_ext_sched.py. Static projection of every running stage's need AND live unreclaimable memory:
max(static, live) + need <= OWN_CAP 32 GB, the container keeps >= 20 GiB free, cores <= 13.
  A   A0_main P3 (adopted PGID)                                         6.2 GB, 1 core  -> targets A0_main (then a message to main by hand)
  E1  A0_ext P1 now (light: 1 core beside A0 P3)                        6.2 GB, 1 core
  E2  A0_ext P2,P3 --reuse-p2 A0_main (fast, 2 workers while A0 runs)   6.2 + 2 x 1.7 GB, 2 cores then 1
  V   V4_main P2,P3 --p1-from A0_main (fast) after A0_main has finished: workers = min(12, memory, CPU)
  then targets V4_main + negative control (V4 vs A0 must FAIL); targets A0_ext + EXT-REPRO.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 ADOPT_A0_PGID=<pgid> STOP_PGIDS=<a,b,c> /workspace/venv/bin/python -B run_sched5.py"""
import os, sys, json, time, signal, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_sched as RS

R, LG = RS.R, RS.LG
A0LOG, V4LOG, E1LOG, E2LOG = f"{LG}/launch_A0_main.log", f"{LG}/launch_V4_main.log", f"{LG}/launch_A0_ext_P1.log", f"{LG}/launch_A0_ext_P23.log"
OWN_CAP, CPU_CAP, W_GB, PARENT = 32.0, 13, 1.7, 6.2
FAST = {"OBJB_FAST": "1"}


def log(**kw): RS.log(sched="v5", **kw)


def main():
    log(ev="start", pid=os.getpid(), pgid=os.getpgid(0))
    for pg in [int(x) for x in os.environ.get("STOP_PGIDS", "").split(",") if x]:
        if RS.alive(pg):
            log(ev="stop", pgid=pg, why="replaced by scheduler v5 / v4 scoring yields to A0_main P3"); os.killpg(pg, signal.SIGTERM)
            for _ in range(60):
                if not RS.alive(pg): break
                time.sleep(1)
            if RS.alive(pg): os.killpg(pg, signal.SIGKILL)
    a0 = RS.Adopted(int(os.environ["ADOPT_A0_PGID"]), A0LOG); log(ev="adopt", name="A0_main P3", pgid=a0.pid)
    subprocess.run(["rm", "-rf", "/dev/shm/object_b_p2/V4_main", "/dev/shm/object_b_p2/A0_ext"])   # sandboxes of stopped runs (this task's)
    st = {"v4_w": 0}; v4 = e1 = e2 = None; done = set()

    def need_running():
        n = 0.0; c = 0
        if a0.poll() is None: n += PARENT; c += 1
        if v4 is not None and v4.poll() is None:
            p2 = RS.has(V4LOG, r"^P2 \{"); n += PARENT + (0 if p2 else st["v4_w"] * W_GB); c += 1 if p2 else st["v4_w"]
        if e1 is not None and e1.poll() is None: n += PARENT; c += 1
        if e2 is not None and e2.poll() is None:
            p2 = RS.has(E2LOG, r"^P2 \{"); n += PARENT + (0 if p2 else 2 * W_GB); c += 1 if p2 else 2
        return n, c

    def admit(step, need, cores):
        s, c = need_running(); u = RS.unrec(); proj = max(s, u) + need
        ok = proj <= OWN_CAP and RS.CAP - proj >= RS.FREE_MIN and c + cores <= CPU_CAP
        log(ev="mem_check", step=step, static_running_GiB=round(s, 2), unreclaimable_now_GiB=round(u, 2), own_need_GiB=round(need, 2), projected_GiB=round(proj, 2),
            free_at_projected_GiB=round(RS.CAP - proj, 2), cores_in_use=c, own_cores=cores, ok=ok)
        return ok

    while True:
        time.sleep(30)
        # extension, light beside A0
        if e1 is None and admit("A0_ext P1", PARENT, 1):
            e1 = RS.launch("A0_ext P1", ["b_launch.py", "--tag", "A0_ext", *RS.AXE, "--workers", "2", "--stages", "P1"], {"OBJB_DATA": "x0918r", **FAST}, E1LOG, "w")
            continue
        if e1 is not None and e1.poll() is not None and "e1" not in done:
            done.add("e1"); log(ev="done", name="A0_ext P1", rc=e1.returncode)
            if e1.returncode == 0: subprocess.run(["cp", "-p", f"{R}/receipts/RUN_CONFIG_A0_ext.json", f"{R}/receipts/RUN_CONFIG_A0_ext_P1.json"])
        if "e1" in done and e1.returncode == 0 and e2 is None and admit("A0_ext P2,P3 2 workers", PARENT + 2 * W_GB, 2):
            e2 = RS.launch("A0_ext P2,P3 2w", ["b_launch.py", "--tag", "A0_ext", *RS.AXE, "--workers", "2", "--stages", "P2,P3", "--reuse-p2", "A0_main"],
                           {"OBJB_DATA": "x0918r", **FAST}, E2LOG, "w")
            continue
        # A0 finished -> targets first (the handoff), then the v4 arm at full width
        if a0.poll() is not None and "a0" not in done:
            done.add("a0"); log(ev="done", name="A0_main P3", rc=a0.returncode)
            if a0.returncode == 0:
                RS.run_small("targets A0_main", ["b_targets.py", "A0_main"], {}, f"{LG}/targets_A0_main.log"); done.add("t_A0")
        if "a0" in done and v4 is None:
            s, c = need_running(); u = RS.unrec(); n = min(12, int((OWN_CAP - max(s, u) - PARENT) // W_GB), CPU_CAP - c)
            if n >= 4 and admit(f"V4_main P2 {n} workers", PARENT + n * W_GB, n):
                st["v4_w"] = n
                v4 = RS.launch(f"V4_main P2,P3 {n}w", ["b_launch.py", "--tag", "V4_main", *RS.AX, "--workers", str(n), "--stages", "P2,P3", "--p1-from", "A0_main"],
                               {"OBJB_ARM": "V4", **FAST}, V4LOG)
        if v4 is not None and v4.poll() is not None and "v4" not in done:
            done.add("v4"); log(ev="done", name="V4_main", rc=v4.returncode)
            if v4.returncode == 0:
                RS.run_small("targets V4_main", ["b_targets.py", "V4_main"], {"OBJB_ARM": "V4"}, f"{LG}/targets_V4_main.log")
                RS.run_small("negative control EXT-REPRO V4_main vs A0_main (must FAIL)", ["ext_repro_check.py", "A0_main", "V4_main"], {}, f"{LG}/negctrl_V4_vs_A0.log")
        if e2 is not None and e2.poll() is not None and "e2" not in done:
            done.add("e2"); log(ev="done", name="A0_ext P2,P3", rc=e2.returncode)
            if e2.returncode == 0: RS.run_small("targets A0_ext", ["b_targets.py", "A0_ext"], {"OBJB_DATA": "x0918r"}, f"{LG}/targets_A0_ext.log")
        if "e2" in done and e2.returncode == 0 and "t_A0" in done and "repro" not in done:
            RS.run_small("EXT-REPRO A0_ext vs A0_main", ["ext_repro_check.py", "A0_main", "A0_ext"], {}, f"{LG}/ext_repro_A0_ext.log"); done.add("repro")
        running = any(p is not None and p.poll() is None for p in (a0, v4, e1, e2))
        pending = (e1 is None) or ("e1" in done and e1.returncode == 0 and e2 is None) or ("a0" in done and a0.returncode == 0 and v4 is None)
        if not running and not pending:
            log(ev="END", done=sorted(done)); break


if __name__ == "__main__":
    main()
