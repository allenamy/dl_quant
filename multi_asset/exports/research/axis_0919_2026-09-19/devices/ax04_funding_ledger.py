"""AX04 (axis_0919, stream D): per-settlement funding LEDGER with per-settlement intervals, window [AX_LO_S, AX_HI_S] (settlement second, inclusive),
plus a 4h accounting table on the cache anchor grid.

Why a ledger: r6_panel_splice.py gave every September REST row the interval AT FETCH TIME (x0910 defect, memory x0910_fund_iv_interval_mismatch:
547 f_fund_iv cells / 23 names wrong). Here a settlement's interval is derived from the settlement stream itself, never from fundingInfo:
  iv_src 0 'zip_col'   the monthly archive row carries an interval column (same parse as pod_panel_ext.py L117-130)
  iv_src 1 'gap'       round((t_i - t_{i-1}) / 3600) in (0, 24], snapped to {1,2,4,6,8} (pod_panel_ext.py L136-141 rule; T5d: gap == producer ledger, 0 disagreements)
  iv_src 2 'prod'      no usable gap (first settlement / gap > 24h / a second settlement 1 s after another, gap rounds to 0 h): producer ledger
                       interval at that exact settlement, if recorded
  iv_src 3 'next_gap'  NOT USED since rehearsal 2026-09-19 07:5xZ (kept as a code so receipts stay comparable): the next gap is recorded only as the
                       diagnostic column iv_next_gap
  iv_src 4 'default8'  otherwise 8 = the builders' own documented fallback (pod_panel_ext.py L136-139 "首行/失败默认 8"). Rehearsal finding: all 20
                       unresolved settlements in 08-21..09-18 are the SECOND of a pair 1 s apart on tokenized-stock perps (GLW, STRC, GOOGL, NVDA ...);
                       a next-gap rule gave 1 h and moved the seeded v1 EMA of GLW/STRC away from the builder rule (T5d ivfix used 8 there).
Rates: REST (fundingRate, fetched this round) > zip > fund_aug; every overlap between sources is compared and mismatches are counted.
Cross-checks (report only, never used to set a value except iv_src 2): producer ledger (live aux.json ledger_tail, read-only copy) and the T5d
interval-source ledger (aux snapshots 09-04 / 09-13). Dead contracts: flag after_last_trade = settlement later than the symbol's last TRADED bar
(log_cnt > 0) in the cache + 24h (memory dead_contracts_frozen_rows: funding after the last trade is not paid) — a flag, nothing is removed.
Accounting table (anchors A on the 4h grid, AX_LO_S <= A <= AX_HI_S): f_fund_now / f_fund_iv = last settlement <= A (stale > 12h => NaN; pod_panel_ext
rule); next4h_sum / next4h_n = sum / count of settlement rates in (A, A+4h] (NaN when A+4h > AX_HI_S); next4h_sum_live excludes after_last_trade rows.
env: AX_REST AX_FUND_AUG AX_FDIR AX_PROD_LEDGER AX_T5D_SRC AX_CACHE AX_LO_S AX_HI_S AX_OUT_NPZ AX_OUT_ACC AX_RECEIPT (all required; refuses to overwrite).
"""
import os, io, csv, sys, json, glob, gzip, zipfile, time, hashlib
import numpy as np
REQ = ["AX_REST", "AX_FUND_AUG", "AX_FDIR", "AX_PROD_LEDGER", "AX_T5D_SRC", "AX_CACHE", "AX_LO_S", "AX_HI_S", "AX_OUT_NPZ", "AX_OUT_ACC", "AX_RECEIPT"]
E = {k: os.environ[k] for k in REQ}
for k in ("AX_OUT_NPZ", "AX_OUT_ACC", "AX_RECEIPT"): assert not os.path.exists(E[k]), f"refuse to overwrite {E[k]}"
LO, HI = int(E["AX_LO_S"]), int(E["AX_HI_S"])
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
def snap(x): return float(ALLOWED[np.argmin(np.abs(ALLOWED - float(x)))])
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
t0 = time.time()
SYMS = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
REST = json.loads(gzip.open(E["AX_REST"], "rt").read()); RR = REST["rates_raw"]; INFO = REST.get("fundingInfo_at_fetch", {})
AUG = json.loads(gzip.open(E["AX_FUND_AUG"], "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
PL = json.load(open(E["AX_PROD_LEDGER"]))["ledger"]; PLD = {s: {int(r[0]): (r[1], r[2]) for r in v} for s, v in PL.items()}
T5 = json.load(open(E["AX_T5D_SRC"]))["ledger"]; T5D = {s: {int(r[0]): r[1] for r in v} for s, v in T5.items()}
# ---- last TRADED bar per symbol from the cache (channel log_cnt > 0), streamed
def stream_channel(path, ch, block=20000):
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        rowb = int(np.prod(shape[1:])) * dt.itemsize; out = np.empty((shape[0], shape[1]), dt); r = 0
        while r < shape[0]:
            k = min(block, shape[0] - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
            out[r:r + k] = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))[:, :, ch]; r += k
    return out
C = np.load(E["AX_CACHE"], allow_pickle=True); CTS = C["ts"].astype(np.int64); assert [str(s) for s in C["symbols"]] == SYMS
assert [str(c) for c in C["ch"]][4] == "log_cnt"
LC = stream_channel(E["AX_CACHE"], 4); traded = np.isfinite(LC) & (LC > 0)
last_row = np.where(traded.any(0), len(CTS) - 1 - np.argmax(traded[::-1], axis=0), -1)
LAST_TRADE = {s: (int(CTS[last_row[j]]) if last_row[j] >= 0 else None) for j, s in enumerate(SYMS)}
del LC, traded
print(f"[{time.time()-t0:.0f}s] cache last-traded computed; cache end {U(CTS[-1])}", flush=True)
cols = {k: [] for k in ("sym", "ts", "ts_ms", "rate", "mark", "iv", "iv_src", "srcbits", "iv_gap", "iv_next_gap", "prod_iv", "prod_rate", "t5d_iv", "after_last_trade", "aug_iv_fetchtime")}
cnt = {"rate_mismatch_rest_zip": 0, "rate_mismatch_rest_aug": 0, "rate_mismatch_zip_aug": 0, "rest_maxabs_vs_aug": 0.0,
       "iv_src": {n: 0 for n in ("zip_col", "gap", "prod", "next_gap", "default8")},
       "prod_checked": 0, "prod_iv_mismatch": 0, "prod_rate_mismatch": 0, "t5d_checked": 0, "t5d_iv_mismatch": 0,
       "aug_fetchtime_iv_ne_final": 0, "infotime_iv_ne_last": 0, "rest_rows_after_hi_dropped": 0,
       "events_only_in_aug_window_overlap": 0, "events_only_in_rest_window_overlap": 0, "after_last_trade_rows": 0}
examples = {k: [] for k in ("prod_iv_mismatch", "prod_rate_mismatch", "t5d_iv_mismatch", "rate_mismatch", "aug_fetchtime_iv_ne_final", "fallback", "coverage")}
AUG_END = max(int(r[0]) // 1000 for v in (AUG.get("rates") or {}).values() for r in v)
REST_LO = int(REST["meta"]["start_ms"]) // 1000
for j, s in enumerate(SYMS):
    ev = {}
    for zp in sorted(glob.glob(f"{E['AX_FDIR']}/{s}/*.zip")):            # parse VERBATIM pod_panel_ext.py L112-130
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        e = ev.setdefault(ts_ // 1000, {}); e["zip"] = rate; e["ziv"] = iv
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        e = ev.setdefault(int(t_ms) // 1000, {}); e["aug"] = float(rate)
    for r in RR.get(s, []) or []:
        t_s = int(r["fundingTime"]) // 1000
        if t_s > HI: cnt["rest_rows_after_hi_dropped"] += 1; continue
        e = ev.setdefault(t_s, {}); e["rest"] = float(r["fundingRate"]); e["ms"] = int(r["fundingTime"])
        try: e["mark"] = float(r.get("markPrice")) if r.get("markPrice") not in (None, "") else np.nan
        except Exception: e["mark"] = np.nan
    ft = np.array(sorted(t for t in ev if t <= HI), np.int64)
    if not len(ft): continue
    # source-coverage in the overlap window of fund_aug and REST
    for t in ft:
        if REST_LO <= t <= AUG_END:
            e = ev[int(t)]
            if "aug" in e and "rest" not in e: cnt["events_only_in_aug_window_overlap"] += 1; examples["coverage"].append((s, U(t), "aug_only"))
            if "rest" in e and "aug" not in e and "zip" not in e: cnt["events_only_in_rest_window_overlap"] += 1; examples["coverage"].append((s, U(t), "rest_only"))
    dth = np.round(np.diff(ft) / 3600.0); gap = np.full(len(ft), np.nan); gap[1:] = np.where((dth > 0) & (dth <= 24), dth, np.nan)
    lt = LAST_TRADE[s]
    for i, t in enumerate(ft):
        if t < LO: continue
        e = ev[int(t)]
        rate = e["rest"] if "rest" in e else (e["zip"] if "zip" in e else e["aug"])
        bits = (1 if "zip" in e else 0) | (2 if "aug" in e else 0) | (4 if "rest" in e else 0)
        for a, b, key in (("rest", "zip", "rate_mismatch_rest_zip"), ("rest", "aug", "rate_mismatch_rest_aug"), ("zip", "aug", "rate_mismatch_zip_aug")):
            if a in e and b in e and e[a] != e[b]:
                cnt[key] += 1; examples["rate_mismatch"].append((s, U(t), a, e[a], b, e[b]))
        if "rest" in e and "aug" in e: cnt["rest_maxabs_vs_aug"] = max(cnt["rest_maxabs_vs_aug"], abs(e["rest"] - e["aug"]))
        ivg = snap(gap[i]) if np.isfinite(gap[i]) else np.nan
        pl = PLD.get(s, {}).get(int(t))
        if np.isfinite(e.get("ziv", np.nan)): iv, src = float(e["ziv"]), 0
        elif np.isfinite(ivg): iv, src = ivg, 1
        elif pl is not None and pl[1] is not None: iv, src = float(pl[1]), 2
        else: iv, src = 8.0, 4
        nxt = np.nan                                             # diagnostic only (never sets iv)
        if i + 1 < len(ft):
            dn = round((ft[i + 1] - t) / 3600.0)
            if 0 < dn <= 24: nxt = snap(dn)
        if src >= 2: examples["fallback"].append((s, U(t), ["zip_col", "gap", "prod", "next_gap", "default8"][src], iv, "prev_gap_s", int(t - ft[i - 1]) if i > 0 else None, "next_gap_h", nxt))
        cnt["iv_src"][["zip_col", "gap", "prod", "next_gap", "default8"][src]] += 1
        if pl is not None:
            cnt["prod_checked"] += 1
            if pl[1] is not None and float(pl[1]) != iv: cnt["prod_iv_mismatch"] += 1; examples["prod_iv_mismatch"].append((s, U(t), iv, pl[1], src))
            if pl[0] is not None and float(pl[0]) != rate: cnt["prod_rate_mismatch"] += 1; examples["prod_rate_mismatch"].append((s, U(t), rate, pl[0]))
        t5 = T5D.get(s, {}).get(int(t))
        if t5 is not None and t5 is not False:
            cnt["t5d_checked"] += 1
            if float(t5) != iv: cnt["t5d_iv_mismatch"] += 1; examples["t5d_iv_mismatch"].append((s, U(t), iv, t5))
        if "aug" in e and s in AUG_IV and AUG_IV[s] != iv:
            cnt["aug_fetchtime_iv_ne_final"] += 1; examples["aug_fetchtime_iv_ne_final"].append((s, U(t), AUG_IV[s], iv))
        alt = bool(lt is None or t > lt + 86400)
        cnt["after_last_trade_rows"] += int(alt)
        for k, v in (("sym", j), ("ts", int(t)), ("ts_ms", int(e.get("ms", int(t) * 1000))), ("rate", float(rate)), ("mark", float(e.get("mark", np.nan))),
                     ("iv", iv), ("iv_src", src), ("srcbits", bits), ("iv_gap", ivg), ("iv_next_gap", nxt), ("prod_iv", float(pl[1]) if (pl is not None and pl[1] is not None) else np.nan),
                     ("prod_rate", float(pl[0]) if (pl is not None and pl[0] is not None) else np.nan), ("t5d_iv", float(t5) if (t5 is not None and t5 is not False) else np.nan),
                     ("after_last_trade", alt), ("aug_iv_fetchtime", AUG_IV.get(s, np.nan) if "aug" in e else np.nan)):
            cols[k].append(v)
    # fundingInfo at fetch time vs the last settlement's interval (report: fundingInfo shows the NEXT interval around a switch)
    if s in INFO and cols["sym"] and cols["sym"][-1] == j:
        try:
            if float(INFO[s]["fundingIntervalHours"]) != cols["iv"][-1]: cnt["infotime_iv_ne_last"] += 1
        except Exception: pass
    if j % 100 == 0: print(f"[{time.time()-t0:.0f}s] sym {j}", flush=True)
A = {"sym": np.array(cols["sym"], np.int16), "ts": np.array(cols["ts"], np.int64), "ts_ms": np.array(cols["ts_ms"], np.int64),
     "rate": np.array(cols["rate"], np.float64), "mark": np.array(cols["mark"], np.float64), "iv": np.array(cols["iv"], np.float32),
     "iv_src": np.array(cols["iv_src"], np.int8), "srcbits": np.array(cols["srcbits"], np.int8), "iv_gap": np.array(cols["iv_gap"], np.float32),
     "iv_next_gap": np.array(cols["iv_next_gap"], np.float32),
     "prod_iv": np.array(cols["prod_iv"], np.float32), "prod_rate": np.array(cols["prod_rate"], np.float64), "t5d_iv": np.array(cols["t5d_iv"], np.float32),
     "after_last_trade": np.array(cols["after_last_trade"], bool), "aug_iv_fetchtime": np.array(cols["aug_iv_fetchtime"], np.float32),
     "symbols": np.array(SYMS), "iv_src_names": np.array(["zip_col", "gap", "prod", "next_gap", "default8"]),
     "srcbits_legend": np.array("1=zip archive, 2=fund_aug.json.gz, 4=REST fundingRate (this pull)"),
     "last_traded_close_ts": np.array([LAST_TRADE[s] if LAST_TRADE[s] is not None else -1 for s in SYMS], np.int64),
     "window": np.array([LO, HI], np.int64)}
np.savez_compressed(E["AX_OUT_NPZ"], **A)
# ---- 4h accounting table
grid = np.arange(((LO + 14399) // 14400) * 14400, HI + 1, 14400, dtype=np.int64); nG, NW = len(grid), len(SYMS)
now = np.full((nG, NW), np.nan, np.float32); ivn = np.full((nG, NW), np.nan, np.float32)
n4 = np.full((nG, NW), np.nan, np.float32); s4 = np.full((nG, NW), np.nan, np.float64); s4l = np.full((nG, NW), np.nan, np.float64)
complete = (grid + 14400) <= HI
for j in range(NW):
    m = A["sym"] == j
    if not m.any(): continue
    t = A["ts"][m]; r = A["rate"][m]; iv = A["iv"][m]; alt = A["after_last_trade"][m]
    pos = np.searchsorted(t, grid, side="right") - 1; ok = pos >= 0
    stale = ok & ((grid - np.where(ok, t[np.maximum(pos, 0)], 0)) > 12 * 3600)
    use = ok & ~stale
    now[use, j] = r[pos[use]]; ivn[use, j] = iv[pos[use]]
    lo_i = np.searchsorted(t, grid, side="right"); hi_i = np.searchsorted(t, grid + 14400, side="right")
    cr = np.concatenate([[0.0], np.cumsum(r)]); crl = np.concatenate([[0.0], np.cumsum(np.where(alt, 0.0, r))])
    n4[complete, j] = (hi_i - lo_i)[complete]; s4[complete, j] = (cr[hi_i] - cr[lo_i])[complete]; s4l[complete, j] = (crl[hi_i] - crl[lo_i])[complete]
np.savez_compressed(E["AX_OUT_ACC"], ts=grid, symbols=np.array(SYMS), f_fund_now=now, f_fund_iv=ivn, next4h_n=n4, next4h_sum=s4, next4h_sum_live=s4l,
                    definition=np.array("f_fund_now/f_fund_iv: last settlement <= anchor (stale >12h => NaN; pod_panel_ext.py rule), ledger interval; "
                                        "next4h_*: settlements in (A, A+4h] (NaN when A+4h beyond the ledger end); *_live excludes after_last_trade rows"))
n = len(A["ts"])
rep = {"device": "ax04_funding_ledger.py", "self_sha256": sha(os.path.abspath(__file__)), "env": E,
       "inputs_sha256": {k: sha(E[k]) for k in ("AX_REST", "AX_FUND_AUG", "AX_PROD_LEDGER", "AX_T5D_SRC", "AX_CACHE")},
       "window": [U(LO), U(HI)], "n_rows": n, "n_symbols_with_rows": int(len(np.unique(A["sym"]))),
       "first_ts": U(A["ts"].min()), "last_ts": U(A["ts"].max()), "aug_end": U(AUG_END), "rest_lo": U(REST_LO), "counts": cnt,
       "iv_hist": {str(k): int(v) for k, v in zip(*np.unique(A["iv"], return_counts=True))},
       "examples": {k: v[:40] for k, v in examples.items()}, "n_examples": {k: len(v) for k, v in examples.items()},
       "out_npz": E["AX_OUT_NPZ"], "out_npz_sha256": sha(E["AX_OUT_NPZ"]), "out_acc": E["AX_OUT_ACC"], "out_acc_sha256": sha(E["AX_OUT_ACC"]),
       "acc_grid": [U(grid[0]), U(grid[-1]), int(nG)], "wall_s": round(time.time() - t0, 1), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open(E["AX_RECEIPT"], "w"), indent=1, default=str)
print("AX04_DONE", json.dumps({k: rep[k] for k in ("n_rows", "n_symbols_with_rows", "first_ts", "last_ts", "counts", "iv_hist")}, default=str), flush=True)
