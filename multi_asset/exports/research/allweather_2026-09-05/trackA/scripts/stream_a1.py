"""stream_a1.py — Track A family A1 source pull in QUOTA MODE (team-lead 2026-09-05 15:1xZ: stream-parse-and-delete, raw zips < ~1 GB at any time).
For the 477 perp symbols with a Binance spot pair (spot/perp_to_spot_map.json): perp 5m monthly klines 2022-01..2026-08 (CDN futures/um/monthly/klines)
and spot 5m klines (monthly 2022-01..2026-07 + daily 2026-08-01..2026-09-04). Each zip: downloaded (16 threads) -> parsed in a process pool ->
written by the single main process into compact memmaps -> sha256 + row counts appended to spot/a1_manifest.jsonl -> zip DELETED. 404s are recorded
in the manifest (no sentinel files). Idempotent: manifest entries are skipped on restart; zips already on disk are parsed without download.
Raw cap: at most RAW_MAX (400) downloaded-but-unparsed files in flight. Write probe (1 MB) every 2000 files; a failed probe halts cleanly.
Compact layout (row = index in features/a1_syms.json = the 477 mapped perp symbols, sorted; column = ext-cache 5m grid row, ts = bar CLOSE time):
  features/a1_spot_close.npy  (477, T) float32  spot close × price_mult (perp price units)
  features/a1_spot_lqv.npy    (477, T) float16  log1p(spot quote volume) clipped [0, 25]   (same encoding as the ext cache log_qv channel)
  features/a1_spot_tbf.npy    (477, T) float16  spot taker-buy quote volume / quote volume in [0, 1]
  features/a1_perp_close.npy  (477, T) float32  perp close
Perp quote volume / taker-buy share are NOT re-stored: the feature stage takes them from the ext cache channels log_qv / tbf (same source zips).
Spot archive timestamps are microseconds from 2025-01-01 -> normalised. Receipts: PLAN / PROG / DL_DONE lines, manifest, a1_syms.json.
env: ROOT DL_THREADS(<=16) NPROC RAW_MAX DL_ONLY(perp,spot)
"""
import os, io, sys, json, time, socket, hashlib, threading, queue, zipfile, urllib.request, urllib.error
import numpy as np
from concurrent.futures import ProcessPoolExecutor
socket.setdefaulttimeout(30)
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA"); CDN = "https://data.binance.vision/data"
NTHREADS = int(os.environ.get("DL_THREADS", "16")); assert NTHREADS <= 16
NPROC = int(os.environ.get("NPROC", "8")); RAW_MAX = int(os.environ.get("RAW_MAX", "400"))
ONLY = os.environ.get("DL_ONLY", "perp,spot").split(",")
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); T = len(CTS); T0 = int(CTS[0]); assert np.all(np.diff(CTS) == 300); del Z
MAP = json.load(open(f"{ROOT}/spot/perp_to_spot_map.json"))["map"]
SYMS = sorted(MAP); NS = len(SYMS); ROW = {s: i for i, s in enumerate(SYMS)}
json.dump({"syms": SYMS, "n": NS, "row_index": "position in syms", "map": {s: MAP[s] for s in SYMS}}, open(f"{ROOT}/features/a1_syms.json", "w"), indent=0)
ARR = {"spot_close": np.float32, "spot_lqv": np.float16, "spot_tbf": np.float16, "perp_close": np.float32}
PATH = {a: f"{ROOT}/features/a1_{a}.npy" for a in ARR}
MM = {}
for a, dt in ARR.items():
    if os.path.exists(PATH[a]): MM[a] = np.load(PATH[a], mmap_mode="r+")
    else:
        MM[a] = np.lib.format.open_memmap(PATH[a], mode="w+", dtype=dt, shape=(NS, T)); MM[a][:] = np.nan; MM[a].flush()
MANIFEST = f"{ROOT}/spot/a1_manifest.jsonl"
done = set()
if os.path.exists(MANIFEST):
    for line in open(MANIFEST):
        try: done.add(json.loads(line)["file"])
        except Exception: pass
