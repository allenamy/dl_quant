"""tests_judge_dynamic_deps.py — ROUND 8 (independent review B-R2, 2026-09-12; DESIGN_judge_floor_28 §9): the judge verifies every input the
RECEIPT recorded, not only the caller's declaration.

The reviewer's cell "dynamic extra": a valid v2-shaped receipt that additionally recorded a FEMAT sha; after the FEMAT changes, a caller that OMITS
`femat` from its JUDGE_ELIGIBILITY entry got eligibility.ok=True (round 7), while a caller that DECLARED it got False. The 28-name static floor
cannot see conditional inputs (femat / signal_receipt exist only for FEMAT-injected arms). Fix: judge_v4._eligibility -> v4_gate_common.require(...,
recorded_extras=True): every name in receipt.inputs_sha256 beyond the caller's inputs + the judge-bound names is located from receipt.inputs_path
and verified; a recorded name with no locatable path is refused.

Cells (each on a fresh synthetic world: 7 arms x 4 cells x 3168 anchors, A1e +1 bps so a PROMOTE would be visible; device copy = judge + common +
the ARCHIVED contract, receipts signed with the archived v2 gate's sha, which that contract approves):
  (i)    recorded femat, FEMAT changed after the receipt, caller omits femat      -> NOT eligible, why names 'femat' changed, 0 PROMOTE
  (ii)   recorded femat unchanged, caller omits femat                             -> eligible (verified from the receipt), 29 inputs, 4 PROMOTE
  (iii)  recorded femat but inputs_path lacks it                                  -> refused 'recorded conditional input ... no locatable path'
  (iv)   no extras (the real A1 shape)                                            -> eligible as before; static: the real A1 receipt has no extras
  (v)    OLD judge (judge_v4.r5_f6850dc3.py) on cell (i)                          -> eligible (old code red)
  + caller declares the changed femat (both rounds refuse); two extras with the second changed; extra recorded with sha None; extra file deleted;
    unit-level require with recorded_extras False/True and the CLI flag.
Run: /usr/bin/python3 tests_judge_dynamic_deps.py   (exit 0 iff every cell behaves). Kept separate from tests_pipeline_gates.py (under concurrent edit)."""
import calendar
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FAILS, N = [], [0]


def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail != '' else ''}", flush=True)
    if not cond:
        FAILS.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    p = subprocess.run([PY] + args, capture_output=True, text=True, env=e, cwd=HERE)
    return p.returncode, p.stdout + p.stderr


V2 = _sha(f"{HERE}/v4e_gate_export_v2.py")
R5 = f"{HERE}/judge_v4.r5_f6850dc3.py"
UPSTREAM = ("wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins")
BUNDLE_FILES = ("slow_pred_pinned.npy", "slow2026.txt", "config.json", "cache_tail_40d.npz", "fund_ema_v1_state.json", "funding_ledger_seed.json", "leg_returns.npz", "parity_signals_aug.json")
MISC3 = ("costb_json", "umask_npz", "slow_npy")
ARMS = ("A0", "A0p", "A1", "A1s", "A1e", "A2", "A3")


def world(q, promote_arm="A1e"):
    """Synthetic arms + RAW references on the exact frozen axis; promote_arm carries +1 bps so its (A) cells would read PROMOTE when eligible."""
    hc = f"{q}/hc"; v = f"{hc}/dev_v4/probe_artifacts"; old = f"{hc}/dev_raw/probe_artifacts"; os.makedirs(v); os.makedirs(old)
    ts = calendar.timegm((2025, 3, 1, 0, 0, 0)) + np.arange(3168) * 14400
    for arm in ARMS:
        for seat in ("dyn", "fix"):
            for seed in (42, 2027):
                r = np.zeros((len(ts), 23)); r[:, 0] = ts; r[:, 5] = 1.0; r[:, 18] = 2.0 if arm == promote_arm else 1.0; r[:, 19] = r[:, 18]
                np.savez(f"{v}/w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz", d30_n2_c42_rec=r)
    for seed in (42, 2027):
        r = np.zeros((len(ts), 23)); r[:, 0] = ts; r[:, 5] = 1.0; r[:, 18] = 1.0; r[:, 19] = 1.0
        np.savez(f"{old}/w10_ablation_series_RAW_M1_UCRYPTO_s{seed}.npz", d30_n2_c42_rec=r)
    return hc


def device(q, judge_src=None):
    """Device copy: the judge under test (default: the archived current one), the archived common, the archived (shipped) contract."""
    d = f"{q}/device"; os.makedirs(d)
    shutil.copy(judge_src or f"{HERE}/judge_v4.py", f"{d}/judge_v4.py"); shutil.copy(f"{HERE}/v4_gate_common.py", f"{d}/v4_gate_common.py")
    shutil.copy(f"{HERE}/ELIGIBILITY_CONTRACT.json", f"{d}/ELIGIBILITY_CONTRACT.json")
    return d


