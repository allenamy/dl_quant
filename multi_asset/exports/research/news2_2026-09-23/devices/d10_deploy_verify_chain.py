#!/usr/bin/env python3
"""d10_deploy_verify_chain.py -- deploy-time identity check for the October chain (news2 2026-09-27, lead ruling after the re-read
delivery: "the file list is derived from the runbook and the import closure; use fresh2's common/pod2_deploy_verify.sh").

Runs on the Mac (ssh to pod2). The three-way comparison itself is NOT reimplemented: every remote dir is judged by
common/pod2_deploy_verify.sh (sha of git HEAD blob == working tree == pod2 file). This device only decides WHICH files must be there
and reads that tool's per-file lines:

  1. population = the runbook chain + its Python import closure (tests_october_chain_contract.chain_from_runbook / import_closure, the
     same derivation the contract test uses), minus a short declared set that must never be on pod2 (the four historical pull drivers
     pinned in the contract test; the Mac-installed archive job; the Mac-side contract test);
  2. every chain file homed in news2 devices/ must be in <EXP>/devices; every chain file homed in research/common/ must be in
     <EXP>/devices or <EXP>/common (devices look in their own dir first); <EXP>/devices and <EXP>/common are judged WHOLE by the tool
     (a stale or unknown extra file there is red too);
  3. code the chain runs from OUTSIDE <EXP> (hard-coded pod2 roots in the chain's shell scripts, and absolute *.py string literals in
     the chain's Python) plus that code's own local imports: each such file must have an OK line from the tool run on its directory.
     Other files in those shared roots are reported, not judged (they are other runs' deployments). A root with no declared local
     source is red (UNMAPPED_ROOT), and a literal named in EXCLUDED_LITERALS that no longer occurs is red (stale exclusion).

usage:  d10_deploy_verify_chain.py --exp <pod2 dir> --out <receipt.json>             (verify)
        d10_deploy_verify_chain.py --exp <pod2 dir> --out <receipt.json> --sync      (git archive HEAD -> pod2, then verify; refuses
                                                                                      a dir that already has devices/ or common/)
        d10_deploy_verify_chain.py --selftest
Last line: CHAIN_DEPLOY_VERIFY PASS=True|False ...; rc 0 only on PASS.
"""
import argparse, ast, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import tests_october_chain_contract as C   # noqa: E402  (population derivation shared with the contract test)
RESEARCH, COMMON, REPO = C.RESEARCH, C.COMMON, C.REPO
sys.path.insert(0, COMMON)
import durable_write as DW   # noqa: E402
TOOL = os.path.join(COMMON, "pod2_deploy_verify.sh")
NC_DEV = os.path.join(RESEARCH, "nc_2026-09-23", "devices")

NEVER_ON_POD2 = {n: "historical pull driver: must not be re-run (sha pinned in tests_october_chain_contract.py)"
                 for n in C.HISTORICAL_PULL_DRIVERS}
NEVER_ON_POD2.update({
    "archive_live_ledger.py": "installed on the Mac as ~/funding_ledger_archive (lead deploy), never run on pod2",
    "tests_october_chain_contract.py": "the contract test runs on the Mac against the repo",
    # runbook 1d names it only as the SHAPE of the new driver d10_reaudit_months_pod2.sh (months from argv, new output suffix); it
    # hard-codes EXP=/dev/shm/d10_2026-09-25 (found by this device's first derivation: UNMAPPED_ROOT), so running it as-is would run
    # the 09-25 deploy's devices.
    "d10_reaudit_jan_to_aug_pod2.sh": "runbook 1d template only (hard-codes the 09-25 EXP); the step runs the new driver",
})
# Shared pod2 roots the chain's code runs from, and where their bytes live in the repo. The nc root and the news2 root run the
# EXECUTED nc_legs / nc_hist_features (nc_2026-09-23/devices/README_executed_versions_2026-09-27.md), so those two names map there.
_EXEC = {"nc_legs.py": "multi_asset/exports/research/nc_2026-09-23/devices/nc_legs.executed_18387627.py",
         "nc_hist_features.py": "multi_asset/exports/research/nc_2026-09-23/devices/nc_hist_features.executed_3eee6e88.py"}
