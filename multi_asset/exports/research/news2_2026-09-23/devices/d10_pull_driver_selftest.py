#!/usr/bin/env python3
"""d10_pull_driver_selftest.py -- end-to-end red/green controls for d10_pull_months_pod2.sh (news2 class fix, 2026-09-27), run on a
LOCAL file:// fake archive laid out exactly like pod2's $EXP (devices/ common/ symlists/ zips/ logs/). No network.

The defect class under test: a driver that reads the puller's exit code 1 as "checksum mismatch" and DELETES zips in answer. Python
exits 1 for anything that raises before the puller's excepthook exists, so the old drivers would answer an import error by deleting
(or quarantining) files listed in a STALE manifest. Each control below is one way the pipeline can break; the driver must stop,
by name, touching nothing. The same crash control is also run on an offline copy of the old driver (d10_pull_resume_pod2.sh, only
its EXP= and PY= lines replaced, asserted exactly once each) to show what it did.

  DG   good world                                   -> exit 0, last line COMPLETE all_verified=yes, zips VERIFIED
  DG2  run again on the VERIFIED month              -> exit 0, the puller is not invoked (pull log unchanged)
  DM   persistent checksum mismatch                 -> p1 MISMATCH -> repair -> p2 MISMATCH -> NAMED; exit 2, all_verified=no
  DC1  puller dies at import (rc 1, no manifest) over a stale MISMATCH manifest -> exit 1 FAILED, zips and manifest byte-identical
  DC2  puller SIGKILLed                             -> exit 1 FAILED, nothing touched
  DC3  puller exits 0 and writes no manifest        -> exit 1 FAILED
  DC4  month-state device crashes                   -> exit 1 FAILED before any pull
  DC5  verdict device missing                       -> exit 1 FAILED (no anchored P9_VERDICT line is itself FAILED)
  DC6  repair device crashes on a real mismatch     -> exit 1 FAILED, no second pass
  DC7  symbol list missing                          -> exit 1 FAILED
  OLD  the old driver on DC1's world                -> it runs the repair on the stale manifest (expected to FAIL this control)
usage: d10_pull_driver_selftest.py <out.json>
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.realpath(__file__))
COMMON = os.path.join(os.path.dirname(os.path.dirname(HERE)), "common")
DRIVER = os.path.join(HERE, "d10_pull_months_pod2.sh")
OLD_DRIVER = os.path.join(HERE, "d10_pull_resume_pod2.sh")
DEVICES = ["p9_pull_monthly_funding_zips.py", "p9_pull_verdict.py", "d10_month_state.py", "d10_manifest_gate.py",
           "d10_drop_mismatched.py", "d10_pull_months_pod2.sh"]
MONTH = "2026-05"
SYMS = ("AUSDT", "BUSDT")


def mkzip(sym):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(f"{sym}-fundingRate-{MONTH}.csv", "calc_time,funding_interval_hours,last_funding_rate\n1777000000000,8,0.0001\n")
    return b.getvalue()


def world(good=True, symlist=True):
    exp = tempfile.mkdtemp(prefix="p9drv_")
    for d in ("devices", "common", "symlists", "zips", "logs", "arch"):
        os.makedirs(os.path.join(exp, d))
    for n in DEVICES:
        shutil.copy(os.path.join(HERE, n), os.path.join(exp, "devices", n))
    shutil.copy(os.path.join(COMMON, "durable_write.py"), os.path.join(exp, "common", "durable_write.py"))
    for s in SYMS:
        d = os.path.join(exp, "arch", s); os.makedirs(d)
        z = mkzip(s); open(os.path.join(d, f"{s}-fundingRate-{MONTH}.zip"), "wb").write(z)  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
        h = hashlib.sha256(z).hexdigest() if (good or s == "AUSDT") else "0" * 64
        open(os.path.join(d, f"{s}-fundingRate-{MONTH}.zip.CHECKSUM"), "w").write(f"{h}  {s}-fundingRate-{MONTH}.zip\n")  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    if symlist:
        open(os.path.join(exp, "symlists", f"{MONTH}.txt"), "w").write("\n".join(SYMS) + "\n")  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    return exp


def stale(exp):
    """A month left by an earlier run: both zips on disk, and a manifest (no nonce, rev-1 shape) that says BUSDT mismatched."""
    zd = os.path.join(exp, "zips", MONTH); os.makedirs(zd, exist_ok=True)
    files = {}
    for s in SYMS:
        z = mkzip(s); open(os.path.join(zd, f"{s}-fundingRate-{MONTH}.zip"), "wb").write(z)  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
        h = hashlib.sha256(z).hexdigest()
        files[s] = {"status": 200, "sha256": h, "checksum_match": s != "BUSDT"}
    open(os.path.join(zd, f"MANIFEST_{MONTH}.json"), "w").write(json.dumps({"month": MONTH, "files": files}))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test


def snapshot(exp):
    zd = os.path.join(exp, "zips", MONTH)
    out = {}
    for root, _, fs in os.walk(zd):
        for f in fs:
            p = os.path.join(root, f); out[os.path.relpath(p, zd)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def fake_puller(exp, body):
    open(os.path.join(exp, "devices", "p9_pull_monthly_funding_zips.py"), "w").write(body)  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test


def run(exp, driver=None):
    env = dict(os.environ, EXP=exp, PY=sys.executable, P9_BASE="file://" + os.path.join(exp, "arch"))
    env.pop("P9_RUN_NONCE", None)
    drv = driver or os.path.join(exp, "devices", "d10_pull_months_pod2.sh")
    p = subprocess.run(["bash", drv, MONTH], capture_output=True, text=True, env=env, timeout=180)
    log = os.path.join(exp, "logs", "pull_months_pod2.log")
    lines = open(log).read().splitlines() if os.path.exists(log) else []
    return p.returncode, lines, p.stdout + p.stderr


def last(lines):
    return lines[-1] if lines else ""


def has(lines, needle):
    return any(needle in l for l in lines)


def pull_log(exp):
    p = os.path.join(exp, "logs", f"pull_{MONTH}.log")
    return open(p).read() if os.path.exists(p) else None


RES = {}


def rec(name, ok, **kw):
    RES[name] = dict(kw, **{"pass": bool(ok)})


def main():
    outp = sys.argv[1]
    # DG / DG2
    exp = world(); rc, L, _ = run(exp)
    gate = subprocess.run([sys.executable, "-B", os.path.join(exp, "devices", "d10_manifest_gate.py"), os.path.join(exp, "zips", MONTH), MONTH],
                          capture_output=True, text=True).stdout.splitlines()[:1]
    rec("DG_good_world", rc == 0 and " COMPLETE all_verified=yes" in last(L) and gate and gate[0].startswith(f"{MONTH} VERIFIED "),
        rc=rc, last=last(L), gate=gate)
    before = pull_log(exp); rc, L, _ = run(exp)
    rec("DG2_verified_month_not_repulled", rc == 0 and pull_log(exp) == before and has(L, "not re-fetched"), rc=rc, last=last(L))
    # DM
    exp = world(good=False); rc, L, _ = run(exp)
    rec("DM_persistent_mismatch_named", rc == 2 and has(L, "pass=p1") and has(L, "P9_VERDICT MISMATCH") and has(L, "pass=p2")
        and has(L, "NAMED, NOT SKIPPED SILENTLY") and " COMPLETE all_verified=no" in last(L), rc=rc, last=last(L))
    # DC1: import-time crash over a stale MISMATCH manifest
    exp = world(); stale(exp); s0 = snapshot(exp)
    fake_puller(exp, "import no_such_module_p9_selftest\n")
    rc, L, _ = run(exp)
    rec("DC1_import_crash_rc1_touches_nothing", rc == 1 and " FAILED" in last(L) and snapshot(exp) == s0 and not has(L, "repair"),
        rc=rc, last=last(L), zips_unchanged=snapshot(exp) == s0)
    # DC2
    exp = world(); stale(exp); s0 = snapshot(exp)
    fake_puller(exp, "import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n")
    rc, L, _ = run(exp)
    rec("DC2_sigkill_touches_nothing", rc == 1 and " FAILED" in last(L) and snapshot(exp) == s0, rc=rc, last=last(L))
    # DC3
    exp = world(); fake_puller(exp, "import sys\nsys.exit(0)\n"); rc, L, _ = run(exp)
    rec("DC3_rc0_without_manifest_FAILED", rc == 1 and " FAILED" in last(L) and has(L, "no manifest file"), rc=rc, last=last(L))
    # DC4
    exp = world(); open(os.path.join(exp, "devices", "d10_month_state.py"), "w").write("raise RuntimeError('state device broken')\n")  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    rc, L, _ = run(exp)
    rec("DC4_state_device_crash_FAILED_before_pull", rc == 1 and " FAILED" in last(L) and pull_log(exp) is None, rc=rc, last=last(L))
    # DC5
    exp = world(); os.remove(os.path.join(exp, "devices", "p9_pull_verdict.py")); rc, L, _ = run(exp)
    rec("DC5_verdict_device_missing_FAILED", rc == 1 and " FAILED" in last(L), rc=rc, last=last(L))
    # DC6
    exp = world(good=False)
    open(os.path.join(exp, "devices", "d10_drop_mismatched.py"), "w").write("raise RuntimeError('repair device broken')\n")  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    rc, L, _ = run(exp)
    rec("DC6_repair_crash_FAILED_no_second_pass", rc == 1 and " FAILED" in last(L) and not has(L, "pass=p2"), rc=rc, last=last(L))
    # DC7
    exp = world(symlist=False); rc, L, _ = run(exp)
    rec("DC7_missing_symbol_list_FAILED", rc == 1 and " FAILED" in last(L) and pull_log(exp) is None, rc=rc, last=last(L))
    # OLD: the pre-fix driver on DC1's world (offline copy; only EXP= and PY= replaced)
    exp = world(); stale(exp); s0 = snapshot(exp)
    fake_puller(exp, "import no_such_module_p9_selftest\n")
    src = open(OLD_DRIVER).read()
    for a, b in (("EXP=/dev/shm/d10_2026-09-25\n", "EXP=${EXP:?}\n"), ("PY=/workspace/venv/bin/python\n", "PY=${PY:?}\n")):
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    old = os.path.join(exp, "old_driver_offline.sh"); open(old, "w").write(src)  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    env = dict(os.environ, EXP=exp, PY=sys.executable)
    p = subprocess.run(["bash", old], capture_output=True, text=True, env=env, timeout=180)
    ol = open(os.path.join(exp, "logs", "pull_resume_pod2.log")).read().splitlines()
    rec("OLD_driver_same_crash_touches_nothing", snapshot(exp) == s0 and not has(ol, "repairing"), rc=p.returncode,
        repaired=has(ol, "repairing"), zips_unchanged=snapshot(exp) == s0, zips_after=sorted(snapshot(exp)))

    new_ok = all(v["pass"] for k, v in RES.items() if not k.startswith("OLD"))
    sys.path.insert(0, COMMON)
    import durable_write as DW
    body = {"driver": DRIVER, "driver_sha256": hashlib.sha256(open(DRIVER, "rb").read()).hexdigest(),
            "old_driver": OLD_DRIVER, "old_driver_sha256": hashlib.sha256(open(OLD_DRIVER, "rb").read()).hexdigest(),
            "devices_sha256": {n: hashlib.sha256(open(os.path.join(HERE, n), "rb").read()).hexdigest() for n in DEVICES},
            "durable_write_sha256": hashlib.sha256(open(os.path.join(COMMON, "durable_write.py"), "rb").read()).hexdigest(),
            "selftest_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
            "python": sys.version.split()[0], "controls": RES, "ALL_NEW_PASS": new_ok}
    sha = DW.write_json(outp, body, indent=1)
    for k, v in RES.items():
        tag = ("PASS" if v["pass"] else "FAIL") if not k.startswith("OLD") else ("would pass" if v["pass"] else "FAILS this control")
        print(f"  [{tag}] {k} rc={v.get('rc')}")
    print("receipt_sha256", sha)
    print("P9_DRIVER_SELFTEST", "ALL_NEW_PASS" if new_ok else "RED")
    sys.exit(0 if new_ok else 1)


if __name__ == "__main__":
    main()
