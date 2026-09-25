#!/usr/bin/env python3
"""d10_month_state.py <zipdir> <month> -- is this month fetched AND checksum-verified?

lead's rule: "已存在且 CHECKSUM 核过的 zip 不重取". So "done" is not "a manifest exists" -- it is
"every fetched zip has checksum_match TRUE", the disk set equals the manifest's, and every zip still
hashes to what was recorded (R25-11).

This is the PULLER'S RESUME device, not a consumer's gate, and the two want different things. The driver
skips a month whose state starts with VERIFIED. So the states are split by WHETHER A RE-FETCH CAN FIX IT:

  ABSENT / MISMATCH / REHASH_MISMATCH / SET_MISMATCH   a re-fetch can fix it -> NOT VERIFIED*, month re-pulled
  VERIFIED_WITH_UNVERIFIED                            the venue served no .CHECKSUM: re-fetching cannot fix
                                                      it, so the driver must NOT loop on it. Named, never
                                                      silently counted as verified.
  VERIFIED                                            green

A consumer MUST NOT reuse this split: for anything that reads the data, VERIFIED_WITH_UNVERIFIED is red.
Consumers call d10_manifest_gate.require_verified(), which accepts only VERIFIED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as GATE

d, month = sys.argv[1], sys.argv[2]
v = GATE.verify_month(d, month)

if v["verdict"] == "ABSENT_MANIFEST":
    print("ABSENT"); sys.exit(0)

n_zips, n404 = v.get("n_on_disk", 0), v["n_404"]

if v["mismatch"]:
    print(f"MISMATCH n={len(v['mismatch'])} names={','.join(sorted(v['mismatch'])[:8])}")
elif v["rehash_mismatch"]:
    names = ",".join(r["symbol"] for r in v["rehash_mismatch"][:8])
    print(f"REHASH_MISMATCH n={len(v['rehash_mismatch'])} names={names} "
          f"(bytes changed after the pull; the served CHECKSUM no longer certifies them)")
elif v["in_manifest_not_on_disk"] or v["on_disk_not_in_manifest"] or v["zip_where_404"]:
    print(f"SET_MISMATCH missing={len(v['in_manifest_not_on_disk'])} "
          f"stray={len(v['on_disk_not_in_manifest'])} zip_where_404={len(v['zip_where_404'])} "
          f"names={','.join((v['in_manifest_not_on_disk'] + v['on_disk_not_in_manifest'] + v['zip_where_404'])[:8])}")
elif v["unverified"] or v["missing_key"] or v["no_recorded_sha"]:
    unv = sorted(set(v["unverified"]) | set(v["missing_key"]) | set(v["no_recorded_sha"]))
    print(f"VERIFIED_WITH_UNVERIFIED n_zips={n_zips} n_404={n404} rehashed={v['n_rehashed']} "
          f"unverified={len(unv)} names={','.join(unv[:8])}")
elif v["verdict"] == "NO_ZIPS":
    print(f"NO_ZIPS n_404={n404} (manifest has entries but no file-bearing month)")
elif v["ok"]:
    print(f"VERIFIED n_zips={n_zips} n_404={n404} rehashed={v['n_rehashed']}")
else:
    print(f"NOT_VERIFIED verdict={v['verdict']}")  # never silently green on an unforeseen class
