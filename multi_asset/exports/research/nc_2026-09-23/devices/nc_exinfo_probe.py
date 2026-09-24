#!/usr/bin/env python3
"""ONE read-only exchangeInfo request (lead 2026-09-24): confirm why SCRTUSDT / STORJUSDT left the NC producer's fetch set at 08Z.
Prints ONLY the named symbols' `status` and `contractType` fields verbatim (plus request bookkeeping). PUBLIC endpoint, weight 1.
Order and guards:
  --after-log F --end-regex R   wait (poll 10 s, give up at --wait-deadline-min minutes) until log F has a line matching R — the M3
                                evaluation agent's fetch must have ended first, so the two jobs' weights never overlap; refuses if not seen
  require_quiet_window(>= 10 min) immediately before the request; any HTTP 429 / 418 aborts (no retry; headers recorded); the IP's
  used weight after the request is recorded; the request is logged to <out>.requests.jsonl.
The producer's own Fetcher (treeNC5 shadow_loop_v3.py) is used, loaded with WIDE_SHADOW_HOME pointing at the output directory so nothing
under ~/wide_shadow is written.
usage: ~/wide_shadow/venv/bin/python nc_exinfo_probe.py <tree> <out.json> --after-log F --end-regex R [--symbols A,B] [--wait-deadline-min 60]"""
import argparse, importlib.util, json, os, re, sys, time, urllib.error

HOME = os.path.expanduser("~")
sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
from venue_quiet_window import require_quiet_window


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("out")
    ap.add_argument("--after-log", required=True); ap.add_argument("--end-regex", required=True)
    ap.add_argument("--symbols", default="SCRTUSDT,STORJUSDT"); ap.add_argument("--wait-deadline-min", type=float, default=60)
    a = ap.parse_args(); syms = [s for s in a.symbols.split(",") if s]
    t_end = time.time() + a.wait_deadline_min * 60; rx = re.compile(a.end_regex); seen = None
    while time.time() < t_end:
        if os.path.exists(a.after_log):
            for line in open(a.after_log, errors="replace"):
                if rx.search(line): seen = line.strip()[:300]
        if seen: break
        time.sleep(10)
    if not seen:
        print(f"EXINFO_PROBE REFUSED: end line /{a.end_regex}/ not seen in {a.after_log} within {a.wait_deadline_min} min; no request sent", flush=True); return 3
    print(f"EXINFO_PROBE preceding job ended: {seen}", flush=True)
    require_quiet_window(min_remaining_min=10)
    os.environ["WIDE_SHADOW_HOME"] = os.path.dirname(os.path.abspath(a.out)); os.environ["WIDE_SHADOW_BUNDLE"] = f"{HOME}/wide_shadow/shadow_bundle"
    spec = importlib.util.spec_from_file_location("nc_shadow_loop_exinfo", f"{a.tree}/shadow_loop_v3.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    real = M.urllib.request.urlopen; aborted = {}

    def guarded(url, *x, **k):
        try:
            return real(url, *x, **k)
        except urllib.error.HTTPError as e:
            if e.code in (429, 418):
                aborted.update({"code": e.code, "headers": dict(e.headers.items())}); raise SystemExit(f"EXINFO_PROBE ABORT HTTP {e.code}")
            raise
    M.urllib.request.urlopen = guarded
    fx = M.Fetcher(); t0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    r = fx.get("/fapi/v1/exchangeInfo", {}, 1); used = fx._diag.get("used_weight_1m_last")
    rows = {s["symbol"]: s for s in r.get("symbols", [])}
    rec = {"utc": t0, "path": "/fapi/v1/exchangeInfo", "weight_declared": 1, "used_weight_1m_after": used, "n_symbols_in_response": len(rows),
           "preceding_job_end_line": seen,
           "symbols": {s: ({"status": rows[s].get("status"), "contractType": rows[s].get("contractType")} if s in rows else "ABSENT_FROM_RESPONSE") for s in syms}}
    open(a.out + ".requests.jsonl", "a").write(json.dumps({k: rec[k] for k in ("utc", "path", "weight_declared", "used_weight_1m_after")}) + "\n")
    json.dump(rec, open(a.out, "w"), indent=1)
    print("EXINFO_PROBE " + json.dumps(rec), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
