#!/usr/bin/env python3
"""Build wide-universe derivatives (OI/positioning) channels from Binance metrics.

5min metrics -> 1h panel-aligned channels, leakage-safe (<=t-5min, one-bar lag).
Channels (7): oi_level_norm, d_oi_1h, d_oi_24h, doi_x_ret,
              top_ls_ratio_z, top_vs_global_divergence, taker_ratio_ema.

Reads raw daily metrics zips (parallel per-symbol), aligns to wide_dl_full ts grid,
writes wide_metrics_ch.npz (ts, symbols, ch_names, CH[T,N,C], MASK[T,N,C]).
"""
import os, sys, glob, zipfile, argparse, warnings
import numpy as np, pandas as pd
from multiprocessing import Pool

warnings.filterwarnings("ignore")
PANEL = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"
LAG_MS = 300_000            # one 5-min bar conservative lag
STALE_MS = 6 * 3600_000     # last snapshot >6h before T -> NaN (coverage-gap guard)
OI_COL = "sum_open_interest_value"
COLS = ["sum_open_interest", "sum_open_interest_value",
        "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
        "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]

_PANEL_TS = None
_RAW_DIR = None


def _init(panel_ts, raw_dir):
    global _PANEL_TS, _RAW_DIR
    _PANEL_TS = panel_ts; _RAW_DIR = raw_dir


def read_symbol_raw(sym, raw_dir):
    files = sorted(glob.glob(os.path.join(raw_dir, sym, sym + "-metrics-*.zip")))
    if not files:
        return None
    parts = []
    for f in files:
        try:
            with zipfile.ZipFile(f) as z:
                with z.open(z.namelist()[0]) as fh:
                    parts.append(pd.read_csv(fh))
        except Exception as e:
            print("  WARN %s %s: %s" % (sym, os.path.basename(f), e), file=sys.stderr)
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)
    df["ts"] = pd.to_datetime(df["create_time"], utc=True).astype("int64") // 1_000_000
    df = df.sort_values("ts").drop_duplicates("ts", keep="last").reset_index(drop=True)
    return df[["ts"] + [c for c in COLS if c in df.columns]]


def asof_align(df, panel_ts):
    src = df["ts"].values.astype(np.int64)
    tgt = panel_ts.astype(np.int64) - LAG_MS
    idx = np.searchsorted(src, tgt, side="right") - 1
    valid = idx >= 0
    used = np.where(valid, src[np.clip(idx, 0, len(src) - 1)], -1)
    fresh = valid & ((panel_ts.astype(np.int64) - used) <= STALE_MS)
    out = {}
    for c in COLS:
        if c not in df.columns:
            continue
        a = np.full(len(panel_ts), np.nan)
        a[fresh] = df[c].values.astype(np.float64)[idx[fresh]]
        out[c] = a
    return out


def worker(sym):
    df = read_symbol_raw(sym, _RAW_DIR)
    if df is None:
        return (sym, None, 0, None, None)
    al = asof_align(df, _PANEL_TS)
    fin = np.isfinite(al.get(OI_COL, np.full(len(_PANEL_TS), np.nan)))
    n_ok = int(fin.sum())
    first = int(_PANEL_TS[fin][0]) if n_ok else None
    last = int(_PANEL_TS[fin][-1]) if n_ok else None
    return (sym, al, n_ok, first, last)


