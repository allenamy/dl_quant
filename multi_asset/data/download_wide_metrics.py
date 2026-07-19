#!/usr/bin/env python3
"""Download Binance futures/um daily metrics for the wide universe.
Uses S3 ListObjectsV2 (via s3.ap-northeast-1) for exact per-symbol date lists,
then pooled keep-alive concurrent GETs. Resume-safe, coverage log.
"""
import os, re, json, time, argparse, glob, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        ad = HTTPAdapter(pool_connections=4, pool_maxsize=8,
                         max_retries=Retry(total=3, backoff_factor=0.5,
                                           status_forcelist=[500, 502, 503, 504]))
        s.mount("https://", ad); _tls.s = s
    return s


def list_symbol_dates(sym, end_date):
    """Page through S3 listing -> sorted list of date strings <= end_date."""
    prefix = PREFIX + sym + "/"
    dates = []; token = None
    for _ in range(20):
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        for attempt in range(4):
            try:
                r = sess().get(S3, params=params, timeout=30)
                if r.status_code == 200:
                    break
                time.sleep(1.0 * (attempt + 1))
            except Exception:
                time.sleep(1.0 * (attempt + 1))
        else:
            break
        for key in re.findall(r"<Key>([^<]+)</Key>", r.text):
            m = re.search(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip$", key)
            if m and m.group(1) <= end_date:
                dates.append(m.group(1))
        tok = re.findall(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", r.text)
        trunc = re.findall(r"<IsTruncated>([^<]+)</IsTruncated>", r.text)
        if trunc and trunc[0] == "true" and tok:
            token = tok[0]
        else:
            break
    return sorted(set(dates))


def download_one(sym, d, outdir, retries=3):
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
            time.sleep(1.0 * (k + 1))
        except Exception:
            time.sleep(1.0 * (k + 1))
    return "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--symbols", default="")
    a = ap.parse_args()
    P = np.load(PANEL, allow_pickle=True); syms = list(P["symbols"])
    if a.symbols:
        want = set(a.symbols.split(",")); syms = [s for s in syms if s in want]
    os.makedirs(a.outdir, exist_ok=True)
    cov = {}; t0 = time.time()
    ex = ThreadPoolExecutor(max_workers=a.workers)
    for i, sym in enumerate(syms):
        dates = list_symbol_dates(sym, a.end)
        if not dates:
            cov[sym] = {"start": None, "end": None, "files": 0, "missing": 0, "fail": 0}
            print("[%d/%d] %-14s NO DATA (%.0fs)" % (i + 1, len(syms), sym, time.time() - t0), flush=True)
            with open(os.path.join(a.outdir, "_coverage.json"), "w") as fh:
                json.dump(cov, fh, indent=1)
            continue
        res = {"ok": 0, "skip": 0, "missing": 0, "fail": 0}
        futs = [ex.submit(download_one, sym, d, a.outdir) for d in dates]
        for f in as_completed(futs):
            s = f.result(); res[s] = res.get(s, 0) + 1
        fs = sorted(glob.glob(os.path.join(a.outdir, sym, sym + "-metrics-*.zip")))
        fdates = [os.path.basename(x).replace(sym + "-metrics-", "").replace(".zip", "") for x in fs]
        s0 = fdates[0] if fdates else None; s1 = fdates[-1] if fdates else None
        cov[sym] = {"start": s0, "end": s1, "files": len(fs),
                    "listed": len(dates), "missing": res["missing"], "fail": res["fail"]}
        print("[%d/%d] %-14s %s..%s files=%5d/%5d fail=%3d (%.0fs)" % (
            i + 1, len(syms), sym, s0, s1, len(fs), len(dates), res["fail"], time.time() - t0), flush=True)
        with open(os.path.join(a.outdir, "_coverage.json"), "w") as fh:
            json.dump(cov, fh, indent=1)
    ex.shutdown()
    tot = sum(v["files"] for v in cov.values()); tf = sum(v["fail"] for v in cov.values())
    print("\nDONE %d syms, %d files, %d fails, %.0fs" % (len(syms), tot, tf, time.time() - t0))
    with open(os.path.join(a.outdir, "_coverage.json"), "w") as fh:
        json.dump(cov, fh, indent=1)


if __name__ == "__main__":
    main()
