#!/usr/bin/env python3
"""Release / rollback ORDER rehearsal for the vendored upstream (E-0925-D; lead review of DEPLOY_v2_durable §3, 2026-09-25). Read-only on
production and on the research repo's working tree: the two upstream states are STAGED copies extracted from git objects, and each
executor's drift guard is run from its own checkout (a temporary git worktree of the candidate clone) against a staged copy.
  O1 old executor (5d3029c) guard vs UNPATCHED upstream  → green   (today)
  O2 old executor guard vs PATCHED upstream              → RED     (rollback in the wrong order: executor rolled back while the upstream is
                                                                    still patched ⇒ its own safe_commit battery is blocked by drift_gate)
  N1 new executor (candidate) guard vs PATCHED upstream  → green   (forward in the right order: upstream first, then executor)
  N2 new executor guard vs UNPATCHED upstream            → RED     (forward in the wrong order: executor before the upstream)
PASS iff all four hold ⇒ the only order in which every step's own battery is green: forward = upstream then executor; rollback = upstream
revert then executor (the mirror).
usage: python3 test_release_order_drift.py <candidate clone> <old sha> <new sha> <patch commit> <research repo> <out json>"""
import json, os, shutil, subprocess, sys, tempfile

FILES = ["regime_classifier.py", "deliver_report.py", "production_state_guard.py", "factor_version_registry.py", "pilot_metrics.py", "durable_io.py"]
RUN_OLD = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('g', sys.argv[1]); m = importlib.util.module_from_spec(s); "
           "s.loader.exec_module(m); m.UPSTREAM = sys.argv[2]; sys.exit(m.main())")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)


def main():
    clone, old, new, patch, rrepo, outp = sys.argv[1:7]
    tmp = tempfile.mkdtemp(prefix="release_order_")
    up_p, up_u = f"{tmp}/upstream_patched", f"{tmp}/upstream_unpatched"
    os.makedirs(up_p); os.makedirs(up_u)
    for f in FILES:
        r = git(rrepo, "show", f"{patch}:multi_asset/engine/live/{f}")
        assert r.returncode == 0, (f, r.stderr[:200]); open(f"{up_p}/{f}", "w").write(r.stdout)
        r = git(rrepo, "show", f"{patch}~1:multi_asset/engine/live/{f}")
        if r.returncode == 0: open(f"{up_u}/{f}", "w").write(r.stdout)      # durable_io.py did not exist before the patch
    wt_old = f"{tmp}/wt_old"
    r = git(clone, "worktree", "add", "--detach", wt_old, old); assert r.returncode == 0, r.stderr[:200]
    wt_new = f"{tmp}/wt_new"
    r = git(clone, "worktree", "add", "--detach", wt_new, new); assert r.returncode == 0, r.stderr[:200]
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~")}
    def old_guard(up):
        r = subprocess.run(["/usr/bin/python3", "-c", RUN_OLD, f"{wt_old}/ops/check_upstream_drift.py", up], capture_output=True, text=True, env=env, timeout=120)
        return r.returncode, (r.stdout.strip().splitlines() or [""])[0][:160]
    def new_guard(up):
        r = subprocess.run(["/usr/bin/python3", f"{wt_new}/ops/check_upstream_drift.py", "--upstream", up], capture_output=True, text=True, env=env, timeout=120)
        return r.returncode, (r.stdout.strip().splitlines() or [""])[0][:160]
    cells = {"O1_old_vs_unpatched_green": (old_guard(up_u), 0), "O2_old_vs_patched_RED": (old_guard(up_p), 1),
             "N1_new_vs_patched_green": (new_guard(up_p), 0), "N2_new_vs_unpatched_RED": (new_guard(up_u), 1)}
    rec = {"device": os.path.abspath(__file__), "old": old, "new": new, "patch": patch,
           "cells": {k: {"rc": v[0][0], "first_line": v[0][1], "expected_rc": v[1], "ok": v[0][0] == v[1]} for k, v in cells.items()}}
    rec["VERDICT"] = "PASS" if all(c["ok"] for c in rec["cells"].values()) else "FAIL"
    for wt in (wt_old, wt_new): git(clone, "worktree", "remove", "--force", wt)
    shutil.rmtree(tmp, ignore_errors=True)
    with open(outp, "w") as f: json.dump(rec, f, indent=1)
    for k, c in rec["cells"].items(): print(f"  {'OK  ' if c['ok'] else 'FAIL'} {k}: rc={c['rc']} (expected {c['expected_rc']}) {c['first_line']}")
    print("RELEASE_ORDER_DRIFT", rec["VERDICT"], flush=True)
    return 0 if rec["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
