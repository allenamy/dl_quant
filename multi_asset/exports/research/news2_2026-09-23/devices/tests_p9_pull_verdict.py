#!/usr/bin/env python3
"""tests_p9_pull_verdict.py -- red/green tests for p9_pull_verdict.py (news2 class fix of the puller exit codes, 2026-09-27).

The class: the drivers read the puller's exit code 1 as "checksum mismatch" and answer it by DELETING zips and re-fetching. Rev 1 made
the puller exit 4 on any failure it can catch -- but Python itself exits 1 for anything raised before the hook is installed (an import,
a syntax error), and ssh / the kernel / the shell have their own codes. So an exit code is not evidence of a mismatch. The repair
signal is now a POSITIVE statement from THIS run: a manifest carrying this run's nonce, a consistent intended exit code, and >= 1
entry with checksum_match False. Anything else is FAILED, including shapes nobody has thought of yet.
usage: python3 -B tests_p9_pull_verdict.py [out.json]
"""
import hashlib, json, os, sys, tempfile
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import p9_pull_verdict as V

RES = []
def cell(n, fn):
    try: fn(); RES.append((n, True, ""))
    except AssertionError as e: RES.append((n, False, "assert: %s" % e))
    except Exception as e: RES.append((n, False, "%s: %s" % (type(e).__name__, e)))

M = "2026-09"; N = "run-abc-2026-09-p1"
def man(d, files=None, nonce=N, month=M, intended=None, n_symbols=None, raw=None):
    p = os.path.join(d, "MANIFEST_%s.json" % month)
    if raw is not None:
        open(p, "w").write(raw); return p
    files = {"AUSDT": {"status": 200, "checksum_match": True, "sha256": "a" * 64}} if files is None else files
    bad = sum(1 for v in files.values() if v.get("checksum_match") is False)
    body = {"month": month, "run_nonce": nonce, "n_symbols": len(files) if n_symbols is None else n_symbols,
            "intended_rc": (1 if bad else 0) if intended is None else intended, "files": files}
    if nonce is None: del body["run_nonce"]
    if intended == "absent": del body["intended_rc"]
    open(p, "w").write(json.dumps(body)); return p
def td(): return tempfile.mkdtemp(prefix="p9v_")
BAD = {"AUSDT": {"status": 200, "checksum_match": True}, "BUSDT": {"status": 200, "checksum_match": False}}

def expect(v, rc, path, nonce=N, month=M, why=None):
    """`why` pins the reason: a red cell that goes FAILED for a different reason than the one it was written for is not
    testing its rule (a check placed earlier would be masking it)."""
    got = V.verdict(rc, path, nonce, month)
    assert got["verdict"] == v, "expected %s, got %s (%s)" % (v, got["verdict"], got["reason"])
    assert why is None or why in got["reason"], "FAILED for the wrong reason: %r lacks %r" % (got["reason"], why)
    return got

# baseline
cell("G1_rc0_fresh_manifest_no_mismatch_OK", lambda: expect("OK", 0, man(td())))
cell("G2_rc1_fresh_manifest_with_mismatch_MISMATCH", lambda: expect("MISMATCH", 1, man(td(), BAD)))
cell("G3_404_entries_are_not_a_failure", lambda: expect("OK", 0, man(td(), {"AUSDT": {"status": 200, "checksum_match": True},
                                                                         "CUSDT": {"status": 404}})))
def g4():
    g = expect("MISMATCH", 1, man(td(), BAD))
    assert g["mismatch"] == ["BUSDT"], g
cell("G4_mismatch_names_the_symbols", g4)

