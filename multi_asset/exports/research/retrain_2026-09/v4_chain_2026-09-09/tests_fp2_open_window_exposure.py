#!/usr/bin/env python3
"""synthetic test for fp2_open_window_exposure.py: one OPEN event; the symbol becomes a member 8h after OPEN and stays for 3 days ⇒ known counts per horizon."""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
d = tempfile.mkdtemp(); T0 = 1_700_000_000 - (1_700_000_000 % 14400); E = T0 + 14400 * np.arange(400, dtype=np.int64)     # 400 anchors, 4h grid
syms = ["AUSDT", "BUSDT", "CUSDT"]; o = int(E[100]) + 3600                                                                # OPEN at anchor 100 + 1h
mem = np.empty(400, object)
for k in range(400):
    base = [0, 1]
    if E[k] >= o + 8 * 3600 and E[k] < o + 3 * 86400: base = base + [2]                                                  # C is a member from +8h to +3d (only anchors ≥ o+8h)
    mem[k] = np.array(base)
np.savez(f"{d}/king_meta.npz", E_ts=E, members=mem, names=np.array(["fea_%d" % i for i in range(82)]))    # the REAL king meta shape: 82 FEATURE names, no symbol axis
np.savez(f"{d}/dl.npz", E_ts=E, members=mem, symbols=np.array(syms))
json.dump({"symbols": {"CUSDT": {"transitions": [{"kind": "OPEN", "effective_ms": o * 1000}, {"kind": "CLOSE", "effective_ms": (o - 86400 * 40) * 1000}]}, "ZUSDT": {"transitions": [{"kind": "OPEN", "effective_ms": o * 1000}]}}}, open(f"{d}/cal.json", "w"))
e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "CALENDAR": f"{d}/cal.json", "KING_META": f"{d}/king_meta.npz", "DL_TARGETS": f"{d}/dl.npz", "OUT_JSON": f"{d}/out.json"}
r = subprocess.run([PY, f"{HERE}/fp2_open_window_exposure.py"], env=e, capture_output=True, text=True); j = json.load(open(f"{d}/out.json"))
ev = {x["symbol"]: x for x in j["sources"]["king"]["events"]}
n48 = sum(1 for k in range(400) if o <= E[k] < o + 172800 and E[k] >= o + 8 * 3600); n7 = sum(1 for k in range(400) if o <= E[k] < o + 604800 and E[k] >= o + 8 * 3600 and E[k] < o + 3 * 86400)
check("E1 rc 0, 2 OPEN events; the king meta (82 feature `names`, no symbols) takes its symbol axis from the DL targets file and records the provenance; the symbol outside the axis makes the verdict PARTIAL and is named",
      r.returncode == 0 and j["VERDICT"] == "PARTIAL" and j["n_open_events"] == 2 and ev["ZUSDT"]["in_symbol_axis"] is False and j["sources"]["king"]["symbol_axis_from"] == f"{d}/dl.npz" and j["sources"]["king"]["n_symbols"] == 3 and any("ZUSDT" in u or "not on the symbol axis" in u for u in j["UNAVAILABLE"]), (r.returncode, j.get("VERDICT"), j["sources"]["king"].get("n_symbols"), r.stderr[-200:]))
check(f"E2 CUSDT member anchors within 48h == {n48}, within 7d == {n7} (3-day membership), within 30d == {n7}; first member anchor after OPEN = first grid anchor ≥ +8h",
      ev["CUSDT"]["member_anchors_within_48h"] == n48 and ev["CUSDT"]["member_anchors_within_168h"] == n7 and ev["CUSDT"]["member_anchors_within_720h"] == n7 and 8.0 <= ev["CUSDT"]["first_member_anchor_after_open_h"] < 12.0, ev["CUSDT"])
tot = j["sources"]["king"]["totals"]
check("E3 totals = per-event sums; share = count / total member cells; both sources (king by names, dl by symbols) agree", tot["member_anchors_within_168h"] == n7 and abs(tot["share_of_member_cells"]["member_anchors_within_168h"] - n7 / tot["total_member_cells"]) < 1e-12 and j["sources"]["dl"]["totals"] == tot, tot)
r2 = subprocess.run([PY, f"{HERE}/fp2_open_window_exposure.py"], env=dict(e, KING_META=f"{d}/nope.npz"), capture_output=True, text=True); j2 = json.load(open(f"{d}/out.json"))
check("E4 a missing input ⇒ UNAVAILABLE, rc 3 (never a count of zero)", r2.returncode == 3 and j2["VERDICT"] == "UNAVAILABLE", j2["UNAVAILABLE"])
np.savez(f"{d}/king_bad.npz", E_ts=E, members=np.array([np.array([0, 7])] + [np.array([0]) for _ in range(399)], dtype=object), names=np.array(["f"]))
r3 = subprocess.run([PY, f"{HERE}/fp2_open_window_exposure.py"], env=dict(e, KING_META=f"{d}/king_bad.npz"), capture_output=True, text=True)
check("E5 a member index beyond the borrowed symbol axis ⇒ refused (rc≠0, 'exceeds symbol axis'), never silently miscounted", r3.returncode != 0 and "exceeds symbol axis" in (r3.stdout + r3.stderr), (r3.returncode, (r3.stdout + r3.stderr)[-160:]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
