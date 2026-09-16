"""LED-04 ruling (a), real-data reproduction (READ-ONLY on the live copy, writes only to its own
scratch): run the FIXED watchdog's §4-4 over a copy of the live pilot_log twice —

  (1) with NO amendment record file, which must reproduce the live `last_eval.json`'s
      `cum_return_from_start_pct` BIT FOR BIT (the change is inert when no record exists), and
  (2) with FX-EXEC2's real 250-record file placed where the apply step puts it,

and report both numbers, the per-transfer-day facts and the difference. The expected shape is
FX-EXEC2's own measurement (receipt LED04_cond4_transfer_day_effect.json on their 14:27Z copy:
-1.3136% recorded vs -1.5749% amended, 0.2613 pp). Two instruments, one quantity — if they disagree
the disagreement is the finding, not the number.

usage: led04_cond4_watchdog_reproduction.py <code_tree> <state_copy_root> <amendments.jsonl> <scratch> [<max_day>]
       state_copy_root holds live/pilot_log and live/watchdog/last_eval.json
"""
import json, os, shutil, sys

CODE, STATE, AMEND, SCRATCH = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
MAX_DAY = sys.argv[5] if len(sys.argv) > 5 else None
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import watchdog as WD                                                # noqa: E402

SRC = os.path.join(STATE, "live", "pilot_log")
ROOT = os.path.join(SCRATCH, "live", "pilot_log")
if os.path.exists(os.path.join(SCRATCH, "live")):
    shutil.rmtree(os.path.join(SCRATCH, "live"))
os.makedirs(os.path.dirname(ROOT), exist_ok=True)
shutil.copytree(SRC, ROOT)
if MAX_DAY:
    for d in sorted(os.listdir(ROOT)):
        if d.isdigit() and d > MAX_DAY:
            shutil.rmtree(os.path.join(ROOT, d))

AM_DIR = os.path.join(SCRATCH, "live", "ledger_amendments")
AM_PATH = os.path.join(AM_DIR, "daily_nav_realised_split.jsonl")


def run():
    ev = WD.evaluate(ROOT, venue_events=[], ops_stats=[])
    c4 = ev.get("conditions", {}).get("cond4_drawdown") or {}
    b = c4.get("realised_amendments") or {}
    return {"cum_return_from_start_pct": c4.get("cum_return_from_start_pct"),
            "max_drawdown_from_peak_pct_INFO": c4.get("max_drawdown_from_peak_pct_INFO"),
            "triggered": c4.get("triggered"), "blind": c4.get("blind"),
            "chain_broken": c4.get("chain_broken"),
            "n_records_loaded": b.get("n_records_loaded"),
            "days_amended": b.get("days_amended"),
            "unamended_prefix_days": b.get("unamended_prefix_days"),
            "transfer_days": [{k: t.get(k) for k in
                               ("day", "status", "source", "recorded_usdt", "usdt",
                                "delta_recorded_minus_amended_usdt", "why")}
                              for t in (b.get("transfer_days") or [])]}


if os.path.exists(AM_PATH):
    os.remove(AM_PATH)
without = run()
os.makedirs(AM_DIR, exist_ok=True)
shutil.copyfile(AMEND, AM_PATH)
with_ = run()

live_cum = None
try:
    live_cum = ((json.load(open(os.path.join(STATE, "live", "watchdog", "last_eval.json")))
                 .get("conditions", {}).get("cond4_drawdown") or {})
                .get("cum_return_from_start_pct"))
except Exception as e:
    live_cum = f"unreadable: {type(e).__name__}"

out = {"code_tree": CODE, "state_copy": STATE, "max_day": MAX_DAY,
       "amendments_file": AMEND, "n_amendment_lines": sum(1 for _ in open(AMEND)),
       "live_last_eval_cum_pct": live_cum,
       "without_records": without, "with_records": with_,
       "reproduces_live_without_records": (without["cum_return_from_start_pct"] == live_cum
                                           if MAX_DAY is None else "N/A (window truncated)"),
       "understatement_pp": (None if None in (without["cum_return_from_start_pct"],
                                              with_["cum_return_from_start_pct"])
                             else round(without["cum_return_from_start_pct"]
                                        - with_["cum_return_from_start_pct"], 4))}
print(json.dumps(out, indent=1, default=str))
