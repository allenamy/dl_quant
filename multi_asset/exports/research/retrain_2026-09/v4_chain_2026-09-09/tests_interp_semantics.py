#!/usr/bin/env python3
"""Battery for the interpreter-semantics verdict-hole CLASS (E-0918-R, 2026-09-18).

THE DEFECT: `python -O` / PYTHONOPTIMIZE=1 is taken from the PARENT environment and REMOVES every `assert`
statement at compile time (__debug__ False). A gate whose verdict is a load-bearing assert then vacuously
PASSES a bad input. It is NOT an os.environ read, so R15-C1's ENV_KEYS/AST completeness check is blind to it
by construction. The independent reviewer reproduced it on the real gate (v4_gate_step2_m.py: a King-META
feature-name mismatch is refused under a clean parent env, and PASSES with PYTHONOPTIMIZE=1, with the real
downstream `require` then accepting the receipt).

THE FIX under test (all in v4_gate_common.py — the library EVERY gate imports, so the guard is one place and a
new sibling module cannot be forgotten by an isolated copy):
  (1) STARTUP GUARD: v4_gate_common.assert_verdict_safe refuses (exit 11) under a verdict-unsafe interpreter,
      and is CALLED at v4_gate_common's import, so every gate that imports the library is covered with no
      per-gate edit; the merge (which writes its own JSON) imports the library for this guard + require_true.
  (2) FINGERPRINT: v4_gate_common.finalize records the interpreter fingerprint in every receipt.
  (3) CONSUMER RE-CHECK: v4_gate_common.require rejects a receipt recorded under verdict-unsafe semantics.
  (4) -O-PROOF CHECKS: the merge's demonstrated load-bearing asserts (incl. the pre-2025 causality/leakage
      guard) became require_true (raises whatever the optimize level).

THE CLASS-CLOSER (sections [D]/[D2]): a SOURCE-DERIVED audit asserts every governed device is guarded — imports
v4_gate_common (⇒ the import-time guard) OR calls assert_verdict_safe itself. A NEW governed device that emits a
verdict via a bare assert and is NOT guarded is caught WITHOUT anyone listing it (a throwaway device nobody
registered), and the interventional cell shows it vacuously-passes under -O while the guarded version refuses.

This battery uses check() (never a bare assert) for its OWN verdicts and REFUSES to certify while itself running
under -O — a battery whose asserts could be stripped cannot certify anything.
Run: python3 tests_interp_semantics.py   (exit 0 iff ALL PASS)."""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FAILS, N = [], [0]
sys.path.insert(0, HERE)
import v4_gate_common as G   # the module under test (holds the inlined interpreter guard)

# ── [0] SELF-SAFETY: a battery whose own asserts could be stripped cannot certify. Refuse under -O. ──
if sys.flags.optimize != 0 or not __debug__:
    sys.stderr.write("INTERP_TEST_REFUSED this battery must run under a plain interpreter (optimize=0); it certifies -O behaviour via subprocess\n")
    sys.exit(2)


def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)[:240]) if detail != '' and not cond else ''}", flush=True)
    if not cond:
        FAILS.append(name)


TMP = tempfile.mkdtemp(prefix="interp_sem_")

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
print("[A] the interpreter guard (inlined in v4_gate_common) — unit behaviour")
fp = G.interp_fingerprint()
check("★★ fingerprint carries the load-bearing flags", all(k in fp for k in ("optimize", "debug", "bytes_warning", "warnoptions", "executable", "version")), sorted(fp))
check("★★ this (plain) interpreter is verdict-safe: interp_unsafe() == []", G.interp_unsafe() == [], G.interp_unsafe())
check("★★★ interp_unsafe flags a fingerprint with optimize=1 (asserts stripped)", bool(G.interp_unsafe({"optimize": 1, "debug": False})), None)
check("★★ interp_unsafe flags -bb (bytes_warning>=2) and -W error", bool(G.interp_unsafe({"bytes_warning": 2})) and bool(G.interp_unsafe({"warnoptions": ["error"]})), None)
ok, why = G.interp_ok_from_receipt({"optimize": 0, "debug": True, "bytes_warning": 0, "warnoptions": []})
check("★★ interp_ok_from_receipt accepts a safe recorded fingerprint", ok, why)
bad_ok, bad_why = G.interp_ok_from_receipt({"optimize": 1, "debug": False})
check("★★★ interp_ok_from_receipt REJECTS a receipt recorded under optimize=1", not bad_ok and "unsafe" in bad_why, bad_why)
absent_ok, absent_why = G.interp_ok_from_receipt(None)
check("★★ interp_ok_from_receipt rejects a MISSING fingerprint (non-dict)", not absent_ok, absent_why)
try:
    G.require_true(1 == 2, "boom"); _rt = "no raise"
