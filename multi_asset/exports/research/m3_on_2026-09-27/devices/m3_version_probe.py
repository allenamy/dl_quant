#!/usr/bin/env python3
"""Version measurements for the M3-ON release (DEPLOY_m3_on_2026-09-27). READ-ONLY (git refs, GitHub ls-remote, files, the running tree's
own drift guard). Every line prints MEASURED next to COMPARED; exit 3 on any mismatch; last line M3_VERSION_PROBE <step> OK|MISMATCH n=<k>.
  pre <OLDSHA>              running tree HEAD == OLDSHA; book.json beta_overlay.mode == shadow, max_combined_leverage == 2.5
  after-w3 <NEWSHA> <OLDSHA> running tree HEAD == local origin/main == GitHub main == NEWSHA; `git show --name-only NEWSHA` == [config/book.json];
                            book.json parsed == OLDSHA's with ONLY beta_overlay.mode changed to "on" (max_combined_leverage still 2.5, every
                            other key identical); exactly one changed line in the diff; code area clean; drift guard across 6 green
  after-rb <RBSHA> <OLDSHA>  rollback: HEAD == RBSHA (== origin == GitHub); book.json BYTES == OLDSHA's (mode shadow again)
usage: /usr/bin/python3 m3_version_probe.py <step> ... [--out F]"""
import json, os, re, subprocess, sys
HOME = os.path.expanduser("~"); DQ = f"{HOME}/dl_quant_live"; LINES, BAD = [], []
def say(s): LINES.append(s); print(s, flush=True)
def cmp_(name, measured, want):
    ok = measured == want
    say(f"  {'OK ' if ok else 'BAD'} {name}: measured={measured} compared_with={want}")
    if not ok: BAD.append(name)
def sh(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw); return r.returncode, r.stdout.strip()
def refs(sha):
    _, head = sh(["git", "-C", DQ, "rev-parse", "HEAD"]); _, om = sh(["git", "-C", DQ, "rev-parse", "origin/main"])
    _, lr = sh(["git", "ls-remote", "https://github.com/allenamy/dl_quant_live.git", "refs/heads/main"]); gh = lr.split()[0] if lr else None
    full = sh(["git", "-C", DQ, "rev-parse", sha])[1]
    cmp_("running tree HEAD", head, full); cmp_("local origin/main", om, full); cmp_("GitHub main (ls-remote)", gh, full)
def book_at(sha): return sh(["git", "-C", DQ, "show", f"{sha}:config/book.json"])[1]
def main():
    a = sys.argv[1:]; out = None
    if "--out" in a: i = a.index("--out"); out = a[i + 1]; a = a[:i] + a[i + 2:]
    step = a[0]; cur = open(f"{DQ}/config/book.json").read()
    if step == "pre":
        cmp_("running tree HEAD == OLDSHA", sh(["git", "-C", DQ, "rev-parse", "HEAD"])[1], sh(["git", "-C", DQ, "rev-parse", a[1]])[1])
        bo = json.loads(cur).get("beta_overlay") or {}
        cmp_("beta_overlay.mode", bo.get("mode"), "shadow"); cmp_("beta_overlay.max_combined_leverage", bo.get("max_combined_leverage"), 2.5)
    elif step == "after-w3":
        new, old = a[1], a[2]; refs(new)
        _, files = sh(["git", "-C", DQ, "show", "--name-only", "--format=", new]); cmp_("NEWSHA commit files", sorted(files.split()), ["config/book.json"])
        d_new, d_old = json.loads(cur), json.loads(book_at(old))
        cmp_("committed book.json == running tree book.json", book_at(new) == cur.rstrip("\n") or book_at(new) == cur, True)
        cmp_("beta_overlay.mode", d_new.get("beta_overlay", {}).get("mode"), "on")
        cmp_("beta_overlay.max_combined_leverage", d_new.get("beta_overlay", {}).get("max_combined_leverage"), 2.5)
        d_old["beta_overlay"]["mode"] = "on"
        cmp_("book.json == OLDSHA's with ONLY beta_overlay.mode changed", d_new == d_old, True)
        _, diff = sh(["git", "-C", DQ, "diff", "--unified=0", old, new, "--", "config/book.json"])
        chg = [l for l in diff.splitlines() if re.match(r"^[+-](?![+-])", l)]
        cmp_("diff lines", chg, ['-  "mode": "shadow",', '+  "mode": "on",'])
        st = subprocess.run(["git", "-C", DQ, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout
        cmp_("running tree code area clean", [l for l in st.splitlines() if not l[3:].startswith(("state/", "logs/"))], [])
        rc, o = sh(["/usr/bin/python3", f"{DQ}/ops/check_upstream_drift.py"], cwd=DQ, timeout=180)
        cmp_("drift guard green across 6", rc == 0 and "no drift across 6" in o, True)
    elif step == "after-rb":
        rb, old = a[1], a[2]; refs(rb)
        cmp_("book.json bytes == OLDSHA's (rolled back)", cur.rstrip("\n") == book_at(old).rstrip("\n"), True)
        cmp_("beta_overlay.mode", (json.loads(cur).get("beta_overlay") or {}).get("mode"), "shadow")
    else:
        print("unknown step"); return 2
    say(f"M3_VERSION_PROBE {step} {'OK' if not BAD else 'MISMATCH'} n={len(BAD)}" + (f" {BAD}" if BAD else ""))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f: f.write("\n".join(LINES) + "\n")
    return 0 if not BAD else 3
if __name__ == "__main__":
    sys.exit(main())
