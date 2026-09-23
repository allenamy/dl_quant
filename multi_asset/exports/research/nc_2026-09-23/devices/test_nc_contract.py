"""Red/green unit tests for nc_contract (DESIGN §A1/§A4/§A5/§A6 + FREEZE amendment 1). Every cell first asserts its baseline and
prints the measured values; a mutation of the rule must turn the cell red (the mutated function is built inside the test).
usage: python test_nc_contract.py <researcher feature_contract.py dir> <tradability.py dir>"""
import os, sys, json, math, importlib, copy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RES_DIR, TRAD_DIR = sys.argv[1], sys.argv[2]
sys.path.insert(0, RES_DIR); sys.path.insert(0, TRAD_DIR)
import nc_contract as NC
import feature_contract as FC          # researcher, e4338749
import tradability as TR

cells = []


def cell(name, ok, **detail):
    cells.append({"cell": name, "PASS": bool(ok), **detail})
    print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:300], flush=True)


# --- snap_interval
exp = {3600: 1.0, 7200: 2.0, 10800: 4.0, 14400: 4.0, 18000: 6.0, 21600: 6.0, 25200: 8.0, 28800: 8.0, 86400: 8.0, 86401: None,
       0: None, -3600: None, int(3.4 * 3600): 4.0, int(1.6 * 3600): 2.0, int(6.9 * 3600): 6.0, 5400: 2.0, 1800: 1.0}
got = {k: NC.snap_interval(k) for k in exp}
cell("A4.snap_interval_table", got == exp, got=got)


def snap_min(dt_s):     # mutation: ties to the SMALLER (the producer's old min() rule)
    h = dt_s / 3600.0
    if not (0 < h <= 24): return None
    return float(min(NC.IV_GRID, key=lambda a: abs(a - h)))


cell("A4.R_tie_rule_detected", any(snap_min(k) != v for k, v in exp.items()), mutated_3h=snap_min(10800))


def snap_old(dt_s):     # mutation: the producer's old rule (> 24 h -> 8, no unknown)
    h = dt_s / 3600.0
    return float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (h if 0 < h <= 24 else 8.0))))


cell("A4.R_gt24h_unknown_detected", snap_old(86401) != NC.snap_interval(86401), old=snap_old(86401), new=NC.snap_interval(86401))

# --- EMA vs researcher funding_state on a synthetic ledger with resets, interval switches and a > 24 h gap
rng = np.random.default_rng(7)
names = 3
fts, rates, offs = [], [], [0]
base = 1_700_000_000
for j in range(names):
    t = base + j * 3600
    seq = []
    for k in range(60):
        step = [14400, 28800, 3600, 14400, 90000][k % 5] if j == 1 else ([28800, 14400][k % 2] if j == 2 else 28800)
        t += step
        seq.append(t)
    fts.extend(seq); rates.extend(rng.normal(0, 1e-4, len(seq)).tolist()); offs.append(len(fts))
fts = np.array(fts, np.int64); rates = np.array(rates); offs = np.array(offs)
iv = np.full(len(fts), np.nan)
for j in range(names):
    b, e = offs[j], offs[j + 1]
    for i in range(b + 1, e):
        v = NC.snap_interval(int(fts[i] - fts[i - 1]))
        iv[i] = np.nan if v is None else v
anchors = np.arange(base + 14400, fts.max() + 14400, 14400, dtype=np.int64)
fe, fn, fi, rn = FC.funding_state(anchors, offs, fts, rates, iv)
mine = np.full(fe.shape, np.nan); mine_n = mine.copy(); mine_i = mine.copy(); mine_r = mine.copy()
for j in range(names):
    b, e = offs[j], offs[j + 1]
    led, state = [], None
    ev = list(zip(fts[b:e].tolist(), rates[b:e].tolist()))
    k = 0
    for a_i, A in enumerate(anchors):
        new = []
        while k < len(ev) and ev[k][0] <= A:
            new.append(ev[k]); k += 1
        led, state, _ = NC.ingest_settlements(led, state, new)
        if led:
            mine[a_i, j], mine_n[a_i, j], mine_i[a_i, j], mine_r[a_i, j] = NC.funding_asof(state, led[-1], A)


def same(a, b):
    return bool(np.array_equal(np.asarray(a, np.float64).view(np.uint64), np.asarray(b, np.float64).view(np.uint64)) or
                (np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(np.where(np.isnan(a), 0, a).view(np.uint64), np.where(np.isnan(b), 0, b).view(np.uint64))))


cell("A4.ema_asof_bitwise_vs_researcher_funding_state", same(mine, fe) and same(mine_n, fn) and same(mine_i, fi) and same(mine_r, rn),
     n_finite=int(np.isfinite(fe).sum()), n_nan=int(np.isnan(fe).sum()), resets=int(np.isnan(iv).sum()))
cell("A4.population_has_resets_and_stale", int(np.isnan(iv).sum()) >= names and int(np.isnan(fe).sum()) > 0,
     resets=int(np.isnan(iv).sum()), nan_cells=int(np.isnan(fe).sum()))


# mutation: the producer's OLD update (no reset, 1 s floor, a*(rn-acc) form) must differ
def old_update(led_rows):
    est = None; out = []
    for ft, rate, ivv in led_rows:
        ivv = 8.0 if ivv is None else ivv
        rnn = rate * (8.0 / ivv)
        if est is None: est = {"acc": rnn, "last_ts": ft}
        else:
            a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0))
            est = {"acc": est["acc"] + a * (rnn - est["acc"]), "last_ts": ft}
        out.append(est["acc"])
    return out