def receipt(q, arm="A1e", extras=None, path_missing=(), sha_none=()):
    """A v2-signed BUNDLE_export receipt over the 28-name closure, plus `extras` {name: path} recorded the way the v2 gate records femat /
    signal_receipt for a FEMAT arm. Returns (receipt_path, caller_inputs) where caller_inputs = the 24 names a standalone locator declares
    (no books, no extras). path_missing: extras recorded in inputs_sha256 but absent from inputs_path. sha_none: extras recorded with sha None."""
    inputs = {}
    for k in UPSTREAM + MISC3:
        open(f"{q}/{arm}_{k}.bin", "wb").write(f"{arm}:{k}".encode()); inputs[k] = f"{q}/{arm}_{k}.bin"
    for seat in ("dyn", "fix"):
        for seed in (42, 2027):
            inputs[f"base_{seat}_s{seed}"] = f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{seed}.npz"
    bdir = f"{q}/{arm}_bundle"; os.makedirs(bdir, exist_ok=True); man = {}
    for f in BUNDLE_FILES:
        open(f"{bdir}/{f}", "wb").write(f"{arm}:bundle:{f}".encode()); man[f] = _sha(f"{bdir}/{f}"); inputs[f"bundle/{f}"] = f"{bdir}/{f}"
    json.dump(man, open(f"{bdir}/MANIFEST.json", "w")); inputs["bundle_manifest"] = f"{bdir}/MANIFEST.json"
    inputs["eligibility_contract"] = f"{q}/device/ELIGIBILITY_CONTRACT.json"
    caller = dict(inputs)
    for seat in ("dyn", "fix"):
        for seed in (42, 2027):
            inputs[f"book_{seat}_s{seed}"] = f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz"
    inputs.update(extras or {})
    shas = {k: (None if k in sha_none else _sha(p)) for k, p in inputs.items()}
    paths = {k: p for k, p in inputs.items() if k not in path_missing}
    rec = {"gate": "BUNDLE_export", "PASS": True, "arm": arm, "self_sha256": V2, "inputs_sha256": shas, "inputs_path": paths, "utc": "2026-09-12T00:00:00Z",
           "receipt_schema": "v4_gate_common/2 (gate, PASS, self_sha256, inputs_sha256 bound)", "fixture": "synthetic identity only (tests_judge_dynamic_deps.py)"}
    rp = f"{q}/export_{arm}.json"; json.dump(rec, open(rp, "w"))
    return rp, caller


def judge(q, dev, hc, elig, name="J"):
    json.dump(elig, open(f"{q}/ELIG_{name}.json", "w"))
    rc, out = run([f"{dev}/judge_v4.py"], {"JUDGE_HC": hc, "JUDGE_OUT": f"{q}/{name}.json", "JUDGE_ELIGIBILITY": f"{q}/ELIG_{name}.json"})
    j = json.load(open(f"{q}/{name}.json")) if os.path.exists(f"{q}/{name}.json") else None
    return rc, out, j


def n_promote(j): return sum(v == "(A) PROMOTE" for v in (j or {}).get("verdicts", {}).values())
def A(j): return (j or {}).get("eligibility_by_arm", {}).get("A1e", {})


def cell(d, name, judge_src=None, extras_of=None, mutate=None, caller_extra=None, path_missing=(), sha_none=()):
    """One world + device + receipt; extras_of(q) -> {name: path} written before the receipt; mutate(q) runs AFTER the receipt (a changed FEMAT);
    caller_extra: names the caller declares on top of the 24. Returns (rc, out, j, receipt_path, caller)."""
    q = f"{d}/{name}"; os.makedirs(q); hc = world(q); dev = device(q, judge_src)
    ex = extras_of(q) if extras_of else None
    rp, caller = receipt(q, extras=ex, path_missing=path_missing, sha_none=sha_none)
    if mutate: mutate(q)
    entry = dict(caller); entry.update({k: ex[k] for k in (caller_extra or ())})
    rc, out, j = judge(q, dev, hc, {"A1e": {"receipt": rp, "inputs": entry}})
    return rc, out, j, rp, caller, ex


def femat_only(q):
    p = f"{q}/femat.npz"; open(p, "wb").write(b"original synthetic FEMAT"); return {"femat": p}


def femat_and_signal(q):
    p = f"{q}/femat.npz"; open(p, "wb").write(b"original synthetic FEMAT"); s = f"{q}/signal_receipt.json"; open(s, "w").write("{}")
    return {"femat": p, "signal_receipt": s}


def change_femat(q): open(f"{q}/femat.npz", "wb").write(b"CHANGED synthetic FEMAT")
def change_signal(q): open(f"{q}/signal_receipt.json", "w").write('{"changed": true}')
def delete_femat(q): os.remove(f"{q}/femat.npz")


