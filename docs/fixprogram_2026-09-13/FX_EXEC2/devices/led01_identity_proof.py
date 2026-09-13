#!/usr/bin/python3
"""LED-01 req. 1 identity proof (read-only): compute, with the executor tree given as argv[1], everything the (symbol,
trade_id) collapse-key change could move — per day over every day of the ledger copy (argv[2] = pilot_log root):
pilot_log.collapse_supersedes kept-row indices, FROZEN pilot_metrics.dedupe_fills output (row indices in output order),
pilot_metrics.m2_markout over the day's fills and over its stress-anchor subset (the watchdog cond3 inputs,
watchdog.py:1370-1395), and the raw/collapsed counts; plus watchdog.evaluate's cond3_crash_markout detail over the whole
copy. Writes only argv[3]. Run once with the old tree and once with the new; the canonical sha256 of the two outputs
must be equal. Usage: /usr/bin/python3 led01_identity_proof.py <tree> <pilot_log_root> <out.json>"""
import hashlib, json, os, sys, time
TREE, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
for d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(TREE, d))
os.environ.setdefault("LIVE_MODE", "DRY_RUN")
import pilot_log as PL, pilot_metrics as PM
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
res = {"tree": TREE, "pilot_log_py": sha(os.path.join(TREE, "live", "pilot_log.py")),
       "pilot_metrics_py": sha(os.path.join(TREE, "live", "pilot_metrics.py")), "per_day": {}}
for day in PL.available_days(ROOT):
    one = PL.read_day(ROOT, day)
    fills = one["fills"]
    pos = {id(r): i for i, r in enumerate(fills)}
    stress = {a["anchor_ts"] for a in one["anchors"] if a.get("regime_at_anchor") == "stress"}
    sub = [x for x in fills if x["anchor_ts"] in stress]
    res["per_day"][day] = {
        "n_raw": len(fills),
        "collapse_kept": [pos[id(r)] for r in PL.collapse_supersedes(fills)],
        "dedupe_order": [pos[id(r)] for r in PM.dedupe_fills(fills)],
        "m2_all": PM.m2_markout(fills),
        "m2_stress": (PM.m2_markout(sub) if sub else None),
    }
import watchdog as WD
ev = WD.evaluate(ROOT, venue_events=[], ops_stats=[])
res["cond3_crash_markout"] = (ev.get("conditions") or {}).get("cond3_crash_markout")
canon = json.dumps({k: v for k, v in res.items() if k not in ("tree", "pilot_log_py", "pilot_metrics_py")},
                   sort_keys=True, default=repr).encode()
res["canonical_sha256"] = hashlib.sha256(canon).hexdigest()
json.dump(res, open(OUT, "w"), indent=1, sort_keys=True, default=repr)
print("LED01_IDENTITY", "canonical_sha256", res["canonical_sha256"], "days", len(res["per_day"]),
      "pilot_log.py", res["pilot_log_py"][:16], "pilot_metrics.py", res["pilot_metrics_py"][:16],
      "cond3_keys", sorted((res["cond3_crash_markout"] or {}).keys())[:6])
