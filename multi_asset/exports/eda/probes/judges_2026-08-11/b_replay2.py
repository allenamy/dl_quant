"""READ-ONLY design validation for B. root = the pilot_log dir itself (read_day joins day to it)."""
import os, sys, datetime as dt
R = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(R, "live"))
for d in ("scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(R, d))
os.environ.setdefault("LIVE_MODE", "LIVE")
import pilot_log as PL, reconcile as RC, position_break as PB

root = os.path.join(R, "state", "live", "pilot_log")
days = PL.available_days(root)
dd = [(d, PL.read_day(root, d)) for d in days]
print("days:", days, {d: len(o["orders"]) for d, o in dd})

rec = RC.reconcile(dd)
print("\n=== reconcile (already quantity-space, common mark) ===")
print("  n_anomalies:", len(rec["anomalies"]), "  latest:", len(rec["latest"]),
      "  by kind:", rec.get("n_anomalies_by_kind"),
      "  unreconcilable:", len(rec.get("unreconcilable") or []))

pb = PB.evaluate(dd)
print("\n=== position_break (current: NOTIONAL space, undecomposed) ===")
for r in pb["per_anchor"]:
    ts = dt.datetime.fromtimestamp(r["anchor_ts"], dt.timezone.utc).strftime("%m-%d %H:%MZ")
    if not r.get("judged"):
        print(f"  {ts}  NOT JUDGED  {r.get('state')}")
        continue
    print(f"  {ts}  {r.get('state'):<8} break {r.get('break_frac') or r.get('frac')}  "
          f"dev {r.get('total_dev_usdt')}  gross {round(r.get('target_gross') or 0,1)}  "
          f"triggered {r.get('triggered')}")
print("\n  verdict:", pb["state"], " triggered:", pb["triggered"])
