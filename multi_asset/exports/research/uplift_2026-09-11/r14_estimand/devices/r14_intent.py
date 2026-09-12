#!/usr/bin/env python3
"""r14_intent.py — AMENDMENT 2 device. INTENT-weighted drift (the un-selected estimator),
the fill-selection effect, the fill shortfall, two placebos, the k sensitivity, and the
reconciliation against exec_caliber_reconcile.

drift(x)  = sgn(x) * (P(E + 5k min) / P(E) - 1) * 1e4        [bps, + = COST to the book]
            P from the LIVE producer's own 5m cache; P(E) = close of the bar CLOSING AT E.
PRIMARY   = |intended_notional|-weighted drift over attempt_idx==1 orders.jsonl rows, ERA2.

READ-ONLY on ~/dl_quant_live and ~/wide_shadow. ENV WHITELIST = EXPLICITLY EMPTY (asserted).
PREREG + AMENDMENT 1 + AMENDMENT 2 sha256 all asserted before any computation.
"""
import os, sys, json, time, hashlib, math
from collections import defaultdict

_FORBIDDEN = ["LEGS", "PHI", "CAL", "MEMBERS_TOPN", "COSTB_JSON", "PANEL_IN", "V2", "OUT_TAG",
              "W3FIX", "FTRIM", "UMASK_SCOPE", "SLOW_NPY", "FPRED", "FSEED", "LOOK", "WRULE",
              "TRADE_TOPN", "UMASK_NPZ", "SHADOW_OFFSET_MIN", "RNSM", "FTPOS", "LTRIM_TH", "CDAMP"]
_present = sorted([k for k in _FORBIDDEN if k in os.environ])
assert _present == [], f"E-0826-D: env vars present that must not be: {_present}"
ENV_WHITELIST = []

import numpy as np

def _no_env(*a, **k):
    raise AssertionError("r14 ENV WHITELIST is EMPTY: this device reads no environment variable")
os.environ.get = _no_env

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r14_estimand"
SHAS = {"PREREG_r14_cost_estimand_2026-09-12.md": "bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904",
        "PREREG_AMENDMENT_1_r14_2026-09-12.md": "6207572a9dba8a32554b6c3a44467509e179127ae92084f2bf44f7fafb872594",
        "PREREG_AMENDMENT_2_r14_2026-09-12.md": "abfcc85064ee2fbdbfa3c7f45f2a2b5a4fe2b3870ab4c8d7a9f03c26576cfc54"}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
for fn, s in SHAS.items():
    got = sha(f"{ROOT}/{fn}")
    assert got == s, f"{fn} sha mismatch: {got}"
SELF_SHA = sha(os.path.abspath(__file__))

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SHADOW = "/Users/haosiyu/wide_shadow"
OUT = f"{ROOT}/receipts/RECEIPT_r14_intent_2026-09-12.json"
NB = 2000; BOOT_SEED = 20260905
MODEL_BPS = 2.9537
TURN_REPLAY = 0.0540270
TURN_LIVE = 0.10864
TS_LO = 1785556800   # 2026-08-01T04:00Z
TS_HI = 1789099200   # 2026-09-11T04:00Z  (the archived infra1 window; the first run used the wrong epoch)

R = {"self_sha256": SELF_SHA, "prereg_shas": SHAS, "env_whitelist": ENV_WHITELIST,
     "env_whitelist_declared": "EXPLICITLY EMPTY SET (asserted at runtime)",
     "utc": time.strftime("%FT%TZ", time.gmtime()), "gates": {}}

# ---- cache ----
CACHE = f"{SHADOW}/state/rolling.npz"
z = np.load(CACHE, allow_pickle=True)
CTS = z["ts"].astype(np.int64); CD = z["data"]
RET = np.asarray(CD[:, :, 0], np.float64); LQV = np.asarray(CD[:, :, 3], np.float64); del z
cfg = json.load(open(f"{SHADOW}/shadow_bundle/config.json"))
PSYM = [str(s) for s in cfg["symbols_panel"]]; SIDX = {s: i for i, s in enumerate(PSYM)}
assert CD.shape[1] == len(PSYM)
assert (np.diff(CTS) == 300).all(), "G3 FAIL"
ROW = {int(t): i for i, t in enumerate(CTS)}
fin = np.isfinite(RET)
CL = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])
CN = np.concatenate([np.zeros((1, RET.shape[1]), np.int64), np.cumsum(fin, 0)])
QVe = np.where(np.isfinite(LQV), np.expm1(np.clip(LQV, 0, 30)), 0.0)
CQ = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(QVe, 0)])
CQN = np.concatenate([np.zeros((1, RET.shape[1]), np.int64), np.cumsum(np.isfinite(LQV), 0)])

