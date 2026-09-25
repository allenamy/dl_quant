#!/usr/bin/env python3
"""Rehearsal test of the files-only installer (nc_install_files.py) and packager (nc_package_files.py) on a COPY of the machine layout.
The real ~/wide_shadow is only READ (rsync into the fixture, minus venv / state/snap / logs); ~/Library/LaunchAgents/com.hsy.sidecar.plist is
only READ (copied into the fixture). Fixture copies per cell are APFS clones (cp -c), so each cell starts from the same bytes.
Red controls required by the lead (2026-09-25): any state touch in files-only mode is red; after the archive moves the source is gone and the
archived sha equals the pre-move sha; after rollback every file is bit-for-bit back at its pre-release bytes.
  F0 preflight PASS on the fixture (baseline green first)
  F1 apply: every dest == candidate; every archive source gone, archived sha == pre-move sha; state manifest diff empty; producer loads
  F2 RED: a contract carrying a dest under wide_shadow/state/ is refused at preflight
  F3 RED: a mutant that touches ONE state file (utime) during apply ⇒ apply refused with FILES-ONLY VIOLATION
  F4 RED: an archive source changed after packaging ⇒ refused at preflight
  F5 rollback after F1: every dest back to its baseline sha (None = removed), every archive source back at its pre-move sha, archive dst gone
  F6 RED: a mutant rollback that forgets the archive ⇒ refused ("archive move not reversed")
  F7 RED: --no-launchctl on the REAL home ⇒ refused before anything
usage: ~/wide_shadow/venv/bin/python test_nc_install_files.py <derived tree> <work dir>
"""
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~")
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(name):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py")); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main():
    tree, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    assert not os.path.exists(work), f"refusing to reuse {work}"
    os.makedirs(work)
    base = f"{work}/fixture_base"
    os.makedirs(f"{base}/Library/LaunchAgents"); os.makedirs(f"{base}/dl_quant_live/state")
    r = subprocess.run(["rsync", "-a", "--exclude", "venv", "--exclude", "state/snap", "--exclude", "__pycache__", "--exclude", "loop.out*",
                        "--exclude", "shadow_log.jsonl", "--exclude", ".env*", "--exclude", "*.log", f"{HOME}/wide_shadow/", f"{base}/wide_shadow/"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:300]
    shutil.copy2(f"{HOME}/Library/LaunchAgents/com.hsy.sidecar.plist", f"{base}/Library/LaunchAgents/com.hsy.sidecar.plist")
    open(f"{base}/dl_quant_live/state/anchor.lock", "w").close()
    def clone(tag):
        d = f"{work}/{tag}"; r = subprocess.run(["cp", "-cR", base, d], capture_output=True, text=True); assert r.returncode == 0, r.stderr[:200]; return d
    pkg = f"{work}/pkg"
    r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "nc_package_files.py"), tree, pkg, "--label", "rehearsal", "--home", base], capture_output=True, text=True)
    print(r.stdout[-600:], r.stderr[-300:]); assert r.returncode == 0
    C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
    IF = load("nc_install_files"); IF.NI.IGNORE_WINDOW = True
    pre_dest = {it["dest"]: it["baseline_sha256"] for it in C["files"]}
    pre_src = {mv["src"]: mv["expected_sha256"] for mv in C["archive_moves"]}
    print("F0 / F1 / F5")
    h1 = clone("h1")
    try:
        _, rep = IF.preflight(pkg, h1); ok = rep["package"] == "PASS"
    except IF.Refused as e:
        ok, rep = False, str(e)
    check("F0 baseline green: preflight PASS on the fixture", ok, rep if not ok else f"{len(C['files'])} files, {len(C['archive_moves'])} archive moves")
    rec = IF.apply(pkg, f"{work}/bk1", h1, 20, True)
    check("F1 apply reached installed_not_started", rec["stage"] == "installed_not_started")
    check("F1 every dest == candidate", all(sha(f"{h1}/{it['dest']}") == it["candidate_sha256"] for it in C["files"]))
    check("F1 archive: every source gone AND the archived sha == the pre-move sha",
          all(not os.path.exists(f"{h1}/{mv['src']}") and sha(f"{h1}/{mv['dst']}") == pre_src[mv["src"]] for mv in C["archive_moves"]))
    check("F1 files-only: the state manifest is unchanged (diff empty)", rec.get("state_manifest_diff") == [], rec.get("state_manifest_diff"))
    check("F1 the installed producer loads the state", bool(rec.get("producer_load", {}).get("module_sha256")), rec.get("producer_load"))
    rb = IF.rollback(pkg, f"{work}/bk1", h1, 20, True)
    check("F5 rollback reached rolled_back_not_started", rb["stage"] == "rolled_back_not_started")
    check("F5 every dest bit-for-bit back at its pre-release bytes (None = removed)",
          all((sha(f"{h1}/{d}") if os.path.exists(f"{h1}/{d}") else None) == s for d, s in pre_dest.items()))
    check("F5 every archive source back at its pre-move sha, archive destinations gone",
          all(os.path.isfile(f"{h1}/{s}") and sha(f"{h1}/{s}") == x for s, x in pre_src.items()) and all(not os.path.exists(f"{h1}/{mv['dst']}") for mv in C["archive_moves"]))
    check("F5 rollback touched no state file", rb.get("state_manifest_diff") == [], rb.get("state_manifest_diff"))
    print("F2 forbidden dest")
    pkg2 = f"{work}/pkg_bad_state"; shutil.copytree(pkg, pkg2)
    C2 = copy.deepcopy(C); os.makedirs(f"{pkg2}/files/wide_shadow/state", exist_ok=True)
    open(f"{pkg2}/files/wide_shadow/state/aux.json", "w").write("{}")
    C2["files"].append({"dest": "wide_shadow/state/aux.json", "candidate_sha256": sha(f"{pkg2}/files/wide_shadow/state/aux.json"),
                        "baseline_sha256": sha(f"{h1}/wide_shadow/state/aux.json")})
    with open(f"{pkg2}/INSTALL_CONTRACT.json", "w") as f: json.dump(C2, f, indent=1)
    try:
        IF.preflight(pkg2, h1); refused = None
    except IF.Refused as e:
        refused = str(e)
    check("F2 RED: a contract writing wide_shadow/state/ is refused at preflight", refused is not None and "may not write state" in refused, refused)
    print("F3 state touched during apply")
    h3 = clone("h3")
    def touch(home): os.utime(f"{home}/wide_shadow/state/aux.json", None)
    try:
        IF.apply(pkg, f"{work}/bk3", h3, 20, True, _hook=touch); refused = None
    except IF.Refused as e:
        refused = str(e)
    check("F3 RED: one state file touched during apply ⇒ refused with FILES-ONLY VIOLATION", refused is not None and "FILES-ONLY VIOLATION" in refused, refused)
    print("F4 archive source changed")
    h4 = clone("h4"); open(f"{h4}/wide_shadow/fea171/sidecar_blend.py", "a").write("\n# changed\n")
    try:
        IF.preflight(pkg, h4); refused = None
    except IF.Refused as e:
        refused = str(e)
    check("F4 RED: an archive source changed after packaging ⇒ refused", refused is not None and "archive source" in refused, refused)
    print("F6 mutant rollback without unarchive")
    h6 = clone("h6"); IF.apply(pkg, f"{work}/bk6", h6, 20, True)
    try:
        IF.rollback(pkg, f"{work}/bk6", h6, 20, True, _skip_unarchive=True); refused = None
    except IF.Refused as e:
        refused = str(e)
    check("F6 RED: a rollback that forgets the archive is refused", refused is not None and "archive move not reversed" in refused, refused)
    print("F7 rehearsal flags on the real home")
    r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "nc_install_files.py"), "preflight", pkg, "--no-launchctl"], capture_output=True, text=True)
    check("F7 RED: --no-launchctl on the real home is refused before anything", r.returncode == 3 and "rehearsal-only" in r.stdout, r.stdout[-200:])
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    print("TEST_NC_INSTALL_FILES", "PASS" if not FAILS else "FAIL", FAILS if FAILS else "")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
