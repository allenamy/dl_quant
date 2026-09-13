#!/usr/bin/env python3
"""t7_pull.py — T7 full-pull worker, one process per host (--venue upbit | bithumb | binance). Rules: <root>/plan/PULL_PLAN_FROZEN.json (sha-checked).
Durability: page body written gzip (mtime 0) to a temp file, fsync, os.replace (atomic); THEN the manifest line is appended with fsync.
A crash between the two leaves a page file without a manifest line; the resume re-requests that cursor and compares body sha (a different body = REVISION error).
Resume: per (market, unit) the cursor is min oldest_open over accepted manifest pages; DONE records are never re-pulled.
Exit codes: 0 all done; 1 some market-unit / zip unresolved after pass 2; 2 control failure; 3 stopped (test interruption or free disk below minimum); 4 crash.
No return values are computed here."""
import sys, os, json, time, gzip, hashlib, calendar, argparse, io, zipfile, csv, urllib.parse, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http2 as H
ap = argparse.ArgumentParser(); ap.add_argument("--venue", required=True, choices=["upbit", "bithumb", "binance"]); ap.add_argument("--root", required=True)
ap.add_argument("--max-requests", type=int, default=0, help="test only: simulated interruption after N data requests"); A = ap.parse_args()
ROOT, V = A.root, A.venue
PLAN_P = ROOT + "/plan/PULL_PLAN_FROZEN.json"; _pb = open(PLAN_P, "rb").read()
assert hashlib.sha256(_pb).hexdigest() == open(PLAN_P + ".sha256").read().split()[0], "PLAN SHA MISMATCH"
PLAN = json.loads(_pb)
for d in ("manifest", "logs", "run"): os.makedirs(ROOT + "/" + d, exist_ok=True)
def ensure_newline_tail(path):   # AMENDMENT 1: a worker killed mid-append can leave a torn last line; terminate it so the next append cannot fuse with it
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            f.seek(-1, 2); last = f.read(1)
        if last != b"\n":
            with open(path, "ab") as f: f.write(b"\n"); f.flush(); os.fsync(f.fileno())
            return True
    return False
RUN_ID = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "_%d" % os.getpid()
LOG, MAN, ERR, DONE = (ROOT + "/logs/http_%s.jsonl" % V, ROOT + "/manifest/pages_%s.jsonl" % V, ROOT + "/manifest/errors_%s.jsonl" % V, ROOT + "/manifest/done_%s.jsonl" % V)
PROG = ROOT + "/run/progress_%s.json" % V
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}
PULL_END, CUTOFF = PLAN["pull_end_epoch"], PLAN["cutoff_epoch"]
STATE = {"n_data_requests": 0, "t0": time.time(), "units_done_this_run": 0, "errors_this_run": 0}
TORN_REPAIRED = [os.path.basename(p) for p in (LOG, MAN, ERR, DONE, ROOT + "/run/controls_%s.jsonl" % V, ROOT + "/run/exits_%s.jsonl" % V) if ensure_newline_tail(p)]
class Stop(Exception): pass
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def sha(b): return hashlib.sha256(b).hexdigest()
def to_param(t): return urllib.parse.quote(iso(t) + "Z") if V == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
def parse(body):
    try: return json.loads(body.decode("utf-8"))
    except Exception: return None
def append(path, rec):
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())
def atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True); tmp = path + ".tmp.%d" % os.getpid()
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
def gz(body):
    bio = io.BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", mtime=0) as g: g.write(body)
    return bio.getvalue()
def read_jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except json.JSONDecodeError: pass   # torn last line after a crash: its page is re-fetched and re-verified
    return out
def free_ok():
    st = os.statvfs(ROOT); return st.f_bavail * st.f_frsize >= PLAN["min_free_bytes"]
def progress(**kw):
    atomic_write(PROG, json.dumps({"utc": H.utc_iso(), "run_id": RUN_ID, "pid": os.getpid(), "venue": V, "n_data_requests": STATE["n_data_requests"],
                                   "elapsed_s": round(time.time() - STATE["t0"], 1), "units_done_this_run": STATE["units_done_this_run"],
                                   "errors_this_run": STATE["errors_this_run"], **kw}).encode())
def err(rec):
    STATE["errors_this_run"] += 1; append(ERR, {"utc": H.utc_iso(), "run_id": RUN_ID, "venue": V, **rec})
