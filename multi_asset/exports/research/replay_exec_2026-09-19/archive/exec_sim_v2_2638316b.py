#!/usr/bin/env python3
"""replay_exec 2026-09-19 · EXECUTOR-LAYER SIMULATOR: producer target books → executed positions, turnover, fees, funding and
price P&L, with self-evolving state (positions, entry prices, per-name stop counters / stop set / cooldown, day-loss halt).

Design contract (DESIGN_FP3_P §2 P-C and §8): the book layer is a pure function of DECISION-TIME-VISIBLE state only — the
sim's own positions / entry prices / stop state / equity, the archived target_live/<A>.json, the venue's tradable set and
meta exclusions as the executor recorded them BEFORE trading (phase_A universe gate, anchors.external_book.meta_excluded),
the config timeline (gross_mult, chase weights) as recorded, and market prices. Post-anchor readbacks, fills and NAV rows are
NEVER inputs to a decision; they are only the validation target (v1_gate.py).

Same code, imported from the COPY of the running executor tree 409ea16 exported into the mirror (snapshot_inputs.py):
  scheduler.anchor_loop.apply_withhold_and_reshape (POP → RESHAPE → CLAMP, force_flat = per-name stop set)
  live.binance_executor.RebalanceExecutor.plan (deltas → min-notional → lot rounding; full exits sized by held quantity)
  live.external_book.parse_target / target_vector / held_not_in_target / below_min_notional (2 × minNotional dust)
  signal.legs.to_notional · live.per_name_stop.evaluate / active_sets (−30% × 2 anchors, 7-day cooldown, wide profile)
  live.chase_policy.plan_experiment (C neutral_only frame + randomised arms, the anchor's recorded weights)
  live.requote_experiment.assign (deterministic requote / direct arm)
Not imported (stated approximations, see the result doc): the venue-cap clamp (maxNotionalValue per leverage bracket, ~1 name),
the dead zone (never active live: every anchor process starts with gross 0 ⇒ resize, 272/272 anchors), the placement bandit
(pooled into the maker outcome shares), rate limits / transport failures / −4400 venue lock (pooled into the top-up fill rate).

Fill model (CALIBRATION_FROZEN_*.json "params", EXPECTED VALUE — no random draws): per plan with rounded quantity q at mid m,
d = q·m. First maker leg: P(−5022 reject) p_rej; rested legs fill fully / not at all / partially (mean fraction f̄) with the
calibrated shares. Rejected legs go to requote (from the experiment's first anchor: arm = requote_experiment.assign(rid, sym, 0.5);
before it: the measured requote share as an expected-value mix; reduce-only exempt ⇒ requote) whose own outcome shares are
calibrated, or directly to the from_reject taker. Each residual CATEGORY (zero-fill: d,
partial: (1−f̄)·d) is checked against the symbol's floor after lot rounding (the executor's own rule), then chased only if
the name's chase arm is chase / chase_forced (chase_policy on the expected residuals, recorded weights, E4 exclusion of stop
names from 09-13 12Z), times the calibrated top-up fill rate of that arm (chase_forced is abandoned far more often). All legs of anchor A execute at the decision boundary
b_d = A+25min at P(b_d)·(1 + side·s_leg), s_leg = calibrated notional-weighted slippage vs mid_at_anchor per leg type
(the taker legs' 15-minute drift is inside s_leg, which is why they are placed at b_d and not at their fill time).
Fees = |notional| × calibrated rate (maker / taker × fee era, data-derived switch). Funding = −q·P(t_s)·rate at every
settlement (symbol's own fundingTime ⇒ interval-correct), rates = producer ledger (aux.json) with the executor's funding rows
as fallback. Prices = ONE chain per symbol on the producer's 5-minute panel (simlib.Panel).

Events: --events live  = the actual protective timeline injected (flatten instants from the protective-flatten fills; anchors
                          the executor did not trade: HALT = every row blocked_by_halt, HOLD = no rows and no fills, MAKER_ONLY =
                          maker fills without order rows — the 09-09 12Z run that died before its top-up leg).
        --events rule  = only §4-2 fires: at each N+40 the day's equity change vs the previous UTC day's last N+40 value (net of
                          transfers) < −4% ⇒ flatten at N+46 and halt until the next UTC day's FIRST anchor (00Z). Live resumes on
                          the first anchor AFTER a new-day NAV row exists (09-06 trip → 09-07 04Z), i.e. this approximation
                          resumes one anchor earlier; stated, not hidden. HOLD only where the target file is missing (the
                          executor's own on_unavailable=hold rule).
Knobs for the battery (all default OFF; every run records them): --no-stop, --no-min-notional, --zero-fees, --fee-asset-wrong,
--funding-sign-flip, --funding-double, --no-exit-completion (= the v1 behaviour).
VERSION v2 (2026-09-19, after V1): adds EXIT COMPLETION (see on_anchor). v1 (sha fbcaa25e, archive/exec_sim_v1_fbcaa25e.py) is the
device the V1 verdict of record was computed with; v2 changes no calibration parameter.
usage: exec_sim.py --events {live,rule} --out <out.json> [--calib CAL.json] [--mirror DIR] [knobs]
"""
import argparse, collections, copy, json, os, sys, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L

