#!/usr/bin/env python3
"""bt_hist_sim31.py — HISTORY ADAPTER for executor simulator v3.1 (replay_exec_2026-09-19/exec_sim.py sha 29679672, imported UNCHANGED
from a sha-verified copy). Library module; the driver is bt_launch.py. Port of stream R's r_hist_sim.py (bc57c865, written for v2) to v3.1.

Reused verbatim from exec_sim.Sim (v3.1): on_anchor (parse_target → withhold / held-exit / stop / cooldown / dust → apply_withhold_and_reshape →
RebalanceExecutor.plan → per-request pooled draws, quantities fixed at the decision, every fill an EVENT at t_dec + pooled offsets priced at
the decision-visible bar × (1 ± pooled slippage)), schedule / fill_time / book, on_fill (a §4-2 flatten cancels pending rebalance fills),
flatten_start (inventory held at the flatten start, pooled flatten offsets), on_funding (inventory held at the settlement instant),
on_eval (per_name_stop.evaluate wide profile + the §4-2 −4 % day rule), status (rule mode: HALT until the next UTC day), px / mv / equity /
gross / fee_rate / dust_now, step ordering (time, priority, insertion).
Replaced (the live-only parts of Sim.__init__ / run; each stated in the receipt):
  __init__      flat book, NAV0 USDT at the first anchor; empty stop state; no transfers; no live readback frames (self.frame = {}) ⇒ the
                stop / §4-2 evaluation of A is at A + eval_offset_without_frame_s (N+45, the calibration's own rule without a frame);
                t_dec(A) = A + decision_offset_default_s (N+24:00; v3.1's own rule where no rid was recorded), rid = "A{t_dec}";
                fee era = USDT for every trade (current); config per anchor = CfgMap31 (gm 2.0, chase weights, tradable = W24H TRADABLE at A).
  targets       HistMirror + target_doc (verbatim from r_hist_sim.py): the S2 book row written as a wide_target_v1 file just before the decision
                (written_utc = A+20 min), parsed by the executor's own external_book.parse_target, deleted after; no fresh target ⇒ no file ⇒
                the executor's own on_unavailable = hold.
  prices        FullPanel over a FULL 5-minute log-price grid (bt_prices_full.py; bitwise equal to the pinned table at every pinned sample).
  run()         one heap in v3.1's (time, priority, insertion) order: boundary snapshots at every anchor A (priority 'win', after all other
                events at A), decisions, evaluations, fills, flattens, funding at every settlement; a 5-minute NAV sampler that, before an event
                at time t is processed, records NAV(b) = K + Σ q·P(b) for every grid boundary b < t (so NAV(b) is the state after every event
                with time ≤ b — the same convention as the window snapshot).
  logs          audits keep running invariants instead of ~10^7 tuples (fee = |cash| × rate; funding = −q·P·rate, no duplicate (sym, t));
                decisions keep a digest per anchor (full records only for anchors named by the battery).
UNAVAILABLE bars (3,084 bars with no official kline: halts / relistings / token swaps) — NAMED, PLUGGABLE policies, recorded in every output:
  LEGACY-ZERO-RETURN  the table's value is used as is (0 return through the gap, the stream-R v2 behaviour); NOT silent: every window in
                      which a held name has an UNAVAILABLE bar (or, for the old table, any cache-NaN bar it priced at 0) is counted with its
                      notional and its price / funding P&L.
  UA-FREEZE-EXCLUDE   docs/PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19.md AMENDMENT 1 §A1.2 (f4ad35ce2), mapped to the
                      executor-simulation layer E2 as follows (the mapping is this device's, written before any number):
                      (A) pricing: name s in window [A, A+4h] with ANY UNAVAILABLE bar closing in [A, A+4h] (the endpoint bar A included) is an
                          UNKNOWN cell; its price-and-trading P&L and its funding in that window are REMOVED from the main NAV numerator and
                          booked in a separate UNKNOWN column; fees stay in the main reading; the denominator (window-start NAV × gm) is
                          unchanged; notional at risk = Σ|q·P| of those names at the window start; bounds for the excluded amount: UNBOUNDED
                          (no official bar ⇒ no feasible band, RESULT_raw_price_restore §4).
                      (B) trading: s is not traded at anchor A (its plan row becomes skip='ua_frozen', the position is held) when the bar
                          closing at A (the anchor's boundary price) OR the decision bar floor_b(t_dec) is UNAVAILABLE for s.
                      (B') a fill event of s whose bar (closing at ceil_b(t)) is UNAVAILABLE is not booked (the venue had no trades then).
                      The simulator state (sizing equity, stop evaluation, §4-2) keeps valuing a frozen name at the table's last price; only the
                      main reading excludes the UNKNOWN cells. Counts per window / anchor: cells, names, notional, frozen names / notional,
                      cancelled fills / notional.
"""
import collections, copy, hashlib, heapq, json, math, os, time, types

