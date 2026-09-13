#!/usr/bin/env python3
"""fx_trd_build.py — FX-DATA TRD-01 step B1 (pod2, CPU, read-only on every input). Builds the canonical tradability artifact of
SPEC_TRADABILITY_2026-09-13.md (sha 99ae35e0, commit 73b59ec0) with the shared module multi_asset/exports/research/common/tradability.py.

Inputs (read-only, guarded sha): holefix2 5m cache (rows to 2026-09-01T00:00Z) and its x0910 extension (to 2026-09-11T00:00Z); T7's committed
1h perpetual klines (count column; third-party positive control, copied read-only to pod2) with its receipt.
Steps:
  P  preconditions (SPEC §1 a-d): symbol axes equal; x0910 prefix == holefix2 on log_cnt bitwise; ts grid spacing census; no fractional counts.
  S  bar states on the union axis (holefix2 rows + x0910 tail rows), log_cnt only (ret5 read for the frozen-close census only).
  A  decision states on the 4h grid (every ts ≡ 0 mod 14400 inside the data) for W24H and W4H via tradability.window_states.
  R  5m rolling flags for W24H and W4H via tradability.rolling_tradable; assert rolling == (anchor state == TRADABLE) at every grid row (SPEC §3).
  D  dual implementation: an independent loop over 400 random (anchor, symbol) cells + every anchor of 12 fixed symbols must equal A.
  T7 third-party control: per (symbol, hour) traded-in-hour from the cache (any TRADED bar with close in (h, h+3600]) vs T7 count > 0.
  C  census (descriptive; SPEC §4): last/first traded; dead_after name-anchors per year; lag name-anchors (TRADABLE ∧ dead_after); UNTRADED-state
     name-anchors of names that trade again later (halts / illiquid exclusions) with the top names; NODATA; frozen-close signature of UNTRADED bars.
Output: deterministic npz (fixed zip timestamps) + receipt JSON. Usage: python3 fx_trd_build.py <out_dir> <t7_dir> <t7_receipt.json>
"""
import os, sys, json, time, zipfile, hashlib, calendar
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
OUT_DIR, T7_DIR, T7_RECEIPT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T
assert T.SPEC_SHA256 == "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"; CACHE_X = "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
EXPECT = {CACHE: "1d7f459dee434ec4", CACHE_X: "8115299410cd5e8d"}
T0 = time.time()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
rec = {"device": "fx_trd_build.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)), "module": "tradability.py",
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")), "spec_sha256": T.SPEC_SHA256,
       "numpy": np.__version__, "env": {k: os.environ[k] for k in sorted(os.environ)}, "argv": sys.argv, "utc_start": utc(time.time())}
rec["inputs"] = {p: T.guarded_sha256(p) for p in (CACHE, CACHE_X)}
for p, pre in EXPECT.items(): assert rec["inputs"][p].startswith(pre), (p, rec["inputs"][p][:16], pre)
log("input shas ok")

def stream_channels(path, chans, first_row=0, block=20000):
    """read [rows >= first_row, :, chans] of data.npy inside an npz without materialising the full array"""
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        assert not fort and len(shape) == 3
        rowb = int(np.prod(shape[1:])) * dt.itemsize; skip = first_row * rowb
        while skip > 0:
            n = min(skip, 1 << 28); got = fh.read(n); assert len(got) == n; skip -= n
        n_rows = shape[0] - first_row; out = np.empty((n_rows, shape[1], len(chans)), dt); r = 0
        while r < n_rows:
            k = min(block, n_rows - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
            out[r:r + k] = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))[:, :, chans]; r += k
    return out, shape

