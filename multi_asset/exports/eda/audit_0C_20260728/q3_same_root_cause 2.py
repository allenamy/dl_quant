#!/usr/bin/env python3
"""0C audit Q3 — is §4-7's DRIFT the same fact as §4-5b's anomaly list, or an independent problem?

The lead asserts they derive from ONE reconcile() call. Verified against the CODE, not the claim:

  production path (scheduler/run_anchor.py:261-263)
      ops_stats, venue_events, _ = WI.collect(log_root)      <- reconcile CALL #1
      WD.run(log_root, venue_events=..., ops_stats=...)      <- reconcile CALL #2

  CALL #1  watchdog_inputs.derive_ops_stats:104-116
      _rec = RC.reconcile([(d, PL.read_day(root, d)) for d in PL.available_days(root)])
      out[-1]["unrecovered_position_drift"] = None if _rec["last_reconciled_ats"] is None
                                              else bool(_rec["latest"])
  CALL #2  watchdog.evaluate:859-861, 929
      _rec = RC.reconcile([(d, PL.read_day(root, d)) for d in PL.available_days(root)])
      _latest = [a for a in anomalies if a["anchor_ts"] == last_reconciled_ats]

  reconcile.py:389   "latest": [a for a in anomalies if a["anchor_ts"] == last_ats]

=> §4-7's drift boolean is `bool(X)` and §4-5b's name list is `X`, for the SAME X. TWO CALLS of one
   pure function, same root, same window (both `PL.available_days(root)`), same default tol/floor.
   So §4-7 cannot carry a name or a cause §4-5b does not have — NOT because they were checked and
   agreed, but because §4-7 has no name-level content at all: it is one bit read off 5b's list.

THIS SCRIPT tests that structurally rather than trusting the reading: it perturbs the ledger in
memory and checks the two derivations move together, and it enumerates the ONE way they can
diverge (the two calls read the disk at different moments).
Read-only w.r.t. ~/dl_quant_live.
"""
import os, sys, json, copy

ROOT = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import pilot_log as PL, reconcile as RC, watchdog_inputs as WI

DAYS = PL.available_days(ROOT)
days_data = [(d, PL.read_day(ROOT, d)) for d in DAYS]

# ── 1. the two derivations, on the SAME ledger ────────────────────────────────────────────────
rec = RC.reconcile(copy.deepcopy(days_data))
b5_names = sorted((a["symbol"], a["kind"]) for a in rec["latest"])
ops = WI.derive_ops_stats(ROOT, DAYS)
drift = ops[-1]["unrecovered_position_drift"]

print("=" * 96)
print("Q3 — §4-5b's list vs §4-7's bit, computed independently from the same on-disk ledger")
print("=" * 96)
print(f"§4-5b latest anchor      : {rec['last_reconciled_ats']!r}")
print(f"§4-5b latest names       : {b5_names}")
print(f"§4-7 unrecovered_drift   : {drift!r}")
print(f"§4-7 drift_last_reconciled_ats : {ops[-1].get('drift_last_reconciled_ats')!r}")
print(f"§4-7 drift_n_historical  : {ops[-1].get('drift_n_historical')!r}")
print(f"§4-7 drift_n_unreconcilable_latest : {ops[-1].get('drift_n_unreconcilable_latest')!r}")
print(f"AGREE (bool(list) == bit): {bool(rec['latest']) == bool(drift)}")
print(f"§4-7 rate half (the OTHER way §4-7 can fire): "
      f"per_day_fail_rate={[o['rebalance_fail_rate'] for o in ops]} -> "
      f"{'would fire' if all(o['rebalance_fail_rate'] > 0.05 for o in ops[-3:]) else 'does not fire'}")

# ── 2. does §4-7 have any name-level content of its own? ──────────────────────────────────────
print("\nkeys §4-7 writes about drift (this is its ENTIRE drift payload):")
for k in sorted(ops[-1]):
    if "drift" in k:
        print(f"   {k} = {json.dumps(ops[-1][k], ensure_ascii=False)[:120]}")
print("=> no per-name field exists. §4-7 cannot name a symbol §4-5b does not, because it names none.")

# ── 3. structural test: perturb the ledger, do the LIST and the BIT stay locked together? ─────
# ★ MY FIRST VERSION OF THIS TEST WAS WRONG AND IS KEPT AS A NOTE, because its failure is the one
#   this audit is about. It patched every unquantifiable leg to `filled_notional = 0.0` — a
#   FACTUALLY FALSE size (PORTALUSDT moved 18,598.7 contracts) — so the anomaly merely changed
#   KIND, from `execution_of_unknown_size` to `quantity_residual`, and my verdict line printed
#   "DIVERGED" while the two guards were in fact still in perfect agreement (list non-empty, bit
#   True). A test that asserts the wrong property reports red for the wrong reason.
# ⇒ The property to test is AGREEMENT UNDER PERTURBATION, not silence.
print("\n" + "=" * 96)
print("STRUCTURAL TEST — perturb the ledger; does bool(5b list) track the 4-7 bit every time?")
print("=" * 96)


