#!/usr/bin/env python3
"""fx_fnd_hol_rebuild.py — the ONE merged rebuild for FND-01/02 and HOL-01 (pod2, CPU, read-only inputs). Committed before it runs.

FND-01 and HOL-01 are the same file, which is why they are one device (lead's ruling R2): building them separately would leave two
panels nobody can reconcile.

  HOL-01  the incumbent panel's PREFIX kline columns were built on the pre-holefix cache. The hole-fixed full-history build already
          exists as `wide_panel_4h_rawbuild_x0910.npz` (r6_chain S4, pod_panel_ext.py UNMODIFIED). The merged panel takes its kline
          columns from there for the whole axis.
  FND-01  the incumbent TAIL funding took its interval from a per-symbol map read once from /fapi/v1/fundingInfo at 2026-09-11
          (`SEP_IV`), applied to every September row. The merged panel re-resolves every settlement row through
          `common/funding_interval.py`: zip-declared column -> P9 exact (by the COLUMN iv_best) -> safe spacing -> unresolved.

WHAT IS TAKEN VERBATIM, AND WHY THAT MATTERS. The EMA continuation algebra (v0 wall-clock HL3d raw rate, v1 wall-clock HL3d
normfix, v2 settlement-space span) is NOT retyped: this device reads `r6_panel_splice.py` from git, finds its one top-level symbol
loop with `ast`, takes the statements from `seeds = {}` to the end of that loop, and executes that source text. The receipt records
the source sha and the `ast.dump` sha of every statement executed. Only the interval derivation — the defect's actual location — is
this device's own code.

CONTROLS, all before any changed cell is written:
  C1  HOL: the prefix kline difference between the rebuild and the incumbent must be confined to the holefix2 fill neighbourhoods,
      reproducing AD_D's own reading (393,475 cells near holes, 0 away). A kline cell that differs away from every fill run would
      mean this is not a hole measurement, and the device stops.
  C2  FND: rebuilding the tail funding with the INCUMBENT interval rule must reproduce the incumbent x0910 panel's funding tail
      BITWISE. That is the G-R6-style proof that this device's legacy-rule reimplementation is the same rule; without it, a later
      difference could not be attributed to the interval change.
  C3  the cut row and the tail kline columns keep r6's own assertions.

Usage: python3 fx_fnd_hol_rebuild.py <p9_csv_gz> <p9_sha256> <out_dir> <out_receipt.json>
Exit 0 only if C1 and C2 passed and the written file reloads.
"""
import os, sys, ast, csv, io, json, glob, gzip, time, zipfile, hashlib
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
P9, P9_SHA, OUT_DIR, OUT = sys.argv[1:5]
for p in os.environ["PYTHONPATH"].split(":"): sys.path.insert(0, p)
import funding_interval as FI
import tradability as T

W = "/workspace"
SPLICE_SRC = f"{W}/fx_data_2026-09-13/devices/r6_panel_splice.py"     # the committed copy, synced beside this device
CAN_P = f"{W}/data/wide_panel_4h_v2ext.npz"
EXT_P = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_rawbuild_x0910.npz"
INC_P = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
HOLES = f"{W}/review_scratch/holefix2_cells.npz"
FSEP = f"{W}/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz"
AUGP = f"{W}/fund_aug.json.gz"
FDIR = f"{W}/wide_multisrc/funding"
HL = 3 * 86400.0
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
T0 = time.time()
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
FAILS = []; CHECKS = []
def check(n, ok, d=None):
    CHECKS.append({"check": n, "ok": bool(ok), **({"detail": d} if d is not None else {})})
    if not ok: FAILS.append(n)

rec = {"device": "fx_fnd_hol_rebuild.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "resolver_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "funding_interval.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (SPLICE_SRC, CAN_P, EXT_P, INC_P, HOLES, FSEP, AUGP, P9)},
       "utc_start": U(time.time())}
assert rec["inputs"][P9] == P9_SHA, ("P9 table sha", rec["inputs"][P9])
assert rec["inputs"][SPLICE_SRC].startswith("cccc5b6be9248671"), ("splice source is not the committed r6 blob",)

# ---------------- the verbatim EMA continuation block ----------------
src = open(SPLICE_SRC).read(); tree = ast.parse(src)
loop = [n for n in tree.body if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
        and [e.id for e in n.target.elts] == ["j", "s"]]
assert len(loop) == 1, "expected exactly one 'for j, s in enumerate(syms)' loop"
body = loop[0].body
start = next(i for i, n in enumerate(body)
             if isinstance(n, ast.Assign) and any(getattr(t_, "id", None) == "seeds" for t_ in n.targets))
