#!/usr/bin/python3
"""T3 POST-HOC (constructed AFTER the frozen R1 result was seen; NOT pre-registered; does NOT change the frozen verdict).

Why it exists: the frozen estimator c_eff = fee_I + fsh_I + opp_I contains the window's REALISED return of our own
reversal-aligned intents (opp_I = u * m_U). Exact algebra on the same frozen components:
    g   = sum I s y4 / sum I        (subset replay gross per unit intended)
    u   = sum U / sum I             (unfilled share),  m_U = sum U s y4 / sum U,  m_F = sum N_f s y4 / sum N_f
    g   = u m_U + (1-u) m_F,  Delta = m_U - m_F   =>   c_eff = fee_I + fsh_I + u g + u (1-u) Delta          (identity)
Substituting the reversal book's own replay gross g* for the window-realised g separates EXECUTION (fee, entry
shortfall, fill selection Delta) from SIGNAL LEVEL (g*):
    c_eff(g*) = fee_I + fsh_I + u g* + u (1-u) Delta ;   c_eff(g*) < g*  <=>  g* > g_be := fee_F + fsh_F + u Delta
g_be = the gross per unit turnover a passively executed book needs to break even. g* = 1.6036 (P6, EMA a=0.5).
Assumption this adds (stated, untested here): the fill-selection gap Delta measured on our intents does not depend on the
subset's realised gross level. UTC-day block bootstrap 2000, default_rng([20260905, k]) with post-hoc k = 311..
"""
import hashlib, json, os, time
import numpy as np
T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
MAIN = f"{T3}/devices/t3_passive_rev.py"
src = open(MAIN).read(); cut = src.index("COMP = [")
ns = {"__file__": MAIN, "__name__": "t3_passive_rev_prefix"}
exec(compile(src[:cut], MAIN, "exec"), ns)
era2, era1 = ns["era2"], ns["era1"]
GSTAR = 1.6036
SELF_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
MAIN_SHA = hashlib.sha256(open(MAIN, "rb").read()).hexdigest()

def parts(p):
    c = p["c"]; U = max(c["I"] - c["Nf"], 0.0)
    y = c["gross"] / c["I"]            # s*y4_E  (gross = I s y4)
    return {"I": c["I"], "Nf": c["Nf"], "U": U, "fee": c["fee"], "fsh": c["fsh"], "opp": c["opp"], "gross": c["gross"],
            "fy": c["Nf"] * y, "uy": U * y}

def est(t):
    I, Nf, U = t["I"], t["Nf"], t["U"]
    u = U / I; feeI = t["fee"] / I; fshI = t["fsh"] / I; g = t["gross"] / I
    mU = t["uy"] / U if np.all(U > 0) else np.nan; mF = t["fy"] / Nf
    D = mU - mF
    feeF = t["fee"] / Nf; fshF = t["fsh"] / Nf
    gbe = feeF + fshF + u * D
    ce_star = feeI + fshI + u * (GSTAR / 1e4) + u * (1 - u) * D          # GSTAR is in bps; everything here is in fractions
    ce_frozen = (t["fee"] + t["fsh"] + t["opp"]) / I
    return {"u": u, "fee_F": feeF * 1e4, "fsh_F": fshF * 1e4, "m_U": mU * 1e4, "m_F": mF * 1e4, "Delta": D * 1e4,
            "u_times_Delta": u * D * 1e4, "g_be": gbe * 1e4, "c_eff_at_gstar": ce_star * 1e4, "c_eff_frozen": ce_frozen * 1e4, "g_realised": g * 1e4,
            "identity_resid": (ce_frozen - (feeI + fshI + u * g + u * (1 - u) * D)) * 1e4}

