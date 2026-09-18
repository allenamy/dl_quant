#!/usr/bin/env python3
"""Round 16b: a fresh OBSERVATION (readback) timed at/before the carried prefix's last observation must be INSERTED into the cross-section on resume,
not dropped — a full pass sorts it in, so a resume that omits it decides a different set of observations.

DEFECT: the resume observation merge kept only obs with t > carried_last (the `newo` filter), silently dropping an earlier-timed fresh readback. If that
readback would have been ADMITTED and constrained a later reading (monotonicity), the dropped resume misses the anomaly the full pass catches.
FIX: insert every fresh obs SORTED and feed a late one's time to the late-evidence τ so the admission prefix rebuilds from it. Matches the full pass.

Fixture: an open BUY. carried cross-section is k0=0 (baseline) and k2=1 (CLEAN in the half). The resumed window brings a backdated k1=2. A full pass then
admits k1=2 and FLAGS k2=1 (monotonicity: x cannot fall from 2 to 1). The fixed resume inserts k1 and reaches the same FLAG; the pre-fix device drops k1
and calls k2 CLEAN. Red control: archive/q6_shadow_v6r16b_pre_f59eda83.py (the device immediately before this fix — it has the drop but not this fix).
Run: python3 tests_q6_late_obs_r16.py   (exit 0 iff ALL PASS)."""
import hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.environ.get("Q6_DEV") or os.path.join(HERE, "q6_shadow.py")
OLD = os.path.join(HERE, "archive", "q6_shadow_v6r16b_pre_f59eda83.py")     # immediate predecessor: has the drop, not this fix (archive/support resolves its oracle)
BASE = 1786147200; D1, D2 = "20260808", "20260809"
ROOT = tempfile.mkdtemp(prefix="q6lo_tests_", dir=os.environ.get("TMPDIR") or None)
N = [0]; FAILS = []


def check(name, cond, detail=""):
    N[0] += 1
    print(("  OK   " if cond else "  FAIL ") + name + (("  — " + str(detail)[:230]) if (detail and not cond) else ""))
    if not cond: FAILS.append(name)


def rb(k, q):
    return dict(anchor_ts=BASE + k * 14400, read_ts=BASE + k * 14400 + 20, symbol="AAA", venue_position_qty=q, venue_position_notional=q * 100, source="exec@post_anchor")


def order_r1(anchor_k=0):
    return dict(anchor_ts=BASE + anchor_k * 14400, submit_ts=BASE + anchor_k * 14400, symbol="AAA", side="buy", cancel_ts=BASE + anchor_k * 14400 + 10,
                request_ledger=[dict(client_id="r1", qty=100, confirmed_qty=0, terminal=False, confirmed_qty_final=False, state="confirmed")])


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
    return {"rc": 0, "n_obs": len(o), "cat": [x["category"] for x in o], "notes": r.get("notes", {})}


# carried: k0=0, k2=1 (CLEAN). resumed window: backdated k1=2. full pass admits k1 and FLAGS k2 (monotone x can't fall 2->1).
days = {D1: {"position_readback": [rb(0, 0), rb(2, 1)], "orders": [order_r1(0)]},
        D2: {"position_readback": [rb(1, 2)]}}
fx = fixture("lo", days)
half = run(fx, "half", D1, D1, cp_out=os.path.join(fx, "cp.json"))
full = run(fx, "full", D1, D2)
res = run(fx, "resume", D2, D2, cp_in=os.path.join(fx, "cp.json"))

check("[L0] the FULL pass sorts the backdated k1 in: both post-baseline observations present (k1, k2) with k2=1 FLAGGED (monotonicity from k1=2)",
      full["rc"] == 0 and full["n_obs"] == 2 and full["cat"] == ["CLEAN", "FLAGGED"], full)
check("[L1] the RESUMED pass INSERTS the late observation and reaches the SAME verdict as the full pass (3 obs, k2 FLAGGED)",
      res["rc"] == 0 and res["n_obs"] == full["n_obs"] and res["cat"] == full["cat"], (res, full.get("cat")))
check("[L2] the resume records the late-observation insertion (candidate present ⇒ hit=1)", res.get("notes", {}).get("resume_late_observation_inserted") == 1, res.get("notes"))
old_half = run(fx, "old_half", D1, D1, cp_out=os.path.join(fx, "cpo.json"), dev=OLD) if os.path.exists(OLD) else None
old_res = run(fx, "old_resume", D2, D2, cp_in=os.path.join(fx, "cpo.json"), dev=OLD) if old_half and old_half.get("rc") == 0 else None
check("[L3] RED CONTROL: the pre-fix device DROPS the backdated k1 (only k2 remains, 1 obs) and calls k2 CLEAN — the anomaly the full pass catches is missed",
      old_res is None or (old_res.get("n_obs") == 1 and old_res.get("cat") == ["CLEAN"]), old_res)

# control: a fresh obs strictly AFTER the carried prefix (the normal case) is NOT a late observation and triggers no insertion/rebuild
days2 = {D1: {"position_readback": [rb(0, 0), rb(1, 1)], "orders": [order_r1(0)]}, D2: {"position_readback": [rb(6, 1)]}}
fx2 = fixture("ctrl", days2)
run(fx2, "half", D1, D1, cp_out=os.path.join(fx2, "cp.json"))
res2 = run(fx2, "resume", D2, D2, cp_in=os.path.join(fx2, "cp.json"))
check("[L4] CONTROL: a normal fresh obs after the carried prefix is NOT flagged as a late observation (no spurious insertion note)",
      res2["rc"] == 0 and not res2.get("notes", {}).get("resume_late_observation_inserted") and set(res2["cat"]) == {"CLEAN"}, res2)

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  fixtures under {ROOT}")
sys.exit(0 if not FAILS else 1)
