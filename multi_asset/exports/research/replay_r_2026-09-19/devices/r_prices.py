#!/usr/bin/env python3
"""r_prices.py — stream R historical PRICE CHAIN for the executor simulator (task brief item 2, "prices").

Source = the research 5m cache dlnative_5m_wide829_f16_holefix2.npz (1d7f459d…; channel ret5 = simple return of the 5-minute bar ending at ts),
streamed out of the npz (never loaded whole; no copy written). The ret5 channel is float16 and HARD-CLIPPED at ±0.300048828125
(memory card cache_ret5_channel_clipped_at_0p30; E-0908-B family), so it is NOT the accounting return on crash bars. RAW restoration rule
(the G0 rule, made bar-level): for every 4h accounting cell (E, E+4h] = the 48 cache rows with ts in (E, E+4h], compare the cache compound
Π(1+r)−1 (NaN bar ⇒ 0) with the accounting meta RAW y4[E] (meta_newprod_v4.npz 0e3c09ac…, the S2 pin, Π(1+r)−1 of UNCLIPPED returns):
  |diff| ≤ 1e-6 or y4 NaN  ⇒ cache kept as is;
  else, PATCH bars = the cell's bound-hitting bars (|ret5| ≥ 0.2999) ∪ its NaN bars; their log-returns are set to equal shares of
       log1p(y4) − Σ log1p(r) over the cell's other bars, so the cell compounds to meta RAW y4 exactly (the path inside the cell before the
       first patched bar is the cache's; the correction sits on the clipped / missing bars, where the cache is known to be wrong);
       a cell with |diff| > 1e-6 and no bound / NaN bar is UNEXPLAINED (counted; any ⇒ RED).
GATE P1 (after patching): max |Π(1+r)−1 − y4| over every cell with finite meta y4 inside the cache ≤ 1e-6 (brief: "verify the 4h compounding
against meta RAW y4 within 1e-6"); plus 0 unexplained cells. RED ⇒ exit 3, the simulator refuses a table without a PASS receipt.
Alignment check first (refuses otherwise): cache ts = bar CLOSE time, established on BTCUSDT against the official 5m kline file (close_t / close_{t−1}).

Absolute level (only lot-size rounding in the executor's plan() depends on it; P&L uses ratios): the close of the official 5m kline opening
2026-08-22 00:00Z (wide_multisrc/klines5m_daily/<SYM>/2026-08-22.zip) placed on its close boundary; the chain runs backwards/forwards from it
through the cache. Symbols with no such file (never listed in late Aug 2026) get level 1.0 at their first finite bar (they are also absent from
the executor's current exchange_info_cache ⇒ no lot rounding, level irrelevant; counted). Sanity (not a gate): chain ratio vs kline ratio
08-22 00:05 → 08-31 00:00 for every kline symbol.

Output (sample boundaries only, float64 log-price table, < 500 MB): every hour boundary, every anchor's A+25m (decision/execution), A+40m (stop
evaluation), A+50m (rule flatten at N+46 → next boundary), and floor_5m(fundingTime) of every settlement in the window.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_prices.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, io
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
ROOT = "/workspace/replay_r_2026-09-19"
CACHE = ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec4")          # sha256 prefix pinned by S2 (A2.3); full sha recorded
META = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
LEDGER = ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e")
KLD = "/workspace/wide_multisrc/klines5m_daily"
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
R0 = ROOT + "/receipts/R0_REPRO.json"
ROW = 300; TOL = 1e-6; BOUND = 0.2999
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST = calendar.timegm((2026, 8, 30, 20, 0, 0))
KREF_OPEN = calendar.timegm((2026, 8, 22, 0, 0, 0)); KCHK_OPEN = calendar.timegm((2026, 8, 30, 23, 55, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


rec = dict(device="r_prices.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = ROOT + "/receipts/R_PRICES.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


r0 = json.load(open(R0)); check("R0_PASS", r0.get("VERDICT") == "PASS", {"R0_sha256": sha(R0)})
for nm, (p, s) in (("cache", CACHE), ("meta", META), ("ledger", LEDGER)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got.startswith(s), {"expected": s[:16], "got": got[:16]})
if FAILS: finish(3, "R_PRICES VERDICT=REFUSED")

# ---------------- stream the ret5 channel out of the cache ----------------
Z = np.load(CACHE[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_is_channel0", CH[0] == "ret5", CH)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)), {"first": int(TS[0]), "last": int(TS[-1]), "n": len(TS)})
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(CACHE[0]); fh = zf.open("data.npy")
ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp, "dtype": str(dt)})
if FAILS: finish(3, "R_PRICES VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2; CHK = 8192
for r0_ in range(0, T, CHK):
    k = min(CHK, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
rec["cache_ret5"] = dict(global_min=float(np.nanmin(R16)), global_max=float(np.nanmax(R16)), n_bound_bars=int((np.abs(R16.astype(np.float32)) >= BOUND).sum()),
                         n_nan=int(np.isnan(R16).sum()))

# ---------------- alignment: ts = bar close time (BTCUSDT vs official kline) ----------------
def kline_closes(sym, day):
    p = f"{KLD}/{sym}/{day}.zip"
    if not os.path.isfile(p): return None
    z = zipfile.ZipFile(p); txt = z.read(z.namelist()[0]).decode().strip().splitlines()
    if txt and txt[0].startswith("open_time"): txt = txt[1:]
    out = {}
    for ln in txt:
        c = ln.split(","); out[int(c[0]) // 1000] = float(c[4])
    return out
kb = kline_closes("BTCUSDT", "2026-08-22"); jb = SY.index("BTCUSDT"); tix = {int(t): i for i, t in enumerate(TS)}
opens = sorted(kb)[1:60]
e_close = [abs(float(R16[tix[o + ROW], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]      # ts = open + 300 = close time
e_open = [abs(float(R16[tix[o], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]
check("align.ts_is_bar_close", max(e_close) < 2e-4 and max(e_open) > max(e_close) * 10, {"max_err_ts_close": max(e_close), "max_err_ts_open": max(e_open)})
if FAILS: finish(3, "R_PRICES VERDICT=REFUSED")

# ---------------- meta RAW y4 cells ----------------
M = np.load(META[0], allow_pickle=True); E = M["E_ts"].astype(np.int64); Y4 = M["y4"]; assert Y4.dtype == np.float32 and Y4.shape == (len(E), NS)
check("meta.strict_4h", bool(np.all(np.diff(E) == 14400)), {"first": int(E[0]), "last": int(E[-1]), "n": len(E)})
ce = np.array([(int(e) in tix) and (int(e) + 14400 in tix) for e in E]); Eidx = np.array([tix[int(e)] for e in E[ce]]); Ecell = np.nonzero(ce)[0]
check("meta.cells_inside_cache", len(Ecell) > 10000 - 200, {"cells_rows": int(len(Ecell)), "first": int(E[Ecell[0]]), "last": int(E[Ecell[-1]])})

# ---------------- sample boundaries ----------------
LZ = np.load(LEDGER[0], allow_pickle=True); ft_all = LZ["ft"].astype(np.int64)
fsel = (ft_all > A_FIRST) & (ft_all <= A_LAST + 14400)
anch = np.arange(A_FIRST, A_LAST + 1, 14400, dtype=np.int64)
H0 = A_FIRST - 14400; H1 = A_LAST + 2 * 14400
S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
S |= set(((ft_all[fsel] // ROW) * ROW).tolist())
BND = np.array(sorted(S), np.int64); brow = np.array([tix[int(b)] for b in BND])        # every sample boundary is a cache row (asserted by the dict lookup)
rec["samples"] = dict(n=len(BND), first=int(BND[0]), last=int(BND[-1]), n_funding_times_window=int(fsel.sum()))
log("samples", len(BND))

# ---------------- per symbol block: log returns, patch, verify, sample ----------------
LP = np.empty((len(BND), NS), np.float64)
first_fin = np.full(NS, -1, np.int64); last_fin = np.full(NS, -1, np.int64); cref = np.zeros(NS); ref_px = np.ones(NS); ref_b = np.full(NS, -1, np.int64); has_k = np.zeros(NS, bool)
PATCH = []; UNEXPL = []; maxdiff_after = 0.0; maxdiff_before_clean = 0.0; n_cells_checked = 0; n_meta_nan_cache_moves = 0
BLK = 48
for j0 in range(0, NS, BLK):
    js = list(range(j0, min(NS, j0 + BLK)))
    r = R16[:, js].astype(np.float64); nanm = np.isnan(r); bnd = np.abs(r) >= BOUND
    Lr = np.log1p(np.where(nanm, 0.0, r))
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])          # C[k] = log price at boundary TS[k-1]; C[i+1] = through row i
    g = C[Eidx + 48 + 1] - C[Eidx + 1]                                      # rows Eidx+1 .. Eidx+48 = ts in (E, E+4h]
    y = Y4[Ecell][:, js].astype(np.float64); fy = np.isfinite(y)
    comp = np.expm1(g); dif = np.abs(comp - y)
    n_meta_nan_cache_moves += int(((~fy) & (np.abs(g) > 0)).sum())
    need = fy & (dif > TOL)
    for a, jj in zip(*np.nonzero(need)):
        i0 = Eidx[a] + 1; rows = np.arange(i0, i0 + 48); jcol = js[jj]
        pb = rows[bnd[rows, jj] | nanm[rows, jj]]
        if len(pb) == 0:
            UNEXPL.append((int(E[Ecell[a]]), SY[jcol], float(comp[a, jj]), float(y[a, jj]))); continue
        other = np.setdiff1d(rows, pb); tgt = np.log1p(y[a, jj]) - Lr[other, jj].sum()
        Lr[pb, jj] = tgt / len(pb)
        PATCH.append((int(E[Ecell[a]]), jcol, len(pb), int(bnd[pb, jj].sum()), int(nanm[pb, jj].sum()), float(comp[a, jj]), float(y[a, jj])))
    clean = fy & ~need
    if clean.any(): maxdiff_before_clean = max(maxdiff_before_clean, float(dif[clean].max()))
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    g2 = C[Eidx + 48 + 1] - C[Eidx + 1]; d2 = np.abs(np.expm1(g2) - y)
    if fy.any(): maxdiff_after = max(maxdiff_after, float(d2[fy].max()))
    n_cells_checked += int(fy.sum())
    LP[:, js] = C[brow + 1]                                                 # log price at each sample boundary (through the row ending there)
    for jj, jcol in enumerate(js):
        fin = np.nonzero(~nanm[:, jj])[0]
        if len(fin): first_fin[jcol] = int(TS[fin[0]]); last_fin[jcol] = int(TS[fin[-1]])
        kl = kline_closes(SY[jcol], "2026-08-22")
        bref = KREF_OPEN + ROW
        if kl is not None and KREF_OPEN in kl and bref in tix:
            has_k[jcol] = True; ref_b[jcol] = bref; ref_px[jcol] = kl[KREF_OPEN]; cref[jcol] = C[tix[bref] + 1, jj]
        elif len(fin):
            ref_b[jcol] = int(TS[fin[0]]); ref_px[jcol] = 1.0; cref[jcol] = C[fin[0] + 1, jj]
    log("block", j0, "patches", len(PATCH), "unexplained", len(UNEXPL))
del R16

rec["patch"] = dict(n_cells_patched=len(PATCH), n_bars_patched=int(sum(p[2] for p in PATCH)), n_with_bound_bars=int(sum(p[3] > 0 for p in PATCH)),
                    n_with_nan_bars_only=int(sum(p[3] == 0 and p[4] > 0 for p in PATCH)), n_anchors=len({p[0] for p in PATCH}),
                    largest=sorted([dict(E=time.strftime("%Y-%m-%dT%HZ", time.gmtime(p[0])), sym=SY[p[1]], cache_compound=p[5], meta_y4=p[6], bars=p[2]) for p in PATCH],
                                   key=lambda d: -abs(d["cache_compound"] - d["meta_y4"]))[:25],
                    n_cells_meta_nan_but_cache_moves=n_meta_nan_cache_moves)
rec["unexplained"] = [dict(E=time.strftime("%Y-%m-%dT%HZ", time.gmtime(u[0])), sym=u[1], cache_compound=u[2], meta_y4=u[3]) for u in UNEXPL[:50]]
check("P1.unexplained_cells_zero", len(UNEXPL) == 0, {"n": len(UNEXPL)})
check("P1.max_abs_diff_after_patch_le_1e-6", maxdiff_after <= TOL, {"max_abs_diff_after": maxdiff_after, "max_abs_diff_unpatched_cells": maxdiff_before_clean, "cells_checked": n_cells_checked})

# ---------------- kline sanity (not a gate) ----------------
bchk = KCHK_OPEN + ROW; devs = {}
brix = {int(b): i for i, b in enumerate(BND)}
for j in np.nonzero(has_k)[0]:
    k2 = kline_closes(SY[j], "2026-08-30")
    if k2 is None or KCHK_OPEN not in k2 or bchk not in brix: continue
    chain = np.exp(LP[brix[bchk], j] - cref[j]); kr = k2[KCHK_OPEN] / ref_px[j]
    devs[SY[j]] = float(chain / kr - 1.0)
dv = np.abs(np.array(list(devs.values()))) if devs else np.array([np.nan])
rec["kline_sanity"] = dict(n=len(devs), median_abs_rel_dev=float(np.median(dv)), p99_abs_rel_dev=float(np.percentile(dv, 99)), max_abs_rel_dev=float(dv.max()),
                           worst=sorted(devs.items(), key=lambda kv: -abs(kv[1]))[:10])
rec["levels"] = dict(n_kline_ref=int(has_k.sum()), n_level_one=int(((~has_k) & (first_fin >= 0)).sum()), n_no_data=int((first_fin < 0).sum()),
                     no_kline_symbols=[SY[j] for j in np.nonzero((~has_k) & (first_fin >= 0))[0]])

# ---------------- write ----------------
os.makedirs(ROOT + "/work", exist_ok=True)
lp_p = ROOT + "/work/price_logtable.npy"; mt_p = ROOT + "/work/price_meta.npz"
np.save(lp_p + ".tmp.npy", LP); os.replace(lp_p + ".tmp.npy", lp_p)
np.savez(mt_p + ".tmp.npz", bounds=BND, symbols=np.array(SY), first_fin=first_fin, last_fin=last_fin, cref=cref, ref_px=ref_px, ref_b=ref_b, has_kline=has_k,
         patches=np.array([(p[0], p[1], p[2], p[3], p[4]) for p in PATCH], np.int64).reshape(-1, 5))
os.replace(mt_p + ".tmp.npz", mt_p)
rec["outputs"] = dict(logtable=dict(path=lp_p, sha256=sha(lp_p), shape=list(LP.shape)), meta=dict(path=mt_p, sha256=sha(mt_p)))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "R_PRICES VERDICT=%s patched_cells=%d unexplained=%d max_abs_diff_after=%.3e kline_median_dev=%.2e" % (
    rec["VERDICT"], len(PATCH), len(UNEXPL), maxdiff_after, rec["kline_sanity"]["median_abs_rel_dev"]))
