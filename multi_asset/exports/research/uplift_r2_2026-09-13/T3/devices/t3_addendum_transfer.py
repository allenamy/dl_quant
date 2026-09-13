#!/usr/bin/python3
"""T3 PREREG ADDENDUM 1 (sha d79eec98...) — A1 posted-but-unfilled maker orders on reversal-aligned names (orders.jsonl
terminal states), A2 order distribution versus a hypothetical REV_SHORT book (side / size / tier / time since the move),
A3 cache-free second instrument for the opportunity term (next-anchor venue mid). Descriptive; no gate; frozen verdict unchanged.
Reuses t3_passive_rev.py's frozen plan construction by exec of its prefix (gates G4/G6 re-asserted there).
ENV WHITELIST = EMPTY SET (asserted in the prefix)."""
import bisect, hashlib, json, math, os, time
from collections import defaultdict, Counter
import numpy as np
T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
ADD = f"{T3}/PREREG_ADDENDUM_1_T3_transfer_2026-09-13.md"; ADD_SHA = "d79eec9820f9da1831ea178f29f0bf3ae63f2182a8e2b8534644a44ab4c7f3d9"
EXI = f"{T3}/private/exchange_info_cache_live_20260913.json"; EXI_SHA = "405cf828454c84881c83059d04a85f6da117b8b8dd2ab485f8bef4a348d893bb"
MAIN = f"{T3}/devices/t3_passive_rev.py"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(ADD) == ADD_SHA, "addendum sha"; assert sha(EXI) == EXI_SHA, "exchange info sha"
src = open(MAIN).read(); cut = src.index("COMP = [")
ns = {"__file__": MAIN, "__name__": "t3_passive_rev_prefix"}
exec(compile(src[:cut], MAIN, "exec"), ns)
g = ns
era2, orders_by, anchors, ats_sorted = g["era2"], g["orders_by"], g["anchors"], g["ats_sorted"]
Y4, QV4H, RT, EIDX, SIDX, CIDX, RET, SYM = g["Y4"], g["QV4H"], g["RT"], g["EIDX"], g["SIDX"], g["CIDX"], g["RET"], g["SYM"]
LOG, read_jsonl, days = g["LOG"], g["read_jsonl"], g["days"]
T0_EDGE, T1_EDGE = g["T0_EDGE"], g["T1_EDGE"]
EXINFO = json.load(open(EXI))
U450 = f"{T3}/private/syms450_20260913.txt"; U450_SHA = "29e57eb8d48c66e21240024f7111e2061659820770c1947a3791d04a880c83ec"
assert sha(U450) == U450_SHA, "syms450 sha"
LIVE450 = set(x.strip() for x in open(U450) if x.strip())
# coverage facts added after the addendum freeze (inputs of its pre-registered dust rule; no estimator change)
R1 = [p for p in era2 if p["align"] is not None and p["align"] > 0]
I_R1 = sum(p["I"] for p in R1)

def plan_rows(p):
    rows = sorted(orders_by[p["key"]], key=lambda r: r["_pos"])
    mk = [r for r in rows if r.get("order_type") == "maker"]
    a1 = [r for r in mk if r.get("attempt_idx") == 1]
    r0 = a1[0]
    return rows, mk, r0
def back_PE(p, M_run, j):
    prod = 1.0
    for jj in range(1, p["Kf"] + 1):
        prod *= 1.0 + RET[CIDX[p["E"] + 300 * jj], j]
    return M_run / prod

