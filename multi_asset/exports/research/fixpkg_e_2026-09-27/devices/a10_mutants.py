# mutation ladder for the new A10 block: each mutant is applied to a fresh copy of the dev tree (ops/check_nosleep.py or live/tests_nosleep.py),
# then tests_nosleep runs; expected = the named checks go FAIL and the suite exits 1. Baseline (no mutation) must be ALL PASS, rc 0.
import os, re, shutil, subprocess, sys, tempfile
DEV = os.path.abspath(sys.argv[1])
M = [
 ("baseline", None, None, None, []),
 ("timeout_dropped", "ops/check_nosleep.py", 'rc, out, err = _run(["pmset", "-g", "log"], timeout=timeout)', 'rc, out, err = _run(["pmset", "-g", "log"])', ["A10 RED CAPABILITY"]),
 ("failure_reads_as_empty", "ops/check_nosleep.py", "    if rc != 0:\n        return None\n    evs = []", "    if rc != 0:\n        return []\n    evs = []", ["A10 RED CAPABILITY"]),
 ("run_swallows_timeout_as_ok", "ops/check_nosleep.py", '        return 127, "", str(e)', '        return 0, "", str(e)', ["A10 RED CAPABILITY"]),
 ("reader_command_changed", "ops/check_nosleep.py", '_run(["pmset", "-g", "log"], timeout=timeout)', '_run(["pmset", "-g", "log", "-x"], timeout=timeout)', ["A10p", "A10h"]),
 ("parser_drops_sleep", "ops/check_nosleep.py", 'if "Entering Sleep state" not in line:', 'if "Entering Sleep  state" not in line:', ["A10p"]),
 ("red_check_moved_out_of_seal", "live/tests_nosleep.py", "    check(\"★★ A10 RED CAPABILITY", "check(\"★★ A10 RED CAPABILITY", ["A10s every"]),
]
bad = 0
for name, f, a, b, want in M:
    d = tempfile.mkdtemp(prefix="a10mut_"); shutil.copytree(DEV, d, dirs_exist_ok=True)
    if f:
        p = os.path.join(d, f); s = open(p).read(); assert s.count(a) == 1, (name, s.count(a)); open(p, "w").write(s.replace(a, b))
    r = subprocess.run(["/usr/bin/python3", os.path.join(d, "live/tests_nosleep.py")], capture_output=True, text=True, timeout=120)
    fails = [l for l in r.stdout.splitlines() if l.startswith("  FAIL")]
    hit = [w for w in want if any(w in l for l in fails)]
    ok = (r.returncode == 0 and not fails) if not want else (r.returncode == 1 and hit == want)
    bad += not ok
    print(f"{'OK  ' if ok else 'BAD '} {name:30s} rc={r.returncode} n_fail={len(fails)} expected_red={want} caught={hit}")
    for l in fails: print("        " + l[:150])
    shutil.rmtree(d)
print("A10_MUTANTS", "PASS" if bad == 0 else f"FAIL {bad}")
sys.exit(1 if bad else 0)
