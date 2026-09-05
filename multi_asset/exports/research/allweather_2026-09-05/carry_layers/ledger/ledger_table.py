#!/usr/bin/env python
"""ledger_table.py — carry_layers VERIFIED layer (PREREG_carry_layers_2026-09-05 §2 last bullet): live funding ledger 2026-08-16 → 2026-09-05, read-only,
avoidable payment / dodged notional / net after cost by THR × interval × COST, plus the 1h-interval names' share of paid.
Source: ~/dl_quant_live/state/live/pilot_log/2026*/funding.jsonl (fields settlement_ts, symbol, position_notional_at_settlement, funding_rate, funding_paid [USDT cash flow to us: + = received, − = paid; verified below against −sign(notional×rate)], funding_interval_h).
prev rule: r̂ = the symbol's immediately previous settlement rate — from the ledger's own previous row when its spacing equals the interval, else from fund_aug.json.gz (fapi history to 2026-09-01), else unknown (not dodged, counted).
oracle rule: r̂ = the settled rate. Dodge ⇔ row pays (funding_paid < 0, i.e. notional×rate > 0) AND |r̂| ≥ THR. Cost = |notional| × COST bps (round trip). No price-drift term here (no prices in the ledger; the replay carries it).
Scale bridge: bps of gross per anchor = USDT / n_anchors(window) / mean full-book gross (Σ|notional| at 00/08/16Z settlements, where every name is charged) × 1e4.
usage: ledger_table.py <out_dir>  → ledger_table.json, ledger_table.md"""
import json, glob, gzip, os, sys, time, calendar, hashlib
import numpy as np
LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
FA = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/carry/fund_aug.json.gz"
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
LO, HI = T("2026-08-16"), T("2026-09-06")
THRS = (6.0, 10.0, 15.0); COSTS = (7.84, 15.8)
files = sorted(glob.glob(f"{LED}/2026*/funding.jsonl")); rows = []; n_raw = 0
for f in files:
    for line in open(f):
        line = line.strip()
        if not line: continue
        r = json.loads(line); n_raw += 1
        rows.append((float(r["settlement_ts"]), r["symbol"], float(r["position_notional_at_settlement"]), float(r["funding_rate"]), float(r["funding_paid"]), float(r.get("funding_interval_h") or 0)))
n_all = len(rows); rows = [r for r in rows if LO <= r[0] < HI]
keyed = {}; dup = 0
for r in rows:
    k = (int(r[0]), r[1])
    if k in keyed: dup += 1
    keyed[k] = r