M_FUT = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 8)]
M_SPOT = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
D_SPOT = [f"2026-08-{i:02d}" for i in range(1, 32)] + [f"2026-09-{i:02d}" for i in range(1, 5)]
JOBS = []   # (side, perp_sym, local_path, url)
for s in SYMS:
    if "perp" in ONLY:
        for mo in M_FUT: JOBS.append(("perp", s, f"{ROOT}/perp5m/{s}/{s}-5m-{mo}.zip", f"{CDN}/futures/um/monthly/klines/{s}/5m/{s}-5m-{mo}.zip"))
    if "spot" in ONLY:
        p = MAP[s]["spot"]
        for mo in M_SPOT: JOBS.append(("spot", s, f"{ROOT}/spot/klines/{p}/{p}-5m-{mo}.zip", f"{CDN}/spot/monthly/klines/{p}/5m/{p}-5m-{mo}.zip"))
        for d in D_SPOT: JOBS.append(("spot", s, f"{ROOT}/spot/klines/{p}/{p}-5m-{d}.zip", f"{CDN}/spot/daily/klines/{p}/5m/{p}-5m-{d}.zip"))
todo = [j for j in JOBS if os.path.basename(j[2]) not in done]
print(f"SELF_SHA256 {SELF}", flush=True)
print(f"PLAN mapped_syms {NS} jobs {len(JOBS)} already_in_manifest {len(JOBS)-len(todo)} todo {len(todo)} threads {NTHREADS} nproc {NPROC} raw_max {RAW_MAX} utc " + time.strftime("%FT%TZ", time.gmtime()), flush=True)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
def write_probe():
    p = f"{ROOT}/logs/_probe_a1"
    try:
        with open(p, "wb") as f: f.write(b"x" * (1 << 20)); f.flush(); os.fsync(f.fileno())
        os.remove(p); return True
    except Exception as e:
        print(f"WRITE_PROBE_FAIL {e!r}", flush=True); return False
