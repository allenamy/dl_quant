#!/usr/bin/env python3
"""Behavioural tests for q6_shadow.py v6 — independent review round 15 (R15-Q1…Q3).

Every case drives the device's REAL CLI as a subprocess (never a helper standing in for it), because all three round-15 findings live in the
checkpoint RESUME path — a defect a pure-helper test would step around. The GREEN baseline is asserted first, then each red case is shown to be red
on the archived predecessor `archive/q6_shadow_v6pre_r15_c3ffc13a.py` (the exact bytes of q6_shadow.py at the start of round 15, sha256
0362223080b2ffbf49700e5213bfd460f509e6d14bf67310053820a5b7e18b61), so a pass here is a discriminating pass and not a fixture that never
exercised the rule. A separate file (not extending tests_q6_resume_r14.py) keeps the R15 provenance and its own red control self-contained.

  R15-Q1  a contradiction CREATED BY THE MERGE (a fresh floor-ladder step raises a carried request's floor above its exact total, or fills push it
          past cap) was never re-checked after resume — fact_conflict only compares (cap, side) and two exact totals, so it read CLEAN.
  R15-Q2  late evidence was detected ONLY for a rid already in the checkpoint: (a) a brand-new rid with backdated hard facts and (b) a late FILL
          both escaped, so the carried prefix was never rebuilt. (With a new readback the model's own rebuild masks it; the escape bites when the
          late fact arrives with NO new readback.)
  R15-Q3  the checkpoint WROTE state_sha256 / identity_sha256 but verified NEITHER on load — a checkpoint whose per-symbol state was edited resumed
          silently. The hash was a label, not a guard.

Run: python3 tests_q6_merge_r15.py      (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS)."""
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("Q6_DEV") or os.path.join(HERE, "q6_shadow.py")
_OLD_SRC = os.path.join(HERE, "archive", "q6_shadow_v6pre_r15_c3ffc13a.py")   # the exact bytes of q6_shadow.py at the start of round 15
BASE = 1786147200                                                           # 2026-08-08 00:00 UTC, 4h aligned
D1, D2 = "20260808", "20260809"
ROOT = tempfile.mkdtemp(prefix="q6r15_tests_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []; TABLE = []

spec = importlib.util.spec_from_file_location("q6_r15_under_test", DEV); Q6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(Q6)


def _stage_old():
    """the archived predecessor resolves its support/ import from its OWN directory; the archive folder has none, so stage it with support/ beside it."""
    if not os.path.exists(_OLD_SRC): return None
    d = tempfile.mkdtemp(prefix="q6r15_old_", dir=os.environ.get("TMPDIR") or None)
    shutil.copy(_OLD_SRC, os.path.join(d, "q6_shadow_v6pre.py"))
    shutil.copytree(os.path.join(HERE, "support"), os.path.join(d, "support"), ignore=shutil.ignore_patterns("__pycache__"))
    return os.path.join(d, "q6_shadow_v6pre.py")


OLD = _stage_old()


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q, s="AAA"):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol=s, venue_position_qty=q, venue_position_notional=q * 100, source="exec@post_anchor")


def order_row(anchor_k, cq, terminal, final, cap, rid="r1", side="buy", snap_k=None):
    """one request_ledger order row with explicit event timing: born at anchor_k, confirmed_qty snapshot stamped by cancel_ts at snap_k (default anchor_k)."""
    snap_k = anchor_k if snap_k is None else snap_k
    return dict(anchor_ts=BASE + anchor_k * 14400, submit_ts=BASE + anchor_k * 14400, symbol="AAA", side=side, cancel_ts=BASE + snap_k * 14400 + 10,
                request_ledger=[dict(client_id=rid, qty=cap, confirmed_qty=cq, terminal=terminal, confirmed_qty_final=final, state="confirmed")])


