"""ROUND-3 PLACEBO JUDGE.  Reads only r3_placebo/out/*.npz produced by r3_drive.py.

STATISTIC (pinned, judge_v4):  g = net_ex / gross_total, bps per anchor per unit gross.
ALSO REPORTED FOR EVERY ARM AND EVERY NULL (this is the whole point of round 3):
    g_gross = pnl_ex / gross_total       -- cost-free; the cost artifact cannot touch it
    g_carry = carry_ex / gross_total
    g_cost  = cost_ex  / gross_total      -- the churn bill the broken null was really paying
    g_cm    = g + g_cost * (1 - cost_real/cost_null)   -- null re-priced at the real arm's bill
E-0911-A: the first LOOK=900 anchors are seat warm-up (w3=[1/3,1/3,1/3], LEGS mask bypassed)
and are DROPPED from every full-cycle reading.
Bootstrap: UTC-day block bootstrap, 2000 resamples, rng numpy.default_rng([20260905, k]).

DECISION RULE, DECLARED BEFORE THE NUMBERS WERE READ:
  An arm's placebo margin SURVIVES a turnover-matched null iff, on FULL post-warm:
   (i)   the null family is admissible: mean cost ratio null/real within [0.75, 1.25];
   (ii)  margin_gross = real g_gross - null g_gross > 0 (real beats null before any cost);
   (iii) the paired per-anchor margin in NET g has a 95% day-block CI excluding 0;
   (iv)  with K = 12 arms declared, the BONF12 (alpha 0.05/12) lower bound also excludes 0
         -> SURVIVES; (iii) only -> SURVIVES_NOMINAL; otherwise FAILS.
"""
import numpy as np, os, json, sys, glob

R = "/workspace/uplift_2026-09-11/r3_placebo"
OUT = R + "/out"
K_DECLARED = 12
FAM = {"R1": "R", "R2": "R", "R3": "R", "O1": "RO", "O2": "RO",
       "T1": "T", "T2": "T", "T3": "T", "P1": "P_legacy"}
MATCHED = ["R1", "R2", "R3", "O1", "O2", "T1", "T2", "T3"]