# ---------------- P preconditions ----------------
Z = np.load(CACHE, allow_pickle=True); ZX = np.load(CACHE_X, allow_pickle=True)
SY = [str(s) for s in Z["symbols"]]; SYX = [str(s) for s in ZX["symbols"]]; CH = [str(c) for c in Z["ch"]]
assert SY == SYX, "P(a) symbol axes differ"; assert CH == [str(c) for c in ZX["ch"]] and CH[0] == "ret5" and CH[4] == "log_cnt", CH
TS = Z["ts"].astype(np.int64); TSX = ZX["ts"].astype(np.int64); NTS = len(TS)
assert np.array_equal(TSX[:NTS], TS), "P(b) x0910 ts prefix differs"
A_h, sh = stream_channels(CACHE, [0, 4]); log("holefix2 channels", A_h.shape, sh)
A_x, shx = stream_channels(CACHE_X, [0, 4]); log("x0910 channels", A_x.shape, shx)
pre_eq_cnt = bool(np.array_equal(A_x[:NTS, :, 1], A_h[:, :, 1], equal_nan=True)); pre_eq_ret = bool(np.array_equal(A_x[:NTS, :, 0], A_h[:, :, 0], equal_nan=True))
assert pre_eq_cnt, "P(b) x0910 prefix log_cnt != holefix2"
del A_h
ts5 = TSX; RET = A_x[:, :, 0]; LC = A_x[:, :, 1]
d = np.diff(ts5); gaps = {int(k): int(v) for k, v in zip(*np.unique(d, return_counts=True))}
rec["P"] = {"symbols": len(SY), "rows_holefix2": int(NTS), "rows_union": int(len(ts5)), "first_bar": utc(ts5[0]), "last_bar_holefix2": utc(TS[-1]), "last_bar": utc(ts5[-1]),
            "x0910_prefix_equal_log_cnt": pre_eq_cnt, "x0910_prefix_equal_ret5": pre_eq_ret, "spacing_census_s": gaps}
assert (d > 0).all(), "P(c) ts not increasing"
S = T.bar_states(LC)   # raises on P(d)
lcf = np.where(np.isfinite(LC), LC, np.float16(0)).astype(np.float32)
rec["P"]["log_cnt_min_positive"] = float(lcf[lcf > 0].min()); rec["P"]["log_cnt_max"] = float(lcf.max()); del lcf
finR = np.isfinite(RET)
rec["P"]["cells"] = {"TRADED": int((S == T.TRADED).sum()), "UNTRADED": int((S == T.UNTRADED).sum()), "NODATA": int((S == T.NODATA).sum()),
                     "TRADED_ret5_nan": int(((S == T.TRADED) & ~finR).sum()), "UNTRADED_ret5_nan": int(((S == T.UNTRADED) & ~finR).sum()),
                     "NODATA_ret5_finite": int(((S == T.NODATA) & finR).sum()), "UNTRADED_ret5_exactly0": int(((S == T.UNTRADED) & finR & (RET == 0)).sum()),
                     "UNTRADED_ret5_nonzero": int(((S == T.UNTRADED) & finR & (RET != 0)).sum())}
log("P", json.dumps(rec["P"]))
del RET, finR, LC, A_x

