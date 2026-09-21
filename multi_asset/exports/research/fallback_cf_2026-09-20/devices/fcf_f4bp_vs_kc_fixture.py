#!/usr/bin/env python3
"""fcf_f4bp_vs_kc_fixture.py — RED-CAPABILITY CONTROL for the repaired `fcf_f4bp_vs_kc.py` (round-7 review FB-01).

WHY THIS EXISTS. A control that compares a field with itself passes on every input, including inputs on which the
property it claims to test is false. The withdrawn version of `fcf_f4bp_vs_kc.py` did exactly that. The only thing
that distinguishes the repaired device from the withdrawn one is that the repaired one CAN go red, so that has to be
demonstrated on an input where the answer is known independently — and the demonstration is worthless unless the
baseline is first asserted GREEN (a red-capability check on an already-red baseline is vacuous: see
`red_capability_check_is_vacuous_when_baseline_is_red`).

ORDER IS PART OF THE TEST, AND IT IS THE PUBLISHED ORDER:
  1. GREEN baseline — two independently written sources whose seats really do agree. Device must print
     `VERDICT=PASS`, exit 0, and its isolated chain-state bucket must be non-empty (so the C check is exercised, not
     skipped).
  2. RED — the reviewer's fixture, rebuilt here from its description: two anchors, byte-identical legz on both sides,
     archive masked seat [0,0,1] vs candidate masked seat [.5,0,.5], real max|Δz| = 1. Device must print
     `VERDICT=REFUSED`, exit 3, and must NAME the anchor. The withdrawn device printed
     `VERDICT=PASS equal=2 compared=2 exit=0` on this same fixture.
  3. Ledger control, both directions — two sides reading different (path, field) pairs must be accepted; two sides
     reading the SAME (path, field) pair must be rejected. That is the guard against FB-01 coming back.

usage: fcf_f4bp_vs_kc_fixture.py <out.json>     env: FCF_DEV_DIR (dir holding fcf_f4bp_vs_kc.py), FCF_FIXTURE_DIR, FCF_PY
"""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, time

import numpy as np

ENV_WHITELIST = ("FCF_DEV_DIR", "FCF_FIXTURE_DIR", "FCF_PY")
DEV_DIR = os.environ.get("FCF_DEV_DIR", os.path.dirname(os.path.abspath(__file__)))
FIX_DIR = os.environ.get("FCF_FIXTURE_DIR", "/workspace/fallback_cf_2026-09-20/work/fixtures/fcf_f4bp_vs_kc")
PY = os.environ.get("FCF_PY", sys.executable)
DEVICE = os.path.join(DEV_DIR, "fcf_f4bp_vs_kc.py")
AA = np.array([1656547200, 1656561600], np.int64)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def build(root, arch_w3_masked, cand_w3, ftrim_n_kc):
    """Two directories, two independently written sets of files. The candidate side is NEVER handed the archive's seat."""
    ob = os.path.join(root, "archive"); out = os.path.join(root, "candidate")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(ob); os.makedirs(os.path.join(out, "work"))
    pm = np.array([0, 1, 0, 1], np.int16); pm_off = np.array([0, 2, 4])
    # per anchor, n = 2 members: legz = [king(2), rev24(2), fund(2)]
    legz = np.array([1., -1., 0., 0., -1., 1.] * 2); legz_off = np.array([0, 6, 12])
    for side in (ob, os.path.join(out, "work")):
        name = "P1.vec.npz" if side == ob else "F4bp_P1.vec.npz"
        np.savez(os.path.join(side, name), anchor=AA, pm=pm, pm_off=pm_off, legz=legz, legz_off=legz_off)
    np.savez(os.path.join(ob, "P3.vec.npz"), anchor=AA, kc_idx=pm, kc_val=np.array([.1, -.1, .2, -.2]), kc_off=pm_off)
    np.savez(os.path.join(ob, "TARGETS_A0_main.npz"), scaled_kind=np.ones(2, np.int8))
    np.savez(os.path.join(out, "work", "F4bp_KING.npz"), anchor=AA, king_file_idx=pm,
             king_file_val=np.array([.2, -.2, .3, -.3]), king_file_off=pm_off)
    json.dump({"records": [{"anchor": int(a),
                            "combo": {"combo_meta": {"w3_masked": list(arch_w3_masked)}, "ftrim": {"n_kc": ftrim_n_kc}}}
                           for a in AA]}, open(os.path.join(ob, "P3.json"), "w"))
    json.dump({"anchor": AA.tolist(), "w3": [list(cand_w3)] * len(AA)},
              open(os.path.join(out, "work", "F4bp_w3.json"), "w"))
    return ob, out


def run_device(root, tag):
    ob, out = root
    gate = os.path.join(os.path.dirname(ob), f"gate_{tag}.json")
    env = dict(os.environ, FCF_OBJB=ob, FCF_OUT=out)
    r = subprocess.run([PY, "-B", DEVICE, gate], capture_output=True, text=True, env=env)
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    verdict_line = next((l for l in reversed(lines) if l.startswith("FCF_F4BP_VS_KC VERDICT=")), "")
    return {"exit_code": r.returncode, "verdict_line": verdict_line,
            "gate": json.load(open(gate)) if os.path.exists(gate) else None,
            "stderr_tail": r.stderr.strip().splitlines()[-3:]}


