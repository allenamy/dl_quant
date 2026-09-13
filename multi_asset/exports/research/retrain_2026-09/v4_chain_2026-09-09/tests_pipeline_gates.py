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
    # ── round 5 (researcher drift case): an edited gate that re-runs signs its own receipt; the runtime pin matches it; the frozen contract does not ──
    os.makedirs(f"{d}/edited"); open(f"{d}/edited/v4_gate_common.py", "w").write(open(f"{HERE}/v4_gate_common.py").read())
    open(f"{d}/edited/v4_gate_closure.py", "w").write(open(f"{HERE}/v4_gate_closure.py").read() + "\n# local edit after review\n")
    rc, out = run([f"{d}/edited/v4_gate_closure.py", f"{d}/fA.npz", f"{d}/fB.npz", f"{d}/tA.npz", f"{d}/tB.npz", f"{d}/edited_out.json"], {"HOLE_CELLS": f"{d}/holes.npz", "EXPECT_NCOLS": "89"})
    ed = json.load(open(f"{d}/edited_out.json"))
    check("★ [r5] the edited gate runs and PASSes on its own, signing the receipt with ITS sha", rc == 0 and ed["PASS"] is True and ed["self_sha256"] == _sha(f"{d}/edited/v4_gate_closure.py"), (rc, out[-160:]))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/edited_out.json", G, "self_sha=" + ed["self_sha256"]] + ALL5)
    check("★★★ [r5] require pinned to the edited gate's OWN runtime sha ⇒ rc 3 'not an APPROVED source' (round 4: pin == receipt ⇒ accepted; the reviewer's drift case)",
          rc == 3 and "not an APPROVED source" in out, out.strip()[-200:])
    rc, out = run(["v4_gate_common.py", "approved", "G2_closure", ed["self_sha256"]])
    check("★ [r5] the CLI `approved` sub-command answers NOT_APPROVED for it (rc 3) and APPROVED for the archived gate (rc 0)",
          rc == 3 and run(["v4_gate_common.py", "approved", "G2_closure", _sha(f"{HERE}/v4_gate_closure.py")])[0] == 0, out.strip()[-120:])
    os.makedirs(f"{d}/nocontract"); open(f"{d}/nocontract/v4_gate_common.py", "w").write(open(f"{HERE}/v4_gate_common.py").read())
    rc, out = run([f"{d}/nocontract/v4_gate_common.py", "require", f"{d}/out.json", G, SS] + ALL5)
    check("★★ [r5] a governed gate required through a v4_gate_common with NO frozen contract beside it ⇒ rc 3 (nothing can be required without the reviewed definition)",
          rc == 3 and "frozen contract missing" in out, out.strip()[-160:])
    rc, out = run([f"{d}/nocontract/v4_gate_common.py", "require", f"{d}/g9.json", "gate=G9_unregistered", "self_sha=" + s1["self_sha256"], f"extra_recorded={d}/holes.npz"])
    check("★ [r5] an UNGOVERNED gate (not registered, not in the contract) is unaffected by a missing contract (rc 0) — and confers nothing (arms map only to contract gates)", rc == 0, out.strip()[-120:])
    _ct = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
    check("★★★ [r5→r6] the ARCHIVED contract is self-consistent: approved sources of G2/STEP1/STEP2 are exactly the archived gate files' shas; BUNDLE_export approves exactly the archived v2 export gate (v4e_gate_export_v2.py, applied 2026-09-12 on user word after r20 closed N1; was [] while the physical gate did not exist); every candidate arm maps to BUNDLE_export with book binding",
          _ct["gates"]["G2_closure"]["approved_source_sha256"] == [_sha(f"{HERE}/v4_gate_closure.py")] and _ct["gates"]["STEP1"]["approved_source_sha256"] == [_sha(f"{HERE}/v4_gate_step1.py")]
          and _ct["gates"]["STEP2"]["approved_source_sha256"] == [_sha(f"{HERE}/v4_gate_step2.py")] and _ct["gates"]["BUNDLE_export"]["approved_source_sha256"] == [_sha(f"{HERE}/v4e_gate_export_v2.py")] and _ct["gates"]["BUNDLE_export"]["source"] == "v4e_gate_export_v2.py" and _ct["status"].startswith("APPLIED 2026-09-12")
          and set(_ct["arms"]) == {"A1", "A1s", "A1e", "A2", "A3"} and all(a["candidacy_gate"] == "BUNDLE_export" and a["book_binding"] for a in _ct["arms"].values()),
          {g: [x[:8] for x in v["approved_source_sha256"]] for g, v in _ct["gates"].items()})
    check("★ [r5] make_sha_manifest.py lists the contract as a reviewed file", 'f == "ELIGIBILITY_CONTRACT.json"' in open(f"{HERE}/make_sha_manifest.py").read())
    import importlib; sys.path.insert(0, HERE); _gc = importlib.import_module("v4_gate_common")
    check("★★ [r4] REQUIRED_INPUTS names exactly what the archived chains declare: G2 5 (v4s), STEP1@v4s 2, STEP1@v4 4 (gpu3/post_export), STEP2 2",
          set(_gc.REQUIRED_INPUTS["G2_closure"]) == {"fea_A", "fea_B", "targets_A", "targets_B", "hole_cells"} and _gc.REQUIRED_INPUTS["STEP1@v4"] == ["dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4"]
          and _gc.REQUIRED_INPUTS["STEP2"] == ["wide_fea_v4", "wide_fea_v4_meta"] and "profile=v4s" in open(f"{HERE}/chain_v4s_gpu.sh").read() and "profile=v4" in open(f"{HERE}/chain_v4_gpu3.sh").read() and "profile=v4" in open(f"{HERE}/chain_v4_post_export.sh").read())
    check("★★ [r5→r6] REQUIRED_INPUTS[BUNDLE_export] = the 7 export inputs + the arm's 4 judged books at [7:11] + (round 6) the 4 baseline books, manifest, 8 bundle files, costb/umask/slow, the contract = 28 = the v2 export gate's closure (exact list vs the real receipt asserted in [O])",
          _gc.REQUIRED_INPUTS["BUNDLE_export"][7:11] == list(_gc.BOOK_INPUTS) and len(_gc.REQUIRED_INPUTS["BUNDLE_export"]) == 28
          and _gc.REQUIRED_INPUTS["BUNDLE_export"][:7] == ["wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins"], len(_gc.REQUIRED_INPUTS["BUNDLE_export"]))


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
    # round 5: the frozen contract travels with the device; its approved sources are the TRANSLATED gate scripts (path translation changes the bytes)
    _ct = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
    for _g, _f in (("G2_closure", "v4_gate_closure.py"), ("STEP1", "v4_gate_step1.py"), ("STEP2", "v4_gate_step2.py")):
        _ct["gates"][_g]["approved_source_sha256"] = [_sha(f"{rr}/{_f}")]
    json.dump(_ct, open(f"{rr}/ELIGIBILITY_CONTRACT.json", "w"), indent=1)
    if scenario == "gate_edited_rerun":   # round 5 (researcher drift case): the closure gate is edited locally AFTER the contract froze its sha; the chain pins the runtime sha of the edited file
        open(f"{rr}/v4_gate_closure.py", "a").write("\n# local edit after review: not the approved program\n")
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
    env = dict(os.environ, PATH=f"{root}/bin:" + os.environ["PATH"], V4_LEGACY_OK="1")   # R5 (2026-09-12): the legacy chains refuse without V4_LEGACY_OK=1; the harness runs them deliberately
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
    r = chain_case("chain_v4s_gpu.sh", "gate_edited_rerun", d)
    check("★★★ [r5] chain_runtime_gate_sha_accepts_changed_recipe: the closure gate edited after the contract froze its sha, receipt signed by the edited gate, chain pins the runtime sha ⇒ rc 3 'not an APPROVED source', ZERO trainings, no DONE (round 4: rc 0, 8 trainings, DONE)",
          r["rc"] == 3 and r["train"] == 0 and r["merge"] == 0 and not r["done"] and "not an APPROVED source" in r["log"], {k: r[k] for k in ("rc", "train", "merge", "done")} | {"tail": r["log"].strip().splitlines()[-1][-200:] if r["log"].strip() else r["err"]})
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


ELIG_UPSTREAM = ("wide_fea_v4", "wide_fea_v4_meta", "bundle_base", "export_panel", "bundle_cache", "fund_aug", "live_pins")   # the exporter's 7 upstream inputs (the round-5 floor minus the books)
ELIG_BASELINE = ("base_dyn_s42", "base_dyn_s2027", "base_fix_s42", "base_fix_s2027")                                          # ROUND 6: the approved A0 baseline books (v2 gate E9)
ELIG_BUNDLE_FILES = ("slow_pred_pinned.npy", "slow2026.txt", "config.json", "cache_tail_40d.npz", "fund_ema_v1_state.json",
                     "funding_ledger_seed.json", "leg_returns.npz", "parity_signals_aug.json")                                # ROUND 6: the shipped bundle's closure (v2 gate E1: MANIFEST + every listed file)
ELIG_MISC = ("costb_json", "umask_npz", "slow_npy", "eligibility_contract")                                                    # ROUND 6: cost model, mask, king file (E6), the standard itself (E0)
ELIG_INPUTS = ELIG_UPSTREAM + ELIG_BASELINE + ("bundle_manifest",) + tuple(f"bundle/{f}" for f in ELIG_BUNDLE_FILES) + ELIG_MISC   # the 24 names a JUDGE_ELIGIBILITY entry declares; the judge adds the 4 judged books = the v2 gate's 28-name closure


def bound_entry(q, arm, gate="BUNDLE_export", src=None, receipt_override=None, entry_override=None, bind_books=True, books_of=None, extra_inputs=None):
    """Write a finalize-shaped export receipt BOUND to (gate, gate-source sha, input shas, the arm's four judged books) for `arm` and return the
    JUDGE_ELIGIBILITY entry naming it. Synthetic: the 'gate source' is the archived exporter (the test contract approves it), the inputs are small
    files written here (their shas are what binds). Round 5: the receipt also hashes book_<seat>_s<seed> = the judged w10 files of `books_of` (default arm).
    ROUND 6 (DESIGN_judge_floor_28_2026-09-12): the entry declares the v2 export gate's FULL closure in its real shape — the 7 upstream files, the 4
    approved baseline books (= the hc A0 books, the path shape v4e_gate_export_v2.derive_paths uses), a bundle directory with the 8 shipped files and
    a MANIFEST.json {file: sha256} (E1), costb/umask/slow files (E6) and the contract the judge reads (q/device/ELIGIBILITY_CONTRACT.json when the device
    copy exists — judge_case writes it before calling this — else the archived one). extra_inputs: {name: path} recorded AND declared on top of the
    floor (a FEMAT arm's femat / signal_receipt — extras the floor allows and require still verifies)."""
    src = src or f"{HERE}/pod_export_bundle_v4.py"; inputs = {}
    for k in ELIG_UPSTREAM + ELIG_MISC[:3]:
        open(f"{q}/{arm}_{k}.bin", "wb").write(f"{arm}:{k}".encode()); inputs[k] = f"{q}/{arm}_{k}.bin"
    for seat in ("dyn", "fix"):
        for seed in (42, 2027):
            inputs[f"base_{seat}_s{seed}"] = f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{seed}.npz"   # the approved baseline arm is A0 (contract approved_baseline.baseline_arm)
    bdir = f"{q}/{arm}_bundle"; os.makedirs(bdir, exist_ok=True); man = {}
    for f in ELIG_BUNDLE_FILES:
        open(f"{bdir}/{f}", "wb").write(f"{arm}:bundle:{f}".encode()); man[f] = _sha(f"{bdir}/{f}"); inputs[f"bundle/{f}"] = f"{bdir}/{f}"
    json.dump(man, open(f"{bdir}/MANIFEST.json", "w")); inputs["bundle_manifest"] = f"{bdir}/MANIFEST.json"
    cpath = f"{q}/device/ELIGIBILITY_CONTRACT.json"
    inputs["eligibility_contract"] = cpath if os.path.exists(cpath) else f"{HERE}/ELIGIBILITY_CONTRACT.json"
    inputs.update(extra_inputs or {})
    shas = {k: _sha(p) for k, p in inputs.items() if os.path.exists(p)}
    if bind_books:
        for seat in ("dyn", "fix"):
            for seed in (42, 2027):
                bp = f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_{books_of or arm}_{seat}_s{seed}.npz"
                if os.path.exists(bp): shas[f"book_{seat}_s{seed}"] = _sha(bp)
    rec = {"gate": gate, "PASS": True, "arm": arm, "self_sha256": _sha(src), "inputs_sha256": shas, "inputs_path": inputs,
           "utc": "2026-09-10T00:00:00Z", "receipt_schema": "v4_gate_common/2 (gate, PASS, self_sha256, inputs_sha256 bound)"}
    rec.update(receipt_override or {}); path = f"{q}/export_{arm}.json"; json.dump(rec, open(path, "w"))
    e = {"receipt": path, "gate": gate, "self_sha": _sha(src), "inputs": inputs}; e.update(entry_override or {}); return e


def test_contract(approve_exporter=True):
    """The archived frozen contract with BUNDLE_export's approved list = [sha of the archived exporter] (the synthetic gate source bound_entry signs with)."""
    c = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json"))
    c["gates"]["BUNDLE_export"]["approved_source_sha256"] = [_sha(f"{HERE}/pod_export_bundle_v4.py")] if approve_exporter else []
    return c


