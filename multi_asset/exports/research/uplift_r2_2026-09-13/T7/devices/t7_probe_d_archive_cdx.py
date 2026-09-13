#!/usr/bin/env python3
"""t7_probe_d_archive_cdx.py — PROBE D: does the Internet Archive hold historical snapshots of the venues' public market lists?
Only CDX index queries (no snapshot bodies yet). Logged."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http as H
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = T7 + "/receipts/http_log_probe_d.jsonl"
out = {"device": os.path.basename(__file__), "run_utc": H.utcnow_iso(), "cdx": {}}
for u in ("api.upbit.com/v1/market/all*", "api.bithumb.com/public/ticker/ALL_KRW*", "api.bithumb.com/public/ticker/ALL*", "api.bithumb.com/v1/market/all*"):
    url = "https://web.archive.org/cdx/search/cdx?url=" + u + "&output=json&fl=timestamp,original,statuscode,mimetype,length&filter=statuscode:200&collapse=timestamp:6&limit=500"
    st, hdr, body, js = H.get_json(url, LOG, "cdx_" + u)
    rows = js[1:] if isinstance(js, list) and js else []
    out["cdx"][u] = {"status": st, "n_snapshots_monthly_collapsed": len(rows), "first": rows[0] if rows else None, "last": rows[-1] if rows else None,
                     "by_year": {y: sum(1 for r in rows if r[0].startswith(y)) for y in ("2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026")},
                     "rows": rows, "body_head": None if st == 200 else body[:200].decode("utf-8", "replace")}
json.dump(out, open(T7 + "/receipts/PROBE_D_archive_cdx.json", "w"), indent=1, ensure_ascii=False)
for k, v in out["cdx"].items():
    print(k, v["status"], v["n_snapshots_monthly_collapsed"], v["first"], v["last"], v["by_year"], v["body_head"])