def fill_row(ts_abs, qty, tid, side="BUY"):
    return dict(fill_ts=ts_abs, symbol="AAA", side=side, fill_px=100, fill_notional=qty * 100, trade_id=tid)


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
               PYTHONPATH=os.pathsep.join([os.path.join(HERE, "support"), os.environ.get("PYTHONPATH", "")]))
    env.pop("Q6_CHECKPOINT_IN", None)
    if cp_in: env["Q6_CHECKPOINT_IN"] = cp_in
    p = subprocess.run([sys.executable, dev, start, end, out], capture_output=True, text=True, env=env)
    if expect_fail: return {"rc": p.returncode, "err": (p.stderr + p.stdout)[-700:]}
    if p.returncode != 0: return {"rc": p.returncode, "err": (p.stderr + p.stdout)[-800:], "crashed": True}
    r = json.loads(open(out).read()); c = json.loads(open(cp).read())
    o = (r.get("detail", {}).get("AAA", {}) or {}).get("observations", [])
    ck = r.get("checkpoint", {})
    return {"rc": 0, "receipt": r, "cp": c, "cp_path": cp, "distance": [x.get("distance_lots") for x in o], "category": [x.get("category") for x in o],
            "excluded_k": [x["k"] for x in o if x.get("excluded")], "notes": r.get("notes", {}), "unmeasurable": r.get("unmeasurable", []),
            "state_sha256": (ck.get("state_sha256")), "late_rebuilds": list((ck.get("late_evidence_rebuilds") or {}).keys()),
            "records_before": list((ck.get("records_before_rebuild") or {}).keys())}


print(f"device {os.path.basename(DEV)} sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}  |  red control staged: {bool(OLD)}")

# ───────────────────────────── [G] green baseline ─────────────────────────────
print("\n[G] GREEN BASELINE — a consistent split resume must be CLEAN and reproduce the uninterrupted state bit for bit")
g = fixture("green", {D1: {"position_readback": [rb(0, 0), rb(1, 1), rb(2, 1)], "orders": [order_row(1, cq=0, terminal=False, final=False, cap=100)]},
                      D2: {"position_readback": [rb(6, 1)]}})
g_full = run(g, "full"); g_half = run(g, "half", end=D1); g_res = run(g, "resume", start=D2, cp_in=g_half["cp_path"])
check("[G0] the uninterrupted pass runs and every observation is CLEAN", g_full["rc"] == 0 and set(g_full["category"]) == {"CLEAN"}, g_full.get("category") or g_full)
check("[G1] the resumed pass gives the same categories and distances as the uninterrupted one",
      g_res["rc"] == 0 and g_res["category"] == g_full["category"] and g_res["distance"] == g_full["distance"], (g_res.get("category"), g_full.get("category")))
check("[G2] the resumed MATERIAL-STATE sha equals the uninterrupted one, and the NEW load-time guard accepted the untampered checkpoint",
      g_res["state_sha256"] == g_full["state_sha256"] and g_res["rc"] == 0, (g_res.get("state_sha256"), g_full.get("state_sha256")))
check("[G3] a consistent resume triggers NO late-evidence rebuild and no post-merge contradiction",
      not g_res["late_rebuilds"] and g_res["notes"].get("request_contradiction_post_merge") in (None, 0) and g_res["notes"].get("resume_prefix_rebuilt_by_late_evidence") in (None, 0), g_res["notes"])
TABLE.append(("G baseline resume parity", g_full["category"], g_res["category"]))

# ───────────────────────────── [Q1] merge-created contradiction ─────────────────────────────
print("\n[Q1] a fresh floor-ladder step raises a carried request's floor above its exact total — a §1d.4 contradiction CREATED BY THE MERGE")
q1 = fixture("q1_merge_contra", {
    D1: {"position_readback": [rb(0, 0), rb(1, 3)], "orders": [order_row(1, cq=3, terminal=True, final=True, cap=10, rid="same")]},   # carried: exact 3
    D2: {"position_readback": [rb(6, 3)], "orders": [order_row(6, cq=5, terminal=False, final=False, cap=10, rid="same", snap_k=6)]}})  # fresh floor 5 merges in
