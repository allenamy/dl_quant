#!/usr/bin/env python3
"""Version measurements for the NC deploy (lead 2026-09-24, user: "never run the wrong code version"). READ-ONLY: hashes files, reads git
refs / launchctl / ps / lsof / logs; writes nothing outside --out. Every line prints the MEASURED value next to the value it is compared with;
mismatches are listed by name; exit 3 if any, else 0. The final line is VERSION_PROBE <step> OK|MISMATCH n=<k>.
  after-a3 <pkg> [--home H]                 every contract destination re-hashed == candidate_sha256
  after-a4 <pkg> <NEWSHA>                   running tree HEAD == origin/main (local ref and GitHub ls-remote) == NEWSHA; `git show NEWSHA` files ==
                                            the 5 pathspec files exactly; running-tree config/book.json: booster_sha_pin, f10_sha_pin, beta_overlay.mode,
                                            beta_overlay.max_combined_leverage, external_book.producer_contract (and == the bytes committed in NEWSHA)
  after-a5 <pkg> <NC_INSTALL_RECEIPT.json>  producer / combo daemon process start > A3 completion; sha of the script at the path each process runs
                                            (cwd from lsof + argv) == candidate (shadow_loop_v3.py a68c7a5f, combo_stage.py 363dd8c8); sidecar not loaded,
                                            disabled, no process
  first-anchor <pkg> <A>                    target_live/<A>.json booster_sha / f10_sha; shadow_log signal row booster_sha; on-disk model shas; MANIFEST;
                                            generation.json schema / anchor / file set; executor anchors row external_book ok / reason / shas vs book pins;
                                            anchor_runs.log lines naming a pin refusal or HOLD for A
usage: /usr/bin/python3 nc_version_probe.py <step> ... [--out F]"""
import argparse, datetime, glob, hashlib, json, os, re, subprocess, sys

HOME = os.path.expanduser("~"); DQ = f"{HOME}/dl_quant_live"; WS = f"{HOME}/wide_shadow"
PATHSPEC = ["config/book.json", "ops/anchor_report.py", "live/tests_anchor_report_builder.py",
            "ops/producer_release/20260923_nc/INSTALL_CONTRACT.json", "ops/producer_release/20260923_nc/PATCH_RECEIPT.json"]
LINES, BAD = [], []


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def say(s): LINES.append(s); print(s, flush=True)
def cmp_(name, measured, want):
    ok = measured == want
    say(f"  {'OK ' if ok else 'BAD'} {name}: measured={measured} compared_with={want}")
    if not ok: BAD.append(name)
def sh(args):
    r = subprocess.run(args, capture_output=True, text=True); return r.returncode, r.stdout.strip()
def contract(pkg): return json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
def cand(pkg, dest): return [f for f in contract(pkg)["files"] if f["dest"] == dest][0]["candidate_sha256"]


def after_a3(a):
    C = contract(a.pkg); say(f"after-a3 contract {sha(a.pkg + '/INSTALL_CONTRACT.json')} files={len(C['files'])} home={a.home}")
    for f in C["files"]:
        p = f"{a.home}/{f['dest']}"
        cmp_(f["dest"], sha(p) if os.path.exists(p) else None, f["candidate_sha256"])


def after_a4(a):
    C = contract(a.pkg); pins = C["executor_pins"]
    _, head = sh(["git", "-C", DQ, "rev-parse", "HEAD"]); _, om = sh(["git", "-C", DQ, "rev-parse", "origin/main"])
    rc, lr = sh(["git", "-C", DQ, "ls-remote", "origin", "refs/heads/main"]); lr = lr.split()[0] if rc == 0 and lr else f"ls-remote rc={rc}"
    _, full = sh(["git", "-C", DQ, "rev-parse", a.newsha])
    say(f"after-a4 NEWSHA={full}")
    cmp_("running tree HEAD", head, full); cmp_("origin/main (local ref)", om, full); cmp_("origin/main (GitHub ls-remote)", lr, full)
    _, files = sh(["git", "-C", DQ, "show", "--name-only", "--format=", full])
    cmp_("git show NEWSHA file list", sorted(x for x in files.splitlines() if x), sorted(PATHSPEC))
    B = json.load(open(f"{DQ}/config/book.json")); eb = B.get("external_book", {}); bo = B.get("beta_overlay", {})
    for k, v in (("external_book.booster_sha_pin", eb.get("booster_sha_pin")), ("external_book.f10_sha_pin", eb.get("f10_sha_pin")),
                 ("beta_overlay.mode", bo.get("mode")), ("beta_overlay.max_combined_leverage", bo.get("max_combined_leverage")),
                 ("external_book.producer_contract", eb.get("producer_contract"))):
        say(f"  VAL {k} = {v}")
    cmp_("booster_sha_pin == contract", eb.get("booster_sha_pin"), pins["booster_sha_pin"])
    cmp_("f10_sha_pin == contract", eb.get("f10_sha_pin"), pins["f10_sha_pin"])
    cmp_("beta_overlay.mode", bo.get("mode"), a.beta_mode)
    cmp_("beta_overlay.max_combined_leverage", bo.get("max_combined_leverage"), a.max_combined)
    cmp_("external_book.producer_contract", eb.get("producer_contract"), "nc_v1")
    r = subprocess.run(["git", "-C", DQ, "show", f"{full}:config/book.json"], capture_output=True)
    cmp_("running-tree book.json bytes == NEWSHA:config/book.json", hashlib.sha256(open(f"{DQ}/config/book.json", "rb").read()).hexdigest(),
         hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None)


