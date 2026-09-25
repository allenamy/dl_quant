#!/usr/bin/env python3
"""d10_verify_existing_zips.py <zipdir> <month> [--dry-run] -- verify zips that were never checked.

Why this exists. The fixed manifest gate (R25-11) immediately found a real, not hypothetical, unverified
population: 376 of 560 zips in 2026-01 carry `status: "exists_not_refetched"` with the file's own sha256
and NO `checksum_match`. The puller's exists-branch (p9_pull_monthly_funding_zips.py L40, sha ed33dfbb)
implemented lead's rule "已存在且 CHECKSUM 核过的 zip 不重取" as "已存在的 zip 不重取" and dropped the
qualifier -- it recorded what the local file hashes to and never asked the venue what it SHOULD hash to.
The pre-fix consumers then read an absent key as verified. 2026-01 is the month that was interrupted at
10:21Z and resumed at 10:37Z, so the resumed pass found 376 files present and skipped verifying all of them.

Why it verifies instead of re-pulling. A re-pull would overwrite the very bytes whose correctness is in
question, so it can only answer "are the bytes right NOW"; this answers "were the bytes we already read
right", which is the question the audits depend on. Only the .CHECKSUM is fetched (a few dozen bytes,
data.binance.vision, no fapi weight, >=0.21s apart).

The manifest is updated in place, and the write is verified by reading it back through the same loader and
comparing -- a receipt's sha must come from the verified write, not from an independent later re-read.
Entries that already have checksum_match are left untouched, so the device is idempotent and never
downgrades a verified entry.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
t_last = [0.0]


def get(url):
    dt = time.time() - t_last[0]
    if dt < 0.21:
        time.sleep(0.21 - dt)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return 200, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return -1, repr(e)[:120].encode()
    finally:
        t_last[0] = time.time()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    zipdir, month = sys.argv[1], sys.argv[2]
    dry = "--dry-run" in sys.argv
    mp = os.path.join(zipdir, f"MANIFEST_{month}.json")
    doc = json.load(open(mp))
    man = doc["files"]

    todo = sorted(s for s, v in man.items()
                  if v.get("status") in (200, "exists_not_refetched") and "checksum_match" not in v)
    already = sum(1 for v in man.values() if v.get("checksum_match") is True)
    print(f"{month}: {len(man)} entries, {already} already verified, {len(todo)} to verify now"
          f"{' (DRY RUN, nothing fetched or written)' if dry else ''}")
    if dry or not todo:
        for s in todo[:10]:
            print(f"   would verify {s}")
        return 0

    out = {"verified_true": [], "MISMATCH": [], "no_checksum_served": [], "zip_absent": [], "fetch_error": []}
    t0 = time.time()
    for i, s in enumerate(todo):
        fn = os.path.join(zipdir, f"{s}-fundingRate-{month}.zip")
        if not os.path.exists(fn):
            out["zip_absent"].append(s)
            man[s]["checksum_match"] = None
            man[s]["verify_note"] = "manifest says present, file absent on disk"
            continue
        h = sha_file(fn)
        code, b = get(f"{BASE}/{s}/{s}-fundingRate-{month}.zip.CHECKSUM")
        field = b.decode(errors="ignore").split()[0] if code == 200 and b else None
        man[s]["sha256"] = h                      # re-hashed here and now, not trusted from before
        man[s]["checksum_file_sha256_field"] = field
        man[s]["checksum_http_status"] = code
        man[s]["verified_without_refetch"] = True
        man[s]["verified_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if field is None:
            man[s]["checksum_match"] = None
            out["no_checksum_served"].append(s) if code == 200 or code == 404 else out["fetch_error"].append((s, code))
        else:
            ok = (field == h)
            man[s]["checksum_match"] = ok
            (out["verified_true"] if ok else out["MISMATCH"]).append(s)
        if i % 50 == 0:
            print(f"   {i}/{len(todo)} {s} match={man[s].get('checksum_match')} {time.time()-t0:.0f}s", flush=True)

    doc.setdefault("verify_passes", []).append(
        {"device": os.path.basename(__file__), "self_sha256": sha_file(os.path.realpath(__file__)),
         "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_attempted": len(todo),
         "n_verified_true": len(out["verified_true"]), "n_mismatch": len(out["MISMATCH"]),
         "n_no_checksum_served": len(out["no_checksum_served"]),
         "n_zip_absent": len(out["zip_absent"]), "n_fetch_error": len(out["fetch_error"]),
         "why": "R25-11 follow-on: the exists-branch never verified these against the venue"})

    tmp = mp + ".part"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, mp)
    # read back through the SAME loader and compare, then report the sha of that verified write
    back = json.load(open(mp))
    assert back == doc, "manifest read-back differs from what was written"
    print(f"\n   verified_true={len(out['verified_true'])}  MISMATCH={len(out['MISMATCH'])}  "
          f"no_checksum_served={len(out['no_checksum_served'])}  zip_absent={len(out['zip_absent'])}  "
          f"fetch_error={len(out['fetch_error'])}")
    for k in ("MISMATCH", "zip_absent", "fetch_error"):
        if out[k]:
            print(f"   {k}: {out[k][:10]}")
    print(f"   manifest rewritten and read back identical; sha256={sha_file(mp)}")
    return 2 if out["MISMATCH"] else 0


if __name__ == "__main__":
    sys.exit(main())
