#!/usr/bin/env python3
"""r14_flip.py — STEP 5. (a) the realised cash wall on the COMBO epoch, for comparability with the
published trackB 0.286; (b) which previously-rejected candidates flip if the wall is repriced
DOWNWARD, and the exact margin each needs.

All candidate cost/gross ratios are TAKEN FROM THE ARCHIVED RESULT DOCUMENTS, each with its line
reference, and are recomputed here only in the sense of re-deriving survival(lambda). No candidate
is re-run. READ-ONLY. ENV WHITELIST = EXPLICITLY EMPTY (asserted).
"""
import os, json, time, hashlib, math
from collections import defaultdict
_FORBIDDEN = ["LEGS", "PHI", "CAL", "MEMBERS_TOPN", "COSTB_JSON", "PANEL_IN", "V2", "OUT_TAG",
              "W3FIX", "FTRIM", "UMASK_SCOPE", "SLOW_NPY", "FPRED", "FSEED", "LOOK", "WRULE",
              "TRADE_TOPN", "UMASK_NPZ", "SHADOW_OFFSET_MIN", "RNSM", "FTPOS", "LTRIM_TH", "CDAMP"]
assert sorted([k for k in _FORBIDDEN if k in os.environ]) == []
ENV_WHITELIST = []
import numpy as np
def _no_env(*a, **k):
    raise AssertionError("r14 ENV WHITELIST is EMPTY")
os.environ.get = _no_env

ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r14_estimand"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
SHAS = {"PREREG_r14_cost_estimand_2026-09-12.md": "bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904",
        "PREREG_AMENDMENT_1_r14_2026-09-12.md": "6207572a9dba8a32554b6c3a44467509e179127ae92084f2bf44f7fafb872594",
        "PREREG_AMENDMENT_2_r14_2026-09-12.md": "abfcc85064ee2fbdbfa3c7f45f2a2b5a4fe2b3870ab4c8d7a9f03c26576cfc54",
        "PREREG_AMENDMENT_3_r14_2026-09-12.md": "e6cc65a1a84dd2b815ed9ee819bc801bab7c197e61b3bbe57187e574dce46a44"}
for fn, s in SHAS.items():
    assert sha(f"{ROOT}/{fn}") == s, fn

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
MODEL = 2.9537; MODEL_FEE = 2.3914; MODEL_HS = 0.2814; MODEL_IMP = 0.2809
TURN_REPLAY = 0.0540270; TURN_LIVE = 0.10864
COMBO_T0 = 1787716800   # 2026-08-26T04:00Z
NB = 2000; BOOT_SEED = 20260905
R = {"self_sha256": sha(os.path.abspath(__file__)), "prereg_shas": SHAS,
     "env_whitelist": ENV_WHITELIST, "env_whitelist_declared": "EXPLICITLY EMPTY SET (asserted)",
     "utc": time.strftime("%FT%TZ", time.gmtime())}

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
        m = r.get("mid_at_anchor_vector")
        if isinstance(m, str):
            m = json.loads(m)
        anch[ts] = m or {}
_bnbc = sorted([t for t in anch if anch[t].get("BNBUSDT")])
def bnb(ts):
    return anch[min(_bnbc, key=lambda t: abs(t - ts))]["BNBUSDT"] if _bnbc else None
F = {}
for dd in days:
    p = f"{LIVE}/{dd}/fills.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln); F[(r["symbol"], r.get("trade_id"))] = r
F = list(F.values())

def wall(pred, kseed):
    d = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in F:
        ts = r.get("anchor_ts")
        if ts is None or not pred(r, ts):
            continue
        nz = abs(float(r.get("fill_notional") or 0.0)); px = float(r.get("fill_px") or 0.0)
        M = (anch.get(ts) or {}).get(r["symbol"])
        if nz <= 0 or px <= 0 or not M:
            continue
        sgn = 1.0 if r.get("side") == "buy" else -1.0
        slip = sgn * (px / float(M) - 1.0) * 1e4
        c = float(r.get("commission") or 0.0)
        fee = (c * (bnb(ts) or 0.0)) if (r.get("commission_asset") or "USDT") == "BNB" else c
        day = int(math.floor(float(r.get("fill_ts") or ts) / 86400.0))
        d[day][0] += slip * nz; d[day][1] += fee / nz * 1e4 * nz; d[day][2] += nz
    if not d:
        return None
    ks = sorted(d)
    a = np.array([d[k][0] for k in ks]); b = np.array([d[k][1] for k in ks]); w = np.array([d[k][2] for k in ks])
    rng = np.random.default_rng([BOOT_SEED, kseed])
    idx = rng.integers(0, len(ks), size=(NB, len(ks)))
    tot = (a[idx] + b[idx]).sum(1) / w[idx].sum(1)
    return {"slip": round(float(a.sum() / w.sum()), 4), "fee": round(float(b.sum() / w.sum()), 4),
            "cash_wall_bps_per_unit_traded": round(float((a.sum() + b.sum()) / w.sum()), 4),
            "ci95": [round(float(np.percentile(tot, 2.5)), 4), round(float(np.percentile(tot, 97.5)), 4)],
            "notional": round(float(w.sum()), 1), "n_days": len(ks)}

