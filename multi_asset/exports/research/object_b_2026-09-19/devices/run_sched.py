#!/usr/bin/env python3
"""Object B scheduler for the rest of the night (lead approval 13:3xZ: own peak ~30 GB; the container's unreclaimable memory = anon + shmem
must leave >= 20 GiB of the cgroup cap free at every heavy step's projected peak; scale down on foreign heavy load; total CPU within the
13.6-core quota so A0's final pass is not starved). Replaces the two armed shell launchers (run_v4_chain.sh, run_ext_chain.sh).

Plan (every heavy step is admitted by check(); every check and action is appended to receipts/SCHED_LOG.jsonl):
  s0  A0_main P2,P3 relaunched with 13 scorer workers (resumable: skips anchors already in any shard of the run)
  s1  after A0 P2: A0_ext P1 (OBJB_DATA=x0918r)            [~6 GB, 1 core]
      after A0 P2: V4_main P2,P3 (OBJB_ARM=V4, --p1-from A0_main, 9 workers)   [~6 + 9 x 1.3 GB]
  s2  after V4 P2 and A0_ext P1: A0_ext P2,P3 --reuse-p2 A0_main (4 workers)
  s3  targets per run when it ends; EXT-REPRO (A0_ext vs A0_main); negative control (V4_main vs A0_main must FAIL)
  scale-down: if the cgroup's free unreclaimable memory drops below 20 GiB while a P2 stage runs, that stage (V4 first, then A0) is stopped by
  its own recorded PGID and relaunched with half the workers (resumable). Stops only process groups started by this scheduler.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 [ADOPT_A0_PGID=<pgid> V4_WORKERS=<n>] /workspace/venv/bin/python -B run_sched.py
  fast (15:3xZ, after FAST-GATE PASS): ADOPT_A0_PGID=1295510 RELAUNCH_A0=1 FAST=1 W_GB=<measured> A0_WORKERS=13 V4_WORKERS=11
  restart (13:4xZ): V4_WORKERS=11 — V4 P2 (11) + A0 P3 (1) + A0_ext P1 (1) = 13 cores within the 13.6 quota; projected ~32.7 GB, free >= 20 GiB."""
import os, sys, json, time, signal, subprocess, re

R = "/workspace/object_b_2026-09-19"; D = f"{R}/devices"; LG = f"{R}/logs"; PY = "/workspace/venv/bin/python"
SLOG = f"{R}/receipts/SCHED_LOG.jsonl"
CAP = int(open("/sys/fs/cgroup/memory.max").read()) / 2 ** 30; FREE_MIN = 20.0
W_GB, PARENT_GB = float(os.environ.get("W_GB", "1.3")), 6.2   # probe receipts/memprobe_samples.txt; 12-worker P2 peaked at 21.85 GB (= 6.2 + 12 x 1.3)
FAST = {"OBJB_FAST": "1"} if os.environ.get("FAST") == "1" else {}   # warm-executor scorer path (FAST-GATE PASS; b_launch re-asserts it)
AX = ["--start", "2022-01-31T00:00:00Z", "--end", "2026-08-31T00:00:00Z"]; AXE = ["--start", "2022-01-31T00:00:00Z", "--end", "2026-09-18T20:00:00Z"]


def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(**kw):
    kw = {"utc": utc(), **kw}
    with open(SLOG, "a") as f: f.write(json.dumps(kw) + "\n")
    print(json.dumps(kw), flush=True)


def unrec():
    s = {}
    for l in open("/sys/fs/cgroup/memory.stat"):
        k, v = l.split()[:2]
        if k in ("anon", "shmem"): s[k] = int(v) / 2 ** 30
    return s.get("anon", 0.0) + s.get("shmem", 0.0)


def check(step, need_gb):
    u = unrec(); proj = u + need_gb; ok = CAP - proj >= FREE_MIN
    log(ev="mem_check", step=step, unreclaimable_now_GiB=round(u, 2), own_need_GiB=round(need_gb, 2), projected_GiB=round(proj, 2),
        cap_GiB=round(CAP, 2), free_at_projected_GiB=round(CAP - proj, 2), ok=ok)
    return ok


def alive(pg):
    try: os.killpg(pg, 0); return True
    except ProcessLookupError: return False


