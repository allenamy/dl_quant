#!/usr/bin/env python3
"""r21_bridge.py -- Part B: the cost SAME-EVENT bridge (PREREG_r21 sha256 c4de6df3... SS B1-B5).

For every deduped LIVE fill in the window E in [2026-08-23 00Z, 2026-09-10 20Z], on ONE price clock:
    fee_bps            commission (BNB rows converted at the anchor's BNBUSDT mid, E-0911-C) / fill notional
    slip_run           sgn*(F/M - 1)*1e4        M = ledger mid_at_anchor (executor anchor-RUN start, E+23..24 min)
    drift_E            sgn*(M/mid_E - 1)*1e4    mid_E := M / prod_{rows E+1..E+k}(1+ret5)   (pinned pod 5m cache, channel BY NAME, no expm1)
    gap_E              sgn*(F/mid_E - 1)*1e4    == exact composition of slip_run and drift_E (asserted)
    realised_vs_E      fee_bps + gap_E          what the desk paid RELATIVE TO THE REPLAY'S OWN REFERENCE (close at E)
    realised_vs_run    fee_bps + slip_run       what estimand A measured (relative to the anchor-run mid)
    modelled           costb_PWR_G230k blended tier rate for (E, symbol) = fee_model + halfspread(taker leg) + impact
    gap_model          modelled - realised_vs_E (+ = replay over-charges relative to its own reference)
READ-ONLY on ~/dl_quant_live and ~/wide_shadow. ENV WHITELIST = EXPLICITLY EMPTY (asserted). PREREG sha asserted.
"""
import os, sys, json, time, hashlib, math, gzip, calendar
from collections import defaultdict, Counter
_FORBIDDEN = ["LEGS", "PHI", "CAL", "MEMBERS_TOPN", "COSTB_JSON", "PANEL_IN", "V2", "OUT_TAG", "W3FIX", "FTRIM", "UMASK_SCOPE",
              "SLOW_NPY", "FPRED", "FSEED", "LOOK", "WRULE", "TRADE_TOPN", "UMASK_NPZ", "SHADOW_OFFSET_MIN", "RNSM", "FTPOS",
              "LTRIM_TH", "CDAMP", "CEM_Q", "CEM_MODE", "R12_NULL", "R21_DOSE"]
_present = sorted(k for k in _FORBIDDEN if k in os.environ)
assert _present == [], f"E-0826-D: caliber flags present: {_present}"
ENV_WHITELIST = []
import numpy as np
def _no_env(*a, **k): raise AssertionError("r21_bridge ENV WHITELIST is EMPTY: this device reads no environment variable")
os.environ.get = _no_env

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
R21 = f"{ROOT}/r21_nulls_costbridge"
PREREG = f"{R21}/PREREG_r21_2026-09-12.md"
PREREG_SHA = "c4de6df3a37483462d4e10373c30ea4137c02c78f9a23e06148007c5ce246232"
SLICE = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/r21/r21_slice.npz"
SLICE_SHA = "2572bd1eeb1f3e674c638f3440affb08fbe5cd5c030c203b109276e1e2a12c42"
COSTB = f"{ROOT}/r3k_impact/costb_PWR_G230k.json"; COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
TIERS = f"{ROOT}/infra1_cost/tier_stats.json"; TIERS_SHA = "f473286943906b7836c1609f9480b263f2f6c24a45a27e327dcda0064bbe47a7"
R14 = f"{ROOT}/r14_estimand/receipts/RECEIPT_r14_gap_2026-09-12.json"; R14_SHA = "f5a8cd3c941fe779a604e041f0c09e23348a2b8ed9f2bfc3d10a03409e79c2e9"
LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SHADOW = "/Users/haosiyu/wide_shadow"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""): h.update(c)
    return h.hexdigest()
for p, s in ((PREREG, PREREG_SHA), (SLICE, SLICE_SHA), (COSTB, COSTB_SHA), (TIERS, TIERS_SHA), (R14, R14_SHA)):
    got = sha(p); assert got == s, f"{p} sha mismatch {got}"
SELF_SHA = sha(os.path.abspath(__file__))
NB = 2000; BOOT_SEED = 20260905
TURN_REPLAY = 0.0540270; TURN_LIVE = 0.10864; RES_FLOOR = 0.23
E0 = calendar.timegm((2026, 8, 23, 0, 0, 0)); E1 = calendar.timegm((2026, 9, 10, 20, 0, 0))
T_COMBO = calendar.timegm((2026, 8, 26, 4, 0, 0)); T_LEV2 = calendar.timegm((2026, 9, 3, 0, 0, 0))
R = {"self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "env_whitelist": ENV_WHITELIST, "env_whitelist_declared": "EXPLICITLY EMPTY SET (asserted at runtime)",
     "utc": time.strftime("%FT%TZ", time.gmtime()), "inputs": {}, "gates": {}, "window": {"E_first_utc": time.strftime("%FT%TZ", time.gmtime(E0)), "E_last_utc": time.strftime("%FT%TZ", time.gmtime(E1)), "grid_anchors": 114}}