q1_half = run(q1, "half", end=D1); q1_res = run(q1, "resume", start=D2, cp_in=q1_half["cp_path"])
check("[Q1.0] the resumed pass makes the symbol UNMEASURABLE (floor 5 from the merge exceeds the credible total 3)",
      q1_res["rc"] == 0 and set(q1_res["category"]) == {"UNMEASURABLE"}, q1_res.get("category") or q1_res)
check("[Q1.1] it is counted under a note that is SPECIFIC to merge-created contradictions, and names the bound", q1_res["rc"] == 0
      and q1_res["notes"].get("request_contradiction_post_merge") == 1 and any("outside [floor 5, cap 10]" in u.get("why", "") for u in q1_res["unmeasurable"]),
      (q1_res["notes"].get("request_contradiction_post_merge"), q1_res.get("unmeasurable")))
q1_half_old = run(q1, "half_old", end=D1, dev=OLD) if OLD else None
q1_old = run(q1, "resume_old", start=D2, cp_in=q1_half_old["cp_path"], dev=OLD) if q1_half_old and q1_half_old.get("rc") == 0 else None
check("[Q1.2] RED CONTROL: the archived pre-R15 v6 resumes the same checkpoint to CLEAN, CLEAN — the merge-created contradiction is invisible",
      q1_old is None or q1_old.get("category") == ["CLEAN", "CLEAN"], q1_old and q1_old.get("category"))
TABLE.append(("Q1 merge-created contradiction", q1_res.get("category"), "pre-R15 CLEAN,CLEAN"))

# ───────────────────────────── [Q2a] brand-new rid, late ─────────────────────────────
print("\n[Q2a] a BRAND-NEW rid (not in the checkpoint) whose hard facts are backdated before the carried prefix — a late fact with NO new readback")
q2a = fixture("q2a_new_rid", {
    D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order_row(1, cq=0, terminal=False, final=False, cap=100, rid="r1")]},   # carried explains read 1
    D2: {"orders": [order_row(1, cq=3, terminal=False, final=False, cap=100, rid="r2", snap_k=1)]}})                                    # NEW rid r2, floor 3 at t1
q2a_half = run(q2a, "half", end=D1); q2a_res = run(q2a, "resume", start=D2, cp_in=q2a_half["cp_path"])
check("[Q2a.0] the carried reading of 1 is rebuilt out: r2's floor of 3 makes it infeasible ⇒ distance 2, FLAGGED, excluded",
      q2a_res["rc"] == 0 and q2a_res["category"] == ["FLAGGED"] and q2a_res["distance"] == [2] and q2a_res["excluded_k"] == [1], (q2a_res.get("category"), q2a_res.get("distance"), q2a_res.get("excluded_k")))
check("[Q2a.1] the rebuild is recorded and the ORIGINAL receipt is preserved (§1d.3)", q2a_res["late_rebuilds"] == ["AAA"] and q2a_res["records_before"] == ["AAA"], (q2a_res["late_rebuilds"], q2a_res["records_before"]))
q2a_half_old = run(q2a, "half_old", end=D1, dev=OLD) if OLD else None
q2a_old = run(q2a, "resume_old", start=D2, cp_in=q2a_half_old["cp_path"], dev=OLD) if q2a_half_old and q2a_half_old.get("rc") == 0 else None
check("[Q2a.2] RED CONTROL: the archived pre-R15 v6 resumes to CLEAN with no rebuild — a new rid's late facts never triggered one",
      q2a_old is None or (q2a_old.get("category") == ["CLEAN"] and not q2a_old.get("late_rebuilds")), q2a_old and (q2a_old.get("category"), q2a_old.get("late_rebuilds")))