def parse_zip(args):
    """worker: -> (side, sym, file, sha, bytes, n_rows, idx, close, lqv, tbf) or error tuple."""
    side, sym, path, mult = args
    import pandas as pd
    try:
        sha = sha256_file(path); nb = os.path.getsize(path)
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        d = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None, usecols=[0, 4, 7, 10])
        ot = d.iloc[:, 0].to_numpy(np.int64); ot = np.where(ot > 10**14, ot // 1000000, ot // 1000)
        idx = (ot + 300 - T0) // 300; ok = (idx >= 0) & (idx < T) & (ot % 300 == 0)
        c = d.iloc[:, 1].to_numpy(np.float64)[ok] * mult; q = d.iloc[:, 2].to_numpy(np.float64)[ok]; b = d.iloc[:, 3].to_numpy(np.float64)[ok]
        with np.errstate(invalid="ignore", divide="ignore"):
            lqv = np.clip(np.log1p(np.maximum(q, 0)), 0, 25).astype(np.float16); tbf = np.where(q > 0, np.clip(b / q, 0, 1), np.nan).astype(np.float16)
        return ("ok", side, sym, os.path.basename(path), sha, nb, int(len(ot)), idx[ok].astype(np.int32), c.astype(np.float32), lqv, tbf)
    except Exception as e:
        return ("bad", side, sym, os.path.basename(path), repr(e))

# ---- download threads -> parse queue (bounded by RAW_MAX via semaphore) ----
dq = queue.Queue(); pq = queue.Queue(); sem = threading.Semaphore(RAW_MAX)
cnt = {"ok": 0, "miss404": 0, "err": 0, "bytes": 0, "parsed": 0, "bad": 0}; lock = threading.Lock(); errs = []
for j in todo: dq.put(j)
def dl_worker():
    while True:
        try: side, sym, out, url = dq.get_nowait()
        except queue.Empty: return
        if os.path.exists(out):
            sem.acquire(); pq.put((side, sym, out)); continue
        os.makedirs(os.path.dirname(out), exist_ok=True); last = ""
        for a in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as r: data = r.read()
                sem.acquire()
                with open(out + ".part", "wb") as f: f.write(data)
                os.replace(out + ".part", out)
                with lock: cnt["ok"] += 1; cnt["bytes"] += len(data)
                pq.put((side, sym, out)); break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    with lock: cnt["miss404"] += 1
                    pq.put((side, sym, out, 404)); break
                last = "HTTP %d" % e.code
            except Exception as e:
                last = repr(e)
            time.sleep(2 * (a + 1))
        else:
            with lock: cnt["err"] += 1; errs.append((url, last))
th = [threading.Thread(target=dl_worker, daemon=True) for _ in range(NTHREADS)]
t0 = time.time()
for t in th: t.start()
MAN = open(MANIFEST, "a"); last_p = t0; nfiles = 0; freed = 0
def handle(res):
    global freed
    if res[0] == "ok":
        _, side, sym, fn, sha, nb, nrow, idx, c, lqv, tbf = res; r = ROW[sym]
        if side == "spot":
            MM["spot_close"][r, idx] = c; MM["spot_lqv"][r, idx] = lqv; MM["spot_tbf"][r, idx] = tbf
        else:
            MM["perp_close"][r, idx] = c
        MAN.write(json.dumps({"side": side, "sym": sym, "file": fn, "sha256": sha, "bytes": nb, "n_rows": nrow, "n_on_grid": int(len(idx))}) + "\n")
        cnt["parsed"] += 1
    else:
        MAN.write(json.dumps({"side": res[1], "sym": res[2], "file": res[3], "status": "BAD " + res[4]}) + "\n"); cnt["bad"] += 1
with ProcessPoolExecutor(max_workers=NPROC) as ex:
    inflight = []
    while True:
        alive = any(t.is_alive() for t in th)
        try:
            item = pq.get(timeout=2)
        except queue.Empty:
            item = None
        if item is not None:
            if len(item) == 4:   # 404
                MAN.write(json.dumps({"side": item[0], "sym": item[1], "file": os.path.basename(item[2]), "status": 404}) + "\n")
            else:
                side, sym, path = item; mult = float(MAP[sym]["price_mult"]) if side == "spot" else 1.0
                inflight.append((ex.submit(parse_zip, (side, sym, path, mult)), path))
        still = []
        for fut, path in inflight:
            if fut.done():
                handle(fut.result()); freed += os.path.getsize(path); os.remove(path); sem.release(); nfiles += 1
                if nfiles % 2000 == 0:
                    MAN.flush(); [m.flush() for m in MM.values()]
                    if not write_probe(): print("HALT: write probe failed", flush=True); sys.exit(3)
            else: still.append((fut, path))
        inflight = still
        if time.time() - last_p >= 30:
            last_p = time.time(); dn = cnt["ok"] + cnt["miss404"] + cnt["err"]
            print("PROG " + time.strftime("%H:%M:%SZ", time.gmtime()) + f" dl {dn}/{len(todo)} ok {cnt['ok']} 404 {cnt['miss404']} err {cnt['err']} parsed {cnt['parsed']} bad {cnt['bad']} inflight {len(inflight)} {dn/(time.time()-t0):.1f} req/s MB_dl {cnt['bytes']/1e6:.0f} MB_freed {freed/1e6:.0f}", flush=True)
        if not alive and pq.empty() and not inflight: break
MAN.flush(); MAN.close(); [m.flush() for m in MM.values()]
with open(f"{ROOT}/logs/a1_dl_errors.txt", "a") as f:
    for u, e in errs: f.write(u + "\t" + e + "\n")
print(f"DL_DONE ok {cnt['ok']} miss404 {cnt['miss404']} err {cnt['err']} parsed {cnt['parsed']} bad {cnt['bad']} requests {len(todo)} bytes {cnt['bytes']} freed {freed} secs {time.time()-t0:.0f} utc " + time.strftime("%FT%TZ", time.gmtime()), flush=True)
for a in ARR: print(f"ARRAY {a} finite_frac {np.isfinite(np.load(PATH[a], mmap_mode='r')).mean():.4f} sha256 {sha256_file(PATH[a])[:16]}", flush=True)
