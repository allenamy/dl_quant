#!/usr/bin/python3
"""T3 main device — PREREG_T3_markout_curve_2026-09-13.md §3 (sha c7be8500...), gates G4-G6, judgement.

Effective per-unit-turnover cost of a PASSIVELY executed 4 h cross-sectional reversal book, transferred from the
live executor's own maker-leg intents (PROGRAM AMENDMENT 1 item 3):
    c_eff = [ sum fee_usdt + sum N_f * s*(F/P_E - 1) + sum U * s*y4_E ] / sum I          (bps per unit intended turnover)
Read-only on every input. ENV WHITELIST = EMPTY SET (asserted; os.environ.get / os.getenv raise after import).
"""
import calendar, hashlib, json, math, os, sys, time
from collections import defaultdict, Counter

T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
PREREG = f"{T3}/PREREG_T3_markout_curve_2026-09-13.md"; PREREG_SHA = "c7be850055160d7eeafe10fb859470f442d3f0552333ba290d9496357be8f8f6"
LOG = f"{T3}/private/ledger_snap_20260913T0455Z"
SLICE = f"{T3}/private/t3_slice.npz"; SLICE_SHA = "951fb883daf5d64cff8442dfe49d752ab766b81a51c1c72954b316683eef6c82"
COSTB = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r3k_impact/costb_PWR_G230k.json"
COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
BOOK_CFG = "/Users/haosiyu/dl_quant_live/config/book.json"          # read-only, for T-A1 in-service values
GATE_BPS = 1.6                                                      # PROGRAM §2 T3 / AMENDMENT 1 item 3 (P6: 1.6036)
NB = 2000; SEED = 20260905
ERA2_LO, ERA2_HI = 22.0, 30.0; ERA1_HI = 3.0
E_MAX = calendar.timegm((2026, 9, 10, 20, 0, 0))

_FORBID = ("CAL", "JUDGE", "PANEL", "W10_", "POD_", "DLW_", "KING_", "SEAT_", "UMASK", "LEGS", "FTRIM", "R12_", "R21_", "PHI", "CEM_Q", "LIVE_MODE")
_hit = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hit, f"E-0826-D: forbidden env present {_hit}"
import numpy as np
from scipy.stats import rankdata
def _no_env(*a, **k):
    raise RuntimeError("E-0826-D: this device reads no environment variable")
os.environ.get = _no_env; os.getenv = _no_env

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
assert sha256(PREREG) == PREREG_SHA, "prereg sha"
assert sha256(SLICE) == SLICE_SHA, "slice sha"
assert sha256(COSTB) == COSTB_SHA, "costb sha"
SELF_SHA = sha256(os.path.abspath(__file__))

def read_jsonl(p):
    out = []
    with open(p) as f: lines = f.readlines()
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln: continue
        try: out.append(json.loads(ln))
        except json.JSONDecodeError:
            if i == len(lines) - 1: continue
            raise
    return out

def utc(ts): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
days = sorted(d for d in os.listdir(LOG) if d.isdigit() and len(d) == 8)

# ---------------- ledger ----------------
anchors = {}
for d in days:
    p = f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for r in read_jsonl(p):
        mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str): mv = json.loads(mv)
        anchors[r["anchor_ts"]] = {"mid": mv or {}, "halted": bool(r.get("opening_halted")), "rid": r.get("rebalance_id")}
ats_sorted = sorted(anchors)
ats_bnb = [t for t in ats_sorted if anchors[t]["mid"].get("BNBUSDT")]
def bnb_px(anchor_ts):
    m = anchors.get(anchor_ts, {}).get("mid", {}).get("BNBUSDT")
    if m: return float(m), 0.0
    t = min(ats_bnb, key=lambda x: abs(x - anchor_ts)); return float(anchors[t]["mid"]["BNBUSDT"]), abs(t - anchor_ts)

fills_raw = []
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if os.path.exists(p): fills_raw.extend(read_jsonl(p))
seen_last = {}
for i, f in enumerate(fills_raw):
    if f.get("trade_id") is not None: seen_last[f["trade_id"]] = i
