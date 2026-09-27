#!/usr/bin/env python3
"""tests_october_chain_contract.py -- the class guard for the two puller defects, over every device the October runbook names
(news2, 2026-09-27).

Fixing the puller alone is instance-shaped: tomorrow's new device writes `json.dump(x, open(p, "w"))` again, and tomorrow's new
driver branches on "exit code 1" again. So the population is derived from the guarded object itself -- every `<name>.py` / `<name>.sh`
the runbook docs/RUNBOOK_october_rebuild_D10_2026-09-27.md mentions that resolves to this devices dir or research/common -- and
three rules are checked on it:

  W  (python) no raw write: open(.., "w"/"a"/"x"/"+"), json.dump, pickle.dump, np.save/savez/savez_compressed, .to_csv/.to_parquet/
     .to_json, Path.write_text/write_bytes (except through durable_write). A line may opt out only with
     `# durable-exempt: <reason of >= 10 chars>` (fixture writes inside a selftest, a space probe that is deleted immediately).
  D  (shell) a script that runs p9_pull_monthly_funding_zips.py must also run p9_pull_verdict.py and set P9_RUN_NONCE.
  H  (every .sh in this dir, named in the runbook or not) the same as D, unless it is one of the four historical pull drivers pinned
     below by sha; those must never be named in the runbook as a step to run. Editing one changes its sha and makes this test red.
  K  known violations: devices that may not be edited outside a deploy (the installed archive job) are listed with their exact count;
     a count going UP is red, a count going DOWN is also red until the pin is lowered (a ratchet, not an allowlist).
Mutation controls run the same scanner on synthetic sources: each defect shape must be flagged, and the clean shapes must not be.
usage: python3 -B tests_october_chain_contract.py [out.json]
"""
import ast, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
RESEARCH = os.path.dirname(os.path.dirname(HERE))
COMMON = os.path.join(RESEARCH, "common")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(RESEARCH)))
RUNBOOK = os.path.join(REPO, "docs", "RUNBOOK_october_rebuild_D10_2026-09-27.md")
MUST_BE_IN_CHAIN = ("p9_pull_monthly_funding_zips.py", "p9_pull_verdict.py", "d10_pull_months_pod2.sh", "durable_write.py",
                    "d10_build_ledger_ms.py", "d10_build_fund_state.py", "d10_stage2_assemble.py", "d10_parity_gate.py")
HISTORICAL_PULL_DRIVERS = {   # sha at the commit that ran them; they branch on "rc == 1" and must not be re-run
    "d10_pull_driver_mac.sh": "34ce3cf57ca658b5257ae95433674ab217633d60a9723463b936200a15554a42",
    "d10_pull_may_to_july.sh": "c4a6772b02aed09f9e70a15aad2759ae7bd1d7c4e9c36f8f810c1466d20dd51c",
    "d10_pull_resume_pod2.sh": "49ee1db511131db1c138bc9fbe92a08e18623882ea390b871515d73a0e3bbe99",
    "d10_census_driver.sh": "ffea260fe076763aaee5bb5e73c52fef3d0845ea7f8fa8aaa4d798e2a7e8c8d2",
}
KNOWN_VIOLATIONS = {
    # installed as ~/funding_ledger_archive/archive_live_ledger.py (sha a71c2a22..., lead 2026-09-26 21:01Z); its writes are durable
    # by its own hand-rolled helper, which this scanner cannot see through. Changing it means a redeploy by lead, not an edit here.
    "archive_live_ledger.py": 6,   # 1 = its own temp/fsync/read-back helper (os.fdopen L139), 5 = its 7b selftest fixtures
}
# lead 2026-09-27 (dry-run plan freeze, decision 1): these receipts must carry argv DERIVED from vars(<parse_args result>) -- never a
# hand-written list -- and the interpreter version.
RECEIPT_ARGV_REQUIRED = ("d10_build_ledger_ms.py", "d10_build_fund_state.py", "d10_parity_gate.py")


def receipt_argv_problems(src):
    """[] if the source assigns X = <..>.parse_args(), and puts "argv": vars(X) and "python": ... into a dict (or rec["argv"] = vars(X))."""
    tree = ast.parse(src)
    parsed = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
              and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "parse_args" for t in n.targets if isinstance(t, ast.Name)}
    def is_vars_of_parsed(v):
        return (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "vars" and len(v.args) == 1
                and isinstance(v.args[0], ast.Name) and v.args[0].id in parsed)
    keys = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value in ("argv", "python"):
                    keys.setdefault(k.value, []).append(v)
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript):
            sl = n.targets[0].slice
            if type(sl).__name__ == "Index":         # Python < 3.9 wraps the key; 3.9+ gives the Constant itself
                sl = sl.value
            if isinstance(sl, ast.Constant) and sl.value in ("argv", "python"):
                keys.setdefault(sl.value, []).append(n.value)
    out = []
    if not parsed:
        out.append("no X = ....parse_args() found")
    if not any(is_vars_of_parsed(v) for v in keys.get("argv", [])):
        out.append("receipt argv is not vars(<parse_args result>)")
    if not keys.get("python"):
        out.append("receipt has no python (interpreter) field")
    return out


