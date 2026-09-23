#!/usr/bin/env python3
"""s2_eval_betas_pod2.py — R10 A.4-5 stage 2, pod2, CPU only, read-only on the certified tables.

EVALUATION beta device = m2_lib.bars_4h + m2_lib.betas_at (the M2/M3/M3b research evaluation's library, sha pinned), on the certified
price table price_full_raw_x0918r (+ meta), loaded exactly as m2_btc_overlay_2026-09-23/devices/m2_build_targets.py L66-L91 does:
  PM = np.load(meta, allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; bj = SY.index("BTCUSDT")
  LP = np.load(npy, mmap_mode="r"); grid = PM["grid"].astype(np.int64)
  T, R, V = bars_4h(LP, grid, PM["first_fin"], PM["last_fin"], PM["unavail_grid_row"], PM["unavail_col"])
  B, NOBS, EST, RAW = betas_at(T, R, V, anchors, bj)
Extra small outputs (diagnostics): the certified 4h bars over the union window, first_fin / last_fin / has_kline, the UA and gap-filled
cells inside the union window, BTC's price at each anchor = ref_px * exp(LP[row(A)] - cref_raw) (bt_hist_sim31.FullPanel's formula,
devices_v3/bt_hist_sim31.py L120), the certified 5-minute simple return at every cache clip cell (argv list), and every certified
5-minute cell with |simple return| > 0.30 in the union window.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B s2_eval_betas_pod2.py PATH,HOME,LC_CTYPE \
         <out_dir> <clip_cells.json>
"""
import os, sys, json, time, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

T0 = time.time()
OUTD, CLIPF = sys.argv[2], sys.argv[3]
BT = "/workspace/baseline_tables_2026-09-19"
PIN = {"price_full_raw": (BT + "/work/price_full_raw_x0918r.npy", "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"),
       "price_full_meta": (BT + "/work/price_full_raw_x0918r_meta.npz", "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"),
       "m2_lib": (os.path.join(HERE, "m2_lib.py"), "93f8e76088ca523158df4d3ddb12f4f3239d0b75e3e0f7362ecc9ced914c8c9d")}
H4, ROW, NWIN = 14400, 300, 180
A_FIRST, A_LAST = 1789315200, 1789776000
ANCHORS = np.arange(A_FIRST, A_LAST + 1, H4, dtype=np.int64)
rec = dict(device="s2_eval_betas_pod2.py", self_sha256=M.sha_file(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ),
           numpy=np.__version__, python=sys.version, utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)


def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


os.makedirs(OUTD, exist_ok=True)
for k, (p, s) in PIN.items():
    got = M.sha_file(p); rec["inputs"][k] = {"path": p, "sha256": got}; check(f"pin.{k}", got == s, {"got": got[:16], "want": s[:16]})
rec["inputs"]["clip_cells"] = {"path": CLIPF, "sha256": M.sha_file(CLIPF)}
if FAILS:
    json.dump(rec, open(OUTD + "/S2_eval_pod2.json", "w"), indent=1, default=str); sys.exit("REFUSED pins")

PM = np.load(PIN["price_full_meta"][0], allow_pickle=True)
log("meta keys", PM.files)
SY = [str(s) for s in PM["symbols"]]; bj = SY.index(M.BTC); nS = len(SY)
LP = np.load(PIN["price_full_raw"][0], mmap_mode="r"); grid = PM["grid"].astype(np.int64)
check("price.shape", LP.shape == (len(grid), nS), list(LP.shape))
check("grid.5min_contiguous", bool(np.all(np.diff(grid) == ROW)), {"first": utc(grid[0]), "last": utc(grid[-1]), "n": len(grid)})
log("bars_4h ...")
T, R, V = M.bars_4h(LP, grid, PM["first_fin"], PM["last_fin"], PM["unavail_grid_row"], PM["unavail_col"])
log("bars", len(T), "valid cells", int(V.sum()), "T[-1]", utc(T[-1]))
check("anchors_le_last_4h_boundary", int(ANCHORS.max()) <= int(T[-1]), {"last_boundary": utc(T[-1]), "last_anchor": utc(ANCHORS.max())})
B, NOBS, EST, RAW = M.betas_at(T, R, V, ANCHORS, bj)
log("betas done", B.shape)

