#!/usr/bin/env python3
"""R11 MEMBER (ii) FINANCING + current-regime fee run-rate + corrected reject denominator.
ENV WHITELIST = EMPTY SET (asserted, E-0826-D). READ-ONLY on ~/dl_quant_live. No GPU/network/venue call.
Margin arithmetic inputs, each VERIFIED to a file in the live repo:
  IM  = notional / 20   <- config/book.json expected_leverage_bracket=20, asserted at startup by
        binance_broker.arm() A6 (rejects launch if any symbol's venue bracket differs).
  MM  ~ 1.2006% of notional <- desk A7 measurement 2026-07-29 (docs/API_SEMANTICS.md L43), blended
        tier-1 maintMarginRatio over the then-109-name universe. FLAGGED: universe is now 450 names.
  All symbols CROSSED, ONE_WAY <- arm() A5/A1.
Tail inputs (LOWER BOUNDS, not estimates) <- E-0908-B restatement, docs/CALIBER_STATUS_2026-09-09.md L26
  and memory clip_compound_label_defect_2026_09_08: full history maxDD 41.49%->44.87%, worst day
  -6.04%->-11.21% (CALIBER_STATUS prints -11.17; both cited).
"""
import json, os, glob, hashlib
from datetime import datetime, timezone
from collections import defaultdict, Counter
import numpy as np
_real_get = os.environ.get
def _no_env(k, d=None): raise RuntimeError("E-0826-D violation: env read %r; whitelist EMPTY" % k)
os.environ.get = _no_env
LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_income"
def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]
R = {"device": "r11_financing_arith.py", "env_whitelist": [], "gpu_used": False, "network": False,
     "live_touched_write": False, "self_sha256": sha16(os.path.abspath(__file__))}
days = sorted(d for d in os.listdir(LOG) if d.isdigit())
def rd(day, fn):
    p = f"{LOG}/{day}/{fn}"
    if not os.path.exists(p): return
    for l in open(p):
        try: yield json.loads(l)
        except Exception: pass
NAVYR = lambda g: g * 2190 * 2 / 100.0
GBPS  = lambda navpct: navpct / (2190 * 2 / 100.0)

# ---------- latest account state + realized vs target gross ----------------------------------
last = None
for d in days:
    for r in rd(d, "daily_nav.jsonl"): last = r
gr = []
for d in days[-5:]:
    for r in rd(d, "anchors.jsonl"):
        if r.get("realized_gross") and r.get("target_gross"):
            gr.append((r["anchor_ts"], float(r["realized_gross"]), float(r["target_gross"])))
rg = np.array([x[1] for x in gr]); tg = np.array([x[2] for x in gr])
NAV = float(last["nav"]); TG = float(last["target_gross"]); RG = float(np.median(rg))
IM = RG / 20.0; IM_t = TG / 20.0; MMR = 0.012006
R["ACCOUNT"] = {"as_of_day": last["day"], "nav_usdt": round(NAV, 2), "wallet_balance": round(float(last["wallet_balance"]), 2),
    "sizing_policy": last["sizing_policy"], "target_gross_usdt": round(TG, 2),
    "realized_gross_usdt_median_last5d": round(RG, 2),
    "realized_over_target_gross": round(float(np.median(rg / tg)), 4),
    "note_realized_vs_target": "the book does not reach its target gross; the gap is name-level skips "
        "(min-notional, venue rejects, halts). Margin is consumed by REALIZED gross, so the encumbrance "
        "below is computed on realized, with the target-gross figure given as the upper bound."}
R["MARGIN"] = {
    "initial_margin_rule": "notional/20 (expected_leverage_bracket=20, arm() A6 asserts it every launch)",
    "IM_on_realized_gross_usdt": round(IM, 2), "IM_on_target_gross_usdt": round(IM_t, 2),
    "IM_as_pct_of_NAV_realized": round(100 * IM / NAV, 3), "IM_as_pct_of_NAV_target": round(100 * IM_t / NAV, 3),
    "maint_margin_ratio_blended_measured": MMR,
    "MM_on_realized_gross_usdt": round(RG * MMR, 2), "MM_as_pct_of_NAV": round(100 * RG * MMR / NAV, 3),
    "unencumbered_by_IM_usdt": round(NAV - IM, 2), "unencumbered_by_IM_pct_of_NAV": round(100 * (NAV - IM) / NAV, 3),
    "MMR_CAVEAT": "1.2006% was measured on a 109-name universe on 2026-07-29. The universe is now 450 "
                  "names, skewed to smaller caps whose tier-1 MMR is higher. Treat as a LOWER BOUND on MM."}