import numpy as np

H4 = 14400
ROW = 300
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
POLICIES = ("LEGACY-ZERO-RETURN", "UA-FREEZE-EXCLUDE")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


class NullLog(list):
    def append(self, x): pass


class TradeAudit(list):
    """v3.1 trade tuple (t, s, dq, px, cash, maker, fee, kind, A): fee = |cash| × fee_rate(t, maker), counts by kind"""
    def __init__(self, sim):
        super().__init__(); self.sim = sim; self.n = 0; self.max_fee_err = 0.0; self.kind = collections.Counter(); self.notional = collections.Counter(); self.last = None
    def append(self, x):
        t, s, dq, px, cash, maker, fee, kind, A = x; self.n += 1; self.last = x
        self.max_fee_err = max(self.max_fee_err, abs(fee - abs(cash) * self.sim.fee_rate(t, maker)))
        self.kind[kind] += 1; self.notional["maker" if maker else "taker"] += abs(cash)


class FundAudit(list):
    """v3.1 funding tuple (t, s, q, P, r, f): f = −q·P·r; duplicate (symbol, time) charges; per-row hook for the UNKNOWN column"""
    def __init__(self, hook):
        super().__init__(); self.n = 0; self.max_err = 0.0; self.dup = 0; self.cur_t = None; self.seen = set(); self.hook = hook
    def append(self, x):
        t, s, q, P, r, f = x; self.n += 1; self.max_err = max(self.max_err, abs(f - (-q * P * r)))
        if t != self.cur_t: self.cur_t = t; self.seen = set()
        if s in self.seen: self.dup += 1
        self.seen.add(s); self.hook(s, f)


class ExitAudit(list):
    """v3.1 exit tuple (A, s, remainder notional after the decision, floor, held notional): v3.1 has NO guaranteed exit — a sub-floor
    remainder is dust by construction; counted, not a violation"""
    def __init__(self): super().__init__(); self.n = 0; self.subfloor = 0
    def append(self, x):
        A, s, rem, fl, held = x; self.n += 1
        if rem != 0.0 and abs(rem) < fl - 1e-9: self.subfloor += 1


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=repr)


class DecisionStore(dict):
    """exec_sim stores the full decision record per anchor (~400 target entries): keep a sha256 digest per anchor ('digest'), nothing
    ('none'), and the full record only for anchors in `keep`"""
    def __init__(self, mode="none", keep=()):
        super().__init__(); self.mode = mode; self.keep = set(int(a) for a in keep); self.full = {}
    def __setitem__(self, A, rec):
        if int(A) in self.keep: self.full[int(A)] = json.loads(canon(rec))
        if self.mode == "digest" or int(A) in self.keep: dict.__setitem__(self, A, hashlib.sha256(canon(rec).encode()).hexdigest())


