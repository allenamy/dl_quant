#!/usr/bin/env python3
"""Rehearsal of the gap-class-fix files-only release on a COPY of the machine layout (derived from nc_2026-09-23 test_nc_install_files.py;
the installer is the UNCHANGED nc_install_files.py). The real ~/wide_shadow is only READ (rsync into the fixture minus venv / state/snap / logs).
  F0 preflight PASS on the fixture (baseline green first)
  F1 apply: every dest == candidate; state manifest diff empty; the installed producer loads the state; the INSTALLED tests_prev_state.py passes
  F2 RED: a contract carrying a dest under wide_shadow/state/ is refused at preflight
  F3 RED: a mutant that touches ONE state file during apply => refused with FILES-ONLY VIOLATION
  F5 rollback after F1: combo_stage back at 12a76de8, the three new files removed, no state touched
  F8 RED: combo_stage.py changed after packaging (not at its baseline) => refused at preflight
  F9 RED: a pinned unchanged file (nc_contract.py) changed after packaging => refused at preflight
usage: ~/wide_shadow/venv/bin/python test_gap_install_files.py <tree> <work dir>"""
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~")
NCDEV = os.path.join(HERE, "..", "..", "nc_2026-09-23", "devices")
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def main():
    tree, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    assert not os.path.exists(work), f"refusing to reuse {work}"; os.makedirs(work)
    base = f"{work}/fixture_base"; os.makedirs(f"{base}/dl_quant_live/state")
    r = subprocess.run(["rsync", "-a", "--exclude", "venv", "--exclude", "state/snap", "--exclude", "__pycache__", "--exclude", "loop.out*",
                        "--exclude", "shadow_log.jsonl", "--exclude", ".env*", "--exclude", "*.log", f"{HOME}/wide_shadow/", f"{base}/wide_shadow/"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:300]
    open(f"{base}/dl_quant_live/state/anchor.lock", "w").close()
    def clone(tag):
        d = f"{work}/{tag}"; r = subprocess.run(["cp", "-cR", base, d], capture_output=True, text=True); assert r.returncode == 0, r.stderr[:200]; return d
    pkg = f"{work}/pkg"
    r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "gap_package_files.py"), tree, pkg, "--label", "rehearsal", "--home", base], capture_output=True, text=True)
    print(r.stdout[-700:], r.stderr[-300:]); assert r.returncode == 0
    C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
    s = importlib.util.spec_from_file_location("nc_install_files", os.path.join(NCDEV, "nc_install_files.py")); IF = importlib.util.module_from_spec(s); s.loader.exec_module(IF)
    IF.NI.IGNORE_WINDOW = True
    pre_dest = {it["dest"]: it["baseline_sha256"] for it in C["files"]}
    h1 = clone("h1")
    try:
        _, rep = IF.preflight(pkg, h1); ok = rep["package"] == "PASS"
    except IF.Refused as e:
        ok, rep = False, str(e)
    check("F0 baseline green: preflight PASS on the fixture", ok, rep if not ok else f"{len(C['files'])} files, {len(C['unchanged'])} pinned unchanged")
    rec = IF.apply(pkg, f"{work}/bk1", h1, 20, True)
    check("F1 apply reached installed_not_started", rec["stage"] == "installed_not_started")
    check("F1 every dest == candidate", all(sha(f"{h1}/{it['dest']}") == it["candidate_sha256"] for it in C["files"]))
    check("F1 files-only: the state manifest is unchanged (diff empty)", rec.get("state_manifest_diff") == [], rec.get("state_manifest_diff"))
    check("F1 the installed producer loads the state", bool(rec.get("producer_load", {}).get("module_sha256")), rec.get("producer_load"))
    r = subprocess.run([sys.executable, "-B", f"{h1}/wide_shadow/fea171/tests_prev_state.py"], capture_output=True, text=True)
    check("F1 the INSTALLED tests_prev_state.py passes (and the old predicate is red)", r.returncode == 0 and "PREV_STATE_TESTS PASS" in r.stdout, r.stdout[-200:])
    rb = IF.rollback(pkg, f"{work}/bk1", h1, 20, True)
    check("F5 rollback reached rolled_back_not_started", rb["stage"] == "rolled_back_not_started")
    check("F5 every dest back at its pre-release bytes (None = removed)", all((sha(f"{h1}/{d}") if os.path.exists(f"{h1}/{d}") else None) == x for d, x in pre_dest.items()))
    check("F5 rollback touched no state file", rb.get("state_manifest_diff") == [], rb.get("state_manifest_diff"))
    pkg2 = f"{work}/pkg_bad_state"; shutil.copytree(pkg, pkg2); C2 = copy.deepcopy(C); os.makedirs(f"{pkg2}/files/wide_shadow/state", exist_ok=True)
    open(f"{pkg2}/files/wide_shadow/state/aux.json", "w").write("{}")
    C2["files"].append({"dest": "wide_shadow/state/aux.json", "candidate_sha256": sha(f"{pkg2}/files/wide_shadow/state/aux.json"), "baseline_sha256": sha(f"{h1}/wide_shadow/state/aux.json")})
    with open(f"{pkg2}/INSTALL_CONTRACT.json", "w") as f: json.dump(C2, f, indent=1)
    try: IF.preflight(pkg2, h1); refused = None
    except IF.Refused as e: refused = str(e)
    check("F2 RED: a contract writing wide_shadow/state/ is refused at preflight", refused is not None and "may not write state" in refused, refused)
    h3 = clone("h3")
    try: IF.apply(pkg, f"{work}/bk3", h3, 20, True, _hook=lambda home: os.utime(f"{home}/wide_shadow/state/aux.json", None)); refused = None
    except IF.Refused as e: refused = str(e)
    check("F3 RED: one state file touched during apply => FILES-ONLY VIOLATION", refused is not None and "FILES-ONLY VIOLATION" in refused, refused)
    h8 = clone("h8"); open(f"{h8}/wide_shadow/fea171/combo_stage.py", "a").write("\n# drift\n")
    try: IF.preflight(pkg, h8); refused = None
    except IF.Refused as e: refused = str(e)
    check("F8 RED: combo_stage changed after packaging => refused", refused is not None and "baseline" in refused, refused)
    h9 = clone("h9"); open(f"{h9}/wide_shadow/fea171/nc_contract.py", "a").write("\n# drift\n")
    try: IF.preflight(pkg, h9); refused = None
    except IF.Refused as e: refused = str(e)
    check("F9 RED: a pinned unchanged import changed => refused", refused is not None and "keeps has changed" in refused, refused)
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed"); print("TEST_GAP_INSTALL_FILES", "PASS" if not FAILS else "FAIL", FAILS if FAILS else "")
    return 0 if not FAILS else 1
if __name__ == "__main__":
    sys.exit(main())
