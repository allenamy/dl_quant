#!/usr/bin/env python3
"""Behavioural test for q6_shadow.py — round 16: a carried UNATTRIBUTED fill whose owning request is only DETERMINED LATER.

DEFECT (reviewer, reproduced through the complete entry point with clean inputs): a fill that is UNATTRIBUTED when the checkpoint is written, and
whose request A's claim arrives in the resumed window, was never moved out of the unattributed set on resume and never consumed A's capacity. A full
recompute flags the over-capacity (A floor > cap ⇒ UNMEASURABLE); the buggy resume leaves the fill floating in U_k and reads CLEAN.
FIX: carried unattributed fills are RE-OFFERED to `attribute_fills` over the MERGED request set on resume (attribute_fills is the sole producer of
attribution state, on resume as in a fresh build); a fill that MOVES onto a request consumes its capacity and, if its event time precedes the carried
prefix, feeds the late-evidence τ so the prefix is rebuilt.

Every case drives the REAL CLI. Red control: the archived pre-R16 device archive/q6_shadow_v6r16pre_f86bee10.py, which still leaves the fill floating.
Run: python3 tests_q6_unattributed_r16.py   (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("Q6_DEV") or os.path.join(HERE, "q6_shadow.py")
_OLD_SRC = os.path.join(HERE, "archive", "q6_shadow_v6r16pre_f86bee10.py")
BASE = 1786147200; D1, D2 = "20260808", "20260809"
ROOT = tempfile.mkdtemp(prefix="q6u16_tests_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []


def _stage_old():
    if not os.path.exists(_OLD_SRC): return None
    d = tempfile.mkdtemp(prefix="q6u16_old_", dir=os.environ.get("TMPDIR") or None)
    shutil.copy(_OLD_SRC, os.path.join(d, "q6old.py"))
    shutil.copytree(os.path.join(HERE, "support"), os.path.join(d, "support"), ignore=shutil.ignore_patterns("__pycache__"))
    return os.path.join(d, "q6old.py")


OLD = _stage_old()


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol="AAA", venue_position_qty=q, venue_position_notional=q * 100, source="exec@post_anchor")


def fill(ts, qty, tid, side="BUY"):
    return dict(fill_ts=ts, symbol="AAA", side=side, fill_px=100, fill_notional=qty * 100, trade_id=tid)


def order_A(anchor_k, trade_qty=None, cap=1):
    e = dict(client_id="A", qty=cap, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed")
    if trade_qty is not None: e["trade_qty"] = trade_qty
    return dict(anchor_ts=BASE + anchor_k * 14400, submit_ts=BASE + anchor_k * 14400, symbol="AAA", side="buy", cancel_ts=BASE + anchor_k * 14400 + 10, request_ledger=[e])


def fixture(name, days):
    root = os.path.join(ROOT, name)
    for d, data in days.items():
        p = os.path.join(root, "state", "live", "pilot_log", d); os.makedirs(p, exist_ok=True)
        for n in ("orders", "position_readback", "fills", "anchors"):
            open(os.path.join(p, n + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in data.get(n, [])))
    return root


def run(root, tag, start, end, cp_in=None, cp_out=None, dev=DEV):
    out = os.path.join(root, tag + ".json")
    f = os.path.join(root, tag + "_f.json"); open(f, "w").write(json.dumps({"AAA": {"step": 1.0}}))
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=f, Q6_PROCS="1", Q6_DETAIL="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.path.join(HERE, "support"))
    env.pop("Q6_CHECKPOINT_IN", None); env.pop("Q6_CHECKPOINT_OUT", None)
    if cp_in: env["Q6_CHECKPOINT_IN"] = cp_in
    if cp_out: env["Q6_CHECKPOINT_OUT"] = cp_out
    p = subprocess.run([sys.executable, dev, start, end, out], capture_output=True, text=True, env=env)
    if p.returncode != 0: return {"rc": p.returncode, "err": (p.stderr + p.stdout)[-500:]}
    r = json.load(open(out)); o = (r.get("detail", {}).get("AAA", {}) or {}).get("observations", [])
    st = None
    if cp_out and os.path.exists(cp_out): st = json.load(open(cp_out)).get("state_sha256")
    return {"rc": 0, "cat": [x["category"] for x in o], "notes": r.get("notes", {}), "state_sha": st,
            "unmeas": [u.get("why") for u in r.get("unmeasurable", [])]}


print(f"device {os.path.basename(DEV)} sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}  |  red control staged: {bool(OLD)}")

# ── the defect fixture: F (BUY 5, fx1) at BASE+100 is unattributed in window 1 (born before A); A (BUY cap1) claims it in window 2 via trade_qty ──
print("\n[U] a carried UNATTRIBUTED fill whose owner A is determined in the resumed window ⇒ it must move onto A and blow A's capacity")
dfx = {D1: {"position_readback": [rb(0, 0), rb(1, 5)], "orders": [order_A(1)], "fills": [fill(BASE + 100, 5, "fx1")]},
       D2: {"orders": [order_A(6, trade_qty={"fx1": 5})]}}
u = fixture("u16", dfx)
half = run(u, "half", D1, D1, cp_out=os.path.join(u, "cp.json"))
full = run(u, "full", D1, D2, cp_out=os.path.join(u, "cpfull.json"))
res = run(u, "resume", D2, D2, cp_in=os.path.join(u, "cp.json"), cp_out=os.path.join(u, "cpres.json"))
check("[U0] window 1 is CLEAN and the fill is unattributed (fills_unattributed=1) — nothing claims it yet", half["cat"] == ["CLEAN"] and half["notes"].get("fills_unattributed") == 1, (half.get("cat"), half.get("notes", {}).get("fills_unattributed")))
check("[U1] the FULL-window recompute flags it UNMEASURABLE (A's floor 5 exceeds cap 1)",
      full["cat"] == ["UNMEASURABLE"] and any("exceeds capacity 1" in (w or "") for w in full["unmeas"]), (full.get("cat"), full.get("unmeas")))
check("[U2] the RESUMED run reaches the SAME verdict as the full recompute — the carried unattributed fill moved onto A and consumed its capacity",
      res["cat"] == full["cat"] and res["cat"] == ["UNMEASURABLE"], (res.get("cat"), full.get("cat")))
check("[U3] the resume records that a previously-unattributed fill moved, and the merge-created over-capacity was caught",
      res["notes"].get("resume_unattributed_fill_now_attributed") == 1 and res["notes"].get("request_contradiction_post_merge") == 1, res.get("notes"))
oldhalf = run(u, "oldhalf", D1, D1, cp_out=os.path.join(u, "cpold.json"), dev=OLD) if OLD else None
oldres = run(u, "oldresume", D2, D2, cp_in=os.path.join(u, "cpold.json"), dev=OLD) if oldhalf and oldhalf.get("rc") == 0 else None
check("[U4] RED CONTROL: the archived pre-R16 device leaves the fill floating in U_k and resumes CLEAN", oldres is None or oldres.get("cat") == ["CLEAN"], oldres and oldres.get("cat"))

# ── control: a carried unattributed fill that NOBODY claims must STAY unattributed — no spurious rebuild, resume == single-pass ──
print("\n[C] CONTROL: an unclaimed carried unattributed fill stays unattributed on resume (no over-fire, restart parity preserved)")
cfx = {D1: {"position_readback": [rb(0, 0), rb(1, 5)], "fills": [fill(BASE + 100, 5, "fx1")]},          # F unattributed, no request at all
       D2: {"position_readback": [rb(6, 5)]}}                                                          # later reading, still no owner for F
c = fixture("c16", cfx)
c_half = run(c, "half", D1, D1, cp_out=os.path.join(c, "cp.json"))
c_full = run(c, "full", D1, D2, cp_out=os.path.join(c, "cpfull.json"))
c_res = run(c, "resume", D2, D2, cp_in=os.path.join(c, "cp.json"), cp_out=os.path.join(c, "cpres.json"))
check("[C0] the unclaimed fill stays unattributed and both passes stay CLEAN", c_full["cat"] == c_res["cat"] and set(c_res["cat"]) == {"CLEAN"}, (c_full.get("cat"), c_res.get("cat")))
check("[C1] no spurious late-evidence rebuild fired (the fill did not move)", not c_res["notes"].get("resume_unattributed_fill_now_attributed") and not c_res["notes"].get("resume_prefix_rebuilt_by_late_evidence"), c_res.get("notes"))
check("[C2] restart parity holds: the resumed material-state sha equals the uninterrupted one (re-offering did not distort a fill nobody claims)",
      c_res["state_sha"] is not None and c_res["state_sha"] == c_full["state_sha"], (c_res.get("state_sha"), c_full.get("state_sha")))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