fills = [f for i, f in enumerate(fills_raw) if f.get("trade_id") is None or seen_last.get(f["trade_id"]) == i]   # collapse_supersedes

orders_by = defaultdict(list); n_orders = 0
for d in days:
    p = f"{LOG}/{d}/orders.jsonl"
    if not os.path.exists(p): continue
    for pos, r in enumerate(read_jsonl(p)):
        r["_pos"] = (d, pos); orders_by[(r["rebalance_id"], r["symbol"])].append(r); n_orders += 1

fills_by = defaultdict(list)
for f in fills:
    fills_by[(f["rebalance_id"], f["symbol"], f.get("order_type"))].append(f)

# ---------------- meta slice ----------------
Z = np.load(SLICE, allow_pickle=False)
SYM = [str(s) for s in Z["symbols"]]; SIDX = {s: j for j, s in enumerate(SYM)}
E_TS = Z["E_ts"].astype(np.int64); EIDX = {int(e): k for k, e in enumerate(E_TS)}
Y4 = Z["y4"].astype(np.float64); QVK = Z["qvk"].astype(np.float64); MEM = Z["members_mask"]
CTS = Z["cache_ts"].astype(np.int64); CIDX = {int(t): k for k, t in enumerate(CTS)}; RET = Z["ret5"].astype(np.float64)
assert [str(c) for c in Z["channels"]][int(Z["ret5_channel_index"])] == "ret5"
QV4H = np.expm1(np.clip(QVK, 0, 30)) * 48.0
CB = json.load(open(COSTB))
T0_EDGE, T1_EDGE = 5e6, 1e6
assert CB["tiers"][0]["name"].startswith("tier0_qv4h>=5e6") and CB["tiers"][1]["name"].startswith("tier1_qv4h>=1e6")

# reversal rank per meta anchor (score = -y4[E-4h]; eligible = member & finite(y4[E-4h]) & qv4h>=2.5e5)
RT = np.full(Y4.shape, np.nan)
for k in range(1, len(E_TS)):
    assert E_TS[k] - E_TS[k - 1] == 14400
    el = MEM[k] & np.isfinite(Y4[k - 1]) & (QV4H[k] >= 2.5e5)
    n = int(el.sum())
    if n >= 10:
        RT[k, el] = rankdata(-Y4[k - 1, el]) / (n - 1) - 0.5

