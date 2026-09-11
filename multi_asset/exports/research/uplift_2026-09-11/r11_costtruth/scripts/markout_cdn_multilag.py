#!/usr/bin/env python3
"""r11 STEP 2 — MARKOUT TERM STRUCTURE from Binance public daily aggTrades archives.

DERIVED FROM: multi_asset/exports/research/retrain_2026-09/markout_cdn_2026-09-05/scripts/markout_cdn.py
              sha256 542f98a67da3f0d826c9ac01af38fc8f948924f98abbfbaa0f2f32a3d87426f3
              (the device that produced the marks already imported into fills.jsonl; validated 20/20
               against an independent parser, out/validation_summary.json).
CHANGE vs that device, and ONLY this change:
  - MARK_DELAYS_MS = {60s, 300s, 900s, 3600s, 14400s} instead of the single 60 s.
    The mark RULE is untouched at every lag: FIRST aggTrade with T >= target and T <= target + 60 s.
    Keeping the window at 60 s for every lag is deliberate: the instrument must be IDENTICAL across
    the term structure, otherwise the curve measures the window and not the price.
  - each archive additionally reports trade count and quote volume, so liquidity deciles come from the
    same bytes and need no second source.

GATE: lag 60 s reproduces the mark already recorded in fills.jsonl (`mid_at_fill_plus_60s`). That
comparison is made by the consumer (r11_term_structure.py) and MUST pass before any other lag is read.

SIGN CONVENTION — copied verbatim from trackB_realized_cost_2026-09-11.py lines 6-8:
  "markout = side_sign * (mid_at_fill_plus_60s - fill_px) / fill_px .  POSITIVE markout = the price
   moved OUR WAY after the fill ... = a GAIN to us.  Adverse selection COST is therefore -markout."
This script emits raw mark prices only; the sign is applied downstream, once, under that convention.

Disk discipline: archives are fetched into memory, parsed, dropped. Nothing written but the outputs.
ENV WHITELIST: {} (empty) — asserted below (E-0826-D).
"""
import argparse, collections, datetime as dt, hashlib, io, json, os, sys, time
import urllib.error, urllib.request, zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd

_FORBID = ("CAL", "JUDGE", "PANEL", "EXPORT_PANEL", "EMA_STATE_JSON", "W10_", "POD_", "DLW_", "KING_", "SEAT_", "UMASK")
_hits = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hits, f"ENV WHITELIST VIOLATION: {_hits}"
ENV_WHITELIST = {}

BASE = "https://data.binance.vision/data/futures/um/daily/aggTrades/{sym}/{fname}"
COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]
USE = ["agg_trade_id", "price", "quantity", "transact_time"]
DTYPES = {"agg_trade_id": "int64", "price": "float64", "quantity": "float64", "transact_time": "int64"}

MARK_DELAYS_MS = [60_000, 300_000, 900_000, 3_600_000, 14_400_000]   # 60s, 5m, 15m, 1h, 4h
WINDOW_MS = 60_000        # identical at every lag, on purpose
DAY_MS = 86_400_000
CONFIG = dict(mark_delays_ms=MARK_DELAYS_MS, window_ms=WINDOW_MS, base_url=BASE,
              derived_from_sha256="542f98a67da3f0d826c9ac01af38fc8f948924f98abbfbaa0f2f32a3d87426f3")


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
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "markout-cdn-multilag/1.0"})
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
    T = df["transact_time"].to_numpy(); P = df["price"].to_numpy()
    Q = df["quantity"].to_numpy();      A = df["agg_trade_id"].to_numpy()
    sorted_in_file = bool(np.all(np.diff(T) >= 0)) if len(T) > 1 else True
    if not sorted_in_file:
        o = np.argsort(T, kind="stable")
        T, P, Q, A = T[o], P[o], Q[o], A[o]
    return dict(T=T, P=P, Q=Q, A=A, n=int(len(T)), header=has_header,
                sorted_in_file=sorted_in_file, csv_name=names[0])


