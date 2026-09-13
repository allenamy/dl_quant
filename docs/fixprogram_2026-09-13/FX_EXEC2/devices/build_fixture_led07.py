#!/usr/bin/python3
"""FX-EXEC2 LED-07 fixture builder: a KEY PROJECTION of every live anchors.jsonl row (08-01..cutoff) for the
anchor-series accessor suite. Projection keeps only the fields the accessor reads; each output row carries its
provenance (day, 1-based line, sha256 of the verbatim source line). Read-only on a ledger COPY; writes OUT only.
Usage: /usr/bin/python3 build_fixture_led07.py <pilot_log_root_copy> <out_dir> <last_day_inclusive>"""
import gzip, hashlib, json, os, sys
SRC, OUT, LAST = sys.argv[1], sys.argv[2], sys.argv[3]
KEEP_EB = ("nominal_ts", "ok", "sha_ok", "reason")
KEEP = ("anchor_ts", "rebalance_id", "opening_halted", "realized_gross", "target_gross", "book_source",
        "venue_gross_usdt", "net_over_gross")
os.makedirs(OUT, exist_ok=True)
rows, src = [], {}
for day in sorted(d for d in os.listdir(SRC) if d.isdigit() and len(d) == 8 and d <= LAST):
    p = os.path.join(SRC, day, "anchors.jsonl")
    if not os.path.exists(p):
        continue
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        raw_all = f.read()
    assert len(raw_all) == os.stat(p).st_size
    src[day] = hashlib.sha256(raw_all).hexdigest()
    for i, raw in enumerate(raw_all.splitlines(keepends=True)):
        if not raw.strip():
            continue
        r = json.loads(raw)
        out = {k: r[k] for k in KEEP if k in r}
        eb = r.get("external_book")
        if isinstance(eb, dict):
            out["external_book"] = {k: eb[k] for k in KEEP_EB if k in eb}
        elif "external_book" in r:
            out["external_book"] = eb
        out["_prov"] = {"day": day, "line": i + 1, "line_sha256": hashlib.sha256(raw).hexdigest()}
        rows.append(out)
blob = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode()
with gzip.open(os.path.join(OUT, "anchors_projection.jsonl.gz"), "wb", compresslevel=9) as g:
    g.write(blob)
json.dump({"source_root": SRC, "last_day": LAST, "n_rows": len(rows), "projection_keys": list(KEEP),
           "external_book_keys": list(KEEP_EB), "source_file_sha256": src,
           "projection_sha256": hashlib.sha256(blob).hexdigest()},
          open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
print("FIXTURE_LED07", len(rows), hashlib.sha256(blob).hexdigest()[:16])
