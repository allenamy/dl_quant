#!/usr/bin/env python3
"""Round 16: the archived pre-fix devices must RUN from where they live and SHOW their bugs — a red control that cannot run is not a red control.

Each archived device does `sys.path.insert(0, HERE/support)` with HERE = its own directory (archive/). So archive/support must exist and provide the
frozen oracle. This test enforces that invariant and, for the two most recent archives, drives them DIRECTLY from archive/ (no staging, NO PYTHONPATH)
so resolution MUST come from archive/support, and asserts they still exhibit the bug they are kept for. If archive/support is missing, or its oracle
drifts from the sha-pinned one, or an archive stops reproducing its bug, this goes red.
Run: python3 tests_q6_archive_runnable.py   (exit 0 iff ALL PASS)."""
import hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 1786147200
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# [A0] archive/support provides the frozen oracle, byte-identical to the real one (a copy that drifts would make a device record a different oracle sha)
real = os.path.join(HERE, "support", "reconcile_carry_409ea16.py")
arch = os.path.join(HERE, "archive", "support", "reconcile_carry_409ea16.py")
check("[A0] archive/support/ oracle exists and is byte-identical to support/ oracle (frozen 409ea16 — no drift)",
      os.path.exists(arch) and sha(arch) == sha(real), (os.path.exists(arch), sha(arch)[:16] if os.path.exists(arch) else None, sha(real)[:16]))


def rb(k, q, notional="AUTO"):
    d = dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol="AAA", venue_position_qty=q, source="exec@post_anchor")
    if notional == "AUTO": d["venue_position_notional"] = q * 100
    elif notional is not None: d["venue_position_notional"] = notional
    return d


def write(root, day, reads, orders=(), fills=()):
    p = os.path.join(root, "state", "live", "pilot_log", day); os.makedirs(p, exist_ok=True)
    for n, rows in (("position_readback", reads), ("orders", orders), ("fills", fills), ("anchors", [])):
        open(os.path.join(p, n + ".jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in rows))


def run_direct(dev, start, end, root, cp_in=None, cp_out=None):
    """invoke archive/<dev> DIRECTLY with NO PYTHONPATH, cwd=HERE, so the device must resolve archive/support itself."""
    out = os.path.join(root, "o_%s_%s.json" % (start, end))
    f = os.path.join(root, "f.json"); open(f, "w").write(json.dumps({"AAA": {"step": 1.0}}))
    env = dict(os.environ, Q6_REPO=root, Q6_FILTERS=f, Q6_PROCS="1", Q6_DETAIL="1")
    env.pop("PYTHONPATH", None); env.pop("Q6_CHECKPOINT_IN", None); env.pop("Q6_CHECKPOINT_OUT", None)
    if cp_in: env["Q6_CHECKPOINT_IN"] = cp_in
    if cp_out: env["Q6_CHECKPOINT_OUT"] = cp_out
    p = subprocess.run([sys.executable, os.path.join("archive", dev), start, end, out], cwd=HERE, capture_output=True, text=True, env=env)
    if p.returncode != 0: return {"rc": p.returncode, "err": (p.stderr + p.stdout)[-400:]}
    r = json.load(open(out)); o = (r.get("detail", {}).get("AAA", {}) or {}).get("observations", [])
    return {"rc": 0, "cat": [x["category"] for x in o]}


# [A1] pre-notional archive runs directly and shows its bug: a missing-notional distance-4 reading is CLEAN (should be MISSING_PRICE)
r1 = tempfile.mkdtemp(prefix="q6ar_notional_", dir=os.environ.get("TMPDIR") or None)
write(r1, "20260808", [rb(0, 0), rb(1, 5, notional=None)],
      orders=[dict(anchor_ts=BASE + 14400, submit_ts=BASE + 14400, symbol="AAA", side="buy", cancel_ts=BASE + 14410,
                   request_ledger=[dict(client_id="r1", qty=1, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed")])])
res1 = run_direct("q6_shadow_v6r15_47bbbd61.py", "20260808", "20260808", r1)
check("[A1] pre-notional archive v6r15_47bbbd61 RUNS directly from archive/ (imports its oracle) and SHOWS its bug (missing notional ⇒ CLEAN)",
      res1.get("rc") == 0 and res1.get("cat") == ["CLEAN"], res1)

# [A2] pre-R16 archive runs directly (half+resume) and shows its bug: a carried unattributed fill's late claim resumes CLEAN (should be UNMEASURABLE)
r2 = tempfile.mkdtemp(prefix="q6ar_unattr_", dir=os.environ.get("TMPDIR") or None)
oA = lambda k, tq=None: dict(anchor_ts=BASE + k * 14400, submit_ts=BASE + k * 14400, symbol="AAA", side="buy", cancel_ts=BASE + k * 14400 + 10,
                             request_ledger=[dict(client_id="A", qty=1, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed", **({"trade_qty": tq} if tq else {}))])
write(r2, "20260808", [rb(0, 0), rb(1, 5)], orders=[oA(1)], fills=[dict(fill_ts=BASE + 100, symbol="AAA", side="BUY", fill_px=100, fill_notional=500, trade_id="fx1")])
write(r2, "20260809", [], orders=[oA(6, tq={"fx1": 5})])
h = run_direct("q6_shadow_v6r16pre_f86bee10.py", "20260808", "20260808", r2, cp_out=os.path.join(r2, "cp.json"))
res2 = run_direct("q6_shadow_v6r16pre_f86bee10.py", "20260809", "20260809", r2, cp_in=os.path.join(r2, "cp.json"))
check("[A2] pre-R16 archive v6r16pre_f86bee10 RUNS directly from archive/ and SHOWS its bug (carried unattributed fill's late claim resumes CLEAN)",
      h.get("rc") == 0 and res2.get("rc") == 0 and res2.get("cat") == ["CLEAN"], (h, res2))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {tempfile.gettempdir()}")
sys.exit(0 if not FAILS else 1)
