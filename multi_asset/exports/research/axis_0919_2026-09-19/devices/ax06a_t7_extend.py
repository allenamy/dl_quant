"""AX06a (axis_0919): extend the T7 third-party 1h perpetual-kline control (count column) past 2026-08-31T23:00Z open, so that the tradability
builder's T7 control (fx_trd_build.py step T7: cache TRADED-in-hour vs venue trade count > 0) also covers the appended cache rows.
Source: PUBLIC https://fapi.binance.com/fapi/v1/klines?symbol=S&interval=1h&startTime=..&endTime=..&limit=499 (weight 2), no credentials.
For every symbol file in AX_T7_IN (read-only): old rows copied verbatim; REST rows with open_s in (last old open_s, AX_T7_END_OPEN_S] appended
(source code 9 = REST this round). Output files under AX_T7_OUT (new dir; refuses to overwrite) + receipt with device_sha256 (the key the builder reads).
Rate: AX_RPS (default 3 req/s); anchor-window guard HH:00-HH:57 of 00/04/08/12/16/20 UTC.
"""
import os, sys, json, time, hashlib, urllib.request, urllib.error, socket
import numpy as np
socket.setdefaulttimeout(30)
IN, OUT, END_OPEN = os.environ["AX_T7_IN"], os.environ["AX_T7_OUT"], int(os.environ["AX_T7_END_OPEN_S"])
RATE = float(os.environ.get("AX_RPS", "3")); RPT = os.environ["AX_T7_RECEIPT"]
assert not os.path.exists(OUT) and not os.path.exists(RPT), "refuse to overwrite"
os.makedirs(OUT)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
_next = [time.time()]
def get(url):
    for attempt in range(6):
        while True:
            t = time.gmtime()
            if t.tm_hour % 4 == 0 and t.tm_min < 57: time.sleep(30); continue
            break
        now = time.time()
        if now < _next[0]: time.sleep(_next[0] - now)
        _next[0] = max(time.time(), _next[0]) + 1.0 / RATE
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-readonly/1.0"})) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 418: raise SystemExit("HTTP 418 IP ban: abort")
            if e.code == 429: time.sleep(float(e.headers.get("Retry-After") or 60)); continue
            if e.code == 400: return None
            raise
        except urllib.error.URLError: time.sleep(5 * (attempt + 1))
    raise RuntimeError("retries exhausted")
t0 = time.time(); man = {}
for fn in sorted(os.listdir(IN)):
    if not fn.endswith(".npz"): continue
    s = fn[:-4]; z = np.load(os.path.join(IN, fn)); arr = {k: z[k] for k in z.files}
    last = int(arr["open_s"][-1]); st = last + 3600
    rows = []
    if st <= END_OPEN:
        j = get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&startTime={st*1000}&endTime={END_OPEN*1000}&limit=499")
        rows = [r for r in (j or []) if st <= int(r[0]) // 1000 <= END_OPEN]
    new_open = np.array([int(r[0]) // 1000 for r in rows], np.int64)
    assert len(new_open) == 0 or (np.all(np.diff(new_open) == 3600) and new_open[0] > last), s
    out = {"open_s": np.concatenate([arr["open_s"], new_open]), "count": np.concatenate([arr["count"], np.array([int(r[8]) for r in rows], np.int64)]),
           "volume": np.concatenate([arr["volume"], np.array([float(r[5]) for r in rows], np.float64)]),
           "source": np.concatenate([arr["source"], np.full(len(rows), 9, np.int8)])}
    p = os.path.join(OUT, fn); np.savez(p, **out)
    back = np.load(p); assert all(np.array_equal(back[k][:len(arr[k])], arr[k]) for k in arr), f"prefix changed {s}"
    man[s] = {"old_rows": int(len(arr["open_s"])), "new_rows": int(len(rows)), "old_last_open": time.strftime("%F %H:%MZ", time.gmtime(last)),
              "new_last_open": time.strftime("%F %H:%MZ", time.gmtime(int(out["open_s"][-1]))), "sha256": sha(p)}
rec = {"device": "ax06a_t7_extend.py", "device_sha256": sha(os.path.abspath(__file__)), "t7_in": IN, "t7_out": OUT, "end_open_utc": time.strftime("%F %H:%MZ", time.gmtime(END_OPEN)),
       "n_files": len(man), "n_new_rows": sum(v["new_rows"] for v in man.values()), "files_with_no_new_rows": [s for s, v in man.items() if v["new_rows"] == 0],
       "source": "https://fapi.binance.com/fapi/v1/klines interval=1h (public)", "wall_s": round(time.time() - t0, 1), "files": man,
       "note": "old rows (T7 run, receipt device_sha256 1b1a07a3…) copied verbatim and asserted bitwise; appended rows source code 9"}
json.dump(rec, open(RPT, "w"), indent=1)
print("AX06A_DONE", json.dumps({k: rec[k] for k in ("n_files", "n_new_rows", "wall_s")}), "no_new:", rec["files_with_no_new_rows"][:20], flush=True)
