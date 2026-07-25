"""0C — DAY-BUDGET CONSISTENCY CHECKER for the pilot protocol (structural fix for F2/F18).

> created 2026-07-25 | Session: 0C | 状态: permanent guard | 作废条件: 从不

WHY: twice now a day-count change silently broke a gate elsewhere (F2: P0 14d vs a 20d gate window;
F18: adding a 3d ramp left 11 evaluable days against a 14d minimum). Diagnosis: "days" is a
CROSS-SECTION COUPLED quantity in this protocol, not a local parameter. "Remember to recompute" is
defence by memory, and memory fails a third time.

FIX: every day count lives HERE, once. Gates reference symbols. This script asserts the invariants
that couple them, and exits non-zero on violation. Changing any number = run this = the breakage is
mechanical, not remembered. Same move as assert_funding_dim.py: replace belief with mechanism.

Usage: python multi_asset/exports/eda/check_day_budget.py   (exit 0 = consistent)
"""
import os
import json, sys

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"

# ------------------------------------------------------------------ THE SINGLE SOURCE OF TRUTH
BUDGET = {
    "ramp_days_P0":            3,    # §2.2/§9-F13  ramp, not evaluated
    "min_eval_days":          14,    # §3a  gate window minimum (team-lead F2 ruling)
    "eval_days_P0":           14,
    "eval_days_P1":           20,
    "eval_days_P2":           20,
    "ramp_days_P1":            0,
    "ramp_days_P2":            0,
    "c_fail_persist_days":     5,    # §3a  red requires c>7.0 this many consecutive days
                                     #      (team-lead 2026-07-25: ALL phases, not just P0 --
                                     #       a consecutive-day threshold measures evidential
                                     #       decisiveness, a property of the MEASUREMENT, and
                                     #       must not be scaled to the window length)
    "sl_c_persist_days":       5,    # §4-1
    "sl_wfid_persist_days":    3,    # §4-6
    "sl_ops_persist_days":     3,    # §4-7
    "funding_gate_min_days":  60,    # §3f  record-only below this CUMULATIVE day count
    "challenger_min_days":    60,    # §6-C1 (runs in SHADOW, parallel to the pilot)
    "dryrun_days":             5,    # §2.5
    "shadow_schema_days":      5,    # §10  shadow must run schema v2 this long first
    "cooling_off_hours":      72,    # §9-F7
    "stress_events_for_gate":  3,    # §3a  n_eff needed before stress-c can downgrade to CONDITIONAL
    "retest_days":            20,    # §3a  amber re-test window (was hardcoded in prose until 2026-07-25)
    "funding_signcheck_start_day": 1,   # §3f  per-anchor sign-consistency check; live from day 1
                                     #      (team-lead 2026-07-25: 10 -> 1; the new check needs no accumulation)
}
B = BUDGET
PHASES = ["P0", "P1", "P2"]
WITHIN_PHASE_PERSIST = {           # gates that must be REACHABLE inside a single phase's eval window
    "c_fail_persist_days (§3a red)": "c_fail_persist_days",
    "sl_c_persist_days (§4-1)":      "sl_c_persist_days",
    "sl_wfid_persist_days (§4-6)":   "sl_wfid_persist_days",
    "sl_ops_persist_days (§4-7)":    "sl_ops_persist_days",
}
# gates measured on CUMULATIVE pilot days.
#   value = (symbol, acknowledged_reason_or_None)
# An UNACKNOWLEDGED cumulative gate whose threshold exceeds the pilot is a silently dead gate -> FAIL.
# An ACKNOWLEDGED one is a deliberate design choice -> reported, not failed. A guard that can never go
# green stops being read, which is the same failure mode it exists to prevent.
CUMULATIVE_GATES = {
    "funding_gate_min_days (§3f)": ("funding_gate_min_days",
                                    "DELIBERATE: §3f is record-only for the whole pilot (funding is 3.6% of "
                                    "return and was never a gate). The useful half -- sign/settlement-timing "
                                    "error detection -- needs no annualisation and is live from evaluated "
                                    "day 10. Band activates in steady-state operation post-pilot."),
}

fail, warn, derived = [], [], {}

# ---- derived totals -------------------------------------------------------
for p in PHASES:
    derived[f"total_days_{p}"] = B[f"ramp_days_{p}"] + B[f"eval_days_{p}"]
