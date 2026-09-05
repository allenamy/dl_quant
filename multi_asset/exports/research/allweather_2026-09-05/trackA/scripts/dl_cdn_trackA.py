"""dl_cdn_trackA.py — Track A (PREREG_allweather_programme_2026-09-05 §2 A1/A2) CDN puller. Structure follows
jpline_rebuild/patched/dl_klines_fast.py (queue + worker threads, .404 sentinel idempotency, .part -> rename, counters),
no rate limit / no anchor pause (STATE.md §4 user ruling 2026-09-05: static CDN pulls on pod2 exempt), THREADS<=16.
Trees (all under /workspace/review_scratch/allweather_trackA/):
  premidx/<S>/<S>-5m-YYYY-MM.zip        futures/um/monthly/premiumIndexKlines/<S>/5m/   2022-01..2026-08  (829 perp symbols)
  perp5m/<S>/<S>-5m-YYYY-MM.zip         futures/um/monthly/klines/<S>/5m/               2022-01..2026-08  (829 perp symbols)
  spot/klines/<P>/<P>-5m-YYYY-MM.zip    spot/monthly/klines/<P>/5m/                     2022-01..2026-07  (mapped spot pairs)
  spot/klines/<P>/<P>-5m-YYYY-MM-DD.zip spot/daily/klines/<P>/5m/                       2026-08-01..2026-09-04
Order: premidx -> perp -> spot (A2 can be gated first if spot is slow). Receipts: SELF_SHA256, planned counts, 30 s progress, DL_DONE.
"""
import os, sys, time, socket, hashlib, threading, queue, urllib.request, urllib.error, json
socket.setdefaulttimeout(30)
ROOT = "/workspace/review_scratch/allweather_trackA"
CDN = "https://data.binance.vision/data"
NTHREADS = int(os.environ.get("DL_THREADS", "16")); assert NTHREADS <= 16
ONLY = os.environ.get("DL_ONLY", "premidx,perp,spot").split(",")
def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
PERP = sorted(open("/workspace/panel_symbols_wide.txt").read().strip().split("|")); assert len(PERP) == 829, len(PERP)
MAP = json.load(open(f"{ROOT}/spot/perp_to_spot_map.json"))["map"]
SPOT = sorted(set(v["spot"] for v in MAP.values()))
M_FUT = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 8)]
M_SPOT = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
D_SPOT = [f"2026-08-{i:02d}" for i in range(1, 32)] + [f"2026-09-{i:02d}" for i in range(1, 5)]
JOBS = []
if "premidx" in ONLY:
    for s in PERP:
        for mo in M_FUT: JOBS.append((f"{ROOT}/premidx/{s}/{s}-5m-{mo}.zip", f"{CDN}/futures/um/monthly/premiumIndexKlines/{s}/5m/{s}-5m-{mo}.zip"))
if "perp" in ONLY:
    for s in PERP:
        for mo in M_FUT: JOBS.append((f"{ROOT}/perp5m/{s}/{s}-5m-{mo}.zip", f"{CDN}/futures/um/monthly/klines/{s}/5m/{s}-5m-{mo}.zip"))
if "spot" in ONLY:
    for p in SPOT:
        for mo in M_SPOT: JOBS.append((f"{ROOT}/spot/klines/{p}/{p}-5m-{mo}.zip", f"{CDN}/spot/monthly/klines/{p}/5m/{p}-5m-{mo}.zip"))
        for d in D_SPOT: JOBS.append((f"{ROOT}/spot/klines/{p}/{p}-5m-{d}.zip", f"{CDN}/spot/daily/klines/{p}/5m/{p}-5m-{d}.zip"))
def _satisfied(out):
    return os.path.exists(out) or os.path.exists(out + ".404")
todo = [j for j in JOBS if not _satisfied(j[0])]
print("SELF_SHA256 " + sha256(os.path.abspath(__file__)), flush=True)
print(f"PLAN perp_syms {len(PERP)} spot_pairs {len(SPOT)} jobs {len(JOBS)} todo {len(todo)} threads {NTHREADS} only {ONLY} utc " + time.strftime("%FT%TZ", time.gmtime()), flush=True)
q = queue.Queue()
for j in todo: q.put(j)
cnt = {"ok": 0, "miss404": 0, "err": 0, "bytes": 0}; lock = threading.Lock(); errs = []
def fetch(out, url):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    last = ""
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: data = r.read()
            tmp = out + ".part"
            with open(tmp, "wb") as f: f.write(data)
            os.replace(tmp, out)
            with lock: cnt["ok"] += 1; cnt["bytes"] += len(data)
            return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(out + ".404", "w").close()
                with lock: cnt["miss404"] += 1
                return
            last = "HTTP %d" % e.code
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (a + 1))
    with lock: cnt["err"] += 1; errs.append((url, last))
def worker():
    while True:
        try: out, url = q.get_nowait()
        except queue.Empty: return
        fetch(out, url); q.task_done()
th = [threading.Thread(target=worker, daemon=True) for _ in range(NTHREADS)]
t0 = time.time()
for t in th: t.start()
last_p = t0
while any(t.is_alive() for t in th):
    time.sleep(5)
    if time.time() - last_p >= 30:
        last_p = time.time(); done = cnt["ok"] + cnt["miss404"] + cnt["err"]
        print("PROG " + time.strftime("%H:%M:%SZ", time.gmtime()) + f" done {done}/{len(todo)} ok {cnt['ok']} 404 {cnt['miss404']} err {cnt['err']} {done/(time.time()-t0):.1f} req/s MB {cnt['bytes']/1e6:.0f}", flush=True)
with open(f"{ROOT}/logs/dl_errors.txt", "a") as f:
    for u, e in errs: f.write(u + "\t" + e + "\n")
print(f"DL_DONE ok {cnt['ok']} miss404 {cnt['miss404']} err {cnt['err']} requests {len(todo)} bytes {cnt['bytes']} secs {time.time()-t0:.0f} utc " + time.strftime("%FT%TZ", time.gmtime()), flush=True)
