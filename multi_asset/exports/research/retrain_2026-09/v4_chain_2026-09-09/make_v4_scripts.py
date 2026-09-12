"""v4 copies of the three production scripts. Each = original verbatim + the minimum env plumbing; unified diffs printed and saved."""
import difflib, hashlib, json, os, re
GEN_OUT = os.environ.get("GEN_OUT", "/workspace/review_scratch")   # review b0a573a1 P1-REGEN: outputs + bases parametrised so regeneration can be TESTED bitwise
def diff(a, b, na, nb):
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), na, nb, lineterm="", n=0)); return "\n".join(d)
out = {}
# ---- 1) monthly-fold trainer ----
p = os.environ.get("GEN_TRAINER_BASE", "/workspace/review_scratch/allweather_trackB/pod_f10_train_monthly_earlystop.py"); s = open(p).read(); n = s
n = n.replace('and DLW == "/workspace/dlw_ext" and OUT == "/workspace/f8_ext", "env whitelist (production V2MAIN recipe on ext data) violated"',
              'and DLW in (_V4_DLW_RAW, _V4_DLW_CLIP) and OUT == _V4_F8, "env whitelist (V2MAIN recipe on the v4 chain) violated"   # v4: DLW/OUT re-pointed; monthly (2026-09-12): the admissible dirs come from the month env (V4_DLW_RAW/V4_DLW_CLIP/V4_F8, defaults = the September constants)')
n = n.replace("assert ARM == \"V2MAIN\" and V2 == 1 and SEED == 42 and COST == 3.52",
              '_V4_DLW_RAW = os.environ.get("V4_DLW_RAW", "/workspace/dlw_v4raw"); _V4_DLW_CLIP = os.environ.get("V4_DLW_CLIP", "/workspace/dlw_hf3"); _V4_F8 = os.environ.get("V4_F8", "/workspace/f8_v4")   # monthly: month-env dirs (defaults = September)\n'
              "assert ARM == \"V2MAIN\" and V2 == 1 and SEED in (42, 2027) and COST == 3.52")   # v4: SEED whitelist {42, 2027} (comment kept OUT of the continued statement); monthly 2026-09-12: admissible dirs from the month env
# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (a)/(c)): base-trainer locator from env; MONTHS_ALL derived/declared through v4_months.py (no hand-written 202501..202608)
n = n.replace('_BASE = "/workspace/pod_f10_train_ext.py"', '_BASE = os.environ.get("V4_BASE_TRAINER", "/workspace/pod_f10_train_ext.py")   # monthly (2026-09-12): locator from the month env; default = the September constant')
n = n.replace('"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE", "BEST_EP_FLOOR", "BEST_EP_FIX")},',
              '"F10_DLW", "F10_OUT", "MWF_OUT", "EMBARGO", "MWF_TAG", "MONTHS", "FORCE", "BEST_EP_FLOOR", "BEST_EP_FIX",\n'
              '                                                          "MONTHS_ALL", "V4_DLW_RAW", "V4_DLW_CLIP", "V4_F8", "V4_BASE_TRAINER", "V4_MONTH", "V4_MONTH_ENV")},')
_old_months = 'ALL_MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]\nMONTHS = [int(m) for m in os.environ.get("MONTHS", "").split(",") if m] or ALL_MONTHS\nassert all(m in ALL_MONTHS for m in MONTHS), MONTHS'
assert _old_months in n, "trainer base: month constant block not found"
n = n.replace(_old_months,
              '# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (a), review R2): the fold-month set is DECLARED by the month env (MONTHS_ALL) or DERIVED from the\n'
              '# targets axis (complete months 202501..last complete) — v4_months.py; a declared month the data cannot label is refused, MONTHS must be ⊆ MONTHS_ALL.\n'
              'import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_months import months_all as _months_all, parse_months as _parse_months, check_subset as _check_subset\n'
              'ALL_MONTHS = _months_all(os.environ.get("MONTHS_ALL"), E_ts)\n'
              'MONTHS = _parse_months(os.environ["MONTHS"]) if os.environ.get("MONTHS") else ALL_MONTHS\n'
              '_check_subset(MONTHS, ALL_MONTHS)\n'
              'rep["months_all"] = ALL_MONTHS; rep["months_all_source"] = "env MONTHS_ALL" if os.environ.get("MONTHS_ALL") else "derived from the targets axis (v4_months.months_all_from_axis)"')
assert "from v4_months import" in n and 'os.environ.get("V4_BASE_TRAINER"' in n and '"V4_MONTH_ENV")},' in n, "monthly trainer lines not emitted"
old_gate = s[s.index("_GATE_0901 = {"):s.index("_BASE = ")]
new_gate = ('_GATE_V4 = json.load(open(os.environ["F10_GATE_JSON"]))   # v4: identity gate against the v4 data chain receipt (targets/fea82/fea89 sha256), written by the chain\n'
            'for _k, _v in _GATE_V4.items():\n    assert rep[_k] == _v, f"{_k} differs from the v4 chain receipt: {rep[_k]} vs {_v}"\n')
