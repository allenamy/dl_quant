#!/usr/bin/env python3
"""t7nc_g3b.py — T7 guard G3b (panel alignment), run on pod2 BEFORE any IC. Committed before it is run; not run until the lead has reviewed it.
Source: PREREG_T7_S1.md (62c6da52) §2.4 G3 last sentence: "G3b 面板对齐: 溢价装置所用 BTC 指数价与 S1 所用面板的 BTC 价格水平跨行 lag −3..+3 相关峰在 0";
        t7_s1_guards.py docstring "G3b (panel alignment) runs on pod2 before any IC"; AMENDMENT (21ecc60f5) §0 rows 4-5 (the S1 returns panel on NC is the
        v4 bookkeeping META meta_newprod_v4.npz 0e3c09ac, axis = NC combo axis ∩ META ∩ legs, 2023-01-01 .. 2026-08-30T20Z).
Interpretation fixed here (the frozen text gives only the lag range and the peak rule; everything below mirrors the frozen G3 in t7_s1_guards.py):
  * "panel BTC price level": META has no price column, so the level is rebuilt from META's own BTC return column: L[k+1] = L[k] + log1p(y4[k, BTC]),
    i.e. the log level at E_k + 4h (y4 = RAW Π(1+r) − 1 over [E_k, E_k + 4h], CALIBER_PIN_v4 L16). Only the BTCUSDT column of y4 is read.
  * "premium device's BTC index price": the T7 pull's BTCUSDT index hourly close (krw_pull/derived/binance_filled/BTCUSDT.npz, the file
    t7_s1_common.load_index reads), taken at the hour bar opening at E_k + 3h (closing at E_k + 4h).
  * detrend: centred mean over ±6 rows (±24 h, the G3 window in rows), at least 6 finite; rho(h) = corr(Ldetr[k], Idetr[k + h]), h in −3..+3.
  * PASS per calendar year of the NC evaluation axis: argmax rho == 0 and rho(0) > max(rho(−1), rho(+1)) (G3's rule without the dispersion clause,
    which needs a common unit); negative controls (index shifted by +1 and by −1 row) must put the argmax at −1 / +1 respectively (NEG_RED).
  * any year failing PASS or NEG_RED => STOP (frozen §2.4: any guard red => stop).
Inputs copied to /dev/shm/alloc_2026-09-26/t7nc/: BTCUSDT_index.npz (sha pinned below after copy); META read in place on /workspace.
usage (pod2): /workspace/venv/bin/python -B t7nc_g3b.py  -> /dev/shm/alloc_2026-09-26/t7nc/T7NC_G3B.json ; exit 0 PASS, 2 STOP
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
D = "/dev/shm/alloc_2026-09-26/t7nc"
META = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
LEGS = ("/dev/shm/news2_2026-09-23/work/legs.npz", "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65")
IDX = (f"{D}/BTCUSDT_index.npz", sys.argv[1] if len(sys.argv) > 1 else None)   # sha of the copied Mac file, passed and asserted
T0, T1 = calendar.timegm((2023, 1, 1, 0, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))
EVAL_YEARS = (2023, 2024, 2025, 2026)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


for p, s in (META, LEGS, IDX): assert s and sha(p) == s, ("input sha", p)
M = np.load(META[0], allow_pickle=False); L = np.load(LEGS[0])
sym = [str(x) for x in L["symbols"]]; j = sym.index("BTCUSDT")
E = M["E_ts"].astype(np.int64); y = M["y4"][:, j].astype(np.float64)          # the ONLY return column read: BTCUSDT
I = np.load(IDX[0]); io = I["open_s"].astype(np.int64); ic = I["close"].astype(np.float64)
keep = (E >= T0) & (E <= T1); E = E[keep]; y = y[keep]
lv = np.concatenate([[0.0], np.cumsum(np.where(np.isfinite(y), np.log1p(y), np.nan))])[1:]   # log level at E_k + 4h (NaN propagates after a gap)
pos = np.searchsorted(io, E + 3 * 3600); okp = (pos < io.size) & (io[np.minimum(pos, io.size - 1)] == E + 3 * 3600)
ix = np.where(okp, np.log(ic[np.minimum(pos, io.size - 1)]), np.nan)


def detrend(a, w=6):
    o = np.full_like(a, np.nan)
    for i in range(a.size):
        lo, hi = max(0, i - w), min(a.size, i + w + 1); s = a[lo:hi]; f = np.isfinite(s)
        if np.isfinite(a[i]) and f.sum() >= 6: o[i] = a[i] - s[f].mean()
    return o


def spec(x, z):
    r = {}
    for h in range(-3, 4):
        a, b = (x[:x.size - h], z[h:]) if h >= 0 else (x[-h:], z[:z.size + h])
        m = np.isfinite(a) & np.isfinite(b); r[h] = float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 48 else float("nan")
    am = max((h for h in r if np.isfinite(r[h])), key=lambda h: r[h]); return am, r


yrs = np.array([time.gmtime(int(t)).tm_year for t in E]); rows = []
for yv in EVAL_YEARS:
    m = yrs == yv; x = detrend(lv[m]); z = detrend(ix[m])
    am, r = spec(x, z)
    zp = np.concatenate([[np.nan], z[:-1]]); zm = np.concatenate([z[1:], [np.nan]])
    amp, _ = spec(x, zp); amm, _ = spec(x, zm)
    ok = am == 0 and r[0] > max(r[-1], r[1]); red = amp == 1 and amm == -1
    rows.append({"year": yv, "anchors": int(m.sum()), "finite_level": int(np.isfinite(lv[m]).sum()), "finite_index": int(np.isfinite(ix[m]).sum()),
                 "argmax_rho": am, "rho": {str(h): round(v, 5) for h, v in r.items()}, "neg_shift_plus1_argmax": amp, "neg_shift_minus1_argmax": amm,
                 "PASS": bool(ok), "NEG_RED": bool(red)})
PASS = all(r["PASS"] and r["NEG_RED"] for r in rows) and [r["year"] for r in rows] == list(EVAL_YEARS)
rec = {"device": "t7nc_g3b.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {"META": META[1], "legs": LEGS[1], "btc_index": IDX[1]}, "returns_read": "META y4 BTCUSDT column only (guard; no candidate x return)",
       "rows": rows, "PASS": PASS, "STOP": not PASS}
b = json.dumps(rec, indent=1).encode(); p = f"{D}/T7NC_G3B.json"
with open(p + ".tmp", "wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
os.replace(p + ".tmp", p); assert sha(p) == hashlib.sha256(b).hexdigest()
print("T7NC_G3B", "PASS" if PASS else "STOP", hashlib.sha256(b).hexdigest()[:16], flush=True)
sys.exit(0 if PASS else 2)