print("[S] static: the device under test and its predecessor")
_j = open(f"{HERE}/judge_v4.py").read(); _c = open(f"{HERE}/v4_gate_common.py").read(); _m = open(f"{HERE}/make_sha_manifest.py").read()
check("★★★ [r8] the archived judge passes recorded_extras=True to require; the r5 snapshot exists, its sha starts with f6850dc3 and it does NOT",
      "recorded_extras=True" in _j and os.path.exists(R5) and _sha(R5).startswith("f6850dc3") and "recorded_extras" not in open(R5).read(), _sha(R5)[:12] if os.path.exists(R5) else "no snapshot")
check("★★ [r8] v4_gate_common.require has the recorded_extras keyword and the CLI accepts recorded_extras=1", "recorded_extras=False):" in _c and 'kv.pop("recorded_extras"' in _c)
check("★ [r8] make_sha_manifest recognises snapshot suffixes .r0–.r9 (was .r0–.r4: the r5 snapshot would have been listed as a live script)", 'SNAP = re.compile(r"\\.r([0-9])_[0-9a-f]{8}\\.")' in _m)
_real = json.load(open(f"{HERE}/receipts/judge_floor_2026-09-12/BUNDLE_export_v2_A1_applied.json"))
sys.path.insert(0, HERE); import importlib; _gc = importlib.import_module("v4_gate_common")   # noqa: E402
check("★★ [r8] (iv) static: the REAL A1 v2 receipt records exactly the 28 floor names — no conditional extras, so round 8 changes nothing for it",
      set(_real["inputs_sha256"]) == set(_gc.REQUIRED_INPUTS["BUNDLE_export"]) and set(_real["inputs_path"]) == set(_real["inputs_sha256"]), sorted(set(_real["inputs_sha256"]) ^ set(_gc.REQUIRED_INPUTS["BUNDLE_export"])))

