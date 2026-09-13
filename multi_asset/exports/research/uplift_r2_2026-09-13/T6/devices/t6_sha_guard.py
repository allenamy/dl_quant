#!/usr/bin/env python3
"""t6_sha_guard.py -- write/verify a SHA256SUMS file that refuses silent empty reads.
Background (2026-09-13 09:38Z): the Mac data volume was 98 % full; macOS evicted recently written files under ~/Desktop to
'dataless' (APFS flag), and `shasum` read three of them as 0 bytes, recording sha256(empty) = e3b0c442... without any error.
This guard hashes a file only if it is not flagged dataless AND the number of bytes read equals st_size; otherwise it exits 2.
Usage: python3 t6_sha_guard.py write <out_sums> <file>...   |   python3 t6_sha_guard.py check <sums>
"""
import os, sys, stat, hashlib
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def guarded(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE %s: APFS dataless flag set (content not local)" % p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE %s: read %d bytes but st_size %d" % (p, n, st.st_size))
    return h.hexdigest(), n
mode = sys.argv[1]
if mode == "write":
    out, files = sys.argv[2], sys.argv[3:]; lines = []
    for p in files:
        d, n = guarded(p); lines.append("%s  %s" % (d, p))
    open(out, "w").write("\n".join(lines) + "\n"); print("SUMMARY t6_sha_guard write n=%d out=%s" % (len(lines), out))
elif mode == "check":
    bad = 0; n = 0
    for line in open(sys.argv[2]):
        if not line.strip(): continue
        d, p = line.rstrip("\n").split("  ", 1); g, _ = guarded(p); n += 1
        if g != d: bad += 1; print("MISMATCH %s recorded %s got %s" % (p, d[:16], g[:16]))
    print("SUMMARY t6_sha_guard check n=%d mismatches=%d" % (n, bad)); sys.exit(1 if bad else 0)