def undefined_names(src):
    """Names that are loaded somewhere but bound nowhere in the module (no import, assignment, def/class, argument, loop/with/except
    target, comprehension variable) and are not builtins. Coarse on purpose -- binding anywhere counts -- so it only reports names that
    CANNOT resolve at run time. Added after the dry run hit NameError: DW in two devices whose writes I routed through durable_write
    without inserting the import (d3a7f013d); parse and --help both passed because the name is only reached at the very end."""
    import builtins
    tree = ast.parse(src)
    bound, loaded = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__spec__", "__builtins__"}, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, (ast.Store, ast.Del)):
                bound.add(n.id)
            else:
                loaded.setdefault(n.id, n.lineno)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                bound.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            bound.update(n.names)
    return sorted((ln, nm) for nm, ln in loaded.items() if nm not in bound)


EXEMPT_RE = re.compile(r"#\s*durable-exempt:\s*(.*)$")
WRITE_MODE = re.compile(r"[wax+]")
NP_WRITERS = {"save", "savez", "savez_compressed", "savetxt"}
DF_WRITERS = {"to_csv", "to_parquet", "to_json", "to_pickle", "to_feather"}
DW_NAMES = {"DW", "durable_write"}


def _mode_of(call):
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
        return call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    if len(call.args) >= 2 or any(kw.arg == "mode" for kw in call.keywords):
        return "?"                                       # a computed mode is not provably read-only
    return "r"


def scan_python(src, name="<src>"):
    """Return [(line, what)] of raw writes not opted out with a reasoned durable-exempt comment."""
    lines = src.splitlines()
    out = []
    for node in ast.walk(ast.parse(src, name)):
        if not isinstance(node, ast.Call):
            continue
        f, what = node.func, None
        if isinstance(f, ast.Name) and f.id == "open":
            m = _mode_of(node)
            if m == "?" or WRITE_MODE.search(m):
                what = "open(..., %r)" % m
        elif isinstance(f, ast.Attribute):
            base = f.value.id if isinstance(f.value, ast.Name) else None
            if f.attr == "dump" and base in ("json", "pickle"):
                what = "%s.dump" % base
            elif f.attr in NP_WRITERS and base in ("np", "numpy"):
                what = "np.%s" % f.attr
            elif f.attr in DF_WRITERS:
                what = ".%s" % f.attr
            elif f.attr == "write_text" or (f.attr == "write_bytes" and base not in DW_NAMES):
                what = ".%s" % f.attr
            elif f.attr == "fdopen" and base == "os":
                m = _mode_of(node)
                if m == "?" or WRITE_MODE.search(m):
                    what = "os.fdopen(..., %r)" % m
        if what is None:
            continue
        ln = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
        ex = EXEMPT_RE.search(ln)
        if ex and len(ex.group(1).strip()) >= 10:
            continue
        out.append((node.lineno, what + (" (durable-exempt without a reason)" if ex else "")))
    return sorted(out)


def scan_shell(src):
    """Return the list of rule-D violations for one shell script."""
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    if "p9_pull_monthly_funding_zips.py" not in code:
        return []
    bad = []
    if "p9_pull_verdict.py" not in code:
        bad.append("runs the puller but never asks p9_pull_verdict.py (branches on the exit code)")
    if "P9_RUN_NONCE" not in code:
        bad.append("runs the puller without P9_RUN_NONCE (the verdict cannot tell this run's manifest from a stale one)")
    return bad


def chain_from_runbook():
    text = open(RUNBOOK).read()
    names = sorted(set(re.findall(r"\b([A-Za-z0-9_]+\.(?:py|sh))\b", text)))
    resolved, elsewhere = {}, []
    for n in names:
        for d in (HERE, COMMON):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                resolved[n] = p
                break
        else:
            elsewhere.append(n)
    return text, resolved, elsewhere


RES = []
def cell(n, fn):
    try:
        info = fn(); RES.append((n, True, info if info is not None else ""))
    except AssertionError as e: RES.append((n, False, "assert: %s" % e))
    except Exception as e: RES.append((n, False, "%s: %s" % (type(e).__name__, e)))


