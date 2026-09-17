#!/usr/bin/env python3
"""tests for fp2_decision.py (F03, hardened after independent review round 2: R04 identity closure, R05 numbers, R06 coverage, R08 profile).
A complete synthetic root R and device dir D are built so that the POSITIVE control passes every binding; each negative cell breaks exactly one
binding or number and must land on UNAVAILABLE / REFUSED_PROFILE / EXPLORATORY_NO_RECOMMENDATION — never SWAP_RECOMMENDED."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:260]) if detail is not None else ""), flush=True)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def cell(lo, hi): return {"n": 5000, "dg": (lo + hi) / 2, "ci95": [lo, hi], "n_days": 800}
SEEDS = ("42", "2027"); YEARS = {"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": 0.1}
class Root:
    """a synthetic root: D holds the device files the decision binds to (copies of the real ones) + a contract approving the export gate;
    R/v4_gates holds the receipts; R/hc/probe_artifacts holds the four 'books' (small files) that every receipt hashes."""
    def __init__(self):
        self.T = tempfile.mkdtemp(prefix="fp2dec_"); self.R = f"{self.T}/R"; self.D = f"{self.T}/D"; os.makedirs(f"{self.R}/v4_gates"); os.makedirs(f"{self.R}/hc/probe_artifacts"); os.makedirs(self.D)
        for f in ("fp2_per_year_table.py", "v4e_gate_export_v2.py", "fp2_member_rule_check.py"): shutil.copy2(f"{HERE}/{f}", f"{self.D}/{f}")
        self.contract = {"gates": {"BUNDLE_export": {"approved_source_sha256": [sha(f"{self.D}/v4e_gate_export_v2.py")]}}}; json.dump(self.contract, open(f"{self.D}/ELIGIBILITY_CONTRACT.json", "w"))
        self.books = {}
        for a in ("A0", "A1"):
            for s in SEEDS:
                p = f"{self.R}/hc/probe_artifacts/w10_ablation_series_V4_{a}_dyn_s{s}.npz"; open(p, "wb").write(f"book {a} {s}".encode()); self.books[f"{a}/dyn/s{s}"] = p
        self.umask = f"{self.R}/umask.npz"; open(self.umask, "wb").write(b"umask"); self.kmeta = f"{self.R}/data/wide_fea_v4_meta.npz"; os.makedirs(f"{self.R}/data"); open(self.kmeta, "wb").write(b"kmeta")
        self.dlt = f"{self.R}/dlw_v4raw/data/dlw_targets.npz"; os.makedirs(os.path.dirname(self.dlt)); open(self.dlt, "wb").write(b"dlt")
    def per_year(self, cells, years=None, verdict="PASS", reaches_UB=True, seeds=SEEDS, arms_sha=None, self_sha=None, umask_sha=None):
        years = years or YEARS; d = {}
        for s in seeds:
            c = cells[s] if s in cells else cells
            d[f"A1-A0/dyn/s{s}"] = {w: cell(*c[w]) for w in c if w in ("W_ALPHA", "KING_LIVE")}; d[f"A1-A0/dyn/s{s}"]["by_year"] = {y: {"n": 2000, "dg": v, "ci95": [v - 0.3, v + 0.3]} for y, v in years.items()}
        arms = {k: {"path": p, "sha256": (arms_sha or sha)(p)} for k, p in self.books.items()}
        rec = {"gate": "FP2_PER_YEAR", "VERDICT": verdict, "self_sha256": self_sha or sha(f"{self.D}/fp2_per_year_table.py"), "umask": {"sha256": umask_sha or sha(self.umask)}, "arms": arms, "delta": d,
               "coverage": {"reaches_UB": reaches_UB, "years": sorted(years), "ts_max": "2026-08-30T20:00:00Z", "UB": "2026-08-30T20:00:00Z"}}
        p = f"{self.R}/v4_gates/PER_YEAR_TABLE.json"; json.dump(rec, open(p, "w")); return p
    def export(self, PASS=True, arm="A1", failed=None, self_sha=None, contract_sha=None, books=None, path=None):
        books = books or self.books; xin = {}; xsh = {}
        for k, p in books.items():
            a, seat, s = k.split("/"); tag = f"{'book' if a == 'A1' else 'base'}_{seat}_{s}"; xin[tag] = p; xsh[tag] = sha(p)
        xin["bundle_meta"] = self.kmeta; xsh["bundle_meta"] = sha(self.kmeta)
        rec = {"gate": "BUNDLE_export", "PASS": PASS, "arm": arm, "failed_checks": failed or [], "self_sha256": self_sha or sha(f"{self.D}/v4e_gate_export_v2.py"), "contract_sha256": contract_sha or sha(f"{self.D}/ELIGIBILITY_CONTRACT.json"), "inputs_path": xin, "inputs_sha256": xsh}
        p = path or f"{self.R}/v4_gates/BUNDLE_export_v2_A1.json"; json.dump(rec, open(p, "w")); return p
    def member_rule(self, verdict="PASS", kmeta_sha=None, dlt_sha=None):
        rec = {"gate": "FP2_MEMBER_RULE_CHECK", "VERDICT": verdict, "self_sha256": sha(f"{self.D}/fp2_member_rule_check.py"), "inputs": {"MASKED_KING_META": {"path": self.kmeta, "sha256": kmeta_sha or sha(self.kmeta)}, "MASKED_DL_TARGETS": {"path": self.dlt, "sha256": dlt_sha or sha(self.dlt)}}}
        p = f"{self.R}/v4_gates/MEMBER_RULE_CHECK.json"; json.dump(rec, open(p, "w")); return p
    def step1(self, verdict="PASS", dlt_sha=None):
        rec = {"gate": "STEP1", "VERDICT": verdict, "inputs_path": {"dlw_v4raw_targets": self.dlt}, "inputs_sha256": {"dlw_v4raw_targets": dlt_sha or sha(self.dlt)}}
        p = f"{self.R}/v4_gates/step1.json"; json.dump(rec, open(p, "w")); return p
    def run(self, py, xp, mr=None, s1=None, extra=None, umask=None):
        e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "R": self.R, "D": self.D, "PER_YEAR_JSON": py, "EXPORT_RECEIPT": xp, "MEMBER_RULE_JSON": mr or self.member_rule(), "STEP1_JSON": s1 or self.step1(),
             "EXPECTED_UMASK": umask or self.umask, "OUT_JSON": f"{self.T}/D.json", "OUT_MD": f"{self.T}/D.md"}; e.update(extra or {})
        r = subprocess.run([PY, f"{HERE}/fp2_decision.py"], env=e, capture_output=True, text=True); j = json.load(open(f"{self.T}/D.json"))
        return r.returncode, r.stdout + r.stderr, j
both = lambda lo, hi: {"W_ALPHA": (lo, hi), "KING_LIVE": (lo, hi)}
X = Root()
# ── positive control: every binding intact ──
rc, o, j = X.run(X.per_year(both(-0.01, 0.10)), X.export())
check("★★★ P0 positive control (all bindings intact, cells [−0.01,+0.10]) ⇒ NONINFERIOR ⇒ SWAP_RECOMMENDED rc 0, no UNAVAILABLE", rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED" and j["G1"]["verdict"] == "NONINFERIOR" and not j["UNAVAILABLE"], (rc, j["RECOMMENDATION"], j["UNAVAILABLE"][:3]))
rc, o, j = X.run(X.per_year({"42": both(-0.06, -0.01), "2027": both(-0.01, 0.1)}), X.export())
check("★★★ T2 reviewer: one cell [−0.06, −0.01] ⇒ UNDECIDED ⇒ NO_SWAP", j["G1"]["verdict"] == "UNDECIDED" and j["RECOMMENDATION"] == "NO_SWAP", (j["G1"]["verdict"], j["reasons"]))
rc, o, j = X.run(X.per_year(both(-0.04, -0.01)), X.export())
check("★★★ T3 reviewer: cells [−0.04, −0.01] ⇒ NONINFERIOR ⇒ SWAP_RECOMMENDED", j["G1"]["verdict"] == "NONINFERIOR" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year({"42": both(-0.20, -0.06), "2027": both(0.01, 0.1)}), X.export())
check("★★ T4 one cell upper < −δ ⇒ WORSE ⇒ NO_SWAP", j["G1"]["verdict"] == "WORSE" and j["RECOMMENDATION"] == "NO_SWAP", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export())
check("★★ T5 all lower > 0 ⇒ BETTER ⇒ SWAP_RECOMMENDED", j["G1"]["verdict"] == "BETTER" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": -0.1, "2023": -0.2, "2024": 0.2, "2025": 0.0, "2026": 0.1}), X.export())
check("★★ T7 G2: two years worse than −δ ⇒ NO_SWAP even with BETTER", j["G1"]["verdict"] == "BETTER" and j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.2, "2024": 0.2, "2025": 0.0, "2026": -0.1}), X.export())
check("★★ T8 G2: the single worse year is 2026 ⇒ NO_SWAP", j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
# ── R05 numbers ──
py = X.per_year(both(0.01, 0.10)); d = json.load(open(py)); d["delta"]["A1-A0/dyn/s42"]["W_ALPHA"] = {"n": 5000, "dg": float("inf"), "ci95": [float("inf"), float("inf")], "n_days": 800}; json.dump(d, open(py, "w"))
rc, o, j = X.run(py, X.export())
check("★★★ R05a reviewer: an Inf cell (lower +inf would read BETTER) ⇒ UNAVAILABLE 'not a finite measurement', rc 3", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE" and any("not a finite measurement" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": float("nan")}), X.export())
check("★★★ R05b reviewer: NaN dg for 2026 (NaN < −δ is False, so it was silently 'not bad') ⇒ UNAVAILABLE naming 2026", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE" and any("non-finite dg" in u and "2026" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
py = X.per_year(both(0.01, 0.10)); d = json.load(open(py)); d["delta"]["A1-A0/dyn/s42"]["W_ALPHA"]["ci95"] = [0.5, 0.1]; json.dump(d, open(py, "w")); rc, o, j = X.run(py, X.export())
check("★★ R05c lo > hi ⇒ UNAVAILABLE", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE", j["UNAVAILABLE"][:1])
# ── R06 coverage ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0}), X.export())
check("★★★ R06a reviewer: table without 2026 (so '2026 not bad' is vacuous) ⇒ UNAVAILABLE 'years … != contiguous … through CURRENT_YEAR 2026'", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE" and any("contiguous" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), reaches_UB=False), X.export())
check("★★★ R06b table that does not reach the frozen UB ⇒ UNAVAILABLE", rc == 3 and any("frozen upper bound" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2024": 0.2, "2025": 0.0, "2026": 0.1}), X.export())
check("★★ R06c a gap year (2023 missing) ⇒ UNAVAILABLE", rc == 3 and any("contiguous" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── R04 identity closure ──
bare = f"{X.R}/v4_gates/bare.json"; json.dump({"PASS": True, "arm": "A1"}, open(bare, "w")); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), bare)
check("★★★ R04a reviewer: a bare {PASS:true, arm:A1} export receipt ⇒ UNAVAILABLE (no gate source, no contract, no books)", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE" and len(j["UNAVAILABLE"]) >= 3, j["UNAVAILABLE"][:2])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), arms_sha=lambda p: "0" * 64), X.export())
check("★★★ R04b reviewer: a table whose arm records do not hash to the books on disk (fake table) ⇒ UNAVAILABLE 'changed since the table'", rc == 3 and any("changed since the table" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(self_sha="1" * 64))
check("★★★ R04c reviewer: export receipt written by a gate source that is not the one in D ⇒ UNAVAILABLE", rc == 3 and any("v4e_gate_export_v2.py in D" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
Y = Root(); Y.contract = {"gates": {"BUNDLE_export": {"approved_source_sha256": ["2" * 64]}}}; json.dump(Y.contract, open(f"{Y.D}/ELIGIBILITY_CONTRACT.json", "w"))
rc, o, j = Y.run(Y.per_year(both(0.01, 0.10)), Y.export())
check("★★★ R04d the gate source in D is NOT approved by the contract in D ⇒ UNAVAILABLE 'not in the contract's BUNDLE_export approved list'", rc == 3 and any("approved list" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(contract_sha="3" * 64))
check("★★ R04e export receipt hashed a different contract ⇒ UNAVAILABLE", rc == 3 and any("different contract" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
other = dict(X.books); other["A1/dyn/s42"] = f"{X.R}/hc/probe_artifacts/other.npz"; open(other["A1/dyn/s42"], "wb").write(b"another book")
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(books=other))
check("★★★ R04f the export gate hashed a DIFFERENT book than the table for A1/s42 ⇒ UNAVAILABLE 'did not hash the same book'", rc == 3 and any("same book" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), mr=X.member_rule(verdict="FAIL"))
check("★★★ R04g member-rule check FAIL ⇒ UNAVAILABLE", rc == 3 and any("member-rule check VERDICT" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), mr=X.member_rule(kmeta_sha="4" * 64))
check("★★ R04h member-rule check verified a different king meta than the bundle the export gate hashed ⇒ UNAVAILABLE", rc == 3 and any("king meta" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), s1=X.step1(dlt_sha="5" * 64))
check("★★ R04i STEP1 hashed different DL targets than the member-rule check ⇒ UNAVAILABLE", rc == 3 and any("DL targets differ" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), umask_sha="6" * 64), X.export())
check("★★ R04j table umask != expected umask ⇒ UNAVAILABLE", rc == 3 and any("EXPECTED_UMASK" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
outside = f"{X.T}/outside.json"; shutil.copy2(X.export(), outside); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), outside)
check("★★ R04k export receipt outside R/v4_gates ⇒ UNAVAILABLE", rc == 3 and any("not under R/v4_gates" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), self_sha="7" * 64), X.export())
check("★★ R04l table written by a different fp2_per_year_table.py than D's ⇒ UNAVAILABLE", rc == 3 and any("fp2_per_year_table.py in D" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── R08 profile ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"SEEDS": "42"})
check("★★★ R08a reviewer: SEEDS=42 under the formal profile ⇒ REFUSED_PROFILE rc 3 (the four-cell conjunction cannot be shrunk)", rc == 3 and j["RECOMMENDATION"] == "REFUSED_PROFILE", j["reasons"])
rc, o, j = X.run(X.per_year(both(-9.0, -8.0)), X.export(), extra={"DELTA": "inf"})
check("★★★ R08b reviewer: DELTA=inf under the formal profile (would read −9 bps as non-inferior) ⇒ REFUSED_PROFILE", rc == 3 and j["RECOMMENDATION"] == "REFUSED_PROFILE", j["reasons"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"PROFILE": "exploratory", "WINDOWS": "W_ALPHA"})
check("★★★ R08c exploratory profile with a shrunken window set ⇒ EXPLORATORY_NO_RECOMMENDATION (rc 0), never SWAP_RECOMMENDED", rc == 0 and j["RECOMMENDATION"] == "EXPLORATORY_NO_RECOMMENDATION", j["RECOMMENDATION"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"SEEDS": "42,2027", "DELTA": "0.05"})
check("★ R08d restating the formal values is not an override ⇒ still SWAP_RECOMMENDED", rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["RECOMMENDATION"])
# ── G3 / arm binding ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(PASS=False, failed=["x"]))
check("★★ T9 export gate PASS=false ⇒ UNAVAILABLE (a failed export gate is not 'G3 false' but a broken input closure)", rc == 3 and any("export receipt PASS" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(arm="A0"))
check("★★ T11 export receipt bound to another arm ⇒ UNAVAILABLE", rc == 3 and any("export receipt arm" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), verdict="PARTIAL"), X.export())
check("★★ T12 per-year table VERDICT PARTIAL ⇒ UNAVAILABLE", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE", j["UNAVAILABLE"][:1])
py = X.per_year(both(0.01, 0.10)); d = json.load(open(py)); del d["delta"]["A1-A0/dyn/s2027"]; json.dump(d, open(py, "w")); rc, o, j = X.run(py, X.export())
check("★★ T6 seed 2027 cells missing ⇒ UNAVAILABLE (never inferred from three cells)", rc == 3 and any("cell missing" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