class HistMirror:
    """verbatim from r_hist_sim.py: the executor-tree copy + exchange filters; target_live/<A>.json in a private temp dir"""
    def __init__(self, root, target_dir):
        self.root = os.path.abspath(root); self.tree = os.path.join(self.root, "exec_tree_409ea16"); self.tdir = target_dir
        os.makedirs(target_dir, exist_ok=True)
    def exchange_filters(self): return json.load(open(os.path.join(self.root, "state", "exchange_info_cache.json")))
    def target_path(self, A): return os.path.join(self.tdir, f"{int(A)}.json")
    def anchor_rows(self): return {}


class FullPanel:
    """absolute price at a 5-minute boundary from a full-grid log-price table: ref_px · exp(LP[b] − cref); None before the first finite bar"""
    def __init__(self, LP, grid0, syms, first_fin, cref, ref_px):
        self.LP = LP; self.g0 = int(grid0); self.n = LP.shape[0]; self.sidx = {s: j for j, s in enumerate(syms)}
        self.first_fin = np.asarray(first_fin, np.int64); self.cref = np.asarray(cref, np.float64); self.ref_px = np.asarray(ref_px, np.float64)
        self.ff_list = self.first_fin.tolist(); self.cref_list = self.cref.tolist(); self.ref_list = self.ref_px.tolist()
        self.t_first, self.t_last = self.g0, self.g0 + (self.n - 1) * ROW
    def row(self, b):
        r = (int(b) - self.g0) // ROW
        assert (int(b) - self.g0) % ROW == 0 and 0 <= r < self.n, f"boundary {b} off the price grid"
        return r
    def ua_hold(self, ua_index, dry=False):
        """UA-FREEZE-EXCLUDE (V): the value at an UNAVAILABLE bar is the last AVAILABLE bar's value (the table's content at a UA bar is never
        read). Returns the number of cells whose value differs from that (0 on a table that carries 0 returns there); applies it unless dry."""
        n = 0; off = (ua_index.g0 - self.g0) // ROW
        for c, rows in ua_index.by_col.items():
            last = None; run_prev = -1
            for r in rows.tolist():
                pr = r + off
                if last is None or r != last + 1: run_prev = pr - 1          # a new gap run: its last available bar is the one before it
                last = r
                if not (0 <= pr < self.n) or not (0 <= run_prev < self.n): continue
                if self.LP[pr, c] != self.LP[run_prev, c]:
                    n += 1
                    if not dry: self.LP[pr, c] = self.LP[run_prev, c]
        if not dry: self.ua_held_cells = n
        return n

    def px(self, sym, b):
        j = self.sidx.get(sym)
        if j is None: return None
        ff = self.ff_list[j]
        if ff < 0 or int(b) < ff: return None
        return float(self.ref_list[j] * math.exp(self.LP[self.row(b), j] - self.cref_list[j]))


class RateMap:
    """verbatim from r_hist_sim.py: rate.get((symbol, t)) over settlement arrays sorted by time"""
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
    """verbatim from r_hist_sim.py: P2 ledger_full.npz (zip ∪ API, per symbol per fundingTime)"""
    def __init__(self, ledger_npz, syms, t_lo, t_hi):
        Z = np.load(ledger_npz, allow_pickle=True); off = Z["off"]; ft = Z["ft"].astype(np.int64); rt = Z["rate"].astype(np.float64)
        assert [str(s) for s in Z["symbols"]] == list(syms)
        jj = np.repeat(np.arange(len(syms)), np.diff(off)); m = (ft > t_lo) & (ft <= t_hi)
        o = np.argsort(ft[m], kind="stable"); self.rate = RateMap(ft[m][o], jj[m][o], rt[m][o], list(syms))
        self.times = [int(t) for t in self.rate.times]; self.n_rows = int(m.sum())
        self.xcheck = {"source": "P2 ledger_full.npz (zip ∪ API, per fundingTime)"}; self.src = collections.Counter()