EXTERNAL_ROOTS = {
    "/dev/shm/nc_2026-09-23/devices": {"local": [NC_DEV], "maps": _EXEC},
    "/dev/shm/news2_2026-09-23/devices": {"local": [HERE, NC_DEV], "maps": _EXEC},
    "/dev/shm/nc_2026-09-23/devices_arm": {"local": [NC_DEV], "maps": {}},
}
# (device, literal) -> why the literal is not code the chain runs. A literal listed here that no longer occurs is red.
EXCLUDED_LITERALS = {
    ("d10_legs_rn8_vs_archive.py", "/dev/shm/nc_2026-09-23/tree/shadow_loop_v3.py"):
        "provenance string written into the receipt (matched by hash), never imported or run",
    ("d10_stage5_engine.py", "/workspace/dlarch_2026-09-24/dlarch_chain_run.py"):
        "d10_stage5_engine.py is not in the October chain population; listed so a later runbook naming it turns this red for review",
    ("d10_stage5_engine.py", "/workspace/dlarch_2026-09-24/dlarch_cell_retain.py"):
        "same as above",
}
ABS_PY = re.compile(r"^/(?:dev/shm|workspace|root)/[A-Za-z0-9_./-]+\.(?:py|sh)$")


def shell_refs(text):
    """Absolute remote paths of *.py/*.sh a shell script references through variables it assigns itself, e.g.
    NCR=/dev/shm/nc_2026-09-23; D=$NCR/devices; ... $D/nc_p2_build.py  ->  /dev/shm/nc_2026-09-23/devices/nc_p2_build.py.
    A reference whose prefix does not expand to an absolute path (e.g. $EXP from argv) is left to the <EXP> check."""
    body = "\n".join(l.split("#", 1)[0] if not l.lstrip().startswith("#!") else "" for l in text.splitlines())
    env = {}
    for m in re.finditer(r"(?:^|[\s;])([A-Za-z_][A-Za-z0-9_]*)=([^\s;\"'()`]+)", body):
        env[m.group(1)] = m.group(2)
    def expand(s, depth=0):
        if depth > 8:
            return s
        t = re.sub(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", lambda m: env.get(m.group(1), m.group(0)), s)
        return t if t == s else expand(t, depth + 1)
    out = set()
    for m in re.finditer(r"(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?:/[A-Za-z0-9_.-]+)*/[A-Za-z0-9_]+\.(?:py|sh))\b", body):
        p = expand(m.group(1))
        if ABS_PY.match(p):
            out.add(p)
    return out


def py_literal_refs(text):
    out = set()
    for n in ast.walk(ast.parse(text)):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and ABS_PY.match(n.value):
            out.add(n.value)
    return out


def local_imports(src):
    mods = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods.add(n.module.split(".")[0])
    return mods


def source_for(root, name):
    spec = EXTERNAL_ROOTS[root]
    if name in spec["maps"]:
        return os.path.join(REPO, spec["maps"][name])
    for d in spec["local"]:
        if os.path.isfile(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


def derive():
    _, resolved, _ = C.chain_from_runbook()
    pop = dict(resolved, **C.import_closure(resolved))
    exp_dev, exp_common, skipped, foreign = {}, {}, {}, {}
    for key, p in sorted(pop.items()):
        n, home = os.path.basename(p), os.path.dirname(os.path.realpath(p))
        if n in NEVER_ON_POD2:
            skipped[n] = NEVER_ON_POD2[n]
        elif home == os.path.realpath(HERE):
            exp_dev[n] = os.path.relpath(p, REPO)
        elif home == os.path.realpath(COMMON):
            exp_common[n] = os.path.relpath(p, REPO)
        else:
            foreign[key] = "owner-deployed from its own research dir (checked by its owner at its own start)"
    # code run from outside <EXP>
    refs, used_excl = {}, set()
    for n, rel in sorted(dict(exp_dev, **exp_common).items()):
        text = open(os.path.join(REPO, rel)).read()
        lits = shell_refs(text) if n.endswith(".sh") else py_literal_refs(text)
        for lit in sorted(lits):
            if (n, lit) in EXCLUDED_LITERALS:
                used_excl.add((n, lit)); continue
            refs.setdefault(lit, []).append(n)
    external, problems = {}, []
    direct = set(refs)
    todo = sorted(refs)
    while todo:
        path = todo.pop(0)
        root, name = os.path.dirname(path), os.path.basename(path)
        if path in external:
            continue
        if root not in EXTERNAL_ROOTS:
            problems.append("UNMAPPED_ROOT %s (referenced by %s)" % (path, refs.get(path))); continue
        src = source_for(root, name)
        external[path] = {"source": os.path.relpath(src, REPO) if src else None, "referenced_by": refs.get(path, ["import"]),
                          "kind": "ref" if path in direct else "import"}
        if src and name.endswith(".py"):
            for m in sorted(local_imports(open(src).read())):
                if source_for(root, m + ".py"):
                    q = root + "/" + m + ".py"
                    if q not in external and q not in todo:
                        refs.setdefault(q, []).append("import by " + name); todo.append(q)
    for (dev, lit), why in EXCLUDED_LITERALS.items():
        if dev in exp_dev or dev in exp_common:
            if (dev, lit) not in used_excl:
                problems.append("STALE_EXCLUSION %s %s" % (dev, lit))
    return {"exp_devices": exp_dev, "exp_common": exp_common, "never_on_pod2": skipped, "foreign_owner_deployed": foreign,
            "external": external, "excluded_literals": {"%s %s" % k: v for k, v in EXCLUDED_LITERALS.items()},
            "derive_problems": problems}


LINE = re.compile(r"^(OK|MISMATCH|UNKNOWN|ARCHIVE)\s+(\S+)")


def parse_tool(out):
    per = {}
    for l in out.splitlines():
        m = LINE.match(l)
        if m:
            per[m.group(2)] = m.group(1)
    fin = [l for l in out.splitlines() if l.startswith("DEPLOY_VERIFY ")]
    return per, (fin[-1] if fin else None)


def judge(man, runs, exp):
    """runs: {remote dir: (rc, tool stdout)}. Pure: selftested on synthetic tool output."""
    bad = list(man["derive_problems"])
    dv, cm = exp + "/devices", exp + "/common"
    pdv, fdv = parse_tool(runs[dv][1]); rc_dv = runs[dv][0]
    if not (rc_dv == 0 and fdv and fdv.startswith("DEPLOY_VERIFY PASS=True")):
        bad.append("EXP_DEVICES_DIR_NOT_PASS %s" % fdv)
    pcm = {}
    if cm in runs:
        pcm, fcm = parse_tool(runs[cm][1])
        if not (runs[cm][0] == 0 and fcm and fcm.startswith("DEPLOY_VERIFY PASS=True")):
            bad.append("EXP_COMMON_DIR_NOT_PASS %s" % fcm)
    for n in man["exp_devices"]:
        if pdv.get(n) != "OK":
            bad.append("EXP_DEVICE %s %s" % (n, pdv.get(n, "MISSING")))
    for n in man["exp_common"]:
        got = [x for x in (pdv.get(n), pcm.get(n)) if x is not None]
        if not got or any(g != "OK" for g in got):
            bad.append("EXP_COMMON %s devices=%s common=%s" % (n, pdv.get(n, "absent"), pcm.get(n, "absent")))
    ext = {}
    for path in man["external"]:
        root, name = os.path.dirname(path), os.path.basename(path)
        st = parse_tool(runs[root][1])[0].get(name, "MISSING") if root in runs else "NOT_RUN"
        # An import found only statically: if the file is not in that remote dir, Python cannot load it from there (e.g.
        # nc_hist_features imports nc_contract from the PATCH_RECEIPT-pinned producer tree it puts first on sys.path). If it IS there
        # it can shadow, so a present copy must be OK.
        if st == "MISSING" and man["external"][path].get("kind") == "import":
            st = "ABSENT_IMPORT_RESOLVED_ELSEWHERE"
            ext[path] = st
            continue
        ext[path] = st
        if st != "OK":
            bad.append("EXTERNAL %s %s" % (path, st))
    return bad, ext


def tool_args(root, exp):
    if root == exp + "/devices":
        return [root, HERE + ":" + COMMON]
    if root == exp + "/common":
        return [root, COMMON]
    spec = EXTERNAL_ROOTS[root]
    return [root, ":".join(spec["local"])] + ["%s=%s" % kv for kv in sorted(spec["maps"].items())]


def ssh(cmd, **kw):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "pod2", cmd], capture_output=True, text=True, **kw)