rows = sorted(keyed.values(), key=lambda r: (r[0], r[1])); n = len(rows)
fa = json.load(gzip.open(FA, "rt"))["rates"]; fa_t = {s: np.array([x[0] for x in v], np.int64) // 1000 for s, v in fa.items()}; fa_v = {s: np.array([x[1] for x in v]) for s, v in fa.items()}
last_seen = {}; prev = []; prev_src = {"ledger": 0, "fund_aug": 0, "unknown": 0}
for r in rows:
    S, s, notion, rate, paid, iv = r; p = np.nan
    if s in last_seen and iv > 0 and abs((S - last_seen[s][0]) - iv * 3600) < 1: p = last_seen[s][1]; prev_src["ledger"] += 1
    elif s in fa_t:
        i = int(np.searchsorted(fa_t[s], int(S), side="left")) - 1
        if i >= 0: p = float(fa_v[s][i]); prev_src["fund_aug"] += 1
        else: prev_src["unknown"] += 1
    else: prev_src["unknown"] += 1
    prev.append(p); last_seen[s] = (S, rate)
A = np.array([(r[0], r[2], r[3], r[4], r[5]) for r in rows], float); prev = np.array(prev); sym = np.array([r[1] for r in rows])
S_, notion, rate, cash, iv = A.T
sign_ok = np.sign(cash) == -np.sign(notion * rate); sign_agree = float(sign_ok[(cash != 0) & (notion * rate != 0)].mean())
paid = -cash   # + = we paid
ivc = np.where(iv == 1, "1h", np.where(iv == 4, "4h", np.where(iv == 8, "8h", "other")))
paying = paid > 0
sett = np.unique(S_); full = np.array([s for s in sett if (int(s) % 86400) in (0, 8 * 3600, 16 * 3600)])
gross_full = np.array([np.abs(notion[S_ == s]).sum() for s in full]); gross_mean = float(gross_full.mean())
n_days = (HI - LO) / 86400; n_anchors = n_days * 6
res = {"source_files": len(files), "rows_raw_all_files": n_raw, "rows_in_window": n_all - 0, "rows_after_dedupe": n, "duplicates_dropped": dup, "window": ["2026-08-16 00:00Z", "2026-09-05 23:59Z"], "n_settlements": int(len(sett)), "n_full_book_settlements_00_08_16Z": int(len(full)),
       "mean_full_book_gross_usdt": round(gross_mean, 2), "n_anchors_in_window": n_anchors, "prev_rate_source_counts": prev_src, "sign_convention": "funding_paid = cash flow to us (+ received); paid := −funding_paid", "share_rows_sign_eq_minus_notional_x_rate": round(sign_agree, 5), "fund_aug_sha256": hashlib.sha256(open(FA, "rb").read()).hexdigest(),
       "totals": {"paid_usdt": round(float(paid[paying].sum()), 2), "received_usdt": round(float(-paid[~paying].sum()), 2), "net_paid_usdt": round(float(paid.sum()), 2), "net_paid_bps_gross_per_anchor": round(float(paid.sum()) / n_anchors / gross_mean * 1e4, 4),
                  "paid_share_by_interval": {c: round(float(paid[paying & (ivc == c)].sum() / paid[paying].sum()), 4) for c in ("1h", "4h", "8h", "other")}, "rows_by_interval": {c: int((ivc == c).sum()) for c in ("1h", "4h", "8h", "other")},
                  "charged_notional_share_by_interval": {c: round(float(np.abs(notion[ivc == c]).sum() / np.abs(notion).sum()), 4) for c in ("1h", "4h", "8h", "other")},
                  "paid_share_abs_rate_ge_10bps": round(float(paid[paying & (np.abs(rate) >= 1e-3)].sum() / paid[paying].sum()), 4)},
       "top_paying_symbols": [], "table": []}
agg = {}
for s_, p_ in zip(sym[paying], paid[paying]): agg[s_] = agg.get(s_, 0.0) + p_
res["top_paying_symbols"] = [{"symbol": s_, "paid_usdt": round(v, 2), "share_of_paid": round(v / float(paid[paying].sum()), 4), "interval": str(ivc[sym == s_][-1])} for s_, v in sorted(agg.items(), key=lambda x: -x[1])[:8]]
for rule in ("prev", "oracle"):
    rr = prev if rule == "prev" else rate
    for thr in THRS:
        for c in ("1h", "4h", "8h", "all"):
            m = paying & (np.isfinite(rr)) & (np.abs(rr) >= thr / 1e4) & ((ivc == c) if c != "all" else True)
            av = float(paid[m].sum()); dn = float(np.abs(notion[m]).sum()); ne = int(m.sum()); nsym = int(len(set(sym[m])))
            row = {"rule": rule, "thr_bps": thr, "interval": c, "events": ne, "symbols": nsym, "avoidable_payment_usdt": round(av, 2), "avoidable_share_of_paid": round(av / float(paid[paying].sum()), 4), "dodged_notional_usdt": round(dn, 2),
                   "dodged_notional_share_of_charged": round(dn / float(np.abs(notion).sum()), 4), "dodged_notional_per_anchor_share_of_gross": round(dn / n_anchors / gross_mean, 4)}
            for cost in COSTS:
                net = av - dn * cost / 1e4; row[f"cost_{cost}_usdt"] = round(dn * cost / 1e4, 2); row[f"net_{cost}_usdt"] = round(net, 2); row[f"net_{cost}_bps_gross_per_anchor"] = round(net / n_anchors / gross_mean * 1e4, 4)
            if rule == "prev":   # realised rate of the rows the prev rule would have dodged (what the dodge actually avoids)
                row["realised_paid_on_prev_dodged_usdt"] = round(float(paid[m].sum()), 2); row["prev_rule_false_positive_rows"] = int((m & (np.abs(rate) < thr / 1e4)).sum())
            res["table"].append(row)
json.dump(res, open(f"{OUT}/ledger_table.json", "w"), indent=1)
L = []; P = L.append
P(f"## Live funding ledger 2026-08-16 → 2026-09-05 (read-only; {res['source_files']} files, {n} rows after dedupe of {dup} duplicates; {res['n_settlements']} settlements; mean full-book gross {gross_mean:,.0f} USDT at 00/08/16Z; n_anchors {n_anchors:.0f})")
t = res["totals"]; P(f"paid {t['paid_usdt']} / received {t['received_usdt']} / net paid {t['net_paid_usdt']} USDT = {t['net_paid_bps_gross_per_anchor']} bps of gross per anchor; paid share by interval 1h {t['paid_share_by_interval']['1h']} · 4h {t['paid_share_by_interval']['4h']} · 8h {t['paid_share_by_interval']['8h']}; charged-notional share 1h {t['charged_notional_share_by_interval']['1h']}; |rate|≥10 bps rows = {t['paid_share_abs_rate_ge_10bps']} of paid; prev-rate source {prev_src}; sign check share(sign(funding_paid) = −sign(notional×rate)) = {sign_agree:.4f}")
P("top paying names: " + ", ".join(f"{x['symbol']} {x['paid_usdt']} ({x['share_of_paid']:.1%}, {x['interval']})" for x in res["top_paying_symbols"]))
P("\n| rule | THR bps | interval | events | names | avoidable paid USDT (share of paid) | dodged notional USDT (share of charged; per anchor/gross) | cost@7.84 | net@7.84 (bps/gross/anchor) | cost@15.8 | net@15.8 (bps/gross/anchor) |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
for r in res["table"]:
    P(f"| {r['rule']} | {r['thr_bps']:.0f} | {r['interval']} | {r['events']} | {r['symbols']} | {r['avoidable_payment_usdt']} ({r['avoidable_share_of_paid']:.1%}) | {r['dodged_notional_usdt']:,.0f} ({r['dodged_notional_share_of_charged']:.1%}; {r['dodged_notional_per_anchor_share_of_gross']:.3%}) | {r['cost_7.84_usdt']} | **{r['net_7.84_usdt']}** ({r['net_7.84_bps_gross_per_anchor']:+.3f}) | {r['cost_15.8_usdt']} | {r['net_15.8_usdt']} ({r['net_15.8_bps_gross_per_anchor']:+.3f}) |")
open(f"{OUT}/ledger_table.md", "w").write("\n".join(L) + "\n"); print("\n".join(L)); print("LEDGER_DONE")
