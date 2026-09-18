#!/usr/bin/env python3
"""Behavioural tests for q6_shadow.py v6 — independent review round 14 (R14-Q1…Q5).

Every case drives the device's REAL CLI as a subprocess (never a helper standing in for it), because the round-14 finding was precisely that the
checkpoint resume path and the fresh build were two different fact contracts. The reviewer's own input generators are reproduced in shape from
`agents/q6/audit_q6_v5.py` (frozen at codex 5a1ef77a): a `same` client_id, one symbol AAA, readbacks on the 4h grid, a per-run filters file that
sets the lot step. The GREEN baseline is asserted first; each red case is then shown to be red on the archived predecessor
`archive/q6_shadow_v5_1d5600da.py`, so a pass here is a discriminating pass and not a fixture that never exercised the rule.
Run: python3 tests_q6_resume_r14.py      (exit 0 iff ALL PASS)"""
import copy, hashlib, importlib.util, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("Q6_DEV") or os.path.join(HERE, "q6_shadow.py")
# The archived predecessor resolves its `support/` import from its OWN directory, and the archive folder has none — so the red control is staged
# into a scratch directory with a copy of support/ beside it. The bytes are unchanged; only its location is.
_OLD_SRC = os.path.join(HERE, "archive", "q6_shadow_v5_1d5600da.py")


def _stage_old():
    if not os.path.exists(_OLD_SRC): return None
    import shutil
    d = tempfile.mkdtemp(prefix="q6r14_old_", dir=os.environ.get("TMPDIR") or None)
    shutil.copy(_OLD_SRC, os.path.join(d, "q6_shadow_v5.py"))
    shutil.copytree(os.path.join(HERE, "support"), os.path.join(d, "support"), ignore=shutil.ignore_patterns("__pycache__"))
    return os.path.join(d, "q6_shadow_v5.py")


OLD = _stage_old()
BASE = 1786147200                                                           # 2026-08-08 00:00 UTC, 4h aligned
D1, D2 = "20260808", "20260809"
ROOT = tempfile.mkdtemp(prefix="q6r14_tests_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []; TABLE = []


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q, s="AAA"):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol=s, venue_position_qty=q,
                venue_position_notional=q * 100, source="exec@post_anchor")


def order(snap=1, cq=0, terminal=False, final=False, cap=3, side="buy", rid="same"):
    return dict(anchor_ts=BASE + 14400, submit_ts=BASE + 14400, symbol="AAA", side=side, cancel_ts=BASE + snap * 14400 + 10,
                request_ledger=[dict(client_id=rid, qty=cap, confirmed_qty=cq, terminal=terminal, confirmed_qty_final=final, state="confirmed")])


def fixture(name, days):
    root = os.path.join(ROOT, name)
    for d, data in days.items():
        p = os.path.join(root, "state", "live", "pilot_log", d); os.makedirs(p, exist_ok=True)
        for n in ("orders", "position_readback", "fills", "anchors"):
            open(os.path.join(p, n + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in data.get(n, [])))
    return root


def run(root, tag, start=D1, end=D2, cp_in=None, step=1.0, dev=DEV, expect_fail=False):
    out = os.path.join(root, tag + ".json"); cp = os.path.join(root, tag + "_cp.json")
    f = os.path.join(root, tag + "_filters.json"); open(f, "w").write(json.dumps({"AAA": {"step": step}}))
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=f, Q6_PROCS="1", Q6_DETAIL="1", Q6_CHECKPOINT_OUT=cp, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join([os.path.join(HERE, "support"), os.environ.get("PYTHONPATH", "")]))   # the archived device lives in archive/ and still needs support/
    env.pop("Q6_CHECKPOINT_IN", None)
    if cp_in: env["Q6_CHECKPOINT_IN"] = cp_in
    p = subprocess.run([sys.executable, dev, start, end, out], capture_output=True, text=True, env=env)
    if expect_fail: return {"rc": p.returncode, "stderr": p.stderr[-600:], "stdout": p.stdout[-300:]}
    if p.returncode != 0: return {"rc": p.returncode, "stderr": p.stderr[-800:], "crashed": True}
    r = json.loads(open(out).read()); c = json.loads(open(cp).read())
    obs = (r.get("detail", {}).get("AAA", {}) or {}).get("observations", [])
    return {"rc": 0, "receipt": r, "cp": c, "cp_path": cp, "distance": [o["distance_lots"] for o in obs],
            "category": [o["category"] for o in obs]}


