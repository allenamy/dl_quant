#!/usr/bin/env python3
"""Self-test of release_gates.py (E-0926-A). Every case: does the run stop, and did the NEXT gate start?
The next gate of every case touches a marker file; "later gates NOT started" is measured by the marker's absence.
Baseline first (must be green, else every red below is void). Red control: the OLD shell-sequence pattern with
an unsplit variable (the 2026-09-26 01:18Z shape) is run through zsh and must REACH the next step — the defect
this runner closes, reproduced.
usage: /usr/bin/python3 release_gates_selftest.py <scratch dir>"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); RG = os.path.join(HERE, "release_gates.py")
S = os.path.abspath(sys.argv[1]); os.makedirs(S, exist_ok=True)
FAILS = []; N = [0]


def check(name, cond, extra=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)[:300]) if extra != '' else ''}")
    if not cond: FAILS.append(name)


def case(name, first_gate, extra_gates=None):
    d = tempfile.mkdtemp(prefix="rg_", dir=S); marker = os.path.join(d, "NEXT_GATE_STARTED")
    nxt = {"name": "next", "argv": ["/usr/bin/python3", "-c", f"open({marker!r},'w').write('x'); print('NEXT_OK')"], "verdict": "^NEXT_OK$"}
    gates = ([first_gate] if first_gate else []) + (extra_gates if extra_gates is not None else [nxt])
    gp = os.path.join(d, "gates.json"); json.dump(gates, open(gp, "w"))
    p = subprocess.run(["/usr/bin/python3", RG, gp, os.path.join(d, "log.txt")], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr, os.path.exists(marker), open(os.path.join(d, "log.txt")).read() if os.path.exists(os.path.join(d, "log.txt")) else ""


PY = "/usr/bin/python3"
print("[0] baseline: two passing gates ⇒ exit 0, both ran")
rc, out, nxt, log = case("baseline", {"name": "pair", "argv": [PY, "-c", "print('UPSTREAM_PAIR_CHECK PASS compared_equal=6')"], "verdict": "^UPSTREAM_PAIR_CHECK PASS "})
check("★★★ BASELINE green: rc 0, ALL_PASS, the next gate ran", rc == 0 and "RELEASE_GATES ALL_PASS n=2" in out and nxt, (rc, out.strip()))

print("[1] the 01:18Z shape: argv[0] is the whole unsplit command string ⇒ launch failure ⇒ STOP")
rc, out, nxt, log = case("unsplit", {"name": "pair", "argv": [f"{PY} {HERE}/v2c_upstream_pair_check.py", "/tmp/x", "--expect-n", "6"], "verdict": "^UPSTREAM_PAIR_CHECK PASS "})
check("★★★ launch failure stops: rc 3, 'LAUNCH FAILED', next gate NOT started", rc == 3 and "LAUNCH FAILED" in out and not nxt, (rc, out.strip()))

print("[2] non-zero exit WITHOUT any red verdict ⇒ STOP")
rc, out, nxt, log = case("false", {"name": "g", "argv": ["/usr/bin/false"], "verdict": "^X$"})
check("★★★ exit 1 with no output stops, next NOT started", rc == 3 and "exit code 1" in out and not nxt, (rc, out.strip()))

print("[3] exit 0 but NO verdict line ⇒ STOP (the gate did not judge)")
rc, out, nxt, log = case("true", {"name": "g", "argv": ["/usr/bin/true"], "verdict": "^UPSTREAM_PAIR_CHECK PASS "})
check("★★★ silent exit 0 stops, next NOT started", rc == 3 and "NO verdict line" in out and not nxt, (rc, out.strip()))

print("[4] explicit red verdict with exit 1 ⇒ STOP")
rc, out, nxt, log = case("red", {"name": "pair", "argv": [PY, "-c", "import sys; print('UPSTREAM_PAIR_CHECK RED compared_equal=5'); sys.exit(1)"], "verdict": "^UPSTREAM_PAIR_CHECK PASS "})
check("★★ explicit red stops, next NOT started", rc == 3 and not nxt, (rc, out.strip()))

print("[5] a PASS-looking line but exit 1 ⇒ STOP (rc wins over text)")
rc, out, nxt, log = case("passtext_rc1", {"name": "pair", "argv": [PY, "-c", "import sys; print('UPSTREAM_PAIR_CHECK PASS x'); sys.exit(1)"], "verdict": "^UPSTREAM_PAIR_CHECK PASS "})
check("★★ verdict text with non-zero exit still stops", rc == 3 and not nxt, (rc, out.strip()))

print("[6] timeout ⇒ STOP")
rc, out, nxt, log = case("timeout", {"name": "slow", "argv": [PY, "-c", "import time; time.sleep(5)"], "verdict": "^X$", "timeout_s": 1})
check("★ timeout stops, next NOT started", rc == 3 and "timeout" in out and not nxt, (rc, out.strip()))

print("[7] malformed gate files ⇒ exit 2, nothing runs")
rc, out, nxt, log = case("empty", None, extra_gates=[])
check("★★ an EMPTY gate list does not pass vacuously (exit 2)", rc == 2 and "MALFORMED" in out, (rc, out.strip()))
rc, out, nxt, log = case("noverdict", {"name": "g", "argv": ["/usr/bin/true"]})
check("★★ a gate without a verdict regex is refused (exit 2) and nothing ran", rc == 2 and not nxt, (rc, out.strip()))
rc, out, nxt, log = case("stringargv", {"name": "g", "argv": f"{PY} -c print(1)", "verdict": "1"})
check("★ argv given as one STRING is refused (exit 2)", rc == 2 and not nxt, (rc, out.strip()))

print("[8] RED CONTROL: the old shell-sequence pattern (zsh, unsplit $PAIR; `;`) reaches the next step")
d = tempfile.mkdtemp(prefix="rg_old_", dir=S); marker = os.path.join(d, "FF_REACHED")
old = f'PAIR="{PY} {HERE}/v2c_upstream_pair_check.py"; $PAIR /tmp/x --expect-n 6; echo "pair rc=$?"; touch {marker}'
p = subprocess.run(["/bin/zsh", "-c", old], capture_output=True, text=True)
check("★★★ RED CONTROL: old pattern — the gate fails to launch (rc 127) and the next step still runs", os.path.exists(marker) and "pair rc=127" in p.stdout, (p.stdout.strip(), p.stderr.strip()[:150]))

print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
print("RELEASE_GATES_SELFTEST " + ("ALL GREEN" if not FAILS else f"RED {FAILS}"))
sys.exit(1 if FAILS else 0)
