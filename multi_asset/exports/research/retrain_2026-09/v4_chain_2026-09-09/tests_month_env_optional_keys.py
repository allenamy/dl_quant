#!/usr/bin/env python3
"""FP2-3: optional contract keys. The frozen September contract must still load; a contract carrying PREV_MONTH_ENV/PREV_SHA_JSON loads;
an unregistered key is still refused; a missing REQUIRED key is still refused; a present-but-EMPTY optional key is refused."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:200]) if detail is not None else ""), flush=True)
def load(envfile):
    cmd = f'source "{HERE}/chain_lib.sh" 2>/dev/null; load_month_env "{envfile}" && echo LOADED_OK'
    p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=dict(os.environ, PY=sys.executable, D=HERE, R=tempfile.mkdtemp()))
    return ("LOADED_OK" in p.stdout), (p.stdout + p.stderr)[-300:]
sep = os.path.join(HERE, "v4_month_2026-09.env"); base = open(sep, encoding="utf-8").read()
ok, out = load(sep)
if not ok and "PY" in out and "not found" in out:
    print("  UNAVAIL chain_lib.sh not sourceable in this environment — control not run"); print(f"\n{N[0]}/{N[0]} checks passed; UNAVAILABLE"); sys.exit(3)
check("★★★ the frozen September contract (no optional keys) still loads", ok, out)
d = tempfile.mkdtemp()
def mk(extra, drop=None):
    lines = [l for l in base.splitlines() if not (drop and l.startswith(drop + "="))]
    p = os.path.join(d, "c.env"); open(p, "w").write("\n".join(lines + extra) + "\n"); return p
ok, out = load(mk([f"PREV_MONTH_ENV={sep}", f"PREV_SHA_JSON={HERE}/v4_scripts_sha_full.json"]))
check("★★★ a contract carrying PREV_MONTH_ENV and PREV_SHA_JSON loads (optional keys accepted)", ok, out)
ok, out = load(mk(["SOMETHING_ELSE=/x"]))
check("★★★ an unregistered key is still refused", not ok and "unregistered" in out or "malformed" in out, out)
ok, out = load(mk([], drop="CACHE"))
check("★★★ a missing REQUIRED key is still refused (key_missing)", not ok and "key_missing" in out, out)
ok, out = load(mk(["PREV_MONTH_ENV="]))
check("★★ a present-but-EMPTY optional key is refused", not ok and "key_missing" in out, out)
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
