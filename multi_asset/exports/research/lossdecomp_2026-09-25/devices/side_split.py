#!/usr/bin/env python3
"""Certified long/short split of the held book (lead 2026-09-27, user question "no broad rally in the last two days — why still losing?";
lead's quick ESTIMATE 8c2216ddb: both sides lose => wrong-way selection). READ-ONLY, pooled (no arm split).
Input: layered_book rev 4 output dir (LAYERED_BOOK.json + NAMES.jsonl, --dump-names) — the L5 readback book and the SAME rr return per name
per interval that layered_book priced (so the side totals sum to its certified L5 total; asserted per anchor).
Per interval (this readback -> next), per side (sign of the held L5 notional):
  price       sum n_i r_i                          (certified: equals layered_book L5 per anchor, asserted)
  beta        sum n_i beta_i r_BTC                 beta_i = the producer's own m3_beta_v2 beta for that anchor (target_live beta_overlay;
                                                    missing field => the nearest EARLIER anchor's betas, named); r_BTC = BTCUSDT rr, same interval
  residual    price - beta                         (the selection part: what the names did beyond their BTC exposure)
  no_beta     price of held names without a beta (outside the producer's universe) — reported apart, never split
  funding     funding.jsonl funding_paid, settlement in (tA, tB], side = sign(position_notional_at_settlement)
  fees        fills.jsonl commission of the anchor's rebalance, side = sign of the name's L5 after the trades (flat after => the fill's
              side: BUY closes a short => short side)
FROZEN VERDICT RULE (written before any reading; lead's estimate is the hypothesis):
  over the priced intervals of the window, CONFIRMED iff residual_long < 0 AND residual_short < 0 (both sides lose after removing BTC beta);
  REFUTED-<side> for a side whose residual >= 0; also reported per UTC day of the interval start. No significance claim (a few days).
usage: ~/wide_shadow/venv/bin/python side_split.py <layered_book out dir> <out json>"""
import collections, glob, hashlib, json, os, sys, time
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
src, outp = sys.argv[1], sys.argv[2]
LB = json.load(open(f"{src}/LAYERED_BOOK.json")); NM = [json.loads(l) for l in open(f"{src}/NAMES.jsonl")]
snap = f"{WS}/state/snap/{LB['price_snapshot']}"
Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
assert hashlib.sha256(open(f"{snap}/rolling.npz", "rb").read()).hexdigest() == LB["rolling_sha256"], "price snapshot differs from layered_book's"
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; jb = syms.index("BTCUSDT")
LP = np.cumsum(np.log1p(np.nan_to_num(RR[:, jb]))); LP = np.concatenate([[0.0], LP])
def r_btc(tA, tB):
    i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
    return float(np.expm1(LP[i1 + 1] - LP[i0 + 1]))
betas_by_A = {}
for p in sorted(glob.glob(f"{WS}/state/target_live/*.json")):
    try:
        d = json.load(open(p))
    except Exception:
        continue
    b = (d.get("beta_overlay") or {}).get("betas")
    if b: betas_by_A[int(d["anchor_ts"])] = b
def betas_for(A):
    k = [a for a in betas_by_A if a <= A]
    return (betas_by_A[max(k)], max(k)) if k else (None, None)
days = sorted({time.strftime("%Y%m%d", time.gmtime(x["tA"] + d)) for x in NM for d in (-86400, 0, 86400, 2 * 86400)})
def rows(t):
    out = []
    for d in days:
        p = f"{L}/{d}/{t}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out
FUND = rows("funding")
sys.path.insert(0, f"{HOME}/dl_quant_live/live"); import pilot_log as PL
FILLS = PL.collapse_supersedes(rows("fills"))
lb_by_A = {r["A"]: r for r in LB["anchors"]}
res, tot, byday = [], collections.defaultdict(float), collections.defaultdict(lambda: collections.defaultdict(float))
checks = []
for x in NM:
    if not x["priced"]: continue
    A, tA, tB = x["A"], x["tA"], x["tB"]
    bet, bA = betas_for(A); rb = r_btc(tA, tB)
    c = collections.defaultdict(float); n_nobeta = 0; unpriced = 0.0
    side_of = {}
    for s, (l5, r, l2) in x["names"].items():
        if l5 is None: continue
        sd = "long" if l5 > 0 else ("short" if l5 < 0 else None)
        side_of[s] = sd
        if sd is None: continue
        if r is None: unpriced += abs(l5); continue
        c[f"price_{sd}"] += l5 * r
        if bet is not None and s in bet:
            c[f"beta_{sd}"] += l5 * float(bet[s]) * rb
        else:
            c[f"no_beta_{sd}"] += l5 * r; n_nobeta += 1
    for sd in ("long", "short"):
        c[f"residual_{sd}"] = c[f"price_{sd}"] - c[f"beta_{sd}"] - c[f"no_beta_{sd}"]
    for f in FUND:
        st = float(f["settlement_ts"])
        if tA < st <= tB:
            pn = float(f["position_notional_at_settlement"]); c["funding_" + ("long" if pn > 0 else "short")] += float(f.get("funding_paid") or 0.0)
    rid = (lb_by_A.get(fmt(A)) or {}).get("rebalance_id")
    for f in FILLS:
        if f.get("rebalance_id") != rid or rid is None: continue
        sd = side_of.get(f["symbol"]) or ("short" if str(f.get("side")).upper() == "BUY" else "long")
        c["fees_" + sd] -= abs(float(f.get("commission") or 0.0))
    lbr = lb_by_A.get(fmt(A)) or {}
    l5_cert = (lbr.get("pnl_by_layer") or {}).get("L5_readback")
    ok = l5_cert is not None and abs(c["price_long"] + c["price_short"] - l5_cert) < 1e-6 * max(1.0, abs(l5_cert))
    checks.append(ok)
    row = {"A": fmt(A), "interval": [fmt(tA), fmt(tB)], "r_btc": round(rb, 5), "betas_from": fmt(bA) if bA else None,
           "n_names_no_beta": n_nobeta, "unpriced_abs": round(unpriced, 1), "L5_certified": l5_cert, "sum_equals_certified_L5": ok,
           **{k: round(v, 2) for k, v in sorted(c.items())}}
    res.append(row)
    dkey = time.strftime("%m-%d", time.gmtime(tA))
    for k, v in c.items():
        tot[k] += v; byday[dkey][k] += v
sides = {sd: {k: round(tot[f"{k}_{sd}"], 1) for k in ("price", "beta", "residual", "no_beta", "funding", "fees")} for sd in ("long", "short")}
verdict = ("CONFIRMED (both sides lose after removing BTC beta)" if sides["long"]["residual"] < 0 and sides["short"]["residual"] < 0 else
           " / ".join(f"REFUTED-{sd} (residual {sides[sd]['residual']:+.1f})" for sd in ("long", "short") if sides[sd]["residual"] >= 0))
out = {"device": "side_split.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "layered_book": {"dir": src, "device_sha256": LB["device_sha256"], "window": LB["window"], "price_snapshot": LB["price_snapshot"]},
       "n_priced_intervals": len(res), "all_side_sums_equal_certified_L5": all(checks), "window_totals": sides,
       "by_day": {d: {sd: {k: round(v.get(f"{k}_{sd}", 0.0), 1) for k in ("price", "beta", "residual", "no_beta", "funding", "fees")} for sd in ("long", "short")}
                  for d, v in sorted(byday.items())},
       "VERDICT": verdict, "intervals": res}
json.dump(out, open(outp, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("n_priced_intervals", "all_side_sums_equal_certified_L5", "window_totals", "by_day", "VERDICT")}, indent=1))
