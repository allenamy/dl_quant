"""Handoff audit, block r10-r11: every first-hand recomputation in AUDIT_NOTES_r10_r11_2026-09-12.md.
READ-ONLY. Touches ~/dl_quant_live only with open()/read.
ENV WHITELIST (E-0826-D) = EMPTY SET -- asserted below.
Exact re-run:
    env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 audit_recompute_r10_r11.py
"""
import os, sys, json, hashlib, calendar, time, re
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN","PANEL",
           "PANEL_IN","EXPORT_PANEL","EMA_STATE_JSON","JUDGE_HC","JUDGE_REQUIRE_W","SLEEVE")
assert not [k for k in _FORBID if k in os.environ], "E-0826-D env violation"
import numpy as np

B   = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""): h.update(c)
    return h.hexdigest()
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
OUT = {"self_sha256": sha(os.path.abspath(__file__)), "env_whitelist": [],
       "env_seen_at_runtime": sorted(os.environ), "numpy": np.__version__,
       "python": sys.version.split()[0]}

# ---- 1. SHA256SUMS verification -------------------------------------------------
dirs = ["r10_combine","r11_costtruth","r11_tail","r11_verdict","klass_independent_objective_2026-09-12",
        "r10_screen/TSMOM_DIR","r10_screen/VRP_DELTA1","r10_screen/CMUM_CARRY",
        "r10_screen/COINT_PAIR","r10_screen/SLOW_CLOCK"]
s = {"ok":0,"mismatch":[],"missing":[],"no_manifest":[]}
for d in dirs:
    f = os.path.join(B,d,"SHA256SUMS.txt")
    if not os.path.exists(f): s["no_manifest"].append(d); continue
    for ln in open(f):
        m = re.match(r'^([0-9a-f]{64})\s+\.?/?(.*)$', ln.strip())
        if not m: continue
        p = os.path.join(B,d,m.group(2))
        if not os.path.exists(p): s["missing"].append(f"{d}/{m.group(2)}"); continue
        if sha(p) == m.group(1): s["ok"] += 1
        else: s["mismatch"].append({"file":f"{d}/{m.group(2)}","stated":m.group(1),"actual":sha(p)})
OUT["sha_manifest_check"] = s

# ---- 2. independence matrix, recomputed from the series -------------------------
z = np.load(B+"/r10_combine/series/books_on_pinned_axis.npz", allow_pickle=True)
ts = z["ts"]; names = [str(x) for x in z["names"]]; G = z["G"]; TU = z["TU"]
P = ["A0","TSMOM","VRP","CMUM","SLOW","COINT","REVS"]; ixp = [names.index(k) for k in P]
M = np.corrcoef(G[:,ixp].T)
rec = json.load(open(B+"/r10_combine/receipts/S3_COMBINE_FINAL.json"))
OUT["independence"] = {
  "n": int(len(ts)), "monotone_4h": bool(np.all(np.diff(ts)==14400)),
  "span": [time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(ts[0]))),
           time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(int(ts[-1])))],
  "A0_row": {k: round(float(M[0,j]),6) for j,k in enumerate(P)},
  "maxabs_diff_vs_receipt": float(np.max(np.abs(np.round(M,4)-np.array(rec["corr_pearson"]["M"])))),
  "max_offdiag_abs_among_candidates": float(np.max(np.abs(M[1:,1:] - np.eye(6)))),
  "zero_padded": {k: int((G[:,names.index(k)]==0).sum()) for k in P},
  "rho_on_covered_only": {k: round(float(np.corrcoef(G[:,0][G[:,names.index(k)]!=0],
        G[:,names.index(k)][G[:,names.index(k)]!=0])[0,1]),6) for k in ["CMUM","COINT"]},
}

# ---- 3. allocation asymmetry counter-examples ------------------------------------
ce = []
for pool,v in rec["allocations"].items():
    if pool=="A0_alone": continue
    for a,o in v.items():
        d = o["vs_A0_alone"]
        if d["d_maxDD_bps"] > 0: ce.append(["maxDD_WORSENS",pool,a,d["d_maxDD_bps"]])
        if d["d_worst_UTC_day_bps"] > 0: ce.append(["WORSTDAY_IMPROVES",pool,a,d["d_worst_UTC_day_bps"]])
OUT["allocation_asymmetry_counterexamples"] = ce
OUT["allocation_n_nontrivial"] = sum(len(v) for p,v in rec["allocations"].items() if p!="A0_alone")

# ---- 4. TSMOM regime, incl. the mislabelled frozen window -------------------------
Z = np.load(B+"/r10_screen/TSMOM_DIR/receipts/primary_series.npz")
tts = Z["ts"].astype(np.int64); gT = Z["gT"]; gA0 = Z["gA0"]
def cond(msk):
    t_=gT[msk]; a_=gA0[msk]; lo=a_<=np.quantile(a_,0.20)
    return {"n":int(msk.sum()),"rho":round(float(np.corrcoef(t_,a_)[0,1]),6),
            "rho_bq":round(float(np.corrcoef(t_[lo],a_[lo])[0,1]),6),
            "TSMOM_mean_bq":round(float(t_[lo].mean()),6),"A0_mean_bq":round(float(a_[lo].mean()),4)}
