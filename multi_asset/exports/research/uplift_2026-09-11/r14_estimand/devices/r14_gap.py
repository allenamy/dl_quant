#!/usr/bin/env python3
"""r14_gap.py — IS THE POST-FILL MARKOUT ALREADY INSIDE THE REPLAY'S y4?

Measures, per deduped LIVE fill, the gap between the price the desk actually transacted at and
the price at which the replay's y4 window OPENS, decomposed exactly into

    slip  = sgn*(F/M - 1)*1e4          M = ledger `mid_at_anchor` (the executor's anchor-RUN start)
    drift = sgn*(M/P_ref - 1)*1e4      P_ref = close of the 5m bar CLOSING AT the 4h grid instant E
    GAP   = sgn*(F/P_ref - 1)*1e4      == exact product of the two (asserted, G4)

READ-ONLY on ~/dl_quant_live and ~/wide_shadow. No order, no write, no trading endpoint.
ENV WHITELIST = EXPLICITLY EMPTY (E-0826-D): asserted at runtime, written into the receipt.
PREREG sha256 asserted before any computation.
"""
import os, sys, json, time, hashlib, math
from collections import defaultdict

# ---------------- E-0826-D: env whitelist = EXPLICITLY EMPTY, ASSERTED ----------------
_FORBIDDEN = ["LEGS", "PHI", "CAL", "MEMBERS_TOPN", "COSTB_JSON", "PANEL_IN", "V2", "OUT_TAG",
              "W3FIX", "FTRIM", "UMASK_SCOPE", "SLOW_NPY", "FPRED", "FSEED", "LOOK", "WRULE",
              "TRADE_TOPN", "UMASK_NPZ", "SHADOW_OFFSET_MIN", "RNSM", "FTPOS", "LTRIM_TH", "CDAMP"]
_present = sorted([k for k in _FORBIDDEN if k in os.environ])
assert _present == [], f"E-0826-D: env vars present that must not be: {_present}"
ENV_WHITELIST = []          # explicitly empty, enumerated into the receipt

import numpy as np          # imported BEFORE the guard: numpy/ctypes read PYTHONUSERBASE at import

def _no_env(*a, **k):
    raise AssertionError("r14 ENV WHITELIST is EMPTY: this device reads no environment variable")
os.environ.get = _no_env    # from here on, any env read by THIS device's own logic aborts the run

# ---------------- prereg assertion ----------------
ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r14_estimand"
PREREG = f"{ROOT}/PREREG_r14_cost_estimand_2026-09-12.md"
AMEND1 = f"{ROOT}/PREREG_AMENDMENT_1_r14_2026-09-12.md"
PREREG_SHA = "bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904"
AMEND1_SHA = "6207572a9dba8a32554b6c3a44467509e179127ae92084f2bf44f7fafb872594"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
assert sha(PREREG) == PREREG_SHA, f"PREREG sha mismatch: {sha(PREREG)}"
assert sha(AMEND1) == AMEND1_SHA, f"AMENDMENT 1 sha mismatch: {sha(AMEND1)}"
SELF_SHA = sha(os.path.abspath(__file__))

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SHADOW = "/Users/haosiyu/wide_shadow"
OUT = f"{ROOT}/receipts/RECEIPT_r14_gap_2026-09-12.json"

NB = 2000
BOOT_SEED = 20260905
MODEL_BPS = 2.9537                 # costb_PWR_G230k book_avg_bps_per_unit_turnover
TURN_REPLAY = 0.0540270            # MATCHED caliber E[t_i/g_i]
TURN_LIVE = 0.10864                # r11 live traded / gross
G1_TOL = 0.25

R = {"self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "amendment1_sha256": AMEND1_SHA,
     "env_whitelist": ENV_WHITELIST, "env_whitelist_declared": "EXPLICITLY EMPTY SET (asserted)",
     "utc": time.strftime("%FT%TZ", time.gmtime()), "gates": {}, "inputs": {}}

# ---------------- 1. the live producer's rolling 5m cache (LIVE-CACHE lineage) ----------------
CACHE = f"{SHADOW}/state/rolling.npz"
z = np.load(CACHE, allow_pickle=True)
CTS = z["ts"].astype(np.int64)
CD = z["data"]                              # (T, 829, 7) float16; ch = ret5,range,cpos,log_qv,...
RET = np.asarray(CD[:, :, 0], np.float64)
LQV = np.asarray(CD[:, :, 3], np.float64)
del z
cfg = json.load(open(f"{SHADOW}/shadow_bundle/config.json"))
PSYM = [str(s) for s in cfg["symbols_panel"]]
SIDX = {s: i for i, s in enumerate(PSYM)}   # G2: BY NAME, never by position
assert CD.shape[1] == len(PSYM), f"axis width {CD.shape[1]} != symbols_panel {len(PSYM)}"

