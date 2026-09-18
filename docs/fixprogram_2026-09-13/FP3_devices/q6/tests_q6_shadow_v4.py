#!/usr/bin/env python3
"""Behavioural tests for q6_shadow.py v4 against the FROZEN Q6 contract (PREREG_reconcile_carry_forward_unexplained_2026-09-10 §1c/§1d).

The fixtures are the independent reviewer's 15 counterexamples of round 11 (codex 5eba83be, agents/q6/audit_q6.py: builders rb / order / fill and
the case list are reproduced here verbatim in shape) plus two green controls. Each case runs the COMPLETE device as a subprocess on a synthetic
pilot_log root (env Q6_REPO; no lot-step file ⇒ step 1) and asserts the CONTRACT outcome per observation (distance in lots, category, admitted /
excluded, unmeasurable), the fill-attribution / identity notes, the online-clock column, and that the production enumeration oracle
(support/reconcile_carry_409ea16.py, sha pinned) reached the same verdict wherever it could enumerate. The green controls are asserted FIRST: a
red case is only meaningful when the baseline is green.
Run: python3 tests_q6_shadow_v4.py   (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS)."""
import hashlib, json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "q6_shadow.py")
ORACLE_SHA = "58e637eadf58bec8797b6fb0138302bf4cb462b89cbd1015695813fdd3377b7f"
BASE = 1786147200                                                           # 2026-08-08 00:00 UTC, four-hour aligned (the reviewer's harness)
DAY = "20260808"
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:220]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q, s="AAA", source="exec@post_anchor", delay=20):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + delay, symbol=s, venue_position_qty=q, venue_position_notional=q * 10, source=source)


def order(k, cap, cq=0, terminal=False, final=False, s="AAA", rid="r1", side="buy"):
    return dict(anchor_ts=BASE + k * 14400, symbol=s, side=side, request_ledger=[dict(client_id=rid, qty=cap, confirmed_qty=cq, terminal=terminal, confirmed_qty_final=final, state="confirmed")])


def fill(k, q, s="AAA", tid=1, side="buy", delay=10):
    return dict(fill_ts=BASE + k * 14400 + delay, symbol=s, side=side, fill_px=10, fill_notional=q * 10, trade_id=tid)


ROOT = tempfile.mkdtemp(prefix="q6v4_tests_", dir=os.environ.get("TMPDIR") or None)