# ---------------- plans ----------------
excl = Counter(); excl_I = defaultdict(float)
plans = []
g4_mid_eq = g4_mid_n = 0
g4_fill_ledger = g4_fill_orders = 0.0
I_disagree = 0; overfill = 0; identity_max = 0.0; guard_excl = Counter(); bnb_gap_max = 0.0
for key, rows in orders_by.items():
    mk = [r for r in rows if r.get("order_type") == "maker"]
    if not mk:
        continue
    rej = [r for r in mk if r.get("attempt_idx") == 1 and r.get("terminal_reason") == "venue_reject" and "-5022" in (r.get("note") or "")]
    sub = [r for r in mk if r.get("submit_ts") is not None]
    if not (sub or rej):
        excl["not_sent:" + "|".join(sorted(set(str(r.get("terminal_reason")) for r in mk)))] += 1
        continue
    a1 = sorted([r for r in mk if r.get("attempt_idx") == 1], key=lambda r: r["_pos"])
    if not a1:
        excl["no_attempt1_maker_row"] += 1; continue
    r0 = a1[0]
    if r0.get("intended_notional") is None or r0.get("mid_at_anchor") in (None, 0):
        excl["missing_intended_or_mid"] += 1; continue
    I = abs(float(r0["intended_notional"]))
    if any(abs(abs(float(r.get("intended_notional") or 0.0)) - I) > 1e-9 * max(I, 1.0) for r in a1): I_disagree += 1
    s = 1.0 if r0.get("side") == "buy" else -1.0
    assert r0.get("side") in ("buy", "sell")
    M_run = float(r0["mid_at_anchor"]); ats = r0["anchor_ts"]
    E = int(math.floor(ats / 14400.0) * 14400); off_min = (ats - E) / 60.0
    era = "ERA2" if ERA2_LO <= off_min <= ERA2_HI else ("ERA1" if off_min <= ERA1_HI else None)
    if era is None:
        excl["anchor_offset_outside_eras"] += 1; excl_I["anchor_offset_outside_eras"] += I; continue
    if E > E_MAX:
        excl["E_after_meta_end"] += 1; excl_I["E_after_meta_end"] += I; continue
    status = "first_send" if not rej else ("requote" if sub else "refused_no_requote")
    arm = next((r.get("placement_arm") for r in a1 if r.get("placement_arm") is not None), None)
    # requote_arm is written on the TOP-UP row for the "direct" arm (the requote was skipped) and on maker rows for
    # "requote"/"exempt" -> read it from ANY row of the plan (fix found at first run: maker-only read never saw "direct")
    rq_arm = next((r.get("requote_arm") for r in sorted(rows, key=lambda r: r["_pos"]) if r.get("requote_arm") is not None), None)
    halted = anchors.get(ats, {}).get("halted", False)
    # G4 (a) mid equality vs anchors vector
    av = anchors.get(ats, {}).get("mid", {}).get(key[1])
    mid_eq = int(av is not None and float(av) == M_run)
    # maker-leg fills
    fl = fills_by.get((key[0], key[1], "maker"), [])
    Nf = sum(abs(float(f["fill_notional"])) for f in fl)
    qty = sum(abs(float(f["fill_notional"])) / float(f["fill_px"]) for f in fl)
    fee = 0.0
    for f in fl:
        c = float(f.get("commission") or 0.0)
        if (f.get("commission_asset") or "USDT") == "BNB":
            px, gap = bnb_px(f.get("anchor_ts")); bnb_gap_max = max(bnb_gap_max, gap); c *= px
        fee += c
    ord_filled = sum(abs(float(r.get("filled_notional") or 0.0)) for r in mk)
    # meta lookups
    j = SIDX.get(key[1]); k = EIDX.get(E)
    if j is None or k is None:
        excl["symbol_or_E_not_in_meta"] += 1; excl_I["symbol_or_E_not_in_meta"] += I; continue
    y4E = Y4[k, j]
    if not np.isfinite(y4E):
        excl["y4_E_nonfinite"] += 1; excl_I["y4_E_nonfinite"] += I; continue
    # P_E back-projection (K = floor primary, K = round sensitivity)
    def back(Kb):
        if Kb == 0: return M_run, True
        prod = 1.0
        for jj in range(1, Kb + 1):
            ci = CIDX.get(E + 300 * jj)
            if ci is None: return None, False
            v = RET[ci, j]
            if not np.isfinite(v) or abs(v) >= 0.2999: return None, False
            prod *= (1.0 + v)
        return M_run / prod, True
    Kf = int(math.floor(off_min / 5.0)); Kr = int(round(off_min / 5.0))
    PE, okf = back(Kf); PEr, okr = back(Kr)
    if not okf:
        guard_excl["K_floor"] += 1; excl["guard_K_floor"] += 1; excl_I["guard_K_floor"] += I; continue
    if Nf > 1.02 * I: overfill += 1
    U = max(I - Nf, 0.0)
    rt = RT[k, j]; qv = QV4H[k, j]
    tier = 0 if qv >= T0_EDGE else (1 if qv >= T1_EDGE else 2)
    def comps(PEx):
        b = s * (M_run / PEx - 1.0)
        o_run = s * ((1.0 + y4E) * PEx / M_run - 1.0)
        d = dict(I=I, Nf=Nf, fee=fee, gross=I * s * y4E, opp=U * s * y4E, opp_lat=U * b, opp_run=U * o_run, opp_cross=U * s * b * o_run)
        if Nf > 0:
            F = Nf / qty
            a = s * (F / M_run - 1.0); sh = s * (F / PEx - 1.0)
            d.update(fsh=Nf * sh, f_a=Nf * a, f_b=Nf * b, f_ab=Nf * s * a * b, fsh_exact=Nf * sh * (1.0 + y4E) / (1.0 + s * sh), _id=abs(sh - (a + b + s * a * b)))
        else:
            d.update(fsh=0.0, f_a=0.0, f_b=0.0, f_ab=0.0, fsh_exact=0.0, _id=0.0)
        return d
    c = comps(PE); identity_max = max(identity_max, c["_id"])
    cr = comps(PEr) if okr else None
    if not okr: guard_excl["K_round"] += 1
    align = None if not np.isfinite(rt) else s * rt
    plans.append(dict(key=key, era=era, E=E, day=E // 86400, s=s, status=status, arm=arm, rq_arm=rq_arm, halted=halted,
                      tier=tier, rt=(None if not np.isfinite(rt) else float(rt)), align=align, c=c, cr=cr, I=I,
                      mid_eq=mid_eq, ord_filled=ord_filled, Kf=Kf, Kr=Kr))

