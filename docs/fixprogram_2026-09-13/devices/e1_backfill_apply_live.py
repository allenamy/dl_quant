#!/usr/bin/python3
"""E1 apply (fix program 2026-09-13), after e1_backfill_rehearsal.py proved on a copy: watchdog not tripped
before/after, no blind condition, only cond3 fill counts changed (NO_STRESS), second apply writes 0.
Writes ONLY appended fills rows for day 20260912 in ~/dl_quant_live/state/live/pilot_log (idempotent by trade_id);
order rows untouched by design. Then re-runs the watchdog on a fresh COPY of the updated live pilot_log.
Credentials loaded in-process from ~/dl_quant_live/.env (no copy). Usage: e1_backfill_apply_live.py <receipt_json>"""
import json, os, shutil, sys, tempfile, time, hashlib
REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
os.chdir(REPO)
import envfile
envfile.load(os.path.join(REPO, ".env"))
os.environ["LIVE_MODE"] = "LIVE"; os.environ.setdefault("BINANCE_LIVE_CONFIRM", "I_UNDERSTAND")
import watchdog as WD, watchdog_inputs as WI, backfill_fills as BF, binance_broker as BB
DAY = "20260912"; OUT = sys.argv[1]
ROOT = os.path.join(REPO, "state/live/pilot_log")
F = os.path.join(ROOT, DAY, "fills.jsonl")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
res = {"utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "day": DAY}
bk = F + ".pre_e1_backfill_20260913"
if not os.path.exists(bk):
    shutil.copy2(F, bk)
res["backup"] = {"path": bk, "sha": sha(bk)}
res["fills_sha_before"] = sha(F); res["fills_lines_before"] = sum(1 for _ in open(F))
broker = BB.BinanceBroker(mode="LIVE"); broker.arm()
rep = BF.run(root=ROOT, day=DAY, apply=True, broker=broker, log=lambda *a, **k: None)
res["apply"] = rep
res["n_written"] = sum(r.get("n_rows_written", 0) for r in rep.get("results", []))
res["fills_sha_after"] = sha(F); res["fills_lines_after"] = sum(1 for _ in open(F))
tree = tempfile.mkdtemp(prefix="e1_post_"); shutil.rmtree(tree); shutil.copytree(ROOT, tree)
ops, ve, _ = WI.collect(tree)
ev, _, _ = WD.run(tree, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops, verbose=False, state_dir=tempfile.mkdtemp(prefix="e1_post_wd_"))
res["watchdog_on_copy_after_apply"] = {"tripped": ev.get("tripped"), "blind": ev.get("conditions_blind") or [], "triggers": ev.get("triggers") or []}
shutil.rmtree(tree, ignore_errors=True)
res["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(res, open(OUT, "w"), indent=1, default=str)
print("E1_APPLY n_written", res["n_written"], "lines", res["fills_lines_before"], "->", res["fills_lines_after"],
      "watchdog_after tripped", res["watchdog_on_copy_after_apply"]["tripped"], "blind", res["watchdog_on_copy_after_apply"]["blind"])