TABLE.append(("Q2a new-rid backdated fact", q2a_res.get("category"), "pre-R15 CLEAN"))

# ───────────────────────────── [Q2b] late fill ─────────────────────────────
print("\n[Q2b] a late FILL (backdated before the carried prefix) with NO new readback — attributed after the τ computation, so v6 never saw it")
q2b = fixture("q2b_late_fill", {
    D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order_row(1, cq=0, terminal=False, final=False, cap=100, rid="r1")]},
    D2: {"fills": [fill_row(BASE + 14405, qty=5, tid="late1")]}})                                                                      # 5 lots filled before t1
q2b_half = run(q2b, "half", end=D1); q2b_res = run(q2b, "resume", start=D2, cp_in=q2b_half["cp_path"])
check("[Q2b.0] the carried reading of 1 is rebuilt out: 5 lots were already filled ⇒ distance 4, FLAGGED, excluded",
      q2b_res["rc"] == 0 and q2b_res["category"] == ["FLAGGED"] and q2b_res["distance"] == [4] and q2b_res["excluded_k"] == [1], (q2b_res.get("category"), q2b_res.get("distance"), q2b_res.get("excluded_k")))
check("[Q2b.1] the rebuild is recorded and the original receipt preserved", q2b_res["late_rebuilds"] == ["AAA"] and q2b_res["records_before"] == ["AAA"], (q2b_res["late_rebuilds"], q2b_res["records_before"]))
q2b_half_old = run(q2b, "half_old", end=D1, dev=OLD) if OLD else None
q2b_old = run(q2b, "resume_old", start=D2, cp_in=q2b_half_old["cp_path"], dev=OLD) if q2b_half_old and q2b_half_old.get("rc") == 0 else None
check("[Q2b.2] RED CONTROL: the archived pre-R15 v6 resumes to CLEAN with no rebuild — the late fill is silently absorbed",
      q2b_old is None or (q2b_old.get("category") == ["CLEAN"] and not q2b_old.get("late_rebuilds")), q2b_old and (q2b_old.get("category"), q2b_old.get("late_rebuilds")))
TABLE.append(("Q2b late fill, no new read", q2b_res.get("category"), "pre-R15 CLEAN"))

# ───────────────────────────── [Q2c] control: consistent late fill ─────────────────────────────
print("\n[Q2c] CONTROL: a CONSISTENT late fill (matches the reading) must stay CLEAN and — order independence — reproduce the uninterrupted state exactly")
q2c = fixture("q2c_ok_late_fill", {
    D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order_row(1, cq=0, terminal=False, final=False, cap=100, rid="r1")]},
    D2: {"fills": [fill_row(BASE + 14405, qty=1, tid="ok1")]}})                                                                        # 1 lot filled == the reading
q2c_full = run(q2c, "full"); q2c_half = run(q2c, "half", end=D1); q2c_res = run(q2c, "resume", start=D2, cp_in=q2c_half["cp_path"])
check("[Q2c.0] the consistent late fill stays CLEAN and is not excluded (the fix does not over-fire into a spurious FLAG)",
      q2c_res["rc"] == 0 and q2c_res["category"] == ["CLEAN"] and q2c_res["excluded_k"] == [], (q2c_res.get("category"), q2c_res.get("excluded_k")))
check("[Q2c.1] ORDER INDEPENDENCE: the resumed material-state sha equals the uninterrupted full-window one (the rebuild reproduced, it did not distort)",
      q2c_full["rc"] == 0 and q2c_res["state_sha256"] == q2c_full["state_sha256"], (q2c_res.get("state_sha256"), q2c_full.get("state_sha256")))
TABLE.append(("Q2c consistent late fill", q2c_res.get("category"), "parity " + str(q2c_res.get("state_sha256") == q2c_full.get("state_sha256"))))

