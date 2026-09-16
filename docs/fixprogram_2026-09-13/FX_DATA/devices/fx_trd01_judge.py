#!/usr/bin/env python3
"""fx_trd01_judge.py — FX-DATA TRD-01 step D (pod2, CPU, read-only). Committed before it is run.

Judges the SPEC_TRADABILITY_2026-09-13 section 7 arms. SPEC section 7 says the estimator is "the r18_judge estimator, verbatim",
so this device does not re-implement it: it reads `/workspace/uplift_2026-09-11/r18_foundation/devices/r18_judge.py`, extracts
`load`, `draws`, `boot`, `shp`, `level` and `block` with `ast.get_source_segment`, and executes that source text unchanged in a
namespace built here. The receipt records the source sha and each node's `ast.dump` sha, so "verbatim" is a property of the run.

  P  positive control, first and blocking. C0 was run here with the A0 recipe on the same unmodified device, so its `rec` and `W`
     must equal the archived `r3k/arms/A0_PWR230k_s{seed}.npz` BITWISE. r18_judge's own published anchor is re-asserted on seed 42
     (g over W_ALPHA = 0.6341957 and matched turnover = 0.0540270, both to 5e-7). A failure here means the arms are not A0 and no
     delta is reported.
  D  paired deltas against C0 for TU / TB / TF / TF4 on W_ALPHA (primary, n = 9138), W_FULL (n = 10038) and KING_LIVE (2024+,
     n = 5838), with r18_judge's own UTC-day block bootstrap (2000 draws, default_rng([20260905, k])), the dprice / dcarry / dcost
     decomposition and per-year rows.
  L  the label, from `common/equivalence_labels.py` with DELTA_TABLE_K2 key D1: delta = 0.05 bps / anchor / unit gross, two-sided
     TOST on each seed's CI95, then `aggregate` over the two seeds. delta in {0.02, 0.25} is reported as sensitivity and never sets
     the label. TF4 is a window sensitivity and its label is reported as SENSITIVITY_ONLY.
  X  also reported, per SPEC section 7: dead and lag name-anchors left inside the fixed universe, |W| outside the member set on
     non-tradable names, and the fund base size change per year.

Usage: python3 fx_trd01_judge.py <arms_dir> <artifact.npz> <artifact_sha256> <out_receipt.json>
Exit 0 only if the positive control passed.
"""
import os, sys, ast, json, time, hashlib, calendar
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ARMS, ART, ART_SHA, OUT = sys.argv[1:5]
PP = os.environ["PYTHONPATH"].split(":")
for p in PP: sys.path.insert(0, p)
import tradability as T
import equivalence_labels as EL

W = "/workspace"
JUDGE = f"{W}/uplift_2026-09-11/r18_foundation/devices/r18_judge.py"
ARCH = {s: f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{s}.npz" for s in ("42", "2027")}
DELTA_TABLE = "DELTA_TABLE_K2.json"      # copied read-only beside this device; sha asserted below
DELTA_TABLE_SHA = "ad6af2075ca71ed756be26bbe7759761f981add24f02581de41c3f014643dea6"
D1 = 0.05; SENS = (0.02, 0.25)
SEEDS = ("42", "2027"); TREAT = ("TU", "TB", "TF", "TF4")
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
FAILS = []; CHECKS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_trd01_judge.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(PP[0], "tradability.py")), "spec_sha256": T.SPEC_SHA256,
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "judge_source": JUDGE, "judge_source_sha256": T.guarded_sha256(JUDGE),
       "delta_table_sha256": T.guarded_sha256(DELTA_TABLE), "D1_delta": D1, "utc_start": utc(time.time())}
assert rec["delta_table_sha256"] == DELTA_TABLE_SHA, ("DELTA_TABLE_K2 sha", rec["delta_table_sha256"])
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact_sha256"] = A.sha256

