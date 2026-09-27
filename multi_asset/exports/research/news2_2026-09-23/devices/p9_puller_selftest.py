#!/usr/bin/env python3
"""p9_puller_selftest.py -- red/green controls for p9_pull_monthly_funding_zips.py, run against a LOCAL file:// fake archive (P9_BASE)
so no network is touched. Each control is also run on the previous revision to show what it did.
  G   baseline: two good symbols -> rc 0, manifest parses, both checksum_match True, printed sha == sha of the manifest bytes;
      rev 2: the manifest carries this run's P9_RUN_NONCE and intended_rc 0, and the out dir holds exactly the zips + manifest
  R1  one symbol's .CHECKSUM is wrong -> rc 1 (the drivers' repair signal) and the manifest names it checksum_match False;
      rev 2: intended_rc 1
  R2  the manifest cannot be written (its path is a directory) -> rc 4 (NOT 1), no MANIFEST file, no temp left behind
      (rev 1's version of this control never asserted the temp; its receipt listed MANIFEST_2026-05.json.tmp and passed)
  R3  a crash before any download (symbols file unreadable) -> rc 4 (NOT 1)
  R4  rev 2: common/durable_write.py cannot be found -> rc 4 (the excepthook is installed before that import)
  R5  rev 2: no P9_RUN_NONCE in the environment -> the manifest still carries a (generated) nonce, printed on stdout, so a
      driver that forgot to export one gets FAILED from p9_pull_verdict.py rather than a verdict on someone else's manifest
usage: p9_puller_selftest.py <new.py> <previous.py> <scratch dir> <out.json> [--previous-is-rev0]
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, zipfile


def mkzip(sym, month):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(f"{sym}-fundingRate-{month}.csv", "calc_time,funding_interval_hours,last_funding_rate\n1777000000000,8,0.0001\n")
    return b.getvalue()


def world(base, good=True):
    arch = os.path.join(base, "arch"); month = "2026-05"
    for s in ("AUSDT", "BUSDT"):
        d = os.path.join(arch, s); os.makedirs(d, exist_ok=True)
        z = mkzip(s, month); open(os.path.join(d, f"{s}-fundingRate-{month}.zip"), "wb").write(z)
        h = hashlib.sha256(z).hexdigest() if (good or s == "AUSDT") else "0" * 64
        open(os.path.join(d, f"{s}-fundingRate-{month}.zip.CHECKSUM"), "w").write(f"{h}  {s}-fundingRate-{month}.zip\n")
    symf = os.path.join(base, "syms.txt"); open(symf, "w").write("AUSDT\nBUSDT\n")
    return "file://" + arch, symf, month


NONCE = "selftest-nonce-1"


def run(dev, base_url, month, symf, out, nonce=NONCE):
    env = dict(os.environ, P9_BASE=base_url)
    env.pop("P9_RUN_NONCE", None)
    if nonce is not None:
        env["P9_RUN_NONCE"] = nonce
    p = subprocess.run([sys.executable, "-B", dev, month, symf, out], capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout + p.stderr


def controls(dev, scratch, tag):
    res = {}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_G_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, symf, out); mp = os.path.join(out, f"MANIFEST_{mo}.json")
    ok = rc == 0 and os.path.exists(mp)
    extra = sorted(set(os.listdir(out)) - {f"AUSDT-fundingRate-{mo}.zip", f"BUSDT-fundingRate-{mo}.zip", f"MANIFEST_{mo}.json"})
    nonce_ok = False
    if ok:
        M = json.load(open(mp)); ok = all(v.get("checksum_match") is True for v in M["files"].values()) and hashlib.sha256(open(mp, "rb").read()).hexdigest() in o
        nonce_ok = M.get("run_nonce") == NONCE and M.get("intended_rc") == 0
    res["G_baseline"] = {"rc": rc, "pass": bool(ok)}
    res["G_rev2_nonce_intended_rc_and_nothing_else_in_out"] = {"rc": rc, "extra_files": extra, "pass": bool(ok and nonce_ok and not extra)}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R1_", dir=scratch); url, symf, mo = world(b, good=False); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, symf, out); mp = os.path.join(out, f"MANIFEST_{mo}.json")
    named = os.path.exists(mp) and json.load(open(mp))["files"]["BUSDT"].get("checksum_match") is False
    res["R1_checksum_mismatch_rc1"] = {"rc": rc, "pass": rc == 1 and named}
    res["R1_rev2_intended_rc_1"] = {"rc": rc, "pass": bool(named and json.load(open(mp)).get("intended_rc") == 1)}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R2_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    os.makedirs(os.path.join(out, f"MANIFEST_{mo}.json"))                    # the manifest path is a directory -> write fails
    rc, o = run(dev, url, mo, symf, out)
    left = [n for n in os.listdir(out) if n.endswith(".tmp") or n.endswith(".part")]
    res["R2_manifest_write_failure_rc4"] = {"rc": rc, "tmp_left": left,
                                            "pass": rc == 4 and os.path.isdir(os.path.join(out, f"MANIFEST_{mo}.json")) and not left}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R3_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, os.path.join(b, "no_such_symbols.txt"), out)
    res["R3_crash_rc4"] = {"rc": rc, "pass": rc == 4}
    iso = tempfile.mkdtemp(prefix=f"p9_{tag}_R4_iso_")                    # outside the repo: no common/ within two levels
    dev_iso = os.path.join(iso, "devices", os.path.basename(dev)); os.makedirs(os.path.dirname(dev_iso)); shutil.copy(dev, dev_iso)
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R4_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev_iso, url, mo, symf, out)
    res["R4_helper_import_failure_rc4"] = {"rc": rc, "pass": rc == 4}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R5_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, symf, out, nonce=None); mp = os.path.join(out, f"MANIFEST_{mo}.json")
    gen = json.load(open(mp)).get("run_nonce") if os.path.exists(mp) else None
    res["R5_no_env_nonce_generated_and_printed"] = {"rc": rc, "nonce": gen, "pass": bool(rc == 0 and gen and f"P9_RUN_NONCE={gen}" in o)}
    return res


def main():
    new, prev, scratch, outp = sys.argv[1:5]; os.makedirs(scratch, exist_ok=True)
    prev_run = prev
    if "--previous-is-rev0" in sys.argv:
        # rev 0 hardcodes the https BASE; run it OFFLINE through a copy whose single BASE line reads P9_BASE (asserted exactly one
        # match), otherwise its controls would hit the real archive (my first run of this harness did exactly that: rev-0 G/R1
        # fetched data.binance.vision and are void -- public archive, no exchange API, but not the fake world the controls are about)
        src0 = open(prev).read(); line = 'BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"'
        assert src0.count(line) == 1, "rev0 BASE line not found exactly once"
        prev_run = os.path.join(scratch, "p9_rev0_offline.py")
        open(prev_run, "w").write(src0.replace(line, 'BASE = os.environ["P9_BASE"]  # selftest-only offline copy'))
    else:
        # rev >= 1 reads P9_BASE itself; the previous revision is run from a copy placed where it finds the same common/
        prev_run = os.path.join(os.path.dirname(os.path.realpath(new)), "_p9_previous_for_selftest.py")
        shutil.copy(prev, prev_run)
    try:
        rec = {"new": [new, hashlib.sha256(open(new, "rb").read()).hexdigest()],
               "previous": [prev, hashlib.sha256(open(prev, "rb").read()).hexdigest()], "previous_run_as": prev_run,
               "new_controls": controls(new, scratch, "new"), "previous_same_shapes": controls(prev_run, scratch, "prev")}
    finally:
        if prev_run.endswith("_p9_previous_for_selftest.py") and os.path.exists(prev_run):
            os.remove(prev_run)
    rec["ALL_NEW_PASS"] = all(v["pass"] for v in rec["new_controls"].values())
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common"))
    import durable_write as DW
    sha = DW.write_json(outp, rec, indent=1)
    for k, v in rec["new_controls"].items(): print(f"  new [{'PASS' if v['pass'] else 'FAIL'}] {k} rc={v['rc']}")
    for k, v in rec["previous_same_shapes"].items(): print(f"  previous {k} rc={v['rc']} ({'would pass' if v['pass'] else 'FAILS this control'})")
    print("receipt_sha256", sha)
    print("P9_SELFTEST", "ALL_NEW_PASS" if rec["ALL_NEW_PASS"] else "RED")
    sys.exit(0 if rec["ALL_NEW_PASS"] else 1)


if __name__ == "__main__":
    main()
