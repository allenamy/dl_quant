#!/usr/bin/env python3
"""Re-verify recorded SHA256SUMS lines without trusting silent reads: local file only if NOT dataless and bytes read == st_size; otherwise the committed
git blob (git verifies object integrity on read) with byte count == `git cat-file -s`. Prints one line per entry + a summary. Read-only."""
import os, sys, stat, hashlib, subprocess, json
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
REPO = "/Users/haosiyu/Desktop/quant_research"; BASE = f"{REPO}/multi_asset/exports/research/parity_replay_2026-09-12/phase2"
EMPTY = hashlib.sha256(b"").hexdigest()
out = []; bad = 0; unver = 0
for sums in sys.argv[1:]:
    for line in open(sums):
        if not line.strip() or line.startswith("#"): continue
        d, p = line.rstrip("\n").split("  ", 1)
        ap = os.path.normpath(os.path.join(BASE, p)); rp = os.path.relpath(ap, REPO)
        rec = {"sums": os.path.basename(sums), "path": rp, "recorded16": d[:16], "recorded_is_empty_sha": d == EMPTY}
        st = os.stat(ap)
        if not (st.st_flags & SF_DATALESS):
            h = hashlib.sha256(); n = 0
            with open(ap, "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
            if n == st.st_size and n > 0: rec.update(method="local_guarded", computed16=h.hexdigest()[:16], ok=h.hexdigest() == d)
            else: rec.update(method="local_short_read", n=n, st_size=st.st_size, ok=None)
        else:
            s = subprocess.run(["git", "-C", REPO, "cat-file", "-s", f"HEAD:{rp}"], capture_output=True, text=True)
            if s.returncode == 0:
                size = int(s.stdout.strip()); blob = subprocess.run(["git", "-C", REPO, "cat-file", "-p", f"HEAD:{rp}"], capture_output=True)
                if blob.returncode == 0 and len(blob.stdout) == size and size > 0:
                    g = hashlib.sha256(blob.stdout).hexdigest(); rec.update(method="git_blob(dataless local)", computed16=g[:16], ok=g == d)
                else: rec.update(method="git_blob_failed", err=blob.stderr[-200:].decode(errors="replace"), ok=None)
            else: rec.update(method="dataless_and_untracked(verify on pod2)", ok=None)
        if rec.get("ok") is False or rec["recorded_is_empty_sha"]: bad += 1
        if rec.get("ok") is None: unver += 1
        out.append(rec)
for r in out: print(json.dumps(r))
print(f"SUMMARY entries={len(out)} mismatches_or_empty={bad} unverified_locally={unver}")
