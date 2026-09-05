#!/workspace/venv/bin/python
"""
markout_cdn.py -- +60 s markouts for pending live fills, computed from Binance public
daily aggTrades archives (the venue's aggTrades API only serves the last 2 days).

Mark rule (frozen; mirrors the executor's ops/backfill_markout.py as stated by the lead):
  target  = fill_ts + 60 s
  mark    = FIRST aggTrade with T >= target and T <= target + 60 s
  strict  = the same first trade, recorded as mark_px_5s / mark_lag_5s only when T <= target + 5 s
  none    -> status "no_trade_within_60s"
Source : https://data.binance.vision/data/futures/um/daily/aggTrades/<SYM>/<SYM>-aggTrades-<YYYY-MM-DD>.zip
File choice: the UTC day of `target` selects the file; if target + 60 s crosses midnight the
next day's file is also read and the earliest trade across both files wins.  A mark taken from a
later day's file is only accepted when every earlier needed file was read OK.
404 -> "archive_missing"; repeated transport failure -> "download_error"; bad CSV -> "parse_error".

Disk discipline: every archive is downloaded into memory (BytesIO), parsed, and dropped; nothing
is written under the workspace except the outputs.  Each (symbol, day) archive is fetched once.
"""
import argparse
import collections
import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

ROOT = "/workspace/review_scratch/markout_cdn"
BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades/{sym}/{fname}"
COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]
USE = ["agg_trade_id", "price", "transact_time"]
DTYPES = {"agg_trade_id": "int64", "price": "float64", "transact_time": "int64"}
MARK_DELAY_MS = 60_000
WINDOW_MS = 60_000
STRICT_MS = 5_000
DAY_MS = 86_400_000
CONFIG = dict(mark_delay_ms=MARK_DELAY_MS, window_ms=WINDOW_MS, strict_ms=STRICT_MS,
              workers=16, retries=4, base_url=BASE, script=os.path.abspath(__file__))


