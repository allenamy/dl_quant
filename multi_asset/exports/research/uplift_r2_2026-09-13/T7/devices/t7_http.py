#!/usr/bin/env python3
"""t7_http.py — T7 public market data client (feasibility only; no credentials; no trading/account endpoints).
- Host allowlist: api.upbit.com, api.bithumb.com (quotation/public paths only), data.binance.vision (CDN archive).
  No Binance REST host is reachable through this client, so no Binance trading/account endpoint can be called.
- Per-host rate limit: MIN_INTERVAL = 0.25 s (4 req/s; task cap is 5 req/s per venue).
- 429: back off (Retry-After if present, else 2**attempt s, cap 60) and retry; 418: fatal stop.
- 5xx / timeout / connection error: back off 2**attempt s (cap 30), up to MAX_TRY attempts, then return status=-1.
- Other 4xx: returned immediately (a 404 is a fact, not an error to retry).
- Every attempt is appended to a JSONL log: utc, url, status, elapsed_ms, selected headers, body_len, body_sha256, error.
  HTTP errors are recorded as errors and are never converted into empty results by this module.
"""
import json, time, hashlib, os, urllib.request, urllib.error, urllib.parse, socket, threading

ALLOW_HOSTS = {"api.upbit.com", "api.bithumb.com", "data.binance.vision", "crix-api-cdn.upbit.com", "min-api.cryptocompare.com", "web.archive.org"}   # last two: survivorship-fallback probes only (unofficial / third-party, keyless)
BANNED_PATH_WORDS = ("order", "account", "withdraw", "deposit", "wallet", "api_key", "apikey")
MIN_INTERVAL = 0.25
HOST_INTERVAL = {"web.archive.org": 1.5}   # be gentle with the archive
MAX_TRY = 6
UA = "t7-feasibility-probe/1.0 (public market data; research)"
_last = {}
_lock = threading.Lock()
KEEP_HEADERS = ("remaining-req", "retry-after", "date", "content-type", "content-length", "x-ratelimit-limit",
                "x-ratelimit-remaining", "x-ratelimit-reset", "last-modified", "etag", "server", "cf-cache-status", "x-cache")


class Fatal(Exception):
    pass


def utcnow_iso():
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".%03dZ" % int((t % 1) * 1000)


def get(url, log_path, tag="", timeout=30):
    """Return (status, headers_dict_lowercase, body_bytes). status=-1 means transport failure after retries."""
    u = urllib.parse.urlsplit(url)
    assert u.scheme == "https", url
    assert u.hostname in ALLOW_HOSTS, ("HOST NOT ALLOWED", u.hostname)
    if u.hostname in ("api.upbit.com", "api.bithumb.com"):   # word check on exchange REST paths only (archive paths contain symbols such as ORDERUSDT)
        low = u.path.lower()
        assert not any(w in low for w in BANNED_PATH_WORDS), ("BANNED PATH WORD", url)
        assert u.path.startswith("/v1/market/all") or u.path.startswith("/v1/candles/") or u.path.startswith("/v1/ticker") \
            or u.path.startswith("/public/"), ("ONLY QUOTATION PATHS", url)
    if u.hostname == "data.binance.vision":   # public archive only
        assert u.path.startswith("/data/futures/um/") or u.path.startswith("/data/spot/"), ("ONLY ARCHIVE DATA PATHS", url)
    if u.hostname == "crix-api-cdn.upbit.com":
        assert u.path.startswith("/v1/crix/candles/"), ("ONLY CANDLE PATHS", url)
    if u.hostname == "web.archive.org":   # historical snapshots of the venues' public market lists (survivorship census only)
        assert u.path.startswith("/cdx/search/cdx") or u.path.startswith("/web/"), ("ONLY CDX / SNAPSHOT PATHS", url)
    if u.hostname == "min-api.cryptocompare.com":
        assert u.path.startswith("/data/v2/histo") or u.path.startswith("/data/histo"), ("ONLY HISTO PATHS", url)
    attempt = 0
    while True:
        attempt += 1
        with _lock:   # reserve the next per-host slot, sleep outside the lock (hosts never throttle each other)
            slot = max(time.monotonic(), _last.get(u.hostname, -1e9) + HOST_INTERVAL.get(u.hostname, MIN_INTERVAL))
            _last[u.hostname] = slot
        if slot > time.monotonic():
            time.sleep(slot - time.monotonic())
        t_req = utcnow_iso(); t0 = time.monotonic()
        status, hdr, body, err = -1, {}, b"", None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status = r.status; hdr = {k.lower(): v for k, v in r.headers.items()}; body = r.read()
        except urllib.error.HTTPError as e:
            status = e.code; hdr = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
            try:
                body = e.read()
            except Exception:
                body = b""
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            err = "%s: %s" % (type(e).__name__, e)
        rec = dict(utc=t_req, tag=tag, url=url, attempt=attempt, status=status, elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
                   headers={k: hdr[k] for k in KEEP_HEADERS if k in hdr}, body_len=len(body),
                   body_sha256=hashlib.sha256(body).hexdigest(), error=err,
                   body_head=(body[:240].decode("utf-8", "replace") if (status != 200 or len(body) < 240) and not url.endswith(".zip") else None))
        with open(log_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if status == 418:
            raise Fatal("HTTP 418 (IP ban signal) on %s" % url)
        if status == 429:
            if attempt >= MAX_TRY * 2:
                return status, hdr, body
            ra = hdr.get("retry-after")
            try:
                sl = float(ra) if ra is not None else min(60.0, 2.0 ** attempt)
            except ValueError:
                sl = min(60.0, 2.0 ** attempt)
            time.sleep(sl); continue
        if status == -1 or status >= 500:
            if attempt >= MAX_TRY:
                return status, hdr, body
            time.sleep(min(30.0, 2.0 ** attempt)); continue
        return status, hdr, body


def get_json(url, log_path, tag=""):
    st, hdr, body = get(url, log_path, tag)
    js = None
    if body:
        try:
            js = json.loads(body.decode("utf-8"))
        except Exception:
            js = None
    return st, hdr, body, js
