#!/usr/bin/env python3
"""fx_trd_verify.py — FX-DATA TRD-01 step B2 (pod2, CPU, read-only on every input). Committed before it is run.

Purpose: the artifact built by fx_trd_build.py is a NEW object with a NEW definition (SPEC_TRADABILITY_2026-09-13, log_cnt only).
The census the lead asked it to be checked against (156 dead perpetuals, 13,770,575 frozen post-death rows with ret5 == 0, 60 names
with funding records after death) comes from a DIFFERENT device with DIFFERENT definitions: `ad_tradability.py` (AUDIT_DATA bb8a2806)
gates every bar state on ret5 being finite and runs on the holefix2 cache alone (to 2026-09-01), while the artifact runs on
holefix2 + x0910 (to 2026-09-11) and does not read ret5 at all. Two counts that agree are not the same set. This device therefore:

  V1  reproduces ad_tradability.py's H1 numbers with ITS OWN definitions, on ITS OWN axis, and compares to EVERY key of the
      committed receipt AD_H_tradability.json. The expected values are parameters read from that file; a key present in the
      receipt and absent from the recomputation (or vice versa) is a failure, never a skip.
  V2  recomputes the same quantities with the SPEC definitions on the same holefix2 prefix, and enumerates every cell where the
      two definitions disagree, with the symbols and times. This is the accounting that explains any V1/V3 difference.
  V3  ties the artifact to V2: the artifact's traded5 bits and last/first traded times, restricted to the holefix2 prefix, must
      equal the SPEC recomputation bit for bit.
  V4  compares the artifact's dead-name SET (union axis, data_end - 24 h) to the audit's dead-name SET (holefix2, cache_end - 24 h)
      name by name, and reports the symmetric difference with each name's last traded bar.
  V5  reproduces H5 (funding records after death) from the ARTIFACT's last_traded_ts over the audit's dead names and the same three
      funding sources, and compares to every key of the receipt's H5 block.
  V6  reports the union-axis post-death row census (the artifact's own number, directly comparable to 13,770,575).

Usage: python3 fx_trd_verify.py <artifact.npz> <artifact_sha256> <AD_H_tradability.json> <AD_H_sha256> <out_receipt.json>
Exit 0 only if every check in every section passed.
"""
import os, sys, io, csv, json, glob, gzip, zipfile, time, calendar
from multiprocessing import Pool
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, ADH, ADH_SHA, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T
assert T.SPEC_SHA256 == "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"

W = "/workspace"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz"
CACHE_X = f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
FDIR = f"{W}/wide_multisrc/funding"; AUGP = f"{W}/fund_aug.json.gz"; SEPP = f"{W}/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz"
T0 = time.time()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year

FAILS = []
def check(name, got, expected, extra=None):
    """record one comparison; never skip. `expected` None means 'no expected value exists' which is itself a failure."""
    ok = (expected is not None) and (got == expected)
    CHECKS.append({"check": name, "ok": bool(ok), "got": got, "expected": expected, **({"note": extra} if extra else {})})
    if not ok: FAILS.append(name)
    return ok
CHECKS = []

rec = {"device": "fx_trd_verify.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)), "module": "tradability.py",
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time())}
adh_sha = T.guarded_sha256(ADH)
assert adh_sha == ADH_SHA, ("AD_H receipt sha mismatch", adh_sha, ADH_SHA)
AD = json.load(open(ADH))
rec["inputs"] = {ADH: adh_sha, CACHE: T.guarded_sha256(CACHE), CACHE_X: T.guarded_sha256(CACHE_X)}
assert rec["inputs"][CACHE] == AD["inputs"][CACHE], "the audit ran on a different holefix2 cache"
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact"] = {"path": ART, "sha256": A.sha256, "data_end": utc(A.data_end_ts), "symbols": len(A.symbols), "anchors": len(A.anchor_ts)}
log("guards ok; artifact", A.sha256[:16], "audit receipt", adh_sha[:16])

