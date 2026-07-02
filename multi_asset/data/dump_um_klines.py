"""D3 Stage-0C family B: basket error-correction / breadth / dispersion (cross-asset state).

MECHANISM. BTC is anchored by the alt basket (index/basket flow); when BTC diverges from a
rolling-beta-weighted 13-alt basket the spread mean-reverts (error-correction) -> a genuinely
orthogonal mean-direction channel absent from the model's X (zero cross-asset content). Breadth,
cross-sectional dispersion, and alt-BTC beta/corr compression are the risk-on/off state that
gates when the reversion pays. These live at the 1-6h scale (10-360 obs/window) so 1m um-futures
klines from data.binance.vision are sufficient (1s alt bars are not needed for this family).

Universe (matches CLAUDE.md): BTC + 13 alts = ETH SOL BNB XRP DOGE ADA LINK BCH TRX LTC DOT FIL ETC.

Outputs an HOURLY-grid CSV (close_time_ms + B1..B6), joined by the gate at close_time_ms <= t.
Also provides a `splice` subcommand: on the bar_data overlap months (2025-10/11) it compares
klines-derived 1h alt returns vs bar_data-derived 1h returns; per-symbol corr must be >= 0.99.

Run on SERVER (has internet + bar_data for splice):
  conda run -n hsy_v5push python multi_asset/data/dump_um_klines.py build \
    --start 2024-01 --end 2026-05 --out exports/d3_basket_ecm_1h.csv
  conda run -n hsy_v5push python multi_asset/data/dump_um_klines.py splice \
    --klines exports/d3_basket_ecm_1h.csv --months 2025-10 2025-11
"""
from __future__ import annotations
import numpy as np, pandas as pd, os, io, sys, argparse, zipfile, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
BTC = "BTCUSDT"
ALTS = ["ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT",
        "BCHUSDT","TRXUSDT","LTCUSDT","DOTUSDT","FILUSDT","ETCUSDT"]
SYMS = [BTC] + ALTS
# bar_data symbol keys for the splice check
BAR_KEY = {"BTCUSDT":"bnfbtc","ETHUSDT":"bnfeth","SOLUSDT":"bnfsol","BNBUSDT":"bnfbnb",
           "XRPUSDT":"bnfxrp","DOGEUSDT":"bnfdog","ADAUSDT":"bnfada","LINKUSDT":"bnflink",
           "BCHUSDT":"bnfbch","TRXUSDT":"bnftrx","LTCUSDT":"bnfltc","DOTUSDT":"bnfdot",
           "FILUSDT":"bnffil","ETCUSDT":"bnfetc"}
KL_COLS = ["open_time","open","high","low","close","volume","close_time",
           "quote_volume","count","taker_buy_base","taker_buy_quote","ignore"]
HOUR_MS = 3_600_000


def _months(start: str, end: str):
    y0, m0 = map(int, start.split("-")); y1, m1 = map(int, end.split("-"))
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12: m = 1; y += 1