def self_sha256():
    with open(os.path.abspath(__file__), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def utc_day(ms):
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%d")


def day_start_ms(day):
    return int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def log(msg, fh=None):
    line = f"{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    if fh is not None:
        fh.write(line + "\n"); fh.flush()


def fetch(url, retries=4, timeout=180):
    """Return (status, payload). status in {'ok','archive_missing','download_error'}."""
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "markout-cdn/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
                cl = r.headers.get("Content-Length")
                if cl is not None and int(cl) != len(data):
                    raise IOError(f"short read {len(data)} != {cl}")
                return "ok", data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "archive_missing", None
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(2.0 * (k + 1))
    return "download_error", last


def parse_zip(data):
    """-> dict(T sorted int64 ms, P float64, A int64 agg id, n, header, sorted_in_file, csv_name)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    assert len(names) == 1, names
    with z.open(names[0]) as f:
        first = f.readline()
    has_header = first.startswith(b"agg_trade_id")
    with z.open(names[0]) as f:
        if has_header:
            df = pd.read_csv(f, header=0, usecols=USE, dtype=DTYPES)
        else:
            df = pd.read_csv(f, header=None, names=COLS, usecols=USE, dtype=DTYPES)
    T = df["transact_time"].to_numpy()
    P = df["price"].to_numpy()
    A = df["agg_trade_id"].to_numpy()
    sorted_in_file = bool(np.all(np.diff(T) >= 0)) if len(T) > 1 else True
    if not sorted_in_file:
        o = np.argsort(T, kind="stable")  # stable: keeps agg_trade_id order among equal T
        T, P, A = T[o], P[o], A[o]
    return dict(T=T, P=P, A=A, n=int(len(T)), header=has_header, sorted_in_file=sorted_in_file, csv_name=names[0])


def work(job):
    """job = (sym, day, fname, queries); queries = [(qid, target_ms, lo_ms, hi_ms), ...]."""
    sym, day, fname, queries = job
    url = BASE.format(sym=sym, fname=fname)
    t0 = time.time()
    status, data = fetch(url, retries=CONFIG["retries"])
    meta = dict(sym=sym, day=day, fname=fname, status=status, sha256=None, bytes=0, n_rows=0, header=None,
                sorted_in_file=None, dl_s=round(time.time() - t0, 2), parse_s=None, err=None, n_queries=len(queries))
    if status != "ok":
        meta["err"] = data if status == "download_error" else None
        return meta, {}
    meta["sha256"] = hashlib.sha256(data).hexdigest()
    meta["bytes"] = len(data)
    t1 = time.time()
    try:
        tr = parse_zip(data)
    except Exception as e:  # noqa: BLE001
        meta["status"] = "parse_error"
        meta["err"] = repr(e)
        return meta, {}
    del data
    meta.update(n_rows=tr["n"], header=tr["header"], sorted_in_file=tr["sorted_in_file"], parse_s=round(time.time() - t1, 2))
    T, P, A = tr["T"], tr["P"], tr["A"]
    res = {}
    for qid, target, lo, hi in queries:
        i = int(np.searchsorted(T, lo, side="left"))
        if i < len(T) and T[i] <= hi:
            res[qid] = dict(T=int(T[i]), P=float(P[i]), A=int(A[i]), fname=fname, day=day, sha=meta["sha256"])
        else:
            res[qid] = None
    return meta, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=f"{ROOT}/input/pending_fills.json")
    ap.add_argument("--out", default=f"{ROOT}/out/marks.json")
    ap.add_argument("--archives", default=f"{ROOT}/out/archives.json")
    ap.add_argument("--meta", default=f"{ROOT}/out/run_meta.json")
    ap.add_argument("--log", default=f"{ROOT}/logs/run.log")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--resume", action="store_true",
                    help="keep rows already ok/no_trade_within_60s in an existing --out; refetch only the rest")
    ap.add_argument("--limit", type=int, default=0, help="debug: only the first N archives")
    args = ap.parse_args()
    CONFIG["workers"] = args.workers
    CONFIG["self_sha256"] = self_sha256()
    CONFIG["argv"] = sys.argv
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    fh = open(args.log, "a")
    log(f"config={json.dumps(CONFIG)}", fh)

    with open(args.input, "rb") as f:
        raw = f.read()
    CONFIG["input_sha256"] = hashlib.sha256(raw).hexdigest()
    rows = json.loads(raw)["rows"]
    log(f"input={args.input} sha256={CONFIG['input_sha256']} rows={len(rows)}", fh)

    prev = {}
    if args.resume and os.path.exists(args.out):
        with open(args.out) as f:
            prev = json.load(f)
        log(f"resume: {len(prev)} existing records loaded from {args.out}", fh)

    files = collections.defaultdict(list)  # (sym, day) -> [(qid, target, lo, hi)]
    qinfo = {}
    for qid, r in enumerate(rows):
        tid = str(r["trade_id"])
        if tid in prev and prev[tid]["status"] in ("ok", "no_trade_within_60s"):
            continue
        target = int(round(r["fill_ts"] * 1000)) + MARK_DELAY_MS
        hi = target + WINDOW_MS
        d0, d1 = utc_day(target), utc_day(hi)
        days = [d0] if d0 == d1 else [d0, d1]
        qinfo[qid] = dict(target=target, hi=hi, files=[])
        for d in days:
            ds = day_start_ms(d)
            de = ds + DAY_MS - 1
            files[(r["symbol"], d)].append((qid, target, max(target, ds), min(hi, de)))
            qinfo[qid]["files"].append((r["symbol"], d))
    jobs = [(sym, d, f"{sym}-aggTrades-{d}.zip", qs) for (sym, d), qs in sorted(files.items())]
    if args.limit:
        jobs = jobs[: args.limit]
        keep = {k for k in files if k in {(j[0], j[1]) for j in jobs}}
        qinfo = {q: v for q, v in qinfo.items() if all(f in keep for f in v["files"])}
    log(f"queries={len(qinfo)} archives={len(jobs)} workers={args.workers}", fh)

    metas, partial = {}, collections.defaultdict(list)
    t0 = time.time()
    nbytes = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for k, fut in enumerate(as_completed(futs), 1):
            meta, res = fut.result()
            metas[(meta["sym"], meta["day"])] = meta
            nbytes += meta["bytes"]
            for qid, v in res.items():
                partial[qid].append(v)
            if meta["status"] not in ("ok",):
                log(f"  {meta['fname']}: {meta['status']} {meta['err'] or ''}", fh)
            if k % 100 == 0 or k == len(jobs):
                du = subprocess.run(["du", "-sh", ROOT], capture_output=True, text=True).stdout.split()[0]
                el = time.time() - t0
                log(f"[{k}/{len(jobs)}] archives done; {nbytes/1e9:.2f} GB fetched; {el/60:.1f} min; "
                    f"du({ROOT})={du}", fh)

    marks = dict(prev)
    for qid, info in qinfo.items():
        r = rows[qid]
        tid = str(r["trade_id"])
        fstat = [metas[f]["status"] for f in info["files"]]
        found = [v for v in partial.get(qid, []) if v]
        rec = dict(symbol=r["symbol"], day=r["day"], target_ts=info["target"],
                   mark_px=None, mark_ts=None, mark_lag_s=None, mark_agg_trade_id=None,
                   mark_px_5s=None, mark_lag_5s=None, status=None, source=None, file_sha256=None)
        best = None
        if found:
            best = min(found, key=lambda v: (v["T"], v["A"]))
            # accept only if every earlier needed file was read OK (a missing earlier day could hide an earlier trade)
            earlier = [f for f in info["files"] if f[1] < best["day"]]
            if any(metas[f]["status"] != "ok" for f in earlier):
                best = None
        if best is not None:
            lag = (best["T"] - info["target"]) / 1000.0
            rec.update(mark_px=best["P"], mark_ts=best["T"], mark_lag_s=lag, mark_agg_trade_id=best["A"],
                       status="ok", source=f"data.binance.vision daily aggTrades {best['fname']}",
                       file_sha256=best["sha"])
            if best["T"] <= info["target"] + STRICT_MS:
                rec.update(mark_px_5s=best["P"], mark_lag_5s=lag)
        else:
            if all(s == "ok" for s in fstat):
                st = "no_trade_within_60s"
            elif "archive_missing" in fstat:
                st = "archive_missing"
            elif "parse_error" in fstat:
                st = "parse_error"
            else:
                st = "download_error"
            fnames = ", ".join(metas[f]["fname"] for f in info["files"])
            shas = [metas[f]["sha256"] for f in info["files"] if metas[f]["sha256"]]
            rec.update(status=st, source=f"data.binance.vision daily aggTrades {fnames}",
                       file_sha256=shas[0] if len(shas) == 1 else (shas or None))
        marks[tid] = rec

    with open(args.out, "w") as f:
        json.dump(marks, f, indent=0, sort_keys=True)
    arch = sorted(metas.values(), key=lambda m: (m["sym"], m["day"]))
    with open(args.archives, "w") as f:
        json.dump(arch, f, indent=0)
    cnt = collections.Counter(v["status"] for v in marks.values())
    acnt = collections.Counter(m["status"] for m in arch)
    run_meta = dict(config=CONFIG, generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    n_rows=len(rows), n_marks_written=len(marks), status_counts=dict(cnt),
                    archive_status_counts=dict(acnt), archives_fetched=len(arch), bytes_fetched=nbytes,
                    n_unsorted_archives=sum(1 for m in arch if m["sorted_in_file"] is False),
                    n_headerless_archives=sum(1 for m in arch if m["header"] is False),
                    elapsed_s=round(time.time() - t0, 1))
    with open(args.meta, "w") as f:
        json.dump(run_meta, f, indent=1)
    log(f"done: marks={len(marks)} status={dict(cnt)} archives={dict(acnt)} unsorted={run_meta['n_unsorted_archives']} "
        f"headerless={run_meta['n_headerless_archives']} bytes={nbytes/1e9:.2f}GB elapsed={run_meta['elapsed_s']}s", fh)
    fh.close()


if __name__ == "__main__":
    main()
