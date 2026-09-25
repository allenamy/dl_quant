#!/usr/bin/env python3
"""nc_install_files.py — the installer's FILES-ONLY mode (lead ruling 2026-09-25: "nc_install --files-only"; a sibling of nc_install.py that
imports its helpers — the NC state-seeding paths of nc_install.py are not touched). Contract: nc_package_files.py (nc_files_contract_v1).
  preflight <pkg>              read-only: package bytes = contract; no dest under a forbidden prefix (wide_shadow/state/); every dest still at its
                               baseline and not a symlink; every archive source at its expected sha, its destination absent; the unchanged set
                               unchanged.
  apply <pkg> <backup dir>     quiet window (>= --reserve min left); producer-side services not running, the not_loaded labels not loaded; the
                               executor anchor.lock held; a MANIFEST of the whole state tree (every file under wide_shadow/state: size + mtime_ns,
                               plus sha of the top-level state files) taken; backup of every dest and archive source; files installed atomically
                               (tmp + fsync + os.replace, read back == contract); archive moves (os.rename, the source gone, sha(dst) == expected);
                               the INSTALLED producer loads the state; the state MANIFEST re-taken and REQUIRED EQUAL (any state touch = refused).
  rollback <pkg> <backup dir>  quiet window, services, lock; every dest back to its baseline bytes (new files moved aside); every archive move
                               reversed (sha checked); the RESTORED producer loads the state; the state MANIFEST again required unchanged; every
                               dest / archive source verified at its pre-release sha.
--home H runs against a copy of the machine layout (rehearsal); --no-launchctl / --ignore-window are rehearsal-only (refused on the real home).
Every receipt is written with an explicitly closed handle (E-0925-A family).
usage: ~/wide_shadow/venv/bin/python nc_install_files.py {preflight|apply|rollback} <pkg> [<backup dir>] [--home H] [--reserve 20]
       [--no-launchctl] [--ignore-window]"""
import argparse, importlib.util, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("nc_install_base", os.path.join(HERE, "nc_install.py"))
NI = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(NI)
check, sha, utc, Refused = NI.check, NI.sha, NI.utc, NI.Refused


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=str)


def not_loaded(labels, skip):
    if skip: return {"skipped": True}
    out = {}
    for lb in labels:
        r = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{lb}"], capture_output=True, text=True, timeout=30)
        out[lb] = {"loaded": r.returncode == 0}
        check(r.returncode != 0, f"service must not be loaded: {lb}")
    return out


def state_manifest(home):
    """every file under wide_shadow/state: (size, mtime_ns); plus sha256 of the top-level state files. A files-only install must leave it EQUAL."""
    root = f"{home}/wide_shadow/state"; m = {}
    for dp, dn, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except FileNotFoundError:
                continue
            rel = os.path.relpath(p, root)
            m[rel] = [st.st_size, st.st_mtime_ns] + ([sha(p)] if dp == root and os.path.isfile(p) else [])
    return m


def preflight(pkg, home):
    C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json")); rep = {"contract_sha256": sha(f"{pkg}/INSTALL_CONTRACT.json"), "files": len(C["files"]),
                                                               "archive_moves": len(C.get("archive_moves", []))}
    check(C.get("schema") == "nc_files_contract_v1", f"not a files-only contract: {C.get('schema')}")
    for it in C["files"]:
        check(not any(it["dest"].startswith(p) for p in C.get("forbidden_dest_prefixes", []) + ["wide_shadow/state/"]),
              f"a files-only contract may not write state: {it['dest']}")
        check(sha(f"{pkg}/files/{it['dest']}") == it["candidate_sha256"], f"package file differs from contract: {it['dest']}")
        cur = f"{home}/{it['dest']}"; now = sha(cur) if os.path.exists(cur) else None
        check(now == it["baseline_sha256"], f"destination not at its baseline: {it['dest']} {now} != {it['baseline_sha256']}")
        check(not os.path.islink(cur), f"destination is a symlink: {it['dest']}")
    for mv in C.get("archive_moves", []):
        s, d = f"{home}/{mv['src']}", f"{home}/{mv['dst']}"
        check(os.path.isfile(s) and not os.path.islink(s) and sha(s) == mv["expected_sha256"], f"archive source missing or changed: {mv['src']}")
        check(not os.path.exists(d), f"archive destination already exists: {mv['dst']}")
    for u, s_ in C["unchanged"].items():
        check(os.path.exists(f"{home}/{u}") and sha(f"{home}/{u}") == s_, f"a file the release keeps has changed: {u}")
    rep["package"] = "PASS"
    return C, rep


