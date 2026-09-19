#!/usr/bin/env python3
"""r_hist_sim.py — stream R HISTORICAL ADAPTER for the stream-E executor simulator (exec_sim.py v2, sha 2638316b…, imported UNCHANGED from a
sha-verified copy of multi_asset/exports/research/replay_exec_2026-09-19/). Library module; the driver is r_launch.py.

What is reused verbatim (exec_sim.Sim methods, not re-implemented): on_anchor (parse_target → withhold / held-exit / stop / cooldown / dust →
apply_withhold_and_reshape → RebalanceExecutor.plan → expected-value fill model from CALIBRATION_FROZEN bf487711 → exit completion), trade,
on_funding, flatten, on_stop_eval (per_name_stop.evaluate wide profile + the §4-2 −4% day rule), status, px / mv / equity / gross, fee_rate.
The executor's own functions come from the 409ea16 tree copy exactly as in stream E (ExecutorCode).

What this module replaces (the live-only inputs of Sim.__init__ / run, all stated in the RESULT doc):
  HistMirror    target_live/<A>.json = a file this adapter writes just before the anchor's decision from the S2 book (P2-CMB or P2-LIT,
                S2 A6.2 definitions via p2_s2_lib.books), deleted after; no fresh target ⇒ no file ⇒ the executor's own on_unavailable=hold.
                written_utc = A+20 min (producer write time), universe = the S2 PIT universe row at A (the list production signs).
                anchor_rows() = {} (no live weights_sha to cross-check).
  HistPanel     absolute price at a 5-minute boundary from r_prices.py's log-price table (holefix2 cache, RAW-restored on clipped bars,
                4h-compounding gated against meta RAW y4 ≤ 1e-6); None before a symbol's first finite bar.
  RateMap       settlement rates from P2 ledger_full.npz (zip ∪ API, per symbol per fundingTime) in the (symbol, time) → rate interface
                on_funding reads; built one settlement time at a time (memory).
  CfgMap        per-anchor config = the CURRENT production configuration throughout: gross_mult 2.0; chase weights 0.5/0.5; venue-tradable
                set = research tradability_v1 W24H state == TRADABLE at A (≥ 1 traded 5m bar in (A−24h, A]); meta exclusions none (the PIT
                universe is crypto-only already); rid = "A{A+1439}" (the executor's rebalance-id form: run start N+23:59).
  params        calibration numbers unchanged; the requote timeline is the current one from anchor 0 (executor_hash, p = 0.5); fee era =
                USDT (maker/taker rates of the calibration's USDT_era) for every trade; E4 (stopped names never chased) from anchor 0.
  state         flat book, 100,000 USDT at the first scored anchor; stop state empty; no external transfers (B32 never fires).
  run()         windows = [A, A+4h) for every scored anchor (the stream-E run() uses the LIVE_G windows); events at the same offsets
                (decision N+24:00 → fills at the N+25 boundary, stop evaluation N+40, rule flatten N+46 → next boundary, funding at each
                settlement, snapshots at A).
  audit logs    trade_log / fund_log / exit_log keep running invariants instead of storing ~10^7 tuples (fee = |notional| × rate;
                funding = −q·P·rate; an exited name is flat or ≥ its floor after the decision); depth_log / plan_log are not kept.
"""
import collections, copy, hashlib, json, math, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
DEC_OFF, STOP_OFF = 1500, 2400


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


class NullLog(list):
    def append(self, x): pass


class TradeAudit(list):
    def __init__(self, sim): super().__init__(); self.sim = sim; self.n = 0; self.max_fee_err = 0.0; self.kind = collections.Counter(); self.notional = collections.Counter()
    def append(self, x):
        t, s, cash, maker, fee, kind = x; self.n += 1
        exp = abs(cash) * self.sim.fee_rate(t, maker); self.max_fee_err = max(self.max_fee_err, abs(fee - exp))
        self.kind[kind] += 1; self.notional["maker" if maker else "taker"] += abs(cash)


class FundAudit(list):
    def __init__(self): super().__init__(); self.n = 0; self.max_err = 0.0; self.seen = set(); self.dup = 0
    def append(self, x):
        t, s, q, P, r, f = x; self.n += 1; self.max_err = max(self.max_err, abs(f - (-q * P * r)))
        k = (s, int(t))
        if k in self.seen: self.dup += 1
        self.seen.add(k)
        if len(self.seen) > 200000: self.seen = set()          # bounded; duplicates can only occur at the same time stamp


class ExitAudit(list):
    def __init__(self): super().__init__(); self.n = 0; self.tails = 0
    def append(self, x):
        A, s, rem, fl = x; self.n += 1
        if rem != 0.0 and abs(rem) < fl - 1e-9: self.tails += 1


class HistMirror:
    def __init__(self, root, target_dir):
        self.root = os.path.abspath(root); self.tree = os.path.join(self.root, "exec_tree_409ea16"); self.tdir = target_dir
        os.makedirs(target_dir, exist_ok=True)
    def exchange_filters(self): return json.load(open(os.path.join(self.root, "state", "exchange_info_cache.json")))
    def target_path(self, A): return os.path.join(self.tdir, f"{int(A)}.json")
    def anchor_rows(self): return {}


