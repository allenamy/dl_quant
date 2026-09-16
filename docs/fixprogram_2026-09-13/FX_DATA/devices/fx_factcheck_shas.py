#!/usr/bin/env python3
"""fx_factcheck_shas.py — every file sha cited in FACT_TABLE_DATA.md must match the file (FX-DATA).

Written because I typed a receipt's sha into the fact table before computing it TWICE (`44a03a0c` for the red-test receipt, real
`ba64920e`; `c3b04640` for the guard-control receipt, real `16da7a35`). A correction each time is not a fix for a recurrence, so the
procedure changes: a cited sha is no longer something I assert, it is something this checker verifies. Run it before any commit that
adds a citation, and as part of reviewing the fact table.

It scans for the citation form the table uses -- `name.ext` (`sha16`) -- resolves it under FX_DATA/{receipts,artifacts,devices}
first and then across the research tree and the audit receipts, hashes the file, and requires the cited prefix to match. A citation
whose file cannot be found anywhere is reported, never skipped: an unresolvable citation is an unverified claim, not a pass.

Usage: python3 fx_factcheck_shas.py [fact_table.md]
"""
import hashlib, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(BASE)))
ROOTS = [os.path.join(REPO, "multi_asset", "exports", "research"),
         os.path.join(REPO, "multi_asset", "exports", "research", "common"),
         os.path.join(REPO, "docs", "audit_pipeline_2026-09-13", "devices_data", "receipts"),
         os.path.join(REPO, "docs", "audit_pipeline_2026-09-13", "devices_data")]
DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "FACT_TABLE_DATA.md")
PAT = re.compile(r"`([A-Za-z0-9_./-]+\.(?:json|log|sh|npz|csv|py|md))`\s*\(`([0-9a-f]{8,64})`\)")
s = open(DOC).read()
bad, missing, ambiguous, ok = [], [], [], 0
for m in PAT.finditer(s):
    name, sha = m.group(1), m.group(2)
    hit = None
    for d in ("receipts", "artifacts", "devices", ""):
        f = os.path.join(BASE, d, os.path.basename(name))
        if os.path.isfile(f):
            hit = f; break
    if hit is None:                      # citations to the wider research tree must be VERIFIED too, not merely reported
        for root in ROOTS:
            cand = os.path.join(root, name)
            if os.path.isfile(cand):
                hit = cand; break
        if hit is None:
            # Resolve by PATH SUFFIX, never by basename. A basename fallback found retrain_2026-09/pod_panel_ext.py for the
            # citation second_instrument_rebuild_2026-09-05/patched/pod_panel_ext.py and reported a false MISMATCH against a
            # citation that was correct. A checker that can point at the wrong file would eventually make someone "fix" a
            # right answer, so a non-unique match is AMBIGUOUS and is reported as such, never resolved by guessing.
            base = os.path.basename(name); cands = []
            for root in ROOTS:
                for dirpath, _dn, fn in os.walk(root):
                    if base in fn:
                        full = os.path.join(dirpath, base)
                        if full.endswith(os.sep + name.replace("/", os.sep)) or os.path.basename(name) == name:
                            cands.append(full)
            cands = sorted(set(cands))
            if len(cands) == 1: hit = cands[0]
            elif len(cands) > 1: ambiguous.append({"citation": name, "candidates": cands[:6]}); continue
    if hit is None:
        missing.append(name); continue
    real = hashlib.sha256(open(hit, "rb").read()).hexdigest()
    if real.startswith(sha): ok += 1
    else: bad.append({"citation": name, "cited": sha, "real": real[:len(sha)], "file": hit})
for b in bad: print("MISMATCH %-48s cited %s real %s" % (b["citation"], b["cited"], b["real"]))
for a in ambiguous: print("AMBIGUOUS %-46s matches %d files; a checker must refuse, not guess: %s" % (a["citation"], len(a["candidates"]), a["candidates"][:3]))
for m2 in missing: print("NOT-FOUND %s (a citation whose file is not under FX_DATA is reported, never skipped)" % m2)
print("FACTCHECK verified=%d mismatched=%d ambiguous=%d not_found=%d doc=%s" % (ok, len(bad), len(ambiguous), len(missing), os.path.basename(DOC)))
sys.exit(1 if (bad or ambiguous or missing) else 0)
