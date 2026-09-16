#!/usr/bin/env python3
"""fx_factcheck_shas.py — every file sha cited in FACT_TABLE_DATA.md must match the file (FX-DATA).

Written because I typed a receipt's sha into the fact table before computing it TWICE (`44a03a0c` for the red-test receipt, real
`ba64920e`; `c3b04640` for the guard-control receipt, real `16da7a35`). A correction each time is not a fix for a recurrence, so the
procedure changes: a cited sha is no longer something I assert, it is something this checker verifies. Run it before any commit that
adds a citation, and as part of reviewing the fact table.

It scans for the citation form the table uses -- `name.ext` (`sha16`) -- resolves the basename under FX_DATA/{receipts,artifacts,
devices}, hashes the file, and requires the cited prefix to match. A citation whose file cannot be found is reported, never skipped.

Usage: python3 fx_factcheck_shas.py [fact_table.md]
"""
import hashlib, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "FACT_TABLE_DATA.md")
PAT = re.compile(r"`([A-Za-z0-9_./-]+\.(?:json|log|sh|npz|csv|py|md))`\s*\(`([0-9a-f]{8,64})`\)")
s = open(DOC).read()
bad, missing, ok = [], [], 0
for m in PAT.finditer(s):
    name, sha = m.group(1), m.group(2)
    hit = None
    for d in ("receipts", "artifacts", "devices", ""):
        f = os.path.join(BASE, d, os.path.basename(name))
        if os.path.isfile(f):
            hit = f; break
    if hit is None:
        missing.append(name); continue
    real = hashlib.sha256(open(hit, "rb").read()).hexdigest()
    if real.startswith(sha): ok += 1
    else: bad.append({"citation": name, "cited": sha, "real": real[:len(sha)], "file": hit})
for b in bad: print("MISMATCH %-48s cited %s real %s" % (b["citation"], b["cited"], b["real"]))
for m2 in missing: print("NOT-FOUND %s (a citation whose file is not under FX_DATA is reported, never skipped)" % m2)
print("FACTCHECK verified=%d mismatched=%d not_found=%d doc=%s" % (ok, len(bad), len(missing), os.path.basename(DOC)))
sys.exit(1 if bad else 0)
