#!/usr/bin/env python3
"""tests_run_v4_arms.py — F01 (independent review 2026-09-17, P1): the arms wrapper must hand EVERY arm a non-empty, existing SLOW_NPY that is the
arm's OWN king score file (A0 = SLOW_v3_on_v4axis.npy, A1 = SLOW_v4.npy) and the umask override, through the REAL wrapper with a stub run_arm.sh
that records the env it received. Cells: W1 A0 → SLOW_v3_on_v4axis + V4_UMASK_NPZ; W2 A1 → SLOW_v4; W3 no override ⇒ default umask path;
W4 (RED CAPABILITY, frozen broken revision run_v4_arms.r1_de4ed666.sh) A0 gets SLOW_NPY EMPTY and the wrapper still runs (rc 0) — the defect;
W5 current wrapper with the A0 king file ABSENT ⇒ ARMS_FAIL rc 3, no arm launched.
FP3 item J (2026-09-17): run_arm.sh is a DEVICE file executed from beside the wrapper (never the tree copy), with the tree and interpreter passed
explicitly. The current wrapper is therefore exercised from a COPY placed in a temp device dir next to a stub run_arm.sh (the stub in the tree
stays only for the frozen r1 cell). W6 tree stub present but NO run_arm.sh beside the wrapper ⇒ ARMS_FAIL rc 3, zero calls (no fallback);
W7 the wrapper passes RUN_ARM_ROOT = the tree and RUN_ARM_PY = V4_PY to the runner and prints the runner's path + sha; W8 the REAL device
run_arm.sh runs a probe device inside an explicitly named tree (cwd = tree/dev_v4, CMD/END lines in tree/logs/commands.txt naming the device copy);
W9 the REAL device run_arm.sh with no RUN_ARM_ROOT (its own dir has no dev_v4/) ⇒ rc 3 'missing tree', nothing executed; W10 unknown interpreter ⇒ rc 3."""
import os, subprocess, sys, tempfile, json, shutil, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
STUB = '#!/bin/bash\nTAG=$1; shift 3\necho "$TAG $* RUN_ARM_ROOT=${RUN_ARM_ROOT:-} RUN_ARM_PY=${RUN_ARM_PY:-}" >> "${RUN_ARM_ROOT:-$(dirname "$0")}/logs/stub_calls.txt"\necho "END[$TAG] rc=0 $(date -u +%FT%TZ)" >> "${RUN_ARM_ROOT:-$(dirname "$0")}/logs/commands.txt"\nexit 0\n'
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
def tree(tmp, king_files=("SLOW_v3_on_v4axis.npy", "SLOW_v4.npy", "SLOW_v4e.npy"), tree_stub=True):
    H = f"{tmp}/hc"; KD = f"{tmp}/kd"; os.makedirs(f"{H}/dev_v4/f8_2026-08-22/preds"); os.makedirs(f"{H}/dev_v4/logs"); os.makedirs(f"{H}/logs"); os.makedirs(f"{H}/masks"); os.makedirs(f"{H}/calib"); os.makedirs(KD)
    for f in king_files: open(f"{KD}/{f}", "wb").write(b"k")
    for s in ("42", "2027"):
        for fp in (f"f10_A0_s{s}.npy", f"f10_v4RAW_s{s}.npy"): open(f"{H}/dev_v4/f8_2026-08-22/preds/{fp}", "wb").write(b"p")
    open(f"{H}/masks/umask_UPIT_CRYPTO.npz", "wb").write(b"u"); open(f"{H}/calib/costb_fee_steady.json", "w").write("{}")
    if tree_stub: open(f"{H}/run_arm.sh", "w").write(STUB); os.chmod(f"{H}/run_arm.sh", 0o755)   # the TREE copy: only the frozen r1 wrapper may use it
    return H, KD
def devcopy(tmp, stub=True):
    """the current wrapper exercised from a temp DEVICE DIR: a copy of run_v4_arms.sh with (or without) a stub run_arm.sh beside it"""
    dd = f"{tmp}/dev"; os.makedirs(dd, exist_ok=True); shutil.copy2(f"{HERE}/run_v4_arms.sh", f"{dd}/run_v4_arms.sh")
    if stub: open(f"{dd}/run_arm.sh", "w").write(STUB); os.chmod(f"{dd}/run_arm.sh", 0o755)
    return f"{dd}/run_v4_arms.sh"