def run(name, reads, orders=(), fills=()):
    root = os.path.join(ROOT, name); log = os.path.join(root, "state", "live", "pilot_log", DAY); os.makedirs(log, exist_ok=True)
    for f, rows in (("position_readback", reads), ("orders", orders), ("fills", fills), ("anchors", [])):
        open(os.path.join(log, f + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    out = os.path.join(root, "receipt.json")
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=os.path.join(root, "no_filters.json"), Q6_PROCS="1", Q6_DETAIL="1")
    r = subprocess.run([sys.executable, DEV, DAY, DAY, out], capture_output=True, text=True, env=env)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit(f"device failed on {name}: rc {r.returncode}\n{r.stdout[-800:]}\n{r.stderr[-1500:]}")
    return json.load(open(out))


def obs(rec, s="AAA"):
    return rec["detail"][s]["observations"]


def dist(rec, s="AAA"):
    return [o["distance_lots"] for o in obs(rec, s)]


def cats(rec, s="AAA"):
    return [o["category"] for o in obs(rec, s)]


def excl(rec, s="AAA"):
    return [o["k"] for o in obs(rec, s) if o["excluded"]]


def oracle_ok(rec, name, skipped=None):
    """the oracle must either agree, or REFUSE with a named reason (R12-Q2: a static Request cannot carry a time-varying floor, so flattening the
    floor to the final fill sum made it disagree with the correct model; refusing is the honest outcome and is asserted by name)."""
    oc = rec["oracle_crosscheck"]
    if skipped:
        check(f"[{name}] oracle REFUSES with the named reason {skipped!r} (not a silent skip, not a false agreement)",
              oc["checked"] == 0 and not oc["disagree"] and (oc.get("skipped_why") or {}).get(skipped) == 1, oc)
    else:
        check(f"[{name}] oracle cross-check: enumerated and agrees", oc["checked"] >= 1 and not oc["disagree"], oc)


print("support oracle sha:", hashlib.sha256(open(os.path.join(HERE, "support", "reconcile_carry_409ea16.py"), "rb").read()).hexdigest()[:16])
check("support oracle == production live/reconcile_carry.py @409ea16 (sha pinned)", hashlib.sha256(open(os.path.join(HERE, "support", "reconcile_carry_409ea16.py"), "rb").read()).hexdigest() == ORACLE_SHA)
try:
    from scipy.optimize import milp  # noqa: F401
    check("interpreter has scipy.optimize.milp (HiGHS)", True)
except Exception as e:   # noqa: BLE001
    check("interpreter has scipy.optimize.milp (HiGHS)", False, repr(e)); print("FAILURES: milp missing"); sys.exit(1)

table = []
print("\n[G] green controls (asserted before any red case)")
r = run("control_open_buy2_grows", [rb(0, 0), rb(1, 1), rb(2, 2)], [order(1, 2)])
check("[G1] open BUY2, reads 0→1→2: every observation admitted, distance 0, CLEAN", dist(r) == [0, 0] and cats(r) == ["CLEAN", "CLEAN"] and excl(r) == [], obs(r)); oracle_ok(r, "G1"); table.append(("G1 control_open_buy2_grows", dist(r), cats(r)))
r = run("control_attributed_fill", [rb(0, 0), rb(1, 1)], [order(1, 1)], [fill(1, 1)])
check("[G2] open BUY1 + one fill attributed to it (unique alive same side), read 1: distance 0, fill NOT double counted", dist(r) == [0] and r["notes"].get("fills_attributed_unique_alive_same_side") == 1 and not r["notes"].get("fills_unattributed"), (dist(r), r["notes"])); oracle_ok(r, "G2", skipped="time_varying_floor"); table.append(("G2 control_attributed_fill", dist(r), cats(r)))
r = run("control_two_open_buy1_reads_1_2", [rb(0, 0), rb(1, 1), rb(2, 2)], [order(1, 1, rid="a"), order(1, 1, rid="b")])
check("[G3] two open BUY1 (joint {(1,0),(0,1)} after read 1), read 2 next: admissible (distance 0)", dist(r) == [0, 0] and excl(r) == [], obs(r)); oracle_ok(r, "G3"); table.append(("G3 two_open_buy1_1_2", dist(r), cats(r)))

print("\n[R] the reviewer's 15 counterexamples — contract outcome")
r = run("exact_evidence_missing_fill", [rb(0, 0), rb(1, 5)], [order(1, 5, 5, True, True)])
check("[R1] terminal BUY5 with credible total 5, read 5, no fills row: distance 0 (v2 gave 5)", dist(r) == [0] and cats(r) == ["CLEAN"], obs(r)); oracle_ok(r, "R1"); table.append(("R1 exact_evidence_missing_fill", dist(r), cats(r)))
r = run("known_fill_and_terminal_lower_doublecount", [rb(0, 0), rb(1, 1)], [order(1, 2, 1, True, False)], [fill(1, 1)])
check("[R2] terminal BUY2 unknown total, floor 1, the same fill 1 in fills.jsonl, read 1: distance 0 (v2 double-counted ⇒ 1)", dist(r) == [0] and r["notes"].get("fills_attributed_unique_alive_same_side") == 1, (dist(r), r["notes"])); oracle_ok(r, "R2"); table.append(("R2 known_fill_and_terminal_lower_doublecount", dist(r), cats(r)))
r = run("terminal_unknown_grows", [rb(0, 0), rb(1, 1), rb(2, 2)], [order(1, 2, 0, True, False)])
check("[R3] terminal BUY2 unknown total, reads 1 then 2: second reading distance 1 and EXCLUDED (post-terminal constant; v2 gave 0)", dist(r) == [0, 1] and excl(r) == [2] and cats(r)[1] == "FLAGGED", obs(r)); oracle_ok(r, "R3"); table.append(("R3 terminal_unknown_grows", dist(r), cats(r)))
r = run("open_lower_ignored", [rb(0, 0), rb(1, 1)], [order(1, 2, 2, False, False)])
check("[R4] open BUY2 with evidence floor 2, read 1: distance 1 (v2 ignored the open request's floor ⇒ 0)", dist(r) == [1] and excl(r) == [1], obs(r)); oracle_ok(r, "R4"); table.append(("R4 open_lower_ignored", dist(r), cats(r)))
r = run("signed_sell_capacity", [rb(0, 0), rb(1, -1)], [order(1, -2, -1, False, False, side="sell")])
check("[R5] SELL2 with signed qty −2 / confirmed −1, read −1: MEASURABLE, distance 0 (v2: negative bounds ⇒ unmeasurable)", dist(r) == [0] and cats(r) == ["CLEAN"] and r["counts"].get("UNMEASURABLE", 0) == 0, obs(r)); oracle_ok(r, "R5"); table.append(("R5 signed_sell_capacity", dist(r), cats(r)))
r = run("trade_id_collision", [rb(0, 0, "AAA"), rb(0, 0, "BBB"), rb(1, 1, "AAA"), rb(1, 1, "BBB")], [], [fill(1, 1, "AAA", 7), fill(1, 1, "BBB", 7)])
check("[R6] two symbols share trade_id 7: de-dup by (symbol, trade_id) keeps both fills ⇒ both distance 0 (v2 dropped AAA's fill ⇒ 1)", dist(r, "AAA") == [0] and dist(r, "BBB") == [0] and r["notes"].get("fills_unattributed") == 2, (dist(r, "AAA"), dist(r, "BBB"), r["notes"])); table.append(("R6 trade_id_collision", dist(r, "AAA") + dist(r, "BBB"), cats(r, "AAA") + cats(r, "BBB")))
r = run("checkpoint_old_open_lost", [rb(0, 0), rb(1, 1)], [order(0, 2)])
check("[R7] open BUY2 born in the baseline bucket (x(t0) a variable, same cross-section), read 1: distance 0 (v2 dropped the request ⇒ 1)", dist(r) == [0], obs(r)); oracle_ok(r, "R7"); table.append(("R7 checkpoint_old_open_lost", dist(r), cats(r)))
r = run("later_read_time_with_earlier_position", [rb(0, 0), rb(1, 1), rb(1, 2, source="late_other_read", delay=40)], [], [fill(1, 1, tid=1, delay=10), fill(1, 1, tid=2, delay=30)])
check("[R8] post read at +20 (q 1) with fills at +10 and +30: only the fill ≤ read_ts enters ⇒ distance 0; the other read source is ignored (v2 mixed clocks ⇒ 1)", dist(r) == [0] and r["notes"].get("readback_other_source_ignored") == 1, (obs(r), r["notes"])); table.append(("R8 later_read_time_with_earlier_position", dist(r), cats(r)))
r = run("flatten_other_symbol_erases_debt", [rb(0, 0), rb(0, 0, "BBB"), rb(1, 1), rb(1, 0, "BBB"), rb(2, 1), rb(2, 0, "BBB"), rb(2, 0, "BBB", "protective_flatten", 40), rb(3, 1), rb(3, 0, "BBB")])
check("[R9] AAA 0→1→1→1 with no request/fill: distance 1 at EVERY anchor (history debt carried; BBB's flatten does not reset AAA)", dist(r, "AAA") == [1, 1, 1] and excl(r, "AAA") == [1, 2, 3] and cats(r, "AAA") == ["FLAGGED"] * 3, obs(r, "AAA"))
check("[R9b] BBB (flat, one protective flatten readback as an observation): all CLEAN, flatten kind present", all(c == "CLEAN" for c in cats(r, "BBB")) and any(o["kind"] == "flatten" for o in obs(r, "BBB")) and not r.get("episodes_split_at_flattens"), obs(r, "BBB")); oracle_ok(r, "R9"); table.append(("R9 flatten_other_symbol_erases_debt", dist(r, "AAA"), cats(r, "AAA")))
r = run("same_rid_doubles_capacity", [rb(0, 0), rb(1, 2)], [order(1, 1), order(1, 1)])
check("[R10] the same client_id twice (BUY1): ONE request ⇒ read 2 has distance 1 (v2 doubled capacity ⇒ 0)", dist(r) == [1] and r["notes"].get("duplicate_identity_merged") == 1, (obs(r), r["notes"])); oracle_ok(r, "R10"); table.append(("R10 same_rid_doubles_capacity", dist(r), cats(r)))
r = run("joint_2buy1_1_0_0", [rb(0, 0), rb(1, 1), rb(2, 0), rb(3, 0)], [order(1, 1, rid="a"), order(1, 1, rid="b")])
check("[R11] two open BUY1, reads 1→0→0: anchors 2 and 3 excluded with distance 1, and REPORTED with the carried mark (v2 dropped them: mark 0 at zero position)", dist(r) == [0, 1, 1] and excl(r) == [2, 3] and cats(r)[1:] == ["FLAGGED", "FLAGGED"] and all(abs(o["usdt"] - 10.0) < 1e-9 for o in obs(r)[1:]), obs(r)); oracle_ok(r, "R11"); table.append(("R11 joint_2buy1_1_0_0", dist(r), cats(r)))
r = run("chronological_buy2_2_0_1", [rb(0, 0), rb(1, 2), rb(2, 0), rb(3, 1)], [order(1, 2)])
check("[R12] open BUY2, reads 2→0→1: chronological admission keeps anchor 1, excludes 2 (distance 2) and 3 (distance 1)", dist(r) == [0, 2, 1] and excl(r) == [2, 3], obs(r)); oracle_ok(r, "R12"); table.append(("R12 chronological_buy2_2_0_1", dist(r), cats(r)))
r = run("late_evidence_all_visible_online", [rb(0, 0), rb(1, 1), rb(2, 1)], [], [dict(fill(1, 1), backfilled_utc="2026-08-08T09:00:00Z")])
on = r["detail"]["AAA"]["online"]
check("[R13] fill observed at 09:00Z (event 04:00Z): OFFLINE column 0/0; ONLINE column (evidence by observation time) 1 at both anchors, reported separately", dist(r) == [0, 0] and on["status"] == "ok" and on["distance_lots"] == [0, 1, 1], (dist(r), on)); table.append(("R13 late_evidence_all_visible_online", dist(r), cats(r)))
r = run("missing_side_assumed_sell", [rb(0, 0), rb(1, -1)], [order(1, 1, side=None)])
check("[R14] request without side: UNMEASURABLE from its birth (v2 assumed SELL ⇒ 0)", cats(r) == ["UNMEASURABLE"] and r["counts"].get("UNMEASURABLE") == 1 and "side missing" in str(obs(r)[0]["why"]), obs(r)); oracle_ok(r, "R14"); table.append(("R14 missing_side_assumed_sell", dist(r), cats(r)))
r = run("contradictory_exact_capacity_dropped", [rb(0, 0), rb(1, 2)], [order(1, 1, 2, True, True)], [fill(1, 2)])
check("[R15] capacity 1 with credible total 2 (and fill 2): hard contradiction ⇒ UNMEASURABLE, no fact dropped (v2 gave 0)", cats(r) == ["UNMEASURABLE"] and r["notes"].get("request_contradiction", 0) >= 1, (obs(r), r["notes"])); oracle_ok(r, "R15"); table.append(("R15 contradictory_exact_capacity_dropped", dist(r), cats(r)))

print("\n[O] the online clock is never pretended on the real ledger shape")
r = run("online_unavailable_with_ledger", [rb(0, 0), rb(1, 1)], [order(1, 1)], [fill(1, 1)])
check("[O1] a symbol with an order-row request (no write time stored) ⇒ online column UNAVAILABLE with the reason, offline column still computed", r["detail"]["AAA"]["online"]["status"] == "UNAVAILABLE" and dist(r) == [0], r["detail"]["AAA"]["online"])

print("\nper-case table (distance in lots per observation after the baseline; category)")
for name, d, c in table: print(f"  {name:48s} {str(d):16s} {c}")

# ───────────────────── round 12 (independent review 625e7f2d): the fact-TIME layer ─────────────────────
print("\n[R12] the reviewer's four new counterexamples — each was CLEAN/agreeing on v3")

# R12-Q1a: a cumulative snapshot (confirmed_qty) must bind from the moment it was TAKEN, not from the request's birth.
r = run("r12_later_snapshot_backdated_to_birth",
        [rb(0, 10), rb(1, 10), rb(2, 11)],
        [dict(anchor_ts=BASE + 0 * 14400, symbol="AAA", side="buy", submit_ts=BASE + 0 * 14400 + 5, last_fill_ts=BASE + 2 * 14400 + 10,
              request_ledger=[dict(client_id="r1", qty=1, confirmed_qty=1, terminal=True, confirmed_qty_final=True, state="confirmed")])],
        [fill(2, 1)])
check("[R12-1] snapshot taken at the settlement time does NOT bind at birth: reads 10→10→11 are all CLEAN (v3: first window distance 1, FLAGGED 100 USDT)",
      dist(r) == [0, 0] and cats(r) == ["CLEAN", "CLEAN"], obs(r))
table.append(("R12-1 later_snapshot_backdated_to_birth", dist(r), cats(r)))

# R12-Q1b: a duplicate row that changes ONLY `terminal` was merged as trade ids and the terminal constraint was lost.
_o1 = dict(anchor_ts=BASE + 0 * 14400, symbol="AAA", side="buy", submit_ts=BASE + 5,
           request_ledger=[dict(client_id="r1", qty=2, confirmed_qty=1, terminal=False, confirmed_qty_final=False, state="confirmed")])
_o2 = dict(anchor_ts=BASE + 0 * 14400, symbol="AAA", side="buy", submit_ts=BASE + 5, last_fill_ts=BASE + 6,
           request_ledger=[dict(client_id="r1", qty=2, confirmed_qty=1, terminal=True, confirmed_qty_final=False, state="confirmed")])
r = run("r12_duplicate_terminal_only_update_lost", [rb(0, 0), rb(1, 1), rb(2, 2)], [_o1, _o2], [fill(1, 1)])
check("[R12-2] a duplicate that only flips `terminal` is adopted: after the terminal the position cannot grow ⇒ the last read is distance 1 (v3: 0, 0)",
      dist(r)[-1] == 1 and r["notes"].get("duplicate_terminal_adopted", 0) >= 1, (dist(r), r["notes"].get("duplicate_terminal_adopted")))
table.append(("R12-2 duplicate_terminal_only_update_lost", dist(r), cats(r)))

# R12-Q2: the oracle cannot represent a time-varying floor ⇒ it must refuse, not flatten the floor onto every time.
r = run("r12_oracle_time_varying_floor", [rb(0, 0), rb(1, 0), rb(2, 1)],
        [dict(anchor_ts=BASE + 0 * 14400, symbol="AAA", side="buy", submit_ts=BASE + 5,
              request_ledger=[dict(client_id="r1", qty=1, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed")])],
        [fill(2, 1)])
check("[R12-3] MILP is right (0, 0) on a floor that only exists from the fill onward", dist(r) == [0, 0], obs(r))
oracle_ok(r, "R12-3", skipped="time_varying_floor")
table.append(("R12-3 oracle_time_varying_floor", dist(r), cats(r)))

# R12-Q3 (P2): an off-lattice readback must not be rounded into an exact lattice fact.
r = run("r12_off_lattice_readback", [rb(0, 0), dict(anchor_ts=BASE + 14400, read_ts=BASE + 14400 + 20, symbol="AAA",
                                                    venue_position_qty=0.49, venue_position_notional=49.0, source="exec@post_anchor")])
check("[R12-4] a 0.49 reading at step 1 is OFF_LATTICE, not CLEAN (v3 rounded it to 0 and hid a 49 USDT change)",
      cats(r) == ["OFF_LATTICE"] and r["notes"].get("off_lattice_observation_not_clean", 0) == 1, (cats(r), r["notes"].get("off_lattice_observation_not_clean")))
table.append(("R12-4 off_lattice_readback", dist(r), cats(r)))

# R12-Q3 (accepted semantics, pinned as a control): an unbounded derived request absorbs anything — CLEAN here means "compatible with an
# UNKNOWN capacity", and the receipt must say so by counting the regime. This is the reviewer's `unbounded_derived_absorbs_million`.
r = run("r12_unbounded_derived_absorbs_million", [rb(0, 0), rb(1, 1000000)],
        [dict(anchor_ts=BASE + 1 * 14400, symbol="AAA", side="buy", submit_ts=BASE + 14400 + 5, last_fill_ts=BASE + 14400 + 10, terminal_reason="filled")],
        [fill(1, 1)])
check("[R12-5] CONTROL (accepted semantics): a pre-ledger derived request has UNKNOWN capacity, so even +1,000,000 stays CLEAN — and the receipt counts it as weak evidence",
      cats(r) == ["CLEAN"] and r["notes"].get("derived_requests_unbounded_capacity", 0) >= 1, (cats(r), r["notes"].get("derived_requests_unbounded_capacity")))
table.append(("R12-5 unbounded_derived_absorbs_million (control)", dist(r), cats(r)))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)