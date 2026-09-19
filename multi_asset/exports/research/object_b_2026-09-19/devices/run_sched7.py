#!/usr/bin/env python3
"""Object B scheduler v7 (18:5xZ). Finding 18:07-18:44Z: the container THRASHES well below its 56.8 GiB memory.max. With ~30 GB of
unreclaimable memory in use, memory.pressure (PSI) was some/full avg10 = 75% and A0_main P3 slowed from 1.3 to 6-10 s/anchor — also while the
v4 processes were SIGSTOPped (their memory still held). Releasing the v4 memory (13.4 GB in use) brought PSI to 0 and A0_main P3 back to
1.3 s/anchor within a minute (all logged in SCHED_LOG). So admission now caps this task's projected total at OWN_CAP = 24 GB (empirical;
13 fast scorers + parent = 26.5 GB already ran slower than in the gate), in addition to >= 20 GiB free and <= 13 cores.
W_GB = 1.56 (measured per fast scorer at peak). A0 stays first.
  A   A0_main P3 (adopted)                                    -> targets A0_main (handoff)
  E1  A0_ext P1 (adopted)          -> E2 A0_ext P2,P3 --reuse-p2 A0_main (fast, 4 workers) -> targets A0_ext + EXT-REPRO (after A0)
  V   V4_main P2,P3 (fast, --p1-from A0_main) only after A0_main has finished; workers = min(12, cap, CPU); scaled up (stop by PGID +
      resumable relaunch) once the extension's P3 has finished; then targets V4_main + negative control
PSI is sampled every loop and logged when avg10 > 20%.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 ADOPT_A0_PGID=<pgid> ADOPT_E1_PGID=<pgid> /workspace/venv/bin/python -B run_sched7.py"""
import os, sys, json, time, signal, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_sched as RS

R, LG = RS.R, RS.LG
A0LOG, V4LOG, E1LOG, E2LOG = f"{LG}/launch_A0_main.log", f"{LG}/launch_V4_main.log", f"{LG}/launch_A0_ext_P1.log", f"{LG}/launch_A0_ext_P23.log"
OWN_CAP, CPU_CAP, W_GB, PARENT = float(os.environ.get("OWN_CAP_GB", "24")), 13, 1.56, 6.2
FAST = {"OBJB_FAST": "1"}


def log(**kw): RS.log(sched="v7", **kw)


def psi():
    try: return float(open("/sys/fs/cgroup/memory.pressure").read().split()[1].split("=")[1])
    except Exception: return None


