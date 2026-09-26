#!/usr/bin/env python3
"""rev 1 (news2 review 2026-09-27): r1_manifest also carries plan_rows_full (every key of every planned row).
Build live/tests_fixtures/funding_gap/ for tests_funding_gap.py R1/G9 (read-only on production; writes only into the clone).
  binance_funding_d01e35d.py.txt   = git show d01e35d:live/binance_funding.py (the pre-fix module, frozen for G9)
  r1_pilot_log/20260926/           = production 20260926 position_readback (whole day), fills with fill_ts in (A, B) (originals and
                                     supersedes alike), and the PRE-BACKFILL funding file (funding.jsonl.pre_gap_backfill_20260926T2111Z)
  r1_venue_answers.json            = news2's recorded venue answers (RAW.json: income / rates / intervals) + stepSize per symbol
                                     (executor exchange_info_cache.json)
  r1_manifest.json                 = day, now_ms (20:47:00Z, after B), n_plan, plan_rows [(symbol, settlement_ts, position, paid, rate)]
usage: python3 build_funding_gap_fixture.py <clone>"""
import hashlib, json, os, subprocess, sys
clone = sys.argv[1]; out = f"{clone}/live/tests_fixtures/funding_gap"; assert not os.path.exists(out); os.makedirs(f"{out}/r1_pilot_log/20260926")
PL = os.path.expanduser("~/dl_quant_live/state/live/pilot_log/20260926")
FB = os.path.expanduser("~/Desktop/quant_research/multi_asset/exports/research/funding_backfill_2026-09-26/window/run_20260926T2111Z")
src = subprocess.run(["git", "-C", os.path.expanduser("~/dl_quant_live"), "show", "d01e35d:live/binance_funding.py"], capture_output=True, check=True).stdout
open(f"{out}/binance_funding_d01e35d.py.txt", "wb").write(src)
cen = json.load(open(f"{FB}/CENSUS.json")); A, B = cen["readback_before_gap"]["read_ts"], cen["readback_after_gap"]["read_ts"]
open(f"{out}/r1_pilot_log/20260926/position_readback.jsonl", "wb").write(open(f"{PL}/position_readback.jsonl", "rb").read())
with open(f"{out}/r1_pilot_log/20260926/fills.jsonl", "w") as f:
    for l in open(f"{PL}/fills.jsonl"):
        r = json.loads(l)
        if r.get("fill_ts") is not None and A < float(r["fill_ts"]) < B: f.write(l)
open(f"{out}/r1_pilot_log/20260926/funding.jsonl", "wb").write(open(f"{PL}/funding.jsonl.pre_gap_backfill_20260926T2111Z", "rb").read())
raw = json.load(open(f"{FB}/RAW.json")); ex = json.load(open(os.path.expanduser("~/dl_quant_live/state/exchange_info_cache.json")))
syms = sorted({i["symbol"] for i in raw["income"]}) 
steps = {s: ex[s]["step"] for s in syms if isinstance(ex.get(s), dict) and ex[s].get("step")}
json.dump({"income": raw["income"], "rates": raw["rates"], "intervals": raw["intervals"], "steps": steps,
           "source": {"RAW.json_sha256": hashlib.sha256(open(f"{FB}/RAW.json", "rb").read()).hexdigest(), "window_ms": raw["window_ms"]}},
          open(f"{out}/r1_venue_answers.json", "w"))
plan = json.load(open(f"{FB}/plan/PLAN.json"))
json.dump({"day": "20260926", "now_ms": 1790455620000, "A": A, "B": B, "n_plan": plan["n_rows_planned"],
           "plan_rows": [[r["symbol"], r["settlement_ts"], r["position_notional_at_settlement"], r["funding_paid"], r["funding_rate"]] for r in plan["rows"]],
           "plan_rows_full": plan["rows"],   # rev 1 (news2 review): the WHOLE planned row, every key, for R1
           "plan_sha256": hashlib.sha256(open(f"{FB}/plan/PLAN.json", "rb").read()).hexdigest()}, open(f"{out}/r1_manifest.json", "w"))
print("FIXTURE_OK", {"steps": len(steps), "of_syms": len(syms), "income": len(raw["income"]), "plan": plan["n_rows_planned"]})