def proc(label):
    _, out = sh(["launchctl", "print", f"gui/{os.getuid()}/{label}"])
    m = re.search(r"^\s*pid = (\d+)", out, re.M); return int(m.group(1)) if m else None


def proc_info(pid):
    _, lstart = sh(["ps", "-o", "lstart=", "-p", str(pid)]); _, args = sh(["ps", "-o", "args=", "-p", str(pid)])
    _, cw = sh(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"]); cwd = [l[1:] for l in cw.splitlines() if l.startswith("n")]
    st = datetime.datetime.strptime(" ".join(lstart.split()), "%a %b %d %H:%M:%S %Y").astimezone(datetime.timezone.utc) if lstart else None
    return st, args, (cwd[0] if cwd else None)


def after_a5(a):
    R = json.load(open(a.receipt)); t3 = datetime.datetime.strptime(R["completed_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    say(f"after-a5 A3 apply completed_utc={R['completed_utc']} stage={R.get('stage')} VERDICT={R.get('VERDICT')} USER_OVERRIDE={R.get('USER_OVERRIDE')}")
    for label, script, dest in (("com.hsy.shadowloop", "shadow_loop_v3.py", "wide_shadow/shadow_loop_v3.py"),
                                ("com.hsy.combolive", "combo_stage.py", "wide_shadow/fea171/combo_stage.py")):
        pid = proc(label)
        if pid is None:
            cmp_(f"{label} pid", None, "running"); continue
        st, args, cwd = proc_info(pid)
        say(f"  VAL {label} pid={pid} start_utc={st.strftime('%Y-%m-%dT%H:%M:%SZ') if st else None} cwd={cwd} args={args[:160]}")
        cmp_(f"{label} start > A3 completion", bool(st and st > t3), True)
        if label == "com.hsy.shadowloop":
            path = os.path.join(cwd or "", script) if script in args.split() else None
        else:   # the daemon cd's to $HOME/wide_shadow/fea171 and runs `python -u combo_stage.py` there each anchor
            dsrc = open(f"{WS}/fea171/combo_live_daemon.sh").read()
            ok = 'cd "$HOME/wide_shadow/fea171"' in dsrc and "-u combo_stage.py" in dsrc
            say(f"  VAL combo daemon script invokes combo_stage.py in its cwd: {ok}")
            path = os.path.join(cwd or "", script) if ok else None
        say(f"  VAL {label} script path={path} realpath={os.path.realpath(path) if path else None}")
        cmp_(f"{label} {script} sha at the run path", sha(path) if path and os.path.exists(path) else None, cand(a.pkg, dest))
    _, sc = sh(["launchctl", "print", f"gui/{os.getuid()}/com.hsy.sidecar"])
    loaded = bool(re.search(r"^\s*state = ", sc, re.M))
    _, dis = sh(["launchctl", "print-disabled", f"gui/{os.getuid()}"]); dl = [l.strip() for l in dis.splitlines() if "com.hsy.sidecar" in l]
    _, ps = sh(["ps", "-A", "-o", "pid=,args="]); sp = [l.strip() for l in ps.splitlines() if re.search(r"sidecar_daemon|sidecar_blend", l) and "nc_version_probe" not in l]
    say(f"  VAL sidecar launchctl loaded={loaded} print-disabled={dl} processes={sp}")
    cmp_("sidecar not loaded", loaded, False); cmp_("sidecar processes", sp, [])
    cmp_("sidecar disabled", bool(dl) and all(("disabled" in l or "true" in l) for l in dl), True)


def first_anchor(a):
    A = int(a.anchor); C = contract(a.pkg); pins = C["executor_pins"]
    tl = f"{WS}/state/target_live/{A}.json"; T = json.load(open(tl)) if os.path.exists(tl) else {}
    say(f"first-anchor A={A} ({datetime.datetime.fromtimestamp(A, datetime.timezone.utc):%Y-%m-%dT%H:%MZ})")
    say(f"  VAL target_live booster_sha={T.get('booster_sha')} f10_sha={T.get('f10_sha')} written_utc={T.get('written_utc')}")
    cmp_("target_live booster_sha", T.get("booster_sha"), pins["booster_sha_pin"]); cmp_("target_live f10_sha", T.get("f10_sha"), pins["f10_sha_pin"])
    sig = [json.loads(l) for l in open(f"{WS}/shadow_log.jsonl") if f'"anchor_ts": {A}' in l or f'"anchor_ts":{A}' in l]
    sig = [r for r in sig if r.get("e") == "signal"]
    say(f"  VAL shadow_log signal rows for A: {len(sig)}; booster_sha(12)={[r.get('booster_sha') for r in sig]}")
    cmp_("shadow_log signal booster_sha (12)", [r.get("booster_sha") for r in sig][-1:] , [pins["booster_sha_pin"][:12]])
    man = json.load(open(f"{WS}/shadow_bundle/MANIFEST.json"))
    cmp_("MANIFEST slow2026.txt", man.get("slow2026.txt"), pins["booster_sha_pin"])
    cmp_("on-disk slow2026.txt", sha(f"{WS}/shadow_bundle/slow2026.txt"), pins["booster_sha_pin"])
    cmp_("on-disk f10_live_s42_np.npz", sha(f"{WS}/fea171/f10_live_s42_np.npz"), pins["f10_sha_pin"])
    G = json.load(open(f"{WS}/state/generation.json"))
    say(f"  VAL generation.json schema_version={G.get('schema_version')} anchor_ts={G.get('anchor_ts')} files={sorted(G.get('files', {}))}")
    cmp_("generation.json file set (NC contract = 5 signed files)", sorted(G.get("files", {})),
         sorted(["rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz"]))
    B = json.load(open(f"{DQ}/config/book.json"))["external_book"]
    L = f"{DQ}/state/live/pilot_log"; rows = []
    for f in sorted(glob.glob(f"{L}/2*/anchors.jsonl"))[-2:]:
        rows += [json.loads(x) for x in open(f)]
    rows = [r for r in rows if (r.get("external_book") or {}).get("nominal_ts") == A]
    eb = (rows[-1].get("external_book") or {}) if rows else {}
    say(f"  VAL executor anchors rows for A: {len(rows)}; external_book ok={eb.get('ok')} reason={eb.get('reason')} sha_ok={eb.get('sha_ok')} "
        f"booster_sha={eb.get('booster_sha')} f10_sha={eb.get('f10_sha')} opening_halted={rows[-1].get('opening_halted') if rows else None}")
    cmp_("executor external_book ok", eb.get("ok"), True); cmp_("executor external_book reason", eb.get("reason"), None)
    cmp_("executor read booster_sha == book pin", eb.get("booster_sha"), B.get("booster_sha_pin"))
    cmp_("executor read f10_sha == book pin", eb.get("f10_sha"), B.get("f10_sha_pin"))
    t0 = datetime.datetime.fromtimestamp(A, datetime.timezone.utc).strftime("%Y-%m-%dT%H")
    hits = [l.strip()[:200] for l in open(f"{DQ}/state/anchor_runs.log", errors="replace") if l.startswith(t0[:13]) and re.search(r"REFUSED|HOLD|sha_pin|pin_mismatch|PIN", l)]
    say(f"  VAL anchor_runs.log lines in hour {t0}Z naming REFUSED/HOLD/sha_pin/PIN: {len(hits)}")
    for h in hits[:10]: say(f"    {h}")
    cmp_("anchor_runs.log pin refusal / HOLD lines", [h for h in hits if re.search(r"REFUSED|HOLD", h)], [])


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="step", required=True)
    p = sp.add_parser("after-a3"); p.add_argument("pkg"); p.add_argument("--home", default=HOME)
    p = sp.add_parser("after-a4"); p.add_argument("pkg"); p.add_argument("newsha"); p.add_argument("--beta-mode", default="shadow"); p.add_argument("--max-combined", type=float, default=2.5)
    p = sp.add_parser("after-a5"); p.add_argument("pkg"); p.add_argument("receipt")
    p = sp.add_parser("first-anchor"); p.add_argument("pkg"); p.add_argument("anchor")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    {"after-a3": after_a3, "after-a4": after_a4, "after-a5": after_a5, "first-anchor": first_anchor}[a.step](a)
    say(f"VERSION_PROBE {a.step} {'OK' if not BAD else 'MISMATCH'} n={len(BAD)}" + (f" bad={BAD}" if BAD else ""))
    if a.out:
        open(a.out, "w").write("\n".join(LINES) + "\n")
    return 0 if not BAD else 3


if __name__ == "__main__":
    sys.exit(main())
