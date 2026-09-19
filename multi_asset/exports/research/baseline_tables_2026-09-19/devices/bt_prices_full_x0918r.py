#!/usr/bin/env python3
"""bt_prices_full_x0918r.py — the EXTENDED restored price table (raw_price_fix_2026-09-19/ext_x0918r, commit 1a1e221b4: price_logtable_raw_x0918r.npy
9249b0da, price_meta_raw_x0918r.npz da136830; 5m bars to 2026-09-19T00:00Z, last anchor 2026-09-18T20Z) re-emitted on the FULL 5-minute grid for
simulator v3.1 (same reason as bt_prices_full.py: v3.1 reads N+20 / N+45 and the prereg asks for a 5-minute NAV). Nothing about the prices changes.
Chain = r_prices_raw_x0918r.py (217425a1) L166-176 verbatim: cache x0918r (08bb2957) ret5 → rp_lib.base_logs → rp_lib.apply_patch with the COMBINED
patch (base 984c2892 ∪ extension 01d234c7) → gap fills log1p(gap_raw) (all from the base patch; the extension adds none) → cumsum.
Grid = [2022-06-29T20:00Z, 2026-09-19T00:00Z] (the extended table's span; its boundaries past the cache's last row are not priceable, as there).
GATES (each refuses the write):
  G1 the sample set rebuilt by the extension device's rule equals the pinned meta's `bounds` (64,769);
  G2 at EVERY one of those 64,769 sample boundaries × 829 symbols the full grid equals the pinned extended table BITWISE (uint64 view);
  G3 over the old grid span (438,721 rows, 2022-06-29T20:00Z → 2026-08-31T04:00Z) the full grid equals bt_prices_full.py's raw grid
     price_full_raw.npy (b935ea28) BITWISE on every cell — the extension changes nothing already simulated;
  G4 first_fin / cref / ref_px / ref_b equal the pinned extended meta; G5 UNAVAILABLE bars = the base patch's 3,084 (the extension adds none),
     each a NaN cache bar with 0 log return on the grid.
Outputs (pod2): /workspace/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy (+ price_full_raw_x0918r_meta.npz); receipt
receipts/BT_PRICES_FULL_X0918R.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_prices_full_x0918r.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
ROOT = "/workspace/baseline_tables_2026-09-19"; RPF = "/workspace/raw_price_fix_2026-09-19"
PIN = {
    "cache_x0918r": ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75"),
    "base_patch": (RPF + "/r_prices_raw_patch.npz", "984c28923838501758fe52d1ea7d0cd92fc7fc26c4869058b112bb43670343b2"),
    "ext_patch": (RPF + "/ext_x0918r/r_prices_raw_patch_x0918r_ext.npz", "01d234c7e8e28ea986ec9be6b322ee1ec64b98bb3e76aaf0e547587ee3cd93d2"),
    "rp_lib": (RPF + "/devices/rp_lib.py", "f802036f1a2e9e9f13f7347c49ecda68b54a38b9b2c6f3167f6ba40295c61488"),
    "ext_device": (RPF + "/ext_x0918r/devices/r_prices_raw_x0918r.py", "217425a1be249d01d209d15af5864bd54271b83843c6dd4d41440b11c2af6d5e"),
    "ext_lp": (RPF + "/ext_x0918r/work/price_logtable_raw_x0918r.npy", "9249b0da4a4c578900cbafd29e1cec28de57f4437f037f1280040b2a84196608"),
    "ext_meta": (RPF + "/ext_x0918r/work/price_meta_raw_x0918r.npz", "da136830cee7e1a219e56e69ce9d50de2eead6864df7d205cdb7559151162df3"),
    "ledger_p2": ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
    "ledger_axis": ("/workspace/axis_0919/funding/funding_ledger.npz", "74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d"),
    "my_full_raw": (ROOT + "/work/price_full_raw.npy", "b935ea28e386ba3c82145fe4527ebce2258c0a29208109dc4a07d1b6d13b6cac"),
    "my_full_meta": (ROOT + "/work/price_full_meta.npz", "f2f5382889f8c926ab2b47a81def234b1d5b7ee9cc15a86cdcfaba69416ff7b4"),
}
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
ROW = 300; CELL = 14400
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST = calendar.timegm((2026, 9, 18, 20, 0, 0)); H0 = A_FIRST - CELL


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = dict(device="bt_prices_full_x0918r.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           python=sys.version.split()[0], utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = ROOT + "/receipts/BT_PRICES_FULL_X0918R.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


for nm, (p, s) in PIN.items():
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
if FAILS: finish(3, "BT_PRICES_FULL_X0918R VERDICT=REFUSED")
spec = importlib.util.spec_from_file_location("rp_lib", PIN["rp_lib"][0]); RL = importlib.util.module_from_spec(spec); spec.loader.exec_module(RL)

Z = np.load(PIN["cache_x0918r"][0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_channel0_strict_5m", CH[0] == "ret5" and bool(np.all(np.diff(TS) == ROW)), {"first": iso(TS[0]), "last": iso(TS[-1])})
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(PIN["cache_x0918r"][0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp})
if FAILS: finish(3, "BT_PRICES_FULL_X0918R VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2
for r0_ in range(0, T, 8192):
    k = min(8192, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
tix = {int(t): i for i, t in enumerate(TS)}

# ---- G1 sample set (r_prices_raw_x0918r.py L112-124) and the full grid ----
LZ = np.load(PIN["ledger_p2"][0], allow_pickle=True); ft_p2 = LZ["ft"].astype(np.int64)
LA = np.load(PIN["ledger_axis"][0], allow_pickle=True); ft_ax = LA["ts"].astype(np.int64)
anch = np.arange(A_FIRST, A_LAST + 1, CELL, dtype=np.int64); H1 = A_LAST + 2 * CELL
S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
for f_ in (ft_p2, ft_ax):
    sel = (f_ > A_FIRST) & (f_ <= A_LAST + CELL); S |= set(((f_[sel] // ROW) * ROW).tolist())
allb = np.array(sorted(S), np.int64); BND = allb[allb <= int(TS[-1])]
PME = np.load(PIN["ext_meta"][0], allow_pickle=True)
check("G1.sample_set_equals_pinned_meta_bounds", bool(np.array_equal(BND, PME["bounds"].astype(np.int64))), {"n": len(BND)})
GEND = int(TS[-1]); GRID = np.arange(H0, GEND + 1, ROW, dtype=np.int64); grow = np.array([tix[int(b)] for b in GRID]); NG = len(GRID)
gpos = {int(b): i for i, b in enumerate(GRID)}; bpos = np.array([gpos[int(b)] for b in BND])
rec["grid"] = dict(H0=iso(H0), end=iso(GEND), n_rows=NG)

# ---- patch (r_prices_raw_x0918r.py L149-163) ----
PB = np.load(PIN["base_patch"][0], allow_pickle=True); PX = np.load(PIN["ext_patch"][0], allow_pickle=True)
check("patch.symbols", [str(s) for s in PB["symbols"]] == SY and [str(s) for s in PX["symbols"]] == SY)
prow = np.concatenate([PB["row"], PX["row"]]).astype(np.int64); pcol = np.concatenate([PB["col"], PX["col"]]).astype(np.int64)
pts = np.concatenate([PB["ts"], PX["ts"]]).astype(np.int64); pst = np.concatenate([PB["status"], PX["status"]]).astype(np.int64); praw = np.concatenate([PB["raw"], PX["raw"]]).astype(np.float64)
S_LO, S_HI = int(BND[0]), int(BND[-1]); inr = (pts > S_LO) & (pts <= S_HI); okst = np.isin(pst, [RL.RESTORED, RL.NOT_CLIPPED])
check("patch.no_unavailable_bound_bar_in_range", int((inr & ~okst).sum()) == 0)
pst[(~inr) & ~okst] = RL.NOT_CLIPPED
grw = np.concatenate([PB["gap_row"], PX["gap_row"]]).astype(np.int64); gcl = np.concatenate([PB["gap_col"], PX["gap_col"]]).astype(np.int64)
grv = np.concatenate([PB["gap_raw"], PX["gap_raw"]]).astype(np.float64)
urow = np.concatenate([PB["gap_unavail_row"], PX["gap_unavail_row"]]).astype(np.int64); ucol = np.concatenate([PB["gap_unavail_col"], PX["gap_unavail_col"]]).astype(np.int64)
check("G5.unavailable_count_3084_ext_adds_none", len(urow) == 3084 and len(PX["gap_unavail_row"]) == 0, {"n": len(urow)})
check("G5.unavailable_are_nan_cache_bars", bool(np.all(np.isnan(R16[urow, ucol].astype(np.float32)))))
if FAILS: finish(3, "BT_PRICES_FULL_X0918R VERDICT=REFUSED")

LPE = np.load(PIN["ext_lp"][0], mmap_mode="r"); LPF = np.load(PIN["my_full_raw"][0], mmap_mode="r"); NG_OLD = LPF.shape[0]
PMF = np.load(PIN["my_full_meta"][0], allow_pickle=True)
check("G3.old_grid_is_a_prefix", int(PMF["grid"][0]) == H0 and np.array_equal(PMF["grid"].astype(np.int64), GRID[:NG_OLD]), {"old_rows": NG_OLD, "new_rows": NG})
OUT = np.empty((NG, NS), np.float64); first_fin = np.full(NS, -1, np.int64); cref = np.zeros(NS); refb = PME["ref_b"].astype(np.int64)
n_applied = 0; mis2 = 0; mis3 = 0
for j0 in range(0, NS, 48):
    js = list(range(j0, min(NS, j0 + 48)))
    r = R16[:, js].astype(np.float64); nanm = np.isnan(r); Lr = RL.base_logs(r)
    sel = np.nonzero((pcol >= j0) & (pcol < j0 + len(js)))[0]
    n_applied += RL.apply_patch(Lr, r, prow[sel], pcol[sel] - j0, pst[sel], praw[sel])
    gsel = np.nonzero((gcl >= j0) & (gcl < j0 + len(js)))[0]
    if len(gsel): Lr[grw[gsel], gcl[gsel] - j0] = np.log1p(grv[gsel])
    usel = np.nonzero((ucol >= j0) & (ucol < j0 + len(js)))[0]
    if len(usel) and not np.all(Lr[urow[usel], ucol[usel] - j0] == 0.0): check(f"G5.unavailable_zero_return.block{j0}", False)
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    OUT[:, js] = C[grow + 1]
    for jj, jcol in enumerate(js):
        if refb[jcol] >= 0: cref[jcol] = C[tix[int(refb[jcol])] + 1, jj]
        fin = np.nonzero(~nanm[:, jj])[0]
        if len(fin): first_fin[jcol] = int(TS[fin[0]])
    del C, Lr
    a_ = np.ascontiguousarray(OUT[np.ix_(bpos, js)]).view(np.uint64); b_ = np.ascontiguousarray(LPE[:, j0:j0 + len(js)]).view(np.uint64); mis2 += int((a_ != b_).sum())
    for k0 in range(0, NG_OLD, 65536):
        k1 = min(NG_OLD, k0 + 65536)
        mis3 += int((np.ascontiguousarray(OUT[k0:k1, j0:j0 + len(js)]).view(np.uint64) != np.ascontiguousarray(LPF[k0:k1, j0:j0 + len(js)]).view(np.uint64)).sum())
    if j0 % 192 == 0: log("block", j0, "applied", n_applied, "G2 mismatch", mis2, "G3 mismatch", mis3)
del R16
check("G2.full_grid_equals_pinned_extended_table_at_every_sample_bitwise", mis2 == 0, {"cells": int(len(BND) * NS), "mismatch": mis2})
check("G3.full_grid_equals_my_old_full_raw_grid_on_the_old_span_bitwise", mis3 == 0, {"cells": int(NG_OLD * NS), "mismatch": mis3})
check("G4.cref_first_fin_ref_equal_pinned_meta", bool(np.array_equal(cref, PME["cref"].astype(np.float64))) and bool(np.array_equal(first_fin, PME["first_fin"].astype(np.int64))))
check("patch.applied_952_plus_ext", n_applied == int((pst == RL.RESTORED).sum()), {"applied": n_applied})
check("grid.finite", bool(np.isfinite(OUT).all()))
if FAILS: finish(3, "BT_PRICES_FULL_X0918R VERDICT=RED (not written)")
g0r = int(grow[0]); ug = urow - g0r; uin = (ug >= 0) & (ug < NG)
fg = grw - g0r; fin_ = (fg >= 0) & (fg < NG)
op = ROOT + "/work/price_full_raw_x0918r.npy"; mp = ROOT + "/work/price_full_raw_x0918r_meta.npz"
np.save(op + ".tmp.npy", OUT); os.replace(op + ".tmp.npy", op); del OUT
np.savez(mp + ".tmp.npz", grid=GRID, symbols=np.array(SY), first_fin=first_fin, last_fin=PME["last_fin"].astype(np.int64), cref_raw=cref,
         ref_px=PME["ref_px"].astype(np.float64), ref_b=refb, has_kline=PME["has_kline"], unavail_grid_row=ug[uin], unavail_col=ucol[uin],
         gapfilled_grid_row=fg[fin_], gapfilled_col=gcl[fin_], inlife_nan_grid_row=np.zeros(0, np.int64), inlife_nan_col=np.zeros(0, np.int64),
         pinned_ext_sha=np.array(PIN["ext_lp"][1]), note=np.array("raw table only; the OLD table has no extension (inlife_nan arrays empty)"))
os.replace(mp + ".tmp.npz", mp)
rec["unavailable"] = dict(n_on_grid=int(uin.sum()), n_gapfilled_on_grid=int(fin_.sum()))
rec["outputs"] = dict(raw=dict(path=op, sha256=sha(op)), meta=dict(path=mp, sha256=sha(mp)), shape=[NG, NS])
rec["VERDICT"] = "PASS"
finish(0, "BT_PRICES_FULL_X0918R VERDICT=PASS grid_rows=%d samples_bitwise=%d/%d old_span_bitwise=%d/%d" % (NG, len(BND) * NS - mis2, len(BND) * NS, NG_OLD * NS - mis3, NG_OLD * NS))
