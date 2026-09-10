"""v4 copies of the three production scripts. Each = original verbatim + the minimum env plumbing; unified diffs printed and saved."""
import difflib, hashlib, json, os, re
GEN_OUT = os.environ.get("GEN_OUT", "/workspace/review_scratch")   # review b0a573a1 P1-REGEN: outputs + bases parametrised so regeneration can be TESTED bitwise
def diff(a, b, na, nb):
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), na, nb, lineterm="", n=0)); return "\n".join(d)
out = {}
# ---- 1) monthly-fold trainer ----
p = os.environ.get("GEN_TRAINER_BASE", "/workspace/review_scratch/allweather_trackB/pod_f10_train_monthly_earlystop.py"); s = open(p).read(); n = s
n = n.replace('and DLW == "/workspace/dlw_ext" and OUT == "/workspace/f8_ext", "env whitelist (production V2MAIN recipe on ext data) violated"',
              'and DLW in ("/workspace/dlw_v4raw", "/workspace/dlw_hf3") and OUT == "/workspace/f8_v4", "env whitelist (V2MAIN recipe on the v4 chain) violated"   # v4: DLW/OUT re-pointed')
n = n.replace("assert ARM == \"V2MAIN\" and V2 == 1 and SEED == 42 and COST == 3.52", "assert ARM == \"V2MAIN\" and V2 == 1 and SEED in (42, 2027) and COST == 3.52")   # v4: SEED whitelist {42, 2027} (comment kept OUT of the continued statement)
old_gate = s[s.index("_GATE_0901 = {"):s.index("_BASE = ")]
new_gate = ('_GATE_V4 = json.load(open(os.environ["F10_GATE_JSON"]))   # v4: identity gate against the v4 data chain receipt (targets/fea82/fea89 sha256), written by the chain\n'
            'for _k, _v in _GATE_V4.items():\n    assert rep[_k] == _v, f"{_k} differs from the v4 chain receipt: {rep[_k]} vs {_v}"\n')
n = n.replace(old_gate, new_gate)
assert n.count("v4:") == 2 and "SEED in (42, 2027)" in n, n.count("v4:"); open(os.path.join(GEN_OUT, "pod_f10_train_monthly_v4.py"), "w").write(n); out["trainer"] = diff(s, n, "pod_f10_train_monthly_earlystop.py", "pod_f10_train_monthly_v4.py")
# ---- 2) refit with FIX7 rule ----
p = os.environ.get("GEN_REFIT_BASE", "/workspace/pod_f10_refit_ext.py"); s = open(p).read(); n = s
n = n.replace('SEED = int(os.environ.get("SEED", "42"))', 'SEED = int(os.environ.get("SEED", "42")); BEST_EP_FIX = int(os.environ.get("BEST_EP_FIX", "-1"))   # v4: -1 = verbatim argmax; k = keep exactly epoch k (FIX rule)')
n = n.replace('    if va > best_va:\n        best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}',
              '    if (BEST_EP_FIX < 0 and va > best_va) or (BEST_EP_FIX >= 0 and ep == BEST_EP_FIX):   # v4: FIX rule keeps exactly epoch BEST_EP_FIX\n        best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}')
n = n.replace('"seed": SEED, "n_cols": int(XT.shape[1]), "va_curve": curve, "best_va": best_va,', '"seed": SEED, "n_cols": int(XT.shape[1]), "va_curve": curve, "best_va": best_va, "best_ep_rule": ("fix%d" % BEST_EP_FIX if BEST_EP_FIX >= 0 else "argmax"),')
assert n.count("v4:") == 2; open(os.path.join(GEN_OUT, "pod_f10_refit_v4.py"), "w").write(n); out["refit"] = diff(s, n, "pod_f10_refit_ext.py", "pod_f10_refit_v4.py")
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
assert n.count("# v4") == 4, n.count("# v4"); open(os.path.join(GEN_OUT, "pod_export_bundle_v4.py"), "w").write(n); out["bundle"] = diff(s, n, "pod_export_bundle_v3.py", "pod_export_bundle_v4.py")
for k, v in out.items(): print("=== %s ===\n%s\n" % (k, v))
json.dump({k: hashlib.sha256(open(f).read().encode()).hexdigest()[:16] for k, f in (("trainer_v4", os.path.join(GEN_OUT, "pod_f10_train_monthly_v4.py")), ("refit_v4", os.path.join(GEN_OUT, "pod_f10_refit_v4.py")), ("bundle_v4", os.path.join(GEN_OUT, "pod_export_bundle_v4.py")))}, open(os.path.join(GEN_OUT, "v4_scripts_sha.json"), "w"), indent=1)
import py_compile
for f in ("pod_f10_train_monthly_v4.py", "pod_f10_refit_v4.py", "pod_export_bundle_v4.py"): py_compile.compile(os.path.join(GEN_OUT, f), doraise=True)
print("all three compile")
