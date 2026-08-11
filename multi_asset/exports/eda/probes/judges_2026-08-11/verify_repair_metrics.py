#!/usr/bin/env python3
"""Verify + repair wide-metrics download.

Re-lists ALL symbols SERIALLY with robust retry (exp backoff), distinguishing
HTTP-error/timeout from a genuine empty listing. Downloads any missing dates.
Fixes the false-'NO DATA' bug (swallowed listing failures) and catches any
silent pagination truncation. Writes authoritative coverage JSON.
"""
import os, re, sys, json, time, glob, argparse, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import requests
from requests.adapters import HTTPAdapter

S3 = "https://s3.ap-northeast-1.amazonaws.com/data.binance.vision"
CDN = "https://data.binance.vision"
PREFIX = "data/futures/um/daily/metrics/"
PANEL = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"
UA = {"User-Agent": "Mozilla/5.0 (research data pull)"}
_tls = threading.local()


def sess():
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session(); s.headers.update(UA)
        # NO adapter-level retries: we do our own explicit retry so failures are visible
        s.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0))
        _tls.s = s
    return s


def robust_list(sym, end_date, max_retries=6):
    """Return (status, dates). status='OK' (valid listing, dates may be empty=true no-data)
    or 'ERROR' (could not fetch a page after retries -> do NOT treat as no-data)."""
    prefix = PREFIX + sym + "/"
    dates = []; token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        r = None
        for attempt in range(max_retries):
            try:
                resp = sess().get(S3, params=params, timeout=20)
                if resp.status_code == 200:
                    r = resp; break
            except Exception:
                pass
            time.sleep(min(2 ** attempt, 20))  # 1,2,4,8,16,20 backoff
        if r is None:
            return "ERROR", sorted(set(dates))
        for key in re.findall(r"<Key>([^<]+)</Key>", r.text):
            m = re.search(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip$", key)
            if m and m.group(1) <= end_date:
                dates.append(m.group(1))
        trunc = re.findall(r"<IsTruncated>([^<]+)</IsTruncated>", r.text)
        tok = re.findall(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", r.text)
        if trunc and trunc[0] == "true" and tok:
            token = tok[0]
        else:
            break
    return "OK", sorted(set(dates))


def download_one(sym, d, outdir, retries=4):
    dst = os.path.join(outdir, sym, sym + "-metrics-" + d + ".zip")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return "skip"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = CDN + "/" + PREFIX + sym + "/" + sym + "-metrics-" + d + ".zip"
    for k in range(retries):
        try:
            r = sess().get(url, timeout=40)
            if r.status_code == 200:
                tmp = dst + ".part"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                os.replace(tmp, dst); return "ok"
            if r.status_code in (403, 404):
                return "missing"
        except Exception:
            pass
        time.sleep(1.0 * (k + 1))
    return "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--only", default="")  # optional subset (comma) to repair
    a = ap.parse_args()
    P = np.load(PANEL, allow_pickle=True); syms = list(P["symbols"])
    if a.only:
        want = set(a.only.split(",")); syms = [s for s in syms if s in want]

    # PHASE 1: authoritative serial listing (no download contention)
    print("=== PHASE 1: robust serial listing (%d syms) ===" % len(syms), flush=True)
    listing = {}; errors = []
    for i, sym in enumerate(syms):
        st, dates = robust_list(sym, a.end)
        if st == "ERROR":
            errors.append(sym)
        listing[sym] = {"status": st, "n_listed": len(dates), "dates": dates}
        tag = st if st == "OK" else "**ERROR**"
        print("[%d/%d] %-14s %s listed=%d" % (i + 1, len(syms), sym, tag, len(dates)), flush=True)
    # retry ERROR coins once more (serial, extra backoff)
    if errors:
        print("=== retrying %d ERROR coins ===" % len(errors), flush=True)
        for sym in errors:
            time.sleep(2)
            st, dates = robust_list(sym, a.end, max_retries=8)
            listing[sym] = {"status": st, "n_listed": len(dates), "dates": dates}
            print("  retry %-14s %s listed=%d" % (sym, st, len(dates)), flush=True)

    # PHASE 2: download missing dates for all coins (modest concurrency)
    print("=== PHASE 2: download missing ===", flush=True)
    tasks = []
    for sym, info in listing.items():
        if info["status"] != "OK":
            continue
        have = set(os.path.basename(x).replace(sym + "-metrics-", "").replace(".zip", "")
                   for x in glob.glob(os.path.join(a.outdir, sym, sym + "-metrics-*.zip")))
        for d in info["dates"]:
            if d not in have:
                tasks.append((sym, d))
    print("missing files to fetch: %d" % len(tasks), flush=True)
    res = {"ok": 0, "missing": 0, "fail": 0}
    if tasks:
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(download_one, s, d, a.outdir): (s, d) for s, d in tasks}
            done = 0
            for f in as_completed(futs):
                r = f.result(); res[r] = res.get(r, 0) + 1; done += 1
                if done % 500 == 0:
                    print("  fetched %d/%d ok=%d fail=%d" % (done, len(tasks), res["ok"], res["fail"]), flush=True)
    print("download result:", res, flush=True)

    # PHASE 3: authoritative coverage report
    cov = {}
    for sym, info in listing.items():
        fs = sorted(glob.glob(os.path.join(a.outdir, sym, sym + "-metrics-*.zip")))
        fdates = [os.path.basename(x).replace(sym + "-metrics-", "").replace(".zip", "") for x in fs]
        n_have = len(fdates); n_list = info["n_listed"]
        if info["status"] != "OK":
            status = "LIST_ERROR"
        elif n_list == 0:
            status = "TRUE_NODATA"
        elif n_have >= n_list:
            status = "COMPLETE"
        else:
            status = "PARTIAL(%d/%d)" % (n_have, n_list)
        cov[sym] = {"status": status, "n_listed": n_list, "n_have": n_have,
                    "start": fdates[0] if fdates else None, "end": fdates[-1] if fdates else None}
    with open(os.path.join(a.outdir, "_coverage_verified.json"), "w") as fh:
        json.dump(cov, fh, indent=1)
    # summary
    from collections import Counter
    cnt = Counter(v["status"].split("(")[0] for v in cov.values())
    print("=== COVERAGE SUMMARY ===")
    for k, v in cnt.items():
        print("  %-14s %d" % (k, v))
    bad = {s: v for s, v in cov.items() if not v["status"].startswith("COMPLETE") and v["status"] != "TRUE_NODATA"}
    if bad:
        print("=== NEEDS ATTENTION ===")
        for s, v in bad.items():
            print("  %-14s %s" % (s, v["status"]))
    tot = sum(v["n_have"] for v in cov.values())
    print("TOTAL files on disk:", tot)


if __name__ == "__main__":
    main()
