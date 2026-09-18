#!/usr/bin/env python3
"""FP3 Q6 SHADOW v3 (2026-09-18; read-only, nothing wired into production) — the frozen contract, not a relaxation of a different one.

Contract: docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md §1c/§1d (where §1/§1b conflict, §1c governs). Oracle: the production
pure module live/reconcile_carry.py @409ea16 (support/reconcile_carry_409ea16.py, sha recorded) — `feasible_exact` is the contract on the lot
lattice by enumeration; it refuses large domains, so this device solves the SAME constraint set as a mixed-integer program in lot units (exact on the
lattice, HiGHS) and cross-checks against the oracle wherever the oracle can enumerate. The two must agree; any disagreement is reported, never hidden.

Per symbol s, one EPOCH (no split at protective flattens — a flatten readback is an observation equation, position → 0 at its read_ts; the only
legitimate epoch boundary is a user-signed accounting row, and none exists ⇒ the epoch starts at the first post_anchor readback inside the copy
window, declared as the OFFLINE SCAN BASELINE Q_s(t_0)). Observation times t_0 < t_1 < … are the post_anchor readbacks' own read_ts (same
cross-section: only evidence with event time ≤ read_ts enters that equation) plus flatten readbacks.
  requests i: side σ_i ∈ {+1,−1} from the order row; capacity Q_i = |qty| (NON-NEGATIVE coordinates; SELL quantities are signed in the ledger);
              birth b_i = submit_ts (else the order row's anchor time); terminal d_i = max(cancel_ts, last_fill_ts, last attributed fill) or None (open);
              evidence floor C_i(t) = max(|confirmed_qty| when the ledger says confirmed, Σ fills attributed to i with fill_ts ≤ t) — attributed fills RAISE
              the floor, they are never a separate known increment; exact total when terminal AND confirmed_qty_final; state=rejected ⇒ exact 0.
              Identity = client_id; duplicate ledger entries are ONE request (contradictory duplicates ⇒ UNMEASURABLE); a missing side, exact > cap,
              floor > cap, exact < floor ⇒ UNMEASURABLE for the symbol from that request's birth on (no fact is dropped to make it computable).
  variables:  x_i(t_k) in lots, integer; 0 before birth; monotone; the first observation at/after d_i is still free, CONSTANT from the next on
              (an unknown past is not future capacity); x_i(t_k) ∈ [C_i(t_k), Q_i]; = exact from the pin on.
  equation k: Σ_i σ_i [x_i(t_k) − x_i(t_0)] + U_k = Q_s(t_k) − Q_s(t_0)   with U_k = Σ UNATTRIBUTED fills (symbol, trade_id) in (t_0, t_k] (signed lots)
  admission:  chronological (§1d.2): distance at k = min |RHS_k − LHS_k| over the set admitted so far; 0 ⇒ admitted; > 0 ⇒ EXCLUDED OBSERVATION
              (recorded with anchor, reading, distance; never re-ordered; hard constraints never degrade). Hard set infeasible ⇒ UNMEASURABLE.
Evidence grades (declared, see receipt): from 2026-09-13 the request ledger exists (client_id, confirmed_qty[_final], trade_qty per trade id) ⇒ requests
are precise; before it, orders rows carry no request ledger and no filled_qty ⇒ requests are DERIVED from the row (cap = intended_notional /
(a submitted order of a known SIDE, terminal inside its run; capacity UNKNOWN because the submitted quantity is not stored and intended_notional /
price_submit is an estimate the executor's own quantities exceed; floor = attributed fills; terminal_reason venue_reject ⇒ exact 0) — weaker
evidence: a balance can only be flagged there when no combination of the submitted sides and the recorded fills reaches the reading; the receipt
separates the two regimes.
Fill attribution precedence: (1) the fill's (symbol, trade_id) appears in a ledger entry's trade_qty; (2) the fill's (rebalance_id, symbol,
attempt_idx) names client_id rid-SYMBOL-attempt; (3) fixture fallback (rows without those keys): the UNIQUE request of the same symbol and side alive at
fill_ts; else UNATTRIBUTED (signed known increment with identity (symbol, trade_id)). Fills are de-duplicated by (symbol, trade_id) (the ledger writes an
original and a backfilled copy; cores identical, the backfilled copy is kept for its observation time).
Snapshot time (R13, accepted): `max(cancel_ts, last_fill_ts)` is a SOURCED WEAK BOUND on when a request's `confirmed_qty` snapshot was taken —
NOT that moment. `cancel_ts` is the local time of the cancel response; `confirmed_qty` can be raised later by the child-fill set; and several
requests share one order row's aggregate clock. Each request records `snapshot_time_source`, and a row carrying neither field says so
("ABSENT:…", counted as `requests_without_snapshot_time`) instead of silently falling back. Cumulative snapshots are kept as a LADDER of
(value, event time) steps, never as one scalar.
Two clocks: the primary column is the OFFLINE reconstruction (all evidence by event time). An ONLINE column (evidence admitted only when its observation
time ≤ read_ts) is computed only when EVERY piece of evidence of that symbol carries an observation time (fills: backfilled_utc); order rows store no
write time ⇒ on the real ledger the online column is UNAVAILABLE and says so.
Categories per (symbol, observation): CLEAN (distance 0, or distance × mark ≤ 1 USDT) / FLAGGED (> 1 USDT) / MISSING_PRICE (distance > 0, no mark at
or before the observation) / UNMEASURABLE (reason). Mark = |notional/qty| of the readback when qty ≠ 0, else the latest earlier mark of the symbol
(readback or fill price). Persistent = FLAGGED on ≥ 6 post_anchor observations. Distance = 0 proves nothing about the truth (it is compatible with
the evidence); a FLAGGED distance is a balance no admissible trajectory of the recorded requests and fills can produce.
env: Q6_REPO (default ~/dl_quant_live; must contain state/live/pilot_log/<day>/{orders,fills,position_readback,anchors}.jsonl),
     Q6_FILTERS (lot steps; default <REPO>/state/live/exchange_info_cache.json; absent ⇒ step 1.0 for every symbol, recorded), Q6_PROCS (workers).
usage: q6_shadow.py <from_day> <to_day> <out.json>"""
import sys, os, json, time, glob, hashlib, collections, math
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "support"))
import reconcile_carry_409ea16 as ORACLE                                   # pure functions; the frozen production module, never the live tree

VERSION = "v6"; DEVICE = "q6_shadow.py"; FLAG_USDT = 1.0; PERSIST_N = 6; LOT_TOL = 1e-6
ORACLE_MAX_TRAJ = 200_000                                                  # cross-check budget for the enumeration oracle


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def U(t):
    return time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))