era2 = [p for p in plans if p["era"] == "ERA2"]; era1 = [p for p in plans if p["era"] == "ERA1"]
g4_mid_n = len(era2); g4_mid_eq = sum(p["mid_eq"] for p in era2)
g4_fill_ledger = sum(p["c"]["Nf"] for p in era2); g4_fill_orders = sum(p["ord_filled"] for p in era2)
plan_keys = set(p["key"] for p in plans)
orphan_maker = [(k, sum(abs(float(f["fill_notional"])) for f in v)) for k, v in fills_by.items() if k[2] == "maker" and (k[0], k[1]) not in orders_by]
G4 = {"mid_equal_share": g4_mid_eq / max(g4_mid_n, 1), "n": g4_mid_n,
      "maker_leg_fill_notional_ledger_vs_orders_rel_diff": (g4_fill_ledger - g4_fill_orders) / max(g4_fill_orders, 1e-9),
      "ledger_fill_notional_usdt": g4_fill_ledger, "orders_filled_notional_usdt": g4_fill_orders}
G4["PASS"] = bool(G4["mid_equal_share"] >= 0.99 and abs(G4["maker_leg_fill_notional_ledger_vs_orders_rel_diff"]) <= 0.005)
G6 = {"identity_maxabs_fraction": identity_max, "PASS": bool(identity_max <= 1e-12)}
print("G4", json.dumps(G4)); print("G6", json.dumps(G6))
if not G4["PASS"] or not G6["PASS"]:
    json.dump({"G4": G4, "G6": G6, "excluded": dict(excl)}, open(f"{T3}/receipts/PASSIVE_REV_GATEFAIL.json", "w"), indent=1)
    print("GATE FAIL -> STOP (prereg §2)"); sys.exit(2)

