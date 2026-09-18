#!/usr/bin/env python3
"""pnl_path.py — event-path PRICE P&L engine shared by P-C2 v4 and the live page (independent review round 11 R11-PC2 a/b/c / R11-PAGE 6, round 12 R12-P2/P3/M1).

WHAT ROUND 12 CHANGED (each a reviewer counterexample that v3 passed):
  (i)   ONE event order. v3 sorted the pricing path by 5-minute boundary first ("fill before set" inside a boundary) while the quantity-consistency
        check walked real event time, so a flatten followed by a reopen in the SAME bar let the older flatten erase the reopen — mispriced path,
        zero residual. Both now use `ev_sorted` = strictly real event time (fills before sets only at an equal timestamp, because a flatten readback
        is written after its own fills). Reviewer's case (hold 10, sell 10 @105, readback 0, buy 5 @108 in one bar, next read 5): v3 end-qty 0 and
        P&L 100 with a CHECKED zero gap; v4 end-qty 5 and 150 on boundary prices, 110 once the recorded fill prices are applied.
  (ii)  FILL PRICES. Every event was valued at its boundary price. The per-fill correction signed_qty x (boundary_px - fill_px) is now computed from
        the fill prices already in the ledger and reported as its OWN column (`fill_price_correction_usdt`, `pnl_usdt_with_fill_prices`). It is not
        folded into the boundary figure: the two are printed side by side because the reviewer showed the approximation can flip a group's sign.
  (iii) PARTIAL FLATTENS. L2cut truncated the whole reference position at the first flatten/set without looking at what the set left standing
        (hold 10, flatten only 5 => v3 100, truth 150). The cut is now the set's ACTUAL ratio (new_qty / qty_before), applied successively.
  (iv)  DAY COVERAGE. The six windows run from anchor+~25min to the next anchor = 21.5 h, not 24 h. `gap_pnl` prices the carried position over each
        [anchor, decision] gap, so the ACTUAL layer can be reported for the whole day; the intent layers are defined per decision window and are
        NOT extended (stated, not hidden). Every record carries `coverage_s`.
  (v)   LONG/SHORT. The path P&L is split by the sign of the position IN EACH SEGMENT (`pnl_long` + `pnl_short` == `pnl`), so a round trip that
        starts and ends flat is no longer dropped from both legs.

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


def ev_sorted(events):
    """THE event order, used by the pricing path, the cut path and the residual check alike: real event time, and only at an equal timestamp a
    fill before a set (a flatten readback is written after the fills it reports). Accepts 4-, 5- or 6-tuples (b, kind, value, t[, fill_px[, trade_key]])."""
    return sorted(events, key=lambda e: (float(e[3]), 0 if e[1] == "fill" else 1))


def qty_path(q0, events, t_d, b_lo, b_hi):
    """events: list of (boundary, kind, value, event_time) with kind 'fill' (signed delta) or 'set' (absolute); at one boundary fills apply first, then
    set (a flatten readback is written after its own fills). Two quantities are distinguished:
      q_dec    the quantity AT THE DECISION TIME t_d = q0 after every event with event_time < t_d (a pre-window flatten is a real 0) — the base the
               executor's request increments are added to (L1 hold / L2);
      q_start  the quantity the PRICING starts from at b_lo = q_dec plus the events with event_time ≥ t_d that land on the first boundary b_lo
               (a fill executed at the window's first price is a perfect execution of the intent, not a pre-existing position).
    Events are applied in `ev_sorted` order (real event time) — round 12 R12-P2: the boundary-first order let a flatten erase a later reopen in the
    same bar. Two events in one boundary both write `path[b]`; the chronologically last one stands, which is the true quantity leaving that bar.
    Returns (q_dec, q_start, path, n_pre, n_in, n_post, cuts) where cuts = [(boundary, ratio, qty_entering_the_bar, qty_after)] for each in-window
    `set` (ratio = qty_after / qty_ENTERING_THE_BAR — the flatten's own fills sit in the same bar as the readback that reports the result, so the
    quantity immediately before the readback would make every partial flatten look like a no-op; None when a non-zero size is set onto a flat name)."""
    ev = ev_sorted(events)
    q_dec = float(q0); n_pre = 0
    for e in ev:
        b, kind, v, t = e[0], e[1], e[2], e[3]
        if t < t_d:
            q_dec = q_dec + float(v) if kind == "fill" else float(v); n_pre += 1
    q = q_dec; n_in = n_post = 0; path = {}; cuts = []; cur_bar = None; q_bar_start = q_dec
    for e in ev:
        b, kind, v, t = e[0], e[1], e[2], e[3]
        if t < t_d:
            continue
        bb = max(b, b_lo)
        if bb > b_hi:
            n_post += 1; continue
        if bb != cur_bar:
            cur_bar = bb; q_bar_start = q            # the quantity ENTERING this bar — the reference a `set` in this bar is measured against
        n_in += 1
        if kind == "fill":
            q = q + float(v)
        else:
            # A protective flatten is an EPISODE: its own sell fills and the readback that reports the result land in the same bar. Measuring the
            # set against the quantity immediately before the readback would call it a no-op (the fills already moved the position). The ratio is
            # therefore taken against the quantity entering the bar — R12-P2: a flatten of 5 out of 10 is a half cut, not a full one and not a no-op.
            nq = float(v)
            cuts.append((bb, (nq / q_bar_start if q_bar_start else (0.0 if nq == 0 else None)), q_bar_start, nq))
            q = nq
        if bb > b_lo:
            path[bb] = q
    q_start = q_dec
    for e in ev:
        b, kind, v, t = e[0], e[1], e[2], e[3]
        if t >= t_d and max(b, b_lo) == b_lo:
            q_start = q_start + float(v) if kind == "fill" else float(v)
    return q_dec, q_start, path, n_pre, n_in, n_post, cuts


def cut_path(q_intent, cuts, b_lo, b_hi):
    """The INTENT position scaled by what each in-window `set` actually left standing (round 12 R12-P2: v3 truncated the whole reference position at
    the first set, so a partial flatten of 5 out of 10 was priced as a full exit).

    ★ ROUND 13 R13-P2 (3): ONE ratio per BAR. Every `set` inside one 5-minute bar is measured against the SAME `q_bar_start` (the quantity entering
    that bar), so applying each ratio in turn squares the cut: a readback sequence 10 → 8 → 5 in one bar recorded ratios 0.8 and 0.5 and v4 produced
    0.8 × 0.5 = 0.4 ⇒ a reference position of 4 where the actual path leaves 5. The bar's composite ratio is the LAST set's outcome over the quantity
    entering the bar; the cuts list is built in `ev_sorted` order, so the last entry for a boundary is the chronologically last set in it.
    Returns (q_start_after_cuts_at_or_before_b_lo, {boundary: q})."""
    last_of_bar = {}
    for c in cuts:                                                     # built in event order ⇒ the final write per boundary is that bar's outcome
        last_of_bar[int(c[0])] = c
    q = float(q_intent); q_start = float(q_intent); path = {}
    for b in sorted(last_of_bar):
        (bb, ratio, qb, nq) = last_of_bar[b]
        q *= (1.0 if ratio is None else float(ratio))
        if b <= b_lo:
            q_start = q
        elif b <= b_hi:
            path[b] = q
    return q_start, path


def segment_pnl(q_start, path, px, b_lo, b_hi):
    """cash identity over boundaries b_lo..b_hi: Σ q(before b_k) × (px[b_k] − px[b_{k−1}]), split by the SIGN OF THE POSITION IN EACH SEGMENT
    (round 12 R12-M1: the page assigned a whole name by its start or end sign, so a round trip that begins and ends flat vanished from both legs).
    Returns (pnl, q_end, pnl_long, pnl_short) with pnl_long + pnl_short == pnl exactly."""
    q = q_start; pnl = pl = ps = 0.0; prev = px[b_lo]
    for b in range(b_lo + ROW, b_hi + ROW, ROW):
        seg = q * (px[b] - prev); pnl += seg
        if q > 0: pl += seg
        elif q < 0: ps += seg
        prev = px[b]
        if b in path:
            q = path[b]
    return pnl, q, pl, ps


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


def decision_time(L, A):
    """(t_d, source) for the run labelled A WITHOUT pricing anything — the day driver needs the gap [A, t_d) before it prices the window [t_d, A+4h],
    and the two must use the same instant (R13-P2 (1)/(2): one chronological chain, one fill partition)."""
    d = L.pa.get(A)
    if not d:
        return A + 1440.0, "A+24min_no_phase_A"
    rid = d.get("rebalance_id")
    subs = [float(r["submit_ts"]) for r in L.od if r.get("rebalance_id") == rid and r.get("submit_ts")]
    return (min(subs), "min_submit_ts") if subs else (A + 1440.0, "A+24min_fallback")


def window_pnl(L, panel, A, window_end=None, px_chain=None):
    """Event-path price P&L of the four layers for the run labelled A (nominal 4h anchor). Returns a dict (status ≠ OK when decision-time records are
    missing). Window = [t_d, A+4h] with t_d = earliest submit_ts of the rebalance (fallback A + 24 min); boundaries b0 = ceil(t_d), b1 = ceil(A+4h).

    ★ ROUND 13 R13-P2 (1) — ONE PRICE REFERENCE PER SYMBOL PER DAY. v4 re-derived a fresh reference in every window (that window's own readback mark,
    else its first fill, else mid_at_anchor) while `gap_pnl` chained off the previous window's END price, so the two sides of a join could disagree and
    the difference was booked nowhere: the reviewer's fixture ends a window at 120, starts the next at 132 holding 10, and 120 USDT of position value
    falls outside every explanation while the gap reports 0. On the real five days 5,010 name-joins differ by more than one cent.
      `px_chain` (dict symbol → {"b", "px", "source"}) is the day's carried reference, MUTATED IN PLACE by this function and by `gap_pnl`. When a symbol
      is in the chain and the panel can index from the chain boundary, the chain reference is used; the symbol's own would-be reference is still derived
      and the join difference is REPORTED (`price_chain_joins`) with a candidate cause — it is NEVER added to P&L, because a mark/close difference is not
      a realised gain. A reset is recorded whenever the chain cannot be used (`reset_reason`).
    ★ ROUND 13 R13-P2 (2) — HALF-OPEN FILL PARTITION. The gap owns (A, t_d) and the window owns [t_d, t_end]: a fill exactly at t_d used to be price-
    corrected on BOTH sides (the reviewer's buy 5 at t_d added its 100 correction twice). Both functions record the `(symbol, trade_id)` keys they
    corrected so the caller can assert the partition over the day's fill set."""
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
        ev[s].append((ceil_b(t), "fill", q, t, float(r["fill_px"]), (s, r.get("trade_id"))))
        if t_d <= t <= t_end:                                          # R13-P2 (2): the window owns [t_d, t_end]; the gap owns (A, t_d) — half-open, no overlap
            n_fills += 1; fees[str(r.get("commission_asset"))] += float(r.get("commission") or 0.0)
    flats = L.flattens(t_prev_read, max(t_end, t_next_read))
    for r in flats:
        if float(r["read_ts"]) > t_ref_of(r["symbol"]):
            ev[r["symbol"]].append((ceil_b(float(r["read_ts"])), "set", float(r["venue_position_qty"] or 0.0), float(r["read_ts"]), None, None))
    syms = set(prev) | set(first) | set(L0n or {}) | set(ev)
    layers = {"L0_producer": {}, "L1_executor_target": {}, "L2_request_intent": {}, "L2_cut_at_flatten": {}, "L3_actual_path": {}}
    per = {}; cens = {k: {"n": 0, "notional": 0.0} for k in layers}; mid_dev = []; resid = []; n_intra = 0; n_pre = n_in = n_post = 0; n_cut = 0
    fill_corr_total = 0.0; n_fp_corr = 0; corr_keys = []
    chain = px_chain if px_chain is not None else {}                  # R13-P2 (1): the day's carried price reference, mutated in place
    joins = []; n_reset = collections.Counter()
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
        own = ref                                                    # what this window would have chosen on its own (kept for the join report)
        ch = chain.get(s)
        if ch is not None and panel.index(s, int(ch["b"]), min(int(ch["b"]), b0), b1) is not None:
            ref = (int(ch["b"]), float(ch["px"]), "day_chain:" + str(ch.get("source", "")))
            if own is not None and own[0] != ref[0] or (own is not None and own[2] != ref[2]):
                pj = panel.index(s, own[0], min(own[0], b0), b1)
                if pj is not None:
                    px_own_b0 = own[1] * pj[b0]
                    pxi = panel.index(s, ref[0], min(ref[0], b0), b1)
                    px_chain_b0 = ref[1] * pxi[b0]
                    joins.append({"symbol": s, "px_chain_at_b0": px_chain_b0, "px_own_at_b0": px_own_b0, "own_source": own[2],
                                  "rel": (px_own_b0 / px_chain_b0 - 1.0) if px_chain_b0 else None, "qty_at_join": None, "value_diff_usdt": None,
                                  "cause": ("mark_vs_close" if own[2] == "readback_mark" else ("fill_px_vs_close" if own[2] == "first_fill_px" else "mid_vs_close"))})
        elif ch is not None:
            n_reset["chain_unusable_panel_gap"] += 1
        elif ref is not None:
            n_reset["new_symbol_in_day"] += 1
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
        evs = [(e[0], e[1], e[2], e[3]) for e in ev.get(s, [])]
        q_dec, q_start, path, a, b_, c, cuts = qty_path(q0, evs, t_d, b0, b1); n_pre += a; n_in += b_; n_post += c
        qL1 = (float(o["target_w"]) * Gt / conv) if o else q_dec                     # no orders row ⇒ the executor did not act on the name ⇒ hold what it had at decision time
        if o and o.get("side") and not str(o.get("terminal_reason", "")).startswith("skipped"):
            qL2 = q_dec + float(o.get("intended_notional") or 0.0) / conv               # placed request: decision-time quantity + the increment it asked for
        else:
            qL2 = q_dec                                                             # skipped or absent request: the position stays what it was
        fp_corr = 0.0; n_fp = 0
        for e in ev.get(s, []):
            b, k, v, t, fp = e[0], e[1], e[2], e[3], e[4]; tk = e[5] if len(e) > 5 else None
            if k == "fill" and b0 < b <= b1:
                n_intra += 1
                if fp: fill_dev.append((s, fp / px_abs[b] - 1.0))
            # R12-P3: the correction that turns the boundary-priced path into one that transacts at the RECORDED fill price.
            # Buying v at fp when the boundary mark is px[b] is worth v x (px[b] - fp) more than the boundary approximation says.
            # R13-P2 (2): the window owns [t_d, t_end] — half-open against the gap's (A, t_d), so a fill exactly at t_d is corrected ONCE.
            if k == "fill" and fp and t_d <= t <= t_end and b0 <= b <= b1:
                fp_corr += float(v) * (px_abs[b] - float(fp)); n_fp += 1; corr_keys.append(tk)
        fill_corr_total += fp_corr; n_fp_corr += n_fp
        pnl3, q_end, pnl3_l, pnl3_s = segment_pnl(q_start, path, px_abs, b0, b1)
        held = {"L0_producer": qL0, "L1_executor_target": qL1, "L2_request_intent": qL2}
        # the request intent CUT at this symbol's first in-window flatten: separates the flatten's footprint (L2cut − L2) from execution timing (L3 − L2cut)
        b_flat = min([c_[0] for c_ in cuts], default=None)
        if cuts: n_cut += 1
        out_s = {"status": "OK", "q0": q0, "q_dec": q_dec, "q_start": q_start, "q_end_path": q_end, "px_b0": p0, "px_b1": px_abs[b1], "ref": ref[2], "n_events_in": b_,
                 "fill_price_correction": fp_corr, "n_fills_corrected": n_fp, "cuts": [(int(c_[0]), (None if c_[1] is None else round(float(c_[1]), 6)), c_[2], c_[3]) for c_ in cuts]}
        for k, qk in held.items():
            if qk is None:
                layers[k][s] = None; continue
            pnl_k = qk * (px_abs[b1] - p0)
            layers[k][s] = {"qty": qk, "notional_b0": qk * p0, "pnl": pnl_k, "pnl_long": (pnl_k if qk > 0 else 0.0), "pnl_short": (pnl_k if qk < 0 else 0.0)}
        qc_start, qc_path = cut_path(qL2, cuts, b0, b1)
        pnl_cut, q_cut_end, pcl, pcs_ = segment_pnl(qc_start, qc_path, px_abs, b0, b1)
        layers["L2_cut_at_flatten"][s] = {"qty": qL2, "notional_b0": qL2 * p0, "pnl": pnl_cut, "pnl_long": pcl, "pnl_short": pcs_, "cut_at": b_flat,
                                          "qty_start_after_cuts": qc_start, "qty_end": q_cut_end}
        layers["L3_actual_path"][s] = {"qty": q_start, "notional_b0": q_start * p0, "pnl": pnl3, "pnl_long": pnl3_l, "pnl_short": pnl3_s, "qty_end": q_end,
                                       "fill_price_correction": fp_corr, "pnl_with_fill_prices": pnl3 + fp_corr}
        # consistency check against the NEXT post_anchor readback: continue the path with every event whose EVENT TIME ≤ that readback's read_ts
        # (the next rebalance's own fills happen before its readback, so they belong to the check, not to this window's pricing)
        rn = nxt.get(s)
        if nxt and (rn is not None or abs(q_end) > 0):
            t_chk = float(rn["read_ts"]) if rn is not None else t_next_read
            q_chk = q0
            for e in ev_sorted(ev.get(s, [])):                                     # THE shared event order (R12-P2: the path used a different one)
                b, k, v, t = e[0], e[1], e[2], e[3]
                if t <= t_chk:
                    q_chk = q_chk + v if k == "fill" else v
            qn = float(rn["venue_position_qty"]) if rn is not None else 0.0; dq = q_chk - qn
            if abs(dq) > 0:
                resid.append((s, dq, dq * px_abs[b1]))
        for _j in joins:                                             # the join's POSITION VALUE difference, now that the starting quantity is known
            if _j["symbol"] == s and _j["qty_at_join"] is None:
                _j["qty_at_join"] = q_start; _j["value_diff_usdt"] = q_start * (_j["px_own_at_b0"] - _j["px_chain_at_b0"])
        chain[s] = {"b": b1, "px": px_abs[b1], "source": "window_end:" + time.strftime("%m-%d %H:%MZ", time.gmtime(A))}   # R13-P2 (1): carry this symbol's price forward
        per[s] = out_s
    summary = {}
    for k, Ls in layers.items():
        vals = [v for v in Ls.values() if v]
        summary[k] = {"n": len(Ls), "n_priced": len(vals), "gross_b0": float(sum(abs(v["notional_b0"]) for v in vals)), "net_b0": float(sum(v["notional_b0"] for v in vals)),
                      "pnl_usdt": float(sum(v["pnl"] for v in vals)), "pnl_long_usdt": float(sum(v.get("pnl_long", 0.0) for v in vals)),
                      "pnl_short_usdt": float(sum(v.get("pnl_short", 0.0) for v in vals)), "censored": cens[k]}
    summary["L3_actual_path"]["fill_price_correction_usdt"] = float(fill_corr_total)
    summary["L3_actual_path"]["pnl_usdt_with_fill_prices"] = float(summary["L3_actual_path"]["pnl_usdt"] + fill_corr_total)
    summary["L3_actual_path"]["n_fills_price_corrected"] = int(n_fp_corr)
    l3g = sum(abs(v["notional_b0"]) for v in layers["L3_actual_path"].values() if v)
    wclass = "FLATTEN" if n_cut else ("HALTED_FLAT_BOOK" if (not subs and n_fills == 0 and l3g == 0.0) else ("NO_FILLS" if n_fills == 0 else "NORMAL"))
    rec.update(status="OK", rebalance_id=rid, window_class=wclass, n_names_cut_at_flatten=n_cut, t_decision=t_d, t_end=t_end,
               coverage_s=int(b1 - b0), coverage_note="the DECISION window [t_d, A+4h]; the [A, t_d] gap before it is priced separately by gap_pnl (R12-P3)",
               fill_price_correction_usdt=float(fill_corr_total), n_fills_price_corrected=int(n_fp_corr), t_decision_source=("min_submit_ts" if subs else "A+24min_fallback"), b0=b0, b1=b1, n_rows=(b1 - b0) // ROW,
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
               price_chain_joins={"n_names_compared": len(joins), "n_over_1pct": sum(1 for j in joins if j["rel"] is not None and abs(j["rel"]) > 0.01),
                                  "n_value_over_1cent": sum(1 for j in joins if j["value_diff_usdt"] is not None and abs(j["value_diff_usdt"]) > 0.01),
                                  "abs_value_diff_sum_usdt": float(sum(abs(j["value_diff_usdt"]) for j in joins if j["value_diff_usdt"] is not None)),
                                  "max_abs_rel": max((abs(j["rel"]) for j in joins if j["rel"] is not None), default=None),
                                  "causes": dict(collections.Counter(j["cause"] for j in joins)), "resets": dict(n_reset),
                                  "top": sorted([{k: (round(v, 8) if isinstance(v, float) else v) for k, v in j.items()} for j in joins],
                                                key=lambda j: -abs(j["value_diff_usdt"] or 0.0))[:10],
                                  "rule": "the day chain's price at b0 vs the price this window would have derived on its own; REPORTED, never added to P&L "
                                          "(a mark-vs-close difference is a valuation difference, not a realised gain)"},
               fill_partition={"owns": "[t_decision, t_end]", "n_fills_price_corrected": int(n_fp_corr), "keys": [list(k) if k else None for k in corr_keys],
                               "rule": "R13-P2 (2): the gap owns (A, t_d) and the window owns [t_d, t_end]; a fill exactly at t_d belongs to the window ONLY"},
               per_name=per, per_name_layers=layers)
    return rec


def gap_pnl(L, panel, A, t_d, prev_rec, px_chain=None):
    """R12-P3 (day coverage): price the CARRY gap [A, t_d] — the ~25 minutes between one window's end (the anchor instant) and the next window's
    decision boundary. Six such gaps a day are the 150 minutes the six decision windows do not cover (21.5 h of 24 h).

    Only the ACTUAL path is carried: the intent layers (L0/L1/L2) are DEFINED as "what the decision asked to hold from its own decision time", so
    they have no value before that decision exists — this function does not invent one. The carried state is the previous window's per-name ending
    quantity and ending price (`qty_end`, `px_b1`), so the two windows chain on the same price index without re-deriving a reference.
    Events inside the gap (fills, flatten readbacks) are applied in `ev_sorted` order, exactly as inside a window.
    Returns a dict with status GAP_OK / NO_PREV_WINDOW / EMPTY / PANEL_NOT_YET_COVERING.

    ★ ROUND 13 R13-P2: (2) the gap owns the HALF-OPEN interval (A, t_d) — a fill exactly at t_d belongs to the following window only (v4 corrected it on
    both sides, doubling the reviewer's 100 USDT correction to 200); (4) the gap no longer walks the previous window's priced layer alone — a name that
    first appears here (its fill is counted in `n_fills_in_gap`) used to get n_priced 0, censored 0 and a clean GAP_OK, i.e. it vanished. The population
    is now `previous priced layer ∪ names with gap events ∪ names the previous window CENSORED`, and anything that cannot be priced is censored with a
    named reason; (1) the day price chain `px_chain` is used and updated here too, so the gap and the window it joins share one reference."""
    rec = {"gap_for_anchor": A, "utc": time.strftime("%m-%d %H:%MZ", time.gmtime(A)), "t_from": float(A), "t_to": float(t_d)}
    if not prev_rec or prev_rec.get("status") != "OK":
        rec["status"] = "NO_PREV_WINDOW"; rec["why"] = (prev_rec or {}).get("status"); return rec
    b_lo = ceil_b(A); b_hi = ceil_b(t_d)
    rec.update(b_lo=b_lo, b_hi=b_hi, coverage_s=int(b_hi - b_lo))
    if b_hi <= b_lo:
        rec["status"] = "EMPTY"; rec["pnl_usdt"] = 0.0; rec["coverage_s"] = 0; return rec
    if b_hi > panel.t_last:
        rec["status"] = "PANEL_NOT_YET_COVERING"; return rec
    prev_layer = (prev_rec.get("per_name_layers") or {}).get("L3_actual_path") or {}
    prev_names = prev_rec.get("per_name") or {}
    ev = collections.defaultdict(list); n_fills = 0; corr_keys = []
    for r in L.fills:
        t = float(r["fill_ts"])
        if A < t < t_d:                                                # R13-P2 (2): HALF-OPEN — a fill exactly at t_d is the window's, not the gap's
            q = float(r["fill_notional"]) / float(r["fill_px"]); q = q if str(r.get("side", "")).lower() == "buy" else -q
            ev[r["symbol"]].append((ceil_b(t), "fill", q, t, float(r["fill_px"]), (r["symbol"], r.get("trade_id")))); n_fills += 1
    for r in L.flattens(A, t_d):
        ev[r["symbol"]].append((ceil_b(float(r["read_ts"])), "set", float(r["venue_position_qty"] or 0.0), float(r["read_ts"]), None, None))
    pnl = pl = ps = 0.0; corr = 0.0; n_priced = 0; cens = {"n": 0, "notional": 0.0, "why": collections.Counter()}; n_carried = 0; per = {}
    chain = px_chain if px_chain is not None else {}
    # R13-P2 (4): the population is the previous priced layer ∪ names with gap events ∪ names the previous window censored — a name whose first
    # appearance is a fill inside this gap used to be counted in n_fills and then dropped without a trace.
    prev_cens = {k for k, v in prev_names.items() if (v or {}).get("status") == "CENSORED"}
    pop = sorted(set(prev_layer) | set(ev) | prev_cens)
    for s_ in pop:
        v = prev_layer.get(s_)
        q_end = float((v or {}).get("qty_end") or 0.0)
        px_ref = float((prev_names.get(s_) or {}).get("px_b1") or 0.0); ref_b = b_lo; ref_src = "prev_window_end"
        if not px_ref:                                                     # no previous priced end: the day chain, else this gap's first fill price
            ch = chain.get(s_)
            if ch is not None and panel.index(s_, int(ch["b"]), min(int(ch["b"]), b_lo), b_hi) is not None:
                px_ref = float(ch["px"]); ref_b = int(ch["b"]); ref_src = "day_chain"
            else:
                f0 = sorted([e for e in ev.get(s_, []) if e[1] == "fill" and e[4]], key=lambda e: e[3])
                if f0: px_ref = float(f0[0][4]); ref_b = int(f0[0][0]); ref_src = "first_fill_px"
        if q_end == 0.0 and not ev.get(s_) and s_ not in prev_cens:
            continue                                                       # nothing carried and nothing happened: no gap exposure
        n_carried += 1
        px = panel.index(s_, ref_b, min(ref_b, b_lo), b_hi) if px_ref else None
        if px is None:
            why = ("no_reference_price" if not px_ref else ("carried_from_censored_window" if s_ in prev_cens else "panel_rows_missing_or_nonfinite"))
            cens["n"] += 1; cens["notional"] += abs(q_end * px_ref); cens["why"][why] += 1
            per[s_] = {"status": "CENSORED", "why": why, "n_events": len(ev.get(s_, []))}; continue
        px_abs = {b: px_ref * x for b, x in px.items()}
        _qd, q_start, path, _a, _b, _c, _cuts = qty_path(q_end, [(e[0], e[1], e[2], e[3]) for e in ev.get(s_, [])], float(A), b_lo, b_hi)
        seg, q_out, sl, ss = segment_pnl(q_start, path, px_abs, b_lo, b_hi)
        for e in ev.get(s_, []):
            b, k, vv, t, fp = e[0], e[1], e[2], e[3], e[4]
            if k == "fill" and fp and b_lo <= b <= b_hi:
                corr += float(vv) * (px_abs[b] - float(fp)); corr_keys.append(e[5] if len(e) > 5 else None)
        pnl += seg; pl += sl; ps += ss; n_priced += 1
        chain[s_] = {"b": b_hi, "px": px_abs[b_hi], "source": "gap_end:" + time.strftime("%m-%d %H:%MZ", time.gmtime(A))}
        per[s_] = {"q_start": q_start, "q_end": q_out, "pnl": seg, "ref": ref_src}
    cens = {"n": cens["n"], "notional": cens["notional"], "why": dict(cens["why"])}
    rec.update(status="GAP_OK", pnl_usdt=float(pnl), pnl_long_usdt=float(pl), pnl_short_usdt=float(ps), fill_price_correction_usdt=float(corr),
               pnl_usdt_with_fill_prices=float(pnl + corr), n_names_carried=n_carried, n_priced=n_priced, censored=cens, n_fills_in_gap=n_fills,
               per_name={k: v for k, v in per.items() if v.get("status") == "CENSORED"},
               fill_partition={"owns": "(A, t_decision)", "n_fills_price_corrected": len(corr_keys), "keys": [list(k) if k else None for k in corr_keys],
                               "rule": "R13-P2 (2): half-open — a fill exactly at t_d belongs to the window, not to this gap"},
               censored_reasons=dict(cens["why"]),
               note="carried ACTUAL position only; the intent layers are not defined before their own decision time")
    return rec


def layer_diffs(rec):
    L = rec["layers"]
    return {"L3_minus_L2_timing_and_fills": L["L3_actual_path"]["pnl_usdt"] - L["L2_request_intent"]["pnl_usdt"],
            "L3_minus_L2cut_execution": L["L3_actual_path"]["pnl_usdt"] - L["L2_cut_at_flatten"]["pnl_usdt"],
            "L2cut_minus_L2_flatten_footprint": L["L2_cut_at_flatten"]["pnl_usdt"] - L["L2_request_intent"]["pnl_usdt"],
            "L2_minus_L1_skips": L["L2_request_intent"]["pnl_usdt"] - L["L1_executor_target"]["pnl_usdt"],
            "L1_minus_L0_book_layer": L["L1_executor_target"]["pnl_usdt"] - L["L0_producer"]["pnl_usdt"],
            "L3_minus_L0_total": L["L3_actual_path"]["pnl_usdt"] - L["L0_producer"]["pnl_usdt"],
            # R12-P3: the SAME execution proxy once the recorded fill prices replace the boundary approximation on the actual path
            "L3_minus_L2cut_execution_with_fill_prices": L["L3_actual_path"]["pnl_usdt_with_fill_prices"] - L["L2_cut_at_flatten"]["pnl_usdt"],
            "fill_price_correction": L["L3_actual_path"]["fill_price_correction_usdt"]}
