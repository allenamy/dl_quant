#!/usr/bin/env python3
"""r11_frequency_tests.py -- the three frequency ladders (what the desk was TOLD / what the
CORRECTED replay says / what LIVE has actually done) and the significance tests that separate
a count anomaly from a volatility anomaly. READ-ONLY. Env whitelist = EMPTY SET (E-0826-D)."""
import os, json, time, hashlib
import numpy as np
from math import comb
from scipy.stats import f as fdist, chi2
ENV_WHITELIST = []
_W=["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","COSTB_JSON","SLOW_NPY","UMASK_NPZ",
    "UMASK_SCOPE","JUDGE_HC","PANEL_IN","OMP_NUM_THREADS","PYTHONHASHSEED"]
_s={k:os.environ[k] for k in _W if k in os.environ}; assert _s=={}, _s
ROOT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()
WD=os.path.expanduser("~/dl_quant_live/live/watchdog.py")

A=json.load(open(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_tail_2026-09-12.json"))
B=json.load(open(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_live_vs_replay_vol_2026-09-12.json"))
P=A["part1_tail_on_corrected_caliber"]["PINNED"]; NW=A["part1_companion_NOWARM"]["at_2.00x"]
NDP=P["n_days"]; NDN=NW["n_days"]

# --- what the desk was TOLD, quoted verbatim from the live watchdog (read-only) ----------------
TOLD={"source":"~/dl_quant_live/live/watchdog.py L100-122 (READ-ONLY)","sha256":sha256(WD),
      "series":"1,641-day historical series 2022-01..2026-06, 'canonical engine'",
      "daily_sd_pct_at_2x":1.2427,"n_days":1641,
      "breaches":{"le_4.00":3,"le_2.68":8,"le_2.00":17},
      "per_yr":{k:round(v/1641*365,4) for k,v in {"le_4.00":3,"le_2.68":8,"le_2.00":17}.items()},
      "quoted":"'this fires 3 times in 4.5 years' / '8 times in 4.5 years ~ 1.8/yr' / "
               "'the real frequency can only be HIGHER than 1.8/yr, never lower'"}
LIVE=B["live"]; NJ=LIVE["n_days_2x_equiv"]
OBS={"le_4.00":len(LIVE["breaches"]["le_4.00"]),"le_2.68":len(LIVE["breaches"]["le_2.68"]),
     "le_2.00":len(LIVE["breaches"]["le_2.00"])}

def pge(k,n,p): return float(1.0 - sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k)))
LAD={}
for key,tag in [("le_4.00","4.00"),("le_2.68","2.68"),("le_2.00","2.00")]:
    p_rep=P[f"days_le_{tag}pct"]["close_to_close_n"]/NDP
    p_nw =NW[f"days_le_{tag}pct"]["close_to_close_n"]/NDN
    p_told=TOLD["breaches"][key]/TOLD["n_days"]
    LAD[key]={
      "desk_was_told_per_yr":TOLD["per_yr"][key],
      "corrected_replay_postwarm_per_yr":round(p_rep*365,4),
      "corrected_replay_nowarm_per_yr":round(p_nw*365,4),
      "live_realised_per_yr":round(OBS[key]/NJ*365,4),
      "live_observed_k":OBS[key],"live_n_judgeable_days":NJ,
      "ratio_corrected_over_told":round(p_rep/p_told,3) if p_told>0 else None,
      "binom_P_Xge_k_under_corrected_replay":round(pge(OBS[key],NJ,p_rep),4),
      "binom_P_Xge_k_under_desk_told":round(pge(OBS[key],NJ,p_told),4)}

# --- the volatility test: is LIVE daily vol above the corrected replay's? ----------------------
sl=LIVE["daily_sd_pct_2x_equivalent"]; sr=B["replay_primary_window_at_2x"]["daily_sd_pct"]
F=(sl/sr)**2; d1=NJ-1; d2=NDP-1
VOL={"live_daily_sd_pct_2x_equiv":sl,"n_live":NJ,
     "corrected_replay_daily_sd_pct_at_2x":sr,"n_replay_days":NDP,
     "F":float(F),"dof":[d1,d2],"p_one_sided_live_greater":float(fdist.sf(F,d1,d2)),
     "live_sd_CI95":[float(sl*np.sqrt(d1/chi2.ppf(0.975,d1))),float(sl*np.sqrt(d1/chi2.ppf(0.025,d1)))],
     "reading":"a count of 1 breach in 34 days is NOT significant against any base rate; the "
               "volatility ratio is. The anomaly the desk is feeling is a SCALE anomaly."}
# same test on the per-anchor caliber (n is 7x larger, so it has real power)
al=LIVE["anchor_sd_pct_2x_equivalent"]; ar=B["replay_primary_window_at_2x"]["anchor_sd_pct"]
n_a=LIVE["n_anchors_2x_equiv"]
VOL["per_anchor"]={"live_sd_pct":al,"replay_sd_pct":ar,"n_live_anchors":n_a,
    "F":float((al/ar)**2),"dof":[n_a-1,9137],
    "p_one_sided_live_greater":float(fdist.sf((al/ar)**2,n_a-1,9137))}

# --- realised rolling-1y drawdown exceedance on the corrected caliber --------------------------
RD={"postwarm_rolling_1y_maxDD":A["part1_tail_on_corrected_caliber"]["PINNED"]["rolling_1y_maxDD_pct"],
    "nowarm_rolling_1y_maxDD":NW["rolling_1y_maxDD_pct"],
    "bootstrap_P_1y_maxDD_ge25_at_2x_postwarm":A["part2_leverage_ladder"]["PINNED"]["2.00x"]["bootstrap_1y"]["P_maxDD_ge_25pct"],
    "bootstrap_P_1y_maxDD_ge25_at_2x_nowarm":A["part1_companion_NOWARM"]["at_2.00x_bootstrap_1y"]["P_maxDD_ge_25pct"],
    "bootstrap_P_from_start_le_m25_at_2x_postwarm":A["part2_leverage_ladder"]["PINNED"]["2.00x"]["bootstrap_1y"]["P_from_start_le_minus25pct"],
    "live_rule_caliber":"watchdog.py L131 DRAWDOWN_LIMIT_PCT = -25.0, % of STARTING equity, "
                        "explicitly NOT peak-relative; both calibers reported"}

OUT={"env_whitelist":ENV_WHITELIST,"gpu_used":False,"live_written":False,"network_used":False,
     "device_self_sha256":sha256(os.path.abspath(__file__)),
     "inputs":{"RECEIPT_r11_tail":sha256(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_tail_2026-09-12.json"),
               "RECEIPT_r11_live_vs_replay_vol":sha256(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_live_vs_replay_vol_2026-09-12.json"),
               "live_watchdog.py":TOLD["sha256"]},
     "what_the_desk_was_told":TOLD,"three_ladders":LAD,"volatility_test":VOL,"drawdown_25":RD}
json.dump(OUT,open(f"{ROOT}/r11_tail/receipts/RECEIPT_r11_frequency_tests_2026-09-12.json","w"),indent=1)
print(json.dumps(OUT,indent=1))