COMP = ["I", "Nf", "fee", "fsh", "opp", "gross", "f_a", "f_b", "f_ab", "fsh_exact", "opp_lat", "opp_run", "opp_cross"]
def block(sel, kseed, use_round=False):
    sel = [p for p in sel if (p["cr"] is not None) or not use_round]
    out = {"n_plans": len(sel), "kseed": kseed}
    if not sel: return out
    dk = sorted(set(p["day"] for p in sel)); di = {d: i for i, d in enumerate(dk)}
    A = {c: np.zeros(len(dk)) for c in COMP}
    for p in sel:
        cc = p["cr"] if use_round else p["c"]
        for c in COMP: A[c][di[p["day"]]] += cc[c]
    rng = np.random.default_rng([SEED, kseed]); idx = rng.integers(0, len(dk), size=(NB, len(dk)))
    Bs = {c: A[c][idx].sum(1) for c in COMP}
    tot = {c: float(A[c].sum()) for c in COMP}
    def stat(num_keys, den="I", scale=1e4):
        pt = sum(tot[x] for x in num_keys) / tot[den] * scale
        bd = sum(Bs[x] for x in num_keys) / Bs[den] * scale
        return {"point": round(pt, 4), "ci95": [round(float(np.percentile(bd, 2.5)), 4), round(float(np.percentile(bd, 97.5)), 4)],
                "se_boot": round(float(np.std(bd, ddof=1)), 4)}
    out.update({"n_days": len(dk), "days_first_last": [time.strftime("%F", time.gmtime(dk[0] * 86400)), time.strftime("%F", time.gmtime(dk[-1] * 86400))],
                "intended_usdt": round(tot["I"], 1), "maker_filled_usdt": round(tot["Nf"], 1),
                "c_eff_bps": stat(["fee", "fsh", "opp"]),
                "c_eff_exact_bps": stat(["fee", "fsh_exact", "opp"]),
                "fill_rate": stat(["Nf"], scale=1.0),
                "fee_bps_per_unit_intended": stat(["fee"]),
                "filled_shortfall_vs_E_bps_per_unit_intended": stat(["fsh"]),
                "  of_which_vs_run_mid_a": stat(["f_a"]), "  of_which_latency_E_to_run_b": stat(["f_b"]), "  of_which_cross": stat(["f_ab"]),
                "unfilled_opportunity_bps_per_unit_intended": stat(["opp"]),
                "  of_which_latency_E_to_run": stat(["opp_lat"]), "  of_which_run_clock": stat(["opp_run"]), "  of_which_cross ": stat(["opp_cross"]),
                "subset_replay_gross_bps_per_unit_intended": stat(["gross"]),
                "fee_bps_per_unit_filled": stat(["fee"], den="Nf"),
                "filled_shortfall_vs_E_bps_per_unit_filled": stat(["fsh"], den="Nf"),
                "second_order_term_bps": round((tot["fsh_exact"] - tot["fsh"]) / tot["I"] * 1e4, 5)})
    return out

def judge(b):
    ce = b["c_eff_bps"]; pt = ce["point"]; lo, hi = ce["ci95"]; se = ce["se_boot"]
    if hi < GATE_BPS: v = "PASS"
    elif lo > GATE_BPS: v = "FAIL"
    else: v = "UNDECIDABLE"
    r = {"rule": "CI upper < 1.6 => PASS; CI lower > 1.6 => FAIL; else UNDECIDABLE (PROGRAM §2 T3 / AMENDMENT 1 item 3)", "verdict": v,
         "c_eff_point": pt, "ci95": [lo, hi], "gate_bps": GATE_BPS}
    if v == "UNDECIDABLE":
        dist = abs(pt - GATE_BPS)
        r["n_days_required"] = None if dist < 0.05 else round(b["n_days"] * (1.96 * se / dist) ** 2, 1)
        if dist < 0.05: r["note"] = "point estimate sits on the gate: no sample size decides it"
    return r

R0 = [p for p in era2]
R1 = [p for p in era2 if p["align"] is not None and p["align"] > 0]
R2 = [p for p in era2 if p["align"] is not None and p["align"] >= 0.3]
R1c = [p for p in era2 if p["align"] is not None and p["align"] < 0]
res = {"R1_primary": block(R1, 201), "R0_all": block(R0, 202), "R2_extreme": block(R2, 203)}
res["R1_primary"]["judgement"] = judge(res["R1_primary"])
res["R0_all"]["judgement_reported_only"] = judge(res["R0_all"])
res["R2_extreme"]["judgement_reported_only"] = judge(res["R2_extreme"])
sens = {
    "204_R1_excl_opening_halted_anchors": block([p for p in R1 if not p["halted"]], 204),
    "205_R1_excl_requote_arm_direct": block([p for p in R1 if p["rq_arm"] != "direct"], 205),
    "206_R1_join": block([p for p in R1 if p["arm"] == "join"], 206),
    "207_R1_behind": block([p for p in R1 if p["arm"] == "behind"], 207),
    "208_R1_tier0plus1": block([p for p in R1 if p["tier"] in (0, 1)], 208),
    "209_R1_tier2": block([p for p in R1 if p["tier"] == 2], 209),
    "210_R1_buy": block([p for p in R1 if p["s"] > 0], 210),
    "211_R1_sell": block([p for p in R1 if p["s"] < 0], 211),
    "212_ERA1_R1": block([p for p in era1 if p["align"] is not None and p["align"] > 0], 212),
    "213_R1c_anti_aligned": block(R1c, 213),
    "214_R1_K_round": block(R1, 214, use_round=True),
}
qs = np.quantile([p["I"] for p in R1], [1 / 3, 2 / 3]) if R1 else [0, 0]
sens["215_R1_intent_size_tercile_low"] = block([p for p in R1 if p["I"] <= qs[0]], 215)
sens["216_R1_intent_size_tercile_mid"] = block([p for p in R1 if qs[0] < p["I"] <= qs[1]], 216)
sens["217_R1_intent_size_tercile_high"] = block([p for p in R1 if p["I"] > qs[1]], 217)
for kname, b in sens.items():
    if b.get("n_plans"): b["judgement_reported_only"] = judge(b)