n = n.replace(old_gate, new_gate)
assert n.count("v4:") == 2 and "SEED in (42, 2027)" in n, n.count("v4:"); open(os.path.join(GEN_OUT, "pod_f10_train_monthly_v4.py"), "w").write(n); out["trainer"] = diff(s, n, "pod_f10_train_monthly_earlystop.py", "pod_f10_train_monthly_v4.py")
# ---- 2) refit with FIX7 rule ----
p = os.environ.get("GEN_REFIT_BASE", "/workspace/pod_f10_refit_ext.py"); s = open(p).read(); n = s
_old_head = ('"""F-10 部署重训 @jpline: V2MAIN 冻结配方全史(→2026-08-10), 保存权重+标定+α(REVIEW §6.2)。"""\nimport os, json, time, math, hashlib\nimport numpy as np\nimport torch, torch.nn as nn\n'
             'ROOT = "/workspace"  # EXT_ENV line rewritten\nDLW = os.environ.get("F10_DLW", f"{ROOT}/dlw_ext")\nOUT = os.environ.get("F10_OUT", f"{ROOT}/f8_ext")\nSEED = int(os.environ.get("SEED", "42"))')
assert _old_head in n, "refit base: header block not found"
n = n.replace(_old_head, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_refit_head_2026-09-12.txt")).read().rstrip("\n"))   # monthly 2026-09-12 (review R1): env REQUIRED before importing torch
n = n.replace('    if va > best_va:\n        best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}',
              '    if (BEST_EP_FIX < 0 and va > best_va) or (BEST_EP_FIX >= 0 and ep == BEST_EP_FIX):   # v4: FIX rule keeps exactly epoch BEST_EP_FIX\n        best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}')
_old_tail = n[n.index('mdl.load_state_dict(best_state)\nos.makedirs(f"{OUT}/models", exist_ok=True)\ntorch.save({'):]
assert _old_tail.rstrip("\n").endswith('log(f"REFIT_DONE s{SEED} best_va {best_va:+.3f} α {float(mdl.alpha()):.3f} -> models/f10_live_s{SEED}.pt")'), "refit base: tail block not as expected"
n = n.replace(_old_tail, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_refit_tail_2026-09-12.txt")).read())   # monthly 2026-09-12: report = best_ep_rule + true label cutoff + sidecar json
assert n.count("v4:") == 2 and "REFIT_REFUSED" in n and '"trained_through_label_utc"' in n; open(os.path.join(GEN_OUT, "pod_f10_refit_v4.py"), "w").write(n); out["refit"] = diff(s, n, "pod_f10_refit_ext.py", "pod_f10_refit_v4.py")
# ---- 3) king bundle export ----
p = os.environ.get("GEN_EXPORT_BASE", "/workspace/pod_export_bundle_v3.py"); s = open(p).read(); n = s
n = n.replace('OUT = "/workspace/shadow_bundle_v3"', 'OUT = os.environ.get("BUNDLE_OUT", "/workspace/shadow_bundle_v4")   # v4')
# review b0a573a1 P1-REGEN: the archived exporter reads BUNDLE_BASE from env (AMENDMENT 2); regenerating used to restore the hard-coded v3 base and silently void the env.
n = n.replace('BASE = json.load(open("/workspace/slow_scorer_v3base.json"))  # Δ2', 'BASE = json.load(open(os.environ.get("BUNDLE_BASE", "/workspace/slow_scorer_v4base.json")))  # Δ2 (v4: base = v3 own fold IC, PREREG_v4 §2.3)')
assert 'os.environ.get("BUNDLE_BASE"' in n, "BUNDLE_BASE env line not emitted"
n = n.replace('FEA = np.load("/workspace/data/wide_fea_v2ext.npy")\nMT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)',
              'FEA = np.load(os.environ.get("BUNDLE_FEA", "/workspace/data/wide_fea_v4.npy"))   # v4\nMT = np.load(os.environ.get("BUNDLE_META", "/workspace/data/wide_fea_v4_meta.npz"), allow_pickle=True)')
n = n.replace('Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)', 'Z = zload(os.environ.get("BUNDLE_CACHE", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"), allow_pickle=True)   # v4')
n = n.replace('with tarfile.open("/workspace/shadow_bundle_v3.tar.gz", "w:gz") as t:', 'with tarfile.open(os.environ.get("BUNDLE_TAR", "/workspace/shadow_bundle_v4.tar.gz"), "w:gz") as t:   # v4')
n = n.replace("print(f\"BUNDLE_DONE files {len(man)} size {os.path.getsize('/workspace/shadow_bundle_v3.tar.gz')//1048576}MB\", flush=True)",
              "print(f\"BUNDLE_DONE files {len(man)} size {os.path.getsize(os.environ.get('BUNDLE_TAR', '/workspace/shadow_bundle_v4.tar.gz'))//1048576}MB\", flush=True)")
# round 3 (review 31fa3e4e §5): the archived exporter reads the guard band from env (PREREG_king_clock_E AMENDMENT 2) — the generator did not emit
# these lines, so a regeneration silently restored the fixed [2.27, 2.57] band and the frozen archive's own suite read 20/21.
n = n.replace("if not (2.27 <= sh <= 2.57):",
              '_GLO = float(os.environ.get("BUNDLE_GUARD_LO", "2.27")); _GHI = float(os.environ.get("BUNDLE_GUARD_HI", "2.57"))   # PREREG_king_clock_E AMENDMENT 2: band re-based for the [E+1,E+48] label; defaults verbatim\n'
              'print(f"guard band [{_GLO:.3f}, {_GHI:.3f}] {\'PASS\' if _GLO <= sh <= _GHI else \'FAIL\'}", flush=True)\n'
              "if not (_GLO <= sh <= _GHI):")
assert 'os.environ.get("BUNDLE_GUARD_LO"' in n and 'os.environ.get("BUNDLE_GUARD_HI"' in n, "BUNDLE_GUARD env lines not emitted"
# monthly 2026-09-12 (RUNBOOK_2026-10 §0★ 修订 2 (b), review R4): generation REQUIRED, LIVE_PINS/FUND_AUG/FUNDING_DIR from env, king training cutoff in provenance
_here = os.path.dirname(os.path.abspath(__file__))
_old_ehead = ('用法: python3 pod_export_bundle_v3.py\n"""\nimport os, io, csv, json, time, glob, gzip, zipfile, hashlib, tarfile\nimport numpy as np\nimport sys; sys.path.insert(0, "/workspace")\n'
              'from scipy.stats import rankdata, spearmanr\nfrom zload import zload\n')
assert _old_ehead in n, "exporter base: header block not found"
n = n.replace(_old_ehead, open(os.path.join(_here, "gen_export_head_2026-09-12.txt")).read())
n = n.replace('PINS = json.load(open("/workspace/live_pins.json"))          # Δ4/Δ5', 'PINS = json.load(open(os.environ.get("LIVE_PINS", "/workspace/live_pins.json")))          # Δ4/Δ5; monthly: env locator (default = September path)')
n = n.replace('import lightgbm as lgb\ntr = YRA < 2026; te = YRA == 2026',
              'import lightgbm as lgb\ntr = YRA < 2026; te = YRA == 2026\n'
              '_tr_anchors = np.unique(A[tr]); _king_train_end = int(E_ts[int(_tr_anchors.max())])   # 2026-09-12: the last anchor whose label entered the slow2026 fit (review R4)\n'
              'def _iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))\n'
              'print(f"king training set: {int(tr.sum())} rows / {len(_tr_anchors)} anchors, last training anchor {_iso(_king_train_end)} (label end {_iso(_king_train_end + 4 * 3600)}); axis end {_iso(E_ts[-1])}; generation {_GEN}", flush=True)')
n = n.replace('AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())',
              'AUG = json.loads(gzip.open(os.environ.get("FUND_AUG", "/workspace/fund_aug.json.gz"), "rt").read())   # monthly: env locator (default = September path)\n_FUNDING_DIR = os.environ.get("FUNDING_DIR", "/workspace/wide_multisrc/funding")')
n = n.replace('    for zp in sorted(glob.glob(f"/workspace/wide_multisrc/funding/{s}/*.zip")):', '    for zp in sorted(glob.glob(f"{_FUNDING_DIR}/{s}/*.zip")):')
_old_prov = n[n.index('           "provenance": {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),'):n.index('          open(f"{OUT}/config.json", "w"), indent=1)')]
assert '"generation": "v3_2026-09"' in _old_prov, "exporter base: provenance block not as expected"
n = n.replace(_old_prov, open(os.path.join(_here, "gen_export_prov_2026-09-12.txt")).read())
assert "_GEN" in n and '"king_train_end_utc"' in n and '"generation": "v3_2026-09"' not in n and "_FUNDING_DIR" in n, "monthly exporter lines not emitted"
assert n.count("# v4") == 4, n.count("# v4"); open(os.path.join(GEN_OUT, "pod_export_bundle_v4.py"), "w").write(n); out["bundle"] = diff(s, n, "pod_export_bundle_v3.py", "pod_export_bundle_v4.py")
for k, v in out.items(): print("=== %s ===\n%s\n" % (k, v))
json.dump({k: hashlib.sha256(open(f).read().encode()).hexdigest()[:16] for k, f in (("trainer_v4", os.path.join(GEN_OUT, "pod_f10_train_monthly_v4.py")), ("refit_v4", os.path.join(GEN_OUT, "pod_f10_refit_v4.py")), ("bundle_v4", os.path.join(GEN_OUT, "pod_export_bundle_v4.py")))}, open(os.path.join(GEN_OUT, "v4_scripts_sha.json"), "w"), indent=1)
import py_compile
for f in ("pod_f10_train_monthly_v4.py", "pod_f10_refit_v4.py", "pod_export_bundle_v4.py"): py_compile.compile(os.path.join(GEN_OUT, f), doraise=True)
print("all three compile")
