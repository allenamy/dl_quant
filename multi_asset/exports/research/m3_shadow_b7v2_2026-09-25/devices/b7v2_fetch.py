#!/usr/bin/env python3
"""b7v2_fetch.py — B7 v2 method (a), research side: the venue's raw 4h klines for the names of ONE v2 shadow anchor's production beta
field, plus one exchangeInfo read (venue status of those names at fetch time). Mac, /usr/bin/python3, standard library only.
Read-only on production: it reads a COPY of target_live/<A>.json (b7v2_copy_inputs.sh), never the live tree.

Requests (lead's pre-approved envelope, 2026-09-25: quiet window only, venue_quiet_window.py passed at start, ≤ 500 requests, 1-minute
used weight ≤ 300, 429/418 guards; command, request count and peak weight go verbatim into the receipt):
  1 × GET https://fapi.binance.com/fapi/v1/exchangeInfo                                   (weight 1)
  n × GET https://fapi.binance.com/fapi/v1/klines?symbol=S&interval=4h&startTime=(A−181·4h)·1000&endTime=A·1000−1&limit=200
      (open times A−181·4h … A−4h ⇒ 181 klines = the closes at every boundary A−180·4h … A; limit 200 ⇒ weight 2)
  total requests n + 1; refused at start if n + 1 > 500.
GUARDS:
  * quiet window: venue_quiet_window.require_quiet_window(min_remaining_min=20) before the first request (SystemExit if closed); before
    EVERY request the window must be open with ≥ 5 min left, else ABORT (no waiting across windows, no resume inside a run);
    VENUE_QUIET_WINDOW_OVERRIDE set ⇒ refused;
  * weight: every response's X-MBX-USED-WEIGHT-1M is read; > 300 ⇒ ABORT; a response without the header ⇒ ABORT (unknown is not below the
    limit); ≥ 240 ⇒ SOFT BRAKE: sleep until 2 s past the next minute boundary before the next request (logged); requests paced ≥ 0.5 s
    apart (≤ 240 weight/min from this process);
  * HTTP 429 or 418 ⇒ ABORT at once; no request is ever retried; any other non-200 / transport error ⇒ that symbol FAILED (named).
Outputs (<out_dir>): KLINES_RAW.jsonl.gz ({"symbol","status","body"} per symbol, body = venue text unparsed), EXINFO_SUBSET.json
({symbol: {status, contractType, deliveryDate}} for the field's names; absent names listed; full body sha256), FETCH_LOG.jsonl (one line
per request), FETCH_MANIFEST.json (verdict COMPLETE / ABORTED_<reason> / PARTIAL_FAILED_SYMBOLS, n_requests, max_used_weight_1m,
n_soft_brakes, shas). Last stdout line: B7V2_FETCH A=<A> VERDICT=… n_requests=… max_used_weight_1m=… manifest_sha256=…
usage: /usr/bin/python3 -B b7v2_fetch.py <inputs_dir with target_live/<A>.json> <A> <out_dir>
"""
import gzip, hashlib, json, os, sys, time, urllib.error, urllib.request

sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common")
import venue_quiet_window as VQW

H4 = 14400
LIMIT = 200
MAX_REQUESTS = 500
WEIGHT_ABORT = 300
WEIGHT_BRAKE = 240
PACE_S = 0.5
KL_URL = "https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=4h&startTime={a}&endTime={b}&limit={n}"
EX_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
_urlopen = urllib.request.urlopen        # replaced by the self-test's fake transport
_sleep = time.sleep
_now = time.time


def sha(b): return hashlib.sha256(b).hexdigest()


def sha_file(p):
    with open(p, "rb") as f: return sha(f.read())


def get(url):
    status, body, wt, err = None, b"", None, None
    try:
        with _urlopen(urllib.request.Request(url, headers={"User-Agent": "quant-research-b7v2/1"}), timeout=20) as r:
            status = r.status; body = r.read(); wt = r.headers.get("X-MBX-USED-WEIGHT-1M")
    except urllib.error.HTTPError as e:
        status = e.code; body = (e.read() or b"") if hasattr(e, "read") else b""
        wt = e.headers.get("X-MBX-USED-WEIGHT-1M") if getattr(e, "headers", None) else None; err = f"HTTPError {e.code}"
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:200]}"
    return status, body, wt, err