counts = {"ERA2_plans": len(era2), "ERA1_plans": len(era1), "ERA2_unclassified": sum(1 for p in era2 if p["align"] is None),
          "ERA2_R1": len(R1), "ERA2_R2": len(R2), "ERA2_R1c": len(R1c),
          "ERA2_status": dict(Counter(p["status"] for p in era2)), "ERA2_arm": dict(Counter(str(p["arm"]) for p in era2)),
          "ERA2_requote_arm": dict(Counter(str(p["rq_arm"]) for p in era2)), "ERA2_tier": dict(Counter(p["tier"] for p in era2)),
          "R1_intended_usdt": round(sum(p["I"] for p in R1), 1),
          "excluded_counts": dict(excl), "excluded_intended_usdt": {k: round(v, 1) for k, v in excl_I.items()},
          "G5_guard_excluded": dict(guard_excl), "intended_disagreement_groups": I_disagree, "overfill_gt_1p02": overfill,
          "bnb_fallback_max_anchor_gap_s": bnb_gap_max, "size_tercile_edges_usdt": [float(qs[0]), float(qs[1])],
          "maker_fill_groups_without_any_order_row": {"n_groups": len(orphan_maker), "notional_usdt": round(sum(v for _, v in orphan_maker), 1)},
          "ERA2_plans_with_zero_maker_fill": sum(1 for p in era2 if p["c"]["Nf"] == 0),
          "ERA2_K_floor_values": dict(Counter(p["Kf"] for p in era2)), "ERA2_K_round_values": dict(Counter(p["Kr"] for p in era2))}
g5_R1_share = excl_I.get("guard_K_floor", 0.0) / max(sum(p["I"] for p in R1) + excl_I.get("guard_K_floor", 0.0), 1e-9)
G5 = {"guard_excluded_intended_usdt_all_eras": round(excl_I.get("guard_K_floor", 0.0), 1), "share_vs_R1_plus_excluded_upper_bound": g5_R1_share,
      "limitation_flag_gt_5pct": bool(g5_R1_share > 0.05)}

# ---------------- §3.6 transfer diagnostics: REV_SHORT raw book on the ERA2 meta anchors ----------------
e2_E = sorted(set(p["E"] for p in era2))
def bins_of(rt_abs):
    return min(int(rt_abs / 0.1), 4)
rev_turn = defaultdict(float); rev_tot_turn = 0.0; rev_gross = 0.0; n_rev = 0; turn_series = []
for E in e2_E:
    k = EIDX[E]
    w = np.nan_to_num(RT[k] / np.nansum(np.abs(RT[k])))
    wp = np.nan_to_num(RT[k - 1] / np.nansum(np.abs(RT[k - 1]))) if np.isfinite(RT[k - 1]).sum() >= 10 else np.zeros_like(w)
    dw = w - wp
    y = np.nan_to_num(Y4[k]); rev_gross += float((w * y).sum()) * 1e4; n_rev += 1
    tt = float(np.abs(dw).sum()); rev_tot_turn += tt; turn_series.append(tt)
    for jj in np.where(np.abs(dw) > 0)[0]:
        rtj = RT[k, jj]
        if not np.isfinite(rtj):
            cell = ("exit_unranked", "na", "na")
        else:
            al = "aligned" if np.sign(dw[jj]) * rtj > 0 else "anti"
            qv = QV4H[k, jj]; tr = 0 if qv >= T0_EDGE else (1 if qv >= T1_EDGE else 2)
            cell = (bins_of(abs(rtj)), al, tr)
        rev_turn[cell] += abs(dw[jj])
