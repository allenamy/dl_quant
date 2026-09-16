#!/usr/bin/env python3
"""R16R-E2 (independent review, second round, 2026-09-16): the amendment APPLIER's admission must bind identity.

WHY THIS FILE EXISTS. The first-round E2 fix taught the CONSUMER (`ledger_amendments._row_sha_ok`) to check that
the hashed row carries the nav_ts/day the record claims. The WRITE side — `led04_apply_amendments.checks()`,
the admission that decides whether a records file may be applied at all — still verified only line + row_sha.
Two records with correct day/line/row_sha and their nav_ts swapped passed admission with failures=[]. A consumer
that later rejects a bad record is a remedy for a record that should never have been admitted.

This file drives the applier as the operator does (subprocess, check mode, no --apply) on a real-shaped root:
  [A] correct records                      → CHECKS_PASS, exit 0, failures []          (green baseline)
  [B] nav_ts swapped between two records   → REFUSE, exit 2, two 'C2b IDENTITY' failures
  [C] record nav_ts = NaN (NaN != NaN)     → REFUSE, exit 2, 'C2b IDENTITY'
  [D] control: the pre-fix applier from git (defect shape: no C2b) on arm-[B]'s root → CHECKS_PASS exit 0 — RED
Arm [D] is the red-capability control WITH asserted-green baseline [A]. If no ancestor carries the pre-fix
shape the control is UNAVAILABLE (exit 3), never faked. No production path is touched; roots are temp dirs.
"""
import hashlib, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "led04_apply_amendments.py")
REPO = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
REL_DEV = os.path.relpath(DEV, REPO)
KIND = "daily_nav_realised_split_amendment"
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)

def build(nav_ts_for_record):
    """root with pilot_log/<day>/daily_nav.jsonl (2 PRE-FIX rows) and a records file with one record per row.
    `nav_ts_for_record(i, rows)` returns the nav_ts the record for row i CLAIMS (identity is the thing under test)."""
    root = tempfile.mkdtemp(prefix="led04_id_"); day = "20260901"
    plog = os.path.join(root, "pilot_log", day); os.makedirs(plog)
    rows = [{"day": day, "nav_ts": 1.0, "nav": 1000.0, "prev_nav": 990.0, "realised_pnl": 11.0, "realised_by_type": {"COMMISSION": 11.0}, "mode": "LIVE"},
            {"day": day, "nav_ts": 2.0, "nav": 1001.0, "prev_nav": 990.0, "realised_pnl": 12.0, "realised_by_type": {"COMMISSION": 12.0}, "mode": "LIVE"}]
    lines = [(json.dumps(r, separators=(",", ":")) + "\n").encode() for r in rows]
    open(os.path.join(plog, "daily_nav.jsonl"), "wb").write(b"".join(lines))
    recs = [{"kind": KIND, "day": day, "nav_ts": nav_ts_for_record(i, rows), "line": i + 1,
             "row_sha256": hashlib.sha256(lines[i]).hexdigest(),
             "amended": {"realised_pnl_usdt": 100.0 + i, "realised_usdt_by_type": {"COMMISSION": 100.0 + i}},
             "source": {"income_sha256": "t"}, "reason": "identity test"} for i in range(2)]
    recf = os.path.join(root, "records.jsonl")
    open(recf, "w").write("".join(json.dumps(r) + "\n" for r in recs))
    return root, recf, hashlib.sha256(open(recf, "rb").read()).hexdigest()

def run(dev, root, recf, sha):
    receipt = os.path.join(tempfile.mkdtemp(), "receipt.json")
    p = subprocess.run([sys.executable, dev, "--root", root, "--records", recf, "--records-sha", sha, "--receipt", receipt],
                       capture_output=True, text=True)
    res = json.load(open(receipt)) if os.path.exists(receipt) else {}
    return p.returncode, (p.stdout + p.stderr).strip()[-300:], res.get("check_failures"), res.get("verdict")

print("[A] green baseline: correct records through the current applier (check mode)")
rc, out, fails, verdict = run(DEV, *build(lambda i, rows: rows[i]["nav_ts"]))
check("★★★ A1 correct records: CHECKS_PASS, exit 0, failures []", rc == 0 and verdict == "CHECKS_PASS" and fails == [], (rc, verdict, fails))

print("\n[B] nav_ts swapped between the two records (day/line/row_sha all correct — the reviewer's construction)")
root_b, recf_b, sha_b = build(lambda i, rows: rows[1 - i]["nav_ts"])
rc, out, fails, verdict = run(DEV, root_b, recf_b, sha_b)
c2b = [f for f in (fails or []) if f.startswith("C2b IDENTITY")]
check("★★★ B1 admission REFUSES (exit 2) with two C2b IDENTITY failures naming the claimed vs carried nav_ts",
      rc == 2 and len(c2b) == 2 and all("nav_ts=" in f for f in c2b), (rc, fails))
check("★★ B2 the refusal is the ONLY difference from [A]: same root shape, same shas, only the identity claim moved",
      rc == 2 and "C2 row mismatch" not in " ".join(fails or []), fails)

print("\n[C] record nav_ts is NaN (NaN != NaN must not pass as 'equal')")
rc, out, fails, verdict = run(DEV, *build(lambda i, rows: float("nan") if i == 0 else rows[i]["nav_ts"]))
check("★★ C1 NaN identity claim is refused (exit 2, one C2b IDENTITY)", rc == 2 and len([f for f in (fails or []) if f.startswith("C2b IDENTITY")]) == 1, (rc, fails))

print("\n[D] red capability: the pre-fix applier (defect shape: no C2b in checks) on arm [B]'s root")
old, old_ref = None, None
for ref in ("HEAD", "HEAD~1", "HEAD~2", "HEAD~3"):
    c = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{REL_DEV}"], capture_output=True, text=True)
    if c.returncode == 0 and "C2b" not in c.stdout and "def checks(root)" in c.stdout:
        old, old_ref = c.stdout, ref; break
if old is None:
    print("  UNAVAIL D  no ancestor within HEAD..HEAD~3 carries the pre-fix applier — control not run, not faked")
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed; control UNAVAILABLE"); sys.exit(3 if not FAILS else 1)
print(f"  (control source: {old_ref}:{REL_DEV})")
old_dev = os.path.join(tempfile.mkdtemp(), "led04_prefix.py"); open(old_dev, "w").write(old)
rc, out, fails, verdict = run(old_dev, root_b, recf_b, sha_b)
check("★★★ D1 (PRE-FIX: RED) the swapped records are ADMITTED: CHECKS_PASS exit 0, failures [] — the reviewer's finding reproduced",
      rc == 0 and verdict == "CHECKS_PASS" and fails == [], (rc, verdict, fails))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
