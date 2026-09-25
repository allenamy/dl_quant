"""dlarch_vendor_news2.py -- copy the news2 files my trainer imports/reads out of volatile /dev/shm
into my own persistent tree, by sha, with a manifest.

WHY (lead ruling 2026-09-25): /dev/shm is volatile and the T0/T3 family's artifacts must not depend on
another agent's shm tree. news2 has frozen it and verified 5/5 shas, but a freeze is a promise about
intent, not a property of the filesystem -- they said themselves they nearly cleared it once under
their own "free it when the run is done" rule, because the dependency was invisible to them.

SCOPE, stated plainly: vendored = the 7 CODE files of the import closure + 2 SMALL data files
(bundle_config.json 20 KB, P1_members_2025H2on.npz 62 KB), ~127 KB total. NOT vendored = the BULK data
(work/NEWS_FEATURES.npz 2.96 GB, work/legs.npz 35 MB, 2 receipt json), which stays referenced in W
because 2.96 GB does not fit my /workspace quota (occupied 1.1 GB, last measured headroom ~1.6 GiB).

The residual exposure is AVAILABILITY, not correctness, and the reason is specific: those bulk files
ARE sha-pinned -- they sit in `inputs`, whose shas are asserted per fold, and NEWT_SHA plus two
receipt cross-checks bind them further. So if W changes or vanishes the run fails LOUDLY; it cannot
silently train on other data. Cost = a re-run, not a wrong result.
I do NOT claim "every input is pinned" as a blanket statement, because until this device ran it was
false: bundle_config.json and P1_members_2025H2on.npz were read at L214/L216 and appeared in NO pinned
list, so a change to them WOULD have been silent. They are vendored and sha-asserted now. The lesson is
that the pinned list and the read list are different lists, and only comparing them shows the gap.

PATH IS PART OF THE IDENTITY: `sources` is {str(path): sha}, so the path is a dict KEY -- vendoring
CHANGES the sources signature, and the resume guard (L260) and merge (L105) both assert
old['sources'] == sources. So a vendored T3 is not resumable from a /dev/shm-era fold, by design, and
the T3 prereg must name this path change and carry a one-cell bitwise comparison (same fold trained
both ways via --out-root, requiring bitwise-identical scores.npz).

usage: dlarch_vendor_news2.py <env-whitelist> <news2-ROOT> <dst-dir> <manifest.json>
"""
import os, sys, json, time, hashlib, shutil

WL = set(sys.argv[1].split(","))
_x = sorted(set(os.environ) - WL)
assert not _x, f"env outside whitelist: {_x}"
SRC, DST, MANIFEST = sys.argv[2], sys.argv[3], sys.argv[4]

# The FULL import closure plus the small data files, as relative paths under the news2 ROOT, mirrored
# into the vendor dir so `sys.path` and every W-relative read change by one prefix only.
#
# HOW THIS LIST WAS BUILT, and why the first attempt was wrong: I first vendored the 5 files that
# dlarch_train_f10.py names in `sources`. That is a PROVENANCE list, not the import closure -- T3 does
# `from book_universe import align, PATH, SHA` and the chain imports `combo_target`, neither of which is
# in `sources`. Removing W/devices from sys.path with only those 5 vendored would have broken T3 at
# import time. The closure below was enumerated by walking `import`/`from` statements transitively from
# dlarch_train_f10.py and dlarch_chain_torch.py and keeping every name that resolves to news2's devices
# dir; book_universe and combo_target import only stdlib/numpy/scipy, so the walk terminates here.
#
# The two data files were NOT sha-pinned anywhere before: they are read at L214/L216 but are absent from
# `inputs`, so a change to them would have been SILENT. Vendoring them and asserting their shas in the
# trainer closes that hole; it is the reason this list is not code-only.
EXPECT = {
    "devices/news2_train_f10.py":        "66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db",
    "devices/f10_observability.py":       "c6399d7ae4948250",
    "devices/nc_hist_features.py":        "3eee6e8842eb86cf",
    "devices/nc_legs.py":                 "18387627f8426a45",
    "devices/nc_p2_build.py":             "671b69e692fb5004",
    "devices/book_universe.py":           "90e332cc27cf8f34aabcac13f9829f84e463ffa900efbe554e17c07436e8dcca",
    "devices/combo_target.py":            "d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544",
    "inputs/bundle_config.json":          "3a8422f377519cac",
    "receipts/P1_members_2025H2on.npz":   "2323623fda933371",
}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


os.makedirs(DST, exist_ok=True)
rows = {}
bad = []
for name, exp in EXPECT.items():
    s = os.path.join(SRC, name)
    d = os.path.join(DST, name)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    if not os.path.exists(s):
        rows[name] = {"status": "SOURCE_MISSING"}
        bad.append(name)
        continue
    src_sha = sha(s)
    if not src_sha.startswith(exp):
        # a prefix mismatch means the source is NOT the file whose sha is pinned in the delivered
        # receipts -- copying it would quietly change what "vendored" means
        rows[name] = {"status": "SOURCE_SHA_MISMATCH", "expected_prefix": exp, "actual": src_sha}
        bad.append(name)
        continue
    shutil.copy2(s, d)
    dst_sha = sha(d)
    # read back and compare BEFORE trusting the copy (E-0925-A: a sha taken from an unverified write
    # certifies damage). shutil.copy2 does not fsync, and a quota-full write can fail silently.
    ok = (dst_sha == src_sha)
    rows[name] = {"status": "OK" if ok else "COPY_SHA_DIFFERS", "sha256": src_sha,
                  "copied_sha256": dst_sha, "bytes": os.path.getsize(d),
                  "src": os.path.abspath(s), "dst": os.path.abspath(d)}
    if not ok:
        bad.append(name)

rec = {"device": "dlarch_vendor_news2.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "src_dir": os.path.abspath(SRC), "dst_dir": os.path.abspath(DST),
       "files": rows, "all_ok": not bad,
       "vendored": "7 code files (the full import closure) + 2 small data files that were previously "
                   "read but pinned NOWHERE (inputs/bundle_config.json, receipts/P1_members_2025H2on.npz). "
                   "NOT vendored: bulk data (work/NEWS_FEATURES.npz 2.96 GB, work/legs.npz 35 MB, 2 receipt "
                   "json) -- those stay in /dev/shm and do not fit the quota, but they ARE sha-pinned via "
                   "`inputs` per fold, so the residual exposure is availability, not correctness.",
       "closure_note": "the 5 files named in `sources` are a PROVENANCE list, not the import closure: "
                       "book_universe and combo_target are imported by T3 and the chain but appear in "
                       "neither, so vendoring only `sources` would have broken T3 at import time.",
       "path_is_part_of_identity": "sources = {str(path): sha}, so vendoring CHANGES the sources "
                                   "signature; the T3 prereg must name this and carry a one-cell "
                                   "bitwise comparison (same fold via --out-root, scores.npz identical)."}
tmp = MANIFEST + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, MANIFEST)
back = json.load(open(MANIFEST))
assert back == rec, "manifest read back differs from what was written"

for n, v in rows.items():
    print("  %-22s %-18s %s" % (n, v["status"], v.get("sha256", "")[:16]))
print("VENDOR_NEWS2 all_ok=%s manifest=%s sha256=%s" % (rec["all_ok"], MANIFEST, sha(MANIFEST)[:16]))
assert not bad, f"vendoring failed for: {bad}"