E4_FROM_ANCHOR = 1789300800           # 09-13 12Z: ef60f85 (E4: a stopped name's from_partial residual is never chased)
TRADE, HALT, HOLD, MAKER_ONLY = "TRADE", "HALT", "HOLD", "MAKER_ONLY"


class ExecutorCode:
    """the running executor's pure functions, imported from the mirrored COPY of tree 409ea16"""
    def __init__(self, mirror):
        t = mirror.tree
        if t not in sys.path:
            sys.path.insert(0, t)
        import scheduler.anchor_loop as AL
        from live import binance_executor as BX
        import chase_policy as CP
        import requote_experiment as RQ
        self.AL, self.BX, self.CP, self.RQ = AL, BX, CP, RQ
        self.EXT, self.PNS, self.LG = AL.EXT, AL.PNS, AL.LG
        for m in (AL, BX, CP, RQ, AL.EXT, AL.PNS, AL.LG):
            assert os.path.realpath(m.__file__).startswith(os.path.realpath(t)), f"{m.__name__} not imported from the mirror copy: {m.__file__}"
        self.book_cfg = json.load(open(os.path.join(t, "config", "book.json")))
        ext = self.EXT.config(self.book_cfg)
        assert ext["source"] == "external", ext.get("error")
        self.ext_cfg = dict(ext, universe_sha_pin=None, booster_sha_pin=None, f10_sha_pin=None)   # pins only refuse; every archived book the executor traded was accepted (weights_sha checked below)
        self.pns_conf = self.PNS.cfg(os.path.join(t, "config", "book.json"))
        assert self.pns_conf.get("_profile") == "wide" and abs(float(self.pns_conf["depth_pct"]) + 0.30) < 1e-12, self.pns_conf
        self.filters = self.BX.SymbolFilters.__new__(self.BX.SymbolFilters)
        self.filters.f = mirror.exchange_filters(); self.filters.cache_path = None
        self.stub = types.SimpleNamespace(filters=self.filters, band_bps=self.BX.DEFAULT_BAND_BPS)
        self.files = {os.path.relpath(m.__file__, mirror.root): L.sha_file(m.__file__) for m in (AL, BX, CP, RQ, AL.EXT, AL.PNS, AL.LG)}


# ───────────────────────────── decision-time timeline from the executor's own records ─────────────────────────────
def config_timeline(M, anchors):
    """gross_mult, chase weights, venue-tradable set, meta exclusions and rebalance_id per nominal anchor, as recorded at
    DECISION time (phase_A = before orders; anchors row fields written from the same run's decision state). Carried forward
    over anchors without a record. Returns {A: {...}} and a provenance count."""
    an = M.anchor_rows()
    out, prov = {}, collections.Counter()
    last = {"gm": None, "weights": None, "tradable": None, "meta": set()}
    for A in anchors:
        pa = M.phase_a_trade(A); r = an.get(A)
        gm = None
        if pa and (pa.get("external_book") or {}).get("gross_mult") is not None:
            gm = float(pa["external_book"]["gross_mult"]); prov["gm_phase_a"] += 1
        elif r is not None:
            try:
                gm = float(json.loads(r["factor_version"]).get("gross_mult")); prov["gm_anchor_row"] += 1
            except Exception:
                gm = None
        if gm is None:
            gm = last["gm"]; prov["gm_carried"] += 1
        w = ((r or {}).get("chase_experiment") or {}).get("weights") if r else None
        if w:
            prov["weights_recorded"] += 1
        else:
            w = last["weights"]; prov["weights_carried"] += 1
        tr = ((pa or {}).get("universe") or {}).get("tradable")
        if tr is not None:
            tr = set(tr); prov["tradable_recorded"] += 1
        else:
            tr = last["tradable"]; prov["tradable_carried"] += 1
        me = ((r or {}).get("external_book") or {}).get("meta_excluded") if r else None
        if isinstance(me, dict):
            me = set(me); prov["meta_recorded"] += 1
        else:
            me = last["meta"]; prov["meta_carried"] += 1
        rid = (pa or {}).get("rebalance_id") or f"A{A + 1440}"
        out[A] = {"gm": gm, "weights": w, "tradable": tr, "meta": me, "rid": rid, "rid_recorded": bool(pa)}
        last = {"gm": gm, "weights": w, "tradable": tr, "meta": me}
    return out, dict(prov)