def judge_case(d, name, n=3168, partial=False, drop_arm=False, drop_raw27=False, duplicate=False, nan_repro=False, promote=False, export_gate=None, bad_repro=False,
               promote_arm="A1e", eligibility=None, mutate=None, contract="test", post_mutate=None, strict=False, judge_src=None):
    """eligibility: callable(q) -> {arm: entry} written to a file for JUDGE_ELIGIBILITY, or a str passed inline. mutate: callable(v_dir, raw_dir) run after the fixtures are written.
    Round 5: the judge runs from a DEVICE COPY (q/device: judge_v4.py + v4_gate_common.py + a contract) — contract="test" approves the archived exporter for
    BUNDLE_export (positive controls), "archive" runs the archived judge in place with the shipped contract, "none" ships no contract, or a dict is written verbatim.
    post_mutate: callable(v_dir, raw_dir) run AFTER the eligibility receipts are written (a book replaced after the receipt). strict: JUDGE_REQUIRE_W=1."""
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
    if strict: env["JUDGE_REQUIRE_W"] = "1"
    if export_gate is not None:
        json.dump(export_gate, open(f"{q}/G2_export.json", "w")); env["JUDGE_EXPORT_GATE"] = f"{q}/G2_export.json"
    judge = "judge_v4.py"
    if contract != "archive":   # round 6: the device copy (and its contract) is written BEFORE the eligibility callback, so a bound entry can hash the contract the judge will read
        os.makedirs(f"{q}/device")
        for f in ("judge_v4.py", "v4_gate_common.py"): open(f"{q}/device/{f}", "w").write(open(f"{HERE}/{judge_src if (judge_src and f == 'judge_v4.py') else f}").read())   # round 7: judge_src runs an ARCHIVED judge in the device (old-code-is-red controls)
        if contract == "test": json.dump(test_contract(), open(f"{q}/device/ELIGIBILITY_CONTRACT.json", "w"))
        elif isinstance(contract, dict): json.dump(contract, open(f"{q}/device/ELIGIBILITY_CONTRACT.json", "w"))
        judge = f"{q}/device/judge_v4.py"
    if callable(eligibility):
        _el = eligibility(q)
        if isinstance(_el, str): env["JUDGE_ELIGIBILITY"] = _el                      # inline JSON text (round 5: books exist by now, so the entry can bind them)
        else: json.dump(_el, open(f"{q}/ELIG.json", "w")); env["JUDGE_ELIGIBILITY"] = f"{q}/ELIG.json"
    elif isinstance(eligibility, str): env["JUDGE_ELIGIBILITY"] = eligibility
    if post_mutate is not None: post_mutate(v, old)
    rc, out = run([judge], env)
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
    check("★★★ [r4→r5] the caller names gate=G2_closure for A1e while the frozen contract says BUNDLE_export ⇒ 'caller-supplied standard conflicts', A1e not eligible, no PROMOTE (round 4 let the caller name the gate)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "conflicts with the frozen contract" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
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
    rc, out, j = judge_case(d, "r4_inline_json", promote=True, eligibility=lambda q: json.dumps({"A1e": bound_entry(q, "A1e")}))
    check("★★ [r4] JUDGE_ELIGIBILITY given INLINE as JSON text (not a path) binds the same way", rc == 0 and j and j["eligible_arms"] == ["A1e"] and sum(v == "(A) PROMOTE" for v in j["verdicts"].values()) == 4, (rc, j and j["eligible_arms"]))
    rc, out, j = judge_case(d, "r4_garbage_env", promote=True, eligibility="{not json")
    check("★★ [r4] an unparseable JUDGE_ELIGIBILITY is ignored with a warning, never treated as permission: informational, eligibility_error set, no PROMOTE",
          rc == 0 and j and j["eligibility"] == "informational" and j["eligibility_error"] and _no_promote(j) and "JUDGE_ELIGIBILITY ignored" in out, (rc, j and j["eligibility_error"]))
    rc, out, j = judge_case(d, "r4_no_pin", promote=True, eligibility=lambda q: {"A1e": {k: v for k, v in bound_entry(q, "A1e").items() if k != "self_sha"}})
    check("★★★ [r4→r5] an entry with NO self_sha is fine — the pin now comes from the frozen contract, not the caller: A1e eligible, 4 PROMOTE (round 4 required the caller to pin, which is the wrong party)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is True and sum(v == "(A) PROMOTE" for v in j["verdicts"].values()) == 4, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r5_receipt_from_unapproved_source", promote=True,
                            eligibility=lambda q: {"A1e": {k: v for k, v in bound_entry(q, "A1e", receipt_override={"self_sha256": _sha(f"{HERE}/judge_v4.py")}).items() if k != "self_sha"}})
    check("★★★ [r5] a BUNDLE_export receipt written by a program whose sha is NOT in the contract's approved list (the judge's) ⇒ A1e not eligible ('not an approved source'), no PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "not an approved source" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _drop_cache(q):
        e = bound_entry(q, "A1e"); e["inputs"] = {k: v for k, v in e["inputs"].items() if k != "bundle_cache"}; return {"A1e": e}
    rc, out, j = judge_case(d, "r4_missing_registered_input", promote=True, eligibility=_drop_cache)
    check("★★★ [r4] an eligibility entry that omits a registered BUNDLE_export input (bundle_cache) ⇒ A1e not eligible, no PROMOTE", rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "omitted registered input(s) ['bundle_cache']" in j["eligibility_by_arm"]["A1e"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r4_list_not_map", promote=True, eligibility=json.dumps([{"receipt": "x"}]))
    check("★ [r4] a JSON list instead of {arm: entry} ⇒ ignored (informational, no PROMOTE)", rc == 0 and j and j["eligibility"] == "informational" and _no_promote(j), (rc, j and j["eligibility_error"]))

    # ── round 4: RAW references validated before the reproduction; NPZ schema + integer timestamps validated in load() (researcher extra cases) ──
    import glob as _glob
    def _rewrite(pattern, fn):
        for p in sorted(_glob.glob(pattern)):
            z = np.load(p, allow_pickle=True); arrays = {k: z[k] for k in z.files}; arrays = fn(arrays) or arrays; np.savez(p, **arrays)
    def _raw_only60(v, old): _rewrite(f"{old}/*.npz", lambda a: dict(a, d30_n2_c42_rec=a["d30_n2_c42_rec"][-60:]))
    rc, out, j = judge_case(d, "r4_both_raw_only60", mutate=_raw_only60)
    check("★★★ [r4] judge_both_raw_references_only60: both RAW references carry only the last 60 frozen anchors ⇒ rc 2 at the reference-axis gate (round 3: intersect1d reproduced on 60 and passed)",
          rc == 2 and "JUDGE_REFUSED reference axis" in out and "n=60 != 3168" in out, out.strip().splitlines()[-1][-200:])
    def _raw_dup_gap(v, old):
        def f(a): r = a["d30_n2_c42_rec"].copy(); r[100, 0] = r[99, 0]; return dict(a, d30_n2_c42_rec=r)
        _rewrite(f"{old}/*.npz", f)
    rc, out, j = judge_case(d, "r4_raw_duplicate_and_gap", mutate=_raw_dup_gap)
    check("★★★ [r4] judge_raw_duplicate_and_gap: RAW references with anchor 100 duplicated onto 99 (count still 3168) ⇒ rc 2 'not a strict 4h grid' (round 3: intersect1d deduplicated and passed)",
          rc == 2 and "JUDGE_REFUSED reference axis" in out and "not a strict 4h grid" in out, out.strip().splitlines()[-1][-200:])
    def _arm_frac(v, old):
        def f(a): r = a["d30_n2_c42_rec"].copy(); r[:, 0] += 0.25; return dict(a, d30_n2_c42_rec=r)
        _rewrite(f"{v}/*.npz", f)
    rc, out, j = judge_case(d, "r4_fractional_ts", mutate=_arm_frac)
    check("★★★ [r4] judge_fractional_timestamp_plus025: every arm's rec[:,0] + 0.25 s ⇒ rc 2 'not integer seconds' (round 3: astype(int64) truncated silently and passed)",
          rc == 2 and "JUDGE_REFUSED arm schema" in out and "not integer seconds" in out, out.strip().splitlines()[-1][-200:])
    def _arm_tiny(v, old):
        def f(a): r = a["d30_n2_c42_rec"].copy(); r[:, 0] += 1e-10; return dict(a, d30_n2_c42_rec=r)
        _rewrite(f"{v}/*.npz", f)
    rc, out, j = judge_case(d, "r4_tiny_float_ts", mutate=_arm_tiny)
    check("★★ [r4] float timestamps within 1e-9 of an integer are accepted (float64 storage is fine, fractions are not) ⇒ rc 0", rc == 0 and j and len(j["verdicts"]) == 18, (rc, out.strip().splitlines()[-1][-120:]))
    def _false_schema(v, old): _rewrite(f"{v}/*.npz", lambda a: dict(a, cols=np.array(["WRONG_COLUMN"] * 23), symbols=np.array(["WRONG_SYMBOL"])))
    rc, out, j = judge_case(d, "r4_false_schema_no_W", mutate=_false_schema)
    check("★★★ [r4] judge_false_schema_no_W: arms with cols=['WRONG_COLUMN']*23, symbols=['WRONG_SYMBOL'], no W ⇒ rc 2 'cols differ' (round 3: never looked at cols/symbols/W, passed and PROMOTEd)",
          rc == 2 and "JUDGE_REFUSED arm schema" in out and "cols differ from the frozen COLS" in out, out.strip().splitlines()[-1][-200:])
    _COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
    def _book_no_W(v, old): _rewrite(f"{v}/*.npz", lambda a: dict(a, cols=np.array(_COLS), symbols=np.array(["AAAUSDT", "BBBUSDT"])))
    rc, out, j = judge_case(d, "r4_book_without_W", mutate=_book_no_W)
    check("★★★ [r4] correct cols but a book (symbols present) WITHOUT d30_n2_c42_W ⇒ rc 2 'book without d30_n2_c42_W'", rc == 2 and "book without d30_n2_c42_W" in out, out.strip().splitlines()[-1][-160:])
    def _book_bad_W(v, old): _rewrite(f"{v}/*.npz", lambda a: dict(a, cols=np.array(_COLS), symbols=np.array(["AAAUSDT", "BBBUSDT"]), d30_n2_c42_W=np.zeros((len(a["d30_n2_c42_rec"]), 3), np.float32)))
    rc, out, j = judge_case(d, "r4_book_W_wrong_shape", mutate=_book_bad_W)
    check("★★ [r4] W with 3 columns for 2 symbols ⇒ rc 2 (W shape must be (n, n_symbols))", rc == 2 and "d30_n2_c42_W shape" in out, out.strip().splitlines()[-1][-160:])
    def _book_ok(v, old): _rewrite(f"{v}/*.npz", lambda a: dict(a, cols=np.array(_COLS), symbols=np.array(["AAAUSDT", "BBBUSDT"]), d30_n2_c42_W=np.zeros((len(a["d30_n2_c42_rec"]), 2), np.float32))); _rewrite(f"{old}/*.npz", lambda a: dict(a, cols=np.array(_COLS), symbols=np.array(["AAAUSDT", "BBBUSDT"]), d30_n2_c42_W=np.zeros((len(a["d30_n2_c42_rec"]), 2), np.float32)))
    rc, out, j = judge_case(d, "r4_book_full_schema", mutate=_book_ok)
    check("★★ [r4] GREEN: the full book schema (cols == COLS, symbols, W (n, n_symbols)) on arms AND references ⇒ rc 0, 18 verdicts", rc == 0 and j and len(j["verdicts"]) == 18, (rc, out.strip().splitlines()[-1][-120:]))
    judge_case(d, "r4_require_W_fixture")   # a plain bare-rec fixture; rerun the judge on it with JUDGE_REQUIRE_W=1
    rc, out = run(["judge_v4.py"], {"JUDGE_HC": f"{d}/r4_require_W_fixture/hc", "JUDGE_OUT": f"{d}/r4_require_W.json", "JUDGE_REQUIRE_W": "1"})
    check("★★ [r4] JUDGE_REQUIRE_W=1 on bare-rec fixtures (no W anywhere) ⇒ rc 2 (the real w10 artifacts carry W; the flag demands it)", rc == 2 and "book without d30_n2_c42_W" in out and "JUDGE_REQUIRE_W=1" in out, out.strip().splitlines()[-1][-160:])
    def _ref_nan(v, old):
        def f(a): r = a["d30_n2_c42_rec"].copy(); r[5, 18] = np.nan; return dict(a, d30_n2_c42_rec=r)
        _rewrite(f"{old}/*s42.npz", f)
    rc, out, j = judge_case(d, "r4_ref_nonfinite", mutate=_ref_nan)
    check("★★★ [r4] a NaN in the seed-42 RAW reference's frozen g ⇒ rc 3 'non-finite reference' BEFORE the reproduction", rc == 3 and "JUDGE_REFUSED non-finite reference" in out and "RAW_M1_s42" in out, out.strip().splitlines()[-1][-160:])
    def _ref_no_rec(v, old): _rewrite(f"{old}/*s2027.npz", lambda a: {"something_else": a["d30_n2_c42_rec"]})
    rc, out, j = judge_case(d, "r4_ref_schema", mutate=_ref_no_rec)
    check("★★ [r4] a RAW reference without d30_n2_c42_rec ⇒ rc 2 (reference schema, before the reproduction)", rc == 2 and "JUDGE_REFUSED reference axis/schema" in out and "no d30_n2_c42_rec" in out, out.strip().splitlines()[-1][-160:])
    rc, out, j = judge_case(d, "r4_partial_fractional", partial=True, mutate=_arm_frac)
    check("★★ [r4] JUDGE_ALLOW_PARTIAL=1 with fractional-timestamp arms ⇒ rc 0 exploratory, every arm listed under schema_bad, no verdict issued", rc == 0 and j and j["exploratory"] is True and len(j["schema_bad"]) == 28 and j["verdicts"] == {}, (rc, j and len(j["schema_bad"])))
    rc, out, j = judge_case(d, "r4_still_missing_ref", drop_raw27=True)
    check("★★ [r4] a MISSING seed-2027 reference still lands at the reproduction gate rc 3 'missing_reference' (unchanged round-3 behaviour; the new axis gate only judges files that exist)", rc == 3 and "missing_reference" in out and "A0p_dyn_s2027" in out, out.strip().splitlines()[-1][-160:])


# ── [N] round 5 (independent review cfaf1bbe §2–5): the standard is the frozen contract; receipts bind to the arm and its books; strict book contract ──
with tempfile.TemporaryDirectory() as d:
    print("\n[N] judge_v4 round 5: frozen ELIGIBILITY_CONTRACT.json decides; JUDGE_ELIGIBILITY only locates receipts; strict book contract")
    def _no_promote(j): return j and not any(v == "(A) PROMOTE" for v in j["verdicts"].values())
    def _n_promote(j): return sum(v == "(A) PROMOTE" for v in (j or {}).get("verdicts", {}).values())
    # a GENUINE G2_closure receipt, written by the archived closure gate on the [A] fixture, bound to A1e (researcher judge_actual_G2_not_export)
    os.makedirs(f"{d}/g2"); fx = fixture(f"{d}/g2")
    rc, out = run(["v4_gate_closure.py", f"{d}/g2/fA.npz", f"{d}/g2/fB.npz", f"{d}/g2/tA.npz", f"{d}/g2/tB.npz", f"{d}/g2/G2.json"], {"HOLE_CELLS": f"{d}/g2/holes.npz", "EXPECT_NCOLS": "89"}); assert rc == 0
    _g2in = {"fea_A": f"{d}/g2/fA.npz", "fea_B": f"{d}/g2/fB.npz", "targets_A": f"{d}/g2/tA.npz", "targets_B": f"{d}/g2/tB.npz", "hole_cells": f"{d}/g2/holes.npz"}
    rc, out, j = judge_case(d, "r5_actual_G2_not_export", promote=True, eligibility=lambda q: {"A1e": {"receipt": f"{d}/g2/G2.json", "inputs": _g2in}})
    check("★★★ [r5] judge_actual_G2_not_export: a REAL G2_closure PASS (right gate source, all 5 inputs fresh) located for A1e ⇒ NOT eligible ('receipt is from gate G2_closure; the frozen contract requires BUNDLE_export'), 0 PROMOTE (round 4: 4 PROMOTE)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "requires 'BUNDLE_export'" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r5_actual_G2_caller_says_G2", promote=True, eligibility=lambda q: {"A1e": {"receipt": f"{d}/g2/G2.json", "gate": "G2_closure", "self_sha": _sha(f"{HERE}/v4_gate_closure.py"), "inputs": _g2in}})
    check("★★★ [r5] the same G2 receipt with the caller ALSO naming gate=G2_closure + its true sha (a self-consistent but wrong standard) ⇒ 'caller-supplied standard conflicts with the frozen contract', 0 PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "conflicts with the frozen contract" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _step1_entry(q):
        s1 = {"gate": "STEP1", "PASS": True, "arm": "A1e", "self_sha256": _sha(f"{HERE}/v4_gate_step1.py"), "inputs_sha256": {k: _sha(f"{d}/g2/holes.npz") for k in ("dlw_v4raw_targets", "fea82_v4raw")}}
        json.dump(s1, open(f"{q}/s1.json", "w")); return {"A1e": {"receipt": f"{q}/s1.json", "profile": "v4s", "inputs": {k: f"{d}/g2/holes.npz" for k in ("dlw_v4raw_targets", "fea82_v4raw")}}}
    rc, out, j = judge_case(d, "r5_actual_STEP1_downgraded_profile", promote=True, eligibility=_step1_entry)
    check("★★★ [r5] judge_actual_STEP1_downgraded_profile: a STEP1 PASS under a caller-chosen profile=v4s located for A1e ⇒ not eligible (conflict: the contract's profile is None / gate STEP1 ≠ BUNDLE_export), 0 PROMOTE (round 4: 4 PROMOTE)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _unknown_gate(q):
        u = {"gate": "UNREGISTERED_quality", "PASS": True, "arm": "A1e", "self_sha256": _sha(f"{HERE}/v4_gate_closure.py"), "inputs_sha256": {"fea_A": _sha(f"{d}/g2/fA.npz")}}
        json.dump(u, open(f"{q}/u.json", "w")); return {"A1e": {"receipt": f"{q}/u.json", "inputs": {"fea_A": f"{d}/g2/fA.npz"}}}
    rc, out, j = judge_case(d, "r5_actual_unknown_gate_one_input", promote=True, eligibility=_unknown_gate)
    check("★★★ [r5] judge_actual_unknown_gate_one_input: a PASS from an unregistered gate name with one input ⇒ not eligible (gate ≠ BUNDLE_export), 0 PROMOTE (round 4: 4 PROMOTE)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "requires 'BUNDLE_export'" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    # ── binding to the arm and to its books (researcher receipt_A1e_relabel_to_A1 / book_replaced_after_receipt) ──
    rc, out, j = judge_case(d, "r5_relabel_A1e_to_A1", promote=True, promote_arm="A1", eligibility=lambda q: {"A1": bound_entry(q, "A1e")})
    check("★★★ [r5] receipt_A1e_relabel_to_A1: A1e's receipt (arm=A1e, A1e's books) located under map key A1 with A1 +1 bps ⇒ A1 not eligible ('bound to arm A1e'), 0 PROMOTE (round 4: 6 PROMOTE)",
          rc == 0 and j and j["eligibility_by_arm"]["A1"]["ok"] is False and "bound to arm 'A1e'" in j["eligibility_by_arm"]["A1"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1"]["why"]))
    def _relabel_arm_field(q):   # the receipt's arm field is forged to A1 but the books hashed are A1e's
        return {"A1": bound_entry(q, "A1", books_of="A1e")}
    rc, out, j = judge_case(d, "r5_relabel_books_of_other_arm", promote=True, promote_arm="A1", eligibility=_relabel_arm_field)
    check("★★★ [r5] a receipt whose arm field says A1 but whose hashed books are A1e's ⇒ A1 not eligible ('book_dyn_s42 changed since the receipt'), 0 PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1"]["ok"] is False and "book_" in j["eligibility_by_arm"]["A1"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1"]["why"]))
    def _replace_book(v, old):
        for p in sorted(glob.glob(f"{v}/*_A1e_*.npz")):
            z = np.load(p); r = z["d30_n2_c42_rec"].copy(); r[:, 18] = 3.0; r[:, 19] = 3.0; np.savez(p, d30_n2_c42_rec=r)
    import glob
    rc, out, j = judge_case(d, "r5_book_replaced_after_receipt", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")}, post_mutate=_replace_book)
    check("★★★ [r5] book_replaced_after_receipt: A1e's economics rewritten AFTER the receipt sealed its book shas ⇒ not eligible ('book_… changed since the receipt'), 0 PROMOTE (round 4: 4 PROMOTE)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "changed since the receipt" in j["eligibility_by_arm"]["A1e"]["why"] and "book_" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r5_receipt_without_books", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e", bind_books=False)})
    check("★★★ [r5] a BUNDLE_export receipt that never hashed the judged books ⇒ not eligible ('no sha for input book_dyn_s42'), 0 PROMOTE (the seven export inputs alone do not connect the receipt to the judged artefact)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "book_dyn_s42" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r5_unregistered_arm", promote=True, eligibility=lambda q: {"A9": bound_entry(q, "A9", books_of="A1e")})
    check("★★ [r5] an arm not registered in the contract (A9) ⇒ not eligible ('not registered as a candidate'), no PROMOTE", rc == 0 and j and j["eligibility_by_arm"]["A9"]["ok"] is False and "not registered as a candidate" in j["eligibility_by_arm"]["A9"]["why"] and _no_promote(j), (rc, j and j["eligibility_by_arm"]["A9"]["why"]))
    # ── the standard is not the caller's: the shipped contract approves NO export gate; a device without a contract cannot promote ──
    rc, out, j = judge_case(d, "r5_shipped_contract_empty_approved", promote=True, eligibility=lambda q: {"A1e": {k: v for k, v in bound_entry(q, "A1e").items() if k in ("receipt", "inputs")}}, contract="archive")
    check("★★★ [r5→r6] the ARCHIVED judge + its shipped contract (APPLIED 2026-09-12: BUNDLE_export approves ONLY v4e_gate_export_v2.py): a fully bound (28-name closure), book-bound A1e receipt signed by the archived EXPORTER (pod_export_bundle_v4.py) ⇒ STILL not eligible ('not an approved source'), 0 PROMOTE — the exporter is not the gate; only a receipt written by the reviewed v2 gate can confer candidacy",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "not an approved source" in j["eligibility_by_arm"]["A1e"]["why"]
          and j["contract"]["approved_sources"]["BUNDLE_export"] == [_sha(f"{HERE}/v4e_gate_export_v2.py")] and _n_promote(j) == 0,
          (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r5_device_without_contract", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")}, contract="none")
    check("★★ [r5] a device copy with NO contract beside the judge ⇒ informational, contract.error set, a warning printed, 0 PROMOTE", rc == 0 and j and j["contract"]["error"] and j["eligibility"] == "informational" and "frozen eligibility contract unavailable" in out and _n_promote(j) == 0, (rc, j and j["contract"]["error"]))
    _ct_bad = test_contract(); _ct_bad["contract_schema"] = "something/else"
    rc, out, j = judge_case(d, "r5_malformed_contract", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")}, contract=_ct_bad)
    check("★ [r5] a malformed contract (wrong schema tag) ⇒ treated as unavailable: informational, 0 PROMOTE", rc == 0 and j and j["contract"]["error"] and _n_promote(j) == 0, (rc, j and j["contract"]["error"]))
    rc, out, j = judge_case(d, "r5_contract_sha_recorded", promote=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")})
    check("★★★ [r5→r6] GREEN positive control under the TEST contract (device copy approving the archived exporter): A1e eligible, exactly 4 PROMOTE, the output records the contract's sha and approved sources so a reviewer can see WHICH standard judged, and the judge bound the four judged books into the 28-name input set it verified (round 6 floor)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is True and _n_promote(j) == 4 and j["contract"]["sha256"] == _sha(f"{d}/r5_contract_sha_recorded/device/ELIGIBILITY_CONTRACT.json")
          and j["contract"]["approved_sources"]["BUNDLE_export"] == [_sha(f"{HERE}/pod_export_bundle_v4.py")]
          and {"book_dyn_s2027", "book_dyn_s42", "book_fix_s2027", "book_fix_s42"} <= set(j["eligibility_by_arm"]["A1e"]["inputs"]) and len(j["eligibility_by_arm"]["A1e"]["inputs"]) == 28
          and "registered floor BUNDLE_export=28" in j["eligibility_by_arm"]["A1e"]["why"] and "28 inputs verified" in j["eligibility_by_arm"]["A1e"]["why"],
          (rc, j and j["eligibility_by_arm"]["A1e"], j and j["contract"]["sha256"]))
    check("★ [r5] the caller's entry needs only {receipt, inputs}: caller_supplied is empty when it names no standard", j and j["eligibility_by_arm"]["A1e"].get("caller_supplied") in ({"gate": "BUNDLE_export", "self_sha": _sha(f"{HERE}/pod_export_bundle_v4.py")}, {}), j and j["eligibility_by_arm"]["A1e"].get("caller_supplied"))
    # ── strict book contract (researcher negative_gross / infinite_gross / nonfinite_W / symbols_order_reversed / no_cols_strict / no_symbols_strict / rec_only_default / valid_strict_schema_positive) ──
    _COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
    def _bookify(v, old, gross=None, W_nan=False, reverse_arm=None, drop=()):
        for p in sorted(glob.glob(f"{v}/*.npz") + glob.glob(f"{old}/*.npz")):
            z = np.load(p); r = z["d30_n2_c42_rec"].copy(); n = len(r)
            if gross is not None: r[:, 5] = gross; r[:, 18] = r[:, 18] * (gross if np.isfinite(gross) else 1.0); r[:, 19] = r[:, 18]   # keep g when finite (the researcher's −1 case kept g)
            sym = np.array(["SYNTH_A", "SYNTH_B"]); W = np.tile([0.5, -0.5], (n, 1)).astype(np.float32)
            if reverse_arm and f"_{reverse_arm}_" in os.path.basename(p): sym = sym[::-1]
            if W_nan: W[0, 0] = np.nan
            arrays = {"d30_n2_c42_rec": r, "cols": np.array(_COLS), "symbols": sym, "d30_n2_c42_W": W}
            for k in drop: arrays.pop(k)
            np.savez(p, **arrays)
    rc, out, j = judge_case(d, "r5_strict_positive", promote=True, strict=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")}, mutate=lambda v, o: _bookify(v, o))
    check("★★★ [r5] valid_strict_schema_positive: full book schema (cols, symbols, finite W, gross 1) under JUDGE_REQUIRE_W=1 + the test contract ⇒ rc 0, A1e eligible, exactly 4 PROMOTE", rc == 0 and j and _n_promote(j) == 4, (rc, out.strip().splitlines()[-1][-160:]))
    rc, out, j = judge_case(d, "r5_negative_gross", promote=True, strict=True, eligibility=lambda q: {"A1e": bound_entry(q, "A1e")}, mutate=lambda v, o: _bookify(v, o, gross=-1.0))
    check("★★★ [r5] negative_gross: gross_total = −1 with the numerators flipped (g unchanged) ⇒ rc 2 'gross_total on the frozen window must be finite and > 0' (round 4: rc 0, 4 PROMOTE)", rc == 2 and "finite and > 0" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_infinite_gross", strict=True, mutate=lambda v, o: _bookify(v, o, gross=np.inf))
    check("★★★ [r5] infinite_gross: gross_total = +inf ⇒ rc 2 (round 4: accepted, g = 0)", rc == 2 and "finite and > 0" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_negative_gross_default_mode", mutate=lambda v, o: _bookify(v, o, gross=-1.0, drop=("cols", "symbols", "d30_n2_c42_W")))
    check("★★★ [r5] the gross check holds in DEFAULT (rec-only) mode too: gross −1 on bare rec ⇒ rc 2", rc == 2 and "finite and > 0" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_nonfinite_W", strict=True, mutate=lambda v, o: _bookify(v, o, W_nan=True))
    check("★★★ [r5] nonfinite_W: a NaN in W ⇒ rc 2 'non-finite entries in d30_n2_c42_W' (round 4: rc 0, 4 PROMOTE)", rc == 2 and "non-finite entries in d30_n2_c42_W" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_symbols_reversed", strict=True, mutate=lambda v, o: _bookify(v, o, reverse_arm="A1e"))
    check("★★★ [r5] symbols_order_reversed: one arm's symbols axis reversed while W is not ⇒ rc 2 'symbols axis differs' (round 4: rc 0, 4 PROMOTE)", rc == 2 and "JUDGE_REFUSED symbols axis" in out and "A1e" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_no_cols_strict", strict=True, mutate=lambda v, o: _bookify(v, o, drop=("cols",)))
    check("★★★ [r5] no_cols_strict: strict mode without cols ⇒ rc 2 'strict book contract: cols missing' (round 4: rc 0, 4 PROMOTE)", rc == 2 and "cols missing" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_no_symbols_strict", strict=True, mutate=lambda v, o: _bookify(v, o, drop=("symbols",)))
    check("★★★ [r5] no_symbols_strict: strict mode without symbols ⇒ rc 2 'symbols missing' (round 4: rc 0, 4 PROMOTE)", rc == 2 and "symbols missing" in out, out.strip().splitlines()[-1][-200:])
    rc, out, j = judge_case(d, "r5_rec_only_default", mutate=lambda v, o: _bookify(v, o, drop=("cols", "symbols", "d30_n2_c42_W")))
    check("★★ [r5] rec_only_default: bare rec in DEFAULT mode is the documented narrow contract ⇒ rc 0, 18 verdicts (gross > 0 still enforced)", rc == 0 and j and len(j["verdicts"]) == 18, (rc, out.strip().splitlines()[-1][-120:]))
    rc, out = run(["judge_v4.py"], {"JUDGE_HC": f"{d}/r5_rec_only_default/hc", "JUDGE_OUT": f"{d}/r5_alias.json", "JUDGE_STRICT_BOOK": "1"})
    check("★ [r5] JUDGE_STRICT_BOOK=1 is an alias of JUDGE_REQUIRE_W=1 (bare rec ⇒ rc 2)", rc == 2, out.strip().splitlines()[-1][-120:])


# ── [O] ROUND 6 (r20 gate closure; DESIGN_judge_floor_28_2026-09-12): the BUNDLE_export floor is the v2 export gate's FULL 28-name closure ─────
# The independent reviewer showed the judge's require stayed PASS after the SHIPPED prediction file was mutated: the bundle was not among the 11 names.
# Here: (i) the floor equals, name for name, what the REAL v2 receipt for A1 registered (a real receipt satisfies the judge); (ii) omitting any single
# name is refused, at the require level (all 28) and at the judge level (the 17 new ones); (iii) the archived exporter is still not an approved source.
with tempfile.TemporaryDirectory() as d:
    print("\n[O] round 6: REQUIRED_INPUTS[BUNDLE_export] = the v2 export gate's 28-name closure; the judge refuses an entry that leaves any of them undeclared")
    import importlib; sys.path.insert(0, HERE); _gc = importlib.import_module("v4_gate_common")
    _FLOOR = list(_gc.REQUIRED_INPUTS["BUNDLE_export"]); _BOOKS = list(_gc.BOOK_INPUTS); _NEW17 = _FLOOR[11:]
    _real_p = f"{HERE}/receipts/judge_floor_2026-09-12/BUNDLE_export_v2_A1_applied.json"; _real = json.load(open(_real_p))
    check("★★★ [r6] (i) REAL SHAPE, static: the floor has 28 distinct names, the judged books at [7:11], and equals EXACTLY the registered_inputs of the real v2 receipt for A1 (pod2 2026-09-12T09:23:10Z, self d63f4ec3…, PASS, no failed check) — no name invented, none missing",
          len(_FLOOR) == 28 and len(set(_FLOOR)) == 28 and _FLOOR[7:11] == _BOOKS and set(_FLOOR) == set(_real["registered_inputs"]) and set(_real["inputs_sha256"]) == set(_FLOOR)
          and _real["gate"] == "BUNDLE_export" and _real["PASS"] is True and _real["arm"] == "A1" and _real["self_sha256"] == _sha(f"{HERE}/v4e_gate_export_v2.py") and _real["failed_checks"] == [],
          (len(_FLOOR), sorted(set(_FLOOR) ^ set(_real["registered_inputs"]))))
    check("★★ [r6] the real receipt recorded the OLD 11-name floor it was judged against (registered_floor_v4_gate_common) — the gap this round closes; femat/signal_receipt are absent from it (E7 not applicable for A1), so they are rightly NOT in the static floor",
          _real["registered_floor_v4_gate_common"] == _FLOOR[:11] and _real["checks"]["E7_signal_receipt"]["applicable"] is False and "femat" not in _FLOOR and "signal_receipt" not in _FLOOR, _real.get("registered_floor_v4_gate_common"))
    check("★★ [r6] the fixture declares exactly the 24 non-book names (the judge adds the 4 books): ELIG_INPUTS ∪ BOOK_INPUTS == the floor", set(ELIG_INPUTS) | set(_BOOKS) == set(_FLOOR) and len(ELIG_INPUTS) == 24 and not (set(ELIG_INPUTS) & set(_BOOKS)), sorted(set(ELIG_INPUTS) ^ (set(_FLOOR) - set(_BOOKS))))
    check("★ [r6] the other gates' floors are untouched by round 6 (G2 5, STEP1 2, STEP1@v4s 2, STEP1@v4 4, STEP2 2; no BUNDLE_export@profile)",
          {k: len(v) for k, v in _gc.REQUIRED_INPUTS.items()} == {"G2_closure": 5, "STEP1": 2, "STEP1@v4s": 2, "STEP1@v4": 4, "STEP2": 2, "BUNDLE_export": 28}, {k: len(v) for k, v in _gc.REQUIRED_INPUTS.items()})
    # unit level, through the ARCHIVED module + SHIPPED contract: a receipt signed by the approved v2 gate over the full 28 ⇒ ok; any single omission ⇒ refused
    q = f"{d}/unit"; os.makedirs(f"{q}/hc/dev_v4/probe_artifacts")
    for arm in ("A0", "A1e"):
        for seat in ("dyn", "fix"):
            for seed in (42, 2027): np.savez(f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{seed}.npz", d30_n2_c42_rec=np.zeros((3, 23)))
    _V2 = _sha(f"{HERE}/v4e_gate_export_v2.py")
    e = bound_entry(q, "A1e", src=f"{HERE}/v4e_gate_export_v2.py")
    full = dict(e["inputs"]); full.update({f"book_{seat}_s{seed}": f"{q}/hc/dev_v4/probe_artifacts/w10_ablation_series_V4_A1e_{seat}_s{seed}.npz" for seat in ("dyn", "fix") for seed in (42, 2027)})
    ok, why = _gc.require(e["receipt"], full, expected_gate="BUNDLE_export", expected_self_sha=_V2)
    check("★★★ [r6] (i) unit: a v2-signed receipt over the full 28 names, required through the archived module + shipped contract ⇒ ok, '28 inputs verified, registered floor BUNDLE_export=28'", ok is True and "28 inputs verified" in why and "registered floor BUNDLE_export=28" in why, why)
    _omit_bad = {}
    for k in _FLOOR:
        ok_k, why_k = _gc.require(e["receipt"], {kk: vv for kk, vv in full.items() if kk != k}, expected_gate="BUNDLE_export", expected_self_sha=_V2)
        if ok_k or f"omitted registered input(s) ['{k}']" not in why_k: _omit_bad[k] = (ok_k, why_k)
    check("★★★ [r6] (ii) unit: omitting ANY single one of the 28 (each of the 28 tried in turn) ⇒ refused, naming exactly that input", not _omit_bad, _omit_bad)
    ok, why = _gc.require(e["receipt"], full, expected_gate="BUNDLE_export", expected_self_sha=_sha(f"{HERE}/pod_export_bundle_v4.py"))
    check("★★★ [r6] (iii) unit: the v2-signed receipt pinned to the archived EXPORTER's sha ⇒ refused at the identity check ('caller trusts') before approval is even consulted", ok is False and "caller trusts" in why, why)
    e_x = bound_entry(q, "A1e")   # the SAME 28-name closure (identical synthetic files), but SIGNED by the archived exporter (pod_export_bundle_v4.py) and pinned to it
    full_x = dict(e_x["inputs"]); full_x.update({k: v for k, v in full.items() if k.startswith("book_")})
    ok, why = _gc.require(e_x["receipt"], full_x, expected_gate="BUNDLE_export", expected_self_sha=_sha(f"{HERE}/pod_export_bundle_v4.py"))
    check("★★★ [r6] (iii) unit: a receipt over the same 28 names signed by the archived exporter and pinned to its own sha ⇒ 'not an APPROVED source' under the shipped contract (a wider floor does not widen approval)", ok is False and "not an APPROVED source" in why, why)
    # judge level, on synthetic arms with A1e +1 bps (so that a PROMOTE would be visible), the ARCHIVED judge and the SHIPPED contract
    def _n_promote(j): return sum(v == "(A) PROMOTE" for v in (j or {}).get("verdicts", {}).values())
    def _v2_entry(q, drop=None, extra=None):
        e = bound_entry(q, "A1e", src=f"{HERE}/v4e_gate_export_v2.py", extra_inputs=extra); return {"A1e": {"receipt": e["receipt"], "inputs": {k: v for k, v in e["inputs"].items() if k != drop}}}
    rc, out, j = judge_case(d, "r6_real_shape_archive", promote=True, contract="archive", eligibility=lambda q: _v2_entry(q))
    check("★★★ [r6] (i) judge: the ARCHIVED judge + SHIPPED contract, an entry {receipt, inputs} whose receipt is signed by the v2 gate over the real-shape 28 closure ⇒ A1e ELIGIBLE, 'registered floor BUNDLE_export=28', 28 inputs verified, exactly 4 PROMOTE (the positive control on the real standard)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is True and "registered floor BUNDLE_export=28" in j["eligibility_by_arm"]["A1e"]["why"] and "28 inputs verified" in j["eligibility_by_arm"]["A1e"]["why"]
          and len(j["eligibility_by_arm"]["A1e"]["inputs"]) == 28 and j["contract"]["sha256"] == _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json") and _n_promote(j) == 4, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    for k in _NEW17:
        rc, out, j = judge_case(d, "r6_omit_" + k.replace("/", "__"), promote=True, contract="archive", eligibility=lambda q, k=k: _v2_entry(q, drop=k))
        if k == "eligibility_contract":   # ROUND 7 ([Q]): this name is JUDGE-bound like the four books — the caller's omission is supplied by the judge from its own contract path; the receipt must still have hashed that exact file
            check("★★ [r6→r7] (ii) judge: the entry with 'eligibility_contract' left undeclared ⇒ A1e STILL eligible — round 7 binds that name to the judge's own contract (the receipt hashed it), 28 inputs verified, 4 PROMOTE (was: refused as a caller omission in round 6; a caller-chosen path is what [Q] closes)",
                  rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is True and "28 inputs verified" in j["eligibility_by_arm"]["A1e"]["why"] and "eligibility_contract" in j["eligibility_by_arm"]["A1e"]["inputs"] and _n_promote(j) == 4, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
            continue
        check(f"★★★ [r6] (ii) judge: the same entry with {k!r} left undeclared ⇒ A1e NOT eligible ('omitted registered input(s) [{k!r}]'), 0 PROMOTE (the 11-name floor let this through)",
              rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and f"omitted registered input(s) ['{k}']" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _stale_bundle(q):
        m = _v2_entry(q); open(m["A1e"]["inputs"]["bundle/slow_pred_pinned.npy"], "wb").write(b"predictions rewritten AFTER the export receipt"); return m
    rc, out, j = judge_case(d, "r6_shipped_pred_mutated", promote=True, contract="archive", eligibility=_stale_bundle)
    check("★★★ [r6] the reviewer's original probe, now at the JUDGE: the shipped slow_pred_pinned.npy mutated after the receipt ⇒ A1e not eligible ('bundle/slow_pred_pinned.npy' changed since the receipt), 0 PROMOTE (with 11 names the judge could not see the bundle)",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "'bundle/slow_pred_pinned.npy' changed since the receipt" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    rc, out, j = judge_case(d, "r6_exporter_signed_28_archive", promote=True, contract="archive", eligibility=lambda q: {"A1e": {k: v for k, v in bound_entry(q, "A1e").items() if k in ("receipt", "inputs")}})
    check("★★★ [r6] (iii) judge: a receipt over the SAME 28 names but signed by the archived exporter (pod_export_bundle_v4.py) under the shipped contract ⇒ still 'not an approved source', 0 PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is False and "not an approved source" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 0, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))
    def _femat_arm(q):
        open(f"{q}/femat.npz", "wb").write(b"femat"); open(f"{q}/sig.json", "w").write("{}"); return _v2_entry(q, extra={"femat": f"{q}/femat.npz", "signal_receipt": f"{q}/sig.json"})
    rc, out, j = judge_case(d, "r6_femat_extras", promote=True, contract="archive", eligibility=_femat_arm)
    check("★★ [r6] a FEMAT-arm shape (femat + signal_receipt recorded by the gate AND declared, on top of the 28) is verified as extras, not refused: eligible, 30 inputs verified, 4 PROMOTE",
          rc == 0 and j and j["eligibility_by_arm"]["A1e"]["ok"] is True and len(j["eligibility_by_arm"]["A1e"]["inputs"]) == 30 and "30 inputs verified" in j["eligibility_by_arm"]["A1e"]["why"] and _n_promote(j) == 4, (rc, j and j["eligibility_by_arm"]["A1e"]["why"]))


# ── [Q] ROUND 7 (2026-09-12; DESIGN_judge_floor_28_2026-09-12 §7 F9; user word 09-12「修复所有漏洞」): the judge binds the STANDARD it enforces ───────────
# Round 6 put `eligibility_contract` in the 28-name floor but let the CALLER say which file that name points at: require then verified only "the file at the
# caller's path is unchanged since the receipt", never "the receipt was written under the contract THIS judge reads". Here: (i) a receipt whose gate hashed a
# DIFFERENT contract (one key added, same approvals) is refused at the judge, naming eligibility_contract, and the caller's path is recorded; (ii) a byte-identical
# copy at another path is still accepted (the sha binds, not the path); (iii) the same probe under the SHIPPED contract (archive mode, v2-signed) is refused;
# (iv) the archived round-6 judge (judge_v4.r4_7f1aa5d6.py) ACCEPTS case (i) — the old code is red under this suite's standard; (v) static guards.
with tempfile.TemporaryDirectory() as d:
    print("\n[Q] round 7: the judge, not the caller, binds eligibility_contract to the contract it reads")
    import shutil as _sh
    def _n_promote(j): return sum(v == "(A) PROMOTE" for v in (j or {}).get("verdicts", {}).values())
    def _other(q, base, identical=False):
        p = f"{q}/other_contract.json"
        if identical: _sh.copyfile(base, p)
        else: c = json.load(open(base)); c["_round7_probe"] = "one key added: a different contract carrying the same approvals"; json.dump(c, open(p, "w"))
        return p
    def _entry_other(q, identical=False, src=None):
        base = f"{q}/device/ELIGIBILITY_CONTRACT.json" if os.path.exists(f"{q}/device/ELIGIBILITY_CONTRACT.json") else f"{HERE}/ELIGIBILITY_CONTRACT.json"
        e = bound_entry(q, "A1e", src=src, extra_inputs={"eligibility_contract": _other(q, base, identical)}); return {"A1e": {"receipt": e["receipt"], "inputs": e["inputs"]}}
    rc, out, j = judge_case(d, "r7_receipt_under_other_contract", promote=True, eligibility=lambda q: _entry_other(q))
    _r = j and j["eligibility_by_arm"]["A1e"]
    check("★★★ [r7] (i) a receipt whose gate hashed a DIFFERENT contract (one key added) and an entry pointing eligibility_contract at that file ⇒ A1e NOT eligible ('eligibility_contract' changed since the receipt: the judge rebinds the name to ITS contract), caller path recorded, 0 PROMOTE",
          rc == 0 and _r and _r["ok"] is False and "'eligibility_contract' changed since the receipt" in _r["why"] and _r.get("caller_contract_path", "").endswith("/other_contract.json") and _n_promote(j) == 0, (rc, _r and _r["why"], _r and _r.get("caller_contract_path")))
    rc, out, j = judge_case(d, "r7_identical_copy_elsewhere", promote=True, eligibility=lambda q: _entry_other(q, identical=True))
    _r = j and j["eligibility_by_arm"]["A1e"]
    check("★★ [r7] (ii) the same entry but the other file is a BYTE-IDENTICAL copy of the judge's contract ⇒ still eligible (the sha binds, not the path), 28 inputs verified, caller path recorded, 4 PROMOTE",
          rc == 0 and _r and _r["ok"] is True and "28 inputs verified" in _r["why"] and _r.get("caller_contract_path", "").endswith("/other_contract.json") and _n_promote(j) == 4, (rc, _r and _r["why"]))
    rc, out, j = judge_case(d, "r7_other_contract_archive", promote=True, contract="archive", eligibility=lambda q: _entry_other(q, src=f"{HERE}/v4e_gate_export_v2.py"))
    _r = j and j["eligibility_by_arm"]["A1e"]
    check("★★★ [r7] (iii) under the SHIPPED contract + archived judge, a v2-signed receipt over the full 28 names whose eligibility_contract sha is another contract's ⇒ NOT eligible, judge contract sha = shipped 1188267a…, 0 PROMOTE",
          rc == 0 and _r and _r["ok"] is False and "'eligibility_contract' changed since the receipt" in _r["why"] and j["contract"]["sha256"] == _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json") and _n_promote(j) == 0, (rc, _r and _r["why"]))
    rc, out, j = judge_case(d, "r7_old_judge_accepts_other_contract", promote=True, judge_src="judge_v4.r4_7f1aa5d6.py", eligibility=lambda q: _entry_other(q))
    _r = j and j["eligibility_by_arm"]["A1e"]
    check("★★★ [r7] (iv) OLD CODE IS RED: the archived round-6 judge (judge_v4.r4_7f1aa5d6.py) run in the device on case (i) ⇒ A1e ELIGIBLE and 4 PROMOTE — it verified the caller's file, not its own contract (the defect this round closes)",
          rc == 0 and _r and _r["ok"] is True and _n_promote(j) == 4 and "caller_contract_path" not in _r, (rc, _r and _r["why"]))
    _js = open(f"{HERE}/judge_v4.py").read()
    check("★★ [r7] (v) static: the live judge carries the binding line and the archived round-6 judge is the sha it is named by (7f1aa5d6…) and does NOT carry it",
          'inputs["eligibility_contract"] = _CONTRACT_PATH' in _js and _sha(f"{HERE}/judge_v4.r4_7f1aa5d6.py").startswith("7f1aa5d6") and 'inputs["eligibility_contract"] = _CONTRACT_PATH' not in open(f"{HERE}/judge_v4.r4_7f1aa5d6.py").read(),
          _sha(f"{HERE}/judge_v4.r4_7f1aa5d6.py")[:12])
    check("★ [r7] (v) static: the contract's own text still describes the judge as the one that reads it from its directory (no env can substitute) — the binding line implements that sentence",
          "reads THIS file from its own directory" in open(f"{HERE}/ELIGIBILITY_CONTRACT.json").read(), None)


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

# ── [P] MONTHLY CHAIN (2026-09-12; RUNBOOK_2026-10 §0★ 修订 2 (a)(b)(c), independent review 0dfc0d87 R1–R5): the month set is derived/declared, refit and
#        exporter refuse without env, the month env is a contract, the driver stops at preflight against an empty root (negative control) ──────────
print("\n[P] monthly chain: month set, refusals without env, month env contract, preflight approval, dryrun negative control")
import calendar as _cal
import glob as _glob
import v4_months as _VM
_t0 = _cal.timegm((2025, 1, 1, 0, 0, 0)); _sep = list(range(_t0, _cal.timegm((2026, 9, 1, 0, 0, 0)), 14400))
_der = _VM.months_all_from_axis(_sep)
check("★★★ [P] month set DERIVED from a 2025-01-01..2026-08-31 20Z axis == the September constant 202501..202608 (bit-identity of the month set)", _der == _VM.LEGACY_MONTHS_ALL_2026_09 and len(_der) == 20, (_der[0], _der[-1], len(_der)))
check("★★★ [P] round-robin shards of that set == the four hand-written SH0..SH3 lists of chain_v4_gpu3.sh (bit-identity of the dispatch)", _VM.shards(_der) == _VM.LEGACY_SHARDS_2026_09, _VM.shards(_der))
_src3 = open(f"{HERE}/chain_v4_gpu3.sh").read()
check("★★ [P] the legacy lists the test compares against ARE the strings in the archived chain_v4_gpu3.sh (the test is not self-referential)", all(f"SH{k}={s}" in _src3 for k, s in enumerate(_VM.LEGACY_SHARDS_2026_09)))
_oct = list(range(_t0, _cal.timegm((2026, 10, 5, 0, 0, 0)), 14400))
check("★★ [P] an axis extended into an INCOMPLETE October ⇒ derived set ends 202609 (September complete, October excluded)", _VM.months_all_from_axis(_oct)[-1] == 202609 and len(_VM.months_all_from_axis(_oct)) == 21)
check("★★ [P] an axis ending 2026-09-30 20Z (September complete) ⇒ ends 202609", _VM.months_all_from_axis(list(range(_t0, _cal.timegm((2026, 10, 1, 0, 0, 0)), 14400)))[-1] == 202609)
def _raises(fn, *a):
    try:
        fn(*a); return None
    except ValueError as e:
        return str(e)
_e = _raises(_VM.months_all, "202501,202609", _sep)
check("★★★ [P] MUTATION: declared MONTHS_ALL with 202609 on the September axis ⇒ refused (the data cannot label it) and the message names the month", _e is not None and "202609" in _e, _e)
check("★★★ [P] MONTHS ⊄ MONTHS_ALL ⇒ refused", _raises(_VM.check_subset, [202609], _der) is not None)
check("★★ [P] parse_months refuses '2025-03', duplicates and descending lists; tolerates spaces", all(_raises(_VM.parse_months, s) for s in ("202501,2025-03", "202501,202501", "202502,202501")) and _VM.parse_months("202501, 202502") == [202501, 202502])
check("★★ [P] a missing interior anchor ⇒ that month is not complete ⇒ refused (no silent hole)", _raises(_VM.months_all_from_axis, np.delete(np.array(_sep), 100)) is not None)
rc, out = run(["v4_months.py", "shards", ",".join(str(m) for m in _der)])
check("★★ [P] CLI `v4_months.py shards` prints exactly SH0..SH3 of the September chain", rc == 0 and out.strip().splitlines() == [f"SH{k}={s}" for k, s in enumerate(_VM.LEGACY_SHARDS_2026_09)], out[-200:])
rc, out = run(["v4_months.py", "shards", "202501,2025-03"])
check("★ [P] CLI refuses a malformed list with rc 3", rc == 3 and "MONTHS_SHARDS_FAIL" in out)
for _f in ("pod_f10_train_monthly_v4.py", "merge_mwf_v4b.py"):
    _s = open(f"{HERE}/{_f}").read()
    check(f"★★★ [P] {_f}: no hand-written 202501..202608 constant; imports v4_months.months_all", "202501 + k for k in range(12)" not in _s and "from v4_months import months_all" in _s)
_tr = open(f"{HERE}/pod_f10_train_monthly_v4.py").read()
check("★★ [P] trainer env whitelist takes the admissible dirs from V4_DLW_RAW/V4_DLW_CLIP/V4_F8 with the September constants as defaults (bare call unchanged)",
      "DLW in (_V4_DLW_RAW, _V4_DLW_CLIP) and OUT == _V4_F8" in _tr and 'os.environ.get("V4_DLW_RAW", "/workspace/dlw_v4raw")' in _tr and 'os.environ.get("V4_F8", "/workspace/f8_v4")' in _tr and "_check_subset(MONTHS, ALL_MONTHS)" in _tr)
_la = open(f"{HERE}/launch_mwf_v4b.sh").read()
check("★★ [P] launcher: DLW/F8/device dir from the month env with September defaults; MONTHS_ALL forwarded to the trainer", "${V4_DLW_RAW:-/workspace/dlw_v4raw}" in _la and "${V4_DLW_CLIP:-/workspace/dlw_hf3}" in _la and "F8=${V4_F8:-/workspace/f8_v4}" in _la and "${MONTHS_ALL:+MONTHS_ALL=$MONTHS_ALL}" in _la)
_mg = open(f"{HERE}/merge_mwf_v4b.py").read()
check("★★ [P] merge: mwf root / gate json / trainer / splice sources / dev preds from V4_* env with September defaults; the HF2 comparison is skipped (never asserted) when the reference cannot align", 'os.environ.get("V4_F8", "/workspace/f8_v4")' in _mg and "hf_skip" in _mg and "assert HF.shape == PRED.shape" not in _mg)
# refit: refuses without env, BEFORE importing torch (R1)
_env_clear = {k: "" for k in ("F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX")}   # empty = "not set" for the refit's guard; run_sandboxed (defined below) supplies nonexistent inputs + temp outputs
_rf = open(f"{HERE}/pod_f10_refit_v4.py").read()
check("★★ [P] refit source: no environ.get defaults for the four keys; report = best_ep_rule + trained_through_label_utc (last TBPTT loss anchor) + the kept pool-end field + sidecar json",
      all(x not in _rf for x in ('environ.get("F10_DLW"', 'environ.get("F10_OUT"', 'environ.get("BEST_EP_FIX"', 'environ.get("SEED"')) and '"trained_through_label_utc"' in _rf and '"best_ep_rule"' in _rf
      and '"trained_through": int(E_ts[tr_idx[-1]])' in _rf and "_last_loss_idx = int(starts[-1] + WIN - 1)" in _rf and 'f"{OUT}/models/f10_live_s{SEED}.json"' in _rf)
# exporter: generation AND output dir REQUIRED, king training cutoff recorded (R4).
# ★ 2026-09-12 INCIDENT (W3): the first version of the mutation check below ran the exporter with ONLY BUNDLE_GENERATION set; on the mac it died at
#   `from zload import zload`, on pod2 zload exists, so it exported with every DEFAULT path and rewrote /workspace/shadow_bundle_v4/slow2026.txt (the
#   r20 A1 bundle). Rule now enforced by this block: every real-program invocation in the suite names NONEXISTENT inputs and a temp output, and asserts
#   that nothing was written — a test must be unable to touch real data whatever machine it runs on.
_NOPE = {"BUNDLE_FEA": "/nonexistent/w3/fea.npy", "BUNDLE_META": "/nonexistent/w3/meta.npz", "BUNDLE_BASE": "/nonexistent/w3/base.json", "LIVE_PINS": "/nonexistent/w3/pins.json",
         "EXPORT_PANEL": "/nonexistent/w3/panel.npz", "BUNDLE_CACHE": "/nonexistent/w3/cache.npz", "FUND_AUG": "/nonexistent/w3/aug.json.gz", "FUNDING_DIR": "/nonexistent/w3/funding",
         "EMA_STATE_JSON": "/nonexistent/w3/ema.json", "BUNDLE_TAR": "/nonexistent/w3/never.tar.gz"}
# ★ SUITE RULE (team-lead, E-0912-B): a cell that invokes a REAL WRITER runs it only through run_sandboxed() — every input key it reads is a nonexistent
#   path, every output key is a fresh temp dir, and the cell asserts the temp dir stays empty. The static cell below greps THIS file for writer
#   invocations outside the helper (or outside the incident-sandbox `_NOPE` block) and fails if any exists.
_REAL_WRITERS = ("pod_export_bundle_v4.py", "pod_f10_refit_v4.py", "pod_legs_v4b.py", "build_dev_v4.py", "pod_dlw_targets_raw.py", "pod_fea_ext_clamp.py",
                 "merge_mwf_v4b.py", "pod_f10_train_monthly_v4.py", "pod_f8_build_stable.py", "pod_dlw_targets_raw.py")
_WRITER_INPUT_KEYS = ("BUNDLE_FEA", "BUNDLE_META", "BUNDLE_BASE", "LIVE_PINS", "EXPORT_PANEL", "BUNDLE_CACHE", "FUND_AUG", "FUNDING_DIR", "EMA_STATE_JSON",
                      "F10_DLW", "LEGS_TG", "LEGS_META", "LEGS_PRED", "LEGS_OLD", "LEGS_PANEL", "KING_META", "DLW_RAW", "CACHE", "HOLE_CELLS", "PREV_META", "V4_REF_META",
                      "DLWT_CACHE", "DLWT_PANEL", "CACHE_IN", "PANEL_IN", "F10_GATE_JSON", "MONTHS")
_WRITER_OUTPUT_KEYS = ("BUNDLE_OUT", "BUNDLE_TAR", "F10_OUT", "LEGS_OUT", "MWF_OUT", "DLWT_OUT", "FEA_OUT", "META_OUT", "V4_R", "V4_HC", "V4_KING_DIR", "V4_F8", "V4_DEV_PREDS", "GEN_OUT")
def run_sandboxed(script, env, tmp):
    """Run a real writer with NONEXISTENT inputs and temp outputs; return (rc, out, written) where written = files that appeared under tmp."""
    e = {k: f"/nonexistent/w3sandbox/{k.lower()}" for k in _WRITER_INPUT_KEYS}
    e.update({k: f"{tmp}/{k.lower()}" for k in _WRITER_OUTPUT_KEYS}); e.update(env or {})
    rc, out = run([script], e)
    written = [os.path.relpath(os.path.join(r, f), tmp) for r, _, fs in os.walk(tmp) for f in fs]
    return rc, out, written
with tempfile.TemporaryDirectory() as _dx:
    rc, out, _w = run_sandboxed("pod_f10_refit_v4.py", _env_clear, _dx)
    check("★★★ [P] refit with NO env ⇒ rc 2 REFIT_REFUSED naming all four keys (was: silent dlw_ext / f8_ext / argmax); nothing written", rc == 2 and "REFIT_REFUSED" in out and all(k in out for k in ("F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX")) and _w == [], out[-200:])
    rc, out, _w = run_sandboxed("pod_f10_refit_v4.py", {"SEED": "42", "BEST_EP_FIX": ""}, _dx)
    check("★★★ [P] refit with F10_DLW/F10_OUT/SEED but NO BEST_EP_FIX ⇒ refused, names BEST_EP_FIX only (the sub-shell FIX7 of the launcher never reaches a bare call); nothing written", rc == 2 and "['BEST_EP_FIX']" in out and _w == [], out[-200:])
    rc, out, _w = run_sandboxed("pod_f10_refit_v4.py", {"SEED": "42", "BEST_EP_FIX": "7"}, _dx)
    check("★★★ [P] MUTATION + SANDBOX: all four keys present ⇒ the refusal does NOT fire; the program proceeds and dies on the first nonexistent input (rc≠0, no REFIT_REFUSED), temp root stays EMPTY", rc != 0 and "REFIT_REFUSED" not in out and _w == [], (rc, _w, out[-160:]))
    rc, out, _w = run_sandboxed("pod_legs_v4b.py", {}, _dx)
    check("★★★ [P] SANDBOX: pod_legs_v4b.py with nonexistent LEGS_* inputs dies before writing (no LEGS_V4B_DONE, temp root empty)", rc != 0 and "LEGS_V4B_DONE" not in out and _w == [], (rc, _w, out[-160:]))
    rc, out, _w = run_sandboxed("build_dev_v4.py", {}, _dx)
    check("★★★ [P] SANDBOX: build_dev_v4.py with nonexistent inputs dies before writing (no DEV_V4_DONE, temp root empty)", rc != 0 and "DEV_V4_DONE" not in out and _w == [], (rc, _w, out[-160:]))
    _self = open(os.path.abspath(__file__)).read().splitlines()
    _viol = [(i + 1, l.strip()[:120]) for i, l in enumerate(_self)
             if ("run([" in l or "_bash(" in l or "subprocess.run(" in l) and any(w in l for w in _REAL_WRITERS) and "run_sandboxed" not in l and "_NOPE" not in l and "GEN_OUT" not in l and not l.lstrip().startswith("#")]
    check("★★★ [P] STATIC RULE: no cell in this suite invokes a real writer outside run_sandboxed()/the _NOPE sandbox block (E-0912-B: a bare invocation exported into /workspace/shadow_bundle_v4 on pod2)", _viol == [], _viol[:5])
with tempfile.TemporaryDirectory() as _dx:
    _out = f"{_dx}/never_written_bundle"
    rc, out = run(["pod_export_bundle_v4.py"], {**_NOPE, "BUNDLE_GENERATION": "", "BUNDLE_OUT": _out})
    check("★★★ [P] exporter without BUNDLE_GENERATION ⇒ rc 2 BUNDLE_FAIL generation_env_missing (was: the source constant 'v3_2026-09'); nothing written", rc == 2 and "BUNDLE_FAIL generation_env_missing" in out and not os.path.exists(_out), out[-200:])
    rc, out = run(["pod_export_bundle_v4.py"], {**_NOPE, "BUNDLE_GENERATION": "v4_2026-10", "BUNDLE_OUT": ""})
    check("★★★ [P] exporter without BUNDLE_OUT ⇒ rc 2 BUNDLE_FAIL bundle_out_env_missing (2026-09-12 incident: the September default was the r20 bundle); nothing written", rc == 2 and "BUNDLE_FAIL bundle_out_env_missing" in out and not os.path.exists(_out), out[-200:])
    rc, out = run(["pod_export_bundle_v4.py"], {**_NOPE, "BUNDLE_GENERATION": "v4_2026-10", "BUNDLE_OUT": _out})
    check("★★★ [P] MUTATION: with BUNDLE_GENERATION + BUNDLE_OUT the refusals do NOT fire — the program proceeds and dies on the FIRST nonexistent input (rc≠0, no BUNDLE_FAIL, the temp output dir stays EMPTY)",
          rc != 0 and "generation_env_missing" not in out and "bundle_out_env_missing" not in out and "BUNDLE_DONE" not in out and (not os.path.exists(_out) or os.listdir(_out) == []), (rc, out[-200:], os.path.exists(_out) and os.listdir(_out)))
_ex = open(f"{HERE}/pod_export_bundle_v4.py").read()
check("★★ [P] exporter source: provenance.generation = env; king_train_end_utc = last anchor of the label-year<2026 fit; built_utc kept separate; LIVE_PINS/FUND_AUG from env",
      '"generation": _GEN' in _ex and '"generation": "v3_2026-09"' not in _ex and '"king_train_end_utc": _iso(_king_train_end)' in _ex and "_tr_anchors = np.unique(A[tr]); _king_train_end = int(E_ts[int(_tr_anchors.max())])" in _ex
      and '"built_utc": time.strftime' in _ex and 'os.environ.get("LIVE_PINS", "/workspace/live_pins.json")' in _ex and 'os.environ.get("FUND_AUG", "/workspace/fund_aug.json.gz")' in _ex)
check("★★★ [P] exporter source: NO output default — BUNDLE_OUT is os.environ[...] (refused above when absent) and the tar default follows BUNDLE_OUT; the September path /workspace/shadow_bundle_v4 appears in no code line",
      'OUT = os.environ["BUNDLE_OUT"]' in _ex and 'os.environ.get("BUNDLE_OUT",' not in _ex and '"/workspace/shadow_bundle_v4' not in "\n".join(l for l in _ex.splitlines() if not l.lstrip().startswith("#") and '"""' not in l and "BUNDLE_FAIL bundle_out_env_missing" not in l))
_lg = open(f"{HERE}/pod_legs_v4b.py").read()
check("★★ [P] legs: the in-service legs file and the panel are env locators (LEGS_OLD / LEGS_PANEL) with September defaults", 'os.environ.get("LEGS_OLD", "/workspace/f8_ext/data/f10v2_legs.npz")' in _lg and 'os.environ.get("LEGS_PANEL", "/workspace/data/wide_panel_4h_v3splice.npz")' in _lg)
_ar = open(f"{HERE}/run_v4_arms.sh").read()
check("★★ [P] run_v4_arms.sh waits every arm BY PID and collects rcs (the bare `wait; grep | tail -4` is gone); dev tree / king dir from V4_HC / V4_KING_DIR", "for p in \"${pids[@]}\"; do wait $p; rc=$?" in _ar and "ARMS_FAIL" in _ar and "H=${V4_HC:-/workspace/review_scratch/health_check}" in _ar and "done; wait;" not in _ar)
# month env contract (chain_lib.load_month_env) — bash level
def _bash(cmd, env=None):
    e = dict(os.environ); e.update(env or {}); p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=e, cwd=HERE); return p.returncode, p.stdout + p.stderr
_KEYS = [k for k in open(f"{HERE}/chain_lib.sh").read().split('V4_MONTH_KEYS="', 1)[1].split('"', 1)[0].split()]
check("★★ [P] chain_lib registers the month contract keys (46 = 41 + the 4 PREV_* reference keys of the month-generic gates + PREV_CLAMP_BUILDER_SHA256, W7 2026-09-12) incl. the ones the task names: R, cache/panel/raw_patch, DLW/F8, MONTHS_ALL, SEEDS, BUNDLE_GENERATION, BUNDLE_BASE, EXPORT_PANEL, EMA_STATE_JSON, LIVE_PINS",
      len(_KEYS) == 46 and all(k in _KEYS for k in ("R", "CACHE", "PANEL_SPLICE", "RAW_PATCH", "DLW_RAW", "DLW_CLIP", "F8", "MONTHS_ALL", "SEEDS", "BUNDLE_GENERATION", "BUNDLE_BASE", "EXPORT_PANEL", "EMA_STATE_JSON", "LIVE_PINS", "PREV_DLW_CLIP", "PREV_F8", "PREV_KING_FEA", "PREV_KING_FEA_UNCLAMPED", "PREV_CLAMP_BUILDER_SHA256")), len(_KEYS))
with tempfile.TemporaryDirectory() as d:
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {HERE}/v4_month_2026-09.env; echo R=$R V4_F8=$V4_F8 RAW_PATCH=$RAW_PATCH", {"L": "/dev/null"})
    check("★★★ [P] load_month_env on the shipped September contract ⇒ rc 0; R / V4_F8 / RAW_PATCH resolve to the September paths (positive control of the contract file)",
          rc == 0 and "R=/workspace/review_scratch " in out and "V4_F8=/workspace/f8_v4" in out and "RAW_PATCH=/workspace/review_scratch/raw_patch.npz" in out, out[-300:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {HERE}/v4_month_2026-10.env.template >/dev/null; echo GATE_STEP1=$GATE_STEP1", {"L": "/dev/null"})
    check("★★ [P] the October template loads (every key present) and names the month-generic gate v4_gate_step1_m.py (not yet contract-approved: preflight refuses it as NOT approved until the user's word)", rc == 0 and "GATE_STEP1=v4_gate_step1_m.py" in out, out[-200:])
    _lines = open(f"{HERE}/v4_month_2026-09.env").read().splitlines()
    open(f"{d}/missing.env", "w").write("\n".join(l for l in _lines if not l.startswith("SEEDS=")) + "\n")
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/missing.env", {"L": "/dev/null"})
    check("★★★ [P] a contract missing one key (SEEDS) ⇒ rc 4 FAIL_month_env_key_missing_SEEDS", rc == 4 and "FAIL_month_env_key_missing_SEEDS" in out, out[-200:])
    open(f"{d}/empty.env", "w").write("\n".join((l if not l.startswith("SEEDS=") else "SEEDS=") for l in _lines) + "\n")
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/empty.env", {"L": "/dev/null"})
    check("★★ [P] a key present but EMPTY ⇒ refused the same way", rc == 4 and "FAIL_month_env_key_missing_SEEDS" in out, out[-200:])
    open(f"{d}/bad.env", "w").write("\n".join(_lines) + "\nSEEDS=42; rm -rf /\n")
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/bad.env", {"L": "/dev/null"})
    check("★★★ [P] a line with shell syntax (';') ⇒ rc 4 FAIL_month_env_malformed, nothing sourced", rc == 4 and "FAIL_month_env_malformed" in out, out[-200:])
    open(f"{d}/sub.env", "w").write("\n".join((l if not l.startswith("SEEDS=") else "SEEDS=$(echo 42)") for l in _lines) + "\n")
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/sub.env", {"L": "/dev/null"})
    check("★★ [P] a command substitution in a value ⇒ refused", rc == 4 and "FAIL_month_env_malformed" in out, out[-200:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/nope.env", {"L": "/dev/null"})
    check("★★ [P] a missing contract file ⇒ rc 4 FAIL_month_env_missing", rc == 4 and "FAIL_month_env_missing" in out, out[-200:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; MONTHS_ALL={','.join(str(m) for m in _der)} set_shards_from_months_all; echo SH0=$SH0 SH1=$SH1 SH2=$SH2 SH3=$SH3", {"L": "/dev/null", "PY": PY, "CHAIN_DEVICE_DIR": HERE, "R": d})
    check("★★★ [P] chain_lib set_shards_from_months_all reproduces the four hand-written shard lists from MONTHS_ALL", rc == 0 and all(f"SH{k}={s}" in out for k, s in enumerate(_VM.LEGACY_SHARDS_2026_09)), out[-300:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; MONTHS_ALL=202501,2025-03 set_shards_from_months_all; echo SH0=$SH0", {"L": "/dev/null", "PY": PY, "CHAIN_DEVICE_DIR": HERE, "R": d})
    check("★★ [P] MUTATION: a malformed MONTHS_ALL ⇒ set_shards dies (rc 4), no shard list is set", rc == 4 and "SH0=2025" not in out, out[-200:])
    # ── NEGATIVE CONTROL: the driver against an EMPTY month root stops at preflight and launches nothing ──
    rc, out = _bash(f"bash {HERE}/chain_v4_monthly_dryrun.sh {HERE}/v4_month_2026-09.env {d}", {"PY": PY})
    _recs = _glob.glob(f"{d}/v4_dryrun_*/dryrun_receipt.json"); _rr = json.load(open(_recs[0])) if _recs else None
    check("★★★ [P] NEGATIVE CONTROL: chain_v4_monthly.sh against an empty month root ⇒ driver rc 3, stopped at FAIL_preflight, training_launched 0, dryrun exit 0 (control passed)",
          rc == 0 and _rr and _rr["PASS"] is True and _rr["driver_rc"] == 3 and str(_rr["stopped_at"]).startswith("FAIL_preflight") and _rr["training_launched"] == 0, (rc, _rr and {k: _rr[k] for k in ("PASS", "driver_rc", "stopped_at", "training_launched")}))
    check("★★ [P] the dryrun receipt binds the driver / chain_lib / env shas and lists the preflight failures (every input under the empty root is missing)",
          _rr and _rr["driver_sha256"] == _sha(f"{HERE}/chain_v4_monthly.sh") and _rr["chain_lib_sha256"] == _sha(f"{HERE}/chain_lib.sh") and _rr["preflight_PASS"] is False and any("input missing" in f for f in _rr["preflight_fails"]), _rr and _rr["preflight_fails"][:2])
    # ── a root where EVERY input exists (fakes): preflight PASSES; under V4_DRYRUN=1 the next stage dies at the guard; without it the stage really runs ──
    def _fake_root(dd):
        root = f"{dd}/root"; os.makedirs(f"{root}/v4_gates", exist_ok=True); os.makedirs(f"{root}/funding", exist_ok=True)
        def touch(rel):
            p = f"{root}/{rel}"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b"x"); return p
        keys = dict(V4_MONTH="2026-99", R=root, PY=PY, CACHE=touch("cache.npz"), PANEL_SPLICE=touch("splice.npz"), PANEL_KING=touch("king_panel.npz"), RAW_PATCH=touch("raw_patch.npz"), HOLE_CELLS=touch("holes.npz"),
                    DLW_RAW=f"{root}/dlw_v4raw", DLW_CLIP=f"{root}/dlw_hf3", F8=f"{root}/f8_v4", KING_FEA=f"{root}/data/wide_fea_v4.npy", KING_META=f"{root}/data/wide_fea_v4_meta.npz",
                    MONTHS_ALL="202501,202502", SEEDS="42", MWF_ROOT="mwf_v4b", BUNDLE_OUT=f"{root}/bundle", BUNDLE_TAR=f"{root}/bundle.tar.gz", BUNDLE_GENERATION="v4_test", BUNDLE_BASE=touch("base.json"),
                    EXPORT_PANEL=f"{root}/splice.npz", EMA_STATE_JSON=touch("ema.json"), LIVE_PINS=touch("pins.json"), FUND_AUG=touch("aug.json.gz"), FUNDING_DIR=f"{root}/funding",
                    LEGS_OLD=touch("legs_old.npz"), LEGS_PANEL=f"{root}/splice.npz", DLW_EXT=f"{root}/dlw_ext", F8_EXT=f"{root}/f8_ext", HC=f"{root}/hc", KING_DIR=f"{root}/king", EXPORT_ARM="A1", SIGNAL_RECEIPT=touch("sig.json"),
                    BUILDER_FEA82=touch("b82.py"), BUILDER_FEA89=touch("b89.py"), BASE_TRAINER=touch("base_trainer.py"), GATE_STEP1="v4_gate_step1.py", GATE_STEP2="v4_gate_step2.py",
                    PREV_BUNDLE=f"{root}/prev", PREV_META=touch("prev_meta.npz"), REF_META=touch("ref_meta.npz"),
                    PREV_DLW_CLIP=f"{root}/prev_clip", PREV_F8=f"{root}/prev_f8", PREV_KING_FEA=touch("prev_king_fea.npy"), PREV_KING_FEA_UNCLAMPED="NONE", PREV_CLAMP_BUILDER_SHA256=_sha(f"{HERE}/pod_fea_ext_clamp.py"))
        touch("dlw_ext/data/dlw_targets.npz"); touch("f8_ext/preds/f10_V2MAIN_s42.npy"); touch("prev/slow_pred_pinned.npy")
        for rel in ["masks/umask_UPIT_CRYPTO.npz", "calib/costb_fee_steady.json", "run_arm.sh"] + [f"dev_v4/probe_artifacts/w10_ablation_series_V4_A0_{seat}_s{s}.npz" for seat in ("dyn", "fix") for s in (42, 2027)]: touch(f"hc/{rel}")
        envf = f"{dd}/fake.env"; open(envf, "w").write("\n".join(f"{k}={v}" for k, v in keys.items()) + "\n"); return root, envf
    _root, _envf = _fake_root(d)
    rc, out = _bash(f"V4_DRYRUN=1 V4_STAGES=preflight,cache bash {HERE}/chain_v4_monthly.sh {_envf}")
    _pf = json.load(open(f"{_root}/v4_gates/preflight.json"))
    check("★★★ [P] a root where every input EXISTS: preflight PASSES (21 device files pinned, 3/3 gate sources approved by the frozen contract) and, under V4_DRYRUN=1, the next stage dies at the guard (rc 9 FAIL_dryrun_guard_cache_would_launch) before running anything",
          rc == 9 and _pf["PASS"] is True and len(_pf["device_sha256"]) == 21 and all(a["ok"] for a in _pf["gate_approval"].values()) and "FAIL_dryrun_guard_cache_would_launch" in out and not os.path.exists(f"{_root}/cache_coverage.log"), (rc, _pf["fails"][:2], out[-200:]))
    rc, out = _bash(f"V4_STAGES=preflight,cache bash {HERE}/chain_v4_monthly.sh {_envf}")
    check("★★ [P] MUTATION: the same root WITHOUT V4_DRYRUN ⇒ the cache stage really runs (cache_coverage.log written) and fails on the fake cache with FAIL_cache_coverage_rc_*, rc 3 — the guard is what stopped the dryrun",
          rc == 3 and "FAIL_cache_coverage_rc_" in out and os.path.exists(f"{_root}/cache_coverage.log") and json.load(open(f"{_root}/v4_gates/cache_coverage.json"))["PASS"] is False, (rc, out[-200:]))
    open(f"{_envf}.badgate", "w").write(open(_envf).read().replace("GATE_STEP1=v4_gate_step1.py", "GATE_STEP1=v4_gate_closure.py"))
    rc, out = _bash(f"V4_STAGES=preflight bash {HERE}/chain_v4_monthly.sh {_envf}.badgate")
    _pf = json.load(open(f"{_root}/v4_gates/preflight.json"))
    check("★★★ [P] MUTATION: GATE_STEP1 pointing at a real but UNAPPROVED program (v4_gate_closure.py, approved only for G2_closure) ⇒ preflight FAIL 'gate source NOT approved', rc 3",
          rc == 3 and _pf["PASS"] is False and any("NOT approved" in f and "STEP1" in f for f in _pf["fails"]), _pf["fails"][:2])
    open(f"{_envf}.nokey", "w").write("\n".join(l for l in open(_envf).read().splitlines() if not l.startswith("BUNDLE_GENERATION=")) + "\n")
    rc, out = _bash(f"V4_STAGES=preflight bash {HERE}/chain_v4_monthly.sh {_envf}.nokey")
    check("★★ [P] the driver itself refuses a contract missing BUNDLE_GENERATION (rc 4) before any stage", rc == 4 and "FAIL_month_env_key_missing_BUNDLE_GENERATION" in out, out[-200:])
    rc, out = _bash(f"V4_STAGES=preflight bash {HERE}/chain_v4_monthly.sh {_envf}")
    check("★ [P] a stage SUBSET writes MONTHLY_STAGES_DONE.json (DONE false), never MONTHLY_DONE.json", rc == 0 and os.path.exists(f"{_root}/v4_gates/MONTHLY_STAGES_DONE.json") and json.load(open(f"{_root}/v4_gates/MONTHLY_STAGES_DONE.json"))["DONE"] is False and not os.path.exists(f"{_root}/v4_gates/MONTHLY_DONE.json"), out[-150:])

# ── [R] MONTH-GENERIC DATA GATES (2026-09-12 W7; docs/PREREG_v4_gates_monthly_2026-09-12.md; DESIGN_v4_monthly_chain §7 (i)): v4_gate_step1_m.py / v4_gate_step2_m.py read every
#        path from the month contract env, compare against the PREVIOUS month's pinned build, exempt the extension tail, refuse missing inputs and a reference identical to the candidate.
#        Frozen sources untouched (G0); diff == whitelist (G0); refusals on the October template (G2); wrong-month mutations on synthetic two-month worlds (G3); receipt identity + require (G4) ──
print("\n[R] month-generic STEP1/STEP2 gates: frozen untouched, diff == whitelist, template refusals (G2), wrong-month mutations (G3), receipt identity / require (G4)")
import difflib as _dl
import re as _re
import shutil as _shu
_W7 = f"{HERE}/receipts/monthly_chain_2026-09-12/w7_gates"
_FROZEN_SHA = {"v4_gate_step1.py": "278fdce611e91571d24ec26c78ddc4620668bfd4598a01f577f1f6887dd62be4", "v4_gate_step2.py": "db7ab3561f97423a8d5dd74251257adcedd743129d22a07d7cd186d102dd80d8"}
for _f, _s in _FROZEN_SHA.items():
    check(f"★★★ [R] G0 frozen {_f} sha unchanged ({_s[:12]}) — the contract-approved program is not the one edited", _sha(f"{HERE}/{_f}") == _s, _sha(f"{HERE}/{_f}")[:12])
import inspect as _insp
import v4_gate_common as _GC
check("★★ [R] G0 v4_gate_common: finalize(gate, res, out_path, inputs, exit_code_fail) and the STEP1@v4 / STEP2 registry names the new gates keep verbatim",
      list(_insp.signature(_GC.finalize).parameters) == ["gate", "res", "out_path", "inputs", "exit_code_fail"] and _GC.REQUIRED_INPUTS["STEP1@v4"] == ["dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4"] and _GC.REQUIRED_INPUTS["STEP2"] == ["wide_fea_v4", "wide_fea_v4_meta"])
_CON = json.load(open(f"{HERE}/ELIGIBILITY_CONTRACT.json")); _CON_SHA = _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json"); _COMMON_SHA = _sha(f"{HERE}/v4_gate_common.py"); _NEW_SHA = {g: _sha(f"{HERE}/{g}") for g in ("v4_gate_step1_m.py", "v4_gate_step2_m.py")}
check("★★ [R] G0 contract approves the frozen gates (278fdce6 / db7ab356) and does NOT (yet) list the month-generic ones — approval is the user's word, not this task's",
      _FROZEN_SHA["v4_gate_step1.py"] in _CON["gates"]["STEP1"]["approved_source_sha256"] and _FROZEN_SHA["v4_gate_step2.py"] in _CON["gates"]["STEP2"]["approved_source_sha256"]
      and _NEW_SHA["v4_gate_step1_m.py"] not in _CON["gates"]["STEP1"]["approved_source_sha256"] and _NEW_SHA["v4_gate_step2_m.py"] not in _CON["gates"]["STEP2"]["approved_source_sha256"])
_WL = {"v4_gate_step1.py": [9, 27, 32, 53, 56, 57, 78, 91, 92, 99, 104, 105, 106, 107, 108], "v4_gate_step2.py": [8, 14, 15, 22, 27, 28, 36, 48, 49, 50, 58, 64, 65, 66]}   # PREREG §1 tables
_LIT = {"v4_gate_step1.py": ["1e-6", "t - 48", "t - 1", "200000", "8640"], "v4_gate_step2.py": ["< 8640", "== 138", "CH = 128", "% 2048"]}                              # PREREG §4 thresholds
for _f, _wl in _WL.items():
    _m = _f.replace(".py", "_m.py"); _fl = open(f"{HERE}/{_f}").read().splitlines(keepends=True); _ml = open(f"{HERE}/{_m}").read().splitlines(keepends=True)
    _d = list(_dl.unified_diff(_fl, _ml, fromfile=_f, tofile=_m, n=0)); _saved = open(f"{_W7}/{_m.replace('.py', '.diff')}").read()
    check(f"★★★ [R] G0 saved diff {_m.replace('.py', '.diff')} == difflib recomputed now (the reviewer's artefact IS the change)", "".join(_d) == _saved, len(_d))
    _rm = []; _add = [l for l in _d if l.startswith("+") and not l.startswith("+++")]
    for _h in _d:
        _mm = _re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", _h)
        if _mm:
            _a = int(_mm.group(1)); _b = int(_mm.group(2)) if _mm.group(2) is not None else 1; _rm += list(range(_a, _a + _b))
    check(f"★★★ [R] G0 {_m}: the REMOVED frozen lines are exactly the PREREG §1 whitelist ({len(_wl)} lines: paths, reference objects, tail counts, finalize inputs)", sorted(_rm) == _wl, sorted(_rm))
    check(f"★★ [R] G0 {_m}: every ADDED line carries the `# [M]` marker (grep-able month-generic surface, {len(_add)} lines)", _add and all("# [M]" in l for l in _add), [l[:60] for l in _add if "# [M]" not in l][:3])
    _ft = "".join(_fl); _mt = "".join(_ml)
    check(f"★★★ [R] G0 {_m}: threshold literals occur exactly as often as in the frozen source {_LIT[_f]} (thresholds/statistics unchanged)", all(_ft.count(t) == _mt.count(t) for t in _LIT[_f]), {t: (_ft.count(t), _mt.count(t)) for t in _LIT[_f]})
    check(f"★ [R] G0 {_m}: no September literal path survives (/workspace/review_scratch, /workspace/dlw_, /workspace/f8_, /workspace/data/)", not any(p in _mt for p in ("/workspace/review_scratch", "/workspace/dlw_", "/workspace/f8_", "/workspace/data/")))
    check(f"★ [R] G0 {_m}: no os.environ.get(<key>, <non-empty default>) — every locator is required (an empty-string default is the refusal path, not a September fallback)", not _re.search(r'os\.environ\.get\("[A-Z_0-9]+",\s*"[^"]', _mt))

# ── synthetic two-month worlds: anchors E_row = 2016 + 48k (k < 138 ⇔ E_row < 8640 ⇒ n_first138 == 138 on any common axis ≥ 138 anchors), 6 symbols,
#    hole run rows 2100..2150 ⇒ neigh [2052, 10790] ⇒ anchors k ∈ [1, 182] inside, k = 0 and k ≥ 183 outside; filled symbols {0, 1} ──
_T0 = 1_700_000_000; _NWm = 6; _KP = [10, 50, 120, 170]; _NA_REF = 200; _NA_NEW = 230
_N82 = np.array(["fund_ema", "fund_now", "a_v", "b_v", "c_v", "d_r", "e_r", "f_r", "g_v", "h_r"]); _N89 = np.array([f"A:skew_{k}" for k in range(8)]); _SYM = np.array([f"S{i}USDT" for i in range(_NWm)])
def _members(nA, short=()):
    m = np.empty(nA, dtype=object)
    for i in range(nA): m[i] = np.arange(_NWm - 1) if i in short else np.arange(_NWm)
    return m
def _base(seed, nA):
    rng = np.random.default_rng(seed); E_row = 2016 + 48 * np.arange(nA); E_ts = _T0 + 300 * E_row
    return dict(E_row=E_row, E_ts=E_ts, y4s=rng.normal(size=(nA, _NWm)), qvk=rng.uniform(1, 2, size=(nA, _NWm)), YR4s=rng.normal(size=(nA, _NWm)), YRZ=rng.integers(0, _NWm, size=(nA, _NWm)).astype(float),
                yrs=np.full(nA, 2025), has_panel=np.ones((nA, _NWm), bool), btcv=rng.normal(size=nA), X82=rng.normal(size=(nA * _NWm, len(_N82))).astype(np.float32),
                X89=rng.normal(size=(nA * _NWm, len(_N89))).astype(np.float32), F=rng.normal(size=(nA, _NWm, len(_N82))).astype(np.float32), y4=rng.normal(size=(nA, _NWm)))
def _write_month(d, b, nA, kind, hole=(2100, 2150), patch_k=(30, 100, 210), prev=None):
    """kind 'new': RAW+CLIP targets, fea82 (+RAW copy), fea89, king fea/meta, cache, holes, raw_patch. kind 'ref': the reference build = first nA anchors of `prev`
    (same base) perturbed ONLY inside the hole neighbourhood for filled symbols (+ an unclamped variant differing only in the first 138 anchors)."""
    os.makedirs(f"{d}/dlw_raw/data", exist_ok=True); os.makedirs(f"{d}/dlw_clip/data", exist_ok=True); os.makedirs(f"{d}/f8/data", exist_ok=True)
    sl = slice(0, nA); E_row = b["E_row"][sl]; E_ts = b["E_ts"][sl]; nrows = 2016 + 48 * (_NA_NEW + 4)
    np.savez(f"{d}/cache.npz", ts=_T0 + 300 * np.arange(nrows))
    hr = np.arange(hole[0], hole[1] + 1); np.savez(f"{d}/holes.npz", fill_runs=np.array([list(hole)]), neigh_rows=np.array([[hole[0] - 48, hole[1] + 8640]]), row=np.repeat(hr, 2), col=np.tile([0, 1], len(hr)), symbols=_SYM)
    y4s = b["y4s"][sl].copy(); y4old = (b["y4s"][sl] * 0.9).copy(); qvk = b["qvk"][sl].copy(); YR4s = b["YR4s"][sl].copy(); YRZ = b["YRZ"][sl].copy(); y4 = b["y4"][sl].copy()
    X82 = b["X82"][: nA * _NWm].copy(); X89 = b["X89"][: nA * _NWm].copy(); F = b["F"][sl].copy(); pa = np.repeat(np.arange(nA), _NWm); ps = np.tile(np.arange(_NWm), nA)
    short = ()
    if kind == "ref":   # perturb inside neigh (k in _KP ⊂ [1,182]) — value columns only for filled symbols {0,1}; rank columns any symbol; members shortened
        kp = np.array(_KP); short = tuple(_KP)
        y4s[kp, 0] += 0.01; y4old[kp, 1] += 0.01; qvk[kp, 0] *= 1.1; YR4s[kp, :] += 0.01; YRZ[kp, :] += 1; y4[kp, 0] += 0.01
        X82[kp * _NWm + 0, 2] += 0.01; X82[kp * _NWm + 3, 5] += 0.01; X89[kp * _NWm + 1, 0] += 0.01; F[kp, 0, 2] += 0.01; F[kp, 3, 5] += 0.01
        FE = F.copy(); FE[:138, :, 2] += 0.001; np.save(f"{d}/king_fea_unclamped.npy", FE)
    tg = dict(E_ts=E_ts, E_row=E_row, members=_members(nA, short), yrs=b["yrs"][sl], has_panel=b["has_panel"][sl], symbols=_SYM, btcv=b["btcv"][sl], qvk=qvk, y4old=y4old, y4s=y4s, YR4s=YR4s, YRZ=YRZ)
    np.savez(f"{d}/dlw_clip/data/dlw_targets.npz", **tg); np.savez(f"{d}/dlw_clip/data/dlw_fea82.npz", X=X82, pair_a=pa, pair_s=ps, names=_N82); np.savez(f"{d}/f8/data/f8_fea89.npz", X=X89, pair_a=pa, pair_s=ps, names=_N89)
    np.save(f"{d}/king_fea.npy", F); np.savez(f"{d}/king_meta.npz", E_ts=E_ts, names=_N82, members=_members(nA, short), y4=y4, qvk=qvk)
    if kind == "new":   # RAW = CLIP except inside the raw-patch windows (E_row in [t-48, t-1]); YR4s/YRZ differ on the patched rows
        pk = np.array([k for k in patch_k if k < nA]); prow = E_row[pk] + 24; np.savez(f"{d}/raw_patch.npz", row=prow, col=np.full(len(pk), 2))
        A = dict(tg); A["y4s"] = y4s.copy(); A["y4s"][pk, 2] += 0.5; A["YR4s"] = YR4s.copy(); A["YR4s"][pk, :] += 0.1; A["YRZ"] = YRZ.copy(); A["YRZ"][pk, :] += 1
        np.savez(f"{d}/dlw_raw/data/dlw_targets.npz", **A); _shu.copyfile(f"{d}/dlw_clip/data/dlw_fea82.npz", f"{d}/dlw_raw/data/dlw_fea82.npz")
def _env1(new, ref, out, **over):
    e = dict(HOLE_CELLS=f"{new}/holes.npz", DLW_RAW=f"{new}/dlw_raw", DLW_CLIP=f"{new}/dlw_clip", RAW_PATCH=f"{new}/raw_patch.npz", CACHE=f"{new}/cache.npz", F8=f"{new}/f8", PREV_DLW_CLIP=f"{ref}/dlw_clip", PREV_F8=f"{ref}/f8", STEP1_OUT=out); e.update(over); return e
def _env2(new, ref, out, **over):
    e = dict(HOLE_CELLS=f"{new}/holes.npz", CACHE=f"{new}/cache.npz", KING_FEA=f"{new}/king_fea.npy", KING_META=f"{new}/king_meta.npz", PREV_KING_FEA=f"{ref}/king_fea.npy", PREV_KING_FEA_UNCLAMPED=f"{ref}/king_fea_unclamped.npy", PREV_META=f"{ref}/king_meta.npz", STEP2_OUT=out); e.update(over); return e
def _none_env(new, ref, out, rootdir, **over):
    """AMENDMENT 1: a NONE month must carry PREV_CLAMP_BUILDER_SHA256 and a month root R whose v4_gates/deps_preflight_device.json pins pod_fea_ext_clamp.py at that sha."""
    os.makedirs(f"{rootdir}/v4_gates", exist_ok=True); _pin = over.pop("pin", _sha(f"{HERE}/pod_fea_ext_clamp.py")); _pf = over.pop("preflight_pin", _pin)
    json.dump({"stage": "preflight_device", "deps_sha256": {f"{HERE}/pod_fea_ext_clamp.py": _pf, f"{HERE}/chain_lib.sh": _sha(f"{HERE}/chain_lib.sh")}}, open(f"{rootdir}/v4_gates/deps_preflight_device.json", "w"))
    return _env2(new, ref, out, PREV_KING_FEA_UNCLAMPED="NONE", PREV_CLAMP_BUILDER_SHA256=_pin, R=rootdir, **over)
def _g(script, env):
    rc, out = run([script], env); rp = env.get("STEP1_OUT") or env.get("STEP2_OUT"); r = json.load(open(rp)) if rp and os.path.exists(rp) else None; return rc, out, r
_META = {"utc", "built_utc", "argv", "self_sha256", "inputs_sha256", "inputs_path", "receipt_schema", "gate"}
def _keys(o, path=""):
    if isinstance(o, dict): return set().union(*[_keys(v, f"{path}/{k}") for k, v in o.items() if path or k not in _META]) | {f"{path}/{k}" for k in o if path or k not in _META}
    return set()
def _tmpl_env(path):
    e = {}
    for l in open(path):
        l = l.strip()
        if l and not l.startswith("#"): k, v = l.split("=", 1); e[k] = v.replace("$R", e.get("R", "$R"))
    return e
_ARCH1 = json.load(open(f"{HERE}/receipts/monthly_chain_2026-09-12/pod2_root/step1.json")); _ARCH2 = json.load(open(f"{HERE}/receipts/monthly_chain_2026-09-12/pod2_root/step2.json"))
with tempfile.TemporaryDirectory() as d:
    _bX = _base(1, _NA_NEW); _bY = _base(7, _NA_REF)
    _write_month(f"{d}/X1", _bX, _NA_NEW, "new"); _write_month(f"{d}/X0", _bX, _NA_REF, "ref"); _write_month(f"{d}/X1same", _bX, _NA_REF, "new"); _write_month(f"{d}/Y", _bY, _NA_REF, "ref", hole=(6000, 6050))
    # ── positive: month X+1 (230 anchors) against its reference month X (200 anchors): differences only in the hole neighbourhood, 30 tail anchors exempt ──
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_tail.json"))
    check("★★★ [R] G3(h) STEP1 on the extension-month fixture ⇒ PASS rc 0; the 30 new-month anchors are the tail: axis_only_hf3=30, outside_neigh 0, tail_exempt 30 + ref_axis_end_utc; fea82/fea89 pairs_only_a=180 all tail-exempt",
          rc == 0 and r and r["PASS"] is True and r["B_targets_hf3_vs_hf2"]["axis_only_hf3"] == 30 and r["B_targets_hf3_vs_hf2"]["axis_only_hf3_outside_neigh"] == 0 and r["B_targets_hf3_vs_hf2"]["axis_only_hf3_tail_exempt"] == 30
          and "ref_axis_end_utc" in r["B_targets_hf3_vs_hf2"] and all(r[k]["pairs_only_a"] == 180 and r[k]["pairs_only_a_outside_neigh"] == 0 and r[k]["pairs_only_a_tail_exempt"] == 180 for k in ("B_fea82_hf3_vs_hf2", "B_fea89_f8v4_vs_f8hf2")), (rc, out[-300:]))
    check("★★ [R] STEP1 the in-neigh reference differences are counted (not hidden) and A (RAW vs CLIP) sees exactly the 3 patched anchors", r and r["B_targets_hf3_vs_hf2"]["y4s_diff_cells"] == 4 and r["B_targets_hf3_vs_hf2"]["members_diff_rows"] == 4 and r["B_fea82_hf3_vs_hf2"]["common_pairs_diff"] == 8
          and r["A_raw_vs_clip"]["patch_anchors"] == 3 and r["A_raw_vs_clip"]["y4s_big_cells"] == 3 and r["A_raw_vs_clip"]["PASS"] is True and r["fea82_copy_identical"] is True, r and (r["B_targets_hf3_vs_hf2"]["y4s_diff_cells"], r["A_raw_vs_clip"]["patch_anchors"]))
    check("★★★ [R] G4 STEP1 receipt identity: gate=STEP1, self_sha256 == sha(v4_gate_step1_m.py), every REQUIRED_INPUTS[STEP1@v4] name + hf2/raw_patch/hole_cells + cache hashed (11 inputs, none None)",
          r and r["gate"] == "STEP1" and r["self_sha256"] == _NEW_SHA["v4_gate_step1_m.py"] and set(r["inputs_sha256"]) == set(_ARCH1["inputs_sha256"]) | {"cache"} and all(r["inputs_sha256"].values()) and len(r["inputs_sha256"]) == 11, r and sorted(r["inputs_sha256"]))
    _S1 = dict(zip(("dlw_v4raw_targets", "dlw_hf3_targets", "fea82_v4raw", "fea89_f8v4"), (f"{d}/X1/dlw_raw/data/dlw_targets.npz", f"{d}/X1/dlw_clip/data/dlw_targets.npz", f"{d}/X1/dlw_raw/data/dlw_fea82.npz", f"{d}/X1/f8/data/f8_fea89.npz")))
    rc, out = run(["v4_gate_common.py", "require", f"{d}/s1_tail.json", "gate=STEP1", "profile=v4", f"self_sha={_NEW_SHA['v4_gate_step1_m.py']}"] + [f"{k}={v}" for k, v in _S1.items()])
    check("★★★ [R] G4 require under the REAL contract refuses the month-generic gate's PASS receipt: 'not an APPROVED source' (the contract, not the caller, decides; approval = user word)", rc == 3 and "not an APPROVED source" in out, out[-200:])
    os.makedirs(f"{d}/sim"); _shu.copyfile(f"{HERE}/v4_gate_common.py", f"{d}/sim/v4_gate_common.py"); _c2 = json.loads(json.dumps(_CON))
    _c2["gates"]["STEP1"]["approved_source_sha256"].append(_NEW_SHA["v4_gate_step1_m.py"]); _c2["gates"]["STEP2"]["approved_source_sha256"].append(_NEW_SHA["v4_gate_step2_m.py"]); json.dump(_c2, open(f"{d}/sim/ELIGIBILITY_CONTRACT.json", "w"))
    rc, out = run([f"{d}/sim/v4_gate_common.py", "require", f"{d}/s1_tail.json", "gate=STEP1", "profile=v4", f"self_sha={_NEW_SHA['v4_gate_step1_m.py']}"] + [f"{k}={v}" for k, v in _S1.items()])
    check("★★★ [R] G4 the SAME receipt under a SIMULATED contract copy (approved list + new sha; real contract untouched) ⇒ REQUIRE_OK with the STEP1@v4 floor (4 inputs verified) — nothing else has to change for the driver to accept the new gates once approved",
          rc == 0 and "REQUIRE_OK" in out and "registered floor STEP1@v4=4" in out and _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json") == _CON_SHA, out[-200:])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_tail.json"))
    check("★★★ [R] G3(h) STEP2 on the extension-month fixture ⇒ PASS rc 0; anchors_only_v4 = 30 (tail) exempt, n_first138 == 138, clamp checks evaluated (clamp_vs_ext.anchors 138, outside_138 0), in-neigh reference diffs counted",
          rc == 0 and r2 and r2["PASS"] is True and len(r2["anchors_only_v4"]) == 30 and r2["anchors_only_v4_outside_neigh"] == 0 and r2["anchors_only_v4_tail_exempt"] == 30 and "ref_axis_end_utc" in r2 and r2["n_first138"] == 138
          and r2["features"]["clamp_vs_ext"] == {"anchors": 138, "outside_138": 0} and r2["features"]["v4_vs_ext"]["outside_138_and_neigh"] == 0 and r2["features"]["v4_vs_clamp"]["anchors"] == 4 and r2["members_diff_rows"] == 4 and "clamp_checks" not in r2, (rc, out[-300:]))
    check("★★★ [R] G4 STEP2 receipt identity: gate=STEP2, self_sha256 == sha(v4_gate_step2_m.py), the 6 frozen input names + cache hashed (7, none None)",
          r2 and r2["gate"] == "STEP2" and r2["self_sha256"] == _NEW_SHA["v4_gate_step2_m.py"] and set(r2["inputs_sha256"]) == set(_ARCH2["inputs_sha256"]) | {"cache"} and all(r2["inputs_sha256"].values()), r2 and sorted(r2["inputs_sha256"]))
    rc, out = run([f"{d}/sim/v4_gate_common.py", "require", f"{d}/s2_tail.json", "gate=STEP2", f"self_sha={_NEW_SHA['v4_gate_step2_m.py']}", f"wide_fea_v4={d}/X1/king_fea.npy", f"wide_fea_v4_meta={d}/X1/king_meta.npz"])
    check("★★★ [R] G4 STEP2 receipt under the simulated contract ⇒ REQUIRE_OK (STEP2 floor, 2 inputs) — exactly the driver's require_gate call shape", rc == 0 and "REQUIRE_OK" in out and "registered floor STEP2=2" in out, out[-200:])
    # ── field-set identity: no extension tail ⇒ the receipt's verdict field set == the archived September receipts' (recursively) ──
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1same", f"{d}/X0", f"{d}/s1_same.json"))
    check("★★★ [R] G3(i) STEP1 with NO extension tail (same axis as the reference) ⇒ PASS and the verdict field set == the archived September step1.json field set (78 fields; no *_tail_exempt anywhere)",
          rc == 0 and r and r["PASS"] is True and _keys(r) == _keys(_ARCH1) and "tail_exempt" not in json.dumps(r), r and (sorted(_keys(r) ^ _keys(_ARCH1))[:6], rc))
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1same", f"{d}/X0", f"{d}/s2_same.json"))
    check("★★★ [R] G3(i) STEP2 with NO extension tail ⇒ PASS and the verdict field set == the archived September step2.json field set (31 fields)", rc == 0 and r2 and r2["PASS"] is True and _keys(r2) == _keys(_ARCH2) and "tail_exempt" not in json.dumps(r2), r2 and sorted(_keys(r2) ^ _keys(_ARCH2))[:6])
    # ── G2: the October TEMPLATE (TODO paths, four new keys absent) ⇒ clean refusal: rc 3, PASS=false receipt, REFUSED names every missing key and TODO path, no PASS anywhere ──
    _te = _tmpl_env(f"{HERE}/v4_month_2026-10.env.template"); _te = {k: _te[k] for k in ("HOLE_CELLS", "DLW_RAW", "DLW_CLIP", "RAW_PATCH", "CACHE", "F8", "KING_FEA", "KING_META", "PREV_META")}
    rc, out, r = _g("v4_gate_step1_m.py", {**_te, "PREV_DLW_CLIP": "", "PREV_F8": "", "STEP1_OUT": f"{d}/s1_tmpl.json"})
    check("★★★ [R] G2 STEP1 on the October template env (TODO paths; PREV_DLW_CLIP / PREV_F8 absent) ⇒ rc 3, STEP1_REFUSED, receipt PASS=false naming missing_env [PREV_DLW_CLIP, PREV_F8] and every TODO/absent path; inputs sha None",
          rc == 3 and "STEP1_REFUSED" in out and r and r["PASS"] is False and r["REFUSED"]["missing_env"] == ["PREV_DLW_CLIP", "PREV_F8"] and any("TODO_" in str(v) for v in r["REFUSED"]["missing_files"].values())
          and set(r["REFUSED"]["missing_files"]) >= {"hole_cells", "cache", "dlw_v4raw_targets", "dlw_hf2_targets", "fea89_f8hf2"} and not any(r["inputs_sha256"].values()), (rc, r and r["REFUSED"].get("missing_env"), out[-200:]))
    rc, out, r2 = _g("v4_gate_step2_m.py", {**_te, "PREV_KING_FEA": "", "PREV_KING_FEA_UNCLAMPED": "", "STEP2_OUT": f"{d}/s2_tmpl.json"})
    check("★★★ [R] G2 STEP2 on the October template env ⇒ rc 3, STEP2_REFUSED, PASS=false, missing_env [PREV_KING_FEA, PREV_KING_FEA_UNCLAMPED], TODO cache/holes named",
          rc == 3 and "STEP2_REFUSED" in out and r2 and r2["PASS"] is False and r2["REFUSED"]["missing_env"] == ["PREV_KING_FEA", "PREV_KING_FEA_UNCLAMPED"] and any("TODO_" in str(v) for v in r2["REFUSED"]["missing_files"].values()), (rc, r2 and r2["REFUSED"].get("missing_env")))
    _full = _tmpl_env(f"{HERE}/v4_month_2026-10.env.template"); _te2 = {k: _full[k] for k in list(_te) + ["PREV_DLW_CLIP", "PREV_F8", "PREV_KING_FEA", "PREV_KING_FEA_UNCLAMPED"]}
    rc, out, r = _g("v4_gate_step1_m.py", {**_te2, "STEP1_OUT": f"{d}/s1_tmpl2.json"}); rc2_, out2_, r2_ = _g("v4_gate_step2_m.py", {**_te2, "STEP2_OUT": f"{d}/s2_tmpl2.json"})
    check("★★★ [R] G2 the October template AS SHIPPED (PREV_* = TODO paths, PREV_KING_FEA_UNCLAMPED=NONE, GATE_STEP1/2 = the _m gates): both gates refuse on the TODO PATHS (no missing_env), rc 3, PASS=false; STEP2 treats NONE as the explicit skip (wide_fea_v2ext not a missing file)",
          rc == 3 and rc2_ == 3 and r and r2_ and r["PASS"] is False and r2_["PASS"] is False and "missing_env" not in r["REFUSED"] and "missing_env" not in r2_["REFUSED"] and "TODO_dlw_hf3" in r["REFUSED"]["missing_files"]["dlw_hf2_targets"]
          and "TODO_wide_fea_v4" in r2_["REFUSED"]["missing_files"]["wide_fea_v2ext_clamp"] and "wide_fea_v2ext" not in r2_["REFUSED"]["missing_files"] and _full["GATE_STEP1"] == "v4_gate_step1_m.py" and _full["GATE_STEP2"] == "v4_gate_step2_m.py" and _te2["PREV_KING_FEA_UNCLAMPED"] == "NONE", (rc, rc2_, r and r["REFUSED"].keys(), r2_ and sorted(r2_["REFUSED"].get("missing_files", {}))))
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_todo.json", PREV_DLW_CLIP="/workspace/m2026-10/TODO_prev_clip"))
    check("★★ [R] G3(f) a TODO path in one key ⇒ REFUSED names exactly that input pair (dlw_hf2_targets, fea82_hf2) by path; rc 3; PASS=false", rc == 3 and r and r["PASS"] is False and set(r["REFUSED"]["missing_files"]) == {"dlw_hf2_targets", "fea82_hf2"} and "TODO_prev_clip" in r["REFUSED"]["missing_files"]["dlw_hf2_targets"] and "missing_env" not in r["REFUSED"], r and r["REFUSED"])
    rc, out = run(["v4_gate_step1_m.py"], {**_env1(f"{d}/X1", f"{d}/X0", ""), "STEP1_OUT": ""})
    check("★★ [R] G2 STEP1 without STEP1_OUT ⇒ rc 3 'STEP1_REFUSED missing STEP1_OUT' and NO receipt (no September default path is written to)", rc == 3 and "STEP1_REFUSED missing STEP1_OUT" in out and not os.path.exists("/workspace/review_scratch/v4_gates/step1.json"), out[-120:])
    for _r_ in ("s1_tmpl", "s2_tmpl", "s1_todo"):
        rc, out = run(["v4_gate_common.py", "require", f"{d}/{_r_}.json", "gate=" + ("STEP1" if _r_.startswith("s1") else "STEP2"), f"self_sha={_NEW_SHA['v4_gate_step1_m.py' if _r_.startswith('s1') else 'v4_gate_step2_m.py']}", f"x={HERE}/v4_gate_common.py"])
        check(f"★ [R] G2 a refusal receipt ({_r_}) can never be required (rc 3)", rc == 3, out[-120:])
    # ── G3 mutations: pointing a path at the WRONG month's file changes the verdict or is refused (each named) ──
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_self.json", PREV_DLW_CLIP=f"{d}/X1/dlw_clip"))
    check("★★★ [R] G3(a) STEP1 reference == candidate (PREV_DLW_CLIP → this month's DLW_CLIP) ⇒ REFUSED reference_is_candidate names dlw_hf3_targets==dlw_hf2_targets and fea82_hf3==fea82_hf2; rc 3; nothing compared",
          rc == 3 and r and r["PASS"] is False and r["REFUSED"] == {"reference_is_candidate": ["dlw_hf3_targets==dlw_hf2_targets", "fea82_hf3==fea82_hf2"]} and "A_raw_vs_clip" not in r, (rc, r and r["REFUSED"]))
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_wrongref.json", PREV_DLW_CLIP=f"{d}/Y/dlw_clip"))
    check("★★★ [R] G3(b) STEP1 PREV_DLW_CLIP → an unrelated month (world Y) ⇒ B targets/fea82 differences outside the neighbourhood ⇒ PASS false, rc 3 (the verdict changed)",
          rc == 3 and r and r["PASS"] is False and r["B_targets_hf3_vs_hf2"]["PASS"] is False and r["B_targets_hf3_vs_hf2"]["y4s_diff_outside_neigh"] > 0 and r["B_fea82_hf3_vs_hf2"]["diff_pairs_outside_neigh"] > 0 and r["A_raw_vs_clip"]["PASS"] is True, r and (r["B_targets_hf3_vs_hf2"]["y4s_diff_outside_neigh"]))
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_wrongf8.json", PREV_F8=f"{d}/Y/f8"))
    check("★★★ [R] G3(b′) STEP1 PREV_F8 → world Y ⇒ only the fea89 comparison fails (diff_pairs_outside_neigh > 0), targets/fea82 still PASS ⇒ total PASS false", rc == 3 and r and r["PASS"] is False and r["B_fea89_f8v4_vs_f8hf2"]["PASS"] is False and r["B_fea89_f8v4_vs_f8hf2"]["diff_pairs_outside_neigh"] > 0 and r["B_targets_hf3_vs_hf2"]["PASS"] is True and r["B_fea82_hf3_vs_hf2"]["PASS"] is True, r and r["B_fea89_f8v4_vs_f8hf2"]["diff_pairs_outside_neigh"])
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_wrongholes.json", HOLE_CELLS=f"{d}/Y/holes.npz"))
    check("★★★ [R] G3(c) STEP1 HOLE_CELLS → world Y's hole file (run at rows 6000..6050) ⇒ the reference's real differences (k=10, 50) fall outside that neighbourhood ⇒ PASS false", rc == 3 and r and r["PASS"] is False and r["B_targets_hf3_vs_hf2"]["members_diff_rows_outside_neigh"] > 0 and r["neigh_rows"] == [[5952, 14690]], r and r["neigh_rows"])
    rc, out, r = _g("v4_gate_step1_m.py", _env1(f"{d}/X1", f"{d}/X0", f"{d}/s1_nokey.json", PREV_F8=""))
    check("★★★ [R] G3(e) STEP1 PREV_F8 unset ⇒ REFUSED missing_env ['PREV_F8'] + missing_files fea89_f8hf2 (None); rc 3", rc == 3 and r and r["PASS"] is False and r["REFUSED"]["missing_env"] == ["PREV_F8"] and r["REFUSED"]["missing_files"] == {"fea89_f8hf2": None}, r and r["REFUSED"])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_self.json", KING_FEA=f"{d}/X0/king_fea.npy"))
    check("★★★ [R] G3(d) STEP2 KING_FEA → the reference file ⇒ REFUSED reference_is_candidate ['wide_fea_v4==wide_fea_v2ext_clamp'] (a same-content comparison verifies nothing); rc 3", rc == 3 and r2 and r2["PASS"] is False and r2["REFUSED"] == {"reference_is_candidate": ["wide_fea_v4==wide_fea_v2ext_clamp"]}, r2 and r2["REFUSED"])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_selfmeta.json", PREV_META=f"{d}/X1/king_meta.npz"))
    check("★★ [R] G3(d′) STEP2 PREV_META → this month's meta ⇒ REFUSED ['wide_fea_v4_meta==wide_fea_v2ext_meta']", rc == 3 and r2 and r2["REFUSED"] == {"reference_is_candidate": ["wide_fea_v4_meta==wide_fea_v2ext_meta"]}, r2 and r2["REFUSED"])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_wrongref.json", PREV_KING_FEA=f"{d}/Y/king_fea.npy"))
    check("★★★ [R] G3(b) STEP2 PREV_KING_FEA → world Y ⇒ v4_vs_clamp.outside > 0 and clamp_vs_ext.outside_138 > 0 ⇒ PASS false, rc 3", rc == 3 and r2 and r2["PASS"] is False and r2["features"]["v4_vs_clamp"]["outside"] > 0 and r2["features"]["clamp_vs_ext"]["outside_138"] > 0, r2 and r2["features"])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_wrongmeta.json", PREV_META=f"{d}/Y/king_meta.npz"))
    check("★★ [R] G3(b″) STEP2 PREV_META → world Y's meta ⇒ y4/qvk differences outside the neighbourhood ⇒ PASS false", rc == 3 and r2 and r2["PASS"] is False and r2["y4_diff_outside_neigh"] > 0, r2 and r2.get("y4_diff_outside_neigh"))
    rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/s2_none.json", f"{d}/R_none"))
    check("★★★ [R] G3(g) STEP2 PREV_KING_FEA_UNCLAMPED=NONE (with the builder identity of AMENDMENT 1) ⇒ PASS (data checks intact) and the receipt SAYS so: clamp_checks.mode='NOT_EVALUATED…' + the three equal builder shas, features == {v4_vs_clamp} only, wide_fea_v2ext path/sha None (the skip is recorded, never silent)",
          rc == 0 and r2 and r2["PASS"] is True and str(r2["clamp_checks"]["mode"]).startswith("NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE") and r2["clamp_checks"]["pinned_sha256"] == r2["clamp_checks"]["preflight_pinned_sha256"] == r2["clamp_checks"]["device_file_sha256"] == _sha(f"{HERE}/pod_fea_ext_clamp.py")
          and set(r2["features"]) == {"v4_vs_clamp"} and r2["inputs_path"]["wide_fea_v2ext"] is None and r2["inputs_sha256"]["wide_fea_v2ext"] is None and r2["anchors_only_v4_tail_exempt"] == 30, (rc, r2 and (r2.get("REFUSED"), list(r2.get("features", {})))))
    rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/s2_none_wrong.json", f"{d}/R_none", PREV_KING_FEA=f"{d}/Y/king_fea.npy"))
    check("★★★ [R] G3(g′) NONE does not blind the data check: NONE + PREV_KING_FEA → world Y ⇒ PASS false (v4_vs_clamp.outside > 0)", rc == 3 and r2 and r2["PASS"] is False and r2["features"]["v4_vs_clamp"]["outside"] > 0, r2 and r2["features"])
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_nokey.json", PREV_KING_FEA_UNCLAMPED=""))
    check("★★ [R] G3(e′) STEP2 PREV_KING_FEA_UNCLAMPED EMPTY (not NONE) ⇒ REFUSED missing_env — the skip needs the explicit word NONE in the contract", rc == 3 and r2 and r2["REFUSED"]["missing_env"] == ["PREV_KING_FEA_UNCLAMPED"], r2 and r2["REFUSED"])
    # ── the tail exemption is ONE-SIDED: an extra new-month anchor BEFORE the reference's first anchor is not a tail and must be explained by a hole ──
    _m1 = dict(np.load(f"{d}/X1/king_meta.npz", allow_pickle=True)); _F1 = np.load(f"{d}/X1/king_fea.npy"); os.makedirs(f"{d}/X1pre")
    _mm = np.empty(len(_m1["members"]) + 1, dtype=object); _mm[0] = np.arange(_NWm); _mm[1:] = _m1["members"]
    np.savez(f"{d}/X1pre/king_meta.npz", E_ts=np.concatenate([[_T0 + 300 * 1968], _m1["E_ts"]]), names=_m1["names"], members=_mm, y4=np.vstack([_m1["y4"][:1], _m1["y4"]]), qvk=np.vstack([_m1["qvk"][:1], _m1["qvk"]])); np.save(f"{d}/X1pre/king_fea.npy", np.concatenate([_F1[:1] * 0.5, _F1]))
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/s2_pre.json", KING_FEA=f"{d}/X1pre/king_fea.npy", KING_META=f"{d}/X1pre/king_meta.npz"))
    check("★★★ [R] G3 MUTATION of the tail rule: a new-month anchor BEFORE the reference axis start (row 1968, outside neigh) is NOT exempt ⇒ anchors_only_v4_outside_neigh == 1 ⇒ PASS false (the 30 real tail anchors still exempt)",
          rc == 3 and r2 and r2["PASS"] is False and r2["anchors_only_v4_outside_neigh"] == 1 and r2["anchors_only_v4_tail_exempt"] == 30 and len(r2["anchors_only_v4"]) == 31, r2 and (r2.get("anchors_only_v4_outside_neigh"), r2.get("anchors_only_v4_tail_exempt")))
    # ── the driver's calling convention: chain_lib.run_gate <name> <basename in D> <log> STEPx_OUT=… with the contract keys exported ──
    rc, out = _bash(f". {HERE}/chain_lib.sh; run_gate STEP1 v4_gate_step1_m.py {d}/rg1.log STEP1_OUT={d}/rg1.json; echo rc=$?", {**_env1(f"{d}/X1", f"{d}/X0", ""), "STEP1_OUT": "", "PY": PY, "CHAIN_DEVICE_DIR": HERE, "R": d, "L": "/dev/null"})
    check("★★★ [R] under the driver's run_gate (chain_lib.sh; D=CHAIN_DEVICE_DIR; contract keys exported) the month-generic STEP1 runs, rc 0, receipt PASS — no driver change is needed, only the contract keys + approval",
          "rc=0" in out and os.path.exists(f"{d}/rg1.json") and json.load(open(f"{d}/rg1.json"))["PASS"] is True and "STEP1 PASS" in open(f"{d}/rg1.log").read(), out[-200:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; run_gate STEP2 v4_gate_step2_m.py {d}/rg2.log STEP2_OUT={d}/rg2.json; echo rc=$?", {**_env2(f"{d}/X1", f"{d}/X0", ""), "STEP2_OUT": "", "PY": PY, "CHAIN_DEVICE_DIR": HERE, "R": d, "L": "/dev/null"})
    check("★★ [R] run_gate STEP2 v4_gate_step2_m.py ⇒ rc 0, receipt PASS", "rc=0" in out and os.path.exists(f"{d}/rg2.json") and json.load(open(f"{d}/rg2.json"))["PASS"] is True, out[-200:])
check("★★★ [R] G0 after every run: the frozen gate sources still carry their contract-approved shas (step1 278fdce6, step2 db7ab356) and v4_gate_common / the contract are byte-identical to what this section started with (the tests never wrote to them)",
      _sha(f"{HERE}/v4_gate_step1.py") == _FROZEN_SHA["v4_gate_step1.py"] and _sha(f"{HERE}/v4_gate_step2.py") == _FROZEN_SHA["v4_gate_step2.py"] and _sha(f"{HERE}/v4_gate_common.py") == _COMMON_SHA and _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json") == _CON_SHA)

# ── [S] INDEPENDENT REVIEW B-R1 / B-R3 / B-R4 / R5 (2026-09-12 W7; codex_batch_incident_review_2026-09-12/retrain/RESULT.md; PREREG_v4_gates_monthly AMENDMENT 1):
#        B-R1 every driver stage verifies its prerequisites (bound to this contract/root/inputs) BEFORE guard/dispatch — the graph is code, not file order;
#        B-R3 the month contract is isolated from the parent shell (keys must be lines of the file; unset before sourcing) and the data stage runs its
#        subprocesses under env -i with every variable they read set explicitly (CLIP: DLWT_RAW_PATCH= empty); B-R4 NONE is bound to the builder identity and
#        every new-tail anchor must pass the pre-registered quality floor; R5 the five legacy chains are sealed behind V4_LEGACY_OK=1 ──
print("\n[S] researcher B-R1 (stage prerequisites), B-R3 (contract isolation + clean data env), B-R4 (NONE builder identity + tail quality), R5 (legacy seal)")
_LEGACY = ("chain_v4_data.sh", "chain_v4_gpu3.sh", "chain_v4s_gpu.sh", "chain_king_e.sh", "chain_v4_post_export.sh")
_PRODUCER_SKIP = ("v4_gate_common.py", "-", "v4_months.py")
def _producers(calls): return [os.path.basename(c["argv"][0]) for c in calls if c["argv"] and os.path.basename(c["argv"][0]) not in _PRODUCER_SKIP and c["argv"][0] != "-c"]
with tempfile.TemporaryDirectory() as d:
    # ── R5 ──
    for _f in _LEGACY:
        _src = open(f"{HERE}/{_f}").read().splitlines(); _gi = next(i for i, l in enumerate(_src) if "V4_LEGACY_OK" in l)
        check(f"★★ [S] R5 {_f}: the V4_LEGACY_OK guard is the FIRST action line (line {_gi + 1}, exit 64); everything above it is comment/blank", all(l.startswith("#") or not l.strip() for l in _src[:_gi]) and "exit 64" in _src[_gi], _gi + 1)
        _cw = f"{d}/legacy_{_f}"; os.makedirs(f"{_cw}/cwd"); _e = {k: v for k, v in os.environ.items() if k != "V4_LEGACY_OK"}
        open(f"{_cw}/{_f}", "w").write(open(f"{HERE}/{_f}").read().replace("/workspace", f"{_cw}/ws"))   # PATH-TRANSLATED copy (E-0912-B safety): even a broken guard could only write under the temp root, never into September's /workspace
        p = subprocess.run(["bash", f"{_cw}/{_f}"], capture_output=True, text=True, env=_e, cwd=f"{_cw}/cwd", timeout=60)
        check(f"★★★ [S] R5 bare `bash {_f}` (translated copy) ⇒ rc 64, LEGACY_REFUSED on stderr, NOTHING written in cwd or the translated root (the September-only chain is physically sealed, not just documented)", p.returncode == 64 and "LEGACY_REFUSED" in p.stderr and os.listdir(f"{_cw}/cwd") == [] and not os.path.exists(f"{_cw}/ws"), (p.returncode, p.stderr[-100:], os.listdir(_cw)))
    p = subprocess.run(["bash", f"{d}/legacy_chain_v4_data.sh/chain_v4_data.sh"], capture_output=True, text=True, env=dict(os.environ, V4_LEGACY_OK="1"), cwd=f"{d}/legacy_chain_v4_data.sh/cwd", timeout=60)
    check("★★ [S] R5 with V4_LEGACY_OK=1 the guard opens: the translated chain_v4_data.sh proceeds past it (rc ≠ 64, no LEGACY_REFUSED) and fails on its (translated, nonexistent) paths instead — the [J]/[K] harness runs the guarded chains for real with V4_LEGACY_OK=1", p.returncode != 64 and "LEGACY_REFUSED" not in p.stderr, (p.returncode, p.stderr[-120:]))
    check("★ [S] R5 the archived snapshots (.rN_<sha8>.sh) are untouched by the seal (判决装置与结论同寿命)", not any("V4_LEGACY_OK" in open(f"{HERE}/{f}").read() for f in os.listdir(HERE) if _re.search(r"\.r[0-4]_[0-9a-f]{8}\.sh$", f)))
    # ── B-R3: the contract is a FILE, not the environment ──
    _lines = open(f"{HERE}/v4_month_2026-09.env").read().splitlines(); open(f"{d}/noseeds.env", "w").write("\n".join(l for l in _lines if not l.startswith("SEEDS=")) + "\n")
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/noseeds.env; echo rc=$? SEEDS=$SEEDS", {"L": "/dev/null", "SEEDS": "42"})
    check("★★★ [S] B-R3 (researcher W3_omitted_SEEDS_inherited_ACCEPTED, was rc 0): SEEDS deleted from the file while SEEDS=42 is in the parent shell ⇒ rc 4 FAIL_month_env_key_missing_SEEDS — a key must be a LINE OF THE FILE", rc == 4 and "FAIL_month_env_key_missing_SEEDS" in out and "not a line of the file" in out, out[-200:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; load_month_env {HERE}/v4_month_2026-09.env >/dev/null; echo rc=$? R=$R DLW_RAW=$DLW_RAW PREV_F8=$PREV_F8", {"L": "/dev/null", "R": "/tmp/inherited_junk", "DLW_RAW": "/tmp/junk_dlw", "PREV_F8": "/tmp/junk_prev"})
    check("★★★ [S] B-R3 inherited R / DLW_RAW / PREV_F8 in the parent shell are UNSET before sourcing ⇒ the file's values win (rc 0)", rc == 0 and "R=/workspace/review_scratch " in out and "DLW_RAW=/workspace/dlw_v4raw" in out and "PREV_F8=/workspace/f8_hf2" in out, out[-200:])
    _keys46 = open(f"{HERE}/chain_lib.sh").read().split('V4_MONTH_KEYS="', 1)[1].split('"', 1)[0].split()
    check("★★ [S] B-R4 contract key PREV_CLAMP_BUILDER_SHA256 registered (46 keys); the September contract pins the builder sha the frozen STEP2 gate was verified with (b9f9c728… == the archived preflight device_sha256 == the file in the device dir)",
          "PREV_CLAMP_BUILDER_SHA256" in _keys46 and len(_keys46) == 46 and "PREV_CLAMP_BUILDER_SHA256=b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac" in open(f"{HERE}/v4_month_2026-09.env").read()
          and json.load(open(f"{HERE}/receipts/monthly_chain_2026-09-12/pod2_root/preflight.json"))["device_sha256"]["pod_fea_ext_clamp.py"] == "b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac" == _sha(f"{HERE}/pod_fea_ext_clamp.py"), (len(_keys46), _sha(f"{HERE}/pod_fea_ext_clamp.py")[:12]))
    # ── B-R1 / B-R3 on the DRIVER with a fail-closed mock interpreter (the researcher's shape: logs every call, delegates only v4_gate_common / heredocs / -c to the real interpreter, exits 77 otherwise) ──
    _MOCK = f"{d}/mock_python"; _MLOG = f"{d}/mock_calls.jsonl"
    open(_MOCK, "w").write(f'''#!{PY}
import json, os, sys, subprocess
LOG = {_MLOG!r}; a = sys.argv[1:]; n = os.path.basename(a[0]) if a else ""
open(LOG, "a").write(json.dumps({{"argv": a, "env": {{k: os.environ.get(k) for k in ("F10_DLW", "F10_OUT", "BEST_EP_FIX", "SEED", "DLWT_RAW_PATCH", "DLWT_CACHE", "DLWT_OUT", "F171_OUT", "F8_OUT", "FEA_OUT", "W7_CANARY", "PATH")}}}}) + "\\n")
if n in ("v4_gate_common.py", "-", "v4_months.py") or (a and a[0] == "-c"): sys.exit(subprocess.call([{PY!r}, "-B"] + a, stdin=sys.stdin))
def w(p, b=b"x"): os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b)
if n == "cache_coverage_gate_v2.py": sys.exit(0)
if n == "pod_dlw_targets_raw.py": w(os.environ["DLWT_OUT"] + "/data/dlw_targets.npz", ("raw" if os.environ.get("DLWT_RAW_PATCH") else "clip").encode()); sys.exit(0)
if n == "b82.py": w(os.environ["F171_OUT"] + "/data/dlw_fea82.npz"); sys.exit(0)
if n == "b89.py": w(os.environ["F8_OUT"] + "/data/f8_fea89.npz"); sys.exit(0)
if n == "pod_fea_ext_clamp.py": w(os.environ["FEA_OUT"]); w(os.environ["META_OUT"]); sys.exit(0)
print("MOCK_INTERCEPT_NO_BUSINESS_CODE " + n); sys.exit(77)
'''); os.chmod(_MOCK, 0o755)
    def _mock_env(dd):
        _r, _e = _fake_root(dd); _em = f"{dd}.env"; _txt = open(_e).read(); assert f"PY={PY}\n" in _txt; open(_em, "w").write(_txt.replace(f"PY={PY}\n", f"PY={_MOCK}\n")); return _r, _em
    def _drv(stages, envf, dryrun=False):
        open(_MLOG, "w").close(); e = {"V4_STAGES": stages, "W7_CANARY": "leak", "DLWT_RAW_PATCH": "stale-inherited-patch"}
        if dryrun: e["V4_DRYRUN"] = "1"
        rc, out = _bash(f"bash {HERE}/chain_v4_monthly.sh {envf}", e); calls = [json.loads(l) for l in open(_MLOG) if l.strip()]; return rc, out, calls
    _bad = {}
    for _st in ("cache", "data", "gates", "king", "legs", "mwf", "refit", "arms", "judge", "export"):
        _r2, _e2 = _mock_env(f"{d}/empty_{_st}"); rc, out, calls = _drv(_st, _e2)
        if not (rc == 3 and f"FAIL_{_st}_prereq_preflight" in out and not _producers(calls)): _bad[_st] = (rc, out[-160:], _producers(calls))
    check("★★★ [S] B-R1 (researcher W3_refit_subset_dispatches_without_upstream_receipts, was: refit dispatched): V4_STAGES=<stage> on a root with NO preflight receipt ⇒ each of the 10 stages dies FAIL_<stage>_prereq_preflight rc 3 and the interpreter receives NO producer/trainer/refit call", not _bad, _bad)
    _r3, _e3 = _mock_env(f"{d}/empty_refit_dry"); rc, out, calls = _drv("refit", _e3, dryrun=True)
    check("★★★ [S] B-R1 prerequisites are checked BEFORE the dryrun guard: V4_DRYRUN=1 V4_STAGES=refit on an empty root ⇒ FAIL_refit_prereq_preflight (not 'would launch'), rc 3, zero refit calls", rc == 3 and "FAIL_refit_prereq_preflight" in out and "would_launch" not in out and not any("pod_f10_refit_v4.py" in c["argv"][0] for c in calls if c["argv"]), (rc, out[-160:]))
    _rP, _eP = _mock_env(f"{d}/pf"); rc, out, calls = _drv("preflight", _eP)
    check("★★ [S] B-R1 setup: preflight alone on the fake root PASSES under the mock interpreter (rc 0; preflight.json PASS bound to this contract's sha; deps_preflight_device.json pinned)",
          rc == 0 and json.load(open(f"{_rP}/v4_gates/preflight.json"))["PASS"] is True and json.load(open(f"{_rP}/v4_gates/preflight.json"))["month_env_sha256"] == _sha(_eP) and os.path.exists(f"{_rP}/v4_gates/deps_preflight_device.json"), out[-200:])
    _exp = {"data": "FAIL_data_prereq_cache_coverage", "gates": "FAIL_gates_prereq_f10_gate_RAW", "king": "FAIL_king_prereq_step2", "legs": "FAIL_legs_prereq_step1", "mwf": "FAIL_mwf_prereq_step1", "refit": "FAIL_refit_prereq_step1", "arms": "FAIL_arms_prereq_step2", "judge": "FAIL_judge_prereq_build_dev", "export": "FAIL_export_prereq_judge"}
    _bad = {}
    for _st, _want in _exp.items():
        rc, out, calls = _drv(_st, _eP)
        if not (rc == 3 and _want in out and not _producers(calls)): _bad[_st] = (rc, out[-160:], _producers(calls))
    check("★★★ [S] B-R1 dependency GRAPH: with preflight PASS and nothing else, each stage stops at its NEXT missing prerequisite BY NAME (data→cache_coverage, gates→f10_gate_RAW, king/arms→step2, legs/mwf/refit→step1, judge→build_dev, export→judge), rc 3, no producer called", not _bad, _bad)
    open(f"{d}/other.env", "w").write(open(_eP).read() + "# a different contract file (same keys, extra comment => different sha)\n")
    rc, out, calls = _drv("cache", f"{d}/other.env")
    check("★★★ [S] B-R1 the preflight receipt is bound to the CONTRACT: the same root run under a contract file with a different sha ⇒ FAIL_cache_prereq_preflight ('bound to contract sha … this run's contract is …')", rc == 3 and "FAIL_cache_prereq_preflight" in out and not _producers(calls), out[-200:])
    rc, out, calls = _drv("cache", _eP)
    check("★★ [S] B-R1 positive: with the preflight prerequisite satisfied the cache stage DISPATCHES (mock cache gate rc 0 ⇒ cache_coverage.json PASS, rc 0)", rc == 0 and json.load(open(f"{_rP}/v4_gates/cache_coverage.json"))["PASS"] is True and "cache_coverage_gate_v2.py" in _producers(calls), (rc, out[-160:]))
    rc, out, calls = _drv("data", _eP); _tg = [c for c in calls if c["argv"] and os.path.basename(c["argv"][0]) == "pod_dlw_targets_raw.py"]; _prod = [c for c in calls if c["argv"] and os.path.basename(c["argv"][0]) in ("pod_dlw_targets_raw.py", "b82.py", "b89.py", "pod_fea_ext_clamp.py")]
    check("★★★ [S] B-R3 (researcher W3_CLIP_command_inherits_ambient_RAW_PATCH, was 'stale-inherited-patch'): data stage rc 0 under the mock; the RAW build gets DLWT_RAW_PATCH=<contract RAW_PATCH>, the CLIP build gets DLWT_RAW_PATCH='' (explicitly empty) — the parent's DLWT_RAW_PATCH=stale-inherited-patch reaches neither",
          rc == 0 and len(_tg) == 2 and _tg[0]["env"]["DLWT_RAW_PATCH"] == f"{_rP}/raw_patch.npz" and _tg[1]["env"]["DLWT_RAW_PATCH"] == "" and _tg[0]["env"]["DLWT_OUT"] == f"{_rP}/dlw_v4raw" and _tg[1]["env"]["DLWT_OUT"] == f"{_rP}/dlw_hf3", (rc, [(c["env"]["DLWT_OUT"], c["env"]["DLWT_RAW_PATCH"]) for c in _tg], out[-160:]))
    check("★★★ [S] B-R3 env -i: none of the 5 data subprocesses sees the parent's canary W7_CANARY=leak (allowlist only: PATH kept), all 5 called in order, DATA_DONE written",
          len(_prod) == 5 and all(c["env"]["W7_CANARY"] is None and c["env"]["PATH"] for c in _prod) and [os.path.basename(c["argv"][0]) for c in _prod] == ["pod_dlw_targets_raw.py", "pod_dlw_targets_raw.py", "b82.py", "b89.py", "pod_fea_ext_clamp.py"] and "CHAIN_V4_MONTHLY_DATA_DONE" in open(f"{_rP}/chain_v4_monthly.log").read(), [os.path.basename(c["argv"][0]) for c in _prod])
    check("★★ [S] B-R3 the CLIP targets file was built WITHOUT a patch and the RAW one WITH (the mock wrote what it was told)", open(f"{_rP}/dlw_hf3/data/dlw_targets.npz", "rb").read() == b"clip" and open(f"{_rP}/dlw_v4raw/data/dlw_targets.npz", "rb").read() == b"raw")
    rc, out, calls = _drv("gates", _eP)
    check("★★★ [S] B-R1 positive control of the graph: after data, V4_STAGES=gates finds its prerequisites (F10_GATE receipts, identical targets/fea89) and DISPATCHES the gate programs (mock ⇒ rc 77, no receipt) ⇒ stops at FAIL_gate_require_step1, rc 3", rc == 3 and "v4_gate_step1.py" in _producers(calls) and "FAIL_gate_require_step1" in out and "_prereq_" not in out.split("gates ran")[-1], (rc, _producers(calls), out[-160:]))
    open(f"{_rP}/dlw_v4raw/data/dlw_targets.npz", "wb").write(b"raw-changed-after-data-stage")
    rc, out, calls = _drv("gates", _eP)
    check("★★★ [S] B-R1 MUTATION: RAW targets changed after the data stage ⇒ gates stops at FAIL_gates_prereq_f10_gate_raw_targets (identity vs the F10_GATE receipt), no gate program invoked", rc == 3 and "FAIL_gates_prereq_f10_gate_raw_targets" in out and not _producers(calls), (rc, out[-160:]))
    # ── B-R1 helpers on synthetic receipts: pinned-input identity, refit sidecar binding ──
    open(f"{d}/a.bin", "wb").write(b"A"); open(f"{d}/b.bin", "wb").write(b"B"); json.dump({"stage": "x", "deps_sha256": {f"{d}/a.bin": _sha(f"{d}/a.bin"), f"{d}/b.bin": _sha(f"{d}/b.bin")}}, open(f"{d}/deps.json", "w"))
    _pe = {"L": "/dev/null", "PY": PY, "R": d}
    rc, out = _bash(f". {HERE}/chain_lib.sh; prereq_deps_identity refit mwf_inputs {d}/deps.json {d}/a.bin {d}/b.bin; echo rc=$?", _pe)
    check("★★ [S] B-R1 prereq_deps_identity: pinned files unchanged ⇒ ok (rc 0)", "rc=0" in out and "FAIL" not in out, out[-150:])
    open(f"{d}/b.bin", "wb").write(b"B2"); rc, out = _bash(f". {HERE}/chain_lib.sh; prereq_deps_identity refit mwf_inputs {d}/deps.json {d}/a.bin {d}/b.bin; echo rc=$?", _pe)
    check("★★★ [S] B-R1 prereq_deps_identity: an input changed after the mwf dispatch pinned it ⇒ FAIL_refit_prereq_mwf_inputs rc 3", rc == 3 and "FAIL_refit_prereq_mwf_inputs" in out, out[-150:])
    rc, out = _bash(f". {HERE}/chain_lib.sh; prereq_deps_identity refit mwf_inputs {d}/deps.json {d}/a.bin {d}/never_pinned.bin; echo rc=$?", _pe)
    check("★★ [S] B-R1 prereq_deps_identity: a file the dispatch never pinned ⇒ refused ('not pinned')", rc == 3 and "not pinned" in out, out[-150:])
    for _p in ("dlw/data/dlw_targets.npz", "dlw/data/dlw_fea82.npz", "f8/data/f8_fea89.npz", "f8/data/f10v2_legs.npz", "f8/models/f10_live_s42.pt"): os.makedirs(os.path.dirname(f"{d}/{_p}"), exist_ok=True); open(f"{d}/{_p}", "wb").write(_p.encode())
    _ins = {"targets": f"{d}/dlw/data/dlw_targets.npz", "fea82": f"{d}/dlw/data/dlw_fea82.npz", "fea89": f"{d}/f8/data/f8_fea89.npz", "legs": f"{d}/f8/data/f10v2_legs.npz"}
    # round 3: the fixture now models EVERY field pod_f10_refit_v4.py writes (seed / best_ep_kept / env_given.SEED / self_sha256) — the round-2 fixture omitted three of them and still passed
    _sc = {"seed": 42, "best_ep_rule": "fix7", "best_ep_kept": 7, "env_given": {"F10_DLW": f"{d}/dlw", "F10_OUT": f"{d}/f8", "SEED": "42", "BEST_EP_FIX": "7"}, "inputs": _ins, "inputs_sha256": {k: _sha(v) for k, v in _ins.items()},
           "pt": f"{d}/f8/models/f10_live_s42.pt", "pt_sha256": _sha(f"{d}/f8/models/f10_live_s42.pt"), "self_sha256": _sha(f"{HERE}/pod_f10_refit_v4.py")}
    _scp = f"{d}/f8/models/f10_live_s42.json"; json.dump(_sc, open(_scp, "w")); _SIDE = f"prereq_refit_sidecar arms refit_s42 {_scp} {d}/dlw {d}/f8 42 {HERE}/pod_f10_refit_v4.py"
    rc, out = _bash(f". {HERE}/chain_lib.sh; {_SIDE}; echo rc=$?", _pe)
    check("★★ [S] B-R1 prereq_refit_sidecar: fix7 + env_given bound to this month's dirs + inputs/weights identical ⇒ ok (rc 0)", "rc=0" in out and "FAIL" not in out, out[-150:])
    def _restore():
        open(f"{d}/f8/data/f10v2_legs.npz", "wb").write(b"f8/data/f10v2_legs.npz"); open(f"{d}/f8/models/f10_live_s42.pt", "wb").write(b"f8/models/f10_live_s42.pt")
    for _name, _mut in (("argmax epoch rule", lambda m: m.update(best_ep_rule="argmax")), ("F10_DLW of ANOTHER month (dlw_ext)", lambda m: m["env_given"].update(F10_DLW="/workspace/dlw_ext")),
                        ("legs changed after refit", lambda m: open(f"{d}/f8/data/f10v2_legs.npz", "wb").write(b"changed legs")), ("weights swapped after refit", lambda m: open(f"{d}/f8/models/f10_live_s42.pt", "wb").write(b"other weights"))):
        m = json.loads(json.dumps(_sc)); _mut(m); json.dump(m, open(_scp, "w")); rc, out = _bash(f". {HERE}/chain_lib.sh; {_SIDE}; echo rc=$?", _pe); _restore()
        check(f"★★★ [S] B-R1 prereq_refit_sidecar MUTATION {_name} ⇒ FAIL_arms_prereq_refit_s42 rc 3", rc == 3 and "FAIL_arms_prereq_refit_s42" in out, out[-150:])
    # ── B-R4 on the [R] fixtures: NONE bound to the builder identity; new-tail quality floor 0.90 ──
    _bX = _base(1, _NA_NEW); _write_month(f"{d}/X1", _bX, _NA_NEW, "new"); _write_month(f"{d}/X0", _bX, _NA_REF, "ref")
    rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/n0.json", PREV_KING_FEA_UNCLAMPED="NONE"))
    check("★★★ [S] B-R4 (researcher W7_NONE_positive_without_any_builder_or_preflight_identity, was PASS): NONE with NO builder pin and NO month root ⇒ REFUSED clamp_builder_identity naming PREV_CLAMP_BUILDER_SHA256 and R; rc 3; PASS=false",
          rc == 3 and r2 and r2["PASS"] is False and "clamp_builder_identity" in r2["REFUSED"] and any("PREV_CLAMP_BUILDER_SHA256" in w for w in r2["REFUSED"]["clamp_builder_identity"]["why"]) and any(w.startswith("R unset") for w in r2["REFUSED"]["clamp_builder_identity"]["why"]), (rc, r2 and r2.get("REFUSED")))
    rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/n1.json", f"{d}/Rn1", pin="ab" * 32))
    check("★★★ [S] B-R4 NONE with a contract pin that is NOT the builder on disk ⇒ REFUSED ('on-disk builder … != contract pin'); the receipt records the compared shas", rc == 3 and r2 and any("on-disk builder" in w for w in r2["REFUSED"]["clamp_builder_identity"]["why"]) and r2["REFUSED"]["clamp_builder_identity"]["device_file_sha256"] == _sha(f"{HERE}/pod_fea_ext_clamp.py"), r2 and r2.get("REFUSED"))
    rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/n2.json", f"{d}/Rn2", preflight_pin="cd" * 32))
    check("★★★ [S] B-R4 NONE where THIS month's preflight pinned a different builder than the contract ⇒ REFUSED ('preflight-pinned builder … != contract pin')", rc == 3 and r2 and any("preflight-pinned builder" in w for w in r2["REFUSED"]["clamp_builder_identity"]["why"]), r2 and r2.get("REFUSED"))
    _e4 = _none_env(f"{d}/X1", f"{d}/X0", f"{d}/n3.json", f"{d}/Rn3"); os.remove(f"{d}/Rn3/v4_gates/deps_preflight_device.json"); rc, out, r2 = _g("v4_gate_step2_m.py", _e4)
    check("★★ [S] B-R4 NONE without this month's deps_preflight_device.json ⇒ REFUSED ('preflight deps receipt missing')", rc == 3 and r2 and any("preflight deps receipt missing" in w for w in r2["REFUSED"]["clamp_builder_identity"]["why"]), r2 and r2.get("REFUSED"))
    _F = np.load(f"{d}/X1/king_fea.npy"); _orig = _F.copy(); _F[200:] = np.nan; np.save(f"{d}/X1/king_fea.npy", _F)
    rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/t0.json", f"{d}/Rt0"))
    check("★★★ [S] B-R4 (researcher W7_entire_new_tail_NaN_still_PASS_boundary, was PASS): the 30 new-tail anchors all NaN ⇒ tail_quality.ok false (member_finite_frac_min 0.0 < floor 0.90) ⇒ PASS false rc 3 — the tail is exempt from the reference comparison, not from quality",
          rc == 3 and r2 and r2["PASS"] is False and r2["tail_quality"]["ok"] is False and r2["tail_quality"]["member_finite_frac_min"] == 0.0 and r2["tail_quality"]["n_tail_anchors"] == 30 and r2["tail_quality"]["floor"] == 0.90 and r2["features"]["v4_vs_clamp"]["outside"] == 0, (rc, r2 and r2.get("tail_quality")))
    _F = _orig.copy(); _F[200:, :, 0] = np.nan; np.save(f"{d}/X1/king_fea.npy", _F); rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/t1.json", f"{d}/Rt1"))
    check("★★ [S] B-R4 tail with 1 of 10 feature columns NaN (member finite fraction 0.90) ⇒ AT the floor ⇒ ok, PASS", rc == 0 and r2 and r2["tail_quality"]["ok"] is True and abs(r2["tail_quality"]["member_finite_frac_min"] - 0.9) < 1e-9, r2 and r2.get("tail_quality"))
    _F = _orig.copy(); _F[200:, :, :2] = np.nan; np.save(f"{d}/X1/king_fea.npy", _F); rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/t2.json", f"{d}/Rt2"))
    check("★★★ [S] B-R4 tail with 2 of 10 columns NaN (0.80 < 0.90) ⇒ FAIL", rc == 3 and r2 and r2["PASS"] is False and r2["tail_quality"]["ok"] is False and abs(r2["tail_quality"]["member_finite_frac_min"] - 0.8) < 1e-9, r2 and r2.get("tail_quality"))
    _F = _orig.copy(); _F[205] = np.nan; np.save(f"{d}/X1/king_fea.npy", _F); rc, out, r2 = _g("v4_gate_step2_m.py", _none_env(f"{d}/X1", f"{d}/X0", f"{d}/t2b.json", f"{d}/Rt2b"))
    check("★★★ [S] B-R4 a SINGLE dead tail anchor among 30 good ones ⇒ FAIL (the floor is per anchor, min not mean)", rc == 3 and r2 and r2["tail_quality"]["ok"] is False and r2["tail_quality"]["member_finite_frac_min"] == 0.0 and r2["tail_quality"]["member_finite_frac_median"] == 1.0, r2 and r2.get("tail_quality"))
    np.save(f"{d}/X1/king_fea.npy", _orig); rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1", f"{d}/X0", f"{d}/t3.json"))
    check("★★ [S] B-R4 the tail quality gate also runs on the unclamped-reference path (positive fixture: 30 tail anchors, valid member index, min 1.0, ok) and is part of PASS", rc == 0 and r2 and r2["PASS"] is True and r2["tail_quality"] == {"n_tail_anchors": 30, "member_index_ok": True, "member_finite_frac_min": 1.0, "member_finite_frac_median": 1.0, "n_members_min": 6, "floor": 0.9, "ok": True}, r2 and r2.get("tail_quality"))
    _write_month(f"{d}/X1s", _bX, _NA_REF, "new"); rc, out, r2 = _g("v4_gate_step2_m.py", _env2(f"{d}/X1s", f"{d}/X0", f"{d}/t4.json"))
    check("★★ [S] B-R4 no tail ⇒ no tail_quality field (the September-style field set of [R] G3(i) is unchanged)", rc == 0 and r2 and "tail_quality" not in r2 and _keys(r2) == _keys(_ARCH2), r2 and sorted(_keys(r2) ^ _keys(_ARCH2))[:4])
print("\n[T] round 3 (REVIEW_code_and_research_2026-09-13 §3.D): D1 refit-sidecar identity, D2 new-tail member index, D3 contract value binding — every cell runs the ARCHIVED pre-round-3 source (RED) and the current one (GREEN) in the same breath")
_PRE_LIB = f"{HERE}/chain_lib.r1_3cd82956.sh"; _PRE_S2 = f"{HERE}/v4_gate_step2_m.r1_0fe5ec55.py"
check("★★★ [T] the pre-round-3 sources are archived beside the current ones and ARE the bytes the reviewer probed (chain_lib 3cd82956…, v4_gate_step2_m 0fe5ec55… — the shas in RESULT.md's key-source table); the RED control outlives the verdict",
      _sha(_PRE_LIB).startswith("3cd82956") and _sha(_PRE_S2).startswith("0fe5ec55"), (_sha(_PRE_LIB)[:8], _sha(_PRE_S2)[:8]))
with tempfile.TemporaryDirectory() as d:
    # ── D1: prereq_refit_sidecar must prove WHAT the JSON is about, not that a JSON exists ──────────────────────────────────────────────────
    for _r in ("dlw/data", "f8/data", "f8/models", "other/dlw/data", "other/f8/data"): os.makedirs(f"{d}/{_r}", exist_ok=True)
    _IN = {"targets": f"{d}/dlw/data/dlw_targets.npz", "fea82": f"{d}/dlw/data/dlw_fea82.npz", "fea89": f"{d}/f8/data/f8_fea89.npz", "legs": f"{d}/f8/data/f10v2_legs.npz"}
    for _k, _v in _IN.items(): open(_v, "wb").write(_k.encode())
    _PTF = lambda s: f"{d}/f8/models/f10_live_s{s}.pt"
    for _s in (42, 2027): open(_PTF(_s), "wb").write(f"weights s{_s}".encode())
    _REFIT_SRC = f"{HERE}/pod_f10_refit_v4.py"; _REFIT_SHA = _sha(_REFIT_SRC); _SAYL = f"{d}/say.log"
    def _mk(seed=42, **over):   # a COMPLETE sidecar in exactly the shape the refit writer emits
        m = {"seed": seed, "best_ep_rule": "fix7", "best_ep_kept": 7, "env_given": {"F10_DLW": f"{d}/dlw", "F10_OUT": f"{d}/f8", "SEED": str(seed), "BEST_EP_FIX": "7"},
             "inputs": dict(_IN), "inputs_sha256": {k: _sha(v) for k, v in _IN.items()}, "pt": _PTF(seed), "pt_sha256": _sha(_PTF(seed)), "self_sha256": _REFIT_SHA}
        m.update(over); return m
    def _side(lib, obj, slot=42, seed=42, bound=True, src=None):   # the helper only HASHES `src`; the canary cell below proves it is never executed
        _p = f"{d}/f8/models/f10_live_s{slot}.json"; json.dump(obj, open(_p, "w")); open(_SAYL, "w").close()
        _a = (" %d %s" % (seed, src or _REFIT_SRC)) if bound else ""
        rc, out = _bash(f". {lib}; prereq_refit_sidecar arms refit_s{seed} {_p} {d}/dlw {d}/f8" + _a + "; echo rc=$?", {"L": _SAYL, "PY": PY, "R": d})
        return rc, out + open(_SAYL).read()   # the ok-message goes through `say` to $L, only refusals reach stderr
    _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _mk())
    check("★★★ [T] D1 POSITIVE: a complete, canonical seed-42 sidecar (four inputs at this month's paths, weights at f10_live_s42.pt, all shas current) ⇒ rc 0, and the chain log says the BYTES were verified, not that a JSON was found",
          _rc_n == 0 and "4 inputs + weights verified against the bytes on disk" in _o_n and f"written by pod_f10_refit_v4.py {_REFIT_SHA[:12]}" in _o_n and "FAIL" not in _o_n, (_rc_n, _o_n[-200:]))
    _CAN = f"{d}/canary_src.py"; _CANMARK = f"{d}/CANARY_WAS_EXECUTED"
    open(_CAN, "w").write(f"open({_CANMARK!r}, 'w').write('executed')\n")
    _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _mk(), src=_CAN)
    check("★★★ [T] D1 the refit source argument is HASHED, never RUN (interventional, not a reading of the code): point it at a script whose only statement writes a marker file ⇒ the helper refuses on the sha mismatch and the marker does NOT exist",
          _rc_n == 3 and "written by a different program" in _o_n and not os.path.exists(_CANMARK), (_rc_n, os.path.exists(_CANMARK), _o_n[-160:]))
    _keep42 = open(_PTF(42), "rb").read()
    _m = _mk(); _m.pop("pt_sha256"); open(_PTF(42), "wb").write(b"tampered weights")
    _rc_o, _o_o = _side(_PRE_LIB, _m, bound=False); _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _m)
    check("★★★ [T] D1(a) (researcher sidecar_changed_weights_missing_hash_ACCEPTED, rc 0): the weights changed AND the pt_sha256 key was deleted ⇒ pre-round-3 chain_lib ACCEPTS (rc 0 — `elif m.get('pt_sha256') and …` made an absent key a SKIP), round 3 REFUSES rc 3 naming it",
          _rc_o == 0 and _rc_n == 3 and "NO pt_sha256" in _o_n and "FAIL_arms_prereq_refit_s42" in _o_n, (_rc_o, _rc_n, _o_n[-200:]))
    open(_PTF(42), "wb").write(_keep42)
    _m = _mk(); _m["inputs"] = {"targets": _IN["targets"]}; _m["inputs_sha256"] = {"targets": _sha(_IN["targets"])}
    _rc_o, _o_o = _side(_PRE_LIB, _m, bound=False); _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _m)
    check("★★★ [T] D1(b) (researcher sidecar_omits_three_required_input_identities_ACCEPTED, rc 0): the four declared inputs shrunk to `targets` ⇒ pre-round-3 ACCEPTS (the loop walked whatever the sidecar listed), round 3 REFUSES and names fea82/fea89/legs",
          _rc_o == 0 and _rc_n == 3 and all(k in _o_n for k in ("fea82", "fea89", "legs")), (_rc_o, _rc_n, _o_n[-200:]))
    _rc_o, _o_o = _side(_PRE_LIB, _mk(seed=42), slot=2027, seed=2027, bound=False); _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _mk(seed=42), slot=2027, seed=2027)
    check("★★★ [T] D1(c) (researcher sidecar_seed42_submitted_for_seed2027_ACCEPTED, rc 0): a complete, internally consistent SEED-42 sidecar dropped into the seed-2027 slot ⇒ pre-round-3 ACCEPTS (it had no expected seed), round 3 REFUSES on all three seed carriers (seed, env_given.SEED, the .pt path)",
          _rc_o == 0 and _rc_n == 3 and "seed=42 != expected 2027" in _o_n and "env_given.SEED='42' != expected 2027" in _o_n and "f10_live_s2027.pt" in _o_n, (_rc_o, _rc_n, _o_n[-240:]))
    _OTH = {k: v.replace(f"{d}/", f"{d}/other/") for k, v in _IN.items()}
    for _k, _v in _OTH.items(): open(_v, "wb").write(open(_IN[_k], "rb").read())
    _m = _mk(); _m["inputs"] = _OTH; _m["inputs_sha256"] = {k: _sha(v) for k, v in _OTH.items()}
    _rc_o, _o_o = _side(_PRE_LIB, _m, bound=False); _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _m)
    check("★★★ [T] D1(d) EXPECTED PATHS: the four inputs are BYTE-IDENTICAL copies under another tree ⇒ pre-round-3 ACCEPTS (every recorded sha matches its file), round 3 REFUSES — 'four files whose shas match' is not 'this month's four artefacts'",
          _rc_o == 0 and _rc_n == 3 and all(f"input {k} path" in _o_n for k in ("targets", "fea82", "fea89", "legs")) and _o_n.count("!= this month's") >= 4, (_rc_o, _rc_n, _o_n.count("!= this month's"), _o_n[-200:]))
    _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _mk(self_sha256="ab" * 32))
    check("★★ [T] D1(e) beyond the four mandated checks (reviewer: 绑定实际生成 sidecar 的程序): a sidecar whose self_sha256 is not the refit source this driver dispatches ⇒ refused — the same rule require_gate already applies to gate receipts",
          _rc_n == 3 and "written by a different program" in _o_n, (_rc_n, _o_n[-160:]))
    _rc_n, _o_n = _side(f"{HERE}/chain_lib.sh", _mk(), bound=False)
    check("★★★ [T] D1(f) the helper FAILS CLOSED on its own arguments: called with the round-2 five-argument form (no expected seed, no refit source) ⇒ rc 3 'MANDATORY arguments', never a quieter check",
          _rc_n == 3 and "MANDATORY arguments" in _o_n and "FAIL_arms_prereq_refit_s42" in _o_n, (_rc_n, _o_n[-160:]))
    _DRV = open(f"{HERE}/chain_v4_monthly.sh").read()
    check("★★★ [T] D1 call site: chain_v4_monthly.sh has exactly one prereq_refit_sidecar call and it passes the loop seed $SD and $D/pod_f10_refit_v4.py (a helper that fails closed is only useful if the driver actually binds it)",
          _DRV.count("prereq_refit_sidecar") == 1 and 'prereq_refit_sidecar arms refit_s$SD "$F8/models/f10_live_s$SD.json" "$DLW_RAW" "$F8" "$SD" "$D/pod_f10_refit_v4.py"' in _DRV)
    _RF = open(f"{HERE}/pod_f10_refit_v4.py").read()
    check("★★★ [T] D1 no-drift: every key and path the gate now REQUIRES is one pod_f10_refit_v4.py actually writes (the four input roles, the {DLW}/{OUT} layout, models/f10_live_s{SEED}.pt, best_ep_kept, env_given.SEED, self_sha256) — a gate may not demand a field the writer never emits",
          all(f'"{k}"' in _RF for k in ("seed", "best_ep_rule", "best_ep_kept", "env_given", "inputs", "inputs_sha256", "self_sha256", "targets", "fea82", "fea89", "legs", "SEED"))
          and all(p in _RF for p in ('f"{DLW}/data/dlw_targets.npz"', 'f"{DLW}/data/dlw_fea82.npz"', 'f"{OUT}/data/f8_fea89.npz"', 'f"{OUT}/data/f10v2_legs.npz"', 'f"{OUT}/models/f10_live_s{SEED}.pt"'))
          and 'meta["pt"]' in _RF and 'meta["pt_sha256"]' in _RF)
    # ── D2: the new-tail member index is validated STRUCTURALLY FIRST, then the finite-fraction floor ───────────────────────────────────────
    _bT = _base(1, _NA_NEW); _write_month(f"{d}/T1", _bT, _NA_NEW, "new"); _write_month(f"{d}/T0", _bT, _NA_REF, "ref")
    _MFT = f"{d}/T1/king_meta.npz"; _MT = {k: v.copy() for k, v in np.load(_MFT, allow_pickle=True).items()}
    def _memb(val, out, script="v4_gate_step2_m.py"):   # replace ONE new-tail anchor's member index, run the gate, restore
        _mm = {k: v.copy() for k, v in _MT.items()}; _mm["members"][_NA_REF] = np.array(val, dtype=np.int64); np.savez(_MFT, **_mm)
        rc, _, r = _g(script, _none_env(f"{d}/T1", f"{d}/T0", f"{d}/{out}.json", f"{d}/R{out}")); np.savez(_MFT, **_MT); return rc, r
    _rc_o, _r_o = _memb([-1], "d2old", "v4_gate_step2_m.r1_0fe5ec55.py"); _rc_n, _r_n = _memb([-1], "d2new")
    check("★★★ [T] D2 (researcher tail_invalid_negative_member_index_ACCEPTED, PASS): one new-tail anchor's members = [-1] ⇒ pre-round-3 gate PASSes rc 0 (numpy read the LAST column and scored finite fraction 1.0), round 3 FAILs rc 3 with member_index_ok false and the range named — structure first, floor second",
          _rc_o == 0 and _r_o["PASS"] is True and _r_o["tail_quality"]["member_finite_frac_min"] == 1.0 and _rc_n == 3 and _r_n["PASS"] is False
          and _r_n["tail_quality"]["member_index_ok"] is False and "outside [0, 6)" in _r_n["tail_quality"]["member_index_bad"][0]["why"][0], (_rc_o, _rc_n, _r_n["tail_quality"]))
    _rc_o, _r_o = _memb([6], "d2hiold", "v4_gate_step2_m.r1_0fe5ec55.py"); _rc_n, _r_n = _memb([6], "d2hinew")
    check("★★★ [T] D2 out-of-range HIGH (members = [6], NW = 6): the pre-round-3 gate CRASHED on the subscript (rc 1, no receipt at all), round 3 writes a clean FAIL receipt rc 3 — an invalid index is never used as a subscript",
          _rc_o == 1 and _r_o is None and _rc_n == 3 and _r_n["PASS"] is False and _r_n["tail_quality"]["member_index_ok"] is False, (_rc_o, _rc_n, _r_n and _r_n["tail_quality"]))
    _rc_o, _r_o = _memb([0, 0, 1, 2, 3, 4], "d2dupold", "v4_gate_step2_m.r1_0fe5ec55.py"); _rc_n, _r_n = _memb([0, 0, 1, 2, 3, 4], "d2dupnew")
    check("★★★ [T] D2 DUPLICATE member (members = [0,0,1,2,3,4]): pre-round-3 PASSes (it counted symbol 0 twice and never noticed), round 3 FAILs naming '1 duplicate index(es)' — the count of members is not the count of symbols",
          _rc_o == 0 and _r_o["PASS"] is True and _rc_n == 3 and _r_n["PASS"] is False and "duplicate" in _r_n["tail_quality"]["member_index_bad"][0]["why"][0], (_rc_o, _rc_n, _r_n["tail_quality"]))
    _rc_n, _r_n = _memb([5, 4, 3, 2, 1, 0], "d2perm")
    check("★★★ [T] D2 POSITIVE: an unsorted but valid permutation [5,4,3,2,1,0] still PASSes (the rule is integer / in [0, NW) / unique — NOT sortedness, and NOT a particular membership)",
          _rc_n == 0 and _r_n["PASS"] is True and _r_n["tail_quality"]["member_index_ok"] is True and "member_index_bad" not in _r_n["tail_quality"], (_rc_n, _r_n["tail_quality"]))
    _rc_n, _r_n = _memb([], "d2empty")
    check("★★ [T] D2 the pre-existing zero-member rule is unchanged by the new structural rule (members = [] ⇒ FAIL via n_members_min 0, member_index_ok stays true — an empty index is well-formed, just empty)",
          _rc_n == 3 and _r_n["PASS"] is False and _r_n["tail_quality"]["n_members_min"] == 0 and _r_n["tail_quality"]["member_index_ok"] is True, (_rc_n, _r_n["tail_quality"]))
    # ── D3: a contract value may reference ONLY a contract key already defined in the same file ─────────────────────────────────────────────
    _SEP = open(f"{HERE}/v4_month_2026-09.env").read(); assert "\nSEEDS=42,2027\n" in _SEP
    open(f"{d}/ind.env", "w").write(_SEP.replace("\nSEEDS=42,2027\n", "\nSEEDS=$UNLISTED_SEEDS\n"))
    _rc_o, _o_o = _bash(f". {_PRE_LIB}; load_month_env {d}/ind.env >/dev/null; echo rc=$? SEEDS=$SEEDS", {"L": "/dev/null", "UNLISTED_SEEDS": "2027"})
    _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/ind.env", {"L": "/dev/null", "UNLISTED_SEEDS": "2027"})
    check("★★★ [T] D3 (researcher BR3_file_key_indirect_ambient_reference_ACCEPTED, rc 0 with SEEDS=2027): `SEEDS=$UNLISTED_SEEDS` is a LINE of the file but its VALUE comes from the parent shell ⇒ pre-round-3 loader accepts and takes 2027 (only CONTRACT keys were unset), round 3 refuses rc 4 and names the key",
          _rc_o == 0 and "SEEDS=2027" in _o_o and _rc_n == 4 and "$UNLISTED_SEEDS is not a contract key" in _o_n and "FAIL_month_env_unbound_reference_ind.env" in _o_n, (_rc_o, _o_o[-80:], _rc_n, _o_n[-200:]))
    _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {HERE}/v4_month_2026-09.env >/dev/null; echo rc=$? R=$R RAW_PATCH=$RAW_PATCH HC=$HC", {"L": "/dev/null", "R": "/tmp/inherited", "UNLISTED_SEEDS": "2027"})
    check("★★★ [T] D3 POSITIVE: the shipped September contract still loads (rc 0) and its 5 legitimate `$R/...` values still resolve — a blanket ban on `$` would have rejected both delivered contracts (September 5 values, October template 12), so the rule is the narrow one: a contract key, defined earlier in the same file",
          _rc_n == 0 and "R=/workspace/review_scratch " in _o_n and "RAW_PATCH=/workspace/review_scratch/raw_patch.npz" in _o_n and "HC=/workspace/review_scratch/health_check" in _o_n, (_rc_n, _o_n[-200:]))
    _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {HERE}/v4_month_2026-10.env.template >/dev/null; echo rc=$?", {"L": "/dev/null"})
    check("★★ [T] D3 POSITIVE: the October template's 12 `$R/...` values pass the same rule (the template is refused later, by preflight, for its TODO_ paths — not by the loader for its syntax)", _rc_n == 0, (_rc_n, _o_n[-200:]))
    open(f"{d}/fwd.env", "w").write("HC=$R/health_check\n" + _SEP.replace("\nHC=$R/health_check\n", "\n"))
    _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/fwd.env", {"L": "/dev/null", "R": "/tmp/inherited"})
    check("★★★ [T] D3 FORWARD reference: `HC=$R/...` placed BEFORE the R= line ⇒ rc 4 'referenced before it is defined' — otherwise the unset makes it expand to the empty string and HC silently becomes /health_check (non-empty, so the round-2 emptiness check would have passed it)",
          _rc_n == 4 and "referenced before it is defined" in _o_n, (_rc_n, _o_n[-200:]))
    for _nm, _val, _want in (("braced_foreign", "KING_DIR=${EVIL}/king", "$EVIL is not a contract key"), ("bare_dollar", "KING_DIR=/k$", "bare $ / command substitution")):
        open(f"{d}/{_nm}.env", "w").write(_SEP.replace("\nKING_DIR=$R/king_v4\n", f"\n{_val}\n"))
        _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/{_nm}.env", {"L": "/dev/null", "EVIL": "/tmp/pwn"})
        check(f"★★ [T] D3 {_nm}: `{_val}` ⇒ rc 4 naming it ({_want})", _rc_n == 4 and _want in _o_n and "FAIL_month_env_unbound_reference" in _o_n, (_rc_n, _o_n[-160:]))
    open(f"{d}/cmdsub.env", "w").write(_SEP.replace("\nKING_DIR=$R/king_v4\n", "\nKING_DIR=$(id -u)\n"))
    _rc_n, _o_n = _bash(f". {HERE}/chain_lib.sh; load_month_env {d}/cmdsub.env", {"L": "/dev/null"})
    check("★★ [T] D3 command substitution is still caught by the round-2 line grammar (rc 4 month_env_malformed), so the two layers do not depend on each other", _rc_n == 4 and "malformed" in _o_n, (_rc_n, _o_n[-160:]))
check("★★★ [S] G0 after every run: frozen gate sources, v4_gate_common and the contract byte-identical to what [R] started with",
      _sha(f"{HERE}/v4_gate_step1.py") == _FROZEN_SHA["v4_gate_step1.py"] and _sha(f"{HERE}/v4_gate_step2.py") == _FROZEN_SHA["v4_gate_step2.py"] and _sha(f"{HERE}/v4_gate_common.py") == _COMMON_SHA and _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json") == _CON_SHA)
check("★★★ [T] G0 the FOUR contract-frozen files are byte-identical after round 3 as well (STEP1 278fdce6, STEP2 db7ab356, the contract 1188267a, the v2 export gate d63f4ec3) — round 3 touched none of them",
      _sha(f"{HERE}/v4_gate_step1.py").startswith("278fdce6") and _sha(f"{HERE}/v4_gate_step2.py").startswith("db7ab356") and _sha(f"{HERE}/ELIGIBILITY_CONTRACT.json").startswith("1188267a") and _sha(f"{HERE}/v4e_gate_export_v2.py").startswith("d63f4ec3"),
      [_sha(f"{HERE}/{f}")[:8] for f in ("v4_gate_step1.py", "v4_gate_step2.py", "ELIGIBILITY_CONTRACT.json", "v4e_gate_export_v2.py")])

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