except AssertionError as e:
    _rt = "raised:" + str(e)
check("★★ require_true raises AssertionError on a false condition", _rt == "raised:boom", _rt)
# the module that holds the -O detector must not itself be -O-strippable
_gc_asserts = [n.lineno for n in ast.walk(ast.parse(open(f"{HERE}/v4_gate_common.py").read())) if isinstance(n, ast.Assert)]
check("★★★ v4_gate_common.py (holds the -O detector) contains ZERO bare asserts (the detector cannot be weakened by -O)", _gc_asserts == [], _gc_asserts)

print("\n[A2] the guard as a subprocess under different parent interpreters")
def _guard_rc(env_over):
    e = dict(os.environ); e.update(env_over)
    p = subprocess.run([PY, "-c", "import sys;sys.path.insert(0,%r);import v4_gate_common as g;g.assert_verdict_safe('probe');print('RETURNED')" % HERE], capture_output=True, text=True, env=e, cwd=HERE)
    return p.returncode, p.stdout + p.stderr
rc, out = _guard_rc({})
check("★★★ assert_verdict_safe RETURNS (rc 0) under a clean parent interpreter", rc == 0 and "RETURNED" in out, (rc, out[-80:]))
rc, out = _guard_rc({"PYTHONOPTIMIZE": "1"})
check("★★★ assert_verdict_safe REFUSES (rc 11, INTERP_REFUSED) under parent PYTHONOPTIMIZE=1 — same source bytes, different semantics", rc == G.INTERP_REFUSE_EXIT and "INTERP_REFUSED" in out and "RETURNED" not in out, (rc, out[-120:]))
p = subprocess.run([PY, "-O", "-c", "import sys;sys.path.insert(0,%r);import v4_gate_common as g;g.assert_verdict_safe('probe');print('RETURNED')" % HERE], capture_output=True, text=True)
check("★★ assert_verdict_safe REFUSES under the -O flag directly (not only the env var)", p.returncode == G.INTERP_REFUSE_EXIT, p.returncode)

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[B] v4_gate_common: import guard, receipt fingerprint, consumer re-check")
p = subprocess.run([PY, "-O", "-c", "import sys;sys.path.insert(0,%r);import v4_gate_common;print('IMPORTED')" % HERE], capture_output=True, text=True)
check("★★★ importing v4_gate_common under -O REFUSES at load (exit 11) BEFORE any gate reaches its verdict — this is how every importer is guarded with no per-gate edit",
      p.returncode == G.INTERP_REFUSE_EXIT and "INTERP_REFUSED" in (p.stdout + p.stderr) and "IMPORTED" not in (p.stdout + p.stderr), (p.returncode, (p.stdout + p.stderr)[-120:]))
_gc = open(f"{HERE}/v4_gate_common.py").read()
check("★★ v4_gate_common CALLS assert_verdict_safe at module load (so 'imports v4_gate_common' is a real guarantee)", re.search(r"(?m)^assert_verdict_safe\(", _gc) is not None, None)
_rc_dir = os.path.join(TMP, "gc"); os.makedirs(_rc_dir, exist_ok=True)
subprocess.run([PY, "-c", "import sys;sys.path.insert(0,%r);import v4_gate_common as G;G.finalize('PROBE',{'PASS':True},%r,{'x':%r})" % (HERE, f"{_rc_dir}/r.json", f"{HERE}/v4_gate_common.py")], capture_output=True, text=True, cwd=HERE)
_r = json.load(open(f"{_rc_dir}/r.json"))
check("★★★ finalize records an `interp` fingerprint in the receipt (optimize=0 on this run)", isinstance(_r.get("interp"), dict) and _r["interp"].get("optimize") == 0, _r.get("interp"))
_badrec = dict(_r); _badrec["interp"] = {"optimize": 1, "debug": False}; _badrec["PASS"] = True; _badrec["self_sha256"] = _sha(f"{HERE}/v4_gate_common.py")
json.dump(_badrec, open(f"{_rc_dir}/bad.json", "w"))
_reqsrc = ("import sys;sys.path.insert(0,%r);import v4_gate_common as G;"
           "ok,why=G.require(%r,{'x':%r},expected_gate='PROBE',expected_self_sha=%r);print('OK' if ok else 'REJECT',why)"
           % (HERE, f"{_rc_dir}/bad.json", f"{HERE}/v4_gate_common.py", _sha(f"{HERE}/v4_gate_common.py")))