# ---------- tail-adequate buffer --------------------------------------------------------------
maxdd, worstday = 0.4487, 0.1121
def buffer(mult):
    """E = futures equity as a fraction of total NAV N, sized so that at the trough of a
    (mult x maxDD) drawdown the futures equity still covers IM on the then-current gross.
    gross = 2 x N_total throughout (constant_leverage_2.00); all P&L lands in the futures account."""
    dd = mult * maxdd
    if dd >= 1.0: return None
    # trough total NAV = (1-dd)N ; gross' = 2(1-dd)N ; IM' = 2(1-dd)N/20 = 0.1(1-dd)N
    return dd + 0.1 * (1.0 - dd)
R["BUFFER"] = {"tail_inputs": {"full_history_maxDD_restated": maxdd, "worst_day_restated": worstday,
        "status": "BOTH ARE LOWER BOUNDS, NOT ESTIMATES (E-0908-B: clip-then-compound flattened both "
                  "the crash end and the squeeze end; extreme-day COUNT unchanged, DEPTH understated)"},
    "rule": "futures equity fraction E/N must cover the drawdown plus IM on the trough gross",
    "by_safety_multiple_on_maxDD": {}}
for m in (1.0, 1.25, 1.5, 2.0):
    e = buffer(m)
    idle = 1.0 - e
    R["BUFFER"]["by_safety_multiple_on_maxDD"][f"{m}x"] = {
        "drawdown_assumed_pct_of_NAV": round(100 * m * maxdd, 2),
        "required_futures_equity_pct_of_NAV": round(100 * e, 2),
        "genuinely_idle_pct_of_NAV": round(100 * idle, 2),
        "idle_usdt_at_current_NAV": round(idle * NAV, 2)}
R["BUFFER"]["value_per_1pct_annual_yield"] = {
    m: {"NAV_pct_per_year": round(v["genuinely_idle_pct_of_NAV"] / 100.0, 4),
        "g_bps_per_anchor_per_unit_gross": round(GBPS(v["genuinely_idle_pct_of_NAV"] / 100.0), 6),
        "pct_of_A0_0.6342": round(100 * GBPS(v["genuinely_idle_pct_of_NAV"] / 100.0) / 0.6342, 3)}
    for m, v in R["BUFFER"]["by_safety_multiple_on_maxDD"].items()}
R["BUFFER"]["STRUCTURAL_BLOCKER"] = (
    "Under sizing_policy=constant_leverage_2.00 the book's gross is recomputed every anchor as "
    "nav x 2.0 where nav = the FUTURES account margin_balance. Every dollar moved out of the futures "
    "wallet therefore shrinks gross by two dollars at the next anchor. The idle fraction above is NOT "
    "withdrawable under the deployed policy; realising it requires either (a) a yield-bearing margin "
    "asset that never leaves the futures wallet, or (b) decoupling the sizing base from the futures "
    "wallet balance. Both are live changes. (a) additionally collides with arm() A5/A6, which assert "
    "the collateral and bracket configuration at every launch.")

# ---------- realized funding carry (what the desk is paid/charged for HOLDING) ----------------
fsum = 0.0; fn = 0; fday = defaultdict(float)
for d in days:
    seen = set()
    for r in rd(d, "funding.jsonl"):
        k = (r["symbol"], r["settlement_ts"])
        if k in seen: continue
        seen.add(k); v = float(r.get("funding_paid") or 0.0)
        fsum += v; fn += 1; fday[d] += v
R["FUNDING_CARRY"] = {"window": [days[0], days[-1]], "rows_deduped": fn, "net_usdt": round(fsum, 2),
    "sign": "funding_paid POSITIVE = RECEIVED by the book (verified on a row: long 903.53 notional at "
            "rate -0.00590608 -> +5.22 credited)",
    "reading": "over these 42 days the book NET PAID 871.74 USDT of funding. This is NOT a non-forecast "
               "income line for this book: the funding-momentum leg deliberately holds the extreme-funding "
               "names, so paying funding is the position's entry fee, already inside A0's alpha "
               "(memory funding_settlement_window_momentum_dodge_refuted / funding_transfer_priced_in_"
               "settlement_window). Recorded here so it is not double-counted as upside.",
    "by_day_last10": {d: round(fday[d], 2) for d in days[-10:]}}

# ---------- current-regime fee run-rate (BNB discount OFF since 2026-09-07) --------------------
bnb = {}
for d in days:
    for r in rd(d, "anchors.jsonl"):
        mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except Exception: mv = {}
        if mv and mv.get("BNBUSDT"): bnb[float(r["anchor_ts"])] = float(mv["BNBUSDT"])
