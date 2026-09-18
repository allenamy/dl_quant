#!/usr/bin/env python3
"""Behavioural tests for pc3_stop_counterfactual.py v2 (independent review round 11 R11-PC3 counterexamples + the v2 contract).
Green baseline first, then each red case. The frozen production per_name_stop.py (409ea16) is read from PC3_PNS_DIR (a `git show` export; the
live tree is never imported). Run: PC3_PNS_DIR=<dir with per_name_stop.py> python3 tests_pc3_v2.py   (exit 0 iff ALL PASS)."""
import os, sys, json, time, importlib.util, tempfile, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pc3", os.path.join(HERE, "pc3_stop_counterfactual.py")); pc3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc3)
PNS_DIR = os.environ.get("PC3_PNS_DIR"); assert PNS_DIR and os.path.exists(os.path.join(PNS_DIR, "per_name_stop.py")), "PC3_PNS_DIR must point at an exported per_name_stop.py"
sys.path.insert(0, PNS_DIR); import per_name_stop as PNS

N = [0]; FAILS = []
def check(name, cond, detail=""):
    N[0] += 1; print(("  PASS " if cond else "  FAIL ") + name + (("  — " + str(detail)[:160]) if detail != "" else ""), flush=True)
    if not cond: FAILS.append(name)

A0 = 14400
def fill(ts, qty, px, s="X", tid=None):
    return {"symbol": s, "fill_ts": ts, "fill_px": px, "fill_notional": abs(qty) * px, "side": "BUY" if qty > 0 else "SELL", "trade_id": tid if tid is not None else ts}
def rb(A, qty, mark, read_ts, s="X", source="fapi/v3/account@post_anchor"):
    return {"symbol": s, "anchor_ts": A, "read_ts": read_ts, "venue_position_qty": qty, "venue_position_notional": qty * mark, "source": source}
def snap_of(snaps, A):
    return next((s, u) for a, s, u in snaps if a == A)

print("[1] cost basis: green baseline (one fill, one readback)")
snaps, _ = pc3.build_snapshots([fill(1, 1, 100)], [rb(A0, 1, 120, A0 + 2700)])
s, u = snap_of(snaps, A0)
check("baseline: unrealised = (120−100)×1 = +20, entry 100, basis known", abs(s["positions_unrealized"]["X"] - 20) < 1e-9 and abs(s["positions_entry_notional"]["X"] - 100) < 1e-9 and u == [], (s, u))

print("[2] R11-PC3 fixture: fills AFTER the readback's read_ts must not enter that readback (v1 gave −100)")
snaps, _ = pc3.build_snapshots([fill(1, 1, 100), fill(A0 + 3000, -1, 100), fill(A0 + 3300, 1, 200)], [rb(A0, 1, 100, A0 + 2700)])
s, u = snap_of(snaps, A0)
check("same cross-section: unrealised at read_ts = 0 (not −100)", abs(s["positions_unrealized"]["X"]) < 1e-9 and u == [], s["positions_unrealized"])

print("[3] R11-PC3 fixture: a zero readback ENDS the lifecycle; a later position without fills is UNKNOWN (v1 gave −40 from stale cost)")
snaps, _ = pc3.build_snapshots([fill(1, 1, 100)], [rb(A0, 1, 100, A0 + 2700), rb(2 * A0, 0, 0, 2 * A0 + 2700), rb(3 * A0, 1, 60, 3 * A0 + 2700)])
s3, u3 = snap_of(snaps, 3 * A0)
check("lifecycle reset: third snapshot has X UNKNOWN, no unrealised value", "X" in u3 and "X" not in s3["positions_unrealized"], (s3, u3))
snaps, _ = pc3.build_snapshots([fill(1, 1, 100), fill(2 * A0 + 3000, 1, 60)], [rb(A0, 1, 100, A0 + 2700), rb(2 * A0, 0, 0, 2 * A0 + 2700), rb(3 * A0, 1, 60, 3 * A0 + 2700)])
s3, u3 = snap_of(snaps, 3 * A0)
check("new lifecycle with its own fill: basis known = 60, unrealised 0", u3 == [] and abs(s3["positions_unrealized"]["X"]) < 1e-9 and abs(s3["positions_entry_notional"]["X"] - 60) < 1e-9, (s3, u3))