def run(script, arm, H, KD, extra=None):
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "V4_HC": H, "V4_KING_DIR": KD}; e.update(extra or {})
    r = subprocess.run(["bash", script, arm, "42"], env=e, capture_output=True, text=True, cwd=H)
    calls = open(f"{H}/logs/stub_calls.txt").read().splitlines() if os.path.exists(f"{H}/logs/stub_calls.txt") else []
    return r.returncode, r.stdout + r.stderr, calls
def env_of(call, key):
    for w in call.split():
        if w.startswith(key + "="): return w.split("=", 1)[1]
    return None
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t); um = f"{t}/tradable.npz"; open(um, "wb").write(b"t")
    rc, out, calls = run(devcopy(t), "A0", H, KD, {"V4_UMASK_NPZ": um})
    check("W1 A0 (current wrapper): both seats launched with SLOW_NPY = KD/SLOW_v3_on_v4axis.npy and UMASK_NPZ = V4_UMASK_NPZ override",
          rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == f"{KD}/SLOW_v3_on_v4axis.npy" and env_of(c, "UMASK_NPZ") == um and env_of(c, "FPRED") == "f10_A0_s42.npy" for c in calls), (rc, calls, out[-200:]))
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t); rc, out, calls = run(devcopy(t), "A1", H, KD)
    check("W2 A1: SLOW_NPY = KD/SLOW_v4.npy, FPRED f10_v4RAW_s42.npy", rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == f"{KD}/SLOW_v4.npy" and env_of(c, "FPRED") == "f10_v4RAW_s42.npy" for c in calls), (rc, calls))
    check("W3 no V4_UMASK_NPZ ⇒ default H/masks/umask_UPIT_CRYPTO.npz", all(env_of(c, "UMASK_NPZ") == f"{H}/masks/umask_UPIT_CRYPTO.npz" for c in calls), [env_of(c, "UMASK_NPZ") for c in calls])
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t); rc, out, calls = run(f"{HERE}/run_v4_arms.r1_de4ed666.sh", "A0", H, KD, {"V4_UMASK_NPZ": f"{t}/x.npz"})
    check("★★★ W4 RED CAPABILITY (frozen broken revision r1_de4ed666): A0 launched with SLOW_NPY EMPTY and rc 0 — the F01 defect reproduced from the real bytes",
          rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == "" for c in calls), (rc, calls[:1], out[-120:]))
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t, king_files=("SLOW_v4.npy",)); rc, out, calls = run(devcopy(t), "A0", H, KD)
    check("★★★ W5 current wrapper, A0 king file ABSENT ⇒ ARMS_FAIL rc 3, no arm launched (no silent fallback)", rc == 3 and "ARMS_FAIL missing SLOW_NPY" in out and calls == [], (rc, out[-160:], calls))
# ── FP3 item J: the runner is the device copy beside the wrapper ──
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t, tree_stub=True); rc, out, calls = run(devcopy(t, stub=False), "A0", H, KD)
    check("★★★ W6 J: tree HAS a run_arm.sh but none beside the wrapper ⇒ ARMS_FAIL rc 3 before any launch (the tree copy is never a fallback)",
          rc == 3 and "ARMS_FAIL missing device run_arm.sh beside this wrapper" in out and calls == [] and not os.path.exists(f"{H}/logs/commands.txt"), (rc, out[-200:], calls))
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t, tree_stub=False); w = devcopy(t); rc, out, calls = run(w, "A1", H, KD, {"V4_PY": "/some/python"})
    dsha = hashlib.sha256(open(f"{t}/dev/run_arm.sh", "rb").read()).hexdigest()
    check("★★ W7 J: the wrapper passes RUN_ARM_ROOT = the tree and RUN_ARM_PY = V4_PY to the device runner, and prints the runner's path + sha256",
          rc == 0 and len(calls) == 2 and all(env_of(c, "RUN_ARM_ROOT") == H and env_of(c, "RUN_ARM_PY") == "/some/python" for c in calls) and f"RUN_ARM={os.path.realpath(t)}/dev/run_arm.sh sha256={dsha}" in out, (rc, calls[:1], out[:200]))