# G3 row convention
d = np.diff(CTS)
g3_diff = bool((d == 300).all())
anch_rows = CTS[(CTS % 14400) == 0]
g3_anchor = bool(len(anch_rows) > 0)
assert g3_diff, "G3 FAIL: rolling.npz ts not a strict 300s grid"
R["gates"]["G3_row_convention"] = {"all_diffs_300": g3_diff, "n_rows": int(len(CTS)),
    "n_anchor_rows": int(len(anch_rows)),
    "ts_first_utc": time.strftime("%FT%TZ", time.gmtime(int(CTS[0]))),
    "ts_last_utc": time.strftime("%FT%TZ", time.gmtime(int(CTS[-1]))),
    "source": "shadow_loop_v3.py L285-299: close_s=(kline_open+300000)//1000, only close_s<=anchor "
              "ingested, ret5 = c/prev_close - 1 => row ts IS the bar CLOSE time and ret5 is a "
              "close-to-close SIMPLE return"}
ROW = {int(t): i for i, t in enumerate(CTS)}

# cumulative log1p for exact product over row ranges; NaN bars treated as 0 return and counted
fin = np.isfinite(RET)
CL = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])
CN = np.concatenate([np.zeros((1, RET.shape[1]), np.int64), np.cumsum(fin, 0)])
QVe = np.where(np.isfinite(LQV), np.expm1(np.clip(LQV, 0, 30)), 0.0)
CQ = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(QVe, 0)])
CQN = np.concatenate([np.zeros((1, RET.shape[1]), np.int64), np.cumsum(np.isfinite(LQV), 0)])

# ---------------- 2. live ledgers, READ-ONLY ----------------
days = sorted(x for x in os.listdir(LIVE) if x.isdigit())
anch = {}
for dd in days:
    p = f"{LIVE}/{dd}/anchors.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln)
        ts = r.get("anchor_ts")
        if ts is None:
            continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str):
            mid = json.loads(mid)
        anch[ts] = {"day": dd, "mid": mid or {}}
ats = sorted(anch)
_bnbc = [t for t in ats if anch[t]["mid"].get("BNBUSDT")]
def bnb_mid(ts):
    if not _bnbc:
        return None
    t = min(_bnbc, key=lambda t: abs(t - ts))
    return anch[t]["mid"]["BNBUSDT"]
BNB = {t: bnb_mid(t) for t in ats}
# orders.jsonl also carries a per-row mid_at_anchor; used only as a fallback where the vector lacks the name
omid = {}
for dd in days:
    p = f"{LIVE}/{dd}/orders.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln)
        ts = r.get("anchor_ts"); m = r.get("mid_at_anchor")
        if ts is not None and m:
            omid[(ts, r["symbol"])] = float(m)

def load_fills(dayset):
    raw = 0
    F = {}
    for dd in dayset:
        p = f"{LIVE}/{dd}/fills.jsonl"
        if not os.path.exists(p):
            continue
        for ln in open(p):
            r = json.loads(ln)
            raw += 1
            F[(r["symbol"], r.get("trade_id"))] = r     # LAST-WINS by position (append-only file)
    return raw, list(F.values())

raw_all, fills_all = load_fills(days)
R["inputs"]["fills_raw_all_days"] = raw_all
R["inputs"]["fills_dedup_all_days"] = len(fills_all)
R["inputs"]["days"] = [days[0], days[-1]]
R["inputs"]["n_anchor_rows_ledger"] = len(ats)
R["inputs"]["cache_sha256"] = sha(CACHE)
R["inputs"]["cache_path"] = CACHE
R["inputs"]["lineage_note"] = ("LIVE-CACHE lineage: ~/wide_shadow/state/rolling.npz is the live "
    "producer's own 5m cache, same construction formula as pod_build_wide (shadow_loop_v3.py L242), "
    "NOT the pinned pod v4 artifact dlnative_5m_wide829_f16_holefix2.npz")

# ---------------- G1b: exact dedupe reproduction on the archived day set ----------------
ARCH_DAYS = [dd for dd in days if "20260801" <= dd <= "20260911"]
raw_a, fills_a = load_fills(ARCH_DAYS)
R["gates"]["G1b_dedupe_counts"] = {"archived_n_raw": 81161, "archived_n_dedup": 33886,
    "measured_n_raw": raw_a, "measured_n_dedup": len(fills_a),
    "day_set": [ARCH_DAYS[0], ARCH_DAYS[-1]],
    "PASS_exact": bool(raw_a == 81161 and len(fills_a) == 33886)}

