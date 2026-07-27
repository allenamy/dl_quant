"""0C — turn the self-harm chain from INFERENCE into EVIDENCE (team-lead approved 2026-07-27).

The claim under test: §4-5b's anomalies were produced by OUR OWN unrecorded fills, not by a real
position discrepancy. Everything below runs on `reconcile`, which is a pure function — no
production is re-run, nothing is written to the live tree.

  FORWARD   replay the windows whose fills are missing; do the anomaly names coincide with the
            names whose fills are missing?
  ★ REVERSE the control that makes it evidence rather than coincidence: backfill the missing
            fills FROM THE VENUE'S OWN TRADE RECORD and replay. If the anomalies do not
            disappear (or drop sharply), then "missing fills cause the anomalies" was never
            demonstrated — it was merely consistent with the data.

★ WHY THE REVERSE CONTROL IS NOT OPTIONAL: a forward match alone is satisfied by any factor that
  moves both quantities together. Only removing the proposed cause and watching the effect go
  away distinguishes "this caused it" from "these co-occur". This is the same requirement 0C
  imposes on every widening-direction fix in this project, applied here to 0C's own hypothesis.

Read-only w.r.t. the production tree: the backfill is injected into an IN-MEMORY copy.

★★ STATUS 2026-07-27T15:5xZ — THE REVERSE CONTROL IN THIS FILE IS NOT YET VALID. DO NOT READ ITS
   "NOT DEMONSTRATED" AS A VERDICT ON THE HYPOTHESIS. Diagnosis, from reconcile's own code:

     reconcile windows fills by EXECUTION TIME, not by anchor:
         _win = _between(prev_read_ts, cur_read_ts)      # readback-to-readback
         _between: `for t, sym, f in _exec: if t_lo < t <= t_hi`     # t = the FILL's own time

     this file instead aggregates every trade since the newest anchor onto ONE order row and
     stamps it `anchor_ts + 60`. For the 07-26 flatten (trades 12:17:54-12:18:40Z) that puts
     ~$23k into the window ENDING at the 12:17:30Z readback — the window before the one it
     belongs to. So the backfill manufactures disagreement in window N while still leaving it
     absent from window N+1, and the anomaly count RISES (371 -> 400).

   ⇒ THE FIX: attribute each venue trade individually, carrying ITS OWN timestamp, so it lands in
     the readback window that actually contains it. Not attempted under time pressure — a second
     rushed instrument is how the first wrong answer gets confirmed.
   ⇒ Until then the self-harm chain keeps EXACTLY the status it had: forward evidence only
     (1:1 anchor correspondence + the ladder's cited 77 matching reconcile's 77), causation
     inferred, not demonstrated.

   ★ This is the SECOND time today my own instrument was the defect (the first: this session's
     first-exam checker would have rendered a verdict 26 minutes before the settlement). Both
     were caught before a conclusion was reported, which is the only part that went right.
"""
import json
import glob
import sys
import time
from collections import defaultdict

LOGROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
LIVEDIR = "/Users/haosiyu/dl_quant_live/live"
sys.path.insert(0, LIVEDIR)
import pilot_log as PL          # noqa: E402
import reconcile as RC          # noqa: E402


def load_days():
    return {d: PL.read_day(LOGROOT, d) for d in PL.available_days(LOGROOT)}


def anomalies_by_anchor(days):
    rec = RC.reconcile([(d, days[d]) for d in sorted(days)])
    out = defaultdict(set)
    for a in rec["anomalies"]:
        out[round(float(a["anchor_ts"]))].add(a["symbol"])
    return out, rec


def backfill(days, trades_cache):
    """Replace our `filled_notional` with the VENUE's own SIGNED total per (symbol, anchor).

    ★ SIGNED, AND THAT IS THE WHOLE POINT — my first version summed |qty x px| and guessed the
      sign from `target_w`. `reconcile.signed_fills_by_anchor` documents the convention: buy
      positive, sell negative, and nothing re-applies a sign. An unsigned backfill makes a sold
      position look bought, which manufactures MORE disagreement than it removes — my first run
      showed 371 -> 402 anomalies and I nearly reported the hypothesis refuted by my own
      instrument. The weak point had been flagged in this docstring before the run; flagging it
      is not the same as getting it right.

    ★ REPLACE, not add: the counterfactual being constructed is "what if the ledger recorded
      exactly what the venue did", so the venue's total IS the value. Adding to what is already
      there double-counts the windows that were recorded correctly.
    """
    tr = json.load(open(trades_cache))
    out = {d: {k: [dict(r) for r in v] for k, v in one.items()} for d, one in days.items()}
    rows = [r for d in out for r in out[d].get("orders", [])]
    ats_all = sorted({float(r["anchor_ts"]) for r in rows})
    by_key = {}
    for r in rows:
        by_key.setdefault((r["symbol"], float(r["anchor_ts"])), []).append(r)

    venue_signed = defaultdict(float)
    for sym, v in tr.items():
        for t_ms, qty_signed, px in v:          # qty_signed: + for BUY, - for SELL
            t = t_ms / 1000.0
            cand = [a for a in ats_all if a <= t]
            if cand:
                venue_signed[(sym, max(cand))] += qty_signed * px

    n_set = 0
    for (sym, ats), signed_notional in venue_signed.items():
        rs = by_key.get((sym, ats))
        if not rs:
            continue
        for r in rs[1:]:
            r["filled_notional"] = 0.0
        rs[0]["filled_notional"] = signed_notional
        rs[0]["last_fill_ts"] = rs[0].get("last_fill_ts") or ats + 60
        n_set += 1
    return out, n_set


def main(trades_cache):
    days = load_days()
    print("=== FORWARD: anomalies on the tree as it stands ===")
    before, rec_b = anomalies_by_anchor(days)
    for a in sorted(before):
        print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(a))}  {len(before[a]):4d} names")
    print(f"  total anomalies = {len(rec_b['anomalies'])}")

    if not trades_cache:
        print("\n(no trades cache given — reverse control skipped)")
        return
    print("\n=== REVERSE CONTROL: backfill the venue's own fills, replay ===")
    patched, n_inj = backfill(days, trades_cache)
    print(f"  order rows given a backfilled filled_notional: {n_inj}")
    after, rec_a = anomalies_by_anchor(patched)
    print(f"  {'anchor':16s} {'before':>8s} {'after':>8s}   verdict")
    for a in sorted(set(before) | set(after)):
        b, af = len(before.get(a, ())), len(after.get(a, ()))
        v = "GONE" if af == 0 and b else ("reduced" if af < b else ("unchanged" if af == b else "WORSE"))
        print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(a)):16s} {b:8d} {af:8d}   {v}")
    tb, ta = len(rec_b["anomalies"]), len(rec_a["anomalies"])
    print(f"  TOTAL            {tb:8d} {ta:8d}")
    print()
    if ta <= 0.25 * tb:
        print("  ⇒ SELF-HARM CHAIN DEMONSTRATED: removing the proposed cause removes the effect.")
    elif ta < tb:
        print(f"  ⇒ PARTIAL ({100*(tb-ta)/tb:.0f}% removed). Some anomalies have another cause — "
              f"name them, do not fold them in.")
    else:
        print("  ⇒ NOT DEMONSTRATED. The forward match was coincidence or the attribution rule "
              "above is wrong. The hypothesis does NOT get to keep its status.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
