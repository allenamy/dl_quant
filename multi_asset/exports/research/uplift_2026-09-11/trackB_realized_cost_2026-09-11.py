#!/usr/bin/env python3
"""TRACK B step 1+2: true realized cost per anchor from the live ledgers. READ-ONLY on /Users/haosiyu/dl_quant_live.
SIGN CONVENTION (stated explicitly, and used everywhere below):
  a POSITIVE number is a COST to the book (money leaving), a NEGATIVE number is a CREDIT.
  commission in fills.jsonl is venue-reported and POSITIVE when paid -> reported as +.
  markout   = side_sign * (mid_at_fill_plus_60s - fill_px) / fill_px .  POSITIVE markout = the price moved OUR WAY
              after the fill = we were ADVERSELY selected against the counterparty's favour = a GAIN to us.
              Adverse selection COST is therefore -markout, reported with the cost sign.
DEDUPE: key = (symbol, trade_id); when the same key appears twice keep the row that carries mid_at_fill_plus_60s
        (the backfilled row supersedes). Duplicate count is reported.
"""
import json, os, sys
from collections import defaultdict
import numpy as np

LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
COMBO_START = 1787716800.0   # 2026-08-26T04:00:00Z
days = sorted(d for d in os.listdir(LOG) if d.isdigit())

# ---------- anchors: mids + gross ----------
anch = {}
for d in days:
    p = f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str): mid = json.loads(mid)
        anch[ts] = dict(day=d, realized_gross=r.get("realized_gross"), target_gross=r.get("target_gross"),
                        mid=mid or {}, regime=r.get("regime_at_anchor"))
ats = sorted(anch)

# gross from the venue position readback (the BOOK layer, not the target layer)
pbg = defaultdict(float); pbn = defaultdict(int)
prev_pos = {}; pos_by_anchor = {}
for d in days:
    p = f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r["anchor_ts"]
        v = float(r.get("venue_position_notional") or 0.0)
        pbg[ts] += abs(v); pbn[ts] += 1
        pos_by_anchor.setdefault(ts, {})[r["symbol"]] = v

def bnb_mid(ts):
    c = [t for t in ats if anch[t]["mid"].get("BNBUSDT")]
    if not c: return None
    t = min(c, key=lambda t: abs(t - ts)); return anch[t]["mid"]["BNBUSDT"]
BNB = {t: bnb_mid(t) for t in ats}

# ---------- fills: dedupe ----------
raw_n = 0; F = {}
dupe_same = 0; dupe_diff = 0
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); raw_n += 1
        k = (r["symbol"], r["trade_id"])
        cur = F.get(k)
        if cur is None:
            F[k] = r; continue
        same = (cur.get("fill_notional") == r.get("fill_notional") and cur.get("commission") == r.get("commission")
                and cur.get("fill_px") == r.get("fill_px"))
        dupe_same += same; dupe_diff += (not same)
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None:
            F[k] = r
fills = list(F.values())
print(f"fills.jsonl rows {raw_n} -> deduped {len(fills)}  (dropped {raw_n-len(fills)}; "
      f"identical-payload dupes {dupe_same}, payload-differing dupes {dupe_diff})")

# ---------- per-anchor aggregation ----------
A = defaultdict(lambda: dict(fee=0.0, fee_bnb_usdt=0.0, notional=0.0, mk_notional=0.0, tk_notional=0.0,
                             mk_fee=0.0, tk_fee=0.0, mo_wn=0.0, mo_w=0.0, n=0, n_mo=0))
for r in fills:
    ts = r.get("anchor_ts")
    if ts is None: continue
    a = A[ts]
    c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
    cu = c * (BNB.get(ts) or 1.0) if ca == "BNB" else c
    if ca == "BNB": a["fee_bnb_usdt"] += cu
    nz = abs(float(r.get("fill_notional") or 0.0))
    mk = bool(r.get("venue_maker_flag")) if r.get("venue_maker_flag") is not None else (r.get("order_type") == "maker")
    a["fee"] += cu; a["notional"] += nz; a["n"] += 1
    if mk: a["mk_notional"] += nz; a["mk_fee"] += cu
    else:  a["tk_notional"] += nz; a["tk_fee"] += cu
    m60 = r.get("mid_at_fill_plus_60s"); px = float(r.get("fill_px") or 0.0)
    if m60 is not None and px > 0:
        sgn = 1.0 if r.get("side") == "buy" else -1.0
        mo = sgn * (float(m60) - px) / px          # +ve = price moved our way after the fill
        a["mo_wn"] += mo * nz; a["mo_w"] += nz; a["n_mo"] += 1

# ---------- orders: churn ----------
O = defaultdict(lambda: dict(intended=0.0, filled=0.0, n_orders=0, n_attempts=0, n_cancel=0,
                             skipped=0.0, n_lines=0, by_reason=defaultdict(float), max_attempt=0))
for d in days:
    p = f"{LOG}/{d}/orders.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        o = O[ts]; o["n_lines"] += 1
        ai = int(r.get("attempt_idx") or 1); o["max_attempt"] = max(o["max_attempt"], ai)
        ints = abs(float(r.get("intended_notional") or 0.0))
        fl = abs(float(r.get("filled_notional") or 0.0))
        o["intended"] += ints; o["filled"] += fl
        tr = r.get("terminal_reason") or "?"
        o["by_reason"][tr] += ints
        if tr == "skipped_min_notional": o["skipped"] += ints
        if r.get("submit_ts") is not None: o["n_orders"] += 1
        if r.get("cancel_ts") is not None: o["n_cancel"] += 1
        o["n_attempts"] += 1