def sync(exp, man):
    """HEAD blobs only (git archive), never the working tree; refuses a target that already has devices/ or common/."""
    r = ssh("test -e %s/devices -o -e %s/common && echo EXISTS || echo NEW" % (exp, exp))
    if r.stdout.strip() != "NEW":
        sys.exit("SYNC REFUSED: %s/devices or /common exists (or ssh failed: %r); sync only into a new dir" % (exp, r.stdout + r.stderr))
    for sub, tree in (("devices", os.path.relpath(HERE, REPO)), ("common", os.path.relpath(COMMON, REPO))):
        a = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", "HEAD:" + tree], capture_output=True, check=True)
        x = subprocess.run(["ssh", "-o", "BatchMode=yes", "pod2", "mkdir -p %s/%s && tar -x -C %s/%s" % (exp, sub, exp, sub)],
                           input=a.stdout, capture_output=True)
        if x.returncode:
            sys.exit("SYNC FAILED %s: %s" % (sub, x.stderr.decode()[-300:]))


def selftest():
    res = []
    def ok(name, cond):
        res.append((name, bool(cond))); print("  [%s] %s" % ("PASS" if cond else "FAIL", name))
    sh = "NCR=/dev/shm/nc_2026-09-23; D=$NCR/devices\nW=/dev/shm/news2_2026-09-23\n$PY $D/nc_p2_build.py p1\n$P $W/devices/nc_legs.py\n" \
         "# $D/commented.py\n$PY $EXP/devices/x.py\n"
    ok("S1_shell_refs_expand_own_vars", shell_refs(sh) == {"/dev/shm/nc_2026-09-23/devices/nc_p2_build.py",
                                                           "/dev/shm/news2_2026-09-23/devices/nc_legs.py"})
    ok("S2_py_literals", py_literal_refs('A = "/dev/shm/x/devices/a.py"\nB = "rel/b.py"\n') == {"/dev/shm/x/devices/a.py"})
    exp = "/workspace/T"
    man = {"derive_problems": [], "exp_devices": {"a.py": "x"}, "exp_common": {"durable_write.py": "y"},
           "external": {"/dev/shm/nc_2026-09-23/devices/nc_legs.py": {}}}
    good = {exp + "/devices": (0, "OK       a.py s\nOK       durable_write.py s\nDEPLOY_VERIFY PASS=True n=2 bad=0"),
            exp + "/common": (0, "OK       durable_write.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0"),
            "/dev/shm/nc_2026-09-23/devices": (1, "OK       nc_legs.py s\nMISMATCH nc_gate_g1.py h\nDEPLOY_VERIFY PASS=False n=2 bad=1")}
    ok("S3_baseline_green (unrelated mismatch in a shared root is not judged)", judge(man, good, exp)[0] == [])
    def mut(k, v):
        r = dict(good); r[k] = v; return judge(man, r, exp)[0]
    ok("S4_missing_exp_device_red", mut(exp + "/devices", (0, "OK       durable_write.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0")))
    ok("S5_exp_dir_not_pass_red", mut(exp + "/devices", (1, "OK       a.py s\nOK       durable_write.py s\nUNKNOWN  z.py r\n"
                                                                "DEPLOY_VERIFY PASS=False n=3 bad=1")))
    ok("S6_stale_common_copy_in_devices_red", mut(exp + "/devices", (0, "OK       a.py s\nMISMATCH durable_write.py h\n"
                                                                          "DEPLOY_VERIFY PASS=True n=2 bad=0")))
    ok("S7_common_absent_everywhere_red", judge(man, dict(good, **{
        exp + "/devices": (0, "OK       a.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0"),
        exp + "/common": (0, "OK       other.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0")}), exp)[0])
    ok("S8_external_mismatch_red", mut("/dev/shm/nc_2026-09-23/devices", (1, "MISMATCH nc_legs.py h\nDEPLOY_VERIFY PASS=False n=1 bad=1")))
    ok("S9_external_missing_red", mut("/dev/shm/nc_2026-09-23/devices", (0, "OK       other.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0")))
    ok("S10_no_final_line_red (ssh died mid-output)", mut(exp + "/devices", (0, "OK       a.py s\nOK       durable_write.py s\n")))
    man_i = dict(man, external={"/dev/shm/nc_2026-09-23/devices/nc_legs.py": {"kind": "import"}})
    r_i = dict(good, **{"/dev/shm/nc_2026-09-23/devices": (0, "OK       other.py s\nDEPLOY_VERIFY PASS=True n=1 bad=0")})
    ok("S15_absent_static_import_not_red_but_present_mismatch_red",
       judge(man_i, r_i, exp)[0] == [] and judge(man_i, dict(good, **{"/dev/shm/nc_2026-09-23/devices":
                                              (1, "MISMATCH nc_legs.py h\nDEPLOY_VERIFY PASS=False n=1 bad=1")}), exp)[0])
    ok("S11_derive_problem_red", judge(dict(man, derive_problems=["UNMAPPED_ROOT /x/y.py"]), good, exp)[0])
    m = derive()
    ok("S12_real_population_nonempty_and_has_the_pinned_names",
       all(n in m["exp_devices"] for n in ("p9_pull_monthly_funding_zips.py", "d10_build_ledger_ms.py", "d10_stage2_assemble.py"))
       and "durable_write.py" in m["exp_common"])
    ok("S13_real_external_includes_the_executed_nc_code",
       {"/dev/shm/news2_2026-09-23/devices/nc_legs.py", "/dev/shm/news2_2026-09-23/devices/nc_hist_features.py",
        "/dev/shm/nc_2026-09-23/devices/nc_p2_build.py", "/dev/shm/nc_2026-09-23/devices/nc_hist_features.py",
        "/dev/shm/nc_2026-09-23/devices_arm/nc_contract.py"} <= set(m["external"]))
    ok("S14_real_derive_has_no_problems", m["derive_problems"] == [])
    n_ok = sum(r[1] for r in res)
    print("DEPLOY_CHAIN_SELFTEST %d/%d %s" % (n_ok, len(res), "ALL_PASS" if n_ok == len(res) else "RED"))
    return n_ok == len(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp"); ap.add_argument("--out"); ap.add_argument("--sync", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.exp and a.out) or os.path.exists(a.out):
        sys.exit("usage: --exp DIR --out NEW_RECEIPT.json (the receipt must not exist yet)")
    exp = a.exp.rstrip("/")
    man = derive()
    if a.sync:
        sync(exp, man)
    roots = [exp + "/devices"]
    if ssh("test -d %s/common && echo Y || echo N" % exp).stdout.strip() == "Y":
        roots.append(exp + "/common")
    roots += sorted({os.path.dirname(p) for p in man["external"]})
    runs = {}
    for r in roots:
        p = subprocess.run(["bash", TOOL] + tool_args(r, exp), capture_output=True, text=True, timeout=600)
        runs[r] = (p.returncode, p.stdout)
    bad, ext = judge(man, runs, exp)
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    rec = {"argv": vars(a), "python": sys.version.split()[0], "repo_head": head, "exp": exp,
           "device_sha256": sha(os.path.realpath(__file__)), "tool": os.path.relpath(TOOL, REPO), "tool_sha256": sha(TOOL),
           "runbook_sha256": sha(C.RUNBOOK), "manifest": man, "external_status": ext,
           "tool_runs": {r: {"rc": rc, "stdout": out} for r, (rc, out) in runs.items()}, "problems": bad, "PASS": not bad}
    rsha = DW.write_json(a.out, rec, indent=1)
    for b in bad:
        print("  RED", b)
    print("receipt", a.out, rsha)
    print("CHAIN_DEPLOY_VERIFY PASS=%s exp=%s n_exp_devices=%d n_exp_common=%d n_external=%d problems=%d head=%s"
          % (not bad, exp, len(man["exp_devices"]), len(man["exp_common"]), len(man["external"]), len(bad), head[:12]))
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