def main():
    log(ev="start", pid=os.getpid(), pgid=os.getpgid(0), own_cap_GB=OWN_CAP, w_gb=W_GB)
    a0 = RS.Adopted(int(os.environ["ADOPT_A0_PGID"]), A0LOG); log(ev="adopt", name="A0_main P3", pgid=a0.pid)
    e1 = RS.Adopted(int(os.environ["ADOPT_E1_PGID"]), E1LOG); log(ev="adopt", name="A0_ext P1", pgid=e1.pid)
    st = {"v4_w": 0}; v4 = e2 = None; done = set(); last_psi_log = 0

    def need_running():
        n = 0.0; c = 0
        if a0.poll() is None: n += PARENT; c += 1
        if v4 is not None and v4.poll() is None:
            p2 = RS.has(V4LOG, r"^P2 \{"); n += PARENT + (0 if p2 else st["v4_w"] * W_GB); c += 1 if p2 else st["v4_w"]
        if e1.poll() is None: n += PARENT; c += 1
        if e2 is not None and e2.poll() is None:
            p2 = RS.has(E2LOG, r"^P2 \{"); n += PARENT + (0 if p2 else 4 * W_GB); c += 1 if p2 else 4
        return n, c

    def admit(step, need, cores):
        s, c = need_running(); u = RS.unrec(); proj = max(s, u) + need
        ok = proj <= OWN_CAP and RS.CAP - proj >= RS.FREE_MIN and c + cores <= CPU_CAP
        log(ev="mem_check", step=step, static_running_GiB=round(s, 2), unreclaimable_now_GiB=round(u, 2), own_need_GiB=round(need, 2), projected_GiB=round(proj, 2),
            own_cap_GB=OWN_CAP, free_at_projected_GiB=round(RS.CAP - proj, 2), cores_in_use=c, own_cores=cores, psi_avg10=psi(), ok=ok)
        return ok

    def v4_width():
        s, c = need_running(); return min(12, int((OWN_CAP - s - PARENT) // W_GB), CPU_CAP - c)

    def launch_v4(n, why):
        st["v4_w"] = n
        return RS.launch(f"V4_main P2,P3 {n}w ({why})", ["b_launch.py", "--tag", "V4_main", *RS.AX, "--workers", str(n), "--stages", "P2,P3", "--p1-from", "A0_main"],
                         {"OBJB_ARM": "V4", **FAST}, V4LOG)

    while True:
        time.sleep(30)
        p = psi()
        if p is not None and p > 20 and time.time() - last_psi_log > 300:
            last_psi_log = time.time(); log(ev="PSI_HIGH", memory_pressure_avg10=p, unreclaimable_GiB=round(RS.unrec(), 2))
        # extension
        if e1.poll() is not None and "e1" not in done:
            done.add("e1"); log(ev="done", name="A0_ext P1", rc=e1.returncode)
            if e1.returncode == 0: subprocess.run(["cp", "-p", f"{R}/receipts/RUN_CONFIG_A0_ext.json", f"{R}/receipts/RUN_CONFIG_A0_ext_P1.json"])
        if "e1" in done and e1.returncode == 0 and e2 is None and admit("A0_ext P2,P3 4 workers", PARENT + 4 * W_GB, 4):
            e2 = RS.launch("A0_ext P2,P3 4w", ["b_launch.py", "--tag", "A0_ext", *RS.AXE, "--workers", "4", "--stages", "P2,P3", "--reuse-p2", "A0_main"],
                           {"OBJB_DATA": "x0918r", **FAST}, E2LOG, "w")
            continue
        # A0 -> targets (handoff) -> v4
        if a0.poll() is not None and "a0" not in done:
            done.add("a0"); log(ev="done", name="A0_main P3", rc=a0.returncode)
            if a0.returncode == 0:
                RS.run_small("targets A0_main", ["b_targets.py", "A0_main"], {}, f"{LG}/targets_A0_main.log"); done.add("t_A0")
        if "a0" in done and v4 is None and not (e2 is not None and e2.poll() is None and not RS.has(E2LOG, r"^P2 \{")):
            n = v4_width()
            if n >= 4 and admit(f"V4_main P2 {n} workers", PARENT + n * W_GB, n):
                v4 = launch_v4(n, "after A0_main")
                continue
        # scale v4 up once the extension no longer runs, if v4 is still scoring
        if v4 is not None and v4.poll() is None and not RS.has(V4LOG, r"^P2 \{") and "scaled" not in done and "e2" in done:
            s, c = need_running(); others = s - (PARENT + st["v4_w"] * W_GB); n = min(12, int((OWN_CAP - others - PARENT) // W_GB), CPU_CAP - (c - st["v4_w"]))
            done.add("scaled")
            if n > st["v4_w"] + 1:
                log(ev="scale_up", from_w=st["v4_w"], to_w=n); RS.stop("V4_main", v4); subprocess.run(["rm", "-rf", "/dev/shm/object_b_p2/V4_main"])
                v4 = launch_v4(n, "scale-up after the extension")
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
        running = any(q is not None and q.poll() is None for q in (a0, v4, e1, e2))
        pending = ("e1" in done and e1.returncode == 0 and e2 is None) or ("a0" in done and a0.returncode == 0 and v4 is None)
        if not running and not pending:
            log(ev="END", done=sorted(done)); break


if __name__ == "__main__":
    main()