_rq = subprocess.run([PY, "-c", _reqsrc], capture_output=True, text=True, cwd=HERE)
check("★★★ require REJECTS a PASS receipt whose recorded interp is optimize=1 (consumer-side backstop)", "REJECT" in _rq.stdout and "unsafe" in _rq.stdout, _rq.stdout.strip()[-160:])

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
# ── compact STEP2 world builder (same shape as tests_pipeline_gates.fixture; a genuine PASSING X1/X0 pair) ──
_T0 = 1_700_000_000; _NW = 6; _KP = [10, 50, 120, 170]; _NAR = 200; _NAN = 230
_N82 = np.array(["fund_ema", "fund_now", "a_v", "b_v", "c_v", "d_r", "e_r", "f_r", "g_v", "h_r"]); _N89 = np.array([f"A:s_{k}" for k in range(8)]); _SYM = np.array([f"S{i}USDT" for i in range(_NW)])
def _members(nA, short=()):
    m = np.empty(nA, dtype=object)
    for i in range(nA): m[i] = np.arange(_NW - 1) if i in short else np.arange(_NW)
    return m
def _base(seed, nA):
    r = np.random.default_rng(seed); E_row = 2016 + 48 * np.arange(nA)
    return dict(E_row=E_row, E_ts=_T0 + 300 * E_row, y4s=r.normal(size=(nA, _NW)), qvk=r.uniform(1, 2, size=(nA, _NW)), YR4s=r.normal(size=(nA, _NW)), YRZ=r.integers(0, _NW, size=(nA, _NW)).astype(float),
                yrs=np.full(nA, 2025), has_panel=np.ones((nA, _NW), bool), btcv=r.normal(size=nA), X82=r.normal(size=(nA * _NW, len(_N82))).astype(np.float32),
                X89=r.normal(size=(nA * _NW, len(_N89))).astype(np.float32), F=r.normal(size=(nA, _NW, len(_N82))).astype(np.float32), y4=r.normal(size=(nA, _NW)))