def register():
    # ---- mutation controls first: the scanner must see every defect shape and pass the clean ones ----
    MUT_RED = {
        "json_dump_open": 'import json\njson.dump({"a": 1}, open("m.json", "w"))\n',
        "open_w_write": 'open("m.json", "w").write("x")\n',
        "with_open_wb": 'with open(p, "wb") as f:\n    f.write(b)\n',
        "open_mode_kw": 'open(p, mode="a")\n',
        "open_computed_mode": 'open(p, m)\n',
        "np_savez": 'import numpy as np\nnp.savez(p, a=1)\n',
        "np_save": 'import numpy as np\nnp.save(p, a)\n',
        "pickle_dump": 'import pickle\npickle.dump(x, fh)\n',
        "df_to_parquet": 'df.to_parquet(p)\n',
        "path_write_text": 'P(p).write_text("x")\n',
        "path_write_bytes": 'P(p).write_bytes(b"x")\n',
        "os_fdopen_w": 'import os\nos.fdopen(fd, "wb")\n',
        "exempt_without_reason": 'open(p, "w")  # durable-exempt:\n',
        "exempt_short_reason": 'open(p, "w")  # durable-exempt: probe\n',
    }
    MUT_CLEAN = {
        "durable_write_calls": 'import durable_write as DW\nDW.write_json(p, x)\nDW.write_bytes(p, b)\nDW.write_npz(p, a=1)\n',
        "read_opens": 'open(p)\nopen(p, "rb")\nopen(p, mode="r")\njson.load(open(p))\n',
        "reasoned_exempt": 'open(p, "w")  # durable-exempt: selftest fixture in a temp dir, read back by the test itself\n',
    }
    for k, s in MUT_RED.items():
        cell("M_red_%s_flagged" % k, lambda s=s: (lambda v: (v or (_ for _ in ()).throw(AssertionError("not flagged"))) and None)(scan_python(s)))
    for k, s in MUT_CLEAN.items():
        cell("M_clean_%s_not_flagged" % k, lambda s=s: (lambda v: None if not v else (_ for _ in ()).throw(AssertionError(str(v))))(scan_python(s)))

    def m_shell():
        drv = open(os.path.join(HERE, "d10_pull_months_pod2.sh")).read()
        assert scan_shell(drv) == [], scan_shell(drv)
        no_verdict = "\n".join(l for l in drv.splitlines() if "p9_pull_verdict.py" not in l)
        assert any("p9_pull_verdict" in v for v in scan_shell(no_verdict)), "driver without the verdict call not flagged"
        no_nonce = drv.replace("P9_RUN_NONCE", "P9_RUN_ID")
        assert any("P9_RUN_NONCE" in v for v in scan_shell(no_nonce)), "driver without the nonce not flagged"
        commented = "# p9_pull_verdict.py P9_RUN_NONCE\n" + no_verdict
        assert scan_shell(commented), "a comment mentioning the verdict must not satisfy the rule"
        old = open(os.path.join(HERE, "d10_pull_resume_pod2.sh")).read()
        assert scan_shell(old), "the old rc-branching driver must be flagged"
    cell("M_shell_rules_bite", m_shell)

    def m_argv():
        good = 'import argparse, sys\nap = argparse.ArgumentParser()\na = ap.parse_args()\nrec = {"argv": vars(a), "python": sys.version}\n'
        assert receipt_argv_problems(good) == [], receipt_argv_problems(good)
        hand = good.replace('vars(a)', '["--out", a.out]')
        assert receipt_argv_problems(hand), "a hand-written argv list must be flagged"
        other = good.replace('vars(a)', 'vars(b)')
        assert receipt_argv_problems(other), "vars() of something that is not the parse_args result must be flagged"
        nopy = good.replace(', "python": sys.version', '')
        assert receipt_argv_problems(nopy), "missing interpreter field must be flagged"
        sub = 'import argparse, sys\na = argparse.ArgumentParser().parse_args()\nrec = {}\nrec["argv"] = vars(a)\nrec["python"] = sys.version\n'
        assert receipt_argv_problems(sub) == [], receipt_argv_problems(sub)
    cell("M_receipt_argv_rule_bites", m_argv)

    def m_undef():
        assert undefined_names('import json\nprint(DW.write_json("p", {}))\n') == [(2, "DW")], undefined_names('import json\nprint(DW.write_json("p", {}))\n')
        clean = ('import durable_write as DW, os\nfrom x import y as z\ndef f(a, *b, **c):\n    global G\n    G = [i for i in a]\n'
                 '    try:\n        pass\n    except OSError as e:\n        print(e, z, b, c, os, DW, len)\nclass K: pass\nwith open(__file__) as fh: K\n')
        assert undefined_names(clean) == [], undefined_names(clean)
    cell("M_undefined_name_rule_bites", m_undef)


    # ---- the real population ----
    def c_runbook():
        text, resolved, elsewhere = chain_from_runbook()
        missing = [n for n in MUST_BE_IN_CHAIN if n not in resolved]
        assert not missing, "runbook does not name (or they do not resolve): %s" % missing
        return {"n_resolved": len(resolved), "resolved": sorted(resolved), "named_but_outside_lint_scope": elsewhere}
    cell("C0_runbook_population", c_runbook)

    def c_w():
        _, resolved, _ = chain_from_runbook()
        viol = {}
        for n, p in sorted(resolved.items()):
            if n.endswith(".py") and n != "durable_write.py":
                v = scan_python(open(p).read(), p)
                if v:
                    viol[n] = v
        counts = {n: len(v) for n, v in viol.items()}
        new = {n: viol[n] for n in viol if n not in KNOWN_VIOLATIONS}
        assert not new, "raw writes in chain devices: %s" % json.dumps(new)
        for n, pin in KNOWN_VIOLATIONS.items():
            got = counts.get(n, 0)
            if n in resolved:
                assert pin is not None and got == pin, "ratchet: %s has %d raw writes, pin says %r" % (n, got, pin)
        return {"known_violation_counts": {n: counts.get(n, 0) for n in KNOWN_VIOLATIONS}}
    cell("C1_W_no_raw_writes_in_chain", c_w)

    def c_d():
        _, resolved, _ = chain_from_runbook()
        bad = {n: scan_shell(open(p).read()) for n, p in resolved.items() if n.endswith(".sh") and n not in HISTORICAL_PULL_DRIVERS}
        bad = {n: v for n, v in bad.items() if v}
        assert not bad, bad
    cell("C2_D_chain_drivers_use_the_verdict", c_d)

    def c_h():
        text, resolved, _ = chain_from_runbook()
        bad, hist = {}, {}
        for n in sorted(os.listdir(HERE)):
            if not n.endswith(".sh"):
                continue
            v = scan_shell(open(os.path.join(HERE, n)).read())
            if not v:
                continue
            if n in HISTORICAL_PULL_DRIVERS:
                sha = hashlib.sha256(open(os.path.join(HERE, n), "rb").read()).hexdigest()
                pin = HISTORICAL_PULL_DRIVERS[n]
                assert pin is not None and sha == pin, "historical driver %s sha %s != pin %r (edited? then it must adopt the verdict)" % (n, sha, pin)
                for l in text.splitlines():
                    if n in l and not re.search(r"(?i)historical|do not run|不再使用|不要再跑|不得再跑|只作历史", l):
                        raise AssertionError("runbook names historical driver %s outside a do-not-run line: %s" % (n, l.strip()[:120]))
                hist[n] = sha
            else:
                bad[n] = v
        assert not bad, "pull drivers that branch on the exit code: %s" % bad
        assert sorted(hist) == sorted(HISTORICAL_PULL_DRIVERS), "a pinned historical driver no longer matches: %s" % sorted(hist)
        return {"historical_pinned": hist}
    cell("C3_H_every_pull_driver_in_dir", c_h)

    def c_argv():
        bad = {n: receipt_argv_problems(open(os.path.join(HERE, n)).read()) for n in RECEIPT_ARGV_REQUIRED}
        bad = {n: v for n, v in bad.items() if v}
        assert not bad, bad
    cell("C4_receipts_carry_vars_args_and_python", c_argv)

    def c_undef():
        _, resolved, _ = chain_from_runbook()
        bad = {n: undefined_names(open(p).read()) for n, p in resolved.items() if n.endswith(".py")}
        bad = {n: v for n, v in bad.items() if v}
        assert not bad, bad
        return {"n_python_devices_checked": sum(1 for n in resolved if n.endswith(".py"))}
    cell("C5_no_unresolvable_names_in_chain", c_undef)


def main():
    register()
    ok = all(r[1] for r in RES)
    for n, p, m in RES:
        print("  [%s] %s %s" % ("PASS" if p else "FAIL", n, (json.dumps(m)[:300] if not isinstance(m, str) else m)))
    print("OCTOBER_CHAIN_CONTRACT %d/%d %s" % (sum(r[1] for r in RES), len(RES), "ALL_PASS" if ok else "RED"))
    if len(sys.argv) > 1:
        sys.path.insert(0, COMMON)
        import durable_write as DW
        sha = DW.write_json(sys.argv[1], {"runbook": RUNBOOK, "runbook_sha256": hashlib.sha256(open(RUNBOOK, "rb").read()).hexdigest()
                                          if os.path.exists(RUNBOOK) else None,
                                          "tests_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                                          "python": sys.version.split()[0],
                                          "cells": [{"name": n, "pass": p, "info": m} for n, p, m in RES], "ALL_PASS": ok}, indent=1)
        print("receipt_sha256", sha)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
