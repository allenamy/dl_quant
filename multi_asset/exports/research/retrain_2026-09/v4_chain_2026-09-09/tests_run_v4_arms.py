#!/usr/bin/env python3
"""tests_run_v4_arms.py — F01 (independent review 2026-09-17, P1): the arms wrapper must hand EVERY arm a non-empty, existing SLOW_NPY that is the
arm's OWN king score file (A0 = SLOW_v3_on_v4axis.npy, A1 = SLOW_v4.npy) and the umask override, through the REAL wrapper with a stub run_arm.sh
that records the env it received. Cells: W1 A0 → SLOW_v3_on_v4axis + V4_UMASK_NPZ; W2 A1 → SLOW_v4; W3 no override ⇒ default umask path;
W4 (RED CAPABILITY, frozen broken revision run_v4_arms.r1_de4ed666.sh) A0 gets SLOW_NPY EMPTY and the wrapper still runs (rc 0) — the defect;
W5 current wrapper with the A0 king file ABSENT ⇒ ARMS_FAIL rc 3, no arm launched."""
import os, subprocess, sys, tempfile, json
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
def tree(tmp, king_files=("SLOW_v3_on_v4axis.npy", "SLOW_v4.npy", "SLOW_v4e.npy")):
    H = f"{tmp}/hc"; KD = f"{tmp}/kd"; os.makedirs(f"{H}/dev_v4/f8_2026-08-22/preds"); os.makedirs(f"{H}/dev_v4/logs"); os.makedirs(f"{H}/logs"); os.makedirs(f"{H}/masks"); os.makedirs(f"{H}/calib"); os.makedirs(KD)
    for f in king_files: open(f"{KD}/{f}", "wb").write(b"k")
    for s in ("42", "2027"):
        for fp in (f"f10_A0_s{s}.npy", f"f10_v4RAW_s{s}.npy"): open(f"{H}/dev_v4/f8_2026-08-22/preds/{fp}", "wb").write(b"p")
    open(f"{H}/masks/umask_UPIT_CRYPTO.npz", "wb").write(b"u"); open(f"{H}/calib/costb_fee_steady.json", "w").write("{}")
    # stub run_arm.sh: record TAG + the env words it was given; append END rc=0 like the real one
    open(f"{H}/run_arm.sh", "w").write('#!/bin/bash\nTAG=$1; shift 3\necho "$TAG $*" >> "$(dirname "$0")/logs/stub_calls.txt"\necho "END[$TAG] rc=0 $(date -u +%FT%TZ)" >> "$(dirname "$0")/logs/commands.txt"\nexit 0\n'); os.chmod(f"{H}/run_arm.sh", 0o755)
    return H, KD
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
    rc, out, calls = run(f"{HERE}/run_v4_arms.sh", "A0", H, KD, {"V4_UMASK_NPZ": um})
    check("W1 A0 (current wrapper): both seats launched with SLOW_NPY = KD/SLOW_v3_on_v4axis.npy and UMASK_NPZ = V4_UMASK_NPZ override",
          rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == f"{KD}/SLOW_v3_on_v4axis.npy" and env_of(c, "UMASK_NPZ") == um and env_of(c, "FPRED") == "f10_A0_s42.npy" for c in calls), (rc, calls, out[-200:]))
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t); rc, out, calls = run(f"{HERE}/run_v4_arms.sh", "A1", H, KD)
    check("W2 A1: SLOW_NPY = KD/SLOW_v4.npy, FPRED f10_v4RAW_s42.npy", rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == f"{KD}/SLOW_v4.npy" and env_of(c, "FPRED") == "f10_v4RAW_s42.npy" for c in calls), (rc, calls))
    check("W3 no V4_UMASK_NPZ ⇒ default H/masks/umask_UPIT_CRYPTO.npz", all(env_of(c, "UMASK_NPZ") == f"{H}/masks/umask_UPIT_CRYPTO.npz" for c in calls), [env_of(c, "UMASK_NPZ") for c in calls])
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t); rc, out, calls = run(f"{HERE}/run_v4_arms.r1_de4ed666.sh", "A0", H, KD, {"V4_UMASK_NPZ": f"{t}/x.npz"})
    check("★★★ W4 RED CAPABILITY (frozen broken revision r1_de4ed666): A0 launched with SLOW_NPY EMPTY and rc 0 — the F01 defect reproduced from the real bytes",
          rc == 0 and len(calls) == 2 and all(env_of(c, "SLOW_NPY") == "" for c in calls), (rc, calls[:1], out[-120:]))
with tempfile.TemporaryDirectory() as t:
    H, KD = tree(t, king_files=("SLOW_v4.npy",)); rc, out, calls = run(f"{HERE}/run_v4_arms.sh", "A0", H, KD)
    check("★★★ W5 current wrapper, A0 king file ABSENT ⇒ ARMS_FAIL rc 3, no arm launched (no silent fallback)", rc == 3 and "ARMS_FAIL missing SLOW_NPY" in out and calls == [], (rc, out[-160:], calls))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
