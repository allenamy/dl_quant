#!/usr/bin/env python3
"""FP3 P-C1 v1 (2026-09-18): replay the EXECUTOR's book layer for one anchor as a pure function and compare, per request, with what the executor recorded.
Same code (imported, not rewritten): scheduler.anchor_loop.apply_withhold_and_reshape (POP → RESHAPE → CLAMP), live.binance_executor.RebalanceExecutor.plan
(deltas → min-notional → lot rounding → side), SymbolFilters.round_qty, external_book.below_min_notional. Inputs are the DECISION-TIME records only (DESIGN v3 §1):
phase_A line (sizing.gross, untradable_names/reason, venue_cap_clamp), target_live/<A>.json (+ external_book.gross_norm), previous post_anchor readback (notional +
contracts), orders rows' mid_at_anchor. Acceptance: for every symbol the executor recorded, plan qty (step-rounded) == request_ledger[0].qty, side ==, skip reason ==.
Read-only. usage: pc1_intent_replay.py <nominal_anchor_ts> <out.json>"""
import sys, os, json, time, types, collections
A = int(sys.argv[1]); OUT = sys.argv[2]; REPO = os.path.expanduser("~/dl_quant_live"); WS = os.path.expanduser("~/wide_shadow"); P = f"{REPO}/state/live/pilot_log"
sys.path.insert(0, REPO)
import scheduler.anchor_loop as AL                      # brings live/, signal/ onto sys.path and imports EXT/LG/PNS itself
from live import binance_executor as BX
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t))); day = time.strftime("%Y%m%d", time.gmtime(A)); prev_day = time.strftime("%Y%m%d", time.gmtime(A - 14400))
rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
# ── decision-time records ──
pa = None
for l in open(f"{REPO}/state/anchor_runs.log"):
    if " phase_A: " in l:
        d = json.loads(l.split(" phase_A: ", 1)[1])
        if int(d.get("anchor_ts") or 0) == A or (d.get("external_wait") or {}).get("nominal_anchor_ts") == A: pa = d