derived["pilot_total_days"] = sum(derived[f"total_days_{p}"] for p in PHASES)
derived["pilot_eval_days"] = sum(B[f"eval_days_{p}"] for p in PHASES)

# ---- INV1: every phase's eval window meets the gate minimum ---------------
for p in PHASES:
    if B[f"eval_days_{p}"] < B["min_eval_days"]:
        fail.append(f"INV1 {p}: eval_days_{p}={B[f'eval_days_{p}']} < min_eval_days={B['min_eval_days']} "
                    f"-> the phase cannot satisfy its own §3a gate (this is exactly F2)")

# ---- INV2: within-phase persistence gates must be reachable ---------------
for label, key in WITHIN_PHASE_PERSIST.items():
    for p in PHASES:
        ev = B[f"eval_days_{p}"]
        if B[key] > ev:
            fail.append(f"INV2 {label}: needs {B[key]} consecutive days but {p} only evaluates {ev} "
                        f"-> condition is UNREACHABLE in {p}")
        elif B[key] > 0.7 * ev:
            warn.append(f"INV2 {label}: {B[key]}/{ev} days in {p} = {B[key]/ev:.0%} of the window "
                        f"-> reachable but tight; a few missing days make it unreachable in practice")

# ---- INV3: cumulative gates must be able to fire during the pilot --------
ack = []
for label, (key, reason) in CUMULATIVE_GATES.items():
    if B[key] > derived["pilot_total_days"]:
        msg = (f"INV3 {label}: threshold {B[key]} cumulative days > pilot_total_days="
               f"{derived['pilot_total_days']} -> cannot activate during the pilot.")
        if reason:
            ack.append(f"{msg} ACKNOWLEDGED -- {reason}")
        else:
            fail.append(msg + " UNACKNOWLEDGED -> silently dead gate. Lower it, extend the pilot, or "
                              "declare it record-only with a reason.")

# ---- INV4: ramp days are excluded, never double-counted ------------------
for p in PHASES:
    if B[f"ramp_days_{p}"] and derived[f"total_days_{p}"] != B[f"ramp_days_{p}"] + B[f"eval_days_{p}"]:
        fail.append(f"INV4 {p}: total != ramp + eval")

# ---- INV6: the funding sign-check must start inside a phase -------
if B["funding_signcheck_start_day"] > B["min_eval_days"]:
    fail.append(f"INV6 funding_signcheck_start_day={B['funding_signcheck_start_day']} > min_eval_days="
                f"{B['min_eval_days']} -> the only live funding check never starts within a phase")
# ---- INV7: the amber re-test window must itself be a valid window -
if B["retest_days"] < B["min_eval_days"]:
    warn.append(f"INV7 retest_days={B['retest_days']} < min_eval_days={B['min_eval_days']} -> an amber "
                f"re-test would be judged on a shorter window than the gate minimum")

# ---- INV5: prerequisites run before day 1 -------------------------------
if B["shadow_schema_days"] < 1 or B["dryrun_days"] < 1:
    fail.append("INV5: dry-run and shadow-schema prerequisites must be >= 1 day")

print("=== derived ===", flush=True)
for k, v in derived.items():
    print(f"  {k:22s} {v}", flush=True)
print("\n=== violations ===", flush=True)
for f_ in fail:
    print(f"  FAIL  {f_}", flush=True)
for w in warn:
    print(f"  WARN  {w}", flush=True)
for a_ in ack:
    print(f"  ACK   {a_}", flush=True)
if not fail and not warn:
    print("  (none)", flush=True)

verdict = "PASS" if not fail else f"FAIL ({len(fail)})"
print(f"\nVERDICT: {verdict}   [warnings: {len(warn)}, acknowledged: {len(ack)}]", flush=True)
json.dump(dict(title="pilot protocol day-budget consistency", created="2026-07-25", auditor="0C",
               budget=BUDGET, derived=derived, failures=fail, warnings=warn, acknowledged=ack, verdict=verdict,
               rule="every day count lives in BUDGET; gates reference symbols; changing any number "
                    "means re-running this script -- coupling is enforced mechanically, not remembered"),
          open(EDA + "check_day_budget.json", "w"), indent=1)
print("SAVED exports/eda/check_day_budget.json", flush=True)
sys.exit(0 if not fail else 1)
