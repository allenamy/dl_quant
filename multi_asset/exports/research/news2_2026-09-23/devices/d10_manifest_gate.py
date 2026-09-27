#!/usr/bin/env python3
"""d10_manifest_gate.py -- the one archive-manifest gate every D10 consumer must call.

R25-11 (independent review 7cbe907ba, accepted by lead 2026-09-25): the consumers rejected only entries
whose `checksum_match` was explicitly False. A missing key, or None (the venue served no .CHECKSUM), passed
the gate; and no consumer re-hashed the zips on disk against the manifest, so a file edited or truncated
AFTER the pull would have been read as verified. lead's fix, verbatim:
"checksum_match 必须为 True; 集合相等; 逐个 ZIP 重新哈希."

Three requirements, each reported as its own named failure class so a red gate says WHICH of them failed:

  MISMATCH          a pulled zip's bytes disagreed with the venue's served .CHECKSUM at pull time
  UNVERIFIED        checksum_match is not True (None = no .CHECKSUM served; missing = older manifest)
  SET_MISMATCH      the zips on disk are not exactly the manifest's zip-bearing entries
  REHASH_MISMATCH   a zip on disk no longer hashes to what the manifest recorded

A 404 entry is a symbol the venue has no file for in that month: it is expected NOT to have a zip, so it
is excluded from the disk set (this is the population, not an exemption -- a 404 entry WITH a zip on disk
is a SET_MISMATCH).

Usage as a library:
    from d10_manifest_gate import verify_month, require_verified
    v = verify_month(zipdir, "2026-08")        # -> dict, always; never raises on a red month
    require_verified(zipdir, "2026-08")        # -> dict; SystemExit(2) with the named class if not green

Usage as a device:
    d10_manifest_gate.py <zipdir> <month> [<month> ...]      # print one verdict line per month
    d10_manifest_gate.py --selftest <zipdir> <month>         # baseline green, then 6 mutations, each caught
"""
import hashlib
import json
import os
import sys

ZIP_STATUSES = (200, "exists_not_refetched")  # entries that MUST have a zip on disk
NO_FILE_STATUSES = (404,)                     # entries that must NOT have a zip on disk


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _zips_on_disk(zipdir, month):
    """Enumerate with os.listdir, not glob: a missing directory must throw, and an empty listing of an
    existing directory is a fact we branch on rather than a silent [] (launchd/TCC lesson)."""
    names = os.listdir(zipdir)  # raises FileNotFoundError / NotADirectoryError -- unknown is not green
    suffix = f"-fundingRate-{month}.zip"
    return {n[: -len(suffix)] for n in names if n.endswith(suffix)}


def verify_month(zipdir, month):
    """Return a verdict dict for one month. Never raises for a red month -- the caller decides."""
    v = {"zipdir": os.path.abspath(zipdir), "month": month, "ok": False, "verdict": None,
         "n_entries": 0, "n_zip_entries": 0, "n_404": 0, "n_rehashed": 0,
         "mismatch": [], "unverified": [], "missing_key": [], "on_disk_not_in_manifest": [],
         "in_manifest_not_on_disk": [], "zip_where_404": [], "rehash_mismatch": [], "no_recorded_sha": []}
    mp = os.path.join(zipdir, f"MANIFEST_{month}.json")
    if not os.path.exists(mp):
        v["verdict"] = "ABSENT_MANIFEST"
        return v
    v["manifest_sha256"] = _sha256(mp)
    man = json.load(open(mp))["files"]
    v["n_entries"] = len(man)

    expect_zip, expect_none = set(), set()
    for s, e in man.items():
        st = e.get("status")
        if st in ZIP_STATUSES:
            expect_zip.add(s)
            # (1) checksum_match must be True -- None and a missing key are now their own failure classes
            cm = e.get("checksum_match", "__absent__")
            if cm is False:
                v["mismatch"].append(s)
            elif cm == "__absent__":
                v["missing_key"].append(s)
            elif cm is not True:
                v["unverified"].append(s)
        elif st in NO_FILE_STATUSES:
            expect_none.add(s)
            v["n_404"] += 1
        else:
            v["unverified"].append(s)  # an unrecognised status is not a pass
    v["n_zip_entries"] = len(expect_zip)

    # (2) set equality against the bytes actually present
    disk = _zips_on_disk(zipdir, month)
    v["n_on_disk"] = len(disk)
    v["on_disk_not_in_manifest"] = sorted(disk - expect_zip - expect_none)
    v["in_manifest_not_on_disk"] = sorted(expect_zip - disk)
    v["zip_where_404"] = sorted(disk & expect_none)

    # (3) per-file re-hash of every zip the manifest claims to have verified
    for s in sorted(expect_zip & disk):
        rec = man[s].get("sha256")
        if not rec:
            v["no_recorded_sha"].append(s)
            continue
        got = _sha256(os.path.join(zipdir, f"{s}-fundingRate-{month}.zip"))
        v["n_rehashed"] += 1
        if got != rec:
            v["rehash_mismatch"].append({"symbol": s, "recorded": rec, "now": got})

    if v["mismatch"]:
        v["verdict"] = "MISMATCH"
    elif v["rehash_mismatch"]:
        v["verdict"] = "REHASH_MISMATCH"
    elif v["on_disk_not_in_manifest"] or v["in_manifest_not_on_disk"] or v["zip_where_404"]:
        v["verdict"] = "SET_MISMATCH"
    elif v["unverified"] or v["missing_key"] or v["no_recorded_sha"]:
        v["verdict"] = "UNVERIFIED"
    elif v["n_zip_entries"] == 0:
        v["verdict"] = "NO_ZIPS"  # a month of nothing but 404s is not "verified data"
    else:
        v["verdict"], v["ok"] = "VERIFIED", True
    return v