assert pa, "no phase_A record"; rid = pa["rebalance_id"]; sz = pa["sizing"]; G = float(sz["gross"]); eq_pre = sz["nav"]
an = [r for r in rows(day, "anchors") if r.get("rebalance_id") == rid]; assert an, "no anchors row"; an = an[-1]; eb = an["external_book"]; gross_norm = float(eb["gross_norm"])
tgt_file = json.load(open(f"{WS}/state/target_live/{A}.json")); assert int(tgt_file["anchor_ts"]) == A
target = {s: float(w) / gross_norm * G for s, w in tgt_file["weights"].items()}                     # w / gross_norm × NAV × gross_mult (anchor_loop L1870 + _size_book)
od = [r for r in rows(day, "orders") if r.get("rebalance_id") == rid]; first = {}
for r in sorted(od, key=lambda r: (r["symbol"], int(r.get("attempt_idx") or 0))): first.setdefault(r["symbol"], r)
mids = {s: float(r["mid_at_anchor"]) for s, r in first.items() if r.get("mid_at_anchor")}
rb_prev = [r for r in rows(prev_day, "position_readback") + rows(day, "position_readback") if (A - 14400) <= float(r["anchor_ts"]) < A and r.get("source", "").endswith("@post_anchor")]
held = {r["symbol"]: float(r["venue_position_notional"]) for r in rb_prev}; held_qty = {r["symbol"]: float(r["venue_position_qty"]) for r in rb_prev}
untr = set(pa.get("untradable_names") or []) | set(eb.get("held_exit") or []) | set((eb.get("meta_excluded") or {}).keys() if isinstance(eb.get("meta_excluded"), dict) else (eb.get("meta_excluded") or [])); reasons = pa.get("untradable_reason") or {}
force_flat = set(s for s, why in (reasons.items() if isinstance(reasons, dict) else []) if "per_name_stop" in str(why) and "cooldown" not in str(why))
pns_state = json.load(open(f"{REPO}/state/live/per_name_stop.json")) if os.path.exists(f"{REPO}/state/live/per_name_stop.json") else {}
_cool_s = float((pns_state.get("cfg") or {}).get("cooloff_days") or 7) * 86400.0                        # cooloff length (per_name_stop.py: cooloff_days default 7)
cooldown_active = set(s for s, until in (pns_state.get("cooldown") or {}).items() if (float(until) - _cool_s) <= A < float(until))   # active at A iff set (= until − cooloff) ≤ A < until: valid for past anchors as long as entries are not overwritten
stopped_now = set((pns_state.get("stopped") or {}).keys()); untr |= cooldown_active; force_flat |= stopped_now
# ── filters (offline, from the executor's own cache) ──
sf = BX.SymbolFilters.__new__(BX.SymbolFilters); sf.f = json.load(open(f"{REPO}/state/live/exchange_info_cache.json")); sf.cache_path = None
fl = {s: float((sf.f.get(s) or {}).get("min_notional", 0.0) or 0.0) for s in target}
tradable = set((pa.get("universe") or {}).get("tradable") or []); gate_out = set(s for s in target if tradable and s not in tradable); untr |= gate_out
dust = AL.EXT.below_min_notional(target, fl, float(eb.get("min_notional_mult") or 2.0)); untr |= set(dust["names"])
# ── same-code book layer: POP → RESHAPE → CLAMP ──
G_norm0 = float(an["target_gross"]); held_rec = {s: float(r["prev_w"]) * G_norm0 for s, r in first.items()}   # executor's decision-time positions (state.positions) as it recorded them
clamp, rs = AL.apply_withhold_and_reshape(target, held_rec, untr, G, floors_usdt=fl, floors_source="exchange_info_cache", force_flat=force_flat)
capd = pa.get("venue_cap_clamp") or {}; reduce_only = set(clamp.get("reduced") or ()) | set(clamp.get("flatten_only") or ()) | set(capd.get("reduce_only_syms") or [])
# venue max-notional cap (anchor_loop L2323, after the withhold clamp): apply the RECORDED per-name cap from phase_A (the venue bracket at decision time); replicating
# the bracket lookup itself needs the leverage-bracket snapshot, which is not archived per anchor ⇒ the record is the decision-time source, labelled as such
_capped = capd.get("capped") or {}; cap_applied = {}
_items = _capped.items() if isinstance(_capped, dict) else [(x.get("symbol"), x) for x in _capped if isinstance(x, dict)]
for s_, info in _items:
    if s_ in target and isinstance(info, dict):
        capv = info.get("cap") or info.get("cap_usdt") or info.get("max_notional") or info.get("capped_to")
        _margin = float(capd.get("margin") or 0.0); _lim = float(capv) * (1.0 - _margin) if capv is not None else None            # anchor_loop venue cap: reduce_to_cap ⇒ cap × (1 − margin)
        if _lim is not None and abs(target[s_]) > _lim:
            cap_applied[s_] = {"before": target[s_], "cap": float(capv), "margin": _margin, "after": _lim, "recorded_after": info.get("target_after"), "rule_matches_record": (info.get("target_after") is None or abs(float(info["target_after"]) - _lim) <= 1e-6)}
            target[s_] = _lim * (1.0 if target[s_] > 0 else -1.0)
    elif s_ in target and isinstance(info, (int, float)) and abs(target[s_]) > float(info): cap_applied[s_] = (target[s_], float(info)); target[s_] = float(info) * (1.0 if target[s_] > 0 else -1.0)