print("[4] R11-PC3 fixture: a fill crossing zero sets the residual's basis to that fill's price and marks it KNOWN (v1 kept UNKNOWN)")
B = pc3.Basis(); B.pos["X"] = 1.0; B.avg["X"] = 100.0; B.known["X"] = False; B.apply_fill(fill(5, -2, 90))
check("sign flip: pos −1, avg 90, known True", abs(B.pos["X"] + 1) < 1e-9 and abs(B.avg["X"] - 90) < 1e-9 and B.known["X"] is True, (dict(B.pos), dict(B.avg), dict(B.known)))
B = pc3.Basis(); B.pos["X"] = 1.0; B.avg["X"] = 100.0; B.known["X"] = False; B.apply_fill(fill(5, -0.5, 90))
check("reducing without crossing keeps UNKNOWN", B.known["X"] is False and abs(B.pos["X"] - 0.5) < 1e-9)

print("[5] fills deduped by (symbol, trade_id), not trade_id alone")
snaps, walk = pc3.build_snapshots([fill(1, 1, 100, "X", tid=7), fill(1, 1, 100, "Y", tid=7)], [rb(A0, 1, 100, A0 + 2700, "X"), rb(A0, 1, 100, A0 + 2700, "Y")])
s, u = snap_of(snaps, A0)
check("two symbols sharing trade_id 7 both keep their fill (both known, unrealised 0)", u == [] and walk["n_fills_deduped"] == 2, (u, walk))

print("[6] forward footprint: window starts at A (not A+4h), all-48-rows rule, censoring, maturity")
rts = A0 + np.arange(1, 48 * 20 + 1) * 300                       # 20 four-hour windows after A0
ret5 = np.zeros((len(rts), 1)); ret5[:48, 0] = 1.1 ** (1 / 48) - 1   # +10% only inside (A0, A0+4h]
sidx = {"X": 0}; last = int(rts[-1])
fp = pc3.forward_footprint(A0, "X", rts, ret5, sidx, last, 0)
check("primary (A, A+72h] PRICED with path ≈ +10% (the first window IS counted)", fp["status"] == "PRICED" and abs(fp["path_return"] - 0.1) < 1e-9 and fp["n_windows_priced"] == 18, fp)
fp2 = pc3.forward_footprint(A0, "X", rts, ret5, sidx, last, 14400)
check("exit-aligned (A+4h, A+76h] PRICED with path 0 (the first window is excluded)", fp2["status"] == "PRICED" and abs(fp2["path_return"]) < 1e-9, fp2)
r2 = ret5.copy(); r2[48 * 5 + 3, 0] = np.nan                        # one NaN row inside window 5
fp3 = pc3.forward_footprint(A0, "X", rts, r2, sidx, last, 0)
check("one NaN row ⇒ CENSORED_INCOMPLETE, first_missing_window 5, path None (never compounded as 0)", fp3["status"] == "CENSORED_INCOMPLETE" and fp3["first_missing_window"] == 5 and fp3["path_return"] is None and fp3["n_windows_priced"] == 17, fp3)
r3 = ret5.copy(); r3[48 * 5 + 1:48 * 6, 0] = np.nan                  # 47 of 48 rows NaN (v1 ret4h accepted this as the single value)
fp4 = pc3.forward_footprint(A0, "X", rts, r3, sidx, last, 0)
check("47/48 NaN rows ⇒ CENSORED_INCOMPLETE (v1 accepted 1 of 48)", fp4["status"] == "CENSORED_INCOMPLETE", fp4["status"])
fp5 = pc3.forward_footprint(A0, "X", rts, ret5, sidx, A0 + 47 * 3600, 0)   # panel ends 47 h after A: immature
check("panel ends at A+47h ⇒ CENSORED_IMMATURE with hours_available 47", fp5["status"] == "CENSORED_IMMATURE" and abs(fp5["hours_available"] - 47) < 1e-6, fp5)
fp6 = pc3.forward_footprint(A0, "Z", rts, ret5, sidx, last, 0)
check("symbol not on the panel ⇒ NO_PANEL_SYMBOL", fp6["status"] == "NO_PANEL_SYMBOL")

