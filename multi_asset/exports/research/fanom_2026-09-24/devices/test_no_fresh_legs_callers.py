"""test_no_fresh_legs_callers.py — enforce the retirement of fresh_legs.py from OUTSIDE the file.

Lead ruling 2026-09-26: `fresh_legs.py` stays byte-identical to what the FRESH training receipts pin
(a pinned source file must not be edited in place), so the retirement is enforced here instead.

Asserts, across every .py and .sh in this device suite:
  1. nothing IMPORTS fresh_legs (import fresh_legs / from fresh_legs import / importlib on its path);
  2. nothing INVOKES it as a subprocess (python ... fresh_legs.py, or bare fresh_legs.py in a shell line);
  3. the file's sha still equals the pinned value -- if it drifts, the FRESH provenance chain breaks again.

RED CONTROL: run with --red. It plants each forbidden form in a temporary file inside the suite and requires
the scan to FAIL on it, then removes it. A test that has never failed is not known to be able to fail.

usage: ... test_no_fresh_legs_callers.py WL [--red]
"""
import os, sys, re, json, hashlib, time

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
RED = "--red" in sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__))
PINNED = "97077d7e890223a966ed190ff4a1d6ff"          # first 32 hex of the sha the FRESH training receipt pins
TARGET = "fresh_legs"
# lead ruling 2026-09-26: news_p2_build.py is PINNED, so its gate lives in news_p2_build_guarded.py. Nothing may
# invoke the pinned file directly -- only the wrapper may. This is the same enforcement shape as fresh_legs, but the
# reason differs: fresh_legs is RETIRED (never run it), news_p2_build is GATED (run it only through the wrapper).
GUARDED_TARGET = "news_p2_build"

IMPORT_PAT = re.compile(r"^\s*(?:import\s+fresh_legs|from\s+fresh_legs\s+import)", re.M)
# the wrapper itself legitimately runpy's the pinned file; everything else must go through the wrapper
G_SUBPROC_SH = re.compile(r"(?:^|[;&|]|\$\()\s*(?:(?:/\S+/)?(?:python[0-9.]*|bash|sh)\s+(?:-\S+\s+)*\S*news_p2_build\.py"
                          r"|\./news_p2_build\.py)", re.M)
G_SUBPROC_PY = re.compile(r"(?:subprocess\.\w+|os\.system|os\.popen|os\.exec\w*|runpy\.run_path)\([^\n]*news_p2_build\.py", re.M)
G_IMPORT_PAT = re.compile(r"^\s*(?:import\s+news_p2_build|from\s+news_p2_build\s+import)", re.M)
IMPORTLIB_PAT = re.compile(r"spec_from_file_location\([^)]*fresh_legs", re.S)
# ★ FIRST VERSION WAS WRONG and its own run proved it: a bare `fresh_legs.py(?=\s|$)` alternative matched the
# name in PROSE and reported 19 "violations", every one of them a docstring citing the file's line numbers.
# That is a TEXTUAL instrument used for a BEHAVIOURAL property. An invocation is not a mention, so the pattern
# now requires an actual call MECHANISM on the same line:
#   * shell: the file passed to an interpreter (python/bash/sh), or executed at a command position
#   * python: subprocess./os.system/os.popen/os.exec* naming it
SUBPROC_SH = re.compile(r"(?:^|[;&|]|\$\()\s*(?:(?:/\S+/)?(?:python[0-9.]*|bash|sh)\s+(?:-\S+\s+)*\S*fresh_legs\.py"
                        r"|\./fresh_legs\.py)", re.M)
SUBPROC_PY = re.compile(r"(?:subprocess\.\w+|os\.system|os\.popen|os\.exec\w*)\([^\n]*fresh_legs\.py", re.M)
# the sidecar and this test are allowed to NAME it; they must not call it
EXEMPT = {"test_no_fresh_legs_callers.py", "fresh_legs.DEPRECATED.md", "fresh_legs.py"}
# the wrapper is the ONE sanctioned caller of the pinned builder; the pinned file may name itself
G_EXEMPT = {"test_no_fresh_legs_callers.py", "news_p2_build_guarded.py", "news_p2_build.py"}


def scan(extra=None):
    """returns list of (file, kind, line_no, line) violations"""
    bad = []
    files = [f for f in sorted(os.listdir(HERE)) if f.endswith((".py", ".sh"))]
    if extra: files = files + [extra]
    for f in files:
        if f in EXEMPT: continue
        p = os.path.join(HERE, f)
        try:
            with open(p, errors="replace") as fh: txt = fh.read()
        except Exception: continue
        pats = [(IMPORT_PAT, "IMPORT"), (IMPORTLIB_PAT, "IMPORTLIB"), (SUBPROC_PY, "SUBPROCESS")]
        if f.endswith(".sh"): pats.append((SUBPROC_SH, "SUBPROCESS"))
        if f not in G_EXEMPT:
            pats += [(G_IMPORT_PAT, "GUARDED_BYPASS_IMPORT"), (G_SUBPROC_PY, "GUARDED_BYPASS_CALL")]
            if f.endswith(".sh"): pats.append((G_SUBPROC_SH, "GUARDED_BYPASS_CALL"))
        for pat, kind in pats:
            for m in pat.finditer(txt):
                ln = txt[:m.start()].count("\n") + 1
                bad.append((f, kind, ln, txt.split("\n")[ln - 1].strip()[:110]))
    return bad


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