# ---------------- pinned pod 5m cache slice (BY NAME) ----------------
Z = np.load(SLICE, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); SYM = [str(s) for s in Z["symbols"]]; SIDX = {s: i for i, s in enumerate(SYM)}
assert [str(c) for c in Z["channels"]][int(Z["ret5_channel_index"])] == "ret5"
RET = np.asarray(Z["ret5"], np.float64); assert (np.diff(CTS) == 300).all()
ROW = {int(t): i for i, t in enumerate(CTS)}
fin = np.isfinite(RET)
CL = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])
CN = np.concatenate([np.zeros((1, RET.shape[1]), np.int64), np.cumsum(fin, 0)])
QE = Z["E_ts"].astype(np.int64); QVK = np.asarray(Z["qvk"], np.float64); EIDX = {int(t): i for i, t in enumerate(QE)}
R["inputs"]["slice"] = {"path": SLICE, "sha256": SLICE_SHA, "cache_path": str(Z["cache_path"]), "cache_sha256": str(Z["cache_sha256"]), "meta_path": str(Z["meta_path"]),
                        "meta_sha256": str(Z["meta_sha256"]), "rows": int(len(CTS)), "ts_first": time.strftime("%FT%TZ", time.gmtime(int(CTS[0]))), "ts_last": time.strftime("%FT%TZ", time.gmtime(int(CTS[-1]))),
                        "lineage": "PINNED pod v4 cache dlnative_5m_wide829_f16_holefix2_x0910 (r6 extension of the CALIBER_PIN cache); ret5 = close-to-close SIMPLE 5m return, row ts = bar CLOSE time; NO expm1"}
def prod_rows(c, a, b):
    """prod(1+ret5)-1 over cache rows a..b inclusive; None if any bar missing / out of range."""
    if a > b: return 0.0
    if a < 0 or b + 1 >= CL.shape[0]: return None
    if int(CN[b + 1, c] - CN[a, c]) != (b - a + 1): return None
    return float(np.expm1(CL[b + 1, c] - CL[a, c]))
# LIVE-CACHE lineage (G-B2 cross-check only)
zr = np.load(f"{SHADOW}/state/rolling.npz", allow_pickle=True)
RTS = zr["ts"].astype(np.int64); RRET = np.asarray(zr["data"][:, :, 0], np.float64); del zr    # channel 0 = ret5 (shadow_loop_v3.bars_to_channels; same order as the pod cache `ch`)
cfg = json.load(open(f"{SHADOW}/shadow_bundle/config.json")); RSYM = [str(s) for s in cfg["symbols_panel"]]
assert RSYM == SYM, "rolling.npz symbol axis != pinned cache axis"
assert (np.diff(RTS) == 300).all()
RROW = {int(t): i for i, t in enumerate(RTS)}
rfin = np.isfinite(RRET)
RCL = np.concatenate([np.zeros((1, RRET.shape[1])), np.cumsum(np.where(rfin, np.log1p(np.clip(RRET, -0.99, None)), 0.0), 0)])
RCN = np.concatenate([np.zeros((1, RRET.shape[1]), np.int64), np.cumsum(rfin, 0)])
def rprod_rows(c, a, b):
    if a > b: return 0.0
    if a < 0 or b + 1 >= RCL.shape[0]: return None
    if int(RCN[b + 1, c] - RCN[a, c]) != (b - a + 1): return None
    return float(np.expm1(RCL[b + 1, c] - RCL[a, c]))
R["inputs"]["rolling_npz"] = {"path": f"{SHADOW}/state/rolling.npz", "sha256": sha(f"{SHADOW}/state/rolling.npz"), "rows": int(len(RTS)), "lineage": "LIVE-CACHE (cross-check only, G-B2)"}

# ---------------- cost model: tier rates and their decomposition ----------------
CB = json.load(open(COSTB)); TS = json.load(open(TIERS))["all"]
TIER = []
for t, (cj, st) in enumerate(zip(CB["tiers"], TS)):
    f = st["mk_nz"] / (st["mk_nz"] + st["tk_nz"]); I = CB["impact_bps_by_tier"][t]
    fee_m = st["mk_fee_bps"]; fee_t = st["tk_fee_bps"]; hs = st["spread_bps"] / 2.0
    assert abs(fee_m + I - cj["maker_bps"]) < 1e-5 and abs(fee_t + hs + I - cj["taker_bps"]) < 1e-5 and abs(f - cj["maker_share"]) < 1e-5, (t, cj, st)
    comp = {"fee": f * fee_m + (1 - f) * fee_t, "halfspread_taker_leg": (1 - f) * hs, "impact": I}
    blended = comp["fee"] + comp["halfspread_taker_leg"] + comp["impact"]          # unrounded components; the JSON rates are rounded to 6 dp
    assert abs(blended - (f * cj["maker_bps"] + (1 - f) * cj["taker_bps"])) < 1e-4, (t, blended, cj)
    TIER.append({"name": cj["name"], "blended": blended, **comp, "maker_share": f, "maker_bps": cj["maker_bps"], "taker_bps": cj["taker_bps"],
                 "blended_from_json_rounded": f * cj["maker_bps"] + (1 - f) * cj["taker_bps"]})