R["realised_cash_wall"] = {
  "ALL_fills_whole_live_window": wall(lambda r, ts: True, 1),
  "ERA2_all_order_types": wall(lambda r, ts: (ts % 14400) >= 600, 2),
  "ERA2_steady_state_excl_protective_flatten": wall(
      lambda r, ts: (ts % 14400) >= 600 and (r.get("order_type") or "maker") != "protective_flatten", 3),
  "COMBO_epoch_2026-08-26T04Z_onward": wall(lambda r, ts: ts >= COMBO_T0, 4),
  "COMBO_epoch_excl_protective_flatten": wall(
      lambda r, ts: ts >= COMBO_T0 and (r.get("order_type") or "maker") != "protective_flatten", 5),
  "trackB_published_comparator_bps": 0.286,
  "caliber_note": "slip is measured against the ledger `mid_at_anchor` = the venue mid at the "
                  "executor's anchor-RUN start (E+24m in ERA2), NOT the mid at E. The E->E+24m "
                  "drift is measured separately in RECEIPT_r14_intent and is indistinguishable from zero."}

base = R["realised_cash_wall"]["ERA2_steady_state_excl_protective_flatten"]["cash_wall_bps_per_unit_traded"]
LAM = {"R0_status_quo": 1.0,
       "R1_my_ERA2_steady_cash": round(base / MODEL, 4),
       "R2_trackB_published_cash": round(0.286 / MODEL, 4),
       "R3_r11_withdrawn_estimand_B": 3.2167,
       "R4_fee_only_floor": round(MODEL_FEE / MODEL, 4)}
R["reprice_scenarios_lambda"] = LAM
R["lambda_note"] = ("lambda = repriced wall / MODEL(2.9537). R4 is the defensible FLOOR: the "
                    "commission is unavoidable cash and the model's fee component 2.3914 already "
                    "matches the measured 2.397 to 0.006 bps. Any lambda below R4 is being bought "
                    "entirely with the maker price improvement, which is the selection effect whose "
                    "complement is the 45.48% fill rate (RECEIPT_r14_nulls N3).")

# ---- candidate table. cost_over_gross is QUOTED from the archived documents. ----
CAND = [
 {"name": "CMUM_CARRY", "cost_over_gross": 5.80, "src": "RESULT_r10_independent_sources_2026-09-12.md L78 cost survival -480%",
  "verdict_was": "REJECTED", "non_cost_killer": "universe collapse: 49 COIN-M perps -> 19-22 names in 2026 and falling (r10 §3); prereg arm net SR -24.0"},
 {"name": "REV_SHORT", "cost_over_gross": 3.34, "src": "RESULT_r10_independent_sources_2026-09-12.md L78 cost survival -234%",
  "verdict_was": "REJECTED", "non_cost_killer": "turnover 24.39x A0 in the MATCHED caliber (CLOSEOUT L183 corrected); the reprice does not touch that"},
 {"name": "SLOW_CLOCK", "cost_over_gross": 1.74, "src": "RESULT_r10_independent_sources_2026-09-12.md §3 'cost eats 174% of gross'",
  "verdict_was": "REJECTED", "non_cost_killer": "the pre-declared pure-rho arm's NET was -0.2716 CI95 [-0.4504,-0.0979]; only post-hoc arm picking made it positive"},
 {"name": "COINT_PAIR", "cost_over_gross": 1.51, "src": "RESULT_r10_independent_sources_2026-09-12.md §3 'cost = 151% of gross'",
  "verdict_was": "REJECTED", "non_cost_killer": "GROSS itself insignificant: +0.2610 CI95 [-0.037,+0.544] contains zero"},
 {"name": "VRP_DELTA1", "cost_over_gross": 0.677, "src": "RESULT_r10 L78 cost survival 32.3% => c = (1-0.323)/1",
  "verdict_was": "REJECTED", "non_cost_killer": "died BEFORE cost: gross SR 0.3435; net beta -0.130 injects direction into a neutral book"},
 {"name": "TSMOM_DIR", "cost_over_gross": 0.502, "src": "RESULT_r10 §3 'cost eats 50.2%'",
  "verdict_was": "REJECTED", "non_cost_killer": "mean |net exposure| 0.5705 vs A0 0.0379 and the four demean sites in live/signal/legs.py make it undeployable; hedge sign REVERSED in 2026"},
]
for c in CAND:
    cg = c["cost_over_gross"]
    c["lambda_star_to_flip_net_positive"] = round(1.0 / cg, 4)
    c["wall_bps_needed"] = round(MODEL / cg, 4)
    c["survival_at"] = {k: round(1 - v * cg, 4) for k, v in LAM.items()}
    c["flips_at_R1"] = bool(LAM["R1_my_ERA2_steady_cash"] < 1.0 / cg)
    c["flips_at_R2"] = bool(LAM["R2_trackB_published_cash"] < 1.0 / cg)
    c["flips_at_R4_fee_floor"] = bool(LAM["R4_fee_only_floor"] < 1.0 / cg)
    c["margin_bps_at_R1"] = round(MODEL / cg - base, 4)
