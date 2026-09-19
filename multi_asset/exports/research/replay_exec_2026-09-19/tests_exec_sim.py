#!/usr/bin/env python3
"""replay_exec 2026-09-19 · battery v3 for exec_sim.py (v3) / v1b_gate.py. Every claim: the GREEN baseline is asserted FIRST (non-vacuous:
a measured population > 0), then each mutation must turn the SAME check RED. A mutation that stays green is a battery failure.
v2 battery: archive/tests_exec_sim_v2_0265ed2c.py. Real-data claims run ONE path (seed 0) over the CALIBRATION period only (anchors
08-26 00Z .. 09-10 20Z; the hold-out is not touched by the battery).

Part A — the reviewer's counterexamples (round 5), on tiny synthetic books, against the ARCHIVED v2 AND v3:
  A1 R5-01 future price     the A+25 price changes 100 → 200: the decision at A+24 (equity, sizing, quantity) must not move.   v2 RED, v3 GREEN
  A2 R5-01 fill clock       a settlement at A+24:05 (after the decision, before any fill) charges the PRE-execution inventory. v2 RED, v3 GREEN
  A3 R5-06 exit guarantee   a 20 USD exit under an 80% full / 20% zero first-leg model, no completion: E[executed] = 16 and
                            every path executes 0 or 20 (feasible); no exit-completion leg.                                v2 RED, v3 GREEN
  A4 R5-06 unfillable dust  4 USD held, zero fill probability, plan skipped below the floor: nothing is executed.            v2 RED, v3 GREEN
  A5 R5-07 gate             the reviewer's anti-correlated path (t1 +2 h): the old V1 PASSES it (RED for V1), V1b FAILS it (GREEN)
Part B — real data (v3, seed 0, CAL period):
  [0] mirror bytes = INPUT_MANIFEST            [7] read-only guard (fresh interpreter)                 mut: no guard
  [1] min-notional (vs the REAL venue floor)   mut: --no-min-notional
  [2] per-name stop (independent re-derivation) mut: --no-stop
  [3] fees = |cash| × frozen v3 rate           mut: --zero-fees, --fee-asset-wrong
  [4] funding = −q·P·rate once per key, rates = executor rows; sign convention anchored on the REAL ledger   mut: sign flip, double
  [4b] R5-01 fill-time inventory: every funding charge (real + synthetic settlements injected 5 s and 600 s after six decisions)
       charges the inventory reconstructed from the SEALED initial state + fills booked strictly before it; at decision + 5 s it is the
       pre-decision inventory                    mut: --legacy-book-at-decision
  [5] accounting identity per window           mut: fee not booked to equity
  [6] determinism (same seed identical; another seed differs) + calibration binding   mut: π + 0.10
  [8] V1b judge on the real CAL windows        mut: t1 shift, dropped window, anti-correlated price, fee ×1.4
  [9] R5-06 no guaranteed fills: no exit-completion leg; per plan Σ|filled| ≤ |planned|; fills only for sent plans; skipped
       zero-target plans get nothing             mut: --legacy-exit-completion
  [10] R5-01 future-price invariance: every price after t_dec(A) multiplied by a per-symbol factor in [0.7, 1.3] → the decision of
       A and every earlier decision byte-identical (4 anchors)    mut: --legacy-decision-lookahead
  [11] R5-01 fill clock: every rebalance fill is booked at t_dec + its calibrated offset (or 1 s before A's own readback), never at
       t_dec                                     mut: --legacy-book-at-decision
  [12] R5-13 initial population: the receipt block equals the independently counted t0 readback (sealed, sha reproducible);
       the committed v2 receipt fails it          mut: --legacy-unsealed-initial
  [13] blind protocol: the v3 calibration carries no arm / experiment key; the checker catches one   mut: an injected per-arm key
usage: tests_exec_sim.py [mirror]   → one line per check and a final verdict line; exit code 0 iff every check passed.
"""
import collections, copy, importlib.util, json, math, os, subprocess, sys, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L

RESULTS = []
CAL_FILE = os.path.join(HERE, "CALIBRATION_v3_POOLED_20260826_20260910.json")
V2_FILE = os.path.join(HERE, "archive", "exec_sim_v2_2638316b.py")
SYN_TARGET = os.path.join(HERE, "battery_synthetic_target.json")     # {} — the synthetic books' parse_target stub ignores its bytes


def check(name, ok, detail):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


# ── [7] read-only guard: needs subprocesses, so it runs BEFORE this process installs its own guard ──
def t7_guard():
    probe = os.path.expanduser("~/dl_quant_live/config/book.json")
    code = ("import sys; sys.path.insert(0, %r); import simlib as L; %s\n"
            "try:\n    open(%r, 'rb').read(1); print('OPENED')\nexcept PermissionError as e:\n    print('REFUSED')") % (HERE, "{}", probe)
    g = subprocess.run([sys.executable, "-c", code.format("L.install_readonly_guard()")], capture_output=True, text=True).stdout.strip()
    check("7 read-only guard baseline (guard installed ⇒ open of a live path refused)", g == "REFUSED", f"child says {g!r}")
    m = subprocess.run([sys.executable, "-c", code.format("pass")], capture_output=True, text=True).stdout.strip()
    check("7 read-only guard mutation (no guard ⇒ the same open succeeds, i.e. the refusal came from the guard)", m == "OPENED", f"child says {m!r}")


