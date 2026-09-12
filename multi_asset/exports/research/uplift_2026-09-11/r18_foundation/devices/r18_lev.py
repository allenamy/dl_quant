#!/usr/bin/env python3
"""r18_lev.py — N4 / LEV12-FIX (PREREG_r18 §5.5, §6): r12's leverage/risk gate recomputed with TRUE rolling
peak-to-trough maxDD on the 32 archived r12 smoothing arms and on the fixed-baseline arms NW / NW_S05 / NW_B50.
Cross-checks p_true_maxDD25 against the reviewer's RECEIPT_smoothing.json for the six arms it covers.
Read-only, CPU. Writes only receipts/RECEIPT_r18_lev.json.
"""
import os, sys, json, time, hashlib, calendar, glob
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
R = "/workspace/uplift_2026-09-11/r18_foundation"; UP = "/workspace/uplift_2026-09-11"; R12 = UP + "/r12_smoothing"
REV = "/workspace/codex_research/QNT-2026-0907/uplift_review_20260912/statistics/RECEIPT_smoothing.json"
PREREG_SHA = "51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c"; DER_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r18_foundation_2026-09-12.md") == PREREG_SHA
G = json.load(open(R + "/receipts/RECEIPT_r18_drive_gateP.json")); assert G["gate"]["P"]["PASS"]
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); HALT = -0.04; DDLIM = -0.25
LEVS = [round(x, 2) for x in np.arange(0.25, 2.01, 0.125)]; MULTS = (1.0, 1.4042)   # r12's LITERAL grid (lev12.py L22): the 2-decimal ROUNDED values are the leverages actually used (0.88, not 0.875); needed for exact reconciliation
GRID_NOTE = "L grid = r12's literal values [round(x,2) for x in arange(0.25,2.01,0.125)] — i.e. 0.38/0.62/0.88/1.12/1.38/1.62/1.88 are the leverages computed, as in r12 and the reviewer's receipt"
def roll1y(ud, rs):
    tdd, sl, cg = [], [], []
    for s in range(len(ud)):
        e = np.searchsorted(ud, ud[s] + 365 * 86400, side="right")
        if e - s < 300 or ud[e - 1] - ud[s] < 350 * 86400: continue
        nav = np.concatenate([[1.0], np.cumprod(1.0 + rs[s:e])]); tdd.append(float((nav / np.maximum.accumulate(nav) - 1.0).min())); sl.append(float(nav[1:].min() - 1.0)); cg.append(float(nav[-1] - 1.0))
    return np.array(tdd), np.array(sl), np.array(cg)
