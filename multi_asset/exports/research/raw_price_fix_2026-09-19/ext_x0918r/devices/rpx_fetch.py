#!/usr/bin/env python3
"""rpx_fetch.py — R5-02 extension (x0918r axis) step 2: rp_fetch.py (sha e6ef1b81…) with the paths of ext_x0918r/; the fetch logic is unchanged.
Download the official Binance USD-M futures 5m kline archives named by rpx_census.py's fetch list from the
public bucket data.binance.vision (no API key, no account call), verify every archive against its published .CHECKSUM (sha256), keep them.

  daily   https://data.binance.vision/data/futures/um/daily/klines/<SYM>/5m/<SYM>-5m-<YYYY-MM-DD>.zip  (+ .CHECKSUM)
  monthly https://data.binance.vision/data/futures/um/monthly/klines/<SYM>/5m/<SYM>-5m-<YYYY-MM>.zip   (+ .CHECKSUM), only when the daily
          file is absent (HTTP 404), once per symbol-month.
Throttle: one request at a time, >= 0.2 s between requests, 3 retries with backoff on network errors (404 is an answer, not retried).
A checksum mismatch is downloaded once more; a second mismatch is recorded CHECKSUM_FAIL and the file is not kept.
Disk: a 512 MB fsync write probe under the output dir before any download (refuses on failure).
Resumable: an archive already on disk whose sha256 equals its kept .CHECKSUM is not downloaded again (status CACHED_VERIFIED).
Writes only under /workspace/raw_price_fix_2026-09-19/ext_x0918r/ (kl/, work/fetch_manifest_x0918r.json, receipts/RPX_FETCH.json).
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_fetch.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, urllib.request, urllib.error
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"

T0 = time.time()
OUT = "/workspace/raw_price_fix_2026-09-19/ext_x0918r"; KL = OUT + "/kl"
CENSUS_RECEIPT = OUT + "/receipts/RPX_CENSUS.json"
BASE = "https://data.binance.vision/data/futures/um"
GAP = 0.2; _last = [0.0]


def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


rec = dict(device="rpx_fetch.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ),
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = OUT + "/receipts/RPX_FETCH.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


cr = json.load(open(CENSUS_RECEIPT)); check("census.PASS", cr.get("VERDICT") == "PASS", {"census_receipt_sha256": sha(CENSUS_RECEIPT)})
FL = cr["fetch"]["path"]; check("fetch_list.sha", sha(FL) == cr["fetch"]["sha256"], {"sha256": sha(FL)[:16]})
if FAILS: finish(3, "RPX_FETCH VERDICT=REFUSED")
jobs = json.load(open(FL))

# ---------------- disk probe ----------------
os.makedirs(KL, exist_ok=True); pp = OUT + "/work/.disk_probe"
try:
    with open(pp, "wb") as f:
        blk = b"\0" * (1 << 20)
        for _ in range(512): f.write(blk)
        f.flush(); os.fsync(f.fileno())
    ok = os.path.getsize(pp) == 512 << 20
except OSError as e:
    ok = False; rec["disk_probe_error"] = repr(e)
finally:
    if os.path.exists(pp): os.remove(pp)
st = os.statvfs(OUT); rec["disk"] = dict(probe_512MB_fsync_ok=ok, statvfs_avail_GB=round(st.f_bavail * st.f_frsize / 1e9, 1),
                                         note="MooseFS statvfs is cluster-wide; the probe is the quota test")
check("disk.probe_512MB", ok)
if FAILS: finish(3, "RPX_FETCH VERDICT=REFUSED")


def get(url):
    """-> (http_status, bytes or None)"""
    for att in range(4):
        w = GAP - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return 404, None
            err = e.code
        except Exception as e:
            err = type(e).__name__
        time.sleep(2.0 * (att + 1))
    return err, None


def fetch_one(kind, sym, tag):
    """kind daily|monthly; tag = YYYY-MM-DD or YYYY-MM. Returns a manifest row."""
    name = f"{sym}-5m-{tag}.zip"; url = f"{BASE}/{kind}/klines/{sym}/5m/{name}"; d = os.path.join(KL, kind, sym); os.makedirs(d, exist_ok=True)
    zp = os.path.join(d, name); cp = zp + ".CHECKSUM"
    row = dict(kind=kind, sym=sym, tag=tag, url=url, path=zp)
    if os.path.exists(zp) and os.path.exists(cp):
        ctxt = open(cp).read().strip().split()
        if len(ctxt) == 2 and ctxt[1] == name and sha(zp) == ctxt[0]:
            row.update(status="CACHED_VERIFIED", sha256=ctxt[0], bytes=os.path.getsize(zp)); return row
    for att in range(2):
        hs, body = get(url)
        if hs == 404:
            row.update(status="MISSING", http=404); return row
        if body is None:
            row.update(status="NET_FAIL", http=hs); return row
        hc, cb = get(url + ".CHECKSUM")
        if cb is None:
            row.update(status="CHECKSUM_MISSING", http=hs, http_checksum=hc); return row
        ctxt = cb.decode().strip().split()
        match = len(ctxt) == 2 and ctxt[1] == name and ctxt[0] == sha_b(body)
        if match:
            with open(zp + ".tmp", "wb") as f: f.write(body); f.flush(); os.fsync(f.fileno())
            os.replace(zp + ".tmp", zp)
            with open(cp + ".tmp", "wb") as f: f.write(cb)
            os.replace(cp + ".tmp", cp)
            row.update(status="OK", http=hs, sha256=sha_b(body), bytes=len(body), checksum_text=cb.decode().strip()); return row
        row.update(checksum_mismatch_attempt=att + 1, got=sha_b(body), published=cb.decode().strip())
    row.update(status="CHECKSUM_FAIL"); return row


manifest = []; months_done = {}
for k, jb in enumerate(jobs):
    r = fetch_one("daily", jb["sym"], jb["day"]); r["why"] = jb["why"]; r["day"] = jb["day"]; manifest.append(r)
    if r["status"] == "MISSING":
        mt = jb["day"][:7]; key = (jb["sym"], mt)
        if key not in months_done:
            months_done[key] = fetch_one("monthly", jb["sym"], mt); months_done[key]["for_days"] = []
            manifest.append(months_done[key])
        months_done[key]["for_days"].append(jb["day"]); r["fallback_monthly"] = months_done[key]["status"]
    if k % 50 == 0: log(k, "/", len(jobs), jb["sym"], jb["day"], r["status"])
    if k % 100 == 0:
        json.dump(manifest, open(OUT + "/work/fetch_manifest_x0918r.json.tmp", "w"), indent=0); os.replace(OUT + "/work/fetch_manifest_x0918r.json.tmp", OUT + "/work/fetch_manifest_x0918r.json")
json.dump(manifest, open(OUT + "/work/fetch_manifest_x0918r.json.tmp", "w"), indent=0); os.replace(OUT + "/work/fetch_manifest_x0918r.json.tmp", OUT + "/work/fetch_manifest_x0918r.json")

from collections import Counter
daily = [m for m in manifest if m["kind"] == "daily"]; monthly = [m for m in manifest if m["kind"] == "monthly"]
rec["counts"] = dict(daily=dict(Counter(m["status"] for m in daily)), monthly=dict(Counter(m["status"] for m in monthly)),
                     symbol_days=len(jobs), symbol_days_covered=int(sum(1 for m in daily if m["status"] in ("OK", "CACHED_VERIFIED") or m.get("fallback_monthly") in ("OK", "CACHED_VERIFIED"))),
                     bytes=int(sum(m.get("bytes", 0) for m in manifest)))
rec["not_covered"] = [dict(sym=m["sym"], day=m["day"], daily=m["status"], monthly=m.get("fallback_monthly"), why=m.get("why")) for m in daily
                      if not (m["status"] in ("OK", "CACHED_VERIFIED") or m.get("fallback_monthly") in ("OK", "CACHED_VERIFIED"))]
check("fetch.no_checksum_fail", not any(m["status"] == "CHECKSUM_FAIL" for m in manifest), {"n": sum(m["status"] == "CHECKSUM_FAIL" for m in manifest)})
check("fetch.no_net_fail", not any(m["status"] in ("NET_FAIL", "CHECKSUM_MISSING") for m in manifest))
rec["outputs"] = dict(manifest=dict(path=OUT + "/work/fetch_manifest_x0918r.json", sha256=sha(OUT + "/work/fetch_manifest_x0918r.json")))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "RPX_FETCH VERDICT=%s daily=%s monthly=%s not_covered=%d" % (rec["VERDICT"], rec["counts"]["daily"], rec["counts"]["monthly"], len(rec["not_covered"])))