def load_v2():
    spec = importlib.util.spec_from_file_location("exec_sim_v2_archived", V2_FILE)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


# ───────────────────────────── Part A: synthetic books (reviewer's probes) ─────────────────────────────
def _plan_stub(stub, target, pos, mids, **kw):
    delta = target["S"] - pos.get("S", 0)
    return [{"symbol": "S", "prev_notional": pos.get("S", 0), **({"skip": "skipped_min_notional"} if abs(delta) < 5 else {"qty": delta / mids["S"]})}]


def _x_stub(target_fn):
    ext = types.SimpleNamespace(parse_target=lambda *a: {"ok": True, "symbols": ["S"], "weights_sha": "x"}, held_not_in_target=lambda p, s: [],
                                target_vector=lambda e, s: [1], below_min_notional=lambda *a: {"names": [], "n": 0})
    filters = types.SimpleNamespace(f={"S": {"min_notional": 5}}, round_qty=lambda s, q: q)
    return types.SimpleNamespace(EXT=ext, ext_cfg={"min_notional_mult": 2}, pns_conf={"min_notional_usdt": 5},
                                 PNS=types.SimpleNamespace(active_sets=lambda *a: {"stop": set(), "cooldown": set()}),
                                 LG=types.SimpleNamespace(to_notional=target_fn), filters=filters, stub=None,
                                 AL=types.SimpleNamespace(apply_withhold_and_reshape=lambda *a, **k: ({"reduced": [], "flatten_only": []}, None)),
                                 BX=types.SimpleNamespace(RebalanceExecutor=types.SimpleNamespace(plan=_plan_stub)),
                                 CP=types.SimpleNamespace(plan_experiment=lambda *a, **k: {}), RQ=types.SimpleNamespace(assign=lambda *a: "requote"))


def make_v2(ES2, q=1.0, price=100.0, complete=False, fill=1.0, target_fn=None):
    """the reviewer's harness (probes.py make()), verbatim semantics, on the archived v2 module"""
    s = ES2.Sim.__new__(ES2.Sim); s.mode = "rule"; s.k = {"no_exit_completion": not complete}; s.halt_until = None
    s.q = {"S": q}; s.entry = {"S": 100}; s.K = 100; s.diag = collections.Counter(); s.acc = collections.Counter()
    s.trade_log = []; s.fund_log = []; s.plan_log = []; s.exit_log = []; s.log_anchor = []; s.events_fired = []
    s.pns = {"stopped": {}, "cooldown": {}, "counters": {}}
    s.p = {"decision_boundary_offset_s": 1500, "maker_first": {"p_rej": 0, "p_full": fill, "p_zero": 1 - fill, "p_part": 0, "fbar_part": 0},
           "maker_requote": {"p_rej": 0, "p_full": 0, "p_zero": 1, "p_part": 0, "fbar_part": 0},
           "requote_p_timeline": [{"from_anchor": 0, "p": 0, "mode": "expected_mix"}],
           "taker_fill_rate": {"from_reject": 0, "from_partial_chase": 0, "from_partial_chase_forced": 0},
           "slippage_vs_mid_at_anchor": {"maker_first": 0, "maker_requote": 0, "taker_from_partial": 0, "taker_from_reject": 0},
           "fee_rate": {"BNB_era": {"maker": 0, "taker": 0}, "USDT_era": {"maker": 0, "taker": 0}}}
    s.fee_switch = 0; s.cfg = {0: {"gm": 1, "weights": {}, "tradable": {"S"}, "meta": set(), "rid": "synthetic"}}
    s.P = types.SimpleNamespace(px=lambda sym, b: price if b >= 1500 else 100)
    s.M = types.SimpleNamespace(target_path=lambda a: SYN_TARGET, anchor_rows=lambda: {})
    s.X = _x_stub(target_fn or (lambda v, sy, g: {"S": g}))
    return s


