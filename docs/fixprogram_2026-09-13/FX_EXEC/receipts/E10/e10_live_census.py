"""E10 fact census (READ-ONLY on ~/dl_quant_live/state/live/pilot_log and the research repo ledger_notary/):
per notarized day and file — EXACT (same bytes, same sha) / APPEND (file longer; sha of its first `bytes` bytes == notarized sha) /
PREFIX_CHANGED (longer or equal but prefix sha differs) / TRUNCATED (shorter) / MISSING; files in the day dir the manifest does not list;
for APPEND rows: whether every appended line parses and carries backfilled_utc."""
import json, hashlib, glob, os, collections, sys
N = "/Users/haosiyu/Desktop/quant_research/ledger_notary"; P = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
def prefix_sha(p, n):
    h = hashlib.sha256(); left = n
    with open(p, "rb") as f:
        while left > 0:
            b = f.read(min(1 << 20, left))
            if not b: break
            h.update(b); left -= len(b)
    return h.hexdigest(), n - left
C = collections.Counter(); rows = []
for m in sorted(glob.glob(N + "/manifest_*.json")):
    d = json.load(open(m)); day = d["day"]; dd = os.path.join(P, day)
    listed = set(d["files"]); present = set(os.listdir(dd)) if os.path.isdir(dd) else set()
    for fn, rec in sorted(d["files"].items()):
        p = os.path.join(dd, fn)
        if not os.path.exists(p): st = "MISSING"; extra = None
        else:
            size = os.path.getsize(p); ps, got = prefix_sha(p, rec["bytes"])
            if size < rec["bytes"]: st = "TRUNCATED"
            elif ps != rec["sha256"]: st = "PREFIX_CHANGED"
            elif size == rec["bytes"]: st = "EXACT"
            else: st = "APPEND"
            extra = None
            if st == "APPEND":
                with open(p, "rb") as f:
                    f.seek(rec["bytes"]); tail = f.read()
                lines = [l for l in tail.split(b"\n") if l.strip()]
                ok_nl = tail.endswith(b"\n") and (rec["bytes"] == 0 or open(p, "rb").read()[rec["bytes"] - 1:rec["bytes"]] == b"\n")
                parsed = []; bad = 0
                for l in lines:
                    try: parsed.append(json.loads(l))
                    except Exception: bad += 1
                extra = {"from": rec["bytes"], "to": size, "lines": len(lines), "bad_json": bad, "boundary_newline": ok_nl,
                         "with_backfilled_utc": sum(1 for r in parsed if isinstance(r, dict) and r.get("backfilled_utc")),
                         "backfilled_utc_range": [min((r.get("backfilled_utc") for r in parsed if isinstance(r, dict) and r.get("backfilled_utc")), default=None),
                                                  max((r.get("backfilled_utc") for r in parsed if isinstance(r, dict) and r.get("backfilled_utc")), default=None)]}
        C[st] += 1; rows.append((day, fn, st, extra))
    for fn in sorted(present - listed): C["UNLISTED_FILE"] += 1; rows.append((day, fn, "UNLISTED_FILE", None))
for r in rows:
    if r[2] != "EXACT": print(r)
print("COUNTS", dict(C), "days", len({r[0] for r in rows}))