def data_get(url, tag):
    if A.max_requests and STATE["n_data_requests"] >= A.max_requests: raise Stop("max-requests reached (simulated interruption)")
    if not free_ok(): raise Stop("free disk below plan minimum")
    if os.path.exists(ROOT + "/run/STOP_%s" % V): raise Stop("STOP file present (graceful stop)")   # AMENDMENT 1
    STATE["n_data_requests"] += 1
    return H.get(url, LOG, tag)
# ---------------- controls ----------------
def controls_krw():
    b = BASE[V]; out = {}
    T = calendar.timegm((2026, 9, 1, 0, 0, 0))
    st, _, body = H.get("%s/v1/candles/minutes/60?market=KRW-BTC&count=200&to=%s" % (b, to_param(T)), LOG, "control_pos")
    js = parse(body)
    pos = {"status": st, "n": len(js) if isinstance(js, list) else None, "newest": js[0]["candle_date_time_utc"] if isinstance(js, list) and js else None, "body_sha256": sha(body)}
    pos["ok"] = st == 200 and pos["n"] == 200 and pos["newest"] == "2026-08-31T23:00:00"
    ref_p = ROOT + "/plan/control_reference_%s.json" % V
    if os.path.exists(ref_p):
        pos["reference_sha256"] = json.load(open(ref_p))["pos_body_sha256"]; pos["ok"] = pos["ok"] and pos["reference_sha256"] == pos["body_sha256"]
    elif pos["ok"]:
        atomic_write(ref_p, json.dumps({"pos_body_sha256": pos["body_sha256"], "created_run": RUN_ID}).encode()); pos["reference_created"] = True
    neg_to = urllib.parse.quote("2026-09-01T00:00:00Z") if V == "bithumb" else urllib.parse.quote("2016-01-01T00:00:00Z")
    st2, _, body2 = H.get("%s/v1/candles/minutes/60?market=KRW-BTC&count=200&to=%s" % (b, neg_to), LOG, "control_neg_to")
    js2 = parse(body2); neg = {"status": st2, "n": len(js2) if isinstance(js2, list) else None, "body_head": body2[:120].decode("utf-8", "replace")}
    if V == "bithumb":   # CORRECTION_1: Bithumb answers a Z-spelled `to` with HTTP 200 + {"error":{"name":400,"message":"Invalid parameter..."}}, not []
        neg["ok"] = st2 == 200 and not isinstance(js2, list) and "Invalid parameter" in neg["body_head"]
    else:                # Upbit: a `to` before venue launch is a true empty list
        neg["ok"] = st2 == 200 and neg["n"] == 0
    st3, _, body3 = H.get("%s/v1/candles/minutes/60?market=KRW-ZZZNOTACOIN&count=1" % b, LOG, "control_neg_code")
    js3 = parse(body3); negc = {"status": st3, "is_list": isinstance(js3, list), "body_head": body3[:120].decode("utf-8", "replace")}
    negc["ok"] = (not isinstance(js3, list)) and "Code not found" in negc["body_head"]
    out = {"pos": pos, "neg_to": neg, "neg_code": negc}; out["ok"] = pos["ok"] and neg["ok"] and negc["ok"]
    return out
def controls_binance():
    c = PLAN["controls"]["binance_pos"]
    st, _, body = H.get(c["url"], LOG, "control_pos"); pos = {"status": st, "zip_sha256": sha(body), "expected": c["zip_sha256"]}; pos["ok"] = st == 200 and pos["zip_sha256"] == c["zip_sha256"]
    st2, _, _ = H.get("https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/ZZZNOTACOINUSDT/1h/ZZZNOTACOINUSDT-1h-2026-07.zip", LOG, "control_neg")
    neg = {"status": st2, "ok": st2 == 404}
    return {"pos": pos, "neg": neg, "ok": pos["ok"] and neg["ok"]}
# ---------------- KRW paging ----------------
UNITS = (("60m", "minutes/60"), ("days", "days"))
def aligned(o, unit):
    if unit == "60m": return o % 3600 == 0
    return (o % 86400 == 0) if V == "upbit" else ((o + 9 * 3600) % 86400 == 0)
def mark_done(mk, unit, reason, **kw):
    STATE["units_done_this_run"] += 1; append(DONE, {"utc": H.utc_iso(), "run_id": RUN_ID, "venue": V, "market": mk, "unit": unit, "reason": reason, **kw})