ours = defaultdict(float)
for p in era2:
    if p["align"] is None: continue
    al = "aligned" if p["align"] > 0 else "anti"
    ours[(bins_of(abs(p["rt"])), al, p["tier"])] += p["I"]
def norm(dct):
    t = sum(dct.values()); return {k: v / t for k, v in dct.items()} if t > 0 else {}
pr = norm(rev_turn); po = norm(ours)
cells = sorted(set(pr) | set(po), key=str)
tv_all = 0.5 * sum(abs(pr.get(c, 0) - po.get(c, 0)) for c in cells)
pr_al = norm({c: v for c, v in rev_turn.items() if c[1] == "aligned"}); po_al = norm({c: v for c, v in ours.items() if c[1] == "aligned"})
tv_al = 0.5 * sum(abs(pr_al.get(c, 0) - po_al.get(c, 0)) for c in set(pr_al) | set(po_al))
rev_share_aligned = sum(v for c, v in pr.items() if c[1] == "aligned"); rev_share_anti = sum(v for c, v in pr.items() if c[1] == "anti")
rev_share_unranked_exit = sum(v for c, v in pr.items() if c[1] == "na")
our_share_aligned = sum(v for c, v in po.items() if c[1] == "aligned")
def marg(pd, pos):
    m = defaultdict(float)
    for c, v in pd.items(): m[str(c[pos])] += v
    return dict(sorted(m.items()))
TRANSFER = {
    "rev_short_raw_book_window": {"anchors": n_rev, "mean_turnover_per_anchor": round(rev_tot_turn / max(n_rev, 1), 4),
                                  "mean_gross_bps_per_anchor": round(rev_gross / max(n_rev, 1), 4),
                                  "gross_per_unit_turnover_bps": round(rev_gross / max(rev_tot_turn, 1e-12), 4),
                                  "note": "raw a=1 rank book, sum|w|=1, eligible = member & finite(y4[E-4h]) & qv4h>=2.5e5, first anchor of window uses previous meta anchor weights"},
    "turnover_share_rev_short": {"aligned": round(rev_share_aligned, 4), "anti_aligned": round(rev_share_anti, 4), "exit_of_now_unranked_name": round(rev_share_unranked_exit, 4),
                                 "by_abs_rank_bin(0..4 = |r|<0.1 .. >=0.4)": marg(pr, 0), "by_tier": marg(pr, 2)},
    "intended_share_ours_classified": {"aligned": round(our_share_aligned, 4), "by_abs_rank_bin": marg(po, 0), "by_tier": marg(po, 2)},
    "total_variation_distance_all_cells": round(tv_all, 4), "total_variation_distance_aligned_cells_R1_vs_revshort_aligned": round(tv_al, 4),
}
# post-hoc combination of pre-registered pieces (NOT gating): weight our R1 and R1c costs by REV_SHORT's aligned/anti turnover shares
if res["R1_primary"].get("n_plans") and sens["213_R1c_anti_aligned"].get("n_plans"):
    wa = rev_share_aligned / max(rev_share_aligned + rev_share_anti, 1e-12)
    TRANSFER["posthoc_mixture_not_gating"] = {"weight_aligned": round(wa, 4),
        "c_eff_mixture_point": round(wa * res["R1_primary"]["c_eff_bps"]["point"] + (1 - wa) * sens["213_R1c_anti_aligned"]["c_eff_bps"]["point"], 4),
        "note": "point only; CI not computed (not pre-registered as an estimator)"}