# ---------------- A1 ----------------
cls = defaultdict(lambda: {"n": 0, "I": 0.0, "Nf": 0.0, "U": 0.0, "opp_usdt": 0.0})
for p in R1:
    rows, mk, r0 = plan_rows(p)
    c = p["c"]; U = max(c["I"] - c["Nf"], 0.0); fz = "fill" if c["Nf"] > 0 else "zero_fill"
    sub = [r for r in mk if r.get("submit_ts") is not None]
    if p["status"] == "first_send":
        name = f"first_send | {sub[0].get('terminal_reason')} | {fz}"
    elif p["status"] == "requote":
        name = f"requote_rested | {sub[0].get('terminal_reason')} | {fz}"
    else:
        a2 = [r for r in mk if r.get("attempt_idx") == 2]
        tr2 = "|".join(sorted(set(str(r.get("terminal_reason")) for r in a2))) or "no_attempt2_row"
        name = f"refused_no_requote | attempt2={tr2} | requote_arm={p['rq_arm']} | {fz}"
    d = cls[name]; d["n"] += 1; d["I"] += c["I"]; d["Nf"] += c["Nf"]; d["U"] += U; d["opp_usdt"] += c["opp"]
U_R1 = sum(v["U"] for v in cls.values())
A1 = {k: {"plans": v["n"], "intended_usdt": round(v["I"], 1), "filled_usdt": round(v["Nf"], 1), "unfilled_usdt": round(v["U"], 1),
          "fill_rate": round(v["Nf"] / v["I"], 4) if v["I"] else None, "share_of_R1_unfilled": round(v["U"] / U_R1, 4),
          "opportunity_contribution_bps_per_unit_R1_intended": round(v["opp_usdt"] / I_R1 * 1e4, 4)}
      for k, v in sorted(cls.items(), key=lambda kv: -kv[1]["U"])}

# ---------------- A2 ----------------
gross_by_E = {}
for d in days:
    pth = f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(pth): continue
    for r in read_jsonl(pth):
        E = int(math.floor(r["anchor_ts"] / 14400.0) * 14400); off = (r["anchor_ts"] - E) / 60.0
        if 22.0 <= off <= 30.0 and r.get("target_gross"):
            gross_by_E[E] = float(r["target_gross"])
e2_E = sorted(set(p["E"] for p in R1))
def move_terms(k, j, s, E):
    out = {"m_prev": None, "m_1h": None, "m_early": None}
    yp = Y4[k - 2, j] if k >= 2 else np.nan
    if np.isfinite(yp): out["m_prev"] = -s * yp
    rows = [CIDX.get(E - 300 * i) for i in range(0, 12)]
    if any(r is None for r in rows): return out
    seg = RET[rows, j]
    if not np.all(np.isfinite(seg)) or np.any(np.abs(seg) >= 0.2999): return out
    r1h = float(np.prod(1.0 + seg) - 1.0)
    y = Y4[k - 1, j]
    out["m_1h"] = -s * r1h
    if np.isfinite(y): out["m_early"] = -s * ((1.0 + y) / (1.0 + r1h) - 1.0)
    return out
def tier_of(qv): return 0 if qv >= T0_EDGE else (1 if qv >= T1_EDGE else 2)
rev_orders = []; dust = 0; no_minnot = 0; no_gross = 0
for E in e2_E:
    if E not in gross_by_E: no_gross += 1; continue
    k = EIDX[E]; G = gross_by_E[E]
    w = np.nan_to_num(RT[k] / np.nansum(np.abs(RT[k])))
    wp = np.nan_to_num(RT[k - 1] / np.nansum(np.abs(RT[k - 1])))
    dw = w - wp
    for j in np.where(np.abs(dw) > 0)[0]:
        q = abs(dw[j]) * G; sym = SYM[j]
        mn = (EXINFO.get(sym) or {}).get("min_notional")
        if mn is None: no_minnot += 1; mn = 5.0
        if q < float(mn): dust += 1; continue
        s = 1.0 if dw[j] > 0 else -1.0
        mt = move_terms(k, j, s, E)
        rev_orders.append({"E": E, "q": q, "s": s, "tier": tier_of(QV4H[k, j]), "in_exinfo": isinstance(EXINFO.get(sym), dict), "in_live450": sym in LIVE450, **mt})
ours = []
for p in R1:
    k = EIDX[p["E"]]; j = SIDX[p["key"][1]]
    mt = move_terms(k, j, p["s"], p["E"])
    ours.append({"E": p["E"], "q": p["I"], "s": p["s"], "tier": p["tier"], **mt})
