#!/usr/bin/env python3
"""r14_nulls.py — AMENDMENT 3. N1 randomised-arm null (zero by construction, exact scheme),
N2 RELAB null for the level, N3 fill-rate accounting, and the final ruling arithmetic.

READ-ONLY on ~/dl_quant_live and ~/wide_shadow. ENV WHITELIST = EXPLICITLY EMPTY (asserted).
"""
import os, sys, json, time, hashlib, math
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
SHAS = {"PREREG_r14_cost_estimand_2026-09-12.md": "bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904",
        "PREREG_AMENDMENT_1_r14_2026-09-12.md": "6207572a9dba8a32554b6c3a44467509e179127ae92084f2bf44f7fafb872594",
        "PREREG_AMENDMENT_2_r14_2026-09-12.md": "abfcc85064ee2fbdbfa3c7f45f2a2b5a4fe2b3870ab4c8d7a9f03c26576cfc54",
        "PREREG_AMENDMENT_3_r14_2026-09-12.md": "e6cc65a1a84dd2b815ed9ee819bc801bab7c197e61b3bbe57187e574dce46a44"}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
for fn, s in SHAS.items():
    got = sha(f"{ROOT}/{fn}")
    assert got == s, f"{fn} sha mismatch {got}"
SELF_SHA = sha(os.path.abspath(__file__))

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
SHADOW = "/Users/haosiyu/wide_shadow"
OUT = f"{ROOT}/receipts/RECEIPT_r14_nulls_2026-09-12.json"
NB = 2000; BOOT_SEED = 20260905
MODEL_BPS = 2.9537; TURN_REPLAY = 0.0540270; TURN_LIVE = 0.10864

R = {"self_sha256": SELF_SHA, "prereg_shas": SHAS, "env_whitelist": ENV_WHITELIST,
     "env_whitelist_declared": "EXPLICITLY EMPTY SET (asserted at runtime)",
     "utc": time.strftime("%FT%TZ", time.gmtime())}

z = np.load(f"{SHADOW}/state/rolling.npz", allow_pickle=True)
CTS = z["ts"].astype(np.int64); CD = z["data"]
RET = np.asarray(CD[:, :, 0], np.float64); del z
cfg = json.load(open(f"{SHADOW}/shadow_bundle/config.json"))
PSYM = [str(s) for s in cfg["symbols_panel"]]; SIDX = {s: i for i, s in enumerate(PSYM)}
NW = len(PSYM)
assert (np.diff(CTS) == 300).all()
ROW = {int(t): i for i, t in enumerate(CTS)}
fin = np.isfinite(RET)
CL = np.concatenate([np.zeros((1, NW)), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0.0), 0)])
CN = np.concatenate([np.zeros((1, NW), np.int64), np.cumsum(fin, 0)])

days = sorted(x for x in os.listdir(LIVE) if x.isdigit())
ORD = []
for dd in days:
    p = f"{LIVE}/{dd}/orders.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        ORD.append(json.loads(ln))
FILD = {}
for dd in days:
    p = f"{LIVE}/{dd}/fills.jsonl"
    if not os.path.exists(p):
        continue
    for ln in open(p):
        r = json.loads(ln)
        FILD[(r["symbol"], r.get("trade_id"))] = r
FILD = list(FILD.values())

# ---- the ERA2 attempt-1 intent table, with the whole-anchor drift VECTOR for RELAB ----
DRIFT_VEC = {}          # E -> np.array(NW) of Pi(1+ret5)-1 over rows E+1..E+k, NaN where unusable
rowsI = []
for r in ORD:
    if int(r.get("attempt_idx") or 1) != 1:
        continue
    ints = r.get("intended_notional")
    ts = r.get("anchor_ts")
    if ints is None or float(ints) == 0.0 or ts is None:
        continue
    if (ts % 14400) < 600:
        continue                                    # ERA2 only
    c = SIDX.get(r["symbol"])
    if c is None:
        continue
    E = int(math.floor(ts / 14400.0) * 14400)
    i0 = ROW.get(E)
    if i0 is None:
        continue
    k = max(0, min(int(round((ts - E) / 300.0)), 47))
    key = (E, k)
    if key not in DRIFT_VEC:
        if i0 + 1 + k >= CL.shape[0]:
            DRIFT_VEC[key] = None
        else:
            nb = CN[i0 + 1 + k, :] - CN[i0 + 1, :]
            v = np.expm1(CL[i0 + 1 + k, :] - CL[i0 + 1, :])
            DRIFT_VEC[key] = np.where(nb == k, v, np.nan)
    dv = DRIFT_VEC[key]
    if dv is None or not np.isfinite(dv[c]):
        continue
    ints = float(ints)
    rowsI.append({"E": E, "k": k, "day": E // 86400, "c": c, "w": abs(ints),
                  "sgn": 1.0 if ints > 0 else -1.0, "drift": (1.0 if ints > 0 else -1.0) * dv[c] * 1e4,
                  "rid": r.get("rebalance_id") or "", "sym": r["symbol"],
                  "arm": r.get("placement_arm"), "ot": r.get("order_type") or "maker"})