def main():
    OUTP = sys.argv[1]
    rec = {"device": "fcf_f4bp_vs_kc_fixture.py", "self_sha256": sha(os.path.abspath(__file__)),
           "device_under_test": DEVICE, "device_under_test_sha256": sha(DEVICE),
           "env": {k: os.environ.get(k) for k in ENV_WHITELIST},
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
    FAILS = []

    def step(n, ok, d=None):
        rec["steps"].append(dict(step=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:400] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    os.makedirs(FIX_DIR, exist_ok=True)

    # ── 1 · GREEN BASELINE FIRST. Two independently written sources that really do agree. ────────────────────────
    g_root = build(os.path.join(FIX_DIR, "green"), arch_w3_masked=[0.25, 0.0, 0.75], cand_w3=[0.25, 0.0, 0.75],
                   ftrim_n_kc=0)
    g = run_device(g_root, "green")
    g_iso = ((g["gate"] or {}).get("C_residual_on_simulated_fallback_anchors", {})
             .get("residual_contains__chain_state_cold_start", {}).get("n", 0))
    step("1.GREEN_baseline_two_independent_agreeing_sources",
         g["exit_code"] == 0 and "VERDICT=PASS" in g["verdict_line"] and g_iso > 0,
         dict(exit_code=g["exit_code"], verdict_line=g["verdict_line"], isolated_bucket_n=g_iso,
              why="the baseline must be asserted green BEFORE the red case, or the red case proves nothing"))
    if FAILS:
        rec["VERDICT"] = "REFUSED"; rec["failed"] = FAILS
        json.dump(rec, open(OUTP, "w"), indent=1)
        print(f"FCF_F4BP_VS_KC_FIXTURE VERDICT=REFUSED steps={len(rec['steps'])} failed={len(FAILS)} "
              f"reason=green_baseline_not_green", flush=True)
        sys.exit(3)

    # ── 2 · RED. The reviewer's fixture: same legz, genuinely different candidate seat. ──────────────────────────
    r_root = build(os.path.join(FIX_DIR, "red"), arch_w3_masked=[0.0, 0.0, 1.0], cand_w3=[0.3333, 0.3333, 0.3333],
                   ftrim_n_kc=0)
    r = run_device(r_root, "red")
    gate = r["gate"] or {}
    a3 = next((c for c in gate.get("checks", []) if c["check"].startswith("A3.")), {})
    a2 = next((c for c in gate.get("checks", []) if c["check"].startswith("A2.")), {})
    named = [x for x in (a3.get("detail") or {}).get("refuted_anchors", [])]
    worst = ((a3.get("detail") or {}).get("worst_real_z_difference") or {})
    # independently known truth for this fixture: za = fund = [-1,+1]; zc = .5*king + .5*fund = [0,0] ⇒ max|Δz| = 1
    step("2.RED_on_the_reviewers_fixture",
         r["exit_code"] == 3 and "VERDICT=REFUSED" in r["verdict_line"] and a3.get("ok") is False
         and a2.get("ok") is False and named == ["2022-06-30T00:00:00Z", "2022-06-30T04:00:00Z"]
         and abs(float(worst.get("max_abs_dz", 0)) - 1.0) < 1e-12,
         dict(exit_code=r["exit_code"], verdict_line=r["verdict_line"], A3_ok=a3.get("ok"), A2_ok=a2.get("ok"),
              named_anchors=named, measured_max_abs_dz=worst.get("max_abs_dz"),
              independently_known_max_abs_dz=1.0,
              withdrawn_device_on_this_same_fixture="VERDICT=PASS equal=2 compared=2 exit=0"))

    # ── 3 · Ledger control, both directions ─────────────────────────────────────────────────────────────────────
    spec = importlib.util.spec_from_file_location("fcf_f4bp_vs_kc_under_test", DEVICE)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as td:
        pa = os.path.join(td, "a.json"); pb = os.path.join(td, "b.json")
        open(pa, "w").write("{}"); open(pb, "w").write("{}")
        ok_led = mod.SourceLedger(); ok_led.read("archive_kc", pa, "w3_masked", 1); ok_led.read("candidate_F4bprime", pb, "w3", 1)
        bad_led = mod.SourceLedger(); bad_led.read("archive_kc", pa, "w3_masked", 1); bad_led.read("candidate_F4bprime", pa, "w3_masked", 1)
        step("3a.GREEN_ledger_accepts_two_distinct_sources", ok_led.shared() == [], dict(shared=ok_led.shared()))
        step("3b.RED_ledger_rejects_one_field_read_twice", len(bad_led.shared()) == 1,
             dict(shared=bad_led.shared(), why="this is FB-01 itself: both operands from one (path, field)"))

    rec["VERDICT"] = "PASS" if not FAILS else "REFUSED"; rec["failed"] = FAILS
    json.dump(rec, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_F4BP_VS_KC_FIXTURE VERDICT={rec['VERDICT']} steps={len(rec['steps'])} failed={len(FAILS)} "
          f"receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