EDGES = [5, 10, 25, 50, 100, 250, 500, 1000, float("inf")]
def describe(lst):
    q = np.array([o["q"] for o in lst]); s = np.array([o["s"] for o in lst]); W = q.sum()
    def wq(pct):
        o = np.argsort(q); cw = np.cumsum(q[o]) / W
        return float(q[o][np.searchsorted(cw, pct / 100.0)])
    bins = {}
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        m = (q >= lo) & (q < hi); bins[f"[{lo},{hi})"] = float(q[m].sum() / W)
    bins["[0,5)"] = float(q[q < 5].sum() / W)
    tiers = {t: float(sum(o["q"] for o in lst if o["tier"] == t) / W) for t in (0, 1, 2)}
    def wmean(key):
        v = [(o["q"], o[key]) for o in lst if o[key] is not None]
        return (round(sum(a * b for a, b in v) / sum(a for a, _ in v) * 1e4, 3), len(v)) if v else (None, 0)
    both = [o for o in lst if o["m_1h"] is not None and o["m_early"] is not None]
    last_share = sum(o["q"] * abs(o["m_1h"]) for o in both) / max(sum(o["q"] * (abs(o["m_1h"]) + abs(o["m_early"])) for o in both), 1e-18)
    perE = defaultdict(float)
    for o in lst: perE[o["E"]] += o["q"]
    return {"orders": len(lst), "notional_usdt": round(float(W), 1), "per_anchor_notional_mean_usdt": round(float(np.mean(list(perE.values()))), 1),
            "buy_share_notional": round(float(q[s > 0].sum() / W), 4), "buy_share_count": round(float((s > 0).mean()), 4),
            "size_quantiles_count_weighted_usdt": {f"p{x}": round(float(np.percentile(q, x)), 2) for x in (25, 50, 75, 90, 99)},
            "size_quantiles_notional_weighted_usdt": {f"p{x}": round(wq(x), 2) for x in (25, 50, 75, 90, 99)},
            "size_bin_notional_share": {k: round(v, 4) for k, v in bins.items()},
            "tier_notional_share": {str(t): round(v, 4) for t, v in tiers.items()},
            "move_terms_notional_weighted_bps (positive = moved opposite to the order before it was sent)": {
                "m_1h": wmean("m_1h"), "m_early_3h": wmean("m_early"), "m_prev_anchor": wmean("m_prev")},
            "last_hour_share_of_prior_4h_move": round(float(last_share), 4),
            "move_terms_unusable_guard_or_missing": sum(1 for o in lst if o["m_1h"] is None)}
dr = describe(rev_orders); do = describe(ours)
tv_size = 0.5 * sum(abs(dr["size_bin_notional_share"][k] - do["size_bin_notional_share"][k]) for k in dr["size_bin_notional_share"])
W_rev = sum(o["q"] for o in rev_orders)
A2_cov = {"rev_short_notional_share_on_symbols_absent_from_exchange_info": round(sum(o["q"] for o in rev_orders if not o["in_exinfo"]) / W_rev, 4),
          "rev_short_notional_share_outside_live_450_universe": round(sum(o["q"] for o in rev_orders if not o["in_live450"]) / W_rev, 4),
          "note": "added after the addendum freeze as coverage facts of the dust-rule input and of the executor universe; descriptive"}
A2 = {"coverage_extra": A2_cov, "rev_short_hypothetical_orders": dr, "ours_R1_intents": do, "size_bins_total_variation_distance": round(tv_size, 4),
      "rev_short_dust_dropped_orders": dust, "rev_short_symbols_without_min_notional_used_5usdt": no_minnot, "anchors_without_gross": no_gross,
      "capital_note": "G_E = anchors.jsonl target_gross of the ERA2 anchor row at E (the live book's own capital)"}