# red: every shape that is not a positive statement from this run
cell("R1_rc1_no_manifest_is_FAILED_not_MISMATCH", lambda: expect("FAILED", 1, os.path.join(td(), "MANIFEST_%s.json" % M), why="no manifest file"))
cell("R2_rc1_stale_manifest_other_nonce_FAILED", lambda: expect("FAILED", 1, man(td(), BAD, nonce="run-OLD-p1"), why="stale manifest"))
cell("R3_rc1_manifest_without_nonce_FAILED", lambda: expect("FAILED", 1, man(td(), BAD, nonce=None), why="stale manifest"))
cell("R4_rc1_but_manifest_has_no_mismatch_FAILED", lambda: expect("FAILED", 1, man(td(), intended=1), why="inconsistent"))
cell("R5_rc0_but_manifest_has_mismatch_FAILED", lambda: expect("FAILED", 0, man(td(), BAD, intended=0), why="inconsistent"))
cell("R6_rc4_puller_failure_FAILED", lambda: expect("FAILED", 4, man(td()), why="neither 0 nor 1"))
cell("R7_rc137_killed_FAILED", lambda: expect("FAILED", 137, man(td()), why="neither 0 nor 1"))
cell("R8_rc255_ssh_dropped_FAILED", lambda: expect("FAILED", 255, man(td(), BAD), why="neither 0 nor 1"))
cell("R9_unparseable_manifest_FAILED", lambda: expect("FAILED", 0, man(td(), raw='{"month": "2026-09", "fil'), why="unreadable"))
cell("R10_manifest_for_another_month_FAILED", lambda: expect("FAILED", 0, man(td()), month="2026-08", why="is not '2026-08'"))
cell("R11_files_count_ne_n_symbols_FAILED", lambda: expect("FAILED", 0, man(td(), n_symbols=5), why="empty or partial"))
cell("R12_empty_symbol_list_FAILED", lambda: expect("FAILED", 0, man(td(), files={}), why="empty or partial"))
cell("R13_intended_rc_absent_FAILED", lambda: expect("FAILED", 0, man(td(), intended="absent"), why="<absent>"))
cell("R14_rc_not_an_integer_FAILED", lambda: expect("FAILED", "", man(td()), why="not an integer"))
cell("R15_rc0_manifest_path_is_directory_FAILED", lambda: expect("FAILED", 0, (lambda d: (os.makedirs(os.path.join(d, "MANIFEST_%s.json" % M)),
                                                                                       os.path.join(d, "MANIFEST_%s.json" % M))[1])(td()), why="no manifest file"))

def cli_anchored():
    """The driver greps ^P9_VERDICT (OK|MISMATCH|FAILED); the CLI must print exactly one such line, and must print FAILED (not
    nothing) when its own arguments are wrong, so the driver's default branch is never the only thing standing between a crash and
    a deletion."""
    import subprocess
    p = subprocess.run([sys.executable, "-B", os.path.join(HERE, "p9_pull_verdict.py"), "1", man(td(), BAD), N, M],
                       capture_output=True, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith("P9_VERDICT ")]
    assert len(lines) == 1 and lines[0].startswith("P9_VERDICT MISMATCH "), p.stdout
    q = subprocess.run([sys.executable, "-B", os.path.join(HERE, "p9_pull_verdict.py"), "1"], capture_output=True, text=True)
    ql = [l for l in q.stdout.splitlines() if l.startswith("P9_VERDICT ")]
    assert len(ql) == 1 and ql[0].startswith("P9_VERDICT FAILED "), q.stdout
cell("C1_cli_one_anchored_line_and_FAILED_on_bad_args", cli_anchored)


def main():
    ok = all(r[1] for r in RES)
    for n, p, m in RES:
        print("  [%s] %s %s" % ("PASS" if p else "FAIL", n, m))
    print("P9_VERDICT_TESTS %d/%d %s" % (sum(r[1] for r in RES), len(RES), "ALL_PASS" if ok else "RED"))
    if len(sys.argv) > 1:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "common"))
        import durable_write as DW
        body = json.dumps({"device": os.path.join(HERE, "p9_pull_verdict.py"),
                           "device_sha256": hashlib.sha256(open(os.path.join(HERE, "p9_pull_verdict.py"), "rb").read()).hexdigest(),
                           "tests_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                           "python": sys.version.split()[0], "cells": [{"name": n, "pass": p, "msg": m} for n, p, m in RES],
                           "ALL_PASS": ok}, indent=1).encode()
        print("receipt_sha256", DW.write_bytes(sys.argv[1], body))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
