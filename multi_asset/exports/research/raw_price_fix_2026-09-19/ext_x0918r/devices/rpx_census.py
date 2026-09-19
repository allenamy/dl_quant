#!/usr/bin/env python3
"""rpx_census.py — R5-02 extension to the x0918r data axis (5m bars to 2026-09-19T00:00Z, last anchor 2026-09-18T20Z), step 1: enumerate.

Base = the restored table of commit 0c0fd45a0 (price_logtable_raw.npy 0b134159…, patch r_prices_raw_patch.npz 984c2892…, built on the holefix2
cache 1d7f459d… to 2026-09-01T00:00Z). New cache = stream D's corrected variant x0918r (08bb2957…, docs/RESULT_data_axis_0919_2026-09-19.md §11).
Nothing existing is modified; everything is written under /workspace/raw_price_fix_2026-09-19/ext_x0918r/.

  P0  prefix of the new cache: ts[:490753] and the symbol axis equal the holefix2 cache; the ret5 channel on those 490,753 rows is compared as
      uint16 bit patterns (NaN sign bits included). Every differing cell is listed (the extension must name each one, or prove there are none).
  S   sample boundaries: the old rule (r_prices.py) with the old last anchor is reproduced and asserted equal to the old table's 63,975 bounds;
      the extended set = the same rule with last anchor 2026-09-18T20Z, funding times from the P2 ledger ∪ the stream-D ledger (74b69e63…),
      capped at the cache's last row (boundaries past 2026-09-19T00:00Z cannot be priced; each one is listed). Old set ⊂ new set is asserted.
  B   bound bars (ret5 == ±float16(0.3)) over the whole new cache; those with ts <= the old last boundary must equal the old census exactly;
      NEW SPAN = ts in (old last boundary 2026-08-31T04:00Z, new last boundary].
  N   in-life NaN runs over the whole new cache, classified against the old census: SAME / CHANGED / NEW; a CHANGED or NEW run touching the
      old span is flagged prefix-affecting.
  F   fetch list: for every new-span bound cell the days of E-5m and E; for every new-span or changed NaN run the day before .. its last day;
      plus a control sample for verification (b): every UTC day with new-span bars x (4 fixed majors + 4 others chosen by sha256(day|symbol)).
T2 (target-exposed) does not exist for the new span: the S2 replay books end at 2026-08-31T00Z. Reported as such, not computed.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_census.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, calendar, collections
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
BASE = "/workspace/raw_price_fix_2026-09-19"; OUT = BASE + "/ext_x0918r"
CACHE_R = ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75")
CACHE_H = ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488")
OLD_PMETA = ("/workspace/replay_r_2026-09-19/work/price_meta.npz", "fc6a381a76e311e69ad3d7d1c79c834c8f2417c5d46c792d06101cfd376a6455")
OLD_CENSUS = (BASE + "/work/census.npz", None)                                       # sha taken from RP_CENSUS.json
OLD_CENSUS_RECEIPT = BASE + "/receipts/RP_CENSUS.json"
LEDGER_P2 = ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad")
LEDGER_AX = ("/workspace/axis_0919/funding/funding_ledger.npz", "74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d")
META_X = ("/workspace/axis_0919/meta/meta_newprod_v4_x0918.npz", "22e990f86babd64a30801992627ee2f175e0c920aa442943629f200f16406d1e")
TGT_XR = ("/workspace/axis_0919/x0918r/dlw_v4raw/data/dlw_targets.npz", "eda429829420e2529b1d7fa438e8044d8ea25ceeeef66448cea1f0854f1b96b5")
SYMS_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
ROW = 300; CELL = 14400; N_OLD = 490753
A_FIRST = calendar.timegm((2022, 6, 30, 0, 0, 0)); A_LAST_OLD = calendar.timegm((2026, 8, 30, 20, 0, 0)); A_LAST_NEW = calendar.timegm((2026, 9, 18, 20, 0, 0))
MAJORS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]; N_OTHER = 4
B16 = np.float16(0.3)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def day(t): return time.strftime("%Y-%m-%d", time.gmtime(int(t)))


rec = dict(device="rpx_census.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env=dict(os.environ), numpy=np.__version__,
           utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1); os.makedirs(OUT + "/receipts", exist_ok=True)
    rp = OUT + "/receipts/RPX_CENSUS.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


RC = json.load(open(OLD_CENSUS_RECEIPT)); check("old_census.PASS", RC.get("VERDICT") == "PASS")
OLD_CENSUS = (RC["outputs"]["census"]["path"], RC["outputs"]["census"]["sha256"])
for nm, (p, s) in (("cache_x0918r", CACHE_R), ("cache_holefix2", CACHE_H), ("old_price_meta", OLD_PMETA), ("old_census", OLD_CENSUS), ("ledger_p2", LEDGER_P2),
                   ("ledger_axis", LEDGER_AX), ("meta_x0918", META_X), ("targets_raw_x0918r", TGT_XR)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
if FAILS: finish(3, "RPX_CENSUS VERDICT=REFUSED")


def stream_ret5(path):
    Z = np.load(path, allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; CH = [str(c) for c in Z["ch"]]
    zf = zipfile.ZipFile(path); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
    shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
    assert shp == (len(TS), len(SY), len(CH)) and not fo and dt == np.float16 and CH[0] == "ret5", (shp, dt, CH)
    R = np.empty((len(TS), len(SY)), np.float16); rowb = len(SY) * len(CH) * 2
    for r0_ in range(0, len(TS), 8192):
        k = min(8192, len(TS) - r0_); buf = fh.read(k * rowb); assert len(buf) == k * rowb
        R[r0_:r0_ + k] = np.frombuffer(buf, np.float16).reshape(k, len(SY), len(CH))[:, :, 0]
    fh.close(); return TS, SY, R


# ---------------- P0: prefix of the new cache ----------------
TS, SY, R16 = stream_ret5(CACHE_R[0]); log("x0918r ret5", R16.shape)
check("cache.symbols_axis", hashlib.sha256("\n".join(SY).encode()).hexdigest() == SYMS_SHA)
check("cache.ts_strict_5m", bool(np.all(np.diff(TS) == ROW)), {"n": len(TS), "last": iso(TS[-1])})
TSh, SYh, Rh = stream_ret5(CACHE_H[0]); log("holefix2 ret5", Rh.shape)
check("P0.ts_prefix_equal", len(TSh) == N_OLD and bool(np.array_equal(TS[:N_OLD], TSh)) and SYh == SY)
dm = R16[:N_OLD].view(np.uint16) != Rh.view(np.uint16); nd = int(dm.sum())
rec["P0_ret5_prefix"] = dict(rows=N_OLD, cells=int(N_OLD * len(SY)), bit_differences=nd,
                             differences=[dict(ts=iso(TS[r]), sym=SY[c], x0918r=float(R16[r, c]), holefix2=float(Rh[r, c]), bits_new=int(R16[r, c].view(np.uint16)), bits_old=int(Rh[r, c].view(np.uint16)))
                                          for r, c in np.argwhere(dm)[:200]])
check("P0.ret5_prefix_bitwise_equal_or_listed", nd == 0 or len(rec["P0_ret5_prefix"]["differences"]) == nd, {"bit_differences": nd})
del Rh, dm

# ---------------- S: sample boundaries ----------------
LZ = np.load(LEDGER_P2[0], allow_pickle=True); ft_p2 = LZ["ft"].astype(np.int64)
LA = np.load(LEDGER_AX[0], allow_pickle=True); ft_ax = LA["ts"].astype(np.int64); check("ledger_axis.symbols", [str(s) for s in LA["symbols"]] == SY)
def bounds(a_last, fts, cap):
    anch = np.arange(A_FIRST, a_last + 1, CELL, dtype=np.int64); H0 = A_FIRST - CELL; H1 = a_last + 2 * CELL
    S = set(range(H0, H1 + 1, 3600)); S |= set((anch + 1500).tolist()); S |= set((anch + 2400).tolist()); S |= set((anch + 3000).tolist())
    for ft in fts:
        sel = (ft > A_FIRST) & (ft <= a_last + CELL); S |= set(((ft[sel] // ROW) * ROW).tolist())
    allb = np.array(sorted(S), np.int64)
    return allb[allb <= cap], allb[allb > cap]
PM = np.load(OLD_PMETA[0], allow_pickle=True); BND_OLD_T = PM["bounds"].astype(np.int64)
b_old, drop_old = bounds(A_LAST_OLD, [ft_p2], 1 << 62)
check("S.old_rule_reproduces_old_bounds", bool(np.array_equal(b_old, BND_OLD_T)) and len(drop_old) == 0, {"n": len(b_old)})
b_new, dropped = bounds(A_LAST_NEW, [ft_p2, ft_ax], int(TS[-1]))
b_newp2, _ = bounds(A_LAST_NEW, [ft_p2], int(TS[-1]))
old_set = set(BND_OLD_T.tolist()); new_set = set(b_new.tolist())
check("S.old_bounds_subset_of_new", old_set <= new_set, {"missing": len(old_set - new_set)})
S_LO, S_HI_OLD, S_HI_NEW = int(BND_OLD_T[0]), int(BND_OLD_T[-1]), int(b_new[-1])
added = np.array(sorted(new_set - old_set), np.int64)
rec["samples"] = dict(n_old=len(BND_OLD_T), n_new=len(b_new), added=len(added), added_at_or_before_old_last=int((added <= S_HI_OLD).sum()),
                      added_by_axis_ledger_only=len(new_set - set(b_newp2.tolist())), first=iso(S_LO), old_last=iso(S_HI_OLD), new_last=iso(S_HI_NEW),
                      dropped_past_cache_end=[iso(t) for t in dropped], added_at_or_before_old_last_list=[iso(t) for t in added[added <= S_HI_OLD]])
log("samples", json.dumps({k: v for k, v in rec["samples"].items() if not isinstance(v, list)}))

# ---------------- B: bound bars ----------------
OC = np.load(OLD_CENSUS[0], allow_pickle=True)
bnd = (R16 == B16) | (R16 == -B16)
check("B.no_value_beyond_bound", float(np.nanmax(np.abs(R16.astype(np.float32)))) == float(B16))
rr, cc = np.nonzero(bnd); o = np.lexsort((rr, cc)); rr = rr[o]; cc = cc[o]; bts = TS[rr]
old_part = rr < N_OLD
check("B.old_rows_equal_old_census", {(int(a), int(b)) for a, b in zip(rr[old_part], cc[old_part])} == {(int(a), int(b)) for a, b in zip(OC["b_row"], OC["b_col"])},
      {"x0918r_old_rows": int(old_part.sum()), "old_census": len(OC["b_row"])})
newspan = (bts > S_HI_OLD) & (bts <= S_HI_NEW)
check("B.no_bound_bar_between_old_rows_end_and_span", int((~old_part & ~newspan).sum()) == 0 and int((old_part & newspan).sum()) == 0,
      {"old_rows_in_new_span": int((old_part & newspan).sum()), "new_rows_outside_span": int((~old_part & ~newspan).sum())})
nr, nc = rr[newspan], cc[newspan]; nts = TS[nr]; nE = (nts - 1) // CELL * CELL; npos = ((nts - nE) // ROW).astype(np.int64)
MX = np.load(META_X[0], allow_pickle=True); MXE = {int(e): i for i, e in enumerate(MX["E_ts"].astype(np.int64))}; MXY = MX["y4"]
TX = np.load(TGT_XR[0], allow_pickle=True); TXE = {int(e): i for i, e in enumerate(TX["E_ts"].astype(np.int64))}; TXY = TX["y4s"]
check("targets.symbols", [str(s) for s in TX["symbols"]] == SY)
mfin = np.array([(int(e) in MXE) and bool(np.isfinite(MXY[MXE[int(e)], j])) for e, j in zip(nE, nc)])
tfin = np.array([(int(e) in TXE) and bool(np.isfinite(TXY[TXE[int(e)], j])) for e, j in zip(nE, nc)])
cells = sorted({(int(e), int(j)) for e, j in zip(nE, nc)}); cnb = collections.Counter((int(e), int(j)) for e, j in zip(nE, nc))
rec["bound_new_span"] = dict(bars=int(newspan.sum()), pos=int((R16[nr, nc] > 0).sum()), neg=int((R16[nr, nc] < 0).sum()), cells=len(cells), anchors=len({e for e, _ in cells}),
                             symbols=len({j for _, j in cells}), cells_by_bound_count={str(k): int(v) for k, v in sorted(collections.Counter(cnb.values()).items())},
                             bars_with_meta_x0918_y4=int(mfin.sum()), bars_with_x0918r_target_y4=int(tfin.sum()),
                             list=[dict(sym=SY[j], ts=iso(t), cache=float(R16[r, j]), E=iso(e), pos=int(p), meta_x0918_y4_finite=bool(m), x0918r_target_y4_finite=bool(tf))
                                   for r, j, t, e, p, m, tf in zip(nr, nc, nts, nE, npos, mfin, tfin)],
                             T2="not defined: the S2 replay books end at 2026-08-31T00Z (no book for the new span)")
rec["bound_whole_cache"] = dict(bars=int(len(rr)), old_rows=int(old_part.sum()), new_rows=int((~old_part).sum()))
log("bound new span", {k: v for k, v in rec["bound_new_span"].items() if k != "list"})

# ---------------- N: in-life NaN runs ----------------
fin = ~np.isnan(R16); has = fin.any(0); ff = np.argmax(fin, 0); lf = len(TS) - 1 - np.argmax(fin[::-1], 0)
old_runs = {(int(c), int(a), int(b)) for c, a, b in zip(OC["g_col"], OC["g_row0"], OC["g_row1"])}
runs = []
for j in range(len(SY)):
    if not has[j]: continue
    seg = ~fin[ff[j]:lf[j] + 1, j]
    if not seg.any(): continue
    dd = np.diff(np.concatenate([[0], seg.astype(np.int8), [0]])); st = np.nonzero(dd == 1)[0]; en = np.nonzero(dd == -1)[0]
    for x, y in zip(st, en):
        i0 = int(ff[j] + x); i1 = int(ff[j] + y - 1); ta, tb = int(TS[i0]), int(TS[i1])
        key = (j, i0, i1)
        if key in old_runs: kind = "SAME"
        elif any(c == j and not (b < i0 or a > i1) for c, a, b in old_runs): kind = "CHANGED"
        else: kind = "NEW"
        runs.append(dict(sym=SY[j], col=j, row0=i0, row1=i1, first=iso(ta), last=iso(tb), n_bars=int(y - x), kind=kind,
                         touches_old_span=bool(ta <= S_HI_OLD and tb > S_LO), touches_new_span=bool(tb > S_HI_OLD and ta <= S_HI_NEW)))
old_listed = {(r["col"], r["row0"], r["row1"]) for r in runs if r["kind"] == "SAME"}
vanished = sorted(old_runs - old_listed)
sel_runs = [r for r in runs if r["kind"] != "SAME" and (r["touches_new_span"] or r["touches_old_span"])]
rec["nan_runs"] = dict(total=len(runs), kinds=dict(collections.Counter(r["kind"] for r in runs)), old_runs_no_longer_present=[dict(sym=SY[c], row0=a, row1=b) for c, a, b in vanished],
                       selected=sel_runs, prefix_affecting=[r for r in sel_runs if r["touches_old_span"]],
                       new_span_runs=[r for r in runs if r["touches_new_span"]])
log("nan runs", rec["nan_runs"]["kinds"], "selected", len(sel_runs), "prefix-affecting", len(rec["nan_runs"]["prefix_affecting"]))

# ---------------- F: fetch list ----------------
need = collections.defaultdict(set)
for (e, j) in cells:
    need[(SY[j], day(e - ROW))].add("bound_cell"); need[(SY[j], day(e))].add("bound_cell")
for r in sel_runs:
    t = (calendar.timegm(time.strptime(r["first"], "%Y-%m-%dT%H:%MZ")) - 2 * ROW) // 86400 * 86400; tb = calendar.timegm(time.strptime(r["last"], "%Y-%m-%dT%H:%MZ"))
    while t <= tb:
        need[(r["sym"], day(t))].add("nan_run"); t += 86400
ctrl_days = sorted({day(t - ROW) for t in TS[(TS > S_HI_OLD) & (TS <= S_HI_NEW)]})
dayidx = (TS - ROW) // 86400
ctrl = []
for dstr in ctrl_days:
    d0 = calendar.timegm(time.strptime(dstr, "%Y-%m-%d")) // 86400
    rows = np.nonzero(dayidx == d0)[0]; nfin = fin[rows].sum(0)
    full = [SY[j] for j in np.nonzero(nfin == len(rows))[0]]
    oth = sorted([s for s in full if s not in MAJORS], key=lambda s: hashlib.sha256(f"{dstr}|{s}".encode()).hexdigest())[:N_OTHER]
    for s in [m for m in MAJORS if m in full] + oth:
        ctrl.append((s, dstr)); need[(s, dstr)].add("control")
        prev = day(calendar.timegm(time.strptime(dstr, "%Y-%m-%d")) - 86400); need[(s, prev)].add("control_prev_day")
fetch = [dict(sym=s, day=d, why=sorted(w)) for (s, d), w in sorted(need.items())]
os.makedirs(OUT + "/work", exist_ok=True)
json.dump(fetch, open(OUT + "/work/fetch_list_x0918r.json", "w"), indent=0)
rec["fetch"] = dict(n_symbol_days=len(fetch), n_symbols=len({f["sym"] for f in fetch}), control_days=ctrl_days, control_pairs=len(ctrl),
                    path=OUT + "/work/fetch_list_x0918r.json", sha256=sha(OUT + "/work/fetch_list_x0918r.json"))

np.savez(OUT + "/work/census_x0918r.tmp.npz", b_row=nr.astype(np.int64), b_col=nc.astype(np.int64), b_ts=nts, b_E=nE, b_pos=npos, b_val16=R16[nr, nc],
         b_meta_x0918_finite=mfin, b_target_x0918r_finite=tfin, symbols=np.array(SY),
         g_col=np.array([r["col"] for r in sel_runs], np.int64), g_row0=np.array([r["row0"] for r in sel_runs], np.int64), g_row1=np.array([r["row1"] for r in sel_runs], np.int64),
         g_old_span=np.array([r["touches_old_span"] for r in sel_runs], bool), g_new_span=np.array([r["touches_new_span"] for r in sel_runs], bool),
         bounds_new=b_new, bounds_old=BND_OLD_T, span=np.array([S_LO, S_HI_OLD, S_HI_NEW], np.int64),
         control_sym=np.array([c[0] for c in ctrl]), control_day=np.array([c[1] for c in ctrl]))
os.replace(OUT + "/work/census_x0918r.tmp.npz", OUT + "/work/census_x0918r.npz")
rec["outputs"] = dict(census=dict(path=OUT + "/work/census_x0918r.npz", sha256=sha(OUT + "/work/census_x0918r.npz")))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "RPX_CENSUS VERDICT=%s prefix_bitdiff=%d bound_new_span=%d cells=%d nan_runs_selected=%d prefix_affecting=%d fetch=%d" % (
    rec["VERDICT"], nd, int(newspan.sum()), len(cells), len(sel_runs), len(rec["nan_runs"]["prefix_affecting"]), len(fetch)))