# ---------------- A decision states on the 4h grid ----------------
g0 = ((ts5[0] + 14399) // 14400) * 14400; anchor_ts = np.arange(g0, ts5[-1] + 1, 14400, dtype=np.int64)
st = {}; trunc = {}
for w in T.WINDOWS:
    st[w], trunc[w] = T.window_states(ts5, S, anchor_ts, window=w); log("A", w, st[w].shape, int((st[w] == T.TRADABLE).sum()))
# ---------------- R rolling 5m flags ----------------
roll = {}
row_of = np.searchsorted(ts5, anchor_ts); on_grid = (row_of < len(ts5)) & (ts5[np.minimum(row_of, len(ts5) - 1)] == anchor_ts)
for w in T.WINDOWS:
    roll[w] = T.rolling_tradable(ts5, S, window=w)
    eq = np.array_equal(roll[w][row_of[on_grid]], st[w][on_grid] == T.TRADABLE)
    rec.setdefault("R", {})[w] = {"anchors_on_grid": int(on_grid.sum()), "anchors_off_grid": int((~on_grid).sum()), "rolling_equals_anchor_state": bool(eq)}
    assert eq, ("R", w); log("R", w, "ok")
# ---------------- D dual implementation ----------------
rng = np.random.default_rng(20260913)
cells = [(int(rng.integers(0, len(anchor_ts))), int(rng.integers(0, len(SY)))) for _ in range(400)]
fixed_syms = ["BTCUSDT", "ETHUSDT", "FTTUSDT", "RAYUSDT", "SCUSDT", "STRAXUSDT", "DGBUSDT", "SNTUSDT", "LUNAUSDT", "1000XUSDT", "SOPHUSDT", "IOSTUSDT"]
cells += [(k, SY.index(s)) for s in fixed_syms if s in SY for k in range(len(anchor_ts))]
mism = {w: 0 for w in T.WINDOWS}
import bisect
_tl = {}
def _lists(j):   # independent of the cumsum path: sorted python lists of TRADED / UNTRADED close times, queried with bisect
    if j not in _tl:
        col = S[:, j]; _tl[j] = (ts5[col == T.TRADED].tolist(), ts5[col == T.UNTRADED].tolist())
    return _tl[j]
def _any_in(lst, a, b):   # any x in lst with a < x <= b
    i = bisect.bisect_right(lst, a); return i < len(lst) and lst[i] <= b
for (k, j) in cells:
    A = int(anchor_ts[k]); trl, unl = _lists(j)
    for w, ws in T.WINDOWS.items():
        naive = T.TRADABLE if _any_in(trl, A - ws, A) else (T.UNTRADED if _any_in(unl, A - ws, A) else T.NODATA)
        mism[w] += int(naive != st[w][k, j])
rec["D"] = {"cells_checked": len(cells), "fixed_symbols": [s for s in fixed_syms if s in SY], "mismatch": mism}
assert all(v == 0 for v in mism.values()), ("D", mism); log("D ok", len(cells))

# ---------------- C census ----------------
last_ts, first_ts = T.last_traded(ts5, S); data_end = int(ts5[-1])
dead = T.descriptive_dead_after(anchor_ts, last_ts, data_end)
yrs = np.array([yr(t) for t in anchor_ts])
cen = {}
for y in sorted(set(yrs.tolist())):
    m = yrs == y; s24 = st["W24H"][m]; s4 = st["W4H"][m]; dd = dead[m]
    later_trade = anchor_ts[m][:, None] < last_ts[None, :]          # the name trades again after this anchor (descriptive)
    cen[str(y)] = {"anchors": int(m.sum()), "dead_after_name_anchors": int(dd.sum()),
                   "W24H": {"TRADABLE": int((s24 == 2).sum()), "UNTRADED": int((s24 == 1).sum()), "NODATA": int((s24 == 0).sum()),
                            "lag_TRADABLE_and_dead": int(((s24 == 2) & dd).sum()), "UNTRADED_and_dead": int(((s24 == 1) & dd).sum()),
                            "UNTRADED_but_trades_again": int(((s24 == 1) & later_trade).sum())},
                   "W4H": {"TRADABLE": int((s4 == 2).sum()), "UNTRADED": int((s4 == 1).sum()), "NODATA": int((s4 == 0).sum()),
                           "lag_TRADABLE_and_dead": int(((s4 == 2) & dd).sum()), "UNTRADED_but_trades_again": int(((s4 == 1) & later_trade).sum())}}
rec["C"] = {"symbols_with_trades": int((last_ts >= 0).sum()), "symbols_without_trades": [SY[j] for j in np.where(last_ts < 0)[0]],
            "symbols_dead_inside_data": int(((last_ts >= 0) & (last_ts < data_end - 86400)).sum()), "by_year": cen}
# names excluded while they still trade later (W24H): name -> number of anchors, first/last such anchor
ex = (st["W24H"] == T.UNTRADED) & (anchor_ts[:, None] < last_ts[None, :])
cnt = ex.sum(0); top = np.argsort(-cnt)[:25]
rec["C"]["W24H_untraded_but_trades_again_top"] = {SY[j]: {"anchors": int(cnt[j]), "first": utc(anchor_ts[np.argmax(ex[:, j])]), "last": utc(anchor_ts[len(anchor_ts) - 1 - np.argmax(ex[::-1, j])]),
                                                           "last_trade": utc(last_ts[j])} for j in top if cnt[j] > 0}
ex4 = (st["W4H"] == T.UNTRADED) & (anchor_ts[:, None] < last_ts[None, :]); cnt4 = ex4.sum(0); top4 = np.argsort(-cnt4)[:25]
rec["C"]["W4H_untraded_but_trades_again_top"] = {SY[j]: int(cnt4[j]) for j in top4 if cnt4[j] > 0}
log("C", json.dumps(rec["C"]["by_year"])[:600])

# ---------------- T7 third-party control ----------------
t7r = json.load(open(T7_RECEIPT)); rec["T7"] = {"receipt_device_sha256": t7r.get("device_sha256"), "receipt_sha256": T.guarded_sha256(T7_RECEIPT)}
agg = {"hours_compared": 0, "both_traded": 0, "both_zero": 0, "t7_traded_cache_untraded": 0, "t7_zero_cache_traded": 0, "cache_nodata_t7_row": 0,
       "symbols": 0, "symbols_not_on_axis": 0}
worst = []
cs_tr = None
for fn in sorted(os.listdir(T7_DIR)):
    if not fn.endswith(".npz"): continue
    s = fn[:-4]
    if s not in SY: agg["symbols_not_on_axis"] += 1; continue
    j = SY.index(s); z7 = np.load(os.path.join(T7_DIR, fn)); h = z7["open_s"].astype(np.int64); c = z7["count"].astype(np.int64)
    keep = (h + 3600 <= data_end) & (h >= ts5[0]); h = h[keep]; c = c[keep]
    if not len(h): continue
    col = S[:, j]; ctr = np.concatenate([[0], np.cumsum(col == T.TRADED, dtype=np.int64)]); cfin = np.concatenate([[0], np.cumsum(col != T.NODATA, dtype=np.int64)])
    lo = np.searchsorted(ts5, h, side="right"); hi = np.searchsorted(ts5, h + 3600, side="right")
    ntr = ctr[hi] - ctr[lo]; nfin = cfin[hi] - cfin[lo]
    t7t = c > 0; ct = ntr > 0; nod = nfin == 0
    agg["symbols"] += 1; agg["hours_compared"] += int((~nod).sum()); agg["cache_nodata_t7_row"] += int(nod.sum())
    agg["both_traded"] += int((t7t & ct & ~nod).sum()); agg["both_zero"] += int((~t7t & ~ct & ~nod).sum())
    a1 = int((t7t & ~ct & ~nod).sum()); a2 = int((~t7t & ct & ~nod).sum()); agg["t7_traded_cache_untraded"] += a1; agg["t7_zero_cache_traded"] += a2
    if a1 + a2: worst.append((a1 + a2, s, a1, a2, utc(h[(t7t != ct) & ~nod][0])))
worst.sort(reverse=True)
rec["T7"].update(agg); rec["T7"]["mismatch_symbols_top"] = [dict(symbol=w[1], t7_traded_cache_untraded=w[2], t7_zero_cache_traded=w[3], first=w[4]) for w in worst[:20]]
rec["T7"]["agreement_share"] = (agg["both_traded"] + agg["both_zero"]) / max(agg["hours_compared"], 1)
log("T7", json.dumps(agg))

# ---------------- write deterministic artifact ----------------
def write_npz_deterministic(path, arrays):
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, np.ascontiguousarray(arrays[k]), allow_pickle=False)
    os.replace(tmp, path)