def launch(name, args, env_extra, logfile, mode="a"):
    env = {"PATH": "/usr/bin:/bin", "HOME": "/root", "LC_CTYPE": "C.UTF-8", **env_extra}
    tag = args[args.index("--tag") + 1]; rc_ = f"{R}/receipts/RUN_CONFIG_{tag}.json"
    if os.path.exists(rc_):   # b_launch rewrites its RUN_CONFIG; every earlier one is kept
        subprocess.run(["cp", "-p", rc_, f"{R}/receipts/RUN_CONFIG_{tag}_prev_{time.strftime('%H%M%S', time.gmtime())}.json"])
    f = open(logfile, mode); f.write(f"=== {name} launched {utc()} argv {' '.join(args)} env {env_extra} ===\n"); f.flush()
    p = subprocess.Popen(["nice", "-n", "10", PY, "-B"] + args, cwd=D, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    log(ev="launch", name=name, pgid=p.pid, argv=args, env=env_extra, log=logfile); return p


def stop(name, p):
    log(ev="stop", name=name, pgid=p.pid)
    os.killpg(p.pid, signal.SIGTERM)
    for _ in range(60):
        if p.poll() is not None and not alive(p.pid): break
        time.sleep(1)
    if alive(p.pid): os.killpg(p.pid, signal.SIGKILL)
    p.wait()


class Adopted:
    """a launcher started by an earlier instance of this scheduler (restart without touching the running stage): liveness by its PGID,
    outcome from its log section after the last launch marker (LAUNCH_DONE => 0)."""
    def __init__(self, pgid, logfile): self.pid = pgid; self.logfile = logfile; self.returncode = None

    def poll(self):
        if self.returncode is None and not alive(self.pid):
            last = open(self.logfile, errors="replace").read().rsplit("=== ", 1)[-1]
            self.returncode = 0 if re.search(r"^LAUNCH_DONE", last, re.M) else 1
        return self.returncode

    def wait(self):
        while self.poll() is None: time.sleep(1)
        return self.returncode


def has(path, pat):
    try: return re.search(pat, open(path, errors="replace").read(), re.M) is not None
    except FileNotFoundError: return False


def run_small(name, args, env_extra, logfile):
    env = {"PATH": "/usr/bin:/bin", "HOME": "/root", "LC_CTYPE": "C.UTF-8", **env_extra}
    with open(logfile, "w") as f: rc = subprocess.run(["nice", "-n", "10", PY, "-B"] + args, cwd=D, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    log(ev="done_small", name=name, rc=rc, log=logfile); return rc


def main():
    log(ev="start", pid=os.getpid(), pgid=os.getpgid(0), cap_GiB=round(CAP, 2), rule="free unreclaimable >= 20 GiB at projected peak; own peak ~30 GB")
    A0LOG, V4LOG, E1LOG, E2LOG = f"{LG}/launch_A0_main.log", f"{LG}/launch_V4_main.log", f"{LG}/launch_A0_ext_P1.log", f"{LG}/launch_A0_ext_P23.log"
    # s0: A0 P2,P3 with 13 workers (the 9-worker run PGID 1293032 is this scheduler's predecessor, recorded in the A0 log)
    st = {"a0_w": 13, "v4_w": int(os.environ.get("V4_WORKERS", "9"))}
    old = 1293032; adopt = int(os.environ.get("ADOPT_A0_PGID", "0"))
    relaunch_a0 = os.environ.get("RELAUNCH_A0") == "1"
    if adopt and relaunch_a0:   # hand A0's remaining un-scored anchors to fast workers: stop the adopted run by its PGID, relaunch (resumable)
        assert alive(adopt), adopt
        log(ev="stop", name="A0_main P2 (standard path) for the fast path", pgid=adopt); os.killpg(adopt, signal.SIGTERM)
        for _ in range(90):
            if not alive(adopt): break
            time.sleep(1)
        adopt = 0
    elif adopt:   # restart of the scheduler: the A0 run it launched keeps running untouched
        assert alive(adopt), adopt
        a0 = Adopted(adopt, A0LOG); log(ev="adopt", name="A0_main P2,P3 13w", pgid=adopt, v4_workers=st["v4_w"])
    elif alive(old) and not relaunch_a0:
        log(ev="stop", name="A0_main P2 (9 workers)", pgid=old); os.killpg(old, signal.SIGTERM)
        for _ in range(60):
            if not alive(old): break
            time.sleep(1)
    if not adopt:
        for w in range(12):   # sandboxes of the earlier (untagged) P2 code, all of them this task's
            subprocess.run(["rm", "-rf", f"/dev/shm/object_b_p2/w{w}"])
        st["a0_w"] = int(os.environ.get("A0_WORKERS", "13"))
        while st["a0_w"] > 2 and not check(f"A0_main P2 {st['a0_w']} workers", PARENT_GB + st["a0_w"] * W_GB): st["a0_w"] -= 2
        a0 = launch(f"A0_main P2,P3 {st['a0_w']}w", ["b_launch.py", "--tag", "A0_main", *AX, "--workers", str(st["a0_w"]), "--stages", "P2,P3"], {**FAST}, A0LOG)
    v4 = e1 = e2 = None; done = set()
    while True:
        time.sleep(60)
        # failures
        for nm, lf, p in (("A0_main", A0LOG, a0), ("V4_main", V4LOG, v4), ("A0_ext_P1", E1LOG, e1), ("A0_ext_P23", E2LOG, e2)):
            if p is not None and nm not in done and p.poll() is not None and p.returncode != 0:
                log(ev="FAILED", name=nm, rc=p.returncode, log=lf); done.add(nm)
        a0_p2 = has(A0LOG, r"^P2 \{"); v4_p2 = has(V4LOG, r"^P2 \{")
        # s1
        if a0_p2 and e1 is None and check("A0_ext P1", PARENT_GB):
            e1 = launch("A0_ext P1", ["b_launch.py", "--tag", "A0_ext", *AXE, "--workers", "4", "--stages", "P1"], {"OBJB_DATA": "x0918r", **FAST}, E1LOG, "w")
        if a0_p2 and e1 is not None and v4 is None and check(f"V4_main P2 {st['v4_w']} workers", PARENT_GB + st["v4_w"] * W_GB):
            v4 = launch(f"V4_main P2,P3 {st['v4_w']}w", ["b_launch.py", "--tag", "V4_main", *AX, "--workers", str(st["v4_w"]), "--stages", "P2,P3", "--p1-from", "A0_main"],
                        {"OBJB_ARM": "V4", **FAST}, V4LOG)
        # s2
        if e1 is not None and e1.poll() == 0 and "cp_ext_p1" not in done:
            subprocess.run(["cp", "-p", f"{R}/receipts/RUN_CONFIG_A0_ext.json", f"{R}/receipts/RUN_CONFIG_A0_ext_P1.json"]); done.add("cp_ext_p1")
        if "cp_ext_p1" in done and v4_p2 and e2 is None and check("A0_ext P2,P3 4 workers", PARENT_GB + 4 * W_GB):
            e2 = launch("A0_ext P2,P3 4w", ["b_launch.py", "--tag", "A0_ext", *AXE, "--workers", "4", "--stages", "P2,P3", "--reuse-p2", "A0_main"], {"OBJB_DATA": "x0918r", **FAST}, E2LOG, "w")
        # s3
        if a0.poll() == 0 and "t_A0" not in done:
            run_small("targets A0_main", ["b_targets.py", "A0_main"], {}, f"{LG}/targets_A0_main.log"); done.add("t_A0")
        if v4 is not None and v4.poll() == 0 and "t_V4" not in done:
            run_small("targets V4_main", ["b_targets.py", "V4_main"], {"OBJB_ARM": "V4"}, f"{LG}/targets_V4_main.log")
            run_small("negative control EXT-REPRO V4_main vs A0_main (must FAIL)", ["ext_repro_check.py", "A0_main", "V4_main"], {}, f"{LG}/negctrl_V4_vs_A0.log"); done.add("t_V4")
        if e2 is not None and e2.poll() == 0 and "t_EXT" not in done:
            run_small("targets A0_ext", ["b_targets.py", "A0_ext"], {"OBJB_DATA": "x0918r"}, f"{LG}/targets_A0_ext.log")
            run_small("EXT-REPRO A0_ext vs A0_main", ["ext_repro_check.py", "A0_main", "A0_ext"], {}, f"{LG}/ext_repro_A0_ext.log"); done.add("t_EXT")
        # scale-down on low free memory (V4 P2 first, then A0 P2)
        u = unrec()
        if CAP - u < FREE_MIN:
            log(ev="LOW_FREE", unreclaimable_GiB=round(u, 2), free_GiB=round(CAP - u, 2))
            if v4 is not None and v4.poll() is None and not v4_p2 and st["v4_w"] > 2:
                stop("V4_main P2", v4); st["v4_w"] //= 2
                v4 = launch(f"V4_main P2,P3 {st['v4_w']}w (scaled down)", ["b_launch.py", "--tag", "V4_main", *AX, "--workers", str(st["v4_w"]), "--stages", "P2,P3", "--p1-from", "A0_main"],
                            {"OBJB_ARM": "V4", **FAST}, V4LOG)
            elif a0.poll() is None and not a0_p2 and st["a0_w"] > 2:
                stop("A0_main P2", a0); st["a0_w"] //= 2
                a0 = launch(f"A0_main P2,P3 {st['a0_w']}w (scaled down)", ["b_launch.py", "--tag", "A0_main", *AX, "--workers", str(st["a0_w"]), "--stages", "P2,P3"], {**FAST}, A0LOG)
        running = any(p is not None and p.poll() is None for p in (a0, v4, e1, e2))
        pending = (a0_p2 and (e1 is None or v4 is None)) or ("cp_ext_p1" in done and v4_p2 and e2 is None)
        if not running and not pending:
            log(ev="END", done=sorted(done)); break


if __name__ == "__main__":
    main()
