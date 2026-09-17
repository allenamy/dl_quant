#!/usr/bin/env python3
"""tests_fp2_per_year_table.py — synthetic arms with values known BY CONSTRUCTION, through the real device.
  Y1 constant g per arm per year ⇒ per-year g exact; Δ exact 0.5 each year; CI of a constant is degenerate [Δ,Δ]; maxDD 0 for positive g; Sharpe None (std 0)
  Y2 a year of negative constant g ⇒ maxDD@L2 == 1 − Π(1+2g·1e-4) over that year's anchors (exact)
  Y3 traded cells outside the umask are counted (a cell planted deliberately ⇒ 1)
  Y4 A1 missing ⇒ VERDICT PARTIAL, rc 3, A0 rows present, delta UNAVAILABLE
  Y5 cfg assertion violated (CAL=simple) ⇒ that arm UNAVAILABLE"""
import calendar, json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
COLS = ['ts', 'net', 'pnl', 'carry', 'cost', 'gross_total', 'gross_member', 'gross_sel', 'nsel', 'nmember', 'fires', 'leg_king', 'leg_rev24', 'leg_fund', 'w3_king', 'w3_rev24', 'w3_fund', 'turnover', 'net_ex', 'pnl_ex', 'carry_ex', 'cost_ex', 'netlong']
T0 = calendar.timegm((2022, 1, 31, 0, 0, 0)); ts = T0 + 14400 * np.arange(1200 + 900, dtype=np.int64)   # 900 warm-up + 2100 anchors ≈ 2022-01-31 → 2023-06
YEAR = np.array([calendar.timegm((2023, 1, 1, 0, 0, 0)) <= t for t in ts])
def arm(path, gfun, seat, cal="log", W=None, syms=None, umask=None, gt_row=None):
    """F09/F10 fixture: every arm carries a symbols axis and a REAL umask path in cfg (the device verifies its identity across arms)."""
    dd = os.path.dirname(path); syms = syms or ["AUSDT", "BUSDT", "CUSDT"]; umask = umask or f"{dd}/umask.npz"
    if not os.path.isfile(umask): np.savez(umask, ts=ts, symbols=np.array(syms), mask=np.ones((len(ts), len(syms)), bool), definition=np.array("test"))
    rec = np.zeros((len(ts), len(COLS))); rec[:, 0] = ts; gt = 2.0; g = np.array([gfun(i) for i in range(len(ts))])
    rec[:, COLS.index("gross_total")] = gt; rec[:, COLS.index("net_ex")] = g * gt; rec[:, COLS.index("pnl_ex")] = (g + 0.1) * gt; rec[:, COLS.index("carry_ex")] = 0.1 * gt; rec[:, COLS.index("cost_ex")] = 0.0; rec[:, COLS.index("turnover")] = 0.05 * gt
    cfg = {"CAL": cal, "PHI": 0.45, "LEGS": "101", "WRULE": "msharpe", "UMASK_SCOPE": "m1", "LOOK": 900, "FTRIM": "zero", "MEMBERS_TOPN": 829, "W3FIX": None if seat == "dyn" else "0.21,0,0.79", "UMASK_NPZ": "/x/umask.npz", "COSTB_JSON": "/x/c.json", "SLOW_NPY": "/x/SLOW.npy", "FPRED": "f.npy", "FSEED": "42"}
    if gt_row is not None: rec[gt_row, COLS.index("gross_total")] = -2.0          # Y7: one non-positive gross row
    cfg["UMASK_NPZ"] = umask
    d = {"cols": np.array(COLS), "d30_n2_c42_rec": rec, "config_json": np.array(json.dumps(cfg)), "symbols": np.array(syms)}
    if W is not None: d["d30_n2_c42_W"] = W
    np.savez(path, **d)
