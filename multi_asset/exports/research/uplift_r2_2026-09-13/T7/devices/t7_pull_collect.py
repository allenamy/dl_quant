#!/usr/bin/env python3
"""t7_pull_collect.py — copies the SMALL pull artifacts from <root> into the research repo (T7/pull/), never page data or zips.
Copied: plan (frozen plan, amendment, control references, v1 device copies), run (controls, exits, progress, pids, stdout logs), manifest done/errors files,
checks (CHECKS, rows, IDENTITY_GUARD, OFFSET_SPECTRUM, PULL_SUMMARY, MANIFEST_DIGEST), gzip copies of the page manifests if their total gz size <= 8 MiB
(else only their sha256, bytes and line counts, which MANIFEST_DIGEST already carries), and test-root receipts (exits, controls, checks) for the red/green record.
Writes T7/pull/COLLECT_RECEIPT.json with every copied file's source path and sha256 (source == destination asserted)."""
import os, sys, json, hashlib, shutil, gzip, argparse, time
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--tests", nargs="*", default=[]); A = ap.parse_args()
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DST = T7 + "/pull"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": A.root, "files": []}
def cp(src, rel):
    dst = os.path.join(DST, rel); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
    s1, s2 = sha(src), sha(dst); assert s1 == s2, (src, dst); rec["files"].append({"src": src, "dst": os.path.relpath(dst, T7), "sha256": s1, "bytes": os.path.getsize(dst)})
R = A.root
for f in sorted(os.listdir(R + "/plan")): cp(R + "/plan/" + f, "plan/" + f)
for f in sorted(os.listdir(R + "/run")):
    if f.startswith(("controls_", "exits_", "progress_", "pids", "stdout_", "ABORT_")): cp(R + "/run/" + f, "run/" + f)
for f in sorted(os.listdir(R + "/manifest")):
    if f.startswith(("done_", "errors_")): cp(R + "/manifest/" + f, "manifest/" + f)
for f in sorted(os.listdir(R + "/checks")): cp(R + "/checks/" + f, "checks/" + f)
pages = [f for f in sorted(os.listdir(R + "/manifest")) if f.startswith("pages_")]
tmp = {}
for f in pages:
    raw = open(R + "/manifest/" + f, "rb").read(); tmp[f] = gzip.compress(raw, mtime=0)
gz_total = sum(len(b) for b in tmp.values()); rec["page_manifest_gz_total_bytes"] = gz_total
if gz_total <= 8 * 1024 ** 2:
    for f, b in tmp.items():
        dst = DST + "/manifest/" + f + ".gz"; open(dst, "wb").write(b)
        assert gzip.decompress(open(dst, "rb").read()) == open(R + "/manifest/" + f, "rb").read()
        rec["files"].append({"src": R + "/manifest/" + f, "dst": os.path.relpath(dst, T7), "sha256_uncompressed": sha(R + "/manifest/" + f), "sha256": sha(dst), "bytes": len(b)})
    rec["page_manifests"] = "committed as gzip (decompression asserted byte-identical to source)"
else:
    rec["page_manifests"] = "NOT copied (gz total above 8 MiB); sha256/bytes/lines in checks/MANIFEST_DIGEST.json"
for t in A.tests:
    name = os.path.basename(t.rstrip("/"))
    for sub, pref in (("run", ("controls_", "exits_")), ("checks", ("CHECKS_", "IDENTITY_", "OFFSET_")), ("plan", ("PULL_PLAN_FROZEN", "AMENDMENT"))):
        if os.path.isdir(t + "/" + sub):
            for f in sorted(os.listdir(t + "/" + sub)):
                if f.startswith(pref): cp(t + "/" + sub + "/" + f, "tests/%s/%s/%s" % (name, sub, f))
json.dump(rec, open(DST + "/COLLECT_RECEIPT.json", "w"), indent=1)
print("copied", len(rec["files"]), "files; bytes", sum(x["bytes"] for x in rec["files"]), "; page manifests:", rec["page_manifests"], gz_total)
