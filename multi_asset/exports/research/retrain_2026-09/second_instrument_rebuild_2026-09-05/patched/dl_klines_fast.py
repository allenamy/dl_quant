"""dl_klines_paced.py — PREREG_second_instrument_rebuild_2026-09-05 §1 step 1.
Merge of two git-tracked downloaders, changed ONLY in paths / month set / daily tail / pacing:
  * runpod_scripts/workspace_mirror/pod_hist_dl.py   (sha256 beca960d…)  : queue + worker threads, .404 sentinel idempotency,
                                                       .part -> rename, ok/miss404/err counters, 30 s progress line
  * runpod_scripts/workspace_mirror/pod_dl_klines.py (sha256 34f5cf0a…)  : monthly 2022+ from the CDN + daily August tail,
                                                       3-attempt retry with 2*(a+1) s back-off on non-404 errors
Patches (all listed in logs/patches/dl_klines_paced.diff, sha printed at start):
  P1 paths      : symbols file = <ROOT>/src/panel_symbols_wide.txt (repo copy, 829 symbols); out tree = <ROOT>/klines5m/<S>/
  P2 month set  : monthly 2020-01 .. 2026-07 (both scripts' sets united), daily 2026-08-01 .. 2026-08-16 (prereg §1 row 1)
  P3 pacing     : one shared token bucket, RATE = 4 req/s total across all threads (every attempt, incl. retries and 404s, takes a token);
                  hard pause inside anchor windows [N-5 min, N+30 min] UTC, N in {00,04,08,12,16,20}; pause/resume printed with UTC time
  P5 efficiency : existence check via one os.listdir per symbol dir instead of two stat calls per job (network FS); same rule as pod_hist_dl.py L26
  P4 receipts   : prints own sha256 + patch-diff sha256, planned request count, pacing parameters, UTC now and ETA before the first request;
                  writes logs/dl_errors.txt for non-404 failures; DL_DONE line with counters
Funding zips are NOT pulled (prereg §0.2: already on the pod under /workspace/wide_multisrc/funding/).
"""
import os, sys, time, socket, hashlib, threading, queue, urllib.request, urllib.error
import datetime as dt

socket.setdefaulttimeout(30)
ROOT = "/workspace/review_scratch/jpline_rebuild"
SYMS_FILE = f"{ROOT}/src/panel_symbols_wide.txt"
D = f"{ROOT}/klines5m"
CDN = "https://data.binance.vision/data/futures/um"
RATE = float(os.environ.get("DL_RATE", "4.0"))          # requests / second, total
NTHREADS = int(os.environ.get("DL_THREADS", "8"))
MONTHS = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
DAYS = [f"2026-08-{i:02d}" for i in range(1, 17)]
ANCHORS = (0, 4, 8, 12, 16, 20); PAUSE_BEFORE = 5 * 60; PAUSE_AFTER = 30 * 60
if os.environ.get("DL_PAUSE", "1") == "0": ANCHORS = ()   # P6 (user ruling 2026-09-05 解除限速): no anchor-window pause on the static CDN
DRY = os.environ.get("DL_DRY", "0") == "1"
PATCH_DIFF = f"{ROOT}/logs/patches/dl_klines_fast.diff"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

def utcnow():
    return dt.datetime.now(dt.timezone.utc)

def pause_remaining(t):
    """seconds left inside an anchor pause window at UTC datetime t, else 0."""
    sod = t.hour * 3600 + t.minute * 60 + t.second
    for N in ANCHORS:
        s, e = N * 3600 - PAUSE_BEFORE, N * 3600 + PAUSE_AFTER
        for tt in (sod, sod - 86400):
            if s <= tt < e: return e - tt
    return 0

def next_pause_start(t):
    """seconds until the next pause window starts (0 if inside one)."""
    if pause_remaining(t): return 0
    sod = t.hour * 3600 + t.minute * 60 + t.second
    cands = [N * 3600 - PAUSE_BEFORE for N in ANCHORS] + [24 * 3600 - PAUSE_BEFORE]
    return min(c - sod for c in cands if c > sod)

def eta_seconds(nreq, t0):
    """simulate the bucket: nreq requests at RATE, skipping pause windows."""
    t = t0; rem = float(nreq); total = 0.0
    while rem > 0:
        p = pause_remaining(t)
        if p: t = t + dt.timedelta(seconds=p); total += p; continue
        nxt = next_pause_start(t); step = min(rem / RATE, nxt)
        t = t + dt.timedelta(seconds=step); total += step; rem -= step * RATE
    return total, t

# ---- shared token bucket + anchor pause (P3) ----
_lock = threading.Lock(); _next = [time.monotonic()]; _paused = [False]
def acquire():
    while True:
        with _lock:
            now = utcnow(); p = pause_remaining(now)
            if p:
                if not _paused[0]:
                    print(f"PAUSE {now.strftime('%Y-%m-%dT%H:%M:%SZ')} anchor window, resume in {p:.0f}s", flush=True); _paused[0] = True
                slot = None; wait = min(p, 20)
            else:
                if _paused[0]:
                    print(f"RESUME {now.strftime('%Y-%m-%dT%H:%M:%SZ')}", flush=True); _paused[0] = False
                m = time.monotonic(); slot = max(m, _next[0]); _next[0] = slot + 1.0 / RATE; wait = slot - m
        if wait > 0: time.sleep(wait)
        if slot is not None: return

