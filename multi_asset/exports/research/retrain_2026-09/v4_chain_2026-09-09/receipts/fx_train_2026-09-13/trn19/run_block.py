"""Run ONE test block of tests_pipeline_gates.py against a chosen device dir (RED runs on pre-fix sources). usage: run_block.py <device dir> <block.py>"""
import hashlib, json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.abspath(sys.argv[1]); BLOCK = os.path.abspath(sys.argv[2]); PY = sys.executable
FAILS, N = [], [0]
def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail != '' else ''}", flush=True)
    if not cond: FAILS.append(name)
print(f"BLOCK {BLOCK} sha {_sha(BLOCK)[:16]} on device dir {HERE} chain_lib {_sha(HERE + '/chain_lib.sh')[:16]}")
exec(compile(open(BLOCK).read(), BLOCK, "exec"))
print(f"\nBLOCK {'ALL PASS' if not FAILS else 'FAILURES: ' + str(len(FAILS))}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