R["inputs"]["cost_model"] = {"path": COSTB, "sha256": COSTB_SHA, "tier_stats_sha256": TIERS_SHA, "tiers": TIER, "book_avg_bps_per_unit_turnover": CB["book_avg_bps_per_unit_turnover"]}
def tier_of(q):
    if not np.isfinite(q): return 2
    return 0 if q >= 5e6 else (1 if q >= 1e6 else 2)

# ---------------- ledgers, READ-ONLY ----------------
days = sorted(x for x in os.listdir(LIVE) if x.isdigit())
ANCH = {}; ANCH_BY_DAY = defaultdict(list)
for dd in days:
    p = f"{LIVE}/{dd}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str): mid = json.loads(mid)
        ANCH[float(ts)] = {"day": dd, "mid": mid or {}, "halted": r.get("opening_halted"), "target_gross": r.get("target_gross"), "realized_gross": r.get("realized_gross")}
        ANCH_BY_DAY[dd].append(float(ts))
_bnbc = sorted(t for t in ANCH if ANCH[t]["mid"].get("BNBUSDT"))
def bnb_mid(ts):
    t = min(_bnbc, key=lambda x: abs(x - ts)); return float(ANCH[t]["mid"]["BNBUSDT"]), abs(t - ts)
ORD = []; OMID = {}
for dd in days:
    p = f"{LIVE}/{dd}/orders.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ORD.append(r)
        if r.get("anchor_ts") is not None and r.get("mid_at_anchor"): OMID[(float(r["anchor_ts"]), r["symbol"])] = float(r["mid_at_anchor"])
FIL = {}; raw = 0; raw_by_day = Counter()
for dd in days:
    p = f"{LIVE}/{dd}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); raw += 1; raw_by_day[dd] += 1
        r["_day_file"] = dd
        FIL[(r["symbol"], r.get("trade_id"))] = r          # LAST-WINS by file position (append-only; duplicates are backfill_markout rows BY DESIGN)
FIL = list(FIL.values())
R["inputs"]["ledger"] = {"days": [days[0], days[-1]], "n_days": len(days), "anchor_rows": len(ANCH), "orders_rows": len(ORD), "fills_raw": raw, "fills_dedup_last_wins": len(FIL),
                         "read_utc": R["utc"], "join_rule": "fill.anchor_ts exact match to anchors.jsonl row; else nearest anchor row IN THE SAME DAY FILE within 60 s; never the canonical epoch"}

def find_anchor(ts, dd):
    if ts in ANCH: return ts, "exact"
    c = ANCH_BY_DAY.get(dd, [])
    if c:
        t = min(c, key=lambda x: abs(x - ts))
        if abs(t - ts) < 60: return t, "nearest_same_day"
    return None, "none"

# ---------------- G-B1: reproduce r14's PRIMARY ERA2 slip / fee with r14's own definitions ----------------
r14 = json.load(open(R14)); P14 = r14["PRIMARY_ERA2_all_fills"]
E_R14 = calendar.timegm((2026, 9, 12, 0, 0, 0))
g_num_s = g_num_f = g_den = 0.0; g_n = 0
for r in FIL:
    ts = r.get("anchor_ts")
    if ts is None: continue
    ts = float(ts); E = int(math.floor(ts / 14400.0) * 14400)
    if (ts % 14400) < 600 or E > E_R14: continue
    nz = abs(float(r.get("fill_notional") or 0.0)); px = float(r.get("fill_px") or 0.0)
    if nz <= 0 or px <= 0: continue
    M = (ANCH.get(ts, {}).get("mid") or {}).get(r["symbol"]) or OMID.get((ts, r["symbol"]))
    if not M: continue
    sgn = 1.0 if r.get("side") == "buy" else -1.0
    fee_c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
    fee = fee_c * bnb_mid(ts)[0] if ca == "BNB" else fee_c
    g_num_s += sgn * (px / float(M) - 1.0) * 1e4 * nz; g_num_f += fee / nz * 1e4 * nz; g_den += nz; g_n += 1
gb1 = {"r14_slip": P14["slip"]["mean"], "mine_slip": round(g_num_s / g_den, 4), "r14_fee": P14["fee_bps"]["mean"], "mine_fee": round(g_num_f / g_den, 4), "r14_n_fills": P14["slip"]["n_fills"], "mine_n_fills": g_n,
       "r14_notional": P14["slip"]["notional"], "mine_notional": round(g_den, 1), "tolerance_bps": 0.05}