K_SYMS = sorted(open(SYMS_FILE).read().strip().split("|"))
assert len(K_SYMS) == 829, len(K_SYMS)
JOBS = []
for s in K_SYMS:
    for mo in MONTHS:
        JOBS.append((f"{D}/{s}/{s}-5m-{mo}.zip", f"{CDN}/monthly/klines/{s}/5m/{s}-5m-{mo}.zip"))
    for d in DAYS:
        JOBS.append((f"{D}/{s}/{s}-5m-{d}.zip", f"{CDN}/daily/klines/{s}/5m/{s}-5m-{d}.zip"))
_have = {}
for s in K_SYMS:   # P5: one listdir per symbol instead of 2 stats per job (network FS); semantics identical to pod_hist_dl.py L26
    _have[s] = set(os.listdir(f"{D}/{s}")) if os.path.isdir(f"{D}/{s}") else set()
def _satisfied(out):
    b = os.path.basename(out); s = b.split("-5m-")[0]
    return (b in _have[s]) or (b + ".404" in _have[s])
todo = [j for j in JOBS if not _satisfied(j[0])]
t0 = utcnow(); eta_s, eta_t = eta_seconds(len(todo), t0)
print(f"SELF_SHA256 {sha256(os.path.abspath(__file__))}", flush=True)
print(f"PATCH_SHA256 {sha256(PATCH_DIFF) if os.path.exists(PATCH_DIFF) else 'MISSING'} {PATCH_DIFF}", flush=True)
print(f"SYMBOLS {len(K_SYMS)} sha256 {sha256(SYMS_FILE)}", flush=True)
print(f"PLAN symbols {len(K_SYMS)} x (monthly {len(MONTHS)} [{MONTHS[0]}..{MONTHS[-1]}] + daily {len(DAYS)} [{DAYS[0]}..{DAYS[-1]}]) = {len(JOBS)} (symbol,period) requests; "
      f"already satisfied {len(JOBS)-len(todo)}; planned now {len(todo)}", flush=True)
print(f"FAST_VARIANT pause_disabled={len(ANCHORS)==0} (user ruling 2026-09-05 解除限速; static CDN on pod2 only)", flush=True)
print(f"PACING rate {RATE} req/s total (shared token bucket), threads {NTHREADS}, pause windows [N-{PAUSE_BEFORE//60}min, N+{PAUSE_AFTER//60}min] UTC for N in {ANCHORS}", flush=True)
print(f"UTC_NOW {t0.strftime('%Y-%m-%dT%H:%M:%SZ')}  ETA {eta_s/3600:.2f} h -> {eta_t.strftime('%Y-%m-%dT%H:%M:%SZ')} (upper bound: every planned request billed at 1/{RATE:.0f} s incl. 404s)", flush=True)
if DRY:
    print("DRY_RUN_EXIT", flush=True); sys.exit(0)

q = queue.Queue()
for j in todo: q.put(j)
ok = [0]; miss = [0]; err = [0]; nreq = [0]; lock = threading.Lock()
ERRF = open(f"{ROOT}/logs/dl_errors.txt", "a")
def worker():
    while True:
        try: out, url = q.get_nowait()
        except queue.Empty: return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out) or os.path.exists(out + ".404"):
            with lock: ok[0] += 1
            q.task_done(); continue
        done = False
        for a in range(4):
            acquire()
            with lock: nreq[0] += 1
            try:
                with urllib.request.urlopen(url, timeout=30) as r: data = r.read()
                with open(out + ".part", "wb") as f: f.write(data)
                os.replace(out + ".part", out)
                with lock: ok[0] += 1
                done = True; break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    open(out + ".404", "w").close()
                    with lock: miss[0] += 1
                    done = True; break
                time.sleep(2 * (a + 1))
            except Exception:
                try: os.remove(out + ".part")
                except OSError: pass
                time.sleep(2 * (a + 1))
        if not done:
            with lock:
                err[0] += 1; ERRF.write(url + "\n"); ERRF.flush()
        q.task_done()
ths = [threading.Thread(target=worker, daemon=True) for _ in range(NTHREADS)]
for t in ths: t.start()
ts = time.time()
while any(t.is_alive() for t in ths):
    time.sleep(30)
    el = time.time() - ts
    print(f"ok {ok[0]} miss404 {miss[0]} err {err[0]} left {q.qsize()} req {nreq[0]} rate {nreq[0]/max(el,1):.2f}/s elapsed {el/3600:.2f}h {utcnow().strftime('%H:%M:%SZ')}", flush=True)
ERRF.close()
print(f"DL_DONE ok {ok[0]} miss404 {miss[0]} err {err[0]} requests {nreq[0]} elapsed {(time.time()-ts)/3600:.2f}h {utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}", flush=True)