# union window bars (the 4h bars ending at A_FIRST-179*4h .. A_LAST)
Tb = np.arange(A_FIRST - (NWIN - 1) * H4, A_LAST + 1, H4, dtype=np.int64)
kb = ((Tb - int(T[0])) // H4).astype(np.int64)
check("union_bars_on_T", bool(np.all(T[kb] == Tb)) and int(kb.min()) >= 1)
# BTC price at each anchor
g0 = int(grid[0])
rowA = (ANCHORS - g0) // ROW
check("anchor_rows_on_grid", bool(np.all(grid[rowA] == ANCHORS)))
lpA = np.asarray(LP[rowA, bj], np.float64)
btc_px = float(PM["ref_px"][bj]) * np.exp(lpA - float(PM["cref_raw"][bj]))
check("btc_px_finite_positive", bool(np.all(np.isfinite(btc_px) & (btc_px > 0))), [round(float(x), 2) for x in btc_px[:3]])

# UA / gap-filled cells inside the union window rows (5-minute bars CLOSING in [Tb[0]-4h, A_LAST])
r_lo = (int(Tb[0]) - H4 - g0) // ROW; r_hi = int(rowA.max())
ug, uc = PM["unavail_grid_row"].astype(np.int64), PM["unavail_col"].astype(np.int64)
gg, gc = PM["gapfilled_grid_row"].astype(np.int64), PM["gapfilled_col"].astype(np.int64)
uin = (ug >= r_lo) & (ug <= r_hi); gin = (gg >= r_lo) & (gg <= r_hi)
log("UA cells in window", int(uin.sum()), "gap-filled cells in window", int(gin.sum()))

# certified 5-minute simple returns over the window rows (one contiguous slice) → cells |r| > 0.30, and the values at the cache clip cells
blk = np.asarray(LP[r_lo - 1:r_hi + 1, :], np.float64)
with np.errstate(invalid="ignore"):
    r5 = np.expm1(blk[1:] - blk[:-1])                       # row i ↔ grid row r_lo + i (the bar CLOSING there)
big = np.isfinite(r5) & (np.abs(r5) > 0.30)
bi, bc = np.nonzero(big)
cells = json.load(open(CLIPF))
clip_out = []
for t, s in cells:
    j = SY.index(s) if s in SY else -1
    rr = (int(t) - g0) // ROW - r_lo
    v = float(r5[rr, j]) if (j >= 0 and 0 <= rr < len(r5)) else None
    clip_out.append({"ts": int(t), "utc": utc(t), "sym": s, "cert_col": j, "cert_r5": v,
                     "is_UA": bool(j >= 0 and np.any((ug == r_lo + rr) & (uc == j))),
                     "is_gapfilled": bool(j >= 0 and np.any((gg == r_lo + rr) & (gc == j)))})
log("clip cells looked up", len(clip_out), "cert |r5|>0.30 cells", int(big.sum()))

np.savez_compressed(OUTD + "/S2_eval_pod2.npz", anchors=ANCHORS, symbols=np.array(SY), beta_eval=B, nobs_eval=NOBS, est_eval=EST, raw_eval=RAW,
                    Tb=Tb, R4_cert=R[kb], V_cert=V[kb], first_fin=PM["first_fin"].astype(np.int64), last_fin=PM["last_fin"].astype(np.int64),
                    has_kline=PM["has_kline"], btc_px=btc_px, btc_px_source=np.array("certified price_full_raw_x0918r: ref_px[BTC]*exp(LP[row(A),BTC]-cref_raw[BTC])"),
                    ua_ts=g0 + ug[uin] * ROW, ua_col=uc[uin], gf_ts=g0 + gg[gin] * ROW, gf_col=gc[gin],
                    big_ts=g0 + (r_lo + bi) * ROW, big_col=bc, big_r5=r5[bi, bc], T_last=np.int64(T[-1]))
rec["outputs"] = {"npz": OUTD + "/S2_eval_pod2.npz", "npz_sha256": M.sha_file(OUTD + "/S2_eval_pod2.npz")}
rec["clip_cells_cert"] = clip_out
rec["summary"] = {"n_anchors": len(ANCHORS), "T_last": utc(T[-1]), "n_est_per_anchor": EST.sum(1).tolist(),
                  "ua_cells_in_window": int(uin.sum()), "gapfilled_cells_in_window": int(gin.sum()), "cert_big_cells": int(big.sum()),
                  "btc_px": btc_px.tolist()}
rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUTD + "/S2_eval_pod2.json", "w"), indent=1, default=str)
print(("S2 ALL CHECKS OK" if not FAILS else f"S2 FAILURES {FAILS}"), "npz_sha256=" + rec["outputs"]["npz_sha256"], flush=True)
sys.exit(0 if not FAILS else 1)