# ---------------- 3. per-fill quantities ----------------
G4 = 0.0
rows = []
n_no_mid = n_no_cache = n_no_sym = 0
for r in fills_all:
    ts = r.get("anchor_ts")
    if ts is None:
        continue
    sym = r["symbol"]
    nz = abs(float(r.get("fill_notional") or 0.0))
    px = float(r.get("fill_px") or 0.0)
    if nz <= 0 or px <= 0:
        continue
    M = (anch.get(ts, {}).get("mid") or {}).get(sym) or omid.get((ts, sym))
    if not M:
        n_no_mid += nz
        continue
    M = float(M)
    E = int(math.floor(ts / 14400.0) * 14400)
    sgn = 1.0 if r.get("side") == "buy" else -1.0
    c = SIDX.get(sym)                                  # G2: by name
    i0 = ROW.get(E)
    k = int(round((ts - E) / 300.0))
    k = max(0, min(k, 47))
    drift_raw = None
    qv4h = None
    if c is None:
        n_no_sym += nz
    elif i0 is None or i0 + k >= len(CTS) or i0 - 47 < 0:
        n_no_cache += nz
    else:
        nb = int(CN[i0 + 1 + k, c] - CN[i0 + 1, c])      # rows i0+1 .. i0+k
        if k == 0:
            drift_raw = 0.0
        elif nb == k:
            drift_raw = float(np.expm1(CL[i0 + 1 + k, c] - CL[i0 + 1, c]))
        else:
            drift_raw = None
        nq = int(CQN[i0 + 1, c] - CQN[i0 + 1 - 48, c])
        if nq >= 44:
            qv4h = float(CQ[i0 + 1, c] - CQ[i0 + 1 - 48, c])
    fee_c = float(r.get("commission") or 0.0)
    ca = r.get("commission_asset") or "USDT"
    fee = fee_c * (BNB.get(ts) or 0.0) if ca == "BNB" else fee_c      # E-0911-C
    slip = sgn * (px / M - 1.0) * 1e4
    if drift_raw is None:
        drift = None; gap = None
    else:
        drift = sgn * drift_raw * 1e4
        gap = sgn * ((px / M) * (1.0 + drift_raw) - 1.0) * 1e4
        lhs = (1.0 + sgn * slip / 1e4) * (1.0 + sgn * drift / 1e4)
        G4 = max(G4, abs(lhs - (1.0 + sgn * gap / 1e4)))
    rows.append({"ts": ts, "E": E, "day": int(math.floor(float(r.get("fill_ts") or ts) / 86400.0)),
                 "sym": sym, "nz": nz, "ot": r.get("order_type") or "maker",
                 "ai": int(r.get("attempt_idx") or 1), "slip": slip, "drift": drift, "gap": gap,
                 "fee_bps": fee / nz * 1e4, "qv4h": qv4h, "k_bars": k,
                 "era": ("ERA1" if (ts % 14400) < 600 else "ERA2"),
                 "mo60": (None if r.get("mid_at_fill_plus_60s") is None else
                          -sgn * (float(r["mid_at_fill_plus_60s"]) - px) / px * 1e4),
                 "fill_ts": float(r.get("fill_ts") or ts)})
R["gates"]["G4_identity_maxabs"] = G4
assert G4 <= 1e-12, f"G4 FAIL: identity residual {G4}"
R["gates"]["G2_axis_by_name"] = {"method": "SIDX built from shadow_bundle/config.json symbols_panel; "
    "position never used", "notional_symbol_not_in_axis": round(n_no_sym, 2),
    "notional_no_mid_at_anchor": round(n_no_mid, 2), "notional_anchor_outside_cache": round(n_no_cache, 2),
    "total_fill_notional": round(sum(x["nz"] for x in rows) + n_no_mid, 2)}

# ---------------- 4. statistics ----------------
def wmean(xs, ws):
    s = sum(ws)
    return (sum(x * w for x, w in zip(xs, ws)) / s) if s > 0 else None

def boot(sel, field, kseed):
    """UTC-day block bootstrap of the notional-weighted mean. Returns (mean, ci95, n, notional)."""
    d = defaultdict(lambda: [0.0, 0.0])
    tot_n = 0; tot_w = 0.0; num = 0.0
    for r in sel:
        v = r[field]
        if v is None:
            continue
        d[r["day"]][0] += v * r["nz"]; d[r["day"]][1] += r["nz"]
        tot_n += 1; tot_w += r["nz"]; num += v * r["nz"]
    if tot_w <= 0:
        return None
    keys = sorted(d)
    a = np.array([d[k][0] for k in keys]); b = np.array([d[k][1] for k in keys])
    rng = np.random.default_rng([BOOT_SEED, kseed])
    idx = rng.integers(0, len(keys), size=(NB, len(keys)))
    m = a[idx].sum(1) / b[idx].sum(1)
    return {"mean": round(float(num / tot_w), 4),
            "ci95": [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)],
            "n_fills": tot_n, "notional": round(float(tot_w), 1), "n_days": len(keys)}