print("[7] replica ≡ production evaluate (409ea16) bitwise over a random sequence of snapshots (denominator = current)")
rng = np.random.default_rng(7); conf = dict(PNS.cfg(), enabled=True) if PNS.cfg() else {"enabled": True, "depth_pct": -0.3, "consecutive_anchors": 2, "cooloff_days": 7, "min_notional_usdt": 5.0}
conf = dict(conf, enabled=True); names = [f"S{i}" for i in range(30)]; st_p = {"counters": {}, "stopped": {}, "cooldown": {}}; st_r = dict(st_p); agree = 0; T = 300
for k in range(T):
    pn = {s: float(rng.choice([-1, 1]) * rng.uniform(0, 40)) for s in names if rng.random() < 0.9}
    pu = {s: float(rng.uniform(-0.6, 0.3) * abs(v)) for s, v in pn.items() if rng.random() < 0.85}
    snap = {"positions_notional": pn, "positions_unrealized": pu, "positions_entry_notional": {s: abs(v) * float(rng.uniform(0.5, 1.5)) for s, v in pn.items()}}
    now = A0 * (k + 1) + 3600
    st_p, _ = PNS.evaluate({"positions_notional": pn, "positions_unrealized": pu}, st_p, conf, now); st_r, _ = pc3.evaluate_replica(snap, st_r, conf, now, "current")
    agree += (st_p == st_r)
check(f"replica agrees with production on {T}/{T} anchors (stopped/cooldown/counters bitwise)", agree == T, agree)
check("production function produced stops in the sequence (test is not vacuous)", (len(st_p["cooldown"]) + len(st_p["stopped"])) > 0, st_p)

print("[8] V1 replica keeps dust/exit on the CURRENT notional and uses the entry basis only as the depth denominator (reviewer's PNS_FROZEN_PROBE cases)")
c1 = {"enabled": True, "depth_pct": -0.3, "consecutive_anchors": 1, "min_notional_usdt": 5, "cooloff_days": 7}; empty = {"counters": {}, "stopped": {}, "cooldown": {}}
st, _ = pc3.evaluate_replica({"positions_notional": {"X": -6}, "positions_unrealized": {"X": -2}, "positions_entry_notional": {"X": 4}}, empty, c1, 1, "entry")
check("short current 6 / entry 4 / upnl −2: eligible (6 ≥ 5), depth −0.5 ⇒ TRIGGERS (v1 adapter did not: it fed 4 < dust 5)", "X" in st["stopped"], st)
st, _ = pc3.evaluate_replica({"positions_notional": {"X": 4}, "positions_unrealized": {"X": -2}, "positions_entry_notional": {"X": 6}}, empty, c1, 1, "entry")
check("long current 4 / entry 6 / upnl −2: dust (4 < 5) ⇒ NOT eligible (v1 adapter triggered: it fed 6)", "X" not in st["stopped"] and not st["counters"], st)
st, _ = pc3.evaluate_replica({"positions_notional": {"X": 10}, "positions_unrealized": {"X": -2.5}, "positions_entry_notional": {"X": 12}}, empty, c1, 1, "entry")
check("entry basis larger than current: depth −2.5/12 = −0.208 > −0.3 ⇒ no trigger, while current-basis depth −0.25 also no trigger; counters reset", "X" not in st["stopped"] and not st["counters"])
st, _ = pc3.evaluate_replica({"positions_notional": {"X": 10}, "positions_unrealized": {"X": -3.5}, "positions_entry_notional": {}}, empty, c1, 1, "entry")
check("missing entry basis ⇒ name skipped in V1 (never priced with the current denominator by accident)", "X" not in st["stopped"] and not st["counters"])
st, _ = pc3.evaluate_replica({"positions_notional": {"X": 3}, "positions_unrealized": {"X": -1}, "positions_entry_notional": {"X": 3}}, {"counters": {}, "stopped": {"X": 0}, "cooldown": {}}, c1, 1000, "entry")
check("exit test uses the CURRENT notional (3 < 5 ⇒ stopped name moves to cooldown)", "X" in st["cooldown"] and "X" not in st["stopped"], st)

print("[9] run_spec: V0 needs two consecutive anchors, V2 one; footprint attached with both windows")
snaps = [(A0, {"positions_notional": {"X": 100.0}, "positions_unrealized": {"X": -35.0}, "positions_entry_notional": {"X": 130.0}}, []),
         (2 * A0, {"positions_notional": {"X": 100.0}, "positions_unrealized": {"X": -36.0}, "positions_entry_notional": {"X": 130.0}}, [])]