def make_v3(ES, q=1.0, price=100.0, fill=1.0, target_fn=None, seed=0, knobs=None):
    """the same synthetic book for v3: decision at t_dec = 1440 (A+24:00), fills at t_dec + 30..150 s (first leg)"""
    s = ES.Sim.__new__(ES.Sim)
    s.mode = "live"; s.k = {k: False for k in ES.KNOBS}; s.k.update(knobs or {}); s.seed = seed
    s.q = {"S": q} if q else {}; s.entry = {"S": 100.0} if q else {}; s.K = 100.0
    s.diag = collections.Counter(); s.acc = collections.Counter(); s.clamp_stats = collections.Counter()
    s.trade_log, s.fund_log, s.plan_log, s.exit_log, s.log_anchor, s.events_fired, s.depth_log = [], [], [], [], [], [], []
    s.decisions, s.last_target, s.snaps = {}, {}, {}
    s.pns = {"stopped": {}, "cooldown": {}, "counters": {}}
    s.p = {"first_leg": {"p_rej": 0.0, "p_full": fill, "p_zero": 1.0 - fill, "p_part": 0.0, "fbar_part": 0.0},
           "completion": {"pi_fill": 0.0, "maker_share": 0.0},
           "slippage_vs_executor_mid": {"first_leg": 0.0, "later_leg": 0.0, "flatten": 0.0},
           "fee_rate": {"switch_ts": 0, "BNB_era": {"maker": 0, "taker": 0}, "USDT_era": {"maker": 0, "taker": 0}},
           "eval_offset_without_frame_s": 2700, "rule_flatten_offset_s": 2760}
    s.fee_switch = 0.0
    s.tau1, s.tau2, s.tw, s.tauf = [30.0, 60.0, 90.0, 120.0, 150.0], [1100.0, 1150.0, 1200.0, 1250.0, 1300.0], [0.2] * 5, [0.0] * 5
    s.frame, s.kind, s.halt_until = {}, {}, None
    s.cfg = {0: {"gm": 1.0, "weights": {}, "tradable": {"S"}, "meta": set(), "rid": "A1440", "t_dec": 1440.0}}
    s.ev, s.seq, s.rebal_gen = [], 0, 0
    s.P = types.SimpleNamespace(px=lambda sym, b: price if b >= 1500 else 100.0)
    s.M = types.SimpleNamespace(target_path=lambda a: SYN_TARGET, anchor_rows=lambda: {})
    s.F = types.SimpleNamespace(rate={})
    s.X = _x_stub(target_fn or (lambda v, sy, g: {"S": g}))
    return s


def part_a(ES):
    import v1_gate as V1, v1b_gate as G
    ES2 = load_v2()
    zero = lambda v, sy, g: {"S": 0.0}
    # A1 + A2 on v2 (reviewer's numbers)
    a, b = make_v2(ES2, price=100), make_v2(ES2, price=200)
    a.on_anchor(0); b.on_anchor(0)
    for s_ in (a, b):
        s_.F = types.SimpleNamespace(rate={("S", 1445): 0.01}); s_.on_funding(1445)
    v2_a1 = (a.log_anchor[0]["equity_at_decision"], b.log_anchor[0]["equity_at_decision"], a.q["S"], b.q["S"])
    v2_a2 = (a.fund_log[-1][-1], b.fund_log[-1][-1])
    # A1 + A2 on v3
    c, d = make_v3(ES, price=100), make_v3(ES, price=200)
    for s_ in (c, d):
        s_.F = types.SimpleNamespace(rate={("S", 1445): 0.01})
        s_.on_anchor(0); s_.push(1445, "funding", None); s_.step_until(None)
    same_dec = json.dumps(c.decisions[0], sort_keys=True) == json.dumps(d.decisions[0], sort_keys=True)
    check("A1 R5-01 future price (A+25: 100 → 200) — v3 decision unchanged (baseline GREEN)",
          same_dec and abs(c.q["S"] - 2.0) < 1e-12 and abs(d.q["S"] - 2.0) < 1e-12 and c.decisions[0]["equity"] == 200.0,
          f"v3 equity at decision {c.decisions[0]['equity']} / {d.decisions[0]['equity']}, final qty {c.q['S']} / {d.q['S']}")
    check("A1 R5-01 future price — archived v2 is RED (decision moves with the future price)", v2_a1[0] != v2_a1[1] or v2_a1[2] != v2_a1[3],
          f"v2 equity at decision {v2_a1[0]} → {v2_a1[1]}, final qty {v2_a1[2]} → {v2_a1[3]}")
    f3 = [x[-1] for x in c.fund_log if x[0] == 1445] + [x[-1] for x in d.fund_log if x[0] == 1445]
    check("A2 R5-01 settlement at A+24:05 charges the pre-execution inventory (−1) — v3 GREEN", f3 == [-1.0, -1.0],
          f"v3 charges {f3}; first fill booked at {min(t for t, *_ in c.trade_log)} s")
    check("A2 R5-01 same settlement — archived v2 is RED (charges inventory that does not exist yet)", v2_a2 != (-1.0, -1.0),
          f"v2 charges {v2_a2}")
    # A3 exit under an 80% model
    ex = []; kinds = collections.Counter()
    for sd in range(2000):
        s_ = make_v3(ES, q=0.2, fill=0.8, target_fn=zero, seed=sd); s_.on_anchor(0); s_.step_until(None)
        ex.append(s_.acc["turn"]); kinds.update(k for *_, k, _A in s_.trade_log)
    mean_ex = sum(ex) / len(ex); feas = all(abs(x) < 1e-9 or abs(x - 20.0) < 1e-9 for x in ex)
    check("A3 R5-06 20 USD exit, 80% full / 20% zero, no completion — v3 E[executed] ≈ 16, each path 0 or 20, no completion leg (GREEN)",
          15.0 <= mean_ex <= 17.0 and feas and kinds.get("exit_completion", 0) == 0,
          f"mean over 2,000 seeds {mean_ex:.2f} (MC s.e. {20 * math.sqrt(0.16 / 2000):.2f}), feasible paths {feas}, leg kinds {dict(kinds)}")
    s2 = make_v2(ES2, q=0.2, price=100, complete=True, fill=0.8); s2.X.LG.to_notional = zero; s2.on_anchor(0)
    check("A3 R5-06 same exit — archived v2 is RED (guaranteed completion executes 20)", not (15.0 <= s2.acc["turn"] <= 17.0),
          f"v2 executed {s2.acc['turn']:.2f}, completion legs {sum(x[-1] == 'exit_completion' for x in s2.trade_log)}")
    # A4 unfillable dust
    s4 = make_v3(ES, q=0.04, fill=0.0, target_fn=zero); s4.on_anchor(0); s4.step_until(None)
    check("A4 R5-06 4 USD dust, zero fill probability, plan skipped — v3 executes nothing, the dust stays (GREEN)",
          s4.acc["turn"] == 0.0 and abs(s4.q.get("S", 0) - 0.04) < 1e-12, f"v3 executed {s4.acc['turn']}, remaining qty {s4.q.get('S')}")
    s5 = make_v2(ES2, q=0.04, price=100, complete=True, fill=0.0); s5.X.LG.to_notional = zero; s5.on_anchor(0)
    check("A4 R5-06 same dust — archived v2 is RED (fills 4 USD as maker)", s5.acc["turn"] > 0.0,
          f"v2 executed {s5.acc['turn']:.2f}, remaining qty {s5.q.get('S', 0)}")
    # A5 gate
    sim, live, turn = G.reviewer_counterexample()
    old = V1.judge(sim, live, turn); new = G.judge_v1b(sim, live, turn)
    check("A5 R5-07 reviewer's anti-correlated path, t1 +2 h — V1b FAILS it (GREEN)", not all(x["pass"] for x in new.values()),
          {k: v["pass"] for k, v in new.items() if not v["pass"]})
    check("A5 R5-07 same path — the old V1 PASSES it (RED for V1: the defect is real)", all(x["pass"] for x in old.values()),
          {k: v["pass"] for k, v in old.items()})


