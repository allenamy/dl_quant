#!/usr/bin/env python3
"""R11 NON-FORECAST INCOME — arithmetic device.  ENV WHITELIST = EMPTY SET (asserted below, E-0826-D).
READ-ONLY on /Users/haosiyu/dl_quant_live (opened for read; never written, no process touched, no venue call).
No GPU. No network. Caliber pin: v4 chain 2026-09-09 — but note this device reads the LIVE LEDGER only
(fills/orders/anchors/daily_nav/position_readback), which is outside the panel lineage entirely, so the
v3/v4 panel question does not arise here (same standing as GROUNDTRUTH_lead_2026-09-11 §: live-side
measurement does not pass through the panel lineage).

STATISTIC (frozen, from the task): g = net_ex/gross_total, bps per 4h anchor per unit gross.
UTC-day block bootstrap, 2000 resamples, numpy.default_rng([20260905,k]).
NAV%/yr at 2.0x gross = g_bps * 2190 * 2 / 100.   (check: A0 0.6342 -> 27.78%)

SIGN CONVENTION: POSITIVE = COST to the book.  markout = side*(mid@fill+60s - fill_px)/fill_px,
POSITIVE markout = price moved OUR way = a GAIN; adverse-selection cost = -markout.
"""
import json, os, glob, hashlib, math, sys
from datetime import datetime, timezone
from collections import defaultdict, Counter
import numpy as np

# ---- E-0826-D: assert EMPTY env whitelist -------------------------------------------------
_real_get = os.environ.get
def _no_env(k, d=None):
    raise RuntimeError("E-0826-D violation: script read env var %r; whitelist is EMPTY SET" % k)
os.environ.get = _no_env
ENV_WHITELIST = []

LOG  = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
LIVE = "/Users/haosiyu/dl_quant_live"
OUT  = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_income"
SEED, NBOOT = 20260905, 2000

def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]

R = {"device": "r11_income_arith.py", "env_whitelist": ENV_WHITELIST, "gpu_used": False,
     "live_touched_write": False, "venue_calls": 0, "network": False,
     "self_sha256": None, "inputs_sha16": {}, "stat": {
        "g": "net_ex/gross_total, bps per 4h anchor per unit gross",
        "bootstrap": "UTC-day block, 2000 resamples, numpy.default_rng([20260905,k])",
        "nav_pct_per_year_at_2x": "g_bps * 2190 * 2 / 100",
        "A0_reference": {"mean_g_bps": 0.6342, "sharpe": 1.2912, "n": 9138, "nav_pct_yr_2x": 27.78}}}
R["self_sha256"] = sha16(os.path.abspath(__file__))
for p in (f"{LIVE}/config/book.json", f"{LIVE}/live/placement_bandit.py",
          f"{LIVE}/live/requote_experiment.py", f"{LIVE}/live/binance_broker.py"):
    R["inputs_sha16"][p.replace(LIVE + "/", "")] = sha16(p)

days = sorted(d for d in os.listdir(LOG) if d.isdigit())
R["window"] = {"days": [days[0], days[-1]], "n_days": len(days)}

def rd(day, fn):
    p = f"{LOG}/{day}/{fn}"
    if not os.path.exists(p): return
    for l in open(p):
        try: yield json.loads(l)
        except Exception: pass

# ---------------- anchors: BNB mid, gross ----------------------------------------------------
bnb = {}; gross_anchor = {}; day_of_anchor = {}
for d in days:
    for r in rd(d, "anchors.jsonl"):
        ts = r.get("anchor_ts")
        if ts is None: continue
        mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except Exception: mv = {}
        if mv and mv.get("BNBUSDT"): bnb[float(ts)] = float(mv["BNBUSDT"])
        day_of_anchor[ts] = d
        g = r.get("realized_gross") or r.get("target_gross")
        if g: gross_anchor[ts] = float(g)
bts = sorted(bnb)
def bnbpx(t):
    if not bts: return None
    return bnb[min(bts, key=lambda k: abs(k - t))]
# gross from the venue position readback (book layer) where available
pbg = defaultdict(float)
for d in days:
    for r in rd(d, "position_readback.jsonl"):
        pbg[r["anchor_ts"]] += abs(float(r.get("venue_position_notional") or 0.0))
def gross_of(ts):
    g = pbg.get(ts, 0.0)
    return g if g > 0 else gross_anchor.get(ts, 0.0)