def B(t):
    return int(float(t) // 14400 * 14400)


def parse_utc(s):
    try:
        return time.mktime(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception:   # noqa: BLE001
        return None


def lots(q, step):
    """quantity → lot units (rounded); returns (int lots, residual in lots)"""
    v = float(q) / step; n = int(round(v)); return n, abs(v - n)


# ───────────────────────────── ledger → facts ─────────────────────────────
def load_days(P, F, T):
    days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if F <= d.split("/")[-1] <= T)
    rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
    files = {}
    for d in days:
        for n in ("orders", "fills", "position_readback", "anchors"):
            p = f"{P}/{d}/{n}.jsonl"
            if os.path.exists(p): files[f"{d}/{n}.jsonl"] = sha(p)
    return days, rows, files


def floor_ladder_add(r, value, ts, source=None):
    """★ R13-Q1 (independent review round 13): a cumulative snapshot is a (value, event time) FACT, not a scalar. Replacing an older, smaller
    floor with a newer, larger one erased the earlier constraint and with it the earlier anomaly (BUY2 known ≥1 at t1 and ≥2 at t2, observed
    increment 0 then 2, read CLEAN twice while the contract gives distance 1 at t1). Every step is kept; `floor_at` reads the ladder AS OF t_k.
    The ladder is stored monotone non-decreasing in value and sorted by time; a step with no time applies from the request's birth (and says so)."""
    if value is None or value <= 0: return
    steps = r.setdefault("floor_steps", [])
    if any(st[0] == ts and st[1] == value for st in steps): return
    steps.append([ts, int(value), source])
    steps.sort(key=lambda st: (st[0] is not None, st[0] if st[0] is not None else 0.0))
    best = 0; keep = []
    for st in steps:                                                        # a later step may only TIGHTEN: drop any step that does not raise the bound
        if st[1] > best: best = st[1]; keep.append(st)
    r["floor_steps"] = keep
    r["floor"] = keep[-1][1] if keep else 0                                 # scalar kept in sync: the final (largest) bound …
    r["floor_ts"] = keep[-1][0] if keep else None                           # … and the time it took effect (checkpoint / late-fact compatibility)


def fact_conflict(p, r):
    """★ R14-Q1 (independent review round 14): the hard-fact compatibility test for two records of the SAME request identity (§1d.4), returning a
    reason or None. It used to live INLINE in build_requests, so the checkpoint resume path merged without it: the reviewer's real-CLI pair (day 1
    the same client_id is BUY 3, day 2 it is SELL 3) gave two UNMEASURABLE in one pass and two CLEAN when resumed, because the merge kept the old
    side. A restart may never change the verdict on identical facts, so both entries now go through this one predicate."""
    if (p.get("cap"), p.get("side")) != (r.get("cap"), r.get("side")):
        return f"cap/side {p.get('cap')}/{p.get('side')} vs {r.get('cap')}/{r.get('side')}"
    if p.get("exact") is not None and r.get("exact") is not None and p["exact"] != r["exact"]:
        return f"exact total {p['exact']} vs {r['exact']}"
    return None


def hard_fact_times(r):
    """every event time at which one of this record's HARD facts takes effect (§1d.3): floor-ladder steps, the exact total, the terminal, fills."""
    ts = [st[0] for st in (r.get("floor_steps") or []) if st[0] is not None]
    if r.get("exact") is not None and r.get("exact_ts") is not None: ts.append(r["exact_ts"])
    if r.get("terminal") is not None: ts.append(r["terminal"])
    ts += [f[0] for f in (r.get("fills") or [])]
    return [t for t in ts if t is not None]


def _merge_facts(p, r, notes):
    """merge a duplicate ledger record into the request already held: EVERY fact class separately, each keeping its earliest effective time
    (R12-Q1b). `terminal` is a hard constraint, so a later row that only flips it must not be discarded.

    ★ R14-Q1 / R15-Q1: the PAIRWISE compatibility test `fact_conflict` is performed HERE, first, so the merge is structurally impossible without it —
    an incompatible pair returns the reason and merges NOTHING (the caller records the symbol UNMEASURABLE), a compatible pair merges and returns None.
    This is one of Q6's TWO contradiction predicates and it now has ONE enforced home (every merge path calls this function); the other is the
    WHOLE-RECORD `contradiction_check`, enforced at the single model-assembly choke point. They catch different failures — a pairwise identity conflict
    here (differing cap/side, or two credible exact totals) vs a finalised request whose own floor/exact/cap are mutually inconsistent there — and
    neither can be skipped by adding a new build path, because this one is inside the merge and that one is at the choke point every symbol passes."""
    why = fact_conflict(p, r)
    if why: return why                                                      # incompatible identities: merge NOTHING, hand the reason back to the caller
    p["trade_ids"] |= r["trade_ids"]
    for st in (r.get("floor_steps") or []): floor_ladder_add(p, st[1], st[0], st[2] if len(st) > 2 else None)   # R13-Q1: every step, never a replacement
    if p["exact"] is None and r["exact"] is not None: p["exact"], p["exact_ts"] = r["exact"], r.get("exact_ts")
    if r["terminal"] is not None:
        p["terminal"] = r["terminal"] if p["terminal"] is None else min(p["terminal"], r["terminal"])
        notes["duplicate_terminal_adopted"] += 1
    notes["duplicate_identity_merged"] += 1
    return None


def build_requests(od, step_of, notes):
    """symbol → [request dict]; a request = one client_id (ledger) or one submitted order row (derived, pre-ledger)."""
    REQ = collections.defaultdict(dict)                                     # symbol → client_id → request
    unmeas = collections.defaultdict(list)                                  # symbol → [(birth, reason)]
    for o in od:
        s = o["symbol"]; step = step_of(s); side_s = str(o.get("side") or "").lower()
        side = 1 if side_s == "buy" else (-1 if side_s == "sell" else None)
        birth = float(o.get("submit_ts") or o["anchor_ts"])
        term_rec = max([float(o[k]) for k in ("cancel_ts", "last_fill_ts") if o.get(k)] or [0.0])
        rl = o.get("request_ledger") or []
        if rl:
            for e in rl:
                cid = e.get("client_id") or f"{o.get('rebalance_id')}-{s}-{o.get('attempt_idx')}"
                st = str(e.get("state") or "")
                qty = e.get("qty")
                if st == "rejected" or (qty is None and o.get("terminal_reason") == "venue_reject"):
                    cap_l, exact_l, floor_l, terminal = 0, 0, 0, True; ev = "ledger:rejected(exact 0)"
                else:
                    if side is None: unmeas[s].append((birth, f"{cid}: side missing")); continue
                    cap_l, r1 = lots(abs(float(qty or 0.0)), step)
                    cq = e.get("confirmed_qty"); terminal = bool(e.get("terminal"))
                    floor_l = lots(abs(float(cq)), step)[0] if (cq is not None and st == "confirmed") else 0
                    exact_l = floor_l if (terminal and bool(e.get("confirmed_qty_final")) and cq is not None) else None
                    ev = "ledger:" + ("final" if exact_l is not None else ("confirmed_floor" if floor_l else "cap_only")) + (" inconsistent_note" if e.get("inconsistent") else "")
                    if r1 > LOT_TOL: notes["off_lattice_request_qty"] += 1
                # ★ R12-Q1a (independent review round 12): a cumulative snapshot (confirmed_qty) constrains x_i(t) ≥ C only from the moment that
                #   snapshot was TAKEN (PREREG §1c.5), never from the request's birth: monotonicity gives x_i(t) ≤ x_i(τ) before τ, not ≥. The ledger
                #   stores no read time for confirmed_qty; the defensible event time is the request's own settlement (max cancel_ts / last_fill_ts),
                #   which is when the executor settled and wrote it. floor_ts = that time; before it only ATTRIBUTED FILLS (own event times) bound x_i.
                _snap_ts = (max(term_rec, birth) if term_rec else None)
                _snap_src = "weak_bound:max(cancel_ts,last_fill_ts)" if term_rec else "ABSENT:no cancel_ts / last_fill_ts on the row ⇒ the floor applies from birth"
                if not term_rec: notes["requests_without_snapshot_time"] += 1
                r = {"rid": cid, "side": side if side is not None else 0, "cap": cap_l, "birth": birth, "terminal": (max(term_rec, birth) if terminal else None),
                     "floor": 0, "floor_ts": None, "floor_steps": [], "snapshot_time_source": _snap_src, "exact": exact_l, "exact_ts": _snap_ts,
                     "fills": [], "trade_ids": set(str(t) for t in (e.get("trade_qty") or {})), "source": "ledger", "evidence": ev,
                     "bucket": B(o["anchor_ts"]), "rebalance_id": o.get("rebalance_id"), "attempt_idx": o.get("attempt_idx")}
                floor_ladder_add(r, floor_l, _snap_ts, _snap_src)
                if cid in REQ[s]:                                           # duplicate identity ⇒ ONE request; contradictory duplicates ⇒ unmeasurable
                    p = REQ[s][cid]
                    # ★ R12-Q1b: numerically identical rows are NOT necessarily the same FACTS — a later row may add `terminal` (or a floor/exact
                    #   whose event time is earlier). Merging only trade ids silently dropped the terminal constraint, so a post-terminal position
                    #   growth stayed CLEAN. Every fact class is merged with its own effective time. R14-Q1/R15-Q1: the pairwise compatibility test now
                    #   lives INSIDE `_merge_facts` (it returns the reason and merges nothing on conflict), so build and resume cannot disagree and no
                    #   merge path can bypass it.
                    _why = _merge_facts(p, r, notes)
                    if _why:
                        unmeas[s].append((birth, f"{cid}: duplicate identity with contradictory facts ({_why})")); notes["duplicate_identity_contradictory"] += 1
                else:
                    REQ[s][cid] = r
            continue
        # ── pre-ledger rows: a request only if something was submitted ──
        tr = o.get("terminal_reason")
        if not o.get("submit_ts") or tr in ("skipped_min_notional", "skipped_no_chase_arm", "blocked_by_halt"):
            continue
        cid = f"{o.get('rebalance_id')}-{s}-{o.get('attempt_idx')}"
        if side is None: unmeas[s].append((birth, f"{cid}: side missing")); continue
        if tr == "venue_reject":
            cap_l, exact_l, floor_l, terminal, ev = 0, 0, 0, True, "derived:venue_reject(exact 0)"
        else:
            # the submitted quantity is NOT stored on pre-ledger rows and intended_notional / price_submit is an ESTIMATE, not evidence (the
            # executor's own quantity exceeded it on real rows): capacity is UNBOUNDED; the facts are the side, the terminal window and the fills
            cap_l, exact_l, floor_l, terminal, ev = None, None, 0, True, "derived:side+fills_only(capacity unknown)"
            notes["derived_requests_unbounded_capacity"] += 1
        _snap_ts = (max(term_rec, birth) if term_rec else None)
        _snap_src = "weak_bound:max(cancel_ts,last_fill_ts)" if term_rec else "ABSENT:no cancel_ts / last_fill_ts on the row ⇒ the floor applies from birth"
        if not term_rec: notes["requests_without_snapshot_time"] += 1
        REQ[s][cid] = {"rid": cid, "side": side, "cap": cap_l, "birth": birth, "terminal": max(term_rec, birth) if terminal else None, "floor": 0, "exact": exact_l,
                       "floor_ts": None, "floor_steps": [], "snapshot_time_source": _snap_src, "exact_ts": _snap_ts,
                       "fills": [], "trade_ids": set(), "source": "order_row_derived", "evidence": ev, "bucket": B(o["anchor_ts"]), "terminal_reason": tr,
                       "rebalance_id": o.get("rebalance_id"), "attempt_idx": o.get("attempt_idx")}
        floor_ladder_add(REQ[s][cid], floor_l, _snap_ts, _snap_src)
    return REQ, unmeas


def attribute_fills(fills_by_symbol, REQ, notes, trade_id_only=False):
    """attach fills to requests (precedence: ledger trade ids → rid/attempt → unique alive same-side); the rest are unattributed increments.

    ★ R16 `trade_id_only`: use ONLY the DEFINITIVE ledger-trade-id path. This is how carried UNATTRIBUTED fills are RE-OFFERED on resume. The checkpoint
    does not persist a fill's rebalance_id/attempt_idx (UN tuples are (ts, signed lots, obs_time, trade_id)), so the rid-attempt and unique-alive-same-side
    INFERENCES cannot be reproduced from it — and they must not be re-run on a lossy reconstruction: forcing rid/attempt=None made carried-un fills
    eligible for unique-alive and over-attributed 87 of them on the real 41-day ledger (2496 spurious UNMEASURABLE, resume ≠ single pass). Neither
    inference can legitimately re-fire for a carried-un fill anyway: an order row is submitted BEFORE its fill, so a fill's rid-attempt match was already
    present in the window that left it unattributed; and unique-alive depends on the same-side alive candidate set at the fill's time, which the resumed
    merge does not change (later requests are born later). Only a request whose trade_ids now DEFINITIVELY include the fill can re-claim it."""
    UN = collections.defaultdict(list)                                      # symbol → [(fill_ts, signed lots, obs_time, trade_id)]
    for s, fl in fills_by_symbol.items():
        reqs = REQ.get(s, {}); by_tid = {}; by_key = {}
        for cid, r in reqs.items():
            for t in r["trade_ids"]: by_tid[t] = cid
            if r.get("rebalance_id") is not None and r.get("attempt_idx") is not None: by_key[(r["rebalance_id"], int(r["attempt_idx"]))] = cid
        for f in fl:
            cid = by_tid.get(str(f["trade_id"]))
            how = "ledger_trade_id" if cid else None
            if not trade_id_only and cid is None and f.get("rebalance_id") is not None and f.get("attempt_idx") is not None:
                cid = by_key.get((f["rebalance_id"], int(f["attempt_idx"]))); how = "rid_attempt" if cid else None
            if not trade_id_only and cid is None and f.get("rebalance_id") is None and f.get("attempt_idx") is None:
                cands = [c for c, r in reqs.items() if r["side"] == f["side"] and r["birth"] <= f["ts"] + 1e-9 and (r["terminal"] is None or f["ts"] <= r["terminal"] + 14400)]
                if len(cands) == 1: cid = cands[0]; how = "unique_alive_same_side"
                elif len(cands) > 1: notes["fill_attribution_ambiguous_left_unattributed"] += 1
            if cid is not None and reqs[cid]["side"] != f["side"]:
                notes["fill_side_disagrees_with_request_left_unattributed"] += 1; cid = None
            if cid is not None:
                reqs[cid]["fills"].append((f["ts"], f["lots"], f["obs_time"], f["trade_id"])); notes["fills_attributed_" + how] += 1
            else:
                UN[s].append((f["ts"], f["side"] * f["lots"], f["obs_time"], f["trade_id"])); notes["fills_unattributed"] += 1
    for s in REQ:
        for r in REQ[s].values():
            r["fills"].sort(key=lambda f: f[0])
            if r["fills"] and r["terminal"] is not None and r["fills"][-1][0] > r["terminal"]: r["terminal"] = r["fills"][-1][0]; notes["terminal_extended_to_last_fill"] += 1
    return UN


def contradiction_check(REQ, unmeas, notes, symbols=None, note_key="request_contradiction", dedupe=False):
    """PREREG §1d.4: a request whose HARD facts contradict each other makes the symbol UNMEASURABLE from its birth on; no fact is dropped.

    ★ R15-Q1 (independent review round 15): after a checkpoint resume the merge can raise a carried request's floor (a fresh floor-ladder step, or
    fresh fills attributed onto it) or supply an exact total, any of which pushes floor > cap or the exact total outside [floor, cap]. `fact_conflict`
    only compares (cap, side) and two exact totals, so a contradiction CREATED BY THE MERGE read CLEAN. The resume path re-runs this over the merged
    requests with `symbols` scoped to the resumed set, `note_key` counting the merge-created contradictions separately, and `dedupe` so a contradiction
    already recorded (the pre-merge fresh scan, or a carried `unmeasurable_from`) is not appended or counted a second time."""
    for s in (list(REQ) if symbols is None else [x for x in symbols if x in REQ]):
        for r in REQ[s].values():
            fsum = sum(l for (ft, l, ot, tid) in r["fills"]); floor = max(r["floor"], fsum); why = None
            cap = r["cap"]
            if cap is not None and cap < 0: why = "capacity negative"
            elif cap is not None and floor > cap: why = f"evidence floor {floor} exceeds capacity {cap} lots"
            elif r["exact"] is not None and ((cap is not None and r["exact"] > cap) or r["exact"] < floor): why = f"credible total {r['exact']} outside [floor {floor}, cap {cap}] lots"
            if why:
                entry = (r["birth"], f"{r['rid']}: {why}")
                if dedupe and entry in (unmeas.get(s) or []): continue
                unmeas[s].append(entry); notes[note_key] += 1


# ───────────────────────────── §1d.5 joint checkpoint / §1d.3 late-evidence rebuild ─────────────────────────────
CHECKPOINT_SCHEMA = "q6_joint_checkpoint/2"                                 # /2: the state sha covers records+marks and the code/input/epoch identity (R14-Q5)
EPOCH_DECLARATION = ("OFFLINE SCAN BASELINE: one epoch per symbol from its first post_anchor readback inside the copy window. This is NOT a "
                     "user-signed accounting epoch; no authorised clearing row exists, so carried history is audit state, not settled debt.")
POLICY = {"name": "chronological_admission", "revision": "PREREG_reconcile_carry_forward_unexplained_2026-09-10 §1d rev 4"}


def canon(obj):
    """canonical bytes for a state: sorted keys, compact separators, sets as sorted lists. Two equal states MUST serialise equal —
    the bit-identity claim of §1d.5 ("恢复时按同一政策重放, 结果必须逐位相同") is checked on the sha256 of this."""
    def norm(o):
        if isinstance(o, dict): return {str(k): norm(o[k]) for k in sorted(o, key=str)}
        if isinstance(o, (set, frozenset)): return sorted(str(x) for x in o)
        if isinstance(o, (list, tuple)): return [norm(x) for x in o]
        return o
    return json.dumps(norm(obj), sort_keys=True, separators=(",", ":"), default=str).encode()


# ── §1d.5 material-state sha: the per-symbol fields the restart-parity claim is about (R14-Q5). The writer AND the load-time guard (R15-Q3) hash the
#    state through this ONE function, so the loader reproduces exactly what the writer wrote — two divergent copies of the field list would be a hole. ──
_SYM_FIELDS = ("hard", "observations", "admitted", "excluded", "unmeasurable_from_run", "records", "marks", "q0_lots", "step", "pending_requests")


def state_sha256_of(symbols):
    """sha256 of the canonical bytes of the per-symbol MATERIAL STATE (the _SYM_FIELDS of every symbol). `symbols` is the checkpoint's `symbols` map —
    equally the in-memory `cps` the writer builds or the JSON-loaded dict the loader reads (canon() normalises tuples/lists/sets so the two agree)."""
    return hashlib.sha256(canon({k: {kk: v.get(kk) for kk in _SYM_FIELDS} for k, v in symbols.items()})).hexdigest()


def req_to_cp(r):
    """a request serialised as its HARD-CONSTRAINT GENERATORS. PREREG §1c.4 / D7-4: the checkpoint saves the objects that GENERATE the joint
    feasible set (identity, side, capacity, birth, terminal, evidence floors with their event times, attributed fills) — never the per-request
    marginal interval, which loses the correlation between requests."""
    return {"rid": r["rid"], "side": r["side"], "cap": r["cap"], "birth": r["birth"], "terminal": r["terminal"],
            "floor": r["floor"], "floor_ts": r.get("floor_ts"), "floor_steps": [list(st) for st in (r.get("floor_steps") or [])],
            "snapshot_time_source": r.get("snapshot_time_source"), "exact": r["exact"], "exact_ts": r.get("exact_ts"),
            "fills": [[f[0], f[1], f[2], str(f[3])] for f in r["fills"]], "trade_ids": sorted(str(x) for x in (r.get("trade_ids") or [])),
            "source": r["source"], "evidence": r.get("evidence"), "rebalance_id": r.get("rebalance_id"), "attempt_idx": r.get("attempt_idx"),
            "terminal_reason": r.get("terminal_reason"), "bucket": r.get("bucket")}


def req_from_cp(d):
    r = dict(d); r["fills"] = [(f[0], f[1], f[2], f[3]) for f in (d.get("fills") or [])]; r["trade_ids"] = set(d.get("trade_ids") or [])
    r["floor_steps"] = [list(st) for st in (d.get("floor_steps") or [])]
    if not r["floor_steps"] and (d.get("floor") or 0) > 0: floor_ladder_add(r, d["floor"], d.get("floor_ts"), d.get("snapshot_time_source"))   # older checkpoints
    return r


def merge_late_fact(r, fact, notes=None):
    """PREREG §1d.3: a hard fact arriving late is inserted at ITS OWN event time; it may only tighten. Returns True when anything changed."""
    ch = False
    # ★ R14-Q5: the guard used to be `fact["floor"] > r["floor"]`, comparing against the SCALAR (largest) bound — so a late SMALLER bound at an
    #   EARLIER time was dropped as "no change" even though it constrains a window the large one does not. The ladder already keeps every
    #   (value, time) step and prunes only steps that tighten nothing, so the fact goes straight to it and change is detected on the ladder.
    if fact.get("floor") is not None:
        _before = [list(x) for x in (r.get("floor_steps") or [])]
        floor_ladder_add(r, fact["floor"], fact.get("floor_ts"), fact.get("snapshot_time_source") or "late_evidence")
        if [list(x) for x in (r.get("floor_steps") or [])] != _before: ch = True
    if fact.get("exact") is not None:
        # ★ R14-Q5: two credible exact totals for one request identity is a HARD contradiction (§1d.4) — the arrival order may not pick a winner.
        if r["exact"] is not None and r["exact"] != fact["exact"]:
            r["hard_contradiction"] = f"{r['rid']}: two credible exact totals {r['exact']} vs {fact['exact']}"
            if notes is not None: notes["late_fact_contradictory_exact"] += 1
            return True
        if r["exact"] is None:
            r["exact"] = fact["exact"]; r["exact_ts"] = fact.get("exact_ts"); ch = True
    if fact.get("terminal") is not None and (r["terminal"] is None or fact["terminal"] < r["terminal"]):
        r["terminal"] = fact["terminal"]; ch = True
    for f in (fact.get("fills") or []):
        if str(f[3]) not in {str(x[3]) for x in r["fills"]}:
            r["fills"].append((f[0], f[1], f[2], f[3])); r["fills"].sort(key=lambda x: x[0]); ch = True
    if ch and notes is not None: notes["late_facts_merged"] += 1
    return ch


def fact_event_time(fact):
    """the event time a late fact takes effect at (§1d.3): the earliest of its own stamps"""
    ts = [fact[k] for k in ("floor_ts", "exact_ts", "terminal") if fact.get(k) is not None] + [f[0] for f in (fact.get("fills") or [])]
    return min(ts) if ts else None


def late_evidence_rebuild(cp_sym, late_facts, notes=None):
    """PREREG §1d.3: a HARD fact whose event time precedes already-admitted observations is inserted at its own event time, and the admission
    prefix is REBUILT from that time (hard constraints first, then chronological admission). Equations admitted before and now infeasible are
    downgraded to excluded observations tagged `late_evidence`. The ORIGINAL online receipts are returned untouched — §1d.3 forbids rewriting
    them ("原始在线收据一律保留, 不重写"). Order independence: the same facts arriving early or late end at the same distance.

    Returns {records, admitted, excluded, tau, newly_excluded, records_before (the preserved online receipts), requests}."""
    notes = collections.Counter() if notes is None else notes
    reqs = {r["rid"]: req_from_cp(r) for r in cp_sym["hard"]["requests"]}
    before = [dict(r) for r in cp_sym["records"]]
    taus = []
    for f in late_facts:
        rid = f["rid"]
        if rid in reqs:
            if merge_late_fact(reqs[rid], f, notes): taus.append(fact_event_time(f))
        else:
            reqs[rid] = req_from_cp({"rid": rid, "side": f["side"], "cap": f.get("cap"), "birth": f.get("birth", fact_event_time(f)),
                                     "terminal": f.get("terminal"), "floor": f.get("floor") or 0, "floor_ts": f.get("floor_ts"),
                                     "exact": f.get("exact"), "exact_ts": f.get("exact_ts"), "fills": f.get("fills") or [], "trade_ids": [],
                                     "source": "late_evidence", "evidence": "late:" + str(f.get("evidence") or "hard fact")})
            taus.append(fact_event_time(f)); notes["late_facts_new_request"] += 1
    _contra = next((r.get("hard_contradiction") for r in reqs.values() if r.get("hard_contradiction")), None)
    if _contra:                                                             # §1d.4: hard facts contradicting each other ⇒ the symbol is UNMEASURABLE
        notes["late_fact_hard_contradiction"] += 1
        return {"records": before, "admitted": [list(a) for a in cp_sym["admitted"]], "excluded": list(cp_sym["excluded"]), "tau": None,
                "newly_excluded": [], "records_before": before, "requests": list(reqs.values()), "no_change": False,
                "hard_contradiction": _contra, "status": "unmeasurable"}
    taus = [t for t in taus if t is not None]
    if not taus: return {"records": before, "admitted": [list(a) for a in cp_sym["admitted"]], "excluded": list(cp_sym["excluded"]),
                         "tau": None, "newly_excluded": [], "records_before": before, "requests": list(reqs.values()), "no_change": True}
    tau = min(taus)
    obs = [dict(o) for o in cp_sym["observations"]]
    un = [(f[0], f[1], f[2], f[3]) for f in cp_sym["hard"]["unattributed_fills"]]
    model = SymbolModel(cp_sym["symbol"], [r for r in reqs.values() if r["side"] != 0], un, obs, cp_sym["step"],
                        unmeas_from=[(t, w) for t, w in cp_sym["hard"]["unmeasurable_from"]] or None)
    keep = [r for r in before if r["k"] == 0 or r["t"] < tau - 1e-9]                      # the prefix that pre-dates the late fact is untouched
    resume = {"records": keep, "admitted": [[r["k"], r["rhs_lots"]] for r in keep if r.get("admitted") and r["k"] > 0],
              "unmeasurable_from_run": next((r.get("why") for r in keep if r.get("status") == "unmeasurable"), None)}
    recs = model.run(resume=resume)
    was_admitted = {r["k"] for r in before if r.get("admitted") and r["k"] > 0}
    newly = []
    for r in recs:
        if r.get("excluded") and r["k"] in was_admitted:
            r["excluded_because"] = "late_evidence"; newly.append({"k": r["k"], "rhs_lots": r["rhs_lots"], "distance_lots": r.get("distance_lots"),
                                                                   "was_distance_lots": next((b.get("distance_lots") for b in before if b["k"] == r["k"]), None)})
            notes["observations_excluded_by_late_evidence"] += 1
    return {"records": recs, "admitted": [[r["k"], r["rhs_lots"]] for r in recs if r.get("admitted") and r["k"] > 0],
            "excluded": [{"k": r["k"], "rhs_lots": r["rhs_lots"], "distance_lots": r.get("distance_lots"), "why": r.get("why"),
                          "because": r.get("excluded_because", "chronological_admission")} for r in recs if r.get("excluded")],
            "tau": tau, "newly_excluded": newly, "records_before": before, "requests": list(reqs.values()), "no_change": False}


# ───────────────────────────── the joint feasible set on the lattice ─────────────────────────────
class SymbolModel:
    """requests + observation times of ONE symbol; chronological admission with a lattice-exact MILP; oracle cross-check when enumerable."""

    def __init__(self, sym, reqs, un_fills, obs, step, evidence_filter=None, unmeas_from=None):
        self.sym, self.step, self.unmeas_from = sym, step, unmeas_from
        self.times = [o["t"] for o in obs]; self.obs = obs
        self.reqs = [r for r in sorted(reqs, key=lambda r: (r["birth"], r["rid"]))]
        self.ev = evidence_filter                                           # online clock: evidence admissible iff obs_time ≤ t (None ⇒ offline)
        T = self.times; n = len(T)
        # per request: birth index (first observation ≥ birth), pin index (first observation ≥ terminal) or None (open)
        self.meta = []
        for r in self.reqs:
            bi = next((k for k, t in enumerate(T) if t >= r["birth"] - 1e-9), None)
            pi = None if r["terminal"] is None else next((k for k, t in enumerate(T) if t >= r["terminal"] - 1e-9), None)
            self.meta.append((bi, pi))
        # unattributed increments per observation (cumulative from t_0 by event time; online clock filters by obs_time)
        self.Uk = []
        for k, t in enumerate(T):
            tot = 0
            for (ft, sl, ot, tid) in un_fills:
                if T[0] < ft <= t + 1e-9 and (self.ev is None or (ot is not None and ot <= t + 1e-9)): tot += sl
            self.Uk.append(tot)

    def floor_at(self, i, k):
        """evidence floor of request i at observation k: the LADDER of cumulative snapshots read as of t_k (R13-Q1 — every (value, event time)
        step is kept, a later larger bound never erases an earlier one) plus attributed fills with event time ≤ t_k (online clock: also obs time)"""
        return self.floor_at_time(i, self.times[k])

    def floor_at_time(self, i, t):
        """the same evidence floor read as of an arbitrary time — the pin variable needs it at the LATEST known time (R14-Q4)."""
        r = self.reqs[i]
        base = 0
        if self.ev is None:
            for st in (r.get("floor_steps") or []):
                if st[0] is None or st[0] <= t + 1e-9: base = max(base, st[1])
        fsum = sum(l for (ft, l, ot, tid) in r["fills"] if ft <= t + 1e-9 and (self.ev is None or (ot is not None and ot <= t + 1e-9)))
        return max(base, fsum)

    def _vars(self, n):
        """variable layout up to observation n: list of (i, k) with k in the request's FREE window; value map handles constants"""
        layout = []; index = {}
        for i, r in enumerate(self.reqs):
            bi, pi = self.meta[i]
            if bi is None or bi > n: continue
            last = n if pi is None else min(pi, n)
            if pi is not None and pi == 0 and bi == 0 and r["terminal"] < self.times[0]:
                continue                                                    # terminal before the baseline read: fully absorbed in Q_s(t_0)
            for k in range(bi, last + 1):
                index[(i, k)] = len(layout); layout.append((i, k))
        return layout, index

    def _x(self, i, k, index, n):
        """column index of x_i(t_k) or a constant: 0 before birth, the pin variable after the pin"""
        bi, pi = self.meta[i]
        if bi is None or k < bi: return None, 0
        if pi is not None and pi == 0 and self.reqs[i]["terminal"] < self.times[0]: return None, 0      # absorbed in Q_s(t_0)
        if pi is not None and k > pi: return index[(i, pi)], None
        return index[(i, k)], None

    def solve(self, n, admitted, rhs, known_at=None):
        """distance at observation n given admitted equations (k < n); returns dict(status, distance_lots, lhs_range).

        `known_at` (R13-Q3) is the observation index whose time decides which HARD facts are in force. It defaults to n; the prefix rebuild
        re-decides earlier observations against the facts known NOW, which is what §1d.3 means by rebuilding from the late fact's event time."""
        ka = n if known_at is None else known_at
        t_known = self.times[min(ka, len(self.times) - 1)]
        layout, index = self._vars(n); m = len(layout)
        lb = np.zeros(m + 1); ub = np.full(m + 1, np.inf); lb[0] = 0.0                # column 0 = d ≥ 0
        for c, (i, k) in enumerate(layout):
            r = self.reqs[i]; bi, pi = self.meta[i]
            lo = self.floor_at(i, k); hi = np.inf if r["cap"] is None else r["cap"]
            # ★ R14-Q4: after the terminal pin x_i is CONSTANT, so a cumulative lower bound whose event time falls after the pin still constrains
            #   the pin variable. v5 read the ladder at times[k] ≤ times[pin] only, so a post-terminal NON-final bound (the final one was already
            #   fixed in R13-Q2) had nothing to land on and vanished: BUY3 terminal with unknown total, credible bound 2 later, increment 1 ⇒ CLEAN.
            if pi is not None and k == pi: lo = max(lo, self.floor_at_time(i, t_known))
            _ets = r.get("exact_ts"); _exact_known = r["exact"] is not None and (_ets is None or _ets <= t_known + 1e-9)
            # ★ R13-Q2: an exact total that arrives AFTER the terminal pin still binds — the pin variable IS x_i for every later time, so the fact
            #   has a variable to land on whenever it arrives. v4 evaluated it at times[k] ≤ times[pin], so a late total had no variable and vanished.
            # ★ R15-Q1 (structural): this line OVERWRITES lo with the exact total, DISCARDING the evidence floor set just above. So when floor > exact
            #   the emptiness test `lo > hi` below can never fire (lo == hi == exact). The solver therefore CANNOT detect a floor-vs-exact contradiction
            #   by construction — that class is the WHOLE-RECORD `contradiction_check`'s job at the assembly choke point, never the optimisation's.
            if _exact_known and pi is not None and k >= pi: lo = hi = r["exact"]
            elif _exact_known: hi = min(hi, r["exact"])                      # monotonicity: x(t_k) ≤ x(pin) = exact
            if lo > hi: return {"status": "unmeasurable", "why": f"{r['rid']}: hard bounds empty at k={k} (floor {lo} > cap/exact {hi})"}
            lb[c + 1], ub[c + 1] = lo, hi
        A = []; lo_c = []; hi_c = []
        for c, (i, k) in enumerate(layout):                                 # monotone within the free window
            if (i, k + 1) in index:
                row = np.zeros(m + 1); row[c + 1] = 1; row[index[(i, k + 1)] + 1] = -1; A.append(row); lo_c.append(-np.inf); hi_c.append(0.0)

        def lhs_row(k):
            row = np.zeros(m + 1)
            for i, r in enumerate(self.reqs):
                for (kk, sign) in ((k, r["side"]), (0, -r["side"])):
                    col, const = self._x(i, kk, index, n)
                    if col is not None: row[col + 1] += sign
            return row
        for (k, rhs_k) in admitted:
            row = lhs_row(k); A.append(row); lo_c.append(rhs_k - self.Uk[k]); hi_c.append(rhs_k - self.Uk[k])
        row = lhs_row(n); target = rhs - self.Uk[n]
        r1 = row.copy(); r1[0] = 1.0; A.append(r1); lo_c.append(target); hi_c.append(np.inf)        # d + S ≥ target
        r2 = -row; r2[0] = 1.0; A.append(r2); lo_c.append(-target); hi_c.append(np.inf)             # d − S ≥ −target
        c = np.zeros(m + 1); c[0] = 1.0
        integrality = np.ones(m + 1); integrality[0] = 0
        res = milp(c, constraints=LinearConstraint(np.array(A), np.array(lo_c), np.array(hi_c)), integrality=integrality, bounds=Bounds(lb, ub))
        if res.status == 2: return {"status": "unmeasurable", "why": "hard constraints + admitted history infeasible (should not happen after admission)"}
        if not res.success: return {"status": "unmeasurable", "why": f"solver status {res.status}: {res.message}"}
        return {"status": "ok", "distance_lots": int(round(res.x[0])), "n_vars": m}

    def run(self, resume=None):
        """chronological admission over all observations; returns per-observation records.

        `resume` (PREREG §1d.5) carries a checkpoint prefix: the records already decided, the equations already ADMITTED and the ones already
        EXCLUDED. §1d.2 forbids re-deciding them ("已准入的等式不因后来的观测被撤销"), so the prefix is replayed verbatim and admission continues
        chronologically from the first new observation. The joint object is regenerated from the admitted equations + hard constraints, which is
        why the checkpoint stores those and not per-request marginals."""
        out = []; admitted = []; unmeasurable_from = None; n_prefix = 0
        if resume:
            out = [dict(r) for r in resume["records"]]; admitted = [tuple(a) for a in resume["admitted"]]
            n_prefix = len(out); unmeasurable_from = resume.get("unmeasurable_from_run")
        for n, o in enumerate(self.obs):
            if n < n_prefix: continue
            rec = {"k": n, "t": o["t"], "anchor": o["anchor"], "kind": o["kind"], "rhs_lots": o["rhs"],
                   "lot_residual": float(o.get("lot_residual") or 0.0), "lot_residual_base": float(self.obs[0].get("lot_residual") or 0.0)}
            if n == 0:
                rec.update(status="baseline", distance_lots=0, admitted=True); out.append(rec); continue
            if unmeasurable_from is not None:
                rec.update(status="unmeasurable", why=unmeasurable_from); out.append(rec); continue
            r = self.solve(n, admitted, o["rhs"])
            if r["status"] != "ok" and str(r.get("why", "")).startswith("hard constraints + admitted history infeasible"):
                # ★ R13-Q3: the hard facts are satisfiable on their own — what is infeasible is the ADMITTED HISTORY against them. §1d.3 calls for a
                #   PREFIX REBUILD (hard constraints first, then chronological admission), not a permanent UNMEASURABLE. v4 conflated "hard facts
                #   contradict each other" (⇒ unmeasurable, the `hard bounds empty` branch below) with "a hard fact excludes a prior observation".
                admitted, rebuilt = self._rebuild_prefix(n, out)
                r = self.solve(n, admitted, o["rhs"])
                rec["prefix_rebuilt"] = True; rec["rebuilt_excluded_k"] = rebuilt
            if r["status"] != "ok":
                unmeasurable_from = r["why"]; rec.update(status="unmeasurable", why=r["why"]); out.append(rec); continue
            d = r["distance_lots"]; rec.update(status="ok", distance_lots=d, n_vars=r["n_vars"])
            # ★ R13-Q3 (P2): an OFF-LATTICE reading must never be ADMITTED as an exact equation — v4 changed the label but still wrote the rounded
            #   x into the hard constraints, and the next observation was then judged against a quantity the venue never reported.
            if float(o.get("lot_residual") or 0.0) > LOT_TOL or float(self.obs[0].get("lot_residual") or 0.0) > LOT_TOL:
                rec["admitted"] = False; rec["off_lattice_not_admitted"] = True
            elif d == 0: admitted.append((n, o["rhs"])); rec["admitted"] = True
            else: rec["admitted"] = False; rec["excluded"] = True
            out.append(rec)
        return out

    def _rebuild_prefix(self, n, out):
        """§1d.3 prefix rebuild: re-decide observations 1…n−1 chronologically against the facts in force NOW (`known_at=n`). An equation that was
        admitted and no longer fits is downgraded to an EXCLUDED observation tagged `late_evidence`; its original record keeps the distance it was
        decided with (`distance_lots_before_rebuild`) — §1d.3 forbids rewriting the receipt that was issued at the time."""
        admitted = []; newly = []
        for j in range(1, n):
            recj = next((x for x in out if x["k"] == j), None)
            if recj is None or recj.get("status") == "baseline": continue
            rj = self.solve(j, admitted, self.obs[j]["rhs"], known_at=n)
            if rj["status"] == "ok" and rj["distance_lots"] == 0 and not recj.get("off_lattice_not_admitted"):
                admitted.append((j, self.obs[j]["rhs"]))
                if not recj.get("admitted"): recj["admitted"] = True; recj.pop("excluded", None)
            else:
                if recj.get("admitted"):
                    recj["excluded_because"] = "late_evidence"; newly.append(j)
                recj["admitted"] = False; recj["excluded"] = True
                # §1d.3: "原始在线收据一律保留, 不重写" — `distance_lots` stays the value this observation was DECIDED with; the value under the
                # facts known later is a separate field, so the receipt issued at the time and the current audit are both readable.
                if rj["status"] == "ok": recj["distance_lots_after_rebuild"] = rj["distance_lots"]
        return admitted, newly

    def oracle_check(self):
        """the production enumeration oracle on the same facts, when it can enumerate; None when it cannot (recorded in `oracle_skipped`)"""
        self.oracle_skipped = None
        if self.ev is not None: self.oracle_skipped = "online_clock"; return None
        if self.unmeas_from: return {"status": "unmeasurable", "why": "unmeasurable by construction (contradiction / missing side): " + min(self.unmeas_from)[1]}
        if any(r["cap"] is None for r in self.reqs): self.oracle_skipped = "unbounded_capacity"; return None    # the enumeration oracle needs a finite lattice
        try:
            reqs = []
            for i, r in enumerate(self.reqs):
                bi, pi = self.meta[i]
                if bi is None: continue
                # ★ R12-Q2: the production Request carries ONE static lower bound. Using the final fill sum at every time backdates evidence and
                #   made the oracle disagree with the (correct) model. Only cross-check when this request's floor is the SAME at every observation.
                _f = [self.floor_at(i, k) for k in range(len(self.times))]
                if len(set(_f)) > 1:
                    self.oracle_skipped = "time_varying_floor"; return None
                lower = _f[-1] if _f else 0
                if r["side"] == 0: return {"status": "unmeasurable", "why": "side missing"}
                reqs.append(ORACLE.Request(r["rid"], r["side"], float(r["cap"]), float(r["birth"]), None if r["terminal"] is None else float(r["terminal"]), float(lower), None if r["exact"] is None else float(r["exact"])))
            est = 1
            for rq in reqs:
                est *= max(len(rq.domain(self.times[-1], 1.0)), 1) ** len(self.times)
                if est > ORACLE_MAX_TRAJ: self.oracle_skipped = "domain_too_large"; return None
            obs = [float(o["rhs"] - self.Uk[k]) for k, o in enumerate(self.obs)]
            return ORACLE.feasible_exact(reqs, self.times, obs, step=1.0, max_trajectories=ORACLE_MAX_TRAJ)
        except Exception as e:   # noqa: BLE001
            return {"status": "error", "why": repr(e)}


# ───────────────────────────── per-symbol worker ─────────────────────────────
def symbol_job(args):
    sym, reqs, un, obs, step, marks_hint, unmeas_from, resume = args
    reqs = [r for r in reqs if r["side"] != 0]
    model = SymbolModel(sym, reqs, un, obs, step, unmeas_from=unmeas_from)
    recs = model.run(resume=resume)
    # unmeasurable-from (contradictions found while building) overrides from that time on
    if unmeas_from:
        t_u, why = min(unmeas_from)
        for r in recs:
            if r["t"] >= t_u - 1e-9 and r["k"] > 0: r.update(status="unmeasurable", why=why, distance_lots=None)
    # online column: only when every piece of evidence carries an observation time
    all_ev = [(f[2] if len(f) > 2 else None) for r in reqs for f in r["fills"]] + [f[2] for f in un]
    ledger_ev = any(r["source"] == "ledger" or r["source"] == "order_row_derived" for r in reqs)
    if reqs or un:
        if ledger_ev or any(o is None for o in all_ev): online = {"status": "UNAVAILABLE", "why": "order rows store no write time / a fill has no backfilled_utc: the online view cannot be reconstructed for this symbol"}
        else:
            om = SymbolModel(sym, reqs, un, obs, step, evidence_filter=True); orecs = om.run()
            online = {"status": "ok", "distance_lots": [r.get("distance_lots") for r in orecs], "excluded_k": [r["k"] for r in orecs if r.get("excluded")]}
    else:
        online = {"status": "ok", "distance_lots": [r.get("distance_lots") for r in recs], "excluded_k": [r["k"] for r in recs if r.get("excluded")], "note": "no evidence at all: online == offline"}
    orc = model.oracle_check()
    pend = [{"rid": r["rid"], "side": r["side"], "cap": r["cap"], "birth": r["birth"], "floor_at_end": model.floor_at(i, len(obs) - 1),
             "feasible_interval_lots": [model.floor_at(i, len(obs) - 1), (None if r["cap"] is None else r["cap"])]}
            for i, r in enumerate(model.reqs) if r["terminal"] is None]        # §1c.3: an open request is CARRIED, never dropped
    return sym, recs, online, orc, step, getattr(model, "oracle_skipped", None), pend


def main():
    F, T, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
    REPO = os.path.expanduser(os.environ.get("Q6_REPO") or "~/dl_quant_live"); P = f"{REPO}/state/live/pilot_log"
    FILT = os.environ.get("Q6_FILTERS") or f"{REPO}/state/live/exchange_info_cache.json"
    notes = collections.Counter(); t_start = time.time()
    days, rows, files = load_days(P, F, T)
    steps = {}
    if os.path.exists(FILT):
        ei = json.load(open(FILT)); steps = {s: float(v.get("step") or 0.0) for s, v in ei.items() if isinstance(v, dict)}
    step_of = lambda s: steps.get(s) or 1.0
    step_source = f"{FILT} ({len(steps)} symbols)" if steps else "ABSENT ⇒ step 1.0 for every symbol"
    rb = [r for d in days for r in rows(d, "position_readback")]; od = [r for d in days for r in rows(d, "orders")]; an = [r for d in days for r in rows(d, "anchors")]
    # fills: dedupe by (symbol, trade_id); keep the copy that carries backfilled_utc (observation time) when present
    by_tid = {}
    for d in days:
        for r in rows(d, "fills"):
            k = (r["symbol"], str(r.get("trade_id"))); key = (1 if r.get("backfilled_utc") else 0, d)
            if k not in by_tid or key >= by_tid[k][0]: by_tid[k] = (key, r)
    fills_by_symbol = collections.defaultdict(list)
    for (s, tid), (_, r) in by_tid.items():
        px = float(r.get("fill_px") or 0.0)
        if px <= 0: notes["fill_without_price_dropped"] += 1; continue
        side = 1 if str(r.get("side", "")).upper() == "BUY" else (-1 if str(r.get("side", "")).upper() == "SELL" else 0)
        if side == 0: notes["fill_without_side_dropped"] += 1; continue
        q, res = lots(abs(float(r["fill_notional"])) / px, step_of(s))
        if res > 0.01: notes["fill_qty_off_lattice_gt_1pct_lot"] += 1
        fills_by_symbol[s].append({"ts": float(r["fill_ts"]), "lots": q, "side": side, "obs_time": parse_utc(r["backfilled_utc"]) if r.get("backfilled_utc") else None, "trade_id": str(tid), "px": px,
                                   "rebalance_id": r.get("rebalance_id"), "attempt_idx": r.get("attempt_idx")})
    for s in fills_by_symbol: fills_by_symbol[s].sort(key=lambda f: f["ts"])
    notes["fills_deduped_unique"] = sum(len(v) for v in fills_by_symbol.values())
    # observations: post_anchor reads (primary) + flatten reads; marks
    OBS = collections.defaultdict(list); markrows = collections.defaultdict(list)
    for r in rb:
        src = str(r.get("source", "")); q = float(r["venue_position_qty"]); t = float(r["read_ts"]); s = r["symbol"]
        kind = "post_anchor" if src.endswith("@post_anchor") else ("flatten" if "flatten" in src else None)
        if kind is None: notes["readback_other_source_ignored"] += 1; continue
        ql, res = lots(q, step_of(s))
        # ★ R12-Q3 (independent review round 12): rounding an off-lattice reading into the lattice turns a real balance change into an exact fact.
        #   0.49 at step 1 became 0 and read CLEAN while 49 USDT of position went unmodelled. The residual is carried on the observation and any
        #   reading whose rounding residual is worth more than the flag threshold is categorised OFF_LATTICE, never CLEAN.
        if res > LOT_TOL: notes["readback_off_lattice"] += 1
        # ★ R16 (fifth 'unknown-value-as-identity-element' instance): the old `venue_position_notional or 0.0` coerced a MISSING notional to 0.0 ⇒ a zero
        #   price mark ⇒ usd = |distance|*step*0 = 0 ⇒ the `usd > FLAG_USDT` test failed ⇒ a real non-zero distance read CLEAN instead of MISSING_PRICE.
        #   The price basis is the notional's MAGNITUDE — the abs() below. A NEGATIVE notional is a SHORT's NORMAL reading and MUST be used as its |value|:
        #   27,080 of the window's 48,635 non-zero-qty readbacks are shorts, so the abs() is LOAD-BEARING — deleting it would censor every short position.
        #   ONLY an ABSENT notional (None), or one whose MAGNITUDE is zero, is UNKNOWN ⇒ NO mark fabricated ⇒ the observation falls through to MISSING_PRICE.
        _pn = r.get("venue_position_notional"); _pn = abs(float(_pn)) if _pn is not None else None    # MAGNITUDE = price basis; abs() keeps shorts (negative notional) usable — do NOT remove
        OBS[s].append({"t": t, "anchor": B(r["anchor_ts"]) if kind == "post_anchor" else B(t), "kind": kind, "q_lots": ql, "q": q, "lot_residual": res, "notional": _pn})
        if q and _pn is not None and _pn > 0: markrows[s].append((t, _pn / abs(q)))                   # present AND non-zero magnitude ⇒ a usable price mark
        elif q: notes["readback_qty_without_usable_notional"] += 1        # ABSENT or zero-magnitude ⇒ no mark fabricated ⇒ MISSING_PRICE, never a silent CLEAN
    for s, fl in fills_by_symbol.items():
        for f in fl: markrows[s].append((f["ts"], f["px"]))
    for s in markrows: markrows[s].sort()
    for s in OBS:
        OBS[s].sort(key=lambda o: o["t"])
        i0 = next((i for i, o in enumerate(OBS[s]) if o["kind"] == "post_anchor"), None)
        OBS[s] = OBS[s][i0:] if i0 is not None else []
        q0 = OBS[s][0]["q_lots"] if OBS[s] else 0
        for o in OBS[s]: o["rhs"] = o["q_lots"] - q0
    REQ, unmeas = build_requests(od, step_of, notes)
    UN = attribute_fills(fills_by_symbol, REQ, notes)
    # NB: the WHOLE-RECORD contradiction check does NOT run here. It runs once at the model-assembly choke point below (after any resume merge), so a
    #   single site covers the fresh build AND the merged/resumed request set — see the comment there (R15-Q1).
    gaps_rec = {}
    for r in an:
        kg = r.get("known_gaps") or {}; gaps_rec[B(r["anchor_ts"])] = {"n_named": kg.get("n_named"), "gross_usdt": kg.get("gross_usdt"), "names": [x.get("symbol") for x in (kg.get("names") or [])]}
    symbols = sorted(set(OBS) | set(REQ) | set(UN))                                  # extended with the checkpoint's symbols in the resume block below
    # ── §1d.5 resume: merge the checkpoint's carried state with this window's facts BEFORE any model is built ──
    CP_IN = os.environ.get("Q6_CHECKPOINT_IN"); cp_state = {}; late_rebuilds = {}; _late_tau = {}
    if CP_IN:
        cpj = json.load(open(CP_IN))
        assert cpj["schema"] == CHECKPOINT_SCHEMA, f"checkpoint schema {cpj['schema']!r} != {CHECKPOINT_SCHEMA!r}"
        assert cpj["policy"] == POLICY, "checkpoint policy identity differs: a checkpoint may only be replayed under the policy that wrote it"
        # ★ R14-Q3: the checkpoint stores the lot STEP it was written in but never compared it. Restoring a step-1 checkpoint under step 0.1
        #   reinterpreted every carried lot value and reported a 9-lot distance while the position had not moved. Units are part of the state:
        #   a mismatch is refused, never silently mixed. (A deliberate migration must be a separate, recorded conversion.)
        _step_mismatch = {s: (cp.get("step"), step_of(s)) for s, cp in cpj["symbols"].items()
                          if cp.get("step") is not None and abs(float(cp["step"]) - float(step_of(s))) > 1e-12}
        assert not _step_mismatch, ("checkpoint lot-step mismatch — the carried lot values are in different units than this run's filters; "
                                    "refusing rather than mixing them (R14-Q3): " + json.dumps(_step_mismatch))
        # ★ R15-Q3 (independent review round 15): the checkpoint WRITES state_sha256 / identity_sha256 but v6 recomputed neither on load — the hash was a
        #   label, not a guard, so a checkpoint whose per-symbol state was edited resumed silently. Recompute the MATERIAL-STATE sha from the loaded
        #   per-symbol state with the SAME function the writer used and REFUSE on any mismatch: the state sha is the object the §1d.5 restart-parity claim
        #   is about, so it is reproducible on load bit for bit. identity_sha256 pins the PRODUCING run (its ledger-input shas and window) and by
        #   construction cannot be reproduced from a resume that read a different window — so it is checked ONLY for INTERNAL consistency against its own
        #   recorded `identity` block (which catches tampering with the provenance record) and explicitly NOT against this run's provenance.
        _cp_state_sha = cpj.get("state_sha256")
        assert _cp_state_sha is not None, ("checkpoint carries no state_sha256 — a " + CHECKPOINT_SCHEMA + " checkpoint always writes one; refusing to "
                                           "resume state whose integrity cannot be verified (R15-Q3)")
        _recomputed_state_sha = state_sha256_of(cpj["symbols"])
        assert _recomputed_state_sha == _cp_state_sha, ("checkpoint state_sha256 mismatch — the per-symbol material state does not hash to the value stored "
                                                        "with it, so the carried state was altered after it was written; refusing rather than resuming it "
                                                        "(R15-Q3). recomputed " + _recomputed_state_sha + " != stored " + _cp_state_sha)
        if cpj.get("identity") is not None and cpj.get("identity_sha256") is not None:
            _recomputed_identity_sha = hashlib.sha256(canon(cpj["identity"])).hexdigest()
            assert _recomputed_identity_sha == cpj["identity_sha256"], ("checkpoint identity_sha256 does not match its own recorded identity block — the "
                                                                        "provenance record was altered (R15-Q3). NB: this is an internal-consistency check; "
                                                                        "identity pins the producing run's inputs/window and is NOT reproducible from this resume")
        _late_tau = {}; _t_last_by = {}; _fresh_evt = collections.defaultdict(list); _fresh_fill_ts = collections.defaultdict(list); _carried_un_ts = {}; _carried_un_list = {}
        for s, cp in cpj["symbols"].items():
            cp_state[s] = cp
            carried = {r["rid"]: req_from_cp(r) for r in cp["hard"]["requests"]}
            fresh = REQ.get(s, {})
            _t_last = (cp["observations"][-1]["t"] if cp.get("observations") else None); _t_last_by[s] = _t_last
            for rid, r in fresh.items():                                    # a rid in both halves ⇒ ONE request (identity, §1c)
                if rid in carried:
                    # ★ R14-Q1/R15-Q1: the pairwise compatibility test is INSIDE _merge_facts (returns the reason, merges nothing on conflict), so the
                    #   resume merge goes through the SAME guard as the fresh build and cannot skip it.
                    _why = _merge_facts(carried[rid], r, notes)
                    if _why:
                        unmeas.setdefault(s, []) if not isinstance(unmeas.get(s), list) else None
                        unmeas[s] = list(unmeas.get(s) or []) + [(r["birth"], f"{rid}: checkpoint and window carry contradictory facts ({_why})")]
                        notes["resume_identity_contradictory"] += 1
                        continue
                    # ★ R14-Q2 / R15-Q2: a merged fresh fact can be LATE; the comparison against the carried prefix is DEFERRED to one pass after all
                    #   merging and attribution (below) so it equally covers brand-new rids and fills attributed post-merge.
                    _fresh_evt[s] += hard_fact_times(r)
                else:
                    carried[rid] = r; _fresh_evt[s] += hard_fact_times(r)   # ★ R15-Q2 (a): a brand-new rid's facts are fresh too — v6 never checked them
            REQ[s] = carried
            # ★ R16 (resume-path late ATTRIBUTION): a carried UNATTRIBUTED fill is evidence with a PENDING question — a request whose trade_ids now
            #   DEFINITIVELY include it can claim it. v6 dumped the carried unattributed set straight into UN[s] and re-attributed only the FRESH fills, so
            #   such a fill never moved onto its request and never consumed that request's capacity: a full recompute flagged the over-capacity, a resume
            #   read CLEAN. Fix: RE-OFFER carried unattributed fills to attribution over the MERGED request set — but ONLY by the DEFINITIVE trade-id path
            #   (attribute_fills trade_id_only). The checkpoint did not persist a fill's rid/attempt, so the inference paths cannot be reproduced and must
            #   NOT be re-run on the reconstruction (forcing rid/attempt=None over-attributed 87 fills via unique-alive on the real ledger; see the note in
            #   attribute_fills for why neither inference can legitimately re-fire for a carried-un fill). Fresh fills keep the FULL attribution — they carry
            #   their own rid/attempt. Side is recovered from the sign of the carried signed lots for the trade-id side-agreement check.
            _on_req = {str(f[3]) for r in carried.values() for f in r["fills"]}                       # trade ids DEFINITIVELY on a carried request are settled, not re-offered
            _carried_un_list[s] = [{"ts": u[0], "side": (1 if u[1] >= 0 else -1), "lots": abs(u[1]), "obs_time": u[2], "trade_id": str(u[3])}
                                   for u in cp["hard"]["unattributed_fills"] if str(u[3]) not in _on_req]
            _carried_un_ts[s] = {f["trade_id"]: f["ts"] for f in _carried_un_list[s]}                  # event times; feed τ only for those that MOVE (below)
            _fresh = [f for f in fills_by_symbol.get(s, []) if str(f["trade_id"]) not in _on_req and str(f["trade_id"]) not in _carried_un_ts[s]]
            _fresh_fill_ts[s] = [f["ts"] for f in _fresh]                                              # fresh fills feed τ regardless of attribution (new evidence)
            fills_by_symbol[s] = _fresh                                                                # fresh fills attributed with the FULL paths (they carry rid/attempt)
            UN[s] = []                                                                                 # UN[s] is re-derived ONLY by attribute_fills below — no pre-reconciled dump
            if cp["hard"]["unmeasurable_from"]: unmeas[s] = [(t, w) for t, w in cp["hard"]["unmeasurable_from"]] + list(unmeas.get(s) or [])
            if cp.get("marks"): markrows[s] = [tuple(m) for m in cp["marks"]] + markrows.get(s, []); markrows[s].sort()
        UN_new = attribute_fills({s: fills_by_symbol.get(s, []) for s in cp_state}, REQ, notes)                            # FRESH fills: full attribution (they carry rid/attempt)
        UN_carried = attribute_fills({s: _carried_un_list.get(s, []) for s in cp_state}, REQ, notes, trade_id_only=True)   # carried unattributed: DEFINITIVE trade-id path only
        for s in cp_state: UN[s] = list(UN.get(s, [])) + list(UN_new.get(s, [])) + list(UN_carried.get(s, []))
        for s in cp_state:                                                  # ★ R15-Q2 / R16: the late-evidence τ over EVERY fresh hard fact of the symbol,
            # computed AFTER all merging and attribution. Contributors: carried-rid merges + brand-new rids (in _fresh_evt); every FRESH fill by its own
            # event time (new evidence, attributed or not); and — R16 — a carried UNATTRIBUTED fill that MOVED onto a request this resume (its answer
            # arrived late), which changes the balance at its early event time. A carried unattributed fill that STAYED unattributed is unchanged (it was in
            # U_k before and after), so it does NOT feed τ — else every resume with leftover fills would rebuild spuriously and break restart parity.
            _still_un = {str(x[3]) for x in UN.get(s, [])}
            _moved_un_ts = [ts for tid, ts in _carried_un_ts.get(s, {}).items() if tid not in _still_un]
            if _moved_un_ts: notes["resume_unattributed_fill_now_attributed"] += 1                    # R16: a previously-pending fill's answer arrived and it moved onto a request
            _evt = list(_fresh_evt.get(s, [])) + list(_fresh_fill_ts.get(s, [])) + _moved_un_ts
            _tl = _t_last_by.get(s)
            _late = [t for t in _evt if t is not None and _tl is not None and t <= _tl + 1e-9]
            if _late: _late_tau[s] = min(_late); notes["resume_late_hard_fact"] += 1
        for s, cp in cp_state.items():                                      # observations: the carried prefix keeps its q0 (same cross-section, §1d)
            newo = [o for o in OBS.get(s, []) if o["t"] > (cp["observations"][-1]["t"] if cp["observations"] else -1) + 1e-9]
            for o in newo: o["rhs"] = o["q_lots"] - cp["q0_lots"]
            OBS[s] = [dict(o) for o in cp["observations"]] + newo
    if cp_state: symbols = sorted(set(symbols) | set(cp_state))                      # a symbol carried by the checkpoint is replayed even with no new activity
    # ★ R15-Q1 (single verdict surface): the WHOLE-RECORD contradiction check (floor>cap, exact outside [floor,cap], negative capacity) runs HERE, once,
    #   over the FINAL request set of every symbol. Fresh build, duplicate-identity merge and checkpoint resume all assemble their requests before this
    #   point and a model after it, so this one site is the choke point every path passes — a new build path (present or future) cannot finalise
    #   requests that skip it, which a second call bolted next to the first could not guarantee. It is deliberately NOT delegated to the solver: at the
    #   terminal pin, solve() sets lo=hi=exact and DISCARDS the evidence floor, so a floor-vs-exact contradiction never reaches the optimisation — the
    #   solver CANNOT be the detector for this class, by construction, and "the solver would catch an infeasible set" is false here. (The pairwise
    #   identity guard `fact_conflict` is the other predicate; it is enforced inside `_merge_facts`.) Resumed symbols count under a distinct note key so a
    #   contradiction the merge CREATED stays visible; dedupe keeps one already recorded (a carried `unmeasurable_from`) from being counted twice.
    contradiction_check(REQ, unmeas, notes, symbols=set(symbols) - set(cp_state), note_key="request_contradiction", dedupe=True)
    if cp_state:
        contradiction_check(REQ, unmeas, notes, symbols=set(cp_state), note_key="request_contradiction_post_merge", dedupe=True)
    jobs = []
    for s in symbols:
        cp = cp_state.get(s)
        if len(OBS.get(s, [])) < 2 and not cp:
            notes["symbols_without_two_observations"] += 1; continue
        resume = None
        if cp and cp["records"]:
            _recs = cp["records"]
            # ★ R14-Q2 (independent review round 14): a hard fact arriving with NO new readback must still rebuild the carried audit prefix from its
            #   own event time (§1d.3). v5 only rebuilt when a NEW observation turned out infeasible, so a resumed run kept an admitted reading of 80
            #   at distance 0 while its own hard facts already said the total was 50 (one pass gives 30). The prefix that pre-dates the late fact is
            #   replayed verbatim; everything from τ on is re-decided against the facts known now. The carried receipts are preserved below.
            _tau = _late_tau.get(s) if CP_IN else None
            if _tau is not None:
                _recs = [r for r in cp["records"] if r["k"] == 0 or r["t"] < _tau - 1e-9]
                notes["resume_prefix_rebuilt_by_late_evidence"] += 1
                late_rebuilds[s] = {"tau": _tau, "kept_prefix": len(_recs), "records_before": cp["records"],
                                    "admitted_before": [list(a) for a in cp["admitted"]]}
            #   the admitted list stays the CHECKPOINT's own when nothing was rebuilt (it is the carried joint object, not a re-derivation);
            #   only a τ-truncation re-derives it from the surviving prefix.
            _adm = cp["admitted"] if _tau is None else [[r["k"], r["rhs_lots"]] for r in _recs if r.get("admitted") and r["k"] > 0]
            resume = {"records": _recs, "admitted": _adm, "unmeasurable_from_run": cp.get("unmeasurable_from_run")}
        jobs.append((s, list(REQ.get(s, {}).values()), UN.get(s, []), OBS[s], step_of(s), None, unmeas.get(s), resume))
    procs = int(os.environ.get("Q6_PROCS") or max(1, min(10, (os.cpu_count() or 2) - 2)))
    if procs > 1 and len(jobs) > 8:
        import multiprocessing as mp
        with mp.Pool(procs) as pool: results = pool.map(symbol_job, jobs, chunksize=4)
    else:
        results = [symbol_job(j) for j in jobs]
    # ── assemble ──
    rows_out = []; per_anchor = collections.defaultdict(lambda: collections.Counter()); per_anchor_usd = collections.Counter(); exclusions = []; unmeasurable = []
    cat_total = collections.Counter(); persist = collections.Counter(); solver = collections.Counter(); oracle_cmp = {"checked": 0, "agree": 0, "disagree": [], "not_enumerable": 0}
    symbol_summary = {}; online_avail = collections.Counter(); history_unresolved = 0; regime = collections.Counter(); detail = {}
    want_detail = bool(os.environ.get("Q6_DETAIL"))
    for (s, recs, online, orc, step, orc_skip, pend) in results:
        mk = markrows.get(s, []); flagged_here = 0; excluded_here = []; det = []
        online_avail[online["status"]] += 1
        for rec in recs:
            if rec["k"] == 0: continue
            k = rec["k"]; t = rec["t"]; a = rec["anchor"]; kind = rec["kind"]
            mark = None
            for (mt, mv) in mk:
                if mt <= t + 1e-9: mark = mv
                else: break
            if rec["status"] == "unmeasurable":
                cat = "UNMEASURABLE"; usd = None; d = None
                unmeasurable.append({"symbol": s, "anchor": a, "utc": U(a), "kind": kind, "why": rec.get("why")})
            else:
                d = rec["distance_lots"]; usd = (None if mark is None else abs(d) * step * mark)
                _res = float(rec.get("lot_residual") or 0.0) + float(rec.get("lot_residual_base") or 0.0)      # R12-Q3: quantisation error of this reading (and of the baseline it is差分 against)
                _res_usd = (None if mark is None else _res * step * mark)
                if mark is not None and _res_usd is not None and _res_usd > FLAG_USDT and (d == 0 or usd is None or usd <= _res_usd):
                    cat = "OFF_LATTICE"; notes["off_lattice_observation_not_clean"] += 1                        # the reading is not on the lattice the model is exact on
                elif d == 0: cat = "CLEAN"
                elif mark is None: cat = "MISSING_PRICE"
                elif usd > FLAG_USDT: cat = "FLAGGED"
                else: cat = "CLEAN"; notes["distance_nonzero_but_le_1usdt"] += 1
                if rec.get("excluded"):
                    excluded_here.append(k); exclusions.append({"symbol": s, "anchor": a, "utc": U(a), "kind": kind, "rhs_lots": rec["rhs_lots"], "distance_lots": d, "usdt": usd})
            regime["ledger_era" if a >= 1789257600 else "pre_ledger_era"] += 1              # 2026-09-13 00Z: first full day with request_ledger
            cat_total[cat] += 1; per_anchor[a][cat] += 1
            if cat == "FLAGGED": per_anchor_usd[a] += usd; flagged_here += 1 if kind == "post_anchor" else 0
            if want_detail: det.append({"k": k, "anchor": a, "kind": kind, "status": rec["status"], "distance_lots": d, "category": cat, "usdt": usd, "admitted": bool(rec.get("admitted")),
                                        "excluded": bool(rec.get("excluded")), "why": rec.get("why"), "excluded_because": rec.get("excluded_because"),
                                        "distance_lots_after_rebuild": rec.get("distance_lots_after_rebuild"), "prefix_rebuilt": bool(rec.get("prefix_rebuilt")),
                                        "rebuilt_excluded_k": rec.get("rebuilt_excluded_k"), "off_lattice_not_admitted": bool(rec.get("off_lattice_not_admitted"))})
            if cat in ("FLAGGED", "MISSING_PRICE", "UNMEASURABLE", "OFF_LATTICE"):
                rows_out.append({"symbol": s, "anchor": a, "utc": U(a), "kind": kind, "category": cat, "distance_lots": d, "distance_contracts": (None if d is None else d * step), "unexplained_usdt": usd,
                                 "rhs_lots": rec["rhs_lots"], "excluded_observation": bool(rec.get("excluded")), "in_executor_known_gaps": s in (gaps_rec.get(a, {}).get("names") or []), "why": rec.get("why")})
        if flagged_here >= PERSIST_N: persist[s] = flagged_here
        if excluded_here: history_unresolved += 1
        solver["milp_lattice"] += 1
        if orc is None:
            oracle_cmp["not_enumerable"] += 1
            oracle_cmp.setdefault("skipped_why", collections.Counter())[orc_skip or "unknown"] += 1
        elif orc.get("status") in ("ok", "unmeasurable"):
            oracle_cmp["checked"] += 1
            mine_excl = [r["k"] for r in recs if r.get("excluded")]; mine_last = next((r for r in reversed(recs) if r["k"] > 0), None)
            if orc["status"] == "unmeasurable":
                ok = any(r["status"] == "unmeasurable" for r in recs)
            else:
                ok = (sorted(e["index"] for e in orc["excluded"]) == sorted(mine_excl)) and (mine_last is not None and mine_last.get("distance_lots") is not None and abs(float(orc["distance"] or 0) - mine_last["distance_lots"]) < 1e-9)
            if ok: oracle_cmp["agree"] += 1
            else: oracle_cmp["disagree"].append({"symbol": s, "oracle": {"status": orc["status"], "distance": orc.get("distance"), "excluded": [e["index"] for e in orc.get("excluded", [])]}, "device": {"excluded": mine_excl, "last_distance": (mine_last or {}).get("distance_lots")}})
        if want_detail: detail[s] = {"observations": det, "online": online, "oracle": orc}
        symbol_summary[s] = {"n_obs": len(recs) - 1, "n_flagged_post_anchor": flagged_here, "excluded_k": excluded_here, "online": online["status"], "step": step,
                             "n_requests": len(REQ.get(s, {})), "n_unattributed_fills": len(UN.get(s, [])), "oracle": (None if orc is None else orc.get("status")), "oracle_skipped": (orc_skip if orc is None else None)}
    anchors = sorted(per_anchor)
    summary = [{"anchor": a, "utc": U(a), **{c: per_anchor[a].get(c, 0) for c in ("CLEAN", "FLAGGED", "MISSING_PRICE", "UNMEASURABLE", "OFF_LATTICE")}, "flagged_usdt": round(per_anchor_usd.get(a, 0.0), 2),
                "executor_known_gaps_n": gaps_rec.get(a, {}).get("n_named"), "executor_known_gaps_usdt": gaps_rec.get(a, {}).get("gross_usdt")} for a in anchors]
    out = {"device": DEVICE, "version": VERSION, "self_sha256": sha(os.path.abspath(__file__)), "oracle": {"file": "support/reconcile_carry_409ea16.py", "sha256": sha(os.path.join(HERE, "support", "reconcile_carry_409ea16.py")), "origin": "git show 409ea16:live/reconcile_carry.py"},
           "utc": time.strftime("%FT%TZ", time.gmtime()), "runtime_s": round(time.time() - t_start, 1), "interpreter": sys.version.split()[0], "scipy": __import__("scipy").__version__, "procs": procs,
           "window": [days[0], days[-1]] if days else None, "repo": REPO, "ledger_files_sha256": files, "lot_step_source": step_source,
           "epoch": "single epoch per symbol from its first post_anchor readback inside the window (OFFLINE SCAN BASELINE, not a user-signed accounting row); no split at flattens",
           "snapshot_time_source": "weak_bound:max(cancel_ts,last_fill_ts) — NOT the moment confirmed_qty was read (cancel_ts is the local cancel-response time, confirmed_qty can be raised later by the child-fill set, and several requests share one order row's aggregate clock). Cumulative snapshots are a LADDER of (value, event time) steps; a row with neither field is named per request (snapshot_time_source ABSENT) and counted as requests_without_snapshot_time",
           "evidence_regimes": {"ledger_era": "anchors ≥ 2026-09-13 00Z: request_ledger (client_id, confirmed_qty[_final], trade_qty) ⇒ precise requests",
                                "pre_ledger_era": "anchors < 2026-09-13: requests DERIVED from order rows (known side, terminal inside the run, capacity UNKNOWN/unbounded, floor = attributed fills; venue_reject ⇒ exact 0) — weaker evidence, fewer balances can be flagged", "observations_by_regime": dict(regime)},
           "online_clock": {"status_by_symbol": dict(online_avail), "note": "online column computed only when every piece of evidence carries an observation time; on the real ledger order rows store no write time ⇒ UNAVAILABLE"},
           "soundness": "distance is exact on the lot lattice for the recorded facts (MILP, same constraint set as the oracle); a FLAGGED distance means no admissible trajectory of the recorded requests/fills produces the reading; distance 0 proves nothing about the truth",
           "n_anchors": len(anchors), "n_symbols_modelled": len(results), "counts": dict(cat_total), "n_flagged_rows": sum(1 for r in rows_out if r["category"] == "FLAGGED"),
           "symbols_flagged_ge_6_anchors": dict(persist), "n_symbols_history_unresolved": history_unresolved, "n_excluded_observations": len(exclusions),
           "solver": dict(solver), "oracle_crosscheck": oracle_cmp, "notes": dict(notes), "per_anchor": summary, "rows": rows_out, "exclusions": exclusions, "unmeasurable": unmeasurable, "symbols": symbol_summary, **({"detail": detail} if want_detail else {})}
    CP_OUT = os.environ.get("Q6_CHECKPOINT_OUT")
    if CP_OUT:
        cps = {}
        for (s, recs, online, orc, step, orc_skip, pend) in results:
            mk = markrows.get(s, [])
            cps[s] = {"symbol": s, "step": step, "q0_lots": (OBS[s][0]["q_lots"] if OBS.get(s) else 0),
                      "hard": {"requests": [req_to_cp(r) for r in sorted([x for x in REQ.get(s, {}).values() if x["side"] != 0], key=lambda r: (r["birth"], r["rid"]))],
                               "unattributed_fills": [[f[0], f[1], f[2], str(f[3])] for f in UN.get(s, [])],
                               "unmeasurable_from": [[t, w] for (t, w) in (unmeas.get(s) or [])]},
                      "observations": [{k: o.get(k) for k in ("t", "anchor", "kind", "q_lots", "q", "lot_residual", "notional", "rhs")} for o in OBS.get(s, [])],
                      "records": recs, "admitted": [[r["k"], r["rhs_lots"]] for r in recs if r.get("admitted") and r["k"] > 0],
                      "excluded": [{"k": r["k"], "rhs_lots": r["rhs_lots"], "distance_lots": r.get("distance_lots"), "why": r.get("why"),
                                    "because": r.get("excluded_because", "chronological_admission")} for r in recs if r.get("excluded")],
                      "unmeasurable_from_run": next((r.get("why") for r in recs if r.get("status") == "unmeasurable"), None),
                      "pending_requests": pend, "marks": [[t, v] for (t, v) in mk]}
        cpj = {"schema": CHECKPOINT_SCHEMA, "policy": POLICY, "device": DEVICE, "version": VERSION, "self_sha256": sha(os.path.abspath(__file__)),
               "utc": time.strftime("%FT%TZ", time.gmtime()), "window": [days[0], days[-1]] if days else None,
               "resumed_from": os.environ.get("Q6_CHECKPOINT_IN"), "n_symbols": len(cps), "symbols": cps}
        os.makedirs(os.path.dirname(os.path.abspath(CP_OUT)), exist_ok=True)
        json.dump(cpj, open(CP_OUT, "w"), indent=1, default=str)
        # ★ R14-Q5 (independent review round 14): the sha covered only hard/observations/admitted/excluded/q0_lots/step/pending_requests, so
        #   changing `records` (the original receipts) or `marks` (the price evidence the USD verdict rests on) left it unchanged — it proved the
        #   SELECTED object equal, not the state. It now covers every material per-symbol field AND the identity of what produced them: the device
        #   sha, the ledger input shas, the epoch/start declaration and the policy revision. The receipt says exactly which fields are covered.
        #   _SYM_FIELDS and the state sha are the module-level state_sha256_of(), the SAME function the load-time guard reruns to verify (R15-Q3).
        _identity = {"schema": CHECKPOINT_SCHEMA, "policy": POLICY, "device": DEVICE, "version": VERSION,
                     "device_sha256": sha(os.path.abspath(__file__)), "ledger_files_sha256": files, "window": [days[0], days[-1]] if days else None,
                     "epoch": EPOCH_DECLARATION, "lot_step_source": step_source}
        #   TWO shas, because they answer two questions and only one of them can be compared across a split window: `state_sha256` is the
        #   MATERIAL STATE (this is the object the §1d.5 restart-parity claim is about — a resumed run must reproduce it bit for bit), while
        #   `identity_sha256` pins WHAT PRODUCED IT (device, ledger inputs, window, epoch, policy) and by construction differs between a single
        #   pass over D1..D2 and a resume that only read D2. Reporting one number for both would either break parity or hide provenance.
        cpj["state_sha256"] = state_sha256_of(cps)                          # R15-Q3: ONE hashing function, shared with the load-time verification guard
        cpj["identity_sha256"] = hashlib.sha256(canon(_identity)).hexdigest()
        cpj["identity"] = _identity
        cpj["state_sha256_covers"] = {"per_symbol_fields": list(_SYM_FIELDS), "identity_fields": sorted(_identity),
                                      "state_sha256": "the per-symbol material state ONLY — the restart-parity claim is about this number",
                                      "identity_sha256": "device sha, ledger input shas, window, epoch declaration, policy, lot-step source — NOT comparable across a split window",
                                      "note": "a change to ANY per-symbol field changes state_sha256; nothing outside the listed fields is covered by either"}
        json.dump(cpj, open(CP_OUT, "w"), indent=1, default=str)            # rewritten with the identity block and the sha it covers
        out["checkpoint"] = {"path": CP_OUT, "n_symbols": len(cps), "state_sha256": cpj["state_sha256"], "identity_sha256": cpj["identity_sha256"],
                             "state_sha256_covers": cpj["state_sha256_covers"], "identity": _identity,
                             "late_evidence_rebuilds": {k: {kk: vv for kk, vv in v.items() if kk != "records_before"} for k, v in late_rebuilds.items()},
                             "records_before_rebuild": {k: v["records_before"] for k, v in late_rebuilds.items()}}
        print("checkpoint ->", CP_OUT, len(cps), "symbols | state sha", out["checkpoint"]["state_sha256"][:16],
              "| late-evidence rebuilds", len(late_rebuilds))
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("window", out["window"], "anchors", len(anchors), "symbols", len(results), "| counts", dict(cat_total), "| flagged rows", out["n_flagged_rows"], "| persistent ≥6:", dict(persist),
          "| excluded obs", len(exclusions), "history-unresolved symbols", history_unresolved, "| oracle", {k: (v if not isinstance(v, list) else len(v)) for k, v in oracle_cmp.items()}, "| %.0fs" % out["runtime_s"])


if __name__ == "__main__":
    main()
