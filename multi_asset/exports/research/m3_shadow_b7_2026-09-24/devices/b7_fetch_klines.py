#!/usr/bin/env python3
"""b7_fetch_klines.py — M3 shadow acceptance B7 (AMENDMENT_2 §3 step 4, item 2), research side: pull raw 4h klines from the venue for the
names the PRODUCTION beta field uses at the first two NC anchors (2026-09-24T08Z / 12Z), plus the positive-control anchor 2026-09-18T20Z.
Mac, /usr/bin/python3, standard library only (urllib). Read-only on production: it reads COPIES of target_live/<A>.json made by
b7_copy_inputs.sh (their sha256 are in the copy receipt), never the live tree.

Endpoint: GET https://fapi.binance.com/fapi/v1/klines?symbol=S&interval=4h&startTime=1787155200000&endTime=1790251199999&limit=300
  (open times 2026-08-19T16Z … 2026-09-24T08Z = 215 klines = the closes at every 4h boundary from 2026-08-19T20Z to 2026-09-24T12Z; the
  180-bar windows of all three anchors need boundaries A − 180×4h … A). limit 300 ⇒ request weight 2 (venue table: 100 ≤ limit < 500).
GUARDS (lead, 2026-09-24):
  * quiet window: venue_quiet_window.require_quiet_window(min_remaining_min=20) before the first request, and before EVERY request the
    window must still be open with ≥ 5 min left — otherwise ABORT (no waiting across a window, no partial resume inside this run);
  * weight: every response's X-MBX-USED-WEIGHT-1M is read; a value > 1200 ⇒ ABORT; a response WITHOUT the header ⇒ ABORT (unknown is not
    below the limit); requests are paced ≥ 0.35 s apart (≤ ~6 weight/s from this process);
  * HTTP 429 or 418 ⇒ ABORT at once, no retry; no request is ever retried;
  * any other non-200 or a transport error ⇒ that symbol is recorded FAILED (named in the manifest, MISSING downstream), no retry;
  * one JSONL log line per request: utc, symbol, url, status, used_weight_1m, n_klines, bytes, body sha256, elapsed_ms, error.
Outputs (<out_dir>): KLINES_RAW.jsonl.gz (one line per symbol: {"symbol", "status", "body"} — the body is the venue's bytes decoded as
text, unparsed), FETCH_LOG.jsonl, FETCH_MANIFEST.json (verdict COMPLETE / ABORTED_<reason> / PARTIAL_FAILED_SYMBOLS, counts, shas).
usage: /usr/bin/python3 -B b7_fetch_klines.py <inputs_dir with target_live copies> <out_dir>
"""
import gzip, hashlib, json, os, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common")
import venue_quiet_window as VQW

A08, A12, ACTRL = 1790236800, 1790251200, 1789761600
H4 = 14400
START_MS = (ACTRL - 181 * H4) * 1000                       # 2026-08-19T16:00Z (open time of the kline closing at ACTRL − 180×4h)
END_MS = A12 * 1000 - 1                                   # excludes the kline opening at A12 (still open at A12)
LIMIT = 300
N_EXPECT = (A12 - H4 - (ACTRL - 181 * H4)) // H4 + 1       # 215
WEIGHT_ABORT = 1200
PACE_S = 0.35
URL = "https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=4h&startTime={a}&endTime={b}&limit={n}"


def sha(b): return hashlib.sha256(b).hexdigest()


def sha_file(p):
    with open(p, "rb") as f: return sha(f.read())


