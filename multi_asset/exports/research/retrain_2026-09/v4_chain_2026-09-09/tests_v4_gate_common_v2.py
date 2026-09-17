#!/usr/bin/env python3
"""FP2-4 (2026-09-17): the three-state finalize3 and the readers that consume its receipts.

  [A] three verdicts → receipt fields, printed label, exit code (real subprocess, real receipt on disk)
  [B] the frozen two-state finalize is byte-identical to its pinned sha (the successor did not edit it)
  [C] the existing readers (chain_lib.sh receipt check; the monthly preflight's roll-receipt block) REFUSE an
      UNAVAILABLE receipt — an unevaluated check is never read as passed — and accept a PASS receipt
  [D] verdict_of derives UNAVAILABLE only when nothing failed and something was unevaluated
"""
import hashlib, json, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
FROZEN_SHA8 = "24e813f1"
def sha8(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]

print("[A] three verdicts through a real gate script")
def run_gate(res):
    d = tempfile.mkdtemp(); out = os.path.join(d, "r.json"); g = os.path.join(d, "g.py")
    open(g, "w").write(f"import sys; sys.path.insert(0, {HERE!r})\nfrom v4_gate_common_v2 import finalize3\nfinalize3('T', {res!r}, {out!r}, {{}})\n")
    p = subprocess.run([sys.executable, g], capture_output=True, text=True)
    r = json.load(open(out)) if os.path.exists(out) else {}
    return p.returncode, p.stdout.strip(), r
rc, o, r = run_gate({"PASS": True, "VERDICT": "PASS"})
check("★★★ PASS: exit 0, label 'T PASS', PASS True, VERDICT PASS, schema v2", rc == 0 and o.startswith("T PASS") and r.get("PASS") is True and r.get("VERDICT") == "PASS" and "v2" in r.get("receipt_schema", ""), (rc, o, r.get("VERDICT")))
rc, o, r = run_gate({"PASS": False, "VERDICT": "FAIL", "failed_checks": ["P4"]})
check("★★★ FAIL: exit 3, label 'T FAIL', PASS False, VERDICT FAIL", rc == 3 and o.startswith("T FAIL") and r.get("PASS") is False and r.get("VERDICT") == "FAIL", (rc, o))
rc, o, r = run_gate({"PASS": False, "VERDICT": "UNAVAILABLE", "unevaluated_checks": ["P4"]})
check("★★★ UNAVAILABLE: exit 3 (non-zero), label 'T UNAVAILABLE' (not FAIL), PASS False, VERDICT UNAVAILABLE", rc == 3 and o.startswith("T UNAVAILABLE") and r.get("PASS") is False and r.get("VERDICT") == "UNAVAILABLE", (rc, o))
rc, o, r = run_gate({"PASS": True, "VERDICT": "UNAVAILABLE"})
check("★★ a result that says PASS=True but VERDICT=UNAVAILABLE is written as UNAVAILABLE with PASS False — VERDICT wins, PASS is derived", r.get("PASS") is False and r.get("VERDICT") == "UNAVAILABLE" and rc == 3, (rc, r.get("PASS")))

print("\n[B] the frozen module is untouched")
check(f"★★★ v4_gate_common.py sha8 == {FROZEN_SHA8} (frozen device not edited by the successor)", sha8(os.path.join(HERE, "v4_gate_common.py")) == FROZEN_SHA8, sha8(os.path.join(HERE, "v4_gate_common.py")))

print("\n[C] existing readers refuse an UNAVAILABLE receipt and accept a PASS receipt")
_, _, r_un = run_gate({"PASS": False, "VERDICT": "UNAVAILABLE", "unevaluated_checks": ["P4"]})
_, _, r_ok = run_gate({"PASS": True, "VERDICT": "PASS"})
# reader 1: the monthly preflight's roll-receipt block, reduced to its verdict test (chain_v4_monthly.sh L90: PASS is not True ⇒ fail)
def preflight_reads(rr): return rr.get("PASS") is True
check("★★★ preflight reader: UNAVAILABLE receipt ⇒ fails; PASS receipt ⇒ accepted", not preflight_reads(r_un) and preflight_reads(r_ok))
# reader 2: chain_lib.sh's receipt check (L228: `if r.get("PASS") is not True: ... fail`)
lib = open(os.path.join(HERE, "chain_lib.sh"), encoding="utf-8", errors="replace").read()
check("★★ chain_lib.sh receipt check reads the JSON PASS field with `is not True` (an UNAVAILABLE receipt cannot pass it)", 'r.get("PASS") is not True' in lib)
# reader 3: compare_gate_receipts reads PASS fields, not printed labels
cmp_src = open(os.path.join(HERE, "compare_gate_receipts.py"), encoding="utf-8").read()
check("★ compare_gate_receipts reads PASS from JSON", 'get("PASS")' in cmp_src)
# nobody parses the printed label of finalize
scripts = [f for f in os.listdir(HERE) if f.endswith(".sh")]
label_parsers = [f for f in scripts if re.search(r"grep[^\n]*\bPASS\b[^\n]*->", open(os.path.join(HERE, f), errors="replace").read())]
check("★★ no chain script parses finalize's printed 'GATE PASS -> path' label", not label_parsers, label_parsers)

print("\n[D] verdict_of")
from v4_gate_common_v2 import verdict_of
check("★★ verdict_of: PASS / FAIL(failed) / UNAVAILABLE(only unevaluated) / FAIL(both failed and unevaluated)",
      verdict_of({"PASS": True}) == "PASS" and verdict_of({"PASS": False, "failed_checks": ["x"]}) == "FAIL"
      and verdict_of({"PASS": False, "unevaluated_checks": ["x"]}) == "UNAVAILABLE"
      and verdict_of({"PASS": False, "failed_checks": ["x"], "unevaluated_checks": ["y"]}) == "FAIL")
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