stub = types.SimpleNamespace(filters=sf, band_bps=BX.DEFAULT_BAND_BPS)
plans_A = BX.RebalanceExecutor.plan(stub, target, held_rec, mids, reduce_only_syms=reduce_only, held_qty=held_qty)                 # end-to-end (my inputs)
G_norm = float(an["target_gross"])                                   # Σ|target| at plan time (after withhold/cap clamp) = the gross plan() normalised target_w / prev_w by
rec_target = {s: float(r["target_w"]) * G_norm for s, r in first.items()}; rec_prev = {s: float(r["prev_w"]) * G_norm for s, r in first.items()}   # the executor's OWN post-reshape target and pre-trade notional (orders rows: target_w = tgt/gross, prev_w = cur/gross, gross = Σ|target| = sizing gross)
ro_rec = set(s for s, r in first.items() if r.get("reduce_only"))
plans_B = BX.RebalanceExecutor.plan(stub, rec_target, rec_prev, mids, reduce_only_syms=(ro_rec or reduce_only), held_qty=held_qty)    # stage B: plan() on recorded inputs ⇒ isolates delta→qty fidelity
plan_by = {p["symbol"]: p for p in plans_B}
# stage A: book layer fidelity per name (replayed target after POP→RESHAPE→CLAMP vs recorded)
stageA = []
for s_ in sorted(set(rec_target) | set(target)):
    t_rep = float(target.get(s_, 0.0)); t_rec = rec_target.get(s_); stp = (sf.f.get(s_) or {}).get("step"); tol = (float(stp) * mids[s_]) if (stp and s_ in mids) else 1.0
    stageA.append({"symbol": s_, "replayed": t_rep, "recorded": t_rec, "diff": (None if t_rec is None else t_rep - t_rec), "within_step": (None if t_rec is None else abs(t_rep - t_rec) <= tol)})
capd_rec = pa.get("venue_cap_clamp") or {}
for e in stageA:
    if e["within_step"] is False: e["in_venue_cap_clamp"] = any(e["symbol"] in (capd_rec.get(k) or []) if isinstance(capd_rec.get(k), (list, dict)) else False for k in capd_rec)
A_ok = sum(1 for e in stageA if e["within_step"]); A_n = sum(1 for e in stageA if e["recorded"] is not None); A_max = max((abs(e["diff"]) for e in stageA if e["diff"] is not None), default=0.0)
prev_cmp = [(s_, held.get(s_, 0.0), rec_prev[s_]) for s_ in rec_prev]; prev_maxdiff = max((abs(a_ - b_) for _, a_, b_ in prev_cmp), default=0.0); prev_n_off = sum(1 for _, a_, b_ in prev_cmp if abs(a_ - b_) > 1.0)
# ── per-request comparison ──
cmp = []; cat = collections.Counter()
for s in sorted(set(first) | set(plan_by)):
    o = first.get(s); p = plan_by.get(s); e = {"symbol": s}
    if o is None: e["case"] = "plan_only"; e["plan"] = p.get("skip") or p.get("qty"); cat["plan_only:" + str(p.get("skip") or "qty")] += 1; cmp.append(e); continue
    if p is None: e["case"] = "order_only"; e["order"] = o.get("terminal_reason"); cat["order_only:" + str(o.get("terminal_reason"))] += 1; cmp.append(e); continue
    rl = (o.get("request_ledger") or [{}])[0]; oq = rl.get("qty"); oside = o.get("side"); oterm = o.get("terminal_reason"); oq_src = "request_ledger.qty"
    if oq is None:
        for k in ("qty", "requested_qty", "order_qty"):
            if o.get(k) is not None: oq = o.get(k); oq_src = "order_row." + k; break
    if p.get("skip"):
        ok = (oterm == p["skip"]) or (p["skip"] == "skipped_min_notional" and oterm == "skipped_min_notional")
        e.update(case="skip", plan_skip=p["skip"], order_terminal=oterm, match=bool(ok)); cat[("skip_match" if ok else "skip_MISMATCH") + ":" + str(oterm)] += 1
    else:
        pq = abs(float(p["qty"])); pside = p["side"]; oqf = abs(float(oq)) if oq is not None else None
        if oqf is None and o.get("intended_notional") is not None:                                   # −5022 post-only rejects carry no request ledger: the recorded intent is intended_notional
            oi = float(o["intended_notional"]); pi = float(p["delta_notional"]); ok = abs(pi - oi) <= 1e-6 * max(1.0, abs(oi)) and str(oside).lower() == pside
            e.update(case="request", plan_qty=pq, plan_side=pside, order_qty=None, order_qty_source="intended_notional", order_side=oside, order_terminal=oterm, match=bool(ok), plan_notional=pi, order_intended=oi)
            cat[("intent_match" if ok else "intent_MISMATCH") + ":" + str(oterm)] += 1; cmp.append(e); continue
        ok = (oqf is not None and abs(pq - oqf) <= 1e-9 and str(oside).lower() == pside)
        e.update(case="request", plan_qty=pq, plan_side=pside, order_qty=oqf, order_qty_source=oq_src, order_side=oside, order_terminal=oterm, match=bool(ok), qty_diff=(None if oqf is None else pq - oqf), plan_notional=abs(float(p["delta_notional"])), order_intended=o.get("intended_notional"))
        cat[("qty_match" if ok else ("qty_MISMATCH" if oqf is not None else "qty_MISSING")) + (":" + oterm if not ok else "")] += 1
    cmp.append(e)