def run(d, arms="A0,A1", umask="", extra=None):
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "ARMS_DIR": d, "OUT_JSON": f"{d}/t.json", "OUT_MD": f"{d}/t.md", "ARMS": arms, "SEATS": "dyn", "SEEDS": "42", "UMASK_NPZ": umask}; e.update(extra or {})
    r = subprocess.run([PY, f"{HERE}/fp2_per_year_table.py"], env=e, capture_output=True, text=True); j = json.load(open(f"{d}/t.json")) if os.path.isfile(f"{d}/t.json") else None
    return r.returncode, r.stdout + r.stderr, j
with tempfile.TemporaryDirectory() as d:
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0 if not YEAR[i] else -0.5, "dyn"); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 1.5 if not YEAR[i] else 0.0, "dyn")
    rc, out, j = run(d); a0 = j["arms"]["A0/dyn/s42"]; dl = j["delta"]["A1-A0/dyn/s42"]
    n23 = int((YEAR & (np.arange(len(ts)) >= 900)).sum())
    check("Y1 per-year g exact (A0 2022 = +1.0, 2023 = −0.5), Δ = +0.5 every year and on W_ALPHA, degenerate CI [0.5, 0.5], Sharpe None for constants, rc 0 PASS",
          rc == 0 and j["VERDICT"] == "PASS" and abs(a0["by_year"]["2022"]["g"] - 1.0) < 1e-12 and abs(a0["by_year"]["2023"]["g"] + 0.5) < 1e-12 and all(abs(dl["by_year"][y]["dg"] - 0.5) < 1e-12 for y in ("2022", "2023"))
          and abs(dl["W_ALPHA"]["dg"] - 0.5) < 1e-12 and abs(dl["W_ALPHA"]["ci95"][0] - 0.5) < 1e-12 and abs(dl["W_ALPHA"]["ci95"][1] - 0.5) < 1e-12 and a0["by_year"]["2022"]["sharpe_anchor"] is None and a0["by_year"]["2022"]["maxdd_L"] == 0.0,
          (rc, a0["by_year"], dl["W_ALPHA"]))
    exp = 1.0 - (1.0 + 2.0 * (-0.5) * 1e-4) ** n23
    check("Y2 maxDD@L2 of a year of constant −0.5 bps == 1 − (1 + 2·(−0.5)·1e-4)^n exactly (n = %d anchors)" % n23, abs(-a0["by_year"]["2023"]["maxdd_L"] - exp) < 1e-12, (a0["by_year"]["2023"]["maxdd_L"], -exp))
with tempfile.TemporaryDirectory() as d:
    syms = ["AUSDT", "BUSDT", "CUSDT"]; W = np.zeros((len(ts), 3), np.float32); W[:, 0] = 0.5; W[1000, 2] = 0.1   # symbol C is masked out everywhere; one traded cell planted there
    M = np.ones((len(ts), 3), bool); M[:, 2] = False; np.savez(f"{d}/umask.npz", ts=ts, symbols=np.array(syms), mask=M, definition=np.array("test"))
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn", W=W, syms=syms)
    rc, out, j = run(d, arms="A0", umask=f"{d}/umask.npz"); ms = j["arms"]["A0/dyn/s42"]["mask_stats"]
    check("Y3 mask stats: traded cells counted and the planted cell outside the umask ⇒ traded_cells_outside_mask == 1; umask sha recorded", ms["traded_cells_outside_mask"] == 1 and ms["traded_cells"] == len(ts) + 1 and len(j["umask"]["sha256"]) == 64, ms)
with tempfile.TemporaryDirectory() as d:
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn"); rc, out, j = run(d)
    check("Y4 A1 missing ⇒ VERDICT PARTIAL, rc 3, A0 rows present, delta UNAVAILABLE listed", rc == 3 and j["VERDICT"] == "PARTIAL" and "A0/dyn/s42" in j["arms"] and not j["delta"] and any("A1" in json.dumps(u) for u in j["UNAVAILABLE"]), (rc, j["UNAVAILABLE"]))
with tempfile.TemporaryDirectory() as d:
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn", cal="simple"); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 1.5, "dyn"); rc, out, j = run(d)
    check("Y5 cfg assertion (CAL=simple) ⇒ that arm UNAVAILABLE with the reason, rc 3", rc == 3 and any("CAL" in json.dumps(u) for u in j["UNAVAILABLE"]) and "A0/dyn/s42" not in j["arms"], j["UNAVAILABLE"])
