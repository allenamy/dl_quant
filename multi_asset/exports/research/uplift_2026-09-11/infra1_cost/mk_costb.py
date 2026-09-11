#!/usr/bin/env python3
"""INFRA-1 step 5: emit the honest COSTB JSONs in the device schema.

MODEL (per device tier t, charge per unit of |trade| notional, bps):
  maker_bps_t = fee_maker_t                   + K * I_t
  taker_bps_t = fee_taker_t + S_t/2           + K * I_t
  maker_share_t = measured maker share of filled notional, protective_flatten EXCLUDED
  device blends them as  fr*maker + (1-fr)*taker.
  fee_*      MEASURED, live fills 2026-08-01..09-11, 33,886 deduped fills (BNB fees at anchor BNBUSDT mid)
  S_t        MEASURED, intent-weighted mean of orders.jsonl spread_at_submit_bps
             (= (ask-bid)/mid*1e4, binance_executor.py:505). Half of it = the cost of crossing vs mid.
  I_t        square-root impact, I = K * sigma_4h * sqrt(|trade|*G / qv4h), evaluated on the A0 replay's
             OWN per-name trades at G = $230,000 (the deployed 2026-09-11 gross) and turnover-weighted
             inside each tier. NOT measurable from live fills at this size -- DECLARED EXTRAPOLATION.
             K=1 is the Almgren/Kyle central case; K=0 removes impact entirely.
"""
import json, numpy as np
BASE="/workspace/uplift_2026-09-11/infra1_cost"
S=json.load(open(f"{BASE}/tier_stats.json"))["all"]
RP=json.load(open(f"{BASE}/replay_participation.json"))
fee_mk=[d["mk_fee_bps"] for d in S]; fee_tk=[d["tk_fee_bps"] for d in S]
spread=[d["spread_bps"] for d in S]
mshare=[d["mk_nz"]/(d["mk_nz"]+d["tk_nz"]) for d in S]
imp=[RP[str(t)]["impact_K1_bps"] for t in range(3)]
tsh=[RP[str(t)]["turnover_share"] for t in range(3)]
print("MEASURED tier inputs (live fills 2026-08-01..09-11):")
for t in range(3):
    print("  tier%d fee_mk %.4f fee_tk %.4f spread %.4f half %.4f maker_share %.4f impact(K=1) %.4f turn_share %.4f"%(
        t,fee_mk[t],fee_tk[t],spread[t],spread[t]/2,mshare[t],imp[t],tsh[t]))
def mk(K,path,name):
    tiers=[];bl=[]
    for t in range(3):
        m=fee_mk[t]+K*imp[t]; k=fee_tk[t]+spread[t]/2.0+K*imp[t]; f=mshare[t]
        tiers.append({"name":["tier0_qv4h>=5e6","tier1_qv4h>=1e6","tier2_rest"][t],
                      "maker_bps":round(m,6),"taker_bps":round(k,6),"maker_share":round(f,6)})
        bl.append(f*m+(1-f)*k)
    avg=sum(b*s for b,s in zip(bl,tsh))
    doc=dict(tiers=tiers, model=name, impact_multiple_K=K,
             blended_bps_per_unit_turnover=[round(b,4) for b in bl],
             book_avg_bps_per_unit_turnover=round(avg,4),
             turnover_share_by_tier=[round(s,4) for s in tsh],
             calibration=dict(
               fills_source="/Users/haosiyu/dl_quant_live/state/live/pilot_log/*/fills.jsonl + orders.jsonl, READ-ONLY",
               fills_raw_rows=81161, fills_deduped=33886, dedupe_key="(symbol,trade_id)",
               sample_window_utc=["2026-08-01T04Z","2026-09-11T04Z"], n_live_anchors=243,
               qv4h_join="panel wide_panel_4h_v2ext / meta_newprod_v4 qvk -> expm1(clip(qvk,0,30))*48; "
                         "anchors after 2026-08-31 20Z (15367 of 47135 rows) use the symbol's median qv4h "
                         "over the last 42 panel rows = DECLARED EXTRAPOLATION",
               maker_share_excludes="order_type=protective_flatten (14-17% of filled notional; stop-loss / "
                                    "watchdog events on 2026-09-06 and 2026-09-09, not steady-state rebalancing)",
               fee_note="measured 1.90/4.76 bps vs the deployed model's 1.80/4.50: the deployed value assumes "
                        "100% BNB-discounted fees; realised BNB coverage is ~48% of fill notional",
               impact_form="I_bps = K * sigma_4h_bps * sqrt(|trade|*G/qv4h), sigma_4h from meta y4 per name, "
                           "G=230000 USDT (live NAV 114,949 x constant_leverage_2.00, daily_nav.jsonl 2026-09-11)",
               impact_extrapolation="participation in the replay is 9.8e-6 (tier0) to 4.9e-4 (tier2); at that size "
                                    "impact is BELOW the noise floor of the live fills, so K is NOT fitted. "
                                    "Tier constants are a LINEARISATION valid at G=$230k; impact scales as sqrt(G), "
                                    "so K=2 == 4x gross and K=3 == 9x gross at the same K=1 coefficient.",
               replay_traded_range="the device trades only qv4h>=2.5e5 (log10=5.4); the two least-liquid live "
                                   "deciles (log10 qv4h 4.71-5.40) are OUTSIDE the replay's traded set"))
    json.dump(doc,open(path,"w"),indent=1)
    print("  %-28s blended %s  book-avg %.4f"%(name,[round(b,3) for b in bl],avg))
    return avg
print("\nEMITTED:")
for K,tag in ((0.0,"H0"),(0.5,"H05"),(1.0,"H1"),(1.5,"H15"),(2.0,"H2"),(3.0,"H3"),(4.0,"H4"),(6.0,"H6")):
    mk(K,f"{BASE}/costb_honest_{tag}.json","honest_fee+spread+impactK%g"%K)
# deployed reference blend
D=json.load(open("/workspace/review_scratch/health_check/calib/costb_fee_steady.json"))["tiers"]
bl=[t["maker_share"]*t["maker_bps"]+(1-t["maker_share"])*t["taker_bps"] for t in D]
print("\nDEPLOYED costb_fee_steady blended %s  book-avg %.4f"%([round(b,4) for b in bl],sum(b*s for b,s in zip(bl,tsh))))
