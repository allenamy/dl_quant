#!/usr/bin/env python3
"""d10_pull_api_funding_ms.py -- the API half of the September extension of ledger_full_ms (runbook 1c; lead s7 ruling 6: the
September API source is re-pulled with MILLISECOND keys).

The August source /workspace/fund_aug.json.gz ({"rates": {sym: [[fundingTime_ms, rate], ...]}, "intervals": {...}}) has no producer
in the repo (ERROR_LEDGER L272 names it missing), so this device is written anew and writes the SAME shape for the window it pulls.
It runs on pod2, never on the Mac: /fapi/v1/fundingRate shares a 500 / 5 min / IP limit with fundingInfo, and the Mac's IP is the
live executor's.

Rules: sequential; >= 0.7 s between requests (~430 per 5 min, under the 500 shared limit); paginate by startTime until a page is
shorter than the limit; keys are fundingTime in ms exactly as served (no // 1000); a (symbol) whose request fails is retried once
and then recorded as FAILED -- the output is written only if no symbol FAILED, otherwise the device exits 4 and writes a receipt that
names the failed symbols and no data file (a partial source must not look like a complete one). Output through durable_write.
usage: d10_pull_api_funding_ms.py --symbols FILE --start-utc 2026-08-31T00:00Z --end-utc 2026-10-01T00:00Z --out OUT.json.gz
       (env D10_API_BASE overrides https://fapi.binance.com for the selftest only; it is recorded in the receipt)
"""
import argparse, datetime, gzip, hashlib, json, os, sys, time, urllib.error, urllib.parse, urllib.request

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW  # every file this device writes goes through it (news2 class fix 2026-09-27)

BASE = os.environ.get("D10_API_BASE", "https://fapi.binance.com")
LIMIT = 1000
SPACING_S = 0.7
_last = [0.0]


def utc_ms(s):
    return int(datetime.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)


def get(path, params):
    dt = time.time() - _last[0]
    if dt < SPACING_S:
        time.sleep(SPACING_S - dt)
    try:
        url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research/1.0"}), timeout=30) as r:
            return 200, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return -1, repr(e)[:120].encode()
    finally:
        _last[0] = time.time()


def pull_symbol(sym, start_ms, end_ms):
    rows, t = [], start_ms
    while True:
        code, b = get("/fapi/v1/fundingRate", {"symbol": sym, "startTime": t, "endTime": end_ms, "limit": LIMIT})
        if code != 200:
            return None, f"http {code} {b[:80]!r}"
        page = json.loads(b)
        rows += [[int(d["fundingTime"]), float(d["fundingRate"])] for d in page]
        if len(page) < LIMIT:
            break
        t = int(page[-1]["fundingTime"]) + 1
    rows.sort()
    if any(rows[i][0] >= rows[i + 1][0] for i in range(len(rows) - 1)):
        return None, "fundingTime not strictly increasing"
    return rows, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True); ap.add_argument("--start-utc", required=True); ap.add_argument("--end-utc", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    syms = [l.strip() for l in open(a.symbols) if l.strip()]
    s_ms, e_ms = utc_ms(a.start_utc), utc_ms(a.end_utc)
    assert s_ms < e_ms
    rates, failed, empty = {}, {}, []
    for i, s in enumerate(syms):
        rows, err = pull_symbol(s, s_ms, e_ms)
        if err:
            rows, err = pull_symbol(s, s_ms, e_ms)          # retry once, then name it
        if err:
            failed[s] = err
            continue
        rates[s] = rows
        if not rows:
            empty.append(s)
        if i % 100 == 0:
            print(f"{i}/{len(syms)} {s} rows={len(rows)}", flush=True)
    rec = {"device": os.path.basename(__file__), "self_sha256": hashlib.sha256(open(os.path.realpath(__file__), "rb").read()).hexdigest(),
           "argv": vars(a), "python": {"version": sys.version.split()[0], "executable": sys.executable}, "base": BASE,
           "started_utc": t0, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "symbols_file_sha256": hashlib.sha256(open(a.symbols, "rb").read()).hexdigest(), "n_symbols": len(syms),
           "window_ms": [s_ms, e_ms], "key": "fundingTime MILLISECONDS as served", "n_rows": sum(len(v) for v in rates.values()),
           "empty_symbols": empty, "failed": failed}
    rp = a.out.replace(".json.gz", "_RECEIPT.json")
    if failed:
        rec["verdict"] = "FAILED_NO_DATA_WRITTEN"
        DW.write_json(rp, rec, indent=1)
        print(f"FAILED {len(failed)} symbols: {sorted(failed)[:8]} -- no data file written", flush=True)
        return 4
    body = gzip.compress(json.dumps({"rates": rates}, separators=(",", ":")).encode(), mtime=0)
    rec["out"] = {"path": a.out, "sha256": DW.write_bytes(a.out, body)}
    rec["verdict"] = "COMPLETE"
    print("receipt_sha256", DW.write_json(rp, rec, indent=1))
    print(f"COMPLETE symbols={len(rates)} rows={rec['n_rows']} empty={len(empty)} out_sha256={rec['out']['sha256']}", flush=True)
    return 0


def _crash(t, v, tb):
    import traceback; traceback.print_exception(t, v, tb); sys.stderr.flush(); os._exit(4)


if __name__ == "__main__":
    sys.excepthook = _crash
    sys.exit(main())