YR = np.array([time.gmtime(int(t)).tm_year for t in tts])
OUT["tsmom"] = {
  "A0_in_this_series": {"mean_g": round(float(gA0.mean()),4),
      "sharpe": round(float(gA0.mean()/gA0.std(ddof=1)*np.sqrt(2190)),4),
      "reading": "0.6872/1.3991 = fee_steady cost arm, NOT the PWR arm (0.6342/1.2912)"},
  "FULL_postwarm": cond(np.ones(len(tts),bool)),
  "AS_CODED_frozen_label_upper_1786737600": cond((tts>=1740787200)&(tts<=1786737600)),
  "TRUE_frozen_upper_2026-08-10T20Z_1786392000": cond((tts>=1740787200)&(tts<=T(2026,8,10,20))),
  "Y2026": cond(YR>=2026),
  "FINDING": "r10_tsmom4.py L22 labels the mask FROZEN..2026-08-10 but its upper bound 1786737600 is 2026-08-14 20Z; 24 anchors / 4 days past the pinned frozen window.",
}

# ---- 5. A0 calibers, turnover trap, accounting identity ---------------------------
A0P = B+"/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
a = np.load(A0P, allow_pickle=True); cols=[str(c) for c in a["cols"]]; ci={c:i for i,c in enumerate(cols)}
r = np.asarray(a["rec"],float); ats = np.round(r[:,ci["ts"]]).astype(np.int64)
CUT = T(2026,8,30,20)
def win(warm):
    s_ = np.arange(len(ats))[warm:]; return s_[ats[s_]<=CUT]
sel = win(900); R = r[sel]; gt = R[:,ci["gross_total"]]
OUT["A0_calibers"] = {"sha256_A0_npz": sha(A0P), "n": int(len(sel)),
  "mean_gross_total": round(float(gt.mean()),7),
  "per_gross": {c: round(float((R[:,ci[c]]/gt).mean()),7)
                for c in ["net_ex","pnl_ex","carry_ex","cost_ex","turnover","pnl","carry","cost","net"]},
  "turnover_raw": round(float(R[:,ci["turnover"]].mean()),7),
  "REVS_turnover_ratio_matched_caliber": round(1.3178/float((R[:,ci["turnover"]]/gt).mean()),4),
  "REVS_turnover_ratio_mixed_caliber": round(1.3178/float(R[:,ci["turnover"]].mean()),4),
  "identity_residual_net_ex_minus_pnl_ex_plus_carry_ex_minus_cost_ex": {
      "mean": round(float((R[:,ci["net_ex"]]-(R[:,ci["pnl_ex"]]+R[:,ci["carry_ex"]]-R[:,ci["cost_ex"]])).mean()),6),
      "frac_rows_zero": float((np.abs(R[:,ci["net_ex"]]-(R[:,ci["pnl_ex"]]+R[:,ci["carry_ex"]]-R[:,ci["cost_ex"]]))<1e-9).mean())},
  "REVS_gross_1.1585_as_pct_of": {"A0_pnl_ex_per_gross": round(100*1.1585/float((R[:,ci["pnl_ex"]]/gt).mean()),2),
                                  "A0_pnl_per_gross": round(100*1.1585/float((R[:,ci["pnl"]]/gt).mean()),2)},
}

# ---- 6. breach dates, both windows ------------------------------------------------
def breaches(warm):
    s_ = win(warm); TS = ats[s_]
    eq = (r[s_,ci["net_ex"]]/r[s_,ci["gross_total"]])/1e4 * 2.0
    day = TS//86400; ud,inv = np.unique(day, return_inverse=True)
    dd = np.array([np.prod(1.0+eq[inv==k])-1.0 for k in range(len(ud))])*100
    bad = np.where(dd<=-4.0)[0]
    return {"n_days": int(len(ud)), "daily_sd_pct": round(float(dd.std(ddof=1)),4),
            "breaches_le_4pct": [[time.strftime("%Y-%m-%d",time.gmtime(int(ud[i])*86400)), round(float(dd[i]),4)] for i in bad],
            "worst_day": [time.strftime("%Y-%m-%d",time.gmtime(int(ud[int(np.argmin(dd))])*86400)), round(float(dd.min()),4)]}
OUT["watchdog_recalibration"] = {
  "watchdog_py_sha256": sha("/Users/haosiyu/dl_quant_live/live/watchdog.py"),
  "watchdog_comment_claim": "fires 3 times in 4.5 years, ALL THREE in 2024 (2024-02-28, 2024-03-08, 2024-11-13)",
  "W_ALPHA_postwarm": breaches(900), "W_TAIL_nowarm": breaches(0),
  "FINDING": "zero breaches in 2024 on the corrected v4/PWR caliber, on either window",
}

