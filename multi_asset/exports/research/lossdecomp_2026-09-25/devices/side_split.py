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
rev 1 (2026-09-27, dlarch spec written before any reading, anti-momentum vs idiosyncratic-vol): `--buckets` adds, per interval, tertile
buckets over the WHOLE held book (both sides, equal name counts, one set of edges) of P1 / P3 / P7 (past 1/3/7-day cumulative rr return)
and V7 (std of the 5-minute rr over the last 7 days), computed only from bars closing at or before the interval start tA (asserted per
variable); per interval x side x bucket: n names, |notional|, price / beta / residual (same caliber); names with an undefined variable go to
"unknown". Control: every variable's buckets sum to the side totals (float summation order => relative tolerance 1e-9, named).
Pooled only (no arm split) — inside the blind-state rule.
usage: ~/wide_shadow/venv/bin/python side_split.py <layered_book out dir> <out json> [--buckets]"""
import collections, glob, hashlib, json, os, sys, time
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
src, outp = sys.argv[1], sys.argv[2]; BUCKETS = "--buckets" in sys.argv[3:]
LB = json.load(open(f"{src}/LAYERED_BOOK.json")); NM = [json.loads(l) for l in open(f"{src}/NAMES.jsonl")]
snap = f"{WS}/state/snap/{LB['price_snapshot']}"
Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
assert hashlib.sha256(open(f"{snap}/rolling.npz", "rb").read()).hexdigest() == LB["rolling_sha256"], "price snapshot differs from layered_book's"
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; jb = syms.index("BTCUSDT")
LP = np.cumsum(np.log1p(np.nan_to_num(RR[:, jb]))); LP = np.concatenate([[0.0], LP])
colx = {s_: j for j, s_ in enumerate(syms)}
LPA = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)]); FINA = np.isfinite(RR)
def bucket_vars(s_, tA):
    """(P1, P3, P7, V7, last_bar_ts) from bars closing at or before tA only; None where undefined (< 90% finite bars)."""
    j = colx.get(s_)
    if j is None: return None
    i1 = int(np.searchsorted(ts, tA, side="right")) - 1
    out = {}
    for k, n in (("P1", 288), ("P3", 864), ("P7", 2016)):
        i0 = i1 - n
        out[k] = float(np.expm1(LPA[i1 + 1, j] - LPA[i0 + 1, j])) if i0 >= 0 and FINA[i0 + 1:i1 + 1, j].mean() >= 0.9 else None
    w = RR[max(i1 - 2015, 0):i1 + 1, j]; w = w[np.isfinite(w)]
    out["V7"] = float(np.std(w)) if len(w) >= 0.9 * 2016 else None
    out["_last_bar_ts"] = int(ts[i1])
    return out
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
checks = []; bchecks = []
for x in NM:
    if not x["priced"]: continue
    A, tA, tB = x["A"], x["tA"], x["tB"]
    bet, bA = betas_for(A); rb = r_btc(tA, tB)
    c = collections.defaultdict(float); n_nobeta = 0; unpriced = 0.0
    side_of = {}; per_name = {}
    for s, (l5, r, l2) in x["names"].items():
        if l5 is None: continue
        sd = "long" if l5 > 0 else ("short" if l5 < 0 else None)
        side_of[s] = sd
        if sd is None: continue
        if r is None: unpriced += abs(l5); continue
        c[f"price_{sd}"] += l5 * r
        if bet is not None and s in bet:
            c[f"beta_{sd}"] += l5 * float(bet[s]) * rb
            per_name[s] = (sd, abs(l5), l5 * r, l5 * float(bet[s]) * rb, 0.0)
        else:
            c[f"no_beta_{sd}"] += l5 * r; n_nobeta += 1
            per_name[s] = (sd, abs(l5), l5 * r, 0.0, l5 * r)
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
    if BUCKETS:
        bv = {s_: bucket_vars(s_, tA) for s_ in per_name}
        assert all(v is None or v["_last_bar_ts"] <= tA for v in bv.values()), "a bucket variable used a bar after the interval start"
        row["buckets"] = {}
        for var in ("P1", "P3", "P7", "V7"):
            vals = sorted((bv[s_][var], s_) for s_ in per_name if bv[s_] is not None and bv[s_][var] is not None)
            nv = len(vals); lab = {}
            for k, (_v, s_) in enumerate(vals):
                lab[s_] = ("low", "mid", "high")[min(3 * k // max(nv, 1), 2)]
            edges = [vals[nv // 3][0], vals[2 * nv // 3][0]] if nv >= 3 else None
            agg = collections.defaultdict(lambda: collections.defaultdict(float))
            for s_, (sd, an_, pr, be, nb) in per_name.items():
                b_ = lab.get(s_, "unknown"); a_ = agg[f"{sd}|{b_}"]
                a_["n"] += 1; a_["abs_notional"] += an_; a_["price"] += pr; a_["beta"] += be; a_["residual"] += pr - be - nb
            for sd in ("long", "short"):
                sp = sum(v["price"] for k_, v in agg.items() if k_.startswith(sd + "|")); sr = sum(v["residual"] for k_, v in agg.items() if k_.startswith(sd + "|"))
                okp = abs(sp - c[f"price_{sd}"]) <= 1e-9 * max(1.0, abs(c[f"price_{sd}"])); okr = abs(sr - c[f"residual_{sd}"]) <= 1e-9 * max(1.0, abs(c[f"residual_{sd}"]))
                bchecks.append(okp and okr)
            row["buckets"][var] = {"edges_low_mid_high": edges, "n_defined": nv, "cells": {k_: {kk: round(vv, 2) for kk, vv in v.items()} for k_, v in sorted(agg.items())}}
            for k_, v in agg.items():
                for kk, vv in v.items(): tot[f"B|{var}|{k_}|{kk}"] += vv
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
if BUCKETS:
    wb = collections.defaultdict(dict)
    for k, v in tot.items():
        if k.startswith("B|"):
            _, var, cell, kk = k.split("|")
            wb[var].setdefault(cell, {})[kk] = round(v, 2)
    out["window_buckets"] = {var: dict(sorted(v.items())) for var, v in sorted(wb.items())}
    out["bucket_sums_equal_side_totals_every_interval"] = bool(bchecks) and all(bchecks)
json.dump(out, open(outp, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("n_priced_intervals", "all_side_sums_equal_certified_L5", "window_totals", "by_day", "VERDICT") + (("bucket_sums_equal_side_totals_every_interval", "window_buckets") if BUCKETS else ())}, indent=1))