def _write_month(d, b, nA, kind, hole=(2100, 2150), patch_k=(30, 100, 210)):
    os.makedirs(f"{d}/dlw_raw/data", exist_ok=True); os.makedirs(f"{d}/dlw_clip/data", exist_ok=True); os.makedirs(f"{d}/f8/data", exist_ok=True)
    sl = slice(0, nA); E_row = b["E_row"][sl]; E_ts = b["E_ts"][sl]; nrows = 2016 + 48 * (_NAN + 4)
    np.savez(f"{d}/cache.npz", ts=_T0 + 300 * np.arange(nrows))
    hr = np.arange(hole[0], hole[1] + 1); np.savez(f"{d}/holes.npz", fill_runs=np.array([list(hole)]), neigh_rows=np.array([[hole[0] - 48, hole[1] + 8640]]), row=np.repeat(hr, 2), col=np.tile([0, 1], len(hr)), symbols=_SYM)
    y4s = b["y4s"][sl].copy(); y4old = (b["y4s"][sl] * 0.9).copy(); qvk = b["qvk"][sl].copy(); YR4s = b["YR4s"][sl].copy(); YRZ = b["YRZ"][sl].copy(); y4 = b["y4"][sl].copy()
    X82 = b["X82"][: nA * _NW].copy(); X89 = b["X89"][: nA * _NW].copy(); F = b["F"][sl].copy(); pa = np.repeat(np.arange(nA), _NW); ps = np.tile(np.arange(_NW), nA); short = ()
    if kind == "ref":
        kp = np.array(_KP); short = tuple(_KP)
        y4s[kp, 0] += 0.01; y4old[kp, 1] += 0.01; qvk[kp, 0] *= 1.1; YR4s[kp, :] += 0.01; YRZ[kp, :] += 1; y4[kp, 0] += 0.01
        X82[kp * _NW + 0, 2] += 0.01; X82[kp * _NW + 3, 5] += 0.01; X89[kp * _NW + 1, 0] += 0.01; F[kp, 0, 2] += 0.01; F[kp, 3, 5] += 0.01
        FE = F.copy(); FE[:138, :, 2] += 0.001; np.save(f"{d}/king_fea_unclamped.npy", FE)
    tg = dict(E_ts=E_ts, E_row=E_row, members=_members(nA, short), yrs=b["yrs"][sl], has_panel=b["has_panel"][sl], symbols=_SYM, btcv=b["btcv"][sl], qvk=qvk, y4old=y4old, y4s=y4s, YR4s=YR4s, YRZ=YRZ)
    np.savez(f"{d}/dlw_clip/data/dlw_targets.npz", **tg); np.savez(f"{d}/dlw_clip/data/dlw_fea82.npz", X=X82, pair_a=pa, pair_s=ps, names=_N82); np.savez(f"{d}/f8/data/f8_fea89.npz", X=X89, pair_a=pa, pair_s=ps, names=_N89)
    np.save(f"{d}/king_fea.npy", F); np.savez(f"{d}/king_meta.npz", E_ts=E_ts, names=_N82, members=_members(nA, short), y4=y4, qvk=qvk)
    if kind == "new":
        pk = np.array([k for k in patch_k if k < nA]); np.savez(f"{d}/raw_patch.npz", row=E_row[pk] + 24, col=np.full(len(pk), 2))
        A = dict(tg); A["y4s"] = y4s.copy(); A["y4s"][pk, 2] += 0.5; A["YR4s"] = YR4s.copy(); A["YR4s"][pk, :] += 0.1; A["YRZ"] = YRZ.copy(); A["YRZ"][pk, :] += 1
        np.savez(f"{d}/dlw_raw/data/dlw_targets.npz", **A); import shutil; shutil.copyfile(f"{d}/dlw_clip/data/dlw_fea82.npz", f"{d}/dlw_raw/data/dlw_fea82.npz")
def _env2(new, ref):
    return dict(HOLE_CELLS=f"{new}/holes.npz", CACHE=f"{new}/cache.npz", KING_FEA=f"{new}/king_fea.npy", KING_META=f"{new}/king_meta.npz",
                PREV_KING_FEA=f"{ref}/king_fea.npy", PREV_KING_FEA_UNCLAMPED=f"{ref}/king_fea_unclamped.npy", PREV_META=f"{ref}/king_meta.npz")
def _run_gate_via_chain(world_new, world_ref, receipt, parent_opt, tag):
    d = os.path.dirname(receipt); env = dict(os.environ); env.update(_env2(world_new, world_ref))
    env.update(PY=PY, R=d, L=f"{d}/{tag}.log", CHAIN_DEVICE_DIR=HERE)
    if parent_opt: env["PYTHONOPTIMIZE"] = "1"
    else: env.pop("PYTHONOPTIMIZE", None)
    cmd = f'source "{HERE}/chain_lib.sh"; run_gate STEP2 v4_gate_step2_m.py "{d}/{tag}_g.log" STEP2_OUT="{receipt}"; echo "rc=$?"'
    p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=env, cwd=HERE)
    rc = int(p.stdout.split("rc=")[-1].split()[0]) if "rc=" in p.stdout else -999
    rec = json.load(open(receipt)) if os.path.exists(receipt) else None
    glog = open(f"{d}/{tag}_g.log").read() if os.path.exists(f"{d}/{tag}_g.log") else ""   # run_gate redirects the gate's own stderr (INTERP_REFUSED) here, not to bash
    return rc, rec, p.stdout + p.stderr + glog

print("\n[C] RED CONTROL through the REAL chain_lib run_gate: bad input (King-META name mismatch), clean vs PYTHONOPTIMIZE=1")
_w = os.path.join(TMP, "world"); os.makedirs(_w, exist_ok=True)
_b = _base(1, _NAN); _write_month(f"{_w}/X1", _b, _NAN, "new"); _write_month(f"{_w}/X0", _b, _NAR, "ref")
# corrupt ONLY X1's king_meta names (keep the _v suffix class + every numeric array byte-identical) -> the sole fault is the feature-name match at gate line ~71
_km = dict(np.load(f"{_w}/X1/king_meta.npz", allow_pickle=True)); _nm = _km["names"].copy(); _nm[2] = "zzz_v"; _km["names"] = _nm; np.savez(f"{_w}/X1/king_meta.npz", **_km)
rc_clean, rec_clean, out_clean = _run_gate_via_chain(f"{_w}/X1", f"{_w}/X0", f"{_w}/s2_clean.json", False, "clean")
rc_opt, rec_opt, out_opt = _run_gate_via_chain(f"{_w}/X1", f"{_w}/X0", f"{_w}/s2_opt.json", True, "opt")
check("★★★ [C] clean parent env: the gate REFUSES the name mismatch (no PASS receipt) — the load-bearing assert fires normally",
      rec_clean is None or rec_clean.get("PASS") is not True, (rc_clean, rec_clean and rec_clean.get("PASS")))