# ───────────────────────────── Part B: real data ─────────────────────────────
def run(ES, M, cal, X, P, F, seed=0, stop_at=None, **knobs):
    import v1b_gate as G
    kn = {k: False for k in ES.KNOBS}; kn.update(knobs)
    S = ES.Sim(M, cal, "live", kn, X=X, panel=P, fund=F, seed=seed, run_start_anchor=G.PERIODS["CAL"]["run_start_anchor"],
               last_anchor=G.PERIODS["CAL"]["last_anchor"])
    W = S.run(stop_at=stop_at)
    return S, W


def real_floor(X, s):
    return float((X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0)


def c1_min_notional(S):
    sent = [(A, s, Q, m) for (A, s, Q, m, tgt, prev, st, q1, q2, sk) in S.plan_log if m is not None and Q != 0.0]
    bad = [(A, s, round(abs(Q * m), 4)) for (A, s, Q, m) in sent if abs(Q * m) < real_floor(S.X, s) - 1e-9]
    return len(sent), bad


def c2_stop(S, depth_limit=-0.30):
    status = {r["anchor"]: r["status"] for r in S.log_anchor}
    plans = collections.defaultdict(dict)
    for (A, s, Q, m, tgt, prev, st, q1, q2, sk) in S.plan_log:
        plans[A][s] = (tgt, st, prev)
    trig, viol = [], []
    D = S.depth_log
    for k in range(1, len(D)):
        A0, _, d0, ex0 = D[k - 1]; A1, _, d1, ex1 = D[k]
        if A1 - A0 != 14400:
            continue
        for s, v in d1.items():
            if v <= depth_limit and d0.get(s, 0.0) <= depth_limit and s not in ex0 and s not in ex1:
                An = A1 + 14400
                if status.get(An) not in ("TRADE",):
                    continue
                trig.append((A1, s))
                got = plans.get(An, {}).get(s)
                if got is None:
                    viol.append((An, s, "no plan row for a held name"))
                elif not (got[1] and got[0] == 0.0):
                    viol.append((An, s, f"target {got[0]:+.2f} stop_flag {got[1]}"))
    return trig, viol


def c3_fees(S, cal):
    fr = cal["params"]["fee_rate"]; sw = float(fr["switch_ts"])
    err = 0.0; n = 0; tot = 0.0
    for (t, s, dq, px, cash, maker, fee, kind, A) in S.trade_log:
        era = "BNB_era" if t < sw else "USDT_era"
        err = max(err, abs(fee - abs(cash) * float(fr[era]["maker" if maker else "taker"]))); n += 1; tot += fee
    return n, tot, err


def c4_funding(S):
    worst = 0.0; seen = collections.Counter(); rate_mis = 0; n_live_keys = 0
    for (t, s, q, P, r, f) in S.fund_log:
        exp = -q * P * r
        worst = max(worst, abs(f - exp) / max(1e-9, abs(exp)) if exp != 0 else abs(f))
        seen[(s, int(t))] += 1
        lr = S.F.live.get((s, int(t)))
        if lr is not None:
            n_live_keys += 1; rate_mis += int(abs(lr - r) > 1e-15)
    return len(S.fund_log), worst, sum(1 for v in seen.values() if v > 1), rate_mis, n_live_keys


def q_before(S, s, t, strictly_before_decision_of=None):
    """inventory of s reconstructed from the SEALED initial state + fills booked strictly before t"""
    q = float(S.sealed["positions_qty"].get(s, 0.0))
    for (tt, ss, dq, *_rest) in S.trade_log:
        if ss == s and tt < t:
            q += dq
    return q


def c4b_fill_time(S, synth):
    """(i) every charge: q charged == sealed + fills strictly before t_s; (ii) synthetic settlements at t_dec + 5 s: q charged ==
    inventory strictly before t_dec (the decision's own fills cannot exist yet)"""
    by_sym = collections.defaultdict(list)
    for (tt, ss, dq, *_r) in S.trade_log:
        by_sym[ss].append((tt, dq))
    for v in by_sym.values():
        v.sort()
    q0 = S.sealed["positions_qty"]

    def qa(s, t):
        return float(q0.get(s, 0.0)) + sum(dq for tt, dq in by_sym.get(s, ()) if tt < t)
    bad_all = []
    for (t, s, q, P, r, f) in S.fund_log:
        if abs(qa(s, t) - q) > 1e-9 * max(1.0, abs(q)):
            bad_all.append((L.U(t), s, q, qa(s, t)))
    bad_pre, n_pre = [], 0
    for (t, s, q, P, r, f) in S.fund_log:
        if (s, t) in synth and synth[(s, t)][1] == "dec+5":
            n_pre += 1
            t_dec = synth[(s, t)][0]
            if abs(qa(s, t_dec) - q) > 1e-9 * max(1.0, abs(q)):
                bad_pre.append((L.U(t), s, q, qa(s, t_dec)))
    return len(S.fund_log), bad_all, n_pre, bad_pre


def c5_accounting(W):
    return max(abs((w["equity1"] - w["nav0"]) - (w["price_trade"] + w["funding"] - w["fee"] + w["transfer"])) for w in W)


def c9_no_guarantee(S):
    planned = {(A, s): (Q, sk, tgt) for (A, s, Q, m, tgt, prev, st, q1, q2, sk) in S.plan_log}
    filled = collections.defaultdict(float); kinds = collections.Counter(); orphan = []
    for (t, s, dq, px, cash, maker, fee, kind, A) in S.trade_log:
        kinds[kind] += 1
        if kind == "flatten":
            continue
        filled[(A, s)] += abs(dq)
        pl = planned.get((A, s))
        if pl is None or pl[0] == 0.0:
            orphan.append((A, s, kind))
    over = [(A, s, v, abs(planned[(A, s)][0])) for (A, s), v in filled.items() if (A, s) in planned and v > abs(planned[(A, s)][0]) * (1 + 1e-9) + 1e-12]
    skipped_exit_filled = [(A, s) for (A, s), (Q, sk, tgt) in planned.items() if sk == "skipped_min_notional" and tgt == 0.0 and filled.get((A, s), 0.0) > 0]
    n_exit_skipped = sum(1 for (Q, sk, tgt) in planned.values() if sk == "skipped_min_notional" and tgt == 0.0)
    return kinds, over, orphan, skipped_exit_filled, n_exit_skipped, len(filled)


class PerturbedPanel:
    """every price at a bar AFTER t_cut multiplied by a per-symbol factor in [0.7, 1.3]; prices at bars ≤ t_cut unchanged"""
    def __init__(self, P, t_cut, ES):
        self.P, self.t_cut, self.ES = P, t_cut, ES
        self.ref = P.ref
    def px(self, s, b):
        v = self.P.px(s, b)
        if v is None or b <= self.t_cut:
            return v
        return v * (0.7 + 0.6 * self.ES.u01("perturb", s))


def c10_invariance(ES, M, cal, X, P, F, anchors, S0, **knobs):
    diffs, n = [], 0
    for A in anchors:
        t_dec = S0.cfg[A]["t_dec"]
        Sa, _ = run(ES, M, cal, X, P, F, stop_at=t_dec + 1.0, **knobs)
        Sp, _ = run(ES, M, cal, X, PerturbedPanel(P, t_dec, ES), F, stop_at=t_dec + 1.0, **knobs)
        for B in sorted(Sa.decisions):
            n += 1
            if json.dumps(Sa.decisions[B], sort_keys=True) != json.dumps(Sp.decisions.get(B), sort_keys=True):
                diffs.append((L.UA(A), L.UA(B)))
        if not knobs and json.dumps(Sa.decisions[A], sort_keys=True) != json.dumps(S0.decisions[A], sort_keys=True):
            diffs.append((L.UA(A), "partial run differs from the full baseline"))
    return n, diffs


def c11_fill_clock(S):
    bad, n = [], 0
    offs = set(S.tau1) | set(S.tau2)
    for (t, s, dq, px, cash, maker, fee, kind, A) in S.trade_log:
        if kind in ("flatten",) or A is None:
            continue
        n += 1
        t_dec = S.cfg[A]["t_dec"]; rb = S.frame.get(A)
        ok = t > t_dec and (any(abs(t - (t_dec + o)) < 1e-6 for o in offs) or (rb is not None and abs(t - (rb - 1.0)) < 1e-6))
        if not ok:
            bad.append((L.UA(A), s, t - t_dec))
    return n, bad


def c12_initial(M, S, block):
    day = time.strftime("%Y%m%d", time.gmtime(S.t_start))
    n_rb = sum(1 for r in M.rows(day, "position_readback") if abs(float(r["read_ts"]) - S.t_start) < 1.0 and float(r["venue_position_qty"]) != 0.0)
    return n_rb, block.get("n_positions"), block.get("sealed_before_run"), (block.get("sha256") == S.canon_sha_of_sealed if block.get("sha256") else None)


def main():
    t7_guard()
    M = L.Mirror(sys.argv[1] if len(sys.argv) > 1 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    check("0 mirror bytes equal INPUT_MANIFEST", not bad, f"{len(bad)} mismatching files")
    import exec_sim as ES
    import v1_gate as V1, v1b_gate as G, calib_v3 as C
    cal = json.load(open(CAL_FILE))
    print("      devices: " + ", ".join(f"{n} {L.sha_file(os.path.join(HERE, n))[:12]}" for n in
                                         ("exec_sim.py", "simlib.py", "v1b_gate.py", "v1_gate.py", "calib_v3.py", "tests_exec_sim.py",
                                          "CALIBRATION_v3_POOLED_20260826_20260910.json", "archive/exec_sim_v2_2638316b.py")), flush=True)
    part_a(ES)
    X = ES.ExecutorCode(M); P = L.Panel(M); L.build_references(M, P); F = L.FundingBook(M)
    t0 = time.time()
    S0, W0 = run(ES, M, cal, X, P, F)
    S0.canon_sha_of_sealed = ES.canon_sha(S0.sealed)
    print(f"      baseline run (seed 0, CAL period) {time.time() - t0:.1f} s: {len(W0)} windows, {len(S0.trade_log)} fill events, "
          f"{len(S0.fund_log)} funding charges, sealed initial sha {S0.sealed_sha[:12]}", flush=True)
    # [1]
    n, badm = c1_min_notional(S0)
    check("1 min-notional baseline", n > 0 and not badm, f"{n} sent plans, {len(badm)} below the venue floor")
    Sm, _ = run(ES, M, cal, X, P, F, no_min_notional=True)
    n2, bad2 = c1_min_notional(Sm)
    check("1 min-notional mutation --no-min-notional turns it RED", len(bad2) > 0, f"{len(bad2)} sent plans below the floor (of {n2})")
    # [2]
    trig, viol = c2_stop(S0)
    check("2 per-name stop baseline", len(trig) > 0 and not viol, f"{len(trig)} independent −30%×2 triggers, {len(viol)} violations")
    Ss, _ = run(ES, M, cal, X, P, F, no_stop=True)
    trig2, viol2 = c2_stop(Ss)
    check("2 per-name stop mutation --no-stop turns it RED", len(viol2) > 0, f"{len(trig2)} triggers, {len(viol2)} violations e.g. {viol2[:2]}")
    # [3]
    n, tot, err = c3_fees(S0, cal)
    check("3 fees baseline", n > 0 and tot > 0 and err <= 1e-9, f"{n} fill events, fee {tot:,.2f} USDT, max |fee − recomputed| {err:.2e}")
    for kn in ("zero_fees", "fee_asset_wrong"):
        Sf, _ = run(ES, M, cal, X, P, F, **{kn: True})
        n2, tot2, err2 = c3_fees(Sf, cal)
        check(f"3 fees mutation --{kn.replace('_', '-')} turns it RED", err2 > 1e-6, f"fee {tot2:,.2f} USDT, max |fee − recomputed| {err2:.4f}")
    # [4]
    rows = M.range_rows("funding", "20260826", "20260911")
    sg = [(float(r["funding_paid"]), -float(r["position_notional_at_settlement"]) * float(r["funding_rate"])) for r in rows if abs(float(r["funding_paid"])) > 1e-6]
    agree = sum(1 for a, b in sg if a * b > 0) / len(sg)
    check("4 funding sign convention on the REAL ledger (paid = −notional × rate)", agree >= 0.99, f"{agree:.4%} of {len(sg)} live rows agree in sign")
    n, worst, dup, mis, nk = c4_funding(S0)
    check("4 funding baseline", n > 0 and worst <= 1e-9 and dup == 0 and mis == 0 and nk > 0,
          f"{n} charges, max rel err {worst:.1e}, {dup} duplicate (symbol, time), {mis}/{nk} rate mismatches vs the executor's rows")
    for kn in ("funding_sign_flip", "funding_double"):
        Sf, _ = run(ES, M, cal, X, P, F, **{kn: True})
        check(f"4 funding mutation --{kn.replace('_', '-')} turns it RED", c4_funding(Sf)[1] > 1e-6, f"max rel err {c4_funding(Sf)[1]:.3f}")
    # [4b] fill-time inventory with synthetic mid-window settlements
    trade_anchors = [r["anchor"] for r in S0.log_anchor if r["status"] == "TRADE" and r.get("n_plans_sent", 0) > 20]
    pick = [trade_anchors[i] for i in (3, len(trade_anchors) // 4, len(trade_anchors) // 2, (3 * len(trade_anchors)) // 4, -8, -3)]
    F2 = copy.copy(F); F2.rate = dict(F.rate); synth = {}
    for A in pick:
        t_dec = S0.cfg[A]["t_dec"]
        for s in S0.decisions[A]["target"]:
            for dt, tag in ((5.0, "dec+5"), (600.0, "dec+600")):
                F2.rate[(s, int(t_dec + dt))] = 1e-4; synth[(s, int(t_dec + dt))] = (t_dec, tag)
    Sb, _ = run(ES, M, cal, X, P, F2)
    Sb.canon_sha_of_sealed = None
    nf, bad_all, n_pre, bad_pre = c4b_fill_time(Sb, synth)
    check("4b R5-01 fill-time inventory baseline (every charge = sealed + fills strictly before it; at t_dec+5 s = pre-decision inventory)",
          nf > 0 and n_pre > 0 and not bad_all and not bad_pre,
          f"{nf} charges ({sum(1 for k in synth)} synthetic keys on {len(pick)} anchors), {n_pre} charges at decision+5 s, {len(bad_all)} + {len(bad_pre)} mismatches")
    Sbm, _ = run(ES, M, cal, X, P, F2, legacy_book_at_decision=True)
    nf2, bad_all2, n_pre2, bad_pre2 = c4b_fill_time(Sbm, synth)
    check("4b R5-01 mutation --legacy-book-at-decision turns it RED (settlement 5 s after the decision sees that decision's fills)",
          len(bad_pre2) > 0, f"{len(bad_pre2)} of {n_pre2} decision+5 s charges on inventory that did not exist yet, e.g. {bad_pre2[:2]}")
    # [5]
    e = c5_accounting(W0)
    check("5 accounting identity baseline", e <= 1e-6, f"max |Δequity − (price + funding − fee + transfer)| = {e:.2e} USDT")

    class LeakSim(ES.Sim):
        def book(self, t, s, dq, ref_px, slip, maker, kind, A):
            fee0 = self.acc["fee"]
            out = super().book(t, s, dq, ref_px, slip, maker, kind, A)
            self.K += self.acc["fee"] - fee0          # mutation: the fee is reported but never leaves equity
            return out
    kn = {k: False for k in ES.KNOBS}
    SL = LeakSim(M, cal, "live", kn, X=X, panel=P, fund=F, seed=0, run_start_anchor=G.PERIODS["CAL"]["run_start_anchor"],
                 last_anchor=G.PERIODS["CAL"]["last_anchor"])
    e2 = c5_accounting(SL.run())
    check("5 accounting mutation (fee not booked to equity) turns it RED", e2 > 1e-3, f"max identity error {e2:,.4f} USDT")
    # [6]
    S1, W1 = run(ES, M, cal, X, P, F)
    same = len(W0) == len(W1) and all(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) for a, b in zip(W0, W1))
    Sd, Wd = run(ES, M, cal, X, P, F, seed=1)
    dseed = sum(abs(a["turnover"] - b["turnover"]) for a, b in zip(W0, Wd))
    check("6 determinism baseline (same seed ⇒ identical windows; seed 1 ⇒ a different path)", same and dseed > 1.0,
          f"{len(W0)} windows identical; seed 1 Σ|Δ turnover| {dseed:,.0f} USDT")
    cal2 = copy.deepcopy(cal); cal2["params"]["completion"]["pi_fill"] += 0.10
    S2, W2 = run(ES, M, cal2, X, P, F)
    diff = sum(abs(a["turnover"] - b["turnover"]) for a, b in zip(W0, W2))
    check("6 calibration binding mutation (π + 0.10) changes the output", diff > 1.0, f"Σ|Δ turnover| {diff:,.2f} USDT")
    # [8] V1b on the real CAL windows
    live_w = G.population("CAL"); lt, _ = V1.live_turnover(M, live_w)
    same_w = [dict(w, turnover=t) for w, t in zip(live_w, lt)]
    it = G.judge_v1b(same_w, live_w, lt, label="CAL", declared=G.population("CAL"))
    check("8 V1b judge baseline judge(live, live) on the real CAL windows", all(x["pass"] for x in it.values()), f"{sum(x['pass'] for x in it.values())}/{len(it)} items")
    muts = {"t1 + 7200 s": ([dict(w, t1=w["t1"] + 7200) for w in same_w], "E3_t1"),
            "one window dropped": (same_w[:-1], "E1_population"),
            "price sign-flipped (−live)": ([dict(w, price_trade=-w["price_trade"]) for w in same_w], "W_price_and_trading"),
            "fee ×1.4": ([dict(w, fee=w["fee"] * 1.4) for w in same_w], "W_fee")}
    for name, (mw, item) in muts.items():
        it2 = G.judge_v1b(mw, live_w, lt, label="CAL", declared=G.population("CAL"))
        check(f"8 V1b mutation {name} ⇒ item {item} FAIL", not it2[item]["pass"], f"{item} pass={it2[item]['pass']}")
    # [9]
    kinds, over, orphan, sef, n_es, n_pl = c9_no_guarantee(S0)
    check("9 R5-06 no guaranteed fills baseline", n_pl > 0 and kinds.get("exit_completion", 0) == 0 and not over and not orphan and not sef,
          f"{n_pl} filled plans, leg kinds {dict(kinds)}, {len(over)} overfilled, {len(orphan)} fills without a sent plan, "
          f"{len(sef)} of {n_es} skipped sub-floor exits filled")
    Se, _ = run(ES, M, cal, X, P, F, legacy_exit_completion=True)
    kinds2, over2, orphan2, sef2, n_es2, _ = c9_no_guarantee(Se)
    check("9 R5-06 mutation --legacy-exit-completion turns it RED", kinds2.get("exit_completion", 0) > 0 and (len(over2) + len(orphan2) + len(sef2)) > 0,
          f"{kinds2.get('exit_completion', 0)} guaranteed completion legs, {len(over2)} overfilled plans, {len(orphan2)} fills without a sent plan")
    dust = [(w["end_n_dust"], w["end_dust_usdt"]) for w in W0]
    print(f"      dust exposure (seed 0, CAL): mean {sum(d[0] for d in dust) / len(dust):.1f} names / {sum(d[1] for d in dust) / len(dust):.2f} USDT per window end, "
          f"max {max(d[0] for d in dust)} names / {max(d[1] for d in dust):.2f} USDT", flush=True)
    # [10]
    inv_anchors = [pick[0], pick[2], pick[3], pick[5]]
    n10, d10 = c10_invariance(ES, M, cal, X, P, F, inv_anchors, S0)
    check("10 R5-01 future-price invariance baseline (prices after t_dec(A) × [0.7, 1.3] per symbol ⇒ every decision up to A identical)",
          n10 > 0 and not d10, f"{len(inv_anchors)} cut anchors, {n10} decisions compared, {len(d10)} differ")
    n10m, d10m = c10_invariance(ES, M, cal, X, P, F, inv_anchors, S0, legacy_decision_lookahead=True)
    check("10 R5-01 mutation --legacy-decision-lookahead turns it RED", len(d10m) > 0, f"{len(d10m)} of {n10m} decisions moved with future prices, e.g. {d10m[:3]}")
    # [11]
    n11, b11 = c11_fill_clock(S0)
    check("11 R5-01 fill clock baseline (every rebalance fill at t_dec + calibrated offset, or 1 s before its own readback)", n11 > 0 and not b11,
          f"{n11} rebalance fill events, {len(b11)} off-clock; atoms clamped {S0.clamp_stats.get('n_atoms_clamped', 0)}")
    n11m, b11m = c11_fill_clock(Sbm)
    check("11 R5-01 mutation --legacy-book-at-decision turns it RED", len(b11m) > 0, f"{len(b11m)} of {n11m} fills booked at the decision instant")
    # [12]
    blk = ES.initial_block(S0, {})
    n_rb, n_blk, sealed, sha_ok = c12_initial(M, S0, blk)
    check("12 R5-13 initial population baseline (receipt = independently counted t0 readback, sealed before the run, sha reproducible)",
          n_rb > 0 and n_rb == n_blk and sealed and sha_ok and S0.sealed_sha == ES.canon_sha(S0.sealed), f"t0 readback {n_rb} nonzero, receipt {n_blk}, sealed {sealed}, sha ok {sha_ok}, positions after run {len(S0.q)}")
    blk2 = ES.initial_block(S0, {"legacy_unsealed_initial": True})
    check("12 R5-13 mutation --legacy-unsealed-initial turns it RED", blk2["n_positions"] != n_rb, f"receipt would say {blk2['n_positions']} vs readback {n_rb}")
    v2r = json.load(open(os.path.join(HERE, "SIM_v2_live_20260826_20260918.json")))["initial_state"]["n_positions"]
    check("12 R5-13 the committed v2 receipt fails the same check (reviewer: 328 vs 241)", v2r != n_rb, f"v2 receipt 'initial' {v2r} vs readback {n_rb}")
    # [13]
    viol = C.blind_violations(cal)
    check("13 blind protocol baseline (v3 calibration: no arm / experiment key anywhere)", not viol and "params" in cal, f"{len(viol)} violations")
    cal3 = copy.deepcopy(cal); cal3["params"]["completion"]["fill_rate_chase_arm"] = 0.5
    check("13 blind protocol mutation (injected per-arm key) is caught", len(C.blind_violations(cal3)) > 0, C.blind_violations(cal3))

    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    if n_ok == len(RESULTS):
        print(f"BATTERY VERDICT: ALL PASS {n_ok}/{len(RESULTS)} checks (baselines green first, every mutation red; reviewer cases red on v2)")
        sys.exit(0)
    print(f"BATTERY VERDICT: FAILURES {len(RESULTS) - n_ok}/{len(RESULTS)} checks failed: " + "; ".join(n for n, ok, _ in RESULTS if not ok))
    sys.exit(1)


if __name__ == "__main__":
    main()
