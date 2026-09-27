#!/usr/bin/env python3
"""tests_d10_pull_api_funding_ms.py -- controls for d10_pull_api_funding_ms.py against a LOCAL fake /fapi/v1/fundingRate (no network).
  G   AUSDT spans two pages (1000 + 3 rows): paginated, millisecond keys kept exactly (…003, not …000), output gz parses to the
      fund_aug shape, receipt COMPLETE, rc 0
  G2  CUSDT has no rows in the window: listed in empty_symbols, still COMPLETE
  R1  BUSDT answers HTTP 500 twice: rc 4, receipt FAILED_NO_DATA_WRITTEN naming BUSDT, and NO data file at all
  R2  DUSDT serves a repeated fundingTime: rc 4, named "not strictly increasing", no data file
usage: python3 -B tests_d10_pull_api_funding_ms.py [out.json]
"""
import gzip, hashlib, http.server, json, os, subprocess, sys, tempfile, threading, urllib.parse

HERE = os.path.dirname(os.path.realpath(__file__))
DEV = os.path.join(HERE, "d10_pull_api_funding_ms.py")
T0 = 1788220800000


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        s, start = q["symbol"], int(q["startTime"])
        if s == "BUSDT":
            self.send_response(500); self.end_headers(); return
        if s == "AUSDT":
            allrows = [{"symbol": s, "fundingTime": T0 + 3 + i * 3600000, "fundingRate": "0.0001"} for i in range(1003)]
        elif s == "DUSDT":
            allrows = [{"symbol": s, "fundingTime": T0, "fundingRate": "0.1"}, {"symbol": s, "fundingTime": T0, "fundingRate": "0.2"}]
        else:
            allrows = []
        page = [r for r in allrows if r["fundingTime"] >= start][:1000]
        b = json.dumps(page).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


def run(syms, out):
    d = os.path.dirname(out)
    sf = os.path.join(d, "syms.txt"); open(sf, "w").write("\n".join(syms) + "\n")  # durable-exempt: selftest fixture in a mkdtemp dir
    env = dict(os.environ, D10_API_BASE=f"http://127.0.0.1:{PORT}")
    p = subprocess.run([sys.executable, "-B", DEV, "--symbols", sf, "--start-utc", "2026-08-31T00:00Z", "--end-utc", "2026-10-01T00:00Z",
                        "--out", out], capture_output=True, text=True, env=env, timeout=300)
    rp = out.replace(".json.gz", "_RECEIPT.json")
    return p.returncode, (json.load(open(rp)) if os.path.exists(rp) else None), p.stdout + p.stderr


srv = http.server.HTTPServer(("127.0.0.1", 0), H)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
RES = {}
d = tempfile.mkdtemp(prefix="apims_"); out = os.path.join(d, "api.json.gz")
rc, rec, o = run(["AUSDT", "CUSDT"], out)
ok = rc == 0 and rec and rec["verdict"] == "COMPLETE" and os.path.exists(out)
if ok:
    data = json.loads(gzip.open(out, "rt").read())["rates"]
    ok = len(data["AUSDT"]) == 1003 and data["AUSDT"][0][0] == T0 + 3 and data["CUSDT"] == [] and rec["empty_symbols"] == ["CUSDT"] \
        and rec["out"]["sha256"] == hashlib.sha256(open(out, "rb").read()).hexdigest()
RES["G_pagination_ms_keys_shape"] = {"rc": rc, "pass": bool(ok)}
RES["G2_empty_symbol_named"] = {"pass": bool(rec and rec.get("empty_symbols") == ["CUSDT"])}
d = tempfile.mkdtemp(prefix="apims_"); out = os.path.join(d, "api.json.gz")
rc, rec, o = run(["AUSDT", "BUSDT"], out)
RES["R1_http_error_rc4_no_data"] = {"rc": rc, "pass": rc == 4 and rec and rec["verdict"] == "FAILED_NO_DATA_WRITTEN"
                                    and "BUSDT" in rec["failed"] and not os.path.exists(out)}
d = tempfile.mkdtemp(prefix="apims_"); out = os.path.join(d, "api.json.gz")
rc, rec, o = run(["DUSDT"], out)
RES["R2_non_increasing_rc4_no_data"] = {"rc": rc, "pass": rc == 4 and rec and "strictly" in rec["failed"].get("DUSDT", "") and not os.path.exists(out)}
srv.shutdown()
ok = all(v["pass"] for v in RES.values())
for k, v in RES.items():
    print(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k} {v.get('rc', '')}")
print("API_MS_PULLER_TESTS", "ALL_PASS" if ok else "RED")
if len(sys.argv) > 1:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "common"))
    import durable_write as DW
    print("receipt_sha256", DW.write_json(sys.argv[1], {"device_sha256": hashlib.sha256(open(DEV, "rb").read()).hexdigest(),
                                                        "tests_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                                                        "python": sys.version.split()[0], "cells": RES, "ALL_PASS": ok}, indent=1))
sys.exit(0 if ok else 1)
