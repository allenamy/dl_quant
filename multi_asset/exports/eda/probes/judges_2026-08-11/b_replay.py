"""READ-ONLY design validation for B, run BEFORE any production code changes.

Claim under test: `unauth` in the pre-registered decomposition is ALREADY computed, by
`reconcile` (`residual_qty = q2 - (q1 + sum dq_fills)`), in quantity space at a common mark.
If so, B needs ONE new quantity (`dev` in qty space) and a subtraction — not a second
implementation of unauth, which would be the 'two implementations differing by which convention
they read' family, inside a single stop-loss.

Replay criterion from the prereg: on the 04:00Z anchor, unauth ~ 0 and underfill ~ 1131.
"""
import os, sys, json
R = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(R, "live"))
for d in ("scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(R, d))
os.environ.setdefault("LIVE_MODE", "LIVE")
import pilot_log as PL, reconcile as RC, position_break as PB, state_root as SR

root = SR.state_root("LIVE") if hasattr(SR, "state_root") else os.path.join(R, "state/live")
root = os.path.join(R, "state", "live")
days = sorted(d for d in os.listdir(os.path.join(root, "pilot_log")) if d.isdigit())
print("root:", root, "days:", days)
dd = [(d, PL.read_day(root, d)) for d in days]

rec = RC.reconcile(dd)
print("\n=== reconcile ===")
print("  n_anomalies:", len(rec["anomalies"]), " latest:", len(rec["latest"]))
print("  by kind:", rec.get("n_anomalies_by_kind"))
print("  unreconcilable:", len(rec.get("unreconcilable") or []))
for a in rec["anomalies"][:6]:
    print("   ", a.get("anchor_ts"), a.get("symbol"), a.get("kind"),
          "resid_qty", a.get("residual_qty"), "usdt", a.get("residual_usdt"))

pb = PB.evaluate(dd)
print("\n=== position_break (current, notional space) ===")
for r in pb.get("per_anchor", []):
    if not r.get("judged"):
        continue
    print(f"   {r['anchor_ts']:.0f} {r.get('state'):<10} frac {r.get('break_frac')} "
          f"dev {r.get('total_dev_usdt')} gross {r.get('target_gross')} "
          f"n_int {r.get('n_intended')} trig {r.get('triggered')}")
