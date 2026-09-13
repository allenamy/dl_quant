#!/usr/bin/env python3
"""t7_pull_fill_daily.py — fills whole UTC days missing inside the pulled Binance futures/um indexPriceKlines 1h MONTHLY zips from the DAILY zips
(lead decision 2026-09-13 12:4xZ). FROZEN HERE, BEFORE ANY REQUEST:
- Targets: every (symbol, UTC date) with >= 1 hour missing between the symbol's first and last stored monthly bar (same rule as BINANCE_ARCHIVE_GAPS; expected 979).
- Start gate: refuses to run before 2026-09-13T12:50:00Z (the live executor's 12Z anchor uses this network).
- Rate: host data.binance.vision, at most 2 requests in any rolling 1 s and >= 0.5 s between sends (t7_http2 keep-alive transport, limits overridden here).
- Disk: refuses to start below 3 GiB free; stops cleanly (exit 3, resumable) when free space < 5 GiB.
- Hash rule: every recorded sha256 is computed from the in-memory bytes that are written (never by re-reading a file); a sha256 equal to sha256(empty)
  for a non-empty body aborts the run.
- Storage: <root>/binance_daily/<SYM>/<SYM>-1h-<date>.zip (temp + fsync + atomic rename); manifest <root>/manifest/pages_binance_daily.jsonl (fsync);
  errors <root>/manifest/errors_binance_daily.jsonl; resume skips targets already recorded OK or NOT_FOUND; failures retried once in pass 2.
- Per HTTP 200 daily zip: format = one CSV member, 12 columns, header present or not (recorded), ms open_time, contiguous hours, close_time == open + 3599999,
  24 rows with first/last open == date 00:00 / 23:00 UTC. HTTP 404 => NOT_FOUND (a fact).
- Seams (phase 2, on monthly ∪ filled daily): for every filled day, the hour before 00:00 and the hour after 23:00 must exist in the merged series
  (else NEIGHBOUR_MISSING, recorded); timestamp continuity is exact by construction of hourly opens; price-level continuity
  |ln(open_first / close_prev)| <= ln 1.10 and |ln(close_last / open_next)| <= ln 1.10 (identity/units sanity; only pass/fail is recorded);
  overlap: hours present in BOTH the monthly and the daily file must have identical open/high/low/close strings (mismatch count recorded).
- Output: <root>/derived/binance_filled/<SYM>.npz (open_s, close, source: 0 monthly / 1 daily; monthly wins on overlap), <root>/checks/FILL_DAILY_RECEIPT.json.
No returns are computed."""
import os, sys, json, time, calendar, io, zipfile, csv, hashlib, math, collections, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http2 as H
H.MAX_IN_WINDOW = 2; H.MIN_GAP_S = 0.5
EMPTY = hashlib.sha256(b"").hexdigest()
DEVICE_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()   # the running copy lives in cc_tmp (not iCloud-synced)
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--plan-only", action="store_true"); A = ap.parse_args(); ROOT = A.root
START_GATE = calendar.timegm((2026, 9, 13, 12, 50, 0)); MIN_START = 3 * 1024 ** 3; MIN_RUN = 5 * 1024 ** 3
def free(): st = os.statvfs(ROOT); return st.f_bavail * st.f_frsize
def sha(b):
    d = hashlib.sha256(b).hexdigest()
    if len(b) > 0 and d == EMPTY: raise SystemExit("ABORT: sha256(empty) for a non-empty body")
    return d
def append(p, rec):
    with open(p, "a") as f: f.write(json.dumps(rec) + "\n"); f.flush(); os.fsync(f.fileno())
def atomic_write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + ".tmp.%d" % os.getpid()
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)
def jl(p): return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
def parse_zip(body):
    zf = zipfile.ZipFile(io.BytesIO(body)); names = zf.namelist(); assert len(names) == 1, names
    rows = list(csv.reader(io.StringIO(zf.read(names[0]).decode())))
    header = rows[0] if rows and not rows[0][0].strip().isdigit() else None
    return names[0], header, (rows[1:] if header else rows)
