#!/usr/bin/env python3
"""fx_trd04_states.py — FX-DATA TRD-04 (pod2, CPU, read-only on every input). Committed before it is run.

TRD-04 (AUDIT_DATA bb8a2806, P2): the cross-sectional state variables are computed over "finite qvk INTERSECT CRYPTO m1 mask",
which still contains dead contracts with frozen zero returns and stale funding. Breadth, dispersion and funding dispersion are
therefore biased low. Size on the T1 / T8 / r12 / r19 readings was never measured.

Three instruments compute those states, each with its own axis and its own member rule. This device recomputes all three with the
causal flag and reports what moves. It never edits any existing device or artifact.

  A  T1   `T1/devices/t1_states.py` — 18 columns on the x0910 accounting meta; member set = finite qvk INTERSECT umask row.
  B  T8   `T8/devices/t8_common.py` — 24 columns x 2 seeds on the v2ext panel axis; cols 1-17 read the umask row directly,
          cols 18-24 read `member_row` = (finite qvk) & umask row.
  C  r19  `r19_trackF_reindex/devices/build_regime_fixed.py` — 16 columns; member set = META members[i] INTERSECT umask row.

HOW THE LEGACY CODE IS RE-USED (no transcription). For A and C the original source text is read from disk, the relevant node is
extracted with `ast.get_source_segment` and executed verbatim in a namespace this device builds; the receipt records the source
file sha and the `ast.dump` of every node executed. For B the module is imported and its own functions are called. Nothing is
retyped, so "verbatim" is a property of the run, not a claim.

HOW THE TREATMENT IS INJECTED (no code edit). The flag is ANDed into the array each instrument reads its members FROM:
  A  QVK[k, j] <- NaN where not tradable(E[k], j)        => m = finite qvk INTERSECT umask INTERSECT tradable
  B  D["U"] <- U & tradable(panel ts)                    => market cols get m1 INTERSECT tradable, book cols get the member rule too
  C  members[i] <- members[i] restricted to tradable     => m = META members INTERSECT umask INTERSECT tradable

FROZEN COMPARISON RULE (written before the run; see also FIXPROGRAM section 0 item 8).
  1. Positive control first. Each part must reproduce the STORED artifact of its instrument BITWISE (NaN positions equal and the
     finite values equal as bytes). If any part fails, the device writes the failure and exits 1 without a treatment number.
  2. A column is `UNCHANGED` only if the treated value equals the control at every anchor, bitwise. Anything else is `CHANGED`,
     and the size is reported as: rows changed, max |delta|, median |delta| over changed rows, and |delta| divided by the column's
     own cross-anchor standard deviation.
  3. **No "immaterial" / "equivalent" / "NOT MATERIAL" label is issued by this device.** AUDIT_DATA's suggested action
     ("if nothing moves beyond resolution, record VERIFIED_IMMATERIAL") cannot be followed as written: under FIXPROGRAM section 0
     item 8 such a label may only come from `common/equivalence_labels.py` with a pre-frozen delta, and `DELTA_TABLE_K2.json` has
     no delta for state-variable units. The data layer reports magnitudes; the label belongs to whoever re-runs the reading.

Usage: python3 fx_trd04_states.py <artifact.npz> <artifact_sha256> <out_receipt.json> <out_series.npz>
Exit 0 only if every positive control reproduced bitwise.
"""
import os, sys, ast, json, time, zipfile, hashlib
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, OUT, OUTNPZ = sys.argv[1:5]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T
assert T.SPEC_SHA256 == "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"

W = "/workspace"
T1_SRC = f"{W}/uplift_r2_2026-09-13/T1/devices/t1_states.py"
T1_OUT = f"{W}/uplift_r2_2026-09-13/T1/receipts/T1_states.npz"
T8_DIR = f"{W}/uplift_r2_2026-09-13/T8/devices"
T8_OUT = f"{W}/uplift_r2_2026-09-13/T8/out/T8_data.npz"
R19_SRC = f"{W}/uplift_2026-09-11/r19_trackF_reindex/devices/build_regime_fixed.py"
R19_OUT = f"{W}/uplift_2026-09-11/r19_trackF_reindex/regime_vars_fixed.npz"
T0 = time.time()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))

FAILS = []; CHECKS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_trd04_states.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time()),
       "frozen_rule": "positive control bitwise first; UNCHANGED only if bitwise equal at every anchor; no equivalence label issued here"}
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact"] = {"path": ART, "sha256": A.sha256}
rec["legacy_sources"] = {p: T.guarded_sha256(p) for p in (T1_SRC, R19_SRC, T8_DIR + "/t8_common.py")}
rec["stored_artifacts"] = {p: T.guarded_sha256(p) for p in (T1_OUT, T8_OUT, R19_OUT)}
log("guards ok")