n_req = sum(1 for e in cmp if e.get("case") == "request"); n_ok = sum(1 for e in cmp if e.get("case") == "request" and e.get("match")); stageA_off = [e for e in stageA if e["within_step"] is False]
out = {"device": "pc1_intent_replay.py", "version": "v7", "utc": time.strftime("%FT%TZ", time.gmtime()), "anchor": A, "utc_anchor": U(A), "rebalance_id": rid, "executor_tree": "409ea16", "inputs": {"eq_pre_from_phase_A": eq_pre, "sizing_gross": G, "gross_norm": gross_norm, "n_target": len(tgt_file["weights"]), "n_held_prev_readback": len(held), "n_untradable_phaseA": len(pa.get("untradable_names") or []), "dust": dust, "force_flat": sorted(force_flat), "n_mids": len(mids), "reduce_only_n": len(reduce_only)},
       "reshape_report": {k: v for k, v in (rs or {}).items() if k in ("net_before", "net_after", "gross_before", "gross_after", "names_crossed_floor", "n_pop", "max_name_delta_pp")}, "clamp_counts": {k: len(v) for k, v in clamp.items() if hasattr(v, "__len__")}, "venue_cap_applied_from_record": cap_applied,
       "recorded_reshape": an.get("reshape"), "stage_A_book_layer": {"n": A_n, "within_step": A_ok, "max_abs_diff_usdt": A_max, "rows": [e for e in stageA if e["within_step"] is False][:40]}, "prev_notional_check": {"my_readback_vs_recorded_prev_w": {"n": len(prev_cmp), "n_off_gt_1usdt": prev_n_off, "max_abs_diff_usdt": prev_maxdiff}}, "summary": {"n_symbols_compared": len(cmp), "n_requests": n_req, "n_requests_exact": n_ok, "categories": dict(cat)}, "rows": cmp}
json.dump(out, open(OUT, "w"), indent=1, default=str)
print("P-C1", U(A), rid, "| eq_pre", eq_pre, "gross", G, "G_norm(target_gross)", float(an["target_gross"]), "| targets", len(tgt_file["weights"]), "held", len(held), "untradable", len(untr), "gate_out", len(gate_out), "cooldown", len(cooldown_active), "dust", dust["n"], "force_flat", len(force_flat), "| pops", (rs or {}).get("n_pop"), "clamp", {k: len(v) for k, v in clamp.items() if hasattr(v, "__len__")})
print("reshape replay:", out["reshape_report"]); print("reshape recorded:", {k: an.get("reshape", {}).get(k) for k in ("net_before", "net_after", "gross_before", "gross_after", "max_name_delta_pp")})
print("stage A book layer (replayed post-reshape target vs recorded target_w×G): within step %d / %d, max |diff| %.2f USDT | off:" % (A_ok, A_n, A_max), [(e["symbol"], round(e["replayed"], 2), round(e["recorded"], 2), e.get("in_venue_cap_clamp")) for e in stageA_off][:5], "| venue_cap_clamp keys:", list(capd_rec.keys())[:8]); print("prev notional: my 00Z readback vs recorded prev_w×G: off>1 USDT %d / %d, max %.2f" % (prev_n_off, len(prev_cmp), prev_maxdiff)); print("stage B plan() on RECORDED (target, prev):", out["summary"])
mm = [e for e in cmp if e.get("case") == "request" and not e.get("match")][:8]; print("first mismatches:", [(e["symbol"], e.get("plan_qty"), e.get("order_qty"), e.get("plan_side"), e.get("order_side"), e.get("order_terminal")) for e in mm])
sk = [e for e in cmp if e.get("case") == "skip" and not e.get("match")][:6]; print("skip mismatches:", [(e["symbol"], e.get("plan_skip"), e.get("order_terminal")) for e in sk])