def _load_month_1h(sym: str, ym: str) -> pd.DataFrame | None:
    """Download one monthly 1m-kline zip, aggregate to hourly close. Returns df[hour_ms, close]."""
    url = f"{BASE}/{sym}/1m/{sym}-1m-{ym}.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            buf = io.BytesIO(r.read())
    except Exception as e:
        print(f"  [miss] {sym} {ym}: {e}", flush=True)
        return None
    with zipfile.ZipFile(buf) as z:
        name = z.namelist()[0]
        raw = z.read(name).decode()
    # some monthly files carry a header row; detect by non-numeric first field
    first = raw.split("\n", 1)[0].split(",")[0]
    hdr = None if first.isdigit() else 0           # header row present iff first field non-numeric
    df = pd.read_csv(io.StringIO(raw), header=hdr,
                     names=(KL_COLS if hdr is None else None),
                     usecols=["open_time", "close"],
                     dtype={"open_time": np.int64, "close": np.float64})
    # some vintages store open_time in microseconds -> normalize to ms
    if df["open_time"].iloc[0] > 3_000_000_000_000:
        df["open_time"] //= 1000
    df["hour_ms"] = (df["open_time"] // HOUR_MS) * HOUR_MS
    h = df.groupby("hour_ms")["close"].last().reset_index()
    return h


def build(args):
    months = list(_months(args.start, args.end))
    tasks = [(sym, ym) for sym in SYMS for ym in months]
    print(f"downloading {len(tasks)} monthly kline files ({len(SYMS)} syms x {len(months)} months) "
          f"with {args.workers} workers ...", flush=True)
    got = {}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_load_month_1h, s, y): (s, y) for (s, y) in tasks}
        for f in as_completed(futs):
            got[futs[f]] = f.result()
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(tasks)} files", flush=True)
    price = {}
    for sym in SYMS:
        parts = [got[(sym, ym)] for ym in months if got.get((sym, ym)) is not None]
        if not parts:
            sys.exit(f"no data for {sym}")
        s = pd.concat(parts).drop_duplicates("hour_ms").set_index("hour_ms")["close"].sort_index()
        price[sym] = s
        print(f"  {sym}: {len(s)} hourly bars {s.index.min()}..{s.index.max()}", flush=True)

    grid = sorted(set().union(*[set(price[s].index) for s in SYMS]))
    P = pd.DataFrame({s: price[s].reindex(grid) for s in SYMS}, index=grid)
    P = P.ffill(limit=6)                       # tolerate short gaps only
    logp = np.log(P)
    ret = logp.diff()                          # 1h log-returns, all <=t at close_time
    btc_ret = ret[BTC]
    alt_ret = ret[ALTS]

    # B6 basket 1h return (equal-weight alt index; reverse lead-lag anchor)
    b_basket_ret_1h = alt_ret.mean(axis=1)

    # B1/B2 error-correction residual: trailing-7d beta of BTC~basket, 24h cumulative divergence
    W_BETA, W_SPREAD, W_Z = 168, 24, 168
    cov = btc_ret.rolling(W_BETA).cov(b_basket_ret_1h)
    var = b_basket_ret_1h.rolling(W_BETA).var()
    beta = (cov / var.replace(0, np.nan)).clip(-5, 5)
    resid_1h = btc_ret - beta * b_basket_ret_1h
    b_ecm_residual = resid_1h.rolling(W_SPREAD).sum()          # BTC out/under-perf vs basket, 24h
    b_ecm_resid_z = ((b_ecm_residual - b_ecm_residual.rolling(W_Z).mean())
                     / b_ecm_residual.rolling(W_Z).std().replace(0, np.nan))

    # B3 breadth: fraction of alts above their trailing-24h mean price
    alt_above = (logp[ALTS] > logp[ALTS].rolling(24).mean()).astype(float)
    b_breadth = alt_above.mean(axis=1)

    # B4 dispersion: cross-sectional std of alt 1h returns
    b_dispersion = alt_ret.std(axis=1)

    # B5 beta/corr compression: trailing-24h mean corr(alt_ret, btc_ret) across alts
    corrs = pd.DataFrame({a: alt_ret[a].rolling(24).corr(btc_ret) for a in ALTS}, index=grid)
    b_beta_compression = corrs.mean(axis=1)

    out = pd.DataFrame({
        "close_time_ms": np.array(grid, dtype=np.int64) + HOUR_MS,   # hour bar closes at start+1h
        "b_ecm_residual": b_ecm_residual.values,
        "b_ecm_resid_z": b_ecm_resid_z.values,
        "b_breadth": b_breadth.values,
        "b_dispersion": b_dispersion.values,
        "b_beta_compression": b_beta_compression.values,
        "b_basket_ret_1h": b_basket_ret_1h.values,
    })
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out.to_csv(args.out, index=False, float_format="%.6g")
    print(f"WROTE {args.out}  rows={len(out)}  span={out.close_time_ms.min()}..{out.close_time_ms.max()}")
    print("DONE_BASKET_ECM.")