class CfgMap31:
    """per-anchor config = the CURRENT production configuration throughout (v3.1 keys incl. t_dec)"""
    def __init__(self, tr_state, tr_row, syms, gm, weights, dec_off):
        self.tr = tr_state; self.row = tr_row; self.syms = np.array(syms); self.gm = float(gm); self.w = dict(weights); self.dec_off = int(dec_off); self.cache = {}
    def __contains__(self, A): return int(A) in self.row
    def __getitem__(self, A):
        A = int(A)
        if A not in self.cache:
            t_dec = A + self.dec_off
            self.cache = {A: {"gm": self.gm, "weights": dict(self.w), "tradable": set(self.syms[self.tr[self.row[A]] == 2].tolist()), "meta": set(),
                              "rid": f"A{t_dec}", "rid_recorded": False, "t_dec": float(t_dec)}}
        return self.cache[A]


def target_doc(A, w_row, syms, universe, tag, EXT):
    """verbatim from r_hist_sim.py"""
    nz = np.nonzero(np.abs(w_row) > 0)[0]
    weights = {syms[j]: float(w_row[j]) for j in sorted(nz, key=lambda j: syms[j])}
    if not weights: return None
    gn = float(sum(abs(v) for v in weights.values()))
    body = json.dumps(weights, separators=(",", ":")).encode()
    return {"schema": "wide_target_v1", "anchor_ts": int(A), "weights": weights, "universe": list(universe), "universe_sha": EXT.universe_sha(list(universe)),
            "booster_sha": "replay_r:" + tag, "weights_sha": hashlib.sha256(body).hexdigest(), "written_utc": time.strftime(UTC_FMT, time.gmtime(int(A) + 1200)),
            "gross_norm": gn, "n_names": len(weights), "producer": "replay_r_hist " + tag}


class UAIndex:
    """UNAVAILABLE bars on the price grid: (grid row, col) pairs → per-column sets and per-window sets"""
    def __init__(self, grid0, n_rows, rows, cols, n_sym):
        self.g0 = int(grid0); self.n = int(n_rows)
        self.cells = set(zip((np.asarray(rows, np.int64)).tolist(), (np.asarray(cols, np.int64)).tolist()))
        self.by_col = collections.defaultdict(list)
        for r, c in sorted(self.cells): self.by_col[c].append(r)
        self.by_col = {c: np.array(v, np.int64) for c, v in self.by_col.items()}
    def bar_is_ua(self, j, b_close):
        r = (int(b_close) - self.g0) // ROW
        return (r, j) in self.cells
    def cols_in_window(self, A):
        """columns with any UA bar closing in [A, A+4h] (the anchor's endpoint bar included)"""
        r0 = (int(A) - self.g0) // ROW; r1 = r0 + H4 // ROW
        return {c for c, v in self.by_col.items() if np.any((v >= r0) & (v <= r1))}