gb1["PASS"] = bool(abs(gb1["mine_slip"] - gb1["r14_slip"]) <= 0.05 and abs(gb1["mine_fee"] - gb1["r14_fee"]) <= 0.05)
R["gates"]["G_B1_r14_reproduction"] = gb1
assert gb1["PASS"], gb1

# ---------------- per-fill quantities in the window ----------------
rows = []; excl = Counter(); excl_nz = Counter(); G4 = 0.0; join_kind = Counter(); bnb_gap_max = 0.0
flat = {"n": 0, "notional": 0.0, "fee_usdt": 0.0, "anchor_ts": set(), "days": set()}
for r in FIL:
    ts = r.get("anchor_ts")
    if ts is None: excl["no_anchor_ts"] += 1; continue
    ts = float(ts); E = int(math.floor(ts / 14400.0) * 14400)
    if E < E0 or E > E1: continue
    nz = abs(float(r.get("fill_notional") or 0.0)); px = float(r.get("fill_px") or 0.0); sym = r["symbol"]
    if nz <= 0 or px <= 0: excl["bad_px_or_nz"] += 1; continue
    ot = r.get("order_type") or "maker"
    fee_c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
    if ca == "BNB":
        b, gap = bnb_mid(ts); fee = fee_c * b; bnb_gap_max = max(bnb_gap_max, gap)
    elif ca == "USDT": fee = fee_c
    else: excl["commission_asset_other_" + ca] += 1; excl_nz["commission_asset_other"] += nz; continue
    if ot == "protective_flatten":
        flat["n"] += 1; flat["notional"] += nz; flat["fee_usdt"] += fee; flat["anchor_ts"].add(ts); flat["days"].add(r["_day_file"]); continue
    at, jk = find_anchor(ts, r["_day_file"]); join_kind[jk] += 1
    if at is None: excl["no_anchor_row"] += 1; excl_nz["no_anchor_row"] += nz; continue
    M = ANCH[at]["mid"].get(sym) or OMID.get((ts, sym))
    if not M: excl["no_mid_at_anchor"] += 1; excl_nz["no_mid_at_anchor"] += nz; continue
    M = float(M); off = ts - E
    if not (20 * 60 <= off <= 30 * 60): excl["offset_outside_20_30min"] += 1; excl_nz["offset_outside_20_30min"] += nz; continue
    c = SIDX.get(sym)
    if c is None: excl["symbol_not_in_axis"] += 1; excl_nz["symbol_not_in_axis"] += nz; continue
    i0 = ROW.get(E)
    if i0 is None: excl["E_not_in_cache"] += 1; excl_nz["E_not_in_cache"] += nz; continue
    k = int(round(off / 300.0)); kf = int(math.floor(off / 300.0))
    d_raw = prod_rows(c, i0 + 1, i0 + k)
    if d_raw is None: excl["cache_bar_missing"] += 1; excl_nz["cache_bar_missing"] += nz; continue
    d_raw_f = prod_rows(c, i0 + 1, i0 + kf)
    ri = RROW.get(E); d_live = rprod_rows(c, ri + 1, ri + k) if ri is not None else None
    sgn = 1.0 if r.get("side") == "buy" else -1.0
    slip = sgn * (px / M - 1.0) * 1e4
    drift = sgn * d_raw * 1e4
    gap = sgn * ((px / M) * (1.0 + d_raw) - 1.0) * 1e4
    G4 = max(G4, abs((1.0 + sgn * slip / 1e4) * (1.0 + sgn * drift / 1e4) - (1.0 + sgn * gap / 1e4)))
    fee_bps = fee / nz * 1e4
    qi = EIDX.get(E); q = np.expm1(min(max(QVK[qi, c], 0.0), 30.0)) * 48.0 if (qi is not None and np.isfinite(QVK[qi, c])) else float("nan")
    t = tier_of(q); TT = TIER[t]
    rows.append({"ts": ts, "E": E, "day": E // 86400, "sym": sym, "nz": nz, "ot": ot, "ai": int(r.get("attempt_idx") or 1), "sgn": sgn, "k": k,
                 "fee": fee_bps, "slip_run": slip, "drift_E": drift, "gap_E": gap, "real_E": fee_bps + gap, "real_run": fee_bps + slip,
                 "gap_E_kfloor": sgn * ((px / M) * (1.0 + (d_raw_f if d_raw_f is not None else d_raw)) - 1.0) * 1e4,
                 "drift_live": (sgn * d_live * 1e4) if d_live is not None else None,
                 "tier": t, "qv4h": q, "model": TT["blended"], "model_fee": TT["fee"], "model_hs": TT["halfspread_taker_leg"], "model_imp": TT["impact"],
                 "gap_model": TT["blended"] - (fee_bps + gap), "gap_model_run": TT["blended"] - (fee_bps + slip),
                 "fee_minus_modelfee": fee_bps - TT["fee"], "slip_minus_modelhsimp": slip - (TT["halfspread_taker_leg"] + TT["impact"]),
                 "subera": ("king" if E < T_COMBO else ("combo_1.5x" if E < T_LEV2 else "combo_2.0x")), "halted": ANCH[at]["halted"]})