def work(job):
    """job = (sym, day, fname, queries); queries = [(qid, lagkey, target_ms, lo_ms, hi_ms), ...]"""
    sym, day, fname, queries = job
    url = BASE.format(sym=sym, fname=fname)
    t0 = time.time()
    status, data = fetch(url)
    meta = dict(sym=sym, day=day, fname=fname, status=status, sha256=None, bytes=0, n_rows=0,
                header=None, sorted_in_file=None, quote_volume=None,
                dl_s=round(time.time() - t0, 2), err=None, n_queries=len(queries))
    if status != "ok":
        meta["err"] = data if status == "download_error" else None
        return meta, {}
    meta["sha256"] = hashlib.sha256(data).hexdigest(); meta["bytes"] = len(data)
    try:
        tr = parse_zip(data)
    except Exception as e:  # noqa: BLE001
        meta["status"] = "parse_error"; meta["err"] = repr(e)
        return meta, {}
    del data
    meta.update(n_rows=tr["n"], header=tr["header"], sorted_in_file=tr["sorted_in_file"],
                quote_volume=float(np.sum(tr["P"] * tr["Q"])))
    T, P, A = tr["T"], tr["P"], tr["A"]
    res = {}
    for qid, lagkey, target, lo, hi in queries:
        i = int(np.searchsorted(T, lo, side="left"))
        if i < len(T) and T[i] <= hi:
            res[f"{qid}|{lagkey}"] = dict(T=int(T[i]), P=float(P[i]), A=int(A[i]),
                                          fname=fname, day=day, sha=meta["sha256"])
        else:
            res[f"{qid}|{lagkey}"] = None
    return meta, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    CONFIG.update(workers=args.workers, self_sha256=self_sha256(), argv=sys.argv,
                  env_whitelist=ENV_WHITELIST)
    os.makedirs(args.outdir, exist_ok=True)
    fh = open(f"{args.outdir}/run.log", "a")
    log(f"config={json.dumps(CONFIG)}", fh)

    raw = open(args.input, "rb").read()
    CONFIG["input_sha256"] = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw); rows = payload["rows"]
    log(f"input sha256={CONFIG['input_sha256']} rows={len(rows)}", fh)

    files = collections.defaultdict(list)     # (sym, day) -> queries
    qinfo = {}                                 # (qid, lagkey) -> dict
    for qid, r in enumerate(rows):
        fts_ms = int(round(r["fill_ts"] * 1000))
        for D in MARK_DELAYS_MS:
            lagkey = str(D // 1000)
            target = fts_ms + D
            hi = target + WINDOW_MS
            d0, d1 = utc_day(target), utc_day(hi)
            days = [d0] if d0 == d1 else [d0, d1]
            qinfo[(qid, lagkey)] = dict(target=target, hi=hi, files=[])
            for d in days:
                ds = day_start_ms(d); de = ds + DAY_MS - 1
                files[(r["symbol"], d)].append((qid, lagkey, target, max(target, ds), min(hi, de)))
                qinfo[(qid, lagkey)]["files"].append((r["symbol"], d))
    jobs = [(sym, d, f"{sym}-aggTrades-{d}.zip", qs) for (sym, d), qs in sorted(files.items())]
    if args.limit:
        jobs = jobs[: args.limit]
        keep = {(j[0], j[1]) for j in jobs}
        qinfo = {k: v for k, v in qinfo.items() if all(f in keep for f in v["files"])}
    log(f"queries={len(qinfo)} archives={len(jobs)} workers={args.workers}", fh)

    metas, partial = {}, collections.defaultdict(list)
    t0 = time.time(); nbytes = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        for k, fut in enumerate(as_completed(futs), 1):
            meta, res = fut.result()
            metas[(meta["sym"], meta["day"])] = meta
            nbytes += meta["bytes"]
            for key, v in res.items():
                partial[key].append(v)
            if meta["status"] != "ok":
                log(f"  {meta['fname']}: {meta['status']} {meta['err'] or ''}", fh)
            if k % 200 == 0 or k == len(jobs):
                log(f"[{k}/{len(jobs)}] {nbytes/1e9:.2f} GB; {(time.time()-t0)/60:.1f} min", fh)

    marks = {}   # trade_id -> {lagkey: rec}
    for (qid, lagkey), info in qinfo.items():
        r = rows[qid]; tid = str(r["trade_id"])
        fstat = [metas[f]["status"] for f in info["files"]]
        found = [v for v in partial.get(f"{qid}|{lagkey}", []) if v]
        rec = dict(mark_px=None, mark_ts=None, mark_lag_s=None, mark_agg_trade_id=None,
                   status=None, file_sha256=None)
        best = None
        if found:
            best = min(found, key=lambda v: (v["T"], v["A"]))
            earlier = [f for f in info["files"] if f[1] < best["day"]]
            if any(metas[f]["status"] != "ok" for f in earlier):
                best = None
        if best is not None:
            rec.update(mark_px=best["P"], mark_ts=best["T"],
                       mark_lag_s=(best["T"] - info["target"]) / 1000.0,
                       mark_agg_trade_id=best["A"], status="ok", file_sha256=best["sha"])
        else:
            if all(s == "ok" for s in fstat):
                st = "no_trade_within_window"
            elif "archive_missing" in fstat:
                st = "archive_missing"
            elif "parse_error" in fstat:
                st = "parse_error"
            else:
                st = "download_error"
            rec.update(status=st)
        marks.setdefault(tid, {})[lagkey] = rec

    with open(f"{args.outdir}/marks_multilag.json", "w") as f:
        json.dump(marks, f, indent=0, sort_keys=True)
    arch = sorted(metas.values(), key=lambda m: (m["sym"], m["day"]))
    with open(f"{args.outdir}/archives.json", "w") as f:
        json.dump(arch, f, indent=0)
    cnt = {lk: collections.Counter(v[lk]["status"] for v in marks.values() if lk in v)
           for lk in (str(D // 1000) for D in MARK_DELAYS_MS)}
    run_meta = dict(config=CONFIG,
                    generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    n_rows=len(rows), n_trade_ids=len(marks),
                    status_counts_by_lag={k: dict(v) for k, v in cnt.items()},
                    archive_status_counts=dict(collections.Counter(m["status"] for m in arch)),
                    archives_fetched=len(arch), bytes_fetched=nbytes,
                    n_unsorted_archives=sum(1 for m in arch if m["sorted_in_file"] is False),
                    n_headerless_archives=sum(1 for m in arch if m["header"] is False),
                    elapsed_s=round(time.time() - t0, 1))
    with open(f"{args.outdir}/run_meta.json", "w") as f:
        json.dump(run_meta, f, indent=1)
    log(f"done: trade_ids={len(marks)} by_lag={ {k: dict(v) for k, v in cnt.items()} } "
        f"bytes={nbytes/1e9:.2f}GB elapsed={run_meta['elapsed_s']}s", fh)
    fh.close()


if __name__ == "__main__":
    main()
