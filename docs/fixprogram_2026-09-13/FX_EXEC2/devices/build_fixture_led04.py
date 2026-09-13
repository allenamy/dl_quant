#!/usr/bin/python3
"""FX-EXEC2 LED-04 fixture builder: VERBATIM daily_nav lines (ledger copy) for 20260830, 20260906, 20260911, 20260912
and the VERBATIM amendment-ledger lines (LED04_daily_nav_amendments_20260801_20260912.jsonl) whose row_sha256 matches
one of those daily_nav lines. gzip + MANIFEST with source and extract sha256.
Usage: /usr/bin/python3 build_fixture_led04.py <pilot_log_root_copy> <amendments.jsonl> <out_dir>"""
import gzip, hashlib, json, os, sys
SRC, AMEND, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
DAYS = ["20260830", "20260906", "20260911", "20260912"]
nav_blob, shas = b"", set()
man = {"extracts": []}
for day in DAYS:
    p = os.path.join(SRC, day, "daily_nav.jsonl")
    raw = open(p, "rb").read(); assert len(raw) == os.stat(p).st_size
    lines = [l for l in raw.splitlines(keepends=True) if l.strip()]
    shas |= {hashlib.sha256(l).hexdigest() for l in lines}
    blob = b"".join(lines)
    with gzip.open(os.path.join(OUT, f"{day}_daily_nav.jsonl.gz"), "wb", compresslevel=9) as g:
        g.write(blob)
    man["extracts"].append({"file": f"{day}_daily_nav.jsonl.gz", "source_sha256": hashlib.sha256(raw).hexdigest(),
                            "n_lines": len(lines), "extract_sha256": hashlib.sha256(blob).hexdigest()})
araw = open(AMEND, "rb").read()
alines = [l for l in araw.splitlines(keepends=True) if l.strip() and json.loads(l)["row_sha256"] in shas]
ablob = b"".join(alines)
with gzip.open(os.path.join(OUT, "amendments_subset.jsonl.gz"), "wb", compresslevel=9) as g:
    g.write(ablob)
man["extracts"].append({"file": "amendments_subset.jsonl.gz", "source_sha256": hashlib.sha256(araw).hexdigest(),
                        "n_lines": len(alines), "extract_sha256": hashlib.sha256(ablob).hexdigest()})
json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("FIXTURE_LED04", [(e["file"], e["n_lines"]) for e in man["extracts"]])
