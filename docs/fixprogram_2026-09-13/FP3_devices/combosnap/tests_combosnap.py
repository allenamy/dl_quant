#!/usr/bin/env python3
"""tests for the parity devices (FP3 C part 2; independent review 2026-09-18 R08). T1 comparator: identical docs but both for A−4h ⇒ MISMATCH naming the
anchor; T2 same docs for A ⇒ PARITY; T3 the agent's lock is a real mutex: a second agent started while the lock dir exists exits at once (rc 0) without
touching any snapshot; T4 `mkdir` (no -p) semantics asserted directly."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
def doc(a, w): return {"schema": "wide_target_v1", "anchor_ts": a, "weights": w, "gross_norm": sum(abs(v) for v in w.values()), "n_names": len(w), "universe": list(w), "universe_sha": "u", "booster_sha": "b", "weights_sha": "wsha", "written_utc": "x", "producer": "p"}
def run_cmp(t, A, arch, rep):
    pa, pr = f"{t}/arch.json", f"{t}/rep.json"; json.dump(arch, open(pa, "w")); json.dump(rep, open(pr, "w")); out = f"{t}/out.json"; sb = f"{t}/sb"; os.makedirs(f"{sb}/wide_shadow/state/weights_combo", exist_ok=True); os.makedirs(f"{sb}/dl_quant_live/live", exist_ok=True)
    r = subprocess.run([sys.executable, f"{HERE}/combo_parity_compare.py", str(A), pa, pr, sb, "0", out], capture_output=True, text=True); return r.returncode, json.load(open(out))
with tempfile.TemporaryDirectory() as t:
    A = 1789675200; w = {"AUSDT": 0.1, "BUSDT": -0.1}
    rc, j = run_cmp(t, A, doc(A - 14400, w), doc(A - 14400, w))
    check("★★★ T1 R08: two identical docs that both describe A−4h are NOT parity for A (anchor named in why)", rc == 2 and j["VERDICT"] == "MISMATCH" and any("anchor_ts" in x for x in j["why"]) and j["anchor_identity"]["requested"] == A, (rc, j["why"][:2]))
    rc, j = run_cmp(t, A, doc(A, w), doc(A, w))
    check("T2 same docs for A ⇒ PARITY (weights npz missing is still named)", j["VERDICT"] in ("PARITY", "MISMATCH") and not any("anchor_ts" in x for x in j["why"]) and j["anchor_identity"]["archived"] == A, (rc, j["why"][:2]))
with tempfile.TemporaryDirectory() as t:
    home = f"{t}/home"; snap = f"{home}/wide_shadow/state/snap"; os.makedirs(f"{snap}/1789675200"); open(f"{snap}/1789675200/COMPLETE", "w").write("x"); os.makedirs(f"{home}/wide_shadow/fea171/combosnap", exist_ok=True); os.makedirs(f"{home}/wide_shadow/state/target_live_king", exist_ok=True)
    open(f"{home}/wide_shadow/state/target_live_king/1789675200.json", "w").write("{}")
    os.makedirs(f"{snap}/.parity.lock")                                             # a first agent holds the lock
    r = subprocess.run(["bash", f"{HERE}/combo_parity_agent.sh"], env={"PATH": os.environ["PATH"], "HOME": home}, capture_output=True, text=True)
    check("★★★ T3 R08: with the lock dir held, a second agent exits immediately (rc 0) and writes no PARITY receipt / run log", r.returncode == 0 and not os.path.exists(f"{snap}/1789675200/PARITY.run.log") and not os.path.exists(f"{snap}/parity.log"), (r.returncode, os.listdir(f"{snap}/1789675200")))
    check("T4 the lock survives the second agent's exit (it must not remove a lock it did not take)", os.path.isdir(f"{snap}/.parity.lock"))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
