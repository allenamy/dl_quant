#!/usr/bin/env python3
"""pnl_path.py — event-path PRICE P&L engine shared by P-C2 v3 and the live page (independent review round 11, R11-PC2 a/b/c, R11-PAGE 6).

WHY (the three v2 errors it replaces): (a) post-anchor positions were multiplied by the return from the anchor start, so the price move BEFORE a fill
was credited to the actual layer (buy 10 intended at 100, filled at 110, end 120: truth −100 vs intent, v2 said +20); (b) a protective flatten inside
the window was only labelled, the actual path was not cut to zero at it; (c) L2 deleted names whose order was skipped, i.e. "no incremental order"
was read as "no position".

OBJECTS
  Panel        the producer's 5-minute panel (~/wide_shadow/state/rolling.npz, channel 0 = ret5 = simple return of the bar ENDING at ts, i.e. over
               (ts−300, ts]; symbols from fea171/xfer_syms.npz). Prices are an INDEX per symbol: p(b) = Π(1+ret5) over rows in (b_ref, b]; an absolute
               price needs one reference (b_ref, px_ref). Every 5-minute row between the reference and the window end must be finite, else the name
               is CENSORED for that window (never priced as 0).
  qty path     piecewise-constant contract quantity: starts at q0 (a readback) and changes at EVENTS placed on the 5-minute boundary that contains
               the event time (ceil to 300 s): fills (signed qty = fill_notional / fill_px, deduplicated by (symbol, trade_id)) and flatten readbacks
               (set to 0). Placing a fill at the boundary end means it is valued at the boundary price, not its own fill price: recorded per fill as
               fill_px_vs_path_dev (relative) and counted as intra_row_approx — an approximation, stated, not hidden.
  segment P&L  Σ_k q(b_{k−1}→b_k) × (px(b_k) − px(b_{k−1})) over the window boundaries — the cash identity of a position path at 5-minute resolution.
Fees and funding are NOT price P&L and are never mixed in here.
Read-only. Env overrides for tests: FP3_LIVE_REPO (default ~/dl_quant_live), FP3_WS (default ~/wide_shadow)."""
import os, json, time, math, hashlib, collections
import numpy as np

ROW = 300
REPO = os.environ.get("FP3_LIVE_REPO") or os.path.expanduser("~/dl_quant_live")
WS = os.environ.get("FP3_WS") or os.path.expanduser("~/wide_shadow")
P = f"{REPO}/state/live/pilot_log"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def ceil_b(t):
    """the 5-minute boundary that CONTAINS instant t (the bar (b−300, b] with b ≥ t)"""
    return int(math.ceil(float(t) / ROW) * ROW)


def rows(day, name):
    f = f"{P}/{day}/{name}.jsonl"
    return [json.loads(l) for l in open(f) if l.strip()] if os.path.exists(f) else []


def day_of(t):
    return time.strftime("%Y%m%d", time.gmtime(float(t)))


class Panel:
    def __init__(self, ws=None):
        ws = ws or WS
        self.path = f"{ws}/state/rolling.npz"; self.syms_path = f"{ws}/fea171/xfer_syms.npz"
        R = np.load(self.path, allow_pickle=True)
        self.ts = R["ts"].astype(np.int64); self.ret = np.asarray(R["data"][:, :, 0], np.float64)
        self.syms = [str(x) for x in np.load(self.syms_path, allow_pickle=True)["symbols"]]
        assert len(self.syms) == self.ret.shape[1], (len(self.syms), self.ret.shape)
        assert np.all(np.diff(self.ts) == ROW) and np.all(self.ts % ROW == 0), "panel ts must be a uniform 5-minute grid on 300 s multiples"
        self.sidx = {s: i for i, s in enumerate(self.syms)}; self.row = {int(t): i for i, t in enumerate(self.ts)}
        self.sha = sha(self.path); self.t_first = int(self.ts[0]); self.t_last = int(self.ts[-1])

    def has(self, sym):
        return sym in self.sidx

    def index(self, sym, b_ref, b_lo, b_hi):
        """{boundary: p} for every boundary b in [b_lo, b_hi] (step 300), with p(b_ref) = 1 — or None when any row in (min(b_ref,b_lo), max(b_ref,b_hi)] is
        absent from the panel or non-finite for sym (CENSORED)."""
        if sym not in self.sidx or b_lo > b_hi:
            return None
        lo = min(b_ref, b_lo); hi = max(b_ref, b_hi)
        need = list(range(lo + ROW, hi + ROW, ROW))
        if not need:
            return {b_lo: 1.0}
        try:
            idx = [self.row[b] for b in need]
        except KeyError:
            return None
        r = self.ret[idx, self.sidx[sym]]
        if not np.all(np.isfinite(r)):
            return None
        cum = np.concatenate([[1.0], np.cumprod(1.0 + r)])          # cum[k] = Π over rows lo+ROW .. lo+k·ROW  ⇒ value at boundary lo + k·ROW relative to lo
        at = {lo + k * ROW: cum[k] for k in range(len(cum))}
        base = at[b_ref]
        return {b: at[b] / base for b in range(b_lo, b_hi + ROW, ROW)}


