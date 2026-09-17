#!/usr/bin/env python3
"""tests for fp2_decision.py (F03): the AMENDMENT 7 rule on synthetic receipts, including the independent reviewer's three CI cases."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
def cell(lo, hi): return {"n": 5000, "dg": (lo + hi) / 2, "ci95": [lo, hi], "n_days": 800}
def per_year(cells, years=None, verdict="PASS", seeds=("42", "2027")):
    """cells: dict window -> (lo, hi) applied to both seeds unless a dict keyed by seed is given"""
    years = years or {"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": 0.1}
    d = {}
    for s in seeds:
        c = cells[s] if s in cells else cells
        d[f"A1-A0/dyn/s{s}"] = {w: cell(*c[w]) for w in c if w in ("W_ALPHA", "KING_LIVE")}
        d[f"A1-A0/dyn/s{s}"]["by_year"] = {y: {"n": 2000, "dg": v, "ci95": [v - 0.3, v + 0.3]} for y, v in years.items()}
    return {"gate": "FP2_PER_YEAR", "VERDICT": verdict, "self_sha256": "x" * 64, "umask": {"sha256": "u" * 64}, "arms": {"A0/dyn/s42": {"sha256": "a" * 64}}, "delta": d}
def run(py, export=True, export_pass=True, export_arm="A1", extra=None):
    d = tempfile.mkdtemp(); json.dump(py, open(f"{d}/py.json", "w"))
    if export: json.dump({"gate": "EXPORT_GATE_V2", "PASS": export_pass, "arm": export_arm, "failed_checks": [] if export_pass else ["x"], "contract_path": "/c"}, open(f"{d}/x.json", "w"))
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "PER_YEAR_JSON": f"{d}/py.json", "EXPORT_RECEIPT": f"{d}/x.json" if export else "", "OUT_JSON": f"{d}/D.json", "OUT_MD": f"{d}/D.md"}; e.update(extra or {})
    r = subprocess.run([PY, f"{HERE}/fp2_decision.py"], env=e, capture_output=True, text=True); j = json.load(open(f"{d}/D.json"))
    return r.returncode, r.stdout + r.stderr, j
both = lambda lo, hi: {"W_ALPHA": (lo, hi), "KING_LIVE": (lo, hi)}
rc, o, j = run(per_year(both(-0.01, 0.10)))
check("★★★ T1 reviewer case: all four cells CI [−0.01, +0.10] (lower > −δ) ⇒ G1′ NONINFERIOR ⇒ with G2/G3 ok ⇒ SWAP_RECOMMENDED, rc 0", rc == 0 and j["G1"]["verdict"] == "NONINFERIOR" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", (rc, j["G1"]["verdict"], j["RECOMMENDATION"]))
rc, o, j = run(per_year({"42": both(-0.06, -0.01), "2027": both(-0.01, 0.1)}))
check("★★★ T2 reviewer case: one cell [−0.06, −0.01] (lower < −δ, upper > −δ) ⇒ UNDECIDED ⇒ NO_SWAP", j["G1"]["verdict"] == "UNDECIDED" and j["RECOMMENDATION"] == "NO_SWAP" and "G1′ = UNDECIDED" in j["reasons"], (j["G1"]["verdict"], j["reasons"]))
rc, o, j = run(per_year(both(-0.04, -0.01)))
check("★★★ T3 reviewer case: cells [−0.04, −0.01] ⇒ NONINFERIOR (a negative point estimate whose CI clears −δ is non-inferior by the rule)", j["G1"]["verdict"] == "NONINFERIOR" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
rc, o, j = run(per_year({"42": both(-0.20, -0.06), "2027": both(0.01, 0.1)}))
check("★★ T4 one cell upper < −δ ⇒ WORSE ⇒ NO_SWAP", j["G1"]["verdict"] == "WORSE" and j["RECOMMENDATION"] == "NO_SWAP", j["G1"]["verdict"])
rc, o, j = run(per_year(both(0.01, 0.10)))
check("★★ T5 all lower > 0 ⇒ BETTER ⇒ SWAP_RECOMMENDED", j["G1"]["verdict"] == "BETTER" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
py = per_year(both(0.01, 0.10)); del py["delta"]["A1-A0/dyn/s2027"]; rc, o, j = run(py)
check("★★★ T6 seed 2027 missing ⇒ UNAVAILABLE (no verdict inferred from three cells), rc 3", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE" and j["G1"]["verdict"] is None and any("cell missing" in u for u in j["UNAVAILABLE"]), (rc, j["UNAVAILABLE"]))
rc, o, j = run(per_year(both(0.01, 0.10), years={"2022": -0.1, "2023": -0.2, "2024": 0.2, "2025": 0.0, "2026": 0.1}))
check("★★ T7 G2: two years worse than −δ ⇒ G2 false ⇒ NO_SWAP even with G1′ BETTER", j["G1"]["verdict"] == "BETTER" and j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", (j["G2"]["per_seed"]["s42"]["years_worse_than_delta"], j["RECOMMENDATION"]))
rc, o, j = run(per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.2, "2024": 0.2, "2025": 0.0, "2026": -0.1}))
check("★★ T8 G2: the single worse year is 2026 ⇒ G2 false ⇒ NO_SWAP", j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
rc, o, j = run(per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": -0.2, "2024": 0.2, "2025": 0.0, "2026": 0.1}))
check("★ T8b G2: exactly one worse year, not 2026 ⇒ G2 true", j["G2"]["ok"] is True and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
rc, o, j = run(per_year(both(0.01, 0.10)), export_pass=False)
check("★★ T9 export gate receipt PASS=false ⇒ G3 false ⇒ NO_SWAP", j["G3"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["reasons"])
rc, o, j = run(per_year(both(0.01, 0.10)), export=False)
check("★★ T10 export gate receipt missing ⇒ UNAVAILABLE, rc 3", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE", j["UNAVAILABLE"])
rc, o, j = run(per_year(both(0.01, 0.10)), export_arm="A0")
check("★★ T11 export receipt bound to another arm ⇒ G3 false", j["G3"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G3"])
rc, o, j = run(per_year(both(0.01, 0.10), verdict="PARTIAL"))
check("★★ T12 per-year table VERDICT PARTIAL ⇒ UNAVAILABLE (cells present but the table did not pass its own gates)", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE", j["UNAVAILABLE"])
rc, o, j = run(per_year(both(-0.049, 0.10)), extra={"DELTA": "0.02"})
check("★ T13 δ is a parameter: lower −0.049 is NONINFERIOR at δ=0.05 but UNDECIDED at δ=0.02", j["G1"]["verdict"] == "UNDECIDED", j["G1"]["verdict"])
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
