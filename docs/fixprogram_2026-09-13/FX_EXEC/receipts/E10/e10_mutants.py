"""E10 mutation controls: each mutant removes ONE property from ops/notarize_ledgers.py in a temp copy of the tree; the suite must go
red on the named cells (and only the suite is run). Refuses a mutant whose target text does not match exactly once."""
import os, re, shutil, subprocess, sys, tempfile, json
SRC_TREE = "/Users/haosiyu/cc_tmp/fx_exec"
MUTANTS = [
 ("M1_listing_error_read_as_empty", '        return sorted(os.listdir(path))\n    except OSError as e:\n        raise NotaryError(',
  '        return sorted(os.listdir(path))\n    except OSError as e:\n        return []\n        raise NotaryError(', ["W1"]),
 ("M2_checkpoint_not_cut_at_newline", '    cut = data.rfind(b"\\n") + 1', '    cut = len(data)', ["W11"]),
 ("M3_commit_without_pathspec", '    git("commit", "commit", "-q", "-m", message, "--", *rel)', '    git("commit", "commit", "-q", "-m", message)', ["W5"]),
 ("M4_push_rc_ignored", '        git("push", "push", "-q", push_remote, branch)', '        run(["git", "-C", repo, "push", "-q", push_remote, branch], capture_output=True, text=True)', ["W3"]),
 ("M5_branch_check_removed", '    if cur != branch:\n', '    if False:\n', ["W4"]),
 ("M6_no_line_boundary_check", '    if bytes_ > 0 and data[bytes_ - 1:bytes_] != b"\\n":', '    if False:', ["V5"]),
 ("M7_amendment_hash_unchecked", '                elif len(data) < int(c["bytes"]) or hashlib.sha256(data[:int(c["bytes"])]).hexdigest() != c["sha256"]:',
  '                elif len(data) < int(c["bytes"]):', ["V6b", "R4"]),
 ("M8_genesis_midchain_linked", '        elif rec == prev_sha:', '        elif rec == prev_sha or rec == GENESIS:', ["R2"]),
 ("M9_findings_dropped", '            findings.append({"day": day, "file": fn, "verdict": v, "why": f"against {cp[\'source\']}: {why}"})',
  '            pass', ["W10"]),
 ("M10_genesis_inferred", '    elif genesis:', '    elif True:', ["W8"]),
 ("M11_manifest_rewritten", '    with open(path, "x") as f:', '    with open(path, "w") as f:', ["W7b"]),
 ("M12_all_files_notarized", '    tables = schema_tables()\n    files = {}', '    tables = present\n    files = {}', ["W6"]),
 ("M13_appends_not_recorded", '            appends.append({"day": day,', '            (lambda *a: None)({"day": day,', ["W9"]),
 ("M14_growth_launders_prefix_change", '    if hashlib.sha256(data[:bytes_]).hexdigest() != sha256:\n        return "TAMPERED"',
  '    if len(data) == bytes_ and hashlib.sha256(data[:bytes_]).hexdigest() != sha256:\n        return "TAMPERED"', ["V3"]),
 ("M15_segment_attestation_dropped", '                        att = [src for c0, c1, src in pairs if int(c0["bytes"]) <= a and int(c1["bytes"]) >= b]', '                        att = []', ["V6", "R1"]),
]
only = sys.argv[1:]
res = []
for name, old, new, expect in MUTANTS:
    if only and name not in only: continue
    t = tempfile.mkdtemp(prefix="e10mut_")
    try:
        for d in ("ops", "config"):
            shutil.copytree(os.path.join(SRC_TREE, d), os.path.join(t, d))
        os.makedirs(os.path.join(t, "live", "tests_fixtures"))
        for fn in os.listdir(os.path.join(SRC_TREE, "live")):
            if fn.endswith(".py"): shutil.copy(os.path.join(SRC_TREE, "live", fn), os.path.join(t, "live", fn))
        shutil.copytree(os.path.join(SRC_TREE, "live", "tests_fixtures", "e10_notary"), os.path.join(t, "live", "tests_fixtures", "e10_notary"))
        p = os.path.join(t, "ops", "notarize_ledgers.py"); s = open(p).read()
        n = s.count(old)
        if n != 1:
            res.append((name, "TARGET_MATCH_%d" % n, [], expect)); print(name, "TARGET_MATCH", n, flush=True); continue
        open(p, "w").write(s.replace(old, new, 1))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run(["/usr/bin/python3", os.path.join(t, "live", "tests_ledger_notary.py")], capture_output=True, text=True, env=env, timeout=600, cwd=os.path.join(t, "live"))
        fails = [re.match(r"^  FAIL  (?:★+ )?(\S+)", l).group(1) for l in r.stdout.splitlines() if re.match(r"^  FAIL  (?:★+ )?(\S+)", l)]
        tb = "Traceback" in r.stdout + r.stderr
        ok = r.returncode != 0 and all(e in fails for e in expect) and not tb
        res.append((name, "KILLED" if ok else "SURVIVED", fails, expect)); print(name, "rc", r.returncode, "fails", fails, "expect", expect, "traceback", tb, "=>", "KILLED" if ok else "SURVIVED", flush=True)
    finally:
        shutil.rmtree(t, ignore_errors=True)
print("SUMMARY", json.dumps({"n": len(res), "killed": sum(1 for r in res if r[1] == "KILLED"), "not_killed": [r[0] for r in res if r[1] != "KILLED"]}))
