#!/usr/bin/env python3
"""leverage_budget_table — R10-A01 decision table for the user: with the EXISTING leverage policy, does a BTC leg of +h x NAV
cross any line, and what would each candidate value of beta_overlay.max_combined_leverage do to it? Arithmetic only (no
market data, no returns). Reads the numbers from the executor checkout at a given commit (never typed here):
  target_leverage / external_book.gross_mult (config/book.json), LEVERAGE_ALERT_MULT / LEVERAGE_HALT_MULT (live/watchdog.py).
Assumption stated per row: the leg ADDS gross (the book's own BTC component is ~0.2% of gross, so |b + h| ~ |h|).
usage: /usr/bin/python3 leverage_budget_table.py <executor_checkout> <commit> <out_json>"""
import json, re, subprocess, sys
root, commit, out = sys.argv[1:4]
show = lambda rel: subprocess.check_output(["git", "-C", root, "show", f"{commit}:{rel}"]).decode()
cfg = json.loads(show("config/book.json"))
wd = show("live/watchdog.py")
m = re.search(r"^LEVERAGE_ALERT_MULT, LEVERAGE_HALT_MULT = ([0-9.]+), ([0-9.]+)\s*$", wd, re.M)
alert_mult, halt_mult = float(m.group(1)), float(m.group(2))
tgt = float(cfg["target_leverage"]); gm = float(cfg["external_book"]["gross_mult"])
alert, halt = tgt * alert_mult, tgt * halt_mult
H = [0.1, 0.2, 0.3, 0.38, 1.0, 5.0]
H_NOTE = {0.1: "asked", 0.2: "asked", 0.3: "asked", 0.38: "prereg ex-ante beta -0.19 of gross x 2.0 (upper end of 2026)",
          1.0: "3x-NAV line reached", 5.0: "the review's legal stress input (7x NAV)"}
BUD = [None, 2.0, 2.2, 2.3, 2.5, 3.0, 5.0]
rows = []
for h in H:
    comb = gm + h
    r = {"hedge_nav": h, "note": H_NOTE[h], "combined_leverage": round(comb, 4),
         "old_gate_reads": gm, "old_alert": gm > alert, "old_halt": gm > halt,
         "new_gate_reads": round(comb, 4), "new_alert": comb > alert, "new_halt": comb > halt, "by_budget": {}}
    for b in BUD:
        if b is None:
            r["by_budget"]["unset"] = {"placed_nav": 0.0, "gap_nav": h, "note": "leg refused (budget_unset), HIGH"}
            continue
        room = max(b, gm) - gm
        placed = min(h, room)
        r["by_budget"][f"{b:g}"] = {"placed_nav": round(placed, 4), "gap_nav": round(h - placed, 4),
                                    "combined_leverage": round(gm + placed, 4), "truncated": placed < h}
    rows.append(r)
res = {"device": "leverage_budget_table.py", "executor_commit": commit, "target_leverage": tgt, "gross_mult": gm,
       "alert_mult": alert_mult, "halt_mult": halt_mult, "alert_above_x_nav": alert, "halt_above_x_nav": halt,
       "rows": rows}
json.dump(res, open(out, "w"), indent=1)
print(f"target_leverage {tgt} (external gross_mult {gm}); cond4b alert > {alert:g}x, halt > {halt:g}x (watchdog {alert_mult} / {halt_mult})")
print("hedge(xNAV) | combined | today's gate reads | new gate alert? halt? | placed leg (xNAV) under budget = unset / 2.0 / 2.2 / 2.3 / 2.5 / 3.0 / 5.0")
for r in rows:
    pb = " / ".join(f"{v['placed_nav']:g}" for v in r["by_budget"].values())
    print(f"{r['hedge_nav']:>5g} | {r['combined_leverage']:>5g}x | {r['old_gate_reads']:g}x (never alerts) | "
          f"{'ALERT' if r['new_alert'] else 'no'} / {'HALT' if r['new_halt'] else 'no'} | {pb}   ({r['note']})")