class HistPanel:
    def __init__(self, LP, bounds, syms, first_fin, cref, ref_px):
        self.LP = LP; self.row = {int(b): i for i, b in enumerate(bounds)}; self.sidx = {s: j for j, s in enumerate(syms)}
        self.first_fin = first_fin; self.cref = cref; self.ref_px = ref_px; self.ref = {s: True for s in syms}
        self.t_first, self.t_last = int(bounds[0]), int(bounds[-1])
    def px(self, sym, b):
        j = self.sidx.get(sym)
        if j is None: return None
        ff = self.first_fin[j]
        if ff < 0 or int(b) < ff: return None
        return float(self.ref_px[j] * math.exp(self.LP[self.row[int(b)], j] - self.cref[j]))


class RateMap:
    """rate.get((symbol, t)) over settlement arrays sorted by time; the dict of the current time stamp is built on first use"""
    def __init__(self, t_sorted, sym_idx, rate, syms):
        self.t = t_sorted; self.j = sym_idx; self.r = rate; self.syms = syms
        self.times = np.unique(t_sorted); self.lo = np.searchsorted(t_sorted, self.times, "left"); self.hi = np.searchsorted(t_sorted, self.times, "right")
        self.pos = {int(t): k for k, t in enumerate(self.times)}; self.cur_t = None; self.cur = {}
    def get(self, key, default=None):
        s, t = key; t = int(t)
        if t != self.cur_t:
            k = self.pos.get(t)
            self.cur = {} if k is None else {self.syms[int(j)]: float(r) for j, r in zip(self.j[self.lo[k]:self.hi[k]], self.r[self.lo[k]:self.hi[k]])}
            self.cur_t = t
        return self.cur.get(s, default)


class HistFunding:
    def __init__(self, ledger_npz, syms, t_lo, t_hi):
        Z = np.load(ledger_npz, allow_pickle=True); off = Z["off"]; ft = Z["ft"].astype(np.int64); rt = Z["rate"].astype(np.float64)
        assert [str(s) for s in Z["symbols"]] == list(syms)
        jj = np.repeat(np.arange(len(syms)), np.diff(off)); m = (ft > t_lo) & (ft <= t_hi)
        o = np.argsort(ft[m], kind="stable"); self.rate = RateMap(ft[m][o], jj[m][o], rt[m][o], list(syms))
        self.times = [int(t) for t in self.rate.times]; self.n_rows = int(m.sum())
        self.xcheck = {"source": "P2 ledger_full.npz (zip ∪ API, per fundingTime)"}; self.src = collections.Counter()


class CfgMap:
    def __init__(self, tr_state, tr_row, syms, gm, weights):
        self.tr = tr_state; self.row = tr_row; self.syms = np.array(syms); self.gm = gm; self.w = dict(weights); self.cache = {}
    def __getitem__(self, A):
        A = int(A)
        if A not in self.cache:
            self.cache = {A: {"gm": self.gm, "weights": dict(self.w), "tradable": set(self.syms[self.tr[self.row[A]] == 2].tolist()), "meta": set(),
                              "rid": f"A{A + 1439}", "rid_recorded": False}}
        return self.cache[A]


def target_doc(A, w_row, syms, universe, tag, EXT):
    nz = np.nonzero(np.abs(w_row) > 0)[0]
    weights = {syms[j]: float(w_row[j]) for j in sorted(nz, key=lambda j: syms[j])}
    if not weights: return None
    gn = float(sum(abs(v) for v in weights.values()))
    body = json.dumps(weights, separators=(",", ":")).encode()
    return {"schema": "wide_target_v1", "anchor_ts": int(A), "weights": weights, "universe": list(universe), "universe_sha": EXT.universe_sha(list(universe)),
            "booster_sha": "replay_r:" + tag, "weights_sha": hashlib.sha256(body).hexdigest(), "written_utc": time.strftime(UTC_FMT, time.gmtime(int(A) + 1200)),
            "gross_norm": gn, "n_names": len(weights), "producer": "replay_r_hist " + tag}