print(f"device {os.path.basename(DEV)} sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}  |  red control staged: {bool(OLD)}")

print("\n[G] GREEN BASELINE — consistent facts: one pass and a resumed pass must agree, and the resumed state must be identical")
g = fixture("green", {D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order(1, 1, True, True, 1)]},
                      D2: {"position_readback": [rb(6, 1)]}})
g_full = run(g, "full"); g_half = run(g, "half", end=D1); g_res = run(g, "resume", start=D2, cp_in=g_half["cp_path"])
check("[G0] the uninterrupted pass runs and every observation is CLEAN", g_full["rc"] == 0 and set(g_full["category"]) == {"CLEAN"}, g_full.get("category") or g_full)
check("[G1] the resumed pass gives the same distances and categories as the uninterrupted one",
      g_res["rc"] == 0 and g_res["distance"] == g_full["distance"] and g_res["category"] == g_full["category"], (g_res.get("distance"), g_full.get("distance")))
check("[G2] the resumed MATERIAL-STATE sha equals the uninterrupted one (the §1d.5 restart-parity claim is about this number)",
      g_res["receipt"]["checkpoint"]["state_sha256"] == g_full["receipt"]["checkpoint"]["state_sha256"],
      (g_res["receipt"]["checkpoint"]["state_sha256"][:16], g_full["receipt"]["checkpoint"]["state_sha256"][:16]))
check("[G3] the IDENTITY sha differs across the split — it pins what produced the state (window, inputs) and is deliberately not part of parity",
      g_res["receipt"]["checkpoint"]["identity_sha256"] != g_full["receipt"]["checkpoint"]["identity_sha256"],
      (g_res["receipt"]["checkpoint"]["identity"]["window"], g_full["receipt"]["checkpoint"]["identity"]["window"]))
TABLE.append(("G baseline resume parity", g_full["category"], g_res["category"]))

print("\n[Q1] the SAME client_id is BUY 3 on day 1 and SELL 3 on day 2 — a restart may not change the verdict on identical facts")
q1 = fixture("q1_identity", {D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order()]},
                             D2: {"position_readback": [rb(6, 2)], "orders": [order(side="sell", cap=-3)]}})
q1_full = run(q1, "full"); q1_half = run(q1, "half", end=D1); q1_res = run(q1, "resume", start=D2, cp_in=q1_half["cp_path"])
check("[Q1.0] the uninterrupted pass detects the identity contradiction (both observations UNMEASURABLE)",
      q1_full["category"] == ["UNMEASURABLE", "UNMEASURABLE"], q1_full.get("category") or q1_full)
check("[Q1.1] the RESUMED pass reaches the same verdict — v5 kept the carried side and reported CLEAN, CLEAN",
      q1_res["category"] == ["UNMEASURABLE", "UNMEASURABLE"], q1_res.get("category") or q1_res)
q1_half_old = run(q1, "half_old", end=D1, dev=OLD) if OLD else None
q1_old = run(q1, "resume_old", start=D2, cp_in=q1_half_old["cp_path"], dev=OLD) if q1_half_old and q1_half_old.get("rc") == 0 else None
check("[Q1.2] RED CONTROL: the archived v5 resumes the same checkpoint to CLEAN, CLEAN", q1_old is None or q1_old.get("category") == ["CLEAN", "CLEAN"], q1_old and q1_old.get("category"))
TABLE.append(("Q1 resume identity conflict", q1_full["category"], q1_res.get("category")))

print("\n[Q2] a late hard fact with NO new readback must rebuild the carried prefix at its own event time (§1d.3)")
q2 = fixture("q2_late_no_read", {D1: {"position_readback": [rb(0, 0), rb(1, 80)], "orders": [order(cap=100)]},
                                 D2: {"orders": [order(1, 50, True, True, 100)]}})
q2_full = run(q2, "full"); q2_half = run(q2, "half", end=D1); q2_res = run(q2, "resume", start=D2, cp_in=q2_half["cp_path"])
check("[Q2.0] the uninterrupted pass gives distance 30 (the admitted 80 cannot stand against an exact total of 50)",
      q2_full["distance"] == [30], q2_full.get("distance") or q2_full)