# ───────────────────────────── [Q3] load-time hash verification ─────────────────────────────
print("\n[Q3] a checkpoint whose per-symbol state was edited WITHOUT re-hashing must be REFUSED on load — the hash is now a guard, not a label")
q3 = fixture("q3_tamper", {D1: {"position_readback": [rb(0, 0), rb(1, 1), rb(2, 1)], "orders": [order_row(1, cq=0, terminal=False, final=False, cap=100)]},
                           D2: {"position_readback": [rb(6, 1)]}})
q3_half = run(q3, "half", end=D1); _clean_cp = q3_half["cp_path"]


def tampered(mut):
    j = json.load(open(_clean_cp)); mut(j)
    p = os.path.join(ROOT, "q3_tamper", "cp_" + str(len(TABLE)) + "_" + hashlib.sha1(json.dumps(j, default=str).encode()).hexdigest()[:8] + ".json")
    json.dump(j, open(p, "w"), indent=1, default=str); return p


check("[Q3.0] GREEN CONTROL: the untampered checkpoint resumes normally (the guard does not refuse a valid checkpoint)",
      run(q3, "resume_clean", start=D2, cp_in=_clean_cp)["rc"] == 0)
_t_rec = tampered(lambda j: j["symbols"]["AAA"]["records"].__setitem__(-1, {**j["symbols"]["AAA"]["records"][-1], "distance_lots": 999}))
_r_rec = run(q3, "resume_trec", start=D2, cp_in=_t_rec, expect_fail=True)
check("[Q3.1] editing an original RECORD (distance_lots) without re-hashing is refused by name", _r_rec["rc"] != 0 and "state_sha256 mismatch" in _r_rec["err"], (_r_rec["rc"], _r_rec["err"][-160:]))
_t_mk = tampered(lambda j: j["symbols"]["AAA"].__setitem__("marks", [[BASE, 999.0]]))
check("[Q3.2] editing the price MARKS (the USD verdict rests on them) without re-hashing is refused",
      run(q3, "resume_tmk", start=D2, cp_in=_t_mk, expect_fail=True)["rc"] != 0)
_t_adm = tampered(lambda j: j["symbols"]["AAA"].__setitem__("admitted", []))
check("[Q3.3] dropping the ADMITTED joint equations without re-hashing is refused (v6 replayed the marginal state silently)",
      run(q3, "resume_tadm", start=D2, cp_in=_t_adm, expect_fail=True)["rc"] != 0)
_t_id = tampered(lambda j: j["identity"].__setitem__("device_sha256", "0" * 64))
_r_id = run(q3, "resume_tid", start=D2, cp_in=_t_id, expect_fail=True)
check("[Q3.4] editing the IDENTITY block without re-hashing is refused by the internal-consistency check", _r_id["rc"] != 0 and "identity_sha256" in _r_id["err"], (_r_id["rc"], _r_id["err"][-160:]))
if OLD:
    _old_clean = run(q3, "half_old", end=D1, dev=OLD)["cp_path"]

    def tampered_old(mut):
        j = json.load(open(_old_clean)); mut(j); p = os.path.join(ROOT, "q3_tamper", "old_" + str(len(TABLE)) + ".json"); json.dump(j, open(p, "w"), indent=1, default=str); return p
    _old_res = run(q3, "resume_old_trec", start=D2, dev=OLD,
                   cp_in=tampered_old(lambda j: j["symbols"]["AAA"]["records"].__setitem__(-1, {**j["symbols"]["AAA"]["records"][-1], "distance_lots": 999})), expect_fail=True)
    check("[Q3.5] RED CONTROL: the archived pre-R15 v6 resumes the SAME tampered checkpoint SILENTLY (rc 0) — the written hash was never verified", _old_res["rc"] == 0, _old_res)
TABLE.append(("Q3 tampered checkpoint refused", "REFUSED x4", "pre-R15 accepts"))

print("\n" + "-" * 110)
for a, b, c in TABLE: print(f"  {a:34s} {str(b):28s} {str(c)}")
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
