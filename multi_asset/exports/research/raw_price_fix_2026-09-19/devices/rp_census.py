#!/usr/bin/env python3
"""rp_census.py — R5-02 step 1: enumerate EVERY clipped (ret5 == +-float16(0.3)) or missing (in-life NaN) bar of the pinned 5m cache
that the stream-R replay price path can use, tier them, and write the official-archive fetch list.

Scope is the whole cache (not the 590 cells the old device found through the y4 mismatch):
  bound bars   every cache cell with |ret5| == float16(0.3) = 0.300048828125 (asserted identical to the old device's |r| >= 0.2999 set);
  missing bars every NaN run strictly inside a symbol's life (first .. last finite bar). NaN before listing / after the last bar is not a
               path bar (the replay's px() returns None before the first finite bar; after the last bar see the dead-contract note).
Tiers (each a subset of the previous):
  T0 whole cache;
  T1 inside the replay's sampled range: the bar's ts in (first sample boundary, last sample boundary] of the pinned old price table
     (a ratio between two sample boundaries b1 < b2 contains exactly the bars with ts in (b1, b2]);
  T2 target-exposed: the symbol has a non-zero target in any of the 8 replay books (4 S2 arms x CMB/LIT) at the cell's anchor E or at
     E - 4h (the target held until the E+25m rebalance). A proxy for "the replay holds it": the executor can also keep a name it could
     not exit, so T2 is reported next to T1, never instead of it.
Also: whether the old device patched the cell (price_meta.npz 'patches'), whether meta RAW y4 is finite there.
Fetch list: (symbol, UTC day) daily archives covering, for every bound-bar cell, the closes at E .. E+4h (days of E-5m and E), and for
every in-life NaN run, the day before the run through the day of its last bar.
Writes only under /workspace/raw_price_fix_2026-09-19/ (work/census.npz, work/fetch_list.json, receipts/RP_CENSUS.json).
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rp_census.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, importlib.util
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
OUT = "/workspace/raw_price_fix_2026-09-19"
CACHE = ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488")
META = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
OLD_PMETA = ("/workspace/replay_r_2026-09-19/work/price_meta.npz", "fc6a381a76e311e69ad3d7d1c79c834c8f2417c5d46c792d06101cfd376a6455")
P2LIB = ("/workspace/uplift_r2_2026-09-13/P2/devices/p2_s2_lib.py", "c53f5c495036727fcd7115bad6838229923c91f6b76bed955ebdb0f25d57c831")
S2_RUNS = {   # RUN_CONFIG_replay_r_2026-09-19.json s2_runs (json, vec)
    "S2_A0pred_s42": ("d01063c0ee68a48799229aef60736e7a1a8e46dbbdc9d5d72f3f227f95affbbe", "8c7c886376c484ea243efc2e94bac529f6cc9dfee5ceba3104dd6d89201c9770"),
    "S2_A0pred_s2027": ("c63b59a72438a1a0f789e548ac10e5ed48e54a9e23bcfbdcd532c497b3850133", "17b78784c6846cfc198a10e1531cc9befd82a6b382323a304eda34e1aca0b8c4"),
    "S2_v4_s42": ("4c5612f613ddad105d7c8997dcdc5a37bda8ccb8892b80cf18b370d325232bc6", "902c8d905a63b3a0a03a5ae485707eb21288d122816d32b4d1c81429f6a28a91"),
    "S2_v4_s2027": ("5aba956d75faec46e63147baf84f37b5ed2af58a91061438ce94329aa3a71741", "1aeef37b0ad36676bda586958b958acc20f2ed99fdcda58f0dd4b1358200801b"),
}
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
ROW = 300; CELL = 14400
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST = calendar.timegm((2026, 8, 30, 20, 0, 0))   # RUN_CONFIG window (scored anchors)
B16 = np.float16(0.3)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def day(t): return time.strftime("%Y-%m-%d", time.gmtime(int(t)))


rec = dict(device="rp_census.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1); os.makedirs(OUT + "/receipts", exist_ok=True)
    rp = OUT + "/receipts/RP_CENSUS.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


for nm, (p, s) in (("cache", CACHE), ("meta", META), ("old_price_meta", OLD_PMETA), ("p2_s2_lib", P2LIB)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
if FAILS: finish(3, "RP_CENSUS VERDICT=REFUSED")

# ---------------- stream ret5 (channel 0) out of the cache, never the whole array ----------------
Z = np.load(CACHE[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ret5_is_channel0", CH[0] == "ret5", CH)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)))
NS = len(SY); T = len(TS)
zf = zipfile.ZipFile(CACHE[0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
check("cache.data_header", shp == (T, NS, len(CH)) and not fo and dt == np.float16, {"shape": shp})
if FAILS: finish(3, "RP_CENSUS VERDICT=REFUSED")
R16 = np.empty((T, NS), np.float16); rowb = NS * len(CH) * 2
for r0_ in range(0, T, 8192):
    k = min(8192, T - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
    R16[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, NS, len(CH))[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
tix = {int(t): i for i, t in enumerate(TS)}

# ---------------- replay sample range and books ----------------
PM = np.load(OLD_PMETA[0], allow_pickle=True); BND = PM["bounds"].astype(np.int64); check("old_meta.symbols", [str(s) for s in PM["symbols"]] == SY)
S_LO, S_HI = int(BND[0]), int(BND[-1]); rec["sample_range"] = dict(first=iso(S_LO), last=iso(S_HI), n=len(BND))
old_patch = {(int(e), int(j)) for e, j in zip(PM["patches"][:, 0], PM["patches"][:, 1])}
old_patch_bars = {(int(e), int(j)): int(n) for e, j, n in zip(PM["patches"][:, 0], PM["patches"][:, 1], PM["patches"][:, 2])}
spec = importlib.util.spec_from_file_location("p2_s2_lib", P2LIB[0]); L2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(L2)
AX = None; HELD = None; book_n = {}
for arm, (js, vs) in sorted(S2_RUNS.items()):
    d, Vz, rsha, vsha = L2.load_run(arm); check(f"s2run.{arm}.shas", rsha == js and vsha == vs, {"json": rsha[:16], "vec": vsha[:16]})
    V = {k: Vz[k] for k in Vz.files}; A_, B, fl = L2.books(d, V)
    if AX is None: AX = A_.astype(np.int64); HELD = np.zeros((len(AX), NS), bool)
    assert np.array_equal(AX, A_)
    for bk in ("CMB", "LIT"):
        nz = np.abs(B[bk]) > 0; HELD |= nz; book_n[f"{arm}|{bk}"] = int(nz.sum())
    del B, V, d
if FAILS: finish(3, "RP_CENSUS VERDICT=REFUSED")
AXI = {int(a): i for i, a in enumerate(AX)}
def exposed(E, j):
    i = AXI.get(int(E))
    if i is None: return False
    return bool(HELD[i, j] or (i > 0 and HELD[i - 1, j]))
log("books loaded", book_n)

MZ = np.load(META[0], allow_pickle=True); ME = MZ["E_ts"].astype(np.int64); MY = MZ["y4"]; MEI = {int(e): i for i, e in enumerate(ME)}

# ---------------- bound bars ----------------
bnd_eq = (R16 == B16) | (R16 == -B16); bnd_old = np.abs(R16.astype(np.float32)) >= 0.2999
check("bound.exact_equals_old_threshold_set", bool(np.array_equal(bnd_eq, bnd_old)), {"n_exact": int(bnd_eq.sum()), "n_ge_0.2999": int(bnd_old.sum())})
check("bound.no_value_beyond_bound", float(np.nanmax(np.abs(R16.astype(np.float32)))) == float(B16))
rr, cc = np.nonzero(bnd_eq); o = np.lexsort((rr, cc)); rr = rr[o]; cc = cc[o]
bts = TS[rr]; bE = (bts - 1) // CELL * CELL; bpos = ((bts - bE) // ROW).astype(np.int64)          # 1..48 inside (E, E+4h]
bval = R16[rr, cc].astype(np.float64)
t1 = (bts > S_LO) & (bts <= S_HI)
t2 = np.array([exposed(e, j) for e, j in zip(bE, cc)]) & t1
scored = (bE >= A_FIRST) & (bE <= A_LAST)
y4f = np.array([(int(e) in MEI) and np.isfinite(MY[MEI[int(e)], j]) for e, j in zip(bE, cc)])
oldp = np.array([(int(e), int(j)) in old_patch for e, j in zip(bE, cc)])
cells = sorted({(int(e), int(j)) for e, j in zip(bE, cc)})
cell_nb = {}
for e, j in zip(bE, cc): cell_nb[(int(e), int(j))] = cell_nb.get((int(e), int(j)), 0) + 1
def cset(mask): return {(int(e), int(j)) for e, j in zip(bE[mask], cc[mask])}
c0, c1, c2 = cset(np.ones(len(bE), bool)), cset(t1), cset(t2)
nan_in_cell = {}
for (e, j) in c0:
    if e + ROW in tix and e + CELL in tix:
        i0 = tix[e + ROW]; nan_in_cell[(e, j)] = int(np.isnan(R16[i0:i0 + 48, j]).sum())
    else:
        nan_in_cell[(e, j)] = -1
rec["bound"] = dict(
    T0_whole_cache=dict(bars=int(len(rr)), cells=len(c0), anchors=len({e for e, _ in c0}), symbols=len({j for _, j in c0}), pos=int((bval > 0).sum()), neg=int((bval < 0).sum()),
                        first=iso(bts.min()), last=iso(bts.max())),
    T1_replay_sampled=dict(bars=int(t1.sum()), cells=len(c1), anchors=len({e for e, _ in c1}), symbols=len({j for _, j in c1}), outside_before=int((bts <= S_LO).sum()), outside_after=int((bts > S_HI).sum())),
    T2_target_exposed=dict(bars=int(t2.sum()), cells=len(c2), anchors=len({e for e, _ in c2}), symbols=len({j for _, j in c2})),
    T1_cells_by_bound_bar_count={str(k): int(v) for k, v in zip(*np.unique([cell_nb[c] for c in c1], return_counts=True))},
    T2_cells_by_bound_bar_count={str(k): int(v) for k, v in zip(*np.unique([cell_nb[c] for c in c2], return_counts=True))},
    T1_cells_multi_bound=int(sum(1 for c in c1 if cell_nb[c] >= 2)), T2_cells_multi_bound=int(sum(1 for c in c2 if cell_nb[c] >= 2)),
    T1_cells_with_nan_bars=int(sum(1 for c in c1 if nan_in_cell[c] > 0)),
    old_device=dict(cells_patched_total=len(old_patch), bars_patched_total=int(sum(old_patch_bars.values())), bound_cells_patched=len(c0 & old_patch),
                    bound_cells_not_patched=sorted([dict(E=iso(e), sym=SY[j], n_bound=cell_nb[(e, j)], meta_y4_finite=bool((e in MEI) and np.isfinite(MY[MEI[e], j])),
                                                         in_T1=(e, j) in c1) for (e, j) in c0 - old_patch], key=lambda d: d["E"]),
                    patched_cells_without_bound_bar=len(old_patch - c0),
                    patched_bars_that_are_nan=int(sum(old_patch_bars[c] for c in old_patch & c0) - sum(cell_nb[c] for c in old_patch & c0))),
    scored_anchor_cells_T1=len({c for c in c1 if A_FIRST <= c[0] <= A_LAST}),
    meta_y4_finite_bars=int(y4f.sum()))
log("bound", json.dumps(rec["bound"]["T0_whole_cache"]), json.dumps(rec["bound"]["T1_replay_sampled"]), json.dumps(rec["bound"]["T2_target_exposed"]))

# ---------------- missing bars: in-life NaN runs ----------------
fin = ~np.isnan(R16); has = fin.any(0); ff = np.argmax(fin, 0); lf = T - 1 - np.argmax(fin[::-1], 0)
runs = []
for j in range(NS):
    if not has[j]: continue
    seg = ~fin[ff[j]:lf[j] + 1, j]
    if not seg.any(): continue
    dd = np.diff(np.concatenate([[0], seg.astype(np.int8), [0]])); st = np.nonzero(dd == 1)[0]; en = np.nonzero(dd == -1)[0]
    for x, y in zip(st, en):
        i0 = ff[j] + x; i1 = ff[j] + y - 1; ta, tb = int(TS[i0]), int(TS[i1])
        Es = list(range((ta - 1) // CELL * CELL, (tb - 1) // CELL * CELL + 1, CELL))
        runs.append(dict(sym=SY[j], col=j, row0=int(i0), row1=int(i1), first_ts=ta, last_ts=tb, n_bars=int(y - x), cells=len(Es),
                         in_T1=bool(tb > S_LO and ta <= S_HI), exposed_cells=[iso(e) for e in Es if exposed(e, j)],
                         exposed_bars=int(sum(int(((TS[i0:i1 + 1] > e) & (TS[i0:i1 + 1] <= e + CELL)).sum()) for e in Es if exposed(e, j)))))
runs_T1 = [r for r in runs if r["in_T1"]]; runs_T2 = [r for r in runs_T1 if r["exposed_cells"]]
rec["missing"] = dict(T0_runs=len(runs), T0_bars=int(sum(r["n_bars"] for r in runs)), T1_runs=len(runs_T1), T1_bars=int(sum(r["n_bars"] for r in runs_T1)),
                      T2_runs=len(runs_T2), T2_exposed_bars=int(sum(r["exposed_bars"] for r in runs_T2)),
                      runs=[dict(r, first=iso(r["first_ts"]), last=iso(r["last_ts"])) for r in runs],
                      note="the last NaN of a run is the first bar after the gap (pct_change needs the previous close): the move across the run is absent from the chain")
# dead contracts (after the last finite bar) held by a book: reported only (K6 family, not a clipped / missing-in-life bar)
dead = []
for i, A in enumerate(AX):
    if A < A_FIRST or A > A_LAST: continue
    for j in np.nonzero(HELD[i])[0]:
        if has[j] and TS[lf[j]] < A: dead.append((iso(A), SY[j], iso(TS[lf[j]])))
rec["dead_contract_note"] = dict(n_anchor_symbol=len(dead), examples=dead[:20],
                                 note="target weight on a symbol after its last cache bar: the replay prices it flat; K6 family, out of this fix's scope")
log("missing runs", len(runs), "T1", len(runs_T1), "T2", len(runs_T2), "dead", len(dead))

# ---------------- fetch list ----------------
need = {}
def add(sym, dstr, why): need.setdefault((sym, dstr), set()).add(why)
for (e, j) in c0:
    add(SY[j], day(e - ROW), "bound_cell"); add(SY[j], day(e), "bound_cell")
for r in runs:
    t = (r["first_ts"] - 2 * ROW) // 86400 * 86400
    while t <= r["last_ts"]:
        add(r["sym"], day(t), "nan_run"); t += 86400
fetch = [dict(sym=s, day=dstr, why=sorted(w)) for (s, dstr), w in sorted(need.items())]
os.makedirs(OUT + "/work", exist_ok=True)
json.dump(fetch, open(OUT + "/work/fetch_list.json", "w"), indent=0)
rec["fetch"] = dict(n_symbol_days=len(fetch), n_symbols=len({f["sym"] for f in fetch}), path=OUT + "/work/fetch_list.json", sha256=sha(OUT + "/work/fetch_list.json"))

np.savez(OUT + "/work/census.tmp.npz", b_row=rr.astype(np.int64), b_col=cc.astype(np.int64), b_ts=bts, b_E=bE, b_pos=bpos, b_val16=R16[rr, cc], b_T1=t1, b_T2=t2,
         b_scored=scored, b_y4_finite=y4f, b_old_patched=oldp, symbols=np.array(SY),
         g_col=np.array([r["col"] for r in runs], np.int64), g_row0=np.array([r["row0"] for r in runs], np.int64), g_row1=np.array([r["row1"] for r in runs], np.int64),
         g_T1=np.array([r["in_T1"] for r in runs], bool), g_T2=np.array([bool(r["exposed_cells"]) for r in runs], bool),
         sample_range=np.array([S_LO, S_HI], np.int64))
os.replace(OUT + "/work/census.tmp.npz", OUT + "/work/census.npz")
rec["outputs"] = dict(census=dict(path=OUT + "/work/census.npz", sha256=sha(OUT + "/work/census.npz")))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "RP_CENSUS VERDICT=%s bound_T0=%d T1=%d T2=%d cells_T1=%d anchors_T1=%d nan_runs_T1=%d fetch=%d" % (
    rec["VERDICT"], len(rr), int(t1.sum()), int(t2.sum()), len(c1), len({e for e, _ in c1}), len(runs_T1), len(fetch)))
