#!/usr/bin/python3
"""FX-EXEC2 LED-02 fixture builder: extract VERBATIM ledger lines (byte-identical) for the protective-flatten
cost reader suite from a READ-ONLY ledger copy. Writes gzip JSONL + a manifest with source-file sha256 and
per-extract sha256 of the exact bytes. No venue, no credentials, no writes outside OUT.
Usage: /usr/bin/python3 build_fixture_led02.py <pilot_log_root_copy> <out_dir>"""
import gzip, hashlib, json, os, sys
SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
BATCHES = [("20260912", "FLATTEN-20260912T124737Z", True), ("20260909", "FLATTEN-20260909T164536Z", True),
           ("20260906", "FLATTEN-20260906T084608Z", False), ("20260805", "FLATTEN-20260805T121829Z", False)]
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b); n += len(b)
    assert n == os.stat(p).st_size, f"short read {p}"
    return h.hexdigest(), n
man = {"source_root": SRC, "extracts": []}
for day, rid, want_fills in BATCHES:
    for table in (("orders", "fills") if want_fills else ("orders",)):
        p = os.path.join(SRC, day, f"{table}.jsonl")
        fsha, fsize = sha_file(p)
        lines, idx = [], []
        with open(p, "rb") as f:
            for i, raw in enumerate(f):
                if not raw.strip():
                    continue
                if json.loads(raw).get("rebalance_id") == rid:
                    lines.append(raw); idx.append(i + 1)
        blob = b"".join(lines)
        name = f"{day}_{rid}_{table}.jsonl.gz"
        with gzip.open(os.path.join(OUT, name), "wb", compresslevel=9) as g:
            g.write(blob)
        man["extracts"].append({"file": name, "day": day, "rebalance_id": rid, "table": table,
                                "source_file": f"{day}/{table}.jsonl", "source_sha256": fsha, "source_bytes": fsize,
                                "n_lines": len(lines), "first_line": idx[0] if idx else None,
                                "last_line": idx[-1] if idx else None, "extract_sha256": sha_bytes(blob)})
json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("FIXTURE_LED02", json.dumps([(e["file"], e["n_lines"], e["extract_sha256"][:16]) for e in man["extracts"]]))