def pull_unit(m, unit, path, pages):
    mk, first = m["market"], m["first_day_epoch"]
    cut = CUTOFF if unit == "60m" else CUTOFF - 86400
    if pages:
        last = min(pages, key=lambda p: p["oldest_open"]); cursor = last["oldest_open"]
        if last["oldest_open"] < cut: mark_done(mk, unit, "CUTOFF", resumed=True); return True
        if last["n"] < 200 and last["oldest_open"] < first + 86400: mark_done(mk, unit, "FIRST_TRADE", resumed=True); return True
    else:
        cursor = PULL_END
    empty_tries = 0
    while True:
        url = "%s/v1/candles/%s?market=%s&count=200&to=%s" % (BASE[V], path, mk, to_param(cursor))
        st, hdr, body = data_get(url, "%s_%s" % (mk, unit)); js = parse(body)
        if STATE["n_data_requests"] % 25 == 0: progress(current="%s %s" % (mk, unit), cursor_utc=iso(cursor))
        if st != 200 or not isinstance(js, list):
            err({"market": mk, "unit": unit, "to_epoch": cursor, "url": url, "status": st, "kind": "HTTP_OR_BODY_ERROR", "body_head": body[:160].decode("utf-8", "replace")}); return False
        if not js:
            if cursor <= first + 86400 or cursor <= cut: mark_done(mk, unit, "EMPTY_AT_FIRST_TRADE_OR_CUTOFF", cursor_epoch=cursor); return True
            empty_tries += 1; err({"market": mk, "unit": unit, "to_epoch": cursor, "url": url, "status": st, "kind": "EMPTY_UNEXPECTED", "try": empty_tries})
            if empty_tries >= 2: return False
            time.sleep(5); continue
        opens = [ep(c["candle_date_time_utc"]) for c in js]; bad = None
        if any(opens[i] <= opens[i + 1] for i in range(len(opens) - 1)): bad = "NOT_STRICTLY_DESCENDING"
        elif opens[0] >= cursor: bad = "NEWEST_NOT_BEFORE_CURSOR"
        elif not all(aligned(o, unit) for o in opens): bad = "NOT_ALIGNED"
        elif any(c.get("market") != mk for c in js): bad = "WRONG_MARKET"
        if bad: err({"market": mk, "unit": unit, "to_epoch": cursor, "url": url, "status": st, "kind": bad}); return False
        fpath = "%s/%s/%s/%s/p_%d.json.gz" % (ROOT, V, mk, unit, cursor); bsha = sha(body)
        if os.path.exists(fpath):
            old = gzip.decompress(open(fpath, "rb").read())
            if sha(old) != bsha:
                err({"market": mk, "unit": unit, "to_epoch": cursor, "kind": "REVISION_DIFFERENT_BODY_SAME_CURSOR", "old_sha256": sha(old), "new_sha256": bsha})
                fpath = fpath.replace(".json.gz", ".rev_%s.json.gz" % RUN_ID); atomic_write(fpath, gz(body))
        else:
            atomic_write(fpath, gz(body))
        append(MAN, {"utc": H.utc_iso(), "run_id": RUN_ID, "venue": V, "market": mk, "unit": unit, "to_epoch": cursor, "n": len(js), "newest_open": opens[0],
                     "oldest_open": opens[-1], "body_sha256": bsha, "file": os.path.relpath(fpath, ROOT), "file_sha256": sha(open(fpath, "rb").read())})
        if opens[-1] < cut: mark_done(mk, unit, "CUTOFF"); return True
        if len(js) < 200:
            if opens[-1] < first + 86400: mark_done(mk, unit, "FIRST_TRADE"); return True
            err({"market": mk, "unit": unit, "to_epoch": cursor, "kind": "SHORT_PAGE_BEFORE_FIRST_DAY", "oldest_open": opens[-1], "first_day_epoch": first}); return False
        cursor = opens[-1]
def run_krw():
    done = {(d["market"], d["unit"]) for d in read_jsonl(DONE)}
    pages = {}
    for p in read_jsonl(MAN): pages.setdefault((p["market"], p["unit"]), []).append(p)
    todo = [(m, u, path) for m in PLAN["krw"][V] for (u, path) in UNITS if (m["market"], u) not in done]
    progress(phase="pass1", todo=len(todo))
    failed = []
    for m, u, path in todo:
        if not pull_unit(m, u, path, pages.get((m["market"], u), [])): failed.append((m, u, path))
    progress(phase="pass2", todo=len(failed))
    pages = {}
    for p in read_jsonl(MAN): pages.setdefault((p["market"], p["unit"]), []).append(p)
    still = []
    for m, u, path in failed:
        time.sleep(2)
        if not pull_unit(m, u, path, pages.get((m["market"], u), [])): still.append("%s %s" % (m["market"], u))
    return still