EMA_STMTS = body[start:]
# The block contains a bare `continue` (the "no canonical funding history, leave the tail as the ext build" branch), which is
# illegal outside a loop. Wrapping it in a single-iteration loop keeps that statement's meaning EXACTLY as it was -- skip the
# rest of this symbol -- without editing one character of the extracted source. `padded=True` keeps the original indentation.
# Take the CONTIGUOUS source span, not per-statement segments joined: `get_source_segment` pads only each segment's first line,
# so joining them loses the relative indentation of a nested block. A contiguous span out of the file preserves every character
# and every level of indentation, and is stronger provenance besides.
_lines = src.splitlines(True)[EMA_STMTS[0].lineno - 1: EMA_STMTS[-1].end_lineno]
EMA_SRC = "for _once in (0,):\n" + "".join(_lines)
rec["verbatim_ema_block"] = {"source": SPLICE_SRC, "first_line": EMA_STMTS[0].lineno, "last_line": EMA_STMTS[-1].end_lineno,
                             "n_statements": len(EMA_STMTS), "wrapper": "for _once in (0,): -- so the block's bare `continue` keeps its original meaning",
                             "ast_sha256": hashlib.sha256("".join(ast.dump(n) for n in EMA_STMTS).encode()).hexdigest(),
                             "source_span_sha256": hashlib.sha256("".join(_lines).encode()).hexdigest()}
