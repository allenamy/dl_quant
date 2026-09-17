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
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def cell(lo, hi, n): return {"n": n, "dg": (lo + hi) / 2, "ci95": [lo, hi], "n_days": 800}
SEEDS = ("42", "2027"); YEARS = {"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": 0.1}
WA0 = calendar.timegm((2022, 6, 30, 0, 0, 0)); UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); KL0 = calendar.timegm((2024, 1, 1, 0, 0, 0))
T0 = WA0 - 900 * 14400; TS = T0 + 14400 * np.arange((calendar.timegm((2026, 8, 31, 0, 0, 0)) - T0) // 14400 + 1, dtype=np.int64)
N_WA = int(((TS >= WA0) & (TS <= UB)).sum()); N_KL = int(((TS >= KL0) & (TS <= UB)).sum())
spec = importlib.util.spec_from_file_location("gc_t", f"{HERE}/v4_gate_common.py"); GC = importlib.util.module_from_spec(spec); spec.loader.exec_module(GC)
EXPORT_FLOOR = GC.required_inputs("BUNDLE_export")[0]; STEP1_FLOOR = GC.required_inputs("STEP1", "v4")[0]
def write_book(p, ts=TS):
    rec = np.zeros((len(ts), 3)); rec[:, 0] = ts; rec[:, 1] = 2.0; np.savez(p, cols=np.array(["ts", "gross_total", "net_ex"]), d30_n2_c42_rec=rec, config_json=np.array("{}"))
class Root:
    def __init__(self):
        self.T = tempfile.mkdtemp(prefix="fp2dec_"); self.R = f"{self.T}/R"; self.D = f"{self.T}/D"; os.makedirs(f"{self.R}/v4_gates"); os.makedirs(f"{self.R}/hc/probe_artifacts"); os.makedirs(f"{self.R}/controls"); os.makedirs(self.D)
        for f in ("fp2_per_year_table.py", "v4e_gate_export_v2.py", "fp2_member_rule_check.py", "fp2_gate_step1.py", "v4_gate_common.py"): shutil.copy2(f"{HERE}/{f}", f"{self.D}/{f}")
        self.contract = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))            # the REAL schema (load_contract checks contract_schema/gates/arms); only the approved sources point at the fixture's copies
        self.contract["gates"]["BUNDLE_export"]["approved_source_sha256"] = [sha(f"{self.D}/v4e_gate_export_v2.py")]; self.contract["gates"]["STEP1"]["approved_source_sha256"] = [sha(f"{self.D}/fp2_gate_step1.py")]
        json.dump(self.contract, open(f"{self.D}/ELIGIBILITY_CONTRACT.json", "w"))
        self.books = {}
        for a in ("A0", "A1"):
            for seat in ("dyn", "fix"):
                for s in SEEDS:
                    p = f"{self.R}/hc/probe_artifacts/w10_ablation_series_V4_{a}_{seat}_s{s}.npz"; write_book(p); self.books[f"{a}/{seat}/s{s}"] = p
        self.f = {}
        for name in ("umask", "kmeta", "kfea", "dlt", "dlt_hf3", "fea82", "fea89", "cache", "mmask", "rawp", "hole", "gatelib", "ckmeta", "cdlt", "bundle_slow2026", "other_meta"):
            p = f"{self.R}/data/{name}.bin"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(f"file {name}".encode()); self.f[name] = p
        json.dump({"gate": "FP2_CONTROLS", "VERDICT": "PASS", "outputs_path": {"control_king_meta": self.f["ckmeta"], "control_dl_targets": self.f["cdlt"]}, "outputs_sha256": {"control_king_meta": sha(self.f["ckmeta"]), "control_dl_targets": sha(self.f["cdlt"])}}, open(f"{self.R}/controls/CONTROLS.json", "w"))
    def per_year(self, cells, years=None, verdict="PASS", seeds=SEEDS, arms_sha=None, self_sha=None, umask_sha=None, coverage=None, env=None, n_wa=N_WA, n_kl=N_KL):
        years = years or YEARS; d = {}
        for s in seeds:
            c = cells[s] if s in cells else cells
            d[f"A1-A0/dyn/s{s}"] = {w: cell(*c[w], n_wa if w == "W_ALPHA" else n_kl) for w in c if w in ("W_ALPHA", "KING_LIVE")}; d[f"A1-A0/dyn/s{s}"]["by_year"] = {y: {"n": 2000, "dg": v, "ci95": [v - 0.3, v + 0.3]} for y, v in years.items()}
        arms = {k: {"path": p, "sha256": (arms_sha or sha)(p)} for k, p in self.books.items() if "/dyn/" in k}
        cov = {"reaches_UB": True, "years": sorted(years), "ts_max": "2026-08-31T00:00:00Z", "UB": "2026-08-30T20:00:00Z", "WA_START": "2022-06-30T00:00:00Z", "n_W_ALPHA": n_wa, "n_KING_LIVE": n_kl}; cov.update(coverage or {})
        rec = {"gate": "FP2_PER_YEAR", "VERDICT": verdict, "self_sha256": self_sha or sha(f"{self.D}/fp2_per_year_table.py"), "umask": {"sha256": umask_sha or sha(self.f["umask"])}, "arms": arms, "delta": d, "coverage": cov,
               "env": dict({"UB": "", "WA_START": "", "LEV": "", "SEATS": "dyn", "SEEDS": "42,2027", "ARMS": "A0,A1"}, **(env or {}))}
        p = f"{self.R}/v4_gates/PER_YEAR_TABLE.json"; json.dump(rec, open(p, "w")); return p
    def export(self, PASS=True, arm="A1", failed=None, self_sha=None, contract_sha=None, books=None, path=None, kmeta_key="wide_fea_v4_meta"):
        books = books or self.books; xin = {}
        for k, p in books.items():
            a, seat, s = k.split("/"); xin[f"{'book' if a == 'A1' else 'base'}_{seat}_{s}"] = p
        for name in EXPORT_FLOOR:
            if name in xin: continue
            xin[name] = {"wide_fea_v4_meta": self.f["kmeta"], "wide_fea_v4": self.f["kfea"], "umask_npz": self.f["umask"], "eligibility_contract": f"{self.D}/ELIGIBILITY_CONTRACT.json", "bundle/slow2026.txt": self.f["bundle_slow2026"], "bundle_manifest": self.f["other_meta"]}.get(name) or self._dummy(name)
        if kmeta_key != "wide_fea_v4_meta": xin["wide_fea_v4_meta"], xin[kmeta_key] = self.f["other_meta"], self.f["kmeta"]   # semantic key swapped
        rec = {"gate": "BUNDLE_export", "PASS": PASS, "arm": arm, "failed_checks": failed or [], "self_sha256": self_sha or sha(f"{self.D}/v4e_gate_export_v2.py"), "contract_sha256": contract_sha or sha(f"{self.D}/ELIGIBILITY_CONTRACT.json"),
               "inputs_path": xin, "inputs_sha256": {k: sha(p) for k, p in xin.items()}}
        p = path or f"{self.R}/v4_gates/BUNDLE_export_v2_A1.json"; json.dump(rec, open(p, "w")); return p
    def _dummy(self, name):
        p = f"{self.R}/data/dummy_{name.replace('/', '_')}.bin"; open(p, "wb").write(f"dummy {name}".encode()); return p
    def step1(self, verdict="PASS", PASS=True, gate="STEP1", self_sha=None, path=None, dlt=None, cache=None):
        xin = {"dlw_v4raw_targets": dlt or self.f["dlt"], "dlw_hf3_targets": self.f["dlt_hf3"], "fea82_v4raw": self.f["fea82"], "fea89_f8v4": self.f["fea89"], "cache": cache or self.f["cache"], "member_mask": self.f["mmask"], "raw_patch": self.f["rawp"],
               "hole_cells": self.f["hole"], "fp2_gate_lib": self.f["gatelib"], "controls_receipt": f"{self.R}/controls/CONTROLS.json", "control_dl_targets": self.f["cdlt"]}
        rec = {"gate": gate, "VERDICT": verdict, "PASS": PASS, "self_sha256": self_sha or sha(f"{self.D}/fp2_gate_step1.py"), "inputs_path": xin, "inputs_sha256": {k: sha(p) for k, p in xin.items()}}
        p = path or f"{self.R}/v4_gates/step1.json"; json.dump(rec, open(p, "w")); return p
    def member_rule(self, verdict="PASS", kmeta=None, dlt=None, cache=None):
        ins = {"CACHE": cache or self.f["cache"], "MEMBER_MASK": self.f["mmask"], "RAW_PATCH": self.f["rawp"], "CONTROL_KING_META": self.f["ckmeta"], "CONTROL_DL_TARGETS": self.f["cdlt"], "MASKED_KING_META": kmeta or self.f["kmeta"], "MASKED_DL_TARGETS": dlt or self.f["dlt"]}
        rec = {"gate": "FP2_MEMBER_RULE_CHECK", "VERDICT": verdict, "self_sha256": sha(f"{self.D}/fp2_member_rule_check.py"), "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in ins.items()}}
        p = f"{self.R}/v4_gates/MEMBER_RULE_CHECK.json"; json.dump(rec, open(p, "w")); return p
    def run(self, py, xp, mr=None, s1=None, extra=None, umask=None):
        e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "R": self.R, "D": self.D, "PER_YEAR_JSON": py, "EXPORT_RECEIPT": xp, "MEMBER_RULE_JSON": mr or self.member_rule(), "STEP1_JSON": s1 or self.step1(),
             "EXPECTED_UMASK": umask or self.f["umask"], "OUT_JSON": f"{self.T}/D.json", "OUT_MD": f"{self.T}/D.md"}; e.update(extra or {})
        r = subprocess.run([PY, f"{HERE}/fp2_decision.py"], env=e, capture_output=True, text=True); j = json.load(open(f"{self.T}/D.json"))
        return r.returncode, r.stdout + r.stderr, j
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
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
