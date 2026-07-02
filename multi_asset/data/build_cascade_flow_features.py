"""D3 Stage-0C: liquidation-cascade proxy (family A) + order-flow persistence/toxicity (family C)
from the on-disk Tardis PERP trade stream (full drift coverage through 2026-05-31).

MECHANISM. Binance liquidations execute as MARKET orders in the public trade stream (forceOrder
feed is gone but the signatures remain): monotone same-side sweep runs, sub-second bursts, large-order
size asymmetry, high impact-per-volume. 2026 = deleveraging regime; cascades = information-free forced
flow -> 10-min reversion alpha, and trailing 1-6h cascade-state is the plausible driver of the ONE
surviving drift structure (short-decile x funding flip, H5 F3-F1=-3.59bps, day-clustered t=-2.43).
Family C (flow persistence/toxicity) fills the empty 1-6h band between the 600s model window and the
6h regime_prior: signed-flow autocorr, VPIN-like imbalance, 6h net-flow z, aggressor-ratio drift,
flow-price divergence (squeeze detector).

PRE-REGISTERED DESCRIPTORS (computed BEFORE any Ridge gate; see docstring at bottom for the frozen list).
All are strictly <=t: per-bar descriptors use only trades inside a fully-closed 5m bar; trailing
descriptors use only bars whose close <= the current bar's close. The gate joins each backtest row t
to the last bar with bar_close_ms <= t (one-full-bar shift), which is strict causality.

DISK-SAFE: reads the Tardis trades tree mode implicit read-only (never writes there); emits ONE small
5m-grid CSV. Streams gzip via pandas C-engine, one UTC-day file at a time, parallel over days.

Run on SERVER (data is there, ~2M rows/day):
  conda run -n hsy_v5push python multi_asset/data/build_cascade_flow_features.py \
    --start 2025-08-01 --end 2026-05-31 --procs 12 \
    --out exports/d3_cascade_flow_5m.csv
"""
from __future__ import annotations
import numpy as np, pandas as pd, os, argparse, glob
from datetime import datetime, timezone, timedelta
from multiprocessing import Pool

TRADES_ROOT_DEFAULT = "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/trades"
DAY_US   = 86_400_000_000
BAR_US   = 300_000_000          # 5m
NBAR     = DAY_US // BAR_US      # 288
BURST_US = 100_000              # 100ms sub-second window / sweep-run max inter-trade gap
BURST_K  = 5                    # >=K same-side trades within 100ms => burst trade

# per-bar raw descriptor columns emitted by the day worker
RAW_COLS = ["a_sweep_count","a_run_len_max","a_run_notional_signed","a_impact_per_notional",
            "a_burst_flow_signed","a_size_p99_med","a_size_asym_side",
            "sweep_net","sweep_notl_tot","net_notl","tot_notl","tot_amt","vwap"]
SWEEP_MIN_LEN = 2   # a sweep run must walk >=1 price step (strict monotone, gap<100ms)
SWEEP_EVENT_LEN = 3 # count runs of >=3 fills as a discrete forced-flow event


def _daterange(start: str, end: str):
    d0 = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    d1 = datetime.strptime(end,   "%Y-%m-%d").replace(tzinfo=timezone.utc)
    d = d0
    while d <= d1:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)


