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

    print("\n[E] `require`: chains may only dispatch on a fresh PASS receipt OF THE EXPECTED GATE with declared inputs")
    rc, out = gate(d); assert rc == 0
    G = "gate=G2_closure"
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, f"fea_A={d}/fA.npz", f"targets_B={d}/tB.npz"])
    check("★★★ PASS receipt + expected gate + unchanged inputs ⇒ rc 0", rc == 0 and "REQUIRE_OK" in out, out.strip()[-120:])
    np.savez(f"{d}/fA.npz", X=fx["X"] + 1, pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, f"fea_A={d}/fA.npz"])
    check("★★★ an input that changed AFTER the receipt ⇒ rc 3 (stale receipt is not a receipt)", rc == 3 and "changed since the receipt" in out, out.strip()[-120:])
    np.savez(f"{d}/fA.npz", X=fx["X"].copy(), pair_a=fx["pa"], pair_s=fx["ps"], names=fx["names"])
    json.dump({"gate": "G2_closure", "PASS": False, "inputs_sha256": {}, "self_sha256": "ab" * 32}, open(f"{d}/bad.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/bad.json", G, f"fea_A={d}/fA.npz"])
    check("★★ a FAIL receipt ⇒ rc 3", rc == 3 and "PASS=False" in out, out.strip()[-120:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/nope.json", G, f"fea_A={d}/fA.npz"])
    check("★★ a missing receipt ⇒ rc 3", rc == 3 and "missing" in out)
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, f"unknown_input={d}/fA.npz"])
    check("★ an input the receipt never hashed ⇒ rc 3 (no silent pass on an unrecorded dependency)", rc == 3 and "no sha for input" in out)
    # ── round 3 (review 31fa3e4e §2): identity and dependency binding ──
    good = json.load(open(f"{d}/out.json"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", "gate=UNRELATED_GATE", f"fea_A={d}/fA.npz"])
    check("★★★ [r3] a PASS receipt from ANOTHER gate ⇒ rc 3 (reviewer: wrong gate name used to pass)", rc == 3 and "caller expected 'UNRELATED_GATE'" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", f"fea_A={d}/fA.npz"])
    check("★★★ [r3] a caller that names NO gate ⇒ rc 3 (no anonymous requires)", rc == 3 and "did not declare the gate" in out, out.strip()[-140:])
    for label, ss in (("all-zero", "0" * 64), ("missing", None), ("garbage", "not-a-sha")):
        json.dump(dict(good, self_sha256=ss), open(f"{d}/ss.json", "w"))
        rc, out = run(["v4_gate_common.py", "require", f"{d}/ss.json", G, f"fea_A={d}/fA.npz"])
        check(f"★★★ [r3] self_sha256 {label} ⇒ rc 3 (reviewer: pseudo/absent self sha used to pass)", rc == 3 and "no usable self_sha256" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, "self_sha=" + "ab" * 32, f"fea_A={d}/fA.npz"])
    check("★★ [r3] a pinned gate source that differs from the receipt's ⇒ rc 3", rc == 3 and "caller trusts" in out, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G, "self_sha=" + good["self_sha256"], f"fea_A={d}/fA.npz"])
    check("★★ [r3] the pinned gate source that MATCHES ⇒ rc 0", rc == 0, out.strip()[-140:])
    rc, out = run(["v4_gate_common.py", "require", f"{d}/out.json", G])
    check("★★★ [r3] an EMPTY dependency list ⇒ rc 3 (reviewer: {PASS:true} with no inputs used to pass)", rc == 3 and "declared no inputs" in out, out.strip()[-140:])
    json.dump({"PASS": True, "gate": "G2_closure"}, open(f"{d}/arbitrary.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/arbitrary.json", G, f"fea_A={d}/fA.npz"])
    check("★★ [r3] a hand-written {PASS:true, gate} with no self sha and no input shas ⇒ rc 3", rc == 3, out.strip()[-140:])
    json.dump(dict(good, inputs_sha256=dict(good["inputs_sha256"], fea_A=None)), open(f"{d}/nullsha.json", "w"))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/nullsha.json", G, f"fea_A={d}/fA.npz"])
    check("★ [r3] a receipt whose input sha is null (the gate never saw the file) ⇒ rc 3", rc == 3 and "recorded no sha" in out, out.strip()[-140:])


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

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