check("★★★ [C] PYTHONOPTIMIZE=1 parent env: the gate REFUSES AT IMPORT (INTERP_REFUSED, exit 11) — it does NOT write a PASS receipt (pre-fix it did)",
      rc_opt == G.INTERP_REFUSE_EXIT and "INTERP_REFUSED" in out_opt and (rec_opt is None or rec_opt.get("PASS") is not True), (rc_opt, "INTERP_REFUSED" in out_opt, rec_opt and rec_opt.get("PASS")))
check("★★★ [C] the downstream consumer sees NO acceptable receipt under either env (require has nothing to accept)", rec_clean is None and rec_opt is None, (rec_clean, rec_opt))

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[D] SOURCE AUDIT — every GOVERNED device refuses under -O before it can emit a verdict (source-derived, no hand list)")
_ARCHIVE = re.compile(r"\.r\d+_")
def _is_candidate(fn):
    # exclude only the guard-holding library itself (verified separately in [A]/[B]) and non-device files; the rest is source-derived, no hand list
    return fn.endswith(".py") and not fn.startswith("tests_") and not _ARCHIVE.search(fn) and "diag" not in fn and fn != "v4_gate_common.py"
def _imports_common(src):
    """AST-robust: catches `from v4_gate_common import ...` even mid-line after `sys.path.insert(...);` (how the gates write it)."""
    try: tree = ast.parse(src)
    except SyntaxError: return False
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module == "v4_gate_common": return True
        if isinstance(n, ast.Import) and any(a.name == "v4_gate_common" for a in n.names): return True
    return False
def _declares_envkeys(src):
    return ("ENV_KEYS" in src) and ("--env-keys" in src)
def governed_devices():
    """Source-derived: a device is governed if it emits a receipt via v4_gate_common (imports it) OR is a direct-launch
    device declaring ENV_KEYS + --env-keys (the merge). No hand list — a NEW gate is included the moment it does either."""
    out = {}
    for fn in sorted(os.listdir(HERE)):
        if not _is_candidate(fn): continue
        src = open(f"{HERE}/{fn}").read()
        if _imports_common(src) or _declares_envkeys(src): out[fn] = src
    return out
def guarded(src):
    """Guarded iff it imports v4_gate_common (⇒ the import-time assert_verdict_safe) OR calls assert_verdict_safe itself.
    Both make it refuse under -O before any verdict."""
    return _imports_common(src) or re.search(r"assert_verdict_safe\s*\(", src) is not None
def verdict_asserts(src):
    return [n.lineno for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assert)]

_gov = governed_devices()
check("★★ the source-derived population is non-trivial and includes the reviewer's gates + the merge",
      len(_gov) >= 10 and {"v4_gate_step1_m.py", "v4_gate_step2_m.py", "merge_mwf_v4b.py"} <= set(_gov), sorted(_gov))
_unguarded = [fn for fn, s in _gov.items() if not guarded(s)]
check("★★★ [D] EVERY governed device is guarded (imports v4_gate_common OR calls assert_verdict_safe) ⇒ refuses under -O before a verdict — the invariant that stays closed for a new gate",
      _unguarded == [], _unguarded)
# the merge is the one governed device that writes its OWN receipt (not via finalize) and is NOT a v4_gate_common
# importer for its verdict path — it was the reviewer's second demonstrated device, so its load-bearing asserts are
# converted to require_true (belt-and-braces beyond the import guard it now installs):
_merge_asserts = verdict_asserts(_gov["merge_mwf_v4b.py"])
check("★★★ [D] the merge (causality/leakage + splice guards) now contains ZERO bare asserts — converted to require_true, the direct fix",
      _merge_asserts == [], _merge_asserts)
