#!/usr/bin/env python3
"""p9_pull_verdict.py <rc> <manifest path> <run nonce> <month> -- what did THIS puller run end in? (news2 class fix, 2026-09-27)

The drivers used to branch on the puller's exit code alone: 1 = checksum mismatch -> delete those zips and re-fetch. But 1 is also
what Python exits with when anything raises before the puller's excepthook exists (an import, a syntax error), and 4/137/255 come
from the puller, the kernel and ssh. Rev 1 of the puller fixed the failures it can see; it cannot fix the ones that happen before
it runs. So the exit code is demoted to a consistency check, and the repair signal must be a positive statement written by this run:

  MISMATCH  rc == 1, the manifest carries this run's nonce and month, intended_rc == 1, len(files) == n_symbols > 0,
            and >= 1 entry has checksum_match False                                    -> the driver may drop and re-fetch those
  OK        the same, with rc == 0, intended_rc == 0 and no checksum_match False       -> the driver continues
  FAILED    anything else, named                                                       -> the driver stops; nothing is deleted

Prints exactly one line `P9_VERDICT <OK|MISMATCH|FAILED> ...`, including FAILED for bad arguments or its own crash; the driver
greps that line anchored and treats its absence as FAILED as well.
"""
import json
import os
import sys


def verdict(rc, manifest_path, nonce, month):
    out = {"verdict": "FAILED", "reason": "", "rc": rc, "manifest": manifest_path, "mismatch": []}
    try:
        rc = int(rc)
    except (TypeError, ValueError):
        out["reason"] = "exit code %r is not an integer" % (rc,)
        return out
    if rc not in (0, 1):
        out["reason"] = "puller exit code %d is neither 0 nor 1 (4 = puller failure, 137 = killed, 255 = ssh)" % rc
        return out
    if not os.path.isfile(manifest_path):
        out["reason"] = "no manifest file from this run at %s (a crash before the manifest exits 1 too)" % manifest_path
        return out
    try:
        with open(manifest_path, "rb") as f:
            m = json.loads(f.read().decode())
    except Exception as e:
        out["reason"] = "manifest unreadable: %s: %s" % (type(e).__name__, e)
        return out
    if not isinstance(m, dict) or not isinstance(m.get("files"), dict):
        out["reason"] = "manifest has no files dict"
        return out
    if m.get("run_nonce") != nonce:
        out["reason"] = "manifest run_nonce %r is not this run's %r (stale manifest from an earlier run)" % (m.get("run_nonce"), nonce)
        return out
    if m.get("month") != month:
        out["reason"] = "manifest month %r is not %r" % (m.get("month"), month)
        return out
    if "intended_rc" not in m or m["intended_rc"] != rc:
        out["reason"] = "exit code %d but the manifest says the run ended with %r" % (rc, m.get("intended_rc", "<absent>"))
        return out
    files = m["files"]
    if not files or len(files) != m.get("n_symbols"):
        out["reason"] = "manifest covers %d entries for n_symbols=%r (empty or partial)" % (len(files), m.get("n_symbols"))
        return out
    bad = sorted(s for s, e in files.items() if isinstance(e, dict) and e.get("checksum_match") is False)
    out["mismatch"] = bad
    if rc == 0 and not bad:
        out["verdict"], out["reason"] = "OK", "n=%d" % len(files)
    elif rc == 1 and bad:
        out["verdict"], out["reason"] = "MISMATCH", "n=%d mismatch=%d" % (len(files), len(bad))
    else:
        out["reason"] = "exit code %d with %d mismatching entries is inconsistent" % (rc, len(bad))
    return out


def main():
    try:
        if len(sys.argv) != 5:
            print("P9_VERDICT FAILED reason=usage: p9_pull_verdict.py <rc> <manifest> <nonce> <month> (got %d args)" % (len(sys.argv) - 1))
            return
        v = verdict(*sys.argv[1:5])
        names = ",".join(v["mismatch"][:8])
        print("P9_VERDICT %s rc=%s reason=%s%s" % (v["verdict"], v["rc"], v["reason"], (" names=" + names) if names else ""))
    except BaseException as e:  # the one line must exist even when this device breaks
        print("P9_VERDICT FAILED reason=verdict device crashed: %s: %s" % (type(e).__name__, e))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
