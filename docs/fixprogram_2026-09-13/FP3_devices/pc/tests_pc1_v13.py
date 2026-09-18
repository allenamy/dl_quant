#!/usr/bin/env python3
"""Behavioural tests for pc1_intent_replay.py v14 (independent review rounds 11 R11-PC1, 12 R12-P1, 13 R13-P1, 14 R14-P1/P2, 15 R15-P1/P2). [file kept as tests_pc1_v13.py]
Section [10] is the round-14 block: every case there was a full false pass or a population defect on v12 and must be red on v13.
Section [11] is the round-15 block: every RED case there was a false complete_parity / all_measurable_exact on v13 — an UNREADABLE maker fill read as delta−0, and an
unsent sibling chunk masking an already-known over-fill — and must go green on v14. Run PC1_DEV=<pre-fix device> to see [11.1]-[11.4],[11.6] go red on the predecessor.
Section [8] is the round-12 block: every case there PASSED on v10 with complete_parity=True and must be red on v11. Each red case is one of the reviewer's counterexamples that
v9 passed; the green baseline is asserted FIRST so that a red verdict is a discriminating verdict and not a broken fixture.
Fixtures are a synthetic executor state tree (anchor_runs.log, pilot_log day files, exchange_info_cache.json) and a synthetic producer target;
the executor code is the real 409ea16 tree exported by `git archive` into the scratchpad (PC1_TREE_DIR), so the book layer and planner are the
same code the device uses on real anchors. Nothing here touches ~/dl_quant_live or ~/wide_shadow.
Run: python3 tests_pc1_v13.py   (exit 0 iff ALL PASS)"""
import copy, json, math, os, subprocess, sys, time, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("PC1_DEV") or os.path.join(HERE, "pc1_intent_replay.py")   # PC1_DEV=archive/pc1_intent_replay_v11.py re-runs the suite against the PREDECESSOR: section [9] must go red there (v10 for section [8])
SCRATCH = os.environ.get("PC1_TEST_SCRATCH") or "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/pc1_tests"
TREE = os.environ.get("PC1_TREE_DIR") or "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/exec_trees/409ea16"
A = 1789704000; DAY = time.strftime("%Y%m%d", time.gmtime(A)); PREV = time.strftime("%Y%m%d", time.gmtime(A - 14400)); RID = "A1789705440"
SYMS = ["AUSDT", "BUSDT", "CUSDT", "DUSDT"]; W = dict(zip(SYMS, [.25, .25, -.25, -.25])); GROSS = 100.0
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1; print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:200]) if detail and not cond else ""))
    if not cond: FAILS.append(name)


def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def base_data():
    targ = {s: w * GROSS for s, w in W.items()}
    pa = {"anchor_ts": A, "external_wait": {"nominal_anchor_ts": A}, "rebalance_id": RID, "sizing": {"gross": GROSS, "nav": 50.0}, "untradable_names": {},
          "untradable_reason": {}, "universe": {"tradable": SYMS}, "venue_cap_clamp": {}}
    an = {"rebalance_id": RID, "target_gross": GROSS, "external_book": {"gross_norm": 1.0, "held_exit": [], "meta_excluded": {}, "min_notional_mult": 2.0}, "reshape": {},
          "chase_experiment": {"arm_assigned": {s: "chase" for s in SYMS}}}
    orders = []
    for s, t in targ.items():
        side = "buy" if t > 0 else "sell"; q = math.copysign(25.0, t)
        orders.append({"symbol": s, "rebalance_id": RID, "attempt_idx": 1, "side": side, "order_type": "maker", "terminal_reason": "filled", "target_w": t / GROSS, "prev_w": 0.0,
                       "intended_notional": t, "intended_full": t, "filled_known_notional": t, "filled_notional": t, "mid_at_anchor": 1.0, "reduce_only": False,
                       "request_ledger": [{"client_id": f"{RID}-{s}-1", "qty": q, "confirmed_qty": q, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]})
        orders.append({"symbol": s, "rebalance_id": RID, "attempt_idx": 2, "side": side, "order_type": "topup_taker", "terminal_reason": "skipped_min_notional", "target_w": t / GROSS,
                       "prev_w": 0.0, "intended_notional": 0.0, "mid_at_anchor": 1.0, "reduce_only": False, "request_ledger": None})
    pns_prev = {"stopped": [], "cooldown_n": 0}
    return {"pa": pa, "an": an, "orders": orders, "weights": dict(W), "pns_prev": pns_prev, "readback_prev": [], "filters": {s: {"step": 1.0, "min_notional": 0.1, "tick": 0.0001} for s in SYMS}}


def run(name, data):
    home = os.path.join(SCRATCH, name); repo = os.path.join(home, "dl_quant_live"); ws = os.path.join(home, "wide_shadow")
    for d in (f"{repo}/state/live/pilot_log/{DAY}", f"{repo}/state/live/pilot_log/{PREV}", f"{ws}/state/target_live"): os.makedirs(d, exist_ok=True)
    lines = []
    if data.get("pns_prev") is not None: lines.append(utc(A - 14400 + 2700) + " phase_C: " + json.dumps({"per_name_stop": data["pns_prev"]}))
    lines.append(utc(A + 1500) + " phase_A: " + json.dumps(data["pa"]))
    open(f"{repo}/state/anchor_runs.log", "w").write("\n".join(lines) + "\n")
    wl = lambda p, rows: open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))
    wl(f"{repo}/state/live/pilot_log/{DAY}/orders.jsonl", data["orders"]); wl(f"{repo}/state/live/pilot_log/{DAY}/anchors.jsonl", [data["an"]])
    wl(f"{repo}/state/live/pilot_log/{PREV}/position_readback.jsonl", data["readback_prev"])
    json.dump({"__venue__": "test", "__mode__": "test", **data["filters"]}, open(f"{repo}/state/live/exchange_info_cache.json", "w"))
    json.dump({"anchor_ts": A, "weights": data["weights"]}, open(f"{ws}/state/target_live/{A}.json", "w"))
    out = f"{home}/out.json"; env = dict(os.environ, PC1_REPO=repo, PC1_WS=ws, PC1_TREE_DIR=TREE, PC1_TREE_LABEL="409ea16_export_test")
    r = subprocess.run([sys.executable, DEV, str(A), out], capture_output=True, text=True, env=env)
    open(f"{home}/run.log", "w").write(r.stdout + r.stderr)
    if not os.path.exists(out): return {"status": "CRASH", "stderr": r.stderr[-400:]}
    return json.load(open(out))