def main(argv):
    inp, A, out = os.path.abspath(argv[1]), int(argv[2]), os.path.abspath(argv[3]); os.makedirs(out, exist_ok=True)
    if A % H4: raise SystemExit(f"A={A} not on the 4h grid — refused")
    if os.environ.get("VENUE_QUIET_WINDOW_OVERRIDE"): raise SystemExit("VENUE_QUIET_WINDOW_OVERRIDE is set — refused")
    p = os.path.join(inp, "target_live", f"{A}.json"); d = json.load(open(p)); b = d.get("beta_overlay")
    if not isinstance(b, dict) or not isinstance(b.get("betas"), dict) or not b["betas"]: raise SystemExit(f"{p}: no beta_overlay.betas — refused")
    names = sorted(b["betas"])
    if "BTCUSDT" not in names: raise SystemExit("BTCUSDT not in the production name list — refused")
    if len(names) + 1 > MAX_REQUESTS: raise SystemExit(f"{len(names) + 1} requests > envelope {MAX_REQUESTS} — refused (ask the lead)")
    start_ms, end_ms = (A - 181 * H4) * 1000, A * 1000 - 1
    man = {"device": "b7v2_fetch.py", "self_sha256": sha_file(os.path.abspath(__file__)), "vqw_sha256": sha_file(VQW.__file__), "anchor": A,
           "production_field": {"path": p, "sha256": sha_file(p), "version": b.get("version"), "n_betas": len(names)},
           "start_ms": start_ms, "end_ms": end_ms, "limit": LIMIT, "n_klines_expected": 181, "envelope": {"max_requests": MAX_REQUESTS,
           "weight_abort_above": WEIGHT_ABORT, "soft_brake_at": WEIGHT_BRAKE, "pace_s": PACE_S},
           "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now())), "quiet_window_at_start": VQW.require_quiet_window(min_remaining_min=20)}
    logf = open(os.path.join(out, "FETCH_LOG.jsonl"), "w"); rawf = gzip.open(os.path.join(out, "KLINES_RAW.jsonl.gz"), "wt")
    failed, done, max_w, verdict, last_t, n_req, n_brake = [], 0, None, "COMPLETE", 0.0, 0, 0
    ex_sub = None
    queue = [("__exchangeInfo__", EX_URL)] + [(s, KL_URL.format(s=s, a=start_ms, b=end_ms, n=LIMIT)) for s in names]
    for i, (s, url) in enumerate(queue):
        st = VQW.quiet_window_status()
        if not st["open"] or st["remaining_min"] < 5:
            verdict = f"ABORTED_quiet_window_closing ({st.get('reason') or 'remaining ' + str(st['remaining_min']) + ' min'})"; break
        dt = _now() - last_t
        if dt < PACE_S: _sleep(PACE_S - dt)
        t0 = _now(); last_t = t0; n_req += 1
        status, body, wt, err = get(url)
        rec = {"i": i, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "symbol": s, "url": url, "status": status, "used_weight_1m": wt,
               "bytes": len(body), "body_sha256": sha(body), "elapsed_ms": round(1000 * (_now() - t0), 1), "error": err}
        n_k = None
        if status == 200 and s != "__exchangeInfo__":
            try: n_k = len(json.loads(body.decode()))
            except Exception as e: rec["error"] = f"unparseable body: {type(e).__name__}"; status = -1
        rec["n_klines"] = n_k
        wi = None
        if wt is not None:
            try: wi = int(wt); max_w = max(max_w or 0, wi)
            except ValueError: rec["error"] = f"weight header not an int: {wt!r}"
        brake = wi is not None and WEIGHT_BRAKE <= wi <= WEIGHT_ABORT
        rec["soft_brake"] = brake
        logf.write(json.dumps(rec) + "\n"); logf.flush()
        if status in (429, 418): verdict = f"ABORTED_http_{status}"; failed.append(s); break
        if status is not None and wi is None: verdict = "ABORTED_no_or_bad_weight_header"; failed.append(s); break
        if wi is not None and wi > WEIGHT_ABORT:
            verdict = f"ABORTED_weight_{wi}_above_{WEIGHT_ABORT}"
            if status == 200 and s != "__exchangeInfo__": rawf.write(json.dumps({"symbol": s, "status": status, "body": body.decode()}) + "\n"); done += 1
            break
        if s == "__exchangeInfo__":
            if status != 200: verdict = f"ABORTED_exchangeInfo_status_{status}"; break
            try:
                E = json.loads(body.decode()); by = {x["symbol"]: x for x in E["symbols"]}
            except Exception as e:
                verdict = f"ABORTED_exchangeInfo_unparseable_{type(e).__name__}"; break
            ex_sub = {"body_sha256": sha(body), "server_time_ms": E.get("serverTime"), "fetched_utc": rec["utc"],
                      "symbols": {n: {k: by[n].get(k) for k in ("status", "contractType", "deliveryDate")} for n in names if n in by},
                      "absent": [n for n in names if n not in by]}
        elif status == 200:
            rawf.write(json.dumps({"symbol": s, "status": status, "body": body.decode()}) + "\n"); done += 1
        else:
            failed.append(s)
        if brake:
            n_brake += 1; now = _now(); _sleep((int(now // 60) + 1) * 60 + 2 - now)
    rawf.close(); logf.close()
    if ex_sub is not None: json.dump(ex_sub, open(os.path.join(out, "EXINFO_SUBSET.json"), "w"), indent=1, sort_keys=True)
    if verdict == "COMPLETE" and failed: verdict = "PARTIAL_FAILED_SYMBOLS"
    outs = {f: sha_file(os.path.join(out, f)) for f in ("KLINES_RAW.jsonl.gz", "FETCH_LOG.jsonl", "EXINFO_SUBSET.json") if os.path.isfile(os.path.join(out, f))}
    man.update(verdict=verdict, n_requests=n_req, n_ok=done, n_failed=len(failed), failed=failed, n_not_attempted=len(names) - done - len([f for f in failed if f != "__exchangeInfo__"]),
               max_used_weight_1m=max_w, n_soft_brakes=n_brake, utc_end=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now())), outputs=outs)
    json.dump(man, open(os.path.join(out, "FETCH_MANIFEST.json"), "w"), indent=1)
    print(f"B7V2_FETCH A={A} VERDICT={verdict} n_requests={n_req} ok={done} failed={len(failed)} max_used_weight_1m={max_w} soft_brakes={n_brake} "
          f"manifest_sha256={sha_file(os.path.join(out, 'FETCH_MANIFEST.json'))}", flush=True)
    return 0 if verdict == "COMPLETE" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