R["gates"]["G4_identity_maxabs"] = G4; assert G4 <= 1e-12, G4
R["window"].update({"anchor_rows_in_window": len([t for t in ANCH if E0 <= math.floor(t / 14400) * 14400 <= E1]),
                    "missing_grid_anchors_utc": [time.strftime("%FT%TZ", time.gmtime(e)) for e in range(E0, E1 + 1, 14400) if not any(math.floor(t / 14400) * 14400 == e for t in ANCH)],
                    "halted_anchor_rows_utc": [time.strftime("%FT%TZ", time.gmtime(int(t))) for t in sorted(ANCH) if E0 <= math.floor(t / 14400) * 14400 <= E1 and ANCH[t]["halted"]],
                    "fills_in_price_clock": len(rows), "notional_in_price_clock": round(sum(r["nz"] for r in rows), 1), "excluded_counts": dict(excl), "excluded_notional": {k: round(v, 1) for k, v in excl_nz.items()},
                    "join_kind": dict(join_kind), "bnb_conversion_max_anchor_gap_s": round(bnb_gap_max, 1),
                    "protective_flatten": {"n": flat["n"], "notional": round(flat["notional"], 1), "fee_bps": round(flat["fee_usdt"] / flat["notional"] * 1e4, 4) if flat["notional"] else None,
                                           "n_anchor_ts": len(flat["anchor_ts"]), "days": sorted(flat["days"]), "note": "hangs on an anchor_ts with NO anchors.jsonl row => no mid vector => structurally outside the price clock"}})

# ---------------- statistics: notional-weighted, UTC-day block bootstrap, JOINT resampling ----------------
FIELDS = ["fee", "slip_run", "drift_E", "gap_E", "real_E", "real_run", "model", "model_fee", "model_hs", "model_imp", "gap_model", "gap_model_run",
          "fee_minus_modelfee", "slip_minus_modelhsimp", "gap_E_kfloor", "drift_live"]
def block(sel, kseed):
    out = {"n_fills": len(sel), "notional": round(sum(r["nz"] for r in sel), 1), "n_days": len(set(r["day"] for r in sel))}
    if not sel: return out
    dk = sorted(set(r["day"] for r in sel)); di = {d: i for i, d in enumerate(dk)}
    rng = np.random.default_rng([BOOT_SEED, kseed]); idx = rng.integers(0, len(dk), size=(NB, len(dk)))
    for f in FIELDS:
        a = np.zeros(len(dk)); b = np.zeros(len(dk)); num = den = 0.0; n = 0
        for r in sel:
            v = r.get(f)
            if v is None: continue
            a[di[r["day"]]] += v * r["nz"]; b[di[r["day"]]] += r["nz"]; num += v * r["nz"]; den += r["nz"]; n += 1
        if den <= 0: out[f] = None; continue
        m = a[idx].sum(1) / np.maximum(b[idx].sum(1), 1e-12)
        out[f] = {"mean": round(float(num / den), 4), "ci95": [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)], "n": n}
    return out
R["ALL_fills_in_price_clock"] = block(rows, 1)
R["by_order_type"] = {ot: block([r for r in rows if r["ot"] == ot], 10 + i) for i, ot in enumerate(sorted(set(r["ot"] for r in rows)))}
R["by_subera"] = {s: block([r for r in rows if r["subera"] == s], 20 + i) for i, s in enumerate(["king", "combo_1.5x", "combo_2.0x"])}
R["by_replay_tier"] = {TIER[t]["name"]: block([r for r in rows if r["tier"] == t], 30 + t) for t in range(3)}
R["by_attempt"] = {str(a): block([r for r in rows if r["ai"] == a], 40 + i) for i, a in enumerate(sorted(set(r["ai"] for r in rows)))}
R["excluding_halted_anchors"] = block([r for r in rows if not r["halted"]], 50)
R["by_day"] = {}
for d in sorted(set(r["day"] for r in rows)):
    sel = [r for r in rows if r["day"] == d]; W = sum(r["nz"] for r in sel)
    R["by_day"][time.strftime("%F", time.gmtime(d * 86400))] = {"n": len(sel), "notional": round(W, 1), **{f: round(sum(r[f] * r["nz"] for r in sel) / W, 4) for f in ("fee", "slip_run", "drift_E", "real_E", "model", "gap_model")}}
# G-B2 lineage cross-check on the fills that have both
both = [r for r in rows if r["drift_live"] is not None]
if both:
    W = sum(r["nz"] for r in both)
    R["gates"]["G_B2_lineage_cross_check"] = {"n_fills_with_both": len(both), "drift_E_pod_pinned": round(sum(r["drift_E"] * r["nz"] for r in both) / W, 4),
        "drift_E_live_cache": round(sum(r["drift_live"] * r["nz"] for r in both) / W, 4), "max_abs_per_fill_diff_bps": round(max(abs(r["drift_E"] - r["drift_live"]) for r in both), 4),
        "share_of_fills_identical_1e-6": round(sum(1 for r in both if abs(r["drift_E"] - r["drift_live"]) < 1e-6) / len(both), 4)}