check("[Q2.1] the RESUMED pass also gives 30 — v5 kept admitted 80 at distance 0 while its own hard facts said 50",
      q2_res["distance"] == [30], q2_res.get("distance") or q2_res)
check("[Q2.2] the rebuild is recorded and the ORIGINAL receipts are preserved (§1d.3 forbids rewriting them)",
      q2_res["receipt"]["checkpoint"].get("late_evidence_rebuilds", {}).get("AAA") is not None
      and q2_res["receipt"]["checkpoint"].get("records_before_rebuild", {}).get("AAA") is not None,
      q2_res["receipt"]["checkpoint"].get("late_evidence_rebuilds"))
q2_half_old = run(q2, "half_old", end=D1, dev=OLD) if OLD else None
q2_old = run(q2, "resume_old", start=D2, cp_in=q2_half_old["cp_path"], dev=OLD) if q2_half_old and q2_half_old.get("rc") == 0 else None
check("[Q2.3] RED CONTROL: the archived v5 resumes to distance 0", q2_old is None or q2_old.get("distance") == [0], q2_old and q2_old.get("distance"))
TABLE.append(("Q2 late fact, no new read", q2_full["distance"], q2_res.get("distance")))

print("\n[Q3] a checkpoint written in one lot step, restored under another — units are part of the state")
q3 = fixture("q3_step", {D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order(cap=1)]},
                         D2: {"position_readback": [rb(6, 1)]}})
q3_half = run(q3, "half", end=D1, step=1.0)
q3_res = run(q3, "resume", start=D2, cp_in=q3_half["cp_path"], step=0.1, expect_fail=True)
check("[Q3.0] the resume REFUSES on a lot-step mismatch and names it (v5 silently reinterpreted the carried lots and reported 9 lots)",
      q3_res["rc"] != 0 and "lot-step mismatch" in (q3_res["stderr"] + q3_res["stdout"]), (q3_res["rc"], q3_res["stderr"][-200:]))
q3_same = run(q3, "resume_same_step", start=D2, cp_in=q3_half["cp_path"], step=1.0)
check("[Q3.1] GREEN CONTROL: the same checkpoint restored under the SAME step resumes normally at distance 0",
      q3_same["rc"] == 0 and q3_same["distance"][-1] == 0, q3_same.get("distance") or q3_same)
q3_half_old = run(q3, "half_old", end=D1, step=1.0, dev=OLD) if OLD else None
q3_old = run(q3, "resume_old", start=D2, cp_in=q3_half_old["cp_path"], step=0.1, dev=OLD) if q3_half_old and q3_half_old.get("rc") == 0 else None
check("[Q3.2] RED CONTROL: the archived v5 accepts the mismatch and reports a 9-lot distance on an unmoved position",
      q3_old is None or (q3_old.get("rc") == 0 and q3_old.get("distance", [None])[-1] == 9), q3_old and (q3_old.get("rc"), q3_old.get("distance")))
TABLE.append(("Q3 lot-step mismatch", "REFUSED", q3_res["rc"]))

print("\n[Q4] a credible cumulative lower bound arriving AFTER the terminal pin must bind the pin variable")
q4 = fixture("q4_post_terminal_floor", {D1: {"position_readback": [rb(0, 10), rb(1, 11), rb(2, 11)],
                                             "orders": [order(1, 0, True), order(2, 2, True, False)]}})
q4_r = run(q4, "run", end=D1)
check("[Q4.0] by t2 the request is terminal with a credible bound of 2 while the observed increment is 1 ⇒ distance ≥ 1 (v5 said 0, CLEAN)",
      q4_r["rc"] == 0 and q4_r["distance"][-1] >= 1, q4_r.get("distance") or q4_r)
q4_old = run(q4, "run_old", end=D1, dev=OLD) if OLD else None
check("[Q4.1] RED CONTROL: the archived v5 reports 0, 0 and CLEAN twice", q4_old is None or q4_old.get("distance") == [0, 0], q4_old and q4_old.get("distance"))
TABLE.append(("Q4 post-terminal lower bound", q4_r["distance"], "v5 [0, 0]"))

