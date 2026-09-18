#!/usr/bin/env python3
"""FP3 P-C3 (read-only counterfactual): the per-name stop clause under three specifications, replayed over the LIVE ledgers with the executor's own pure
function `per_name_stop.evaluate(snapshot, state, conf, now)`:
  V0 production   : depth = unrealised / |current notional| ≤ depth_pct, `consecutive_anchors` = 2 (cf40ea21 profile as configured)
  V1 entry-basis  : depth = unrealised / |entry notional| (= avg cost × |qty|)  — the "−30% relative to the entry price" reading (independent review 4.3)
  V2 one-anchor   : production denominator, `consecutive_anchors` = 1
Per-name unrealised P&L is NOT persisted per anchor; it is reconstructed from fills (average cost, basis marked UNKNOWN after a venue re-seat exactly as the cash
engine v5 does) and the post-anchor readback marks. Names with unknown basis are excluded from the depth test (counted). For every stop event the next-3-day
(18 anchors) price return of the stopped name is priced with the producer 5m panel: a stop AVOIDS that P&L (positive avoided-loss = the stop helped).
This is an event-level footprint, not the complete-portfolio contrast the reviewer asked for (reshape/neutrality effects of the exit are not replayed).
usage: pc3_stop_counterfactual.py <from_day YYYYMMDD> <to_day> <out.json>"""
import sys, os, json, time, glob, collections
import numpy as np
F, T, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; REPO = os.path.expanduser("~/dl_quant_live"); WS = os.path.expanduser("~/wide_shadow"); P = f"{REPO}/state/live/pilot_log"
sys.path.insert(0, f"{REPO}/live"); import per_name_stop as PNS
days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if F <= d.split("/")[-1] <= T)
rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))
conf0 = PNS.cfg(); conf0 = dict(conf0, enabled=True); print("production conf:", {k: conf0.get(k) for k in ("depth_pct", "consecutive_anchors", "cooloff_days", "min_notional_usdt", "profile")})
# ── fills (deduped) and readbacks ──
by_tid = {}
for d in days:
    for r in rows(d, "fills"):
        t = r.get("trade_id"); k = (r.get("backfilled_utc") or "", d)
        if t not in by_tid or k >= by_tid[t][0]: by_tid[t] = (k, r)