os.makedirs(OUT_DIR, exist_ok=True)
art = os.path.join(OUT_DIR, "tradability_v1.npz")
arrays = {"spec_sha256": np.array(T.SPEC_SHA256), "symbols": np.array(SY), "anchor_ts": anchor_ts, "data_end_ts": np.array(data_end, np.int64),
          "last_traded_ts": last_ts, "first_traded_ts": first_ts, "ts5": ts5,
          "traded5_bits": np.packbits(S == T.TRADED, axis=1), "nodata5_bits": np.packbits(S == T.NODATA, axis=1)}
for w in T.WINDOWS:
    arrays["state_" + w] = st[w]; arrays["truncated_" + w] = trunc[w]; arrays["tradable5m_%s_bits" % w] = np.packbits(roll[w], axis=1)
arrays["n_symbols"] = np.array(len(SY), np.int64)
write_npz_deterministic(art, arrays)
rec["artifact"] = {"path": art, "sha256": T.guarded_sha256(art), "bytes": os.path.getsize(art), "keys": sorted(arrays), "anchor_grid": [utc(anchor_ts[0]), utc(anchor_ts[-1]), int(len(anchor_ts))]}
A2 = T.Artifact.load(art, expected_sha256=rec["artifact"]["sha256"])
probe = A2.tradable(anchor_ts[-5:], SY, window="W24H"); assert np.array_equal(probe, st["W24H"][-5:] == T.TRADABLE)
rec["artifact"]["reload_roundtrip"] = True
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(os.path.join(OUT_DIR, "RECEIPT_fx_trd_build.json"), "w"), indent=1)
print("FX_TRD_BUILD_DONE", json.dumps({"sha256": rec["artifact"]["sha256"], "T7_agreement": rec["T7"]["agreement_share"], "dead_syms": rec["C"]["symbols_dead_inside_data"]}), flush=True)