# ---------------- fills: dedupe by (symbol, trade_id) ----------------------------------------
F = {}; raw = 0; dsame = 0; ddiff = 0
for d in days:
    for r in rd(d, "fills.jsonl"):
        raw += 1; k = (r["symbol"], r["trade_id"]); cur = F.get(k)
        if cur is None: F[k] = r; continue
        same = (cur.get("fill_notional") == r.get("fill_notional")
                and cur.get("commission") == r.get("commission") and cur.get("fill_px") == r.get("fill_px"))
        dsame += same; ddiff += (not same)
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None: F[k] = r
fills = list(F.values())
R["dedupe"] = {"raw_rows": raw, "deduped": len(fills), "dropped": raw - len(fills),
               "identical_payload_dupes": dsame, "payload_differing_dupes": ddiff}

def fee_usdt(r):
    c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
    if ca == "BNB":
        px = bnbpx(float(r.get("anchor_ts") or 0))
        return c * (px or 0.0), True
    return c, False

# =============================================================================================
# MEMBER (i) — FEE TIER AND REBATE ENGINEERING
# =============================================================================================
cell = defaultdict(lambda: {"nz": 0.0, "fee": 0.0, "n": 0})
byday = defaultdict(lambda: {"bnb_nz": 0.0, "usdt_nz": 0.0, "fee": 0.0, "nz": 0.0})
bytype = defaultdict(lambda: {"nz": 0.0, "fee": 0.0, "n": 0})
tot_nz = 0.0; tot_fee = 0.0
for r in fills:
    nz = abs(float(r.get("fill_notional") or 0.0))
    if nz <= 0: continue
    f, isbnb = fee_usdt(r)
    mk = bool(r.get("venue_maker_flag"))
    ca = r.get("commission_asset") or "USDT"
    c = cell[("maker" if mk else "taker", ca)]; c["nz"] += nz; c["fee"] += f; c["n"] += 1
    t = bytype[r.get("order_type")]; t["nz"] += nz; t["fee"] += f; t["n"] += 1
    dd = datetime.fromtimestamp(float(r.get("fill_ts") or r.get("anchor_ts") or 0), tz=timezone.utc).strftime("%Y%m%d")
    b = byday[dd]; b["nz"] += nz; b["fee"] += f
    (b.__setitem__("bnb_nz", b["bnb_nz"] + nz) if isbnb else b.__setitem__("usdt_nz", b["usdt_nz"] + nz))
    tot_nz += nz; tot_fee += f

R["M1_fee"] = {"cells": {f"{k[0]}|{k[1]}": {"notional": round(v["nz"], 2), "fee_usdt": round(v["fee"], 4),
                "bps": round(v["fee"] / v["nz"] * 1e4, 4), "n_fills": v["n"]} for k, v in sorted(cell.items())},
               "by_order_type": {k: {"notional": round(v["nz"], 2), "bps": round(v["fee"] / v["nz"] * 1e4, 4),
                "share_of_traded_pct": round(100 * v["nz"] / tot_nz, 3), "n_fills": v["n"]} for k, v in sorted(bytype.items())},
               "total_traded_notional": round(tot_nz, 2), "total_fee_usdt": round(tot_fee, 4),
               "all_in_fee_bps_per_unit_traded": round(tot_fee / tot_nz * 1e4, 4)}
mk_nz = sum(v["nz"] for k, v in cell.items() if k[0] == "maker")
tk_nz = tot_nz - mk_nz
bnb_nz = sum(v["nz"] for k, v in cell.items() if k[1] == "BNB")
usdt_nz = tot_nz - bnb_nz
usdt_fee = sum(v["fee"] for k, v in cell.items() if k[1] != "BNB")
R["M1_fee"].update({
    "maker_share_of_traded_notional": round(mk_nz / tot_nz, 4),
    "taker_share_of_traded_notional": round(tk_nz / tot_nz, 4),
    "BNB_coverage_of_traded_notional": round(bnb_nz / tot_nz, 4),
    "BNB_coverage_by_day": {d: round(v["bnb_nz"] / (v["nz"] or 1), 4) for d, v in sorted(byday.items())},
    "traded_notional_by_day": {d: round(v["nz"], 1) for d, v in sorted(byday.items())},
    "tier_identification": {
        "maker_USDT_bps_measured": round(cell[("maker", "USDT")]["fee"] / cell[("maker", "USDT")]["nz"] * 1e4, 4),
        "taker_USDT_bps_measured": round(cell[("taker", "USDT")]["fee"] / cell[("taker", "USDT")]["nz"] * 1e4, 4),
        "maker_BNB_bps_measured": round(cell[("maker", "BNB")]["fee"] / cell[("maker", "BNB")]["nz"] * 1e4, 4),
        "taker_BNB_bps_measured": round(cell[("taker", "BNB")]["fee"] / cell[("taker", "BNB")]["nz"] * 1e4, 4),
        "reading": "USDT-denominated rows are EXACTLY 2.0000 / 5.0000 bps = Binance USDT-perp VIP0 "
                   "(0.0200%/0.0500%). BNB rows are those x0.90 => the 10% BNB fee discount, nothing more."}})