with tempfile.TemporaryDirectory() as d:
    print("\n[D] judge level: the receipt's recorded closure is the dependency set")
    rc, out, j, rp, caller, ex = cell(d, "i_changed_omitted", extras_of=femat_only, mutate=change_femat)
    check("★★★ [r8] (i) recorded femat, FEMAT changed after the receipt, caller omits femat ⇒ A1e NOT eligible, why names 'femat' changed since the receipt, recorded_extras=['femat'], 0 PROMOTE (round 7: eligible, 4 PROMOTE)",
          rc == 0 and j and A(j)["ok"] is False and "'femat' changed since the receipt" in A(j)["why"] and A(j).get("recorded_extras") == ["femat"] and n_promote(j) == 0, (rc, A(j).get("why")))
    check("★★ [r8] (i) the judge output locates the extra it verified (recorded_extras_paths.femat = the receipt's inputs_path.femat)", j and A(j).get("recorded_extras_paths", {}).get("femat") == ex["femat"], j and A(j).get("recorded_extras_paths"))
    rc, out, j, rp, caller, ex = cell(d, "ii_unchanged_omitted", extras_of=femat_only)
    check("★★★ [r8] (ii) recorded femat UNCHANGED, caller omits femat ⇒ eligible: the judge verified it from the receipt — '29 inputs verified (1 recorded beyond the caller's declaration', inputs lists femat, 4 PROMOTE",
          rc == 0 and j and A(j)["ok"] is True and "29 inputs verified (1 recorded beyond the caller's declaration" in A(j)["why"] and "femat" in A(j)["inputs"] and len(A(j)["inputs"]) == 29 and n_promote(j) == 4, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "iii_no_path", extras_of=femat_only, path_missing=("femat",))
    check("★★★ [r8] (iii) recorded femat but inputs_path lacks it ⇒ refused 'receipt recorded conditional input 'femat' but no locatable path', 0 PROMOTE",
          rc == 0 and j and A(j)["ok"] is False and "recorded conditional input 'femat' but no locatable path" in A(j)["why"] and n_promote(j) == 0, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "iv_no_extras")
    check("★★★ [r8] (iv) a receipt with NO extras (the real A1 shape) is unaffected: eligible, '28 inputs verified (0 recorded beyond', recorded_extras=[], 4 PROMOTE",
          rc == 0 and j and A(j)["ok"] is True and "28 inputs verified (0 recorded beyond" in A(j)["why"] and A(j).get("recorded_extras") == [] and n_promote(j) == 4, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "v_old_judge_red", judge_src=R5, extras_of=femat_only, mutate=change_femat)
    check("★★★ [r8] (v) OLD CODE RED: judge_v4.r5_f6850dc3.py on cell (i) (same common, same contract) ⇒ eligible and 4 PROMOTE — the changed FEMAT the receipt hashed is invisible when the caller does not name it",
          rc == 0 and j and A(j)["ok"] is True and "recorded beyond" not in A(j)["why"] and n_promote(j) == 4, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "vi_changed_declared", extras_of=femat_only, mutate=change_femat, caller_extra=("femat",))
    check("★★★ [r8] the reviewer's other half: caller DECLARES the changed femat ⇒ not eligible ('femat' changed since the receipt), 0 recorded beyond (it was declared), 0 PROMOTE",
          rc == 0 and j and A(j)["ok"] is False and "'femat' changed since the receipt" in A(j)["why"] and A(j).get("recorded_extras") == [] and n_promote(j) == 0, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "vii_two_extras_second_changed", extras_of=femat_and_signal, mutate=change_signal)
    check("★★★ [r8] two recorded extras (femat, signal_receipt), only the signal receipt changed, caller omits both ⇒ not eligible naming 'signal_receipt', recorded_extras=['femat','signal_receipt'], 0 PROMOTE",
          rc == 0 and j and A(j)["ok"] is False and "'signal_receipt' changed since the receipt" in A(j)["why"] and A(j).get("recorded_extras") == ["femat", "signal_receipt"] and n_promote(j) == 0, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "viii_two_extras_unchanged", extras_of=femat_and_signal)
    check("★★ [r8] two recorded extras, both unchanged, caller omits both ⇒ eligible, '30 inputs verified (2 recorded beyond', 4 PROMOTE",
          rc == 0 and j and A(j)["ok"] is True and "30 inputs verified (2 recorded beyond" in A(j)["why"] and n_promote(j) == 4, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "ix_sha_none", extras_of=femat_only, sha_none=("femat",))
    check("★★ [r8] an extra recorded with sha None (the gate did not see the file) ⇒ refused 'receipt recorded no sha for input 'femat'', 0 PROMOTE",
          rc == 0 and j and A(j)["ok"] is False and "recorded no sha for input 'femat'" in A(j)["why"] and n_promote(j) == 0, (rc, A(j).get("why")))
    rc, out, j, rp, caller, ex = cell(d, "x_file_deleted", extras_of=femat_only, mutate=delete_femat)
    check("★★ [r8] the recorded FEMAT deleted after the receipt, caller omits it ⇒ refused 'input 'femat' missing on disk', 0 PROMOTE",
          rc == 0 and j and A(j)["ok"] is False and "input 'femat' missing on disk" in A(j)["why"] and n_promote(j) == 0, (rc, A(j).get("why")))

    print("\n[U] unit level: the flag is the mechanism (archived module + shipped contract)")
    q = f"{d}/unit"; os.makedirs(q); hc = world(q); dev = device(q); ex = femat_only(q); rp, caller = receipt(q, extras=ex); change_femat(q)
    full = dict(caller); full.update({f"book_{seat}_s{seed}": f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_A1e_{seat}_s{seed}.npz" for seat in ("dyn", "fix") for seed in (42, 2027)})
    full["eligibility_contract"] = _gc.CONTRACT_PATH   # the archived contract == the device copy byte for byte
    ok0, why0 = _gc.require(rp, full, expected_gate="BUNDLE_export", expected_self_sha=V2)
    ok1, why1 = _gc.require(rp, full, expected_gate="BUNDLE_export", expected_self_sha=V2, recorded_extras=True)
    check("★★★ [r8] require(recorded_extras=False) on the changed-FEMAT receipt with the 28 declared ⇒ ok (the round-7 blind spot, still the behaviour of callers that re-verify only their own declaration)", ok0 is True and "28 inputs verified" in why0, why0)
    check("★★★ [r8] require(recorded_extras=True) on the same call ⇒ refused naming 'femat' changed since the receipt", ok1 is False and "'femat' changed since the receipt" in why1, why1)
    open(ex["femat"], "wb").write(b"original synthetic FEMAT")
    ok2, why2 = _gc.require(rp, full, expected_gate="BUNDLE_export", expected_self_sha=V2, recorded_extras=True)
    check("★★ [r8] FEMAT restored ⇒ recorded_extras=True passes with '29 inputs verified (1 recorded beyond the caller's declaration'", ok2 is True and "29 inputs verified (1 recorded beyond the caller's declaration" in why2, why2)
    change_femat(q)
    rc, out = run(["v4_gate_common.py", "require", rp, "gate=BUNDLE_export", f"self_sha={V2}", "recorded_extras=1"] + [f"{k}={v}" for k, v in full.items()])
    check("★★ [r8] CLI: `require ... recorded_extras=1` ⇒ rc 3 naming femat; without the flag ⇒ rc 0 (documented, not hidden)",
          rc == 3 and "'femat' changed since the receipt" in out and run(["v4_gate_common.py", "require", rp, "gate=BUNDLE_export", f"self_sha={V2}"] + [f"{k}={v}" for k, v in full.items()])[0] == 0, out.strip()[-160:])

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