assert os.path.isdir(os.path.join(TREE, "scheduler")), f"exported executor tree missing: {TREE}"
print("[0] green baseline: four names, plan 25 each, ledger identities <rid>-<SYM>-1, filled makers, top-ups skipped at residual 0")
g = run("control", base_data()); s = g.get("summary", {})
check("baseline runs (status OK)", g.get("status") == "OK", g.get("refusals") or g.get("stderr"))
check("baseline: R1_exact == 4, unexplained == 0, all_measurable_exact", s.get("R1_exact") == 4 and s.get("n_unexplained_or_mismatch") == 0 and s.get("all_measurable_exact") is True, s)
check("baseline: book layer exact 4/4 at 1e-6 USDT", g["stage_A_book_layer"]["exact"] == 4 and g["stage_A_book_layer"]["n"] == 4 and g["stage_A_book_layer"]["max_abs_diff_usdt"] <= 1e-6, g["stage_A_book_layer"])
check("baseline: R3 (top-up) skips consistent 4/4 under the residual rule", g["summary"]["categories"].get("R3_skip_consistent") == 4, g["summary"]["categories"])
check("baseline: complete_parity True (no rejects, book exact) only if the reshape record is non-empty — here the record is empty ⇒ False", s.get("complete_parity") is False, s)

print("\n[1] reviewer probe: every client_id FOREIGN and order types wrong ⇒ v9 said 4/4 exact")
d = base_data()
for r in d["orders"]:
    if r["request_ledger"]: r["request_ledger"][0]["client_id"] = "FOREIGN"; r["order_type"] = "wrong_wire_type"
x = run("foreign_ids", d); cat = x["summary"]["categories"]
check("foreign identities are unexplained requests, R1_exact == 0, all_measurable_exact False", x["summary"]["R1_exact"] == 0 and (x["summary"].get("request_population") or {}).get("UNEXPLAINED:malformed_client_id", 0) >= 4 and x["summary"]["all_measurable_exact"] is False, (cat, x["summary"].get("request_population")))

print("\n[2] reviewer probe: an extra top-up chunk qty=999999 appended ⇒ v9 still 4/4")
d = base_data(); r = copy.deepcopy(d["orders"][0]); r["attempt_idx"] = 2; r["order_type"] = "topup_taker"; r["terminal_reason"] = "filled"
r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 999999.0, "confirmed_qty": 999999.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]; d["orders"].append(r)
x = run("extra_topup", d); cat = x["summary"]["categories"]
check("the extra chunk is R3_lifecycle_unexplained (residual 0 ⇒ the rule says skip, yet 999999 was sent); all_measurable_exact False", cat.get("R3_lifecycle_unexplained", 0) == 1 and x["summary"]["all_measurable_exact"] is False, cat)

print("\n[3] reviewer probe: recorded target/qty shifted A 25→26, B 25→24 (same gross/net) ⇒ v9 within one step 4/4 and requests 4/4")
d = base_data()
for r in d["orders"]:
    if r["symbol"] == "AUSDT": r["target_w"] = .26; r["intended_notional"] = 26.0; r["filled_known_notional"] = 26.0; r["request_ledger"] and r["request_ledger"][0].update(qty=26.0, confirmed_qty=26.0)
    if r["symbol"] == "BUSDT": r["target_w"] = .24; r["intended_notional"] = 24.0; r["filled_known_notional"] = 24.0; r["request_ledger"] and r["request_ledger"][0].update(qty=24.0, confirmed_qty=24.0)
x = run("step_shift", d); cat = x["summary"]["categories"]
check("book layer: only 2/4 exact (A and B off by 1 USDT, no one-step tolerance)", x["stage_A_book_layer"]["exact"] == 2 and x["stage_A_book_layer"]["max_abs_diff_usdt"] >= 0.99, x["stage_A_book_layer"])
check("requests: plans_A is the upstream ⇒ A and B are R1_MISMATCH (plan 25 vs ledger 26/24)", cat.get("R1_MISMATCH", 0) == 2 and x["summary"]["R1_exact"] == 2 and x["summary"]["all_measurable_exact"] is False, cat)

