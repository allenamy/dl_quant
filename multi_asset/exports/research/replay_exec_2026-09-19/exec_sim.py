#!/usr/bin/env python3
"""replay_exec 2026-09-19 · EXECUTOR-LAYER SIMULATOR v3 (causal clocks): producer target books → executed positions, turnover, fees,
funding and price P&L, with self-evolving state (positions, entry prices, per-name stop counters / stop set / cooldown, day-loss
halt). v2 (sha 2638316b, archive/exec_sim_v2_2638316b.py) was rejected by review round 5 (R5-01, R5-06, R5-13); v3 fixes the CLASS:

  R5-01  DECISION CLOCK vs FILL CLOCK. The decision of anchor A happens at t_dec(A) = the executor's recorded read instant (the rid
         timestamp: N+23:00 before 08-27 08Z, N+24:00 after; N+24:00 where no rid was recorded) and reads ONLY what exists then:
         the inventory held at t_dec, the simulated equity at t_dec, and prices of the LAST COMPLETE 5-minute bar at or before
         t_dec (P(floor_b(t_dec)) = the bar ending N+20:00). Quantities are fixed at the decision (the executor's own plan rounds
         to lot steps). Every fill is an EVENT at its own simulated time: t_dec + the calibrated pooled offsets (first leg / later
         legs, notional-weighted 10/30/50/70/90% quantiles, 1/5 of the leg's quantity at each), priced at the decision-visible
         reference × (1 + side × pooled slippage vs the executor's own recorded mid). Inventory changes only when a fill event
         is processed; funding at settlement t_s charges the inventory held at t_s (fills at t < t_s). Flattens: quantity = the
         inventory at the flatten start, fills at start + pooled flatten offsets; pending rebalance fills after the start are
         cancelled (the executor cancels open orders first). A future-perturbation test (battery) changes every price after
         t_dec and requires the plan of A to be byte-identical.
         Frame rule (pre-declared in v1b_gate.py before any v3 number): when the live window frame gives anchor A's own post-run
         readback instant t_rb(A) (= that window's t0), fills of A are booked before it (live: 0.0% of fill notional after it);
         the per-name stop / §4-2 evaluation of A is at t_rb(A) (the executor judges on that readback), else at N+45.
  R5-06  NO GUARANTEED FILLS. Outcomes are per-REQUEST draws (hash of seed, rid, symbol, leg — no RNG state, independent of
         prices), so every path is a feasible execution history: a leg fills fully / not at all / partially, a residual is
         completed or not. v2's exit completion is gone: a sub-floor remainder stays as DUST unless the executor's own logic
         would send an order for it (a full exit is sized by the held quantity and skipped below the venue floor). Dust exposure
         is reported per window. Expectations are the MEAN over R seeded paths (seeds 0..R-1, all reported).
  R5-13  The initial state (positions from the executor's own readback at t0, NAV, rebuilt entries, stop state) is SEALED — a
         canonical JSON and its sha256 — BEFORE the run; main() writes it to disk before the first event and re-verifies after.

POOLED outcome parameters only (blind protocol for CFG-04 / CFG-06): first-leg refusal / full / zero / partial shares; one
completion probability π and maker share μ for every eligible residual (refused or rested, every arm); one slippage per leg class.
The executor's deterministic ARM ASSIGNMENT functions still run (chase_policy.plan_experiment, requote_experiment.assign) and only
their assignment COUNTS are reported — no outcome is conditioned on an arm.

Same executor code as v2, imported from the COPY of tree 409ea16 in the mirror: apply_withhold_and_reshape, RebalanceExecutor.plan,
SymbolFilters.round_qty, external_book.parse_target / target_vector / held_not_in_target / below_min_notional, legs.to_notional,
per_name_stop.evaluate / active_sets, chase_policy.plan_experiment, requote_experiment.assign.
Not modelled (stated): venue-cap clamp, placement bandit, rate limits / transport, in-flight orders at the run start, correlation
between fill probability and the subsequent price path, the producer panel's ±0.30-clipped bars (see the result doc).
Knobs (battery; all default OFF, recorded in every receipt): --no-stop, --no-min-notional, --zero-fees, --fee-asset-wrong,
--funding-sign-flip, --funding-double, and MUTATIONS that re-introduce the reviewed defects: --legacy-decision-lookahead (decision
reads the bar closing after t_dec), --legacy-book-at-decision (every fill booked at t_dec), --legacy-exit-completion (v2's
guaranteed sub-floor exit fill), --legacy-unsealed-initial (receipt counts the initial population after the run).
usage: exec_sim.py --events live --period {CAL,HOLDOUT} --out <out.json> [--last-anchor A] [--paths R] [--calib CAL.json] [--mirror DIR] [knobs]
"""
import argparse, collections, copy, hashlib, heapq, json, math, os, sys, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1b_gate as G

VERSION = "v3"
H4 = 14400
E4_FROM_ANCHOR = 1789300800           # 09-13 12Z: ef60f85 (E4: a stopped name's from_partial residual is never chased)
RQ_FIRST_ANCHOR = 1788609600          # 09-05 12Z: first anchor whose order rows carry requote_p (12aa2a1 deployed 11:48:11Z)
TRADE, HALT, HOLD, MAKER_ONLY = "TRADE", "HALT", "HOLD", "MAKER_ONLY"
KNOBS = ("no_stop", "no_min_notional", "zero_fees", "fee_asset_wrong", "funding_sign_flip", "funding_double",
         "legacy_decision_lookahead", "legacy_book_at_decision", "legacy_exit_completion", "legacy_unsealed_initial")
