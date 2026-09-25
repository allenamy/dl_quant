#!/usr/bin/env python3
"""d10_month_state.py <zipdir> <month> -- is this month fetched AND checksum-verified?

lead's rule: "已存在且 CHECKSUM 核过的 zip 不重取". So "done" is not "a manifest exists" -- it is
"every fetched zip has checksum_match TRUE". A `checksum_match` of None means the venue did not serve
the .CHECKSUM file: that zip is NOT verified, and re-fetching cannot fix it, so it is surfaced by name
in the state string rather than quietly counted as verified.
"""
import json, os, sys

d, month = sys.argv[1], sys.argv[2]
mp = os.path.join(d, f"MANIFEST_{month}.json")
if not os.path.exists(mp):
    print("ABSENT"); sys.exit(0)
man = json.load(open(mp))["files"]
got = {s: v for s, v in man.items() if v.get("status") == 200 or v.get("status") == "exists_not_refetched"}
bad = [s for s, v in man.items() if v.get("checksum_match") is False]
unv = [s for s, v in man.items() if v.get("status") == 200 and v.get("checksum_match") is None]
n404 = sum(1 for v in man.values() if v.get("status") == 404)
if bad:
    print(f"MISMATCH n={len(bad)} names={','.join(sorted(bad)[:8])}")
elif unv:
    print(f"VERIFIED_WITH_UNVERIFIED n_zips={len(got)} n_404={n404} unverified={len(unv)} "
          f"names={','.join(sorted(unv)[:8])}")
else:
    print(f"VERIFIED n_zips={len(got)} n_404={n404}")
