"""l2_net.py — public-archive HTTP client for the L2 pod2 devices (data.binance.vision CDN + its S3 listing endpoint only).
User ruling 2026-09-05 01:5xZ (STATE.md): bulk pulls from the data.binance.vision static CDN on pod2 are exempt from the
exchange-API rate rule; lead AMENDMENT 1 (PROGRAM_uplift_r3 §AMENDMENT 1) caps this line at <= 20 req/s, halved to 10 req/s
whenever pod2 PID 333197 (another researcher's paused collector) is not in a stopped state. No exchange API host is ever contacted
(asserted per request). Every request outcome is counted; 404 is recorded as 'missing', never retried and never read as 'no trading'."""
import http.client, threading, time, re, ssl, subprocess, hashlib, io, zipfile, csv, calendar
import numpy as np
from urllib.parse import quote

HOSTS = {"data.binance.vision", "s3.ap-northeast-1.amazonaws.com"}
PREFIX = "data/futures/um/daily/metrics/"
MAX_RATE = 20.0
COLS = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
        "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]


def collector_state():
    try:
        out = subprocess.run(["ps", "-o", "stat=", "-p", "333197"], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as e:
        return "ERR " + repr(e)
    return out or "GONE"


class Limiter:
    """Global token pacing: at most `rate` request starts per second across all threads; rate re-evaluated every 30 s from PID 333197."""
    def __init__(self):
        self.lock = threading.Lock(); self.next_t = 0.0; self.rate = MAX_RATE; self.last_check = 0.0; self.states = {}
    def _refresh(self, now):
        if now - self.last_check >= 30.0:
            st = collector_state(); self.last_check = now
            self.states[st] = self.states.get(st, 0) + 1
            self.rate = MAX_RATE if st.startswith("T") or st == "GONE" else MAX_RATE / 2.0
    def wait(self):
        with self.lock:
            now = time.monotonic(); self._refresh(now)
            t = max(now, self.next_t); self.next_t = t + 1.0 / self.rate
        d = t - time.monotonic()
        if d > 0:
            time.sleep(d)


class Client:
    def __init__(self, limiter, timeout=25.0):
        self.lim = limiter; self.timeout = timeout; self.tl = threading.local(); self.ctx = ssl.create_default_context()
        self.lock = threading.Lock(); self.counts = {}; self.n_requests = 0; self.bytes = 0
    def _count(self, k):
        with self.lock:
            self.counts[k] = self.counts.get(k, 0) + 1
    def _conn(self, host):
        conns = getattr(self.tl, "conns", None)
        if conns is None:
            conns = self.tl.conns = {}
        c = conns.get(host)
        if c is None:
            c = conns[host] = http.client.HTTPSConnection(host, timeout=self.timeout, context=self.ctx)
        return c
    def _drop(self, host):
        conns = getattr(self.tl, "conns", {})
        c = conns.pop(host, None)
        if c is not None:
            try:
                c.close()
            except Exception:
                pass
    def get(self, host, path, tries=3):
        """Returns (status, body_bytes or None). status None = transport failure after all tries."""
        assert host in HOSTS, ("host not allowed", host)
        last = None
        for a in range(tries):
            self.lim.wait()
            with self.lock:
                self.n_requests += 1
            try:
                c = self._conn(host); c.request("GET", path, headers={"User-Agent": "research-archive-pull", "Connection": "keep-alive"})
                r = c.getresponse(); body = r.read(); st = r.status
                with self.lock:
                    self.bytes += len(body)
                if st == 200:
                    self._count("200"); return 200, body
                if st == 404:
                    self._count("404"); return 404, None
                if st in (418, 429):
                    self._count(str(st)); ra = r.getheader("Retry-After"); time.sleep(min(120.0, float(ra) if ra and ra.isdigit() else 60.0)); continue
                self._count(str(st)); last = st
                if 400 <= st < 500:
                    return st, None
                time.sleep(1.0 + a)
            except Exception as e:
                self._count("EXC " + type(e).__name__); self._drop(host); last = None; time.sleep(1.0 + a)
        return last, None


def list_symbol(client, sym):
    """S3 ListObjectsV2 over PREFIX/sym/. Returns dict(zip_dates, checksum_dates, pages, ok). ok=False if any page failed (never 'no data')."""
    zips, chks = set(), set(); token = None; pages = 0
    for _ in range(50):
        q = "list-type=2&max-keys=1000&prefix=" + quote(PREFIX + sym + "/", safe="")
        if token:
            q += "&continuation-token=" + quote(token, safe="")
        st, body = client.get("s3.ap-northeast-1.amazonaws.com", "/data.binance.vision?" + q)
        if st != 200:
            return dict(zip_dates=sorted(zips), checksum_dates=sorted(chks), pages=pages, ok=False, fail_status=st)
        pages += 1; txt = body.decode("utf-8", "replace")
        for key in re.findall(r"<Key>([^<]+)</Key>", txt):
            m = re.fullmatch(re.escape(PREFIX + sym + "/" + sym) + r"-metrics-(\d{4}-\d{2}-\d{2})\.zip(\.CHECKSUM)?", key)
            if m:
                (chks if m.group(2) else zips).add(m.group(1))
        trunc = re.findall(r"<IsTruncated>([^<]+)</IsTruncated>", txt); tok = re.findall(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", txt)
        if trunc and trunc[0] == "true":
            if not tok:
                return dict(zip_dates=sorted(zips), checksum_dates=sorted(chks), pages=pages, ok=False, fail_status="truncated_without_token")
            token = tok[0]
        else:
            return dict(zip_dates=sorted(zips), checksum_dates=sorted(chks), pages=pages, ok=True, fail_status=None)
    return dict(zip_dates=sorted(zips), checksum_dates=sorted(chks), pages=pages, ok=False, fail_status="page_limit")


def fetch_day(client, sym, day, with_checksum):
    """Download one metrics day. Returns dict(status, zip_sha256, checksum_ok, body)."""
    name = "%s-metrics-%s.zip" % (sym, day)
    st, body = client.get("data.binance.vision", "/" + PREFIX + sym + "/" + name)
    if st != 200:
        return dict(status=st, zip_sha256=None, checksum_ok=None, body=None)
    d = hashlib.sha256(body).hexdigest(); ok = None
    if with_checksum:
        st2, cb = client.get("data.binance.vision", "/" + PREFIX + sym + "/" + name + ".CHECKSUM")
        if st2 == 200:
            tok = cb.decode("utf-8", "replace").split()
            ok = bool(len(tok) == 2 and tok[0].lower() == d and tok[1].lstrip("*") == name)
        else:
            ok = "checksum_status_%s" % st2
    return dict(status=200, zip_sha256=d, checksum_ok=ok, body=body)


def parse_day(body, sym, day):
    """Parse one daily metrics zip in memory. Returns dict(ts[int64 unix s], X[float64 n×6], n_rows, errors{...}, member_ok, crc_ok)."""
    errs = {}
    def bump(k):
        errs[k] = errs.get(k, 0) + 1
    try:
        z = zipfile.ZipFile(io.BytesIO(body)); names = z.namelist()
        member_ok = names == ["%s-metrics-%s.csv" % (sym, day)]
        bad = z.testzip(); crc_ok = bad is None
        raw = z.read(names[0]).decode("utf-8-sig")
    except Exception as e:
        return dict(ts=None, X=None, n_rows=0, errors={"zip_" + type(e).__name__: 1}, member_ok=False, crc_ok=False)
    rd = csv.reader(io.StringIO(raw)); hdr = next(rd, None)
    if hdr is None or "create_time" not in hdr or any(c not in hdr for c in COLS):
        return dict(ts=None, X=None, n_rows=0, errors={"header": 1, "hdr": str(hdr)}, member_ok=member_ok, crc_ok=crc_ok)
    it = hdr.index("create_time"); isy = hdr.index("symbol") if "symbol" in hdr else None; ix = [hdr.index(c) for c in COLS]
    ts, X = [], []
    for row in rd:
        if not row:
            continue
        try:
            t = calendar.timegm(time.strptime(row[it].strip(), "%Y-%m-%d %H:%M:%S"))
        except Exception:
            bump("time_parse"); continue
        if isy is not None and row[isy] != sym:
            bump("symbol_mismatch")
        vals = []
        for q in ix:
            s = row[q].strip() if q < len(row) else ""
            try:
                vals.append(float(s) if s != "" else float("nan"))
            except Exception:
                vals.append(float("nan")); bump("value_parse")
        ts.append(t); X.append(vals)
    return dict(ts=np.array(ts, np.int64), X=np.array(X, np.float64).reshape(-1, 6), n_rows=len(ts), errors=errs, member_ok=member_ok, crc_ok=crc_ok)