def take(src_path, pred, label):
    """execute the original source text of the first top-level node matching pred, verbatim"""
    text = open(src_path).read(); tree = ast.parse(text)
    for node in tree.body:
        if pred(node):
            seg = ast.get_source_segment(text, node)
            rec.setdefault("verbatim_nodes", {})[label] = {"src": src_path, "lineno": node.lineno,
                                                           "ast_sha256": hashlib.sha256(ast.dump(node).encode()).hexdigest()}
            return seg
    raise AssertionError("node not found: " + label)

def bitwise_equal(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    if a.shape != b.shape: return False, {"shape": [list(a.shape), list(b.shape)]}
    na, nb = np.isnan(a), np.isnan(b)
    if not np.array_equal(na, nb): return False, {"nan_positions_differ": int((na != nb).sum())}
    return bool(a[~na].tobytes() == b[~nb].tobytes()), {"cells": int(a.size)}

def delta_table(cols, C, Tt):
    """C control, Tt treated, both [n, len(cols)], rows already aligned by ts"""
    out = {}
    for c, name in enumerate(cols):
        a = C[:, c].astype(np.float64); b = Tt[:, c].astype(np.float64)
        na, nb = np.isnan(a), np.isnan(b)
        same_nan = np.array_equal(na, nb)
        both = ~na & ~nb
        d = np.abs(b[both] - a[both])
        moved = d > 0
        sd = float(np.nanstd(a)) if np.isfinite(a).any() else np.nan
        out[name] = {"unchanged_bitwise": bool(same_nan and a[both].tobytes() == b[both].tobytes()),
                     "nan_positions_equal": bool(same_nan), "nan_only_control": int((na & ~nb).sum()),
                     "nan_only_treated": int((nb & ~na).sum()), "rows_both_finite": int(both.sum()),
                     "rows_changed": int(moved.sum()),
                     "max_abs_delta": float(d.max()) if d.size else 0.0,
                     "median_abs_delta_over_changed": float(np.median(d[moved])) if moved.any() else 0.0,
                     "control_sd": sd,
                     "max_abs_delta_over_sd": float(d.max() / sd) if (d.size and sd and np.isfinite(sd) and sd > 0) else None,
                     "median_abs_delta_over_sd_over_changed": float(np.median(d[moved]) / sd) if (moved.any() and sd and np.isfinite(sd) and sd > 0) else None}
    return out

SERIES = {"spec_sha256": np.array(T.SPEC_SHA256), "artifact_sha256": np.array(A.sha256)}

# ================================ A — T1 ================================
MX = f"{W}/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; PX = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
UMP = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
rec["inputs_T1"] = {p: T.guarded_sha256(p) for p in (MX, PX, UMP)}
ZX = np.load(MX, allow_pickle=True); PXz = np.load(PX, allow_pickle=True); UMz = np.load(UMP, allow_pickle=True)
ns1 = {"np": np}
ns1["E"] = ZX["E_ts"].astype(np.int64); ns1["QVK"] = ZX["qvk"]
Y1 = ZX["y4"].astype(np.float64)
SYM1 = [str(s) for s in PXz["symbols"]]; assert SYM1 == A.symbols, "T1 panel symbols != artifact symbols"
tsP = PXz["ts"].astype(np.int64); ns1["prow"] = {int(t): j for j, t in enumerate(tsP)}
ns1["umts"] = UMz["ts"].astype(np.int64); ns1["umask"] = np.asarray(UMz["mask"])
ns1["umap"] = {int(t): k for k, t in enumerate(ns1["umts"])}
FN1 = PXz["f_fund_now"].astype(np.float64); IV1 = PXz["f_fund_iv"].astype(np.float64)
ns1["FN"] = FN1; ns1["RN8"] = FN1 * (8.0 / np.where(np.isfinite(IV1) & (IV1 > 0), IV1, 8.0))
ns1["ibtc"] = SYM1.index("BTCUSDT")
exec(compile(take(T1_SRC, lambda n: isinstance(n, ast.FunctionDef) and n.name == "trail", "t1.trail"), T1_SRC, "exec"), ns1)
exec(compile(take(T1_SRC, lambda n: isinstance(n, ast.FunctionDef) and n.name == "state_at", "t1.state_at"), T1_SRC, "exec"), ns1)
state_at = ns1["state_at"]
COLS1 = ["ts", "k_meta", "j_panel", "umask_carried", "nmem", "n24", "n72", "nfund", "DISP24", "DISP72", "BREADTH24", "BREADTH72",
         "BTC24", "BTC72", "SIGF", "MUF", "PUMP72", "PUMPSPR72"]
rows = [s for k in range(len(ns1["E"])) if (s := state_at(Y1, k)) is not None]
S1c = np.array(rows, dtype=np.float64)
STORED1 = np.load(T1_OUT, allow_pickle=True)
assert [str(c) for c in STORED1["cols"]] == COLS1, "T1 stored cols differ from the device's COLS"
ok, det = bitwise_equal(S1c, STORED1["S"])
check("A.T1.positive_control_bitwise", ok, det)
log("A control", ok, det)
if ok:
    trd1 = np.zeros((len(ns1["E"]), len(SYM1)), bool)
    hit = np.array([int(t) in A._row for t in ns1["E"]])
    trd1[hit] = A._z["state_W24H"][A.rows(ns1["E"][hit])] == T.TRADABLE
    rec["A_T1_anchors_off_artifact_grid"] = int((~hit).sum())
    drop1 = np.zeros_like(trd1); drop1[hit] = ~trd1[hit]     # anchors with no artifact row keep the legacy member set; counted above
    QT = np.array(ns1["QVK"], dtype=ns1["QVK"].dtype, copy=True)
    QT[drop1] = np.nan
    ns1["QVK"] = QT
    rows_t = [s for k in range(len(ns1["E"])) if (s := state_at(Y1, k)) is not None]
    S1t = np.array(rows_t, dtype=np.float64)
    check("A.T1.row_alignment", np.array_equal(S1c[:, 0], S1t[:, 0]), {"n": int(S1c.shape[0])})
    rec["A_T1"] = {"n_anchors": int(S1c.shape[0]), "cols": COLS1, "delta": delta_table(COLS1, S1c, S1t)}
    SERIES["T1_ts"] = S1c[:, 0].astype(np.int64); SERIES["T1_cols"] = np.array(COLS1)
    SERIES["T1_control"] = S1c; SERIES["T1_treated"] = S1t
    log("A treated done")
del ZX, PXz, Y1

# ================================ B — T8 ================================
sys.path.insert(0, T8_DIR)
import t8_common as t8
D, repB = t8.load_inputs(check_sha=True)
rec["inputs_T8"] = {k: v["sha256"] for k, v in repB["inputs"].items()}
STORED8 = np.load(T8_OUT, allow_pickle=True)
feats8 = [str(x) for x in STORED8["feats"]]
assert feats8 == t8.FEATS, "T8 stored feats differ from t8_common.FEATS"
pts8 = STORED8["ts"].astype(np.int64)
F_ctrl = {s: np.array([t8.features_row(D, i, s) for i in range(t8.N_FULL)], np.float64) for s in t8.SEEDS}
okB = True
for s in t8.SEEDS:
    o, d = bitwise_equal(F_ctrl[s], STORED8["F_" + s]); okB &= o
    check("B.T8.positive_control_bitwise.s" + s, o, d)
log("B control", okB)
if okB:
    panel_ts_full = np.load(t8.INPUTS["PANEL"][0], allow_pickle=True)["ts"].astype(np.int64)
    assert len(panel_ts_full) == t8.N_REC
    trd8 = A._z["state_W24H"][A.rows(panel_ts_full)] == T.TRADABLE
    D2 = dict(D); D2["U"] = D["U"] & trd8
    rec["B_T8_universe_rows_dropped"] = {"control_true": int(D["U"].sum()), "treated_true": int(D2["U"].sum()),
                                         "dropped": int((D["U"] & ~trd8).sum())}
    F_trt = {s: np.array([t8.features_row(D2, i, s) for i in range(t8.N_FULL)], np.float64) for s in t8.SEEDS}
    rec["B_T8"] = {"n_anchors": int(t8.N_FULL), "cols": feats8,
                   "delta": {s: delta_table(feats8, F_ctrl[s], F_trt[s]) for s in t8.SEEDS}}
    SERIES["T8_ts"] = pts8; SERIES["T8_cols"] = np.array(feats8)
    for s in t8.SEEDS:
        SERIES["T8_control_s" + s] = F_ctrl[s]; SERIES["T8_treated_s" + s] = F_trt[s]
    log("B treated done")

# ================================ C — r19 ================================
B19 = f"{W}/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MT19 = f"{B19}/wide_fea_hist_meta.npz"; PW19 = f"{B19}/wide_panel_4h_hist_v2.npz"
rec["inputs_r19"] = {p: T.guarded_sha256(os.path.realpath(p)) for p in (MT19, PW19, UMP)}
MT = np.load(MT19, allow_pickle=True); PW = np.load(PW19, allow_pickle=True); UM = np.load(UMP, allow_pickle=True)
SYM19 = [str(s) for s in PW["symbols"]]; assert SYM19 == A.symbols
loop_src = take(R19_SRC, lambda n: isinstance(n, ast.For) and getattr(getattr(n, "iter", None), "func", None) is not None
                and getattr(n.iter.func, "id", "") == "enumerate", "r19.main_loop")
COLS19 = ["ts", "nmem", "sig_fund", "fund_mean", "fund_med", "frac_neg", "disp24", "mean24",
          "breadth_up", "vol7_med", "absmom7_med", "range24_med", "btc_r24", "btc_m7", "btc_v7", "young30"]
IV19 = PW["f_fund_iv"]
def run_r19(members_arr):
    ns = {"np": np, "E_ts": MT["E_ts"].astype(np.int64), "members": members_arr,
          "pw_row": {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))},
          "umap": {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}, "UMM": np.asarray(UM["mask"]),
          "FN": PW["f_fund_now"], "IV": IV19, "R24": PW["f_rev_24h"], "V7": PW["f_vol_7d"], "M7": PW["f_mom_7d"],
          "RG": PW["f_range_24h"], "RN8": PW["f_fund_now"] * (8.0 / np.where(np.isfinite(IV19) & (IV19 > 0), IV19, 8.0)),
          "ibtc": SYM19.index("BTCUSDT"), "rows": [], "first_seen": {}}
    exec(compile(loop_src, R19_SRC, "exec"), ns)
    return np.array(ns["rows"], dtype=np.float64)
