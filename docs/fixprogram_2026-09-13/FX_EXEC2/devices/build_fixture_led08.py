#!/usr/bin/python3
"""FX-EXEC2 LED-08 fixture builder: VERBATIM ledger lines for the anchor-report builder suite, from a READ-ONLY
ledger copy: anchors rows of 09-12 08Z/12Z and 09-13 04Z/08Z (by external_book.nominal_ts), the order rows of
A1789215839 (09-12 12Z, 4 unknown-fill rows) and of A1785931245 (08-05 12Z, 103 raw-BNB fees). gzip + MANIFEST.
Usage: /usr/bin/python3 build_fixture_led08.py <pilot_log_root_copy> <out_dir>"""
import gzip, hashlib, json, os, sys
SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
man = {"source_root": SRC, "extracts": []}
def take(day, table, pred, name):
    p = os.path.join(SRC, day, f"{table}.jsonl")
    raw_all = open(p, "rb").read(); assert len(raw_all) == os.stat(p).st_size
    lines, idx = [], []
    for i, raw in enumerate(raw_all.splitlines(keepends=True)):
        if raw.strip() and pred(json.loads(raw)):
            lines.append(raw); idx.append(i + 1)
    blob = b"".join(lines)
    with gzip.open(os.path.join(OUT, name), "wb", compresslevel=9) as g:
        g.write(blob)
    man["extracts"].append({"file": name, "source_file": f"{day}/{table}.jsonl",
                            "source_sha256": hashlib.sha256(raw_all).hexdigest(), "lines": idx,
                            "n_lines": len(lines), "extract_sha256": hashlib.sha256(blob).hexdigest()})
nom = lambda ts: (lambda r: isinstance(r.get("external_book"), dict) and r["external_book"].get("nominal_ts") in ts)
take("20260912", "anchors", nom({1789200000, 1789214400}), "20260912_anchors_08Z_12Z.jsonl.gz")
take("20260913", "anchors", nom({1789272000, 1789286400}), "20260913_anchors_04Z_08Z.jsonl.gz")
take("20260912", "orders", lambda r: r.get("rebalance_id") == "A1789215839", "20260912_orders_A1789215839.jsonl.gz")
take("20260805", "orders", lambda r: r.get("rebalance_id") == "A1785931245", "20260805_orders_A1785931245.jsonl.gz")
json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("FIXTURE_LED08", [(e["file"], e["n_lines"], e["extract_sha256"][:16]) for e in man["extracts"]])