c2 = {"enabled": True, "depth_pct": -0.3, "consecutive_anchors": 2, "min_notional_usdt": 5, "cooloff_days": 7}
pf = lambda A, s, off: {"status": "PRICED", "path_return": -0.2, "n_windows_priced": 18, "first_missing_window": None, "window_utc": ["", ""], "n_windows": 18}
ev0 = pc3.run_spec("V0", snaps, c2, PNS, pf); ev2 = pc3.run_spec("V2", snaps, c2, PNS, pf); ev1 = pc3.run_spec("V1", snaps, c2, PNS, pf)
check("V0 triggers once at the second anchor", len(ev0) == 1 and ev0[0]["anchor"] == 2 * A0, [(e["utc"], e["symbol"]) for e in ev0])
check("V2 triggers at the first anchor", len(ev2) == 1 and ev2[0]["anchor"] == A0)
check("V1 (entry basis 130): depth −35/130 = −0.27 > −0.3 ⇒ no trigger", len(ev1) == 0, ev1)
check("long stop, path −20% ⇒ avoided P&L = −(+1)×100×(−0.2) = +20 on both windows", abs(ev0[0]["primary_0_72h"]["avoided_pnl_usdt"] - 20) < 1e-9 and abs(ev0[0]["exit_aligned_4_76h"]["avoided_pnl_usdt"] - 20) < 1e-9)
sm = pc3.summarise(ev0)
check("summarise counts priced/helped", sm["primary_0_72h"]["n_priced"] == 1 and sm["primary_0_72h"]["n_helped"] == 1)

print("[10] production triggers = first appearance after absence, keyed by the 4h bucket of the phase_C time")
tmp = tempfile.mkdtemp(prefix="pc3_", dir=os.environ.get("TMPDIR"))
lines = [("2026-09-01T00:41:00", []), ("2026-09-01T04:41:00", ["X"]), ("2026-09-01T08:41:00", ["X", "Y"]), ("2026-09-01T12:41:00", ["Y"]), ("2026-09-01T16:41:00", ["Y", "X"]), ("2026-09-01T20:41:00", "disabled")]
p = os.path.join(tmp, "anchor_runs.log")
with open(p, "w") as f:
    for t, st_ in lines:
        f.write(f"{t} phase_C: " + json.dumps({"per_name_stop": ({"stopped": st_, "counters": {}} if isinstance(st_, list) else st_)}) + "\n")
    f.write("2026-09-01T21:00:00 phase_A: {}\n")
tr = pc3.production_triggers(p, 0, 4e9)
check("events X@04Z, Y@08Z, X@16Z (re-entry counts again; string per_name_stop ignored)", [(e["symbol"], e["bucket_utc"]) for e in tr] == [("X", "09-01 04:00Z"), ("Y", "09-01 08:00Z"), ("X", "09-01 16:00Z")], tr)

print("[11] match_production: MATCHED / NEAR_MISS / MISSED with reasons; device-only listed; recall and precision")
bX = int(time.mktime(time.strptime("2026-09-01T04:00:00", "%Y-%m-%dT%H:%M:%S")) - time.timezone)
prod = [{"symbol": "X", "bucket": bX, "bucket_utc": "09-01 04:00Z"}, {"symbol": "Y", "bucket": bX, "bucket_utc": "09-01 04:00Z"}, {"symbol": "Z", "bucket": bX, "bucket_utc": "09-01 04:00Z"}, {"symbol": "W", "bucket": bX, "bucket_utc": "09-01 04:00Z"}]
dev = [{"symbol": "X", "anchor": bX, "utc": "09-01 04:00Z", "depth": -0.4}, {"symbol": "Y", "anchor": bX + 14400, "utc": "09-01 08:00Z", "depth": -0.4}, {"symbol": "Q", "anchor": bX, "utc": "09-01 04:00Z", "depth": -0.5}]
snaps = [(bX, {"positions_notional": {"X": 10, "Z": 10, "W": 10}, "positions_unrealized": {"X": -4, "W": -1}, "positions_entry_notional": {}}, ["Z"])]
m = pc3.match_production(prod, dev, snaps, {"depth_pct": -0.3})
st_by = {r["symbol"]: r for r in m["production_events"]}
check("X MATCHED, Y NEAR_MISS (+1 bucket), Z MISSED unknown basis, W MISSED depth −0.1 > −0.3", st_by["X"]["status"] == "MATCHED" and st_by["Y"]["status"].startswith("NEAR_MISS") and st_by["Z"]["status"] == "MISSED" and "unknown basis" in st_by["Z"]["reason"] and st_by["W"]["status"] == "MISSED" and "> threshold" in st_by["W"]["reason"], st_by)
check("recall 1/4, precision 1/3, device-only = Y(08Z) and Q", abs(m["recall"] - 0.25) < 1e-9 and abs(m["precision"] - 1 / 3) < 1e-9 and sorted(d["symbol"] for d in m["device_only_events"]) == ["Q", "Y"], m["device_only_events"])

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
