#!/usr/bin/env python3
"""r_prices_raw_x0918r.py — the R5-02 restored price chain extended to the x0918r data axis (5m bars to 2026-09-19T00:00Z, last anchor 2026-09-18T20Z).

Derived from r_prices_raw.py (07a3deaf…, commit 0c0fd45a0). Same semantics (cache streaming, bar-close alignment check, absolute level from the
2026-08-22 kline, rp_lib.apply_patch contract: official returns on every ±float16(0.3) bar, NaN stays 0 unless listed as an archive-restorable
hole, UNAVAILABLE refused). Differences, all named:
  cache     stream D's x0918r (08bb2957…); rpx_census.py proved its ret5 prefix == holefix2 (1d7f459d…) bitwise on all 490,753 × 829 cells;
  patch     base patch r_prices_raw_patch.npz (984c2892…, all 953 bars of the old rows + 21,313 gap fills) ∪ extension patch
            r_prices_raw_patch_x0918r_ext.npz (the new-span bars); together they must cover every bound bar of the new cache exactly once;
  samples   the r_prices.py rule with last anchor 2026-09-18T20Z; funding times from the P2 ledger ∪ the stream-D ledger; boundaries past the
            cache's last row (2026-09-19T00:00Z) cannot be priced and are dropped (listed). The old 63,975 bounds ⊂ the new set (asserted);
  P1        vs the x0918 accounting meta (22e990f8…, 10,319 anchors; the x0918r meta is PENDING in stream D's chain) over every cell with finite
            y4 not touched by a gap fill; P1b vs the September meta (0e3c09ac…) on its axis, the base device's gate, rerun;
  P5        PREFIX PROOF: at every one of the 63,975 old boundaries the new log-price row equals price_logtable_raw.npy (0b134159…) bit for bit
            (uint64 view, all 829 columns); the per-symbol reference arrays (first_fin, cref, ref_px, ref_b, has_kline) equal price_meta_raw.npz
            for every symbol that had data in the old cache. Every difference is listed; none is tolerated silently.
  sanity    (not a gate) the old 08-22 -> 08-30 23:55 kline check, plus 08-22 -> 09-18 23:55 against stream D's 09-18 daily archives whose
            sha256 I recompute and compare with the venue checksum stream D recorded (KLINES5M_d0918*.json).
Outputs (new files) under /workspace/raw_price_fix_2026-09-19/ext_x0918r/work/: price_logtable_raw_x0918r.npy, price_meta_raw_x0918r.npz;
receipt receipts/R_PRICES_RAW_X0918R.json. The base table / patch are opened read-only and their sha256 is checked before and after.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_prices_raw_x0918r.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, math
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np
BASE = "/workspace/raw_price_fix_2026-09-19"; OUT = BASE + "/ext_x0918r"
RPLIB = (BASE + "/devices/rp_lib.py", "f802036f1a2e9e9f13f7347c49ecda68b54a38b9b2c6f3167f6ba40295c61488")
sys.path.insert(0, BASE + "/devices")
import rp_lib as RL

T0 = time.time()
CACHE = ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75")
META_X = ("/workspace/axis_0919/meta/meta_newprod_v4_x0918.npz", "22e990f86babd64a30801992627ee2f175e0c920aa442943629f200f16406d1e")
META_S = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
LEDGER_P2 = ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad")
LEDGER_AX = ("/workspace/axis_0919/funding/funding_ledger.npz", "74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d")
BASE_LP = (BASE + "/work/price_logtable_raw.npy", "0b134159a61aa77e33b02696f3702c35e7360862b30ed9b356731017fcad0157")
BASE_PM = (BASE + "/work/price_meta_raw.npz", "c27fdb11af42f374")                       # prefix; the full sha is in R_PRICES_RAW.json and re-checked
BASE_PATCH = (BASE + "/r_prices_raw_patch.npz", "984c28923838501758fe52d1ea7d0cd92fc7fc26c4869058b112bb43670343b2")
EXT_PATCH = OUT + "/r_prices_raw_patch_x0918r_ext.npz"
KLD = "/workspace/wide_multisrc/klines5m_daily"; KLD_NEW = "/workspace/axis_0919/dl/klines5m"
KLD_NEW_RECEIPTS = ["/workspace/axis_0919/receipts/KLINES5M_d0918.json", "/workspace/axis_0919/receipts/KLINES5M_d0918_retry1.json"]
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
R0 = "/workspace/replay_r_2026-09-19/receipts/R0_REPRO.json"
ROW = 300; CELL = 14400; TOL = 1e-6
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST_OLD = calendar.timegm((2026, 8, 30, 20, 0, 0)); A_LAST = calendar.timegm((2026, 9, 18, 20, 0, 0))
KREF_OPEN = calendar.timegm((2026, 8, 22, 0, 0, 0)); KCHK_OPEN = calendar.timegm((2026, 8, 30, 23, 55, 0)); KCHK2_OPEN = calendar.timegm((2026, 9, 18, 23, 55, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = dict(device="r_prices_raw_x0918r.py", self_sha256=sha(os.path.abspath(__file__)), rp_lib=dict(path=RPLIB[0], sha256=sha(RPLIB[0])),
           derived_from=dict(path="raw_price_fix_2026-09-19/devices/r_prices_raw.py", sha256="07a3deaf2659b4c1…", commit="0c0fd45a0"),
           argv=sys.argv, env=dict(os.environ), numpy=np.__version__, utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = OUT + "/receipts/R_PRICES_RAW_X0918R.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


check("rp_lib.sha", rec["rp_lib"]["sha256"] == RPLIB[1])
r0 = json.load(open(R0)); check("R0_PASS", r0.get("VERDICT") == "PASS")
RB = json.load(open(BASE + "/receipts/R_PRICES_RAW.json")); check("base_table_receipt_PASS", RB.get("VERDICT") == "PASS" and RB["outputs"]["logtable"]["sha256"] == BASE_LP[1])
BASE_PM = (BASE_PM[0], RB["outputs"]["meta"]["sha256"]); check("base_meta_sha_prefix", BASE_PM[1].startswith("c27fdb11af42f374"))
for nm, (p, s) in (("cache_x0918r", CACHE), ("meta_x0918", META_X), ("meta_september", META_S), ("ledger_p2", LEDGER_P2), ("ledger_axis", LEDGER_AX),
                   ("base_logtable", BASE_LP), ("base_price_meta", BASE_PM), ("base_patch", BASE_PATCH)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
RBR = json.load(open(BASE + "/receipts/RP_RESTORE.json")); RXR = json.load(open(OUT + "/receipts/RPX_RESTORE.json"))
check("base_restore_PASS_and_patch_sha", RBR.get("VERDICT") == "PASS" and RBR["outputs"]["patch"]["sha256"] == BASE_PATCH[1])
xsha = sha(EXT_PATCH); rec["inputs"]["ext_patch"] = dict(path=EXT_PATCH, sha256=xsha)
check("ext_restore_PASS_and_patch_sha", RXR.get("VERDICT") == "PASS" and RXR["outputs"]["patch"]["sha256"] == xsha, {"ext_patch": xsha[:16]})
RXC = json.load(open(OUT + "/receipts/RPX_CENSUS.json")); check("ext_census_PASS", RXC.get("VERDICT") == "PASS")
rec["meta_used_for_P1"] = "x0918 (22e990f8…); the x0918r accounting meta is PENDING in stream D's chain (docs/RESULT_data_axis_0919_2026-09-19.md §11.7)"
if FAILS: finish(3, "R_PRICES_RAW_X0918R VERDICT=REFUSED")

# ---------------- stream the ret5 channel ----------------
Z = np.load(CACHE[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_is_channel0", CH[0] == "ret5", CH)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)), {"first": iso(TS[0]), "last": iso(TS[-1]), "n": len(TS)})
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(CACHE[0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp})
if FAILS: finish(3, "R_PRICES_RAW_X0918R VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2
for r0_ in range(0, T, 8192):
    k = min(8192, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
rec["cache_ret5"] = dict(n_bound_bars=int(RL.is_bound(R16).sum()), n_nan=int(np.isnan(R16).sum()))

# ---------------- alignment: ts = bar close time (BTCUSDT vs official kline), as r_prices.py ----------------
def kline_closes(p):
    if not os.path.isfile(p): return None
    z = zipfile.ZipFile(p); txt = z.read(z.namelist()[0]).decode().strip().splitlines()
    if txt and txt[0].startswith("open_time"): txt = txt[1:]
    out = {}
    for ln in txt:
        c = ln.split(","); out[int(c[0]) // 1000] = float(c[4])
    return out
kb = kline_closes(f"{KLD}/BTCUSDT/2026-08-22.zip"); jb = SY.index("BTCUSDT"); tix = {int(t): i for i, t in enumerate(TS)}
opens = sorted(kb)[1:60]
e_close = [abs(float(R16[tix[o + ROW], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]
e_open = [abs(float(R16[tix[o], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]
check("align.ts_is_bar_close", max(e_close) < 2e-4 and max(e_open) > max(e_close) * 10, {"max_err_ts_close": max(e_close), "max_err_ts_open": max(e_open)})

# ---------------- sample boundaries ----------------
LZ = np.load(LEDGER_P2[0], allow_pickle=True); ft_p2 = LZ["ft"].astype(np.int64)
LA = np.load(LEDGER_AX[0], allow_pickle=True); ft_ax = LA["ts"].astype(np.int64)
def bounds(a_last, fts, cap):
    anch = np.arange(A_FIRST, a_last + 1, CELL, dtype=np.int64); H0 = A_FIRST - CELL; H1 = a_last + 2 * CELL
    S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
    for ft in fts:
        sel = (ft > A_FIRST) & (ft <= a_last + CELL); S |= set(((ft[sel] // ROW) * ROW).tolist())
    allb = np.array(sorted(S), np.int64)
    return allb[allb <= cap], allb[allb > cap]
BND, dropped = bounds(A_LAST, [ft_p2, ft_ax], int(TS[-1]))
CZ = np.load(RXC["outputs"]["census"]["path"], allow_pickle=True)
check("samples.equal_census", bool(np.array_equal(BND, CZ["bounds_new"].astype(np.int64))), {"n": len(BND)})
PMO = np.load(BASE_PM[0], allow_pickle=True); BND_OLD = PMO["bounds"].astype(np.int64)
brix = {int(b): i for i, b in enumerate(BND)}
check("samples.old_subset", all(int(b) in brix for b in BND_OLD), {"n_old": len(BND_OLD)})
brow = np.array([tix[int(b)] for b in BND])
rec["samples"] = dict(n=len(BND), n_old=len(BND_OLD), added=len(BND) - len(BND_OLD), first=iso(BND[0]), last=iso(BND[-1]), dropped_past_cache_end=[iso(t) for t in dropped])

# ---------------- meta y4 cells ----------------
def meta_cells(path):
    M = np.load(path, allow_pickle=True); E = M["E_ts"].astype(np.int64); Y4 = M["y4"]; assert Y4.dtype == np.float32 and Y4.shape == (len(E), NS)
    ce = np.array([(int(e) in tix) and (int(e) + CELL in tix) for e in E]); return E, Y4, np.array([tix[int(e)] for e in E[ce]]), np.nonzero(ce)[0]
EX, YX, EidxX, EcellX = meta_cells(META_X[0]); ES, YS, EidxS, EcellS = meta_cells(META_S[0])
check("meta_x0918.cells_inside_cache", len(EcellX) == len(EX), {"n": len(EX), "first": iso(EX[0]), "last": iso(EX[-1])})
check("meta_september.cells_inside_cache", len(EcellS) == len(ES), {"n": len(ES)})

# ---------------- the combined patch ----------------
PB = np.load(BASE_PATCH[0], allow_pickle=True); PX = np.load(EXT_PATCH, allow_pickle=True)
check("patch.symbols", [str(s) for s in PB["symbols"]] == SY and [str(s) for s in PX["symbols"]] == SY)
check("ext_patch.base_sha_bound", str(PX["base_patch_sha256"]) == BASE_PATCH[1])
prow = np.concatenate([PB["row"], PX["row"]]).astype(np.int64); pcol = np.concatenate([PB["col"], PX["col"]]).astype(np.int64)
pts = np.concatenate([PB["ts"], PX["ts"]]).astype(np.int64); pst = np.concatenate([PB["status"], PX["status"]]).astype(np.int64); praw = np.concatenate([PB["raw"], PX["raw"]]).astype(np.float64)
check("patch.rows_on_axis", bool(np.array_equal(TS[prow], pts)))
check("patch.covers_every_bound_bar_once", len(prow) == rec["cache_ret5"]["n_bound_bars"] and len(set(zip(prow.tolist(), pcol.tolist()))) == len(prow),
      {"patch": len(prow), "cache": rec["cache_ret5"]["n_bound_bars"], "base": len(PB["row"]), "ext": len(PX["row"])})
S_LO, S_HI = int(BND[0]), int(BND[-1]); inr = (pts > S_LO) & (pts <= S_HI); okst = np.isin(pst, [RL.RESTORED, RL.NOT_CLIPPED])
check("P3.no_unavailable_bound_bar_in_range", int((inr & ~okst).sum()) == 0, {"n": int((inr & ~okst).sum())})
out_unavail = (~inr) & ~okst; pst[out_unavail] = RL.NOT_CLIPPED
grow = np.concatenate([PB["gap_row"], PX["gap_row"]]).astype(np.int64); gcol = np.concatenate([PB["gap_col"], PX["gap_col"]]).astype(np.int64)
graw = np.concatenate([PB["gap_raw"], PX["gap_raw"]]).astype(np.float64)
check("patch.gap_entries_on_nan_bars", bool(np.all(np.isnan(R16[grow, gcol].astype(np.float32)))), {"n": len(grow)})
rec["patch_use"] = dict(bars=len(prow), base=len(PB["row"]), ext=len(PX["row"]), in_range=int(inr.sum()), restored_in_range=int((inr & (pst == RL.RESTORED)).sum()),
                        not_clipped_in_range=int((inr & (pst == RL.NOT_CLIPPED)).sum()), gap_filled_bars=len(grow), unavailable_out_of_range_left_cached=int(out_unavail.sum()))
if FAILS: finish(3, "R_PRICES_RAW_X0918R VERDICT=REFUSED")

# ---------------- per symbol block ----------------
LP = np.empty((len(BND), NS), np.float64)
first_fin = np.full(NS, -1, np.int64); last_fin = np.full(NS, -1, np.int64); cref = np.zeros(NS); ref_px = np.ones(NS); ref_b = np.full(NS, -1, np.int64); has_k = np.zeros(NS, bool)
P1 = {"x0918": dict(maxd=0.0, bad=[], n=0, gapx=0), "september": dict(maxd=0.0, bad=[], n=0, gapx=0)}; n_applied = 0
for j0 in range(0, NS, 48):
    js = list(range(j0, min(NS, j0 + 48)))
    r = R16[:, js].astype(np.float64); nanm = np.isnan(r); Lr = RL.base_logs(r)
    sel = np.nonzero((pcol >= j0) & (pcol < j0 + len(js)))[0]
    n_applied += RL.apply_patch(Lr, r, prow[sel], pcol[sel] - j0, pst[sel], praw[sel])
    gsel = np.nonzero((gcol >= j0) & (gcol < j0 + len(js)))[0]; gmask = np.zeros_like(nanm)
    if len(gsel): Lr[grow[gsel], gcol[gsel] - j0] = np.log1p(graw[gsel]); gmask[grow[gsel], gcol[gsel] - j0] = True
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    Gm = np.vstack([np.zeros((1, len(js)), np.int64), np.cumsum(gmask, axis=0)])
    for nm, (E_, Y_, Eidx_, Ecell_) in (("x0918", (EX, YX, EidxX, EcellX)), ("september", (ES, YS, EidxS, EcellS))):
        g2 = C[Eidx_ + 48 + 1] - C[Eidx_ + 1]; y = Y_[Ecell_][:, js].astype(np.float64); fy = np.isfinite(y)
        gcell = (Gm[Eidx_ + 48 + 1] - Gm[Eidx_ + 1]) > 0; d2 = np.abs(np.expm1(g2) - y); chk = fy & ~gcell
        P1[nm]["gapx"] += int((fy & gcell).sum()); P1[nm]["n"] += int(chk.sum())
        if chk.any(): P1[nm]["maxd"] = max(P1[nm]["maxd"], float(d2[chk].max()))
        for a, jj in zip(*np.nonzero(chk & (d2 > TOL))): P1[nm]["bad"].append((iso(E_[Ecell_[a]]), SY[js[jj]], float(np.expm1(g2[a, jj])), float(y[a, jj])))
    del Gm
    LP[:, js] = C[brow + 1]
    for jj, jcol in enumerate(js):
        fin = np.nonzero(~nanm[:, jj])[0]
        if len(fin): first_fin[jcol] = int(TS[fin[0]]); last_fin[jcol] = int(TS[fin[-1]])
        kl = kline_closes(f"{KLD}/{SY[jcol]}/2026-08-22.zip"); bref = KREF_OPEN + ROW
        if kl is not None and KREF_OPEN in kl and bref in tix:
            has_k[jcol] = True; ref_b[jcol] = bref; ref_px[jcol] = kl[KREF_OPEN]; cref[jcol] = C[tix[bref] + 1, jj]
        elif len(fin):
            ref_b[jcol] = int(TS[fin[0]]); ref_px[jcol] = 1.0; cref[jcol] = C[fin[0] + 1, jj]
    if j0 % 192 == 0: log("block", j0, "applied", n_applied)
del R16
rec["P1"] = {nm: dict(cells_checked=v["n"], cells_excluded_gapfilled=v["gapx"], max_abs_diff=v["maxd"], n_over_tol=len(v["bad"]), over_tol=v["bad"][:50]) for nm, v in P1.items()}
check("P1.x0918_meta_max_abs_diff_le_1e-6", P1["x0918"]["n"] > 3_000_000 and P1["x0918"]["maxd"] <= TOL and not P1["x0918"]["bad"], rec["P1"]["x0918"])
check("P1b.september_meta_max_abs_diff_le_1e-6", P1["september"]["n"] > 3_000_000 and P1["september"]["maxd"] <= TOL and not P1["september"]["bad"], rec["P1"]["september"])
check("P3.apply_patch_contract", n_applied == int((pst == RL.RESTORED).sum()), {"applied": n_applied})

# ---------------- P5: prefix proof against the base table ----------------
LPO = np.load(BASE_LP[0], mmap_mode="r"); assert LPO.shape == (len(BND_OLD), NS)
orow = np.array([brix[int(b)] for b in BND_OLD]); diffs = []; n_cells = 0
for k0 in range(0, len(BND_OLD), 4096):
    a = np.ascontiguousarray(LP[orow[k0:k0 + 4096]]).view(np.uint64); b = np.ascontiguousarray(LPO[k0:k0 + 4096]).view(np.uint64); n_cells += a.size
    for i, j in np.argwhere(a != b)[:max(0, 200 - len(diffs))]: diffs.append(dict(boundary=iso(BND_OLD[k0 + i]), sym=SY[j], new=float(LP[orow[k0 + i], j]), old=float(LPO[k0 + i, j])))
    if (a != b).any() and len(diffs) >= 200: diffs.append("... truncated")
ndiff = sum(1 for d in diffs if isinstance(d, dict))
had = PMO["first_fin"].astype(np.int64) >= 0
ref_eq = {k: bool(np.array_equal(np.asarray(v_new)[had], PMO[k][had])) for k, v_new in (("first_fin", first_fin), ("cref", cref), ("ref_px", ref_px), ("ref_b", ref_b), ("has_kline", has_k))}
new_sym = [dict(sym=SY[j], first_finite=iso(first_fin[j]), level_ref=("kline 2026-08-22" if has_k[j] else "1.0 at first finite bar")) for j in np.nonzero((~had) & (first_fin >= 0))[0]]
rec["P5_prefix"] = dict(old_boundaries=len(BND_OLD), cells_compared=int(n_cells), bit_differences=ndiff, differences=diffs[:201], reference_arrays_equal_for_old_symbols=ref_eq,
                        symbols_first_seen_in_new_span=new_sym, last_fin_changed=int((last_fin != PMO["last_fin"]).sum()),
                        note="last_fin moves by construction (the cache is longer); it is not read by the replay's HistPanel")
check("P5.prefix_bitwise_equal_to_base_table", ndiff == 0 and n_cells == len(BND_OLD) * NS, {"cells": n_cells, "bit_differences": ndiff})
check("P5.reference_arrays_equal_for_old_symbols", all(ref_eq.values()), ref_eq)
del LPO

# ---------------- kline sanity (not a gate) ----------------
def chain_vs(open_t, closes_of):
    devs = {}
    if open_t + ROW not in brix: return devs
    for j in np.nonzero(has_k)[0]:
        k2 = closes_of(SY[j])
        if k2 is None or open_t not in k2: continue
        devs[SY[j]] = float(np.exp(LP[brix[open_t + ROW], j] - cref[j]) / (k2[open_t] / ref_px[j]) - 1.0)
    return devs
def summ(devs):
    dv = np.abs(np.array(list(devs.values()))) if devs else np.array([np.nan])
    return dict(n=len(devs), median_abs_rel_dev=float(np.median(dv)), p99_abs_rel_dev=float(np.percentile(dv, 99)), max_abs_rel_dev=float(np.nanmax(dv)),
                worst=sorted(devs.items(), key=lambda kv: -abs(kv[1]))[:10])
rec["kline_sanity_0830"] = summ(chain_vs(KCHK_OPEN, lambda s: kline_closes(f"{KLD}/{s}/2026-08-30.zip")))
vsha = {}
for rp_ in KLD_NEW_RECEIPTS:
    for m in json.load(open(rp_))["manifest"]:
        if m.get("status") == "OK" and m.get("checksum_sha256"): vsha[m["sym"]] = m["checksum_sha256"]
nver = 0; nfail = []
def closes_0918(s):
    global nver
    p = f"{KLD_NEW}/{s}/2026-09-18.zip"
    if s not in vsha or not os.path.isfile(p): return None
    if sha(p) != vsha[s]: nfail.append(s); return None
    nver += 1; return kline_closes(p)
rec["kline_sanity_0918"] = summ(chain_vs(KCHK2_OPEN, closes_0918))
rec["kline_sanity_0918"].update(archives_sha_matched_stream_D_venue_checksum=nver, sha_mismatch=nfail, source=KLD_NEW, checksum_source=KLD_NEW_RECEIPTS)
rec["levels"] = dict(n_kline_ref=int(has_k.sum()), n_level_one=int(((~has_k) & (first_fin >= 0)).sum()), n_no_data=int((first_fin < 0).sum()))

# ---------------- write (only when every gate passed) ----------------
if FAILS: finish(3, "R_PRICES_RAW_X0918R VERDICT=RED (table not written)")
lp_p = OUT + "/work/price_logtable_raw_x0918r.npy"; mt_p = OUT + "/work/price_meta_raw_x0918r.npz"
np.save(lp_p + ".tmp.npy", LP); os.replace(lp_p + ".tmp.npy", lp_p)
np.savez(mt_p + ".tmp.npz", bounds=BND, symbols=np.array(SY), first_fin=first_fin, last_fin=last_fin, cref=cref, ref_px=ref_px, ref_b=ref_b, has_kline=has_k,
         raw_patch_bars=np.stack([np.concatenate([PB["E"], PX["E"]]), pcol, prow, pst, np.concatenate([PB["status"], PX["status"]]).astype(np.int64)], 1).astype(np.int64),
         patch_sha256=np.array([BASE_PATCH[1], xsha]), cache_sha256=np.array(CACHE[1]))
os.replace(mt_p + ".tmp.npz", mt_p)
for nm, (p, s) in (("base_logtable", BASE_LP), ("base_price_meta", BASE_PM), ("base_patch", BASE_PATCH)):
    check(f"base_unchanged_after.{nm}", sha(p) == s)
rec["outputs"] = dict(logtable=dict(path=lp_p, sha256=sha(lp_p), shape=list(LP.shape)), meta=dict(path=mt_p, sha256=sha(mt_p)))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "R_PRICES_RAW_X0918R VERDICT=%s rows=%d prefix_bitdiff=%d P1_x0918=%.3e P1b_sept=%.3e replaced=%d kline0918_median=%.2e" % (
    rec["VERDICT"], len(BND), ndiff, P1["x0918"]["maxd"], P1["september"]["maxd"], n_applied, rec["kline_sanity_0918"]["median_abs_rel_dev"]))