_stored = {t_.id for n in EMA_STMTS for x in ast.walk(n) for t_ in ([x] if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store) else [])}
_loaded = {x.id for n in EMA_STMTS for x in ast.walk(n) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
FREE_NAMES = sorted(_loaded - _stored - set(dir(__builtins__)) - {"np"})
rec["verbatim_ema_block_free_names"] = FREE_NAMES     # every one must be supplied, and a missing one is named, never guessed
EMA_CODE = compile(EMA_SRC, SPLICE_SRC + " [statements %d-%d, wrapped in a 1-iteration loop]" % (EMA_STMTS[0].lineno, EMA_STMTS[-1].end_lineno), "exec")
log("verbatim EMA block: lines %d-%d, %d statements" % (EMA_STMTS[0].lineno, EMA_STMTS[-1].end_lineno, len(EMA_STMTS)))

# ---------------- load panels ----------------
CAN = np.load(CAN_P, allow_pickle=True); EXT = np.load(EXT_P, allow_pickle=True); INC = np.load(INC_P, allow_pickle=True)
syms = [str(x) for x in CAN["symbols"]]
assert syms == [str(x) for x in EXT["symbols"]] == [str(x) for x in INC["symbols"]]
ct = CAN["ts"].astype(np.int64); et = EXT["ts"].astype(np.int64); it = INC["ts"].astype(np.int64)
cut = int(ct[-1]); nC = len(ct); tail_idx = np.where(et > cut)[0]; tail_ts = et[tail_idx]
assert np.array_equal(it, np.concatenate([ct, tail_ts])), "incumbent axis is not prefix+tail"
KLINE = ["f_rev_4h", "f_rev_24h", "f_rev_3d", "f_mom_7d", "f_mom_30d", "f_mom_7d_x24", "f_vol_7d", "f_volq_ratio",
         "f_amihud_24h", "f_range_24h", "f_cpos_24h", "f_tbf_24h", "f_asz_24h", "Y4", "Y24", "elig"]
FUND = ["f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"]
log("axes: prefix %d cut %s tail %d" % (nC, U(cut), len(tail_ts)))

# ---------------- C1: HOL control ----------------
HZ = np.load(HOLES, allow_pickle=True)
# `fill_runs` and `neigh_rows` are 5m CACHE ROW INDICES, not timestamps -- run 26 read them as ts, which put every anchor in the
# "away" bucket and inverted C1 (near 0 / away 393,475 against AD_D's 393,475 / 0). The cache grid starts 2022-01-01T00:00Z at
# 300 s, verified: row 16129 -> 1645833900 = 2022-02-26T00:05Z = the cell list's own minimum. `neigh_rows` is AD_D's OWN
# precomputed neighbourhood (8,640 rows back, 288 forward), so this device uses it rather than re-deriving the window.
CACHE_T0, BAR = 1640995200, 300
_cells_ts = np.asarray(HZ["ts"]).astype(np.int64)
assert int(_cells_ts.min()) == CACHE_T0 + int(np.asarray(HZ["fill_runs"])[0, 0]) * BAR, "cache grid origin does not check out"
runs = [(CACHE_T0 + int(a) * BAR, CACHE_T0 + int(b) * BAR) for a, b in np.asarray(HZ["fill_runs"]).tolist()]
neigh = [(CACHE_T0 + int(a) * BAR, CACHE_T0 + int(b) * BAR) for a, b in np.asarray(HZ["neigh_rows"]).tolist()]
rec["hole_runs_utc"] = [[U(a), U(b)] for a, b in runs]
rec["hole_neighbourhoods_utc"] = [[U(a), U(b)] for a, b in neigh]
near = np.zeros(nC, bool)
for a, b in neigh:
    near |= (ct >= a) & (ct <= b)
c1 = {}
tot_near = tot_away = 0
for k in KLINE:
    if k not in CAN.files or k not in EXT.files: continue
    a = np.asarray(CAN[k], np.float64); b = np.asarray(EXT[k][:nC], np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    d = (na != nb) | (~na & ~nb & (np.abs(a - b) > 1e-6 * np.maximum(1.0, np.abs(b))))
    c1[k] = {"diff_near_hole": int(d[near].sum()), "diff_away_from_hole": int(d[~near].sum())}
    tot_near += c1[k]["diff_near_hole"]; tot_away += c1[k]["diff_away_from_hole"]
rec["C1_hol"] = {"by_key": c1, "total_near_hole": tot_near, "total_away_from_hole": tot_away,
                 "anchors_near_hole": int(near.sum())}
check("C1.kline_prefix_differs_only_near_hole_runs", tot_away == 0,
      {"away": tot_away, "near": tot_near, "AD_D_reported_near": 393475})
log("C1 near %d away %d (AD_D reported 393475 near, 0 away)" % (tot_near, tot_away))

# ---------------- funding event stream ----------------
AUG = json.loads(gzip.open(AUGP, "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
SEP = json.loads(gzip.open(FSEP, "rt").read()); SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}
P9ROW = {}
with gzip.open(P9, "rt") as fh:
    for r in csv.DictReader(fh):
        P9ROW[(r["symbol"], int(r["ft"]))] = r
rec["p9_rows"] = len(P9ROW)
log("P9 rows", len(P9ROW))

def zip_rows(s):
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    return rows

def stream(s, mode):
    """(ft, fr, iv_full). mode 'legacy' = the incumbent rule; mode 'p9' = resolve every row through funding_interval."""
    rows = zip_rows(s)
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan) if mode == "legacy" else np.nan))
    for t_ms, rate in (SEP.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), SEP_IV.get(s, np.nan) if mode == "legacy" else np.nan))
    if not rows: return None, None, None, {}
    rows.sort()
    ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64)
    fr = np.array([ded[t][0] for t in ft], np.float64)
    fiv = np.array([ded[t][1] for t in ft], np.float64)
    tiers = {}
    if mode == "p9":
        for i, t in enumerate(ft):
            res = FI.resolve(P9ROW.get((s, int(t))), allow_spacing=False)
            tiers[res["tier"]] = tiers.get(res["tier"], 0) + 1
            if res["tier"] in FI.GATEABLE:
                fiv[i] = FI.gate_interval(res, what="%s@%d" % (s, t))
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_full = np.where(np.isfinite(fiv), fiv, dv)
    n_fell_through = int((~np.isfinite(fiv)).sum())
    iv_full = np.where(np.isfinite(iv_full), iv_full, 8.0)
    iv_full = ALLOWED[np.argmin(np.abs(iv_full[:, None] - ALLOWED[None, :]), axis=1)]
    tiers["_fell_through_to_spacing_or_default"] = n_fell_through
    return ft, fr, iv_full, tiers

def build_funding(mode):
    out = {c: np.array(INC[c], copy=True) for c in FUND}
    for c in FUND: out[c][:nC] = CAN[c]
    state = {}; agg = {}; ncont = [0]
    for j, s in enumerate(syms):
        ft, fr, iv_full, tiers = stream(s, mode)
        for k, v in tiers.items(): agg[k] = agg.get(k, 0) + v
        if ft is None: continue
        rate_nf = fr * (8.0 / iv_full)
        ns = {"np": np, "CAN": CAN, "out": out, "j": j, "s": s, "ft": ft, "fr": fr, "iv_full": iv_full,
              "rate_nf": rate_nf, "cut": cut, "tail_ts": tail_ts, "nC": nC, "HL": HL, "state": state,
              "n_cont": 0}
        missing = [n for n in FREE_NAMES if n not in ns]
        assert not missing, ("the verbatim block reads names this device does not supply", missing)
        exec(EMA_CODE, ns)
        ncont[0] += ns.get("n_cont", 0)
    agg["_symbols_continued"] = ncont[0]
    return out, agg

