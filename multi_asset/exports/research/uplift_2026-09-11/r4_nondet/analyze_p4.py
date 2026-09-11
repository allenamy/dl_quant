"""P4 item 2 -- THE BOOK-LAYER CONSEQUENCE of DL training nondeterminism.

Statistic copied VERBATIM from r3k_analyze3.py (which itself copied judge_v4 / round-2 integrate.py):
  g = net_ex / gross_total, bps per anchor per unit gross; Sharpe = mean/sd(ddof=1)*sqrt(2190).
E-0911-A: the first LOOK=900 device rows are dropped from every reading (seat warm-up).
COST: the FITTED model r3k/costb_PWR_G230k.json (sha 295b4e7b462373e4) -- every arm here was produced with it.

Groups:
  SAME42  : draws that differ ONLY by the training RUN (seed pinned to 42), all in TODAY's environment
  OTHSEED : draws that differ by SEED, one run each, same environment  (round-3 s7/s101/s1234/s31337)
  ARCH    : the archived s42 / s2027 preds the in-service book's evidence rides (different environment)
"""
import numpy as np, json, os, sys, itertools

R = "/workspace/uplift_2026-09-11/r4_nondet"; A = R + "/arms"
APY = 2190


def ep(s): return int((np.datetime64(s) - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s"))


SPANS = {"FULL": (ep("2022-01-01T00:00"), ep("2026-08-10T20:00")),
         "F23": (ep("2023-01-01T00:00"), ep("2026-08-10T20:00")),
         "FROZEN": (ep("2025-03-01T00:00"), ep("2026-08-10T20:00"))}


def rd(label, seat, cb="PWR230k"):
    p = "%s/w10_ablation_series_R4_A0_%s_%s_s%s.npz" % (A, cb, seat, label)
    Z = np.load(p, allow_pickle=True)
    Rr = np.asarray(Z["d30_n2_c42_rec"], float); cols = [str(c) for c in Z["cols"]]
    ix = {c: i for i, c in enumerate(cols)}
    ts = Rr[:, ix["ts"]].astype(np.int64)
    gt = Rr[:, ix["gross_total"]]
    g = np.where(gt > 0, Rr[:, ix["net_ex"]] / np.maximum(gt, 1e-12), np.nan)
    return ts, g, {c: Rr[:, ix[c]] for c in ("turnover", "w3_king", "w3_fund", "cost_ex", "pnl_ex", "carry_ex", "gross_total")}


def series(ts, g, span, postwarm=True):
    lo, hi = SPANS[span]
    m = (ts >= lo) & (ts <= hi) & np.isfinite(g)
    if postwarm:
        w = np.zeros(len(ts), bool); w[:900] = True; m &= ~w
    return ts[m], g[m]


def sr(x): return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(APY)) if len(x) > 2 else float("nan")


# groups passed as JSON: {"SAME_SEED42_V2ONE":[...], "SAME_SEED42_V2ZERO":[...], "SEEDS_V2ZERO":[...], "ARCHIVED_V2ONE":[...]}
GRP = json.loads(sys.argv[1])
SAME42 = GRP["SAME_SEED42_V2ONE"]
OTHSEED = GRP.get("SEEDS_V2ZERO", [])
ARCH = GRP.get("ARCHIVED_V2ONE", ["42", "2027"])
ALL = sorted(set(sum(GRP.values(), [])))
OUT = {"cost_model": "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json",
       "statistic": "g=net_ex/gross_total; SR=mean/sd(ddof=1)*sqrt(2190); first 900 device rows dropped",
       "groups": GRP}
LV = {}
for seat in ("dyn", "fix"):
    for L in ALL:
        try:
            ts, g, C = rd(L, seat)
        except FileNotFoundError:
            print("MISSING", L, seat); continue
        row = {}
        for sp in SPANS:
            t, x = series(ts, g, sp, True)
            row[sp + "_pw"] = {"n": int(len(x)), "g": round(float(x.mean()), 4), "SR": round(sr(x), 4)}
        m = np.zeros(len(ts), bool); m[900:] = True
        lo, hi = SPANS["FULL"]; m &= (ts >= lo) & (ts <= hi)
        row["turnover_mean"] = round(float(C["turnover"][m].mean()), 5)
        row["w3_king_mean"] = round(float(C["w3_king"][m].mean()), 5)
        row["w3_fund_mean"] = round(float(C["w3_fund"][m].mean()), 5)
        LV["%s|%s" % (seat, L)] = row
OUT["levels"] = LV


def stat(vals):
    v = np.array(vals, float)
    return {"n": int(len(v)), "mean": round(float(v.mean()), 4), "sd": round(float(v.std(ddof=1)), 4),
            "min": round(float(v.min()), 4), "max": round(float(v.max()), 4),
            "range": round(float(v.max() - v.min()), 4)}


DIST = {}
for seat in ("dyn", "fix"):
    for sp in ("FULL", "F23", "FROZEN"):
        for gname, G in GRP.items():
            ks = ["%s|%s" % (seat, L) for L in G if "%s|%s" % (seat, L) in LV]
            if len(ks) < 2: continue
            srs = [LV[k][sp + "_pw"]["SR"] for k in ks]
            gs = [LV[k][sp + "_pw"]["g"] for k in ks]
            DIST["%s|%s|%s" % (seat, sp, gname)] = {"SR": stat(srs), "g": stat(gs),
                                                    "SE_of_one_SR_estimate": round(float(np.sqrt(APY / LV[ks[0]][sp + "_pw"]["n"])), 4),
                                                    "per_draw_SR": {k.split("|")[1]: LV[k][sp + "_pw"]["SR"] for k in ks}}
OUT["distributions"] = DIST

# --- where does the in-service (archived) draw sit inside the same-seed distribution? ---
POS = {}
for seat in ("dyn", "fix"):
    for sp in ("FULL", "F23", "FROZEN"):
        ks = ["%s|%s" % (seat, L) for L in SAME42 if "%s|%s" % (seat, L) in LV]
        if not ks: continue
        srs = np.array([LV[k][sp + "_pw"]["SR"] for k in ks])
        a = LV["%s|42" % seat][sp + "_pw"]["SR"]
        POS["%s|%s" % (seat, sp)] = {"archived_s42_SR": a, "same_seed_mean": round(float(srs.mean()), 4),
                                     "z_vs_same_seed": round(float((a - srs.mean()) / srs.std(ddof=1)), 3),
                                     "frac_of_draws_below_archived": round(float((srs < a).mean()), 3),
                                     "n_draws": int(len(srs))}
OUT["inservice_position"] = POS

# --- per-anchor paired dispersion between draws (connects to round-2's mean|dg|) ---
PAIR = {}
for seat in ("dyn", "fix"):
    for gname, G in GRP.items():
        rows = []
        if len(G) < 2: continue
        for a, b in itertools.combinations(G, 2):
            ta, ga, _ = rd(a, seat); tb, gb, _ = rd(b, seat)
            com, ia, ib = np.intersect1d(ta, tb, return_indices=True)
            lo, hi = SPANS["FULL"]
            m = (com >= lo) & (com <= hi); w = np.zeros(len(com), bool)
            w[:900] = True; m &= ~w
            d = (ga[ia] - gb[ib])[m]
            rows.append({"pair": "%s-%s" % (a, b), "mean_abs_dg": round(float(np.abs(d).mean()), 4),
                         "sd_dg": round(float(d.std(ddof=1)), 4), "mean_dg": round(float(d.mean()), 4)})
        if rows:
            PAIR["%s|%s" % (seat, gname)] = {"pairs": rows,
                                             "mean_abs_dg_avg": round(float(np.mean([r["mean_abs_dg"] for r in rows])), 4),
                                             "sd_of_mean_dg": round(float(np.std([r["mean_dg"] for r in rows], ddof=1)), 4)}
OUT["per_anchor_pairs"] = PAIR

# --- seat amplification: is the dyn (msharpe) seat noisier than the frozen-weight seat? ---
AMPG = sys.argv[2] if len(sys.argv) > 2 else "SEEDS_V2ZERO"
AMP = {"group_used": AMPG}
for sp in ("FULL", "F23", "FROZEN"):
    d = DIST.get("dyn|%s|%s" % (sp, AMPG)); f = DIST.get("fix|%s|%s" % (sp, AMPG))
    if not (d and f): continue
    GG = GRP[AMPG]
    wd = np.mean([LV["dyn|%s" % L]["w3_king_mean"] for L in GG])
    wf = np.mean([LV["fix|%s" % L]["w3_king_mean"] for L in GG])
    AMP[sp] = {"sd_SR_dyn": d["SR"]["sd"], "sd_SR_fix": f["SR"]["sd"],
               "ratio_dyn_over_fix": round(d["SR"]["sd"] / f["SR"]["sd"], 3) if f["SR"]["sd"] > 0 else None,
               "mean_model_leg_weight_dyn": round(float(wd), 4), "mean_model_leg_weight_fix": round(float(wf), 4),
               "sd_SR_dyn_per_unit_modelweight": round(d["SR"]["sd"] / wd, 4),
               "sd_SR_fix_per_unit_modelweight": round(f["SR"]["sd"] / wf, 4),
               "sd_of_dyn_model_leg_weight_across_draws":
                   round(float(np.std([LV["dyn|%s" % L]["w3_king_mean"] for L in GG], ddof=1)), 5)}
OUT["seat_amplification"] = AMP

json.dump(OUT, open(R + "/receipts/RESULT_P4_book.json", "w"), indent=1)
print(json.dumps({k: OUT[k] for k in ("distributions", "inservice_position", "seat_amplification")}, indent=1))
print("ANALYZE_P4_DONE")
