#!/usr/bin/env python3
"""p9_pull_monthly_funding_zips.py — pod2 device (FIXPROGRAM 2026-09-13 P9; lead ruling 15:1xZ: August monthly funding zips approved; user
09-05 exemption for static CDN bulk pulls). Anonymous GET of data.binance.vision monthly fundingRate archives only; no trading/account API.
Rules: sequential, <= 5 requests/s (sleep 0.21 s after every request); sha256 of the IN-MEMORY bytes (and the .CHECKSUM file when served)
before any write; write-probe of the output directory before the first write; never overwrites an existing file; 404 recorded, not retried.
Output: <out>/<SYM>-fundingRate-<MONTH>.zip, <out>/MANIFEST_<MONTH>.json {symbol: {status, bytes, sha256, checksum_file_sha256_field, rows,
iv_counts}}. Usage: python3 -B p9_pull_monthly_funding_zips.py <month YYYY-MM> <symbols file, one per line> <out dir>
rev 2 (news2 class fix 2026-09-27): the exit code is no longer the repair signal. The manifest carries run_nonce (env P9_RUN_NONCE,
else generated and printed) and intended_rc; drivers decide with p9_pull_verdict.py, which requires a manifest from THIS run.
Every file (zip and manifest) is written through common/durable_write.py (temp -> fsync -> read-back -> replace -> fsync dir, temp
removed on failure). The excepthook is installed before any import that can fail."""
import os, sys


def _crash(t, v, tb):
    # rev 1 (lead-approved class fix 2026-09-26): ANY unhandled failure exits 4. Python's default for an uncaught exception is 1,
    # which is also this device's "checksum mismatch" code -- the drivers answer 1 by dropping mismatched files and re-fetching,
    # so a write failure was being handled as a data mismatch. 4 is outside {0, 1}: every driver stops on it, by name.
    import traceback; traceback.print_exception(t, v, tb); sys.stderr.flush(); os._exit(4)


sys.excepthook = _crash
import io, json, time, hashlib, zipfile, csv, uuid, urllib.request, urllib.error
for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the puller")
import durable_write as DW

MONTH, SYMF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NONCE = os.environ.get("P9_RUN_NONCE") or "generated-" + uuid.uuid4().hex
print(f"P9_RUN_NONCE={NONCE}", flush=True)
assert len(MONTH) == 7 and MONTH[4] == "-"
BASE = os.environ.get("P9_BASE", "https://data.binance.vision/data/futures/um/monthly/fundingRate")   # rev 1: override for the self-test only (file://); recorded in the manifest
syms = [l.strip() for l in open(SYMF) if l.strip()]
os.makedirs(OUT, exist_ok=True)
probe = OUT + "/.write_probe"
with open(probe, "wb") as f:  # durable-exempt: 8 MiB space probe, removed on the next line, never read by anyone
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
    if DW.write_bytes(fn, b) != h:
        raise IOError(f"zip written for {s} does not hash to the downloaded bytes")
    man[s] = {"status": 200, "bytes": len(b), "sha256": h, "checksum_file_sha256_field": c_field, "checksum_match": (c_field == h) if c_field else None, "member": name, "rows": len(rows), "iv_counts": ivc}
    if i % 50 == 0: print(f"{i}/{len(syms)} {s} {man[s]['status']} {time.time() - t0:.0f}s", flush=True)
mp = f"{OUT}/MANIFEST_{MONTH}.json"
bad = sum(1 for v in man.values() if v.get("checksum_match") is False)
# rev 2: the manifest states how this run ends (intended_rc) and which run it is (run_nonce); p9_pull_verdict.py checks both.
# The printed sha is the one durable_write returns from the verified bytes, not a later re-read.
_man_sha = DW.write_json(mp, dict(month=MONTH, base=BASE, n_symbols=len(syms), run_nonce=NONCE, intended_rc=1 if bad else 0,
                                  self_sha256=hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                                  durable_write_sha256=hashlib.sha256(open(DW.__file__, "rb").read()).hexdigest(),
                                  symbols_file_sha256=hashlib.sha256(open(SYMF, "rb").read()).hexdigest(),
                                  started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                                  finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), files=man), indent=1)
st = {}
for v in man.values(): st[str(v["status"])] = st.get(str(v["status"]), 0) + 1
print(f"SUMMARY p9_pull_monthly_funding_zips month={MONTH} status={st} checksum_mismatch={bad} manifest_sha256={_man_sha}", flush=True)
sys.exit(1 if bad else 0)