print("\n[Q5] the late-fact helper is the same entry point as the CLI: an earlier smaller bound is a fact, two exact totals are a contradiction")
spec = importlib.util.spec_from_file_location("q6_r14_under_test", DEV); Q6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(Q6)
q5a = fixture("q5_earlier_floor", {D1: {"position_readback": [rb(0, 0), rb(1, 0), rb(2, 2)], "orders": [order(2, 2)]}})
r5a = run(q5a, "run", end=D1)
reb = Q6.late_evidence_rebuild(r5a["cp"]["symbols"]["AAA"], [{"rid": "same", "floor": 1, "floor_ts": BASE + 14400 + 10}])
check("[Q5.0] a late SMALLER bound at an EARLIER time is accepted as a fact (v5 compared it to the scalar floor and called it no_change)",
      reb.get("no_change") is not True and len(reb["requests"][0].get("floor_steps") or []) >= 2, (reb.get("no_change"), reb["requests"][0].get("floor_steps")))
check("[Q5.1] it excludes the observation it contradicts (read 0 at t1 while at least 1 was already filled)",
      1 in [e["k"] for e in reb.get("newly_excluded", [])] or 1 in [e["k"] for e in reb.get("excluded", [])], (reb.get("newly_excluded"), reb.get("excluded")))
q5b = fixture("q5_contradictory_exact", {D1: {"position_readback": [rb(0, 0), rb(1, 2)], "orders": [order(1, 2, True, True)]}})
r5b = run(q5b, "run", end=D1)
reb2 = Q6.late_evidence_rebuild(r5b["cp"]["symbols"]["AAA"], [{"rid": "same", "exact": 1, "exact_ts": BASE + 14400 + 10}])
check("[Q5.2] a second, different credible exact total is a HARD CONTRADICTION, not a silently kept winner (§1d.4)",
      reb2.get("hard_contradiction") and reb2.get("status") == "unmeasurable", {k: reb2.get(k) for k in ("no_change", "hard_contradiction", "status")})
check("[Q5.3] GREEN CONTROL: a late fact that tightens nothing still reports no_change",
      Q6.late_evidence_rebuild(r5b["cp"]["symbols"]["AAA"], [{"rid": "same", "exact": 2, "exact_ts": BASE + 14400 + 10}]).get("no_change") is True)
TABLE.append(("Q5 helper entry parity", "ladder + contradiction", "ok"))

print("\n[Q5-sha] the state sha must cover the original receipts, the price marks and the code/input/epoch identity")
sha_now = g_full["receipt"]["checkpoint"]["state_sha256"]
covers = g_full["receipt"]["checkpoint"]["state_sha256_covers"]
check("[Q5.4] the receipt states which fields the sha covers, and they include records, marks and the identity block",
      "records" in covers["per_symbol_fields"] and "marks" in covers["per_symbol_fields"] and "device_sha256" in covers["identity_fields"], covers)
_cp = json.load(open(g_full["cp_path"])); _sym = copy.deepcopy(_cp["symbols"]["AAA"])
_FIELDS = tuple(covers["per_symbol_fields"])
_ident = g_full["receipt"]["checkpoint"]["identity"]
_hash = lambda sym: hashlib.sha256(Q6.canon({"AAA": {k: sym.get(k) for k in _FIELDS}})).hexdigest()
check("[Q5.5] the recomputed sha matches the receipt (the published formula is the one that was used)", _hash(_sym) == sha_now, (_hash(_sym)[:16], sha_now[:16]))
_mut = copy.deepcopy(_sym); _mut["records"][-1]["distance_lots"] = 999
check("[Q5.6] changing an original receipt CHANGES the sha (v5's subset left it unchanged)", _hash(_mut) != sha_now)
_mut2 = copy.deepcopy(_sym); _mut2["marks"] = [[BASE, 999]]
check("[Q5.7] changing the price marks CHANGES the sha", _hash(_mut2) != sha_now)
_ident2 = dict(_ident); _ident2["device_sha256"] = "0" * 64
check("[Q5.8] changing the code identity CHANGES the IDENTITY sha (provenance is pinned, separately from the parity claim)",
      hashlib.sha256(Q6.canon(_ident2)).hexdigest() != g_full["receipt"]["checkpoint"]["identity_sha256"])

print("\n" + "-" * 110)
for a, b, c in TABLE: print(f"  {a:34s} {str(b):28s} {str(c)}")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