def make_sim_class(ES):
    class HistSim31(ES.Sim):
        def __init__(self, M, cal, mode, knobs, X, panel, fund, anchors, cfg, book, fresh, universe_rows, syms, tag, nav0, seed, policy,
                     ua_index, decisions_mode="none", keep_decisions=(), stop_at=None):
            assert policy in POLICIES, policy
            self.M, self.cal, self.mode, self.k, self.seed = M, cal, mode, dict(knobs), int(seed)
            self.p = cal["params"]; self.X0 = X; self.P = panel; self.F = fund; self.cfg = cfg
            self.frame = {}                                            # no live readback in history
            self.anchors = [int(a) for a in anchors]; self.run_start_anchor, self.last_anchor = self.anchors[0], self.anchors[-1]
            self.t_start, self.t_end = float(self.anchors[0]), float(self.anchors[-1] + H4)
            self.cfg_prov = {"history": "CfgMap31 (current production config at every anchor)"}
            self.flat_times, self.kind, self.xfers = [], {}, []
            self.fee_switch = -math.inf                                # USDT era for every trade (current)
            tm = self.p["timing_offsets_after_decision_s"]
            self.tau1, self.tau2, self.tw = [float(x) for x in tm["first_leg"]], [float(x) for x in tm["later_leg"]], [float(x) for x in tm["weights"]]
            self.tauf = [float(x) for x in self.p["timing_offsets_after_flatten_start_s"]["flatten"]]
            assert abs(sum(self.tw) - 1.0) < 1e-12 and min(self.tau1 + self.tau2) > 0 and min(self.tauf) >= 0
            self.q, self.entry, self.entry_named = {}, {}, {}
            self.nav0 = float(nav0); self.K = float(nav0)
            self.pns = {"counters": {}, "stopped": {}, "cooldown": {}}; self.pns_init = {"note": "flat start, empty stop state"}
            self.sealed = json.loads(canon({"utc": time.strftime(UTC_FMT, time.gmtime(self.t_start)), "t0": self.t_start, "n_positions": 0, "positions_qty": {},
                                            "nav0_usdt": self.nav0, "cash_K0": self.K, "entries": {}, "stop_state": self.pns, "tag": tag, "seed": self.seed,
                                            "policy": policy}))
            self.sealed_sha = hashlib.sha256(canon(self.sealed).encode()).hexdigest()
            self.acc = collections.Counter(); self.halt_until = None
            self.log_anchor, self.events_fired, self.diag = [], [], collections.Counter()
            self.trade_log = TradeAudit(self); self.fund_log = FundAudit(self._fund_hook); self.depth_log = NullLog(); self.plan_log = NullLog(); self.exit_log = ExitAudit()
            self.decisions = DecisionStore(decisions_mode, keep_decisions); self.last_target = {}
            self.day_ref, self.last_eval = {}, None
            self.ev, self.seq, self.rebal_gen = [], 0, 0
            self.clamp_stats = collections.Counter()
            # ---- history-adapter state ----
            self.tbook, self.fresh, self.urows, self.syms, self.tag = book, fresh, universe_rows, list(syms), tag   # tbook: v3.1 has a book() method
            self.sidx = {s: j for j, s in enumerate(self.syms)}; self.aidx = {a: i for i, a in enumerate(self.anchors)}
            self.tstats = collections.Counter(); self.n_stop_ev = 0; self.n_flat_ev = 0; self.stop_log, self.flat_log = [], []
            self.policy = policy; self.UA = ua_index; self.stop_at = stop_at; self.excl = (policy == "UA-FREEZE-EXCLUDE")
            self.X = X
            if policy == "UA-FREEZE-EXCLUDE":                          # (B): plan rows of frozen names become skip='ua_frozen'
                XP = copy.copy(X); XP.BX = types.SimpleNamespace(RebalanceExecutor=types.SimpleNamespace(plan=self._plan_ua))
                self.X = XP
            self._frozen = set(); self.anchor_extra = {}
            self.ua = collections.Counter()                            # counters over the whole run
            # window / unknown-cell accounting
            self._uw = set(); self._uw_base = {}; self._uw_cash = collections.defaultdict(float); self._uw_fund = collections.defaultdict(float)
            self._c = 1.0                                              # main-NAV scale of the current window: NAVm = c·(E − U)
            self._dirty = True; self._J = None; self._Q = None
            self.nav_grid0 = int(self.t_start); self.nav_n = int((self.t_end - self.t_start) // ROW) + 1
            self.nav5_sim = np.full(self.nav_n, np.nan); self.nav5_main = np.full(self.nav_n, np.nan); self._nb = 0
            self.bsnap = {}

        # ---------------- UNAVAILABLE policy hooks ----------------
        def _plan_ua(self, stub, target, pos, mids, reduce_only_syms=None, held_qty=None):
            plans = self.X0.BX.RebalanceExecutor.plan(stub, target, pos, mids, reduce_only_syms=reduce_only_syms, held_qty=held_qty)
            for p in plans:
                if p["symbol"] in self._frozen:
                    if "qty" in p:
                        self.ua["frozen_plans_dropped"] += 1; self.ua["frozen_plan_notional_dropped"] += abs(float(p.get("delta_notional", 0.0)))
                        self.anchor_extra.setdefault("frozen_plan_notional", 0.0); self.anchor_extra["frozen_plan_notional"] += abs(float(p.get("delta_notional", 0.0)))
                    for k in ("qty",): p.pop(k, None)
                    p["skip"] = "ua_frozen"
            return plans

        def on_fill(self, t, f):
            if f["src"] == "rebal" and f["gen"] != self.rebal_gen:
                return super().on_fill(t, f)
            if self.policy == "UA-FREEZE-EXCLUDE":
                j = self.sidx.get(f["s"])
                bc = int(math.ceil(float(t) / ROW) * ROW)
                if j is not None and self.UA.bar_is_ua(j, bc):
                    self.ua["fills_cancelled_ua_bar"] += 1; self.ua["fill_notional_cancelled_ua_bar"] += abs(f["dq"] * f["ref"]); self.ua["fills_cancelled_" + f["src"]] += 1
                    return
            return super().on_fill(t, f)

        def book(self, t, s, dq, ref_px, slip, maker, kind, A):
            x = super().book(t, s, dq, ref_px, slip, maker, kind, A)
            if dq != 0.0:
                self._dirty = True
                if s in self._uw: self._uw_cash[s] += self.trade_log.last[4]
            return x

        def _fund_hook(self, s, f):
            self._dirty = True
            if s in self._uw: self._uw_fund[s] += f

        # ---------------- adapter events ----------------
        def write_target(self, A):
            i = self.aidx[A]; p = self.M.target_path(A)
            if os.path.exists(p): os.remove(p)
            if not self.fresh[i]:
                self.tstats["no_fresh_target"] += 1; return False
            uni = [self.syms[j] for j in np.nonzero(self.urows[i])[0]]
            doc = target_doc(A, self.tbook[i], self.syms, uni, self.tag, self.X.EXT)
            if doc is None:
                self.tstats["empty_target"] += 1; return False
            out = set(doc["weights"]) - set(uni)
            if out: self.tstats["anchors_with_weights_outside_universe"] += 1; self.tstats["names_outside_universe"] += len(out)
            with open(p + ".tmp", "w") as fh: json.dump(doc, fh)
            os.replace(p + ".tmp", p); self.tstats["written"] += 1
            return True

        def on_anchor(self, A):
            self.anchor_extra = {"n_frozen": 0, "frozen_held_notional": 0.0, "frozen_plan_notional": 0.0}
            self._frozen = set()
            if self.policy == "UA-FREEZE-EXCLUDE":
                b_dec = int(math.floor(self.cfg[A]["t_dec"] / ROW) * ROW)
                fr = set()
                for c in self.UA.by_col:
                    if self.UA.bar_is_ua(c, A) or self.UA.bar_is_ua(c, b_dec): fr.add(self.syms[c])
                self._frozen = fr
                if fr:
                    self.ua["anchors_with_frozen_names"] += 1; self.ua["frozen_name_anchors"] += len(fr)
                    self.anchor_extra["n_frozen"] = len(fr)
                    for s in fr:
                        if s in self.q:
                            P = self.px(s, b_dec)
                            if P is not None: self.anchor_extra["frozen_held_notional"] += abs(self.q[s] * P); self.ua["frozen_held_name_anchors"] += 1
            wrote = self.write_target(A)
            n0 = len(self.log_anchor)
            try:
                super().on_anchor(A)
            finally:
                p = self.M.target_path(A)
                if wrote and os.path.exists(p): os.remove(p)
            if len(self.log_anchor) > n0: self.log_anchor[-1].update(self.anchor_extra)

        def on_eval(self, A, t):
            n0 = len(self.events_fired)
            super().on_eval(A, t)
            for e in self.events_fired[n0:]:
                if e["type"] == "STOP": self.stop_log.append((int(A), e["symbol"])); self.n_stop_ev += 1

        def flatten_start(self, t, why):
            super().flatten_start(t, why); self.n_flat_ev += 1; self.flat_log.append((float(t), why))

        # ---------------- 5-minute NAV sampler ----------------
        def _arrays(self):
            if self._dirty or self._J is None:
                items = sorted(self.q.items()); self._J = np.array([self.sidx[s] for s, _ in items], np.int64); self._Q = np.array([q for _, q in items], np.float64)
                self._Ju = np.array([self.sidx[s] for s, _ in items if s in self._uw], np.int64); self._Qu = np.array([q for s, q in items if s in self._uw], np.float64)
                self._dirty = False
            return self._J, self._Q

        def _values(self, r0, r1, J, Q):
            if len(J) == 0: return np.zeros(r1 - r0)
            P = self.P
            blk = np.exp(P.LP[r0:r1][:, J] - P.cref[J][None, :]) * P.ref_px[J][None, :]
            bts = P.g0 + ROW * np.arange(r0, r1)
            blk = np.where(bts[:, None] >= P.first_fin[J][None, :], blk, 0.0)
            return blk @ Q

        def _flush_nav(self, t):
            """record NAV(b) for every grid boundary b < t (state after all events with time <= b)"""
            if self._nb >= self.nav_n: return
            b_hi = min(self.nav_n, int(math.ceil((float(t) - self.nav_grid0) / ROW)))     # boundaries with index < b_hi have time < t
            if b_hi <= self._nb: return
            J, Q = self._arrays()
            r0 = self.P.row(self.nav_grid0 + self._nb * ROW); r1 = r0 + (b_hi - self._nb)
            e = self.K + self._values(r0, r1, J, Q)
            self.nav5_sim[self._nb:b_hi] = e
            if self.excl and self._uw:
                u = (self._values(r0, r1, self._Ju, self._Qu) if len(self._Ju) else 0.0) - self._uw_C()
                self.nav5_main[self._nb:b_hi] = self._c * (e - u)
            else:
                self.nav5_main[self._nb:b_hi] = self._c * e
            self._nb = b_hi

        def _uw_C(self):
            """C_U = Σ_{s∈U} [q_s(A)·P_s(A) + tradecash_s − funding_s]  ⇒  U(b) = Σ_{s∈U} q_s(b)·P_s(b) − C_U"""
            if not self._uw: return 0.0
            return sum(self._uw_base.get(s, 0.0) + self._uw_cash[s] - self._uw_fund[s] for s in self._uw)

        def _U_now(self, b):
            v = 0.0
            for s in self._uw:
                q = self.q.get(s)
                if q:
                    P_ = self.px(s, b)
                    if P_ is not None: v += q * P_
            return v - self._uw_C()

        def _boundary(self, t, k):
            """window boundary k (= start of window k, end of window k−1): snapshot + close the previous window's UNKNOWN cells"""
            b = int(math.floor(float(t) / ROW) * ROW)
            E = self.equity(b)
            U = self._U_now(b) if self._uw else 0.0
            navm = self._c * (E - U) if self.excl else self._c * E
            fl = ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_first", "turn_later", "turn_flatten", "turn_exit_completion")
            unk_price = unk_fund = 0.0
            for s in self._uw:
                q = self.q.get(s, 0.0); P_ = self.px(s, b) if q else None
                unk_price += (q * P_ if P_ is not None else 0.0) - self._uw_base.get(s, 0.0) - self._uw_cash[s]; unk_fund += self._uw_fund[s]
            snap = {"mv": self.mv(b), "gross": self.gross(b), "equity": E, "navm": navm, "dust": self.dust_now(b), "n_pos": len(self.q),
                    "n_stop_ev": self.n_stop_ev, "n_flat_ev": self.n_flat_ev, **{c: self.acc[c] for c in fl},
                    "unk_price_prev": unk_price, "unk_fund_prev": unk_fund, "unk_n_prev": len(self._uw_held)}
            # open window k: unknown names from the UA index (any UA bar closing in [A, A+4h]); only names HELD at the start or traded count
            self._c = navm / E if E != 0 else 1.0
            if k < len(self.anchors):
                A = self.anchors[k]
                cols = self.UA.cols_in_window(A) if self.UA is not None else set()
                self._uw = {self.syms[c] for c in cols}
            else:
                self._uw = set()
            self._uw_base = {}; self._uw_cash = collections.defaultdict(float); self._uw_fund = collections.defaultdict(float)
            held_notional = 0.0
            self._uw_held = set()
            for s in self._uw:
                q = self.q.get(s)
                if q:
                    P_ = self.px(s, b); v = q * P_ if P_ is not None else 0.0
                    self._uw_base[s] = v; held_notional += abs(v); self._uw_held.add(s)
            snap["unk_names_open"] = len(self._uw); snap["unk_held_open"] = len(self._uw_held); snap["unk_notional_open"] = held_notional
            self._dirty = True
            self.bsnap[k] = snap

        def dispatch(self, t, kind, arg):
            if kind == "win":
                return self._boundary(t, arg)
            return super().dispatch(t, kind, arg)

        def run(self):
            n = len(self.anchors)
            for k, A in enumerate(self.anchors):
                self.push(A, "win", k)
                self.push(self.cfg[A]["t_dec"], "anchor", A)
                self.push(self.eval_time(A), "eval", A)
            self.push(self.t_end, "win", n)
            for t in self.F.times:
                if self.t_start < t <= self.t_end: self.push(float(t), "funding", None)
            self._uw_held = set()
            while self.ev:
                t = self.ev[0][0]
                if self.stop_at is not None and t > self.stop_at: break
                self._flush_nav(t)
                t, pri, _, kind, arg = heapq.heappop(self.ev)
                self.dispatch(t, kind, arg)
            if self.stop_at is None: self._flush_nav(self.t_end + 1)
            return self.windows()

        def windows(self):
            """per window k = [A_k, A_k + 4h): the v3.1 window fields + main-reading fields (UA-FREEZE-EXCLUDE removes UNKNOWN cells)"""
            out = []
            fl = ("tradecash", "fee", "fund", "turn", "xfer", "n_trades", "turn_first", "turn_later", "turn_flatten", "turn_exit_completion")
            for k, A in enumerate(self.anchors):
                if k not in self.bsnap or (k + 1) not in self.bsnap: break
                a, z = self.bsnap[k], self.bsnap[k + 1]
                d = {c: z[c] - a[c] for c in fl}
                excl = self.policy == "UA-FREEZE-EXCLUDE"
                w = {"A": A, "gross0": a["gross"], "nav0": a["equity"], "nav1": z["equity"], "navm0": a["navm"], "navm1": z["navm"],
                     "price_trade": (z["mv"] - a["mv"]) - d["tradecash"], "funding": d["fund"], "fee": d["fee"], "turnover": d["turn"],
                     "turnover_first": d["turn_first"], "turnover_later": d["turn_later"], "turnover_flatten": d["turn_flatten"],
                     "transfer": d["xfer"], "n_trades": d["n_trades"], "n_pos0": a["n_pos"],
                     "n_stop_events": z["n_stop_ev"] - a["n_stop_ev"], "n_flatten_events": z["n_flat_ev"] - a["n_flat_ev"],
                     "unk_price": z["unk_price_prev"], "unk_funding": z["unk_fund_prev"], "unk_names": a["unk_names_open"], "unk_held": a["unk_held_open"],
                     "unk_notional": a["unk_notional_open"], "unk_excluded": 1 if excl else 0,
                     **{"end_" + c: v for c, v in z["dust"].items()}}
                out.append(w)
            return out
    return HistSim31
