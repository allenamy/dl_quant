"""0C — [4i] census red test: a counting site must APPLY the predicate, not merely import it.

Written 2026-07-28T00:5xZ, criteria BEFORE the fix (team-lead ruling 2026-07-28: the E outlet
must be closed before the first rehearsal anchor runs). 0C writes the criteria; 0B writes the fix.

────────────────────────────────────────────────────────────────────────────────────────────────
THE LADDER, AND WHY THIS FILE TESTS THE WHOLE OF IT

  v1  substring "is_rehearsal" in the file        -> defeated by 0C mutation A' (a COMMENT
                                                     restores the substring; in this repo comments
                                                     discuss the predicate everywhere)
  v2  AST: the file IMPORTS the predicate         -> defeated by 0C mutation E (measured
                                                     2026-07-28T00:2xZ: delete the exclusion in
                                                     ops/score_post_fix.py, keep the import,
                                                     BOTH suites stay ALL PASS — 50 checks and
                                                     16 checks)
  v3  AST: the file CALLS the predicate           -> defeated by E2 below, and that is the point
                                                     of writing E2 now rather than after v3 ships
  v4  BEHAVIOUR: rehearsal rows do not enter the count

★ THE RULE THIS ENCODES: every rung of that ladder tests a PROPERTY OF THE TEXT except the last.
  Text can be present, well-formed, and parsed by an AST while the behaviour is wrong. Only v4
  asserts the thing anyone actually wants. v3 is worth having as a cheap uniform net — but it must
  not be mistaken for the guarantee, which is exactly the mistake v2 made in v1's place.

★ WHY E2 IS NOT A CONTRIVANCE. "Call the predicate and ignore what it returns" is what a partial
  refactor leaves behind: someone rewrites a comprehension, keeps the call for its (nonexistent)
  side effect, and the value stops reaching the filter. It is the same shape as this repo's
  `venue_reject`/`filled_notional` family — the call happened, the result went nowhere.
"""
import os
import shutil
import subprocess
import sys
import tempfile

SRC = "/Users/haosiyu/dl_quant_live"
TARGET = "live/tests_rehearsal_anchor.py"
DIRS = ("live", "ops", "scheduler", "signal", "config")

FAILS, N = [], [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def snapshot():
    d = tempfile.mkdtemp(prefix="redtest_4i_")
    for sub in DIRS:
        s = os.path.join(SRC, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(d, sub),
                            ignore=shutil.ignore_patterns("__pycache__"))
    return d


def run(root):
    """(exit_code, tail). Non-zero = the suite went red."""
    p = subprocess.run([sys.executable, TARGET], cwd=root, capture_output=True, text=True)
    tail = [ln for ln in (p.stdout or "").splitlines() if "ALL PASS" in ln or "FAILURES" in ln]
    return p.returncode, (tail[-1][:150] if tail else (p.stderr or "")[-150:])


def edit(root, rel, old, new):
    p = os.path.join(root, rel)
    s = open(p).read()
    if old not in s:
        return False
    open(p, "w").write(s.replace(old, new, 1))
    return True


EXCL = "if t in _anchor_ats and not RID.is_rehearsal(r)}"

print("=" * 96)
print("[4i] RED TEST — the census must require APPLICATION, not presence")
print("=" * 96)

base = snapshot()
rc0, t0 = run(base)
check("PRE-ASSERT: the unmutated suite is GREEN (else every result below is meaningless)",
      rc0 == 0, t0)
shutil.rmtree(base, ignore_errors=True)

# ── E1: keep the import, delete the exclusion ──────────────────────────────────────────────────
r = snapshot()
applied = edit(r, "ops/score_post_fix.py", EXCL, "if t in _anchor_ats}")
check("PRE-ASSERT: mutation E1 actually applied (a no-op edit would fake a red)", applied)
rc1, t1 = run(r)
shutil.rmtree(r, ignore_errors=True)
check("★★ E1  import kept, exclusion DELETED ⇒ the suite must go RED", rc1 != 0, t1)

# ── E2: keep the import AND a call, discard the result ─────────────────────────────────────────
r = snapshot()
applied = edit(r, "ops/score_post_fix.py", EXCL,
               "if (RID.is_rehearsal(r), t in _anchor_ats)[1]}")
check("PRE-ASSERT: mutation E2 actually applied", applied)
rc2, t2 = run(r)
shutil.rmtree(r, ignore_errors=True)
check("★★ E2  the predicate is CALLED but its answer is thrown away ⇒ must go RED",
      rc2 != 0, t2)
if rc2 == 0:
    print("      ⇒ an AST `Call` check is satisfied here. Only a BEHAVIOURAL assertion")
    print("        ('a rehearsal row does not enter this site's count') can see E2.")

# ── F1: a counting site outside the searched directories ───────────────────────────────────────
r = snapshot()
os.makedirs(os.path.join(r, "tools"), exist_ok=True)
open(os.path.join(r, "tools", "cert_counter.py"), "w").write(
    'def n(rows):\n    return sum(1 for r in rows if r.get("rebalance_id"))\n')
rc3, t3 = run(r)
shutil.rmtree(r, ignore_errors=True)
check("★★ F1  a counting site in tools/ (outside the four typed dirs) ⇒ must go RED",
      rc3 != 0, t3)
if rc3 == 0:
    print("      ⇒ the FILE LIST is computed but the SEARCH SCOPE is typed. `vendor/` holds 14")
    print("        live .py today; it is outside the census and fails toward green.")

# ── G: the control 0B already closed — proves this harness can see a red at all ────────────────
r = snapshot()
open(os.path.join(r, "ops", "new_counter.py"), "w").write(
    'def by_day(rows):\n    return {r["rebalance_id"]: 1 for r in rows}\n')
rc4, t4 = run(r)
shutil.rmtree(r, ignore_errors=True)
check("★ G  CONTROL: an undeclared counting site inside ops/ is already RED today",
      rc4 != 0, t4)

print(f"\n  {N[0]} checks run")
if N[0] == 0:
    print("  FAIL  ZERO CHECKS RAN — an empty suite is a RED, not a pass")
    sys.exit(1)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
sys.exit(0 if not FAILS else 1)