# T-A4 descriptive: what the live executor actually paid on the top-up leg for the same ERA2 plans (vs P_E), no CI
tk_I = tk_N = tk_fee = tk_sh = 0.0
pl_by = {p["key"]: p for p in era2}
for key, p in pl_by.items():
    tf = fills_by.get((key[0], key[1], "topup_taker"), [])
    if not tf: continue
    Nt = sum(abs(float(f["fill_notional"])) for f in tf); qt = sum(abs(float(f["fill_notional"])) / float(f["fill_px"]) for f in tf)
    Ft = Nt / qt
    c = p["c"]; PE = None
    b = c["f_b"] / c["Nf"] if c["Nf"] > 0 else None
    fee_t = 0.0
    for f in tf:
        cc = float(f.get("commission") or 0.0)
        if (f.get("commission_asset") or "USDT") == "BNB": cc *= bnb_px(f.get("anchor_ts"))[0]
        fee_t += cc
    tk_N += Nt; tk_fee += fee_t
    M_run = None
    for r in orders_by[key]:
        if r.get("order_type") == "maker" and r.get("attempt_idx") == 1 and r.get("mid_at_anchor"): M_run = float(r["mid_at_anchor"]); break
    k = EIDX[p["E"]]; j = SIDX[key[1]]
    Kf = int(math.floor((min(r["anchor_ts"] for r in orders_by[key]) - p["E"]) / 300.0))
    prod = 1.0
    for jj in range(1, Kf + 1): prod *= 1.0 + RET[CIDX[p["E"] + 300 * jj], j]
    PE = M_run / prod
    tk_sh += Nt * p["s"] * (Ft / PE - 1.0)
TOPUP = {"topup_filled_usdt": round(tk_N, 1), "fee_bps_per_unit_topup": round(tk_fee / max(tk_N, 1e-9) * 1e4, 4),
         "shortfall_vs_E_bps_per_unit_topup": round(tk_sh / max(tk_N, 1e-9) * 1e4, 4),
         "all_in_vs_E_bps_per_unit_topup": round((tk_fee + tk_sh) / max(tk_N, 1e-9) * 1e4, 4),
         "note": "descriptive, no CI; ERA2 plans only; compares with the opportunity cost the passive policy would bear instead"}

try:
    bc = json.load(open(BOOK_CFG))
    TA1 = {"k_seconds": bc.get("k_seconds"), "placement_bandit_eps": (bc.get("placement_bandit") or {}).get("eps"),
           "requote_experiment_p": (bc.get("requote_experiment") or {}).get("p_requote"), "book_json_sha256": sha256(BOOK_CFG)}
except Exception as e:
    TA1 = {"error": f"{type(e).__name__}: {e}"}

OUT = {"device": os.path.abspath(__file__), "self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "env_whitelist": [],
       "python": sys.version.split()[0], "numpy": np.__version__, "utc": utc(time.time()),
       "inputs": {"ledger_manifest_sha256": sha256(f"{LOG}/MANIFEST_sha256.txt"), "slice_sha256": SLICE_SHA, "costb_sha256": COSTB_SHA},
       "ledger_counts": {"raw_fill_rows": len(fills_raw), "collapsed_fills": len(fills), "order_rows": n_orders},
       "gates": {"G4": G4, "G5": G5, "G6": G6}, "counts": counts, "results": res, "sensitivities": sens,
       "transfer_diagnostics": TRANSFER, "topup_leg_descriptive": TOPUP, "T_A1_in_service": TA1}
json.dump(OUT, open(f"{T3}/receipts/PASSIVE_REV.json", "w"), indent=1, default=str)
print(json.dumps({"counts": counts, "G5": G5, "R1": res["R1_primary"], "R0": res["R0_all"]["c_eff_bps"], "R2": res["R2_extreme"]["c_eff_bps"],
                  "transfer": TRANSFER, "topup": TOPUP, "TA1": TA1}, indent=1, default=str))
for kname, b in sens.items():
    if b.get("n_plans"):
        print(f"{kname:40s} n={b['n_plans']:6d} days={b['n_days']:3d} c_eff={b['c_eff_bps']['point']:+8.3f} {b['c_eff_bps']['ci95']} fill={b['fill_rate']['point']:.3f} gross={b['subset_replay_gross_bps_per_unit_intended']['point']:+.3f}")
print("DONE")