bts = sorted(bnb)
F = {}
for d in days:
    for r in rd(d, "fills.jsonl"):
        k = (r["symbol"], r["trade_id"]); cur = F.get(k)
        if cur is None: F[k] = r; continue
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None: F[k] = r
def feeu(r):
    c = float(r.get("commission") or 0.0)
    if r.get("commission_asset") == "BNB":
        t = float(r.get("anchor_ts") or 0); return c * (bnb[min(bts, key=lambda k: abs(k - t))] if bts else 0.0)
    return c
def regime(day0, day1, label):
    nz = fee = 0.0; mknz = tknz = 0.0; bnbnz = 0.0
    pa = defaultdict(lambda: [0.0, 0.0])
    for r in F.values():
        dd = datetime.fromtimestamp(float(r.get("fill_ts") or r.get("anchor_ts") or 0), tz=timezone.utc).strftime("%Y%m%d")
        if not (day0 <= dd <= day1): continue
        n = abs(float(r.get("fill_notional") or 0.0))
        if n <= 0: continue
        nz += n; fee += feeu(r)
        if r.get("venue_maker_flag"): mknz += n
        else: tknz += n
        if r.get("commission_asset") == "BNB": bnbnz += n
        pa[r.get("anchor_ts")][0] += n
    g = 0.0
    for d in days:
        if not (day0 <= d <= day1): continue
        for r in rd(d, "position_readback.jsonl"):
            if r["anchor_ts"] in pa: pa[r["anchor_ts"]][1] += abs(float(r.get("venue_position_notional") or 0.0))
    G = sum(v[1] for v in pa.values()); NZ = sum(v[0] for v in pa.values())
    T = NZ / G if G > 0 else float("nan")
    allin = fee / nz * 1e4
    recover = 0.10 * (fee if bnbnz == 0 else fee * (1 - bnbnz / nz))   # 10% on the USDT-paid part
    rb = recover / nz * 1e4
    return {"label": label, "days": [day0, day1], "traded_notional": round(nz, 2),
            "fee_usdt": round(fee, 3), "all_in_fee_bps_per_unit_traded": round(allin, 4),
            "maker_share": round(mknz / nz, 4), "BNB_coverage": round(bnbnz / nz, 4),
            "n_anchors": len(pa), "turnover_traded_over_gross": round(T, 6),
            "fee_g_bps_per_anchor_per_unit_gross": round(allin * T, 5),
            "fee_NAV_pct_per_year_at_2x": round(NAVYR(allin * T), 4),
            "BNB_recoverable_bps_per_unit_traded": round(rb, 4),
            "BNB_recoverable_g_bps": round(rb * T, 6),
            "BNB_recoverable_NAV_pct_per_year_at_2x": round(NAVYR(rb * T), 4)}
R["FEE_REGIMES"] = [regime("20260805", "20260906", "BNB discount ON (100% coverage)"),
                    regime("20260907", "20260911", "BNB discount OFF (0% coverage) = CURRENT"),
                    regime("20260801", "20260911", "whole window")]

# ---------- corrected reject denominator (E-0905-H: denominator effect) -----------------------
den = defaultdict(lambda: Counter())
for d in days:
    for r in rd(d, "orders.jsonl"):
        if r.get("order_type") != "maker" or int(r.get("attempt_idx") or 1) != 1: continue
        tr = r.get("terminal_reason")
        if str(tr).startswith("skipped"): continue           # never reached the venue
        arm = r.get("placement_arm")
        den[d]["n"] += 1; den[(d, arm)]["n"] += 1
        if tr == "venue_reject": den[d]["rej"] += 1; den[(d, arm)]["rej"] += 1
R["REJECT_RATE_corrected_denominator"] = {
    "denominator": "attempt-1 maker lines that REACHED the venue (submitted or rejected); "
                   "skipped_min_notional excluded — E-0905-H, the alarm's denominator shrank when the "
                   "09-03 deposit cut min-notional skips, inflating the printed ratio",
    "by_day": {d: {"n": den[d]["n"], "rej": den[d]["rej"],
                   "rate": round(den[d]["rej"] / den[d]["n"], 4) if den[d]["n"] else None}
               for d in days if den[d]["n"]}}
json.dump(R, open(f"{OUT}/receipts/RECEIPT_r11_M2_financing.json", "w"), indent=1)
os.environ.get = _real_get
print(json.dumps({k: R[k] for k in ("ACCOUNT", "MARGIN", "BUFFER", "FUNDING_CARRY", "FEE_REGIMES")}, indent=1))