def apply(pkg, bk, home, reserve, skip_lc, _hook=None):
    check(not os.path.exists(bk), "backup dir exists"); NI.quiet(reserve)
    C, rep = preflight(pkg, home)
    rep["services_stopped"] = NI.services_idle(C["services"]["stop"], skip_lc)
    rep["services_not_loaded"] = not_loaded(C["services"].get("not_loaded", []), skip_lc)
    lock = NI.take_lock(home); NI.quiet(reserve // 2)
    rec = {"verb": "apply", "schema": C["schema"], "label": C["label"], "started_utc": utc(), "home": home, "preflight": rep, "no_launchctl": skip_lc,
           "ignore_window": NI.IGNORE_WINDOW, "release_basis": C.get("release_basis"), "stage": "backup"}
    os.makedirs(f"{bk}/files")
    wr = lambda: write_json(f"{bk}/NC_FILES_INSTALL_RECEIPT.json", rec)
    wr()
    before = state_manifest(home); rec["state_manifest_before_n"] = len(before)
    write_json(f"{bk}/STATE_MANIFEST_before.json", before)
    sums = []
    for rel in [it["dest"] for it in C["files"]] + [mv["src"] for mv in C.get("archive_moves", [])]:
        cur = f"{home}/{rel}"
        if os.path.exists(cur):
            b = f"{bk}/files/{rel}"; os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(cur, b); sums.append((sha(b), f"files/{rel}"))
    with open(f"{bk}/SHA256SUMS", "w") as f:
        f.write("".join(f"{s}  {p}\n" for s, p in sums))
    rec["backup"] = {"entries": len(sums), "sha256sums": sha(f"{bk}/SHA256SUMS")}; rec["stage"] = "installing_files"; wr()
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"; os.makedirs(os.path.dirname(cur), exist_ok=True)
        mode = (os.stat(cur).st_mode & 0o777) if os.path.exists(cur) else (os.stat(f"{pkg}/files/{it['dest']}").st_mode & 0o777)
        NI.atomic_copy(f"{pkg}/files/{it['dest']}", cur, mode)
        check(sha(cur) == it["candidate_sha256"], f"installed bytes differ: {it['dest']}")
    rec["stage"] = "archiving"; wr(); rec["archived"] = {}
    for mv in C.get("archive_moves", []):
        s, d = f"{home}/{mv['src']}", f"{home}/{mv['dst']}"
        check(sha(s) == mv["expected_sha256"], f"archive source changed since preflight: {mv['src']}")
        os.makedirs(os.path.dirname(d), exist_ok=True); os.rename(s, d)
        check(not os.path.exists(s) and sha(d) == mv["expected_sha256"], f"archive move not verified: {mv['src']} -> {mv['dst']}")
        rec["archived"][mv["src"]] = {"dst": mv["dst"], "sha256": sha(d)}
    rec["stage"] = "verifying"; wr()
    if _hook: _hook(home)                          # test-only: a mutant that touches state here must be caught below
    rec["producer_load"] = NI.producer_loads(home, "files_apply")
    after = state_manifest(home); write_json(f"{bk}/STATE_MANIFEST_after.json", after)
    diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    rec["state_manifest_diff"] = diff[:50]
    check(not diff, f"FILES-ONLY VIOLATION: {len(diff)} state file(s) touched during the install: {diff[:8]}")
    for u, s_ in C["unchanged"].items(): check(sha(f"{home}/{u}") == s_, f"a kept file changed during install: {u}")
    rec["installed"] = {it["dest"]: sha(f"{home}/{it['dest']}") for it in C["files"]}
    rec["stage"] = "installed_not_started"; rec["completed_utc"] = utc(); wr()
    lock.close()
    return rec


def rollback(pkg, bk, home, reserve, skip_lc, _skip_unarchive=False):
    NI.quiet(reserve); C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
    check(os.path.isfile(f"{bk}/NC_FILES_INSTALL_RECEIPT.json") and os.path.isfile(f"{bk}/SHA256SUMS"), "no files-only install backup at this path")
    for line in open(f"{bk}/SHA256SUMS"):
        s, p = line.rstrip("\n").split("  ", 1); check(sha(f"{bk}/{p}") == s, f"backup corrupted: {p}")
    rec = {"verb": "rollback", "schema": C["schema"], "label": C["label"], "started_utc": utc(), "home": home, "no_launchctl": skip_lc,
           "services_stopped": NI.services_idle(C["services"]["stop"], skip_lc)}
    lock = NI.take_lock(home); aside = f"{bk}/rollback_moved_aside_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"; os.makedirs(aside)
    wr = lambda: write_json(f"{aside}/NC_FILES_ROLLBACK_RECEIPT.json", rec)
    before = state_manifest(home)
    rec["stage"] = "restoring_files"; wr()
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"
        if it["baseline_sha256"] is None:
            if os.path.exists(cur):
                m = f"{aside}/files/{it['dest']}"; os.makedirs(os.path.dirname(m), exist_ok=True); shutil.move(cur, m)
        else:
            b = f"{bk}/files/{it['dest']}"; check(sha(b) == it["baseline_sha256"], f"backup is not the baseline: {it['dest']}")
            NI.atomic_copy(b, cur, os.stat(cur).st_mode & 0o777 if os.path.exists(cur) else 0o644)
            check(sha(cur) == it["baseline_sha256"], f"restored bytes differ: {it['dest']}")
    rec["stage"] = "unarchiving"; wr()
    if not _skip_unarchive:                      # test-only switch: a mutant rollback that forgets the archive must be caught below
        for mv in C.get("archive_moves", []):
            s, d = f"{home}/{mv['src']}", f"{home}/{mv['dst']}"
            if os.path.exists(d) and not os.path.exists(s):
                check(sha(d) == mv["expected_sha256"], f"archived copy changed: {mv['dst']}")
                os.makedirs(os.path.dirname(s), exist_ok=True); os.rename(d, s)
    rec["stage"] = "verifying"; wr()
    for it in C["files"]:
        cur = f"{home}/{it['dest']}"
        check((sha(cur) if os.path.exists(cur) else None) == it["baseline_sha256"], f"after rollback not at baseline: {it['dest']}")
    for mv in C.get("archive_moves", []):
        s, d = f"{home}/{mv['src']}", f"{home}/{mv['dst']}"
        check(os.path.isfile(s) and sha(s) == mv["expected_sha256"] and not os.path.exists(d), f"archive move not reversed: {mv['src']}")
    rec["producer_load"] = NI.producer_loads(home, "files_rollback")
    after = state_manifest(home)
    diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    rec["state_manifest_diff"] = diff[:50]
    check(not diff, f"FILES-ONLY VIOLATION during rollback: {len(diff)} state file(s) touched: {diff[:8]}")
    rec["stage"] = "rolled_back_not_started"; rec["completed_utc"] = utc(); wr()
    lock.close()
    return rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("verb", choices=["preflight", "apply", "rollback"]); ap.add_argument("pkg"); ap.add_argument("bk", nargs="?")
    ap.add_argument("--home", default=os.path.expanduser("~")); ap.add_argument("--reserve", type=int, default=20)
    ap.add_argument("--no-launchctl", action="store_true"); ap.add_argument("--ignore-window", action="store_true")
    a = ap.parse_args()
    if (a.no_launchctl or a.ignore_window) and os.path.realpath(a.home) == os.path.realpath(os.path.expanduser("~")):
        print("NC_INSTALL_FILES REFUSED: --no-launchctl / --ignore-window are rehearsal-only (need --home other than the real home)"); return 3
    NI.IGNORE_WINDOW = a.ignore_window
    try:
        if a.verb == "preflight":
            _, rep = preflight(a.pkg, a.home); print("NC_INSTALL_FILES PREFLIGHT_PASS", json.dumps(rep, default=str)[:1500]); return 0
        check(a.bk, f"{a.verb} needs <backup dir>")
        rec = apply(a.pkg, a.bk, a.home, a.reserve, a.no_launchctl) if a.verb == "apply" else rollback(a.pkg, a.bk, a.home, a.reserve, a.no_launchctl)
        print("NC_INSTALL_FILES", rec["stage"], json.dumps(rec.get("producer_load")), flush=True); return 0
    except Refused as e:
        print("NC_INSTALL_FILES REFUSED:", e, flush=True); return 3


if __name__ == "__main__":
    sys.exit(main())