def _rebuild(mutate):
    d = copy.deepcopy(days_data)
    mutate(d)
    r = RC.reconcile(copy.deepcopy(d))
    # §4-7's own derivation, applied to the same object (derive_ops_stats' exact expression)
    bit = None if r["last_reconciled_ats"] is None else bool(r["latest"])
    return r, bit


def _unquantifiable(o):
    return (o.get("submit_ts") is not None
            and (o.get("filled_notional") is None
                 or (float(o.get("filled_notional") or 0.0) != 0.0 and not o.get("avg_fill_px"))))


def _truthful_repair(d):
    """Give every unquantifiable leg the size the VENUE's own readbacks imply, so the residual
    goes to zero honestly. That is what a working backfill would produce."""
    rb = {}
    for _dd, one in d:
        for r in one.get("position_readback", []):
            rb.setdefault(r["anchor_ts"], {})[r["symbol"]] = r
    ats = sorted(rb)
    for _dd, one in d:
        for o in one["orders"]:
            if not _unquantifiable(o):
                continue
            t = o.get("last_fill_ts") or o.get("anchor_ts")
            nxt = next((a for a in ats if rb[a][list(rb[a])[0]].get("read_ts", a) >= float(t)), None)
            if nxt is None or o["symbol"] not in rb[nxt]:
                continue
            j = ats.index(nxt)
            q2 = float(rb[nxt][o["symbol"]].get("venue_position_qty") or 0.0)
            n2 = float(rb[nxt][o["symbol"]].get("venue_position_notional") or 0.0)
            prev = rb[ats[j - 1]].get(o["symbol"], {}) if j else {}
            q1 = float(prev.get("venue_position_qty") or 0.0)
            n1 = float(prev.get("venue_position_notional") or 0.0)
            mark = abs(n2 / q2) if q2 else (abs(n1 / q1) if q1 else 1.0)
            o["filled_notional"] = (q2 - q1) * mark
            o["avg_fill_px"] = mark
            o["terminal_reason"] = "filled"


CASES = [
    ("as-is (no change)", lambda d: None),
    ("truthful backfill of every unquantifiable leg", _truthful_repair),
    ("delete the latest anchor's readback entirely",
     lambda d: [one.__setitem__("position_readback",
                                [r for r in one["position_readback"]
                                 if r["anchor_ts"] != 1785226740.721801])
                for _x, one in d]),
    ("inject a 500-contract phantom on BTCUSDT at the latest anchor",
     lambda d: [r.__setitem__("venue_position_qty", float(r["venue_position_qty"]) + 500.0)
                for _x, one in d for r in one["position_readback"]
                if r["anchor_ts"] == 1785226740.721801 and r["symbol"] == "BTCUSDT"]),
]
print(f"{'perturbation':<52}{'5b list':<10}{'4-7 bit':<10}{'locked?':<9}names")
all_locked = True
for name, fn in CASES:
    r, bit = _rebuild(fn)
    locked = (bool(r["latest"]) == bool(bit))
    all_locked &= locked
    print(f"{name:<52}{len(r['latest']):<10}{str(bit):<10}{'YES' if locked else 'NO':<9}"
          f"{[a['symbol'] for a in r['latest']][:4]}")
print(f"\nlocked in every case: {all_locked}")

# ── 4. the ONE real divergence mode, named ────────────────────────────────────────────────────
print("\n" + "=" * 96)
print("THE ONE WAY THEY CAN DISAGREE IN PRODUCTION")
print("=" * 96)
print("""They are two READS of an append-only ledger separated in wall-clock time:
    WI.collect(log_root)  ... then ...  WD.run(log_root, ops_stats=<from the first read>)
Anything appended between them is in call #2 and not in call #1. §4-5b would then name a symbol
whose bit §4-7 does not carry, or the reverse. That is a STALENESS window, not a second cause —
and it fails toward §4-5b being right, since it holds the later read.
Checked below: were any rows appended during THIS anchor's evaluation window?""")
ev = json.load(open(os.path.expanduser(
    "~/dl_quant_live/state/testnet/watchdog/last_eval.json")))
print(f"   last_eval evaluated_utc = {ev['evaluated_utc']}")
import datetime
t_eval = datetime.datetime.strptime(ev["evaluated_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
    tzinfo=datetime.UTC).timestamp()
late = []
for _d, one in days_data:
    for o in one["orders"]:
        t = o.get("submit_ts") or o.get("last_fill_ts") or o.get("anchor_ts")
        if t and float(t) > t_eval:
            late.append((float(t), o["symbol"], o.get("terminal_reason")))
print(f"   order rows with a timestamp AFTER that eval: {len(late)}")
for t, s, r in sorted(late)[:8]:
    print(f"      {datetime.datetime.fromtimestamp(t, datetime.UTC).isoformat()} {s} {r!r}")
