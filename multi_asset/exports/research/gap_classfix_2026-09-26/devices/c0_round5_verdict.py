#!/usr/bin/env python3
"""Round-5 verdict under option A (integ proposal 2026-09-27 05:4xZ, PENDING the lead's ruling; written before any 08Z reading).
C0 is a conjunction of (i) 'the replay reproduces production' and (ii) 'on an anchor without any gap, patched == current'. No live arm64
anchor is gap-free for ~40 days (member-history holes 09-26 12Z/16Z + 09-27 04Z sit in every window), so the two conjuncts are read from the
frozen C0 section run twice on the same anchor A:
  (i)  part i  (hook base):   arms.C0_A.current_vs_archived == '<n> weights bit-equal' — weights AND every other key incl. beta_overlay equal
                              to the arm64 production target_live/<A>.json (written_utc / weights_sha excluded, as in the frozen judge)
  (ii) part ii (hook mhfill): arms.C0_A: weights '<n> weights bit-equal', states_bitwise kc/fc/f10 all True, target_combo and target_blend
                              bytes equal, weights_combo arrays equal, rc [0, 0]; both codes' HOOK lines carry the same members_hist after-sha;
                              both run.logs say 'missing 0' and neither has MH_RECOMPUTED (the anchor really had no gap)
  T (patched not slower by > 2 s) is reported, as in the frozen judge.
PASS iff (i) and (ii). Any difference => STOP, no release, to the lead.
usage: c0_round5_verdict.py <root> <A> <part_i.json> <part_ii.json> --out <json>"""
import hashlib, json, re, sys, time
root, A, pi, pii = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]; out = sys.argv[sys.argv.index("--out") + 1]
Ri, Rii = json.load(open(pi))["arms"][f"C0_{A}"], json.load(open(pii))["arms"][f"C0_{A}"]
def txt(p):
    try: return open(p, errors="replace").read()
    except OSError: return ""
hooks = {c: txt(f"{root}/ii/{c}_base/{A}/HOOK") for c in ("current", "patched")}
logs = {c: txt(f"{root}/ii/{c}_base/{A}/run.log") for c in ("current", "patched")}
after = {c: (re.search(r"members_hist \S+ -> (\S+)", h) or [None, None])[1] for c, h in hooks.items()}
chk = {
    "i_current_vs_archived_bitwise": bool(re.fullmatch(r"\d+ weights bit-equal", str(Ri.get("current_vs_archived")))),
    "ii_weights_bitwise": bool(re.fullmatch(r"\d+ weights bit-equal", str(Rii.get("weights")))),
    "ii_states_bitwise": Rii.get("states_bitwise") == {"kc": True, "fc": True, "f10": True},
    "ii_target_combo_bytes_equal": Rii.get("target_combo_bytes_equal") is True,
    "ii_target_blend_bytes_equal": Rii.get("target_blend_bytes_equal") is True,
    "ii_weights_combo_arrays_equal": Rii.get("weights_combo_arrays_equal") is True,
    "ii_rc_both_0": Rii.get("rc") == [0, 0],
    "ii_same_filled_history_both_codes": after["current"] is not None and after["current"] == after["patched"],
    "ii_no_gap_left": all("missing 0)" in l for l in logs.values()) and not any("MH_RECOMPUTED" in l for l in logs.values()),
}
ok = all(chk.values())
for k, v in chk.items(): print(f"  {'OK ' if v else 'BAD'} {k}")
print(f"  VAL i: {Ri.get('current_vs_archived')} | ii: {Rii.get('weights')} states={Rii.get('states_bitwise')} T_i={Ri.get('T')} T_ii={Rii.get('T')}")
rec = {"device": "c0_round5_verdict.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "A": A,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": chk, "part_i": Ri, "part_ii": Rii, "hooks": hooks, "VERDICT": "PASS" if ok else "FAIL"}
json.dump(rec, open(out, "w"), indent=1, default=str)
print(f"C0_ROUND5 {'PASS' if ok else 'FAIL'} A={A}")
sys.exit(0 if ok else 1)
