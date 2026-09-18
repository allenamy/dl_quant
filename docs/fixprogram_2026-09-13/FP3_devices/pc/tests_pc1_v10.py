#!/usr/bin/env python3
"""Behavioural tests for pc1_intent_replay.py v10 (independent review round 11, R11-PC1). Each red case is one of the reviewer's counterexamples that
v9 passed; the green baseline is asserted FIRST so that a red verdict is a discriminating verdict and not a broken fixture.
Fixtures are a synthetic executor state tree (anchor_runs.log, pilot_log day files, exchange_info_cache.json) and a synthetic producer target;
the executor code is the real 409ea16 tree exported by `git archive` into the scratchpad (PC1_TREE_DIR), so the book layer and planner are the
same code the device uses on real anchors. Nothing here touches ~/dl_quant_live or ~/wide_shadow.
Run: python3 tests_pc1_v10.py   (exit 0 iff ALL PASS)"""
import copy, json, math, os, subprocess, sys, time, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "pc1_intent_replay.py")
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
check("foreign identities are unexplained requests, R1_exact == 0, all_measurable_exact False", x["summary"]["R1_exact"] == 0 and cat.get("unexplained_request:foreign_identity", 0) >= 4 and x["summary"]["all_measurable_exact"] is False, cat)

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
d = base_data(); d["an"]["chase_experiment"]["arm_assigned"]["AUSDT"] = "no_chase"
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0, terminal=True)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0; r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "confirmed_qty": 15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("nochase_sent", d); cat = x["summary"]["categories"]
check("no_chase draw yet a chunk was sent ⇒ R3_lifecycle_unexplained", cat.get("R3_lifecycle_unexplained", 0) == 1, cat)
d = base_data()
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "skipped_no_chase_arm"; r["intended_notional"] = 15.0
x = run("chase_skipped", d); cat = x["summary"]["categories"]
check("chase draw yet skipped_no_chase_arm ⇒ R3_skip_unexplained:no_chase_arm", cat.get("R3_skip_unexplained:no_chase_arm", 0) == 1, cat)
d = base_data()
for r in d["orders"]:
    if r["symbol"] == "AUSDT" and r["order_type"] == "maker": r["filled_known_notional"] = 10.0; r["request_ledger"][0].update(confirmed_qty=10.0)
    if r["symbol"] == "AUSDT" and r["order_type"] == "topup_taker": r["terminal_reason"] = "filled"; r["intended_notional"] = 15.0; r["request_ledger"] = [{"client_id": f"{RID}-AUSDT-3", "qty": 15.0, "confirmed_qty": 15.0, "state": "confirmed", "terminal": True, "confirmed_qty_final": True}]
x = run("chase_consistent", d); cat = x["summary"]["categories"]
check("chase draw, residual 15 at mid 1 ⇒ chunk 15 is R3_consistent (positive control of the rule)", cat.get("R3_consistent", 0) == 1 and x["summary"]["all_measurable_exact"] is True, cat)

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  device sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}")
sys.exit(0 if not FAILS else 1)