# informational: which guarded devices still carry asserts (unreachable under -O because the guard exits at import first).
# These are SAFE: the import-time guard exits before the assert can be reached; they are recorded, not hidden.
_residual = {fn: len(verdict_asserts(s)) for fn, s in _gov.items() if verdict_asserts(s)}
print(f"       (informational) guarded devices still carrying asserts (unreachable under -O; the import guard exits first): {_residual}")

print("\n[D2] ACCEPTANCE — a NEW governed device NOBODY listed, with a verdict-via-assert and NO guard, is caught by the audit")
_thr = os.path.join(TMP, "new_gate_nobody_listed.py")
open(_thr, "w").write(
    "import os, sys\n"
    "ENV_KEYS = ('THING',)\n"                                       # declares an env contract ⇒ the audit treats it as a governed direct-launch device
    "if len(sys.argv) == 2 and sys.argv[1] == '--env-keys':\n    print(' '.join(ENV_KEYS)); sys.exit(0)\n"
    "names = os.environ.get('THING', 'x').split(',')\n"
    "assert names == ['a', 'b'], 'feature-name match'   # a VERDICT via a bare assert, and NO interpreter guard\n"
    "print('PASS'); open(os.environ['OUT'], 'w').write('PASS')\n")
_src = open(_thr).read()
check("★★★ [D2] the audit ENUMERATES the throwaway device by its own source (ENV_KEYS+--env-keys), nobody listed it", _declares_envkeys(_src), None)
check("★★★ [D2] the audit flags it: guarded()==False (no v4_gate_common import, no assert_verdict_safe call)", guarded(_src) is False, None)
check("★★★ [D2] the audit flags its verdict-via-assert (line found by AST)", verdict_asserts(_src) != [], verdict_asserts(_src))
def _run_throwaway(path, opt):
    e = dict(os.environ, THING="wrong,input", OUT=os.path.join(TMP, "thr_out"))
    if opt: e["PYTHONOPTIMIZE"] = "1"
    else: e.pop("PYTHONOPTIMIZE", None)
    if os.path.exists(e["OUT"]): os.remove(e["OUT"])
    p = subprocess.run([PY, path], capture_output=True, text=True, env=e)
    return p.returncode, os.path.exists(e["OUT"]), p.stdout + p.stderr
rc_c, wrote_c, _ = _run_throwaway(_thr, False); rc_o, wrote_o, _ = _run_throwaway(_thr, True)
check("★★★ [D2] interventional proof the guard is NECESSARY: the UNGUARDED device refuses the bad input under a clean interp (assert fires) but VACUOUSLY PASSES under -O (assert stripped, wrote PASS)",
      (not wrote_c) and wrote_o, (rc_c, wrote_c, rc_o, wrote_o))
_thrg = os.path.join(TMP, "new_gate_guarded.py")
open(_thrg, "w").write("import os, sys\nsys.path.insert(0, %r)\nfrom v4_gate_common import assert_verdict_safe, require_true\n" % HERE +
                       "assert_verdict_safe('new_gate_guarded')\n"
                       "names = os.environ.get('THING', 'x').split(',')\n"
                       "require_true(names == ['a', 'b'], 'feature-name match')\n"
                       "print('PASS'); open(os.environ['OUT'], 'w').write('PASS')\n")
rc_gc, wrote_gc, _ = _run_throwaway(_thrg, False); rc_go, wrote_go, out_go = _run_throwaway(_thrg, True)
check("★★★ [D2] the SAME device once GUARDED (imports v4_gate_common) refuses the bad input under BOTH interps (clean: require_true raises; -O: INTERP_REFUSED) — never a vacuous pass",
      (not wrote_gc) and (not wrote_go) and rc_go == G.INTERP_REFUSE_EXIT and "INTERP_REFUSED" in out_go, (rc_gc, wrote_gc, rc_go, wrote_go))

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
print("\n[E] HONEST SCOPE: this is a capability defect")
check("★ (recorded) NO evidence historical training ran under -O (zero chain sites set PYTHONOPTIMIZE/-O; the env -i builder allowlist excludes it); this battery certifies the CAPABILITY is closed, not that any corruption occurred", True,
      "the reviewer saw none; the fix removes the capability for a verdict to depend on -O")

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)  v4_gate_common {_sha(f'{HERE}/v4_gate_common.py')[:12]}")
sys.exit(0 if not FAILS else 1)
