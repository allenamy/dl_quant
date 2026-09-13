#!/usr/bin/env python3
"""t7_pull_summarize.py — file counts, sizes and manifest digests for the commit (data stays in <root>).
Per market-unit digest = sha256 over the manifest body_sha256 values in cursor order (and per Binance symbol over zip_sha256 in month order).
Output <root>/checks/PULL_SUMMARY.json and <root>/checks/MANIFEST_DIGEST.json."""
import os, json, hashlib, argparse, time, collections
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
_pb = open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "rb").read(); assert hashlib.sha256(_pb).hexdigest() == open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256").read().split()[0]
def jl(p): return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
counts = collections.Counter(); sizes = collections.Counter()
for top in ("upbit", "bithumb", "binance", "binance_daily", "manifest", "logs", "run", "plan", "devices", "derived", "checks"):
    base = os.path.join(ROOT, top)
    for dp, dn, fn in os.walk(base):
        for f in fn:
            if ".tmp." in f: counts[top + "_TMP_LEFTOVER"] += 1
            counts[top] += 1; sizes[top] += os.path.getsize(os.path.join(dp, f))
unit_counts = collections.Counter()
for v in ("upbit", "bithumb"):
    for dp, dn, fn in os.walk(os.path.join(ROOT, v)):
        for f in fn: unit_counts["%s/%s" % (v, os.path.basename(dp))] += 1
dig = {"plan_sha256": hashlib.sha256(_pb).hexdigest(), "krw": {}, "binance": {}, "manifest_files_sha256": {}}
for v in ("upbit", "bithumb"):
    by = collections.defaultdict(list)
    for p in jl(ROOT + "/manifest/pages_%s.jsonl" % v):
        if "market" in p: by[(p["market"], p["unit"])].append(p)
    for (mk, u), ps in sorted(by.items()):
        ps.sort(key=lambda p: -p["to_epoch"]); h = hashlib.sha256("".join(p["body_sha256"] for p in ps).encode()).hexdigest()
        dig["krw"]["%s %s %s" % (v, mk, u)] = {"n_pages": len(ps), "n_rows": sum(p["n"] for p in ps), "newest_open": ps[0]["newest_open"], "oldest_open": ps[-1]["oldest_open"], "body_sha_chain_sha256": h}
by = collections.defaultdict(list)
for r in jl(ROOT + "/manifest/pages_binance.jsonl"):
    if "symbol" in r: by[r["symbol"]].append(r)
for s, rs in sorted(by.items()):
    rs.sort(key=lambda r: r["month"]); h = hashlib.sha256("".join(r.get("zip_sha256", "NOT_FOUND") + r["month"] for r in rs).encode()).hexdigest()
    dig["binance"][s] = {"n_months": len(rs), "n_ok": sum(r["status"] == "OK" for r in rs), "n_not_found": sum(r["status"] == "NOT_FOUND" for r in rs), "chain_sha256": h}
for f in sorted(os.listdir(ROOT + "/manifest")): dig["manifest_files_sha256"][f] = {"sha256": fsha(ROOT + "/manifest/" + f), "bytes": os.path.getsize(ROOT + "/manifest/" + f), "lines": sum(1 for _ in open(ROOT + "/manifest/" + f))}
summ = {"run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": ROOT, "file_counts": dict(counts), "bytes": dict(sizes), "total_bytes": sum(sizes.values()),
        "total_GiB": round(sum(sizes.values()) / 1024 ** 3, 3), "page_file_counts_by_venue_unit": dict(unit_counts)}
json.dump(summ, open(ROOT + "/checks/PULL_SUMMARY.json", "w"), indent=1); json.dump(dig, open(ROOT + "/checks/MANIFEST_DIGEST.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