rec = {"device": "test_no_fresh_legs_callers.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "enforces": ("lead ruling 2026-09-26: enforcement lives OUTSIDE pinned files. fresh_legs.py is RETIRED "
                    "(no caller at all); news_p2_build.py is PINNED AND GATED (callable only via "
                    "news_p2_build_guarded.py, which applies require_clean_fund_replay with no allow)"),
       "suite_dir": HERE}

# ---- 3. the pinned file must not have drifted ----
fl = os.path.join(HERE, "fresh_legs.py")
cur = sha(fl) if os.path.exists(fl) else None
rec["fresh_legs_sha256"] = cur
rec["sha_matches_pinned"] = bool(cur and cur.startswith(PINNED))

# ---- 1-2. no callers ----
viol = scan()
rec["violations"] = [{"file": f, "kind": k, "line": ln, "text": t} for f, k, ln, t in viol]
rec["n_violations"] = len(viol)

# ---- RED CONTROL ----
if RED:
    red = []
    for kind, body in (("IMPORT", "import fresh_legs\n"),
                       ("IMPORTLIB", 'spec_from_file_location("x", "/tmp/fresh_legs.py")\n'),
                       ("SUBPROCESS", "/workspace/venv/bin/python -B fresh_legs.py PATH,HOME\n"),
                       ("SUBPROCESS_PY", 'subprocess.run(["python", "fresh_legs.py"])\n'),
                       ("GUARDED_BYPASS_PY", 'subprocess.run(["python", "news_p2_build.py", "merge"])\n'),
                       ("GUARDED_BYPASS_SH", "/workspace/venv/bin/python -B news_p2_build.py merge\n")):
        tmp = os.path.join(HERE, "_RED_PROBE_tmp.sh" if kind in ("SUBPROCESS", "GUARDED_BYPASS_SH") else "_RED_PROBE_tmp.py")
        with open(tmp, "w") as f: f.write(body)
        try:
            caught = [v for v in scan() if v[0] == os.path.basename(tmp)]
            red.append({"kind": kind, "planted": body.strip()[:60], "detected": bool(caught)})
        finally:
            os.remove(tmp)
    # ★ the defect this test itself had: prose that NAMES the file was reported as a violation. So the red
    # control also plants a pure MENTION and requires it NOT to be flagged -- otherwise the fix is unverified.
    tmpm = os.path.join(HERE, "_RED_MENTION_tmp.py")
    with open(tmpm, "w") as f:
        f.write('"""see fresh_legs.py L80-81 for the RN8 derivation; fresh_legs.py is retired."""\n')
    try:
        mention_flagged = bool([v for v in scan() if v[0] == os.path.basename(tmpm)])
    finally:
        os.remove(tmpm)
    red.append({"kind": "PROSE_MENTION_must_NOT_flag", "planted": "docstring naming the file",
                "detected": not mention_flagged, "note": "detected=True here means the mention was CORRECTLY ignored"})
    rec["red_control"] = red
    rec["red_control_all_fired"] = all(r["detected"] for r in red)

out = os.path.join(HERE, "TEST_NO_FRESH_LEGS_CALLERS.json")
tmp = out + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1); f.flush(); os.fsync(f.fileno())
with open(tmp) as f:
    assert json.load(f) == json.loads(json.dumps(rec)), "receipt did not read back equal"
os.replace(tmp, out)

print("TEST_NO_FRESH_LEGS_CALLERS violations=%d  sha_matches_pinned=%s" % (rec["n_violations"], rec["sha_matches_pinned"]), flush=True)
for v in rec["violations"]:
    print("  VIOLATION %-10s %s:%d  %s" % (v["kind"], v["file"], v["line"], v["text"]), flush=True)
if RED:
    for r in rec["red_control"]:
        print("  red %-11s planted -> detected=%s" % (r["kind"], r["detected"]), flush=True)
    assert rec["red_control_all_fired"], "RED CONTROL FAILED: a planted caller was not detected -- the test is decorative"
assert rec["sha_matches_pinned"], f"fresh_legs.py drifted from the pinned sha ({cur}) -- FRESH provenance will break"
assert not viol, f"{len(viol)} caller(s) of the retired fresh_legs.py"
print("  PASS: nothing imports or invokes it, and the pinned sha is intact", flush=True)