# ---------------- load the holefix2 channels the audit used ----------------
def stream_channels(path, chans, block=20000):
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        assert not fort and len(shape) == 3
        rowb = int(np.prod(shape[1:])) * dt.itemsize
        out = np.empty((shape[0], shape[1], len(chans)), dt); r = 0
        while r < shape[0]:
            k = min(block, shape[0] - r); buf = fh.read(k * rowb); assert len(buf) == k * rowb
            out[r:r + k] = np.frombuffer(buf, dtype=dt).reshape((k,) + tuple(shape[1:]))[:, :, chans]; r += k
    return out, shape

Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; ch = [str(c) for c in Z["ch"]]
assert ch[0] == "ret5" and ch[3] == "log_qv" and ch[4] == "log_cnt" and ch[2] == "cpos" and ch[6] == "tbf", ch
assert syms == A.symbols, "artifact symbol axis differs from the holefix2 cache"
CH5 = [0, 2, 3, 4, 6]                                    # ret5, cpos, log_qv, log_cnt, tbf
DAT, shp = stream_channels(CACHE, CH5)
TT, NW = shp[0], shp[1]
R0 = DAT[:, :, 0]; CPOS = DAT[:, :, 1]; LQV = DAT[:, :, 2]; C4 = DAT[:, :, 3]; TBF = DAT[:, :, 4]
log("holefix2 channels", DAT.shape)

# ================= V1 — reproduce ad_tradability.py H1 with ITS definitions =================
# expressions copied verbatim from docs/audit_pipeline_2026-09-13/devices_data/ad_tradability.py lines 55-93
fin = np.isfinite(R0); traded_a = fin & (C4 > 0); untr_a = fin & (C4 == 0)
cnt_nan_but_ret_finite = int((fin & ~np.isfinite(C4)).sum())
has_tr_a = traded_a.any(0); last_tr_a = np.where(has_tr_a, TT - 1 - np.argmax(traded_a[::-1], 0), -1)
dead_sym_a = has_tr_a & (last_tr_a < TT - 1 - 288)
rows_idx = np.arange(TT)
post_a = untr_a & (rows_idx[:, None] > last_tr_a[None, :]) & dead_sym_a[None, :]
pr, pc = np.where(post_a)
sig = {"post_death_untraded_rows": int(len(pr)), "ret5_exactly_0": int((R0[pr, pc] == 0).sum()),
       "log_qv_exactly_0": int((LQV[pr, pc] == 0).sum()),
       "cpos_nan": int((~np.isfinite(CPOS[pr, pc])).sum()), "tbf_nan": int((~np.isfinite(TBF[pr, pc])).sum())}
cnt_by_sym = np.bincount(pc, minlength=NW)
by_sym = {syms[j]: {"post_death_rows": int(cnt_by_sym[j]), "last_traded_bar_close": utc(CTS[last_tr_a[j]]),
                    "days": round(int(cnt_by_sym[j]) / 288.0, 1)} for j in np.where(cnt_by_sym > 0)[0]}
yr_rows = {}
for y in range(2022, 2027):
    lo = np.searchsorted(CTS, calendar.timegm((y, 1, 1, 0, 0, 0))); hi = np.searchsorted(CTS, calendar.timegm((y + 1, 1, 1, 0, 0, 0)))
    s_ = (pr >= lo) & (pr < hi); yr_rows[str(y)] = {"rows": int(s_.sum()), "symbols": int(len(np.unique(pc[s_])))}
runs = {"n_runs_ge_288": 0, "rows_in_runs": 0, "runs_resumed": 0, "runs_never_resumed": 0}
for j in range(NW):
    u = untr_a[:, j]
    if not u.any(): continue
    d = np.diff(np.concatenate([[0], u.astype(np.int8), [0]])); st_ = np.where(d == 1)[0]; en = np.where(d == -1)[0]
    L = en - st_; big = L >= 288
    runs["n_runs_ge_288"] += int(big.sum()); runs["rows_in_runs"] += int(L[big].sum())
    for a_, b_ in zip(st_[big], en[big]):
        if traded_a[b_:, j].any(): runs["runs_resumed"] += 1
        else: runs["runs_never_resumed"] += 1