led1, st1, _ = NC.ingest_settlements([], None, list(zip(fts[offs[1]:offs[2]].tolist(), rates[offs[1]:offs[2]].tolist())))
new_series = []
st = None
for ft, rate, ivv in led1:
    st, v = NC.ema_step(st, ft, rate, ivv); new_series.append(v)
old_series = old_update(led1)
cell("A4.R_old_update_detected", not same(np.array(new_series), np.array(old_series)),
     n_differ=int(np.sum(~np.isclose(np.nan_to_num(new_series, nan=9.9), np.nan_to_num(old_series, nan=9.9), rtol=0, atol=0))))

# --- as-of freshness boundaries (A5, G11-1 / G11-2)
st = {"acc": 1e-4, "last_ts": 1000}
cell("A5.fresh_43200_counts", not math.isnan(NC.funding_asof(st, [1000, 1e-4, 8.0], 1000 + 43200)[0]))
cell("A5.stale_43201_excluded", math.isnan(NC.funding_asof(st, [1000, 1e-4, 8.0], 1000 + 43201)[0]))
cell("A5.ft_equal_anchor_counts", not math.isnan(NC.funding_asof(st, [1000, 1e-4, 8.0], 1000)[0]))
r = NC.funding_asof({"acc": None, "last_ts": None}, [1000, 1e-4, None], 1000)
cell("A5.unknown_interval_all_nan", all(math.isnan(x) for x in r), got=r)
cell("A5.fn_is_raw_rate_rn8_normalised", NC.funding_asof(st, [1000, 2e-4, 4.0], 1000)[1:] == (2e-4, 4.0, 2e-4 * 8 / 4.0))
try:
    NC.funding_asof(st, [2000, 1e-4, 8.0], 1000); fut = False
except NC.ContractError:
    fut = True
cell("A5.future_row_refused", fut)

# --- ingestion refuses duplicates / disorder
try:
    NC.ingest_settlements([[1000, 1e-4, None]], None, [(1000, 1e-4)]); dup = False
except NC.ContractError:
    dup = True
cell("A4.duplicate_event_refused", dup)

# --- legality (A1): TRADABLE W24H AND liveness; mutations: drop liveness / drop tradability
T5, N = 600, 4
ts5 = np.arange(1, T5 + 1, dtype=np.int64) * 300 + 1_700_000_000
lc = np.full((T5, N), np.log1p(3.0), np.float16); lq = np.full((T5, N), 5.0, np.float16)
lc[-288:, 1] = 0.0                                   # name 1: bars but no trades in 24 h -> not tradable
lc[-288:, 2] = np.nan; lq[-288:, 2] = np.nan         # name 2: no bars in 24 h -> not tradable, not live
lq[-288:, 3] = np.nan                                # name 3: trades counted but log_qv missing (hole-like) -> tradable, not live
L = NC.legal_live(ts5, lc, lq, [int(ts5[-1])], TR)[0]
cell("A1.legal_live_table", L.tolist() == [True, False, False, False], got=L.tolist())
trad_only = (TR.window_states(ts5, TR.bar_states(lc), [int(ts5[-1])], window="W24H")[0][0] == TR.TRADABLE)
cell("A1.R_liveness_matters", trad_only.tolist() != L.tolist(), tradable_only=trad_only.tolist())

# --- fund base (A6 / D12)
b = NC.fund_base(["A", "B", "C", "D"], [True, True, False, True], [True, False, True, True], [1e-4, 2e-4, 3e-4, float("nan")])
cell("A6.fund_base_legal_crypto_fresh", b == {"A": 1e-4}, got=b)

# --- return channel (amendment 1): G3-3 bound bar -> raw; non-bound -> f32(ch0); table gap cell fills NaN
ts = np.arange(10, dtype=np.int64) * 300
ch0 = np.array([[0.01], [np.float16(0.3)], [np.nan], [-0.02], [np.float16(-0.3)], [0.0], [0.005], [np.nan], [0.1], [0.2]], np.float16)
rr = NC.rr_from_ch0(ts, ch0, [ts[1], ts[4], ts[7]], [0, 0, 0], [0.4567, -0.2999, 0.0123])
cell("A3.G3_3_bound_bar_takes_raw", rr[1, 0] == np.float32(0.4567) and rr[1, 0] != np.float32(ch0[1, 0]), rr1=float(rr[1, 0]), f16=float(ch0[1, 0]))
cell("A3.nonbound_is_f32_ch0", bool(np.array_equal(rr[[0, 3, 5, 6, 8, 9], 0], ch0[[0, 3, 5, 6, 8, 9], 0].astype(np.float32))))
cell("A3.nan_stays_nan_unless_table", bool(np.isnan(rr[2, 0])) and rr[7, 0] == np.float32(0.0123))
cell("A3.needs_boundary_raw", NC.needs_boundary_raw(0.4567) and NC.needs_boundary_raw(0.29995) and not NC.needs_boundary_raw(0.2994) and NC.needs_boundary_raw(-0.31),
     f16_of_0p29995=float(np.float16(0.29995)))

ok = all(c["PASS"] for c in cells)
print(f"TEST_NC_CONTRACT {'PASS' if ok else 'FAIL'} cells={len(cells)} failed={[c['cell'] for c in cells if not c['PASS']]}", flush=True)
json.dump({"cells": cells, "PASS": ok}, open(os.path.join(HERE, "TEST_NC_CONTRACT.json"), "w"), indent=1, default=str)
sys.exit(0 if ok else 3)