def qty_path(q0, events, t_d, b_lo, b_hi):
    """events: list of (boundary, kind, value, event_time) with kind 'fill' (signed delta) or 'set' (absolute); at one boundary fills apply first, then
    set (a flatten readback is written after its own fills). Two quantities are distinguished:
      q_dec    the quantity AT THE DECISION TIME t_d = q0 after every event with event_time < t_d (a pre-window flatten is a real 0) — the base the
               executor's request increments are added to (L1 hold / L2);
      q_start  the quantity the PRICING starts from at b_lo = q_dec plus the events with event_time ≥ t_d that land on the first boundary b_lo
               (a fill executed at the window's first price is a perfect execution of the intent, not a pre-existing position).
    Returns (q_dec, q_start, {boundary: q after events at that boundary} for b_lo < b ≤ b_hi, n_pre, n_in, n_post)."""
    ev = sorted(events, key=lambda e: (e[0], 0 if e[1] == "fill" else 1, e[3]))
    q_dec = float(q0); n_pre = 0
    for b, kind, v, t in ev:
        if t < t_d:
            q_dec = q_dec + float(v) if kind == "fill" else float(v); n_pre += 1
    q = q_dec; n_in = n_post = 0; path = {}
    for b, kind, v, t in ev:
        if t < t_d:
            continue
        bb = max(b, b_lo)
        if bb > b_hi:
            n_post += 1; continue
        n_in += 1; q = q + float(v) if kind == "fill" else float(v)
        if bb > b_lo:
            path[bb] = q
    q_start = q_dec
    for b, kind, v, t in ev:
        if t >= t_d and max(b, b_lo) == b_lo:
            q_start = q_start + float(v) if kind == "fill" else float(v)
    return q_dec, q_start, path, n_pre, n_in, n_post


def segment_pnl(q_start, path, px, b_lo, b_hi):
    """cash identity over boundaries b_lo..b_hi: Σ q(before b_k) × (px[b_k] − px[b_{k−1}])"""
    q = q_start; pnl = 0.0; prev = px[b_lo]
    for b in range(b_lo + ROW, b_hi + ROW, ROW):
        pnl += q * (px[b] - prev); prev = px[b]
        if b in path:
            q = path[b]
    return pnl, q