H1 = AD["H1_cache"]
check("V1.TT", int(TT), H1.get("TT"))
check("V1.cache_end", utc(CTS[-1]), H1.get("cache_end"))
check("V1.ret_finite_but_log_cnt_nan_cells", cnt_nan_but_ret_finite, H1.get("ret_finite_but_log_cnt_nan_cells"))
check("V1.symbols_with_trades", int(has_tr_a.sum()), H1.get("symbols_with_trades"))
check("V1.symbols_dead_inside_cache", int(dead_sym_a.sum()), H1.get("symbols_dead_inside_cache"))
exp_sig = H1.get("post_death_signature") or {}
check("V1.post_death_signature.keys", sorted(sig), sorted(exp_sig))
for k in sorted(set(sig) | set(exp_sig)): check("V1.post_death_signature." + k, sig.get(k), exp_sig.get(k))
exp_yr = H1.get("post_death_rows_by_year") or {}
check("V1.post_death_rows_by_year.keys", sorted(yr_rows), sorted(exp_yr))
for k in sorted(set(yr_rows) | set(exp_yr)): check("V1.post_death_rows_by_year." + k, yr_rows.get(k), exp_yr.get(k))
exp_runs = H1.get("zero_trade_runs_ge_24h") or {}
check("V1.zero_trade_runs_ge_24h.keys", sorted(runs), sorted(exp_runs))
for k in sorted(set(runs) | set(exp_runs)): check("V1.zero_trade_runs_ge_24h." + k, runs.get(k), exp_runs.get(k))
exp_top = H1.get("top_symbols_post_death_rows") or {}
got_top = dict(sorted(by_sym.items(), key=lambda kv: -kv[1]["post_death_rows"])[:len(exp_top)])
check("V1.top_symbols_post_death_rows.keys", sorted(got_top), sorted(exp_top))
for s in sorted(set(got_top) | set(exp_top)): check("V1.top_symbols_post_death_rows." + s, got_top.get(s), exp_top.get(s))
rec["V1_audit_rules_reproduced"] = {"symbols_with_trades": int(has_tr_a.sum()), "symbols_dead_inside_cache": int(dead_sym_a.sum()),
                                    "post_death_signature": sig, "post_death_rows_by_year": yr_rows, "zero_trade_runs_ge_24h": runs}
log("V1 done; fails so far", len(FAILS))

# ================= V2 — SPEC definitions on the same holefix2 prefix, difference enumerated =================
S_pref = T.bar_states(C4)
traded_s = S_pref == T.TRADED; untr_s = S_pref == T.UNTRADED
d_tr = traded_s & ~traded_a; d_tr_rev = traded_a & ~traded_s
d_un = untr_s & ~untr_a; d_un_rev = untr_a & ~untr_s
def cells(mask, limit=50):
    r_, c_ = np.where(mask)
    return [{"symbol": syms[int(c_[i])], "ts": utc(CTS[int(r_[i])]), "ret5": float(R0[r_[i], c_[i]]), "log_cnt": float(C4[r_[i], c_[i]])} for i in range(min(limit, len(r_)))]
has_tr_s = traded_s.any(0); last_tr_s = np.where(has_tr_s, TT - 1 - np.argmax(traded_s[::-1], 0), -1)
dead_sym_s = has_tr_s & (last_tr_s < TT - 1 - 288)
rec["V2_spec_vs_audit_on_holefix2"] = {
    "TRADED_spec_not_audit": int(d_tr.sum()), "TRADED_audit_not_spec": int(d_tr_rev.sum()),
    "UNTRADED_spec_not_audit": int(d_un.sum()), "UNTRADED_audit_not_spec": int(d_un_rev.sum()),
    "reason": "the audit gates every bar state on isfinite(ret5); the SPEC reads log_cnt only (SPEC section 1)",
    "TRADED_spec_not_audit_examples": cells(d_tr), "UNTRADED_spec_not_audit_examples": cells(d_un),
    "symbols_with_trades_spec": int(has_tr_s.sum()), "symbols_dead_spec_same_threshold": int(dead_sym_s.sum()),
    "last_traded_row_differs_n": int((last_tr_s != last_tr_a).sum()),
    "last_traded_row_differs": [{"symbol": syms[j], "audit": utc(CTS[last_tr_a[j]]) if last_tr_a[j] >= 0 else None,
                                 "spec": utc(CTS[last_tr_s[j]]) if last_tr_s[j] >= 0 else None} for j in np.where(last_tr_s != last_tr_a)[0][:50]],
    "dead_set_equal_same_threshold": bool(np.array_equal(dead_sym_s, dead_sym_a)),
    "dead_only_spec": [syms[j] for j in np.where(dead_sym_s & ~dead_sym_a)[0]],
    "dead_only_audit": [syms[j] for j in np.where(dead_sym_a & ~dead_sym_s)[0]]}