CAND.sort(key=lambda c: -(c["survival_at"]["R1_my_ERA2_steady_cash"] - c["survival_at"]["R0_status_quo"]))
R["candidates_ranked_by_how_much_the_repricing_moves_them"] = CAND

# arms whose value goes the OTHER way
R["arms_that_get_WORSE_under_a_cheaper_wall"] = [
 {"name": "r8 BUILD1 basis-in-book", "why": "it is the ONE family whose marginal dg RISES with the wall "
  "(marginal turnover -5.13%). Archived ladder dg vs A0 cost_ex: ZEROISH 0.11506->+0.01057, "
  "PWR230k 0.16817->+0.01444, PWR2300k 0.30162->+0.02307; slope +0.067 dg per unit A0 cost_ex.",
  "at_R1": "A0 cost_ex 0.16817 -> 0.0428 => marginal dg falls to about +0.0061, i.e. BELOW the "
           "ZEROISH rung. Closed harder.", "src": "RECEIPT_r11_cost_estimand_reconciliation.json build1_cost_sensitivity"},
 {"name": "trackB pure cost channel", "why": "its ceiling is the cost-to-zero improvement, = A0 cost_ex itself",
  "at_R1": "frozen-window A0 cost_ex 0.1201 -> 0.0306 bps/anchor/gross, vs the G2 resolution 0.23. "
           "Was 0.1201 < 0.23 (closed); becomes 0.0306 < 0.23 (closed by 7.5x). Closed harder.",
  "src": "RECEIPT_r11_cost_estimand_reconciliation.json trackB_prior_sensitivity"},
 {"name": "r12 I-2 ICO_L24_th0228_lam00", "why": "turnover-ADDING (+26.08%), so a cheaper wall helps it",
  "at_R1": "archived: dg +0.01623 at lambda=1 and -0.08496 at lambda=3.2167 => d(dg)/d(lambda) = -0.04565. "
           "At lambda=" + str(LAM["R1_my_ERA2_steady_cash"]) + " dg = +" +
           str(round(0.01623 + (1 - LAM["R1_my_ERA2_steady_cash"]) * 0.04565, 5)) +
           ". STILL NOT ADMISSIBLE: CI95 [-0.1457,+0.1970] and Bonferroni-29 both contain zero, 4/5 "
           "years negative, effect entirely in 2026.", "src": "RESULT_r12_intervention_layer_2026-09-12.md §4"},
]
# ---- coverage of the cash-wall measurement, by order type (why pf is absent, verified not assumed) ----
cov = defaultdict(lambda: [0.0, 0.0, 0])
pf_ts = set()
for r in F:
    ts = r.get("anchor_ts")
    if ts is None or (ts % 14400) < 600:
        continue
    ot = r.get("order_type") or "maker"
    nz = abs(float(r.get("fill_notional") or 0.0))
    has = bool((anch.get(ts) or {}).get(r["symbol"])) and float(r.get("fill_px") or 0.0) > 0
    cov[ot][0] += nz; cov[ot][1] += nz if has else 0.0; cov[ot][2] += 1
    if ot == "protective_flatten":
        pf_ts.add(ts)
R["cash_wall_coverage_ERA2_by_order_type"] = {
    k: {"n_fills": v[2], "notional": round(v[0], 1), "notional_with_anchor_mid": round(v[1], 1),
        "coverage": round(v[1] / v[0], 4) if v[0] else None} for k, v in sorted(cov.items())}
R["protective_flatten_exclusion_is_structural"] = {
    "distinct_anchor_ts_on_pf_fills": len(pf_ts),
    "of_which_have_an_anchors_jsonl_row": sum(1 for t in pf_ts if t in anch),
    "reading": "every protective_flatten fill carries an anchor_ts that has NO anchors.jsonl row, so "
               "there is no mid_at_anchor vector for it and it cannot enter a slip-vs-anchor-mid "
               "measurement AT ALL. The exclusion is structural, not a filter I chose; it happens to "
               "coincide with mk_costb.py's own maker_share_excludes rule (stop-loss / watchdog "
               "traffic on 2026-09-06 and 2026-09-09 is not steady-state rebalancing)."}
json.dump(R, open(f"{ROOT}/receipts/RECEIPT_r14_flip_2026-09-12.json", "w"), indent=1)
print(json.dumps(R, indent=1))