def ret_rows(c, a, b):
    """Pi(1+ret5)-1 over cache row indices a..b inclusive; None if any bar missing or out of range."""
    if a > b:
        return 0.0
    if a < 0 or b + 1 >= CL.shape[0]:
        return None
    if int(CN[b + 1, c] - CN[a, c]) != (b - a + 1):
        return None
    return float(np.expm1(CL[b + 1, c] - CL[a, c]))

# ---- ledgers ----
days = sorted(x for x in os.listdir(LIVE) if x.isdigit())
anch = {}
for dd in days:
    p = f"{LIVE}/{dd}/anchors.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None:
            continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str):
            mid = json.loads(mid)
        anch[ts] = mid or {}
_bnbc = sorted([t for t in anch if anch[t].get("BNBUSDT")])
def bnb_mid(ts):
    if not _bnbc:
        return None
    t = min(_bnbc, key=lambda t: abs(t - ts)); return anch[t]["BNBUSDT"]

ORD = []
for dd in days:
    p = f"{LIVE}/{dd}/orders.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        ORD.append(json.loads(ln))
FIL = {}
raw = 0
for dd in days:
    p = f"{LIVE}/{dd}/fills.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln); raw += 1
        FIL[(r["symbol"], r.get("trade_id"))] = r
FIL = list(FIL.values())
R["inputs"] = {"orders_rows": len(ORD), "fills_raw": raw, "fills_dedup": len(FIL),
               "anchors": len(anch), "days": [days[0], days[-1]],
               "cache_sha256": sha(CACHE), "cache_path": CACHE,
               "lineage": "LIVE-CACHE (~/wide_shadow/state/rolling.npz), not the pinned pod v4 cache"}

def era(ts):
    return "ERA1" if (ts % 14400) < 600 else "ERA2"

def build_intent(kmode, window):
    """kmode: 'auto' (k from anchor_ts), 4, 5. window: 'post' [E,E+5k] or 'pre' [E-5k,E]."""
    out = []
    for r in ORD:
        if int(r.get("attempt_idx") or 1) != 1:
            continue
        ints = r.get("intended_notional")
        if ints is None or float(ints) == 0.0:
            continue
        ints = float(ints)
        ts = r.get("anchor_ts")
        if ts is None:
            continue
        sym = r["symbol"]; c = SIDX.get(sym)
        if c is None:
            continue
        E = int(math.floor(ts / 14400.0) * 14400)
        i0 = ROW.get(E)
        if i0 is None:
            continue
        k = int(round((ts - E) / 300.0)) if kmode == "auto" else int(kmode)
        k = max(0, min(k, 47))
        if window == "post":
            rr = ret_rows(c, i0 + 1, i0 + k)
        else:
            rr = ret_rows(c, i0 - k + 1, i0) if k > 0 else 0.0
        if rr is None:
            continue
        sgn = 1.0 if ints > 0 else -1.0
        nq = int(CQN[i0 + 1, c] - CQN[max(0, i0 + 1 - 48), c])
        qv = float(CQ[i0 + 1, c] - CQ[max(0, i0 + 1 - 48), c]) if (nq >= 44 and i0 - 47 >= 0) else None
        filled = abs(float(r.get("filled_notional") or 0.0))
        out.append({"ts": ts, "E": E, "day": E // 86400, "sym": sym, "w": abs(ints),
                    "filled": filled, "drift": sgn * rr * 1e4, "k": k, "qv4h": qv,
                    "era": era(ts), "ot": r.get("order_type") or "maker",
                    "arm": r.get("placement_arm")})
    return out

def boot(items, field, wfield, kseed):
    d = defaultdict(lambda: [0.0, 0.0])
    num = tot = 0.0; n = 0
    for r in items:
        v = r.get(field); w = r.get(wfield)
        if v is None or w is None or w <= 0:
            continue
        d[r["day"]][0] += v * w; d[r["day"]][1] += w; num += v * w; tot += w; n += 1
    if tot <= 0:
        return None
    keys = sorted(d)
    a = np.array([d[k][0] for k in keys]); b = np.array([d[k][1] for k in keys])
    rng = np.random.default_rng([BOOT_SEED, kseed])
    idx = rng.integers(0, len(keys), size=(NB, len(keys)))
    m = a[idx].sum(1) / b[idx].sum(1)
    return {"mean": round(float(num / tot), 4),
            "ci95": [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)],
            "n": n, "weight": round(float(tot), 1), "n_days": len(keys)}

INT = build_intent("auto", "post")
INT2 = [r for r in INT if r["era"] == "ERA2"]
INT1 = [r for r in INT if r["era"] == "ERA1"]