def summarise(v):
    parts = [f"{v['month']} {v['verdict']}",
             f"entries={v['n_entries']} zip_entries={v['n_zip_entries']} on_disk={v.get('n_on_disk')} "
             f"404={v['n_404']} rehashed={v['n_rehashed']}"]
    for k in ("mismatch", "unverified", "missing_key", "on_disk_not_in_manifest",
              "in_manifest_not_on_disk", "zip_where_404", "no_recorded_sha"):
        if v[k]:
            parts.append(f"{k}={len(v[k])}:{','.join(sorted(v[k])[:6])}")
    if v["rehash_mismatch"]:
        parts.append(f"rehash_mismatch={len(v['rehash_mismatch'])}:"
                     f"{','.join(r['symbol'] for r in v['rehash_mismatch'][:6])}")
    return "  ".join(parts)


def require_verified(zipdir, month, what=""):
    """Gate for a consumer: exit 2, naming the class, unless the month is fully verified."""
    v = verify_month(zipdir, month)
    if not v["ok"]:
        sys.stderr.write(f"ARCHIVE GATE RED ({what or 'consumer'}): {summarise(v)}\n"
                         f"  a red gate is a stop, not a filter: re-pull the named symbols "
                         f"(d10_drop_mismatched.py) or state the month as unaudited.\n")
        raise SystemExit(2)
    return v


def require_verified_months(zipdir, months, what=""):
    return {m: require_verified(zipdir, m, what) for m in months}


# ---------------------------------------------------------------- self-test
def _make_synthetic(root, month="2099-01", n_ok=4, n_404=2):
    """Fabricate a month that is green by construction, so the gate's detection power can be shown
    without the real archive (and without touching pod2). The fixture is built by the SAME hashing
    function the gate uses, which is a real weakness of this control: it cannot catch a wrong hash
    algorithm, only a wrong decision. The real-month --selftest covers that direction."""
    import zipfile as zf
    os.makedirs(root, exist_ok=True)
    files = {}
    for i in range(n_ok):
        s = f"SYN{i}USDT"
        p = os.path.join(root, f"{s}-fundingRate-{month}.zip")
        with zf.ZipFile(p, "w") as z:
            z.writestr(f"{s}-fundingRate-{month}.csv",
                       "calc_time,funding_interval_hours,last_funding_rate\n"
                       f"{1704067200000 + i},8,0.0001\n")
        files[s] = {"status": 200, "checksum_match": True, "sha256": _sha256(p),
                    "checksum_file_sha256_field": _sha256(p)}
    for i in range(n_404):
        files[f"GONE{i}USDT"] = {"status": 404}
    json.dump({"files": files}, open(os.path.join(root, f"MANIFEST_{month}.json"), "w"))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
    return month


