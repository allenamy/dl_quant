#!/usr/bin/python3
"""FX-EXEC2 LED-01 fixture builder: VERBATIM fills.jsonl lines (byte-identical, in write order) for the fills-contract
suite, from a READ-ONLY ledger copy. Per (day, symbol) every line of that symbol, so every chain is complete:
  20260826 1000RATSUSDT  — O,S,S chains (aggtrades_window_expired terminal row, then import_markout_marks row)
  20260909 0GUSDT        — B26b late ORIGINALS carrying backfilled_utc (crash anchor), then markout supersedes
  20260912 PAXGUSDT      — E1 protective_flatten single original (mark pending) + maker/topup O,S pairs
Usage: /usr/bin/python3 build_fixture_led01.py <pilot_log_root_copy> <out_dir>"""
import gzip, hashlib, json, os, sys
SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
PICK = [("20260826", "1000RATSUSDT"), ("20260909", "0GUSDT"), ("20260912", "PAXGUSDT")]
man = {"source_root": SRC, "extracts": []}
for day, sym in PICK:
    p = os.path.join(SRC, day, "fills.jsonl")
    raw_all = open(p, "rb").read(); assert len(raw_all) == os.stat(p).st_size
    lines, idx = [], []
    for i, raw in enumerate(raw_all.splitlines(keepends=True)):
        if raw.strip() and json.loads(raw).get("symbol") == sym:
            lines.append(raw); idx.append(i + 1)
    blob = b"".join(lines)
    name = f"{day}_{sym}_fills.jsonl.gz"
    with gzip.open(os.path.join(OUT, name), "wb", compresslevel=9) as g:
        g.write(blob)
    man["extracts"].append({"file": name, "day": day, "symbol": sym, "source_file": f"{day}/fills.jsonl",
                            "source_sha256": hashlib.sha256(raw_all).hexdigest(), "n_lines": len(lines),
                            "first_line": idx[0], "last_line": idx[-1], "extract_sha256": hashlib.sha256(blob).hexdigest()})
json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("FIXTURE_LED01", [(e["file"], e["n_lines"], e["extract_sha256"][:16]) for e in man["extracts"]])