def live_event_timeline(M, anchors):
    """--events live: the ACTUAL protective timeline (exogenous): flatten instants + per-anchor TRADE / HALT / HOLD / MAKER_ONLY"""
    onom = M.orders_by_nominal()
    fl_t = collections.defaultdict(list)
    t_lo, t_hi = anchors[0], anchors[-1] + 14400 + 3600
    for x in L.all_trades(M, t_lo, t_hi):
        if x["order_type"] == "protective_flatten":
            fl_t[int(x["ts"]) // 3600].append(x["ts"])
    flat = sorted(min(v) for v in fl_t.values())
    merged = []
    for t in flat:
        if not merged or t - merged[-1] > 3600:
            merged.append(t)
    fills_by_rid = collections.Counter()
    for f in M.fills():
        if str(f.get("rebalance_id") or "").startswith("A"):
            fills_by_rid[(L.nominal(float(f["rebalance_id"][1:])), f.get("order_type"))] += 1
    kind = {}
    for A in anchors:
        od = onom.get(A, [])
        sent = [r for r in od if r["terminal_reason"] not in ("blocked_by_halt", "skipped_min_notional")]
        if od and any(r["terminal_reason"] == "blocked_by_halt" for r in od) and not sent:
            kind[A] = HALT                  # every row is blocked_by_halt except min-notional skips (which never reach the halt gate)
        elif not od and fills_by_rid.get((A, "maker")) and not fills_by_rid.get((A, "topup_taker")):
            kind[A] = MAKER_ONLY
        elif not od:
            kind[A] = HOLD
        else:
            kind[A] = TRADE
    return merged, kind


def initial_stop_state(M, t0, conf):
    """the per-name stop state at t0 rebuilt from the executor's own phase_C records (stopped lists + the time a stopped name
    left the list = the cooldown start; cooldown = start + cooloff_days). Asserted against the recorded cooldown_n."""
    _, pc = M.phase_records()
    stopped, cool, last_rec = set(), {}, None
    cd = float(conf.get("cooloff_days", 7)) * 86400.0
    for t, d in pc:
        if t > t0 + 60:
            break
        p = d.get("per_name_stop")
        if not isinstance(p, dict):
            continue
        now = set(p.get("stopped") or [])
        for s in stopped - now:
            cool[s] = t + cd
        for s in list(cool):
            if cool[s] <= t:
                del cool[s]
        stopped = now; last_rec = (t, p)
    assert last_rec is not None
    assert len(cool) == int(last_rec[1].get("cooldown_n") or 0), (sorted(cool), last_rec)
    return {"counters": dict(last_rec[1].get("counters") or {}), "stopped": {s: last_rec[0] for s in stopped}, "cooldown": cool}, \
        {"phase_c_utc": L.U(last_rec[0]), "cooldown": {s: L.U(v) for s, v in sorted(cool.items())}, "stopped": sorted(stopped)}


def initial_entries(M, t0, q0, panel):
    """average entry price per held name at t0, rebuilt from every trade since the book was last flat (the 08-21 20:16Z
    protective flatten) with the venue's rule (adds re-average, reductions keep the entry, a sign flip restarts at the fill
    price). Names whose rebuilt quantity disagrees with the t0 readback by > 1% (or were never traded in that span) start at
    the panel price at t0 (named)."""
    t_flat = 1787343360.0 + 900          # FLATTEN-20260821T201600Z + 15 min
    q, e = collections.defaultdict(float), {}
    for x in L.all_trades(M, t_flat, t0):
        s, dq, px = x["symbol"], x["sq"], x["px"]
        qo = q[s]; qn = qo + dq
        if abs(qo) < 1e-12 or qo * dq > 0:
            e[s] = px if abs(qo) < 1e-12 else (qo * e[s] + dq * px) / qn
        elif qo * qn < 0:
            e[s] = px
        elif abs(qn) < 1e-12:
            e.pop(s, None)
        q[s] = qn
    out, named = {}, {}
    b0 = L.floor_b(t0)
    for s, qq in q0.items():
        if abs(q[s] - qq) <= 0.01 * abs(qq) and s in e:
            out[s] = e[s]
        else:
            p = panel.px(s, b0)
            out[s] = p
            named[s] = {"rebuilt_qty": q[s], "readback_qty": qq, "entry": "panel price at t0"}
    return out, named


# ───────────────────────────────────────────── the simulator ─────────────────────────────────────────────
class Sim:
    def __init__(self, M, cal, mode, knobs, X=None, panel=None, fund=None):
        self.M, self.cal, self.mode, self.k = M, cal, mode, knobs
        self.p = cal["params"]
        self.X = X or ExecutorCode(M)
        self.P = panel
        if self.P is None:
            self.P = L.Panel(M); L.build_references(M, self.P)
        self.F = fund or L.FundingBook(M)
        self.W, _ = L.live_windows()
        self.W = [w for w in self.W if L.A_V1_FIRST <= L.nominal(w["t0"]) <= L.A_V1_LAST]
        self.t_start, self.t_end = self.W[0]["t0"], self.W[-1]["t1"]
        self.anchors = [A for A in range(L.A_V1_FIRST + 14400, L.nominal(self.t_end) + 1, 14400)]   # first decision after t0 = 08-26 04Z; last = the one inside the last window (09-19 00Z)
        self.cfg, self.cfg_prov = config_timeline(M, list(range(L.A_V1_FIRST, self.anchors[-1] + 1, 14400)))
        self.flat_times, self.kind = live_event_timeline(M, self.anchors)
        self.xfers = [(t, a) for t, a in L.transfers() if self.t_start < t <= self.t_end]
        self.fee_switch = float(self.p["fee_rate"]["switch_ts"])
        # initial state = the executor's own post-trade readback at t0 (same call as the NAV row) and the NAV at t0
        rb = [r for d in ("20260826",) for r in M.rows(d, "position_readback") if abs(float(r["read_ts"]) - self.t_start) < 1.0]
        assert rb, "no readback at t0"
        self.q = {r["symbol"]: float(r["venue_position_qty"]) for r in rb if float(r["venue_position_qty"]) != 0.0}
        self.nav0 = float(self.W[0]["nav0_usdt"])
        self.entry, self.entry_named = initial_entries(M, self.t_start, self.q, self.P)
        self.pns, self.pns_init = initial_stop_state(M, self.t_start, self.X.pns_conf)
        b0 = L.floor_b(self.t_start)
        miss = [s for s in self.q if self.P.px(s, b0) is None]
        assert not miss, f"held names without a price chain at t0: {miss}"
        self.K = self.nav0 - sum(q * self.P.px(s, b0) for s, q in self.q.items())
        self.acc = collections.Counter()           # cumulative: tradecash, fee, fund, turn, xfer, n_trades
        self.halt_until = None
        self.log_anchor, self.events_fired, self.diag = [], [], collections.Counter()
        # in-memory audit logs for the battery (not written to the receipt): every trade leg, every funding charge, every depth read
        self.trade_log, self.fund_log, self.depth_log, self.plan_log, self.exit_log = [], [], [], [], []
        self.day_ref = {}                           # UTC day -> (t, equity) of the previous day's last N+40 evaluation (§4-2 reference)
        self.last_eval = None

    # ── prices / equity ──
    def px(self, s, b):
        v = self.P.px(s, b)
        if v is None:
            self.diag["px_missing"] += 1
        return v

    def mv(self, b):
        tot = 0.0
        for s, q in self.q.items():
            p = self.px(s, b)
            if p is not None:
                tot += q * p
        return tot

    def equity(self, b):
        return self.K + self.mv(b)

    def gross(self, b):
        return sum(abs(q * (self.px(s, b) or 0.0)) for s, q in self.q.items())

    def fee_rate(self, t, maker):
        era = "BNB_era" if t < self.fee_switch else "USDT_era"
        if self.k.get("fee_asset_wrong"):
            era = "USDT_era" if era == "BNB_era" else "BNB_era"
        if self.k.get("zero_fees"):
            return 0.0
        return float(self.p["fee_rate"][era]["maker" if maker else "taker"])

    # ── one trade ──
    def trade(self, t, s, notional_mid, b, slip, maker, kind):
        """execute `notional_mid` (signed, valued at P(b)) at P(b)·(1 + side·slip); update qty, entry, cash, fees, turnover"""
        if notional_mid == 0.0:
            return 0.0
        P = self.px(s, b)
        side = 1.0 if notional_mid > 0 else -1.0
        dq = notional_mid / P
        px = P * (1.0 + side * slip)
        cash = dq * px
        fee = abs(cash) * self.fee_rate(t, maker)
        qo = self.q.get(s, 0.0); qn = qo + dq
        if abs(qo) < 1e-15 or qo * dq > 0:
            self.entry[s] = px if abs(qo) < 1e-15 else (qo * self.entry.get(s, px) + dq * px) / qn
        elif qo * qn < 0:
            self.entry[s] = px
        if abs(qn) < 1e-12 * max(1.0, abs(qo)):
            qn = 0.0
        if qn == 0.0:
            self.q.pop(s, None); self.entry.pop(s, None)
        else:
            self.q[s] = qn
        self.K -= cash + fee
        self.trade_log.append((t, s, cash, maker, fee, kind))
        self.acc["tradecash"] += cash; self.acc["fee"] += fee; self.acc["turn"] += abs(cash); self.acc["n_trades"] += 1
        self.acc[f"turn_{kind}"] += abs(cash)
        return abs(cash)

    # ── events ──
    def on_funding(self, t):
        sgn = -1.0 if self.k.get("funding_sign_flip") else 1.0
        mult = 2.0 if self.k.get("funding_double") else 1.0
        for s, q in list(self.q.items()):
            r = self.F.rate.get((s, int(t)))
            if r is None:
                continue
            P = self.px(s, L.floor_b(t))
            if P is None:
                continue
            f = sgn * mult * (-q * P * r)
            self.K += f; self.acc["fund"] += f
            self.fund_log.append((t, s, q, P, r, f))

    def on_transfer(self, t, amt):
        self.K += amt; self.acc["xfer"] += amt

    def flatten(self, t, why):
        b = L.ceil_b(t)
        n = 0
        for s, q in sorted(self.q.items()):
            P = self.px(s, b)
            if P is None:
                continue
            n += 1
            self.trade(t, s, -q * P, b, float(self.p["slippage_flatten_vs_mid_at_submit"]), False, "flatten")
        self.events_fired.append({"type": "FLATTEN", "utc": L.U(t), "why": why, "n_names": n})

    def on_stop_eval(self, A, t):
        b = L.floor_b(t)
        pn = {s: q * self.px(s, b) for s, q in self.q.items() if self.px(s, b) is not None}
        pu = {s: q * (self.px(s, b) - self.entry.get(s, self.px(s, b))) for s, q in self.q.items() if self.px(s, b) is not None}
        self.depth_log.append((A, t, {s: pu[s] / abs(pn[s]) for s in pn if abs(pn[s]) >= float(self.X.pns_conf.get("min_notional_usdt", 5.0))},
                               set(self.pns["stopped"]) | set(self.pns["cooldown"])))
        if not self.k.get("no_stop"):
            before = set(self.pns["stopped"])
            self.pns, ev = self.X.PNS.evaluate({"positions_notional": pn, "positions_unrealized": pu}, self.pns, self.X.pns_conf, t)
            for s in sorted(set(self.pns["stopped"]) - before):
                self.events_fired.append({"type": "STOP", "utc": L.U(t), "symbol": s})
        E = self.equity(b)
        day = time.strftime("%Y%m%d", time.gmtime(t))
        if self.mode == "rule":
            if day not in self.day_ref:
                self.day_ref[day] = self.last_eval if self.last_eval is not None else (self.t_start, self.nav0)
            ref_t, ref_E = self.day_ref[day]
            xf = [a for tt, a in self.xfers if ref_t < tt <= t]
            # B32 (watchdog cond2): a day whose equity window contains an external transfer is UNKNOWN — not judged
            loss = None if xf else ((E - ref_E) / ref_E if ref_E else None)
            if loss is not None and loss < -0.04 and (self.halt_until is None or t >= self.halt_until) and self.gross(b) > 0:
                tf = A + float(self.p["rule_flatten_offset_s"])
                self.pending_flatten = (tf, f"§4-2 day loss {loss:+.2%} at {L.U(t)} (ref {ref_E:,.0f} @ {L.U(ref_t)}, E {E:,.0f})")
                self.halt_until = (int(t) // 86400 + 1) * 86400          # next UTC day's first anchor (00Z)
        self.last_eval = (t, E)

    def status(self, A):
        if self.mode == "live":
            return self.kind.get(A, TRADE)
        if self.halt_until is not None and A < self.halt_until:
            return HALT
        return TRADE

    def on_anchor(self, A):
        st = self.status(A)
        rec = {"anchor": A, "utc": L.UA(A), "status": st}
        tpath = self.M.target_path(A)
        if st in (HALT, HOLD):
            self.log_anchor.append(rec); return
        if not os.path.exists(tpath):
            rec["status"] = HOLD; rec["why"] = "target_live missing (executor on_unavailable=hold)"; self.log_anchor.append(rec); return
        X, c = self.X, self.cfg[A]
        t_dec = A + 1440; b = A + int(self.p["decision_boundary_offset_s"])
        ext = X.EXT.parse_target(open(tpath, "rb").read(), X.ext_cfg, A, t_dec)
        if not ext.get("ok"):
            rec["status"] = HOLD; rec["why"] = f"target invalid: {ext.get('reason')}"; self.log_anchor.append(rec); return
        an = self.M.anchor_rows().get(A)
        if an is not None:
            try:
                ws = json.loads(an["factor_version"]).get("weights_sha")
                rec["weights_sha_matches_executor_read"] = (ws == ext["weights_sha"])
            except Exception:
                pass
        pos = {s: q * self.px(s, b) for s, q in self.q.items() if self.px(s, b) is not None}
        held_exit = X.EXT.held_not_in_target(pos, ext["symbols"])
        symbols = sorted(set(ext["symbols"]) | set(held_exit))
        act = X.PNS.active_sets(self.pns, t_dec)
        if self.k.get("no_stop"):
            act = {"stop": set(), "cooldown": set()}
        untr = set()
        if c["tradable"] is not None:
            untr |= set(symbols) - c["tradable"]
        untr |= (c["meta"] & set(symbols)) | act["stop"] | act["cooldown"] | set(held_exit)
        E = self.equity(b)
        G = E * float(c["gm"])
        target = X.LG.to_notional(X.EXT.target_vector(ext, symbols), symbols, G)
        floors = {s: float((X.filters.f.get(s) or {}).get("min_notional", 0.0) or 0.0) for s in target}
        if self.k.get("no_min_notional"):
            floors = {s: 0.0 for s in floors}
        dust = X.EXT.below_min_notional(target, floors, X.ext_cfg["min_notional_mult"])
        untr |= set(dust["names"])
        clamp, rs = X.AL.apply_withhold_and_reshape(target, pos, untr, G, floors_usdt=floors, floors_source="executor.filters.f[*].min_notional",
                                                     force_flat=act["stop"])
        mids = {s: self.px(s, b) for s in target if self.px(s, b) is not None}
        ro = set(clamp["reduced"]) | set(clamp["flatten_only"])
        if self.k.get("no_min_notional"):
            saved = copy.deepcopy(X.filters.f)
            for v in X.filters.f.values():
                if isinstance(v, dict) and "min_notional" in v:
                    v["min_notional"] = 0.0
        try:
            plans = X.BX.RebalanceExecutor.plan(X.stub, target, pos, mids, reduce_only_syms=ro, held_qty=dict(self.q))
        finally:
            if self.k.get("no_min_notional"):
                X.filters.f.clear(); X.filters.f.update(saved)
        # ── expected-value fill model ──
        pf, prq = self.p["maker_first"], self.p["maker_requote"]
        rq = [x for x in self.p["requote_p_timeline"] if A >= x["from_anchor"]][-1]
        rq_p, rq_mode = float(rq["p"]), rq.get("mode", "executor_hash")
        tf = self.p["taker_fill_rate"]
        tf_rej = float(tf["from_reject"])
        sl = self.p["slippage_vs_mid_at_anchor"]
        legs = {}
        prev_sum = fill_sum = others = 0.0; gross_now = 0.0
        pop = []
        n_plan = n_skip_min = n_skip_nomid = 0; plan_turn = 0.0
        for p in plans:
            s = p["symbol"]
            if p.get("skip") or "qty" not in p:
                n_skip_min += int(p.get("skip") == "skipped_min_notional")
                n_skip_nomid += int(p.get("skip") == "skipped_no_mid")
                if s in act["stop"]:
                    self.plan_log.append((A, s, 0.0, None, float(target.get(s, 0.0)), float(p["prev_notional"]), True))
                prev_sum += float(p["prev_notional"]); gross_now += abs(float(p["prev_notional"]))
                continue
            n_plan += 1
            m = mids[s]; d = float(p["qty"]) * m; plan_turn += abs(d)
            fl = float((X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0)
            self.plan_log.append((A, s, d, fl, float(target.get(s, 0.0)), float(p["prev_notional"]), s in act["stop"]))
            rest = 1.0 - pf["p_rej"]
            M1 = rest * (pf["p_full"] + pf["p_part"] * pf["fbar_part"]) * d
            cats = [(rest * pf["p_zero"], d), (rest * pf["p_part"], (1.0 - pf["fbar_part"]) * d)]
            if s in ro:
                w_rq = 1.0                                      # reduce-only is exempt: always requoted
            elif rq_mode == "executor_hash":
                w_rq = 1.0 if X.RQ.assign(c["rid"], s, rq_p) == "requote" else 0.0
            else:
                w_rq = rq_p                                     # pre-experiment: measured requote share as an expected-value mix
            r2 = pf["p_rej"] * w_rq * (1.0 - prq["p_rej"])
            M2 = r2 * (prq["p_full"] + prq["p_part"] * prq["fbar_part"]) * d
            cats += [(r2 * prq["p_zero"], d), (r2 * prq["p_part"], (1.0 - prq["fbar_part"]) * d)]
            w_rej = pf["p_rej"] * (w_rq * prq["p_rej"] + (1.0 - w_rq))
            R_p = sum(w * r for w, r in cats)
            legs[s] = {"d": d, "M1": M1, "M2": M2, "cats": cats, "w_rej": w_rej, "floor": fl, "mid": m}
            prev_sum += float(p["prev_notional"]); fill_sum += M1 + M2; others += w_rej * d
            gross_now += abs(float(p["prev_notional"]) + M1 + M2)
            if R_p != 0.0:
                pop.append((s, R_p))
        excl = {s: "stopped (E4)" for s in act["stop"]} if A >= E4_FROM_ANCHOR else {}
        ce = X.CP.plan_experiment(pop, c["rid"], book_net_usdt=prev_sum + fill_sum + others, book_gross_usdt=gross_now,
                                  net_basis="sim: expected maker fills + expected from_reject residuals", weights=c["weights"], exclude=excl)
        arms = ce.get("arm_assigned") or {}
        maker_only = (st == MAKER_ONLY)
        tot = collections.Counter()

        def passes(s, x):
            lg = legs[s]
            qq = X.filters.round_qty(s, x / lg["mid"])
            return qq != 0 and abs(qq) * lg["mid"] >= lg["floor"] - 1e-12
        for s, lg in sorted(legs.items()):
            tot["maker"] += self.trade(t_dec, s, lg["M1"], b, float(sl["maker_first"]), True, "maker")
            tot["maker"] += self.trade(t_dec, s, lg["M2"], b, float(sl["maker_requote"]), True, "maker")
            if maker_only:
                continue
            arm = arms.get(s)
            tf_ch = float(tf["from_partial_chase_forced"]) if arm == "chase_forced" else (float(tf["from_partial_chase"]) if arm == "chase" else 0.0)
            Tp = sum(w * r for w, r in lg["cats"] if w > 0 and passes(s, r)) * tf_ch
            Tr = lg["w_rej"] * lg["d"] * tf_rej if passes(s, lg["d"]) else 0.0
            tot["taker"] += self.trade(t_dec, s, Tp, b, float(sl["taker_from_partial"]), False, "taker")
            tot["taker"] += self.trade(t_dec, s, Tr, b, float(sl["taker_from_reject"]), False, "taker")
        # ── v2 EXIT COMPLETION: an exit (executor target exactly 0) whose EXPECTED remainder is below the symbol's floor is closed now.
        #    The expected-value fill leaves 1 − E[fill] of every exited position; in reality that mass is "the whole position, not yet
        #    exited" (≥ floor, exited again next anchor) or 0 — never a sub-floor sliver. Without this, v1 accumulated up to ~150 dust
        #    positions whose cooldown / held-untradable clamp (add_blocked) pinned 2–5% of the sizing gross (found in the mode-(b)
        #    diagnosis after V1; not a calibration parameter).
        n_ec = 0
        if not self.k.get("no_exit_completion"):
            for s, tv in sorted(target.items()):
                q = self.q.get(s, 0.0)
                if tv != 0.0 or q == 0.0 or self.px(s, b) is None:
                    continue
                v = q * self.px(s, b)
                fl = float((X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0)
                if abs(v) < fl:
                    tot["maker"] += self.trade(t_dec, s, -v, b, float(sl["maker_first"]), True, "exit_completion"); n_ec += 1
        for s, tv in target.items():            # audit (battery claim 9): every exited name's remainder after this decision
            if tv == 0.0 and s in pos and self.px(s, b) is not None:
                self.exit_log.append((A, s, self.q.get(s, 0.0) * self.px(s, b), float((X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0)))
        rec.update({"status": st, "rid": c["rid"], "gm": c["gm"], "equity_at_decision": E, "sizing_gross": G, "n_symbols": len(symbols),
                    "n_untradable": len(untr), "n_stop": len(act["stop"]), "n_cooldown": len(act["cooldown"]), "n_held_exit": len(held_exit),
                    "n_dust": dust["n"], "n_plans_sent": n_plan, "n_skip_min_notional": n_skip_min, "n_skip_no_price_chain": n_skip_nomid,
                    "n_exit_completion": n_ec,
                    "plan_turnover": plan_turn,
                    "exec_maker": tot["maker"], "exec_taker": tot["taker"],
                    "exec_over_plan": ((tot["maker"] + tot["taker"]) / plan_turn if plan_turn else None),
                    "arm_counts": ce.get("arm_counts"), "chase_weights": c["weights"], "clamp_counts": {k: len(v) for k, v in clamp.items()}})
        self.log_anchor.append(rec)

    # ── the run ──
    def run(self):
        ev = []
        for w in self.W:
            ev.append((w["t0"], 9, "win0", w["idx"])); ev.append((w["t1"], 9, "win1", w["idx"]))
        for A in self.anchors:
            ev.append((A + int(self.p["decision_boundary_offset_s"]) - 60, 5, "anchor", A))     # decides at N+24:00, executes at the N+25 boundary
            ev.append((A + int(self.p["stop_eval_offset_s"]), 6, "stop_eval", A))
        if self.mode == "live":
            for t in self.flat_times:
                if self.t_start < t <= self.t_end:
                    ev.append((t, 4, "flatten", "live protective flatten (exogenous)"))
        for t, a in self.xfers:
            ev.append((t, 1, "xfer", a))
        fts = sorted({t for (s, t) in self.F.rate if self.t_start < t <= self.t_end})
        for t in fts:
            ev.append((float(t), 2, "funding", None))
        ev.sort(key=lambda e: (e[0], e[1]))
        self.pending_flatten = None
        snaps = {}
        i = 0
        while i < len(ev):
            t, pri, kind, arg = ev[i]; i += 1
            if self.pending_flatten is not None and self.pending_flatten[0] <= t:
                tf, why = self.pending_flatten; self.pending_flatten = None
                self.flatten(tf, why)
            if kind == "win0" or kind == "win1":
                b = L.floor_b(t)
                snaps[(kind, arg)] = {"mv": self.mv(b), "gross": self.gross(b), "equity": self.equity(b), **{k: self.acc[k] for k in
                                      ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_maker", "turn_taker", "turn_flatten")}}
            elif kind == "anchor":
                self.on_anchor(arg)
            elif kind == "stop_eval":
                self.on_stop_eval(arg, t)
            elif kind == "flatten":
                self.flatten(t, arg)
            elif kind == "xfer":
                self.on_transfer(t, arg)
            elif kind == "funding":
                self.on_funding(t)
        out = []
        for w in self.W:
            a, z = snaps[("win0", w["idx"])], snaps[("win1", w["idx"])]
            d = {k: z[k] - a[k] for k in ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_maker", "turn_taker", "turn_flatten")}
            out.append({"idx": w["idx"], "from": w["from"], "to": w["to"], "t0": w["t0"], "t1": w["t1"], "gross0": a["gross"], "nav0": a["equity"],
                        "price_trade": (z["mv"] - a["mv"]) - d["tradecash"], "funding": d["fund"], "fee": d["fee"], "turnover": d["turn"],
                        "turnover_maker": d["turn_maker"], "turnover_taker": d["turn_taker"], "turnover_flatten": d["turn_flatten"],
                        "transfer": d["xfer"], "n_trades": d["n_trades"], "equity1": z["equity"]})
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", choices=("live", "rule"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--calib", default=os.path.join(HERE, "CALIBRATION_FROZEN_2026-09-19.json"))
    ap.add_argument("--mirror", default=L.MIRROR_DEFAULT)
    for k in ("no-stop", "no-min-notional", "zero-fees", "fee-asset-wrong", "funding-sign-flip", "funding-double", "no-exit-completion"):
        ap.add_argument("--" + k, action="store_true")
    a = ap.parse_args()
    knobs = {k.replace("-", "_"): getattr(a, k.replace("-", "_")) for k in ("no-stop", "no-min-notional", "zero-fees", "fee-asset-wrong",
                                                                           "funding-sign-flip", "funding-double", "no-exit-completion")}
    M = L.Mirror(a.mirror)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    assert not bad, f"mirror differs from INPUT_MANIFEST: {bad[:5]}"
    cal = json.load(open(a.calib))
    assert cal.get("frozen_before_v1") is True
    t0 = time.time()
    S = Sim(M, cal, a.events, knobs)
    W = S.run()
    doc = {"device": "exec_sim.py", "version": "v2", "device_sha256": L.sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": "/usr/bin/python3 " + " ".join([os.path.relpath(os.path.abspath(__file__), L.REPO)] + [x if not os.path.isabs(x) else x for x in sys.argv[1:]]),
           "argv": sys.argv[1:], "mode": a.events, "knobs": knobs, "runtime_s": round(time.time() - t0, 1),
           "calibration": {"path": os.path.relpath(os.path.abspath(a.calib), L.REPO), "sha256": L.sha_file(a.calib)},
           "inputs_sha256": L.input_shas(M, extra=[a.calib]), "executor_code_files_sha256": S.X.files,
           "config_timeline_provenance": S.cfg_prov, "initial_state": {"utc": L.U(S.t_start), "nav0": S.nav0, "n_positions": len(S.q),
                                                                        "stop_state": S.pns_init, "entry_prices_not_rebuilt": S.entry_named},
           "event_timeline": {"mode": a.events, "live_flatten_utc": [L.U(t) for t in S.flat_times],
                              "anchor_kind_counts": dict(collections.Counter(S.kind.values())),
                              "non_trade_anchors_live": {L.UA(A): k for A, k in S.kind.items() if k != TRADE}},
           "events_fired": S.events_fired, "diag": dict(S.diag), "funding_xcheck": S.F.xcheck, "funding_source": dict(S.F.src),
           "panel": {"n_refs": len(S.P.ref), "span": f"{L.U(S.P.t_first)}..{L.U(S.P.t_last)}"},
           "anchors": S.log_anchor, "windows": W}
    with open(a.out + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    os.replace(a.out + ".part", a.out)
    n_st = collections.Counter(r["status"] for r in S.log_anchor)
    print(f"exec_sim {a.events}: {len(W)} windows, anchors {dict(n_st)}, events {collections.Counter(e['type'] for e in S.events_fired)}, "
          f"runtime {doc['runtime_s']} s -> {a.out}")


if __name__ == "__main__":
    main()