FL, agg_l = build_funding("legacy"); log("legacy funding rebuilt", json.dumps(agg_l))
c2 = {}
for c in FUND:
    a = np.asarray(INC[c][nC:], np.float64); b = np.asarray(FL[c][nC:], np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    c2[c] = {"nan_equal": bool(np.array_equal(na, nb)),
             "bitwise": bool(np.array_equal(na, nb) and a[~na].tobytes() == b[~nb].tobytes()),
             "maxabs": float(np.abs(a[~na & ~nb] - b[~na & ~nb]).max()) if (~na & ~nb).any() else 0.0}
rec["C2_fnd_legacy_reproduction"] = c2
check("C2.legacy_rule_reproduces_the_incumbent_tail_bitwise", all(v["bitwise"] for v in c2.values()), c2)
log("C2", {k: v["bitwise"] for k, v in c2.items()})

if FAILS:
    rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["stopped_before_writing"] = True
    rec["runtime_s"] = round(time.time() - T0, 1)
    json.dump(rec, open(OUT, "w"), indent=1, default=str)
    print("FX_FND_HOL_STOPPED_CONTROL", json.dumps(FAILS), flush=True); sys.exit(1)

FP, agg_p = build_funding("p9"); log("p9 funding rebuilt", json.dumps(agg_p))
rec["p9_tier_census"] = {"legacy": agg_l, "p9": agg_p}
d = {}
for c in FUND:
    a = np.asarray(FL[c][nC:], np.float64); b = np.asarray(FP[c][nC:], np.float64)
    na, nb = np.isnan(a), np.isnan(b); both = ~na & ~nb
    d[c] = {"cells": int(a.size), "nan_pattern_changed": int((na != nb).sum()),
            "value_changed": int((both & (np.abs(a - b) > 1e-9)).sum()),
            "maxabs": float(np.abs(a[both] - b[both]).max()) if both.any() else 0.0}
rec["D_tail_funding_change"] = d
log("D", json.dumps(d))

# ---------------- build and write ----------------
out = {"ts": np.concatenate([ct, tail_ts]), "symbols": np.array(syms)}
for k in sorted(set(CAN.files) | set(EXT.files)):
    if k in ("ts", "symbols"): continue
    if k in FUND:
        out[k] = FP[k]; continue
    if k in EXT.files and np.asarray(EXT[k]).ndim == 2 and np.asarray(EXT[k]).shape[1] == len(syms):
        out[k] = np.asarray(EXT[k])[:len(out["ts"])]          # HOL-01: klines from the hole-fixed build, whole axis
    elif k in CAN.files:
        out[k] = CAN[k]
check("C3.cut_row_funding_unchanged_vs_canonical",
      all(bool(np.array_equal(np.asarray(CAN[c][-1])[np.isfinite(CAN[c][-1])],
                              np.asarray(out[c][nC - 1])[np.isfinite(CAN[c][-1])])) for c in FUND), None)
check("C3.tail_klines_equal_the_rawbuild",
      all(bool(np.array_equal(np.asarray(EXT[k][tail_idx])[np.isfinite(EXT[k][tail_idx])],
                              np.asarray(out[k][nC:])[np.isfinite(EXT[k][tail_idx])])) for k in ("f_rev_24h", "f_mom_7d", "f_vol_7d")), None)
os.makedirs(OUT_DIR, exist_ok=True)
p = os.path.join(OUT_DIR, "wide_panel_4h_v2ext_x0910_fndhol.npz")
tmp = p + ".tmp"
with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for k in sorted(out):
        zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
        a = np.asarray(out[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
        with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
os.replace(tmp, p)
Z = np.load(p, allow_pickle=False)
check("W.reload_roundtrip_keys", sorted(Z.files) == sorted(out), {"keys": len(out)})
check("W.reload_roundtrip_axis", bool(np.array_equal(Z["ts"].astype(np.int64), out["ts"])), None)
rec["output"] = {"path": p, "sha256": T.guarded_sha256(p), "bytes": os.path.getsize(p), "keys": sorted(out),
                 "anchors": int(len(out["ts"])), "first": U(out["ts"][0]), "last": U(out["ts"][-1]),
                 "naming": "POPULATION SENSITIVITY under SPEC_TRADABILITY_v2: this panel fixes the hole-carrying kline prefix "
                           "and the pull-time interval map; it is NOT an economic-truth fix and exit P&L remains unidentified"}
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = U(time.time())
json.dump(rec, open(OUT, "w"), indent=1, default=str)
print("FX_FND_HOL_DONE", json.dumps({"failed": len(FAILS), "sha256": rec["output"]["sha256"][:16],
                                     "tail_funding_changed": {c: d[c]["value_changed"] for c in FUND}}), flush=True)
sys.exit(1 if FAILS else 0)
