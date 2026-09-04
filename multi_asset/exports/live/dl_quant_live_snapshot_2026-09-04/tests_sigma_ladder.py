#!/usr/bin/env python3
"""tests_sigma_ladder — the gross ladder consumer is fail-safe (g=1.0 on every defect) and exact when valid.
MOCK ONLY: temp files, injected clock; never touches state/, never the venue."""
import json, os, sys, tempfile, time, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from live import sigma_ladder as SL  # noqa: E402

FAILS = []; N = [0]
def check(name, cond, detail=""):
    N[0] += 1; print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}", flush=True)
    if not cond: FAILS.append(name)
def mk(g=1.0, written=None, now=1_800_000_000.0, tamper=False, schema=SL.SCHEMA, p=0.2):
    wt = now - 600 if written is None else written
    doc = {"schema": schema, "g": g, "p": p, "anchor_ts": int(now // 14400 * 14400), "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(wt)),
           "streak_low": 90, "streak_high": 0, "rule": "test"}
    doc["sha"] = SL._sha(doc)
    if tamper: doc["g"] = 0.5 if g == 1.0 else 1.0
    return doc
now = 1_800_000_000.0
print("[1] fail-safe = 1.0")
check("1a missing -> 1.0/missing", SL.evaluate(None, now) == (1.0, {"src": "sigma_ladder", "g": 1.0, "accepted": False, "reason": "missing"}))
check("1b wrong schema -> 1.0", SL.evaluate(mk(0.5, schema="other"), now)[0] == 1.0)
check("1c g outside whitelist (0.7) -> 1.0", SL.evaluate(dict(mk(0.7), **{"sha": SL._sha(mk(0.7))}), now)[1]["reason"].startswith("g_out_of_whitelist"))
check("1d tampered g (sha mismatch) -> 1.0", SL.evaluate(mk(1.0, tamper=True), now) [1]["reason"] == "sha_mismatch")
check("1e stale (7h) -> 1.0", SL.evaluate(mk(0.5, written=now - 7 * 3600), now)[1]["reason"].startswith("stale"))
check("1f future (>10min) -> 1.0", SL.evaluate(mk(0.5, written=now + 3600), now)[1]["reason"].startswith("stale"))
print("[2] valid file is exact")
g, info = SL.evaluate(mk(0.5), now); check("2a g=0.5 accepted with p/streaks", g == 0.5 and info["accepted"] and info["p"] == 0.2 and info["streak_low"] == 90, info)
g, info = SL.evaluate(mk(1.0), now); check("2b g=1.0 accepted", g == 1.0 and info["accepted"])
print("[3] loader")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "sigma_ladder.json")
    check("3a no file -> missing", SL.load(p, now=now)[1]["reason"] == "missing")
    open(p, "w").write("{not json"); check("3b corrupt json -> unreadable", SL.load(p, now=now)[1]["reason"].startswith("unreadable"))
    json.dump(mk(0.5), open(p, "w")); g, info = SL.load(p, now=now); check("3c valid -> 0.5 with path", g == 0.5 and info["path"] == p)
print("[4] arithmetic contract: target_leverage = gross_mult x g")
check("4a 2.0 x 0.5 = 1.0", abs(2.0 * SL.evaluate(mk(0.5), now)[0] - 1.0) < 1e-12)
check("4b 2.0 x 1.0 = 2.0", abs(2.0 * SL.evaluate(mk(1.0), now)[0] - 2.0) < 1e-12)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}   ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