# ---------------- Binance archive ----------------
def hours_in_month(mth):
    y, mo = int(mth[:4]), int(mth[5:]); return calendar.monthrange(y, mo)[1] * 24
def pull_zip(sym, mth):
    url = "https://data.binance.vision/data/futures/um/monthly/indexPriceKlines/%s/1h/%s-1h-%s.zip" % (sym, sym, mth)
    st, hdr, body = data_get(url, "%s_%s" % (sym, mth))
    if STATE["n_data_requests"] % 25 == 0: progress(current="%s %s" % (sym, mth))
    if st == 404:
        append(MAN, {"utc": H.utc_iso(), "run_id": RUN_ID, "venue": V, "symbol": sym, "month": mth, "status": "NOT_FOUND", "url": url}); return True
    if st != 200:
        err({"symbol": sym, "month": mth, "url": url, "status": st, "kind": "HTTP_ERROR"}); return False
    try:
        zf = zipfile.ZipFile(io.BytesIO(body)); names = zf.namelist(); assert len(names) == 1, names
        rows = list(csv.reader(io.StringIO(zf.read(names[0]).decode())))
        header = rows[0] if rows and not rows[0][0].strip().isdigit() else None; data = rows[1:] if header else rows
        ot = [int(r[0]) for r in data]; ct = [int(r[6]) for r in data]
        chk = {"header": header is not None, "n_rows": len(data), "expected_rows_full_month": hours_in_month(mth), "first_open": ot[0] if ot else None, "last_open": ot[-1] if ot else None,
               "ms_units": all(10 ** 12 <= t < 10 ** 13 for t in ot), "contiguous": all(ot[i + 1] - ot[i] == 3600000 for i in range(len(ot) - 1)),
               "close_time_ok": all(c - o == 3599999 for o, c in zip(ot, ct))}
    except Exception as e:
        err({"symbol": sym, "month": mth, "url": url, "status": st, "kind": "BAD_ZIP", "detail": "%s: %s" % (type(e).__name__, e)}); return False
    fpath = "%s/binance/%s/%s-1h-%s.zip" % (ROOT, sym, sym, mth); atomic_write(fpath, body)
    append(MAN, {"utc": H.utc_iso(), "run_id": RUN_ID, "venue": V, "symbol": sym, "month": mth, "status": "OK", "url": url, "zip_sha256": sha(body), "member": names[0],
                 "file": os.path.relpath(fpath, ROOT), **chk})
    return True
def run_binance():
    have = {(r["symbol"], r["month"]) for r in read_jsonl(MAN)}
    todo = [(b["symbol"], mth) for b in PLAN["binance"] for mth in b["months"] if (b["symbol"], mth) not in have]
    progress(phase="pass1", todo=len(todo)); failed = [k for k in todo if not pull_zip(*k)]
    progress(phase="pass2", todo=len(failed)); still = []
    for k in failed:
        time.sleep(2)
        if not pull_zip(*k): still.append("%s %s" % k)
    return still
# ---------------- main ----------------
code = 4; summary = {}
try:
    ctl = controls_binance() if V == "binance" else controls_krw()
    append(ROOT + "/run/controls_%s.jsonl" % V, {"utc": H.utc_iso(), "run_id": RUN_ID, "torn_tails_repaired": TORN_REPAIRED, **ctl})
    if not ctl["ok"]:
        atomic_write(ROOT + "/run/ABORT_%s_%s.json" % (V, RUN_ID), json.dumps(ctl).encode()); code = 2
    else:
        still = run_binance() if V == "binance" else run_krw()
        summary = {"unresolved": still}; code = 0 if not still else 1
except Stop as e:
    summary = {"stopped": str(e)}; code = 3
except Exception:
    summary = {"crash": traceback.format_exc()}; code = 4
finally:
    progress(phase="exit", exit_code=code, **{k: (v if k != "crash" else v[-400:]) for k, v in summary.items()})
    append(ROOT + "/run/exits_%s.jsonl" % V, {"utc": H.utc_iso(), "run_id": RUN_ID, "exit_code": code, "n_data_requests": STATE["n_data_requests"],
                                              "units_done_this_run": STATE["units_done_this_run"], "errors_this_run": STATE["errors_this_run"], **summary})
    sys.exit(code)