def table(g, days):
    ud, inv = np.unique(days, return_inverse=True); yrs = (ud[-1] - ud[0]) / (365.25 * 86400); out = {}
    for M in MULTS:
        rows = {}
        for L in LEVS:
            rd = np.ones(len(ud)); np.multiply.at(rd, inv, 1.0 + L * g * 1e-4); rd -= 1.0; mu = rd.mean(); rs = mu + M * (rd - mu)
            tdd, sl, cg = roll1y(ud, rs); nav = np.concatenate([[1.0], np.cumprod(1.0 + rs)])
            rows["%.3f" % L] = dict(halt_per_yr=float((rs <= HALT).sum() / yrs), p_true_maxDD25=float((tdd <= DDLIM).mean()), p_start_loss25=float((sl <= DDLIM).mean()), median_1y_ret_pct=float(np.median(cg) * 100),
                                    worst_day_pct=float(rs.min() * 100), maxdd_pct=float((nav / np.maximum.accumulate(nav) - 1.0).min() * 100), n_windows=int(len(cg)))
        feas_true = [L for L in LEVS if rows["%.3f" % L]["halt_per_yr"] <= 1.0 and rows["%.3f" % L]["p_true_maxDD25"] <= 0.10]
        feas_old = [L for L in LEVS if rows["%.3f" % L]["halt_per_yr"] <= 1.0 and rows["%.3f" % L]["p_start_loss25"] <= 0.10]
        bt, bo = (max(feas_true) if feas_true else None), (max(feas_old) if feas_old else None)
        out["M%.4f" % M] = dict(rows=rows, max_feasible_L_true=bt, median_1y_ret_at_feasible_true_pct=(rows["%.3f" % bt]["median_1y_ret_pct"] if bt else None), max_feasible_L_oldgate=bo, median_1y_ret_at_feasible_oldgate_pct=(rows["%.3f" % bo]["median_1y_ret_pct"] if bo else None),
                                at_L1=rows["1.000"], at_L2=rows["2.000"])
    return out
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, env=ENV, grid_L=LEVS, grid_note=GRID_NOTE, mults=list(MULTS), arms={})
def add(tag, p, rec, cfg, alpha, band, seed, kind):
    ts = rec[:, 0].astype(np.int64); m = ts <= UB; assert m.sum() == 10038, (tag, m.sum())
    g = (rec[:, 18] / rec[:, 5])[m]; days = (ts[m] // 86400) * 86400
    OUT["arms"][tag] = dict(path=p, sha256=sha(p), SMA=alpha, SBAND=band, seed=seed, kind=kind, n=int(m.sum()), mean_g_WT=float(g.mean()), **table(g, days))
    a = OUT["arms"][tag]["M1.4042"]; b = OUT["arms"][tag]["M1.0000"]
    print("%-26s a=%.2f b=%.2e %s | M1.4042: L1 p_true %.4f p_start %.4f halt/yr %.2f med1y %+.1f%% | feasible(true) %s med %s | feasible(old) %s || M1.0: feasible(true) %s med %s" % (
        tag, alpha, band, kind, a["at_L1"]["p_true_maxDD25"], a["at_L1"]["p_start_loss25"], a["at_L1"]["halt_per_yr"], a["at_L1"]["median_1y_ret_pct"], a["max_feasible_L_true"], ("%+.1f%%" % a["median_1y_ret_at_feasible_true_pct"]) if a["max_feasible_L_true"] else "n/a",
        a["max_feasible_L_oldgate"], b["max_feasible_L_true"], ("%+.1f%%" % b["median_1y_ret_at_feasible_true_pct"]) if b["max_feasible_L_true"] else "n/a"), flush=True)
for f in sorted(glob.glob(R12 + "/arms/S_*.npz")):
    Z = np.load(f, allow_pickle=True); cfg = json.loads(str(Z["config_json"])); assert cfg["LEGS"] == "101" and cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["COSTB_JSON"].endswith("costb_PWR_G230k.json"), cfg
    add(os.path.basename(f)[:-4], f, np.asarray(Z["rec"], float), cfg, cfg["SMA"], cfg["SBAND"], cfg["FSEED"], "archived_r12_defects_on")
for fam in ("NW", "NW_S05", "NW_B50"):
    for s in ("42", "2027"):
        p = R + "/arms/%s_s%s.npz" % (fam, s); Z = np.load(p, allow_pickle=True); cfg = json.loads(str(Z["config_json"])); assert cfg["UPLIFT"]["self_sha256"] == DER_SHA and cfg["R18"]["R18_ELIG"] == 1 and cfg["R18"]["R18_WARM"] == 1
        add("%s_s%s" % (fam, s), p, np.asarray(Z["d30_n2_c42_rec"], float), cfg, cfg["R18"]["SMA"], cfg["R18"]["SBAND"], cfg["FSEED"], "fixed_baseline_r18")
# ---- reconciliation with r12's stored LEV12.json (p_1y_dd_ge25 must equal my p_start_loss25 at M=1.4042) and the reviewer's receipt
L12 = json.load(open(R12 + "/LEV12.json")); rec12 = {}
BY2 = {round(L, 2): "%.3f" % L for L in LEVS}; mk2 = lambda k: BY2[round(float(k), 2)]   # r12 / reviewer keys are 2-decimal strings ("0.38" = 0.375)
for tag, d in L12.items():
    mine = OUT["arms"][tag]["M1.4042"]["rows"]; diffs = [abs(d["rows"][k]["p_1y_dd_ge25"] - mine[mk2(k)]["p_start_loss25"]) for k in d["rows"]]
    hd = [abs(d["rows"][k]["halt_per_yr"] - mine[mk2(k)]["halt_per_yr"]) for k in d["rows"]]; md = [abs(d["rows"][k]["median_1y_cagr_pct"] - mine[mk2(k)]["median_1y_ret_pct"]) for k in d["rows"]]
    rec12[tag] = dict(max_abs_diff_p_start_loss25=float(max(diffs)), max_abs_diff_halt_per_yr=float(max(hd)), max_abs_diff_median_1y=float(max(md)), r12_max_feasible=d["max_feasible_leverage"], mine_max_feasible_oldgate=OUT["arms"][tag]["M1.4042"]["max_feasible_L_oldgate"])
OUT["reconcile_r12_LEV12"] = dict(per_arm=rec12, all_match_1e9=bool(all(v["max_abs_diff_p_start_loss25"] < 1e-9 and v["max_abs_diff_halt_per_yr"] < 1e-9 and v["max_abs_diff_median_1y"] < 1e-9 for v in rec12.values())), all_feasible_match=bool(all(v["r12_max_feasible"] == v["mine_max_feasible_oldgate"] for v in rec12.values())), LEV12_sha256=sha(R12 + "/LEV12.json"))
RV = json.load(open(REV)); recr = {}
for tag, d in RV["arms"].items():
    o = {}
    for M in ("1.0", "1.4042"):
        mk = "M%.4f" % float(M); mine = OUT["arms"][tag][mk]["rows"]; theirs = d["sensitivity"][M]["table"]
        o[mk] = dict(max_abs_diff_p_true=float(max(abs(theirs[k]["p_true_maxDD25"] - mine[mk2(k)]["p_true_maxDD25"]) for k in theirs)), max_abs_diff_p_start=float(max(abs(theirs[k]["p_start_loss25"] - mine[mk2(k)]["p_start_loss25"]) for k in theirs)),
                     max_abs_diff_halt=float(max(abs(theirs[k]["halt_per_year"] - mine[mk2(k)]["halt_per_yr"]) for k in theirs)), theirs_feasible_true=d["sensitivity"][M]["max_feasible_true_maxDD"], mine_feasible_true=OUT["arms"][tag][mk]["max_feasible_L_true"],
                     theirs_L1_p_true=theirs["1.0"]["p_true_maxDD25"], mine_L1_p_true=mine["1.000"]["p_true_maxDD25"])
    recr[tag] = o
OUT["reconcile_reviewer"] = dict(per_arm=recr, receipt_sha256=sha(REV), all_match_1e9=bool(all(v[m]["max_abs_diff_p_true"] < 1e-9 and v[m]["max_abs_diff_p_start"] < 1e-9 for v in recr.values() for m in v)))
print("RECONCILE r12 LEV12:", OUT["reconcile_r12_LEV12"]["all_match_1e9"], OUT["reconcile_r12_LEV12"]["all_feasible_match"]); print("RECONCILE reviewer:", OUT["reconcile_reviewer"]["all_match_1e9"], json.dumps({k: {m: (v[m]["theirs_L1_p_true"], v[m]["mine_L1_p_true"]) for m in v} for k, v in recr.items()}))
# ---- round-12 claims (PREREG §5.5 a-e)
def cl(tag, M="M1.4042"): return OUT["arms"][tag][M]
D, S05, B50 = "S_a010_b25e4_s42", "S_a005_b25e4_s42", "S_a010_b50e4_s42"
claims = {}
claims["a_deployed_feasible_at_L1"] = dict(claim="deployed (.10, 2.5e-4) feasible at L=1.00 with P(1y DD>=25%)=0.086", old_gate_p_start_L1=cl(D)["at_L1"]["p_start_loss25"], true_p_L1=cl(D)["at_L1"]["p_true_maxDD25"], halt_per_yr_L1=cl(D)["at_L1"]["halt_per_yr"],
                                           feasible_true=cl(D)["max_feasible_L_true"], median_at_feasible_true=cl(D)["median_1y_ret_at_feasible_true_pct"], verdict=("PASS" if cl(D)["at_L1"]["p_true_maxDD25"] <= 0.10 and cl(D)["at_L1"]["halt_per_yr"] <= 1 else "FAIL"))
claims["b_S05_plus9p2"] = dict(claim="(.05, 2.5e-4): +9.2% median 1y at L=1.00 / +8.2% at feasible 0.88", old_gate_p_start_L1=cl(S05)["at_L1"]["p_start_loss25"], true_p_L1=cl(S05)["at_L1"]["p_true_maxDD25"], median_L1=cl(S05)["at_L1"]["median_1y_ret_pct"],
                              feasible_true=cl(S05)["max_feasible_L_true"], median_at_feasible_true=cl(S05)["median_1y_ret_at_feasible_true_pct"], feasible_oldgate=cl(S05)["max_feasible_L_oldgate"],
                              verdict=("PASS" if cl(S05)["at_L1"]["p_true_maxDD25"] <= 0.10 else "FAIL (never passed: old-gate P at L=1 was %.4f > 0.10 too)" % cl(S05)["at_L1"]["p_start_loss25"]))
claims["c_B50_feasible_L1_plus5p6"] = dict(claim="(.10, 5e-4) feasible at L=1.00, +5.6%", old_gate_p_start_L1=cl(B50)["at_L1"]["p_start_loss25"], true_p_L1=cl(B50)["at_L1"]["p_true_maxDD25"], median_L1=cl(B50)["at_L1"]["median_1y_ret_pct"], feasible_true=cl(B50)["max_feasible_L_true"],
                                          median_at_feasible_true=cl(B50)["median_1y_ret_at_feasible_true_pct"], verdict=("PASS" if cl(B50)["at_L1"]["p_true_maxDD25"] <= 0.10 and cl(B50)["at_L1"]["halt_per_yr"] <= 1 else "FAIL"))
def direction(dep, s05, b50, M):
    r = {t: (OUT["arms"][t][M]["max_feasible_L_true"], OUT["arms"][t][M]["median_1y_ret_at_feasible_true_pct"], OUT["arms"][t][M]["at_L1"]["median_1y_ret_pct"], OUT["arms"][t][M]["at_L1"]["p_true_maxDD25"]) for t in (dep, s05, b50)}
    med = {t: v[1] for t, v in r.items()}; medL1 = {t: v[2] for t, v in r.items()}
    return dict(per_arm={t: dict(feasible_L_true=v[0], median_at_feasible=v[1], median_at_L1=v[2], p_true_L1=v[3]) for t, v in r.items()},
                slower_better_at_feasible=bool(med[dep] is not None and med[s05] is not None and med[b50] is not None and med[s05] > med[dep] and med[b50] > med[dep]), slower_better_at_L1=bool(medL1[s05] > medL1[dep] and medL1[b50] > medL1[dep]),
                same_feasible_L=bool(r[dep][0] == r[s05][0] == r[b50][0]))
claims["d_slower_is_better"] = dict(archived_s42={M: direction(D, S05, B50, M) for M in ("M1.0000", "M1.4042")}, archived_s2027={M: direction("S_a010_b25e4_s2027", "S_a005_b25e4_s2027", "S_a010_b50e4_s2027", M) for M in ("M1.0000", "M1.4042")},
                                   fixed_s42={M: direction("NW_s42", "NW_S05_s42", "NW_B50_s42", M) for M in ("M1.0000", "M1.4042")}, fixed_s2027={M: direction("NW_s2027", "NW_S05_s2027", "NW_B50_s2027", M) for M in ("M1.0000", "M1.4042")},
                                   note="POINT ESTIMATES on one historical path (overlapping 1y windows); no CI. Direction only.")
claims["e_infeasible_at_2x_whole_grid"] = dict(claim="at 2.0x the constraint is infeasible for the whole grid", any_arm_feasible_at_2_true_M14042=bool(any(v["M1.4042"]["rows"]["2.000"]["p_true_maxDD25"] <= 0.10 and v["M1.4042"]["rows"]["2.000"]["halt_per_yr"] <= 1 for v in OUT["arms"].values())),
                                              any_arm_feasible_at_2_true_M1=bool(any(v["M1.0000"]["rows"]["2.000"]["p_true_maxDD25"] <= 0.10 and v["M1.0000"]["rows"]["2.000"]["halt_per_yr"] <= 1 for v in OUT["arms"].values())), verdict="REAFFIRMED (stricter gate)" if not any(v["M1.4042"]["rows"]["2.000"]["p_true_maxDD25"] <= 0.10 and v["M1.4042"]["rows"]["2.000"]["halt_per_yr"] <= 1 for v in OUT["arms"].values()) else "CHANGED")
OUT["round12_claims"] = claims; OUT["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(OUT, open(R + "/receipts/RECEIPT_r18_lev.json", "w"), indent=1, default=float)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("archived_s42", "archived_s2027", "fixed_s42", "fixed_s2027")} for k, v in claims.items()}, indent=1)); print(json.dumps(claims["d_slower_is_better"], indent=1))
print("DONE_r18_lev")
