#!/usr/bin/env python3
"""caliber_audit_recompute.py -- the judgement device for the CALIBER AUDIT (handoff, 2026-09-12).

Every number in CANONICAL_NUMBERS_2026-09-12.md that is labelled [V-me] is produced here.
READ-ONLY: reads the archived pinned A0 arm + the archived cost-fit receipts. No live tree,
no pod2, no GPU, no network.

E-0826-D: env whitelist = EMPTY SET, asserted below.
E-0904-F: no expm1 anywhere; intra-day NAV compounding is an explicit product of (1+r).
E-0909-C: every drawdown prepends the starting point.
Arithmetic for the daily/ladder block is transcribed from r11_tail/devices/r11_tail.py
(daily_from_grid / maxdd / realised_block) so the two devices are comparable line for line.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np

_WATCHED = ["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","W3FIX","MEMBERS_TOPN","TRADE_TOPN",
            "FTRIM","FTRIM_TH","FTPOS","RNSM","LTRIM_TH","CDAMP","SLEEVE","SEATNET","SEATF10",
            "KTAIL","KMOD","KMOD_L","KMOD_AGREE","KMOD_F10","FUNDSCALE","FEMAT_NPZ","UMASK_NPZ",
            "UMASK_SCOPE","REF_SKIP","COSTB_JSON","SLOW_NPY","JUDGE_HC","JUDGE_REQUIRE_W",
            "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","OMP_NUM_THREADS","PYTHONHASHSEED"]
_set = {k: os.environ[k] for k in _WATCHED if k in os.environ}
assert _set == {}, f"env whitelist violated (expected empty set), found: {_set}"

U = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
PIN = f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
DEV = f"{U}/trackA/w10_sleeve.py"
COSTB = f"{U}/r3k_impact/costb_PWR_G230k.json"
FITK3 = f"{U}/r3k_impact/FITK_v3_shape.json"
FITK2 = f"{U}/r3k_impact/FITK_v2.json"
ARMS13A = f"{U}/r13_A_halfscale/receipts/r13A_arms.npz"
OUT = f"{U}/handoff_audit/caliber/RECEIPT_caliber_audit_2026-09-12.json"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

INPUTS = {p: sha256(p) for p in (PIN, DEV, COSTB, FITK3, FITK2, ARMS13A)}
assert INPUTS[DEV][:16] == "b88e35a46b93d712", "pinned device sha != CALIBER_PIN_v4"
assert INPUTS[COSTB][:16] == "295b4e7b462373e4", "cost book sha != the file every round cites"

Z = np.load(PIN, allow_pickle=True)
CFG = json.loads(str(Z["config_json"]))
assert CFG["UPLIFT"]["self_sha256"][:16] == "b88e35a46b93d712"
assert CFG["CAL"] == "log" and CFG["PHI"] == 0.45 and CFG["LEGS"] == "101"
assert CFG["WRULE"] == "msharpe" and CFG["LOOK"] == 900 and CFG["W3FIX"] is None
assert CFG["UMASK_SCOPE"] == "m1" and CFG["COSTB_JSON"].endswith("costb_PWR_G230k.json")

COLS = [str(c) for c in Z["cols"]]; C = {k: i for i, k in enumerate(COLS)}; R = Z["rec"]
ts = R[:, C["ts"]].astype(np.int64)
def col(n): return R[:, C[n]]
g_all = col("net_ex") / col("gross_total")

T = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%d %H"))
UB_D   = T("2026-08-30 20")   # E-0911-D instrument ceiling
UB_810 = T("2026-08-10 20")   # the r1-r5 full-cycle cap
FROZ0  = T("2025-03-01 00")
warm = np.zeros(len(ts), bool); warm[900:] = True

WINDOWS = {
 "W_ALPHA  post-warm & <=2026-08-30 20Z": warm & (ts <= UB_D),
 "W_TAIL   no warm drop & <=2026-08-30 20Z": (ts <= UB_D),
 "n9018    post-warm & <=2026-08-10 20Z (r1-r5 'FULLCYCLE')": warm & (ts <= UB_810),
 "n9139    post-warm, whole axis (incl 2026-08-31 00Z)": warm,
 "n9918    no warm drop & <=2026-08-10 20Z": (ts <= UB_810),
 "n10039   whole device axis": np.ones(len(ts), bool),
 "FROZEN   2025-03-01..2026-08-10 20Z": (ts >= FROZ0) & (ts <= UB_810),
}

def level(mask):
    g = g_all[mask]; n = len(g); mu = float(g.mean()); sd = float(g.std(ddof=1))
    tr = col("turnover")[mask]; gt = col("gross_total")[mask]
    return dict(n=n, mean_g_bps=mu, sd=sd, sharpe_ann=float(mu/sd*np.sqrt(2190)),
        SE_sharpe=float(np.sqrt(2190/n)),
        pnl_ex_per_gross=float((col("pnl_ex")[mask]/gt).mean()),
        carry_ex_per_gross=float((col("carry_ex")[mask]/gt).mean()),
        cost_ex_per_gross=float((col("cost_ex")[mask]/gt).mean()),
        turnover_RAW_file_column=float(tr.mean()),
        turnover_MATCHED_mean_of_ratios=float((tr/gt).mean()),
        mean_gross_total=float(gt.mean()),
        ratio_matched_over_raw=float((tr/gt).mean()/tr.mean()),
        one_over_mean_gross=float(1.0/gt.mean()),
        effective_cost_bps_per_unit_MATCHED_turnover=float((col("cost_ex")[mask]/gt).mean()/((tr/gt).mean()),),
        first_anchor=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[mask][0]))),
        last_anchor=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[mask][-1]))))

LEVELS = {k: level(m) for k, m in WINDOWS.items()}

# ---- accounting identity: which sign does carry_ex carry? -------------------------------------
m = WINDOWS["W_ALPHA  post-warm & <=2026-08-30 20Z"]
id_plus  = col("net_ex")[m] - (col("pnl_ex")[m] + col("carry_ex")[m] - col("cost_ex")[m])
id_minus = col("net_ex")[m] - (col("pnl_ex")[m] - col("carry_ex")[m] - col("cost_ex")[m])
IDENTITY = {"net_ex-(pnl_ex+carry_ex-cost_ex)_mean": float(id_plus.mean()),
            "net_ex-(pnl_ex+carry_ex-cost_ex)_maxabs": float(np.abs(id_plus).max()),
            "net_ex-(pnl_ex-carry_ex-cost_ex)_mean": float(id_minus.mean()),
            "net_ex-(pnl_ex-carry_ex-cost_ex)_maxabs": float(np.abs(id_minus).max()),
            "VERDICT": "net_ex = pnl_ex - carry_ex - cost_ex EXACTLY (carry is PAID, it is subtracted)"}

# ---- a second, disagreeing turnover series ----------------------------------------------------
ZA = np.load(ARMS13A, allow_pickle=True)
assert np.array_equal(ZA["ts"].astype(np.int64), ts)
TURN2 = {"r13A_base_turn_RAW": float(ZA["base_turn"][m].mean()),
         "r13A_base_turn_MATCHED": float((ZA["base_turn"]/ZA["gross_total"])[m].mean()),
         "file_column_RAW": float(col("turnover")[m].mean()),
         "file_column_MATCHED": float((col("turnover")[m]/col("gross_total")[m]).mean()),
         "cost_ex_maxabs_diff": float(np.abs(ZA["base_cost"][m] - col("cost_ex")[m]).max()),
         "gross_maxabs_diff": float(np.abs(ZA["gross_total"][m] - col("gross_total")[m]).max()),
         "rows_where_turnover_differs_frac": float((np.abs(ZA["base_turn"][m]-col("turnover")[m])>1e-12).mean()),
         "why": "r13A_build_pod.py account(): tu=sum|w-w_prev| over the FULL vector, cost ks=sum(|w-w_prev|[m]*rate) over the MEMBER set. The file column matches the cost caliber; r13A's does not."}

# ---- tail ladder, both windows, arithmetic transcribed from r11_tail.py ------------------------
def ladder(mask):
    g = g_all[mask]; tsx = ts[mask]; days = tsx // 86400
    ud, inv, cnt = np.unique(days, return_inverse=True, return_counts=True)
    assert (cnt == 6).all()
    G = g.reshape(len(ud), 6); out = {"n_days": int(len(ud)), "n_anchors": int(len(g))}
    def mdd(x):
        nav = np.concatenate([[1.0], np.cumprod(1.0 + x)])
        return float((1.0 - nav/np.maximum.accumulate(nav)).max())
    for L in (1.00, 1.25, 1.40, 1.50, 1.75, 2.00, 2.50):
        dr = np.prod(1.0 + L*G/1e4, axis=1) - 1.0
        rdd = np.array([mdd(dr[i:i+365]) for i in range(0, len(dr)-365+1)])
        out[f"{L:.2f}x"] = dict(
            cagr_pct=float((np.prod(1.0+dr)**(365.0/len(dr)) - 1.0)*100),
            ann_vol_pct=float(dr.std(ddof=1)*np.sqrt(365)*100),
            maxDD_pct=float(mdd(dr)*100), worst_day_pct=float(dr.min()*100),
            halts_le_4pct_n=int((dr <= -0.04).sum()),
            halts_le_4pct_per_yr=float((dr <= -0.04).sum()/len(dr)*365),
            alerts_le_2pct_n=int((dr <= -0.02).sum()),
            alerts_le_2pct_per_yr=float((dr <= -0.02).sum()/len(dr)*365),
            rolling1y_n_windows=int(len(rdd)),
            rolling1y_P_maxDD_ge_25pct_EMPIRICAL=float((rdd >= 0.25).mean()),
            rolling1y_median_pct=float(np.median(rdd)*100), rolling1y_max_pct=float(rdd.max()*100))
    return out

LADDER = {"W_ALPHA": ladder(WINDOWS["W_ALPHA  post-warm & <=2026-08-30 20Z"]),
          "W_TAIL":  ladder(WINDOWS["W_TAIL   no warm drop & <=2026-08-30 20Z"])}

# ---- frozen-window Sharpe CI: analytic, per the pin's own SE rule ------------------------------
fz = LEVELS["FROZEN   2025-03-01..2026-08-10 20Z"]
FROZEN_CI = {"sharpe": fz["sharpe_ann"], "SE": fz["SE_sharpe"],
             "CI95_analytic": [fz["sharpe_ann"]-1.96*fz["SE_sharpe"], fz["sharpe_ann"]+1.96*fz["SE_sharpe"]],
             "note": "the [1.306,4.565] in CLOSEOUT is this analytic interval on the FITTED-cost Sharpe 2.9357, NOT a bootstrap and NOT on the pin's 3.04"}

# ---- cost book arithmetic ----------------------------------------------------------------------
cb = json.load(open(COSTB)); f3 = json.load(open(FITK3)); f2 = json.load(open(FITK2))
COST = {"book_avg_in_file": cb["book_avg_bps_per_unit_turnover"],
        "blend_recomputed": float(sum(b*s for b, s in zip(cb["blended_bps_per_unit_turnover"], cb["turnover_share_by_tier"]))),
        "turnover_shares_sum": float(sum(cb["turnover_share_by_tier"])),
        "file_has_a_K_or_exponent_PARAMETER_field": any(k in cb for k in ("K","K_excess","alpha","exponent","impact_exponent")),
        "file_top_level_keys": sorted(cb.keys()),
        "FITK_v3_POWER_K_excess": f3["POWER"]["K_excess"],
        "FITK_v3_POWER_K_excess_CI95": f3["POWER"]["K_excess_CI95"],
        "FITK_v3_per_tier_excess": {k: v["excess"] for k, v in f3["POWER"]["per_tier"].items()},
        "pinned_impact_bps_by_tier": cb["impact_bps_by_tier"],
        "per_tier_equals_pinned": [abs(f3["POWER"]["per_tier"][k]["excess"] - cb["impact_bps_by_tier"][i]) < 1e-12
                                   for i, k in enumerate(("tier0", "tier1", "tier2"))],
        "FITK_v3_implied_exponent_1_over_p": f3["implied_impact_exponent_alpha_1_over_p"],
        "FITK_v2_pooled_alpha_FINE2026": f2["FINE2026_G230k"]["powerlaw_vwap_vs_participation"]["pooled"]["alpha"],
        "FITK_v2_within_tier_alphas_FINE2026": [f2["FINE2026_G230k"]["powerlaw_vwap_vs_participation"][t]["alpha"]
                                                for t in ("tier0", "tier1", "tier2")],
        "effective_rate_paid_on_W_ALPHA_bps_per_unit_matched_turnover":
            LEVELS["W_ALPHA  post-warm & <=2026-08-30 20Z"]["effective_cost_bps_per_unit_MATCHED_turnover"],
        "effective_over_book_avg": LEVELS["W_ALPHA  post-warm & <=2026-08-30 20Z"]["effective_cost_bps_per_unit_MATCHED_turnover"]/cb["book_avg_bps_per_unit_turnover"]}

# ---- NAV arithmetic for every circulating planning pair ----------------------------------------
def nav(gv, L=2.0): return gv*2190*L/1e4*100
NAV = {"A0_W_ALPHA_0.6342": nav(0.6342), "A1x_9199_0.6602": nav(0.6602),
       "CI_B2000_lo_0.1774": nav(0.1774), "CI_B2000_hi_1.1136": nav(1.1136),
       "CI_B4000_lo_0.1653": nav(0.1653), "CI_B4000_hi_1.1071": nav(1.1071),
       "note": "bps/anchor * 2190 anchors/yr * L / 1e4 * 100 = % of NAV per year"}

REC = {"doc": "CALIBER AUDIT judgement device, handoff 2026-09-12",
       "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "env_whitelist": [], "gpu_used": False, "network_used": False, "live_tree_touched": False,
       "self_sha256": sha256(__file__), "inputs_sha256": INPUTS,
       "arm_config": {k: CFG[k] for k in ("CAL","LEGS","PHI","WRULE","LOOK","MEMBERS_TOPN","FTRIM",
                                          "UMASK_SCOPE","W3FIX","FPRED","SLOW_NPY","COSTB_JSON")},
       "statistic": "g = net_ex/gross_total, bps per 4h anchor per unit gross; Sharpe = mean/sd(ddof=1)*sqrt(2190)",
       "LEVELS": LEVELS, "IDENTITY": IDENTITY, "TURNOVER_TWO_SERIES": TURN2,
       "TAIL_LADDER": LADDER, "FROZEN_SHARPE_CI": FROZEN_CI, "COST_MODEL": COST, "NAV_ARITHMETIC": NAV}
json.dump(REC, open(OUT, "w"), indent=1)
print(json.dumps({"LEVELS": {k: {kk: v[kk] for kk in ("n","mean_g_bps","sharpe_ann","turnover_RAW_file_column",
      "turnover_MATCHED_mean_of_ratios","ratio_matched_over_raw")} for k, v in LEVELS.items()},
      "IDENTITY": IDENTITY, "FROZEN_SHARPE_CI": FROZEN_CI,
      "COST": {k: COST[k] for k in ("book_avg_in_file","blend_recomputed","file_has_a_K_or_exponent_PARAMETER_field","file_top_level_keys",
      "per_tier_equals_pinned","effective_rate_paid_on_W_ALPHA_bps_per_unit_matched_turnover","effective_over_book_avg")},
      "TURNOVER_TWO_SERIES": TURN2}, indent=1))
print("wrote", OUT)
