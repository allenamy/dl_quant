#!/usr/bin/env python3
"""INFRA-1 step 1: per-(anchor,symbol) realised execution cost from the LIVE ledgers.
READ-ONLY on /Users/haosiyu/dl_quant_live.

SIGN CONVENTION: positive = COST to the book (money out). Negative = credit.
  fee_usdt        = commission, BNB converted at that anchor's BNBUSDT mid_at_anchor.
  slip_anchor_bps = sgn*(fill_px - mid_at_anchor)/mid_at_anchor*1e4   (the REPLAY-comparable price:
                    the replay marks positions at panel price ~ anchor mid, so this is the cash paid
                    relative to the price the replay assumes it traded at).
  mo_cost_bps     = -sgn*(mid_at_fill_plus_60s - fill_px)/fill_px*1e4 (adverse selection; reported
                    separately, NOT added to the cash line -- the post-fill path is already inside y4).
DEDUPE: key=(symbol,trade_id); keep the row carrying mid_at_fill_plus_60s.
"""
import json, os, sys
from collections import defaultdict

LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = os.path.dirname(os.path.abspath(__file__))
days = sorted(d for d in os.listdir(LOG) if d.isdigit())

anch = {}
for d in days:
    p = f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        mid = r.get("mid_at_anchor_vector")
        if isinstance(mid, str): mid = json.loads(mid)
        anch[ts] = dict(day=d, mid=mid or {}, gross=r.get("realized_gross") or r.get("target_gross"),
                        regime=r.get("regime_at_anchor"))
ats = sorted(anch)
_bnbc = [t for t in ats if anch[t]["mid"].get("BNBUSDT")]
def bnb_mid(ts):
    if not _bnbc: return None
    t = min(_bnbc, key=lambda t: abs(t - ts)); return anch[t]["mid"]["BNBUSDT"]
BNB = {t: bnb_mid(t) for t in ats}

raw_n = 0; F = {}; dup_same = 0; dup_diff = 0
for d in days:
    p = f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); raw_n += 1
        k = (r["symbol"], r["trade_id"]); cur = F.get(k)
        if cur is None: F[k] = r; continue
        same = (cur.get("fill_notional") == r.get("fill_notional") and cur.get("commission") == r.get("commission")
                and cur.get("fill_px") == r.get("fill_px"))
        dup_same += same; dup_diff += (not same)
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None: F[k] = r
fills = list(F.values())
sys.stderr.write(f"fills rows {raw_n} -> dedup {len(fills)} (same-payload {dup_same}, differing {dup_diff})\n")

# per (anchor,symbol,makerflag)
AG = defaultdict(lambda: dict(nz=0.0, fee=0.0, slipw=0.0, slipn=0.0, mow=0.0, mon=0.0, n=0))
no_mid = 0
for r in fills:
    ts = r.get("anchor_ts"); sym = r["symbol"]
    if ts is None: continue
    nz = abs(float(r.get("fill_notional") or 0.0))
    if nz <= 0: continue
    mk = bool(r.get("venue_maker_flag")) if r.get("venue_maker_flag") is not None else (r.get("order_type") == "maker")
    ot = r.get("order_type") or ("maker" if mk else "taker")
    a = AG[(ts, sym, ot)]
    c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
    fee = c * (BNB.get(ts) or 0.0) if ca == "BNB" else c
    a["fee"] += fee; a["nz"] += nz; a["n"] += 1
    px = float(r.get("fill_px") or 0.0); sgn = 1.0 if r.get("side") == "buy" else -1.0
    m0 = (anch.get(ts, {}).get("mid") or {}).get(sym)
    if m0 and px > 0:
        a["slipw"] += sgn * (px - float(m0)) / float(m0) * 1e4 * nz; a["slipn"] += nz
    else: no_mid += nz
    m60 = r.get("mid_at_fill_plus_60s")
    if m60 is not None and px > 0:
        a["mow"] += (-sgn * (float(m60) - px) / px * 1e4) * nz; a["mon"] += nz
sys.stderr.write(f"fill notional with no anchor mid: {no_mid:.0f}\n")

# orders: intent, spread at submit
OG = defaultdict(lambda: dict(intended=0.0, intent_a1=0.0, intent_a2=0.0, skipped=0.0, filled=0.0, spw=0.0, spn=0.0, n=0, ncan=0, nsub=0))
for d in days:
    p = f"{LOG}/{d}/orders.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r = json.loads(ln); ts = r.get("anchor_ts")
        if ts is None: continue
        k = (ts, r["symbol"])
        o = OG[k]; o["n"] += 1
        ai = int(r.get("attempt_idx") or 1)
        ints = abs(float(r.get("intended_notional") or 0.0))
        o["intended"] += ints
        if ai == 1: o["intent_a1"] += ints
        else: o["intent_a2"] += ints
        o["filled"] += abs(float(r.get("filled_notional") or 0.0))
        if (r.get("terminal_reason") or "") == "skipped_min_notional": o["skipped"] += ints
        if r.get("submit_ts") is not None: o["nsub"] += 1
        if r.get("cancel_ts") is not None: o["ncan"] += 1
        sp = r.get("spread_at_submit_bps")
        if sp is not None:
            w = abs(float(r.get("intended_notional") or 0.0))
            o["spw"] += float(sp) * w; o["spn"] += w

rows = []
keys = set((ts, sym) for (ts, sym, _ot) in AG) | set(OG)
for (ts, sym) in sorted(keys):
    o = OG.get((ts, sym), None)
    rec = dict(anchor_ts=ts, day=anch.get(ts, {}).get("day"), symbol=sym,
               regime=anch.get(ts, {}).get("regime"), gross=anch.get(ts, {}).get("gross"),
               mid=(anch.get(ts, {}).get("mid") or {}).get(sym),
               intended=(o["intended"] if o else 0.0), intent_a1=(o["intent_a1"] if o else 0.0),
               intent_a2=(o["intent_a2"] if o else 0.0), skipped=(o["skipped"] if o else 0.0), filled_orders=(o["filled"] if o else 0.0),
               n_orders=(o["n"] if o else 0), n_submit=(o["nsub"] if o else 0), n_cancel=(o["ncan"] if o else 0),
               spread_bps=((o["spw"] / o["spn"]) if (o and o["spn"] > 0) else None))
    for tag, ot in (("mk", "maker"), ("tk", "topup_taker"), ("pf", "protective_flatten")):
        a = AG.get((ts, sym, ot))
        if a is None: a = dict(nz=0.0, fee=0.0, slipw=0.0, slipn=0.0, mow=0.0, mon=0.0, n=0)
        rec[f"{tag}_nz"] = a["nz"]; rec[f"{tag}_fee"] = a["fee"]; rec[f"{tag}_n"] = a["n"]
        rec[f"{tag}_slip_bps"] = (a["slipw"] / a["slipn"]) if a["slipn"] > 0 else None
        rec[f"{tag}_slip_cov"] = a["slipn"]
        rec[f"{tag}_mo_bps"] = (a["mow"] / a["mon"]) if a["mon"] > 0 else None
        rec[f"{tag}_mo_cov"] = a["mon"]
    rows.append(rec)

json.dump(dict(n_raw=raw_n, n_dedup=len(fills), dup_same=dup_same, dup_diff=dup_diff,
               n_rows=len(rows), rows=rows), open(f"{OUT}/fill_cost_rows.json", "w"))
print(f"WROTE {OUT}/fill_cost_rows.json rows={len(rows)} fills_dedup={len(fills)}")
