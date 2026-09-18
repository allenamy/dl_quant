#!/usr/bin/env python3
"""tests for fp2_decision.py v4 (F03; independent review round 3: F2 complete closure, F3 frozen window).
The fixture builds a root R and a device dir D that satisfy the REAL v4_gate_common.require (registered floors, approved sources in the
contract beside the module, every recorded input on disk) with book files that carry a real 4h axis spanning the frozen window; every
negative cell breaks exactly one link and must land on UNAVAILABLE / REFUSED_PROFILE / EXPLORATORY_NO_RECOMMENDATION."""
import calendar, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:260]) if detail is not None else ""), flush=True)
from fp2_decision_fixture import sha, cell, SEEDS, YEARS, WA0, UB, KL0, T0, TS, N_WA, N_KL, GC, EXPORT_FLOOR, STEP1_FLOOR, write_book, Root   # FP3 J: fixture shared with tests_fp2_table_to_decision.py
both = lambda lo, hi: {"W_ALPHA": (lo, hi), "KING_LIVE": (lo, hi)}
X = Root()
rc, o, j = X.run(X.per_year(both(-0.01, 0.10)), X.export())
check("★★★ P0 positive control: real require on export (28-name floor + recorded extras) and STEP1 (v4 floor) pass, member-rule inputs re-hash, semantic bindings hold, frozen window re-derived from the book axes ⇒ NONINFERIOR ⇒ SWAP_RECOMMENDED rc 0",
      rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED" and j["G1"]["verdict"] == "NONINFERIOR" and not j["UNAVAILABLE"] and j["binding"]["export"]["require"]["ok"] and j["binding"]["step1"]["require"]["ok"], (rc, j["RECOMMENDATION"], j["UNAVAILABLE"][:3], o[-300:] if rc else ""))
# ── rule cells (unchanged semantics) ──
rc, o, j = X.run(X.per_year({"42": both(-0.06, -0.01), "2027": both(-0.01, 0.1)}), X.export()); check("★★★ T2 one cell [−0.06, −0.01] ⇒ UNDECIDED ⇒ NO_SWAP", j["G1"]["verdict"] == "UNDECIDED" and j["RECOMMENDATION"] == "NO_SWAP", (j["G1"]["verdict"], j["reasons"]))
rc, o, j = X.run(X.per_year(both(-0.04, -0.01)), X.export()); check("★★★ T3 cells [−0.04, −0.01] ⇒ NONINFERIOR ⇒ SWAP_RECOMMENDED", j["G1"]["verdict"] == "NONINFERIOR" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year({"42": both(-0.20, -0.06), "2027": both(0.01, 0.1)}), X.export()); check("★★ T4 upper < −δ ⇒ WORSE ⇒ NO_SWAP", j["G1"]["verdict"] == "WORSE" and j["RECOMMENDATION"] == "NO_SWAP", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export()); check("★★ T5 all lower > 0 ⇒ BETTER ⇒ SWAP_RECOMMENDED", j["G1"]["verdict"] == "BETTER" and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["G1"]["verdict"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": -0.1, "2023": -0.2, "2024": 0.2, "2025": 0.0, "2026": 0.1}), X.export()); check("★★ T7 two bad years ⇒ NO_SWAP", j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.2, "2024": 0.2, "2025": 0.0, "2026": -0.1}), X.export()); check("★★ T8 the bad year is 2026 ⇒ NO_SWAP", j["G2"]["ok"] is False and j["RECOMMENDATION"] == "NO_SWAP", j["G2"]["per_seed"]["s42"]["years_worse_than_delta"])
# ── F2 (round 3): complete closure through the real require ──
open(X.f["bundle_slow2026"], "ab").write(b" tampered"); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(path=f"{X.R}/v4_gates/BUNDLE_export_v2_A1.json") if False else f"{X.R}/v4_gates/BUNDLE_export_v2_A1.json")
check("★★★ F2a reviewer: bundle/slow2026.txt bytes changed AFTER the export gate passed (four books unchanged) ⇒ UNAVAILABLE 'export gate require: … changed since the receipt'", rc == 3 and any("slow2026" in u and "changed" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
open(X.f["bundle_slow2026"], "wb").write(b"file bundle_slow2026"); X.export()   # restore + re-sign for the following cells
X.step1(); X.member_rule(); open(X.f["dlt"], "ab").write(b" retrained-labels"); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), mr=f"{X.R}/v4_gates/MEMBER_RULE_CHECK.json", s1=f"{X.R}/v4_gates/step1.json")
check("★★★ F2b reviewer: DL targets file replaced on disk while STEP1 and MEMBER receipts still carry the old sha ⇒ UNAVAILABLE (STEP1 require + member input re-hash both refuse)", rc == 3 and any("dlw_v4raw_targets" in u and "changed" in u for u in j["UNAVAILABLE"]) and any("MASKED_DL_TARGETS changed" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:2])
open(X.f["dlt"], "wb").write(b"file dlt")
fake = f"{X.T}/fake_step1.json"; X.step1(gate="NOT_STEP1", PASS=False, self_sha="0" * 64, path=fake); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), s1=fake)
check("★★★ F2c reviewer: STEP1 outside the root, gate NOT_STEP1, all-zero source, PASS=false, VERDICT=PASS with aligned targets ⇒ UNAVAILABLE (root + require refuse)", rc == 3 and any("not under R/v4_gates" in u for u in j["UNAVAILABLE"]) and any("STEP1 require" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:2])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(kmeta_key="bundle_manifest"), mr=X.member_rule())
check("★★★ F2d reviewer: the member-rule king meta appears in the export inputs under ANOTHER key (bundle_manifest) while wide_fea_v4_meta is a different file ⇒ UNAVAILABLE (semantic key binding)", rc == 3 and any("MASKED_KING_META == export.wide_fea_v4_meta" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
X.export()
other_cache = f"{X.R}/data/cache_other.bin"; open(other_cache, "wb").write(b"another cache"); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), mr=X.member_rule(cache=other_cache))
check("★★★ F2e member-rule check ran on a different CACHE than STEP1 ⇒ UNAVAILABLE (semantic binding member.CACHE == step1.cache)", rc == 3 and any("member.CACHE == step1.cache" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
X.member_rule()
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), mr=X.member_rule(verdict="FAIL")); check("★★ F2f member-rule FAIL ⇒ UNAVAILABLE", rc == 3 and any("member-rule check VERDICT" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1]); X.member_rule()
# ── F3 (round 3): the frozen window is a property of the books, not of the table's self-report ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10), coverage={"WA_START": "2025-06-01T00:00:00Z", "UB": "2026-01-01T00:00:00Z", "reaches_UB": True, "n_W_ALPHA": 1000, "n_KING_LIVE": 800, "years": ["2026"]}, years={"2026": 0.1}, n_wa=1000, n_kl=800), X.export())
check("★★★ F3a reviewer: table self-declares a 2025-06 → 2026-01 window, reaches_UB=True, by_year only 2026 (file hashes intact) ⇒ UNAVAILABLE (coverage/years/counts vs frozen)", rc == 3 and any("not the frozen window" in u for u in j["UNAVAILABLE"]) and any("years" in u and "frozen" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:2])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), env={"UB": "2026-01-01T00:00:00Z"}), X.export())
check("★★★ F3b table produced with an overridden UB env ⇒ UNAVAILABLE (env is bound to the formal value)", rc == 3 and any("per-year table env UB" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
Y = Root(); short = TS[TS <= calendar.timegm((2026, 3, 1, 0, 0, 0))]
for k, p in Y.books.items(): write_book(p, ts=short)
rc, o, j = Y.run(Y.per_year(both(0.01, 0.10)), Y.export())
check("★★★ F3c the BOOK FILES end in 2026-03 while the table claims the frozen window ⇒ UNAVAILABLE (axis read from the books: ends before UB, counts differ)", rc == 3 and any("axis ends before the frozen UB" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:2])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), n_wa=9000), X.export())
check("★★ F3d a cell whose n is not the frozen anchor count ⇒ UNAVAILABLE", rc == 3 and any("frozen" in u and "G1 cell" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── P2-1 / P2-3 (review round 4): the terminal EXECUTES the variant approval, the controls chain and the preflight pin; raw axis exactness ──
Z = Root(); Z.write_contract(helper_sha="0" * 64); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export())
check("★★★ P2-1a reviewer: contract STEP1 variant `requires` helper sha zeroed (flat list intact) ⇒ UNAVAILABLE 'required helper fp2_gate_lib.py on disk != contract requires'", rc == 3 and any("required helper fp2_gate_lib.py" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
Z.write_contract(scope={"V4_MONTH": "2026-10", "R": Z.R}); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export())
check("★★★ P2-1b reviewer: STEP1 variant scope month 2026-10 while the preflight says 2026-09 ⇒ UNAVAILABLE (scope executed at the terminal)", rc == 3 and any("scope month" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
Z.write_contract(scope={"V4_MONTH": Z.month, "R": "/somewhere/else"}); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export())
check("★★ P2-1b′ scope root != R ⇒ UNAVAILABLE", rc == 3 and any("scope root" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1]); Z.write_contract()
open(f"{Z.D}/fp2_controls.py", "a").write("\n# swapped\n"); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export())
check("★★★ P2-1c reviewer: fp2_controls.py in D replaced while the controls receipt keeps the old self sha ⇒ UNAVAILABLE (controls chain + preflight pin)", rc == 3 and any("controls receipt not written by" in u for u in j["UNAVAILABLE"]) and any("preflight pinned fp2_controls.py" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:2])
shutil.copy2(f"{HERE}/fp2_controls.py", f"{Z.D}/fp2_controls.py"); Z.preflight()
rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export(), s1=Z.step1(drop=("hole_cells", "fea82_hf3", "fp2_gate_lib")))
check("★★★ P2-1d reviewer: STEP1 receipt with hole_cells / fea82_hf3 / fp2_gate_lib removed from BOTH dicts ⇒ UNAVAILABLE 'receipt lacks required input' ×3 (the variant's key set is fixed at the terminal)", rc == 3 and sum(1 for u in j["UNAVAILABLE"] if "lacks required input" in u) == 3, [u for u in j["UNAVAILABLE"] if "lacks" in u][:3])
open(Z.f["cache"], "ab").write(b" x"); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export()); open(Z.f["cache"], "wb").write(b"file cache")
check("★★ P2-1e a controls INPUT (cache) changed on disk after the controls receipt ⇒ UNAVAILABLE (transitive: STEP1 require + controls chain + member binding)", rc == 3 and any("controls input cache changed" in u for u in j["UNAVAILABLE"]), [u for u in j["UNAVAILABLE"] if "cache" in u][:2])
Z.preflight(pins={**{f: sha(f"{Z.D}/{f}") for f in Z.DEV}, "fp2_gate_lib.py": "9" * 64}); rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export())
check("★★ P2-1f preflight pinned another fp2_gate_lib.py sha ⇒ UNAVAILABLE", rc == 3 and any("preflight pinned fp2_gate_lib.py" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1]); Z.preflight()
rc, o, j = Z.run(Z.per_year(both(0.01, 0.10)), Z.export()); check("★ P2-1g the same root with everything restored ⇒ SWAP_RECOMMENDED (baseline green for the cells above)", rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", j["UNAVAILABLE"][:2])
Q = Root(); write_book(Q.books["A1/dyn/s42"], shift=0.5); rc, o, j = Q.run(Q.per_year(both(0.01, 0.10)), Q.export())
check("★★★ P2-3 reviewer: A1/s42 raw ts all +0.5 s (hash bindings intact) ⇒ UNAVAILABLE 'raw ts axis is not integer seconds' (old device truncated to the grid and PASSed)", rc == 3 and any("not integer seconds" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── round 5 P2 (path alias) ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"EXPORT_GATE": "./v4e_gate_export_v2.py"})
check("★★★ R5-1 reviewer: EXPORT_GATE written as ./<file> (same bytes) ⇒ UNAVAILABLE 'must be a bare basename' (the path form used to skip the variant scope binding)", rc == 3 and any("bare basename" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
Zv = Root(); Zv.write_contract(); c = json.load(open(f"{Zv.D}/ELIGIBILITY_CONTRACT.json")); c["gates"]["STEP1"]["approved_variants"] = {"renamed_step1.py": c["gates"]["STEP1"]["approved_variants"]["fp2_gate_step1.py"]}; json.dump(c, open(f"{Zv.D}/ELIGIBILITY_CONTRACT.json", "w"))
rc, o, j = Zv.run(Zv.per_year(both(0.01, 0.10)), Zv.export())
check("★★ R5-2 the STEP1 bytes are an approved variant registered under ANOTHER file name ⇒ bound by sha and refused ('carries the bytes of approved variant … under another name')", rc == 3 and any("under another name" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── R05 / R08 / earlier identity cells ──
py = X.per_year(both(0.01, 0.10)); d = json.load(open(py)); d["delta"]["A1-A0/dyn/s42"]["W_ALPHA"] = {"n": N_WA, "dg": float("inf"), "ci95": [float("inf"), float("inf")], "n_days": 800}; json.dump(d, open(py, "w")); rc, o, j = X.run(py, X.export())
check("★★★ R05a Inf cell ⇒ UNAVAILABLE", rc == 3 and any("not a finite measurement" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), years={"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": float("nan")}), X.export()); check("★★★ R05b NaN dg 2026 ⇒ UNAVAILABLE", rc == 3 and any("non-finite dg" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
bare = f"{X.R}/v4_gates/bare.json"; json.dump({"PASS": True, "arm": "A1"}, open(bare, "w")); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), bare); check("★★★ R04a bare {PASS,arm} export receipt ⇒ UNAVAILABLE", rc == 3 and j["RECOMMENDATION"] == "UNAVAILABLE", j["UNAVAILABLE"][:2])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), arms_sha=lambda p: "0" * 64), X.export()); check("★★★ R04b fake table (arm shas) ⇒ UNAVAILABLE", rc == 3 and any("changed since the table" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(self_sha="1" * 64)); check("★★★ R04c export written by another gate source ⇒ UNAVAILABLE (require refuses)", rc == 3 and any("export gate require" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
other = dict(X.books); other["A1/dyn/s42"] = f"{X.R}/hc/probe_artifacts/other.npz"; write_book(other["A1/dyn/s42"]); rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(books=other))
check("★★★ R04f export hashed a different A1/s42 book than the table ⇒ UNAVAILABLE", rc == 3 and any("same book" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
X.export()
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"SEEDS": "42"}); check("★★★ R08a SEEDS=42 under formal ⇒ REFUSED_PROFILE", rc == 3 and j["RECOMMENDATION"] == "REFUSED_PROFILE", j["reasons"])
rc, o, j = X.run(X.per_year(both(-9.0, -8.0)), X.export(), extra={"DELTA": "inf"}); check("★★★ R08b DELTA=inf under formal ⇒ REFUSED_PROFILE", rc == 3 and j["RECOMMENDATION"] == "REFUSED_PROFILE", j["reasons"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"UB": "2026-01-01T00:00:00Z"}); check("★★★ F3e UB override under formal ⇒ REFUSED_PROFILE (the window is part of the profile)", rc == 3 and j["RECOMMENDATION"] == "REFUSED_PROFILE", j["reasons"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), extra={"PROFILE": "exploratory", "WINDOWS": "W_ALPHA"}); check("★★★ R08c exploratory ⇒ EXPLORATORY_NO_RECOMMENDATION", rc == 0 and j["RECOMMENDATION"] == "EXPLORATORY_NO_RECOMMENDATION", j["RECOMMENDATION"])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(PASS=False, failed=["E8"])); check("★★ T9 export PASS=false ⇒ UNAVAILABLE", rc == 3 and any("export" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10), verdict="PARTIAL"), X.export()); check("★★ T12 table PARTIAL ⇒ UNAVAILABLE", rc == 3 and any("VERDICT 'PARTIAL'" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
py = X.per_year(both(0.01, 0.10)); d = json.load(open(py)); del d["delta"]["A1-A0/dyn/s2027"]; json.dump(d, open(py, "w")); rc, o, j = X.run(py, X.export()); check("★★ T6 seed 2027 cells missing ⇒ UNAVAILABLE", rc == 3 and any("cell missing" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
# ── R15-C1 (round 15): the export-end anchor must be the bundle's OWN declared provenance, never an EXPORT_ANCHOR_TS override ──
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), lvx=X.liveness("export", anchor_source="EXPORT_ANCHOR_TS (pinned by the caller)"))
check("★★★ R15-C1 the export-end anchor came from EXPORT_ANCHOR_TS (an env/caller override, not the bundle's hashed provenance) ⇒ UNAVAILABLE, never SWAP",
      rc == 3 and j["RECOMMENDATION"] != "SWAP_RECOMMENDED" and any("EXPORT_ANCHOR_TS" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), lvx=X.liveness("export", anchor=None, anchor_source=None))
check("★★ R15-C1 an export-end receipt that states no (checked_at_anchor, anchor_source) ⇒ UNAVAILABLE (the moment the shipped list was judged must be verifiable)",
      rc == 3 and any("checked_at_anchor, anchor_source" in u for u in j["UNAVAILABLE"]), j["UNAVAILABLE"][:1])
rc, o, j = X.run(X.per_year(both(0.01, 0.10)), X.export(), lvx=X.liveness("export"))
check("★ R15-C1 green control: the export end anchored on the bundle's provenance (the default) still ⇒ SWAP_RECOMMENDED (the check discriminates)",
      rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED", (j["RECOMMENDATION"], j["UNAVAILABLE"][:2]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
