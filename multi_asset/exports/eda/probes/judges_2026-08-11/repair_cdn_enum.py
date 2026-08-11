#!/usr/bin/env python3
"""CDN-enumeration repair for wide-metrics download (S3 listing is unreliable).

Repairs coins with 0 files (false NO-DATA from swallowed listing failures) or a
last-file date well before panel end (silent pagination truncation). Bounds each
coin's date range via the panel MEMBER110 point-in-time mask, then GET-with-skip
from the reliable CDN (data.binance.vision). 404 = not available, 200 = fetch.
"""
import os, glob, time, json, argparse, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, requests
from requests.adapters import HTTPAdapter

CDN = "https://data.binance.vision"
PREFIX = "data/futures/um/daily/metrics/"
PANEL = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"
UA = {"User-Agent": "Mozilla/5.0 (research data pull)"}
END = "2026-06-30"; FLOOR = "2021-01-01"
_tls = threading.local()


def sess():
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session(); s.headers.update(UA)
        s.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0))
        _tls.s = s
    return s


def download_one(sym, d, outdir, retries=5):
    dst = os.path.join(outdir, sym, sym + "-metrics-" + d + ".zip")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return "skip"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = CDN + "/" + PREFIX + sym + "/" + sym + "-metrics-" + d + ".zip"
    for k in range(retries):
        try:
            r = sess().get(url, timeout=30)
            if r.status_code == 200:
                tmp = dst + ".part"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                os.replace(tmp, dst); return "ok"
            if r.status_code in (403, 404):
                return "missing"
        except Exception:
            pass
        time.sleep(0.7 * (k + 1))
    return "fail"


def daterange(a, b):
    d = dt.date.fromisoformat(a); e = dt.date.fromisoformat(b)
    while d <= e:
        yield d.strftime("%Y-%m-%d"); d += dt.timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--only", default="")   # optional explicit comma list
    a = ap.parse_args()
    P = np.load(PANEL, allow_pickle=True)
    ts = P["ts"].astype(np.int64); symbols = list(P["symbols"]); member = P["MEMBER110"]

    # determine repair set from disk unless --only given
    def coin_files(s):
        fs = sorted(glob.glob(os.path.join(a.outdir, s, s + "-metrics-*.zip")))
        d = [os.path.basename(x).replace(s + "-metrics-", "").replace(".zip", "") for x in fs]
        return d
    if a.only:
        repair = [s for s in symbols if s in set(a.only.split(","))]
    else:
        repair = []
        for s in symbols:
            d = coin_files(s)
            if (not d) or (d[-1] < "2026-06-25"):
                repair.append(s)
    print("repair set (%d): %s" % (len(repair), " ".join(repair)), flush=True)

    # build (coin,date) task list bounded by MEMBER110
    tasks = []; ranges = {}
    for s in repair:
        j = symbols.index(s)
        mt = ts[member[:, j]]
        if len(mt) == 0:
            ranges[s] = None; continue
        d0 = dt.datetime.utcfromtimestamp(int(mt.min()) / 1000).date() - dt.timedelta(days=3)
        d1 = dt.datetime.utcfromtimestamp(int(mt.max()) / 1000).date()
        lo = max(d0.isoformat(), FLOOR); hi = min(d1.isoformat(), END)
        ranges[s] = (lo, hi)
        have = set(coin_files(s))
        for d in daterange(lo, hi):
            if d not in have:
                tasks.append((s, d))
    print("total candidate fetches: %d" % len(tasks), flush=True)

    res = {"ok": 0, "missing": 0, "fail": 0, "skip": 0}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(download_one, s, d, a.outdir) for s, d in tasks]
        done = 0
        for f in as_completed(futs):
            r = f.result(); res[r] = res.get(r, 0) + 1; done += 1
            if done % 2000 == 0:
                print("  %d/%d ok=%d missing=%d fail=%d (%.0fs)" % (
                    done, len(tasks), res["ok"], res["missing"], res["fail"], time.time() - t0), flush=True)
    print("RESULT:", res, "(%.0fs)" % (time.time() - t0), flush=True)

    # coverage report for repair coins
    cov = {}
    for s in repair:
        d = coin_files(s)
        cov[s] = {"n_have": len(d), "first": d[0] if d else None, "last": d[-1] if d else None,
                  "member_range": ranges.get(s)}
        print("  %-12s n=%5d %s..%s" % (s, len(d), cov[s]["first"], cov[s]["last"]), flush=True)
    with open(os.path.join(a.outdir, "_repair_coverage.json"), "w") as fh:
        json.dump(cov, fh, indent=1)
    # flag any still-suspicious (0 files, or last still far from member end)
    bad = []
    for s in repair:
        r = ranges.get(s); c = cov[s]
        if c["n_have"] == 0:
            bad.append((s, "STILL_ZERO"))
        elif r and c["last"] and c["last"] < r[1] and c["last"] < "2026-06-25":
            # could be genuine delisting; flag for eyeball
            bad.append((s, "ends %s (member_end %s)" % (c["last"], r[1])))
    print("=== FLAGGED FOR REVIEW (%d) ===" % len(bad), flush=True)
    for s, why in bad:
        print("  %-12s %s" % (s, why), flush=True)


if __name__ == "__main__":
    main()
