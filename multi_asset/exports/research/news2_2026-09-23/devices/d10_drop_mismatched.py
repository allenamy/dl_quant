#!/usr/bin/env python3
"""d10_drop_mismatched.py <zipdir> <month> [--report-only] -- lead's retry-once-then-name rule.

Deletes ONLY the zips whose served .CHECKSUM disagreed with the bytes we received, so the puller (which
never overwrites an existing file) re-fetches exactly those and nothing else. With --report-only it names
them instead of deleting, which is the second-failure path: "再不符具名列出, 不静默跳过".
"""
import json, os, sys

d, month = sys.argv[1], sys.argv[2]
report_only = "--report-only" in sys.argv
man = json.load(open(os.path.join(d, f"MANIFEST_{month}.json")))["files"]
bad = sorted(s for s, v in man.items() if v.get("checksum_match") is False)
if not bad:
    print(f"no checksum mismatch in {month}"); sys.exit(0)
print(f"{month} checksum mismatch on {len(bad)} symbol(s): {', '.join(bad)}")
for s in bad:
    print(f"   {s}: bytes_sha256={man[s].get('sha256')} served_checksum={man[s].get('checksum_file_sha256_field')}")
if report_only:
    print(f"{month} NAMED, NOT SKIPPED SILENTLY: {len(bad)} symbol(s) still mismatching after one re-fetch")
    sys.exit(0)
for s in bad:
    p = os.path.join(d, f"{s}-fundingRate-{month}.zip")
    if os.path.exists(p):
        os.remove(p); print(f"   removed {p}")
os.remove(os.path.join(d, f"MANIFEST_{month}.json"))
print(f"{month} dropped {len(bad)} zip(s) and the manifest so exactly those are re-fetched")