def _bardata_mid_1h(bar_root, date_int, key):
    """Read ONLY time64 + mid_<key> from one bar_1s day HDF5 -> hourly-last mid (fast)."""
    import h5py
    ds = str(date_int)
    fp = f"{bar_root}/{date_int}/data_{ds[:4]}-{ds[4:6]}-{ds[6:]}.hdf5"
    with h5py.File(fp, "r") as f:
        t64 = f["time64"][:]                    # ns UTC
        mid = f[f"mid_{key}"][:]
    hour = (t64 // 1_000_000 // HOUR_MS) * HOUR_MS
    return pd.DataFrame({"hour_ms": hour, "mid": mid}).groupby("hour_ms")["mid"].last()


def splice(args):
    """Compare klines-derived 1h alt returns vs bar_data-derived 1h returns on overlap months.
    Reads only time64+mid from the bar_1s HDF5 (fast); a subset of days is enough for corr>=0.99."""
    import calendar
    bar_root = "/mnt/storage/share/bar_data/bar_1s"
    for mon in args.months:
        y, m = map(int, mon.split("-"))
        ndays = calendar.monthrange(y, m)[1]
        dates = [int(f"{y:04d}{m:02d}{d:02d}") for d in range(1, min(ndays, args.days) + 1)]
        print(f"\n=== splice {mon} (first {len(dates)} days) ===", flush=True)
        kh_all = _load_month_1h  # reuse for klines
        print(f"  {'sym':8s} {'n':>5s} {'corr':>7s}", flush=True)
        oks = []
        for sym in SYMS:
            key = BAR_KEY[sym]
            mids = []
            for dt_int in dates:
                try:
                    mids.append(_bardata_mid_1h(bar_root, dt_int, key))
                except Exception as e:
                    print(f"  {sym} {dt_int}: bar load fail {e}", flush=True)
            if not mids:
                continue
            barh = pd.concat(mids).groupby(level=0).last()
            bar_ret = np.log(barh.replace(0, np.nan)).diff()
            kh = _load_month_1h(sym, mon)
            if kh is None:
                continue
            kr = np.log(kh.set_index("hour_ms")["close"]).diff()
            j = pd.concat([kr.rename("kl"), bar_ret.rename("bar")], axis=1).dropna()
            if len(j) < 24:
                print(f"  {sym:8s} {len(j):5d}   too few", flush=True); continue
            c = j["kl"].corr(j["bar"]); oks.append(c)
            print(f"  {sym:8s} {len(j):5d} {c:7.4f}{'' if c>=0.99 else '  <<< BELOW 0.99'}", flush=True)
        if oks:
            print(f"  min corr={min(oks):.4f}  n_ge_0.99={sum(c>=0.99 for c in oks)}/{len(oks)}", flush=True)


# ============================================================================
# PRE-REGISTERED DESCRIPTOR LIST (frozen 2026-07-02, BEFORE Ridge gate).
# Family B (basket error-correction / breadth / dispersion), kill gate: pooled drift Delta < +0.005.
#   B1 b_ecm_residual       # 24h cumulative (BTC_ret - beta*basket_ret); +ve = BTC rich -> revert down
#   B2 b_ecm_resid_z        # z of B1 vs trailing 7d  [tradeable reversion signal]
#   B3 b_breadth            # fraction of 13 alts above their trailing-24h mean price
#   B4 b_dispersion         # cross-sectional std of alt 1h returns
#   B5 b_beta_compression   # trailing-24h mean corr(alt_ret, btc_ret)  [risk-on lockstep state]
#   B6 b_basket_ret_1h      # equal-weight alt basket 1h return  [reverse lead-lag anchor]
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--start", default="2024-01")
    b.add_argument("--end", default="2026-05"); b.add_argument("--out", required=True)
    b.add_argument("--workers", type=int, default=16)
    s = sub.add_parser("splice"); s.add_argument("--klines", required=True)
    s.add_argument("--months", nargs="+", default=["2025-10", "2025-11"])
    s.add_argument("--days", type=int, default=15, help="first N days of each month to check")
    a = ap.parse_args()
    (build if a.cmd == "build" else splice)(a)


if __name__ == "__main__":
    main()
