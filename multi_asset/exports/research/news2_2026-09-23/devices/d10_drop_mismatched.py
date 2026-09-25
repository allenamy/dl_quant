#!/usr/bin/env python3
"""d10_drop_mismatched.py <zipdir> <month> [--report-only] -- lead's retry-once-then-name rule.

Repairs ONLY what a re-fetch can repair, so the puller (which never overwrites an existing file) re-fetches
exactly those and nothing else. With --report-only it names them instead of repairing, which is the
second-failure path: "再不符具名列出, 不静默跳过".

R25-11 widened what counts as needing repair, and this device had to widen with it: a detector that finds a
class the repair cannot clear leaves the driver re-pulling that month on every run forever (the month never
reaches VERIFIED*). So the classes here are exactly the classes d10_month_state.py reports as not-VERIFIED:

  MISMATCH          bytes disagreed with the served .CHECKSUM at pull time  -> delete the zip, re-fetch
  REHASH_MISMATCH   the zip's bytes changed after the pull                  -> delete the zip, re-fetch
  missing zip       in the manifest, absent on disk                         -> manifest dropped, re-fetch
  stray / 404-zip   on disk with no (or a 404) manifest entry               -> QUARANTINED, not deleted

Strays are moved to <zipdir>/quarantine_<month>/ rather than removed: they are bytes we cannot attribute,
and an unattributable file is evidence, not garbage. Moving them makes the disk set equal the manifest's,
so the month can legitimately go green once the rest is repaired.

An unserved .CHECKSUM (checksum_match None) is NOT in this list: re-fetching cannot produce a checksum the
venue does not publish. Those are named by d10_month_state.py and are red for every consumer.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE

d, month = sys.argv[1], sys.argv[2]
report_only = "--report-only" in sys.argv
v = GATE.verify_month(d, month)

if v["verdict"] == "ABSENT_MANIFEST":
    print(f"no manifest for {month}: nothing to repair, the month simply re-pulls"); sys.exit(0)

delete = sorted(set(v["mismatch"]) | {r["symbol"] for r in v["rehash_mismatch"]})
quarantine = sorted(set(v["on_disk_not_in_manifest"]) | set(v["zip_where_404"]))
missing = list(v["in_manifest_not_on_disk"])
unfixable = sorted(set(v["unverified"]) | set(v["missing_key"]) | set(v["no_recorded_sha"]))

if not (delete or quarantine or missing):
    print(f"{month} nothing a re-fetch can repair (gate verdict {v['verdict']})")
    if unfixable:
        print(f"   {len(unfixable)} zip(s) UNVERIFIABLE (venue served no .CHECKSUM): "
              f"{','.join(unfixable[:8])} -- re-fetching cannot fix this; red for every consumer")
    sys.exit(0)

print(f"{month} gate verdict {v['verdict']}: {len(delete)} to re-fetch, {len(quarantine)} to quarantine, "
      f"{len(missing)} missing on disk")
for s in v["mismatch"]:
    print(f"   MISMATCH {s}: bytes disagreed with the served .CHECKSUM at pull time")
for r in v["rehash_mismatch"]:
    print(f"   REHASH {r['symbol']}: manifest={r['recorded'][:16]}… now={r['now'][:16]}…")
for s in quarantine:
    print(f"   STRAY {s}: on disk with no matching manifest entry")
for s in missing[:8]:
    print(f"   MISSING {s}: in the manifest, not on disk")
if unfixable:
    print(f"   UNVERIFIABLE {len(unfixable)}: {','.join(unfixable[:8])} (no .CHECKSUM served; not repairable)")

if report_only:
    print(f"{month} NAMED, NOT SKIPPED SILENTLY: {len(delete)} still bad after one re-fetch, "
          f"{len(quarantine)} stray, {len(missing)} missing, {len(unfixable)} unverifiable")
    sys.exit(0)

for s in delete:
    p = os.path.join(d, f"{s}-fundingRate-{month}.zip")
    if os.path.exists(p):
        os.remove(p); print(f"   removed {p}")
if quarantine:
    q = os.path.join(d, f"quarantine_{month}")
    os.makedirs(q, exist_ok=True)
    for s in quarantine:
        p = os.path.join(d, f"{s}-fundingRate-{month}.zip")
        if os.path.exists(p):
            shutil.move(p, os.path.join(q, os.path.basename(p))); print(f"   quarantined {p} -> {q}/")
mp = os.path.join(d, f"MANIFEST_{month}.json")
if os.path.exists(mp):
    os.remove(mp)
print(f"{month} repaired: {len(delete)} zip(s) deleted, {len(quarantine)} quarantined, manifest dropped "
      f"so exactly the absent files are re-fetched")
