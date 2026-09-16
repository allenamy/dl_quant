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

HOOK = r'''
import runpy, sys, shutil
# R16RF-E2b: a deterministic model of "the records file changes between the check and the write" — at the applier's own
# tempfile.mkstemp event (checks already passed, nothing written yet) the records file is replaced by SWAP. The applier's
# source is not touched; it simply continues.
swap, dev = sys.argv[1], sys.argv[2]; sys.argv = [dev] + sys.argv[3:]
def _hook(event, args):
    if event == "tempfile.mkstemp":
        for i, a in enumerate(sys.argv):
            if a == "--records": shutil.copyfile(swap, sys.argv[i + 1])
sys.addaudithook(_hook)
runpy.run_path(dev, run_name="__main__")
'''
def run(dev, root, recf, sha, apply=False, swap=None):
    receipt = os.path.join(tempfile.mkdtemp(), "receipt.json")
    argv = [dev, "--root", root, "--records", recf, "--records-sha", sha, "--receipt", receipt] + (["--apply"] if apply else [])
    if swap is not None:
        hp = os.path.join(tempfile.mkdtemp(), "hook.py"); open(hp, "w").write(HOOK)
        argv = [hp, swap] + argv
    p = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    res = json.load(open(receipt)) if os.path.exists(receipt) else {}
    return p.returncode, (p.stdout + p.stderr).strip()[-300:], res.get("check_failures"), res.get("verdict"), res

print("[A] green baseline: correct records through the current applier (check mode)")
rc, out, fails, verdict, _ = run(DEV, *build(lambda i, rows: rows[i]["nav_ts"]))
check("★★★ A1 correct records: CHECKS_PASS, exit 0, failures []", rc == 0 and verdict == "CHECKS_PASS" and fails == [], (rc, verdict, fails))

print("\n[B] nav_ts swapped between the two records (day/line/row_sha all correct — the reviewer's construction)")
root_b, recf_b, sha_b = build(lambda i, rows: rows[1 - i]["nav_ts"])
rc, out, fails, verdict, _ = run(DEV, root_b, recf_b, sha_b)
c2b = [f for f in (fails or []) if f.startswith("C2b IDENTITY")]
check("★★★ B1 admission REFUSES (exit 2) with two C2b IDENTITY failures naming the claimed vs carried nav_ts",
      rc == 2 and len(c2b) == 2 and all("nav_ts=" in f for f in c2b), (rc, fails))
check("★★ B2 the refusal is the ONLY difference from [A]: same root shape, same shas, only the identity claim moved",
      rc == 2 and "C2 row mismatch" not in " ".join(fails or []), fails)

print("\n[C] record nav_ts is NaN (NaN != NaN must not pass as 'equal')")
rc, out, fails, verdict, _ = run(DEV, *build(lambda i, rows: float("nan") if i == 0 else rows[i]["nav_ts"]))
check("★★ C1 NaN identity claim is refused (exit 2, one C2b IDENTITY)", rc == 2 and len([f for f in (fails or []) if f.startswith("C2b IDENTITY")]) == 1, (rc, fails))

print("\n[E] R16RF-E2a: ±inf is NOT a finite value — row AND record both carry the same infinity (day/line/sha all match)")
def build_inf(sign):
    """the row itself carries ±inf nav_ts, and the record claims the same — the reviewer's construction."""
    root = tempfile.mkdtemp(prefix="led04_inf_"); day = "20260901"
    plog = os.path.join(root, "pilot_log", day); os.makedirs(plog)
    rows = [{"day": day, "nav_ts": sign * float("inf"), "nav": 1000.0, "prev_nav": 990.0, "realised_pnl": 11.0, "realised_by_type": {"COMMISSION": 11.0}, "mode": "LIVE"}]
    lines = [(json.dumps(r, separators=(",", ":")) + "\n").encode() for r in rows]      # json emits Infinity/-Infinity
    open(os.path.join(plog, "daily_nav.jsonl"), "wb").write(b"".join(lines))
    recs = [{"kind": KIND, "day": day, "nav_ts": sign * float("inf"), "line": 1, "row_sha256": hashlib.sha256(lines[0]).hexdigest(),
             "amended": {"realised_pnl_usdt": 100.0, "realised_usdt_by_type": {"COMMISSION": 100.0}}, "source": {"income_sha256": "t"}, "reason": "inf"}]
    recf = os.path.join(root, "records.jsonl"); open(recf, "w").write("".join(json.dumps(r) + "\n" for r in recs))
    return root, recf, hashlib.sha256(open(recf, "rb").read()).hexdigest()
for _sg, _lab in ((1, "+inf"), (-1, "-inf")):
    rc, out, fails, verdict, res = run(DEV, *build_inf(_sg), apply=True)
    check(f"★★★ E1 {_lab} in row and record: --apply REFUSES (exit 2, C2b IDENTITY), nothing written — the consumer's finite contract, at the writer",
          rc == 2 and any(f.startswith("C2b IDENTITY") for f in (fails or [])) and not res.get("apply"), (rc, fails, res.get("apply")))