fills = sorted((r for _, r in by_tid.values()), key=lambda r: float(r["fill_ts"]))
rb = [r for d in days for r in rows(d, "position_readback") if str(r.get("source", "")).endswith("@post_anchor")]
snaps = collections.defaultdict(dict)
for r in rb: snaps[int(float(r["anchor_ts"]) // 14400 * 14400)][r["symbol"]] = r
anchors = sorted(snaps)
# ── producer panel returns for pricing (5m ret5 → per-anchor 4h returns) ──
R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True); rts = R["ts"].astype(np.int64); ret5 = np.asarray(R["data"][:, :, 0], np.float64); syms = [str(x) for x in np.load(f"{WS}/fea171/xfer_syms.npz", allow_pickle=True)["symbols"]]; sidx = {s: i for i, s in enumerate(syms)}
def ret4h(A, s):
    if s not in sidx: return None
    m = (rts > A) & (rts <= A + 14400)
    if m.sum() != 48: return None
    seg = ret5[m, sidx[s]]
    return float(np.prod(1.0 + np.where(np.isfinite(seg), seg, 0.0)) - 1.0) if np.isfinite(seg).any() else None
# ── average-cost basis walk (cash engine v5 semantics), producing per-anchor snapshots with unrealised P&L ──
pos = collections.defaultdict(float); avg = collections.defaultdict(float); known = collections.defaultdict(lambda: True); fi = 0
def apply_fill(r):
    s = r["symbol"]; px = float(r["fill_px"]); q = float(r["fill_notional"]) / px * (1.0 if str(r.get("side", "")).upper() == "BUY" else -1.0); p0 = pos[s]
    if p0 == 0 or (p0 > 0) == (q > 0): avg[s] = (abs(p0) * avg[s] + abs(q) * px) / max(abs(p0) + abs(q), 1e-12)
    elif abs(q) > abs(p0): avg[s] = px
    pos[s] = p0 + q
    if abs(pos[s]) < 1e-12: avg[s] = 0.0; known[s] = True
snapshots = []
for A in anchors:
    while fi < len(fills) and float(fills[fi]["fill_ts"]) <= A + 3600: apply_fill(fills[fi]); fi += 1
    pn, pu, pe, unk = {}, {}, {}, []
    for s, r in snaps[A].items():
        q = float(r["venue_position_qty"]); v = float(r["venue_position_notional"])
        if abs(q) < 1e-12: continue
        mark = abs(v) / abs(q); pn[s] = v
        if abs(pos[s] - q) * mark > 1.0: pos[s] = q; known[s] = False       # venue re-seat ⇒ basis unknown until flat
        if known[s] and avg[s] > 0: pu[s] = (mark - avg[s]) * q; pe[s] = abs(avg[s] * q)
        else: unk.append(s)
    snapshots.append((A, {"positions_notional": pn, "positions_unrealized": pu, "positions_entry_notional": pe}, unk))
# ── the three specifications ──
def run(spec):
    conf = dict(conf0); state = {"counters": {}, "stopped": {}, "cooldown": {}}; events = []
    if spec == "V2": conf["consecutive_anchors"] = 1
    for A, snap, unk in snapshots:
        sn = dict(snap)
        if spec == "V1":   # entry-basis denominator: feed a notional dict whose magnitude is the ENTRY notional so evaluate()'s depth = unreal/|entry|
            sn = {"positions_notional": {s: (snap["positions_entry_notional"][s] if s in snap["positions_entry_notional"] else v) for s, v in snap["positions_notional"].items()}, "positions_unrealized": snap["positions_unrealized"]}
        before = set(state["stopped"]); state, ev = PNS.evaluate(sn, state, conf, A + 3600)
        for s in set(state["stopped"]) - before:
            side = 1.0 if float(snap["positions_notional"].get(s, 0.0)) > 0 else -1.0
            rets = [ret4h(A + 14400 * k, s) for k in range(1, 19)]; rets = [x for x in rets if x is not None]
            path = float(np.prod([1 + x for x in rets]) - 1.0) if rets else None
            events.append({"symbol": s, "anchor": A, "utc": U(A), "side": "long" if side > 0 else "short", "depth": (snap["positions_unrealized"].get(s, 0.0) / abs(snap["positions_notional"].get(s, 1e-9))), "notional": abs(snap["positions_notional"].get(s, 0.0)), "next3d_price_return": path, "avoided_pnl_usdt": (None if path is None else -side * path * abs(snap["positions_notional"].get(s, 0.0)))})
    return events
out = {"device": "pc3_stop_counterfactual.py", "utc": time.strftime("%FT%TZ", time.gmtime()), "window": [days[0], days[-1]], "n_anchors": len(anchors), "conf_production": {k: conf0.get(k) for k in ("depth_pct", "consecutive_anchors", "cooloff_days", "min_notional_usdt")}, "unknown_basis_names_per_anchor_mean": float(np.mean([len(u) for _, _, u in snapshots])), "specs": {}}
for spec in ("V0", "V1", "V2"):
    ev = run(spec); pr = [e for e in ev if e["avoided_pnl_usdt"] is not None]
    out["specs"][spec] = {"n_stops": len(ev), "n_priced": len(pr), "avoided_pnl_sum_usdt": float(sum(e["avoided_pnl_usdt"] for e in pr)), "avoided_pnl_median_usdt": (float(np.median([e["avoided_pnl_usdt"] for e in pr])) if pr else None), "frac_stops_that_helped": (float(np.mean([e["avoided_pnl_usdt"] > 0 for e in pr])) if pr else None), "by_side": dict(collections.Counter(e["side"] for e in ev)), "events": ev}
json.dump(out, open(OUT, "w"), indent=1, default=str)
print("window", out["window"], "anchors", len(anchors), "| unknown-basis names/anchor", round(out["unknown_basis_names_per_anchor_mean"], 1))
for spec, v in out["specs"].items(): print(f"{spec}: stops {v['n_stops']} (priced {v['n_priced']}) | avoided P&L over next 3 d: sum {v['avoided_pnl_sum_usdt']:+.0f} USDT, median {v['avoided_pnl_median_usdt']}, helped {v['frac_stops_that_helped']} | sides {v['by_side']}")
print("V0 events:", [(e["utc"], e["symbol"], e["side"], round(e["depth"], 3), round(e["avoided_pnl_usdt"] or 0)) for e in out["specs"]["V0"]["events"]][:14])