def _rolling_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing rolling sum of window w (inclusive of current), NaN where < w history."""
    c = np.concatenate([[0.0], np.nancumsum(np.nan_to_num(x))])
    out = c[w:] - c[:-w]
    return np.concatenate([np.full(w - 1, np.nan), out])


def _rolling_mean_std(x: np.ndarray, w: int):
    s1 = _rolling_sum(x, w); s2 = _rolling_sum(x * x, w)
    m = s1 / w; v = s2 / w - m * m
    return m, np.sqrt(np.clip(v, 0, None))


def process_day(args):
    day, trades_root = args
    fp = f"{trades_root}/{day}/binance-futures/BTCUSDT.csv.gz"
    if not os.path.exists(fp):
        return None
    try:
        df = pd.read_csv(fp, usecols=["timestamp", "side", "price", "amount"],
                         dtype={"timestamp": np.int64, "side": "string",
                                "price": np.float64, "amount": np.float64})
    except Exception as e:
        print(f"  [skip] {day}: {e}", flush=True)
        return None
    if len(df) < 100:
        return None
    ts   = df["timestamp"].values.astype(np.int64)
    o    = np.argsort(ts, kind="stable"); ts = ts[o]
    sgn  = np.where(df["side"].values[o] == "buy", 1.0, -1.0)
    price= df["price"].values[o]
    amt  = df["amount"].values[o]
    notl = price * amt
    sn   = sgn * notl                      # signed notional per trade

    day_start = (ts[0] // DAY_US) * DAY_US
    bar = ((ts - day_start) // BAR_US).astype(np.int64)
    np.clip(bar, 0, NBAR - 1, out=bar)

    def bc(idx_bar, wts=None):
        return np.bincount(idx_bar, weights=wts, minlength=NBAR)[:NBAR]

    is_buy = sgn > 0
    tot_notl = bc(bar, notl)
    buy_notl = bc(bar, np.where(is_buy, notl, 0.0))
    sell_notl= bc(bar, np.where(~is_buy, notl, 0.0))
    tot_amt  = bc(bar, amt)
    n_tr     = bc(bar).astype(np.float64)
    vwap     = np.where(tot_amt > 0, tot_notl / np.clip(tot_amt, 1e-12, None), np.nan)

    # ---- bursts (A5): >=K same-side trades within 100ms rolling window -> signed forced flow ----
    burst = np.zeros(len(ts), dtype=bool)
    for side_val in (True, False):
        idx = np.where(is_buy == side_val)[0]
        if len(idx) < BURST_K:
            continue
        t = ts[idx]
        lo = np.searchsorted(t, t - BURST_US, side="right")
        cnt = np.arange(len(t)) - lo + 1
        burst[idx[cnt >= BURST_K]] = True
    burst_notl_buy  = bc(bar, np.where(burst & is_buy,  notl, 0.0))
    burst_notl_sell = bc(bar, np.where(burst & ~is_buy, notl, 0.0))
    a_burst_flow_signed = (burst_notl_buy - burst_notl_sell) / np.clip(tot_notl, 1e-9, None)

    # ---- STRICT-monotone same-side sweep runs (A1-A4, A8/A9) ----
    # A sweep = consecutive same-side trades, gap<100ms, price walking STRICTLY in the aggressor's
    # adverse direction (buy: strictly up the ask; sell: strictly down the bid). Flat-price clusters
    # (same-level fills) are NOT sweeps and are broken here -- that is the book-walking signature.
    d_ts = np.diff(ts)
    side_change = sgn[1:] != sgn[:-1]
    gap_break   = d_ts >= BURST_US
    buy_i  = sgn[1:] > 0
    dprice = price[1:] - price[:-1]
    mono_viol = (buy_i & (dprice <= 0)) | ((~buy_i) & (dprice >= 0))   # STRICT: flat breaks the run
    brk = side_change | gap_break | mono_viol
    run_id = np.concatenate([[0], np.cumsum(brk)]).astype(np.int64)
    R = int(run_id[-1]) + 1
    r_len   = np.bincount(run_id, minlength=R).astype(np.float64)
    r_notl  = np.bincount(run_id, weights=notl, minlength=R)
    first_i = np.zeros(R, dtype=np.int64); first_i[run_id[::-1]] = np.arange(len(run_id))[::-1]
    last_i  = np.zeros(R, dtype=np.int64); last_i[run_id]        = np.arange(len(run_id))
    r_side  = sgn[first_i]
    r_bar   = bar[first_i]
    r_pmove = np.abs(price[last_i] - price[first_i])
    r_notl_signed = r_side * r_notl
    a_run_notional_signed = np.zeros(NBAR); a_run_len_max = np.zeros(NBAR); a_impact = np.zeros(NBAR)
    a_sweep_count = np.zeros(NBAR); sweep_net = np.zeros(NBAR); sweep_notl_tot = np.zeros(NBAR)
    sw = r_len >= SWEEP_MIN_LEN                                  # genuine sweeps only
    if sw.any():
        rr = pd.DataFrame({"bar": r_bar[sw], "notl": r_notl[sw], "notl_signed": r_notl_signed[sw],
                           "len": r_len[sw], "pmove": r_pmove[sw], "abs_notl": np.abs(r_notl[sw])})
        gi = rr.groupby("bar")
        top = rr.loc[gi["abs_notl"].idxmax().values]            # dominant sweep per bar
        b = top["bar"].values.astype(int)
        a_run_notional_signed[b] = top["notl_signed"].values
        a_impact[b] = top["pmove"].values / np.clip(top["abs_notl"].values, 1e-9, None)
        mx = gi["len"].max(); a_run_len_max[mx.index.values.astype(int)] = mx.values
        sn_sum = gi["notl_signed"].sum(); sweep_net[sn_sum.index.values.astype(int)] = sn_sum.values
        an_sum = gi["abs_notl"].sum(); sweep_notl_tot[an_sum.index.values.astype(int)] = an_sum.values
        ev = rr[rr["len"] >= SWEEP_EVENT_LEN].groupby("bar").size()
        a_sweep_count[ev.index.values.astype(int)] = ev.values

    # ---- trade-size asymmetry (A5/A6): per-bar p99/median, and p99 by side ----
    tmp = pd.DataFrame({"bar": bar, "amt": amt, "buy": is_buy})
    med = tmp.groupby("bar")["amt"].median()
    p99 = tmp.groupby("bar")["amt"].quantile(0.99)
    a_size_p99_med = np.full(NBAR, np.nan)
    a_size_p99_med[med.index.values.astype(int)] = (p99 / med.replace(0, np.nan)).values
    p99_buy = tmp[tmp.buy].groupby("bar")["amt"].quantile(0.99)
    p99_sell = tmp[~tmp.buy].groupby("bar")["amt"].quantile(0.99)
    pb = np.full(NBAR, np.nan); ps = np.full(NBAR, np.nan)
    pb[p99_buy.index.values.astype(int)] = p99_buy.values
    ps[p99_sell.index.values.astype(int)] = p99_sell.values
    a_size_asym_side = (pb - ps) / (pb + ps + 1e-12)

    out = pd.DataFrame({
        "bar_start_ms": (day_start + np.arange(NBAR) * BAR_US) // 1000,
        "a_sweep_count": a_sweep_count,
        "a_run_len_max": a_run_len_max,
        "a_run_notional_signed": a_run_notional_signed,
        "a_impact_per_notional": a_impact,
        "a_burst_flow_signed": a_burst_flow_signed,
        "a_size_p99_med": a_size_p99_med,
        "a_size_asym_side": a_size_asym_side,
        "sweep_net": sweep_net,
        "sweep_notl_tot": sweep_notl_tot,
        "net_notl": buy_notl - sell_notl,
        "tot_notl": tot_notl,
        "tot_amt": tot_amt,
        "vwap": vwap,
    })
    # empty bars (no trades) keep NaN price for grid continuity
    return out


def build_trailing(g: pd.DataFrame) -> pd.DataFrame:
    """Second pass on the concatenated 5m grid: family C + trailing-A cascade state + vol control.
    All trailing windows are inclusive-of-current-bar; join at <=t makes them strictly causal."""
    g = g.sort_values("bar_start_ms").reset_index(drop=True)
    net = g["net_notl"].values.astype(np.float64)
    tot = g["tot_notl"].values.astype(np.float64)
    buy_notl = ((tot + net) / 2.0)
    logp = np.log(g["vwap"].replace(0, np.nan).ffill().values)
    ret5 = np.concatenate([[np.nan], np.diff(logp)])
    sweep_net = g["sweep_net"].values.astype(np.float64)
    sweep_mag = g["sweep_notl_tot"].values.astype(np.float64)

    W1, W6, W24 = 12, 72, 288       # 1h, 6h, 24h in 5m bars

    # C1 signed-flow lag-1 autocorr over trailing 1h (vectorized pair-window)
    x = net; xm1 = np.concatenate([[np.nan], net[:-1]])
    Sx = _rolling_sum(x, W1); Sy = _rolling_sum(xm1, W1)
    Sxx = _rolling_sum(x * x, W1); Syy = _rolling_sum(xm1 * xm1, W1)
    Sxy = _rolling_sum(x * xm1, W1)
    cov = Sxy / W1 - (Sx / W1) * (Sy / W1)
    vx = Sxx / W1 - (Sx / W1) ** 2; vy = Syy / W1 - (Sy / W1) ** 2
    c_flow_ac1_1h = cov / np.sqrt(np.clip(vx * vy, 1e-18, None))

    # C2 VPIN-like imbalance over trailing 1h
    c_vpin_1h = _rolling_sum(np.abs(net), W1) / np.clip(_rolling_sum(tot, W1), 1e-9, None)

    # C3 trailing-6h net-flow z vs trailing-24h distribution
    nf6 = _rolling_sum(net, W6)
    m6, s6 = _rolling_mean_std(nf6, W24)
    c_netflow_z_6h = (nf6 - m6) / np.clip(s6, 1e-9, None)

    # C4 aggressor-ratio drift: buy-frac last 1h minus prior 5h
    bf1 = _rolling_sum(buy_notl, W1) / np.clip(_rolling_sum(tot, W1), 1e-9, None)
    buy5 = _rolling_sum(buy_notl, W6) - _rolling_sum(buy_notl, W1)
    tot5 = _rolling_sum(tot, W6) - _rolling_sum(tot, W1)
    bf_prior5h = buy5 / np.clip(tot5, 1e-9, None)
    c_aggr_ratio_drift = bf1 - bf_prior5h

    # C5 flow-price divergence (squeeze): z(net 1h) * (-z(ret 1h))
    nf1 = _rolling_sum(net, W1)
    ret1 = logp - np.concatenate([np.full(W1, np.nan), logp[:-W1]])
    mnf, snf = _rolling_mean_std(nf1, W24); znf = (nf1 - mnf) / np.clip(snf, 1e-9, None)
    mr, sr = _rolling_mean_std(ret1, W24); zr = (ret1 - mr) / np.clip(sr, 1e-9, None)
    c_flow_price_div_1h = znf * (-zr)

    # trailing-A cascade state (net forced-flow direction; 6h cascade magnitude)
    a_casc_net_1h = _rolling_sum(sweep_net, W1)
    a_casc_intensity_6h = _rolling_sum(sweep_mag, W6)

    # vol control for double-sort (trailing 1h realized vol of 5m perp mid returns)
    _, vol1 = _rolling_mean_std(ret5, W1)
    aux_trail_vol_1h = vol1

    g["bar_close_ms"] = g["bar_start_ms"] + BAR_US // 1000
    g["c_flow_ac1_1h"] = c_flow_ac1_1h
    g["c_vpin_1h"] = c_vpin_1h
    g["c_netflow_z_6h"] = c_netflow_z_6h
    g["c_aggr_ratio_drift"] = c_aggr_ratio_drift
    g["c_flow_price_div_1h"] = c_flow_price_div_1h
    g["a_casc_net_1h"] = a_casc_net_1h
    g["a_casc_intensity_6h"] = a_casc_intensity_6h
    g["aux_trail_vol_1h"] = aux_trail_vol_1h
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--trades-root", default=TRADES_ROOT_DEFAULT)
    a = ap.parse_args()
    days = list(_daterange(a.start, a.end))
    print(f"build_cascade_flow: {len(days)} days {a.start}..{a.end} procs={a.procs}", flush=True)
    tasks = [(d, a.trades_root) for d in days]
    parts = []
    with Pool(a.procs) as pool:
        for i, res in enumerate(pool.imap(process_day, tasks, chunksize=1)):
            if res is not None:
                parts.append(res)
            if (i + 1) % 20 == 0:
                print(f"  processed {i+1}/{len(days)} days ({len(parts)} ok)", flush=True)
    if not parts:
        print("NO DATA"); return
    g = pd.concat(parts, ignore_index=True)
    g = build_trailing(g)
    cols = ["bar_start_ms", "bar_close_ms",
            "a_sweep_count", "a_run_len_max", "a_run_notional_signed", "a_impact_per_notional",
            "a_burst_flow_signed", "a_size_p99_med", "a_size_asym_side",
            "a_casc_net_1h", "a_casc_intensity_6h",
            "c_flow_ac1_1h", "c_vpin_1h", "c_netflow_z_6h",
            "c_aggr_ratio_drift", "c_flow_price_div_1h", "aux_trail_vol_1h"]
    g = g[cols]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    g.to_csv(a.out, index=False, float_format="%.6g")
    print(f"WROTE {a.out}  rows={len(g)}  span={g.bar_start_ms.min()}..{g.bar_start_ms.max()}", flush=True)
    print("DONE_CASCADE_FLOW.")


# ============================================================================
# PRE-REGISTERED DESCRIPTOR LIST (frozen 2026-07-02, BEFORE Ridge gate).
# Family A (liquidation-cascade proxy), kill gate: pooled drift Delta < +0.005.
#   A1 a_sweep_count          # # STRICT-monotone same-side sweep runs (>=3 fills) per bar [forced-flow events]
#   A2 a_run_len_max          # max sweep-run length (# fills walked)
#   A3 a_run_notional_signed  # signed notional of the dominant sweep run (+buy/-sell)
#   A4 a_impact_per_notional  # |price move| / notional of the dominant sweep [impact per forced unit]
#   A5 a_burst_flow_signed    # (buy-burst - sell-burst) notional / total  [signed sub-second forced flow]
#   A6 a_size_p99_med         # bar trade-size p99 / median  [large forced orders]
#   A7 a_size_asym_side       # (p99 buy size - p99 sell size)/(sum)  [side of the big orders]
#   A8 a_casc_net_1h          # trailing 1h net signed sweep notional  [forced-flow direction]
#   A9 a_casc_intensity_6h    # trailing 6h total sweep notional        [cascade magnitude state]
# Family C (flow persistence/toxicity 1-6h), kill gate: pooled drift Delta < +0.003.
#   C1 c_flow_ac1_1h          # lag-1 autocorr of 5m signed net-flow, trailing 1h
#   C2 c_vpin_1h              # VPIN-like sum|net|/sum(tot), trailing 1h
#   C3 c_netflow_z_6h         # trailing-6h cumulative net-flow, z vs trailing 24h
#   C4 c_aggr_ratio_drift     # buy-frac(1h) - buy-frac(prior 5h)
#   C5 c_flow_price_div_1h    # z(net 1h) * (-z(ret 1h))  [squeeze / price-against-flow]
# aux_trail_vol_1h            # trailing-1h realized vol of 5m perp mid  [double-sort CONTROL, not a feature]
# ============================================================================
if __name__ == "__main__":
    main()
