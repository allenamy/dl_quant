#!/usr/bin/env python3
"""t7_s1_common.py — shared cell construction for T7 S1 (frozen PREREG_T7_S1.md sha256 62c6da52…; §2.2–§2.4 and §11). Imported by t7_s1_guards.py and
t7_s1_build.py so guards and candidates read identical rules. Detail interpretations below are fixed here, before any S1 number exists.
BAR RULE (§2.2, §11.11): coin i, venue v, anchor N: o = latest KRW 60m bar open in [N-4h, N-1h] with volume > 0 (bars exist only when trades occurred; volume > 0 asserted).
VALID VENUE VALUE needs every leg at hour o:
  coin KRW bar (volume > 0); coin Binance index bar; coin Binance perp kline with count (trades) > 0 [§11.11];
  def A also: KRW-BTC bar at o (volume > 0), BTCUSDT index bar at o, BTCUSDT perp count > 0 at o;
  def B also: KRW-USDT bar u = latest open in [o-3h, o] with volume > 0.
EXCLUSIONS: (venue, symbol, month of N) in the G4 list [§2.4 G4 def-B rule union §11.10 five pairs]; or a G5-flagged venue-day of any KRW market used
  (coin; KRW-BTC for def A; KRW-USDT for def B) contains the bar used (Upbit UTC day; Bithumb KST day starting 15:00Z) [§2.4 G5, stricter reading].
PREMIUM: pA = ln Pkrw_i(o) - ln(Pidx_i(o)/mult) - [ln Pkrw_BTC(o) - ln Pidx_BTC(o)];  pB = ln Pkrw_i(o) - ln(Pidx_i(o)/mult) - ln Pkrw_USDT(u).
TURNOVER (§11.5 hourly): T24_v = sum of candle_acc_trade_price over bars with open in [N-24h, N-1h] (volume > 0); valid iff census first trading day <= N-24h,
  no G5-flagged day of that market intersects [N-24h, N), (venue, symbol, month(N)) not G4-excluded, and T24 > 0.
MERGE (§2.3, §11.5): usable venues = p_v valid and T24_v valid; p = sum(T24_v * p_v) / sum(T24_v) over usable venues; if no venue is usable but exactly one venue has a
  valid p_v, p = that p_v; otherwise NaN.
K3 KRW PART: X_v = T24_v / Pkrw_USDT_v(u*), u* = latest KRW-USDT bar open in [N-4h, N-1h] with volume > 0; K3krw = ln(sum of X_v over venues with valid T24_v and u*).
All KRW series are re-derived from the raw 60m pages with each gunzipped body checked against the manifest body_sha256."""
import os, json, gzip, hashlib, calendar, time, collections, math
import numpy as np
ROOT = "/Users/haosiyu/cc_tmp/krw_pull"
OFF = {"upbit": 0, "bithumb": 15 * 3600}
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def month_of(t): return time.strftime("%Y-%m", time.gmtime(int(t)))
def day_key(v, t): off = OFF[v]; return ((int(t) - off) // 86400) * 86400 + off
def plan(): return json.load(open(ROOT + "/plan/PULL_PLAN_FROZEN.json"))
def derive_krw(v, market, out_dir=ROOT + "/derived_s1"):
    """open_s, close, volume, turnover from raw 60m pages (body sha verified). Cached under derived_s1/<venue>/<market>.npz."""
    p = "%s/%s/%s.npz" % (out_dir, v, market)
    if os.path.exists(p):
        z = np.load(p); return {k: z[k] for k in ("open_s", "close", "volume", "turnover")}
    rows = {}; nbad = 0
    for l in open(ROOT + "/manifest/pages_%s.jsonl" % v):
        r = json.loads(l)
        if r.get("market") != market or r.get("unit") != "60m": continue
        raw = gzip.decompress(open(ROOT + "/" + r["file"], "rb").read())
        if hashlib.sha256(raw).hexdigest() != r["body_sha256"]: nbad += 1; continue
        for c in json.loads(raw):
            rows[ep(c["candle_date_time_utc"])] = (float(c["trade_price"]), float(c["candle_acc_trade_volume"]), float(c["candle_acc_trade_price"]))
    assert nbad == 0, ("BODY SHA MISMATCH", v, market, nbad)
    o = np.array(sorted(rows), dtype=np.int64)
    d = {"open_s": o, "close": np.array([rows[t][0] for t in o]), "volume": np.array([rows[t][1] for t in o]), "turnover": np.array([rows[t][2] for t in o])}
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + ".tmp.%d.npz" % os.getpid()
    np.savez_compressed(tmp, **d); os.replace(tmp, p)
    return d
def load_index(sym):
    p = ROOT + "/derived/binance_filled/%s.npz" % sym
    if not os.path.exists(p): return None
    z = np.load(p); return {"open_s": z["open_s"].astype(np.int64), "close": z["close"]}
def load_perp(sym):
    p = ROOT + "/derived/binance_klines/%s.npz" % sym
    if not os.path.exists(p): return None
    z = np.load(p); return {"open_s": z["open_s"].astype(np.int64), "count": z["count"]}
def at(series_open, t):
    """index of exact open == t (vectorized), -1 if absent."""
    i = np.searchsorted(series_open, t)
    ok = (i < len(series_open)) & (series_open[np.minimum(i, len(series_open) - 1)] == t)
    return np.where(ok, i, -1)
def latest_in(series_open, lo, hi):
    """index of latest open in [lo, hi] (vectorized), -1 if none."""
    i = np.searchsorted(series_open, hi, side="right") - 1
    ok = (i >= 0) & (series_open[np.maximum(i, 0)] >= lo)
    return np.where(ok, i, -1)
def load_g5():
    det = json.load(open(ROOT + "/checks/C3_MISMATCH_DETAIL.json"))
    g5 = collections.defaultdict(set)
    for x in det["days"]: g5[(x["venue"], x["market"])].add(ep(x["day_open_utc"]))
    return g5
def day_keys(v, t):
    t = np.asarray(t, dtype=np.int64); off = OFF[v]
    return np.where(t >= 0, ((t - off) // 86400) * 86400 + off, -1)
def venue_leg(v, N, months, krw, first_day, idx, perp, g5days, g4set, sym, kbtc, ibtc, pbtc, g5btc, kusdt, g5usdt, mult, leaky=False):
    """per-anchor arrays for one (venue, symbol) pair: pA, pB, T24, X_usdt, and diagnostics. N: int64 anchor epochs."""
    n = len(N); nan = np.full(n, np.nan)
    ko = krw["open_s"]; kv = krw["volume"]
    for _nm, _ser in (("coin", krw), ("btc", kbtc), ("usdt", kusdt)):
        if _ser is not None: assert np.all(_ser["volume"] > 0), ("non-positive volume bar present", v, sym, _nm)
    if leaky:   # negative control for G1: the bar that opens AT N (closes N+1h)
        io = at(ko, N)
    else:
        io = latest_in(ko, N - 4 * 3600, N - 3600)
    has = io >= 0; o = np.where(has, ko[np.maximum(io, 0)], -1)
    ix = at(idx["open_s"], o) if idx is not None else np.full(n, -1)
    pc = at(perp["open_s"], o) if perp is not None else np.full(n, -1)
    perp_ok = (pc >= 0) & ((perp["count"][np.maximum(pc, 0)] > 0) if perp is not None else False)
    g4bad = np.isin(months, [m for (vv, ss, m) in g4set if vv == v and ss == sym])
    dk = day_keys(v, o)
    g5bad = np.isin(dk, list(g5days)) if g5days else np.zeros(n, bool)
    base = has & (ix >= 0) & perp_ok & ~g4bad & ~g5bad
    lk = np.log(np.where(has, krw["close"][np.maximum(io, 0)], np.nan)) - np.log(np.where(ix >= 0, idx["close"][np.maximum(ix, 0)] / mult, np.nan)) if idx is not None else nan
    bk = at(kbtc["open_s"], o); bi = at(ibtc["open_s"], o); bp = at(pbtc["open_s"], o)
    btc_ok = (bk >= 0) & (bi >= 0) & (bp >= 0) & (pbtc["count"][np.maximum(bp, 0)] > 0)
    g5b = np.isin(dk, list(g5btc)) if g5btc else np.zeros(n, bool)
    vA = base & btc_ok & ~g5b
    pA = np.where(vA, lk - (np.log(np.where(bk >= 0, kbtc["close"][np.maximum(bk, 0)], np.nan)) - np.log(np.where(bi >= 0, ibtc["close"][np.maximum(bi, 0)], np.nan))), np.nan)
    if kusdt is not None:
        iu = latest_in(kusdt["open_s"], o - 3 * 3600, o); u = np.where(iu >= 0, kusdt["open_s"][np.maximum(iu, 0)], -1)
        du = day_keys(v, u); g5u = np.isin(du, list(g5usdt)) if g5usdt else np.zeros(n, bool)
        vB = base & (iu >= 0) & ~g5u & has
        pB = np.where(vB, lk - np.log(np.where(iu >= 0, kusdt["close"][np.maximum(iu, 0)], np.nan)), np.nan)
        iu2 = latest_in(kusdt["open_s"], N - 4 * 3600, N - 3600); usd_px = np.where(iu2 >= 0, kusdt["close"][np.maximum(iu2, 0)], np.nan)
    else:
        vB = np.zeros(n, bool); pB = nan.copy(); usd_px = nan.copy(); u = np.full(n, -1)
    cs = np.concatenate([[0.0], np.cumsum(krw["turnover"])])
    hi = np.searchsorted(ko, N - 3600, side="right"); lo = np.searchsorted(ko, N - 86400, side="left")
    T24 = cs[hi] - cs[lo]
    d1 = day_keys(v, N - 86400); d2 = day_keys(v, N - 3600)
    t5 = (np.isin(d1, list(g5days)) | np.isin(d2, list(g5days))) if g5days else np.zeros(n, bool)
    tv = (first_day <= N - 86400) & ~t5 & ~g4bad & (T24 > 0)
    T24v = np.where(tv, T24, np.nan)
    X = np.where(tv & np.isfinite(usd_px), T24 / usd_px, np.nan)
    diag = {"o": o, "u": u, "has_bar": has, "idx_ok": ix >= 0, "perp_ok": perp_ok, "btc_ok": btc_ok, "g4bad": g4bad, "g5bad": g5bad, "vA": vA, "vB": vB}
    return pA, pB, T24v, X, diag
def merge(pv_list, T_list):
    """§11.5 merge across venues: weighted by T24 over usable venues; single valid venue fallback."""
    P = np.stack(pv_list); T = np.stack(T_list)
    usable = np.isfinite(P) & np.isfinite(T) & (T > 0)
    wsum = np.where(usable, T, 0.0).sum(0)
    mp = np.where(wsum > 0, np.where(usable, T * np.nan_to_num(P), 0.0).sum(0) / np.where(wsum > 0, wsum, 1.0), np.nan)
    nvalid = np.isfinite(P).sum(0)
    single = np.where(nvalid == 1, np.nansum(np.where(np.isfinite(P), P, 0.0), 0), np.nan)
    return np.where(wsum > 0, mp, np.where(nvalid == 1, single, np.nan))