# ---------------- extract r18_judge's estimator verbatim ----------------
src = open(JUDGE).read(); tree = ast.parse(src)
NS = {"np": np, "json": json, "time": time, "calendar": calendar, "os": os}
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
NS["sha"] = sha
for name, val in (("NB", 2000), ("RES_BPS", 0.23), ("_DRAW", {}),
                  ("UB", calendar.timegm((2026, 8, 30, 20, 0, 0))), ("K24", calendar.timegm((2024, 1, 1, 0, 0, 0)))):
    NS[name] = val
NS["PCT_K"] = (100 * (0.05 / 8) / 2, 100 * (1 - (0.05 / 8) / 2))
want = ("load", "draws", "boot", "shp", "level", "block")
got = {}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in want:
        seg = ast.get_source_segment(src, node)
        rec.setdefault("verbatim_nodes", {})[node.name] = {"lineno": node.lineno,
                                                           "ast_sha256": hashlib.sha256(ast.dump(node).encode()).hexdigest()}
        exec(compile(seg, JUDGE, "exec"), NS); got[node.name] = True
missing = [n for n in want if n not in got]
assert not missing, ("estimator nodes not found in r18_judge.py", missing)
log("estimator extracted verbatim:", sorted(got))

# ---------------- load the arms with r18_judge's own loader ----------------
AR = {}
for s in SEEDS:
    for arm in ("C0",) + TREAT:
        AR[(arm, s)] = NS["load"](os.path.join(ARMS, "%s_PWR230k_s%s.npz" % (arm, s)), None, r18=False)
