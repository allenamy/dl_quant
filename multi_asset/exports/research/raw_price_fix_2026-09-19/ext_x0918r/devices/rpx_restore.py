#!/usr/bin/env python3
"""rpx_restore.py — R5-02 extension (x0918r axis) step 3: official 5m closes for every bar rpx_census.py enumerated in the NEW SPAN
(2026-08-31T04:00Z, 2026-09-19T00:00Z], verification, and the extension patch. Same rules and the same functions (rp_lib.py f802036f…, imported
from the base device directory and sha-pinned) as rp_restore.py; nothing of the base run is modified.

Per bound bar: rp_lib.classify (RESTORED / NOT_CLIPPED / UNAVAILABLE / CONFLICT) from the checksum-verified archives, re-hashed from the bytes parsed.
Per bound cell: fixed path (cache float16 + exact official return on RESTORED bars, rp_lib.apply_patch) and all-official path (49 closes).
NaN runs: the census found no new or changed in-life NaN run (all 15 identical to the base census) -> nothing to restore; asserted from the
census receipt (closed population), not assumed.
Verification (populations closed; measured counts must equal population counts):
  (a) against the x0918 accounting meta (meta_newprod_v4_x0918.npz 22e990f8…; the x0918r meta is PENDING in stream D's chain — see
      docs/RESULT_data_axis_0919_2026-09-19.md §11.7): a1 meta recipe (cache f16 + x0918r raw_patch f32, NaN => 0) reproduces meta y4 (ulp);
      a2 fixed path endpoint within the float32 explained bound; a3 all-official endpoint within the float16 + float32 explained bound; a4 every
      cell a3 cannot measure. Supplementary a5: the x0918r RAW DL targets (dlw_v4raw eda42982…, the y4 source of the meta) at the same cells.
  (b) every finite unclipped cache bar on every fetched day == float16(clip(official r, +-0.3)) bitwise; reported for the new span and for the
      whole fetched set; negative control with the timestamps shifted by one bar.
  (c) float32(official r) == x0918r raw_patch.npz raw32 on every new-span clipped bar, and both sides cover the same bars.
  (d') counterfactual: what the base-device rule (r_prices.py L143-150, equal log shares) would have produced on these cells, vs official, at
      every 5m boundary and at A+25m / A+40m / A+50m.
Writes only under /workspace/raw_price_fix_2026-09-19/ext_x0918r/: r_prices_raw_patch_x0918r_ext.npz, work/fixture_real_cells_x0918r.json,
receipts/RPX_RESTORE.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_restore.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, zipfile, io, math, collections, calendar
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
CACHE_R = ("/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz", "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75")
META_X = ("/workspace/axis_0919/meta/meta_newprod_v4_x0918.npz", "22e990f86babd64a30801992627ee2f175e0c920aa442943629f200f16406d1e")
TGT_XR = ("/workspace/axis_0919/x0918r/dlw_v4raw/data/dlw_targets.npz", "eda429829420e2529b1d7fa438e8044d8ea25ceeeef66448cea1f0854f1b96b5")
RAWP_XR = ("/workspace/axis_0919/x0918r/data/raw_patch.npz", "0a4cfb5988ae8679a93c45a3649942f49ad2b7fd749792bb22b266c2989b0183")
BASE_PATCH = (BASE + "/r_prices_raw_patch.npz", "984c28923838501758fe52d1ea7d0cd92fc7fc26c4869058b112bb43670343b2")
ROW = 300; CELL = 14400; NB = 48; N_OLD = 490753
OFFS = {"A+25m": 1500, "A+40m": 2400, "A+50m": 3000}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = dict(device="rpx_restore.py", self_sha256=sha(os.path.abspath(__file__)), rp_lib=dict(path=RPLIB[0], sha256=sha(RPLIB[0])), argv=sys.argv,
           env=dict(os.environ), numpy=np.__version__, utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={}, checks=[])
FAILS = []
def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:400] if detail is not None else "")
    if not ok: FAILS.append(name)
def finish(code, line):
    rec["failed"] = FAILS; rec["runtime_s"] = round(time.time() - T0, 1)
    rp = OUT + "/receipts/RPX_RESTORE.json"; json.dump(rec, open(rp + ".tmp", "w"), indent=1, default=float); os.replace(rp + ".tmp", rp)
    print(line + " receipt_sha256=" + sha(rp), flush=True); sys.exit(code)


check("rp_lib.sha", rec["rp_lib"]["sha256"] == RPLIB[1], {"got": rec["rp_lib"]["sha256"][:16]})
RC = json.load(open(OUT + "/receipts/RPX_CENSUS.json")); RF = json.load(open(OUT + "/receipts/RPX_FETCH.json"))
check("census.PASS", RC.get("VERDICT") == "PASS", {"sha256": sha(OUT + "/receipts/RPX_CENSUS.json")})
check("fetch.PASS", RF.get("VERDICT") == "PASS", {"sha256": sha(OUT + "/receipts/RPX_FETCH.json")})
CEN = RC["outputs"]["census"]; MAN = RF["outputs"]["manifest"]
check("census.npz_sha", sha(CEN["path"]) == CEN["sha256"]); check("manifest_sha", sha(MAN["path"]) == MAN["sha256"])
for nm, (p, s) in (("cache_x0918r", CACHE_R), ("meta_x0918", META_X), ("targets_raw_x0918r", TGT_XR), ("raw_patch_x0918r", RAWP_XR), ("base_patch", BASE_PATCH)):
    got = sha(p); rec["inputs"][nm] = dict(path=p, sha256=got); check(f"input_sha.{nm}", got == s, {"expected": s[:16], "got": got[:16]})
rec["meta_used_for_a"] = "x0918 meta_newprod_v4_x0918.npz (22e990f8…): the x0918r accounting meta is PENDING in stream D's chain (RESULT_data_axis_0919 §11.7)"
if FAILS: finish(3, "RPX_RESTORE VERDICT=REFUSED")

# ---------------- official closes (hash and parse the same captured bytes) ----------------
manifest = json.load(open(MAN["path"]))
CL = collections.defaultdict(dict); arch = []; n_dup = n_dup_conflict = n_ct_bad = n_rows = 0
for m in manifest:
    if m["status"] not in ("OK", "CACHED_VERIFIED"): continue
    body = open(m["path"], "rb").read(); ctxt = open(m["path"] + ".CHECKSUM").read().strip().split(); name = os.path.basename(m["path"])
    if not (len(ctxt) == 2 and ctxt[1] == name and hashlib.sha256(body).hexdigest() == ctxt[0]):
        check(f"archive.checksum_at_read.{name}", False); continue
    arch.append(dict(name=name, kind=m["kind"], sha256=ctxt[0]))
    with zipfile.ZipFile(io.BytesIO(body)) as z: txt = z.read(z.namelist()[0]).decode()
    d = CL[m["sym"]]
    for ln in txt.splitlines():
        if not ln or ln[0].isalpha(): continue
        c = ln.split(","); ot = int(c[0]); ctm = int(c[6])
        if ot > 10 ** 14: ot //= 1000; ctm //= 1000
        if ctm != ot + 299999: n_ct_bad += 1
        ts = ot // 1000 + ROW; px = float(c[4]); n_rows += 1
        if ts in d:
            n_dup += 1
            if d[ts] != px: n_dup_conflict += 1
        d[ts] = px
rec["archives"] = dict(n=len(arch), n_daily=sum(a["kind"] == "daily" for a in arch), n_monthly=sum(a["kind"] == "monthly" for a in arch), kline_rows=n_rows,
                       duplicate_bars=n_dup, duplicate_conflicts=n_dup_conflict, close_time_not_open_plus_299999=n_ct_bad)
check("archives.all_rehashed_ok", not any(c["check"].startswith("archive.checksum_at_read") for c in rec["checks"]) and len(arch) > 0, {"n": len(arch)})
check("archives.no_duplicate_conflict", n_dup_conflict == 0, {"dups": n_dup})
check("archives.bars_are_5m", n_ct_bad == 0)
def close(sym, ts): return CL.get(sym, {}).get(int(ts))

# ---------------- cache ret5 ----------------
C = np.load(CEN["path"], allow_pickle=True)
Z = np.load(CACHE_R[0], allow_pickle=True); TS = Z["ts"].astype(np.int64); SY = [str(s) for s in Z["symbols"]]; NCH = len(Z["ch"])
check("census.symbols", [str(s) for s in C["symbols"]] == SY)
NS = len(SY); T = len(TS); tix = {int(t): i for i, t in enumerate(TS)}
zf = zipfile.ZipFile(CACHE_R[0]); fh = zf.open("data.npy"); ver = np.lib.format.read_magic(fh)
shp, fo, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh)); assert shp == (T, NS, NCH)
R16 = np.empty((T, NS), np.float16); rowb = NS * NCH * 2
for r0_ in range(0, T, 8192):
    k = min(8192, T - r0_); R16[r0_:r0_ + k] = np.frombuffer(fh.read(k * rowb), np.float16).reshape(k, NS, NCH)[:, :, 0]
fh.close(); log("ret5 streamed", R16.shape)
sidx = {s: j for j, s in enumerate(SY)}
S_LO, S_HI_OLD, S_HI_NEW = [int(x) for x in C["span"]]

# ---------------- (b) control on every fetched day ----------------
days_by_sym = collections.defaultdict(set)
for m in manifest:
    if m["kind"] == "daily" and (m["status"] in ("OK", "CACHED_VERIFIED") or m.get("fallback_monthly") in ("OK", "CACHED_VERIFIED")):
        days_by_sym[m["sym"]].add(m["day"])
cb = collections.Counter(); cbn = collections.Counter(); per_day = collections.defaultdict(collections.Counter); mism = []; shift_eq = shift_n = 0
for sym, dset in sorted(days_by_sym.items()):
    j = sidx[sym]; d = CL[sym]
    for dstr in sorted(dset):
        t0 = calendar.timegm(time.strptime(dstr, "%Y-%m-%d")); prev_in = time.strftime("%Y-%m-%d", time.gmtime(t0 - 86400)) in dset
        for ts in range(t0 + ROW, t0 + 86400 + ROW, ROW):
            i = tix.get(ts)
            if i is None: continue
            if ts == t0 + ROW and not prev_in: cb["first_bar_prev_day_not_fetched"] += 1; continue
            v = R16[i, j]; a = d.get(ts); b = d.get(ts - ROW); ns = ts > S_HI_OLD
            if np.isnan(v):
                cb["cache_nan_official_has" if (a is not None and b is not None) else "both_missing"] += 1; continue
            if a is None or b is None:
                cb["cache_finite_official_missing"] += 1; mism.append((sym, iso(ts), float(v), None)); continue
            if abs(float(v)) == RL.BOUND16: cb["bound_bar"] += 1; continue
            f = RL.builder_ret16(a, b); eq = bool(f == v)
            cb["compared"] += 1; cb["equal"] += int(eq); per_day[dstr]["compared"] += 1; per_day[dstr]["equal"] += int(eq)
            if ns: cbn["compared"] += 1; cbn["equal"] += int(eq)
            if not eq:
                cb["mismatch"] += 1
                if len(mism) < 50: mism.append((sym, iso(ts), float(v), float(f)))
            a2 = d.get(ts - ROW); b2 = d.get(ts - 2 * ROW)
            if a2 is not None and b2 is not None: shift_n += 1; shift_eq += int(RL.builder_ret16(a2, b2) == v)
ctrl_days = [str(x) for x in RC["fetch"]["control_days"]]
rec["control_b"] = dict(counts=dict(cb), new_span=dict(cbn), per_control_day={dd: dict(per_day[dd]) for dd in ctrl_days}, mismatches=mism[:50],
                        shifted_alignment_equal_rate=(shift_eq / shift_n if shift_n else None), shifted_n=shift_n)
check("b.unclipped_bitwise_equal", cb["compared"] > 10000 and cb["mismatch"] == 0 and cb["cache_finite_official_missing"] == 0 and cb["cache_nan_official_has"] == 0,
      {"compared": cb["compared"], "mismatch": cb["mismatch"], "cache_finite_official_missing": cb["cache_finite_official_missing"], "cache_nan_official_has": cb["cache_nan_official_has"]})
check("b.every_control_day_measured", all(per_day[dd]["compared"] >= 8 * 280 for dd in ctrl_days), {dd: per_day[dd]["compared"] for dd in ctrl_days})
check("b.new_span_measured_and_equal", cbn["compared"] > 10000 and cbn["equal"] == cbn["compared"], dict(cbn))
check("b.negative_control_shift_fails", shift_n > 1000 and shift_eq / shift_n < 0.5, {"rate": shift_eq / max(shift_n, 1)})

# ---------------- bound bars (new span) ----------------
b_row = C["b_row"]; b_col = C["b_col"]; b_ts = C["b_ts"]; b_E = C["b_E"]; b_pos = C["b_pos"]; nb = len(b_row)
check("bound.population_equals_census", nb == RC["bound_new_span"]["bars"] and nb > 0, {"n": nb})
st = np.zeros(nb, np.int8); raw = np.full(nb, np.nan); cnow = np.full(nb, np.nan); cprev = np.full(nb, np.nan)
for k in range(nb):
    sym = SY[int(b_col[k])]; a = close(sym, b_ts[k]); b = close(sym, b_ts[k] - ROW)
    s_, r_ = RL.classify(R16[b_row[k], b_col[k]], a, b); st[k] = s_; raw[k] = r_
    cnow[k] = np.nan if a is None else a; cprev[k] = np.nan if b is None else b
sc = {RL.STATUS_NAME[s]: int((st == s).sum()) for s in (RL.RESTORED, RL.NOT_CLIPPED, RL.UNAVAILABLE, RL.CONFLICT)}
rec["bound_bars"] = dict(counts=sc, list=[dict(sym=SY[int(b_col[k])], ts=iso(b_ts[k]), cache=float(R16[b_row[k], b_col[k]]), status=RL.STATUS_NAME[int(st[k])],
                                                 official=float(raw[k]), close_prev=float(cprev[k]), close_now=float(cnow[k])) for k in range(nb)])
check("bound.no_conflict", sc["CONFLICT"] == 0, sc)
log("bound bars", sc)

# (c) cross-check against the x0918r raw_patch
RP = np.load(RAWP_XR[0]); check("c.raw_patch_rows_on_this_axis", bool(np.array_equal(TS[RP["row"]], RP["ts"].astype(np.int64))) and [SY[int(c)] for c in RP["col"]] == [str(x) for x in RP["symbol"]])
rp_new = {(int(r), int(c)): float(v) for r, c, v in zip(RP["row"], RP["col"], RP["raw32"]) if int(r) >= N_OLD}
mine = {(int(b_row[k]), int(b_col[k])): float(raw[k]) for k in range(nb) if st[k] == RL.RESTORED}
eqc = sum(1 for kk, v in mine.items() if kk in rp_new and np.float32(v) == np.float32(rp_new[kk]))
rec["cross_check_raw_patch_x0918r"] = dict(raw_patch_new_rows=len(rp_new), restored_here=len(mine), float32_equal=eqc,
                                           only_here=len(set(mine) - set(rp_new)), only_raw_patch=len(set(rp_new) - set(mine)))
check("c.float32_equals_x0918r_raw_patch", eqc == len(mine) == len(rp_new), rec["cross_check_raw_patch_x0918r"])
BP = np.load(BASE_PATCH[0], allow_pickle=True)
check("c.no_overlap_with_base_patch", not ({(int(r), int(c)) for r, c in zip(BP["row"], BP["col"])} & {(int(r), int(c)) for r, c in zip(b_row, b_col)}))

# ---------------- cells ----------------
MX = np.load(META_X[0], allow_pickle=True); MXE = {int(e): i for i, e in enumerate(MX["E_ts"].astype(np.int64))}; MXY = MX["y4"]
TX = np.load(TGT_XR[0], allow_pickle=True); TXE = {int(e): i for i, e in enumerate(TX["E_ts"].astype(np.int64))}; TXY = TX["y4s"]
rp_all = {(int(r), int(c)): float(v) for r, c, v in zip(RP["row"], RP["col"], RP["raw32"])}
cells = sorted({(int(e), int(j)) for e, j in zip(b_E, b_col)}); bk = collections.defaultdict(list)
for k in range(nb): bk[(int(b_E[k]), int(b_col[k]))].append(k)
NC_ = len(cells)
c_E = np.array([c[0] for c in cells], np.int64); c_col = np.array([c[1] for c in cells], np.int64)
c_status = np.zeros(NC_, np.int8); c_nb = np.zeros(NC_, np.int16); c_nnan = np.zeros(NC_, np.int16); c_y4 = np.full(NC_, np.nan); c_y4t = np.full(NC_, np.nan)
c_Gfix = np.full(NC_, np.nan); c_Graw = np.full(NC_, np.nan); c_close = np.full((NC_, NB + 1), np.nan); c_fix = np.full((NC_, NB + 1), np.nan)
c_old = np.full((NC_, NB + 1), np.nan); c_r16 = np.full((NC_, NB), np.nan, np.float16); c_q16 = np.full(NC_, np.nan)
c_lo = np.full((NC_, NB + 1), np.nan); c_hi = np.full((NC_, NB + 1), np.nan)
a1 = []; a2 = []; a3 = []; a5 = []; dev_rows = []
for ci, (E, j) in enumerate(cells):
    ks = bk[(E, j)]; sym = SY[j]; c_nb[ci] = len(ks)
    i0 = tix[E + ROW]; rows = np.arange(i0, i0 + NB); r16 = R16[rows, j]; c_r16[ci] = r16; c_nnan[ci] = int(np.isnan(r16).sum())
    y4 = float(MXY[MXE[E], j]) if E in MXE else math.nan; c_y4[ci] = y4
    c_y4t[ci] = float(TXY[TXE[E], j]) if E in TXE else math.nan
    cl = np.array([np.nan if close(sym, E + k * ROW) is None else close(sym, E + k * ROW) for k in range(NB + 1)]); c_close[ci] = cl
    pr = b_row[ks] - i0; pst = st[ks]; praw = raw[ks]
    L = RL.base_logs(r16)
    try:
        RL.apply_patch(L, r16, pr, np.zeros(len(pr), np.int64), pst, praw); c_status[ci] = 1
    except RL.UnavailablePath:
        c_status[ci] = 3; known = RL.base_logs(r16).copy(); sign = np.zeros(NB)
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
    _f = np.isfinite(r16) & ~RL.is_bound(r16)
    if np.all(np.isfinite(cl)):
        _rb = np.log(cl[1:] / cl[:-1]); c_q16[ci] = float(np.abs(np.log1p(r16[_f].astype(np.float64)) - _rb[_f]).sum() + np.abs(_rb[np.isnan(r16)]).sum())
    if math.isfinite(y4):
        r32 = np.where(np.isnan(r16), 0.0, r16.astype(np.float32)).astype(np.float32)
        for p_ in range(NB):
            kk = (int(rows[p_]), j)
            if kk in rp_all: r32[p_] = np.float32(rp_all[kk])
        y4r = np.float32(math.expm1(float(np.log1p(r32.astype(np.float64)).sum())))
        a1.append(abs(int(np.float32(y4r).view(np.int32)) - int(np.float32(y4).view(np.int32))))
        q32 = float(sum(abs(math.log1p(float(np.float32(r_))) - math.log1p(r_)) for r_, s_ in zip(praw, pst) if s_ == RL.RESTORED))
        a2.append(dict(sym=sym, E=iso(E), absdiff=abs(c_Gfix[ci] - y4), bound=0.5 * float(np.spacing(np.float32(abs(y4)))) + (1.0 + y4) * math.expm1(q32) + 1e-14))
        if math.isfinite(c_Graw[ci]):
            bnd3 = (1.0 + y4) * (math.exp(c_q16[ci] + q32) - 1.0) + float(np.spacing(np.float32(abs(y4)))) + 1e-12
            a3.append(dict(sym=sym, E=iso(E), absdiff=abs(c_Graw[ci] - y4), bound=bnd3))
        a5.append(dict(sym=sym, E=iso(E), meta_y4=y4, target_y4s=c_y4t[ci], bitwise_equal=bool(np.float32(y4).view(np.int32) == np.float32(c_y4t[ci]).view(np.int32))))
    # (d') the base-device rule on this cell (counterfactual: the base device never saw the new span)
    Lo = RL.base_logs(r16)
    if math.isfinite(y4) and abs(math.expm1(Lo.sum()) - y4) > 1e-6:
        pb = np.nonzero((np.abs(np.where(np.isnan(r16), 0.0, r16.astype(np.float64))) >= 0.2999) | np.isnan(r16))[0]
        oth = np.setdiff1d(np.arange(NB), pb); Lo[pb] = (math.log1p(y4) - Lo[oth].sum()) / len(pb)
    ocum = np.concatenate([[0.0], np.cumsum(Lo)]); c_old[ci] = ocum
    if np.all(np.isfinite(cl)):
        rcum = np.log(cl / cl[0])
        for k_ in range(1, NB + 1):
            lab = next((nm for nm, off in OFFS.items() if k_ * ROW == off), "other")
            dev_rows.append((ci, lab, k_, math.expm1(ocum[k_] - rcum[k_]), math.expm1(cum[k_] - rcum[k_])))
check("cells.no_infeasible_or_unavailable", int((c_status != 1).sum()) == 0, {"status": {str(s): int((c_status == s).sum()) for s in (1, 3, 4)}})
a3_pop = [i for i in range(NC_) if c_status[i] == 1 and math.isfinite(c_y4[i]) and math.isfinite(c_Graw[i])]
a4_pop = [i for i in range(NC_) if c_status[i] == 1 and i not in a3_pop]
a4 = []
for i in a4_pop:
    cl = c_close[i]; fin_c = np.isfinite(cl); k0 = int(np.argmax(fin_c)) if fin_c.any() else -1
    if k0 < 0 or not fin_c[k0:].all(): continue
    r16 = c_r16[i].astype(np.float64); rb = np.log(cl[k0 + 1:] / cl[k0:-1]); rr_ = r16[k0:]; fb = np.isfinite(rr_) & ~RL.is_bound(rr_)
    q = float(np.abs(np.log1p(rr_[fb]) - rb[fb]).sum() + np.abs(rb[np.isnan(rr_)]).sum())
    a4.append(dict(sym=SY[c_col[i]], E=iso(c_E[i]), k0=k0, max_rel_dev=float(np.max(np.abs(np.expm1((c_fix[i][k0:] - c_fix[i][k0]) - np.log(cl[k0:] / cl[k0]))))), bound=math.expm1(q) + 1e-12))
rec["check_a"] = dict(meta="x0918 (x0918r meta PENDING)", cells=NC_, a1_meta_recipe_ulp=a1, a2=a2, a3=a3, a4=a4, a5_targets_x0918r=a5,
                      note="meta y4 is float32 and built from float16 cache + float32 raw: 1e-9 relative is not attainable against it (see base RESULT §3)")
check("a1.meta_recipe_within_1ulp", len(a1) == NC_ and max(a1) <= 1, {"n": len(a1), "ulps": a1})
check("a2.fixed_endpoint_within_float32_bound", len(a2) == NC_ and all(x["absdiff"] <= x["bound"] * (1 + 1e-6) for x in a2), {"max_abs": max((x["absdiff"] for x in a2), default=None)})
check("a3.official_endpoint_within_explained_bound", len(a3) == len(a3_pop) and all(x["absdiff"] <= x["bound"] for x in a3), {"n": len(a3), "max_abs": max((x["absdiff"] for x in a3), default=None)})
check("a4.remaining_cells_measured", len(a4) == len(a4_pop) and all(x["max_rel_dev"] <= x["bound"] for x in a4), {"population": len(a4_pop), "measured": len(a4)})
check("a5.meta_y4_equals_x0918r_target_y4s", len(a5) == NC_ and all(x["bitwise_equal"] for x in a5), {"n": len(a5)})
def devstat(lab):
    sel = [r for r in dev_rows if lab is None or r[1] == lab]
    if not sel: return dict(n=0)
    o = np.abs([r[3] for r in sel]); f = np.abs([r[4] for r in sel])
    return dict(n=len(sel), old_rule_max=float(o.max()), old_rule_n_gt_1e_2=int((o > 1e-2).sum()), fixed_max=float(f.max()), fixed_n_gt_1e_2=int((f > 1e-2).sum()))
rec["check_d_counterfactual"] = dict(all_5m_boundaries=devstat(None), **{lab: devstat(lab) for lab in OFFS},
                                     per_cell=[dict(sym=SY[c_col[i]], E=iso(c_E[i]), n_bound=int(c_nb[i]),
                                                    old_rule_max_rel_dev=float(np.max(np.abs(np.expm1(c_old[i] - np.log(c_close[i] / c_close[i][0]))))),
                                                    fixed_max_rel_dev=float(np.max(np.abs(np.expm1(c_fix[i] - np.log(c_close[i] / c_close[i][0]))))),
                                                    float16_budget=float(math.expm1(c_q16[i]))) for i in range(NC_)])
check("d.population", len(dev_rows) == NC_ * NB, {"n": len(dev_rows)})
check("d.fixed_path_within_float16_budget", all(x["fixed_max_rel_dev"] <= x["float16_budget"] + 1e-12 for x in rec["check_d_counterfactual"]["per_cell"]))

# ---------------- NaN runs (closed population from the census) ----------------
nsel = len(C["g_col"])
check("nan_runs.census_selected_none", nsel == 0 and RC["nan_runs"]["kinds"] == {"SAME": RC["nan_runs"]["total"]} and len(RC["nan_runs"]["old_runs_no_longer_present"]) == 0,
      {"selected": nsel, "kinds": RC["nan_runs"]["kinds"]})

# ---------------- fixture for tests/test_rp_x0918r.py ----------------
fx = dict(source="rpx_restore.py (x0918r extension); cells = every new-span bound cell", device_sha256=rec["self_sha256"], cells=[])
for i in range(NC_):
    ks = sorted(bk[(int(c_E[i]), int(c_col[i]))], key=lambda k: b_pos[k])
    fx["cells"].append(dict(sym=SY[c_col[i]], E=iso(c_E[i]), n_bound=int(c_nb[i]), cache16=[None if np.isnan(v) else float(v) for v in c_r16[i]],
                            official_closes=[float(v) for v in c_close[i]], old_logpath=[float(v) for v in c_old[i]], meta_y4=float(c_y4[i]),
                            patch_status=[RL.STATUS_NAME[int(st[k])] for k in ks], float16_bound=float(math.expm1(c_q16[i]) + 1e-12)))
json.dump(fx, open(OUT + "/work/fixture_real_cells_x0918r.json", "w"), indent=0)
rec["fixture"] = dict(path=OUT + "/work/fixture_real_cells_x0918r.json", sha256=sha(OUT + "/work/fixture_real_cells_x0918r.json"), cells=[(c["sym"], c["E"], c["n_bound"]) for c in fx["cells"]])

# ---------------- write the extension patch (only if every gate above passed) ----------------
if FAILS: finish(3, "RPX_RESTORE VERDICT=RED (patch not written)")
PATCH = OUT + "/r_prices_raw_patch_x0918r_ext.npz"
np.savez_compressed(PATCH + ".tmp.npz",
    row=b_row.astype(np.int64), col=b_col.astype(np.int64), ts=b_ts.astype(np.int64), E=b_E.astype(np.int64), pos=b_pos.astype(np.int64),
    cache16=R16[b_row, b_col], status=st, raw=raw, close_now=cnow, close_prev=cprev,
    cell_E=c_E, cell_col=c_col, cell_status=c_status, cell_n_bound=c_nb, cell_n_nan=c_nnan, cell_y4_meta=c_y4, cell_y4_target_x0918r=c_y4t, cell_G_fixed=c_Gfix,
    cell_G_official=c_Graw, cell_close_official=c_close, cell_logpath_fixed=c_fix, cell_logpath_oldrule=c_old, cell_cache16=c_r16, cell_logpath_lo=c_lo, cell_logpath_hi=c_hi,
    gap_row=np.zeros(0, np.int64), gap_col=np.zeros(0, np.int64), gap_raw=np.zeros(0, np.float64), gap_unavail_row=np.zeros(0, np.int64), gap_unavail_col=np.zeros(0, np.int64),
    symbols=np.array(SY), archives_name=np.array([a["name"] for a in arch]), archives_sha256=np.array([a["sha256"] for a in arch]),
    span=np.array([S_LO, S_HI_OLD, S_HI_NEW], np.int64), base_patch_sha256=np.array(BASE_PATCH[1]),
    meta_json=np.array(json.dumps(dict(device="rpx_restore.py", self_sha256=rec["self_sha256"], rp_lib_sha256=rec["rp_lib"]["sha256"], inputs=rec["inputs"],
                                       census_sha256=CEN["sha256"], manifest_sha256=MAN["sha256"], contains="new-span entries only; use together with base_patch_sha256",
                                       cache_ts_convention="close time = kline open + 300 s", ret5_convention="close_t / close_{t-5m} - 1, clip +-0.3, float16"))))
os.replace(PATCH + ".tmp.npz", PATCH)
rec["outputs"] = dict(patch=dict(path=PATCH, sha256=sha(PATCH), bytes=os.path.getsize(PATCH)))
rec["VERDICT"] = "PASS"
finish(0, "RPX_RESTORE VERDICT=PASS bars=%s cells=%d b_compared=%d b_new_span=%d mismatch=%d patch_sha256=%s" % (
    json.dumps(sc), NC_, cb["compared"], cbn["compared"], cb["mismatch"], rec["outputs"]["patch"]["sha256"]))
