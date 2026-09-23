#!/usr/bin/env python3
"""m3_common.py — shared loaders for m3_feasibility.py / m3_readout.py (pod2): certified path directories → series (bt_tables, unchanged),
BTC daily returns from the pinned price table (M2's btc_daily, verbatim), per-window metrics (M2's metrics(), plus the slope SEs of m3_rules.ols).
Definitions are those frozen in m3_rules.py."""
import os, sys, hashlib

import numpy as np

DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_tables as BTT
import m3_rules as RU

DAY = 86400; BTC = "BTCUSDT"
PRICE = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy"; PRICE_SHA = "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"
META = "/workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz"; META_SHA = "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def pins_ok():
    if sha(PRICE) != PRICE_SHA or sha(META) != META_SHA: raise RU.Empty("price pins do not match")
    return {"price": PRICE_SHA, "meta": META_SHA, "bt_tables": sha(os.path.join(DEV, "bt_tables.py"))}


def load_dir(d, R=32):
    paths, files = BTT.load_run_dir(d, R)
    return {"paths": paths, "mean": BTT.series_mean(paths), "files": files, "dir": d, "file_sha256": {f: sha(os.path.join(d, f)) for f in files}}


def btc_daily(days):
    PM = np.load(META, allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; j = SY.index(BTC); g0 = int(PM["grid"][0])
    LP = np.load(PRICE, mmap_mode="r")
    days = np.asarray(days, np.int64)
    r0 = (days - g0) // 300; r1 = (days + DAY - g0) // 300
    if np.any((days - g0) % 300 != 0) or r1.max() >= LP.shape[0]: raise RU.Empty("BTC day boundary off the price grid")
    return np.expm1(np.asarray(LP[r1, j], float) - np.asarray(LP[r0, j], float))


def bmap_for(s):
    alld = np.unique((s["A"] // DAY) * DAY)
    alld = alld[alld + DAY <= int(s["A"][-1]) + 14400]                 # days whose end is on the grid of this run
    return {int(d): float(v) for d, v in zip(alld, btc_daily(alld))}


def metrics(s, a0, a1, bmap):
    days, rd, n_partial = RU.complete_days(s["A"], s["r"], a0, a1)
    rb = np.array([bmap[int(d)] for d in days])
    sub = BTT.restrict(s, a0, a1)
    o = RU.ols(rd, rb)
    return {"n_days": int(len(days)), "n_partial_days_excluded": n_partial, "n_anchors": int(len(sub["A"])), "sharpe": BTT.sharpe(rd),
            "total_return": float(np.prod(1.0 + rd) - 1.0), "cagr": BTT.cagr(rd), "maxdd_5m": BTT.maxdd_5m(sub, np.ones(len(sub["A"]), bool)),
            "worst_day": float(rd.min()), "mu_daily": float(rd.mean()), "sd_daily": float(rd.std(ddof=1)), "beta_daily_vs_btc": o["slope"],
            "beta_se_classical": o["se_classical"], "beta_se_newey_west_lag5": o["se_newey_west_lag5"], "corr_daily_vs_btc": float(np.corrcoef(rd, rb)[0, 1]),
            "sd_btc_daily": float(rb.std(ddof=1)), "g_bps_per_anchor": float(sub["g"].mean()), "price_bps": float(sub["pnl"].mean()),
            "funding_paid_bps": float(sub["car"].mean()), "fee_bps": float(sub["cst"].mean()), "unknown_excluded_bps": float(sub["unk"].mean()),
            "turnover_over_gross": float(sub["tau"].mean()), "day_stop_flattens": float(sub["dstop"].sum()), "per_name_stops": float(sub["nstop"].sum()),
            "halt_anchors": float(sub["halt"].sum())}


def path_dist(paths, a0, a1, bmap):
    per = [metrics(p, a0, a1, bmap) for p in paths]
    out = {}
    for k in ("sharpe", "maxdd_5m", "worst_day", "total_return", "beta_daily_vs_btc", "day_stop_flattens", "per_name_stops"):
        v = np.array([m[k] for m in per], float)
        if not np.all(np.isfinite(v)): raise RU.Empty(f"non-finite per-path {k}")
        out[k] = {"n_paths": len(v), "path_mean": float(v.mean()), "path_sd": float(v.std(ddof=1)), "p2.5": float(np.percentile(v, 2.5)),
                  "p50": float(np.percentile(v, 50)), "p97.5": float(np.percentile(v, 97.5))}
    return out


def daily_series(s, a0, a1, bmap):
    days, rd, _ = RU.complete_days(s["A"], s["r"], a0, a1)
    return days, rd, np.array([bmap[int(d)] for d in days])