PLAN = json.load(open(ROOT + "/plan/PULL_PLAN_FROZEN.json"))
MAN = ROOT + "/manifest/pages_binance_daily.jsonl"; ERR = ROOT + "/manifest/errors_binance_daily.jsonl"; LOG = ROOT + "/logs/http_binance_daily.jsonl"
# ---- targets (frozen list, written before any request) ----
tp = ROOT + "/plan/FILL_DAILY_TARGETS.json"
if not os.path.exists(tp):
    targets = []
    for b in PLAN["binance"]:
        s = b["symbol"]; p = ROOT + "/derived/binance/%s.npz" % s
        if not os.path.exists(p): continue
        o = np.load(p)["open_s"]; have = set(o.tolist())
        days = sorted({(h // 86400) * 86400 for h in range(int(o.min()), int(o.max()) + 1, 3600) if h not in have})
        targets += [[s, time.strftime("%Y-%m-%d", time.gmtime(d))] for d in days]
    blob = json.dumps({"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rule": "every (symbol, UTC date) with >= 1 missing hour between first and last stored monthly bar",
                       "n_targets": len(targets), "targets": targets}, indent=1).encode()
    atomic_write(tp, blob); open(tp + ".sha256", "w").write(sha(blob) + "  FILL_DAILY_TARGETS.json\n")
T = json.load(open(tp)); assert sha(open(tp, "rb").read()) == open(tp + ".sha256").read().split()[0], "targets sha mismatch"
print("targets", T["n_targets"])
if A.plan_only: sys.exit(0)
# ---- gates ----
now = time.time()
if now < START_GATE: raise SystemExit("REFUSE: before start gate 2026-09-13T12:50:00Z (now %s)" % time.strftime("%H:%M:%SZ", time.gmtime(now)))
if free() < MIN_START: raise SystemExit("REFUSE: free disk %.2f GiB < 3 GiB" % (free() / 1024 ** 3))
RUN = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "_%d" % os.getpid()
done = {(r["symbol"], r["date"]) for r in jl(MAN) if r.get("status") in ("OK", "NOT_FOUND")}
todo = [tuple(t) for t in T["targets"] if tuple(t) not in done]
def fetch(s, d):
    url = "https://data.binance.vision/data/futures/um/daily/indexPriceKlines/%s/1h/%s-1h-%s.zip" % (s, s, d)
    st, hdr, body = H.get(url, LOG, "fill_%s_%s" % (s, d))
    if st == 404:
        append(MAN, {"utc": H.utc_iso(), "run_id": RUN, "symbol": s, "date": d, "status": "NOT_FOUND", "url": url}); return True
    if st != 200:
        append(ERR, {"utc": H.utc_iso(), "run_id": RUN, "symbol": s, "date": d, "url": url, "status": st, "kind": "HTTP_ERROR"}); return False
    try:
        member, header, data = parse_zip(body)
        d0 = calendar.timegm(time.strptime(d, "%Y-%m-%d")) * 1000
        ot = [int(r[0]) for r in data]; ct = [int(r[6]) for r in data]
        fmt = {"member": member, "header": header is not None, "n_cols": sorted({len(r) for r in data}), "n_rows": len(data),
               "ms_units": all(10 ** 12 <= t < 10 ** 13 for t in ot), "contiguous": all(ot[i + 1] - ot[i] == 3600000 for i in range(len(ot) - 1)),
               "close_time_ok": all(c - o == 3599999 for o, c in zip(ot, ct)), "first_is_00": bool(ot) and ot[0] == d0, "last_is_23": bool(ot) and ot[-1] == d0 + 23 * 3600000}
        fmt["format_ok"] = fmt["n_cols"] == [12] and fmt["ms_units"] and fmt["contiguous"] and fmt["close_time_ok"] and fmt["n_rows"] == 24 and fmt["first_is_00"] and fmt["last_is_23"]
    except Exception as e:
        append(ERR, {"utc": H.utc_iso(), "run_id": RUN, "symbol": s, "date": d, "url": url, "status": st, "kind": "BAD_ZIP", "detail": "%s: %s" % (type(e).__name__, e)}); return False
    digest = sha(body); fp = ROOT + "/binance_daily/%s/%s-1h-%s.zip" % (s, s, d); atomic_write(fp, body)
    append(MAN, {"utc": H.utc_iso(), "run_id": RUN, "symbol": s, "date": d, "status": "OK", "url": url, "zip_sha256": digest, "bytes": len(body), "file": os.path.relpath(fp, ROOT), **fmt})
    return True
stopped = None; failed = []
try:
    for k, (s, d) in enumerate(todo):
        if free() < MIN_RUN: stopped = "free disk below 5 GiB"; break
        if not fetch(s, d): failed.append((s, d))
    if not stopped:
        for s, d in failed[:]:
            if free() < MIN_RUN: stopped = "free disk below 5 GiB"; break
            time.sleep(1)
            if fetch(s, d): failed.remove((s, d))
except H.Fatal as e:
    stopped = "FATAL %s" % e
if stopped:
    append(ROOT + "/run/exits_binance_daily.jsonl", {"utc": H.utc_iso(), "run_id": RUN, "exit_code": 3, "stopped": stopped}); sys.exit(3)
# ---- phase 2: merged series, seams, overlap ----
recs = {}
for r in jl(MAN):
    if r.get("status") in ("OK", "NOT_FOUND"): recs[(r["symbol"], r["date"])] = r
bym = collections.defaultdict(list)
for r in jl(ROOT + "/manifest/pages_binance.jsonl"):
    if r.get("status") == "OK": bym[r["symbol"]].append(r)
L125 = math.log(1.10); rows_out = []; C = collections.Counter()
os.makedirs(ROOT + "/derived/binance_filled", exist_ok=True)
tsyms = sorted({t[0] for t in T["targets"]})
for b in PLAN["binance"]:
    s = b["symbol"]; mp = ROOT + "/derived/binance/%s.npz" % s
    if not os.path.exists(mp): continue
    mz = np.load(mp); mon = dict(zip(mz["open_s"].tolist(), mz["close"].tolist())); src = {h: 0 for h in mon}
    merged = dict(mon); ohlc_m = {}
    daily = {}
    for (ss, d), r in recs.items():
        if ss != s or r["status"] != "OK": continue
        body = open(ROOT + "/" + r["file"], "rb").read()
        if hashlib.sha256(body).hexdigest() != r["zip_sha256"]: C["C0_DAILY_ZIP_SHA_MISMATCH"] += 1; continue
        _, _, data = parse_zip(body); daily[d] = data
        for x in data:
            h = int(x[0]) // 1000
            if h in merged: C["overlap_hours"] += 1
            else: merged[h] = float(x[4]); src[h] = 1
    if s in tsyms and daily:
        months_needed = set()   # the filled day's month plus the months of its neighbour hours (a gap on a month's last day needs the next month's first row)
        for d in daily:
            dd0 = calendar.timegm(time.strptime(d, "%Y-%m-%d"))
            months_needed |= {time.strftime("%Y-%m", time.gmtime(dd0 - 3600)), d[:7], time.strftime("%Y-%m", time.gmtime(dd0 + 86400))}
        for r in bym[s]:
            if r["month"] in months_needed:
                _, _, data = parse_zip(open(ROOT + "/" + r["file"], "rb").read())
                for x in data: ohlc_m[int(x[0]) // 1000] = x[1:5]
    for d, data in sorted(daily.items()):
        d0 = calendar.timegm(time.strptime(d, "%Y-%m-%d")); rec = {"symbol": s, "date": d}
        mism = sum(1 for x in data if int(x[0]) // 1000 in ohlc_m and ohlc_m[int(x[0]) // 1000] != x[1:5]); ov = sum(1 for x in data if int(x[0]) // 1000 in ohlc_m)
        rec["overlap_hours"] = ov; rec["overlap_ohlc_mismatch"] = mism
        prev_h, next_h = d0 - 3600, d0 + 86400
        first_open, last_close = float(data[0][1]), float(data[-1][4])
        if prev_h in merged: rec["seam_prev"] = "OK" if abs(math.log(first_open / merged[prev_h])) <= L125 else "PRICE_JUMP"
        else: rec["seam_prev"] = "NEIGHBOUR_MISSING"
        nxt_open = None
        if next_h in merged:
            nxt_open = float(ohlc_m[next_h][0]) if next_h in ohlc_m else None
            if nxt_open is None:
                for dd, dat in daily.items():
                    for x in dat:
                        if int(x[0]) // 1000 == next_h: nxt_open = float(x[1])
            rec["seam_next"] = ("OK" if abs(math.log(last_close / nxt_open)) <= L125 else "PRICE_JUMP") if nxt_open else "NEXT_OPEN_UNAVAILABLE"
        else: rec["seam_next"] = "NEIGHBOUR_MISSING"
        rows_out.append(rec); C["seam_prev_" + rec["seam_prev"]] += 1; C["seam_next_" + rec["seam_next"]] += 1; C["days_with_overlap_mismatch"] += (mism > 0)
    o = np.array(sorted(merged), dtype=np.int64)
    np.savez_compressed(ROOT + "/derived/binance_filled/%s.npz" % s, open_s=o, close=np.array([merged[h] for h in o]), source=np.array([src[h] for h in o], dtype=np.int8))
man = jl(MAN)
fmt = collections.Counter()
for r in recs.values():
    if r["status"] == "OK":
        fmt["format_ok" if r["format_ok"] else "format_fail"] += 1; fmt["header" if r["header"] else "no_header"] += 1
rec = {"device": os.path.basename(__file__), "device_sha256": DEVICE_SHA, "run_id": RUN, "utc_end": H.utc_iso(), "n_targets": T["n_targets"], "targets_sha256": open(tp + ".sha256").read().split()[0],
       "status_counts": dict(collections.Counter(r["status"] for r in recs.values())), "unresolved": ["%s %s" % x for x in failed],
       "format_counts": dict(fmt), "format_fail_list": ["%s %s" % (r["symbol"], r["date"]) for r in recs.values() if r["status"] == "OK" and not r["format_ok"]],
       "seam_and_overlap_counts": dict(C), "seam_failures": [x for x in rows_out if x["seam_prev"] == "PRICE_JUMP" or x["seam_next"] == "PRICE_JUMP" or x["overlap_ohlc_mismatch"]],
       "neighbour_missing": [x for x in rows_out if "NEIGHBOUR_MISSING" in (x["seam_prev"], x["seam_next"])],
       "http_log": os.path.basename(LOG), "rate": {"max_in_window": H.MAX_IN_WINDOW, "min_gap_s": H.MIN_GAP_S}, "free_GiB_end": round(free() / 1024 ** 3, 2)}
blob = json.dumps(rec, indent=1).encode(); atomic_write(ROOT + "/checks/FILL_DAILY_RECEIPT.json", blob)
append(ROOT + "/run/exits_binance_daily.jsonl", {"utc": H.utc_iso(), "run_id": RUN, "exit_code": 0 if not failed else 1, "receipt_sha256": sha(blob), "unresolved": rec["unresolved"]})
print(json.dumps({k: rec[k] for k in ("status_counts", "unresolved", "format_counts", "seam_and_overlap_counts", "free_GiB_end")}, indent=1))
