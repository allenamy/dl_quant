#!/usr/bin/env python3
"""Version measurements for the gap-class-fix release (DEPLOY_gap_classfix_2026-09-26). Derived from nc_2026-09-23 v2c_version_probe.py
(e8e535dfb6 lineage) with the pin updated: the executor tree this release starts from is d01e35d (fix-pkg-d), so after-w3 compares
config/book.json with d01e35d (the release changes no book configuration). after-w4 / after-w5 read the package contract (unchanged logic).
New step first-anchor <pkg> <A>: combo_live_status anchor == A and ok; the combo_stage.py at the daemon's run path == candidate; the
anchor's combo_live.log block printed with its STATE_LOOKUP / MH_RECOMPUTED / GAP_PAGE lines (none expected on a no-gap anchor);
target_combo/<A>.json kc/fc sources. READ-ONLY; every line prints MEASURED next to COMPARED; exit 3 on any mismatch.
usage: /usr/bin/python3 gap_version_probe.py <after-w3 NEWSHA pathspec...|after-w4 pkg receipt|after-w5 pkg receipt|first-anchor pkg A [--expect-mh t1,t2,..]> [--out F]
rev 1 (2026-09-27, arm64 host, before any window): after-w5 pins from candidates ∪ unchanged (rev 0 KeyError), sidecar 'cannot be started' also when
no plist exists; first-anchor --expect-mh checks W6 (b) mechanically (was a manual read of the log)."""
import datetime, hashlib, json, os, re, subprocess, sys

HOME = os.path.expanduser("~"); DQ = f"{HOME}/dl_quant_live"; WS = f"{HOME}/wide_shadow"; OLD_EXEC = "d01e35db56b4d7ed6abf0befd9f18452cd06c329"   # d01e35d fix-pkg-d (pin updated for this release)
LINES, BAD = [], []
EXPECT_MH = None
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def say(s): LINES.append(s); print(s, flush=True)
def cmp_(name, measured, want):
    ok = measured == want
    say(f"  {'OK ' if ok else 'BAD'} {name}: measured={measured} compared_with={want}")
    if not ok: BAD.append(name)
def sh(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw); return r.returncode, r.stdout.strip()


def after_w3(newsha, pathspec):
    _, head = sh(["git", "-C", DQ, "rev-parse", "HEAD"]); _, om = sh(["git", "-C", DQ, "rev-parse", "origin/main"])
    _, lr = sh(["git", "ls-remote", "https://github.com/allenamy/dl_quant_live.git", "refs/heads/main"]); gh = lr.split()[0] if lr else None
    say(f"after-w3 HEAD={head} origin/main={om} github={gh} NEWSHA={newsha}")
    cmp_("running tree HEAD == NEWSHA", head, newsha); cmp_("local origin/main == NEWSHA", om, newsha); cmp_("GitHub main == NEWSHA", gh, newsha)
    _, files = sh(["git", "-C", DQ, "show", "--name-only", "--format=", newsha])
    cmp_("NEWSHA commit files == pathspec", sorted(files.split()), sorted(pathspec))
    st = subprocess.run(["git", "-C", DQ, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout   # NOT stripped:
    # porcelain lines start with a status column that may be a space (" M path"); sh() strips, which shifted the first line (control run 1)
    dirty = [l for l in st.splitlines() if not l[3:].startswith(("state/", "logs/"))]
    cmp_("running tree code area clean", dirty, [])
    v = re.search(r'^VERSION = "([^"]+)"', open(f"{DQ}/live/beta_overlay.py").read(), re.M)
    cmp_("live/beta_overlay.py VERSION", v.group(1) if v else None, "m3_beta_v2")
    _, old_book = sh(["git", "-C", DQ, "show", f"{OLD_EXEC}:config/book.json"])
    cmp_("config/book.json bytes == d01e35d (no book change)", open(f"{DQ}/config/book.json").read().strip() == old_book, True)
    rc, out = sh(["/usr/bin/python3", f"{DQ}/ops/check_upstream_drift.py"], cwd=DQ, timeout=180)
    say(f"  VAL drift guard rc={rc} first line: {(out.splitlines() or [''])[0][:160]}")
    cmp_("running tree drift guard green across 6", rc == 0 and "no drift across 6" in out, True)


def contract(pkg): return json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))


def after_w4(pkg, receipt):
    C = contract(pkg); R = json.load(open(receipt))
    say(f"after-w4 receipt stage={R.get('stage')} completed_utc={R.get('completed_utc')} state_manifest_diff={R.get('state_manifest_diff')}")
    cmp_("receipt stage", R.get("stage"), "installed_not_started"); cmp_("state_manifest_diff", R.get("state_manifest_diff"), [])
    for it in C["files"]:
        p = f"{HOME}/{it['dest']}"; cmp_(f"dest {it['dest']}", sha(p) if os.path.exists(p) else None, it["candidate_sha256"])
    for mv in C.get("archive_moves", []):
        cmp_(f"archive src gone {mv['src']}", os.path.exists(f"{HOME}/{mv['src']}"), False)
        d = f"{HOME}/{mv['dst']}"; cmp_(f"archive dst {mv['dst']}", sha(d) if os.path.exists(d) else None, mv["expected_sha256"])


