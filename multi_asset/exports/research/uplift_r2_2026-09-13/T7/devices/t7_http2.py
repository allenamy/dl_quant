#!/usr/bin/env python3
"""t7_http2.py — HTTP client for the T7 full pull (public market data only; no credentials).
Differences from t7_http.py (kept byte-identical for the committed feasibility receipts):
- Host allowlist: api.upbit.com, api.bithumb.com (paths /v1/candles/ and /v1/market/all only), data.binance.vision (futures/um indexPriceKlines only).
- Rate: HARD per-host sliding window — at most 5 requests in any rolling 1.0 s AND at least 0.21 s between consecutive sends
  (the task cap is 5 req/s per host). One worker process per host, so the window is exact within the process.
- Transport (AMENDMENT 1, 2026-09-13): one persistent HTTPS keep-alive connection per host (http.client); any exception or `Connection: close` drops it and the next attempt reconnects.
  Redirects are not followed (a 3xx is returned as a non-200 status). Rate rules above are unchanged.
- Retries: 429 -> Retry-After or 2**n s (cap 60), up to 10 attempts; 5xx / transport -> 2**n s (cap 30), up to 8 attempts; 418 -> Fatal.
  Other 4xx are returned at once (404 on an archive month is a fact, not an error).
- Every attempt appended to the JSONL log: utc, url, attempt, status, elapsed_ms, rate headers, body_len, body_sha256, error, n_in_window.
  HTTP errors are never converted into empty results here."""
import json, time, hashlib, collections, urllib.parse, socket, http.client, ssl
ALLOW = {"api.upbit.com": ("/v1/candles/", "/v1/market/all"), "api.bithumb.com": ("/v1/candles/", "/v1/market/all"),
         "data.binance.vision": ("/data/futures/um/monthly/indexPriceKlines/", "/data/futures/um/daily/indexPriceKlines/")}
MAX_IN_WINDOW = 5; WINDOW_S = 1.0; MIN_GAP_S = 0.21
UA = "t7-krw-pull/1.0 (public market data; research)"
KEEP = ("remaining-req", "retry-after", "x-ratelimit-remaining", "date", "content-type", "content-length", "last-modified", "etag")
_sent = collections.defaultdict(collections.deque)
class Fatal(Exception): pass
def utc_iso(t=None):
    t = time.time() if t is None else t
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".%03dZ" % int((t % 1) * 1000)
def _throttle(host):
    q = _sent[host]
    while True:
        now = time.monotonic()
        while q and now - q[0] >= WINDOW_S: q.popleft()
        wait = 0.0
        if len(q) >= MAX_IN_WINDOW: wait = max(wait, q[0] + WINDOW_S - now + 0.001)
        if q: wait = max(wait, q[-1] + MIN_GAP_S - now)
        if wait <= 0: break
        time.sleep(wait)
    q.append(time.monotonic())
    return len(q)
_conns = {}
def _drop(host):
    c = _conns.pop(host, None)
    if c is not None:
        try: c.close()
        except Exception: pass
def get(url, log_path, tag="", timeout=40):
    u = urllib.parse.urlsplit(url)
    assert u.scheme == "https" and u.hostname in ALLOW, ("HOST NOT ALLOWED", url)
    assert any(u.path.startswith(p) for p in ALLOW[u.hostname]), ("PATH NOT ALLOWED", url)
    target = u.path + ("?" + u.query if u.query else "")
    attempt = 0
    while True:
        attempt += 1
        n_win = _throttle(u.hostname)
        t_req = utc_iso(); t0 = time.monotonic(); status, hdr, body, err = -1, {}, b"", None
        reused = u.hostname in _conns
        try:
            if not reused: _conns[u.hostname] = http.client.HTTPSConnection(u.hostname, timeout=timeout)
            c = _conns[u.hostname]
            c.request("GET", target, headers={"User-Agent": UA, "Accept": "application/json", "Connection": "keep-alive"})
            r = c.getresponse(); body = r.read(); status = r.status; hdr = {k.lower(): v for k, v in r.getheaders()}
            if hdr.get("connection", "").lower() == "close": _drop(u.hostname)
        except (http.client.HTTPException, socket.timeout, TimeoutError, ConnectionError, ssl.SSLError, OSError) as e:
            err = "%s: %s" % (type(e).__name__, e); status = -1; body = b""; _drop(u.hostname)
        rec = {"utc": t_req, "tag": tag, "url": url, "attempt": attempt, "status": status, "elapsed_ms": round((time.monotonic() - t0) * 1000, 1),
               "headers": {k: hdr[k] for k in KEEP if k in hdr}, "body_len": len(body), "body_sha256": hashlib.sha256(body).hexdigest(), "error": err, "n_in_window": n_win, "conn_reused": reused}
        if status != 200 and len(body) < 300 and not url.endswith(".zip"): rec["body_head"] = body.decode("utf-8", "replace")
        with open(log_path, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if status == 418: raise Fatal("HTTP 418 on " + url)
        if status == 429:
            if attempt >= 10: return status, hdr, body
            ra = hdr.get("retry-after")
            try: sl = float(ra) if ra is not None else min(60.0, 2.0 ** attempt)
            except ValueError: sl = min(60.0, 2.0 ** attempt)
            time.sleep(sl); continue
        if status == -1 or status >= 500:
            if attempt >= 8: return status, hdr, body
            time.sleep(min(30.0, 2.0 ** attempt)); continue
        return status, hdr, body
