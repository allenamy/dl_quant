#!/usr/bin/env python3
"""r_prices_raw.py — stream R historical PRICE CHAIN with the R5-02 fix: the clipped bars carry their OFFICIAL 5m returns.

Derived from replay_r_2026-09-19/devices/r_prices.py (sha 3614558d...). Everything is the same (cache streaming, bar-close alignment check,
sample boundaries, absolute level from the 2026-08-22 kline, kline sanity) EXCEPT the restoration step (old L128-150):
  OLD  a cell (E, E+4h] whose cache compound differs from meta RAW y4 had ALL its bound / NaN bars set to one equal log return so the cell
       compounds to y4. Endpoint exact, intermediate path invented (review R5-02: a +80% / -75% pair became two -32.9% bars); cells whose
       meta y4 is NaN kept their clipped bars.
  NEW  every cache bar at +-float16(0.3) takes its entry in r_prices_raw_patch.npz (rp_restore.py; official closes from checksum-verified
       data.binance.vision archives) through rp_lib.apply_patch: RESTORED => log1p(exact official return); NOT_CLIPPED => cache value kept;
       a bound bar inside the sampled range without an exact official value => REFUSED (scenario "exact"), or, only when explicitly asked
       (argv[2] = lo | hi), the lowest / highest admissible path of rp_lib.extreme_paths for that cell (refused if that side is unbounded).
       NaN bars stay 0 (the accounting meta's convention) unless the patch lists them as an archive-restorable cache hole (gap_* arrays).
GATE P1 (unchanged tolerance): max |prod(1+r)-1 - y4| <= 1e-6 over every cell with finite meta y4 that contains no gap-filled bar, and no
cell above it. New gates: P2 the patch receipt RP_RESTORE is PASS and its sha matches; P3 apply_patch contract (entries only on bound bars,
every bound bar covered); P4 the new table differs from the old one in within-cell paths ONLY inside cells that hold a patched bar.
Diff vs the old table (report): absolute price level and within-cell path change at every sample boundary (A+25m / A+40m / A+50m / other).
Outputs under /workspace/raw_price_fix_2026-09-19/work/: price_logtable_raw.npy (same shape/semantics as the old price_logtable.npy),
price_meta_raw.npz (same keys as the old price_meta.npz + the patch record), price_diff_vs_old.npz; receipt receipts/R_PRICES_RAW.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_prices_raw.py PATH,HOME,LC_CTYPE [exact|lo|hi]
"""
import os, sys, json, time, hashlib, zipfile, calendar, math
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
SCEN = sys.argv[2] if len(sys.argv) > 2 else "exact"; assert SCEN in ("exact", "lo", "hi"), SCEN
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rp_lib as RL

