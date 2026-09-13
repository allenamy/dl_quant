#!/usr/bin/env python3
"""t7_archive_listings.py — historical KRW listing sets from Internet Archive snapshots of the venues' public market lists.
Upbit: api.upbit.com/v1/market/all (list of {market,...}); Bithumb: api.bithumb.com/public/ticker/ALL[_KRW] ({"data":{COIN:{...},"date":...}}; KRW market).
Snapshot choice rule (fixed before fetching): for each venue and calendar half-year, the EARLIEST 200-status snapshot in the CDX list (PROBE_D).
Raw bodies fetched with the id_ modifier (original bytes). Only listing symbols are kept (ticker bodies also carry prices; those are discarded).
Output: receipts/ARCHIVE_listings.json (per snapshot: n_krw, sorted KRW codes, body sha256). Logged."""
import sys, os, json, time, hashlib, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_archive.jsonl"
cdx = json.load(open(T7 + "/receipts/PROBE_D_archive_cdx.json"))["cdx"]
groups = {"upbit": cdx["api.upbit.com/v1/market/all*"]["rows"], "bithumb": cdx["api.bithumb.com/public/ticker/ALL*"]["rows"]}
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "rule": "earliest snapshot per venue per calendar half-year", "snapshots": {}}
for v, rows in groups.items():
    pick = {}
    for r in sorted(rows, key=lambda r: r[0]):
        half = r[0][:4] + ("H1" if int(r[0][4:6]) <= 6 else "H2")
        pick.setdefault(half, r)
    out["snapshots"][v] = {}
    for half, r in sorted(pick.items()):
        ts, orig = r[0], r[1]
        url = f"https://web.archive.org/web/{ts}id_/{orig}"
        st, hdr, body, js = H.get_json(url, LOG, f"archive_{v}_{ts}")
        rec = {"snapshot_ts": ts, "original": orig, "status": st, "body_len": len(body), "body_sha256": hashlib.sha256(body).hexdigest()}
        if body[:2] == b"\x1f\x8b":   # id_ returns the original bytes; many snapshots were stored gzip-encoded
            body = gzip.decompress(body); rec["gunzipped"] = True; rec["decoded_sha256"] = hashlib.sha256(body).hexdigest()
            try: js = json.loads(body.decode("utf-8"))
            except Exception: js = None
        os.makedirs(T7 + "/private/archive_raw", exist_ok=True)
        open(T7 + f"/private/archive_raw/{v}_{ts}.json", "wb").write(body)
        codes = None
        if st == 200 and v == "upbit" and isinstance(js, list):
            codes = sorted(m["market"] for m in js if isinstance(m, dict) and str(m.get("market", "")).startswith("KRW-"))
        elif st == 200 and v == "bithumb" and isinstance(js, dict) and isinstance(js.get("data"), dict):
            codes = sorted("KRW-" + k for k, x in js["data"].items() if k != "date" and isinstance(x, dict))
            rec["bithumb_status_field"] = js.get("status")
        if codes is None:
            rec["PARSE_FAIL"] = True; rec["body_head"] = body[:200].decode("utf-8", "replace")
        else:
            rec["n_krw"] = len(codes); rec["krw_codes"] = codes
        out["snapshots"][v][half] = rec
        print(v, half, ts, st, rec.get("n_krw"), rec.get("PARSE_FAIL"), flush=True)
json.dump(out, open(T7 + "/receipts/ARCHIVE_listings.json", "w"), indent=1, ensure_ascii=False)