def main():
    inp, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]); os.makedirs(out, exist_ok=True)
    if os.environ.get("VENUE_QUIET_WINDOW_OVERRIDE"): raise SystemExit("VENUE_QUIET_WINDOW_OVERRIDE is set — refused (no override for B7)")
    names = set(); src = {}
    for A in (A08, A12):
        p = os.path.join(inp, "target_live", f"{A}.json")
        d = json.load(open(p)); b = d.get("beta_overlay")
        if not isinstance(b, dict) or not isinstance(b.get("betas"), dict) or not b["betas"]: raise SystemExit(f"{p}: no beta_overlay.betas — refused")
        names |= set(b["betas"]); src[str(A)] = {"path": p, "sha256": sha_file(p), "n_betas": len(b["betas"])}
    names = sorted(names)
    if "BTCUSDT" not in names: raise SystemExit("BTCUSDT not in the production name list — refused")
    man = {"device": "b7_fetch_klines.py", "self_sha256": sha_file(os.path.abspath(__file__)), "vqw_sha256": sha_file(VQW.__file__),
           "production_name_sources": src, "n_symbols": len(names), "start_ms": START_MS, "end_ms": END_MS, "limit": LIMIT,
           "n_klines_expected_full_history": N_EXPECT, "weight_abort_above": WEIGHT_ABORT, "pace_s": PACE_S,
           "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "quiet_window_at_start": VQW.require_quiet_window(min_remaining_min=20)}
    logf = open(os.path.join(out, "FETCH_LOG.jsonl"), "w"); rawf = gzip.open(os.path.join(out, "KLINES_RAW.jsonl.gz"), "wt")
    failed, done, max_w, verdict, last_t = [], 0, None, "COMPLETE", 0.0
    for i, s in enumerate(names):
        st = VQW.quiet_window_status()
        if not st["open"] or st["remaining_min"] < 5:
            verdict = f"ABORTED_quiet_window_closing ({st.get('reason') or 'remaining ' + str(st['remaining_min']) + ' min'})"; break
        dt = time.time() - last_t
        if dt < PACE_S: time.sleep(PACE_S - dt)
        url = URL.format(s=s, a=START_MS, b=END_MS, n=LIMIT); t0 = time.time(); last_t = t0
        rec = {"i": i, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "symbol": s, "url": url}
        status, body, wt, err = None, b"", None, None
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "quant-research-b7/1"}), timeout=20) as r:
                status = r.status; body = r.read(); wt = r.headers.get("X-MBX-USED-WEIGHT-1M")
        except urllib.error.HTTPError as e:
            status = e.code; body = e.read() or b""; wt = e.headers.get("X-MBX-USED-WEIGHT-1M") if e.headers else None; err = f"HTTPError {e.code}"
        except Exception as e:                                             # transport error: this symbol FAILED, no retry
            err = f"{type(e).__name__}: {str(e)[:200]}"
        rec.update(status=status, used_weight_1m=wt, bytes=len(body), body_sha256=sha(body), elapsed_ms=round(1000 * (time.time() - t0), 1), error=err)
        n_k = None
        if status == 200:
            try: n_k = len(json.loads(body.decode()))
            except Exception as e: rec["error"] = f"unparseable body: {type(e).__name__}"; status = -1
        rec["n_klines"] = n_k
        logf.write(json.dumps(rec) + "\n"); logf.flush()
        if wt is not None:
            try: max_w = max(max_w or 0, int(wt))
            except ValueError: pass
        if status in (429, 418):
            verdict = f"ABORTED_http_{status}"; failed.append(s); break
        if status is not None and wt is None:
            verdict = "ABORTED_no_weight_header"; failed.append(s); break
        if wt is not None and int(wt) > WEIGHT_ABORT:
            verdict = f"ABORTED_weight_{wt}_above_{WEIGHT_ABORT}"
            if status == 200: rawf.write(json.dumps({"symbol": s, "status": status, "body": body.decode()}) + "\n"); done += 1
            break
        if status == 200:
            rawf.write(json.dumps({"symbol": s, "status": status, "body": body.decode()}) + "\n"); done += 1
        else:
            failed.append(s)
    rawf.close(); logf.close()
    if verdict == "COMPLETE" and failed: verdict = "PARTIAL_FAILED_SYMBOLS"
    man.update(verdict=verdict, n_ok=done, n_failed=len(failed), failed=failed, n_not_attempted=len(names) - done - len(failed),
               max_used_weight_1m=max_w, utc_end=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               outputs={f: sha_file(os.path.join(out, f)) for f in ("KLINES_RAW.jsonl.gz", "FETCH_LOG.jsonl")})
    json.dump(man, open(os.path.join(out, "FETCH_MANIFEST.json"), "w"), indent=1)
    print(f"B7_FETCH VERDICT={verdict} ok={done} failed={len(failed)} max_used_weight_1m={max_w} manifest_sha256={sha_file(os.path.join(out, 'FETCH_MANIFEST.json'))}", flush=True)
    sys.exit(0 if verdict == "COMPLETE" else 2)


if __name__ == "__main__":
    main()
