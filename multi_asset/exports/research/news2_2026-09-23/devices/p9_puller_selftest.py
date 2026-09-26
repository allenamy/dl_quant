#!/usr/bin/env python3
"""p9_puller_selftest.py -- red/green controls for p9_pull_monthly_funding_zips.py rev 1 (lead-approved class fix 2026-09-26), run
against a LOCAL file:// fake archive (P9_BASE) so no network is touched. Each control is also run on the rev-0 file to show what it did.
  G   baseline: two good symbols -> rc 0, manifest parses, both checksum_match True, printed sha == sha of the manifest bytes
  R1  one symbol's .CHECKSUM is wrong -> rc 1 (the drivers' repair signal) and the manifest names it checksum_match False
  R2  the manifest cannot be written (its path is a directory) -> rc 4 (NOT 1), no MANIFEST file, no .tmp left behind
  R3  a crash before any download (symbols file unreadable) -> rc 4 (NOT 1)
usage: p9_puller_selftest.py <rev1.py> <rev0.py> <scratch dir> <out.json>
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


def run(dev, base_url, month, symf, out):
    env = dict(os.environ, P9_BASE=base_url)
    p = subprocess.run([sys.executable, "-B", dev, month, symf, out], capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout + p.stderr


def controls(dev, scratch, tag):
    res = {}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_G_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, symf, out); mp = os.path.join(out, f"MANIFEST_{mo}.json")
    ok = rc == 0 and os.path.exists(mp)
    if ok:
        M = json.load(open(mp)); ok = all(v.get("checksum_match") is True for v in M["files"].values()) and hashlib.sha256(open(mp, "rb").read()).hexdigest() in o
    res["G_baseline"] = {"rc": rc, "pass": bool(ok)}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R1_", dir=scratch); url, symf, mo = world(b, good=False); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, symf, out); mp = os.path.join(out, f"MANIFEST_{mo}.json")
    named = os.path.exists(mp) and json.load(open(mp))["files"]["BUSDT"].get("checksum_match") is False
    res["R1_checksum_mismatch_rc1"] = {"rc": rc, "pass": rc == 1 and named}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R2_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    os.makedirs(os.path.join(out, f"MANIFEST_{mo}.json"))                    # the manifest path is a directory -> write fails
    rc, o = run(dev, url, mo, symf, out)
    left = [n for n in os.listdir(out) if n.endswith(".tmp")]
    res["R2_manifest_write_failure_rc4"] = {"rc": rc, "tmp_left": left, "pass": rc == 4 and os.path.isdir(os.path.join(out, f"MANIFEST_{mo}.json"))}
    b = tempfile.mkdtemp(prefix=f"p9_{tag}_R3_", dir=scratch); url, symf, mo = world(b); out = os.path.join(b, "out")
    rc, o = run(dev, url, mo, os.path.join(b, "no_such_symbols.txt"), out)
    res["R3_crash_rc4"] = {"rc": rc, "pass": rc == 4}
    return res


def main():
    rev1, rev0, scratch, outp = sys.argv[1:5]; os.makedirs(scratch, exist_ok=True)
    # rev 0 hardcodes the https BASE; run it OFFLINE through a copy whose single BASE line reads P9_BASE (asserted exactly one match),
    # otherwise its controls would hit the real archive (my first run of this harness did exactly that: rev-0 G/R1 fetched
    # data.binance.vision and are void -- public archive, no exchange API, but not the fake world the controls are about)
    src0 = open(rev0).read(); line = 'BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"'
    assert src0.count(line) == 1, "rev0 BASE line not found exactly once"
    rev0_off = os.path.join(scratch, "p9_rev0_offline.py")
    open(rev0_off, "w").write(src0.replace(line, 'BASE = os.environ["P9_BASE"]  # selftest-only offline copy'))
    rec = {"rev1": [rev1, hashlib.sha256(open(rev1, "rb").read()).hexdigest()], "rev0": [rev0, hashlib.sha256(open(rev0, "rb").read()).hexdigest()],
           "rev0_offline_copy": [rev0_off, "only the BASE line differs"],
           "rev1_controls": controls(rev1, scratch, "r1"), "rev0_same_shapes": controls(rev0_off, scratch, "r0")}
    rec["ALL_REV1_PASS"] = all(v["pass"] for v in rec["rev1_controls"].values())
    open(outp, "w").write(json.dumps(rec, indent=1))
    for k, v in rec["rev1_controls"].items(): print(f"  rev1 [{'PASS' if v['pass'] else 'FAIL'}] {k} rc={v['rc']}")
    for k, v in rec["rev0_same_shapes"].items(): print(f"  rev0 {k} rc={v['rc']} ({'would pass' if v['pass'] else 'FAILS this control'})")
    print("P9_SELFTEST", "ALL_REV1_PASS" if rec["ALL_REV1_PASS"] else "RED")
    sys.exit(0 if rec["ALL_REV1_PASS"] else 1)


if __name__ == "__main__":
    main()