def _selftest(zipdir, month):
    """Baseline green FIRST (a green baseline is itself the defect detector: an all-red device proves
    nothing), then each of six mutations must be caught with its own verdict."""
    import shutil
    import tempfile
    base = verify_month(zipdir, month)
    print("baseline:", summarise(base))
    if not base["ok"]:
        print("SELFTEST INCONCLUSIVE: the real month is not green, so a red mutation proves nothing")
        return 1
    tmp = tempfile.mkdtemp(prefix="d10gate_")
    try:
        work = os.path.join(tmp, "zips")
        os.makedirs(work)
        mp = f"MANIFEST_{month}.json"
        shutil.copy(os.path.join(zipdir, mp), os.path.join(work, mp))
        man = json.load(open(os.path.join(work, mp)))["files"]
        syms = sorted(s for s, e in man.items() if e.get("status") in ZIP_STATUSES)
        for s in syms:
            shutil.copy(os.path.join(zipdir, f"{s}-fundingRate-{month}.zip"),
                        os.path.join(work, f"{s}-fundingRate-{month}.zip"))
        copy0 = verify_month(work, month)
        print("copy baseline:", summarise(copy0))
        if not copy0["ok"]:
            print("SELFTEST INCONCLUSIVE: the copy is not green; the copier, not the gate, is wrong")
            return 1
        victim = syms[0]
        vzip = os.path.join(work, f"{victim}-fundingRate-{month}.zip")
        full = json.load(open(os.path.join(work, mp)))

        def restore():
            json.dump(full, open(os.path.join(work, mp), "w"))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test
            shutil.copy(os.path.join(zipdir, f"{victim}-fundingRate-{month}.zip"), vzip)
            for n in os.listdir(work):
                if n.endswith(f"-fundingRate-{month}.zip") and n[: -len(f"-fundingRate-{month}.zip")] not in syms:
                    os.remove(os.path.join(work, n))

        def mutate_flip():
            b = bytearray(open(vzip, "rb").read())
            b[len(b) // 2] ^= 0x01
            open(vzip, "wb").write(bytes(b))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test

        def mutate_delete():
            os.remove(vzip)

        def mutate_stray():
            shutil.copy(vzip, os.path.join(work, f"ZZSTRAYUSDT-fundingRate-{month}.zip"))

        def mutate_none():
            d = json.load(open(os.path.join(work, mp)))
            d["files"][victim]["checksum_match"] = None
            json.dump(d, open(os.path.join(work, mp), "w"))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test

        def mutate_drop_key():
            d = json.load(open(os.path.join(work, mp)))
            d["files"][victim].pop("checksum_match", None)
            json.dump(d, open(os.path.join(work, mp), "w"))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test

        def mutate_drop_sha():
            d = json.load(open(os.path.join(work, mp)))
            d["files"][victim].pop("sha256", None)
            json.dump(d, open(os.path.join(work, mp), "w"))  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test  # durable-exempt: selftest fixture inside a mkdtemp dir, read back by the check under test

        cases = [("byte flipped in a pulled zip", mutate_flip, "REHASH_MISMATCH"),
                 ("a pulled zip deleted", mutate_delete, "SET_MISMATCH"),
                 ("a zip on disk with no manifest entry", mutate_stray, "SET_MISMATCH"),
                 ("checksum_match None (no .CHECKSUM served)", mutate_none, "UNVERIFIED"),
                 ("checksum_match key absent (old manifest)", mutate_drop_key, "UNVERIFIED"),
                 ("no recorded sha256 to re-hash against", mutate_drop_sha, "UNVERIFIED")]
        fails = 0
        for name, fn, want in cases:
            restore()
            fn()
            v = verify_month(work, month)
            ok = (not v["ok"]) and v["verdict"] == want
            fails += 0 if ok else 1
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: want {want}, got {v['verdict']}")
        restore()
        v = verify_month(work, month)
        ok = v["ok"]
        fails += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] restored copy is green again: got {v['verdict']}")
        print(f"SELFTEST {'GREEN' if fails == 0 else 'RED'} {len(cases) + 1 - fails}/{len(cases) + 1}")
        return 0 if fails == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--selftest-synthetic":
        import tempfile as _tf
        _r = _tf.mkdtemp(prefix="d10gate_syn_")
        try:
            _m = _make_synthetic(_r)
            print(f"synthetic fixture in {_r} month {_m}")
            sys.exit(_selftest(_r, _m))
        finally:
            import shutil as _sh
            _sh.rmtree(_r, ignore_errors=True)
    if a and a[0] == "--selftest":
        sys.exit(_selftest(a[1], a[2]))
    if len(a) < 2:
        sys.stderr.write(__doc__)
        sys.exit(64)
    red = 0
    for m in a[1:]:
        v = verify_month(a[0], m)
        red += 0 if v["ok"] else 1
        print(summarise(v))
    print(f"{len(a) - 1} month(s): {len(a) - 1 - red} VERIFIED, {red} not")
    sys.exit(0 if red == 0 else 2)