print("\n[4] reviewer probe: all four rejected (venue_reject, no ledger, only intended_notional) ⇒ v9 called 4/4 exact")
d = base_data(); extra = []
for r in d["orders"]:
    if r["order_type"] == "maker":
        r["request_ledger"] = None; r["terminal_reason"] = "venue_reject"; r["filled_known_notional"] = None; r["filled_notional"] = 0.0
        rq = copy.deepcopy(r); rq["requote_arm"] = "requote"; rq["terminal_reason"] = "filled"; rq["filled_known_notional"] = r["intended_notional"]; rq["filled_notional"] = r["intended_notional"]
        q = math.copysign(25.0, r["intended_notional"]); rq["request_ledger"] = [{"client_id": f"{RID}-{r['symbol']}-2", "qty": q, "confirmed_qty": q, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]; extra.append(rq)
d["orders"] += extra                      # production: a benign −5022 reject is requoted once as <rid>-<SYM>-2 (requote arm); the maker leg itself has no ledger
x = run("rejects", d); s = x["summary"]
check("rejects: R1_exact == 0, R1_reject_no_qty_evidence == 4, intent_consistent 4 (reported beside, never as exact), complete_parity False", s["R1_exact"] == 0 and s["R1_reject_no_qty_evidence"] == 4 and s["R1_intent_consistent_among_rejects"] == 4 and s["complete_parity"] is False, s)
check("rejects: requotes are R2_exact 4 and all_measurable_exact stays True — the two flags are distinct", s["R2_exact"] == 4 and s["all_measurable_exact"] is True, s)

print("\n[5] reshape report: the whole record is compared (v9 compared net_before/gross_before only)")
d = base_data(); rr = g["reshape_replayed"]; d["an"]["reshape"] = dict(rr)
x = run("reshape_equal", d)
check("recorded reshape == replayed on every key ⇒ all_recorded_keys_equal True and complete_parity True", x["reshape_compare"]["all_recorded_keys_equal"] is True and x["summary"]["complete_parity"] is True, x["reshape_compare"])
d["an"]["reshape"] = dict(rr, net_after=50.0, gross_after=999.0)
x = run("reshape_mutated", d)
check("net_after=50 / gross_after=999 mutation ⇒ two mismatched keys, not within 1e-9, complete_parity False", set(x["reshape_compare"]["mismatch"]) == {"net_after", "gross_after"} and all(not v["within_1e-9"] for v in x["reshape_compare"]["mismatch"].values()) and x["summary"]["complete_parity"] is False, x["reshape_compare"])

print("\n[6] missing evidence is a refusal, not a default")
d = base_data(); d["pns_prev"] = None
x = run("no_stopset", d)
check("no previous phase_C stop state ⇒ REFUSED UNAVAILABLE_STOPSET (v9 defaulted to an empty stop set)", x.get("status") == "REFUSED" and "UNAVAILABLE_STOPSET" in x.get("refusals", []), x)
d = base_data()
for r in d["orders"]: r.pop("request_ledger", None)
x = run("old_schema", d)
check("orders rows without any request_ledger key (pre-09-12 executor) ⇒ REFUSED UNAVAILABLE_REQUEST_LEDGER_SCHEMA", x.get("status") == "REFUSED" and "UNAVAILABLE_REQUEST_LEDGER_SCHEMA" in x.get("refusals", []), x)

print("\n[7] top-up rule is evaluated, not vacuous: a no_chase draw with a sent chunk is unexplained; a chase draw with skipped_no_chase_arm is unexplained")
# ★ R15-P1 fixture correction: a maker that filled 10 sets BOTH filled_known_notional AND filled_notional to 10 (for a CLOSED ledger
#   filled_notional == filled_known_notional; ledger_row_columns L266). v13 set only filled_known_notional and left filled_notional at the
#   base 25 — a physically impossible row that never occurs in real data (verified: 0/46,363 rows diverge). It passed only because v13's
#   `_fn_of` read the known part; under `_fn_total` (which reads the authoritative total) the intended residual 15 is now realised correctly.
d = base_data(); d["an"]["chase_experiment"]["arm_assigned"]["AUSDT"] = "no_chase"
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0, terminal=True)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0; r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "confirmed_qty": 15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("nochase_sent", d); cat = x["summary"]["categories"]
check("no_chase draw yet a chunk was sent ⇒ R3_lifecycle_unexplained", cat.get("R3_lifecycle_unexplained", 0) == 1, cat)
d = base_data()
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "skipped_no_chase_arm"; r["intended_notional"] = 15.0
x = run("chase_skipped", d); cat = x["summary"]["categories"]
check("chase draw yet skipped_no_chase_arm ⇒ R3_skip_unexplained:skipped_no_chase_arm", cat.get("R3_skip_unexplained:skipped_no_chase_arm", 0) == 1, cat)
d = base_data()
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0; r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "confirmed_qty": 15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("chase_consistent", d); cat = x["summary"]["categories"]
check("chase draw, residual 15 at mid 1 ⇒ chunk 15 is R3_consistent (positive control of the rule)", cat.get("R3_consistent", 0) == 1 and x["summary"]["all_measurable_exact"] is True, cat)