# ---------- rows ----------
rows = []
for ts in sorted(set(list(A) + list(O))):
    G = pbg.get(ts, 0.0)
    if G <= 0: G = anch.get(ts, {}).get("target_gross") or 0.0
    a = A.get(ts, {}); o = O.get(ts, {})
    if G <= 0: continue
    fee = a.get("fee", 0.0); nz = a.get("notional", 0.0)
    mo = (a["mo_wn"] / a["mo_w"]) if a.get("mo_w", 0) > 0 else float("nan")
    adv_cost_usdt = -(a.get("mo_wn", 0.0))       # cost sign: -sum(markout * notional)
    rows.append(dict(ts=ts, day=anch.get(ts, {}).get("day"), gross=G,
                     fee_usdt=fee, traded_notional=nz,
                     mk_share=(a.get("mk_notional", 0.0) / nz if nz > 0 else float("nan")),
                     fee_bps_of_traded=(fee / nz * 1e4 if nz > 0 else float("nan")),
                     mk_fee_bps=(a.get("mk_fee", 0.0) / a["mk_notional"] * 1e4 if a.get("mk_notional", 0) > 0 else float("nan")),
                     tk_fee_bps=(a.get("tk_fee", 0.0) / a["tk_notional"] * 1e4 if a.get("tk_notional", 0) > 0 else float("nan")),
                     markout60_bps=mo * 1e4 if mo == mo else float("nan"),
                     adv_cost_usdt=adv_cost_usdt, mo_cov=(a.get("mo_w", 0.0) / nz if nz > 0 else float("nan")),
                     intended=o.get("intended", 0.0), filled=o.get("filled", 0.0),
                     skipped=o.get("skipped", 0.0), n_lines=o.get("n_lines", 0),
                     n_orders=o.get("n_orders", 0), n_cancel=o.get("n_cancel", 0), max_attempt=o.get("max_attempt", 0),
                     n_fills=a.get("n", 0)))
json.dump(rows, open(f"{OUT}/trackB_realized_cost_rows.json", "w"), indent=1)

def summarise(label, sel):
    R = [r for r in rows if sel(r)]
    if not R: print(f"{label}: no rows"); return
    G = np.array([r["gross"] for r in R]); n = len(R)
    def bps(key):  # gross-weighted: sum(usdt)/sum(gross) in bps  (the correct per-anchor-per-gross caliber)
        v = np.array([r[key] for r in R], float)
        return np.nansum(v) / G.sum() * 1e4
    tn = np.array([r["traded_notional"] for r in R], float)
    it = np.array([r["intended"] for r in R], float)
    fl = np.array([r["filled"] for r in R], float)
    sk = np.array([r["skipped"] for r in R], float)
    mkse = np.array([r["mk_share"] for r in R], float)
    print(f"\n===== {label}  (n={n} anchors, mean gross {G.mean():,.0f} USDT) =====")
    print(f"  traded notional / gross        : {(tn.sum()/G.sum())*100:7.3f} %  per anchor")
    print(f"  ORDER intended / gross         : {(it.sum()/G.sum())*100:7.3f} %  per anchor")
    print(f"  ORDER filled  / gross          : {(fl.sum()/G.sum())*100:7.3f} %  per anchor")
    print(f"  skipped_min_notional / gross   : {(sk.sum()/G.sum())*100:7.3f} %  per anchor")
    print(f"  maker share of traded notional : {np.nansum([r['mk_notional_'] if False else 0 for r in R])*0 + np.nanmean(mkse)*100:7.2f} %")
    print(f"  -- COST, bps of gross per anchor (POSITIVE = cost to the book) --")
    print(f"  exchange fees                  : {bps('fee_usdt'):+8.4f}")
    print(f"  adverse selection (-markout60) : {bps('adv_cost_usdt'):+8.4f}   [coverage {np.nanmean([r['mo_cov'] for r in R])*100:.1f}% of traded notional]")
    print(f"  fees + adverse selection       : {bps('fee_usdt')+bps('adv_cost_usdt'):+8.4f}")
    print(f"  -- unit costs --")
    fe = np.array([r["fee_usdt"] for r in R]).sum(); 
    print(f"  fee per unit traded notional   : {fe/tn.sum()*1e4:7.4f} bps    (maker {np.nansum([r['mk_fee_bps']*0 for r in R])*0 + np.nanmean([r['mk_fee_bps'] for r in R]):.4f} / taker {np.nanmean([r['tk_fee_bps'] for r in R]):.4f} bps)")
    mo_num = np.nansum([-r["adv_cost_usdt"] for r in R]); mo_den = np.nansum([r["mo_cov"]*r["traded_notional"] for r in R])
    print(f"  markout60 per unit traded      : {mo_num/mo_den*1e4:+7.4f} bps  (+ = price moved our way = a GAIN)")
    print(f"  all-in cost per unit traded    : {(fe - mo_num)/tn.sum()*1e4:+7.4f} bps")
    fill_r = fl.sum()/it.sum() if it.sum()>0 else float('nan')
    print(f"  fill ratio (filled/intended)   : {fill_r*100:6.2f} %   cancels/anchor {np.mean([r['n_cancel'] for r in R]):.0f}  order lines/anchor {np.mean([r['n_lines'] for r in R]):.0f}  max attempt_idx {max(r['max_attempt'] for r in R)}")

summarise("ALL 2026-08-01 -> 09-11", lambda r: True)
summarise("COMBO ERA 2026-08-26T04Z ->", lambda r: r["ts"] >= COMBO_START)
summarise("PRE-COMBO", lambda r: r["ts"] < COMBO_START)
print(f"\nwrote {OUT}/trackB_realized_cost_rows.json")
