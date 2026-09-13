#!/usr/bin/env python3
"""t7_s1_perp_klines_pull.py — Binance USDT-perp 1h klines (trade counts) for the frozen S1 tradability rule (PREREG_T7_S1 §11.11: a Binance leg is valid in hour o
only if the perp traded in that hour). The index klines already pulled carry no trades (volume 0; count = ~3600 index updates/hour).
FROZEN HERE, BEFORE ANY REQUEST:
- Scope: futures/um/monthly/klines/<SYM>/1h for exactly the symbol-months of the frozen index pull plan (pull/plan/PULL_PLAN_FROZEN.json 'binance', 10,937),
  then futures/um/daily/klines for every whole or partial UTC day missing between a symbol's first and last stored monthly bar.
- Tradable(sym, hour) := a perp kline exists for that hour AND its `count` (number of trades) > 0. Derived arrays: open_s, count, volume, source (0 monthly, 1 daily).
- Transport/limits: t7_http2 keep-alive; <= 5 requests in any 1 s and >= 0.21 s between sends (host data.binance.vision); the archive path allowlist is extended at
  runtime to futures/um {monthly,daily}/klines only. Pauses while UTC time is in [15:55, 16:50) or [19:55, 20:50) (live executor anchors on this network).
- Disk: refuse to start below 3 GiB free; stop cleanly (exit 3, resumable) below 5 GiB.
- Hash rule: every recorded sha256 is computed from the in-memory bytes written; sha256(empty) for a non-empty body aborts.
- Resume: (symbol, month|date) already recorded OK or NOT_FOUND is skipped; errors retried once in a second pass; HTTP 404 = NOT_FOUND (fact); other statuses = error.
- Per zip: one CSV member, 12 columns, ms open_time, close_time == open + 3599999; contiguity and row count recorded; daily-vs-monthly overlapping hours must be identical rows.
Output: <root>/binance_klines/, <root>/manifest/pages_binance_klines.jsonl, <root>/derived/binance_klines/<SYM>.npz, <root>/checks/PERP_KLINES_RECEIPT.json. No returns are computed."""
import os, sys, json, time, calendar, io, zipfile, csv, hashlib, collections, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http2 as H
H.ALLOW["data.binance.vision"] = ("/data/futures/um/monthly/klines/", "/data/futures/um/daily/klines/")
EMPTY = hashlib.sha256(b"").hexdigest(); DEVICE_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
MIN_START, MIN_RUN = 3 * 1024 ** 3, 5 * 1024 ** 3
def free(): st = os.statvfs(ROOT); return st.f_bavail * st.f_frsize
def sha(b):
    d = hashlib.sha256(b).hexdigest()
    if b and d == EMPTY: raise SystemExit("ABORT sha256(empty) for non-empty body")
    return d
def append(p, r):
    with open(p, "a") as f: f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
def atomic_write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + ".tmp.%d" % os.getpid()
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)
def jl(p): return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
def paused():
    t = time.gmtime(); m = t.tm_hour * 60 + t.tm_min
    return (15 * 60 + 55 <= m < 16 * 60 + 50) or (19 * 60 + 55 <= m < 20 * 60 + 50)
def parse(body):
    zf = zipfile.ZipFile(io.BytesIO(body)); names = zf.namelist(); assert len(names) == 1, names
    rows = list(csv.reader(io.StringIO(zf.read(names[0]).decode())))
    header = rows[0] if rows and not rows[0][0].strip().isdigit() else None
    return names[0], header, (rows[1:] if header else rows)
PLAN = json.load(open(ROOT + "/plan/PULL_PLAN_FROZEN.json"))
MAN = ROOT + "/manifest/pages_binance_klines.jsonl"; ERR = ROOT + "/manifest/errors_binance_klines.jsonl"; LOG = ROOT + "/logs/http_binance_klines.jsonl"
if free() < MIN_START: raise SystemExit("REFUSE: free disk below 3 GiB")
RUN = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "_%d" % os.getpid()
def fetch(kind, sym, key):
    while paused(): time.sleep(30)
    if free() < MIN_RUN: raise KeyboardInterrupt("free disk below 5 GiB")
    url = "https://data.binance.vision/data/futures/um/%s/klines/%s/1h/%s-1h-%s.zip" % (kind, sym, sym, key)
    st, hdr, body = H.get(url, LOG, "%s_%s_%s" % (kind, sym, key))
    if st == 404:
        append(MAN, {"utc": H.utc_iso(), "run_id": RUN, "kind": kind, "symbol": sym, "key": key, "status": "NOT_FOUND", "url": url}); return True
    if st != 200:
        append(ERR, {"utc": H.utc_iso(), "run_id": RUN, "kind": kind, "symbol": sym, "key": key, "url": url, "status": st, "kind_err": "HTTP_ERROR"}); return False
    try:
        member, header, data = parse(body); ot = [int(r[0]) for r in data]; ct = [int(r[6]) for r in data]
        chk = {"member": member, "header": header is not None, "n_rows": len(data), "n_cols": sorted({len(r) for r in data}), "ms_units": all(10 ** 12 <= t < 10 ** 13 for t in ot),
               "contiguous": all(ot[i + 1] - ot[i] == 3600000 for i in range(len(ot) - 1)), "close_time_ok": all(c - o == 3599999 for o, c in zip(ot, ct)),
               "n_zero_count_hours": sum(1 for r in data if int(r[8]) == 0)}
    except Exception as e:
        append(ERR, {"utc": H.utc_iso(), "run_id": RUN, "kind": kind, "symbol": sym, "key": key, "url": url, "status": st, "kind_err": "BAD_ZIP", "detail": "%s: %s" % (type(e).__name__, e)}); return False
    d = sha(body); fp = ROOT + "/binance_klines/%s/%s-1h-%s.zip" % (sym, sym, key); atomic_write(fp, body)
    append(MAN, {"utc": H.utc_iso(), "run_id": RUN, "kind": kind, "symbol": sym, "key": key, "status": "OK", "url": url, "zip_sha256": d, "bytes": len(body), "file": os.path.relpath(fp, ROOT), **chk})
    return True