# ---------------- B4: unfilled intent in the window (r17 units, verbatim grouping) ----------------
G = defaultdict(list)
for r in ORD:
    ts = r.get("anchor_ts")
    if ts is None: continue
    E = int(math.floor(float(ts) / 14400.0) * 14400)
    if E0 <= E <= E1: G[(r["rebalance_id"], r["symbol"])].append(r)
def cls(pw, tw):
    if abs(tw) < 1e-15 and abs(pw) > 0: return "ZERO_TARGET"
    if pw * tw < 0: return "FLIP"
    if abs(pw) > 0 and abs(tw) < abs(pw): return "DERISK"
    return "ADD"
CNT = Counter(); sent = []; dust_I = halt_I = 0.0; dust_n = halt_n = 0; halt_by_cls = Counter(); halt_I_by_cls = defaultdict(float)
for (rid, sym), rs in G.items():
    a1 = [r for r in rs if r["order_type"] == "maker" and r["attempt_idx"] == 1]
    if not a1: CNT["no_a1_" + rs[0]["order_type"]] += 1; continue
    ints = [abs(r.get("intended_full") if r.get("intended_full") is not None else (r["intended_notional"] or 0.0)) for r in a1]
    if len(a1) > 1 and max(ints) > 0 and (max(ints) - min(ints)) / max(ints) > 1e-6: CNT["a1_intent_mismatch"] += 1; continue
    m = a1[0]; I = ints[0]; tr = m["terminal_reason"]; a = float(m["anchor_ts"]); E = int(round(a / 14400.0)) * 14400
    if abs(a - E) >= 3600: CNT["offgrid_groups"] += 1; continue
    pw = m["prev_w"] or 0.0; tw = m["target_w"] or 0.0; c = cls(pw, tw); sgn = 1.0 if (tw - pw) >= 0 else -1.0
    if tr == "skipped_min_notional": dust_I += I; dust_n += 1; continue
    if tr == "blocked_by_halt": halt_I += I; halt_n += 1; halt_by_cls[c] += 1; halt_I_by_cls[c] += I; continue
    if tr == "skipped_no_mid": CNT["skipped_no_mid"] += 1; continue
    if I <= 0: CNT["zero_intent"] += 1; continue
    legs = [r for r in rs if r["order_type"] in ("maker", "topup_taker")]
    Fs = sum((r.get("filled_notional") or 0.0) for r in legs); F = abs(Fs)
    if F > 0 and np.sign(Fs) != sgn: CNT["fill_sign_opposite"] += 1; continue
    Fm = sum(abs(r.get("filled_notional") or 0.0) for r in legs if r["order_type"] == "maker"); Ft = sum(abs(r.get("filled_notional") or 0.0) for r in legs if r["order_type"] == "topup_taker")
    sent.append({"cls": c, "I": I, "F": min(F, I), "F_raw": F, "Fm": Fm, "Ft": Ft, "E": E, "day": E // 86400})
sI = sum(s["I"] for s in sent); sF = sum(s["F"] for s in sent)
B4 = {"unit": "(rebalance_id, symbol) group; I = |intended_full| of the maker attempt-1 row; F = sum|filled_notional| over maker + topup_taker rows, capped at I (r17 SS2.1 verbatim)",
      "groups_total": len(G), "sent_groups": len(sent), "dust_groups_skipped_min_notional": dust_n, "halt_groups_blocked_by_halt": halt_n, "other_excluded": dict(CNT),
      "sent_intent_usdt": round(sI, 1), "sent_filled_usdt": round(sF, 1), "fill_fraction_sent_notional_weighted": round(sF / sI, 4) if sI else None,
      "maker_share_of_filled": round(sum(s["Fm"] for s in sent) / max(sum(s["Fm"] + s["Ft"] for s in sent), 1e-9), 4),
      "dust_intent_usdt": round(dust_I, 1), "halt_intent_usdt": round(halt_I, 1),
      "halt_share_of_all_intent": round(halt_I / (sI + dust_I + halt_I), 4) if (sI + dust_I + halt_I) else None,
      "dust_share_of_all_intent": round(dust_I / (sI + dust_I + halt_I), 4) if (sI + dust_I + halt_I) else None,
      "fill_fraction_including_halt_as_zero": round(sF / (sI + halt_I), 4) if (sI + halt_I) else None,
      "halt_groups_by_class": dict(halt_by_cls), "halt_intent_by_class": {k: round(v, 1) for k, v in halt_I_by_cls.items()},
      "by_class": {}, "by_subera": {}}
for c in ("ADD", "DERISK", "FLIP", "ZERO_TARGET"):
    ss = [s for s in sent if s["cls"] == c]; I_ = sum(s["I"] for s in ss); F_ = sum(s["F"] for s in ss)
    B4["by_class"][c] = {"n": len(ss), "intent": round(I_, 1), "filled": round(F_, 1), "f_w": round(F_ / I_, 4) if I_ else None}
for nm, lo, hi in (("king", E0, T_COMBO), ("combo_1.5x", T_COMBO, T_LEV2), ("combo_2.0x", T_LEV2, E1 + 1)):
    ss = [s for s in sent if lo <= s["E"] < hi]; I_ = sum(s["I"] for s in ss); F_ = sum(s["F"] for s in ss)
    B4["by_subera"][nm] = {"n": len(ss), "intent": round(I_, 1), "filled": round(F_, 1), "f_w": round(F_ / I_, 4) if I_ else None}
# fill fraction by UTC day with a day-block CI on the pooled ratio
dk = sorted(set(s["day"] for s in sent)); di = {d: i for i, d in enumerate(dk)}
a = np.zeros(len(dk)); b = np.zeros(len(dk))
for s in sent: a[di[s["day"]]] += s["F"]; b[di[s["day"]]] += s["I"]
rng = np.random.default_rng([BOOT_SEED, 77]); idx = rng.integers(0, len(dk), size=(NB, len(dk))); m = a[idx].sum(1) / b[idx].sum(1)
B4["fill_fraction_ci95_dayblock"] = [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]
# reconcile with the fills-side: sum of filled notional in the price clock vs sum of F over sent groups
B4["reconcile_fills_ledger_vs_orders_ledger"] = {"fills_jsonl_notional_in_price_clock_plus_excluded": round(sum(r["nz"] for r in rows) + sum(excl_nz.values()), 1),
    "orders_jsonl_sum_F_raw_sent_groups": round(sum(s["F_raw"] for s in sent), 1), "note": "the two ledgers count the same executions from two sides; a small gap = groups excluded above (sign-opposite, offgrid) and fills whose rows were dropped"}
R["B4_unfilled_intent"] = B4

# ---------------- POST-HOC reconciliation quantities (NOT in PREREG_r21; reported for interpretation only, not judged) ----------------
# (a) intent-weighted drift over the same [E, E+5k] rows, r14_intent.py definition: attempt-1 orders, weight |intended_full|, sign of the intent
# (b) cross-sectionally demeaned drift on the fills: drift_dm = sgn*(r_i - median_r over the 829 axis on the same rows) -- removes the common market move
# (c) signed fill-notional imbalance (buys - sells) / (buys + sells), overall and per anchor
PH = {"note": "POST-HOC, not pre-registered; reconciliation with r14 (intent-weighted drift ~ 0) and a market-move control; not used in the ruling"}
int_rows = []
for r in ORD:
    if int(r.get("attempt_idx") or 1) != 1 or r.get("order_type") != "maker": continue
    ints = r.get("intended_full") if r.get("intended_full") is not None else r.get("intended_notional")
    if ints is None or float(ints) == 0.0 or r.get("anchor_ts") is None: continue
    ts = float(r["anchor_ts"]); E = int(math.floor(ts / 14400.0) * 14400)
    if E < E0 or E > E1: continue
    c = SIDX.get(r["symbol"]); i0 = ROW.get(E)
    if c is None or i0 is None: continue
    off = ts - E
    if not (20 * 60 <= off <= 30 * 60): continue
    k = int(round(off / 300.0)); d = prod_rows(c, i0 + 1, i0 + k)
    if d is None: continue
    sgn = 1.0 if float(ints) > 0 else -1.0
    int_rows.append({"day": E // 86400, "nz": abs(float(ints)), "drift": sgn * d * 1e4, "filled": abs(float(r.get("filled_notional") or 0.0)), "tr": r.get("terminal_reason")})
def wboot(items, field, wfield, kseed):
    d = defaultdict(lambda: [0.0, 0.0]); num = tot = 0.0; n = 0
    for r in items:
        w = r[wfield]
        if w <= 0: continue
        d[r["day"]][0] += r[field] * w; d[r["day"]][1] += w; num += r[field] * w; tot += w; n += 1
    if tot <= 0: return None
    keys = sorted(d); a = np.array([d[x][0] for x in keys]); b = np.array([d[x][1] for x in keys])
    rng = np.random.default_rng([BOOT_SEED, kseed]); idx = rng.integers(0, len(keys), size=(NB, len(keys)))
    m = a[idx].sum(1) / np.maximum(b[idx].sum(1), 1e-12)
    return {"mean": round(float(num / tot), 4), "ci95": [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)], "n": n, "weight": round(float(tot), 1)}
PH["drift_intent_weighted_all_sent_and_blocked"] = wboot(int_rows, "drift", "nz", 61)
PH["drift_intent_weighted_sent_only"] = wboot([r for r in int_rows if r["tr"] not in ("skipped_min_notional", "blocked_by_halt")], "drift", "nz", 62)
PH["drift_filled_weighted_on_attempt1_orders"] = wboot(int_rows, "drift", "filled", 63)
# market-move control: median 829-axis return over the same rows, per anchor (k from the anchor row)
MED = {}
for r in rows:
    key = (r["E"], r["k"])
    if key in MED: continue
    i0 = ROW[r["E"]]; a, b = i0 + 1, i0 + r["k"]
    ok = (CN[b + 1, :] - CN[a, :]) == (b - a + 1)
    v = np.expm1(CL[b + 1, :] - CL[a, :])[ok]
    MED[key] = float(np.median(v)) if len(v) >= 30 else 0.0
for r in rows:
    r["drift_dm"] = r["sgn"] * ((1.0 + r["sgn"] * r["drift_E"] / 1e4 - 1.0) - MED[(r["E"], r["k"])]) * 1e4
PH["drift_E_demeaned_by_anchor_universe_median"] = wboot(rows, "drift_dm", "nz", 64)
PH["drift_E_demeaned_by_order_type"] = {ot: wboot([r for r in rows if r["ot"] == ot], "drift_dm", "nz", 65 + i) for i, ot in enumerate(sorted(set(r["ot"] for r in rows)))}
PH["universe_median_move_E_to_run_bps_weighted_by_fill_notional"] = round(sum(MED[(r["E"], r["k"])] * r["nz"] for r in rows) / sum(r["nz"] for r in rows) * 1e4, 4)
B = sum(r["nz"] for r in rows if r["sgn"] > 0); S = sum(r["nz"] for r in rows if r["sgn"] < 0)
PH["signed_fill_notional_imbalance"] = {"buys": round(B, 1), "sells": round(S, 1), "(B-S)/(B+S)": round((B - S) / (B + S), 4)}
PH["drift_by_side"] = {"buy": wboot([r for r in rows if r["sgn"] > 0], "drift_E", "nz", 70), "sell": wboot([r for r in rows if r["sgn"] < 0], "drift_E", "nz", 71)}
R["POST_HOC_reconciliation"] = PH

# ---------------- B5 ruling ----------------
A = R["ALL_fills_in_price_clock"]; gm = A["gap_model"]
lo, hi = gm["ci95"]
ruling = "REPLAY_OVERCHARGES_vs_OWN_REFERENCE" if lo > 0 else ("REPLAY_UNDERCHARGES_vs_OWN_REFERENCE" if hi < 0 else "INDISTINGUISHABLE")
R["RULING"] = {"statistic": "gap_model = modelled - realised_vs_E, bps per unit FILLED notional, notional-weighted, UTC-day block bootstrap B=2000", "mean": gm["mean"], "ci95": gm["ci95"], "ruling": ruling,
    "decomposition_of_gap_model": {"fee_model_minus_fee_paid": A["model_fee"]["mean"] - A["fee"]["mean"],
                                   "halfspread_plus_impact_model_minus_slip_run": (A["model_hs"]["mean"] + A["model_imp"]["mean"]) - A["slip_run"]["mean"],
                                   "minus_drift_E_to_run_plus_cross": -(A["gap_E"]["mean"] - A["slip_run"]["mean"]),
                                   "check_sum": (A["model_fee"]["mean"] - A["fee"]["mean"]) + ((A["model_hs"]["mean"] + A["model_imp"]["mean"]) - A["slip_run"]["mean"]) - (A["gap_E"]["mean"] - A["slip_run"]["mean"])},
    "delta_g_on_MATCHED_replay_turnover_0.0540270": {"mean": round(gm["mean"] * TURN_REPLAY, 4), "ci95": [round(lo * TURN_REPLAY, 4), round(hi * TURN_REPLAY, 4)], "resolution_floor": RES_FLOOR},
    "delta_g_on_LIVE_turnover_0.10864": {"mean": round(gm["mean"] * TURN_LIVE, 4), "ci95": [round(lo * TURN_LIVE, 4), round(hi * TURN_LIVE, 4)]},
    "for_reference_gap_vs_anchor_run_mid_estimand_A": A["gap_model_run"],
    "sign_convention": "+ gap_model = the replay charges MORE than the desk paid relative to the replay's own reference price (close at E)"}
os.makedirs(f"{R21}/receipts", exist_ok=True)
OUT = f"{R21}/receipts/RECEIPT_r21_bridge_2026-09-12.json"
json.dump(R, open(OUT, "w"), indent=1)
with gzip.open(f"{R21}/receipts/r21_fills_table.json.gz", "wt") as f: json.dump(rows, f)
print(json.dumps({k: R[k] for k in ("gates", "window", "ALL_fills_in_price_clock", "RULING")}, indent=1))
print(json.dumps({k: {kk: (vv["mean"] if isinstance(vv, dict) and "mean" in vv else vv) for kk, vv in v.items() if kk in ("n_fills", "notional", "fee", "slip_run", "drift_E", "real_E", "model", "gap_model")} for k, v in R["by_order_type"].items()}, indent=1))
print(json.dumps({k: v for k, v in B4.items() if k not in ("by_subera",)}, indent=1))
print("WROTE", OUT)