print("\n[8] round 12 (R12-P1): seven counterexamples the v10 device reported as complete_parity=True / all_measurable_exact=True.")
print("    Re-run this file with PC1_DEV=archive/pc1_intent_replay_v10.py and every check below must go red.")
G = lambda s, k, d=None: (s.get(k) if isinstance(s, dict) else None) if (s.get(k) is not None if isinstance(s, dict) else False) else d
g2 = run("r12_green", base_data()); s2 = g2["summary"]
check("[8.0] green baseline again: population identity balanced, 4 quantity comparisons, 4 plans MEASURED_EQUAL",
      s2.get("n_quantity_comparisons") == 4 and G(s2, "population_identity", {}).get("plans_balance") is True
      and G(s2, "population_identity", {}).get("requests_balance") is True and G(s2, "plan_population", {}).get("MEASURED_EQUAL") == 4
      and s2["all_measurable_exact"] is True, (G(s2, "plan_population", {}), G(s2, "population_identity", {})))

d = base_data()                                                            # ① a SECOND ledger entry on the same maker row: legal prefix, attempt 99, qty 999999
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker":
        r["request_ledger"].append({"client_id": f"{RID}-AUSDT-99", "qty": 999999.0, "confirmed_qty": 999999.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True})
x = run("r12_second_identity", d); s3 = x["summary"]
check("[8.1] second entry attempt 99 qty 999999 ⇒ UNEXPLAINED:attempt_index_not_mintable and all_measurable_exact False (v10 read only request_ledger[0])",
      G(s3, "request_population", {}).get("UNEXPLAINED:attempt_index_not_mintable") == 1 and s3["all_measurable_exact"] is False, G(s3, "request_population", {}))

d = base_data()                                                            # ② maker ledger quantity sign opposes the plan side
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["request_ledger"][0]["qty"] = -25.0; r["request_ledger"][0]["confirmed_qty"] = -25.0
x = run("r12_sign_flip", d); s4 = x["summary"]
check("[8.2] maker ledger qty −25 where the plan says buy +25 ⇒ R1_MISMATCH, plan MEASURED_DIFFERENT (v10 compared abs())",
      s4["categories"].get("R1_MISMATCH") == 1 and G(s4, "plan_population", {}).get("MEASURED_DIFFERENT") == 1 and s4["all_measurable_exact"] is False, s4["categories"])