stopped = None
try:
    have = {(r["kind"], r["symbol"], r["key"]) for r in jl(MAN) if r["status"] in ("OK", "NOT_FOUND")}
    todo = [("monthly", b["symbol"], m) for b in PLAN["binance"] for m in b["months"] if ("monthly", b["symbol"], m) not in have]
    failed = [t for t in todo if not fetch(*t)]
    for t in failed[:]:
        time.sleep(1)
        if fetch(*t): failed.remove(t)
    # daily fills: hours missing between first and last monthly bar
    recs = [r for r in jl(MAN) if r["status"] == "OK" and r["kind"] == "monthly"]
    bysym = collections.defaultdict(set)
    for r in recs:
        _, _, data = parse(open(ROOT + "/" + r["file"], "rb").read())
        for x in data: bysym[r["symbol"]].add(int(x[0]) // 1000)
    daily_targets = []
    for s, hrs in sorted(bysym.items()):
        days = sorted({(h // 86400) * 86400 for h in range(min(hrs), max(hrs) + 1, 3600) if h not in hrs})
        daily_targets += [("daily", s, time.strftime("%Y-%m-%d", time.gmtime(d))) for d in days]
    have = {(r["kind"], r["symbol"], r["key"]) for r in jl(MAN) if r["status"] in ("OK", "NOT_FOUND")}
    dfailed = [t for t in daily_targets if t not in have and not fetch(*t)]
    for t in dfailed[:]:
        time.sleep(1)
        if fetch(*t): dfailed.remove(t)
    failed += dfailed
except KeyboardInterrupt as e:
    stopped = str(e) or "interrupted"
except H.Fatal as e:
    stopped = "FATAL %s" % e
if stopped:
    append(ROOT + "/run/exits_binance_klines.jsonl", {"utc": H.utc_iso(), "run_id": RUN, "exit_code": 3, "stopped": stopped}); sys.exit(3)
# derived arrays + overlap check
os.makedirs(ROOT + "/derived/binance_klines", exist_ok=True)
by = collections.defaultdict(list)
for r in jl(MAN):
    if r["status"] == "OK": by[r["symbol"]].append(r)
C = collections.Counter(); ov_mismatch = []
for s, rs in sorted(by.items()):
    rows = {}; src = {}
    for r in sorted(rs, key=lambda r: (r["kind"] != "monthly", r["key"])):
        body = open(ROOT + "/" + r["file"], "rb").read()
        if hashlib.sha256(body).hexdigest() != r["zip_sha256"]: C["C0_ZIP_SHA_MISMATCH"] += 1; continue
        _, _, data = parse(body)
        for x in data:
            h = int(x[0]) // 1000
            if h in rows:
                C["overlap_hours"] += 1
                if rows[h] != x[:9]: C["overlap_mismatch"] += 1; ov_mismatch.append((s, h))
            else: rows[h] = x[:9]; src[h] = 0 if r["kind"] == "monthly" else 1
    o = np.array(sorted(rows), dtype=np.int64)
    np.savez_compressed(ROOT + "/derived/binance_klines/%s.npz" % s, open_s=o, count=np.array([int(rows[h][8]) for h in o], dtype=np.int64),
                        volume=np.array([float(rows[h][5]) for h in o]), source=np.array([src[h] for h in o], dtype=np.int8))
    C["symbols"] += 1; C["hours"] += len(o); C["zero_count_hours"] += int(sum(1 for h in o if int(rows[h][8]) == 0))
man = jl(MAN); sc = collections.Counter((r["kind"], r["status"]) for r in man)
rec = {"device": os.path.basename(__file__), "device_sha256": DEVICE_SHA, "run_id": RUN, "utc_end": H.utc_iso(),
       "status_counts": {"%s %s" % k: v for k, v in sc.items()}, "unresolved": ["%s %s %s" % t for t in failed], "n_daily_targets": len(daily_targets),
       "derived_counts": dict(C), "overlap_mismatch_examples": ov_mismatch[:20],
       "format_flags": dict(collections.Counter(("no_header" if not r["header"] else "header") for r in man if r["status"] == "OK")),
       "noncontiguous_zips": sum(1 for r in man if r["status"] == "OK" and not r["contiguous"]), "bad_close_time_zips": sum(1 for r in man if r["status"] == "OK" and not r["close_time_ok"]),
       "free_GiB_end": round(free() / 1024 ** 3, 2)}
blob = json.dumps(rec, indent=1).encode(); atomic_write(ROOT + "/checks/PERP_KLINES_RECEIPT.json", blob)
append(ROOT + "/run/exits_binance_klines.jsonl", {"utc": H.utc_iso(), "run_id": RUN, "exit_code": 0 if not failed else 1, "receipt_sha256": sha(blob), "unresolved": rec["unresolved"]})
print(json.dumps({k: rec[k] for k in ("status_counts", "unresolved", "n_daily_targets", "derived_counts", "noncontiguous_zips", "bad_close_time_zips", "free_GiB_end")}, indent=1))