def proc(label):
    _, out = sh(["launchctl", "print", f"gui/{os.getuid()}/{label}"]); m = re.search(r"^\s*pid = (\d+)", out, re.M); return int(m.group(1)) if m else None


def proc_info(pid):
    _, lst = sh(["ps", "-o", "lstart=", "-p", str(pid)]); _, args = sh(["ps", "-o", "args=", "-p", str(pid)])
    st = datetime.datetime.strptime(lst, "%a %b %d %H:%M:%S %Y").astimezone(datetime.timezone.utc) if lst else None
    _, lo = sh(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"]); cwd = next((l[1:] for l in lo.splitlines() if l.startswith("n")), None)
    return st, args, cwd


def after_w5(pkg, receipt):
    C = contract(pkg); R = json.load(open(receipt))
    # rev 1 (2026-09-27): the sha expected at a run path = the contract's candidate if the release ships that file, else its pinned `unchanged`
    # sha; a path the contract pins neither way is a named BAD. (rev 0 read only the candidates and raised KeyError on shadow_loop_v3.py, which
    # this files-only package does not ship — found by a control run on the arm64 host before any window.)
    cand = {**C.get("unchanged", {}), **{it["dest"]: it["candidate_sha256"] for it in C["files"]}}
    t4 = datetime.datetime.strptime(R["completed_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    say(f"after-w5 W4 completed_utc={R['completed_utc']}")
    for label, script, dest in (("com.hsy.shadowloop", "shadow_loop_v3.py", "wide_shadow/shadow_loop_v3.py"),
                                ("com.hsy.combolive", "combo_stage.py", "wide_shadow/fea171/combo_stage.py")):
        pid = proc(label)
        if pid is None: cmp_(f"{label} pid", None, "running"); continue
        st, args, cwd = proc_info(pid)
        say(f"  VAL {label} pid={pid} start_utc={st.strftime('%Y-%m-%dT%H:%M:%SZ') if st else None} cwd={cwd} args={args[:160]}")
        cmp_(f"{label} start > W4 completion", bool(st and st > t4), True)
        if label == "com.hsy.shadowloop":
            path = os.path.join(cwd or "", script) if script in args.split() else None
        else:
            dsrc = open(f"{WS}/fea171/combo_live_daemon.sh").read(); ok = 'cd "$HOME/wide_shadow/fea171"' in dsrc and "-u combo_stage.py" in dsrc
            say(f"  VAL combo daemon script invokes combo_stage.py in its cwd: {ok}"); path = os.path.join(cwd or "", script) if ok else None
        cmp_(f"{label} {script} sha at the run path {path}", sha(path) if path and os.path.exists(path) else None, cand.get(dest, f"NOT PINNED BY THE CONTRACT: {dest}"))
    for label in ("com.hsy.combosnap", "com.hsy.comboparity"):
        _, out = sh(["launchctl", "print", f"gui/{os.getuid()}/{label}"]); cmp_(f"{label} loaded", bool(re.search(r"^\s*state = ", out, re.M)), True)
    _, sc = sh(["launchctl", "print", f"gui/{os.getuid()}/com.hsy.sidecar"]); loaded = bool(re.search(r"^\s*state = ", sc, re.M))
    _, dis = sh(["launchctl", "print-disabled", f"gui/{os.getuid()}"]); dl = [l.strip() for l in dis.splitlines() if "com.hsy.sidecar" in l]
    _, ps = sh(["ps", "-A", "-o", "pid=,args="]); sp = [l.strip() for l in ps.splitlines() if re.search(r"sidecar_daemon|sidecar_blend", l) and "version_probe" not in l]
    cmp_("sidecar not loaded", loaded, False); cmp_("sidecar processes", sp, [])
    # rev 1: 'cannot be started' = disabled in launchd OR no plist in any launchd search dir (the arm64 host carries no com.hsy.sidecar plist and
    # therefore no disabled-override entry; rev 0 required the override and read that host as BAD although nothing could start the sidecar)
    pl = [d for d in (f"{HOME}/Library/LaunchAgents", "/Library/LaunchAgents", "/Library/LaunchDaemons") if os.path.exists(f"{d}/com.hsy.sidecar.plist")]
    say(f"  VAL sidecar disabled-override lines={dl} plists={pl}")
    cmp_("sidecar cannot be started (disabled override, or no plist anywhere launchd looks)", (bool(dl) and all(("disabled" in l or "true" in l) for l in dl)) or not pl, True)


def first_anchor(pkg, A):
    C = contract(pkg); cand = {it["dest"]: it["candidate_sha256"] for it in C["files"]}; A = int(A)
    stp = f"{WS}/state/combo_live_status.json"; S = json.load(open(stp))
    say(f"first-anchor A={A} status={ {k: S.get(k) for k in ('anchor', 'ok', 'step', 'utc')} }")
    cmp_("combo_live_status anchor", S.get("anchor"), A); cmp_("combo_live_status ok", S.get("ok"), True)
    cmp_("combo_stage.py at the daemon run path == candidate", sha(f"{WS}/fea171/combo_stage.py"), cand["wide_shadow/fea171/combo_stage.py"])
    for rel in ("wide_shadow/fea171/prev_state.py", "wide_shadow/fea171/members_rule.py"):
        cmp_(rel, sha(f"{HOME}/{rel}") if os.path.exists(f"{HOME}/{rel}") else None, cand[rel])
    tc = f"{WS}/state/target_combo/{A}.json"
    if os.path.exists(tc):
        d = json.load(open(tc)); say(f"  VAL target_combo state_lookup={'yes' if 'state_lookup' in d else 'no'} members_recomputed={d.get('members_recomputed')} cold_start_refused={d.get('cold_start_refused')}")
        cmp_("kc_state_source (a normal anchor must be own)", d.get("kc_state_source"), "own"); cmp_("fc_state_source (a normal anchor must be own)", d.get("fc_state_source"), "own")
        tb = f"{WS}/state/target_blend/{A}.json"
        cmp_("f10 h_source (target_blend; a normal anchor must be own)", json.load(open(tb)).get("h_source") if os.path.exists(tb) else None, "own")
    else:
        cmp_("target_combo exists", False, True)
    log = open(f"{WS}/fea171/combo_live.log", errors="replace").read().splitlines()
    ends = [i for i, l in enumerate(log) if l.startswith(f"=== combo_live anchor={A} ")]
    if not ends: cmp_("combo_live.log block for A", None, "present"); return
    i = ends[-1]; j = max(k for k in range(i + 1) if k == 0 or log[k - 1].startswith("=== combo_live anchor=")) if i else 0
    for l in log[j:i + 1]:
        if any(t in l for t in ("STATE_LOOKUP", "MH_RECOMPUTED", "GAP_PAGE", "NC A2 member history", "COMBO_LIVE", "④", "⑤", "=== combo_live")): say("  LOG " + l[:300])
    cmp_("no GAP_PAGE line in this anchor's block (a normal anchor pages nothing)", sum("GAP_PAGE" in l for l in log[j:i + 1]), 0)
    if EXPECT_MH is not None:
        # rev 1 (handbook §2 W6 (b), AMENDMENT written 2026-09-27 before any GAP4 anchor): the recomputed member-history anchors == the frozen literal,
        # no errors; and the literal == the holes of state/members_hist.npz on the 4h grid inside [first hist anchor, A) — a hole the literal
        # missed or a literal anchor that is not a hole is named either way
        d = json.load(open(tc)) if os.path.exists(tc) else {}
        cmp_("members_recomputed anchors == frozen literal", sorted(int(k) for k in (d.get("members_recomputed") or {})), sorted(EXPECT_MH))
        cmp_("members_recompute_errors", d.get("members_recompute_errors") or {}, {})
        rc, out = sh([f"{WS}/venv/bin/python", "-c", "import numpy as np,sys; a=sorted(int(x) for x in np.load(sys.argv[1])['anchors']); A=int(sys.argv[2]); s=set(a); "
                      "print(','.join(str(t) for t in range(a[0], A, 14400) if t not in s))", f"{WS}/state/members_hist.npz", str(A)])
        holes = sorted(int(x) for x in out.split(",") if x) if rc == 0 else None
        say(f"  VAL members_hist holes in [first, A): {holes}")
        cmp_("frozen literal == members_hist holes before A", holes, sorted(EXPECT_MH))


def main():
    a = sys.argv[1:]; out = None
    if "--out" in a: i = a.index("--out"); out = a[i + 1]; a = a[:i] + a[i + 2:]
    global EXPECT_MH
    if "--expect-mh" in a: i = a.index("--expect-mh"); EXPECT_MH = [int(x) for x in a[i + 1].split(",") if x]; a = a[:i] + a[i + 2:]
    step = a[0]
    if step == "after-w3": after_w3(a[1], a[2:])
    elif step == "after-w4": after_w4(a[1], a[2])
    elif step == "after-w5": after_w5(a[1], a[2])
    elif step == "first-anchor": first_anchor(a[1], a[2])
    else: print("unknown step"); return 2
    say(f"GAP_VERSION_PROBE {step} {'OK' if not BAD else 'MISMATCH'} n={len(BAD)}" + (f" {BAD}" if BAD else ""))
    if out: open(out, "w").write("\n".join(LINES) + "\n")
    return 0 if not BAD else 3


if __name__ == "__main__":
    sys.exit(main())