V19c = run_r19(MT["members"])
STORED19 = np.load(R19_OUT, allow_pickle=True)
assert [str(c) for c in STORED19["cols"]] == COLS19
okC, detC = bitwise_equal(V19c, STORED19["V"])
check("C.r19.positive_control_bitwise", okC, detC)
log("C control", okC, detC)
if okC:
    E19 = MT["E_ts"].astype(np.int64)
    hit19 = np.array([int(t) in A._row for t in E19])
    trd19 = np.zeros((len(E19), len(SYM19)), bool)
    trd19[hit19] = A._z["state_W24H"][A.rows(E19[hit19])] == T.TRADABLE
    mem_t = np.empty(len(E19), dtype=object)
    for i in range(len(E19)):
        m = np.asarray(MT["members"][i], np.int64)
        mem_t[i] = m[trd19[i][m]] if hit19[i] else m       # anchors with no artifact row keep the legacy member set
    rec["C_r19_anchors_off_artifact_grid"] = int((~hit19).sum())
    V19t = run_r19(mem_t)
    same_ts = np.array_equal(V19c[:, 0], V19t[:, 0])
    check("C.r19.row_alignment", same_ts, {"control_rows": int(V19c.shape[0]), "treated_rows": int(V19t.shape[0])})
    if same_ts:
        rec["C_r19"] = {"n_anchors": int(V19c.shape[0]), "cols": COLS19, "delta": delta_table(COLS19, V19c, V19t)}
        SERIES["r19_ts"] = V19c[:, 0].astype(np.int64); SERIES["r19_cols"] = np.array(COLS19)
        SERIES["r19_control"] = V19c; SERIES["r19_treated"] = V19t
    else:
        rec["C_r19"] = {"row_alignment_failed": True, "control_rows": int(V19c.shape[0]), "treated_rows": int(V19t.shape[0]),
                        "note": "the treated run drops anchors whose member set falls below the device's len(m) < 50 guard"}
    log("C treated done")

def det_npz(path, arrays):
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)
det_npz(OUTNPZ, SERIES)
rec["series_npz"] = {"path": OUTNPZ, "sha256": T.guarded_sha256(OUTNPZ), "bytes": os.path.getsize(OUTNPZ), "keys": sorted(SERIES)}
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD04_DONE", json.dumps({"checks": len(CHECKS), "failed": len(FAILS), "failed_names": FAILS[:10],
                                   "series_sha256": rec["series_npz"]["sha256"]}), flush=True)
sys.exit(1 if FAILS else 0)
