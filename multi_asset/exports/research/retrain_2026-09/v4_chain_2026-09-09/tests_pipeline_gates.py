"""Fault-injection tests for the hardened v4 chain gates (review b0a573a1 P1-PIPE / R4 / R7). Synthetic inputs only.

Each case reproduces a reviewer scenario that USED to pass or exit 0, and asserts the hardened program condition:
  closure gate: value change outside closure -> FAIL, rc 3 (was PASS=false, rc 0)
                E_ts +300 s on side B, symbols reversed -> FAIL on the axis (was PASS=true, rc 0)
                duplicate pair key / wrong column count -> FAIL
                identical builds -> PASS, rc 0, receipt carries input SHAs
  require:      PASS receipt + unchanged inputs -> rc 0; changed input -> rc 3 (stale); FAIL receipt -> rc 3; missing -> rc 3
Run: python3 tests_pipeline_gates.py   (exit 0 iff every case behaves)."""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FAILS, N = [], [0]
import hashlib as _hl


def _sha(p): return _hl.sha256(open(p, "rb").read()).hexdigest()


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail != '' else ''}", flush=True)
    if not cond:
        FAILS.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    p = subprocess.run([PY] + args, capture_output=True, text=True, env=e, cwd=HERE)
    return p.returncode, p.stdout + p.stderr