# ---- 7. live ledger: BNB flip, fee tier, coverage ---------------------------------
days = sorted(d for d in os.listdir(LOG) if d.isdigit())
per_day = {}; cell = {}; tot = 0.0; bnb = 0.0; nf = 0
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    F = {}
    for ln in open(p):
        q = json.loads(ln); k = (q["symbol"], q["trade_id"])
        cur = F.get(k)
        if cur is None: F[k] = q
        elif q.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None: F[k] = q
    ca = {}; nz = 0.0
    for q in F.values():
        A = q.get("commission_asset") or "USDT"; ca[A] = ca.get(A,0)+1
        n_ = abs(float(q.get("fill_notional") or 0.0)); nz += n_
        mk = q.get("venue_maker_flag"); mk = bool(mk) if mk is not None else (q.get("order_type")=="maker")
        key = ("maker" if mk else "taker")+"|"+A
        c = cell.setdefault(key, [0.0,0.0,0]); c[0]+=n_; c[1]+=float(q.get("commission") or 0.0); c[2]+=1
        if "20260801" <= d <= "20260911":
            tot += n_; nf += 1
            if A=="BNB": bnb += n_
    per_day[d] = {"deduped_rows": len(F), "BNB": ca.get("BNB",0), "USDT": ca.get("USDT",0),
                  "notional": round(nz,1)}
OUT["live_ledger"] = {"source": LOG+"/*/fills.jsonl (READ-ONLY)",
  "dedupe": "key=(symbol,trade_id); the row carrying mid_at_fill_plus_60s supersedes (LAST-WINS on the mark)",
  "per_day": per_day,
  "rates_bps_in_own_asset": {k: {"n":v[2], "notional":round(v[0],1), "rate_bps": round(v[1]/v[0]*1e4,4)}
                             for k,v in sorted(cell.items())},
  "window_0801_0911": {"n_fills": nf, "traded_notional": round(tot,2),
      "BNB_notional_share": round(bnb/tot,4),
      "receipt_says": {"n_fills":34921, "traded_notional":1537656.604180615, "BNB_share":0.3695},
      "why_different": "export_fills_for_markout.py drops rows with no anchor_ts/fill_ts"},
  "config_book_json_sha256": sha("/Users/haosiyu/dl_quant_live/config/book.json"),
  "placement_bandit_sha256": sha("/Users/haosiyu/dl_quant_live/live/placement_bandit.py"),
}

# ---- 8. cost-model parameter provenance -------------------------------------------
cb = json.load(open(B+"/r3k_impact/costb_PWR_G230k.json"))
v3 = json.load(open(B+"/r3k_impact/FITK_v3_shape.json"))
v2 = json.load(open(B+"/r3k_impact/FITK_v2.json"))
OUT["cost_model_provenance"] = {
  "costb_PWR_G230k.json": {"sha256": sha(B+"/r3k_impact/costb_PWR_G230k.json"),
     "has_K": "K" in json.dumps(cb), "has_exponent": "exponent" in json.dumps(cb),
     "book_avg_bps_per_unit_turnover": cb["book_avg_bps_per_unit_turnover"],
     "blended_bps_per_unit_turnover": cb["blended_bps_per_unit_turnover"]},
  "FITK_v3_shape.json": {"sha256": sha(B+"/r3k_impact/FITK_v3_shape.json"),
     "POWER_K_excess": v3["POWER"]["K_excess"], "POWER_K_excess_CI95": v3["POWER"]["K_excess_CI95"],
     "implied_impact_exponent_alpha_1_over_p": v3["implied_impact_exponent_alpha_1_over_p"],
     "p_exponent_turnwtd": v3["p_exponent_turnwtd"]},
  "FITK_v2.json_pooled_alpha": v2["FINE2026_G230k"]["powerlaw_vwap_vs_participation"]["pooled"]["alpha"],
  "FINDING": ("CALIBER_PIN says the pinned model is K=0.17 with impact exponent 0.87. K=0.17 IS the "
              "POWER K_excess in FITK_v3_shape.json. 0.87 is NOT: the v3 POWER shape implies 0.7826. "
              "0.8739 is FITK_v2's pooled power-law of VWAP impact vs participation - a different fit."),
}

D = os.path.dirname(os.path.abspath(__file__))
json.dump(OUT, open(D+"/RECEIPT_audit_recompute_r10_r11.json","w"), indent=1)
print(json.dumps({k:(v if not isinstance(v,dict) else "...") for k,v in OUT.items()}, indent=1)[:800])
print("\nSHA manifest:", OUT["sha_manifest_check"]["ok"], "ok,",
      len(OUT["sha_manifest_check"]["mismatch"]), "mismatch,",
      len(OUT["sha_manifest_check"]["missing"]), "missing;  no manifest:",
      OUT["sha_manifest_check"]["no_manifest"])
print("independence maxabs diff vs receipt:", OUT["independence"]["maxabs_diff_vs_receipt"])
print("asymmetry counter-examples:", len(OUT["allocation_asymmetry_counterexamples"]), "of",
      OUT["allocation_n_nontrivial"], "non-trivial allocations")
print("wrote", D+"/RECEIPT_audit_recompute_r10_r11.json")
