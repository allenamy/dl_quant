"""AX01 (axis_0919, stream D): fetch data.binance.vision DAILY 5m USD-M kline archives + their .CHECKSUM files.

Differences from r6_fetch_klines.py (same URL scheme, same symbol list, same anchor-window guard):
  * days come from env AX_DAYS (comma list) — nothing hard-coded;
  * every zip is verified against the venue's published sha256 (.CHECKSUM); a mismatch is re-fetched up to 3x and then recorded as FAIL;
  * AX_CHECK_ONLY_DAYS: days whose zips ALREADY exist in another tree (r6) — only the CHECKSUM is fetched and compared to the local file;
  * writes ONLY under $AX_ROOT/dl/klines5m (new root); a per-file manifest (sha256, bytes, checksum match) is the receipt;
  * AX_SYMS (optional comma list) restricts the run to a subset — used for a retry of archives that were still being published.
Global token bucket <= AX_RPS req/s (default 5). Anchor-window guard: sleeps through HH:00-HH:57 of 00/04/08/12/16/20 UTC.
"""
import os, sys, time, json, hashlib, threading, queue, socket, urllib.request, urllib.error

socket.setdefaulttimeout(60)
ROOT = os.environ["AX_ROOT"]
DAYS = [d for d in os.environ.get("AX_DAYS", "").split(",") if d]
CHK_DAYS = [d for d in os.environ.get("AX_CHECK_ONLY_DAYS", "").split(",") if d]
CHK_DIR = os.environ.get("AX_CHECK_ONLY_DIR", "")
RATE = float(os.environ.get("AX_RPS", "5"))
TAG = os.environ.get("AX_TAG", "run")
SYMS = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
if os.environ.get("AX_SYMS"):   # retry subset (e.g. archives still being published at the first pass); must be a subset of the panel symbols
    _sub = [x for x in os.environ["AX_SYMS"].split(",") if x]; assert set(_sub) <= set(SYMS), "AX_SYMS not a subset"; SYMS = _sub
OUT = f"{ROOT}/dl/klines5m"
BASE = "https://data.binance.vision/data/futures/um/daily/klines"
os.makedirs(OUT, exist_ok=True)
assert not os.path.exists(f"{ROOT}/receipts/KLINES5M_{TAG}.json"), "receipt exists; refuse to overwrite"

_lk = threading.Lock(); _next = [time.time()]
def token():
    while True:
        with _lk:
            now = time.time()
            if now >= _next[0]:
                _next[0] = max(now, _next[0]) + 1.0 / RATE; return
            slp = _next[0] - now
        time.sleep(slp)

def anchor_guard():
    while True:
        t = time.gmtime()
        if t.tm_hour % 4 == 0 and t.tm_min < 57:
            time.sleep(30); continue
        return

def get(url):
    anchor_guard(); token()
    req = urllib.request.Request(url, headers={"User-Agent": "research-readonly/1.0"})
    with urllib.request.urlopen(req) as r: return r.read()

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

JOBS = [("fetch", s, d) for s in SYMS for d in DAYS] + [("check", s, d) for s in SYMS for d in CHK_DAYS]
q = queue.Queue()
for j in JOBS: q.put(j)
man = []; lock = threading.Lock(); cnt = {"ok": 0, "404": 0, "fail": 0}

def one(kind, s, d):
    fn = f"{s}-5m-{d}.zip"; url = f"{BASE}/{s}/5m/{fn}"
    rec = {"kind": kind, "sym": s, "day": d}
    for attempt in range(4):
        try:
            try:
                ck = get(url + ".CHECKSUM").decode().split()
                ck_sha = ck[0].lower(); ck_name = ck[1] if len(ck) > 1 else None
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # no checksum => confirm the zip is also absent (an archive without a checksum is recorded as such)
                    try:
                        get(url); rec.update(status="ZIP_WITHOUT_CHECKSUM"); return rec
                    except urllib.error.HTTPError as e2:
                        if e2.code == 404: rec.update(status="404"); return rec
                        raise
                raise
            rec.update(checksum_sha256=ck_sha, checksum_name=ck_name, checksum_name_ok=(ck_name == fn))
            if kind == "check":
                p = f"{CHK_DIR}/{s}/{d}.zip"
                if not os.path.exists(p):
                    rec.update(status="LOCAL_MISSING", local=p); return rec
                h = sha_file(p); rec.update(local=p, local_sha256=h, bytes=os.path.getsize(p),
                                            status="OK" if h == ck_sha else "LOCAL_MISMATCH"); return rec
            b = get(url); h = sha_bytes(b)
            if h != ck_sha:
                rec.update(status="MISMATCH_RETRY", got=h); time.sleep(2); continue
            od = f"{OUT}/{s}"; os.makedirs(od, exist_ok=True); p = f"{od}/{d}.zip"
            assert not os.path.exists(p), f"refuse to overwrite {p}"
            with open(p + ".part", "wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
            os.rename(p + ".part", p)
            assert sha_file(p) == ck_sha
            rec.update(status="OK", path=p, sha256=h, bytes=len(b)); return rec
        except Exception as e:
            rec.update(status="ERR", err=repr(e)[:200]); time.sleep(3 * (attempt + 1))
    return rec

def worker():
    while True:
        try: kind, s, d = q.get_nowait()
        except queue.Empty: return
        r = one(kind, s, d)
        with lock:
            man.append(r)
            if r["status"] == "OK": cnt["ok"] += 1
            elif r["status"] == "404": cnt["404"] += 1
            else: cnt["fail"] += 1

t0 = time.time()
ths = [threading.Thread(target=worker, daemon=True) for _ in range(6)]
for t in ths: t.start()
while any(t.is_alive() for t in ths):
    time.sleep(30)
    print(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] {cnt} left {q.qsize()}", flush=True)
os.makedirs(f"{ROOT}/receipts", exist_ok=True)
by = {}
for r in man: by.setdefault((r["kind"], r["day"]), {}).setdefault(r["status"], 0); by[(r["kind"], r["day"])][r["status"]] += 1
rep = {"self_sha256": sha_file(os.path.abspath(__file__)), "tag": TAG, "days": DAYS, "check_only_days": CHK_DAYS,
       "check_only_dir": CHK_DIR, "rate_cap_rps": RATE, "n_symbols": len(SYMS), "jobs": len(JOBS), "counts": cnt,
       "per_kind_day_status": {f"{k}|{d}": v for (k, d), v in sorted(by.items())},
       "non_ok_non_404": [r for r in man if r["status"] not in ("OK", "404")],
       "started_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0)),
       "finished_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "wall_s": round(time.time() - t0, 1),
       "manifest": sorted(man, key=lambda r: (r["kind"], r["sym"], r["day"]))}
p = f"{ROOT}/receipts/KLINES5M_{TAG}.json"
with open(p + ".tmp", "w") as f: json.dump(rep, f, indent=0)
os.replace(p + ".tmp", p)
print("AX01_DONE", json.dumps({k: rep[k] for k in ("counts", "per_kind_day_status", "wall_s")}), "non_ok", len(rep["non_ok_non_404"]), flush=True)
