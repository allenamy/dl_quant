#!/usr/bin/env python3
"""rp_restore.py — R5-02 step 2b/3/4: recover the ORIGINAL official 5m closes for every bar rp_census.py enumerated, verify, write the patch.

Inputs: the census (work/census.npz, receipt RP_CENSUS PASS), the checksum-verified archives (work/fetch_manifest.json, receipt RP_FETCH
PASS; every archive is re-hashed from the same bytes it is parsed from), the pinned cache / meta / old price table, and the raw_patch.npz the
accounting meta y4 was built with (cross-check only).

Per bound bar (|ret5| == float16(0.3)):  c_now = close of the kline opening ts-300, c_prev = close of the kline opening ts-600
  (cache ts = close time); status by rp_lib.classify: RESTORED (official |r| > 0.3 and the builder math reproduces the cached value),
  NOT_CLIPPED (official |r| <= 0.3, the cached bound is an ordinary float16 rounding), UNAVAILABLE (a close is missing), CONFLICT.
Per bound cell (E, E+4h]: the fixed path = cache log returns with the exact official return on RESTORED bars (rp_lib.apply_patch), and the
  all-official path = log(close_k / close_E) from the 49 official closes. UNAVAILABLE cells get rp_lib.feasible_band bounds instead.
Per in-life NaN run: whether the official archive has the bars (CACHE_HOLE, restorable) or not (VENUE_GAP: no kline printed), and the exact
  move across the run that the cache chain drops.
Verification:
  (a) every restored cell with finite meta y4: (a1) the meta recipe (cache float16 + raw_patch float32 on clipped bars, NaN => 0) reproduces
      meta y4 to <= 1 float32 ulp; (a2) |expm1(fixed path) - y4| / (1 + y4) (exact official returns on the bound bars); (a3) the all-official
      compound close(E+4h)/close(E) - 1 vs y4, against the bound explained by float16 rounding of the cache's unclipped bars + float32 storage.
  (b) control: every finite, unclipped cache bar on every fetched day equals float16(clip(official r, +-0.3)) bitwise; negative control with
      the timestamp shifted by one bar must fail.
  (c) float32(official r) == raw_patch.npz raw32 on every clipped bar both cover.
  (d) the old device's path (r_prices.py L143-150 rule, re-implemented and checked against the old price table at every sample boundary in
      the cell) vs the official path at the replay's sample boundaries (A+25m fills, A+40m stop evaluation, A+50m flatten, hours, fundings).
Writes only under /workspace/raw_price_fix_2026-09-19/: r_prices_raw_patch.npz, receipts/RP_RESTORE.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rp_restore.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, io, math, collections, calendar
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rp_lib as RL

T0 = time.time()
OUT = "/workspace/raw_price_fix_2026-09-19"
CACHE = ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488")
META = ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3")
OLD_PMETA = ("/workspace/replay_r_2026-09-19/work/price_meta.npz", "fc6a381a76e311e69ad3d7d1c79c834c8f2417c5d46c792d06101cfd376a6455")
OLD_LP = ("/workspace/replay_r_2026-09-19/work/price_logtable.npy", "3b588cb058920d57621b3e269a9a4a0f640f4f23ea44fd413bf7abeefd774211")
RAWP = "/workspace/review_scratch/raw_patch.npz"                                  # meta y4's own clipped-bar patch (sha recorded, cross-check)
ROW = 300; CELL = 14400; NB = 48
B16 = np.float16(0.3)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = dict(device="rp_restore.py", self_sha256=sha(os.path.abspath(__file__)), rp_lib_sha256=sha(os.path.join(HERE, "rp_lib.py")), argv=sys.argv,
           env=dict(os.environ), numpy=np.__version__, utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:400] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = OUT + "/receipts/RP_RESTORE.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


# ---------------- gates on the previous steps and pinned inputs ----------------
RC = json.load(open(OUT + "/receipts/RP_CENSUS.json")); RF = json.load(open(OUT + "/receipts/RP_FETCH.json"))
check("census.PASS", RC.get("VERDICT") == "PASS", {"sha256": sha(OUT + "/receipts/RP_CENSUS.json")})
check("fetch.PASS", RF.get("VERDICT") == "PASS", {"sha256": sha(OUT + "/receipts/RP_FETCH.json")})
CEN = RC["outputs"]["census"]; MAN = RF["outputs"]["manifest"]
check("census.npz_sha", sha(CEN["path"]) == CEN["sha256"]); check("manifest_sha", sha(MAN["path"]) == MAN["sha256"])
for nm, (p, s) in (("cache", CACHE), ("meta", META), ("old_price_meta", OLD_PMETA), ("old_price_logtable", OLD_LP)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
rec["inputs"]["raw_patch_meta"] = dict(path=RAWP, sha256=sha(RAWP))
if FAILS: finish(3, "RP_RESTORE VERDICT=REFUSED")

# ---------------- official closes from the verified archives (hash and parse the same captured bytes) ----------------
manifest = json.load(open(MAN["path"]))
CL = collections.defaultdict(dict)          # sym -> {close_ts: close}
arch = []; n_dup = 0; n_dup_conflict = 0; n_ct_bad = 0; n_rows = 0
for m in manifest:
    if m["status"] not in ("OK", "CACHED_VERIFIED"): continue
    body = open(m["path"], "rb").read(); ctxt = open(m["path"] + ".CHECKSUM").read().strip().split()
    name = os.path.basename(m["path"])
    if not (len(ctxt) == 2 and ctxt[1] == name and hashlib.sha256(body).hexdigest() == ctxt[0]):
        check(f"archive.checksum_at_read.{name}", False); continue
    ai = len(arch); arch.append(dict(name=name, kind=m["kind"], sha256=ctxt[0]))
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        txt = z.read(z.namelist()[0]).decode()
    d = CL[m["sym"]]
    for ln in txt.splitlines():
        if not ln or ln[0].isalpha(): continue                               # header line (open_time,...)
        c = ln.split(","); ot = int(c[0]); ctm = int(c[6])
        if ot > 10 ** 14: ot //= 1000; ctm //= 1000                        # microsecond archives, if any
        if ctm != ot + 299999: n_ct_bad += 1
        ts = ot // 1000 + ROW; px = float(c[4]); n_rows += 1
        if ts in d:
            n_dup += 1
            if d[ts] != px: n_dup_conflict += 1
        d[ts] = px
rec["archives"] = dict(n=len(arch), n_daily=sum(a["kind"] == "daily" for a in arch), n_monthly=sum(a["kind"] == "monthly" for a in arch), kline_rows=n_rows,
                       duplicate_bars_daily_vs_monthly=n_dup, duplicate_conflicts=n_dup_conflict, close_time_not_open_plus_299999=n_ct_bad)
check("archives.all_rehashed_ok", not any(c["check"].startswith("archive.checksum_at_read") for c in rec["checks"]))
check("archives.no_duplicate_conflict", n_dup_conflict == 0, {"dups": n_dup, "conflicts": n_dup_conflict})
check("archives.bars_are_5m", n_ct_bad == 0, {"n_bad": n_ct_bad})
log("archives", rec["archives"])
def close(sym, ts): return CL.get(sym, {}).get(int(ts))

# ---------------- cache ret5 ----------------
C = np.load(CEN["path"], allow_pickle=True)
Z = np.load(CACHE[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; NCH = len(Z["ch"])
check("census.symbols", [str(s) for s in C["symbols"]] == SY)
NS = len(SY); T = len(TS); tix = {int(t): i for i, t in enumerate(TS)}
zf = zipfile.ZipFile(CACHE[0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh)); assert shp == (T, NS, NCH)
R16 = np.empty((T, NS), np.float16); rowb = NS * NCH * 2
for r0_ in range(0, T, 8192):
    k = min(8192, T - r0_); R16[r0_:r0_ + k] = np.frombuffer(fh.read(k * rowb), np.float16).reshape(k, NS, NCH)[:, :, 0]
fh.close(); log("ret5 streamed")
sidx = {s: j for j, s in enumerate(SY)}

# ---------------- (b) control: every fetched day, every bar ----------------
days_by_sym = collections.defaultdict(set)
for m in manifest:
    if m["kind"] == "daily" and (m["status"] in ("OK", "CACHED_VERIFIED") or m.get("fallback_monthly") in ("OK", "CACHED_VERIFIED")):
        days_by_sym[m["sym"]].add(m["day"])
cb = collections.Counter(); mism = []; shift_eq = 0; shift_n = 0; hole_fill = collections.Counter()
for sym, dset in sorted(days_by_sym.items()):
    j = sidx[sym]; d = CL[sym]
    for dstr in sorted(dset):
        t0 = calendar.timegm(time.strptime(dstr, "%Y-%m-%d"))
        prev_day_in = time.strftime("%Y-%m-%d", time.gmtime(t0 - 86400)) in dset
        for ts in range(t0 + ROW, t0 + 86400 + ROW, ROW):          # bars whose kline opens inside the day
            i = tix.get(ts)
            if i is None: continue
            if ts == t0 + ROW and not prev_day_in:
                cb["first_bar_prev_day_not_fetched"] += 1; continue   # its previous close sits in a day that was not fetched
            v = R16[i, j]; a = d.get(ts); b = d.get(ts - ROW)
            if np.isnan(v):
                if a is not None and b is not None: cb["cache_nan_official_has"] += 1; hole_fill[(sym, dstr)] += 1
                else: cb["both_missing"] += 1
                continue
            if a is None or b is None:
                cb["cache_finite_official_missing"] += 1; mism.append((sym, iso(ts), float(v), None)); continue
            f = RL.builder_ret16(a, b)
            if abs(float(v)) == float(B16):
                cb["bound_bar"] += 1; continue
            cb["compared"] += 1
            if f == v: cb["equal"] += 1
            else:
                cb["mismatch"] += 1
                if len(mism) < 50: mism.append((sym, iso(ts), float(v), float(f)))
            # negative control: pretend cache ts = kline OPEN time (one bar earlier close pair)
            a2 = d.get(ts - ROW); b2 = d.get(ts - 2 * ROW)
            if a2 is not None and b2 is not None:
                shift_n += 1; shift_eq += int(RL.builder_ret16(a2, b2) == v)
rec["control_b"] = dict(counts=dict(cb), mismatches=mism[:50], shifted_alignment_equal_rate=(shift_eq / shift_n if shift_n else None), shifted_n=shift_n,
                        cache_nan_where_official_has_bars={f"{s}|{d}": n for (s, d), n in sorted(hole_fill.items())})
check("b.unclipped_bitwise_equal", cb["compared"] > 100000 and cb["mismatch"] == 0 and cb["cache_finite_official_missing"] == 0,
      {"compared": cb["compared"], "equal": cb["equal"], "mismatch": cb["mismatch"], "cache_finite_official_missing": cb["cache_finite_official_missing"]})
check("b.negative_control_shift_fails", shift_n > 1000 and shift_eq / shift_n < 0.5, {"rate": shift_eq / max(shift_n, 1)})

# ---------------- bound bars ----------------
b_row = C["b_row"]; b_col = C["b_col"]; b_ts = C["b_ts"]; b_E = C["b_E"]; b_pos = C["b_pos"]; b_T1 = C["b_T1"]; b_T2 = C["b_T2"]
nb = len(b_row); st = np.zeros(nb, np.int8); raw = np.full(nb, np.nan); cnow = np.full(nb, np.nan); cprev = np.full(nb, np.nan)
for k in range(nb):
    sym = SY[int(b_col[k])]; a = close(sym, b_ts[k]); b = close(sym, b_ts[k] - ROW)
    s_, r_ = RL.classify(R16[b_row[k], b_col[k]], a, b); st[k] = s_; raw[k] = r_
    cnow[k] = np.nan if a is None else a; cprev[k] = np.nan if b is None else b
sc = {RL.STATUS_NAME[s]: int((st == s).sum()) for s in (RL.RESTORED, RL.NOT_CLIPPED, RL.UNAVAILABLE, RL.CONFLICT)}
rec["bound_bars"] = dict(all=sc, T1={RL.STATUS_NAME[s]: int(((st == s) & b_T1).sum()) for s in (1, 2, 3, 4)},
                         T2={RL.STATUS_NAME[s]: int(((st == s) & b_T2).sum()) for s in (1, 2, 3, 4)},
                         not_clipped=[dict(sym=SY[int(b_col[k])], ts=iso(b_ts[k]), cache=float(R16[b_row[k], b_col[k]]), official=float(raw[k])) for k in np.nonzero(st == RL.NOT_CLIPPED)[0]],
                         unavailable=[dict(sym=SY[int(b_col[k])], ts=iso(b_ts[k]), T1=bool(b_T1[k]), T2=bool(b_T2[k])) for k in np.nonzero(st == RL.UNAVAILABLE)[0]],
                         conflict=[dict(sym=SY[int(b_col[k])], ts=iso(b_ts[k]), cache=float(R16[b_row[k], b_col[k]]), official=float(raw[k])) for k in np.nonzero(st == RL.CONFLICT)[0]],
                         official_range=[float(np.nanmin(raw)), float(np.nanmax(raw))])
check("bound.no_conflict", sc["CONFLICT"] == 0, sc)
log("bound bars", sc)

# (c) cross-check against the raw_patch the meta y4 used
RP = np.load(RAWP); rp_key = {(int(r), int(c)): float(v) for r, c, v in zip(RP["row"], RP["col"], RP["raw32"])}
check("c.raw_patch_rows_on_this_axis", bool(np.array_equal(TS[RP["row"]], RP["ts"].astype(np.int64))) and [SY[int(c)] for c in RP["col"]] == [str(x) for x in RP["symbol"]])
same = 0; diff = []; only_mine = 0
for k in np.nonzero(st == RL.RESTORED)[0]:
    key = (int(b_row[k]), int(b_col[k]))
    if key not in rp_key: only_mine += 1; continue
    if np.float32(raw[k]) == np.float32(rp_key[key]): same += 1
    else: diff.append((SY[key[1]], iso(b_ts[k]), float(raw[k]), rp_key[key]))
mine_keys = {(int(b_row[k]), int(b_col[k])) for k in np.nonzero(st == RL.RESTORED)[0]}
rec["cross_check_raw_patch"] = dict(n_raw_patch=len(rp_key), restored_here=int((st == RL.RESTORED).sum()), float32_equal=same, differ=diff[:20],
                                    restored_not_in_raw_patch=only_mine, raw_patch_not_restored_here=len(set(rp_key) - mine_keys))
check("c.float32_equals_meta_raw_patch", len(diff) == 0 and same == len(rp_key) and only_mine == 0, {"equal": same, "n_raw_patch": len(rp_key), "differ": len(diff)})

# ---------------- cells ----------------
MZ = np.load(META[0], allow_pickle=True); ME = MZ["E_ts"].astype(np.int64); MY = MZ["y4"]; MEI = {int(e): i for i, e in enumerate(ME)}
PM = np.load(OLD_PMETA[0], allow_pickle=True); BND = PM["bounds"].astype(np.int64); brix = {int(b): i for i, b in enumerate(BND)}
LPO = np.load(OLD_LP[0], mmap_mode="r")
old_patched = {(int(e), int(j)) for e, j in zip(PM["patches"][:, 0], PM["patches"][:, 1])}
cells = sorted({(int(e), int(j)) for e, j in zip(b_E, b_col)})
bk = collections.defaultdict(list)
for k in range(nb): bk[(int(b_E[k]), int(b_col[k]))].append(k)
NC_ = len(cells)
c_E = np.array([c[0] for c in cells], np.int64); c_col = np.array([c[1] for c in cells], np.int64)
c_status = np.zeros(NC_, np.int8); c_nb = np.zeros(NC_, np.int16); c_nnan = np.zeros(NC_, np.int16)
c_y4 = np.full(NC_, np.nan); c_Gfix = np.full(NC_, np.nan); c_Graw = np.full(NC_, np.nan)
c_close = np.full((NC_, NB + 1), np.nan)                   # official closes at E, E+5m, ..., E+4h
c_fix = np.full((NC_, NB + 1), np.nan)                     # fixed cumulative log path (cache float16 + exact official on bound bars)
c_lo = np.full((NC_, NB + 1), np.nan); c_hi = np.full((NC_, NB + 1), np.nan)      # bounded scenario (UNAVAILABLE cells only)
c_T1 = np.zeros(NC_, bool); c_T2 = np.zeros(NC_, bool); c_oldp = np.zeros(NC_, bool)
c_r16 = np.full((NC_, NB), np.nan, np.float16)             # the cache ret5 of the cell's 48 bars
c_old = np.full((NC_, NB + 1), np.nan)                     # the old device's cumulative log path (r_prices.py rule), where computable
c_q16 = np.full(NC_, np.nan)                               # sum |log1p(r16) - official log return| over unclipped + NaN bars (float16 precision budget)
a1_ulps = []; a2_rel = []; a2_bnd = []; a3 = []; d_skipped = []; d_cells_in_samples = 0; d_k0_pos = 0; d_table_n = 0; dev_rows = []; old_signflip_bars = 0; old_bars_checked = 0; oldrule_vs_table = 0.0
OFFS = {"A+25m": 1500, "A+40m": 2400, "A+50m": 3000}
for ci, (E, j) in enumerate(cells):
    ks = bk[(E, j)]; sym = SY[j]; c_nb[ci] = len(ks); c_T1[ci] = bool(b_T1[ks].any()); c_T2[ci] = bool(b_T2[ks].any()); c_oldp[ci] = (E, j) in old_patched
    i0 = tix[E + ROW]; rows = np.arange(i0, i0 + NB); r16 = R16[rows, j]; c_nnan[ci] = int(np.isnan(r16).sum()); c_r16[ci] = r16
    y4 = float(MY[MEI[E], j]) if E in MEI else math.nan; c_y4[ci] = y4
    cl = np.array([close(sym, E + k * ROW) if close(sym, E + k * ROW) is not None else np.nan for k in range(NB + 1)]); c_close[ci] = cl
    pr = b_row[ks] - i0; pst = st[ks]; praw = raw[ks]
    L = RL.base_logs(r16)
    try:
        RL.apply_patch(L, r16, pr, np.zeros(len(pr), np.int64), pst, praw); c_status[ci] = 1
    except RL.UnavailablePath:
        c_status[ci] = 3
        known = RL.base_logs(r16).copy(); sign = np.zeros(NB)
        for p_, s_, r_ in zip(pr, pst, praw):
            if s_ == RL.RESTORED: known[p_] = math.log1p(r_)
            elif s_ != RL.NOT_CLIPPED: known[p_] = np.nan; sign[p_] = np.sign(float(r16[p_]))
        try:
            lo, hi = RL.feasible_band(known, sign, math.log1p(y4) if math.isfinite(y4) else math.nan); c_lo[ci] = lo; c_hi[ci] = hi
        except RL.InfeasibleCell:
            c_status[ci] = 4
        continue
    cum = np.concatenate([[0.0], np.cumsum(L)]); c_fix[ci] = cum; c_Gfix[ci] = math.expm1(cum[-1])
    if np.all(np.isfinite(cl)): c_Graw[ci] = cl[-1] / cl[0] - 1.0
    if math.isfinite(y4):
        # (a1) meta recipe: float32 cache + float32 raw_patch on clipped bars, NaN => 0, sum of log1p in float64, stored float32
        r32 = np.where(np.isnan(r16), 0.0, r16.astype(np.float32)).astype(np.float32)
        for p_ in range(NB):
            kk = (int(rows[p_]), j)
            if kk in rp_key: r32[p_] = np.float32(rp_key[kk])
        y4r = np.float32(math.expm1(float(np.log1p(r32.astype(np.float64)).sum())))
        a1_ulps.append(abs(int(np.float32(y4r).view(np.int32)) - int(np.float32(y4).view(np.int32))))
        a2_rel.append(abs(c_Gfix[ci] - y4) / (1.0 + y4))
        q32_ = float(sum(abs(math.log1p(float(np.float32(r_))) - math.log1p(r_)) for r_, s_ in zip(praw, pst) if s_ == RL.RESTORED))
        a2_bnd.append((abs(c_Gfix[ci] - y4), 0.5 * float(np.spacing(np.float32(abs(y4)))) + (1.0 + y4) * math.expm1(q32_) + 1e-14, sym, iso(E)))
        if math.isfinite(c_Graw[ci]):
            fin_ = np.isfinite(r16) & ~RL.is_bound(r16)
            rawb = np.log(cl[1:] / cl[:-1])
            q16 = float(np.abs(np.log1p(r16[fin_].astype(np.float64)) - rawb[fin_]).sum())
            q32 = float(sum(abs(math.log1p(float(np.float32(r_))) - math.log1p(r_)) for r_, s_ in zip(praw, pst) if s_ == RL.RESTORED))
            qnan = float(np.abs(rawb[np.isnan(r16)]).sum())
            bound_ = (1.0 + y4) * (math.exp(q16 + q32 + qnan) - 1.0) + float(np.spacing(np.float32(abs(y4)))) + 1e-12
            a3.append((abs(c_Graw[ci] - y4), bound_, sym, iso(E)))
    # (d) the old device's rule on this cell (r_prices.py L140-150), checked against the old price table at every sample boundary in the cell,
    # then old and fixed paths vs the official closes on the cell's traded sub-range [k0, 48] (k0 = first official close; 0 unless listing /
    # venue gap). Population closed: a T1 cell whose official closes after k0 are incomplete is counted as skipped (gate: 0).
    Lo = RL.base_logs(r16); comp = math.expm1(Lo.sum())
    if math.isfinite(y4) and abs(comp - y4) > 1e-6:
        bnd_ = np.abs(np.where(np.isnan(r16), 0.0, r16.astype(np.float64))) >= 0.2999; pb = np.nonzero(bnd_ | np.isnan(r16))[0]
        oth = np.setdiff1d(np.arange(NB), pb); Lo[pb] = (math.log1p(y4) - Lo[oth].sum()) / len(pb)
        for p_, s_ in zip(pr, pst):
            old_bars_checked += 1
            if np.sign(Lo[p_]) != np.sign(float(r16[p_])): old_signflip_bars += 1
    ocum = np.concatenate([[0.0], np.cumsum(Lo)]); c_old[ci] = ocum
    fin_c = np.isfinite(cl); k0 = int(np.argmax(fin_c)) if fin_c.any() else -1
    full_k0 = k0 >= 0 and bool(fin_c[k0:].all())
    if full_k0 and k0 == 0:
        _rb = np.log(cl[1:] / cl[:-1]); _f = np.isfinite(r16) & ~RL.is_bound(r16)
        c_q16[ci] = float(np.abs(np.log1p(r16[_f].astype(np.float64)) - _rb[_f]).sum() + np.abs(_rb[np.isnan(r16)]).sum())
    if E in brix:
        d_cells_in_samples += 1; d_k0_pos += int(full_k0 and k0 > 0)
        if not full_k0: d_skipped.append((SY[j], iso(E), bool(c_T1[ci])))
        for bt in range(E + ROW, E + CELL + 1, ROW):
            if bt in brix:
                k_ = (bt - E) // ROW
                tv = float(LPO[brix[bt], j] - LPO[brix[E], j]); oldrule_vs_table = max(oldrule_vs_table, abs(tv - ocum[k_])); d_table_n += 1
                if full_k0 and k_ > k0:
                    lab = next((nm for nm, off in OFFS.items() if bt == E + off), "other"); rel = math.log(cl[k_] / cl[k0])
                    dev_rows.append((ci, lab, k_, math.expm1((ocum[k_] - ocum[k0]) - rel), math.expm1((cum[k_] - cum[k0]) - rel)))
    if ci % 100 == 0: log("cell", ci, "/", NC_)

check("cells.no_infeasible", int((c_status == 4).sum()) == 0, {"n": int((c_status == 4).sum())})
rec["cells"] = dict(n=NC_, status={("EXACT" if s == 1 else RL.STATUS_NAME[s]): int((c_status == s).sum()) for s in (1, 3, 4)}, T1=int(c_T1.sum()), T2=int(c_T2.sum()),
                    with_nan_bars=int((c_nnan > 0).sum()), unavailable=[dict(E=iso(c_E[i]), sym=SY[c_col[i]], y4=float(c_y4[i]),
                                                                            lo_min=float(np.nanmin(c_lo[i])), hi_max=float(np.nanmax(c_hi[i]))) for i in np.nonzero(c_status == 3)[0]])
a1 = np.array(a1_ulps); a2 = np.array(a2_rel)
rec["check_a"] = dict(n_cells_y4_finite=len(a1), a1_meta_recipe_ulp_hist={str(k): int(v) for k, v in zip(*np.unique(a1, return_counts=True))} if len(a1) else {},
                      a2_fixed_vs_meta_max_rel=float(a2.max()) if len(a2) else None, a2_fixed_vs_meta_median_rel=float(np.median(a2)) if len(a2) else None,
                      a2_n_rel_le_1e_9=int((a2 <= 1e-9).sum()), a2_n_rel_le_1e_7=int((a2 <= 1e-7).sum()), a2_n_rel_le_2p5e_7=int((a2 <= 2.5e-7).sum()),
                      a3_n=len(a3), a3_within_explained_bound=int(sum(1 for x in a3 if x[0] <= x[1])), a3_max_abs=float(max(x[0] for x in a3)) if a3 else None,
                      a3_max_ratio_to_bound=float(max(x[0] / x[1] for x in a3)) if a3 else None,
                      a3_worst=[dict(absdiff=x[0], bound=x[1], sym=x[2], E=x[3]) for x in sorted(a3, key=lambda x: -x[0])[:10]],
                      note="meta y4 is float32 (eps 1.19e-7) and built from the float16 cache on the 47 unclipped bars plus float32(raw) on clipped bars, "
                           "so 1e-9 relative is not attainable against it; a1 is the exact reproduction of its recipe, a2/a3 bound the representation gap")
check("a1.meta_recipe_within_1ulp", len(a1) > 0 and int(a1.max()) <= 1, {"max_ulp": int(a1.max()) if len(a1) else None})
rec["check_a"].update(a2_n_within_explained_bound=int(sum(1 for x in a2_bnd if x[0] <= x[1] * (1 + 1e-6))), a2_max_abs=float(max(x[0] for x in a2_bnd)) if a2_bnd else None,
                      a2_max_ratio_to_bound=float(max(x[0] / x[1] for x in a2_bnd)) if a2_bnd else None,
                      a2_worst_rel=[dict(absdiff=x[0], bound=x[1], sym=x[2], E=x[3]) for x in sorted(a2_bnd, key=lambda x: -x[0])[:5]],
                      a2_gate_note="attempt 1 gated a2 at |G - y4| / (1 + y4) <= 2.5e-7 and went RED at 7.33e-7 (KORUUSDT 2026-07-15 08Z, y4 = -0.951: "
                                   "|G - y4| = 3.56e-8 = 0.6 float32 ulp of y4, divided by 1 + y4 = 0.049). Dividing a float32 absolute quantisation by 1 + y4 "
                                   "is the wrong yardstick near y4 = -1; the gate is now the per-cell explained bound 0.5 ulp32(y4) + (1 + y4)(e^q32 - 1), "
                                   "q32 = sum over restored bars of |log1p(float32 raw) - log1p(raw)| (the two representation steps of the meta recipe, which a1 "
                                   "reproduces with 0 ulp). Attempt-1 receipt kept as RP_RESTORE.attempt1_RED.json.")
check("a2.fixed_path_endpoint_within_float32_explained_bound", len(a2_bnd) > 0 and all(x[0] <= x[1] * (1 + 1e-6) for x in a2_bnd),
      {"n": len(a2_bnd), "max_ratio": rec["check_a"]["a2_max_ratio_to_bound"], "max_abs": rec["check_a"]["a2_max_abs"]})
check("a3.all_official_within_explained_bound", len(a3) > 0 and all(x[0] <= x[1] for x in a3), {"n": len(a3)})

# (a4) every EXACT cell that a3 cannot measure (meta y4 NaN: the 5 bound cells the old device never patched; or an official close missing
# at the cell start: listing bar): the fixed path is compared with
# the official closes on the cell's traded sub-range [k0, 48] (k0 = first official close in the cell; listing-day / venue-gap cells), against
# the float16 budget of that sub-range. The population is closed: every EXACT cell without a finite y4 must be measured (no vacuous pass).
a4 = []; a4_pop = [i for i in range(NC_) if c_status[i] == 1 and not (math.isfinite(c_y4[i]) and math.isfinite(c_Graw[i]))]   # every EXACT cell a3 does not measure
for i in a4_pop:
    cl = c_close[i]; fin_c = np.isfinite(cl); k0 = int(np.argmax(fin_c))
    if not fin_c[k0:].all(): continue
    r16 = c_r16[i].astype(np.float64); rb = np.log(cl[k0 + 1:] / cl[k0:-1]); rr = r16[k0:]
    fb = np.isfinite(rr) & ~RL.is_bound(rr)
    q = float(np.abs(np.log1p(rr[fb]) - rb[fb]).sum() + np.abs(rb[np.isnan(rr)]).sum())
    dev = float(np.max(np.abs(np.expm1((c_fix[i][k0:] - c_fix[i][k0]) - np.log(cl[k0:] / cl[k0])))))
    kb = [int(k) for k in np.nonzero(RL.is_bound(r16))[0]]
    a4.append(dict(sym=SY[c_col[i]], E=iso(c_E[i]), k0=k0, meta_y4=float(c_y4[i]), bound_pos=kb, max_rel_dev=dev, bound=math.expm1(q) + 1e-12,
                   bound_bar_cache=[float(r16[k]) for k in kb], bound_bar_official=[float(raw[k_]) for k_ in bk[(int(c_E[i]), int(c_col[i]))]],
                   T1=bool(c_T1[i]), T2=bool(c_T2[i]), old_device_patched=bool(c_oldp[i])))
rec["check_a"]["a4_cells_not_in_a3"] = a4
check("a4.cells_not_in_a3_measured_and_within_float16_bound", len(a4) == len(a4_pop) and len(a4_pop) > 0 and all(x["max_rel_dev"] <= x["bound"] for x in a4),
      {"population": len(a4_pop), "measured": len(a4), "max_dev": max((x["max_rel_dev"] for x in a4), default=None)})
DV = np.array([(r[1] != "other", r[3], r[4]) for r in dev_rows]) if dev_rows else np.zeros((0, 3))
def devstat(lab, mask_cells):
    sel = [r for r in dev_rows if (lab is None or r[1] == lab) and mask_cells[r[0]]]
    if not sel: return dict(n=0)
    o = np.abs(np.array([r[3] for r in sel])); f = np.abs(np.array([r[4] for r in sel]))
    return dict(n=len(sel), old_max=float(o.max()), old_p99=float(np.percentile(o, 99)), old_n_gt_1e_4=int((o > 1e-4).sum()), old_n_gt_1e_2=int((o > 1e-2).sum()),
                fixed_max=float(f.max()), fixed_p99=float(np.percentile(f, 99)), fixed_n_gt_1e_4=int((f > 1e-4).sum()), fixed_n_gt_1e_2=int((f > 1e-2).sum()))
multi = c_nb >= 2
rec["check_d_path_vs_official"] = dict(
    old_rule_reimplementation_vs_old_table_max_abs_log=oldrule_vs_table, old_table_samples_compared=d_table_n,
    cells_with_sample_boundaries=d_cells_in_samples, cells_measured_from_k0_gt_0=d_k0_pos, cells_skipped_incomplete_official=d_skipped,
    old_rule_bound_bars_checked=old_bars_checked, old_rule_bound_bars_sign_flipped=old_signflip_bars,
    all_samples_T1=devstat(None, c_T1), all_samples_T2=devstat(None, c_T2),
    **{f"{lab}_T1": devstat(lab, c_T1) for lab in OFFS}, **{f"{lab}_T2": devstat(lab, c_T2) for lab in OFFS},
    **{f"{lab}_T2_multibound": devstat(lab, c_T2 & multi) for lab in OFFS},
    note="relative price error at the replay's sample boundaries inside the cell, vs the all-official path: old = r_prices.py rule, fixed = this patch "
         "(the fixed residual is the cache's float16 rounding on unclipped bars, the precision of every other bar in the replay)")
d_expect = int(sum(int(np.searchsorted(BND, E + CELL, "right") - np.searchsorted(BND, E, "right")) for E in c_E if int(E) in brix))   # independent count
check("d.old_rule_reimplementation_matches_old_table", d_table_n == d_expect and d_expect > 0 and oldrule_vs_table <= 1e-9,
      {"max_abs_log": oldrule_vs_table, "n": d_table_n, "expected_n_sample_boundaries_in_bound_cells": d_expect})
check("d.no_T1_cell_skipped", not any(x[2] for x in d_skipped), {"skipped": d_skipped})
fx_max = rec["check_d_path_vs_official"]["all_samples_T1"].get("fixed_max", 1.0)
check("d.fixed_path_within_float16_precision", fx_max <= 5e-3, {"fixed_max_rel": fx_max})

# ---------------- in-life NaN runs ----------------
# a run bar is restorable when both official closes exist (the builder's own math, exact float64); otherwise UNAVAILABLE and it stays 0 in the
# chain (no path is invented; the move across an official sub-gap is recorded, never placed on a bar: several are relisting / redenomination
# steps, e.g. BNXUSDT 2023-02-22 119.93 -> 1.585).
g_col = C["g_col"]; g_row0 = C["g_row0"]; g_row1 = C["g_row1"]; g_T1 = C["g_T1"]; g_T2 = C["g_T2"]
gap_rows = []; gp_row = []; gp_col = []; gp_raw = []; gu_row = []; gu_col = []
for g in range(len(g_col)):
    j = int(g_col[g]); sym = SY[j]; r0, r1 = int(g_row0[g]), int(g_row1[g])
    ts_run = [int(t) for t in TS[r0:r1 + 1]]
    comp = [(close(sym, t) is not None and close(sym, t - ROW) is not None) for t in ts_run]
    n_ok = int(sum(comp)); fetched = all(time.strftime("%Y-%m-%d", time.gmtime(t - ROW)) in days_by_sym.get(sym, set()) for t in (ts_run[0], ts_run[-1]))
    kind = ("CACHE_HOLE" if n_ok == len(ts_run) else "VENUE_GAP" if n_ok == 0 else "PARTIAL") if fetched else "NOT_FETCHED"
    subg = []                                                                  # official sub-gaps: maximal stretches of non-computable bars
    for t, ok_ in zip(ts_run, comp):
        if ok_: continue
        if subg and t == subg[-1][1] + ROW: subg[-1][1] = t
        else: subg.append([t, t])
    sub = []
    for a_, b_ in subg:
        cb_ = close(sym, a_ - ROW); ca_ = close(sym, b_)
        # the last close before the stretch that exists: walk back from a_ - ROW
        tb_ = a_ - ROW
        while close(sym, tb_) is None and tb_ > ts_run[0] - 2 * ROW: tb_ -= ROW
        sub.append(dict(first=iso(a_), last=iso(b_), n_bars=(b_ - a_) // ROW + 1, last_close_before=close(sym, tb_), last_close_before_ts=iso(tb_),
                        first_close_after=ca_, move_across=(ca_ / close(sym, tb_) - 1.0) if (ca_ is not None and close(sym, tb_) is not None) else None))
    ret_ok = [close(sym, t) / close(sym, t - ROW) - 1.0 for t, ok_ in zip(ts_run, comp) if ok_]
    exposed_cells = set(RC["missing"]["runs"][g]["exposed_cells"]) if RC["missing"]["runs"][g]["col"] == j and RC["missing"]["runs"][g]["row0"] == r0 else None
    assert exposed_cells is not None, "census run order changed"
    un_exposed = [iso(t) for t, ok_ in zip(ts_run, comp) if (not ok_) and iso((t - 1) // CELL * CELL) in exposed_cells]
    gap_rows.append(dict(sym=sym, first=iso(ts_run[0]), last=iso(ts_run[-1]), n_bars=len(ts_run), T1=bool(g_T1[g]), T2=bool(g_T2[g]), fetched=fetched, kind=kind,
                         restorable_bars=n_ok, unavailable_bars=len(ts_run) - n_ok, official_subgaps=sub, exposed_cells=sorted(exposed_cells),
                         unavailable_bars_in_exposed_cells=len(un_exposed), restored_abs_log_move_sum=float(sum(abs(math.log1p(x)) for x in ret_ok)),
                         restored_nonzero_bars=int(sum(1 for x in ret_ok if x != 0.0))))
    if g_T1[g]:
        for t, ok_ in zip(ts_run, comp):
            if ok_:
                gp_row.append(tix[t]); gp_col.append(j); gp_raw.append(close(sym, t) / close(sym, t - ROW) - 1.0)
            else:
                gu_row.append(tix[t]); gu_col.append(j)
rec["nan_runs"] = dict(runs=gap_rows, kinds=dict(collections.Counter(g["kind"] for g in gap_rows)), restorable_bars_T1=len(gp_row), unavailable_bars_T1=len(gu_row),
                       unavailable_bars_in_T2_exposed_cells=int(sum(g["unavailable_bars_in_exposed_cells"] for g in gap_rows if g["T1"])))
check("nan_runs.all_fetched", all(g["fetched"] for g in gap_rows if g["T1"]))
check("nan_runs.no_unavailable_bar_in_exposed_cell", rec["nan_runs"]["unavailable_bars_in_T2_exposed_cells"] == 0, {"n": rec["nan_runs"]["unavailable_bars_in_T2_exposed_cells"]})
log("nan runs", rec["nan_runs"]["kinds"], "restorable T1", len(gp_row), "unavailable T1", len(gu_row))

# ---------------- real-cell fixture for tests/test_rp_counterexamples.py ----------------
offp = np.log(c_close / c_close[:, :1])
_eo = np.abs(np.expm1(c_old - offp)); e_old = np.where(np.isfinite(_eo).any(1), np.nanmax(np.where(np.isfinite(_eo), _eo, -1.0), axis=1), -1.0)
cand = np.nonzero(c_T2 & (c_nb >= 2) & (c_status == 1) & (e_old > 0))[0]
pick = list(cand[np.argsort(-e_old[cand])][:6])
mixed = [i for i in cand if len({int(np.sign(float(v))) for v in c_r16[i][RL.is_bound(c_r16[i])]}) == 2 and i not in pick]
pick += sorted(mixed, key=lambda i: -e_old[i])[:2]
solv = [i for i in range(NC_) if SY[c_col[i]] == "SOLVUSDT" and iso(c_E[i]) == "2025-10-10T20:00Z" and i not in pick]
pick += solv
fx = dict(source="rp_restore.py from r_prices_raw_patch.npz inputs", device_sha256=rec["self_sha256"], cells=[])
for i in pick:
    bpos = np.nonzero(RL.is_bound(c_r16[i]))[0]
    fx["cells"].append(dict(sym=SY[c_col[i]], E=iso(c_E[i]), n_bound=int(c_nb[i]), T2=bool(c_T2[i]),
                            cache16=[None if np.isnan(v) else float(v) for v in c_r16[i]], official_closes=[float(v) for v in c_close[i]],
                            old_logpath=[float(v) for v in c_old[i]], meta_y4=float(c_y4[i]),
                            patch_status=[RL.STATUS_NAME[int(st[k])] for k in sorted(bk[(int(c_E[i]), int(c_col[i]))], key=lambda k: b_pos[k])],
                            float16_bound=float(math.expm1(c_q16[i]) + 1e-12), old_max_rel_dev=float(e_old[i])))
json.dump(fx, open(OUT + "/work/fixture_real_cells.json", "w"), indent=0)
rec["fixture"] = dict(path=OUT + "/work/fixture_real_cells.json", sha256=sha(OUT + "/work/fixture_real_cells.json"), cells=[(c["sym"], c["E"], c["n_bound"], round(c["old_max_rel_dev"], 4)) for c in fx["cells"]])
rec["old_path_worst_cells_T2"] = [dict(sym=SY[c_col[i]], E=iso(c_E[i]), n_bound=int(c_nb[i]), old_max_rel_dev_any_boundary=float(e_old[i])) for i in cand[np.argsort(-e_old[cand])][:25]]

# ---------------- write the patch ----------------
PATCH = OUT + "/r_prices_raw_patch.npz"
np.savez_compressed(PATCH + ".tmp.npz",
    # bound bars (one row per cache bar at +-float16(0.3)); status codes rp_lib: 1 RESTORED, 2 NOT_CLIPPED, 3 UNAVAILABLE, 4 CONFLICT
    row=b_row.astype(np.int64), col=b_col.astype(np.int64), ts=b_ts.astype(np.int64), E=b_E.astype(np.int64), pos=b_pos.astype(np.int64),
    cache16=R16[b_row, b_col], status=st, raw=raw, close_now=cnow, close_prev=cprev, T1=b_T1, T2=b_T2,
    # cells (E, E+4h] containing >= 1 bound bar; cell status 1 EXACT, 3 UNAVAILABLE (then lo/hi hold the bounded scenario)
    cell_E=c_E, cell_col=c_col, cell_status=c_status, cell_n_bound=c_nb, cell_n_nan=c_nnan, cell_y4_meta=c_y4, cell_G_fixed=c_Gfix, cell_G_official=c_Graw,
    cell_close_official=c_close, cell_logpath_fixed=c_fix, cell_logpath_old=c_old, cell_cache16=c_r16, cell_logpath_lo=c_lo, cell_logpath_hi=c_hi, cell_T1=c_T1, cell_T2=c_T2, cell_old_patched=c_oldp,
    # in-life NaN bars inside the sampled range whose official return is computable (both closes exist): exact per-bar official returns
    gap_row=np.array(gp_row, np.int64), gap_col=np.array(gp_col, np.int64), gap_raw=np.array(gp_raw, np.float64),
    # in-life NaN bars inside the sampled range with no official return (venue gaps / relisting steps): left 0, listed so a consumer can refuse them
    gap_unavail_row=np.array(gu_row, np.int64), gap_unavail_col=np.array(gu_col, np.int64),
    symbols=np.array(SY), archives_name=np.array([a["name"] for a in arch]), archives_sha256=np.array([a["sha256"] for a in arch]),
    meta_json=np.array(json.dumps(dict(device="rp_restore.py", self_sha256=rec["self_sha256"], rp_lib_sha256=rec["rp_lib_sha256"], inputs=rec["inputs"],
                                       census_sha256=CEN["sha256"], manifest_sha256=MAN["sha256"], cache_ts_convention="close time = kline open + 300 s",
                                       ret5_convention="close_t / close_{t-5m} - 1, clip +-0.3, float16"))))
os.replace(PATCH + ".tmp.npz", PATCH)
rec["outputs"] = dict(patch=dict(path=PATCH, sha256=sha(PATCH), bytes=os.path.getsize(PATCH)))
rec["VERDICT"] = "PASS" if not FAILS else "RED"
finish(0 if not FAILS else 3, "RP_RESTORE VERDICT=%s bars=%s cells=%s a2_max_rel=%.2e b_compared=%d b_mismatch=%d patch_sha256=%s" % (
    rec["VERDICT"], json.dumps(sc), json.dumps(rec["cells"]["status"]), rec["check_a"]["a2_fixed_vs_meta_max_rel"] or -1, cb["compared"], cb["mismatch"], rec["outputs"]["patch"]["sha256"]))