PRI = {"xfer": 1, "funding": 2, "fill": 3, "flatten": 4, "anchor": 5, "eval": 6, "win": 9}


def u01(seed, *key):
    """per-request uniform in [0, 1): a hash of (seed, rid, symbol, leg) — no RNG state, independent of prices and of order"""
    h = hashlib.blake2b("|".join(str(x) for x in (seed,) + key).encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") / 2.0 ** 64


def canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


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
        self.ext_cfg = dict(ext, universe_sha_pin=None, booster_sha_pin=None, f10_sha_pin=None)   # pins only refuse; every archived book the executor traded was accepted
        self.pns_conf = self.PNS.cfg(os.path.join(t, "config", "book.json"))
        assert self.pns_conf.get("_profile") == "wide" and abs(float(self.pns_conf["depth_pct"]) + 0.30) < 1e-12, self.pns_conf
        self.filters = self.BX.SymbolFilters.__new__(self.BX.SymbolFilters)
        self.filters.f = mirror.exchange_filters(); self.filters.cache_path = None
        self.stub = types.SimpleNamespace(filters=self.filters, band_bps=self.BX.DEFAULT_BAND_BPS)
        self.files = {os.path.relpath(m.__file__, mirror.root): L.sha_file(m.__file__) for m in (AL, BX, CP, RQ, AL.EXT, AL.PNS, AL.LG)}


# ───────────────────────────── decision-time timeline from the executor's own records ─────────────────────────────
def config_timeline(M, anchors):
    """gross_mult, chase weights, venue-tradable set, meta exclusions, rebalance_id and the DECISION INSTANT per nominal anchor, as
    recorded at decision time (phase_A = before orders). Carried forward over anchors without a record."""
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
        t_dec = float(rid[1:])
        assert A + 1200 < t_dec < A + 1800, (L.UA(A), rid)
        prov["t_dec_recorded" if pa else "t_dec_default_N+24"] += 1
        out[A] = {"gm": gm, "weights": w, "tradable": tr, "meta": me, "rid": rid, "rid_recorded": bool(pa), "t_dec": t_dec}
        last = {"gm": gm, "weights": w, "tradable": tr, "meta": me}
    return out, dict(prov)


def live_event_timeline(M, anchors):
    """--events live: the ACTUAL protective timeline (exogenous): flatten start instants + per-anchor TRADE / HALT / HOLD / MAKER_ONLY"""
    onom = M.orders_by_nominal()
    fl_t = collections.defaultdict(list)
    t_lo, t_hi = anchors[0], anchors[-1] + H4 + 3600
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
            kind[A] = HALT
        elif not od and fills_by_rid.get((A, "maker")) and not fills_by_rid.get((A, "topup_taker")):
            kind[A] = MAKER_ONLY
        elif not od:
            kind[A] = HOLD
        else:
            kind[A] = TRADE
    return merged, kind


def initial_stop_state(M, t0, conf):
    """per-name stop state at t0 rebuilt from the executor's own phase_C records; asserted against the recorded cooldown_n"""
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


def last_flatten_before(t0):
    """the last protective flatten (FLATTEN_CLOSURE raw file names) that started before t0, + 15 min — the book was flat then"""
    ts = []
    for p in L.FLATTEN_RAW:
        k = os.path.basename(p).split("FLATTEN-")[1][:15]
        ts.append(time.mktime(time.strptime(k, "%Y%m%dT%H%M%S")) - time.timezone)
    prev = [t for t in ts if t < t0]
    return max(prev) + 900.0


def initial_entries(M, t0, q0, panel, t_flat):
    """average entry per held name at t0, rebuilt from every trade since the book was last flat (venue rule: adds re-average,
    reductions keep the entry, a sign flip restarts at the fill price). Names whose rebuilt quantity disagrees with the t0 readback by
    > 1% start at the panel price at t0 (named)."""
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
            out[s] = panel.px(s, b0)
            named[s] = {"rebuilt_qty": q[s], "readback_qty": qq, "entry": "panel price at t0"}
    return out, named


# ───────────────────────────────────────────── the simulator ─────────────────────────────────────────────
class Sim:
    def __init__(self, M, cal, mode, knobs, X=None, panel=None, fund=None, seed=0, run_start_anchor=L.A_V1_FIRST,
                 last_anchor=L.A_V1_LAST):
        self.M, self.cal, self.mode, self.k, self.seed = M, cal, mode, dict(knobs), int(seed)
        self.p = cal["params"]
        self.X = X or ExecutorCode(M)
        self.P = panel
        if self.P is None:
            self.P = L.Panel(M); L.build_references(M, self.P)
        self.F = fund or L.FundingBook(M)
        Wall, _ = L.live_windows()
        self.frame = {L.nominal(w["t0"]): float(w["t0"]) for w in Wall}      # executor's own post-run readback per anchor
        self.W = [w for w in Wall if run_start_anchor <= L.nominal(w["t0"]) <= last_anchor]
        assert self.W and L.nominal(self.W[0]["t0"]) == run_start_anchor, "run must start at a live window's t0 readback"
        self.run_start_anchor, self.last_anchor = run_start_anchor, last_anchor
        self.t_start, self.t_end = float(self.W[0]["t0"]), float(self.W[-1]["t1"])
        self.anchors = list(range(run_start_anchor + H4, L.nominal(self.t_end) + 1, H4))
        self.cfg, self.cfg_prov = config_timeline(M, list(range(L.A_V1_FIRST, self.anchors[-1] + 1, H4)))
        self.flat_times, self.kind = live_event_timeline(M, self.anchors)
        self.xfers = [(t, a) for t, a in L.transfers() if self.t_start < t <= self.t_end]
        self.fee_switch = float(self.p["fee_rate"]["switch_ts"])
        tm = self.p["timing_offsets_after_decision_s"]
        self.tau1, self.tau2, self.tw = [float(x) for x in tm["first_leg"]], [float(x) for x in tm["later_leg"]], [float(x) for x in tm["weights"]]
        self.tauf = [float(x) for x in self.p["timing_offsets_after_flatten_start_s"]["flatten"]]
        assert abs(sum(self.tw) - 1.0) < 1e-12 and min(self.tau1 + self.tau2) > 0 and min(self.tauf) >= 0
        # ── initial state = the executor's own readback at t0 (same call as the NAV row) + NAV at t0; SEALED before any event ──
        day = time.strftime("%Y%m%d", time.gmtime(self.t_start))
        rb = [r for r in M.rows(day, "position_readback") if abs(float(r["read_ts"]) - self.t_start) < 1.0]
        assert rb, "no readback at t0"
        self.q = {r["symbol"]: float(r["venue_position_qty"]) for r in rb if float(r["venue_position_qty"]) != 0.0}
        self.nav0 = float(self.W[0]["nav0_usdt"])
        t_flat = last_flatten_before(self.t_start)
        self.entry, self.entry_named = initial_entries(M, self.t_start, self.q, self.P, t_flat)
        self.pns, self.pns_init = initial_stop_state(M, self.t_start, self.X.pns_conf)
        b0 = L.floor_b(self.t_start)
        miss = [s for s in self.q if self.P.px(s, b0) is None]
        assert not miss, f"held names without a price chain at t0: {miss}"
        self.K = self.nav0 - sum(q * self.P.px(s, b0) for s, q in self.q.items())
        self.sealed = {"utc": L.U(self.t_start), "t0": self.t_start, "readback_day": day, "n_readback_rows": len(rb),
                       "n_positions": len(self.q), "positions_qty": dict(sorted(self.q.items())), "nav0_usdt": self.nav0,
                       "cash_K0": self.K, "entries": dict(sorted(self.entry.items())), "entries_not_rebuilt": self.entry_named,
                       "entries_rebuilt_since_flat_utc": L.U(t_flat), "stop_state": {"counters": self.pns["counters"],
                       "stopped": sorted(self.pns["stopped"]), "cooldown_until": dict(sorted(self.pns["cooldown"].items()))},
                       "stop_state_provenance": self.pns_init, "run_start_anchor_utc": L.UA(run_start_anchor)}
        self.sealed = json.loads(json.dumps(self.sealed, sort_keys=True, default=str))     # a deep, canonical COPY: nothing the run mutates is shared
        self.sealed_sha = canon_sha(self.sealed)
        self.acc = collections.Counter()
        self.halt_until = None
        self.log_anchor, self.events_fired, self.diag = [], [], collections.Counter()
        self.trade_log, self.fund_log, self.depth_log, self.plan_log, self.exit_log = [], [], [], [], []
        self.decisions = {}                      # A -> the decision record (what the future-perturbation test compares)
        self.last_target = {}
        self.day_ref, self.last_eval = {}, None
        self.ev, self.seq, self.rebal_gen = [], 0, 0
        self.clamp_stats = collections.Counter()

    # ── prices / equity (every read names the bar it uses) ──
    def px(self, s, b):
        v = self.P.px(s, b)
        if v is None:
            self.diag["px_missing"] += 1
        return v

    def mv(self, b):
        return sum(q * p for s, q in self.q.items() for p in [self.px(s, b)] if p is not None)

    def equity(self, b):
        return self.K + self.mv(b)

    def gross(self, b):
        return sum(abs(q * (self.px(s, b) or 0.0)) for s, q in self.q.items())

    def floor_of(self, s):
        return 0.0 if self.k.get("no_min_notional") else float((self.X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0)

    def fee_rate(self, t, maker):
        era = "BNB_era" if t < self.fee_switch else "USDT_era"
        if self.k.get("fee_asset_wrong"):
            era = "USDT_era" if era == "BNB_era" else "BNB_era"
        if self.k.get("zero_fees"):
            return 0.0
        return float(self.p["fee_rate"][era]["maker" if maker else "taker"])

    # ── event queue ──
    def push(self, t, kind, arg):
        heapq.heappush(self.ev, (float(t), PRI[kind], self.seq, kind, arg)); self.seq += 1

    # ── one fill (a quantity fixed earlier, booked now) ──
    def book(self, t, s, dq, ref_px, slip, maker, kind, A):
        if dq == 0.0:
            return 0.0
        side = 1.0 if dq > 0 else -1.0
        px = ref_px * (1.0 + side * slip)
        cash = dq * px
        fee = abs(cash) * self.fee_rate(t, maker)
        qo = self.q.get(s, 0.0); qn = qo + dq
        if abs(qo) < 1e-15 or qo * dq > 0:
            self.entry[s] = px if abs(qo) < 1e-15 else (qo * self.entry.get(s, px) + dq * px) / qn
        elif qo * qn < 0:
            self.entry[s] = px
        if abs(qn) < 1e-9 * max(1.0, abs(qo)):
            qn = 0.0
        if qn == 0.0:
            self.q.pop(s, None); self.entry.pop(s, None)
        else:
            self.q[s] = qn
        self.K -= cash + fee
        self.trade_log.append((t, s, dq, px, cash, maker, fee, kind, A))
        self.acc["tradecash"] += cash; self.acc["fee"] += fee; self.acc["turn"] += abs(cash); self.acc["n_trades"] += 1
        self.acc[f"turn_{kind}"] += abs(cash)
        return abs(cash)

    def fill_time(self, A, t_dec, tau):
        if self.k.get("legacy_book_at_decision"):
            return t_dec
        t = t_dec + tau
        rb = self.frame.get(A)
        if rb is not None and rb > t_dec + 2.0 and t >= rb:
            self.clamp_stats["n_atoms_clamped"] += 1
            return rb - 1.0
        return t

    def schedule(self, A, t_dec, taus, s, Q, ref_px, slip, maker, kind):
        """split the fixed quantity Q over the timing atoms (last atom takes the exact remainder) and queue the fill events"""
        done = 0.0
        for i, (tau, w) in enumerate(zip(taus, self.tw)):
            dq = (Q - done) if i == len(taus) - 1 else Q * w
            done += dq
            t = self.fill_time(A, t_dec, tau)
            if t != t_dec + tau:
                self.clamp_stats["notional_clamped"] += abs(dq * ref_px)
            self.clamp_stats["notional_scheduled"] += abs(dq * ref_px)
            self.push(t, "fill", {"src": "rebal", "gen": self.rebal_gen, "s": s, "dq": dq, "ref": ref_px, "slip": slip,
                                  "maker": maker, "kind": kind, "A": A})

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

    def flatten_start(self, t, why):
        """cancel pending rebalance fills, then close the inventory held NOW over the pooled flatten timing (taker)"""
        self.rebal_gen += 1
        b = L.floor_b(t)
        n = 0
        for s, q in sorted(self.q.items()):
            P = self.px(s, b)
            if P is None:
                continue
            n += 1
            done = 0.0
            for i, (tau, w) in enumerate(zip(self.tauf, self.tw)):
                dq = (-q - done) if i == len(self.tauf) - 1 else -q * w
                done += dq
                self.push(t + tau, "fill", {"src": "flatten", "gen": None, "s": s, "dq": dq, "ref": P,
                                            "slip": float(self.p["slippage_vs_executor_mid"]["flatten"]), "maker": False, "kind": "flatten", "A": None})
        self.events_fired.append({"type": "FLATTEN", "utc": L.U(t), "why": why, "n_names": n})

    def on_fill(self, t, f):
        if f["src"] == "rebal" and f["gen"] != self.rebal_gen:
            self.diag["rebal_fills_cancelled_by_flatten"] += 1; self.diag["rebal_notional_cancelled_usdt"] += abs(f["dq"] * f["ref"])
            return
        self.book(t, f["s"], f["dq"], f["ref"], f["slip"], f["maker"], f["kind"], f["A"])

    def eval_time(self, A):
        rb = self.frame.get(A)
        t_dec = self.cfg[A]["t_dec"] if A in self.cfg else A + 1440
        return rb if (rb is not None and rb > t_dec) else A + float(self.p["eval_offset_without_frame_s"])

    def on_eval(self, A, t):
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
            loss = None if xf else ((E - ref_E) / ref_E if ref_E else None)
            if loss is not None and loss < -0.04 and (self.halt_until is None or t >= self.halt_until) and self.gross(b) > 0:
                tf = max(A + float(self.p["rule_flatten_offset_s"]), t + 1.0)
                self.push(tf, "flatten", f"§4-2 day loss {loss:+.2%} at {L.U(t)} (ref {ref_E:,.0f} @ {L.U(ref_t)}, E {E:,.0f})")
                self.halt_until = (int(t) // 86400 + 1) * 86400
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
        t_dec = c["t_dec"]
        # ★ R5-01: the decision reads the LAST COMPLETE 5-minute bar at or before t_dec (the mutation reads the one closing after it)
        b_dec = L.ceil_b(t_dec) if self.k.get("legacy_decision_lookahead") else L.floor_b(t_dec)
        ext = X.EXT.parse_target(open(tpath, "rb").read(), X.ext_cfg, A, t_dec)
        if not ext.get("ok"):
            rec["status"] = HOLD; rec["why"] = f"target invalid: {ext.get('reason')}"; self.log_anchor.append(rec); return
        an = self.M.anchor_rows().get(A)
        if an is not None:
            try:
                rec["weights_sha_matches_executor_read"] = (json.loads(an["factor_version"]).get("weights_sha") == ext["weights_sha"])
            except Exception:
                pass
        held_now = dict(self.q)                              # inventory at t_dec: every fill with t < t_dec has been booked
        pos = {s: q * self.px(s, b_dec) for s, q in held_now.items() if self.px(s, b_dec) is not None}
        held_exit = X.EXT.held_not_in_target(pos, ext["symbols"])
        symbols = sorted(set(ext["symbols"]) | set(held_exit))
        act = X.PNS.active_sets(self.pns, t_dec)
        if self.k.get("no_stop"):
            act = {"stop": set(), "cooldown": set()}
        untr = set()
        if c["tradable"] is not None:
            untr |= set(symbols) - c["tradable"]
        untr |= (c["meta"] & set(symbols)) | act["stop"] | act["cooldown"] | set(held_exit)
        E = self.equity(b_dec)
        Gs = E * float(c["gm"])
        target = X.LG.to_notional(X.EXT.target_vector(ext, symbols), symbols, Gs)
        floors = {s: self.floor_of(s) for s in target}
        dust = X.EXT.below_min_notional(target, floors, X.ext_cfg["min_notional_mult"])
        untr |= set(dust["names"])
        clamp, rs = X.AL.apply_withhold_and_reshape(target, pos, untr, Gs, floors_usdt=floors, floors_source="executor.filters.f[*].min_notional",
                                                     force_flat=act["stop"])
        mids = {s: self.px(s, b_dec) for s in target if self.px(s, b_dec) is not None}
        ro = set(clamp["reduced"]) | set(clamp["flatten_only"])
        if self.k.get("no_min_notional"):
            saved = copy.deepcopy(X.filters.f)
            for v in X.filters.f.values():
                if isinstance(v, dict) and "min_notional" in v:
                    v["min_notional"] = 0.0
        try:
            plans = X.BX.RebalanceExecutor.plan(X.stub, target, pos, mids, reduce_only_syms=ro, held_qty=dict(held_now))
        finally:
            if self.k.get("no_min_notional"):
                X.filters.f.clear(); X.filters.f.update(saved)
        self.decisions[A] = {"t_dec": t_dec, "decision_bar": b_dec, "equity": E, "sizing_gross": Gs,
                             "target": {s: float(v) for s, v in sorted(target.items())},
                             "plans": [(p["symbol"], p.get("qty"), p.get("skip")) for p in sorted(plans, key=lambda p: p["symbol"])]}
        for s, v in target.items():
            self.last_target[s] = float(v)
        # ── per-request outcomes (pooled parameters; quantities fixed here, booked at their own times) ──
        pf, pc = self.p["first_leg"], self.p["completion"]
        sl = self.p["slippage_vs_executor_mid"]
        maker_only = (st == MAKER_ONLY)
        rid = c["rid"]
        n_plan = n_skip_min = n_skip_nomid = 0; plan_turn = 0.0
        sched = collections.defaultdict(float)
        cnt = collections.Counter()
        pop, prev_sum, first_sum, refused_sum, gross_now = [], 0.0, 0.0, 0.0, 0.0
        refused_names = []
        for p in plans:
            s = p["symbol"]
            if p.get("skip") or "qty" not in p:
                n_skip_min += int(p.get("skip") == "skipped_min_notional")
                n_skip_nomid += int(p.get("skip") == "skipped_no_mid")
                self.plan_log.append((A, s, 0.0, None, float(target.get(s, 0.0)), float(p["prev_notional"]), s in act["stop"], 0.0, 0.0, p.get("skip")))
                prev_sum += float(p["prev_notional"]); gross_now += abs(float(p["prev_notional"]))
                continue
            n_plan += 1
            Q = float(p["qty"]); m = mids[s]; d = Q * m; plan_turn += abs(d); fl = self.floor_of(s)
            u1 = u01(self.seed, rid, s, "first")
            refused = u1 < pf["p_rej"]
            if refused:
                q1 = 0.0; cnt["first_refused"] += 1
            else:
                v = (u1 - pf["p_rej"]) / (1.0 - pf["p_rej"])
                if v < pf["p_full"]:
                    q1 = Q; cnt["first_full"] += 1
                elif v < pf["p_full"] + pf["p_zero"]:
                    q1 = 0.0; cnt["first_zero"] += 1
                else:
                    q1 = X.filters.round_qty(s, Q * float(pf["fbar_part"])); cnt["first_partial"] += 1
            if q1 != 0.0:
                self.schedule(A, t_dec, self.tau1, s, q1, m, float(sl["first_leg"]), True, "first")
            R = Q - q1
            qr = X.filters.round_qty(s, R) if abs(R) > 0 else 0.0
            eligible = qr != 0.0 and abs(qr) * m >= fl - 1e-12
            e4_block = (A >= E4_FROM_ANCHOR and s in act["stop"] and not refused)
            q2 = 0.0
            if eligible and not maker_only and not e4_block:
                if u01(self.seed, rid, s, "completion") < float(pc["pi_fill"]):
                    q2 = qr
                    mk = u01(self.seed, rid, s, "completion_type") < float(pc["maker_share"])
                    self.schedule(A, t_dec, self.tau2, s, q2, m, float(sl["later_leg"]), mk, "later")
                    cnt["completed_maker" if mk else "completed_taker"] += 1
                else:
                    cnt["residual_not_completed"] += 1
            elif qr != 0.0 and not eligible:
                cnt["residual_below_floor"] += 1
            elif e4_block and eligible:
                cnt["residual_e4_not_chased"] += 1
            elif maker_only and eligible:
                cnt["residual_maker_only_anchor"] += 1
            sched[s] += q1 + q2
            self.plan_log.append((A, s, Q, m, float(target.get(s, 0.0)), float(p["prev_notional"]), s in act["stop"], q1, q2, None))
            prev_sum += float(p["prev_notional"]); first_sum += q1 * m; gross_now += abs(float(p["prev_notional"]) + q1 * m)
            if refused:
                refused_sum += R * m; refused_names.append(s)
            elif R != 0.0:
                pop.append((s, R * m))
        # ── R5-06 mutation only: v2's guaranteed exit completion (a zero-target sub-floor remainder filled as maker) ──
        n_ec = 0
        if self.k.get("legacy_exit_completion"):
            for s, tv in sorted(target.items()):
                q_after = held_now.get(s, 0.0) + sched.get(s, 0.0)
                if tv != 0.0 or q_after == 0.0 or s not in mids:
                    continue
                if abs(q_after * mids[s]) < self.floor_of(s):
                    self.schedule(A, t_dec, self.tau1, s, -q_after, mids[s], float(sl["first_leg"]), True, "exit_completion"); n_ec += 1
        for s, tv in target.items():            # audit: every zero-target held name's planned remainder after this decision
            if tv == 0.0 and s in held_now and s in mids:
                self.exit_log.append((A, s, (held_now[s] + sched.get(s, 0.0)) * mids[s], self.floor_of(s), held_now[s] * mids[s]))
        # ── arm ASSIGNMENT only (the executor's own deterministic functions); counts reported, no outcome conditioned on them ──
        excl = {s: "stopped (E4)" for s in act["stop"]} if A >= E4_FROM_ANCHOR else {}
        ce = X.CP.plan_experiment(pop, rid, book_net_usdt=prev_sum + first_sum + refused_sum, book_gross_usdt=gross_now,
                                  net_basis="sim path: first-leg fills + refused residuals", weights=c["weights"], exclude=excl)
        rq_counts = collections.Counter()
        if A >= RQ_FIRST_ANCHOR:
            for s in refused_names:
                rq_counts[X.RQ.assign(rid, s, 0.5)] += 1
        rec.update({"status": st, "rid": rid, "t_dec_utc": L.U(t_dec), "decision_bar_utc": L.U(b_dec), "gm": c["gm"], "equity_at_decision": E,
                    "sizing_gross": Gs, "n_symbols": len(symbols), "n_untradable": len(untr), "n_stop": len(act["stop"]),
                    "n_cooldown": len(act["cooldown"]), "n_held_exit": len(held_exit), "n_dust_target": dust["n"],
                    "n_plans_sent": n_plan, "n_skip_min_notional": n_skip_min, "n_skip_no_price_chain": n_skip_nomid,
                    "plan_turnover": plan_turn, "outcomes": dict(cnt), "n_legacy_exit_completion": n_ec,
                    "chase_assignment_counts": ce.get("arm_counts"), "requote_assignment_counts": dict(rq_counts),
                    "chase_weights": c["weights"], "clamp_counts": {k: len(v) for k, v in clamp.items()}})
        self.log_anchor.append(rec)

    def dust_now(self, b):
        """held names below their venue floor (dust) at bar b: count, Σ|notional|, and the subset whose latest target was exactly 0"""
        n = n0 = 0; v = v0 = 0.0
        for s, q in self.q.items():
            P = self.px(s, b)
            if P is None:
                continue
            x = abs(q * P)
            if 0.0 < x < float((self.X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0):
                n += 1; v += x
                if self.last_target.get(s) == 0.0:
                    n0 += 1; v0 += x
        return {"n_dust": n, "dust_usdt": v, "n_exit_dust": n0, "exit_dust_usdt": v0}

    # ── the event loop (also driven directly by the battery's synthetic books) ──
    def dispatch(self, t, kind, arg):
        if kind == "win":
            b = L.floor_b(t)
            self.snaps[arg] = {"mv": self.mv(b), "gross": self.gross(b), "equity": self.equity(b), "dust": self.dust_now(b),
                               **{k: self.acc[k] for k in ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_first", "turn_later",
                                                           "turn_flatten", "turn_exit_completion")}}
        elif kind == "anchor":
            self.on_anchor(arg)
        elif kind == "eval":
            self.on_eval(arg, t)
        elif kind == "flatten":
            self.flatten_start(t, arg)
        elif kind == "fill":
            self.on_fill(t, arg)
        elif kind == "xfer":
            self.on_transfer(t, arg)
        elif kind == "funding":
            self.on_funding(t)

    def step_until(self, t_until=None):
        """process queued events in (time, priority, insertion) order up to and including t_until (None = all)"""
        while self.ev:
            if t_until is not None and self.ev[0][0] > t_until:
                break
            t, pri, _, kind, arg = heapq.heappop(self.ev)
            self.dispatch(t, kind, arg)

    # ── the run: one time-ordered event queue ──
    def run(self, stop_at=None):
        for w in self.W:
            self.push(w["t0"], "win", ("win0", w["idx"])); self.push(w["t1"], "win", ("win1", w["idx"]))
        for A in self.anchors:
            self.push(self.cfg[A]["t_dec"], "anchor", A)
            self.push(self.eval_time(A), "eval", A)
        if self.mode == "live":
            for t in self.flat_times:
                if self.t_start < t <= self.t_end:
                    self.push(t, "flatten", "live protective flatten (exogenous)")
        for t, a in self.xfers:
            self.push(t, "xfer", a)
        for t in sorted({t for (s, t) in self.F.rate if self.t_start < t <= self.t_end}):
            self.push(float(t), "funding", None)
        self.snaps = {}
        self.step_until(stop_at)
        snaps = self.snaps
        out = []
        for w in self.W:
            if ("win0", w["idx"]) not in snaps or ("win1", w["idx"]) not in snaps:
                continue
            a, z = snaps[("win0", w["idx"])], snaps[("win1", w["idx"])]
            d = {k: z[k] - a[k] for k in ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_first", "turn_later", "turn_flatten",
                                           "turn_exit_completion")}
            out.append({"idx": w["idx"], "from": w["from"], "to": w["to"], "t0": w["t0"], "t1": w["t1"], "gross0": a["gross"], "nav0": a["equity"],
                        "price_trade": (z["mv"] - a["mv"]) - d["tradecash"], "funding": d["fund"], "fee": d["fee"], "turnover": d["turn"],
                        "turnover_first": d["turn_first"], "turnover_later": d["turn_later"], "turnover_flatten": d["turn_flatten"],
                        "turnover_exit_completion": d["turn_exit_completion"], "transfer": d["xfer"], "n_trades": d["n_trades"],
                        "equity1": z["equity"], "gross1": z["gross"], **{"end_" + k: v for k, v in z["dust"].items()}})
        return out


def initial_block(S, knobs):
    """the receipt's initial-state block. Sealed before the run (R5-13); the legacy mutation reproduces v2 (len(q) AFTER the run)."""
    if knobs.get("legacy_unsealed_initial"):
        return {"utc": L.U(S.t_start), "nav0": S.nav0, "n_positions": len(S.q), "sealed_before_run": False}
    return {"sealed_before_run": True, "sha256": S.sealed_sha, "n_positions": S.sealed["n_positions"], "nav0": S.nav0,
            "utc": S.sealed["utc"], "state": S.sealed}


NUM = ("gross0", "nav0", "price_trade", "funding", "fee", "turnover", "turnover_first", "turnover_later", "turnover_flatten",
       "turnover_exit_completion", "transfer", "n_trades", "equity1", "gross1", "end_n_dust", "end_dust_usdt", "end_n_exit_dust",
       "end_exit_dust_usdt")


def aggregate(paths):
    """per-window MEAN over paths (the V1b sim side) and the 5% / 95% path quantiles"""
    import numpy as np
    base = paths[0]
    mean, lo, hi = [], [], []
    for i, w in enumerate(base):
        assert all(p[i]["idx"] == w["idx"] and p[i]["t0"] == w["t0"] and p[i]["t1"] == w["t1"] for p in paths)
        keys = {k: w[k] for k in ("idx", "from", "to", "t0", "t1")}
        arr = {k: np.array([float(p[i][k]) for p in paths]) for k in NUM}
        mean.append(dict(keys, **{k: float(v.mean()) for k, v in arr.items()}))
        lo.append(dict(keys, **{k: float(np.percentile(v, 5)) for k, v in arr.items()}))
        hi.append(dict(keys, **{k: float(np.percentile(v, 95)) for k, v in arr.items()}))
    return mean, lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", choices=("live", "rule"), required=True)
    ap.add_argument("--period", choices=("CAL", "HOLDOUT"), required=True, help="run start as declared in v1b_gate.PERIODS")
    ap.add_argument("--last-anchor", type=int, default=L.A_V1_LAST)
    ap.add_argument("--paths", type=int, default=G.R_MIN)
    ap.add_argument("--out", required=True)
    ap.add_argument("--calib", default=os.path.join(HERE, "CALIBRATION_v3_POOLED_20260826_20260910.json"))
    ap.add_argument("--mirror", default=L.MIRROR_DEFAULT)
    for k in KNOBS:
        ap.add_argument("--" + k.replace("_", "-"), action="store_true")
    a = ap.parse_args()
    knobs = {k: bool(getattr(a, k)) for k in KNOBS}
    M = L.Mirror(a.mirror)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    assert not bad, f"mirror differs from INPUT_MANIFEST: {bad[:5]}"
    cal = json.load(open(a.calib))
    assert cal.get("frozen_before_holdout") is True and cal.get("kind") == "v3_pooled", "v3 needs a frozen v3 pooled calibration"
    rs = G.PERIODS[a.period]["run_start_anchor"]
    t0 = time.time()
    X = ExecutorCode(M); P = L.Panel(M); L.build_references(M, P); F = L.FundingBook(M)
    seeds = list(range(a.paths))
    paths, summaries, sealed_sha, S0 = [], [], None, None
    seal_path = os.path.splitext(a.out)[0] + "_INITIAL_STATE.json"
    for sd in seeds:
        S = Sim(M, cal, a.events, knobs, X=X, panel=P, fund=F, seed=sd, run_start_anchor=rs, last_anchor=a.last_anchor)
        if sd == 0:
            # ★ R5-13: the initial state is written to disk and its sha fixed BEFORE the first event is processed
            with open(seal_path + ".part", "w") as fh:
                json.dump({"sha256": S.sealed_sha, "state": S.sealed}, fh, indent=1, sort_keys=True, default=str)
            os.replace(seal_path + ".part", seal_path)
            sealed_sha = S.sealed_sha
        assert S.sealed_sha == sealed_sha, "initial state differs between paths"
        W = S.run()
        paths.append(W)
        summaries.append({"seed": sd, "n_trade_legs": len(S.trade_log), "net_pnl": sum(w["price_trade"] + w["funding"] - w["fee"] for w in W),
                          "price_trade": sum(w["price_trade"] for w in W), "funding": sum(w["funding"] for w in W), "fee": sum(w["fee"] for w in W),
                          "turnover": sum(w["turnover"] for w in W), "final_equity": W[-1]["equity1"], "n_positions_final": len(S.q),
                          "events": dict(collections.Counter(e["type"] for e in S.events_fired)), "diag": dict(S.diag),
                          "clamp": dict(S.clamp_stats),
                          "outcomes": dict(sum((collections.Counter(r.get("outcomes") or {}) for r in S.log_anchor), collections.Counter())),
                          "chase_assignment": dict(sum((collections.Counter(r.get("chase_assignment_counts") or {}) for r in S.log_anchor), collections.Counter())),
                          "requote_assignment": dict(sum((collections.Counter(r.get("requote_assignment_counts") or {}) for r in S.log_anchor), collections.Counter()))})
        if sd == 0:
            S0 = S
        print(f"  path seed {sd}: net {summaries[-1]['net_pnl']:+,.2f}  legs {len(S.trade_log)}  ({time.time() - t0:.0f} s)", flush=True)
    chk = json.load(open(seal_path))
    assert chk["sha256"] == sealed_sha == canon_sha(chk["state"]), "sealed initial state changed on disk during the run"
    mean, lo, hi = aggregate(paths)
    import numpy as np
    dust = {"per_window_mean_n_dust": {"mean": float(np.mean([w["end_n_dust"] for w in mean])), "max": float(max(w["end_n_dust"] for w in mean))},
            "per_window_mean_dust_usdt": {"mean": float(np.mean([w["end_dust_usdt"] for w in mean])), "max": float(max(w["end_dust_usdt"] for w in mean))},
            "per_window_mean_exit_dust_usdt": {"mean": float(np.mean([w["end_exit_dust_usdt"] for w in mean])), "max": float(max(w["end_exit_dust_usdt"] for w in mean))},
            "dust_over_gross_bps": {"mean": float(np.mean([w["end_dust_usdt"] / w["gross1"] * 1e4 for w in mean if w["gross1"] > 0])),
                                    "max": float(max(w["end_dust_usdt"] / w["gross1"] * 1e4 for w in mean if w["gross1"] > 0))}}
    doc = {"device": "exec_sim.py", "version": VERSION, "device_sha256": L.sha_file(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": "cd " + os.path.relpath(HERE, L.REPO) + " && /usr/bin/python3 exec_sim.py " + " ".join(sys.argv[1:]),
           "argv": sys.argv[1:], "mode": a.events, "knobs": knobs, "runtime_s": round(time.time() - t0, 1),
           "period": {"label": a.period, "run_start_anchor": rs, "run_start_utc": L.UA(rs), "last_anchor": a.last_anchor,
                      "last_anchor_utc": L.UA(a.last_anchor), "declared": G.PERIODS[a.period]},
           "paths": {"seeds": seeds, "n": len(seeds), "draws": "per-request blake2b(seed|rid|symbol|leg) uniforms"},
           "calibration": {"path": os.path.relpath(os.path.abspath(a.calib), L.REPO), "sha256": L.sha_file(a.calib)},
           "inputs_sha256": L.input_shas(M, extra=[a.calib, os.path.join(HERE, "v1b_gate.py")]), "executor_code_files_sha256": X.files,
           "config_timeline_provenance": S0.cfg_prov,
           "initial_state_sealed": dict(initial_block(S0, knobs), sealed_file=os.path.relpath(seal_path, L.REPO)),
           "timing_model": {"first_leg_offsets_s": S0.tau1, "later_leg_offsets_s": S0.tau2, "flatten_offsets_s": S0.tauf, "weights": S0.tw,
                            "frame_rule": "fills of anchor A booked before A's own post-run readback (live window t0) when it exists; evaluation at that readback, else N+45"},
           "event_timeline": {"mode": a.events, "live_flatten_utc": [L.U(t) for t in S0.flat_times],
                              "anchor_kind_counts": dict(collections.Counter(S0.kind.values())),
                              "non_trade_anchors_live": {L.UA(A): k for A, k in S0.kind.items() if k != TRADE}},
           "path_summaries": summaries, "dust_exposure": dust,
           "funding_xcheck": F.xcheck, "funding_source": dict(F.src),
           "panel": {"n_refs": len(P.ref), "span": f"{L.U(P.t_first)}..{L.U(P.t_last)}"},
           "anchors_seed0": S0.log_anchor, "events_fired_seed0": S0.events_fired,
           "windows": mean, "windows_path_p05": lo, "windows_path_p95": hi,
           "path_band_coverage_note": "windows_path_p05 / _p95 = 5% / 95% quantiles over the R paths per window (diagnostic)"}
    with open(a.out + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    os.replace(a.out + ".part", a.out)
    n_st = collections.Counter(r["status"] for r in S0.log_anchor)
    print(f"exec_sim v3 {a.events} {a.period}: {len(mean)} windows × {len(seeds)} paths, anchors {dict(n_st)}, runtime {doc['runtime_s']} s -> {a.out}")


if __name__ == "__main__":
    main()
