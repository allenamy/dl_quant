#!/usr/bin/env python3
"""Version measurements for the v2 + B + C release (DEPLOY_v2_durable_2026-09-25 W3 / W4 / W5; the NC probe's after-a4 / after-a5 are specific
to the NC pathspec and candidates, so this is the release's own). READ-ONLY: hashes files, reads git refs / GitHub ls-remote / launchctl / ps /
lsof; runs the running tree's own drift guard (read-only). Every line prints MEASURED next to COMPARED; exit 3 on any mismatch.
  after-w3 <NEWSHA> <pathspec...>   running tree HEAD == local origin/main == GitHub main (ls-remote) == NEWSHA; `git show --name-only NEWSHA` ==
                                    the pathspec exactly; code area clean (state/ logs/ excluded); live/beta_overlay.py VERSION == m3_beta_v2;
                                    config/book.json bytes == those of 5d3029c (the release changes no book configuration: M3 stays shadow);
                                    the running tree's ops/check_upstream_drift.py rc 0 with "no drift across 6".
  after-w4 <pkg> <receipt>          receipt stage installed_not_started, state_manifest_diff []; every contract dest re-hashed == candidate;
                                    every archive src absent and dst == expected sha.
  after-w5 <pkg> <receipt>          com.hsy.shadowloop / com.hsy.combolive process start > receipt completed_utc; the script at each process's run
                                    path (cwd from lsof + argv; combo daemon runs combo_stage.py in its cwd) == candidate; com.hsy.combosnap /
                                    com.hsy.comboparity loaded; sidecar not loaded, disabled, no process.
usage: /usr/bin/python3 v2c_version_probe.py <step> ... [--out F]"""
import datetime, hashlib, json, os, re, subprocess, sys

HOME = os.path.expanduser("~"); DQ = f"{HOME}/dl_quant_live"; WS = f"{HOME}/wide_shadow"; OLD_EXEC = "5d3029c0411bf08d7d3e1457f6b46c3ac1ff043b"
LINES, BAD = [], []
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
    cmp_("config/book.json bytes == 5d3029c (no book change)", open(f"{DQ}/config/book.json").read().strip() == old_book, True)
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
    C = contract(pkg); R = json.load(open(receipt)); cand = {it["dest"]: it["candidate_sha256"] for it in C["files"]}
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
        cmp_(f"{label} {script} sha at the run path {path}", sha(path) if path and os.path.exists(path) else None, cand[dest])
    for label in ("com.hsy.combosnap", "com.hsy.comboparity"):
        _, out = sh(["launchctl", "print", f"gui/{os.getuid()}/{label}"]); cmp_(f"{label} loaded", bool(re.search(r"^\s*state = ", out, re.M)), True)
    _, sc = sh(["launchctl", "print", f"gui/{os.getuid()}/com.hsy.sidecar"]); loaded = bool(re.search(r"^\s*state = ", sc, re.M))
    _, dis = sh(["launchctl", "print-disabled", f"gui/{os.getuid()}"]); dl = [l.strip() for l in dis.splitlines() if "com.hsy.sidecar" in l]
    _, ps = sh(["ps", "-A", "-o", "pid=,args="]); sp = [l.strip() for l in ps.splitlines() if re.search(r"sidecar_daemon|sidecar_blend", l) and "version_probe" not in l]
    cmp_("sidecar not loaded", loaded, False); cmp_("sidecar processes", sp, [])
    cmp_("sidecar disabled", bool(dl) and all(("disabled" in l or "true" in l) for l in dl), True)


def main():
    a = sys.argv[1:]; out = None
    if "--out" in a: i = a.index("--out"); out = a[i + 1]; a = a[:i] + a[i + 2:]
    step = a[0]
    if step == "after-w3": after_w3(a[1], a[2:])
    elif step == "after-w4": after_w4(a[1], a[2])
    elif step == "after-w5": after_w5(a[1], a[2])
    else: print("unknown step"); return 2
    say(f"V2C_VERSION_PROBE {step} {'OK' if not BAD else 'MISMATCH'} n={len(BAD)}" + (f" {BAD}" if BAD else ""))
    if out: open(out, "w").write("\n".join(LINES) + "\n")
    return 0 if not BAD else 3


if __name__ == "__main__":
    sys.exit(main())