class LedgerDay:
    """the executor's ledgers around one UTC day (previous / this / next day files), read once"""
    def __init__(self, day):
        self.day = day; d0 = int(time.mktime(time.strptime(day, "%Y%m%d")) - time.timezone); self.d0 = d0
        prv = day_of(d0 - 86400); nxt = day_of(d0 + 86400)
        self.rb = rows(prv, "position_readback") + rows(day, "position_readback") + rows(nxt, "position_readback")
        self.od = rows(prv, "orders") + rows(day, "orders") + rows(nxt, "orders")
        self.an = rows(prv, "anchors") + rows(day, "anchors") + rows(nxt, "anchors")
        fl = rows(prv, "fills") + rows(day, "fills") + rows(nxt, "fills"); seen = {}
        for r in fl:
            seen[(r["symbol"], r.get("trade_id"))] = r                          # dedupe by (symbol, trade_id): a trade id is per symbol at the venue
        self.fills = sorted(seen.values(), key=lambda r: float(r["fill_ts"]))
        self.pa = {}
        for l in open(f"{REPO}/state/anchor_runs.log"):
            if " phase_A: " in l:
                try:
                    d = json.loads(l.split(" phase_A: ", 1)[1]); a = (d.get("external_wait") or {}).get("nominal_anchor_ts") or d.get("anchor_ts")
                    if a: self.pa[int(a)] = d
                except Exception:
                    pass

    def post_anchor_read(self, A):
        """the post_anchor readback of the run labelled A (run start in [A, A+4h)): {symbol: row}; read_ts is the cross-section"""
        snap = {}
        for r in self.rb:
            if A <= float(r["anchor_ts"]) < A + 14400 and str(r.get("source", "")).endswith("@post_anchor"):
                snap[r["symbol"]] = r
        return snap

    def latest_read_before(self, t, max_age=8 * 3600.0):
        """per symbol the LATEST post_anchor readback row with read_ts < t (a skipped run means the reference is one run older; beyond max_age the
        reference is flagged stale, never silently zero): {symbol: row}"""
        snap = {}
        for r in self.rb:
            rt = float(r["read_ts"])
            if rt < t and rt >= t - max_age and str(r.get("source", "")).endswith("@post_anchor"):
                cur = snap.get(r["symbol"])
                if cur is None or rt > float(cur["read_ts"]): snap[r["symbol"]] = r
        return snap

    def earliest_read_after(self, t, max_age=8 * 3600.0):
        """per symbol the EARLIEST post_anchor readback row with read_ts > t within max_age: {symbol: row} (empty ⇒ no readback to check against)"""
        snap = {}
        for r in self.rb:
            rt = float(r["read_ts"])
            if rt > t and rt <= t + max_age and str(r.get("source", "")).endswith("@post_anchor"):
                cur = snap.get(r["symbol"])
                if cur is None or rt < float(cur["read_ts"]): snap[r["symbol"]] = r
        return snap

    def flattens(self, t_lo, t_hi):
        return [r for r in self.rb if "flatten" in str(r.get("source", "")) and t_lo < float(r["read_ts"]) <= t_hi]