# ── F09 (independent review 2026-09-17): the reviewer's counterexample — NAV 1 → 1.1 → 1 inside ONE UTC day ──
with tempfile.TemporaryDirectory() as d:
    up, dn = 500.0, (1.0 / 1.1 - 1.0) / (2.0 * 1e-4)            # L=2: ×1.1 then back to 1.0 at anchors 900 (a day start, 2022-06-30 00Z) and 901
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: up if i == 900 else (dn if i == 901 else 0.0), "dyn"); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 0.0, "dyn")
    rc, out, j = run(d); a0 = j["arms"]["A0/dyn/s42"]["W_ALPHA"]
    check("★★★ Y2b F09 intra-day 1 → 1.1 → 1: per-anchor maxDD@L (primary) = −9.0909%, day-end maxDD = 0.00% (the old instrument's blind spot), rc 0",
          rc == 0 and abs(a0["maxdd_L"] - (1.0 / 1.1 - 1.0)) < 1e-9 and a0["maxdd_L_dayend"] == 0.0, (rc, a0["maxdd_L"], a0["maxdd_L_dayend"]))
    md = open(f"{d}/t.md").read()
    check("Y2c the Markdown table carries both columns (逐锚 primary, 日末 secondary)", "maxDD@L 逐锚" in md and "maxDD@L 日末" in md and "-9.09%" in md, [l for l in md.splitlines() if "W_ALPHA" in l][:1])
# ── F10 input gates ──
with tempfile.TemporaryDirectory() as d:
    np.savez(f"{d}/other.npz", ts=ts, symbols=np.array(["AUSDT", "BUSDT", "CUSDT"]), mask=np.ones((len(ts), 3), bool), definition=np.array("other"))
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn"); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 1.5, "dyn", umask=f"{d}/other.npz")
    rc, out, j = run(d)
    check("★★★ Y6 F10 arms evaluated under DIFFERENT umask files ⇒ A1 UNAVAILABLE naming UMASK_NPZ, no Δ, rc 3", rc == 3 and "A1/dyn/s42" not in j["arms"] and not j["delta"] and any("UMASK_NPZ differs" in json.dumps(u) for u in j["UNAVAILABLE"]), (rc, j["UNAVAILABLE"]))
with tempfile.TemporaryDirectory() as d:
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn", gt_row=1000); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 1.5, "dyn")
    rc, out, j = run(d)
    check("★★★ Y7 F10 gross_total −2 on one row ⇒ that arm UNAVAILABLE ('gross_total not finite-positive on 1 rows'), rc 3", rc == 3 and "A0/dyn/s42" not in j["arms"] and any("gross_total not finite-positive on 1 rows" in json.dumps(u) for u in j["UNAVAILABLE"]), (rc, j["UNAVAILABLE"]))
with tempfile.TemporaryDirectory() as d:
    arm(f"{d}/w10_ablation_series_V4_A0_dyn_s42.npz", lambda i: 1.0, "dyn"); arm(f"{d}/w10_ablation_series_V4_A1_dyn_s42.npz", lambda i: 1.5, "dyn")
    rc, out, j = run(d, extra={"WA_START": "2022-07-01T00:00:00Z"})
    check("★★★ Y8 F10 W_ALPHA start pinned to a TIME: ts[900] (2022-06-30 00Z) != pinned 2022-07-01 ⇒ VERDICT UNAVAILABLE, no arms, rc 3", rc == 3 and j["VERDICT"] == "UNAVAILABLE" and not j.get("arms") and any("W_ALPHA" in u for u in j["UNAVAILABLE"]), (rc, j["UNAVAILABLE"]))
    rc, out, j = run(d, extra={"WA_START": "2022-06-30T00:00:00Z"})
    check("Y8b the same axis with the correct pin ⇒ PASS (baseline green for the pin control)", rc == 0 and j["VERDICT"] == "PASS", (rc, j["VERDICT"]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