d = base_data()                                                            # ③ one maker ledger cleared, terminal set to something unknown, its top-up row removed to isolate the signal
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["request_ledger"] = []; r["terminal_reason"] = "UNKNOWN_NO_REQUEST"; r["filled_known_notional"] = None; r["filled_notional"] = None
d["orders"] = [r for r in d["orders"] if not (r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker")]
x = run("r12_unproved_maker", d); s5 = x["summary"]
check("[8.3] a maker row with no ledger and an unknown terminal ⇒ UNMEASURABLE:not_sent, n_unmeasurable 1, complete_parity False (v10: silently True)",
      s5.get("n_unmeasurable") == 1 and any(str(k).startswith("UNMEASURABLE:not_sent") for k in G(s5, "plan_population", {})) and s5["complete_parity"] is False, G(s5, "plan_population", {}))

d = base_data()                                                            # ④ every top-up row deleted while the residual is non-zero
for r in d["orders"]:
    if r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0
d["orders"] = [r for r in d["orders"] if r["order_type"] != "topup_taker"]
x = run("r12_no_topup_rows", d); s6 = x["summary"]
check("[8.4] all top-up rows deleted with residual ≠ 0 ⇒ MISSING_REQUEST and R3_MISSING_ROW (v10 emitted no verdict at all)",
      G(s6, "plan_population", {}).get("MISSING_REQUEST", 0) >= 1 and s6["categories"].get("R3_MISSING_ROW", 0) >= 1 and s6["all_measurable_exact"] is False, G(s6, "plan_population", {}))

d = base_data()                                                            # ⑤ top-up chunk sent on the wrong side and flagged reduce_only
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker":
        r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0; r["side"] = "sell"; r["reduce_only"] = True
        r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": -15.0, "confirmed_qty": -15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("r12_topup_side", d); s7 = x["summary"]
check("[8.5] top-up sell −15 + reduce_only where the rule says buy +15 ⇒ R3_lifecycle_unexplained naming side (v10 summed abs() and never read side)",
      s7["categories"].get("R3_lifecycle_unexplained") == 1 and s7["all_measurable_exact"] is False
      and any("side" in t for e in x["rows"] for t in (e.get("diffs") or [])), [e.get("diffs") for e in x["rows"] if e.get("diffs")])

d = base_data()                                                            # ⑥ top-up chunk one whole lot too large (step 1)
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker":
        r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0
        r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 16.0, "confirmed_qty": 16.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("r12_one_lot", d); s8 = x["summary"]
check("[8.6] top-up 16 where the rule says 15 at step 1 ⇒ R3_lifecycle_unexplained (v10 allowed a full lot of tolerance)",
      s8["categories"].get("R3_lifecycle_unexplained") == 1 and s8["all_measurable_exact"] is False, s8["categories"])

d = base_data()                                                            # ⑦ the real halted-anchor shape: every row blocked_by_halt, no ledger anywhere
d["orders"] = [r for r in d["orders"] if r["order_type"] == "maker"]
for r in d["orders"]: r["request_ledger"] = []; r["terminal_reason"] = "blocked_by_halt"; r["filled_known_notional"] = None; r["filled_notional"] = None
x = run("r12_halted", d); s9 = x["summary"]
check("[8.7] the 09-12 20Z / 09-13 00-08Z shape (every plan blocked_by_halt, zero ledger entries) ⇒ 0 quantity comparisons, all_measurable_exact FALSE (v10 reported True over 966 plans)",
      s9.get("n_quantity_comparisons") == 0 and s9["all_measurable_exact"] is False and s9.get("n_unmeasurable") == 4
      and G(s9, "population_identity", {}).get("plans_balance") is True, (s9.get("n_quantity_comparisons"), G(s9, "plan_population", {})))


# ───────────────── [9] independent review round 13 (7ba79b75) — six counterexamples v11 still passed ─────────────────
# Each fixture reproduces the reviewer's `audit_pc1_v11.py` case by name. Run this file with
#   PC1_DEV=archive/pc1_intent_replay_v12.py python3 tests_pc1_v13.py
# to see every [9] check go red on the predecessor.
print("\n[9] round 13: identity, owner-row binding, field evidence and worst-state aggregation")


def partial_data():
    """the reviewer's `partial()`: the maker leg fills 10 of 25, so a top-up of 15 is expected and recorded.
    The reshape record is filled in (as the reviewer's `data()` does), so `complete_parity` is reachable at all."""
    d = base_data(); d["an"]["reshape"] = dict(g["reshape_replayed"])
    for r in d["orders"]:
        if r["symbol"] == "AUSDT" and r["order_type"] == "maker":
            r["filled_known_notional"] = 10.0; r["filled_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
        if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker":
            r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0
            r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "confirmed_qty": 15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
    return d


def topup_row(d):
    return next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker")


x = run("r13_green_partial", partial_data()); s90 = x["summary"]
check("[9.0] GREEN BASELINE: maker 25 partially filled 10 + a legal 15 top-up ⇒ complete_parity True, both identities balanced, no field gaps",
      G(s90, "complete_parity") is True and G(s90, "n_plans_with_field_evidence_gaps", -1) == 0
      and G(s90, "population_identity", {}).get("plans_balance") is True and G(s90, "population_identity", {}).get("requests_balance") is True, s90)

d = partial_data()                                                          # ① the same top-up client_id twice, 7 + 8 = the expected 15
r = topup_row(d); a = dict(r["request_ledger"][0]); b = dict(a)
a.update(qty=7.0, confirmed_qty=7.0); b.update(qty=8.0, confirmed_qty=8.0); r["request_ledger"] = [a, b]
x = run("r13_duplicate_topup_identity", d); s91 = x["summary"]
check("[9.1] the same client_id on two entries (7 + 8 = 15) ⇒ UNEXPLAINED:duplicate_client_id, complete_parity False (v11 summed them and passed)",
      G(s91, "complete_parity", True) is False and G(s91, "request_population", {}).get("UNEXPLAINED:duplicate_client_id") == 2, G(s91, "request_population", {}))

d = partial_data(); topup_row(d)["side"] = "sell"                           # ② row says sell, signed ledger qty is +15
x = run("r13_topup_row_side_opposes_qty", d); s92 = x["summary"]
check("[9.2] top-up row side=sell while the ledger qty is +15 ⇒ complete_parity False naming the row/ledger side contradiction (v11 never read the row)",
      G(s92, "complete_parity", True) is False and any("side" in t for e in x["rows"] for t in (e.get("diffs") or [])),
      [e.get("diffs") for e in x["rows"] if e.get("diffs")])

d = partial_data(); topup_row(d)["request_ledger"][0]["qty"] = None         # ③a a measured R1 must not bury an unmeasured top-up
x = run("r13_topup_unknown_qty_hidden_by_R1", d); s93 = x["summary"]
check("[9.3] top-up qty=None behind a measured R1 ⇒ n_unmeasurable ≥ 1 and complete_parity False (v11 classed the plan MEASURED_EQUAL with n_unmeasurable 0)",
      G(s93, "complete_parity", True) is False and G(s93, "n_unmeasurable", 0) >= 1
      and any(str(k).startswith("PARTIAL_UNMEASURABLE") for k in G(s93, "plan_population", {})), G(s93, "plan_population", {}))

d = partial_data()                                                          # ③b the same, via an unknown skip reason instead of a null qty
topup_row(d).update(request_ledger=[], terminal_reason="UNKNOWN_SKIP")
x = run("r13_unknown_topup_skip_hidden_by_R1", d); s94 = x["summary"]
check("[9.4] an UNKNOWN_SKIP top-up behind a measured R1 ⇒ n_unmeasurable ≥ 1 and complete_parity False (v11 reported MEASURED_EQUAL)",
      G(s94, "complete_parity", True) is False and G(s94, "n_unmeasurable", 0) >= 1, G(s94, "plan_population", {}))

d = base_data(); d["an"]["reshape"] = dict(g["reshape_replayed"])            # ④ the R1 ledger moved onto another maker row with wrong side / RO
first = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")
bad = json.loads(json.dumps(first)); first["request_ledger"] = []
bad.update(attempt_idx=2, side="sell", reduce_only=True); d["orders"].append(bad)
x = run("r13_maker_request_validated_using_other_row", d); s95 = x["summary"]
check("[9.5] the R1 ledger sits on a row with side=sell / reduce_only=True ⇒ complete_parity False (v11 judged it with the FIRST row's correct fields)",
      G(s95, "complete_parity", True) is False, (G(s95, "complete_parity"), [e.get("diffs") for e in x["rows"] if e.get("diffs")]))

d = base_data(); d["an"]["reshape"] = dict(g["reshape_replayed"])            # ⑤ reduce_only evidence simply absent
for r in d["orders"]:
    if r["symbol"] == "AUSDT": r["reduce_only"] = None
x = run("r13_missing_reduce_only_evidence", d); s96 = x["summary"]
check("[9.6] reduce_only absent on the maker row ⇒ a FIELD EVIDENCE GAP that blocks complete_parity (v11 treated None as a pass)",
      G(s96, "complete_parity", True) is False and G(s96, "n_plans_with_field_evidence_gaps", 0) >= 1
      and any("reduce_only" in k for k in G(s96, "field_evidence_gap_kinds", {})), G(s96, "field_evidence_gap_kinds", {}))

d = base_data(); d["an"]["reshape"] = dict(g["reshape_replayed"])            # ⑥ an orphan row: the population flag must be an equality
orph = json.loads(json.dumps(next(r for r in d["orders"] if r["symbol"] == "AUSDT")))
orph.update(symbol="EXTRAUSDT", request_ledger=[]); d["orders"].append(orph)
x = run("r13_orphan_row_population_equality", d); s97 = x["summary"]
pid = G(s97, "population_identity", {})
check("[9.7] an orphan row with no plan ⇒ the request identity is an EQUALITY, so requests_balance is False (v11 used >= and read True)",
      pid.get("n_request_classified") != pid.get("n_ledger_entries") and pid.get("requests_balance") is False and G(s97, "complete_parity", True) is False, pid)

d = partial_data(); topup_row(d)["request_ledger"][0]["qty"] = float("nan")  # negative control the reviewer kept
x = run("r13_nan_topup_negative_control", d); s98 = x["summary"]
check("[9.8] NEGATIVE CONTROL: a NaN top-up quantity is still refused (not a new hole)", G(s98, "complete_parity", True) is False, G(s98, "complete_parity"))

# ───────────────────────── [10] round 14 (independent review 5a1ef77a): R14-P1 / R14-P2 ─────────────────────────
#   Re-run with PC1_DEV=archive/pc1_intent_replay_v12.py and [10.1]–[10.4] must go red ([10.0] is the green control).
print("\n[10] round 14: a never-sent ledger entry, the residual read off the wrong row, a masked field, and a double-counted duplicate")

x = run("r14_green_partial", partial_data()); s100 = x["summary"]
check("[10.0] GREEN BASELINE (unchanged): maker 25 filled 10 + a legal SENT 15 top-up ⇒ complete_parity True, no unmeasurable leg",
      G(s100, "complete_parity") is True and G(s100, "n_unmeasurable", -1) == 0, s100)

d = partial_data()                                                          # ① the top-up ledger was PRE-BUILT and never sent
tr = topup_row(d); tr["terminal_reason"] = "abandoned_max_attempts"; tr["filled_known_notional"] = None; tr["filled_notional"] = None
tr["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "notional_est": 15.0, "state": "not_sent",
                         "confirmed_notional": None, "confirmed_qty": None, "order_id": None, "terminal": False}]
x = run("r14_topup_not_sent_ledger", d); s101 = x["summary"]
check("[10.1] a pre-built ledger entry with state=not_sent / order_id=None is INTENT, not a 15-lot request ⇒ complete_parity False and the leg is unmeasurable (v12: complete_parity True)",
      G(s101, "complete_parity", True) is False and G(s101, "n_unmeasurable", 0) >= 1
      and any("not_sent" in k for k in G(s101, "plan_population", {})), (G(s101, "complete_parity"), G(s101, "plan_population")))

d = partial_data()                                                          # ② the R1 ledger lives on a second maker row that filled 10; the first row says 25
own = json.loads(json.dumps(next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")))
first = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")
first["request_ledger"] = []; first["filled_known_notional"] = 25.0; first["filled_notional"] = 25.0
own["filled_known_notional"] = 10.0; own["filled_notional"] = 10.0
d["orders"].append(own)
d["orders"] = [r for r in d["orders"] if not (r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker")]   # no top-up row at all
x = run("r14_residual_from_wrong_row", d); s102 = x["summary"]
_rows = {e["symbol"]: e for e in x["rows"]}
check("[10.2] the residual comes from the row that CARRIES the request (filled 10 ⇒ 15 still due), and the 25-vs-10 disagreement is reported ⇒ complete_parity False (v12 read 25 off row1, got residual 0 and passed)",
      G(s102, "complete_parity", True) is False
      and any("owner_row_fill_contradicts_other_row" in z for z in (_rows.get("AUSDT", {}).get("diffs") or []))
      and abs(float((_rows.get("AUSDT", {}).get("R3") or {}).get("residual_rule", 0.0)) - 15.0) < 1e-6,
      (G(s102, "complete_parity"), _rows.get("AUSDT", {}).get("diffs"), (_rows.get("AUSDT", {}).get("R3") or {}).get("residual_rule")))

d = partial_data()                                                          # ③ the top-up row's side contradicts the plan while its quantity is missing
tr = topup_row(d); tr["side"] = "sell"; tr["request_ledger"][0]["qty"] = None
x = run("r14_missing_qty_masks_wrong_side", d); s103 = x["summary"]
_r3 = next((e for e in x["rows"] if e["symbol"] == "AUSDT"), {})
check("[10.3] a missing top-up quantity no longer hides a wrong SIDE on the owning row ⇒ the field contradiction is reported and all_measurable_exact is False (v12: diffs empty, all_measurable_exact True)",
      G(s103, "all_measurable_exact", True) is False and any("row_side" in z for z in (_r3.get("diffs") or [])),
      (G(s103, "all_measurable_exact"), _r3.get("diffs")))

d = partial_data()                                                          # ④ the first-leg ledger entry duplicated: one class per entry, identity must balance
mk = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")
mk["request_ledger"] = mk["request_ledger"] + [json.loads(json.dumps(mk["request_ledger"][0]))]
x = run("r14_duplicate_cid_population", d); s104 = x["summary"]
pid4 = G(s104, "population_identity", {})
check("[10.4] a duplicated client_id is classified ONCE ⇒ n_request_classified == n_ledger_entries and requests_balance True, while complete_parity stays False (v12 counted it three times: 5 entries, 7 classifications)",
      pid4.get("n_request_classified") == pid4.get("n_ledger_entries") and pid4.get("requests_balance") is True
      and G(s104, "complete_parity", True) is False, (pid4, G(s104, "request_population")))

# ───────────────────────── [11] round 15 (independent review R15-P1 / R15-P2) ─────────────────────────
#   [11.1]-[11.4] and [11.6] are false passes on v13 (the pre-fix device) and must go GREEN on v14; [11.0] (green baseline) and [11.5]
#   (no-false-positive) pass on BOTH so a red verdict is discriminating, not a broken fixture. All fixtures drive the REAL device via run().
print("\n[11] round 15: an UNREADABLE maker fill must make the residual UNMEASURABLE (not delta−0), and an unsent sibling must not mask a known over-fill")


def rows_by_sym(x): return {e["symbol"]: e for e in x.get("rows", [])}


# [11.0] GREEN BASELINE (readable partial): a red [11.x] below is then a discriminating verdict.
x = run("r15_green_partial", partial_data()); s110 = x["summary"]
check("[11.0] GREEN BASELINE: maker 25 filled a READABLE 10 (filled_notional=10) + a legal 15 top-up ⇒ complete_parity True, residual_rule 15, n_unmeasurable 0",
      G(s110, "complete_parity") is True and G(s110, "n_unmeasurable", -1) == 0
      and abs(float((rows_by_sym(x).get("AUSDT", {}).get("R3") or {}).get("residual_rule", 0.0)) - 15.0) < 1e-6, s110)

# [11.1] R15-P1 (a): the maker FILL is unreadable (filled_notional=None) and the top-up matches the FABRICATED full delta 25.
d = partial_data()
mk = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")
mk["terminal_reason"] = "filled_amount_unknown"; mk["filled_known_notional"] = None; mk["filled_notional"] = None      # FILL total not closed ⇒ UNREADABLE
mk["request_ledger"] = [{"client_id": f"{RID}-AUSDT-1", "qty": 25.0, "confirmed_qty": 25.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]   # the ORDER reached the venue for 25 ⇒ R1 stays exact
tr = topup_row(d); tr["terminal_reason"] = "filled"; tr["intended_notional"] = 25.0; tr["filled_known_notional"] = 25.0; tr["filled_notional"] = 25.0
tr["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 25.0, "confirmed_qty": 25.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("r15_unreadable_fill_full_delta", d); s111 = x["summary"]; r111 = (rows_by_sym(x).get("AUSDT", {}).get("R3") or {})
check("[11.1] an UNREADABLE maker fill ⇒ residual UNMEASURABLE not delta−0: residual_unmeasurable True, residual_rule None, plan PARTIAL_UNMEASURABLE, complete_parity False (v13: residual 25, R3_consistent, complete_parity True)",
      G(s111, "complete_parity", True) is False and G(s111, "n_unmeasurable", 0) >= 1 and r111.get("residual_unmeasurable") is True
      and r111.get("residual_rule") is None and any("topup_residual_unmeasurable" in k for k in G(s111, "plan_population", {})),
      (G(s111, "complete_parity"), r111.get("residual_rule"), G(s111, "plan_population")))

# [11.2] R15-P1 (b): a KNOWN PART (filled_known_notional=5) is not the total ⇒ v13 fabricated residual = delta−5 = 20 and a 20 top-up matched.
d = partial_data()
mk = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker")
mk["terminal_reason"] = "filled_amount_unknown"; mk["filled_known_notional"] = 5.0; mk["filled_notional"] = None       # 5 known, TOTAL not closed
mk["request_ledger"] = [{"client_id": f"{RID}-AUSDT-1", "qty": 25.0, "confirmed_qty": 25.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
tr = topup_row(d); tr["terminal_reason"] = "filled"; tr["intended_notional"] = 20.0; tr["filled_known_notional"] = 20.0; tr["filled_notional"] = 20.0
tr["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 20.0, "confirmed_qty": 20.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("r15_known_part_not_total", d); s112 = x["summary"]; r112 = (rows_by_sym(x).get("AUSDT", {}).get("R3") or {})
check("[11.2] a KNOWN part (5) is NOT the total ⇒ residual UNMEASURABLE, complete_parity False (v13 read filled_known_notional as the total, residual delta−5=20, the 20 top-up matched, complete_parity True)",
      G(s112, "complete_parity", True) is False and r112.get("residual_unmeasurable") is True and r112.get("residual_rule") is None, (G(s112, "complete_parity"), r112))

# [11.3] R15-P1 (c): a row LOOKS closed (filled_notional=25) but an unknown-part marker is set ⇒ readability is denied by the marker.
d = base_data(); d["an"]["reshape"] = dict(g["reshape_replayed"])
mk = next(r for r in d["orders"] if r["symbol"] == "AUSDT" and r["order_type"] == "maker"); mk["filled_unknown_qty"] = 500.0
x = run("r15_unknown_marker_overrides_total", d); s113 = x["summary"]; r113 = (rows_by_sym(x).get("AUSDT", {}).get("R3") or {})
check("[11.3] filled_unknown_qty set (a further unknown part) overrides a present filled_notional ⇒ residual UNMEASURABLE, complete_parity False (v13 trusted filled_known_notional=25, residual 0, complete_parity True)",
      G(s113, "complete_parity", True) is False and r113.get("residual_unmeasurable") is True, (G(s113, "complete_parity"), r113))

# [11.4] R15-P2 (RED): expected 15, a chunk SENT for 20 (a known over-fill) + a never-sent sibling of 5. The unsent sibling must not mask the over-fill.
d = partial_data(); tr = topup_row(d); tr["terminal_reason"] = "filled"; tr["intended_notional"] = 15.0
tr["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 20.0, "confirmed_qty": 20.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True},
                        {"client_id": f"{RID}-AUSDT-3c1", "qty": 5.0, "state": "not_sent", "confirmed_qty": None, "order_id": None, "terminal": False}]
x = run("r15_overfill_masked_by_unsent_sibling", d); s114 = x["summary"]; r114 = rows_by_sym(x).get("AUSDT", {})
check("[11.4] a SENT chunk 20 vs an expected 15 is a KNOWN over-fill no unsent chunk can undo ⇒ a qty DIFF is reported and all_measurable_exact False (v13: `if n_not_sent` skipped the comparison ⇒ empty diff, all_measurable_exact True)",
      G(s114, "all_measurable_exact", True) is False and any("overfill" in z for z in (r114.get("diffs") or []))
      and (r114.get("R3") or {}).get("known_overshoot") is True, (G(s114, "all_measurable_exact"), r114.get("diffs")))

# [11.5] R15-P2 (no-false-positive, passes on BOTH): expected 15, a chunk SENT for 10 (UNDER) + a never-sent sibling of 5 — a sibling could complete it ⇒ NO over-fill diff.
d = partial_data(); tr = topup_row(d); tr["terminal_reason"] = "filled"; tr["intended_notional"] = 15.0
tr["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 10.0, "confirmed_qty": 10.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True},
                        {"client_id": f"{RID}-AUSDT-3c1", "qty": 5.0, "state": "not_sent", "confirmed_qty": None, "order_id": None, "terminal": False}]
x = run("r15_underfill_with_unsent_sibling", d); s115 = x["summary"]; r115 = rows_by_sym(x).get("AUSDT", {})
check("[11.5] NO-FALSE-POSITIVE: a SENT chunk 10 ≤ expected 15 with an unsent sibling is consistent-so-far ⇒ NO over-fill diff, but the remainder is unmeasurable (n_unmeasurable ≥ 1)",
      not any(("overfill" in z) or (z == "R3:qty") for z in (r115.get("diffs") or [])) and G(s115, "n_unmeasurable", 0) >= 1, (r115.get("diffs"), G(s115, "n_unmeasurable")))

# [11.6] R15 wording: the request states are reported SEPARATELY (an `unknown`/`not_sent` state is NOT asserted to have reached the venue).
check("[11.6] summary.request_state_population reports states SEPARATELY: confirmed and not_sent both counted (the [11.4] fixture carried one confirmed chunk + one not_sent)",
      isinstance(G(s114, "request_state_population"), dict) and G(s114, "request_state_population", {}).get("not_sent", 0) >= 1
      and G(s114, "request_state_population", {}).get("confirmed", 0) >= 1, G(s114, "request_state_population"))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  device sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}")
sys.exit(0 if not FAILS else 1)