R["n_rows_ERA2_attempt1"] = len(rowsI)

def wmean(items, f="drift"):
    n = sum(x[f] * x["w"] for x in items); d = sum(x["w"] for x in items)
    return n / d if d > 0 else None

# ---------------- N1: randomised-arm null (exact scheme) ----------------
band = [x for x in rowsI if x["arm"] in ("join", "behind")]
obs_j = wmean([x for x in band if x["arm"] == "join"])
obs_b = wmean([x for x in band if x["arm"] == "behind"])
D_obs = obs_j - obs_b
nulls = []
for salt in range(NB):
    nj = dj = nb_ = db = 0.0
    pre = f"{salt}:".encode()
    for x in band:
        h = hashlib.sha1(pre + f"{x['rid']}:{x['sym']}".encode()).digest()[-1]
        if h < 128:
            nb_ += x["drift"] * x["w"]; db += x["w"]
        else:
            nj += x["drift"] * x["w"]; dj += x["w"]
    if dj > 0 and db > 0:
        nulls.append(nj / dj - nb_ / db)
nulls = np.array(nulls)
R["N1_randomised_arm_null"] = {
    "n_rows": len(band), "observed_join": round(obs_j, 4), "observed_behind": round(obs_b, 4),
    "observed_D_join_minus_behind": round(D_obs, 4),
    "null_draws": len(nulls), "null_mean": round(float(nulls.mean()), 4),
    "null_sd": round(float(nulls.std(ddof=1)), 4),
    "null_ci95": [round(float(np.percentile(nulls, 2.5)), 4), round(float(np.percentile(nulls, 97.5)), 4)],
    "two_sided_p_of_abs_D": round(float((np.abs(nulls) >= abs(D_obs)).mean()), 4),
    "reading": "D is ZERO BY CONSTRUCTION (the arm is assigned after the target is formed and only "
               "moves the limit price by one tick; it cannot move the [E,E+25m] price path). The "
               "null sd is therefore the HONEST resolution of a within-anchor contrast on this statistic."}

# ---------------- N2: RELAB null for the level ----------------
obs_level = wmean(rowsI)
by_key = defaultdict(list)
for x in rowsI:
    by_key[(x["E"], x["k"])].append(x)
relab = []
for d in range(1, 201):
    rng = np.random.default_rng([4242, d])
    perm = rng.permutation(NW)
    num = den = 0.0
    for key, items in by_key.items():
        dv = DRIFT_VEC[key]
        for x in items:
            v = dv[perm[x["c"]]]
            if not np.isfinite(v):
                continue
            num += x["sgn"] * v * 1e4 * x["w"]; den += x["w"]
    if den > 0:
        relab.append(num / den)
relab = np.array(relab)
R["N2_RELAB_null_level"] = {
    "observed_notional_weighted_drift_bps": round(obs_level, 4),
    "null_draws": len(relab), "null_mean": round(float(relab.mean()), 4),
    "null_sd": round(float(relab.std(ddof=1)), 4),
    "null_ci95": [round(float(np.percentile(relab, 2.5)), 4), round(float(np.percentile(relab, 97.5)), 4)],
    "percentile_of_observed": round(float((relab <= obs_level).mean()), 4),
    "two_sided_p": round(float((np.abs(relab - relab.mean()) >= abs(obs_level - relab.mean())).mean()), 4),
    "family_justification": "RELAB, not SHIFT: the object is the matching between a name's trade "
                            "sign and that same name's next-25-minute return = a NAME-IDENTITY object "
                            "(BACKTEST_METHOD 2026-09-12 §4; r13b measured SHIFT is weak for persistent "
                            "name attributes)"}

# ---------------- N3: fill-rate accounting ----------------
intent_a1 = defaultdict(float); filled_by = defaultdict(float)
for x in rowsI:
    intent_a1[x["ot"]] += x["w"]
tot_int = sum(intent_a1.values())
a1_nonpf = sum(v for k, v in intent_a1.items() if k != "protective_flatten")
for r in FILD:
    ts = r.get("anchor_ts")
    if ts is None or (ts % 14400) < 600:
        continue
    nz = abs(float(r.get("fill_notional") or 0.0))
    filled_by[(r.get("order_type") or "maker", int(r.get("attempt_idx") or 1))] += nz
tot_fill = sum(filled_by.values())
steady = sum(v for (ot, ai), v in filled_by.items() if ot != "protective_flatten")
R["N3_fill_rate_ERA2"] = {
    "attempt1_intent_by_order_type": {k: round(v, 1) for k, v in sorted(intent_a1.items())},
    "attempt1_intent_total": round(tot_int, 1),
    "attempt1_intent_excl_protective_flatten": round(a1_nonpf, 1),
    "filled_by_order_type_and_attempt": {f"{k[0]}|a{k[1]}": round(v, 1) for k, v in sorted(filled_by.items())},
    "filled_total": round(tot_fill, 1),
    "filled_steady_state_excl_pf": round(steady, 1),
    "fill_rate_steady_vs_attempt1_intent_excl_pf": round(steady / a1_nonpf, 4) if a1_nonpf else None,
    "note": "the replay books 100% of |dw| and charges cost on 100% of |dw|; the desk fills this share"}

