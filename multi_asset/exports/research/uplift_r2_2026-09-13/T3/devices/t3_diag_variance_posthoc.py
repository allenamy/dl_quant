#!/usr/bin/python3
"""T3 POST-HOC diagnostic (NOT pre-registered, NOT gating): where does the width of the R1 c_eff interval come from?
(1) per-UTC-day decomposition of R1; (2) net unfilled directional exposure; (3) a market-demeaned variant that
corresponds to a DIFFERENT policy (a passive book that hedges its residual net exposure at zero cost with an
equal-weighted basket of the eligible names). Reuses t3_passive_rev.py's plan construction by import-free re-execution
of the same frozen definitions (the plan list is rebuilt by exec of the main device's code up to the judgement).
ENV WHITELIST = EMPTY SET (asserted inside the main device code)."""
import hashlib, json, math, os, sys, time
import numpy as np
T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
MAIN = f"{T3}/devices/t3_passive_rev.py"
src = open(MAIN).read()
cut = src.index("COMP = [")                          # everything before the estimator/judgement: gates, plans, slice
ns = {"__file__": MAIN, "__name__": "t3_passive_rev_prefix"}
exec(compile(src[:cut], MAIN, "exec"), ns)
era2, Y4, RT, EIDX, SIDX, CIDX, RET, QV4H, MEM = (ns[k] for k in ("era2", "Y4", "RT", "EIDX", "SIDX", "CIDX", "RET", "QV4H", "MEM"))
SELF_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
MAIN_SHA = hashlib.sha256(open(MAIN, "rb").read()).hexdigest()
R1 = [p for p in era2 if p["align"] is not None and p["align"] > 0]

# (1) per-day table
days = sorted(set(p["day"] for p in R1))
per_day = []
for d in days:
    sel = [p for p in R1 if p["day"] == d]
    I = sum(p["c"]["I"] for p in sel); Nf = sum(p["c"]["Nf"] for p in sel)
    fee = sum(p["c"]["fee"] for p in sel); fsh = sum(p["c"]["fsh"] for p in sel); opp = sum(p["c"]["opp"] for p in sel)
    Ubuy = sum(max(p["c"]["I"] - p["c"]["Nf"], 0) for p in sel if p["s"] > 0); Usell = sum(max(p["c"]["I"] - p["c"]["Nf"], 0) for p in sel if p["s"] < 0)
    per_day.append({"day": time.strftime("%F", time.gmtime(d * 86400)), "n": len(sel), "intended_usdt": round(I, 1), "fill_rate": round(Nf / I, 4),
                    "c_eff_bps": round((fee + fsh + opp) / I * 1e4, 3), "fee_bps": round(fee / I * 1e4, 3), "filled_shortfall_bps": round(fsh / I * 1e4, 3),
                    "opportunity_bps": round(opp / I * 1e4, 3), "gross_bps": round(sum(p["c"]["gross"] for p in sel) / I * 1e4, 3),
                    "unfilled_net_long_share_of_intended": round((Ubuy - Usell) / I, 4),
                    "numerator_usdt": round((fee + fsh + opp), 2)})
tot_num = sum(r["numerator_usdt"] for r in per_day); tot_I = sum(r["intended_usdt"] for r in per_day)
for r in per_day: r["share_of_total_numerator"] = round(r["numerator_usdt"] / tot_num, 3) if tot_num else None

# (3) market-demeaned variant
m4h = {}; m20 = {}
for E in sorted(set(p["E"] for p in R1)):
    k = EIDX[E]
    el = MEM[k] & np.isfinite(Y4[k]) & (QV4H[k] >= 2.5e5)
    m4h[E] = float(np.mean(Y4[k, el]))
    rows = [CIDX.get(E + 300 * jj) for jj in range(1, 5)]
    seg = RET[rows][:, el]
    ok = np.all(np.isfinite(seg) & (np.abs(seg) < 0.2999), axis=0)
    m20[E] = float(np.mean(np.prod(1.0 + seg[:, ok], axis=0) - 1.0))
def comps_dm(p):
    c = p["c"]; s = p["s"]; E = p["E"]
    U = max(c["I"] - c["Nf"], 0.0)
    y4 = Y4[EIDX[E], SIDX[p["key"][1]]]
    return {"I": c["I"], "fee": c["fee"], "fsh_dm": c["fsh"] - c["Nf"] * s * m20[E], "opp_dm": U * s * (y4 - m4h[E])}
dk = days; di = {d: i for i, d in enumerate(dk)}
A = {x: np.zeros(len(dk)) for x in ("I", "fee", "fsh_dm", "opp_dm")}
for p in R1:
    cc = comps_dm(p)
    for x in A: A[x][di[p["day"]]] += cc[x]
rng = np.random.default_rng([20260905, 301]); idx = rng.integers(0, len(dk), size=(2000, len(dk)))
B = {x: A[x][idx].sum(1) for x in A}
ce = (B["fee"] + B["fsh_dm"] + B["opp_dm"]) / B["I"] * 1e4
pt = float((A["fee"].sum() + A["fsh_dm"].sum() + A["opp_dm"].sum()) / A["I"].sum() * 1e4)
se = float(np.std(ce, ddof=1)); lo, hi = float(np.percentile(ce, 2.5)), float(np.percentile(ce, 97.5))
dist = abs(pt - 1.6)
DM = {"label": "POST-HOC, different policy (zero-cost residual-exposure hedge with an equal-weighted eligible basket), NOT the frozen estimand",
      "c_eff_dm_point": round(pt, 4), "ci95": [round(lo, 4), round(hi, 4)], "se_boot": round(se, 4), "kseed": 301,
      "filled_shortfall_dm_bps": round(A["fsh_dm"].sum() / A["I"].sum() * 1e4, 4), "opportunity_dm_bps": round(A["opp_dm"].sum() / A["I"].sum() * 1e4, 4),
      "n_days_required_if_this_variance": (None if dist < 0.05 else round(len(dk) * (1.96 * se / dist) ** 2, 1))}
OUT = {"device": os.path.abspath(__file__), "self_sha256": SELF_SHA, "main_device_sha256": MAIN_SHA, "posthoc": True,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "R1_per_day": per_day, "R1_total_intended_usdt": round(tot_I, 1),
       "market_demeaned_variant": DM}
json.dump(OUT, open(f"{T3}/receipts/DIAG_variance_posthoc.json", "w"), indent=1)
print(json.dumps(OUT, indent=1))
