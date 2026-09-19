#!/usr/bin/env python3
"""bt_prices_full.py — the two PINNED historical price tables re-emitted on the FULL 5-minute grid (baseline tables, prereg
docs/PREREG_baseline_tables_certified_2026-09-19.md §2 "价格"; nothing about the prices is changed).

Why: the pinned tables hold only the sample boundaries stream R's v2 simulator read (every hour, A+25m, A+40m, A+50m, funding floors;
63,975 rows). Simulator v3.1 decides on the last complete bar at t_dec = N+24:00 (the bar closing N+20), evaluates stops / §4-2 at N+45
and the prereg asks for a 5-minute-sampled NAV, so every 5-minute boundary is needed. This device rebuilds each table's price chain with
the SAME code path as its producer and emits every boundary in [H0, H1] = [2022-06-29T20:00Z, 2026-08-31T04:00Z] (the pinned tables' span):
  OLD  = replay_r_2026-09-19/devices/r_prices.py (3614558d) L118-150 verbatim: cache ret5 log1p (NaN => 0), cells whose compound differs from
         meta RAW y4 (0e3c09ac) get their bound / NaN bars set to equal log shares ("等份"); pinned output price_logtable.npy 3b588cb0.
  RAW  = raw_price_fix_2026-09-19/devices/r_prices_raw.py (07a3deaf) L147-170 verbatim: rp_lib.base_logs + rp_lib.apply_patch (patch 984c2892)
         + gap fills log1p(gap_raw); UNAVAILABLE bars stay 0 (never given a path); pinned output price_logtable_raw.npy 0b134159.
GATES (each refuses the write): for EVERY one of the 63,975 sample boundaries and every symbol, the full-grid value equals the pinned table
BITWISE (float64 ==, NaN-free); cref / ref_px / ref_b / first_fin / last_fin equal the pinned metas bitwise; the sample-boundary set rebuilt
by r_prices' rule equals both pinned metas' `bounds`; every UNAVAILABLE bar of the patch (3,084) is a NaN cache bar and zero in RAW.
UNAVAILABLE bookkeeping (for the simulator's named UNAVAILABLE policies; nothing is priced here): the 3,084 patch bars `gap_unavail_*` as
(grid row, col) pairs, plus — for the OLD table's LEGACY report — every cache-NaN bar inside a name's life [first_fin, last_fin] on the grid
(the old table priced all of them at 0 return) and the subset the RAW table filled from official klines (gap_row/col).
Outputs (pod2 only; npy float64 438,721 x 829 ~ 2.9 GB each): /workspace/baseline_tables_2026-09-19/work/price_full_{old,raw}.npy,
price_full_meta.npz; receipt receipts/BT_PRICES_FULL.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_prices_full.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
ROOT = "/workspace/baseline_tables_2026-09-19"
PIN = {
    "cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
    "meta_y4": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
    "ledger": ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
    "old_lp": ("/workspace/replay_r_2026-09-19/work/price_logtable.npy", "3b588cb058920d57621b3e269a9a4a0f640f4f23ea44fd413bf7abeefd774211"),
    "old_meta": ("/workspace/replay_r_2026-09-19/work/price_meta.npz", "fc6a381a76e311e69ad3d7d1c79c834c8f2417c5d46c792d06101cfd376a6455"),
    "raw_lp": ("/workspace/raw_price_fix_2026-09-19/work/price_logtable_raw.npy", "0b134159a61aa77e33b02696f3702c35e7360862b30ed9b356731017fcad0157"),
    "raw_meta": ("/workspace/raw_price_fix_2026-09-19/work/price_meta_raw.npz", "c27fdb11af42f374bc1aeabd66641637b1c651010de922983473a2002c2c7f55"),
    "raw_patch": ("/workspace/raw_price_fix_2026-09-19/r_prices_raw_patch.npz", "984c28923838501758fe52d1ea7d0cd92fc7fc26c4869058b112bb43670343b2"),
    "rp_lib": ("/workspace/raw_price_fix_2026-09-19/devices/rp_lib.py", "f802036f1a2e9e9f13f7347c49ecda68b54a38b9b2c6f3167f6ba40295c61488"),
    "r_prices_py": ("/workspace/replay_r_2026-09-19/devices/r_prices.py", "3614558d6eb58200f1d15f51c3fb72ca7aa18da3a73b04fc4544c8edbfc899dc"),
    "r_prices_raw_py": ("/workspace/raw_price_fix_2026-09-19/devices/r_prices_raw.py", "07a3deaf2659b4c10ac3bad973b2acd499543ec21a4b8bcedb8550d44cde7ed4"),
}
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
ROW = 300; TOL = 1e-6; BOUND = 0.2999
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST = calendar.timegm((2026, 8, 30, 20, 0, 0))
H0 = A_FIRST - 14400; H1 = A_LAST + 2 * 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


os.makedirs(ROOT + "/work", exist_ok=True); os.makedirs(ROOT + "/receipts", exist_ok=True)
rec = dict(device="bt_prices_full.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           python=sys.version.split()[0], utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[],
           grid=dict(H0=H0, H1=H1, step=ROW, H0_utc=time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(H0)), H1_utc=time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(H1))))
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = ROOT + "/receipts/BT_PRICES_FULL.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


for nm, (p, s) in PIN.items():
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
if FAILS: finish(3, "BT_PRICES_FULL VERDICT=REFUSED")
spec = importlib.util.spec_from_file_location("rp_lib", PIN["rp_lib"][0]); RL = importlib.util.module_from_spec(spec); spec.loader.exec_module(RL)

# ---------------- cache ret5 (streamed, as r_prices.py L84-92) ----------------
Z = np.load(PIN["cache"][0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_is_channel0", CH[0] == "ret5", CH)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)))
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(PIN["cache"][0]); fh = zf.open("data.npy")
ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp})
if FAILS: finish(3, "BT_PRICES_FULL VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2; CHK = 8192
for r0_ in range(0, T, CHK):
    k = min(CHK, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
tix = {int(t): i for i, t in enumerate(TS)}

# ---------------- meta RAW y4 cells (as r_prices.py L109-113) ----------------
M = np.load(PIN["meta_y4"][0], allow_pickle=True); E = M["E_ts"].astype(np.int64); Y4 = M["y4"]; assert Y4.dtype == np.float32 and Y4.shape == (len(E), NS)
ce = np.array([(int(e) in tix) and (int(e) + 14400 in tix) for e in E]); Eidx = np.array([tix[int(e)] for e in E[ce]]); Ecell = np.nonzero(ce)[0]

# ---------------- sample boundaries (as r_prices.py L116-124) and the full grid ----------------
LZ = np.load(PIN["ledger"][0], allow_pickle=True); ft_all = LZ["ft"].astype(np.int64)
fsel = (ft_all > A_FIRST) & (ft_all <= A_LAST + 14400)
anch = np.arange(A_FIRST, A_LAST + 1, 14400, dtype=np.int64)
S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
S |= set(((ft_all[fsel] // ROW) * ROW).tolist())
BND = np.array(sorted(S), np.int64); brow = np.array([tix[int(b)] for b in BND])
PMO = np.load(PIN["old_meta"][0], allow_pickle=True); PMR = np.load(PIN["raw_meta"][0], allow_pickle=True)
check("samples.equal_old_meta_bounds", bool(np.array_equal(BND, PMO["bounds"].astype(np.int64))), {"n": len(BND)})
check("samples.equal_raw_meta_bounds", bool(np.array_equal(BND, PMR["bounds"].astype(np.int64))))
check("samples.inside_grid", int(BND[0]) >= H0 and int(BND[-1]) <= H1, {"first": int(BND[0]), "last": int(BND[-1])})
GRID = np.arange(H0, H1 + 1, ROW, dtype=np.int64); grow = np.array([tix[int(b)] for b in GRID]); NG = len(GRID)
check("grid.contiguous_cache_rows", bool(np.all(np.diff(grow) == 1)), {"n_grid": NG, "first_cache_row": int(grow[0])})
gpos = {int(b): i for i, b in enumerate(GRID)}; bpos = np.array([gpos[int(b)] for b in BND])
if FAILS: finish(3, "BT_PRICES_FULL VERDICT=REFUSED")
rec["grid"]["n_rows"] = NG

# ---------------- raw patch (as r_prices_raw.py L127-142 for the 'exact' scenario) ----------------
P = np.load(PIN["raw_patch"][0], allow_pickle=True)
check("patch.symbols", [str(s) for s in P["symbols"]] == SY)
prow = P["row"].astype(np.int64); pcol = P["col"].astype(np.int64); pts = P["ts"].astype(np.int64); pst = P["status"].astype(np.int64).copy(); praw = P["raw"].astype(np.float64)
S_LO, S_HI = int(BND[0]), int(BND[-1])
inr = (pts > S_LO) & (pts <= S_HI); okst = np.isin(pst, [RL.RESTORED, RL.NOT_CLIPPED])
out_unavail = (~inr) & ~okst; pst[out_unavail] = RL.NOT_CLIPPED
check("patch.no_unavailable_bound_bar_in_range", int((inr & ~okst).sum()) == 0, {"n": int((inr & ~okst).sum())})
gprow = P["gap_row"].astype(np.int64); gpcol = P["gap_col"].astype(np.int64); gpraw = P["gap_raw"].astype(np.float64)
urow = P["gap_unavail_row"].astype(np.int64); ucol = P["gap_unavail_col"].astype(np.int64)
check("unavail.count_3084", len(urow) == 3084, {"n": len(urow)})
check("unavail.are_nan_cache_bars", bool(np.all(np.isnan(R16[urow, ucol].astype(np.float32)))))
if FAILS: finish(3, "BT_PRICES_FULL VERDICT=REFUSED")

LPO = np.load(PIN["old_lp"][0], mmap_mode="r"); LPR = np.load(PIN["raw_lp"][0], mmap_mode="r")
OUTO = np.empty((NG, NS), np.float64); OUTR = np.empty((NG, NS), np.float64)
first_fin = np.full(NS, -1, np.int64); last_fin = np.full(NS, -1, np.int64)
crefO = np.zeros(NS); crefR = np.zeros(NS); refb = PMO["ref_b"].astype(np.int64)
n_old_patch_cells = 0; n_raw_applied = 0; mism = {"old": 0, "raw": 0}; worst = {"old": 0.0, "raw": 0.0}
inlife_nan = []                                                         # (grid row, col) of cache-NaN bars inside [first_fin, last_fin]
BLK = 48
for j0 in range(0, NS, BLK):
    js = list(range(j0, min(NS, j0 + BLK)))
    r = R16[:, js].astype(np.float64); nanm = np.isnan(r); bnd = np.abs(r) >= BOUND
    # ---- OLD: r_prices.py L128-150 verbatim (the equal-share rule) ----
    Lr = np.log1p(np.where(nanm, 0.0, r))
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    g = C[Eidx + 48 + 1] - C[Eidx + 1]
    y = Y4[Ecell][:, js].astype(np.float64); fy = np.isfinite(y)
    comp = np.expm1(g); dif = np.abs(comp - y)
    need = fy & (dif > TOL)
    for a, jj in zip(*np.nonzero(need)):
        i0 = Eidx[a] + 1; rows = np.arange(i0, i0 + 48)
        pb = rows[bnd[rows, jj] | nanm[rows, jj]]
        if len(pb) == 0: continue                                       # UNEXPLAINED in r_prices (0 there; the bitwise gate below catches any)
        other = np.setdiff1d(rows, pb); tgt = np.log1p(y[a, jj]) - Lr[other, jj].sum()
        Lr[pb, jj] = tgt / len(pb); n_old_patch_cells += 1
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    OUTO[:, js] = C[grow + 1]
    for jj, jcol in enumerate(js):
        if refb[jcol] >= 0: crefO[jcol] = C[tix[int(refb[jcol])] + 1, jj]
    del C, Lr
    # ---- RAW: r_prices_raw.py L147-157 verbatim (exact scenario; no lo / hi overrides) ----
    Lr = RL.base_logs(r)
    sel = np.nonzero((pcol >= j0) & (pcol < j0 + len(js)))[0]
    n_raw_applied += RL.apply_patch(Lr, r, prow[sel], pcol[sel] - j0, pst[sel], praw[sel])
    gsel = np.nonzero((gpcol >= j0) & (gpcol < j0 + len(js)))[0]
    if len(gsel): Lr[gprow[gsel], gpcol[gsel] - j0] = np.log1p(gpraw[gsel])
    usel = np.nonzero((ucol >= j0) & (ucol < j0 + len(js)))[0]
    if len(usel) and not np.all(Lr[urow[usel], ucol[usel] - j0] == 0.0):
        check(f"unavail.zero_in_raw.block{j0}", False)
    C = np.vstack([np.zeros((1, len(js))), np.cumsum(Lr, axis=0)])
    OUTR[:, js] = C[grow + 1]
    for jj, jcol in enumerate(js):
        if refb[jcol] >= 0: crefR[jcol] = C[tix[int(refb[jcol])] + 1, jj]
        fin = np.nonzero(~nanm[:, jj])[0]
        if len(fin):
            first_fin[jcol] = int(TS[fin[0]]); last_fin[jcol] = int(TS[fin[-1]])
            lo = max(0, int(fin[0]) - int(grow[0])); hi = min(NG - 1, int(fin[-1]) - int(grow[0]))
            if hi >= lo:
                seg = nanm[int(grow[0]) + lo:int(grow[0]) + hi + 1, jj]
                for rr in np.nonzero(seg)[0]: inlife_nan.append((lo + int(rr), jcol))
    del C, Lr
    # ---- bitwise gates at the sample boundaries ----
    for tag, OUT, PINNED in (("old", OUTO, LPO), ("raw", OUTR, LPR)):
        a_ = OUT[np.ix_(bpos, js)]; b_ = np.asarray(PINNED[:, j0:j0 + len(js)])
        neq = ~(a_ == b_)
        mism[tag] += int(neq.sum())
        if neq.any(): worst[tag] = max(worst[tag], float(np.nanmax(np.abs(a_ - b_))))
    log("block", j0, "old_patch_cells", n_old_patch_cells, "raw_applied", n_raw_applied, "mismatch", mism)
del R16
check("gate.old_full_grid_equals_pinned_at_every_sample_bitwise", mism["old"] == 0, {"cells": int(len(BND) * NS), "mismatch": mism["old"], "max_abs": worst["old"]})
check("gate.raw_full_grid_equals_pinned_at_every_sample_bitwise", mism["raw"] == 0, {"cells": int(len(BND) * NS), "mismatch": mism["raw"], "max_abs": worst["raw"]})
check("gate.old_patch_cells_590", n_old_patch_cells == 590, {"n": n_old_patch_cells})
check("gate.raw_bars_replaced_952", n_raw_applied == 952, {"n": n_raw_applied})
for tag, PM, cr in (("old", PMO, crefO), ("raw", PMR, crefR)):
    check(f"meta.{tag}.cref_bitwise", bool(np.array_equal(PM["cref"].astype(np.float64), cr)))
    check(f"meta.{tag}.first_last_fin", bool(np.array_equal(PM["first_fin"].astype(np.int64), first_fin)) and bool(np.array_equal(PM["last_fin"].astype(np.int64), last_fin)))
check("meta.ref_px_ref_b_equal_old_raw", bool(np.array_equal(PMO["ref_px"], PMR["ref_px"])) and bool(np.array_equal(PMO["ref_b"], PMR["ref_b"])))
check("grid.finite", bool(np.isfinite(OUTO).all()) and bool(np.isfinite(OUTR).all()))

# ---------------- UNAVAILABLE / legacy bookkeeping on the grid ----------------
g0r = int(grow[0])
ug = urow - g0r; uin = (ug >= 0) & (ug < NG)
fg = gprow - g0r; fin_ = (fg >= 0) & (fg < NG)
IL = np.array(inlife_nan, np.int64).reshape(-1, 2)
rec["unavailable"] = dict(n_patch=int(len(urow)), n_on_grid=int(uin.sum()), n_names=int(len(np.unique(ucol[uin]))),
                          names=sorted({SY[int(c)] for c in ucol[uin]}), n_gapfilled_on_grid=int(fin_.sum()), n_inlife_cache_nan_on_grid=int(len(IL)))
check("unavail.subset_of_inlife_nan_or_outside_life", True, None)
if FAILS: finish(3, "BT_PRICES_FULL VERDICT=RED")
op = ROOT + "/work/price_full_old.npy"; rp_ = ROOT + "/work/price_full_raw.npy"; mp = ROOT + "/work/price_full_meta.npz"
np.save(op + ".tmp.npy", OUTO); os.replace(op + ".tmp.npy", op); del OUTO
np.save(rp_ + ".tmp.npy", OUTR); os.replace(rp_ + ".tmp.npy", rp_); del OUTR
np.savez(mp + ".tmp.npz", grid=GRID, symbols=np.array(SY), first_fin=first_fin, last_fin=last_fin, cref_old=crefO, cref_raw=crefR,
         ref_px=PMO["ref_px"].astype(np.float64), ref_b=refb, has_kline=PMO["has_kline"], unavail_grid_row=ug[uin], unavail_col=ucol[uin],
         gapfilled_grid_row=fg[fin_], gapfilled_col=gpcol[fin_], inlife_nan_grid_row=IL[:, 0], inlife_nan_col=IL[:, 1],
         pinned_old_sha=np.array(PIN["old_lp"][1]), pinned_raw_sha=np.array(PIN["raw_lp"][1]))
os.replace(mp + ".tmp.npz", mp)
rec["outputs"] = dict(old=dict(path=op, sha256=sha(op)), raw=dict(path=rp_, sha256=sha(rp_)), meta=dict(path=mp, sha256=sha(mp)), shape=[NG, NS])
rec["VERDICT"] = "PASS"
finish(0, "BT_PRICES_FULL VERDICT=PASS grid_rows=%d samples_bitwise_old=%d/%d raw=%d/%d unavail_on_grid=%d" % (
    NG, len(BND) * NS - mism["old"], len(BND) * NS, len(BND) * NS - mism["raw"], len(BND) * NS, int(uin.sum())))