# ---------------- final ruling arithmetic ----------------
prev = json.load(open(f"{ROOT}/receipts/RECEIPT_r14_intent_2026-09-12.json"))
g1 = json.load(open(f"{ROOT}/receipts/RECEIPT_r14_gap_2026-09-12.json"))
drift_intent = prev["PRIMARY_drift_intent_ERA2"]
slip_fill = g1["PRIMARY_ERA2_all_fills"]["slip"]
fee_fill = g1["PRIMARY_ERA2_all_fills"]["fee_bps"]
mo60 = g1["PRIMARY_ERA2_all_fills"]["markout60_cost_bps"]
cash = slip_fill["mean"] + fee_fill["mean"]
R["RULING_ARITHMETIC"] = {
  "Q1_is_the_post_fill_markout_inside_y4": {
     "answer": "YES",
     "why_source": "meta_newprod(_v4).y4 = Pi(1+ret5)-1 over cache rows E+1..E+48, i.e. the window "
                   "[E, E+4h] anchor-close to anchor-close (target_alignment_receipt.json max_abs "
                   "3.41e-07; Y4DEF_r9screen.json VERDICT PROD_E1_E48 median_abs_err 1.40e-10); "
                   "w10_sleeve.py L329 marks sm*y4[i] with sm the POST-trade weight, so the replay "
                   "holds the position across the whole window",
     "why_measured": "share of deduped live fill notional whose [t_fill, t_fill+D] lies inside "
                     "[E, E+4h] = " + json.dumps(g1["markout_interval_inside_replay_window_share_of_notional"]),
     "consequence": "charging the post-fill markout as an execution cost DOUBLE-COUNTS a price path "
                    "the replay's own mark already carries => ESTIMAND B is arithmetically wrong"},
  "Q2_what_y4_does_NOT_contain": {
     "quantity": "the return over [E, t_exec] on the traded increment (the desk trades at E+24m in "
                 "the deployed ERA2 form; the replay's window opens at E)",
     "drift_intent_bps_per_unit_traded": drift_intent["mean"], "ci95": drift_intent["ci95"],
     "RELAB_null_sd": R["N2_RELAB_null_level"]["null_sd"],
     "randomised_arm_null_sd": R["N1_randomised_arm_null"]["null_sd"],
     "verdict": "not distinguishable from zero"},
  "realised_cash_cost_vs_ledger_anchor_mid_bps_per_unit_traded": {
     "fee": fee_fill["mean"], "slip": slip_fill["mean"], "sum": round(cash, 4),
     "trackB_published_comparator": 0.286},
  "model_charge_bps_per_unit_turnover": MODEL_BPS,
  "model_decomposition": {"fee": 2.3914, "half_spread_on_taker_leg_only": 0.2814,
                          "impact_excess_of_half_spread": 0.2809, "adverse_selection": 0.0},
  "overlap_with_a_full_markout_charge_bps_per_unit_turnover": 0.2814,
  "overcharge_central_bps_per_unit_turnover": round(MODEL_BPS - cash, 4),
  "overcharge_with_drift_correction": round(MODEL_BPS - cash - drift_intent["mean"], 4),
  "overcharge_ci_from_drift_uncertainty": [round(MODEL_BPS - cash - drift_intent["ci95"][1], 4),
                                           round(MODEL_BPS - cash - drift_intent["ci95"][0], 4)],
  "delta_g_on_MATCHED_replay_turnover": round((MODEL_BPS - cash) * TURN_REPLAY, 4),
  "delta_g_ci_on_MATCHED_replay_turnover": [round((MODEL_BPS - cash - drift_intent["ci95"][1]) * TURN_REPLAY, 4),
                                            round((MODEL_BPS - cash - drift_intent["ci95"][0]) * TURN_REPLAY, 4)],
  "markout60_cost_measured_here_bps": mo60["mean"], "markout60_ci95": mo60["ci95"],
  "THE_BINDING_CAVEAT": "the cheap realised fill price and the 48% fill rate are two halves of ONE "
                        "selection. The replay fills 100% of |dw| at the model price. Repricing the "
                        "cost wall downward WITHOUT also modelling the unfilled complement is not "
                        "allowed; see N3."}
lo = R["RULING_ARITHMETIC"]["overcharge_ci_from_drift_uncertainty"][0]
R["RULING"] = ("ESTIMAND_A_MODEL_OVERCHARGES" if lo > 0 else "CANNOT_DISTINGUISH")
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps(R, indent=1))
print("WROTE", OUT)
