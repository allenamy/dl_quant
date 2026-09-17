#!/usr/bin/env python3
"""fp2_decision_fixture.py — the decision suite's root fixture, shared with the table→decision integration suite (FP3 item J, 2026-09-17).
Builds a root R and a device dir D that satisfy the REAL v4_gate_common.require (registered floors, approved sources in the contract beside the
module, every recorded input on disk) with book files that carry a real 4h axis spanning the frozen window. Extracted byte-for-byte from
tests_fp2_decision.py (its cells import it) so that both suites drive fp2_decision.py through ONE fixture."""
import calendar, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def cell(lo, hi, n): return {"n": n, "dg": (lo + hi) / 2, "ci95": [lo, hi], "n_days": 800}
SEEDS = ("42", "2027"); YEARS = {"2022": 0.1, "2023": 0.0, "2024": 0.2, "2025": 0.0, "2026": 0.1}
WA0 = calendar.timegm((2022, 6, 30, 0, 0, 0)); UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); KL0 = calendar.timegm((2024, 1, 1, 0, 0, 0))
T0 = WA0 - 900 * 14400; TS = T0 + 14400 * np.arange((calendar.timegm((2026, 8, 31, 0, 0, 0)) - T0) // 14400 + 1, dtype=np.int64)
N_WA = int(((TS >= WA0) & (TS <= UB)).sum()); N_KL = int(((TS >= KL0) & (TS <= UB)).sum())
spec = importlib.util.spec_from_file_location("gc_t", f"{HERE}/v4_gate_common.py"); GC = importlib.util.module_from_spec(spec); spec.loader.exec_module(GC)
EXPORT_FLOOR = GC.required_inputs("BUNDLE_export")[0]; STEP1_FLOOR = GC.required_inputs("STEP1", "v4")[0]
def write_book(p, ts=TS, shift=0.0):
    rec = np.zeros((len(ts), 3)); rec[:, 0] = ts + shift; rec[:, 1] = 2.0; np.savez(p, cols=np.array(["ts", "gross_total", "net_ex"]), d30_n2_c42_rec=rec, config_json=np.array("{}"))
class Root:
    def __init__(self):
        self.T = tempfile.mkdtemp(prefix="fp2dec_"); self.R = f"{self.T}/R"; self.D = f"{self.T}/D"; os.makedirs(f"{self.R}/v4_gates"); os.makedirs(f"{self.R}/hc/probe_artifacts"); os.makedirs(f"{self.R}/controls"); os.makedirs(self.D)
        self.DEV = ("fp2_per_year_table.py", "v4e_gate_export_v2.py", "fp2_member_rule_check.py", "fp2_gate_step1.py", "v4_gate_common.py", "fp2_gate_lib.py", "fp2_controls.py", "fp2_decision.py")
        for f in self.DEV: shutil.copy2(f"{HERE}/{f}", f"{self.D}/{f}")
        self.month = "2026-09"; self.write_contract()
    def write_contract(self, helper_sha=None, scope=None):
        """the REAL schema (load_contract checks contract_schema/gates/arms); approved sources point at the fixture's copies; the STEP1 variant entry carries
        requires (fp2_gate_lib.py) + scope (month, root) — P2-1: the decision EXECUTES these"""
        c = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
        c["gates"]["BUNDLE_export"]["approved_source_sha256"] = [sha(f"{self.D}/v4e_gate_export_v2.py")]; c["gates"]["BUNDLE_export"].pop("approved_variants", None)
        c["gates"]["STEP1"]["approved_source_sha256"] = [sha(f"{self.D}/fp2_gate_step1.py")]
        c["gates"]["STEP1"]["approved_variants"] = {"fp2_gate_step1.py": {"sha256": sha(f"{self.D}/fp2_gate_step1.py"), "requires": {"fp2_gate_lib.py": helper_sha or sha(f"{self.D}/fp2_gate_lib.py")}, "scope": scope or {"V4_MONTH": self.month, "R": self.R}}}
        self.contract = c; json.dump(c, open(f"{self.D}/ELIGIBILITY_CONTRACT.json", "w")); self.preflight()
    def preflight(self, pins=None, month=None, PASS=True):
        pf = {"gate": "PREFLIGHT", "PASS": PASS, "month": month or self.month, "root": self.R, "device_sha256": pins or {f: sha(f"{self.D}/{f}") for f in self.DEV}, "inputs": {}}
        json.dump(pf, open(f"{self.R}/v4_gates/preflight.json", "w"))
        self.books = {}
        for a in ("A0", "A1"):
            for seat in ("dyn", "fix"):
                for s in SEEDS:
                    p = f"{self.R}/hc/probe_artifacts/w10_ablation_series_V4_{a}_{seat}_s{s}.npz"; write_book(p); self.books[f"{a}/{seat}/s{s}"] = p
        self.f = {}
        for name in ("umask", "kmeta", "kfea", "dlt", "dlt_hf3", "fea82", "fea89", "cache", "mmask", "rawp", "hole", "gatelib", "ckmeta", "cdlt", "bundle_slow2026", "other_meta"):
            p = f"{self.R}/data/{name}.bin"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(f"file {name}".encode()); self.f[name] = p
        self.f["gatelib"] = f"{self.D}/fp2_gate_lib.py"          # the helper STEP1 records is the one in D (its sha is the contract's `requires`)
        self.controls()
    def controls(self, self_sha=None):
        ins = {"cache": self.f["cache"], "raw_patch": self.f["rawp"], "builder_targets": self.f["fea82"]}
        json.dump({"gate": "FP2_CONTROLS", "VERDICT": "PASS", "mode": "run", "self_sha256": self_sha or sha(f"{self.D}/fp2_controls.py"), "inputs_path": ins, "inputs_sha256": {k: sha(p) for k, p in ins.items()},
                   "outputs_path": {"control_king_meta": self.f["ckmeta"], "control_dl_targets": self.f["cdlt"]}, "outputs_sha256": {"control_king_meta": sha(self.f["ckmeta"]), "control_dl_targets": sha(self.f["cdlt"])}}, open(f"{self.R}/controls/CONTROLS.json", "w"))
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
    def step1(self, verdict="PASS", PASS=True, gate="STEP1", self_sha=None, path=None, dlt=None, cache=None, drop=()):
        xin = {"dlw_v4raw_targets": dlt or self.f["dlt"], "dlw_hf3_targets": self.f["dlt_hf3"], "fea82_v4raw": self.f["fea82"], "fea82_hf3": self.f["fea82"], "fea89_f8v4": self.f["fea89"], "cache": cache or self.f["cache"], "member_mask": self.f["mmask"], "raw_patch": self.f["rawp"],
               "hole_cells": self.f["hole"], "fp2_gate_lib": self.f["gatelib"], "controls_receipt": f"{self.R}/controls/CONTROLS.json", "control_dl_targets": self.f["cdlt"]}
        for k in drop: xin.pop(k, None)
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