print("\n[F] R16RF-E2b: the records file is REPLACED between the check and the write (audit hook at the applier's mkstemp)")
root_f, recf_f, sha_f = build(lambda i, rows: rows[i]["nav_ts"])                    # authorised: correct records
_, recf_swap, _ = build(lambda i, rows: rows[1 - i]["nav_ts"])                     # the bytes that appear after the check
rc, out, fails, verdict, res = run(DEV, root_f, recf_f, sha_f, apply=True, swap=recf_swap)
_tgt = os.path.join(root_f, "ledger_amendments", "daily_nav_realised_split.jsonl")
_persisted = hashlib.sha256(open(_tgt, "rb").read()).hexdigest() if os.path.exists(_tgt) else None
check("★★★ F1 what lands on disk is the AUTHORISED bytes (persisted sha == --records-sha), verdict PASS — the swapped bytes never reached the target",
      rc == 0 and verdict == "PASS" and _persisted == sha_f and res.get("persisted_sha256") == sha_f and res.get("records_bytes_captured_sha256") == sha_f,
      (rc, verdict, _persisted == sha_f, res.get("persisted_sha256") == sha_f))
_after = [json.loads(l) for l in open(_tgt)] if os.path.exists(_tgt) else []
check("★★ F2 …and the persisted records are the CORRECT ones (nav_ts not swapped): every record's nav_ts equals its row's",
      bool(_after) and all(float(r["nav_ts"]) == [60.0 + 1788220800.0, 3600.0 + 1788220800.0][r["line"] - 1] for r in _after) if False else
      bool(_after) and [r["nav_ts"] for r in _after] == [1.0, 2.0], [r.get("nav_ts") for r in _after])

print("\n[D] red capability: the pre-fix applier (defect shape: no C2b in checks) on arm [B]'s root")
old, old_ref = None, None
for ref in ("ba247021", "HEAD", "HEAD~1", "HEAD~2", "HEAD~3"):     # pinned defect commit first (R16RF §3.1), moving window as fallback
    c = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{REL_DEV}"], capture_output=True, text=True)
    if c.returncode == 0 and "C2b" not in c.stdout and "def checks(root)" in c.stdout:
        old, old_ref = c.stdout, ref; break
if old is None:
    print("  UNAVAIL D  no ancestor within HEAD..HEAD~3 carries the pre-fix applier — control not run, not faked")
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed; control UNAVAILABLE"); sys.exit(3 if not FAILS else 1)
print(f"  (control source: {old_ref}:{REL_DEV})")
old_dev = os.path.join(tempfile.mkdtemp(), "led04_prefix.py"); open(old_dev, "w").write(old)
rc, out, fails, verdict, _ = run(old_dev, root_b, recf_b, sha_b)
check("★★★ D1 (PRE-FIX: RED) the swapped records are ADMITTED: CHECKS_PASS exit 0, failures [] — the reviewer's finding reproduced",
      rc == 0 and verdict == "CHECKS_PASS" and fails == [], (rc, verdict, fails))
# the second-round pre-fix source (has C2b, lacks the finite contract and the single capture) = fda1d3ef; probe it by shape
old2 = None
for ref in ("fda1d3ef", "HEAD~1", "HEAD~2", "HEAD~3"):
    c = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{REL_DEV}"], capture_output=True, text=True)
    if c.returncode == 0 and "C2b" in c.stdout and "math.isfinite" not in c.stdout and "RAW_SHA" not in c.stdout:
        old2 = c.stdout; print(f"  (second-round control source: {ref}:{REL_DEV})"); break
if old2 is None:
    print("  UNAVAIL D2/D3 no source with C2b but without the finite/single-capture contract — control not run, not faked")
else:
    old_dev2 = os.path.join(tempfile.mkdtemp(), "led04_r16r.py"); open(old_dev2, "w").write(old2)
    rc, out, fails, verdict, res = run(old_dev2, *build_inf(1), apply=True)
    check("★★★ D2 (PRE-FIX R16R: RED) +inf row+record is ADMITTED and WRITTEN by the second-round applier (exit 0, PASS, written 1) — R16RF-E2a reproduced",
          rc == 0 and verdict == "PASS" and (res.get("apply") or {}).get("written") == 1, (rc, verdict, res.get("apply")))
    root_d, recf_d, sha_d = build(lambda i, rows: rows[i]["nav_ts"]); _, recf_sw, _ = build(lambda i, rows: rows[1 - i]["nav_ts"])
    rc, out, fails, verdict, res = run(old_dev2, root_d, recf_d, sha_d, apply=True, swap=recf_sw)
    _t = os.path.join(root_d, "ledger_amendments", "daily_nav_realised_split.jsonl")
    _p = hashlib.sha256(open(_t, "rb").read()).hexdigest() if os.path.exists(_t) else None
    check("★★★ D3 (PRE-FIX R16R: RED) records swapped after the check: the second-round applier writes the SWAPPED bytes (persisted sha != authorised) and still exits 0 PASS — R16RF-E2b reproduced",
          rc == 0 and verdict == "PASS" and _p is not None and _p != sha_d, (rc, verdict, _p == sha_d))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