# ---------------- PRIMARY ----------------
R["PRIMARY_drift_intent_ERA2"] = boot(INT2, "drift", "w", 11)
R["drift_intent_ERA1_control"] = boot(INT1, "drift", "w", 12)
R["gates"]["A2_4_ERA1_k_is_zero"] = {"mean_k": round(float(np.mean([r["k"] for r in INT1])), 4) if INT1 else None,
                                     "expect": 0.0}
R["drift_intent_ALL"] = boot(INT, "drift", "w", 13)

# ---------------- A2-1 / A2-2 selection ----------------
# drift on FILLED notional (weight = filled notional on the same attempt-1 order rows)
R["A2_1_drift_filled_ERA2"] = boot([r for r in INT2 if r["filled"] > 0], "drift", "filled", 21)
unf = [{**r, "unf": max(r["w"] - r["filled"], 0.0)} for r in INT2]
R["A2_3_drift_UNFILLED_ERA2"] = boot(unf, "drift", "unf", 22)
fi = R["A2_1_drift_filled_ERA2"]; pr = R["PRIMARY_drift_intent_ERA2"]; un = R["A2_3_drift_UNFILLED_ERA2"]
R["A2_2_SELECTION_fill_minus_intent_ERA2"] = {
    "drift_filled": fi["mean"], "drift_intent": pr["mean"],
    "selection_bps": round(fi["mean"] - pr["mean"], 4),
    "drift_unfilled": un["mean"],
    "reading": "positive selection = filled orders saw MORE adverse drift than intent (would be "
               "surprising); negative = the fills are the favourable half, i.e. the classic "
               "maker selection effect"}
tot_int = sum(r["w"] for r in INT2); tot_fil = sum(r["filled"] for r in INT2)
R["A2_3_fill_shortfall_ERA2"] = {"attempt1_intent_notional": round(tot_int, 1),
    "attempt1_filled_notional": round(tot_fil, 1),
    "fill_rate_vs_attempt1_intent": round(tot_fil / tot_int, 4) if tot_int else None,
    "note": "the replay books 100% of dw; the desk books this share at attempt 1 (attempt-2 IOC "
            "top-up covers part of the remainder and is counted separately below)"}

# ---------------- A2-5 pre-anchor placebo, A2-6 k sensitivity ----------------
PRE = build_intent("auto", "pre")
R["A2_5_PLACEBO_pre_anchor_window_ERA2"] = boot([r for r in PRE if r["era"] == "ERA2"], "drift", "w", 31)
R["A2_5_PLACEBO_pre_anchor_window_ERA1"] = boot([r for r in PRE if r["era"] == "ERA1"], "drift", "w", 32)
K4 = build_intent(4, "post"); K5 = build_intent(5, "post")
R["A2_6_k_sensitivity_ERA2"] = {
    "k4_to_E+20m": boot([r for r in K4 if r["era"] == "ERA2"], "drift", "w", 41),
    "k5_to_E+25m": boot([r for r in K5 if r["era"] == "ERA2"], "drift", "w", 42)}
R["A2_4_ERA1_forced_k5_placebo"] = boot([r for r in K5 if r["era"] == "ERA1"], "drift", "w", 43)

# ---------------- splits ----------------
R["S3_by_order_type_ERA2"] = {}
k = 50
for ot in sorted(set(r["ot"] for r in INT2)):
    R["S3_by_order_type_ERA2"][ot] = boot([r for r in INT2 if r["ot"] == ot], "drift", "w", k); k += 1
R["by_placement_arm_ERA2"] = {}
for arm in sorted(set(str(r["arm"]) for r in INT2)):
    R["by_placement_arm_ERA2"][arm] = boot([r for r in INT2 if str(r["arm"]) == arm], "drift", "w", k); k += 1
qv = sorted([r["qv4h"] for r in INT2 if r["qv4h"] is not None])
R["S4_by_liquidity_decile_ERA2"] = {}
if len(qv) > 100:
    edges = [qv[int(len(qv) * i / 10)] for i in range(1, 10)]
    R["S4_decile_edges_qv4h_usdt"] = [round(e, 1) for e in edges]
    for i in range(10):
        lo = -np.inf if i == 0 else edges[i - 1]; hi = np.inf if i == 9 else edges[i]
        R["S4_by_liquidity_decile_ERA2"][f"D{i}"] = boot(
            [r for r in INT2 if r["qv4h"] is not None and lo <= r["qv4h"] < hi], "drift", "w", k); k += 1
R["by_replay_tier_ERA2"] = {}
for lo, hi, nm in ((5e6, np.inf, "tier0_qv4h>=5e6"), (1e6, 5e6, "tier1_qv4h>=1e6"), (-np.inf, 1e6, "tier2_rest")):
    R["by_replay_tier_ERA2"][nm] = boot([r for r in INT2 if r["qv4h"] is not None and lo <= r["qv4h"] < hi],
                                        "drift", "w", k); k += 1