def make_sim_class(ES):
    class HistSim(ES.Sim):
        def __init__(self, M, cal, params, mode, knobs, X, panel, fund, anchors, cfg, book, fresh, universe_rows, syms, tag, nav0):
            self.M, self.cal, self.mode, self.k = M, cal, mode, dict(knobs)
            self.p = params; self.X = X; self.P = panel; self.F = fund; self.cfg = cfg
            self.anchors = [int(a) for a in anchors]; self.t_start = self.anchors[0]; self.t_end = self.anchors[-1] + 14400
            self.kind, self.flat_times, self.xfers = {}, [], []
            self.fee_switch = -math.inf                                # every trade in the USDT era (current)
            self.q, self.entry, self.entry_named = {}, {}, {}
            self.nav0 = float(nav0); self.K = float(nav0)
            self.pns = {"counters": {}, "stopped": {}, "cooldown": {}}; self.pns_init = {"note": "flat start, empty stop state"}
            self.acc = collections.Counter(); self.halt_until = None; self.pending_flatten = None
            self.log_anchor, self.events_fired, self.diag = [], [], collections.Counter()
            self.trade_log = TradeAudit(self); self.fund_log = FundAudit(); self.depth_log = NullLog(); self.plan_log = NullLog(); self.exit_log = ExitAudit()
            self.day_ref, self.last_eval = {}, None
            self.book, self.fresh, self.urows, self.syms, self.tag = book, fresh, universe_rows, syms, tag
            self.aidx = {a: i for i, a in enumerate(self.anchors)}
            self.tstats = collections.Counter(); self.stop_log, self.flat_log = [], []; self.n_stop_ev = 0; self.n_flat_ev = 0
        def write_target(self, A):
            i = self.aidx[A]; p = self.M.target_path(A)
            if os.path.exists(p): os.remove(p)
            if not self.fresh[i]:
                self.tstats["no_fresh_target"] += 1; return False
            uni = [self.syms[j] for j in np.nonzero(self.urows[i])[0]]
            doc = target_doc(A, self.book[i], self.syms, uni, self.tag, self.X.EXT)
            if doc is None:
                self.tstats["empty_target"] += 1; return False
            out = set(doc["weights"]) - set(uni)
            if out: self.tstats["anchors_with_weights_outside_universe"] += 1; self.tstats["names_outside_universe"] += len(out)
            with open(p + ".tmp", "w") as fh: json.dump(doc, fh)
            os.replace(p + ".tmp", p); self.tstats["written"] += 1
            return True
        def on_stop_eval(self, A, t):
            n0 = len(self.events_fired)
            super().on_stop_eval(A, t)
            for e in self.events_fired[n0:]:
                if e["type"] == "STOP": self.stop_log.append((int(A), e["symbol"])); self.n_stop_ev += 1
        def flatten(self, t, why):
            super().flatten(t, why); self.n_flat_ev += 1; self.flat_log.append((float(t), why))
        def on_anchor(self, A):
            wrote = self.write_target(A)
            try:
                super().on_anchor(A)
            finally:
                p = self.M.target_path(A)
                if wrote and os.path.exists(p): os.remove(p)
        def run(self):
            ev = []
            for k, A in enumerate(self.anchors):
                ev.append((A, 9, "win0", k)); ev.append((A + 14400, 9, "win1", k))
                ev.append((A + int(self.p["decision_boundary_offset_s"]) - 60, 5, "anchor", A))
                ev.append((A + int(self.p["stop_eval_offset_s"]), 6, "stop_eval", A))
            for t in self.F.times:
                if self.t_start < t <= self.t_end: ev.append((float(t), 2, "funding", None))
            ev.sort(key=lambda e: (e[0], e[1]))
            snaps = {}; i = 0
            fl = ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_maker", "turn_taker", "turn_flatten", "turn_exit_completion")
            while i < len(ev):
                t, pri, kind, arg = ev[i]; i += 1
                if self.pending_flatten is not None and self.pending_flatten[0] <= t:
                    tf, why = self.pending_flatten; self.pending_flatten = None
                    self.flatten(tf, why)
                if kind in ("win0", "win1"):
                    b = int(t) // 300 * 300; nl = 0.0
                    for s, q in self.q.items():
                        pp = self.px(s, b)
                        if pp is not None: nl += q * pp
                    snaps[(kind, arg)] = {"mv": self.mv(b), "gross": self.gross(b), "equity": self.equity(b), "net": nl, "n_pos": len(self.q), "n_stop_ev": self.n_stop_ev, "n_flat_ev": self.n_flat_ev,
                                          **{k: self.acc[k] for k in fl}}
                elif kind == "anchor":
                    self.on_anchor(arg)
                elif kind == "stop_eval":
                    self.on_stop_eval(arg, t)
                elif kind == "funding":
                    self.on_funding(t)
            out = []
            for k, A in enumerate(self.anchors):
                a, z = snaps[("win0", k)], snaps[("win1", k)]
                d = {c: z[c] - a[c] for c in fl}
                out.append({"A": A, "gross0": a["gross"], "net0": a["net"], "n_pos0": a["n_pos"], "nav0": a["equity"], "nav1": z["equity"],
                            "price_trade": (z["mv"] - a["mv"]) - d["tradecash"], "funding": d["fund"], "fee": d["fee"], "turnover": d["turn"],
                            "turnover_maker": d["turn_maker"], "turnover_taker": d["turn_taker"], "turnover_flatten": d["turn_flatten"],
                            "turnover_exit_completion": d["turn_exit_completion"], "transfer": d["xfer"], "n_trades": d["n_trades"],
                            "n_stop_events": z["n_stop_ev"] - a["n_stop_ev"], "n_flatten_events": z["n_flat_ev"] - a["n_flat_ev"]})
            return out
    return HistSim