T0 = time.time()
ROOT_R = "/workspace/replay_r_2026-09-19"                                         # read only
OUT = "/workspace/raw_price_fix_2026-09-19"
CACHE = ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488")
META = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
LEDGER = ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad")
OLD_PMETA = (ROOT_R + "/work/price_meta.npz", "fc6a381a76e311e69ad3d7d1c79c834c8f2417c5d46c792d06101cfd376a6455")
OLD_LP = (ROOT_R + "/work/price_logtable.npy", "3b588cb058920d57621b3e269a9a4a0f640f4f23ea44fd413bf7abeefd774211")
PATCH = OUT + "/r_prices_raw_patch.npz"; RESTORE_RECEIPT = OUT + "/receipts/RP_RESTORE.json"
KLD = "/workspace/wide_multisrc/klines5m_daily"
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
R0 = ROOT_R + "/receipts/R0_REPRO.json"
ROW = 300; TOL = 1e-6; BOUND = 0.2999
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST = calendar.timegm((2026, 8, 30, 20, 0, 0))
KREF_OPEN = calendar.timegm((2026, 8, 22, 0, 0, 0)); KCHK_OPEN = calendar.timegm((2026, 8, 30, 23, 55, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = dict(device="r_prices_raw.py", self_sha256=sha(os.path.abspath(__file__)), rp_lib_sha256=sha(os.path.join(HERE, "rp_lib.py")), scenario=SCEN,
           derived_from=dict(path="replay_r_2026-09-19/devices/r_prices.py", sha256="3614558d6eb58200f1d15f51c3fb72ca7aa18da3a73b04fc4544c8edbfc899dc"),
           argv=sys.argv, env=dict(os.environ), numpy=np.__version__, utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = OUT + "/receipts/R_PRICES_RAW%s.json" % ("" if SCEN == "exact" else "_" + SCEN)
    json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


r0 = json.load(open(R0)); check("R0_PASS", r0.get("VERDICT") == "PASS", {"R0_sha256": sha(R0)})
for nm, (p, s) in (("cache", CACHE), ("meta", META), ("ledger", LEDGER), ("old_price_meta", OLD_PMETA), ("old_price_logtable", OLD_LP)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
RR = json.load(open(RESTORE_RECEIPT)); psha = sha(PATCH); rec["inputs"]["patch"] = dict(path=PATCH, sha256=psha, restore_receipt_sha256=sha(RESTORE_RECEIPT))
check("P2.restore_receipt_PASS", RR.get("VERDICT") == "PASS")
check("P2.patch_sha_matches_restore_receipt", psha == RR["outputs"]["patch"]["sha256"], {"patch": psha[:16], "receipt": RR["outputs"]["patch"]["sha256"][:16]})
if FAILS: finish(3, "R_PRICES_RAW VERDICT=REFUSED")

# ---------------- stream the ret5 channel out of the cache (as r_prices.py) ----------------
Z = np.load(CACHE[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_is_channel0", CH[0] == "ret5", CH)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)), {"first": int(TS[0]), "last": int(TS[-1]), "n": len(TS)})
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(CACHE[0]); fh = zf.open("data.npy")
ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp, "dtype": str(dt)})
if FAILS: finish(3, "R_PRICES_RAW VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2; CHK = 8192
for r0_ in range(0, T, CHK):
    k = min(CHK, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
rec["cache_ret5"] = dict(n_bound_bars=int((np.abs(R16.astype(np.float32)) >= BOUND).sum()), n_nan=int(np.isnan(R16).sum()))

# ---------------- alignment: ts = bar close time (BTCUSDT vs official kline), as r_prices.py ----------------
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
e_close = [abs(float(R16[tix[o + ROW], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]
e_open = [abs(float(R16[tix[o], jb]) - (kb[o] / kb[o - ROW] - 1.0)) for o in opens]
check("align.ts_is_bar_close", max(e_close) < 2e-4 and max(e_open) > max(e_close) * 10, {"max_err_ts_close": max(e_close), "max_err_ts_open": max(e_open)})
if FAILS: finish(3, "R_PRICES_RAW VERDICT=REFUSED")

# ---------------- meta RAW y4 cells ----------------
M = np.load(META[0], allow_pickle=True); E = M["E_ts"].astype(np.int64); Y4 = M["y4"]; assert Y4.dtype == np.float32 and Y4.shape == (len(E), NS)
check("meta.strict_4h", bool(np.all(np.diff(E) == 14400)))
ce = np.array([(int(e) in tix) and (int(e) + 14400 in tix) for e in E]); Eidx = np.array([tix[int(e)] for e in E[ce]]); Ecell = np.nonzero(ce)[0]
check("meta.cells_inside_cache", len(Ecell) > 10000 - 200, {"cells_rows": int(len(Ecell))})

# ---------------- sample boundaries (identical to r_prices.py; asserted equal to the old table's) ----------------
LZ = np.load(LEDGER[0], allow_pickle=True); ft_all = LZ["ft"].astype(np.int64)
fsel = (ft_all > A_FIRST) & (ft_all <= A_LAST + 14400)
anch = np.arange(A_FIRST, A_LAST + 1, 14400, dtype=np.int64)
H0 = A_FIRST - 14400; H1 = A_LAST + 2 * 14400
S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
S |= set(((ft_all[fsel] // ROW) * ROW).tolist())
BND = np.array(sorted(S), np.int64); brow = np.array([tix[int(b)] for b in BND])
PMO = np.load(OLD_PMETA[0], allow_pickle=True); check("samples.equal_old_table", bool(np.array_equal(BND, PMO["bounds"].astype(np.int64))), {"n": len(BND)})
S_LO, S_HI = int(BND[0]), int(BND[-1]); rec["samples"] = dict(n=len(BND), first=iso(S_LO), last=iso(S_HI))

# ---------------- the patch ----------------
P = np.load(PATCH, allow_pickle=True)
check("patch.symbols", [str(s) for s in P["symbols"]] == SY)
prow = P["row"].astype(np.int64); pcol = P["col"].astype(np.int64); pts = P["ts"].astype(np.int64); pst = P["status"].astype(np.int64).copy(); praw = P["raw"].astype(np.float64)
check("patch.rows_on_axis", bool(np.array_equal(TS[prow], pts)))
check("patch.covers_every_bound_bar", len(prow) == rec["cache_ret5"]["n_bound_bars"], {"patch": len(prow), "cache": rec["cache_ret5"]["n_bound_bars"]})
inr = (pts > S_LO) & (pts <= S_HI)
okst = np.isin(pst, [RL.RESTORED, RL.NOT_CLIPPED])
out_unavail = (~inr) & ~okst; pst[out_unavail] = RL.NOT_CLIPPED            # outside the sampled range they move no sampled price: left as cached
rec["patch_use"] = dict(bars=len(prow), in_range=int(inr.sum()), restored_in_range=int((inr & (pst == RL.RESTORED)).sum()),
                        not_clipped_in_range=int((inr & (pst == RL.NOT_CLIPPED)).sum()), unavailable_in_range=int((inr & ~okst).sum()),
                        unavailable_out_of_range_left_cached=int(out_unavail.sum()))
scen_over = []                                                              # (row, col, log increment) set for a lo / hi scenario
bad_in = np.nonzero(inr & ~okst)[0]
if len(bad_in):
    if SCEN == "exact":
        rec["unavailable_in_range"] = [dict(sym=SY[pcol[k]], ts=iso(pts[k]), status=RL.STATUS_NAME[int(pst[k])]) for k in bad_in]
        check("P3.no_unavailable_bound_bar_in_range_exact", False, {"n": len(bad_in)})
        finish(3, "R_PRICES_RAW VERDICT=REFUSED (UNAVAILABLE bound bars in the sampled range; run a lo / hi scenario explicitly)")
    cix = {(int(e), int(c)): i for i, (e, c) in enumerate(zip(P["cell_E"], P["cell_col"]))}
    for k in bad_in:
        ci = cix[(int(P["E"][k]), int(pcol[k]))]; path = (P["cell_logpath_lo"] if SCEN == "lo" else P["cell_logpath_hi"])[ci]
        inc = float(path[int(P["pos"][k])] - path[int(P["pos"][k]) - 1])
        if not math.isfinite(inc):
            check(f"scenario.{SCEN}.bounded", False, {"sym": SY[pcol[k]], "ts": iso(pts[k])})
            finish(3, "R_PRICES_RAW VERDICT=REFUSED (scenario %s unbounded at %s %s)" % (SCEN, SY[pcol[k]], iso(pts[k])))
        scen_over.append((int(prow[k]), int(pcol[k]), inc)); pst[k] = RL.NOT_CLIPPED     # placeholder so apply_patch covers it; overwritten below
grow = P["gap_row"].astype(np.int64); gcol = P["gap_col"].astype(np.int64); graw = P["gap_raw"].astype(np.float64)
check("patch.gap_entries_on_nan_bars", bool(np.all(np.isnan(R16[grow, gcol].astype(np.float32)))) if len(grow) else True, {"n": len(grow)})
rec["patch_use"]["gap_filled_bars"] = len(grow)

# ---------------- per symbol block: log returns, patch, verify, sample ----------------
LP = np.empty((len(BND), NS), np.float64)
first_fin = np.full(NS, -1, np.int64); last_fin = np.full(NS, -1, np.int64); cref = np.zeros(NS); ref_px = np.ones(NS); ref_b = np.full(NS, -1, np.int64); has_k = np.zeros(NS, bool)
BAD = []; maxdiff_after = 0.0; n_cells_checked = 0; n_cells_gapfilled = 0; n_applied = 0; n_cells_changed = 0
BLK = 48
for j0 in range(0, NS, BLK):
    js = list(range(j0, min(NS, j0 + BLK)))
    r = R16[:, js].astype(np.float64); nanm = np.isnan(r)
    Lr = RL.base_logs(r)
    sel = np.nonzero((pcol >= j0) & (pcol < j0 + len(js)))[0]
    n_applied += RL.apply_patch(Lr, r, prow[sel], pcol[sel] - j0, pst[sel], praw[sel])
    for (rw, cl_, inc) in scen_over:
        if j0 <= cl_ < j0 + len(js): Lr[rw, cl_ - j0] = inc
    gsel = np.nonzero((gcol >= j0) & (gcol < j0 + len(js)))[0]
    gmask = np.zeros_like(nanm)
    if len(gsel):
        Lr[grow[gsel], gcol[gsel] - j0] = np.log1p(graw[gsel]); gmask[grow[gsel], gcol[gsel] - j0] = True
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    g2 = C[Eidx + 48 + 1] - C[Eidx + 1]; y = Y4[Ecell][:, js].astype(np.float64); fy = np.isfinite(y)
    Cb = np.vstack([np.zeros((1, len(js))), np.cumsum(RL.base_logs(r), axis=0)]); gb = Cb[Eidx + 48 + 1] - Cb[Eidx + 1]; del Cb
    n_cells_changed += int((np.abs(g2 - gb) > 0).sum())
    Gm = np.vstack([np.zeros((1, len(js)), np.int64), np.cumsum(gmask, axis=0)]); gcell = (Gm[Eidx + 48 + 1] - Gm[Eidx + 1]) > 0; del Gm
    d2 = np.abs(np.expm1(g2) - y); chk = fy & ~gcell
    n_cells_gapfilled += int((fy & gcell).sum())
    if chk.any(): maxdiff_after = max(maxdiff_after, float(d2[chk].max()))
    for a, jj in zip(*np.nonzero(chk & (d2 > TOL))):
        BAD.append((iso(E[Ecell[a]]), SY[js[jj]], float(np.expm1(g2[a, jj])), float(y[a, jj])))
    n_cells_checked += int(chk.sum())
    LP[:, js] = C[brow + 1]
    for jj, jcol in enumerate(js):
        fin = np.nonzero(~nanm[:, jj])[0]
        if len(fin): first_fin[jcol] = int(TS[fin[0]]); last_fin[jcol] = int(TS[fin[-1]])
        kl = kline_closes(SY[jcol], "2026-08-22")
        bref = KREF_OPEN + ROW
        if kl is not None and KREF_OPEN in kl and bref in tix:
            has_k[jcol] = True; ref_b[jcol] = bref; ref_px[jcol] = kl[KREF_OPEN]; cref[jcol] = C[tix[bref] + 1, jj]
        elif len(fin):
            ref_b[jcol] = int(TS[fin[0]]); ref_px[jcol] = 1.0; cref[jcol] = C[fin[0] + 1, jj]
    log("block", j0, "applied", n_applied, "bad", len(BAD))
del R16
rec["P1"] = dict(cells_checked=n_cells_checked, cells_excluded_gapfilled=n_cells_gapfilled, max_abs_diff_after=maxdiff_after, n_over_tol=len(BAD), over_tol=BAD[:50],
                 bars_replaced=n_applied, meta_cells_whose_compound_changed=n_cells_changed)
check("P1.max_abs_diff_le_1e-6", maxdiff_after <= TOL and len(BAD) == 0, {"max_abs_diff_after": maxdiff_after, "n_over": len(BAD), "cells_checked": n_cells_checked})
check("P3.apply_patch_contract", n_applied == int(((pst == RL.RESTORED)).sum()), {"applied": n_applied})

# ---------------- diff vs the old table ----------------
LPO = np.load(OLD_LP[0], mmap_mode="r"); crefO = PMO["cref"].astype(np.float64)
check("diff.same_reference_prices", bool(np.array_equal(PMO["ref_px"], ref_px)) and bool(np.array_equal(PMO["ref_b"], ref_b)) and bool(np.array_equal(PMO["first_fin"], first_fin)))
valid = BND[:, None] >= first_fin[None, :]; valid &= (first_fin >= 0)[None, :]
dabs = (LP - cref[None, :]) - (np.asarray(LPO) - crefO[None, :])
cstart = (BND - 1) // 14400 * 14400; brix = {int(b): i for i, b in enumerate(BND)}; srow = np.array([brix.get(int(c), -1) for c in cstart])
okrow = srow >= 0
dpath = np.zeros_like(dabs); dpath[okrow] = dabs[okrow] - dabs[srow[okrow]]
off = BND - cstart; lab = np.where(off == 1500, "A+25m", np.where(off == 2400, "A+40m", np.where(off == 3000, "A+50m", "other")))
vm = valid & okrow[:, None]
cells_patch = {(int(e), int(c)) for e, c in zip(P["cell_E"], P["cell_col"])} | {(int((TS[r_] - 1) // 14400 * 14400), int(c_)) for r_, c_ in zip(grow, gcol)}
T2cells = {(int(e), int(c)) for e, c, t in zip(P["cell_E"], P["cell_col"], P["cell_T2"]) if t}
for g in RR["nan_runs"]["runs"]:                                            # target-exposed cells of the in-life NaN runs (census T2) count as T2 too
    for ec in g["exposed_cells"]: T2cells.add((calendar.timegm(time.strptime(ec, "%Y-%m-%dT%H:%MZ")), SY.index(g["sym"])))
rec["diff_vs_old_T2_cells"] = dict(bound_cells=int(P["cell_T2"].sum()), total_with_nan_run_cells=len(T2cells))
def tab(mask):
    x = np.abs(np.expm1(dabs[mask])); z = np.abs(np.expm1(dpath[mask]))
    return dict(n=int(mask.sum()), level_gt_1e_9=int((x > 1e-9).sum()), level_gt_1e_6=int((x > 1e-6).sum()), level_gt_1e_4=int((x > 1e-4).sum()), level_gt_1e_2=int((x > 1e-2).sum()),
                level_max=float(x.max()) if x.size else 0.0, path_gt_1e_6=int((z > 1e-6).sum()), path_gt_1e_4=int((z > 1e-4).sum()), path_gt_1e_2=int((z > 1e-2).sum()),
                path_max=float(z.max()) if z.size else 0.0)
rec["diff_vs_old"] = {L_: tab(vm & (lab == L_)[:, None]) for L_ in ("A+25m", "A+40m", "A+50m", "other")}
chg = np.argwhere(vm & (np.abs(np.expm1(dpath)) > 1e-6))
outside = [(iso(BND[i]), SY[j]) for i, j in chg if (int(cstart[i]), int(j)) not in cells_patch]
check("P4.path_changes_only_inside_patched_cells", len(outside) == 0, {"n_outside": len(outside), "examples": outside[:10]})
cellchg = {}
for i, j in chg:
    key = (int(cstart[i]), int(j)); dd = cellchg.setdefault(key, {"A+25m": 0.0, "A+40m": 0.0, "A+50m": 0.0, "other": 0.0})
    dd[str(lab[i])] = max(dd[str(lab[i])], abs(math.expm1(float(dpath[i, j]))))
rec["diff_vs_old"]["cells_with_path_change_gt_1e_6"] = len(cellchg)
rec["diff_vs_old"]["cells_with_path_change_T2"] = sum(1 for k in cellchg if k in T2cells)
for L_ in ("A+25m", "A+40m", "A+50m"):
    rec["diff_vs_old"][f"cells_{L_}_change_gt_1e_4_T2"] = sum(1 for k, v in cellchg.items() if k in T2cells and v[L_] > 1e-4)
    rec["diff_vs_old"][f"cells_{L_}_change_gt_1e_2_T2"] = sum(1 for k, v in cellchg.items() if k in T2cells and v[L_] > 1e-2)
rec["diff_vs_old"]["largest"] = [dict(E=iso(k[0]), sym=SY[k[1]], T2=k in T2cells, **{kk: round(vv, 6) for kk, vv in v.items()})
                                 for k, v in sorted(cellchg.items(), key=lambda kv: -max(kv[1].values()))[:30]]
kc = sorted(cellchg); np.savez(OUT + "/work/price_diff_vs_old.tmp.npz", cell_E=np.array([k[0] for k in kc], np.int64), cell_col=np.array([k[1] for k in kc], np.int64),
                              cell_T2=np.array([k in T2cells for k in kc], bool), **{("max_path_change_" + L_.replace("+", "p")): np.array([cellchg[k][L_] for k in kc]) for L_ in ("A+25m", "A+40m", "A+50m", "other")})
os.replace(OUT + "/work/price_diff_vs_old.tmp.npz", OUT + "/work/price_diff_vs_old.npz")
del dabs, dpath, LPO

# ---------------- kline sanity (not a gate), as r_prices.py ----------------
bchk = KCHK_OPEN + ROW; devs = {}
for j in np.nonzero(has_k)[0]:
    k2 = kline_closes(SY[j], "2026-08-30")
    if k2 is None or KCHK_OPEN not in k2 or bchk not in brix: continue
    chain = np.exp(LP[brix[bchk], j] - cref[j]); kr = k2[KCHK_OPEN] / ref_px[j]
    devs[SY[j]] = float(chain / kr - 1.0)
dv = np.abs(np.array(list(devs.values()))) if devs else np.array([np.nan])
rec["kline_sanity"] = dict(n=len(devs), median_abs_rel_dev=float(np.median(dv)), p99_abs_rel_dev=float(np.percentile(dv, 99)), max_abs_rel_dev=float(dv.max()))
rec["levels"] = dict(n_kline_ref=int(has_k.sum()), n_level_one=int(((~has_k) & (first_fin >= 0)).sum()), n_no_data=int((first_fin < 0).sum()))

# ---------------- write ----------------
os.makedirs(OUT + "/work", exist_ok=True); sfx = "" if SCEN == "exact" else "_" + SCEN
lp_p = OUT + f"/work/price_logtable_raw{sfx}.npy"; mt_p = OUT + f"/work/price_meta_raw{sfx}.npz"
np.save(lp_p + ".tmp.npy", LP); os.replace(lp_p + ".tmp.npy", lp_p)
np.savez(mt_p + ".tmp.npz", bounds=BND, symbols=np.array(SY), first_fin=first_fin, last_fin=last_fin, cref=cref, ref_px=ref_px, ref_b=ref_b, has_kline=has_k,
         raw_patch_bars=np.stack([P["E"], pcol, prow, pst, P["status"].astype(np.int64)], 1).astype(np.int64),   # E, col, row, status used, status in patch
         patch_sha256=np.array(psha), scenario=np.array(SCEN))
os.replace(mt_p + ".tmp.npz", mt_p)
rec["outputs"] = dict(logtable=dict(path=lp_p, sha256=sha(lp_p), shape=list(LP.shape)), meta=dict(path=mt_p, sha256=sha(mt_p)),
                      diff=dict(path=OUT + "/work/price_diff_vs_old.npz", sha256=sha(OUT + "/work/price_diff_vs_old.npz")))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "R_PRICES_RAW VERDICT=%s scenario=%s replaced=%d max_abs_diff_after=%.3e cells_path_changed=%d kline_median_dev=%.2e" % (
    rec["VERDICT"], SCEN, n_applied, maxdiff_after, len(cellchg), rec["kline_sanity"]["median_abs_rel_dev"]))