check("V2.spec_dead_set_equals_audit_dead_set_at_same_threshold", rec["V2_spec_vs_audit_on_holefix2"]["dead_set_equal_same_threshold"], True)
check("V2.audit_has_no_bar_the_spec_misses", int(d_tr_rev.sum()) + int(d_un_rev.sum()), 0,
      "a bar the audit calls traded/untraded that the SPEC does not would be a real disagreement, not a definition difference")
log("V2 done; fails so far", len(FAILS))

# ================= V3 — the artifact equals the SPEC recomputation on the prefix =================
tr_bits = np.unpackbits(A._z["traded5_bits"], axis=1, count=len(A.symbols)).astype(bool)
ts5 = A._z["ts5"].astype(np.int64)
assert np.array_equal(ts5[:TT], CTS), "artifact ts5 prefix != holefix2 ts"
check("V3.traded5_bits_prefix_equals_spec_recomputation", bool(np.array_equal(tr_bits[:TT], traded_s)), True)
nod_bits = np.unpackbits(A._z["nodata5_bits"], axis=1, count=len(A.symbols)).astype(bool)
check("V3.nodata5_bits_prefix_equals_spec_recomputation", bool(np.array_equal(nod_bits[:TT], S_pref == T.NODATA)), True)
tail_traded = tr_bits[TT:].any(0)                                  # names that trade in the x0910 tail
lt_pref = np.where(has_tr_s, CTS[last_tr_s], -1)
same = ~tail_traded
check("V3.last_traded_ts_equals_prefix_value_for_names_absent_from_the_tail",
      bool(np.array_equal(A.last_traded_ts[same], lt_pref[same])), True)
rec["V3_artifact_vs_spec_prefix"] = {"names_trading_in_x0910_tail": int(tail_traded.sum()),
                                     "names_not_trading_in_tail": int(same.sum())}
log("V3 done; fails so far", len(FAILS))

# ================= V4 — dead-name SET: artifact (union axis) vs audit (holefix2) =================
dead_art = (A.last_traded_ts >= 0) & (A.last_traded_ts < A.data_end_ts - 86400)
set_art = {syms[j] for j in np.where(dead_art)[0]}; set_aud = {syms[j] for j in np.where(dead_sym_a)[0]}
rec["V4_dead_sets"] = {"artifact_n": len(set_art), "audit_n": len(set_aud), "identical": set_art == set_aud,
                       "artifact_threshold": "last trade < " + utc(A.data_end_ts - 86400) + " (union axis to " + utc(A.data_end_ts) + ")",
                       "audit_threshold": "last trade < " + utc(CTS[-1] - 86400) + " (holefix2 to " + utc(CTS[-1]) + ")",
                       "only_artifact": sorted(set_art - set_aud), "only_audit": sorted(set_aud - set_art),
                       "only_artifact_last_traded": {s: utc(A.last_traded_ts[syms.index(s)]) for s in sorted(set_art - set_aud)},
                       "only_audit_last_traded": {s: utc(CTS[last_tr_a[syms.index(s)]]) for s in sorted(set_aud - set_art)}}
check("V4.artifact_dead_count", len(set_art), H1.get("symbols_dead_inside_cache"),
      "count only; the set comparison is the next check and is the one that matters")
check("V4.artifact_dead_set_identical_to_audit_dead_set", set_art == set_aud, True)
log("V4 done; fails so far", len(FAILS))