# ---------------- A3 ----------------
rowsA3 = []; cov_missing = Counter()
for p in R1:
    rows, mk, r0 = plan_rows(p)
    M_run = float(r0["mid_at_anchor"]); t_run = r0["anchor_ts"]; sym = p["key"][1]; j = SIDX[sym]; k = EIDX[p["E"]]
    idx = bisect.bisect_left(ats_sorted, t_run + 60.0)
    if idx >= len(ats_sorted): cov_missing["no_next_anchor"] += 1; continue
    tn = ats_sorted[idx]; gap = (tn - t_run) / 3600.0
    if not (3.0 <= gap <= 5.0): cov_missing["gap_outside_3h_5h"] += 1; continue
    mn = anchors[tn]["mid"].get(sym)
    if not mn: cov_missing["symbol_not_in_next_vector"] += 1; continue
    c = p["c"]; U = max(c["I"] - c["Nf"], 0.0); s = p["s"]
    y = Y4[k, j]; PE = back_PE(p, M_run, j)
    o_next = s * (float(mn) / M_run - 1.0); o_run = s * ((1.0 + y) * PE / M_run - 1.0)
    rowsA3.append({"day": p["day"], "I": c["I"], "fee": c["fee"], "fa": c["f_a"], "Uon": U * o_next, "Uor": U * o_run})
dk = sorted(set(r["day"] for r in rowsA3)); di = {d: i for i, d in enumerate(dk)}
A = {x: np.zeros(len(dk)) for x in ("I", "fee", "fa", "Uon", "Uor")}
for r in rowsA3:
    for x in A: A[x][di[r["day"]]] += r[x]
rng = np.random.default_rng([20260905, 401]); ix = rng.integers(0, len(dk), size=(2000, len(dk)))
B = {x: A[x][ix].sum(1) for x in A}
def st(num, den="I"):
    pt = sum(A[x].sum() for x in num) / A[den].sum() * 1e4; bd = sum(B[x] for x in num) / B[den] * 1e4
    return {"point": round(float(pt), 4), "ci95": [round(float(np.percentile(bd, 2.5)), 4), round(float(np.percentile(bd, 97.5)), 4)], "se_boot": round(float(np.std(bd, ddof=1)), 4)}
diff_pt = (A["Uon"].sum() - A["Uor"].sum()) / A["I"].sum() * 1e4; diff_bd = (B["Uon"] - B["Uor"]) / B["I"] * 1e4
A3 = {"kseed": 401, "plans_covered": len(rowsA3), "plans_R1": len(R1), "intended_share_covered": round(sum(r["I"] for r in rowsA3) / I_R1, 4),
      "missing": dict(cov_missing), "n_days": len(dk),
      "c_run_cf_next_anchor_mid": st(["fee", "fa", "Uon"]), "c_run_meta_y4": st(["fee", "fa", "Uor"]),
      "opportunity_next_anchor_mid": st(["Uon"]), "opportunity_meta_y4_run_clock": st(["Uor"]),
      "difference_cf_minus_meta": {"point": round(float(diff_pt), 4), "ci95": [round(float(np.percentile(diff_bd, 2.5)), 4), round(float(np.percentile(diff_bd, 97.5)), 4)]},
      "clock_note": "cf ends at the next anchor run (E+4h+23/24m); meta ends at the E+4h close; neither contains the E->run latency; the gate uses the E clock"}
A3["reading"] = ("instruments agree on the opportunity term (difference CI contains 0)" if A3["difference_cf_minus_meta"]["ci95"][0] <= 0 <= A3["difference_cf_minus_meta"]["ci95"][1]
                 else "instruments disagree (difference CI excludes 0) -> limitation, clock offset")
OUT = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "addendum_sha256": ADD_SHA, "main_device_sha256": sha(MAIN),
       "exchange_info_sha256": EXI_SHA, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "R1_size": {"plans": len(R1), "intended_usdt": round(I_R1, 1), "unfilled_usdt": round(U_R1, 1), "days": len(set(p["day"] for p in R1))},
       "A1_terminal_states": A1, "A2_order_distribution": A2, "A3_second_instrument": A3}
json.dump(OUT, open(f"{T3}/receipts/ADDENDUM_transfer.json", "w"), indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str))