def run(sel, k):
    dk = sorted(set(p["day"] for p in sel)); di = {d: i for i, d in enumerate(dk)}
    keys = ["I", "Nf", "U", "fee", "fsh", "opp", "gross", "fy", "uy"]
    A = {x: np.zeros(len(dk)) for x in keys}
    for p in sel:
        pp = parts(p)
        for x in keys: A[x][di[p["day"]]] += pp[x]
    tot = {x: float(A[x].sum()) for x in keys}
    pt = est(tot)
    # identity is exact when U + N_f == I on every plan; plans filled slightly above intent (lot rounding, all <= 2 %)
    # break it by a hair -> bound it instead of asserting exactness, and report the count
    assert abs(pt["identity_resid"]) < 0.05, pt["identity_resid"]
    rng = np.random.default_rng([20260905, k]); idx = rng.integers(0, len(dk), size=(2000, len(dk)))
    bt = est({x: A[x][idx].sum(1) for x in keys})
    out = {"n_plans": len(sel), "n_days": len(dk), "kseed": k, "identity_resid_bps": round(float(pt["identity_resid"]), 6),
           "n_plans_filled_above_intent": sum(1 for p in sel if p["c"]["Nf"] > p["c"]["I"]),
           "notional_filled_above_intent_usdt": round(sum(p["c"]["Nf"] - p["c"]["I"] for p in sel if p["c"]["Nf"] > p["c"]["I"]), 2)}
    for key in ("u", "fee_F", "fsh_F", "m_U", "m_F", "Delta", "u_times_Delta", "g_be", "c_eff_at_gstar", "c_eff_frozen", "g_realised"):
        v = bt[key]
        out[key] = {"point": round(float(pt[key]), 4), "ci95": [round(float(np.nanpercentile(v, 2.5)), 4), round(float(np.nanpercentile(v, 97.5)), 4)],
                    "se_boot": round(float(np.nanstd(v, ddof=1)), 4)}
    lo, hi = out["g_be"]["ci95"]
    out["posthoc_reading_vs_1p6"] = ("g_be CI upper < 1.6 (passive execution would clear a 1.6 alpha)" if hi < 1.6 else
                                    "g_be CI lower > 1.6 (a 1.6 alpha would not cover passive execution)" if lo > 1.6 else "g_be CI contains 1.6")
    return out

R1 = [p for p in era2 if p["align"] is not None and p["align"] > 0]
OUT = {"device": os.path.abspath(__file__), "self_sha256": SELF_SHA, "main_device_sha256": MAIN_SHA, "posthoc": True,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "g_star": GSTAR,
       "ERA2_R1": run(R1, 311),
       "ERA2_R2": run([p for p in era2 if p["align"] is not None and p["align"] >= 0.3], 312),
       "ERA2_R0": run(era2, 313),
       "ERA2_R1c": run([p for p in era2 if p["align"] is not None and p["align"] < 0], 314),
       "ERA1_R1": run([p for p in era1 if p["align"] is not None and p["align"] > 0], 315),
       "ERA1_R0": run(era1, 316),
       "ERA2_R1_join": run([p for p in R1 if p["arm"] == "join"], 317),
       "ERA2_R1_behind": run([p for p in R1 if p["arm"] == "behind"], 318)}
json.dump(OUT, open(f"{T3}/receipts/POSTHOC_breakeven.json", "w"), indent=1)
for name, r in OUT.items():
    if isinstance(r, dict) and "g_be" in r:
        print(f"{name:16s} n={r['n_plans']:6d} d={r['n_days']:2d} u={r['u']['point']:.3f} feeF={r['fee_F']['point']:+.2f} fshF={r['fsh_F']['point']:+7.2f} {r['fsh_F']['ci95']} "
              f"mU={r['m_U']['point']:+7.2f} mF={r['m_F']['point']:+7.2f} Delta={r['Delta']['point']:+7.2f} {r['Delta']['ci95']} "
              f"g_be={r['g_be']['point']:+7.2f} {r['g_be']['ci95']} c_eff(g*)={r['c_eff_at_gstar']['point']:+6.2f} {r['c_eff_at_gstar']['ci95']} "
              f"frozen={r['c_eff_frozen']['point']:+6.2f} g_real={r['g_realised']['point']:+7.2f}  -> {r['posthoc_reading_vs_1p6']}")