ts = AR[("C0", "42")]["ts"]
for k, x in AR.items(): assert np.array_equal(x["ts"], ts), k
NS["ts"] = ts
NS["DAY"] = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts])
NS["YEAR"] = np.array([time.gmtime(int(t)).tm_year for t in ts])
NS["DAYS"] = (ts // 86400) * 86400
WA = AR[("C0", "42")]["WA"]; WT = AR[("C0", "42")]["WT"]; KL = AR[("C0", "42")]["KL"]
WINDOWS = {"W_ALPHA": WA, "W_FULL": WT, "KING_LIVE": WA & KL}
log("arms loaded", len(AR), "windows", {k: int(v.sum()) for k, v in WINDOWS.items()})

# ---------------- P. positive control ----------------
for s in SEEDS:
    Zr = np.load(ARCH[s], allow_pickle=False); Zm = np.load(os.path.join(ARMS, "C0_PWR230k_s%s.npz" % s), allow_pickle=False)
    r_ok = np.asarray(Zr["rec"], np.float64).tobytes() == np.asarray(Zm["rec"], np.float64).tobytes()
    w_ok = np.asarray(Zr["W"]).tobytes() == np.asarray(Zm["W"]).tobytes()
    check("P.s%s.C0_rec_bitwise_equals_archived_A0" % s, r_ok,
          {"archived": ARCH[s], "archived_sha256": T.guarded_sha256(ARCH[s])})
    check("P.s%s.C0_W_bitwise_equals_archived_A0" % s, w_ok, None)
    log("P s%s rec %s W %s" % (s, r_ok, w_ok))
g42 = AR[("C0", "42")]["g"][WA]
check("P.s42.published_g_WALPHA_0p6341957", abs(float(g42.mean()) - 0.6341957) < 5e-7, {"got": float(g42.mean())})
check("P.s42.published_tau_matched_0p0540270", abs(float(AR[("C0", "42")]["tau"][WA].mean()) - 0.0540270) < 5e-7,
      {"got": float(AR[("C0", "42")]["tau"][WA].mean())})
if FAILS:
    rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["stopped_before_any_delta"] = True
    json.dump(rec, open(OUT, "w"), indent=1)
    print("FX_TRD01_JUDGE_STOPPED_POSITIVE_CONTROL", json.dumps(FAILS), flush=True); sys.exit(1)

# ---------------- D. paired deltas, and L. the label ----------------
MARGIN = EL.Margin(delta=D1, unit="bps per 4h anchor per unit gross",
                   justification=("DELTA_TABLE_K2 key D1, frozen 2026-09-13 before any arm was run: 0.05 bps/anchor/unit gross is "
                                  "7.9% of A0's own W_ALPHA net and 2.19% of NAV per year at gross 2.0, which the programme has "
                                  "declared economically immaterial for a book-level change"),
                   source="docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.json sha ad6af207, FIXPROGRAM section 4.1")
OUTD = {}
for arm in TREAT:
    per_seed = {}; readings = []
    for s in SEEDS:
        b = {wn: NS["block"](AR[(arm, s)], AR[("C0", s)], m) for wn, m in WINDOWS.items()}
        per_seed[s] = b
        ci = EL.Interval(point=b["W_ALPHA"]["dg"], lo=b["W_ALPHA"]["ci95"][0], hi=b["W_ALPHA"]["ci95"][1], level=0.95)
        readings.append(EL.equivalence(ci, margin=MARGIN))
    agg = EL.aggregate(readings)
    sens = {}
    for d in SENS:
        m2 = EL.Margin(delta=d, unit=MARGIN.unit, justification="sensitivity column only; never sets the label (FIXPROGRAM section 4.1)",
                       source=MARGIN.source)
        sens["delta_%g" % d] = EL.aggregate([EL.equivalence(EL.Interval(point=per_seed[s]["W_ALPHA"]["dg"],
                                                                       lo=per_seed[s]["W_ALPHA"]["ci95"][0],
                                                                       hi=per_seed[s]["W_ALPHA"]["ci95"][1], level=0.95),
                                                            margin=m2) for s in SEEDS])["label"]
    OUTD[arm] = {"by_seed": per_seed, "readings_D1": readings, "label_D1": agg,
                 "label_status": ("SENSITIVITY_ONLY: W=4h never sets a label (SPEC section 2 and section 7)" if arm == "TF4" else "PRIMARY"),
                 "sensitivity_labels": sens}
    log(arm, "W_ALPHA dg", {s: round(per_seed[s]["W_ALPHA"]["dg"], 4) for s in SEEDS}, "label", agg["label"])
rec["D_arms"] = OUTD
rec["C0_levels"] = {s: {wn: NS["level"](AR[("C0", s)], m) for wn, m in WINDOWS.items()} for s in SEEDS}

# ---------------- X. the exposure SPEC section 7 also asks for ----------------
rows = A.rows(ts)
TR = A._z["state_W24H"][rows] == T.TRADABLE
dead = A.dead_after(ts, A.symbols)
UMT = np.load(os.path.join(os.path.dirname(ARMS), "inject", "umask_UPIT_CRYPTO_tradable_W24H.npz"), allow_pickle=False)
um2 = np.asarray(UMT["mask"])
YEAR = NS["YEAR"]
X = {}
for s in SEEDS:
    Wm = np.asarray(np.load(os.path.join(ARMS, "TF_PWR230k_s%s.npz" % s), allow_pickle=False)["W"], np.float64)
    held = np.abs(Wm) > 1e-12
    X[s] = {}
    for y in sorted(set(YEAR.tolist())):
        m = (YEAR == y) & WT
        X[s][str(y)] = {"anchors": int(m.sum()),
                        "dead_name_anchors_still_in_fixed_universe": int((um2[m] & dead[m]).sum()),
                        "lag_tradable_and_dead_name_anchors": int((um2[m] & TR[m] & dead[m]).sum()),
                        "absW_on_non_tradable_outside_member_set": float(np.abs(Wm[m])[held[m] & ~um2[m]].sum()),
                        "absW_total": float(np.abs(Wm[m]).sum())}
        X[s][str(y)]["absW_non_tradable_share"] = round(X[s][str(y)]["absW_on_non_tradable_outside_member_set"]
                                                        / max(X[s][str(y)]["absW_total"], 1e-12), 6)
rec["X_residual_exposure_TF"] = X
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD01_JUDGE_DONE", json.dumps({"failed": len(FAILS),
      "labels": {a: OUTD[a]["label_D1"]["label"] for a in TREAT},
      "dg_WALPHA": {a: {s: round(OUTD[a]["by_seed"][s]["W_ALPHA"]["dg"], 4) for s in SEEDS} for a in TREAT}}), flush=True)
sys.exit(1 if FAILS else 0)
