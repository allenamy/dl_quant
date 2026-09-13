"""W8 regression: replay the independent reviewer's OWN counterexamples (0158f5d1) through THEIR
harness (`probe_followup.pure`, AST-extracted pure functions, no business imports) against the
FIXED reconcile.py. Their expected-failure outcomes must now be the corrected ones, and their real
positive control must be untouched."""
import copy, json, runpy, sys
from pathlib import Path

B = Path("/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907"
         "/multi_asset/exports/research/codex_followup_code_review_2026-09-13/incident")
TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/Users/haosiyu/cc_tmp/w8_ledger_fe97e46/live/reconcile.py")
helper = runpy.run_path(str(B / "probe_followup.py"))
rc = helper["pure"](TARGET)
cases = json.loads((B / "COUNTEREXAMPLES.json").read_text())
if isinstance(cases, dict):
    cases = cases["counterexamples"]
by = {c["case"]: c for c in cases}
print(f"harness = {B/'probe_followup.py'}  (their pure() AST extractor)")
print(f"target  = {TARGET}\n")
ok = True


def say(name, got, want):
    global ok
    good = got == want
    ok &= good
    print(f"  {'OK  ' if good else 'FAIL'}  {name}\n           got={got}  want={want}")


def run(o, rb_pairs, anchors=(("anchor_ts", 3.0),)):
    rb = [dict(symbol="SYNTH", anchor_ts=t, read_ts=t, venue_position_qty=q,
               venue_position_notional=(o.get("_mark", 1.0)) * abs(q)) for t, q in rb_pairs]
    return rc["reconcile"]([("SYNTHETIC", dict(orders=[{k: v for k, v in o.items() if k != "_mark"}],
                                               position_readback=rb,
                                               anchors=[dict(anchor_ts=3., target_gross=1000.)]))],
                           min_notional_by_symbol={})


# ── C4, their exact fixture, their three persisted states, their reduce-only direction ──
c4 = by["C4 lower bound promoted to final"]["input_rows"][0]
for state in ("unknown", "pending", "confirmed"):
    o = copy.deepcopy(c4); o["request_ledger"][0]["state"] = state
    say(f"C4 [{state}] _exec_qty kind", rc["_exec_qty"](o)[2], "bounded")
    o2 = copy.deepcopy(o); o2["_mark"] = 10.0
    r = run(o2, [(1., -8.), (3., -2.)])
    say(f"C4 [{state}] BUY reduce-only, short 8 -> short 2 (cumulative 6): anomalies",
        len(r["latest"]), 0)
c46 = copy.deepcopy(by["C4 read6 inside legitimate [4,8] falsely anomalous"]["input_rows"][0])
c46["_mark"] = 10.0
say("C4 their read-6 case: anomalies at readback 0 -> 6", len(run(c46, [(1., 0.), (3., 6.)])["latest"]), 0)
say("C4 ...and a readback BEYOND the accepted capacity (0 -> 10) is still an anomaly",
    len(run(c46, [(1., 0.), (3., 10.)])["latest"]), 1)
# ── C7, their two fixtures ──
for nm, want in (("C7 nan child", "unquantifiable"), ("C7 negative child offset", "unquantifiable")):
    o = copy.deepcopy(by[nm]["input_rows"][0])
    say(f"{nm}: _exec_qty kind", rc["_exec_qty"](o)[2], want)
print("\n" + ("ALL REGRESSION CHECKS PASS" if ok else "REGRESSION FAILED"))
sys.exit(0 if ok else 1)