# ================= V5 — H5 funding records after death, from the ARTIFACT's last_traded_ts =================
AUG = json.loads(gzip.open(AUGP, "rt").read()); SEP = json.loads(gzip.open(SEPP, "rt").read())
def events(s):
    ev = {}
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit(): continue
                    try: ev.setdefault(int(row[0]) // 1000, set()).add("zip")
                    except Exception: pass
        except Exception: pass
    for t, _ in (AUG.get("rates") or {}).get(s, []): ev.setdefault(int(t) // 1000, set()).add("aug")
    for t, _ in (SEP.get("rates") or {}).get(s, []): ev.setdefault(int(t) // 1000, set()).add("sep")
    return s, {k: sorted(v) for k, v in ev.items()}
dead_names = sorted(set_aud, key=lambda s: syms.index(s))
with Pool(6) as pool: EV = dict(pool.map(events, dead_names, chunksize=4))
h5 = {}; tot = {"events": 0, "zip": 0, "aug": 0, "sep": 0}; by_year = {}
for s in dead_names:
    j = syms.index(s); t_last = int(A.last_traded_ts[j]) + 3600            # the ARTIFACT's value, not the audit's
    after = sorted(t for t in EV[s] if t > t_last)
    if not after: continue
    srcs = {k: sum(1 for t in after if k in EV[s][t]) for k in ("zip", "aug", "sep")}
    h5[s] = {"last_traded_bar_close": utc(A.last_traded_ts[j]), "events_after": len(after), "first_after": utc(after[0]), "last_after": utc(after[-1]), **srcs}
    tot["events"] += len(after)
    for k, v in srcs.items(): tot[k] += v
    for t in after: by_year[str(yr(t))] = by_year.get(str(yr(t)), 0) + 1
H5 = AD["H5_funding_after_death"]
check("V5.symbols_dead_inside_cache", len(dead_names), H5.get("symbols_dead_inside_cache"))
check("V5.symbols_with_events_after_death", len(h5), H5.get("symbols_with_events_after_death"))
exp_tot = H5.get("totals") or {}
check("V5.totals.keys", sorted(tot), sorted(exp_tot))
for k in sorted(set(tot) | set(exp_tot)): check("V5.totals." + k, tot.get(k), exp_tot.get(k))
exp_by = H5.get("events_by_year") or {}
check("V5.events_by_year.keys", sorted(by_year), sorted(exp_by))
for k in sorted(set(by_year) | set(exp_by)): check("V5.events_by_year." + k, by_year.get(k), exp_by.get(k))
exp_per = H5.get("per_symbol") or {}
got_per = dict(sorted(h5.items(), key=lambda kv: -kv[1]["events_after"])[:len(exp_per)])
check("V5.per_symbol.keys", sorted(got_per), sorted(exp_per))
for s in sorted(set(got_per) | set(exp_per)): check("V5.per_symbol." + s, got_per.get(s), exp_per.get(s))
rec["V5_funding_after_death"] = {"symbols_with_events_after_death": len(h5), "totals": tot, "events_by_year": by_year,
                                 "per_symbol_top": dict(sorted(h5.items(), key=lambda kv: -kv[1]["events_after"])[:40])}
log("V5 done; fails so far", len(FAILS))

# ================= V6 — the artifact's own post-death census on the union axis =================
del DAT, R0, CPOS, LQV, C4, TBF, fin, traded_a, untr_a, post_a, traded_s, untr_s, S_pref
DX, shx = stream_channels(CACHE_X, [0, 4])
RX = DX[:, :, 0]; CX = DX[:, :, 1]
SX = T.bar_states(CX)
rows_x = np.arange(shx[0])
last_row_x = np.where(A.last_traded_ts >= 0, np.searchsorted(ts5, A.last_traded_ts), -1)
post_x = (SX == T.UNTRADED) & (rows_x[:, None] > last_row_x[None, :]) & dead_art[None, :]
prx, pcx = np.where(post_x)
rec["V6_union_axis_census"] = {
    "data_end": utc(A.data_end_ts), "rows": int(shx[0]), "dead_symbols": int(dead_art.sum()),
    "post_death_untraded_rows": int(len(prx)),
    "post_death_ret5_exactly_0": int((RX[prx, pcx] == 0).sum()),
    "post_death_ret5_nan": int((~np.isfinite(RX[prx, pcx])).sum()),
    "post_death_ret5_nonzero_finite": int((np.isfinite(RX[prx, pcx]) & (RX[prx, pcx] != 0)).sum()),
    "audit_holefix2_number_for_comparison": sig["post_death_untraded_rows"],
    "difference_vs_audit": int(len(prx)) - sig["post_death_untraded_rows"],
    "note": "the difference is the 2,880 x0910 tail rows of names already dead plus names that died between the two cache ends"}
check("V6.no_post_death_bar_has_a_non_zero_finite_return", rec["V6_union_axis_census"]["post_death_ret5_nonzero_finite"], 0)
log("V6", json.dumps(rec["V6_union_axis_census"])[:400])

rec["checks"] = CHECKS
rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD_VERIFY_DONE", json.dumps({"checks": len(CHECKS), "failed": len(FAILS), "failed_names": FAILS[:20],
                                        "artifact_sha256": A.sha256}), flush=True)
sys.exit(1 if FAILS else 0)