# ---------------- G1 rerun with the CORRECT window epoch ----------------
TS = json.load(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/infra1_cost/tier_stats.json"))
TA = TS["all"]
def arch_target(tag):
    num = den = 0.0
    for t in TA:
        s = t[f"{tag}_slip_bps"]; cov = t[f"{tag}_slip_cov"]; nz = t[f"{tag}_nz"]
        if s is None or cov is None:
            continue
        w = cov * nz; num += s * w; den += w
    return num / den
g1 = {}
for tag, ot in (("mk", "maker"), ("tk", "topup_taker"), ("pf", "protective_flatten")):
    num = den = 0.0; nf = 0
    for r in FIL:
        ts = r.get("anchor_ts")
        if ts is None or (r.get("order_type") or "maker") != ot:
            continue
        E = int(math.floor(ts / 14400.0) * 14400)
        if not (TS_LO <= E <= TS_HI):
            continue
        nz = abs(float(r.get("fill_notional") or 0.0)); px = float(r.get("fill_px") or 0.0)
        M = (anch.get(ts) or {}).get(r["symbol"])
        if nz <= 0 or px <= 0 or not M:
            continue
        sgn = 1.0 if r.get("side") == "buy" else -1.0
        num += sgn * (px / float(M) - 1.0) * 1e4 * nz; den += nz; nf += 1
    if den > 0:
        tgt = arch_target(tag) if tag != "pf" else None
        g1[tag] = {"measured": round(num / den, 4), "archived_tierfree_target": (round(tgt, 4) if tgt is not None else None),
                   "abs_diff": (round(abs(num / den - tgt), 4) if tgt is not None else None),
                   "n_fills": nf, "notional": round(den, 1)}
R["gates"]["G1_slip_reproduction_correct_window"] = {
    "window_utc": [time.strftime("%FT%TZ", time.gmtime(TS_LO)), time.strftime("%FT%TZ", time.gmtime(TS_HI))],
    "tolerance_bps": 0.25, **g1,
    "PASS": bool(all(g1[t]["abs_diff"] is None or g1[t]["abs_diff"] <= 0.25 for t in g1))}

# ---------------- G6 reconciliation with exec_caliber_reconcile ----------------
p = R["PRIMARY_drift_intent_ERA2"]
R["G6_reconciliation_vs_exec_caliber_reconcile"] = {
    "exec_caliber_device_sha256": "e9d8daafa8bbb5aeed03c543e05688be86d77c78b540a18ff389c9ba6708d8a3",
    "exec_caliber_path": "multi_asset/exports/research/allweather_2026-09-05/trackA/results/exec_caliber_reconcile.json",
    "exec_caliber_a_minus_c_2024to26_s42": {"mean": 0.1004, "ci95": [0.0667, 0.1327]},
    "exec_caliber_delta_w_slice_2024to26_s42": {"mean": 0.0805, "ci95": [0.0531, 0.1060]},
    "exec_caliber_2026_to_cut": {"a_minus_c": 0.0780, "delta_w_slice": 0.0072, "delta_w_ci95": [-0.0296, 0.0452]},
    "r14_drift_intent_bps_per_unit_traded": p["mean"], "r14_ci95": p["ci95"],
    "r14_in_bps_per_anchor_per_gross_on_LIVE_turnover": round(p["mean"] * TURN_LIVE, 4),
    "r14_ci95_bps_per_anchor_per_gross_on_LIVE_turnover": [round(p["ci95"][0] * TURN_LIVE, 4),
                                                            round(p["ci95"][1] * TURN_LIVE, 4)],
    "r14_in_bps_per_anchor_per_gross_on_MATCHED_replay_turnover": round(p["mean"] * TURN_REPLAY, 4),
    "sign_convention": "+ = the replay over-credits (a CHARGE against the replay); - = the desk's "
                       "delayed entry is cheaper than the replay's reference (a CREDIT)"}

json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({kk: R[kk] for kk in
    ("gates", "PRIMARY_drift_intent_ERA2", "drift_intent_ERA1_control", "A2_1_drift_filled_ERA2",
     "A2_2_SELECTION_fill_minus_intent_ERA2", "A2_3_drift_UNFILLED_ERA2", "A2_3_fill_shortfall_ERA2",
     "A2_5_PLACEBO_pre_anchor_window_ERA2", "A2_5_PLACEBO_pre_anchor_window_ERA1",
     "A2_6_k_sensitivity_ERA2", "A2_4_ERA1_forced_k5_placebo", "S3_by_order_type_ERA2",
     "by_placement_arm_ERA2", "by_replay_tier_ERA2", "G6_reconciliation_vs_exec_caliber_reconcile")},
    indent=1))
print("WROTE", OUT)
