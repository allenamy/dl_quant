#!/usr/bin/env python3
"""Behavioural test for q6_shadow.py — round 16, the fifth 'unknown-value-as-identity-element' instance.

DEFECT: `venue_position_notional or 0.0` coerced a MISSING/None (or genuine-zero) position notional to 0.0 → price mark 0 → usd = |distance|*step*0 = 0
→ the `usd > FLAG_USDT` test failed → a REAL non-zero distance was categorised CLEAN instead of MISSING_PRICE. Reachable by construction; latent on the
real ledger (0 of 53,663 post_anchor/flatten readbacks in 0808..0918 have qty!=0 with a missing/zero notional) — a code fragility, not an active defect.
FIX: an absent/non-positive notional is UNKNOWN (None ⇒ no mark fabricated); the observation falls through to MISSING_PRICE, never a silent CLEAN.

Every case drives the REAL CLI. The red control is the archived pre-fix device archive/q6_shadow_v6r15_47bbbd61.py (the R15-complete device, sha256
47bbbd61...), which still fabricates the zero mark, so a pass here is discriminating. Green baselines are asserted first.
Run: python3 tests_q6_notional_r16.py   (exit 0 iff ALL PASS). Requires scipy with milp (HiGHS)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("Q6_DEV") or os.path.join(HERE, "q6_shadow.py")
_OLD_SRC = os.path.join(HERE, "archive", "q6_shadow_v6r15_47bbbd61.py")     # the device just before the R16 notional fix (still has `or 0.0`)
BASE = 1786147200; DAY = "20260808"
ROOT = tempfile.mkdtemp(prefix="q6n16_tests_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []


def _stage_old():
    if not os.path.exists(_OLD_SRC): return None
    d = tempfile.mkdtemp(prefix="q6n16_old_", dir=os.environ.get("TMPDIR") or None)
    shutil.copy(_OLD_SRC, os.path.join(d, "q6old.py"))
    shutil.copytree(os.path.join(HERE, "support"), os.path.join(d, "support"), ignore=shutil.ignore_patterns("__pycache__"))
    return os.path.join(d, "q6old.py")


OLD = _stage_old()


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q, notional="AUTO"):
    """readback; notional='AUTO' ⇒ q*100, a number ⇒ that value, None ⇒ the venue_position_notional key is OMITTED (the 'missing' case)."""
    d = dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol="AAA", venue_position_qty=q, source="exec@post_anchor")
    if notional == "AUTO": d["venue_position_notional"] = q * 100
    elif notional is not None: d["venue_position_notional"] = notional
    return d


def order(cap):
    return dict(anchor_ts=BASE + 14400, submit_ts=BASE + 14400, symbol="AAA", side="buy", cancel_ts=BASE + 14410,
                request_ledger=[dict(client_id="r1", qty=cap, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed")])


def run(name, reads, cap=1, dev=DEV):
    root = os.path.join(ROOT, name); log = os.path.join(root, "state", "live", "pilot_log", DAY); os.makedirs(log, exist_ok=True)
    for f, rows in (("position_readback", reads), ("orders", [order(cap)]), ("fills", []), ("anchors", [])):
        open(os.path.join(log, f + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    filt = os.path.join(root, "f.json"); open(filt, "w").write(json.dumps({"AAA": {"step": 1}}))
    out = os.path.join(root, "o.json")
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=filt, Q6_PROCS="1", Q6_DETAIL="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.path.join(HERE, "support"))
    p = subprocess.run([sys.executable, dev, DAY, DAY, out], capture_output=True, text=True, env=env)
    if p.returncode != 0: return {"rc": p.returncode, "err": (p.stderr + p.stdout)[-400:]}
    r = json.load(open(out)); o = r["detail"]["AAA"]["observations"]
    return {"rc": 0, "cat": [x["category"] for x in o], "dist": [x["distance_lots"] for x in o], "usd": [x.get("usdt") for x in o]}


print(f"device {os.path.basename(DEV)} sha {hashlib.sha256(open(DEV,'rb').read()).hexdigest()[:16]}  |  red control staged: {bool(OLD)}")

print("\n[G] GREEN BASELINES — the fix must not change a correct verdict")
g0 = run("g0_present_flag", [rb(0, 0), rb(1, 5, "AUTO")])          # reading 5, cap-1 BUY explains 1 ⇒ distance 4, priced ⇒ FLAGGED
check("[G0] present notional + distance 4 ⇒ FLAGGED (unchanged)", g0["cat"] == ["FLAGGED"] and g0["dist"] == [4], g0)
g1 = run("g1_present_clean", [rb(0, 0), rb(1, 1, "AUTO")])          # reading 1 fully explained ⇒ distance 0 ⇒ CLEAN
check("[G1] present notional + distance 0 ⇒ CLEAN", g1["cat"] == ["CLEAN"] and g1["dist"] == [0], g1)

print("\n[N] THE FIX — a missing/zero notional is UNKNOWN, never a fabricated zero mark")
n0 = run("n0_missing", [rb(0, 0), rb(1, 5, None)])                  # reading 5, distance 4, NO usable price
check("[N0] MISSING notional + distance 4 ⇒ MISSING_PRICE (was silently CLEAN)", n0["cat"] == ["MISSING_PRICE"] and n0["dist"] == [4] and n0["usd"] == [None], n0)
n1 = run("n1_zero", [rb(0, 0), rb(1, 5, 0)])
check("[N1] ZERO notional + distance 4 ⇒ MISSING_PRICE (a genuine 0 price is not usable either)", n1["cat"] == ["MISSING_PRICE"] and n1["dist"] == [4], n1)
n2 = run("n2_missing_but_clean", [rb(0, 0), rb(1, 1, None)])        # distance 0 ⇒ CLEAN regardless of price (fix must NOT over-fire)
check("[N2] CONTROL: MISSING notional + distance 0 ⇒ CLEAN (no distance, no anomaly — the fix does not over-fire)", n2["cat"] == ["CLEAN"] and n2["dist"] == [0], n2)
n3 = run("n3_earlier_mark", [rb(0, 0), rb(1, 1, "AUTO"), rb(2, 5, None)])   # a real mark exists at t1; t2 missing-notional uses the latest earlier mark
check("[N3] a missing-notional reading with an EARLIER mark available ⇒ FLAGGED via that mark, not MISSING_PRICE",
      n3["cat"][-1] == "FLAGGED" and n3["dist"][-1] == 4, n3)

print("\n[RED] the archived pre-fix device fabricates the zero mark and reports CLEAN")
old0 = run("old_missing", [rb(0, 0), rb(1, 5, None)], dev=OLD) if OLD else None
check("[R0] RED CONTROL: pre-fix device categorises the same missing-notional distance-4 reading CLEAN", old0 is None or old0.get("cat") == ["CLEAN"], old0 and old0.get("cat"))
old1 = run("old_present", [rb(0, 0), rb(1, 5, "AUTO")], dev=OLD) if OLD else None
check("[R1] the pre-fix device agrees with the fixed one where the notional IS present (FLAGGED) — the only change is the missing/zero case",
      old1 is None or old1.get("cat") == ["FLAGGED"], old1 and old1.get("cat"))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
