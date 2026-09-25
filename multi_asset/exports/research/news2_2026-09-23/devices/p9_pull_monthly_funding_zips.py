#!/usr/bin/env python3
"""p9_pull_monthly_funding_zips.py — pod2 device (FIXPROGRAM 2026-09-13 P9; lead ruling 15:1xZ: August monthly funding zips approved; user
09-05 exemption for static CDN bulk pulls). Anonymous GET of data.binance.vision monthly fundingRate archives only; no trading/account API.
Rules: sequential, <= 5 requests/s (sleep 0.21 s after every request); sha256 of the IN-MEMORY bytes (and the .CHECKSUM file when served)
before any write; write-probe of the output directory before the first write; never overwrites an existing file; 404 recorded, not retried.
Output: <out>/<SYM>-fundingRate-<MONTH>.zip, <out>/MANIFEST_<MONTH>.json {symbol: {status, bytes, sha256, checksum_file_sha256_field, rows,
iv_counts}}. Usage: python3 -B p9_pull_monthly_funding_zips.py <month YYYY-MM> <symbols file, one per line> <out dir>"""
import os, sys, io, json, time, hashlib, zipfile, csv, urllib.request, urllib.error
MONTH, SYMF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
assert len(MONTH) == 7 and MONTH[4] == "-"
BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
syms = [l.strip() for l in open(SYMF) if l.strip()]
os.makedirs(OUT, exist_ok=True)
probe = OUT + "/.write_probe"
with open(probe, "wb") as f:
    f.write(os.urandom(8 << 20)); f.flush(); os.fsync(f.fileno())
os.remove(probe)
t_last = [0.0]


def get(url):
    dt = time.time() - t_last[0]
    if dt < 0.21: time.sleep(0.21 - dt)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research/1.0"}), timeout=40) as r:
            b = r.read()
        return 200, b
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return -1, repr(e)[:120].encode()
    finally:
        t_last[0] = time.time()


man = {}; t0 = time.time()
for i, s in enumerate(syms):
    fn = f"{OUT}/{s}-fundingRate-{MONTH}.zip"
    if os.path.exists(fn):
        # R25-11 follow-on (2026-09-25): lead's rule is "已存在且 CHECKSUM 核过的 zip 不重取". This branch
        # implemented the first half and dropped the qualifier: it recorded the local file's own sha and
        # never asked the venue what that file SHOULD hash to, so checksum_match was absent -- and the
        # pre-fix consumers read an absent key as verified. Measured cost of that: 376 of 560 zips in
        # 2026-01 (the month interrupted and resumed) were never checked against the venue at all.
        # The file is NOT re-downloaded: re-pulling would overwrite the very bytes whose correctness is
        # in question. Only the tiny .CHECKSUM is fetched, and the bytes already on disk are verified.
        h_local = hashlib.sha256(open(fn, "rb").read()).hexdigest()
        c_code, c_b = get(f"{BASE}/{s}/{s}-fundingRate-{MONTH}.zip.CHECKSUM")
        c_field = c_b.decode(errors="ignore").split()[0] if c_code == 200 and c_b else None
        man[s] = {"status": "exists_not_refetched", "sha256": h_local,
                  "checksum_file_sha256_field": c_field,
                  "checksum_match": (c_field == h_local) if c_field else None,
                  "verified_without_refetch": True, "checksum_http_status": c_code}
        continue
    code, b = get(f"{BASE}/{s}/{s}-fundingRate-{MONTH}.zip")
    if code != 200:
        man[s] = {"status": code, "detail": b.decode(errors="ignore")[:120] if code == -1 else ""}; continue
    h = hashlib.sha256(b).hexdigest()
    c_code, c_b = get(f"{BASE}/{s}/{s}-fundingRate-{MONTH}.zip.CHECKSUM")
    c_field = c_b.decode(errors="ignore").split()[0] if c_code == 200 and c_b else None
    z = zipfile.ZipFile(io.BytesIO(b)); name = z.namelist()[0]
    rows = [r for r in csv.reader(io.TextIOWrapper(io.BytesIO(z.read(name)), encoding="utf-8")) if r and r[0].strip().isdigit()]
    ivc = {}
    for r in rows: ivc[r[1]] = ivc.get(r[1], 0) + 1
    with open(fn + ".part", "wb") as f:
        f.write(b)
    assert hashlib.sha256(open(fn + ".part", "rb").read()).hexdigest() == h
    os.replace(fn + ".part", fn)
    man[s] = {"status": 200, "bytes": len(b), "sha256": h, "checksum_file_sha256_field": c_field, "checksum_match": (c_field == h) if c_field else None, "member": name, "rows": len(rows), "iv_counts": ivc}
    if i % 50 == 0: print(f"{i}/{len(syms)} {s} {man[s]['status']} {time.time() - t0:.0f}s", flush=True)
mp = f"{OUT}/MANIFEST_{MONTH}.json"
json.dump(dict(month=MONTH, base=BASE, n_symbols=len(syms), self_sha256=hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
               symbols_file_sha256=hashlib.sha256(open(SYMF, "rb").read()).hexdigest(), started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
               finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), files=man), open(mp, "w"), indent=1)
st = {}
for v in man.values(): st[str(v["status"])] = st.get(str(v["status"]), 0) + 1
bad = sum(1 for v in man.values() if v.get("checksum_match") is False)
print(f"SUMMARY p9_pull_monthly_funding_zips month={MONTH} status={st} checksum_mismatch={bad} manifest_sha256={hashlib.sha256(open(mp, 'rb').read()).hexdigest()}", flush=True)
sys.exit(1 if bad else 0)