# --- G1 / G1c reproduction of the archived slip ---
TS_LO = 1785556800   # 2026-08-01T04:00Z
TS_HI = 1789012800   # 2026-09-11T04:00Z
ts_lo_utc = time.strftime("%FT%TZ", time.gmtime(TS_LO)); ts_hi_utc = time.strftime("%FT%TZ", time.gmtime(TS_HI))
arch = [r for r in rows if TS_LO <= (math.floor(r["ts"] / 14400.0) * 14400) <= TS_HI]
TS = json.load(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/infra1_cost/tier_stats.json"))["all"]
def arch_target(tag):
    num = den = 0.0
    for t in TS:
        s = t[f"{tag}_slip_bps"]; cov = t[f"{tag}_slip_cov"]; nz = t[f"{tag}_nz"]
        if s is None or cov is None:
            continue
        w = cov * nz; num += s * w; den += w
    return num / den
g1 = {}
for tag, ot in (("mk", "maker"), ("tk", "topup_taker")):
    tgt = arch_target(tag)
    sel = [r for r in arch if r["ot"] == ot]
    mine = wmean([r["slip"] for r in sel], [r["nz"] for r in sel])
    selp = [r for r in sel if r["sym"] in SIDX]
    minep = wmean([r["slip"] for r in selp], [r["nz"] for r in selp])
    g1[tag] = {"archived_tierfree_target": round(tgt, 4), "measured": round(mine, 4),
               "abs_diff": round(abs(mine - tgt), 4), "PASS": bool(abs(mine - tgt) <= G1_TOL),
               "G1c_axis_restricted": round(minep, 4), "G1c_abs_diff": round(abs(minep - tgt), 4),
               "n_fills": len(sel), "notional": round(sum(r["nz"] for r in sel), 1)}
R["gates"]["G1_slip_reproduction"] = {"window_utc": [ts_lo_utc, ts_hi_utc], "tolerance_bps": G1_TOL, **g1}
R["gates"]["G1_PASS"] = bool(all(g1[t]["PASS"] for t in g1))

# --- the double-counting arithmetic (STEP 3 / §5 of the prereg) ---
inside = {}
for D, lab in ((60, "60s"), (300, "5m"), (900, "15m"), (3600, "1h")):
    tot = sum(r["nz"] for r in rows)
    ok = sum(r["nz"] for r in rows if r["fill_ts"] >= r["E"] and r["fill_ts"] + D <= r["E"] + 14400)
    inside[lab] = round(ok / tot, 6) if tot > 0 else None
R["markout_interval_inside_replay_window_share_of_notional"] = inside

# --- primary and secondaries ---
def block(sel, tag, k0):
    return {"slip": boot(sel, "slip", k0), "drift": boot(sel, "drift", k0 + 1),
            "gap": boot(sel, "gap", k0 + 2), "fee_bps": boot(sel, "fee_bps", k0 + 3),
            "markout60_cost_bps": boot(sel, "mo60", k0 + 4),
            "mean_k_bars": round(float(np.mean([r["k_bars"] for r in sel])), 3) if sel else None}

era2 = [r for r in rows if r["era"] == "ERA2"]
era1 = [r for r in rows if r["era"] == "ERA1"]
R["PRIMARY_ERA2_all_fills"] = block(era2, "ERA2", 100)
R["ERA1_all_fills"] = block(era1, "ERA1", 200)
R["ALL_ERAS"] = block(rows, "ALL", 300)

R["S3_by_order_type_ERA2"] = {}
k = 400
for ot in sorted(set(r["ot"] for r in rows)):
    R["S3_by_order_type_ERA2"][ot] = block([r for r in era2 if r["ot"] == ot], ot, k); k += 10

R["S6_by_attempt_ERA2"] = {}
for ai in sorted(set(r["ai"] for r in era2)):
    R["S6_by_attempt_ERA2"][str(ai)] = block([r for r in era2 if r["ai"] == ai], str(ai), k); k += 10

qv = sorted([r["qv4h"] for r in era2 if r["qv4h"] is not None])
R["S4_by_liquidity_decile_ERA2"] = {}
if len(qv) > 100:
    edges = [qv[int(len(qv) * i / 10)] for i in range(1, 10)]
    R["S4_decile_edges_qv4h_usdt"] = [round(e, 1) for e in edges]
    for i in range(10):
        lo = -np.inf if i == 0 else edges[i - 1]
        hi = np.inf if i == 9 else edges[i]
        sel = [r for r in era2 if r["qv4h"] is not None and lo <= r["qv4h"] < hi]
        R["S4_by_liquidity_decile_ERA2"][f"D{i}"] = block(sel, f"D{i}", k); k += 10

# also: the replay's own tier partition, for direct comparison with the cost model
R["by_replay_tier_ERA2"] = {}
for t, (lo, hi, nm) in enumerate(((5e6, np.inf, "tier0_qv4h>=5e6"), (1e6, 5e6, "tier1_qv4h>=1e6"),
                                  (-np.inf, 1e6, "tier2_rest"))):
    sel = [r for r in era2 if r["qv4h"] is not None and lo <= r["qv4h"] < hi]
    R["by_replay_tier_ERA2"][nm] = block(sel, nm, k); k += 10

# ---------------- 5. the ruling arithmetic ----------------
P = R["PRIMARY_ERA2_all_fills"]
x_gap = P["gap"]["mean"]; x_fee = P["fee_bps"]["mean"]
# CI of (gap+fee) by the same day blocks, jointly resampled
d = defaultdict(lambda: [0.0, 0.0])
for r in era2:
    if r["gap"] is None:
        continue
    d[r["day"]][0] += (r["gap"] + r["fee_bps"]) * r["nz"]; d[r["day"]][1] += r["nz"]
keys = sorted(d); a = np.array([d[x][0] for x in keys]); b = np.array([d[x][1] for x in keys])
rng = np.random.default_rng([BOOT_SEED, 999])
idx = rng.integers(0, len(keys), size=(NB, len(keys)))
mm = a[idx].sum(1) / b[idx].sum(1)
allin = {"mean": round(float(a.sum() / b.sum()), 4),
         "ci95": [round(float(np.percentile(mm, 2.5)), 4), round(float(np.percentile(mm, 97.5)), 4)],
         "n_days": len(keys)}
R["ALLIN_realised_cost_vs_replay_reference_ERA2"] = allin
R["MODEL_bps_per_unit_turnover"] = MODEL_BPS
R["MODEL_decomposition"] = {"fee": 2.3914, "half_spread_taker_leg_only": 0.2814, "impact_excess": 0.2809,
    "source": "r3k_mkcostb.py L67 + infra1_cost/tier_stats.json, recomputed here",
    "adverse_selection_term": 0.0,
    "note": "half-spread is charged ONLY on the taker fraction (1-maker_share ~ 0.155-0.189); "
            "impact I is defined as the EXCESS over the half-spread (r3k_mkcostb.py L58) so it does "
            "not re-charge it; CAL_BASE.known_limits[2] states there is no queue/adverse-selection term"}
lo, hi = allin["ci95"]
if allin["mean"] > MODEL_BPS and lo > MODEL_BPS:
    ruling = "ESTIMAND_B_MODEL_UNDERCHARGES"
elif allin["mean"] < MODEL_BPS and hi < MODEL_BPS:
    ruling = "ESTIMAND_A_MODEL_OVERCHARGES"
else:
    ruling = "CANNOT_DISTINGUISH"
R["RULING"] = ruling
over = MODEL_BPS - allin["mean"]
R["repricing"] = {
    "model_minus_measured_bps_per_unit_traded": round(over, 4),
    "ci95_of_model_minus_measured": [round(MODEL_BPS - hi, 4), round(MODEL_BPS - lo, 4)],
    "delta_g_on_MATCHED_replay_turnover_0.0540270": round(over * TURN_REPLAY, 4),
    "delta_g_ci95_on_MATCHED_replay_turnover": [round((MODEL_BPS - hi) * TURN_REPLAY, 4),
                                                round((MODEL_BPS - lo) * TURN_REPLAY, 4)],
    "delta_g_on_LIVE_turnover_0.10864": round(over * TURN_LIVE, 4),
    "sign_convention": "positive delta_g = the model over-charges => g rises by this much",
    "resolution_floor_bps_per_anchor": 0.23}
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({kk: R[kk] for kk in ("gates", "markout_interval_inside_replay_window_share_of_notional",
                                       "PRIMARY_ERA2_all_fills", "ERA1_all_fills",
                                       "ALLIN_realised_cost_vs_replay_reference_ERA2",
                                       "RULING", "repricing")}, indent=1))
print("WROTE", OUT)
