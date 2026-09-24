"""Upstream artefact manifest, for lead requirement 2: prove the rerun of stats+ext changed nothing upstream.

Per-file sha256 over runs/ (792 files, 4.06 GiB), the four reading receipts and the two targets, plus one
composite digest over the sorted (relpath, size, sha) triples. Run before and after; the composite digests
must be equal. Comparing only the composite would hide WHICH file moved, so the per-file map is kept.

usage: python upstream_manifest.py <out.json>
"""
import hashlib, json, os, sys, time

W = "/dev/shm/news2_2026-09-23"
R = f"{W}/receipts/engine"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


entries = {}
for root, _dirs, files in os.walk(f"{W}/runs"):
    for fn in files:
        p = os.path.join(root, fn)
        entries[os.path.relpath(p, W)] = {"size": os.path.getsize(p), "sha256": sha(p)}
for f in ("BT_P_READING_NEWS2_s42.json", "BT_P_READING_NEWS2_s2027.json",
          "BT_P2_READING_NEWS2_s42.json", "BT_P2_READING_NEWS2_s2027.json"):
    p = os.path.join(R, f)
    entries[os.path.relpath(p, W)] = {"size": os.path.getsize(p), "sha256": sha(p)}
for s in ("42", "2027"):
    p = f"{W}/targets/TARGETS_NEWS2_s{s}.npz"
    entries[os.path.relpath(p, W)] = {"size": os.path.getsize(p), "sha256": sha(p)}

h = hashlib.sha256()
for k in sorted(entries):
    h.update(f"{k}\0{entries[k]['size']}\0{entries[k]['sha256']}\n".encode())
rec = {"receipt": os.path.basename(sys.argv[1]),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "what": "runs/ (every file) + the four R-P reading receipts + the two combo targets",
       "n_files": len(entries),
       "total_bytes": sum(v["size"] for v in entries.values()),
       "composite_digest": h.hexdigest(),
       "entries": entries}
json.dump(rec, open(sys.argv[1], "w"), indent=1)
print(f"  n_files={rec['n_files']} total={rec['total_bytes']/2**30:.3f} GiB "
      f"composite={rec['composite_digest'][:24]}")
