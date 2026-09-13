#!/usr/bin/python3
"""E1 rehearsal (fix program 2026-09-13): backfill the 09-12 protective-flatten fills on a COPY of the
live pilot_log, and prove the watchdog verdict is unchanged before touching the live ledger.
Read-only against the live tree: credentials are loaded in-process from ~/dl_quant_live/.env (no copy),
venue calls are GETs (arm checks, allOrders, userTrades), all writes go to a temp copy.
Usage: /usr/bin/python3 e1_backfill_rehearsal.py <receipt_json_path>"""
import json, os, shutil, sys, tempfile, time, hashlib
REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
os.chdir(REPO)
import envfile
_env = envfile.load(os.path.join(REPO, ".env"))
os.environ["LIVE_MODE"] = "LIVE"
os.environ.setdefault("BINANCE_LIVE_CONFIRM", "I_UNDERSTAND")
import watchdog as WD, watchdog_inputs as WI, backfill_fills as BF, binance_broker as BB, pilot_log as PL
DAY = "20260912"
OUT = sys.argv[1]
SRC = os.path.join(REPO, "state/live/pilot_log")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
live_fills = os.path.join(SRC, DAY, "fills.jsonl")
live_sha_before = sha(live_fills) if os.path.exists(live_fills) else None
tree = tempfile.mkdtemp(prefix="e1_rehearsal_"); shutil.rmtree(tree); shutil.copytree(SRC, tree)
def wd(t):
    ops, ve, _ = WI.collect(t)
    ev, _, _ = WD.run(t, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops, verbose=False,
                      state_dir=tempfile.mkdtemp(prefix="e1_wd_"))
    det = {}
    for k in ("detail", "details", "conditions"):
        if isinstance(ev.get(k), dict): det = ev[k]; break
    return {"tripped": ev.get("tripped"), "blind": ev.get("conditions_blind") or [],
            "triggers": ev.get("triggers") or [], "partial": ev.get("conditions_partial") or [],
            "cond_keys": sorted(det.keys()),
            "detail_sha": hashlib.sha256(json.dumps(det, sort_keys=True, default=str).encode()).hexdigest()}, det
res = {"utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "day": DAY, "tree": tree,
       "env_loaded": {"exists": _env.get("exists"), "n_set": _env.get("n_set")},
       "live_fills_sha_before": live_sha_before}
w0, d0 = wd(tree); res["watchdog_before"] = w0
broker = BB.BinanceBroker(mode="LIVE"); res["arm"] = broker.arm()
rep0 = BF.run(root=tree, day=DAY, apply=False, broker=broker, log=lambda *a, **k: None)
res["report"] = rep0
rep1 = BF.run(root=tree, day=DAY, apply=True, broker=broker, log=lambda *a, **k: None)
res["apply_1"] = rep1
rep2 = BF.run(root=tree, day=DAY, apply=True, broker=broker, log=lambda *a, **k: None)
res["apply_2_idempotency"] = {"n_written": sum(r.get("n_rows_written", 0) for r in rep2.get("results", [])),
                              "n_gaps": rep2.get("n_gaps")}
w1, d1 = wd(tree); res["watchdog_after"] = w1
changed = {k: {"before": d0.get(k), "after": d1.get(k)} for k in sorted(set(d0) | set(d1))
           if json.dumps(d0.get(k), sort_keys=True, default=str) != json.dumps(d1.get(k), sort_keys=True, default=str)}
res["watchdog_conditions_changed"] = changed
fills_copy = PL.read_day(tree, DAY).get("fills", [])
bf = [r for r in fills_copy if r.get("backfilled_utc")]
comm = {}
for r in bf:
    a = r.get("commission_asset") or r.get("fee_asset") or "?"
    comm[a] = comm.get(a, 0.0) + float(r.get("commission") or r.get("fee") or 0.0)
res["backfilled_rows"] = {"n": len(bf), "commission_by_asset": comm,
                          "notional": sum(abs(float(r.get("notional") or 0.0)) for r in bf)}
res["live_fills_sha_after"] = sha(live_fills) if os.path.exists(live_fills) else None
res["live_untouched"] = res["live_fills_sha_after"] == live_sha_before
res["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(res, open(OUT, "w"), indent=1, default=str)
print("E1_REHEARSAL", "tripped_before", w0["tripped"], "tripped_after", w1["tripped"], "blind_after", w1["blind"],
      "rows_written", sum(r.get("n_rows_written", 0) for r in rep1.get("results", [])),
      "idempotent_second_write", res["apply_2_idempotency"]["n_written"], "live_untouched", res["live_untouched"],
      "conditions_changed", sorted(changed.keys()))