# BNB shortfall value: 10% of the fee paid in USDT
bnb_recover_usdt = 0.10 * usdt_fee
R["M1_fee"]["lever_BNB_restore"] = {
    "usdt_denominated_notional": round(usdt_nz, 2), "usdt_denominated_fee_usdt": round(usdt_fee, 4),
    "recoverable_usdt_over_window": round(bnb_recover_usdt, 4),
    "recoverable_bps_per_unit_traded": round(bnb_recover_usdt / tot_nz * 1e4, 4)}
# taker-mix lever: what the taker notional would have cost at the maker rate
mk_rate = sum(v["fee"] for k, v in cell.items() if k[0] == "maker") / mk_nz * 1e4
tk_rate = sum(v["fee"] for k, v in cell.items() if k[0] == "taker") / tk_nz * 1e4
R["M1_fee"]["lever_taker_mix"] = {
    "maker_blended_bps": round(mk_rate, 4), "taker_blended_bps": round(tk_rate, 4),
    "taker_notional": round(tk_nz, 2), "spread_bps": round(tk_rate - mk_rate, 4),
    "if_all_taker_became_maker_usdt": round(tk_nz * (tk_rate - mk_rate) / 1e4, 4),
    "bps_per_unit_traded": round(tk_nz * (tk_rate - mk_rate) / 1e4 / tot_nz * 1e4, 4)}

# ---- turnover: traded notional per unit gross per anchor ------------------------------------
per_anchor = defaultdict(lambda: {"nz": 0.0, "fee": 0.0})
for r in fills:
    ts = r.get("anchor_ts")
    if ts is None: continue
    nz = abs(float(r.get("fill_notional") or 0.0)); f, _ = fee_usdt(r)
    per_anchor[ts]["nz"] += nz; per_anchor[ts]["fee"] += f
rows = [(ts, gross_of(ts), v["nz"], v["fee"]) for ts, v in per_anchor.items() if gross_of(ts) > 0]
G_sum = sum(r[1] for r in rows); NZ_sum = sum(r[2] for r in rows)
turnover = NZ_sum / G_sum
R["turnover"] = {"n_anchors_with_fills_and_gross": len(rows), "sum_gross": round(G_sum, 2),
                 "sum_traded_notional": round(NZ_sum, 2),
                 "realized_turnover_traded_over_gross_per_anchor": round(turnover, 6),
                 "r9screen_quoted_turnover_for_A0": 0.03032,
                 "note": "LIVE realized turnover, book layer gross. The A0 replay turnover 0.03032 is a "
                         "DIFFERENT object (replay book, frozen window); both are reported, never mixed."}

def to_anchor_gross(bps_per_unit_traded, T):
    """bps per unit traded -> bps per anchor per unit gross, at turnover T."""
    return bps_per_unit_traded * T
def to_nav_yr(g_bps): return g_bps * 2190 * 2 / 100.0

for key, val in (("lever_BNB_restore", R["M1_fee"]["lever_BNB_restore"]["recoverable_bps_per_unit_traded"]),
                 ("lever_taker_mix", R["M1_fee"]["lever_taker_mix"]["bps_per_unit_traded"])):
    for tname, T in (("at_live_turnover", turnover), ("at_A0_replay_turnover_0.03032", 0.03032)):
        g = to_anchor_gross(val, T)
        R["M1_fee"][key].setdefault("valuation", {})[tname] = {
            "turnover": round(T, 6), "g_bps_per_anchor_per_unit_gross": round(g, 6),
            "NAV_pct_per_year_at_2x": round(to_nav_yr(g), 4),
            "pct_of_A0_0.6342": round(100 * g / 0.6342, 3)}

json.dump(R, open(f"{OUT}/receipts/RECEIPT_r11_M1_fee.json", "w"), indent=1)
os.environ.get = _real_get
print(json.dumps({k: R[k] for k in ("dedupe", "turnover", "M1_fee")}, indent=1))