def real_runner(t, root=None, py=sys.executable, tag="PROBE"):
    """the REAL device run_arm.sh on a probe device: cwd and OUT_TAG are what the device reports"""
    R = f"{t}/tree"; os.makedirs(f"{R}/dev_v4", exist_ok=True)
    open(f"{R}/probe_dev.py", "w").write("import os, sys\nprint('CONFIG cwd=' + os.getcwd() + ' tag=' + os.environ.get('OUT_TAG', '') + ' x=' + os.environ.get('X', ''))\nprint('DONE')\n")
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]}
    if root is not None: e["RUN_ARM_ROOT"] = root
    if py is not None: e["RUN_ARM_PY"] = py
    r = subprocess.run(["bash", f"{HERE}/run_arm.sh", tag, "v4", "probe_dev.py", "X=1"], env=e, capture_output=True, text=True, cwd=t)
    return R, r.returncode, r.stdout + r.stderr
with tempfile.TemporaryDirectory() as t:
    R, rc, out = real_runner(t, root=f"{t}/tree")
    cmds = open(f"{R}/logs/commands.txt").read() if os.path.exists(f"{R}/logs/commands.txt") else ""; dl = open(f"{R}/dev_v4/logs/PROBE.log").read() if os.path.exists(f"{R}/dev_v4/logs/PROBE.log") else ""
    check("★★★ W8 J: the REAL device run_arm.sh inside an explicitly named tree: rc 0, device ran with cwd = tree/dev_v4 and OUT_TAG, CMD line names root + the device copy, END rc=0 appended",
          rc == 0 and f"CONFIG cwd={os.path.realpath(R)}/dev_v4 tag=PROBE x=1" in dl and f"root={R} run_arm={HERE}/run_arm.sh" in cmds and "END[PROBE] rc=0" in cmds and "CONFIG cwd=" in out, (rc, out[-200:], cmds[-200:]))
with tempfile.TemporaryDirectory() as t:
    R, rc, out = real_runner(t, root=None)
    check("★★★ W9 J: the REAL device run_arm.sh with NO RUN_ARM_ROOT (its own directory has no dev_v4/) ⇒ rc 3 'missing tree', no commands.txt anywhere, nothing executed",
          rc == 3 and "missing tree" in out and "RUN_ARM_ROOT=unset" in out and not os.path.exists(f"{HERE}/logs/commands.txt") and not os.path.exists(f"{R}/logs/commands.txt"), (rc, out[-200:]))
with tempfile.TemporaryDirectory() as t:
    R, rc, out = real_runner(t, root=f"{t}/tree", py=f"{t}/no_such_python")
    check("★★ W10 J: unknown interpreter ⇒ rc 3 'missing interpreter', device not run", rc == 3 and "missing interpreter" in out and not os.path.exists(f"{R}/dev_v4/logs/PROBE.log"), (rc, out[-160:]))
# ── J-01 (independent review 2026-09-18): a RELATIVE invocation from the device dir must still execute the device runner, never the tree copy ──
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t, tree_stub=True); dd = f"{t}/dev"; os.makedirs(dd); shutil.copy2(f"{HERE}/run_v4_arms.sh", f"{dd}/run_v4_arms.sh")
    open(f"{dd}/run_arm.sh", "w").write(STUB.replace('echo "$TAG $*', 'echo "DEVICE_RUNNER $TAG $*')); os.chmod(f"{dd}/run_arm.sh", 0o755)
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "V4_HC": H, "V4_KING_DIR": KD}
    r = subprocess.run(["bash", "run_v4_arms.sh", "A0", "42"], env=e, capture_output=True, text=True, cwd=dd)        # relative path, cwd = device dir
    calls = open(f"{H}/logs/stub_calls.txt").read().splitlines() if os.path.exists(f"{H}/logs/stub_calls.txt") else []
    check("★★★ W11 J-01: relative `bash run_v4_arms.sh` from the device dir runs the DEVICE runner (both calls tagged DEVICE_RUNNER), not the tree stub",
          r.returncode == 0 and len(calls) == 2 and all(c.startswith("DEVICE_RUNNER ") for c in calls) and f"RUN_ARM={os.path.realpath(dd)}/run_arm.sh" in r.stdout, (r.returncode, calls[:2], r.stdout[:160]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