def build(raw_dir, out_path, symbols_filter=None, nproc=8):
    P = np.load(PANEL, allow_pickle=True)
    ts = P["ts"].astype(np.int64); symbols = list(P["symbols"]); ch_names = list(P["ch_names"])
    member = P["MEMBER110"]
    ret1h = P["CH"][:, :, ch_names.index("ret_1h")].astype(np.float64)  # raw trailing 1h ret (sign)
    T, N = len(ts), len(symbols)
    use = [s for s in symbols if (symbols_filter is None or s in symbols_filter)]
    raw = {c: np.full((T, N), np.nan) for c in COLS}
    cov = {}
    with Pool(nproc, initializer=_init, initargs=(ts, raw_dir)) as pool:
        for sym, al, n_ok, first, last in pool.imap_unordered(worker, use, chunksize=1):
            j = symbols.index(sym)
            if al is not None:
                for c in COLS:
                    if c in al:
                        raw[c][:, j] = al[c]
            cov[sym] = {"hours": n_ok, "first_ms": first, "last_ms": last}
            print("  %-14s hours=%6d" % (sym, n_ok), flush=True)

    def roll_logmean_ratio(x, win, minp):
        rm = pd.DataFrame(x).rolling(win, min_periods=minp).mean()
        return np.log(pd.DataFrame(x) / rm).values

    def logdiff(x, k):
        s = pd.DataFrame(x)
        return (np.log(s) - np.log(s.shift(k))).values

    def xsec_z(x):
        m = member & np.isfinite(x)
        z = np.full_like(x, np.nan, dtype=np.float64)
        for t in range(T):
            msk = m[t]
            if msk.sum() >= 10:
                v = x[t, msk]; mu = v.mean(); sd = v.std()
                if sd > 1e-9:
                    z[t, msk] = (v - mu) / sd
        return np.clip(z, -4, 4)

    oi = raw[OI_COL].copy(); oi[oi <= 0] = np.nan
    top_pos = raw["sum_toptrader_long_short_ratio"].copy(); top_pos[top_pos <= 0] = np.nan
    glob_acc = raw["count_long_short_ratio"].copy(); glob_acc[glob_acc <= 0] = np.nan
    taker = raw["sum_taker_long_short_vol_ratio"].copy(); taker[taker <= 0] = np.nan

    ch = {}
    ch["oi_level_norm"] = np.clip(roll_logmean_ratio(oi, 720, 168), -3, 3)
    ch["d_oi_1h"] = np.clip(logdiff(oi, 1), -0.5, 0.5)
    ch["d_oi_24h"] = np.clip(logdiff(oi, 24), -1, 1)
    ch["doi_x_ret"] = ch["d_oi_1h"] * np.sign(ret1h)
    ch["top_ls_ratio_z"] = xsec_z(np.log(top_pos))
    ch["top_vs_global_divergence"] = xsec_z(np.log(top_pos) - np.log(glob_acc))
    taker_ema = pd.DataFrame(np.log(taker)).ewm(halflife=6, min_periods=3).mean().values
    ch["taker_ratio_ema"] = xsec_z(taker_ema)

    ch_out = ["oi_level_norm", "d_oi_1h", "d_oi_24h", "doi_x_ret",
              "top_ls_ratio_z", "top_vs_global_divergence", "taker_ratio_ema"]
    C = len(ch_out)
    CH = np.full((T, N, C), np.nan, dtype=np.float32)
    for c, name in enumerate(ch_out):
        CH[:, :, c] = ch[name].astype(np.float32)
    MASK = np.isfinite(CH) & member[:, :, None]
    CH_store = np.where(MASK, CH, 0.0).astype(np.float32)
    np.savez_compressed(out_path, ts=ts, symbols=np.array(symbols, dtype=object),
                        ch_names=np.array(ch_out, dtype=object),
                        CH=CH_store, MASK=MASK)
    memcells = int(member.sum())
    print("\nSAVED %s  CH%s  member-cells=%d" % (out_path, CH_store.shape, memcells))
    for c, name in enumerate(ch_out):
        frac = MASK[:, :, c].sum() / max(memcells, 1)
        print("  %-26s member-coverage=%.3f" % (name, frac))
    return cov


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw_dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--symbols", default="")
    ap.add_argument("--nproc", type=int, default=8)
    a = ap.parse_args()
    sf = set(a.symbols.split(",")) if a.symbols else None
    build(a.raw_dir, a.out, sf, a.nproc)