# ── synthetic fixture: 60 anchors on a 48-row grid, 6 symbols, 89 columns, a hole run at rows 200..250 ──
def fixture(d, nA=60, NW=6, NC=89, seed=0):
    rng = np.random.default_rng(seed)
    E_row = 100 + 48 * np.arange(nA); E_ts = 1_700_000_000 + 300 * E_row
    symbols = np.array([f"S{i}USDT" for i in range(NW)])
    names = np.array([f"{fam}:c{j}_48" for j, fam in enumerate(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"] * 9)][:NC])
    pa = np.repeat(np.arange(nA), NW); ps = np.tile(np.arange(NW), nA)
    X = rng.normal(size=(nA * NW, NC)).astype(np.float32)
    tg = {"E_row": E_row, "E_ts": E_ts, "symbols": symbols, "members": np.array([np.arange(NW)] * nA, dtype=object)}
    np.savez(f"{d}/tA.npz", **tg); np.savez(f"{d}/tB.npz", **tg)
    np.savez(f"{d}/fA.npz", X=X, pair_a=pa, pair_s=ps, names=names); np.savez(f"{d}/fB.npz", X=X.copy(), pair_a=pa, pair_s=ps, names=names)
    np.savez(f"{d}/holes.npz", fill_runs=np.array([[200, 250]]), neigh_rows=np.array([[152, 9000]]), row=np.array([210]), col=np.array([0]), symbols=symbols)
    return dict(E_row=E_row, E_ts=E_ts, symbols=symbols, names=names, pa=pa, ps=ps, X=X, tg=tg)


def gate(d, extra_env=None):
    return run(["v4_gate_closure.py", f"{d}/fA.npz", f"{d}/fB.npz", f"{d}/tA.npz", f"{d}/tB.npz", f"{d}/out.json"],
               {"HOLE_CELLS": f"{d}/holes.npz", "EXPECT_NCOLS": "89", **(extra_env or {})})


with tempfile.TemporaryDirectory() as d:
    print("[A] identical builds PASS with rc 0 and a receipt bound to input SHAs")
    fx = fixture(d)
    rc, out = gate(d); r = json.load(open(f"{d}/out.json"))
    check("★★★ PASS, rc 0", rc == 0 and r["PASS"] is True and r["gate"] == "G2_closure", (rc, out[-200:]))
    check("★★ receipt names every input with a sha256 and records the gate's own sha",
          set(r["inputs_sha256"]) == {"fea_A", "fea_B", "targets_A", "targets_B", "hole_cells"} and all(r["inputs_sha256"].values()) and r.get("self_sha256"))

    print("\n[B] a value change OUTSIDE the closure -> FAIL and rc 3 (reviewer: was PASS=false with rc 0)")
    X2 = fx["X"].copy(); X2[fx["pa"] == 59, 5] += 1.0          # anchor 59 (row 2932) is past the closure of a 48-row F column: [200-48, 250+2016+48]
    np.savez(f"{d}/fB.npz", X=X2, pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    rc, out = gate(d); r = json.load(open(f"{d}/out.json"))
    check("★★★ FAIL is rc 3 and PASS false", rc == 3 and r["PASS"] is False, rc)
    check("★★ the failing column is named", list(r["failing_columns"].keys()) == [str(fx["names"][5])], list(r["failing_columns"]))
    np.savez(f"{d}/fB.npz", X=fx["X"].copy(), pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])

    print("\n[C] axis faults the old gate could not see (reviewer R7): E_ts +300 s and reversed symbols on side B")
    tg = dict(fx["tg"]); tg["E_ts"] = fx["E_ts"] + 300; tg["symbols"] = fx["symbols"][::-1]
    np.savez(f"{d}/tB.npz", **tg)
    rc, out = gate(d); r = json.load(open(f"{d}/out.json"))
    check("★★★ E_row unchanged but E_ts shifted + symbols reversed ⇒ FAIL rc 3 on the axis (was PASS=true rc 0)",
          rc == 3 and r["PASS"] is False and r["axis_ok"] is False
          and set(r["failing_axis_checks"]) >= {"E_ts_equal", "symbols_equal_same_order"}, (rc, r.get("failing_axis_checks")))
    np.savez(f"{d}/tB.npz", **fx["tg"])

    print("\n[D] duplicate pair key and wrong column count -> FAIL")
    pa2 = fx["pa"].copy(); pa2[-1] = pa2[-2]; ps2 = fx["ps"].copy(); ps2[-1] = ps2[-2]
    np.savez(f"{d}/fB.npz", X=fx["X"].copy(), pair_a=pa2, pair_s=ps2, names=fx["names"])
    rc, out = gate(d); r = json.load(open(f"{d}/out.json"))
    check("★★ duplicate pair on B ⇒ FAIL (pairs_unique_B)", rc == 3 and "pairs_unique_B" in r.get("failing_axis_checks", []), r.get("failing_axis_checks"))
    np.savez(f"{d}/fB.npz", X=fx["X"].copy(), pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    rc, out = gate(d, {"EXPECT_NCOLS": "90"}); r = json.load(open(f"{d}/out.json"))
    check("★★ expected 90 columns but 89 present ⇒ FAIL (n_cols_ok)", rc == 3 and "n_cols_ok" in r.get("failing_axis_checks", []))

    print("\n[E] `require`: chains may only dispatch on a fresh PASS receipt OF THE EXPECTED GATE, FROM THE PINNED GATE SOURCE, with declared inputs")
    rc, out = gate(d); assert rc == 0
    G = "gate=G2_closure"; good = json.load(open(f"{d}/out.json")); SS = "self_sha=" + good["self_sha256"]   # round 4: every caller pins the gate source
    ALL5 = [f"fea_A={d}/fA.npz", f"fea_B={d}/fB.npz", f"targets_A={d}/tA.npz", f"targets_B={d}/tB.npz", f"hole_cells={d}/holes.npz"]   # round 4: the registered G2_closure set
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5)
    check("★★★ PASS receipt + expected gate + pinned source + the full registered input set, unchanged ⇒ rc 0", rc == 0 and "REQUIRE_OK" in out and "registered floor G2_closure=5" in out, out.strip()[-120:])
    np.savez(f"{d}/fA.npz", X=fx["X"] + 1, pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5)
    check("★★★ an input that changed AFTER the receipt ⇒ rc 3 (stale receipt is not a receipt)", rc == 3 and "changed since the receipt" in out, out.strip()[-120:])
    np.savez(f"{d}/fA.npz", X=fx["X"].copy(), pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    json.dump({"gate": "G2_closure", "PASS": False, "inputs_sha256": {}, "self_sha256": good["self_sha256"]}, open(f"{d}/bad.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/bad.json", G, SS] + ALL5)
    check("★★ a FAIL receipt ⇒ rc 3", rc == 3 and "PASS=False" in out, out.strip()[-120:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/nope.json", G, SS] + ALL5)
    check("★★ a missing receipt ⇒ rc 3", rc == 3 and "missing" in out)
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5 + [f"unknown_input={d}/fA.npz"])
    check("★ an input the receipt never hashed ⇒ rc 3 (no silent pass on an unrecorded dependency)", rc == 3 and "no sha for input" in out)
    # ── round 3 (review 31fa3e4e §2): identity and dependency binding ──
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", "gate=UNRELATED_GATE", SS] + ALL5)
    check("★★★ [r3] a PASS receipt from ANOTHER gate ⇒ rc 3 (reviewer: wrong gate name used to pass)", rc == 3 and "caller expected 'UNRELATED_GATE'" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", SS] + ALL5)
    check("★★★ [r3] a caller that names NO gate ⇒ rc 3 (no anonymous requires)", rc == 3 and "did not declare the gate" in out, out.strip()[-140:])
    for label, ss in (("all-zero", "0" * 64), ("missing", None), ("garbage", "not-a-sha")):
        json.dump(dict(good, self_sha256=ss), open(f"{d}/ss.json", "w"))
        rc, out = run(["v4_gate_common.py", "require", f"{d}/ss.json", G, SS] + ALL5)
        check(f"★★★ [r3] self_sha256 {label} ⇒ rc 3 (reviewer: pseudo/absent self sha used to pass)", rc == 3 and "no usable self_sha256" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, "self_sha=" + "ab" * 32] + ALL5)
    check("★★ [r3] a pinned gate source that differs from the receipt's ⇒ rc 3", rc == 3 and "caller trusts" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, "self_sha=" + good["self_sha256"]] + ALL5)
    check("★★ [r3] the pinned gate source that MATCHES ⇒ rc 0", rc == 0, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS])
    check("★★★ [r3] an EMPTY dependency list ⇒ rc 3 (reviewer: {PASS:true} with no inputs used to pass)", rc == 3 and "declared no inputs" in out, out.strip()[-140:])
    json.dump({"PASS": True, "gate": "G2_closure"}, open(f"{d}/arbitrary.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/arbitrary.json", G, SS] + ALL5)
    check("★★ [r3] a hand-written {PASS:true, gate} with no self sha and no input shas ⇒ rc 3", rc == 3, out.strip()[-140:])
    json.dump(dict(good, inputs_sha256=dict(good["inputs_sha256"], fea_A=None)), open(f"{d}/nullsha.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/nullsha.json", G, SS] + ALL5)
    check("★ [r3] a receipt whose input sha is null (the gate never saw the file) ⇒ rc 3", rc == 3 and "recorded no sha" in out, out.strip()[-140:])
    # ── round 4 (researcher require_valid_wrong_source_unpinned): the pin is mandatory ──
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G] + ALL5)
    check("★★★ [r4] a caller that does NOT pin self_sha= ⇒ rc 3 even on a genuine PASS receipt (round 3 accepted any real-looking self sha when unpinned)", rc == 3 and "did not pin the gate source" in out, out.strip()[-160:])
    json.dump(dict(good, self_sha256=_sha(f"{HERE}/judge_v4.py")), open(f"{d}/judge_written.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/judge_written.json", G] + ALL5)
    check("★★★ [r4] require_valid_wrong_source_unpinned: receipt self sha = the JUDGE's real sha, caller unpinned ⇒ rc 3 (was rc 0)", rc == 3 and "did not pin" in out, out.strip()[-160:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/judge_written.json", G, SS] + ALL5)
    check("★★★ [r4] the same receipt with the closure gate pinned ⇒ rc 3 'caller trusts' (the judge did not write this gate's receipt)", rc == 3 and "caller trusts" in out, out.strip()[-160:])
    for bad in ("self_sha=", "self_sha=not-a-sha", "self_sha=" + "0" * 64):
        rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, bad] + ALL5)
        check(f"★★ [r4] {bad[:22]!r} ⇒ rc 3 (a pin must be a real sha256)", rc == 3 and ("did not pin" in out or "not a sha256" in out), out.strip()[-120:])
    # ── round 4 (researcher require_correct_identity_dependency_subset): the FULL registered dependency set is a contract ──
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5[:4])
    check("★★★ [r4] omitting hole_cells (4 of the 5 registered G2_closure inputs) ⇒ rc 3 naming the omitted input (round 3 verified the subset and passed)", rc == 3 and "omitted registered input(s) ['hole_cells']" in out, out.strip()[-160:])
    np.savez(f"{d}/holes.npz", different_payload=np.arange(10))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5[:4])
    check("★★★ [r4] researcher's exact case: holes changed AND omitted from the declaration ⇒ rc 3 (was rc 0: the change was invisible)", rc == 3 and "omitted registered input(s) ['hole_cells']" in out, out.strip()[-160:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5)
    check("★★★ [r4] holes changed and DECLARED ⇒ rc 3 'changed since the receipt' (the change is now visible either way)", rc == 3 and "'hole_cells' changed since the receipt" in out, out.strip()[-160:])
    fx = fixture(d); rc, out = gate(d); assert rc == 0; good = json.load(open(f"{d}/out.json")); SS = "self_sha=" + good["self_sha256"]
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5 + [f"extra_note={d}/holes.npz"])
    check("★★ [r4] an EXTRA declared input that the receipt did hash is allowed only if recorded — here it is not ⇒ rc 3 'no sha' (extras are checked, never ignored)", rc == 3 and "no sha for input 'extra_note'" in out, out.strip()[-120:])
    s1 = {"gate": "STEP1", "PASS": True, "self_sha256": _sha(f"{HERE}/v4_gate_step1.py"), "inputs_sha256": {k: _sha(f"{d}/holes.npz") for k in ("dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4", "extra_recorded")}}
    json.dump(s1, open(f"{d}/s1.json", "w")); S1 = ["gate=STEP1", "self_sha=" + s1["self_sha256"]]; two = [f"dlw_v4raw_targets={d}/holes.npz", f"fea82_v4raw={d}/holes.npz"]; four = two + [f"dlw_hf3_targets={d}/holes.npz", f"fea89_f8v4={d}/holes.npz"]
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + ["profile=v4"] + two)
    check("★★★ [r4] STEP1 profile=v4 (gpu3 / post_export) with only the RAW pair ⇒ rc 3: the CLIP targets and fea89 those chains read are registered", rc == 3 and "omitted registered input(s) ['dlw_hf3_targets', 'fea89_f8v4'] for STEP1@v4" in out, out.strip()[-160:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + ["profile=v4"] + four)
    check("★★ [r4] STEP1 profile=v4 with all four ⇒ rc 0", rc == 0 and "registered floor STEP1@v4=4" in out, out.strip()[-120:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + ["profile=v4s"] + two)
    check("★★ [r4] STEP1 profile=v4s (chain_v4s_gpu.sh: RAW only, fea89 bound through G2) with the RAW pair ⇒ rc 0", rc == 0 and "registered floor STEP1@v4s=2" in out, out.strip()[-120:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + ["profile=v4s", f"fea82_v4raw={d}/holes.npz"])
    check("★★ [r4] STEP1 profile=v4s without the RAW targets ⇒ rc 3", rc == 3 and "omitted registered input(s) ['dlw_v4raw_targets']" in out, out.strip()[-120:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + ["profile=nonexistent"] + four)
    check("★★ [r4] an unregistered profile ⇒ rc 3 (a stage cannot invent its own subset)", rc == 3 and "profile 'nonexistent' is not registered" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1.json"] + S1 + four + [f"extra_recorded={d}/holes.npz"])
    check("★★ [r4] bare STEP1 (floor = RAW pair) with four + a recorded extra ⇒ rc 0 (extras allowed when the receipt hashed them)", rc == 0, out.strip()[-120:])
    json.dump(dict(s1, gate="G9_unregistered"), open(f"{d}/g9.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/g9.json", "gate=G9_unregistered", "self_sha=" + s1["self_sha256"], f"extra_recorded={d}/holes.npz"])
    check("★ [r4] an unregistered gate has no floor: the caller's own non-empty declaration still binds ⇒ rc 0 with 'registered floor G9_unregistered=none'", rc == 0 and "registered floor G9_unregistered=none" in out, out.strip()[-120:])
    import importlib; sys.path.insert(0, HERE); _gc = importlib.import_module("v4_gate_common")
    check("★★ [r4] REQUIRED_INPUTS names exactly what the archived chains declare: G2 5 (v4s), STEP1@v4s 2, STEP1@v4 4 (gpu3/post_export), STEP2 2",
          set(_gc.REQUIRED_INPUTS["G2_closure"]) == {"fea_A", "fea_B", "targets_A", "targets_B", "hole_cells"} and _gc.REQUIRED_INPUTS["STEP1@v4"] == ["dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4"]
          and _gc.REQUIRED_INPUTS["STEP2"] == ["wide_fea_v4", "wide_fea_v4_meta"] and "profile=v4s" in open(f"{HERE}/chain_v4s_gpu.sh").read() and "profile=v4" in open(f"{HERE}/chain_v4_gpu3.sh").read() and "profile=v4" in open(f"{HERE}/chain_v4_post_export.sh").read())


with tempfile.TemporaryDirectory() as d:
    print("\n[F] the judge REFUSES without its required inputs (reviewer R4: used to exit 0 with empty verdicts)")
    os.makedirs(f"{d}/hc/dev_v4/probe_artifacts"); os.makedirs(f"{d}/hc/dev_raw/probe_artifacts")
    rc, out = run(["judge_v4.py"], {"JUDGE_HC": f"{d}/hc", "JUDGE_OUT": f"{d}/J.json"})
    check("★★★ no arms at all ⇒ rc 3 at the reproduction gate (A0p reproduction absent), no verdict JSON written",
          rc == 3 and "JUDGE_REFUSED reproduction" in out and not os.path.exists(f"{d}/J.json"), (rc, out.strip().splitlines()[-1][:160] if out.strip() else out))
    rc, out = run(["judge_v4.py"], {"JUDGE_HC": f"{d}/hc", "JUDGE_OUT": f"{d}/J.json", "JUDGE_ALLOW_PARTIAL": "1"})
    check("★ JUDGE_ALLOW_PARTIAL=1 (exploration only) lets it run through and says so",
          rc == 0 and os.path.exists(f"{d}/J.json") and json.load(open(f"{d}/J.json"))["verdicts"] == {}, (rc, out[-200:]))

    print("\n[G] G1 stable-trend gate: required booleans decide the exit code")
    rc, out = run(["stable_trend.py"], {"G1_OUT": f"{d}/G1.json"})
    g1 = json.load(open(f"{d}/G1.json")) if os.path.exists(f"{d}/G1.json") else {}
    check("★★ synthetic G1 passes with rc 0 and a receipt (gate/PASS/self sha)", rc == 0 and g1.get("PASS") is True and g1.get("gate") == "G1_stable_trend_synthetic" and g1.get("self_sha256"), (rc, out[-200:]))

    print("\n[H] generator regeneration is BITWISE (reviewer P1-REGEN: regenerating used to restore the hard-coded v3 BUNDLE_BASE)")
    base = os.path.dirname(HERE); os.makedirs(f"{d}/gen")
    rc, out = run(["make_v4_scripts.py"], {"GEN_OUT": f"{d}/gen", "GEN_TRAINER_BASE": f"{HERE}/base_pod_f10_train_monthly_earlystop.py", "GEN_REFIT_BASE": f"{HERE}/base_pod_f10_refit_ext.py", "GEN_EXPORT_BASE": f"{base}/pod_export_bundle_v3.py"})
    import hashlib
    def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
    same = {f: (os.path.exists(f"{d}/gen/{f}") and sha(f"{d}/gen/{f}") == sha(f"{HERE}/{f}")) for f in ("pod_export_bundle_v4.py", "pod_f10_train_monthly_v4.py", "pod_f10_refit_v4.py")}
    check("★★★ the regenerated EXPORTER is byte-identical to the archived one (BUNDLE_BASE read from env survives regeneration)", rc == 0 and same["pod_export_bundle_v4.py"], (rc, same, out[-300:]))
    check("★★ regenerated trainer + refit are byte-identical to the archived ones", same["pod_f10_train_monthly_v4.py"] and same["pod_f10_refit_v4.py"], same)
    check("★ the regenerated exporter reads BUNDLE_BASE from env", os.path.exists(f"{d}/gen/pod_export_bundle_v4.py") and 'os.environ.get("BUNDLE_BASE"' in open(f"{d}/gen/pod_export_bundle_v4.py").read())

    print("\n[I] chain drivers: a failed shard aborts BEFORE merge; DONE is never written on failure (reviewer P1-PIPE)")
    open(f"{d}/stub_fail.sh", "w").write("#!/bin/bash\n[ \"$3\" = 2 ] && exit 7; exit 0\n"); open(f"{d}/stub_ok.sh", "w").write("#!/bin/bash\nexit 0\n")
    harness = f"""#!/bin/bash
set -o pipefail; R={d}; L={d}/cmds.txt; PY={PY}; . {HERE}/chain_lib.sh
SH0=a; SH1=b; SH2=c; SH3=d
run_shards $1 RAW 42 || die "shards_RAW_s42_rc_[$RCS]" 1
echo MERGE_RAN >> {d}/cmds.txt; say "CHAIN_TEST_DONE"
"""
    open(f"{d}/harness.sh", "w").write(harness)
    p = subprocess.run(["bash", f"{d}/harness.sh", "stub_fail.sh"], capture_output=True, text=True, cwd=d); log = open(f"{d}/cmds.txt").read()
    check("★★★ shard 2 exits 7 ⇒ driver exits 1 with FAIL_shards_... naming the rc list, merge NEVER runs, no DONE",
          p.returncode == 1 and "FAIL_shards_RAW_s42_rc_[0 0 7 0]" in log and "MERGE_RAN" not in log and "DONE" not in log, (p.returncode, log.strip().splitlines()[-2:]))
    open(f"{d}/cmds.txt", "w").close()
    p = subprocess.run(["bash", f"{d}/harness.sh", "stub_ok.sh"], capture_output=True, text=True, cwd=d); log = open(f"{d}/cmds.txt").read()
    check("★★ all shards rc 0 ⇒ merge runs and DONE is written", p.returncode == 0 and "MERGE_RAN" in log and "CHAIN_TEST_DONE" in log, log.strip().splitlines()[-2:])
    json.dump({"gate": "G2_closure", "PASS": False, "inputs_sha256": {}}, open(f"{d}/failed_gate.json", "w"))
    harness2 = f"""#!/bin/bash
set -o pipefail; R={d}; L={d}/cmds2.txt; PY={PY}; . {HERE}/chain_lib.sh
cp {HERE}/v4_gate_common.py {d}/v4_gate_common.py
require_gate {d}/failed_gate.json
echo DISPATCHED >> {d}/cmds2.txt
"""
    open(f"{d}/harness2.sh", "w").write(harness2)
    p = subprocess.run(["bash", f"{d}/harness2.sh"], capture_output=True, text=True, cwd=d); log2 = open(f"{d}/cmds2.txt").read()
    check("★★★ a FAIL receipt stops the driver at require_gate (rc 3), nothing is dispatched", p.returncode == 3 and "DISPATCHED" not in log2 and "FAIL_gate_require_failed_gate" in log2, (p.returncode, log2.strip()[-160:]))


# ── [J] round 3 (review 31fa3e4e §2): the REAL chain drivers, path-translated into a private root, with stub producers ──────────────
# The bash drivers are copied with /workspace -> <root>; `venv/bin/python` is a stub that runs v4_gate_common.py for real and fakes every
# producer/trainer/merge; PATH provides fake nvidia-smi/sleep. Same shape as the reviewer's audit_faults.py chain_case, so the scenarios it
# showed passing (wrong gate / wrong source / changed holes / changed RAW / data cp failure) are asserted to BLOCK here.
import shutil as _sh, stat as _st


def chain_case(entry, scenario, d):
    root = f"{d}/{scenario if entry == 'chain_v4s_gpu.sh' or entry == 'chain_v4_data.sh' else entry.replace('.sh', '') + '_' + scenario}/workspace"; rr = f"{root}/review_scratch"
    for sub in ("review_scratch/v4_gates", "venv/bin", "bin", "f8_v4/logs", "f8_v4s/logs", "f8_v4/gates", "f8_v4s/data", "f8_hf2s/data", "dlw_hf3/data", "dlw_hf2/data",
                "dlw_v4raw/data", "f8_v4/data", "data", "dlw_hf3/results"):
        os.makedirs(f"{root}/{sub}", exist_ok=True)
    for f in os.listdir(HERE):
        if f.endswith((".py", ".sh")):
            open(f"{rr}/{f}", "w").write(open(f"{HERE}/{f}").read().replace("/workspace", root))
    stub = f"""#!/usr/bin/env python3
import sys, os, json, subprocess
a = sys.argv[1:]; n = os.path.basename(a[0]) if a else ""
cfg = json.load(open({root!r} + "/config.json"))
open({root!r} + "/events.txt", "a").write(n + "\\n")
if n == "v4_gate_common.py": sys.exit(subprocess.call([{PY!r}, "-B"] + a))
if n == "-": sys.exit(subprocess.call([{PY!r}, "-B", "-"] + a[1:], stdin=sys.stdin))
if "train_monthly" in n: sys.exit(7 if cfg.get("scenario") == "fail_shard" + os.environ.get("MWF_OUT", "x")[-1] else 0)
if n.startswith("merge_"): print("MERGE_DONE"); sys.exit(0)
if n == "pod_dlw_features_ext.py":
    if cfg.get("scenario") != "data_fea82_missing": open({root!r} + "/dlw_hf3/data/dlw_fea82.npz", "wb").write(b"fea82")
    sys.exit(0)
if n == "pod_dlw_targets_raw.py": open({root!r} + "/dlw_v4raw/data/dlw_targets.npz", "wb").write(b"raw-targets"); sys.exit(0)
if n == "pod_f8_build_ext.py": open({root!r} + "/f8_v4/data/f8_fea89.npz", "wb").write(b"fea89"); sys.exit(0)
if n == "pod_fea_ext_clamp.py":
    open({root!r} + "/data/wide_fea_v4.npy", "wb").write(b"k"); open({root!r} + "/data/wide_fea_v4_meta.npz", "wb").write(b"m"); sys.exit(0)
if n == "pod_legs_v4b.py": print("LEGS_V4B_DONE"); sys.exit(0)
print("STUB_DONE"); sys.exit(0)
"""
    open(f"{root}/venv/bin/python", "w").write(stub); os.chmod(f"{root}/venv/bin/python", 0o700)
    for k, v in (("nvidia-smi", "#!/bin/bash\necho 0\n"), ("sleep", "#!/bin/bash\nexit 0\n")):
        open(f"{root}/bin/{k}", "w").write(v); os.chmod(f"{root}/bin/{k}", 0o700)
    json.dump({"scenario": scenario}, open(f"{root}/config.json", "w"))
    files = {"fea_A": f"{root}/f8_v4s/data/f8_fea89.npz", "fea_B": f"{root}/f8_hf2s/data/f8_fea89.npz", "targets_A": f"{root}/dlw_hf3/data/dlw_targets.npz",
             "targets_B": f"{root}/dlw_hf2/data/dlw_targets.npz", "hole_cells": f"{rr}/holefix2_cells.npz"}
    step1 = {"dlw_v4raw_targets": f"{root}/dlw_v4raw/data/dlw_targets.npz", "dlw_hf3_targets": f"{root}/dlw_hf3/data/dlw_targets.npz",
             "fea82_v4raw": f"{root}/dlw_v4raw/data/dlw_fea82.npz", "fea89_f8v4": f"{root}/f8_v4/data/f8_fea89.npz"}
    step2 = {"wide_fea_v4": f"{root}/data/wide_fea_v4.npy", "wide_fea_v4_meta": f"{root}/data/wide_fea_v4_meta.npz"}
    for pth in list(files.values()) + list(step1.values()) + list(step2.values()) + [f"{root}/f8_v4s/data/f10v2_legs.npz", f"{root}/f8_v4/data/f10v2_legs.npz"]:
        open(pth, "wb").write(b"original:" + os.path.basename(pth).encode())
    open(f"{rr}/export_v4.log", "w").write("BUNDLE_DONE files 8 size 1MB\n")   # post_export precondition (round 3 markers)
    g2 = {"PASS": True, "gate": "G2_closure", "self_sha256": _sha(f"{rr}/v4_gate_closure.py"), "inputs_sha256": {k: _sha(v) for k, v in files.items()}}
    s1 = {"PASS": True, "gate": "STEP1", "self_sha256": _sha(f"{rr}/v4_gate_step1.py"), "inputs_sha256": {k: _sha(v) for k, v in step1.items()}}
    s2 = {"PASS": True, "gate": "STEP2", "self_sha256": _sha(f"{rr}/v4_gate_step2.py"), "inputs_sha256": {k: _sha(v) for k, v in step2.items()}}
    if scenario == "gate_fail": g2["PASS"] = False
    if scenario == "wrong_gate": g2["gate"] = "UNRELATED_PASS"
    if scenario == "wrong_source": g2["self_sha256"] = "0" * 64
    if scenario == "step1_fail": s1["PASS"] = False
    # round 4 (researcher chain_valid_wrong_gate_source): a REAL sha of the WRONG program — the judge's, or another gate's — in the receipt
    if scenario == "g2_written_by_judge": g2["self_sha256"] = _sha(f"{rr}/judge_v4.py")
    if scenario == "step1_written_by_closure_gate": s1["self_sha256"] = _sha(f"{rr}/v4_gate_closure.py")
    if scenario == "step2_written_by_judge": s2["self_sha256"] = _sha(f"{rr}/judge_v4.py")
    if scenario == "gate_script_missing": os.remove(f"{rr}/v4_gate_closure.py")
    if scenario == "chain_omits_hole_cells":   # round 4: a driver edited to declare 4 of the 5 registered G2 inputs
        src = open(f"{rr}/{entry}").read(); assert " hole_cells=" in src; open(f"{rr}/{entry}", "w").write(src.replace(" hole_cells=$R/holefix2_cells.npz", ""))
    json.dump(g2, open(f"{rr}/v4_gates/G2_closure_stable.json", "w")); json.dump(s1, open(f"{rr}/v4_gates/step1.json", "w")); json.dump(s2, open(f"{rr}/v4_gates/step2.json", "w"))
    if scenario == "changed_holes": open(files["hole_cells"], "wb").write(b"new-holes")
    if scenario == "changed_RAW": open(step1["dlw_v4raw_targets"], "wb").write(b"changed RAW target after receipt")
    if scenario == "changed_explicit_input": open(files["fea_A"], "wb").write(b"changed feaA")
    if scenario == "legs_missing": os.remove(f"{root}/f8_v4s/data/f10v2_legs.npz")
    env = dict(os.environ, PATH=f"{root}/bin:" + os.environ["PATH"])
    p = subprocess.run(["bash", f"{rr}/{entry}"], capture_output=True, text=True, env=env, cwd=rr, timeout=120)
    ev = open(f"{root}/events.txt").read() if os.path.exists(f"{root}/events.txt") else ""
    log = open(f"{rr}/v4_commands.txt").read() if os.path.exists(f"{rr}/v4_commands.txt") else ""
    data = open(f"{rr}/chain_v4_data.log").read() if os.path.exists(f"{rr}/chain_v4_data.log") else ""
    return {"rc": p.returncode, "train": ev.count("train_monthly"), "merge": sum(1 for x in ev.splitlines() if x.startswith("merge_")),
            "done": ("_DONE" in log and "CHAIN_" in log) or ("CHAIN_V4_DATA_DONE" in data), "log": log, "data": data, "err": p.stderr[-300:],
            "deps": os.path.exists(f"{rr}/v4_gates/deps_v4s_gpu.json")}


with tempfile.TemporaryDirectory() as d:
    print("\n[J] chain_v4s_gpu.sh under fault injection (reviewer: wrong gate / wrong source / changed holes / changed RAW used to dispatch 8 trainings)")
    r = chain_case("chain_v4s_gpu.sh", "success", d)
    check("★★★ success: both receipts PASS+fresh ⇒ 8 trainings, 2 merges, DONE, deps pinned", r["rc"] == 0 and r["train"] == 8 and r["merge"] == 2 and r["done"] and r["deps"], {k: r[k] for k in ("rc", "train", "merge", "done", "deps", "err")})
    for sc, why in (("wrong_gate", "receipt from another gate"), ("wrong_source", "all-zero self sha"), ("changed_holes", "hole_cells changed after the receipt"),
                    ("changed_RAW", "RAW targets changed after the STEP1 receipt"), ("gate_fail", "G2 receipt FAIL"), ("step1_fail", "STEP1 receipt FAIL"), ("changed_explicit_input", "fea_A changed")):
        r = chain_case("chain_v4s_gpu.sh", sc, d)
        check(f"★★★ {sc}: {why} ⇒ rc 3, ZERO trainings, no DONE", r["rc"] == 3 and r["train"] == 0 and r["merge"] == 0 and not r["done"], {k: r[k] for k in ("rc", "train", "merge", "done")} | {"tail": r["log"].strip().splitlines()[-1][-160:] if r["log"].strip() else r["err"]})
    r = chain_case("chain_v4s_gpu.sh", "legs_missing", d)
    check("★★ legs file missing ⇒ rc 3 before any dispatch", r["rc"] == 3 and r["train"] == 0 and not r["done"], {k: r[k] for k in ("rc", "train", "done")})
    # ── round 4: the chains PIN the gate source (self_sha= computed at run time from the gate script they invoke) ──
    r = chain_case("chain_v4s_gpu.sh", "g2_written_by_judge", d)
    check("★★★ [r4] chain_valid_wrong_gate_source: G2 receipt self sha = the judge's REAL sha ⇒ rc 3, ZERO trainings, no DONE (researcher: rc 0, 8 trainings, DONE)",
          r["rc"] == 3 and r["train"] == 0 and r["merge"] == 0 and not r["done"] and "caller trusts" in r["log"], {k: r[k] for k in ("rc", "train", "merge", "done")} | {"tail": r["log"].strip().splitlines()[-1][-160:] if r["log"].strip() else r["err"]})
    r = chain_case("chain_v4s_gpu.sh", "step1_written_by_closure_gate", d)
    check("★★★ [r4] STEP1 receipt self sha = the CLOSURE gate's real sha (a real gate, the wrong one) ⇒ rc 3, zero trainings", r["rc"] == 3 and r["train"] == 0 and not r["done"] and "caller trusts" in r["log"], {k: r[k] for k in ("rc", "train", "done")})
    r = chain_case("chain_v4s_gpu.sh", "chain_omits_hole_cells", d)
    check("★★★ [r4] a driver that declares only 4 of the 5 registered G2 inputs (hole_cells dropped) ⇒ rc 3 'omitted registered input', ZERO trainings (round 3: the subset passed)",
          r["rc"] == 3 and r["train"] == 0 and not r["done"] and "omitted registered input(s) ['hole_cells']" in r["log"], {k: r[k] for k in ("rc", "train", "done")} | {"tail": r["log"].strip().splitlines()[-2][-160:] if len(r["log"].strip().splitlines()) > 1 else r["err"]})
    r = chain_case("chain_v4s_gpu.sh", "gate_script_missing", d)
    check("★★ [r4] the gate script the chain would pin is missing ⇒ rc 3 gate_source_unreadable before any require/dispatch", r["rc"] == 3 and r["train"] == 0 and "gate_source_unreadable_v4_gate_closure" in r["log"], {k: r[k] for k in ("rc", "train")} | {"tail": r["log"].strip().splitlines()[-1][-120:] if r["log"].strip() else r["err"]})
    check("★★ [r4] the success run's require lines carry the pinned source = sha of the translated gate scripts (pin computed at run time, not typed)",
          "self " + _sha(f"{d}/success/workspace/review_scratch/v4_gate_closure.py")[:12] in open(f"{d}/success/workspace/review_scratch/v4_commands.txt").read()
          and "self " + _sha(f"{d}/success/workspace/review_scratch/v4_gate_step1.py")[:12] in open(f"{d}/success/workspace/review_scratch/v4_commands.txt").read())
    print("\n[J2] chain_v4_gpu3.sh / chain_v4_post_export.sh under the same harness (round 4: every require_gate call in the archive pins its gate source)")
    r = chain_case("chain_v4_gpu3.sh", "success", d)   # separate scenario dir is keyed by scenario name: reuse 'success' root is fine (fresh d per entry below)
    check("★★★ [r4] gpu3 success: STEP1 + STEP2 receipts PASS, fresh, from the pinned sources ⇒ 16 trainings, 4 merges, DONE", r["rc"] == 0 and r["train"] == 16 and r["merge"] == 4 and r["done"], {k: r[k] for k in ("rc", "train", "merge", "done", "err")})
    for sc, why in (("step2_written_by_judge", "STEP2 receipt written by the judge"), ("step1_written_by_closure_gate", "STEP1 receipt written by the closure gate"), ("changed_RAW", "RAW targets changed after STEP1")):
        r = chain_case("chain_v4_gpu3.sh", sc, d)
        check(f"★★★ [r4] gpu3 {sc}: {why} ⇒ rc 3, ZERO trainings, no DONE", r["rc"] == 3 and r["train"] == 0 and r["merge"] == 0 and not r["done"], {k: r[k] for k in ("rc", "train", "merge", "done")} | {"tail": r["log"].strip().splitlines()[-1][-140:] if r["log"].strip() else r["err"]})
    r = chain_case("chain_v4_post_export.sh", "success", d)
    check("★★★ [r4] post_export success: export markers ok, STEP1 receipt (pinned source) passes the wait loop and the dispatch require ⇒ 16 trainings, 4 merges, DONE", r["rc"] == 0 and r["train"] == 16 and r["merge"] == 4 and r["done"], {k: r[k] for k in ("rc", "train", "merge", "done", "err")})
    r = chain_case("chain_v4_post_export.sh", "step1_written_by_closure_gate", d)
    check("★★★ [r4] post_export with a STEP1 receipt from the wrong gate source ⇒ the wait loop never sees a PASS, rc 3 step1_receipt_timeout, ZERO trainings", r["rc"] == 3 and r["train"] == 0 and not r["done"] and "step1_receipt_timeout" in r["log"], {k: r[k] for k in ("rc", "train", "done")} | {"tail": r["log"].strip().splitlines()[-1][-140:] if r["log"].strip() else r["err"]})
    r = chain_case("chain_v4s_gpu.sh", "fail_shard1", d)
    check("★★ shard 1 rc 7 ⇒ rc 1, 4 trainings dispatched, no merge, no DONE (unchanged from round 2)", r["rc"] == 1 and r["train"] == 4 and r["merge"] == 0 and not r["done"], {k: r[k] for k in ("rc", "train", "merge", "done")})

    print("\n[K] chain_v4_data.sh: an unchecked cp can no longer produce DATA_DONE (reviewer data_copy_failure)")
    r = chain_case("chain_v4_data.sh", "data_fea82_missing", d)
    check("★★★ fea82 producer 'succeeds' but writes no file ⇒ FAIL_fea82_output_missing, rc 1, no CHAIN_V4_DATA_DONE (was: DATA_DONE rc 0)",
          r["rc"] == 1 and not r["done"] and "FAIL_fea82_output_missing" in r["data"], (r["rc"], r["data"].strip().splitlines()[-1][-120:] if r["data"].strip() else r["err"]))
    r = chain_case("chain_v4_data.sh", "data_success", d)
    check("★★ every producer writes its output and the copy verifies ⇒ CHAIN_V4_DATA_DONE rc 0", r["rc"] == 0 and r["done"], (r["rc"], r["data"].strip().splitlines()[-1][-120:] if r["data"].strip() else r["err"]))


# ── [L] round 3 (review 31fa3e4e §3): the judge's preconditions and its self-declared standing, on synthetic arms ────────────────────
import calendar as _cal


ELIG_INPUTS = ("wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins")   # the BUNDLE_export input contract


def bound_entry(q, arm, gate="BUNDLE_export", src=None, receipt_override=None, entry_override=None):
    """Write a finalize-shaped export receipt BOUND to (gate, gate-source sha, input shas) for `arm` and return the JUDGE_ELIGIBILITY entry naming it.
    Synthetic: the 'gate source' is the archived exporter, the inputs are small files written here (their shas are what binds)."""
    src = src or f"{HERE}/pod_export_bundle_v4.py"; inputs = {}
    for k in ELIG_INPUTS:
        open(f"{q}/{arm}_{k}.bin", "wb").write(f"{arm}:{k}".encode()); inputs[k] = f"{q}/{arm}_{k}.bin"
    rec = {"gate": gate, "PASS": True, "arm": arm, "self_sha256": _sha(src), "inputs_sha256": {k: _sha(p) for k, p in inputs.items()}, "inputs_path": inputs,
           "utc": "2026-09-10T00:00:00Z", "receipt_schema": "v4_gate_common/2 (gate, PASS, self_sha256, inputs_sha256 bound)"}
    rec.update(receipt_override or {}); path = f"{q}/export_{arm}.json"; json.dump(rec, open(path, "w"))
    e = {"receipt": path, "gate": gate, "self_sha": _sha(src), "inputs": inputs}; e.update(entry_override or {}); return e


def judge_case(d, name, n=3168, partial=False, drop_arm=False, drop_raw27=False, duplicate=False, nan_repro=False, promote=False, export_gate=None, bad_repro=False,
               promote_arm="A1e", eligibility=None, mutate=None):
    """eligibility: callable(q) -> {arm: entry} written to a file for JUDGE_ELIGIBILITY, or a str passed inline. mutate: callable(v_dir, raw_dir) run after the fixtures are written."""
    q = f"{d}/{name}"; hc = f"{q}/hc"; v = f"{hc}/dev_v4/probe_artifacts"; old = f"{hc}/dev_raw/probe_artifacts"
    os.makedirs(v); os.makedirs(old)
    ts = _cal.timegm((2025, 3, 1, 0, 0, 0)) + np.arange(3168) * 14400
    if n != 3168: ts = ts[-n:]
    if duplicate: ts = ts.copy(); ts[100] = ts[99]
    for arm in ("A0", "A0p", "A1", "A1s", "A1e", "A2", "A3"):
        for seat in ("dyn", "fix"):
            for seed in (42, 2027):
                if drop_arm and (arm, seat, seed) == ("A1e", "fix", 2027): continue
                r = np.zeros((len(ts), 23)); r[:, 0] = ts; r[:, 5] = 1.0
                r[:, 18] = 2.0 if (arm == promote_arm and promote) or (arm == "A0p" and bad_repro) else 1.0; r[:, 19] = r[:, 18]
                if nan_repro and arm == "A0p": r[0, 18] = np.nan
                np.savez(f"{v}/w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz", d30_n2_c42_rec=r)
    for seed in (42, 2027):
        if drop_raw27 and seed == 2027: continue
        r = np.zeros((len(ts), 23)); r[:, 0] = ts; r[:, 5] = 1.0; r[:, 18] = 1.0; r[:, 19] = 1.0
        np.savez(f"{old}/w10_ablation_series_RAW_M1_UCRYPTO_s{seed}.npz", d30_n2_c42_rec=r)
    if mutate is not None: mutate(v, old)
    env = {"JUDGE_HC": hc, "JUDGE_OUT": f"{q}/J.json"}
    if partial: env["JUDGE_ALLOW_PARTIAL"] = "1"
    if export_gate is not None:
        json.dump(export_gate, open(f"{q}/G2_export.json", "w")); env["JUDGE_EXPORT_GATE"] = f"{q}/G2_export.json"
    if callable(eligibility):
        json.dump(eligibility(q), open(f"{q}/ELIG.json", "w")); env["JUDGE_ELIGIBILITY"] = f"{q}/ELIG.json"
    elif isinstance(eligibility, str): env["JUDGE_ELIGIBILITY"] = eligibility
    rc, out = run(["judge_v4.py"], env)
    j = json.load(open(f"{q}/J.json")) if os.path.exists(f"{q}/J.json") else None
    return rc, out, j


with tempfile.TemporaryDirectory() as d:
    print("\n[L] judge_v4: exact axis, both references, finiteness, exploratory standing, export-gate eligibility")
    rc, out, j = judge_case(d, "full_valid")
    check("★★★ full valid synthetic set (equal arms) ⇒ rc 0, 18 verdicts all (C), eligibility informational (no export gate given), not exploratory",
          rc == 0 and j and len(j["verdicts"]) == 18 and all(v.startswith("(C)") for v in j["verdicts"].values()) and j["eligibility"] == "informational" and j["exploratory"] is False,
          (rc, j and {k: j.get(k) for k in ("eligibility", "exploratory", "n_extended_more_anchors")}, out.strip().splitlines()[-1][:100] if out.strip() else out))
    check("★ the extended-window surplus is COMPUTED (0 here: the synthetic arms end at the frozen window)", j and j.get("n_extended_more_anchors") == 0, j and j.get("n_extended_more_anchors"))
    rc, out, j = judge_case(d, "missing_raw2027", drop_raw27=True)
    check("★★★ the seed-2027 A0p reference missing ⇒ rc 3 (reviewer: `any` accepted one reference)", rc == 3 and "missing_reference" in out and "A0p_dyn_s2027" in out, out.strip().splitlines()[-1][-160:])
    rc, out, j = judge_case(d, "duplicate_anchor", duplicate=True)
    check("★★★ one anchor duplicated (count still 3168) ⇒ rc 2 at the axis gate (reviewer: 3168 was a count, not a set)", rc == 2 and "not a strict 4h grid" in out, out.strip().splitlines()[-1][-160:])
    rc, out, j = judge_case(d, "short60", n=60)
    check("★★ 60 anchors ⇒ rc 2 (coverage)", rc == 2, out.strip().splitlines()[-1][-120:])
    rc, out, j = judge_case(d, "nan_repro", nan_repro=True)
    check("★★★ a NaN in the A0p reference ⇒ rc 3 (reviewer: NaN > tol is False, used to pass)", rc == 3 and ("nonfinite" in out or "non-finite" in out), out.strip().splitlines()[-1][-160:])
    rc, out, j = judge_case(d, "bad_repro", bad_repro=True)
    check("★★ A0p off by 1 bps ⇒ rc 3 (unchanged from round 2)", rc == 3 and "paired_maxabs_bad" in out, out.strip().splitlines()[-1][-120:])
    rc, out, j = judge_case(d, "missing_arm", drop_arm=True)
    check("★★ a required arm missing ⇒ rc 2", rc == 2 and "A1e_fix_s2027" in out, out.strip().splitlines()[-1][-120:])
    rc, out, j = judge_case(d, "partial_short_promote", n=60, partial=True, promote=True)
    check("★★★ JUDGE_ALLOW_PARTIAL=1 on 60 anchors with A1e +1 bps ⇒ rc 0 but exploratory=true and NO verdict is a PROMOTE (reviewer: 4 PROMOTEs used to print)",
          rc == 0 and j and j["exploratory"] is True and j["verdicts"] and all(v.startswith("EXPLORATORY") for v in j["verdicts"].values()),
          (rc, j and j["exploratory"], j and sorted(set(j["verdicts"].values()))))
    rc, out, j = judge_case(d, "promote_no_export_gate", promote=True)
    check("★★★ full window, A1e +1 bps, NO export gate ⇒ the (A) cells read '(A) INFO — export gate not PASS', eligibility informational (reviewer: PROMOTE printed beside a failed G2)",
          rc == 0 and j and j["eligibility"] == "informational" and any(v.startswith("(A) INFO") for v in j["verdicts"].values()) and not any(v == "(A) PROMOTE" for v in j["verdicts"].values()),
          (rc, j and sorted(set(j["verdicts"].values()))))
    rc, out, j = judge_case(d, "promote_export_FAIL", promote=True, export_gate={"gate": "G2_export_v4e", "PASS": False, "reason": "baseline_guard"})
    check("★★★ with an export-gate receipt PASS=false ⇒ same: INFO, never PROMOTE", rc == 0 and j and j["eligibility"] == "informational" and j["export_gate"]["PASS"] is False and not any(v == "(A) PROMOTE" for v in j["verdicts"].values()),
          (rc, j and j["export_gate"]))
    rc, out, j = judge_case(d, "promote_export_PASS", promote=True, export_gate={"gate": "G2_export_v4e", "PASS": True})
    check("★★★ [r4] the DEPRECATED alias JUDGE_EXPORT_GATE with PASS=true ⇒ still informational, NO PROMOTE, a printed deprecation warning (round 3 let this bare receipt promote)",
          rc == 0 and j and j["eligibility"] == "informational" and j["eligible_arms"] == [] and j["export_gate"]["deprecated"] is True and j["export_gate"]["PASS"] is True
          and not any(v == "(A) PROMOTE" for v in j["verdicts"].values()) and "JUDGE_EXPORT_GATE is DEPRECATED" in out,
          (rc, j and j["eligibility"], j and sorted(set(j["verdicts"].values()))))

    # ── round 4: eligibility is PER ARM and IDENTITY-BOUND (researcher extra cases judge_minimal_PASS / judge_unrelated_stale_PASS / judge_A1e_gate_promotes_other_arm)
    def _no_promote(j): return j and not any(v == "(A) PROMOTE" for v in j["verdicts"].values())
    rc, out, j = judge_case(d, "r4_minimal_PASS", promote=True, eligibility=lambda q: {"A1e": {"receipt": (json.dump({"PASS": True}, open(f"{q}/min.json", "w")) or f"{q}/min.json")}})
    check("★★★ [r4] judge_minimal_PASS: JUDGE_ELIGIBILITY names a bare {PASS:true} for A1e ⇒ informational, A1e NOT eligible (no gate/source/inputs), no PROMOTE anywhere",
          rc == 0 and j and j["eligibility"] == "informational" and j["eligibility_by_arm"]["A1e"]["ok"] is False and _no_promote(j), (rc, j and j["eligibility_by_arm"]))
    rc, out, j = judge_case(d, "r4_wrong_gate_name", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e", entry_override={"gate": "G2_closure"})})
    check("★★★ [r4] a bound PASS receipt from ANOTHER gate (BUNDLE_export receipt, caller expects G2_closure) ⇒ A1e not eligible, no PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "caller expected 'G2_closure'" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _stale(q):
        e = bound_entry(q, "A1e"); open(e["inputs"]["bundle_cache"], "wb").write(b"cache rebuilt AFTER the export receipt"); return {"A1e": e}
    rc, out, j = judge_case(d, "r4_stale_input", promote=True, eligibility=_stale)
    check("★★★ [r4] judge_unrelated_stale_PASS: a bound receipt whose input changed after it was written ⇒ A1e not eligible ('changed since the receipt'), no PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "changed since the receipt" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r4_gate_promotes_other_arm", promote=True, promote_arm="A1", eligibility=lambda q: {"A1e": bound_entry(q, "A1e")})
    check("★★★ [r4] judge_A1e_gate_promotes_other_arm: A1 +1 bps, the ONLY bound PASS is A1e's ⇒ A1's (A) cells read INFO, A1e is eligible but has nothing to promote: ZERO PROMOTE",
          rc == 0 and j and j["eligible_arms"] == ["A1e"] and j["eligibility"] == "candidate" and _no_promote(j)
          and all(j["verdicts"][f"A1-{b}|{s}"].startswith("(A) INFO") and "arm A1" in j["verdicts"][f"A1-{b}|{s}"] for b in ("A0", "A2", "A3") for s in ("dyn", "fix")),
          (rc, j and j["eligible_arms"], j and sorted(set(j["verdicts"].values()))))
    rc, out, j = judge_case(d, "r4_bound_A1e_promotes_A1e", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")})
    check("★★★ [r4] GREEN: a correctly bound export receipt for A1e (gate name + gate source sha + every input sha) with A1e +1 bps ⇒ candidate, eligible_arms=[A1e], exactly the 4 A1e cells read (A) PROMOTE",
          rc == 0 and j and j["eligibility"] == "candidate" and j["eligible_arms"] == ["A1e"] and j["eligibility_by_arm"]["A1e"]["ok"] is True
          and sorted(k for k, v in j["verdicts"].items() if v == "(A) PROMOTE") == ["A1e-A0|dyn", "A1e-A0|fix", "A1e-A1|dyn", "A1e-A1|fix"]
          and all(v == "(C) UNDECIDED" for k, v in j["verdicts"].items() if not k.startswith("A1e")), (rc, j and j["eligible_arms"], j and sorted(set(j["verdicts"].values()))))
    _q = f"{d}/r4_inline_json"; os.makedirs(_q); _e = bound_entry(_q, "A1e")
    rc, out, j = judge_case(d, "r4_inline_json", promote=True, eligibility=json.dumps({"A1e": _e}))
    check("★★ [r4] JUDGE_ELIGIBILITY given INLINE as JSON text (not a path) binds the same way", rc == 0 and j and j["eligible_arms"] == ["A1e"] and sum(v == "(A) PROMOTE" for v in j["verdicts"].values()) == 4, (rc, j and j["eligible_arms"]))
    rc, out, j = judge_case(d, "r4_garbage_env", promote=True, eligibility="{not json")
    check("★★ [r4] an unparseable JUDGE_ELIGIBILITY is ignored with a warning, never treated as permission: informational, eligibility_error set, no PROMOTE",
          rc == 0 and j and j["eligibility"] == "informational" and j["eligibility_error"] and _no_promote(j) and "JUDGE_ELIGIBILITY ignored" in out, (rc, j and j["eligibility_error"]))
    rc, out, j = judge_case(d, "r4_no_pin", promote=True, eligibility=lambda q: {"A1e": {k: v for k, v in bound_entry(q, "A1e").items() if k != "self_sha"}})
    check("★★★ [r4] an eligibility entry that does not pin the gate source (no self_sha) ⇒ A1e not eligible ('did not pin'), no PROMOTE", rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "did not pin" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _drop_cache(q):
        e = bound_entry(q, "A1e"); e["inputs"] = {k: v for k, v in e["inputs"].items() if k != "bundle_cache"}; return {"A1e": e}
    rc, out, j = judge_case(d, "r4_missing_registered_input", promote=True, eligibility=_drop_cache)
    check("★★★ [r4] an eligibility entry that omits a registered BUNDLE_export input (bundle_cache) ⇒ A1e not eligible, no PROMOTE", rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "omitted registered input(s) ['bundle_cache']" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r4_list_not_map", promote=True, eligibility=json.dumps([{"receipt": "x"}]))
    check("★ [r4] a JSON list instead of {arm: entry} ⇒ ignored (informational, no PROMOTE)", rc == 0 and j and j["eligibility"] == "informational" and _no_promote(j), (rc, j and j["eligibility_error"]))


# ── [M] round 3 (review 31fa3e4e §6, AMENDMENT 4): G1 clause (c) is code, and the six anchors must be present ────────────────────
sys.path.insert(0, HERE)
import v4e_parity_lib as _PL
print("\n[M] G1 axis clause (c) and anchor presence")
_Eo = 1_600_000_000 + 14400 * np.arange(200)
_two = list(_PL.DEFAULT_ALLOWED_NEW)
_En = np.sort(np.concatenate([np.array(_two, dtype=np.int64), _Eo]))
_c = _PL.axis_clause(_En, _Eo)
check("★★★ the two clamp-produced 2022-01-07 anchors added in front ⇒ (c) ok, both listed as allowed_hits, no unexplained", _c["ok"] and _c["allowed_hits"] == sorted(_two) and _c["unexplained_new"] == [], _c)
_En2 = np.sort(np.concatenate([np.array(_two + [1_500_000_000], dtype=np.int64), _Eo]))
_c = _PL.axis_clause(_En2, _Eo)
check("★★★ a THIRD early anchor not in the allowed list ⇒ (c) FAILS and names it (reviewer: early anchors passed as a report field)", not _c["ok"] and _c["unexplained_new"] == [1_500_000_000], _c)
_c = _PL.axis_clause(np.append(_Eo, _Eo[-1] + 14400), _Eo)
check("★★ a single extra anchor at the TAIL of the new axis ⇒ ok (tail difference ≤ 1)", _c["ok"] and _c["unexplained_new"] == [int(_Eo[-1] + 14400)], _c)
_c = _PL.axis_clause(_Eo[:-1], _Eo)
check("★★ the old axis has one extra TAIL anchor ⇒ ok", _c["ok"] and _c["old_not_in_new"] == [int(_Eo[-1])], _c)
_c = _PL.axis_clause(np.delete(_Eo, 50), _Eo)
check("★★★ the new axis LACKS an interior old anchor ⇒ (c) FAILS", not _c["ok"] and _c["old_not_in_new"] == [int(_Eo[50])], _c)
_c = _PL.axis_clause(np.append(_Eo, [_Eo[-1] + 14400, _Eo[-1] + 28800]), _Eo)
check("★★ TWO extra tail anchors ⇒ FAILS (only one may differ)", not _c["ok"], _c["unexplained_new"])
_c = _PL.axis_clause(_En, _Eo, allowed_new=_PL.parse_allowed(""))
check("★★ G1_ALLOWED_NEW_ANCHORS='' (no exception) ⇒ the same two anchors now FAIL (the exception is explicit, never implicit)", not _c["ok"] and sorted(_c["unexplained_new"]) == sorted(_two), _c["unexplained_new"])
check("★ parse_allowed: None ⇒ default pair; '1,2' ⇒ (1, 2)", _PL.parse_allowed(None) == tuple(_two) and _PL.parse_allowed("1, 2") == (1, 2))
_pr = _PL.anchors_present(_Eo, [int(_Eo[3]), 123])
check("★★ anchors_present names the missing one", _pr[int(_Eo[3])] is True and _pr[123] is False, _pr)
_src = open(f"{HERE}/v4e_gate_parity.py").read()
check("★★★ the gate's PASS is (a) and (b) and (c) and anchors-present — wiring, not prose", '"PASS": bool(ok_a and ok_b and ok_c and ok_present)' in _src and "axis_clause(En, Eo, ALLOWED_NEW)" in _src and "anchors_present(En, ANCHORS)" in _src)

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
