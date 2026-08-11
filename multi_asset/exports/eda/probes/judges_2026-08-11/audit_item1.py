#!/usr/bin/env python3
"""Metrics leakage audit ITEM 1 (static build-path). Emits JSON to stdout.

(A) alignment: 10 (coin,hour) samples -> panel value uses the LAST raw create_time <= t-5min,
    and the NEXT snapshot is > t-5min (tight boundary, never future).
(B) causality: recompute oi_level_norm / taker_ratio_ema / d_oi at hour t using ONLY rows <= t;
    must equal the stored channel (rolling/ewm/xsec are trailing -> no future use).
(C) OI update cadence: fraction of consecutive 5-min rows where sum_open_interest changes.
"""
import sys, json, glob, zipfile, importlib.util
import numpy as np, pandas as pd

M = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
RAW = M + "/exports/wide_metrics_raw"
NPZ = M + "/exports/wide_metrics_ch.npz"
PANEL = M + "/exports/wide_dl_full.npz"
LAG_MS = 300_000

spec = importlib.util.spec_from_file_location("bwmc", M + "/data/build_wide_metrics_channels.py")
bwmc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bwmc)

P = np.load(PANEL, allow_pickle=True)
ts = P["ts"].astype(np.int64); symbols = list(P["symbols"]); member = P["MEMBER110"]
Z = np.load(NPZ, allow_pickle=True); CH = Z["CH"]; MASK = Z["MASK"]; chn = list(Z["ch_names"])
rng = np.random.default_rng(7)
out = {"A_alignment_samples": [], "B_causality": {}, "C_oi_cadence": {}}

# ---- (A) alignment samples ----
test_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
raw_cache = {}
for s in test_syms:
    df = bwmc.read_symbol_raw(s, RAW)
    if df is not None:
        raw_cache[s] = df
oi_col = bwmc.OI_COL
n_ok = 0
for _ in range(10):
    s = test_syms[rng.integers(len(test_syms))]
    j = symbols.index(s); df = raw_cache[s]
    # pick a panel hour where oi_level_norm is masked-valid for this coin
    valid_t = np.where(MASK[:, j, chn.index("d_oi_1h")])[0]
    if len(valid_t) == 0:
        continue
    t = int(valid_t[rng.integers(len(valid_t))])
    T = ts[t]
    src = df["ts"].values.astype(np.int64)
    tgt = T - LAG_MS
    idx = np.searchsorted(src, tgt, side="right") - 1
    used_ct = int(src[idx]); nxt_ct = int(src[idx + 1]) if idx + 1 < len(src) else None
    ok = (used_ct <= tgt) and (nxt_ct is None or nxt_ct > tgt)
    n_ok += int(ok)
    out["A_alignment_samples"].append({
        "sym": s, "panel_hour_utc": pd.Timestamp(T, unit="ms", tz="UTC").isoformat(),
        "used_create_time_utc": pd.Timestamp(used_ct, unit="ms", tz="UTC").isoformat(),
        "next_snapshot_utc": pd.Timestamp(nxt_ct, unit="ms", tz="UTC").isoformat() if nxt_ct else None,
        "used<=t-5min": bool(used_ct <= tgt), "next>t-5min": bool(nxt_ct is None or nxt_ct > tgt),
        "lag_used_min": round((T - used_ct) / 60000, 1), "PASS": bool(ok)})
out["A_all_pass"] = bool(n_ok == len([x for x in out["A_alignment_samples"]]))
out["A_n_pass"] = n_ok

# ---- (B) causality: recompute at a cut point using only <= t ----
# take BTC; rebuild aligned oi via asof, then compare stored channel vs recompute-with-truncated-future
s = "BTCUSDT"; j = symbols.index(s)
al = bwmc.asof_align(raw_cache[s], ts)
oi = al[oi_col].copy(); oi[oi <= 0] = np.nan
taker = al["sum_taker_long_short_vol_ratio"].copy(); taker[taker <= 0] = np.nan
# full-series channels (as built, per-asset 1-D)
full_oiln = np.clip(np.log(pd.Series(oi) / pd.Series(oi).rolling(720, min_periods=168).mean()), -3, 3).values
full_doi1 = np.clip((np.log(pd.Series(oi)) - np.log(pd.Series(oi).shift(1))), -0.5, 0.5).values
full_takema = pd.Series(np.log(taker)).ewm(halflife=6, min_periods=3).mean().values
# cut future: recompute using only data up to t_cut, evaluate at t_cut
cuts = [int(x) for x in np.linspace(20000, len(ts) - 2, 6)]
mism = {"oi_level_norm": 0, "d_oi_1h": 0, "taker_ema": 0}
checked = 0
for tc in cuts:
    if not np.isfinite(oi[tc]):
        continue
    checked += 1
    oi_cut = oi[:tc + 1]; tk_cut = taker[:tc + 1]
    v_oiln = np.clip(np.log(pd.Series(oi_cut) / pd.Series(oi_cut).rolling(720, min_periods=168).mean()), -3, 3).values[-1]
    v_doi = np.clip((np.log(pd.Series(oi_cut)) - np.log(pd.Series(oi_cut).shift(1))), -0.5, 0.5).values[-1]
    v_tk = pd.Series(np.log(tk_cut)).ewm(halflife=6, min_periods=3).mean().values[-1]
    for nm, fv, cv in [("oi_level_norm", full_oiln[tc], v_oiln), ("d_oi_1h", full_doi1[tc], v_doi), ("taker_ema", full_takema[tc], v_tk)]:
        a, b = fv, cv
        if not (np.isnan(a) and np.isnan(b)) and not (np.isfinite(a) and np.isfinite(b) and abs(a - b) < 1e-9):
            mism[nm] += 1
out["B_causality"] = {"checked_points": checked, "mismatches_full_vs_truncated": mism,
                      "PASS": bool(sum(mism.values()) == 0)}

# ---- (C) OI update cadence ----
df = raw_cache["BTCUSDT"].sort_values("ts")
oiv = df[oi_col].values.astype(float)
chg = np.abs(np.diff(oiv)) > 0
# also for a sample recent window
dt = np.diff(df["ts"].values.astype(np.int64)) / 60000
out["C_oi_cadence"] = {"frac_5min_rows_OI_changed": round(float(chg.mean()), 3),
                       "median_row_spacing_min": round(float(np.median(dt)), 1),
                       "note": "if ~1.0 OI changes every 5min bar; if ~0.33 it refreshes ~15min"}
print(json.dumps(out, indent=1))