def ep(s):
    return int((np.datetime64(s) - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s"))
SPANS = {"FULL": (ep("2022-01-01T00:00"), ep("2026-08-10T20:00")),
         "F23":  (ep("2023-01-01T00:00"), ep("2026-08-10T20:00")),
         "FROZEN": (ep("2025-03-01T00:00"), ep("2026-08-10T20:00"))}

def load(tag):
    p = OUT + "/" + tag + ".npz"
    if not os.path.exists(p):
        return None
    Z = np.load(p, allow_pickle=True)
    Rm = np.asarray(Z["rec"], float)
    cols = [str(c) for c in Z["cols"]]
    ix = {c: i for i, c in enumerate(cols)}
    ts = np.round(Rm[:, ix["ts"]]).astype(np.int64)
    gt = Rm[:, ix["gross_total"]]
    d = {"ts": ts,
         "g":      Rm[:, ix["net_ex"]] / gt,
         "ggross": Rm[:, ix["pnl_ex"]] / gt,
         "gcarry": Rm[:, ix["carry_ex"]] / gt,
         "gcost":  Rm[:, ix["cost_ex"]] / gt,
         "turn":   Rm[:, ix["turnover"]]}
    warm = np.zeros(len(ts), bool); warm[:900] = True     # E-0911-A
    d["warm"] = warm
    return d

def mask(d, span):
    lo, hi = SPANS[span]
    return (~d["warm"]) & (d["ts"] >= lo) & (d["ts"] <= hi) & np.isfinite(d["g"])

def pair(a, b, span):
    ma, mb = mask(a, span), mask(b, span)
    ts = np.intersect1d(a["ts"][ma], b["ts"][mb])
    ia = np.searchsorted(a["ts"], ts); ib = np.searchsorted(b["ts"], ts)
    assert np.array_equal(a["ts"][ia], ts) and np.array_equal(b["ts"][ib], ts)
    return ts, ia, ib

def boot_ci(x, ts, k=9, B=2000, alphas=(0.05,)):
    day = (ts // 86400).astype(np.int64)
    u, inv = np.unique(day, return_inverse=True)
    S = np.bincount(inv, weights=x, minlength=len(u))
    N = np.bincount(inv, minlength=len(u)).astype(float)
    rng = np.random.default_rng([20260905, k])
    idx = rng.integers(0, len(u), size=(B, len(u)))
    mn = S[idx].sum(1) / N[idx].sum(1)
    return {a: (float(np.percentile(mn, 100 * a / 2)), float(np.percentile(mn, 100 * (1 - a / 2))))
            for a in alphas}

def sr(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 else float("nan")

def arm_table(arm, span, baseline=None):
    real = load(arm + "__REAL")
    if real is None:
        return None
    base = load(baseline) if baseline else None
    def lvl(d):
        m = mask(d, span)
        if base is None:
            return {k: float(np.mean(d[k][m])) for k in ("g", "ggross", "gcarry", "gcost", "turn")} | \
                   {"n": int(m.sum()), "SR": sr(d["g"][m])}
        ts, ia, ib = pair(d, base, span)
        return {"g": float(np.mean(d["g"][ia] - base["g"][ib])),
                "ggross": float(np.mean(d["ggross"][ia] - base["ggross"][ib])),
                "gcarry": float(np.mean(d["gcarry"][ia] - base["gcarry"][ib])),
                "gcost": float(np.mean(d["gcost"][ia])),
                "turn": float(np.mean(d["turn"][ia])),
                "n": len(ts), "SR": sr(d["g"][ia] - base["g"][ib])}
    def raw_lvl(d):
        m = mask(d, span)
        return {k: float(np.mean(d[k][m])) for k in ("g", "ggross", "gcarry", "gcost", "turn")} | \
               {"n": int(m.sum()), "SR": sr(d["g"][m])}
    row = {"arm": arm, "span": span, "paired_vs": baseline,
           "real": lvl(real), "real_level_unpaired": raw_lvl(real), "nulls": {}}
    for nt in list(FAM):
        nd = load(arm + "__" + nt)
        if nd is None:
            continue
        L = lvl(nd)
        ts, ir, inn = pair(real, nd, span)
        dif = real["g"][ir] - nd["g"][inn]
        difg = real["ggross"][ir] - nd["ggross"][inn]
        ci = boot_ci(dif, ts, alphas=(0.05, 0.05 / K_DECLARED))
        row["nulls"][nt] = L | {"family": FAM[nt],
                                "cost_ratio_null_over_real": L["gcost"] / max(row["real"]["gcost"], 1e-12),
                                "margin_net": float(dif.mean()),
                                "margin_gross": float(difg.mean()),
                                "margin_net_CI95": ci[0.05],
                                "margin_net_CI_BONF%d" % K_DECLARED: ci[0.05 / K_DECLARED]}
    # pooled matched null = the average of the admissible turnover-matched nulls
    have = [nt for nt in MATCHED if nt in row["nulls"]]
    if have:
        ND = [load(arm + "__" + nt) for nt in have]
        ts = real["ts"][mask(real, span)]
        for d in ND:
            ts = np.intersect1d(ts, d["ts"][mask(d, span)])
        ir = np.searchsorted(real["ts"], ts)
        G = np.array([d["g"][np.searchsorted(d["ts"], ts)] for d in ND])
        GG = np.array([d["ggross"][np.searchsorted(d["ts"], ts)] for d in ND])
        KC = np.array([d["gcost"][np.searchsorted(d["ts"], ts)] for d in ND])
        dif = real["g"][ir] - G.mean(0)
        difg = real["ggross"][ir] - GG.mean(0)
        ci = boot_ci(dif, ts, alphas=(0.05, 0.05 / K_DECLARED))
        cr = float(KC.mean() / max(np.mean(real["gcost"][ir]), 1e-12))
        # cost-matched null net: charge the pooled null the REAL arm's cost bill
        cm = float(np.mean(G.mean(0) + KC.mean(0) - np.mean(real["gcost"][ir])))
        adm = 0.75 <= cr <= 1.25
        ok95 = ci[0.05][0] > 0
        okB = ci[0.05 / K_DECLARED][0] > 0
        verdict = ("SURVIVES" if (adm and difg.mean() > 0 and okB) else
                   "SURVIVES_NOMINAL" if (adm and difg.mean() > 0 and ok95) else
                   "FAILS" if adm else "UNRESOLVED_null_not_matched")
        row["pooled_matched"] = {"nulls": have, "n": len(ts),
                                 "null_g": float(G.mean()), "null_ggross": float(GG.mean()),
                                 "null_gcost": float(KC.mean()), "cost_ratio": cr,
                                 "null_g_costmatched": cm,
                                 "margin_net": float(dif.mean()), "margin_gross": float(difg.mean()),
                                 "margin_net_costmatched": float(np.mean(real["g"][ir]) - cm),
                                 "CI95": ci[0.05], "CI_BONF%d" % K_DECLARED: ci[0.05 / K_DECLARED],
                                 "admissible": adm, "verdict": verdict}
    # ---- per-family aggregation + the best cost-MATCHED family.
    # The family is chosen on the COST RATIO ONLY (a criterion independent of the P&L
    # outcome), never on the margin. Reported alongside the pre-declared pooled read.
    FAMS = {"R": ["R1","R2","R3"], "RO": ["O1","O2"], "T": ["T1","T2","T3"]}
    byfam = {}
    for fam, tags in FAMS.items():
        have = [t for t in tags if t in row["nulls"]]
        if not have: continue
        ND = [load(arm + "__" + t) for t in have]
        ts = real["ts"][mask(real, span)]
        for d in ND: ts = np.intersect1d(ts, d["ts"][mask(d, span)])
        ir = np.searchsorted(real["ts"], ts)
        G  = np.array([d["g"][np.searchsorted(d["ts"], ts)] for d in ND])
        GG = np.array([d["ggross"][np.searchsorted(d["ts"], ts)] for d in ND])
        KC = np.array([d["gcost"][np.searchsorted(d["ts"], ts)] for d in ND])
        dif = real["g"][ir] - G.mean(0); difg = real["ggross"][ir] - GG.mean(0)
        ci = boot_ci(dif, ts, alphas=(0.05, 0.05/K_DECLARED))
        byfam[fam] = {"tags": have, "n": len(ts), "null_g": float(G.mean()),
                      "null_ggross": float(GG.mean()), "null_gcost": float(KC.mean()),
                      "cost_ratio": float(KC.mean()/max(np.mean(real["gcost"][ir]), 1e-12)),
                      "margin_net": float(dif.mean()), "margin_gross": float(difg.mean()),
                      "CI95": ci[0.05], "CI_BONF%d" % K_DECLARED: ci[0.05/K_DECLARED]}
    row["by_family"] = byfam
    if byfam:
        bf = min(byfam, key=lambda f: abs(np.log(max(byfam[f]["cost_ratio"], 1e-9))))
        b = byfam[bf]
        adm = 0.75 <= b["cost_ratio"] <= 1.25
        v = ("SURVIVES" if (adm and b["margin_gross"] > 0 and b["CI_BONF%d" % K_DECLARED][0] > 0) else
             "SURVIVES_NOMINAL" if (adm and b["margin_gross"] > 0 and b["CI95"][0] > 0) else
             "FAILS" if adm else "UNRESOLVED_null_not_matched")
        row["best_matched_family"] = {"family": bf, "verdict": v} | b
    if "P1" in row["nulls"]:
        p = row["nulls"]["P1"]
        row["legacy_bias"] = {"legacy_margin_net": p["margin_net"],
                              "matched_margin_net": row.get("pooled_matched", {}).get("margin_net"),
                              "bias_bps": (p["margin_net"] - row.get("pooled_matched", {}).get("margin_net", np.nan)),
                              "legacy_cost_ratio": p["cost_ratio_null_over_real"]}
    return row

if __name__ == "__main__":
    arms = sorted({os.path.basename(f)[:-len("__REAL.npz")]
                   for f in glob.glob(OUT + "/*__REAL.npz")})
    PAIR = {"XIB_LAG50_s42": "IB_PARITY_s42", "XIB_LAG50_s2027": "IB_PARITY_s2027", "XIB50_s42": "IB_PARITY_s42", "XIB50_s2027": "IB_PARITY_s2027",
            "IB_TRI_B_s42": "IB_PARITY_s42"}
    res = {}
    for a in arms:
        for span in ("FULL", "F23", "FROZEN"):
            r = arm_table(a, span, PAIR.get(a))
            if r: res["%s|%s" % (a, span)] = r
    json.dump(res, open(R + "/JUDGE_r3_placebo.json", "w"), indent=1)
    # ---- printed table
    hdr = ("%-22s %-6s %6s | %8s %8s %7s | %8s %8s %7s %6s | %9s %9s %9s | %-22s")
    print(hdr % ("arm", "span", "n", "RE_net", "RE_gross", "RE_cost", "NL_net", "NL_gross",
                 "NL_cost", "c_rat", "mrg_net", "mrg_gross", "mrg_cm", "verdict"))
    for k in sorted(res):
        r = res[k]
        if "pooled_matched" not in r: continue
        pm = r["pooled_matched"]; re = r["real"]
        print(hdr % (r["arm"][:22], r["span"], pm["n"], "%+.4f" % re["g"], "%+.4f" % re["ggross"],
                     "%.4f" % re["gcost"], "%+.4f" % pm["null_g"], "%+.4f" % pm["null_ggross"],
                     "%.4f" % pm["null_gcost"], "%.2f" % pm["cost_ratio"],
                     "%+.4f" % pm["margin_net"], "%+.4f" % pm["margin_gross"],
                     "%+.4f" % pm["margin_net_costmatched"],
                     pm["verdict"] + " CI[%+.3f,%+.3f]" % pm["CI95"]))