def window_pnl(L, panel, A, window_end=None):
    """Event-path price P&L of the four layers for the run labelled A (nominal 4h anchor). Returns a dict (status ≠ OK when decision-time records are
    missing). Window = [t_d, A+4h] with t_d = earliest submit_ts of the rebalance (fallback A + 24 min); boundaries b0 = ceil(t_d), b1 = ceil(A+4h)."""
    d = L.pa.get(A); rec = {"anchor": A, "utc": time.strftime("%m-%d %H:%MZ", time.gmtime(A))}
    if not d or not (d.get("sizing") or {}).get("gross"):
        rec["status"] = "NO_PHASE_A"; return rec
    rid = d["rebalance_id"]; G = float(d["sizing"]["gross"])
    anr = [r for r in L.an if r.get("rebalance_id") == rid]
    if not anr:
        rec["status"] = "NO_ANCHORS_ROW"; return rec
    anr = anr[-1]; gn = float(anr["external_book"]["gross_norm"]); Gt = float(anr["target_gross"])
    oa = [r for r in L.od if r.get("rebalance_id") == rid]; first = {}
    for r in sorted(oa, key=lambda r: (r["symbol"], int(r.get("attempt_idx") or 0))):
        first.setdefault(r["symbol"], r)
    subs = [float(r["submit_ts"]) for r in oa if r.get("submit_ts")]
    t_d = min(subs) if subs else A + 1440.0; t_end = float(window_end if window_end is not None else A + 14400)
    b0 = ceil_b(t_d); b1 = ceil_b(t_end)
    if b1 <= b0:
        rec["status"] = "EMPTY_WINDOW"; return rec
    if b1 > panel.t_last:
        rec["status"] = "PANEL_NOT_YET_COVERING"; rec["panel_last"] = panel.t_last; return rec
    tf = f"{WS}/state/target_live/{A}.json"
    L0n = {s: float(w) / gn * G for s, w in json.load(open(tf))["weights"].items()} if os.path.exists(tf) else None
    prev = L.latest_read_before(t_d); nxt = L.earliest_read_after(t_end)
    # the reference snapshot: per symbol the latest readback before the decision (one run older when a run was skipped; > 4h40m ⇒ stale flag)
    t_prev_read = min((float(r["read_ts"]) for r in prev.values()), default=A - 14400 + 1440.0)
    t_next_read = max((float(r["read_ts"]) for r in nxt.values()), default=t_end + 2700.0)
    prev_runs = sorted({int(float(r["anchor_ts"]) // 14400 * 14400) for r in prev.values()})
    n_stale = sum(1 for r in prev.values() if t_d - float(r["read_ts"]) > 4 * 3600 + 40 * 60)
    # events per symbol: fills and flatten readbacks after THAT SYMBOL's reference readback (names without one: after the snapshot's earliest read)
    ev = collections.defaultdict(list); fill_dev = []; fees = collections.defaultdict(float); n_fills = 0
    t_ref_of = lambda s: float(prev[s]["read_ts"]) if s in prev else t_prev_read
    for r in L.fills:
        t = float(r["fill_ts"]); s = r["symbol"]
        if t <= t_ref_of(s) or t > max(t_end + 14400, t_next_read):
            continue
        q = float(r["fill_notional"]) / float(r["fill_px"]); q = q if str(r.get("side", "")).lower() == "buy" else -q
        ev[s].append((ceil_b(t), "fill", q, t, float(r["fill_px"])))
        if t_d <= t <= t_end:
            n_fills += 1; fees[str(r.get("commission_asset"))] += float(r.get("commission") or 0.0)
    flats = L.flattens(t_prev_read, max(t_end, t_next_read))
    for r in flats:
        if float(r["read_ts"]) > t_ref_of(r["symbol"]):
            ev[r["symbol"]].append((ceil_b(float(r["read_ts"])), "set", float(r["venue_position_qty"] or 0.0), float(r["read_ts"]), None))
    syms = set(prev) | set(first) | set(L0n or {}) | set(ev)
    layers = {"L0_producer": {}, "L1_executor_target": {}, "L2_request_intent": {}, "L2_cut_at_flatten": {}, "L3_actual_path": {}}
    per = {}; cens = {k: {"n": 0, "notional": 0.0} for k in layers}; mid_dev = []; resid = []; n_intra = 0; n_pre = n_in = n_post = 0; n_cut = 0
    for s in sorted(syms):
        r0 = prev.get(s); q0 = float(r0["venue_position_qty"]) if r0 else 0.0
        # reference price: previous readback mark at its boundary; else the first fill; else the orders row mid at b0
        ref = None
        if r0 and q0:
            ref = (ceil_b(float(r0["read_ts"])), abs(float(r0["venue_position_notional"])) / abs(q0), "readback_mark")
        elif ev.get(s):
            f = sorted([e for e in ev[s] if e[1] == "fill"], key=lambda e: e[3])
            if f: ref = (f[0][0], f[0][4], "first_fill_px")
        if ref is None and first.get(s) and first[s].get("mid_at_anchor"):
            ref = (b0, float(first[s]["mid_at_anchor"]), "mid_at_anchor")
        px = panel.index(s, ref[0], min(ref[0], b0), b1) if ref else None
        if px is None:
            # censored for every layer; record the notional we could not price (intent notional / start notional)
            n_int = {"L0_producer": abs((L0n or {}).get(s, 0.0)), "L1_executor_target": abs(float(first[s]["target_w"]) * Gt) if first.get(s) else abs(float(r0["venue_position_notional"])) if r0 else 0.0,
                     "L2_request_intent": abs(float(r0["venue_position_notional"])) if r0 else abs(float(first[s].get("intended_notional") or 0.0)) if first.get(s) else 0.0,
                     "L3_actual_path": abs(float(r0["venue_position_notional"])) if r0 else 0.0}
            n_int["L2_cut_at_flatten"] = n_int["L2_request_intent"]
            for k in layers:
                cens[k]["n"] += 1; cens[k]["notional"] += n_int[k]
            per[s] = {"status": "CENSORED", "why": ("no_reference_price" if ref is None else "panel_rows_missing_or_nonfinite"), "q0": q0}
            continue
        px_abs = {b: ref[1] * p for b, p in px.items()}
        p0 = px_abs[b0]
        o = first.get(s); mid = float(o["mid_at_anchor"]) if o and o.get("mid_at_anchor") else None
        if mid: mid_dev.append((s, mid / p0 - 1.0))
        conv = mid if mid else p0                                                  # intent notionals → contracts at the executor's own mid (its request quantity semantics); fallback: path price
        qL0 = ((L0n or {}).get(s, 0.0)) / conv if L0n is not None else None
        # L3: the event path (q_start = the quantity AT THE DECISION BOUNDARY, i.e. after every event before it — a pre-window flatten is a real 0)
        evs = [(b, k, v, t) for (b, k, v, t, _p) in ev.get(s, [])]
        q_dec, q_start, path, a, b_, c = qty_path(q0, evs, t_d, b0, b1); n_pre += a; n_in += b_; n_post += c
        qL1 = (float(o["target_w"]) * Gt / conv) if o else q_dec                     # no orders row ⇒ the executor did not act on the name ⇒ hold what it had at decision time
        if o and o.get("side") and not str(o.get("terminal_reason", "")).startswith("skipped"):
            qL2 = q_dec + float(o.get("intended_notional") or 0.0) / conv               # placed request: decision-time quantity + the increment it asked for
        else:
            qL2 = q_dec                                                             # skipped or absent request: the position stays what it was
        for (b, k, v, t, fp) in ev.get(s, []):
            if k == "fill" and b0 < b <= b1:
                n_intra += 1
                if fp: fill_dev.append((s, fp / px_abs[b] - 1.0))
        pnl3, q_end = segment_pnl(q_start, path, px_abs, b0, b1)
        held = {"L0_producer": qL0, "L1_executor_target": qL1, "L2_request_intent": qL2}
        # the request intent CUT at this symbol's first in-window flatten: separates the flatten's footprint (L2cut − L2) from execution timing (L3 − L2cut)
        b_flat = min([max(b, b0) for (b, k, v, t, _p) in ev.get(s, []) if k == "set" and t >= t_d and max(b, b0) <= b1], default=None)
        if b_flat is not None: n_cut += 1
        out_s = {"status": "OK", "q0": q0, "q_dec": q_dec, "q_start": q_start, "q_end_path": q_end, "px_b0": p0, "px_b1": px_abs[b1], "ref": ref[2], "n_events_in": b_}
        for k, qk in held.items():
            if qk is None:
                layers[k][s] = None; continue
            layers[k][s] = {"qty": qk, "notional_b0": qk * p0, "pnl": qk * (px_abs[b1] - p0)}
        layers["L2_cut_at_flatten"][s] = {"qty": qL2, "notional_b0": qL2 * p0, "pnl": qL2 * (px_abs[b_flat if b_flat is not None else b1] - p0), "cut_at": b_flat}
        layers["L3_actual_path"][s] = {"qty": q_start, "notional_b0": q_start * p0, "pnl": pnl3, "qty_end": q_end}
        # consistency check against the NEXT post_anchor readback: continue the path with every event whose EVENT TIME ≤ that readback's read_ts
        # (the next rebalance's own fills happen before its readback, so they belong to the check, not to this window's pricing)
        rn = nxt.get(s)
        if nxt and (rn is not None or abs(q_end) > 0):
            t_chk = float(rn["read_ts"]) if rn is not None else t_next_read
            q_chk = q0
            for (b, k, v, t, _p) in sorted(ev.get(s, []), key=lambda e: (e[3], 0 if e[1] == "fill" else 1)):
                if t <= t_chk:
                    q_chk = q_chk + v if k == "fill" else v
            qn = float(rn["venue_position_qty"]) if rn is not None else 0.0; dq = q_chk - qn
            if abs(dq) > 0:
                resid.append((s, dq, dq * px_abs[b1]))
        per[s] = out_s
    summary = {}
    for k, Ls in layers.items():
        vals = [v for v in Ls.values() if v]
        summary[k] = {"n": len(Ls), "n_priced": len(vals), "gross_b0": float(sum(abs(v["notional_b0"]) for v in vals)), "net_b0": float(sum(v["notional_b0"] for v in vals)),
                      "pnl_usdt": float(sum(v["pnl"] for v in vals)), "censored": cens[k]}
    l3g = sum(abs(v["notional_b0"]) for v in layers["L3_actual_path"].values() if v)
    wclass = "FLATTEN" if n_cut else ("HALTED_FLAT_BOOK" if (not subs and n_fills == 0 and l3g == 0.0) else ("NO_FILLS" if n_fills == 0 else "NORMAL"))
    rec.update(status="OK", rebalance_id=rid, window_class=wclass, n_names_cut_at_flatten=n_cut, t_decision=t_d, t_decision_source=("min_submit_ts" if subs else "A+24min_fallback"), b0=b0, b1=b1, n_rows=(b1 - b0) // ROW,
               layers=summary, fees_in_window={k: v for k, v in fees.items()}, n_fills_in_window=n_fills, events={"pre_window": n_pre, "in_window": n_in, "post_window_not_applied": n_post},
               intra_row_approx=n_intra, flattens_in_window=sorted({time.strftime("%m-%d %H:%MZ", time.gmtime(float(r["read_ts"]))) for r in flats if t_d <= float(r["read_ts"]) <= t_end}),
               n_flatten_rows_in_window=sum(1 for r in flats if t_d <= float(r["read_ts"]) <= t_end),
               mid_vs_path_price={"n": len(mid_dev), "max_abs_rel": max((abs(x[1]) for x in mid_dev), default=None), "median_abs_rel": float(np.median([abs(x[1]) for x in mid_dev])) if mid_dev else None},
               fill_px_vs_path={"n": len(fill_dev), "max_abs_rel": max((abs(x[1]) for x in fill_dev), default=None), "median_abs_rel": float(np.median([abs(x[1]) for x in fill_dev])) if fill_dev else None},
               reference_readback={"runs": [time.strftime("%m-%d %HZ", time.gmtime(a)) for a in prev_runs], "n_names": len(prev), "n_stale_over_4h40m": n_stale, "t_earliest_read": t_prev_read},
               next_readback={"available": bool(nxt), "n_names": len(nxt), "t_latest_read": (t_next_read if nxt else None)},
               unexplained_qty_residual={"status": ("CHECKED" if nxt else "UNAVAILABLE_no_readback_after_window"), "n_names": len(resid), "n_over_1usdt": sum(1 for x in resid if abs(x[2]) > 1.0), "abs_notional_sum": float(sum(abs(x[2]) for x in resid)),
                                         "top": sorted([(s, round(dq, 6), round(v, 2)) for s, dq, v in resid], key=lambda x: -abs(x[2]))[:10], "next_readback_names": len(nxt),
                                         "rule": "path from the previous readback through every fill/flatten with event time <= the next readback's read_ts, minus that readback; priced at the window-end path price"},
               per_name=per, per_name_layers=layers)
    return rec


def layer_diffs(rec):
    L = rec["layers"]
    return {"L3_minus_L2_timing_and_fills": L["L3_actual_path"]["pnl_usdt"] - L["L2_request_intent"]["pnl_usdt"],
            "L3_minus_L2cut_execution": L["L3_actual_path"]["pnl_usdt"] - L["L2_cut_at_flatten"]["pnl_usdt"],
            "L2cut_minus_L2_flatten_footprint": L["L2_cut_at_flatten"]["pnl_usdt"] - L["L2_request_intent"]["pnl_usdt"],
            "L2_minus_L1_skips": L["L2_request_intent"]["pnl_usdt"] - L["L1_executor_target"]["pnl_usdt"],
            "L1_minus_L0_book_layer": L["L1_executor_target"]["pnl_usdt"] - L["L0_producer"]["pnl_usdt"],
            "L3_minus_L0_total": L["L3_actual_path"]["pnl_usdt"] - L["L0_producer"]["pnl_usdt"]}
