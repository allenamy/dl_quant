#!/usr/bin/env python3
"""Round 5 (lead ruling, DEPLOY_gap_classfix 'P5 澄清' 05:5xZ, written before any 08Z reading):
  (i)   frozen C0 section's current_vs_archived == '<n> weights bit-equal' (weights AND every other key incl. beta_overlay equal to the arm64
        production target_live/<A>.json; written_utc / weights_sha excluded exactly as in the frozen judge)
  (iii) every difference between current and patched at A is attributed to the member-history recompute of EXPECT_MH:
        a. patched run.log: 'MH_RECOMPUTED (gap class fix) <k> anchors <EXPECT_MH> errors {}' and '(missing 0)'; current run.log '(missing <k>)';
           the holes of the replayed snapshot's members_hist before A == EXPECT_MH
        b. no other GAP4 path fired in patched: target_combo kc/fc sources 'own', target_blend h_source 'own', no state_lookup key, no
           cold_start_refused, no GAP_PAGE line; members_recomputed keys == EXPECT_MH; both rc 0
        c. the difference stays on the member-history chain: state_H_kc bitwise equal (the King leg reads no member history); anything that
           differs is named (f10 state -> fc state -> combo weights) with its size
  (ii)  is cited, not rerun: run 4 on arm64, current == patched bitwise on 3 gap-free anchors.
PASS iff (i) and (iii) a-c. Any unexplained difference => STOP, no release, to the lead.
usage: c0_round5_attrib.py <root> <A> <c0_section.json> <t1,t2,..> --out <json>"""
import hashlib, json, os, re, sys, time
import numpy as np
root, A, c0p, lit = sys.argv[1], int(sys.argv[2]), sys.argv[3], sorted(int(x) for x in sys.argv[4].split(",") if x)
out = sys.argv[sys.argv.index("--out") + 1]
C0 = json.load(open(c0p))["arms"][f"C0_{A}"]
sb = {c: f"{root}/{c}_base/{A}" for c in ("current", "patched")}; w = {c: f"{sb[c]}/wide_shadow" for c in sb}
log = {c: open(f"{sb[c]}/run.log", errors="replace").read() for c in sb}
rc = {c: open(f"{sb[c]}/RC").read().strip() for c in sb}
def js(c, rel):
    p = f"{w[c]}/{rel}"; return json.load(open(p)) if os.path.exists(p) else None
tc, tb = js("patched", f"state/target_combo/{A}.json") or {}, js("patched", f"state/target_blend/{A}.json") or {}
with np.load(f"{w['current']}/state/members_hist.npz") as m: an = sorted(int(x) for x in m["anchors"])
holes = [t for t in range(an[0], A, 14400) if t not in set(an)]
mh = re.search(r"MH_RECOMPUTED \(gap class fix\) (\d+) anchors (\[[^\]]*\]) errors (\{.*\})", log["patched"])
def st(c, leg):
    p = f"{w[c]}/fea171/state_H_{leg}_{A}.npz"
    if not os.path.exists(p): return None
    with np.load(p) as z: return {k: z[k] for k in z.files}
def st_diff(leg):
    a, b = st("current", leg), st("patched", leg)
    if a is None or b is None: return {"present": [a is not None, b is not None]}
    eq = set(a) == set(b) and all(np.array_equal(a[k], b[k]) and a[k].dtype == b[k].dtype for k in a)
    d = {"bitwise": eq}
    if not eq and set(a) == set(b) and a["idx"].shape == b["idx"].shape and np.array_equal(a["idx"], b["idx"]):
        d["max_abs_val_diff"] = float(np.max(np.abs(a["val"].astype(float) - b["val"].astype(float)))); d["n_val_differ"] = int(np.sum(a["val"] != b["val"]))
    elif not eq: d["idx_sets_differ"] = True
    return d
tl = {c: js(c, f"state/target_live_PARITY/{A}.json") for c in sb}
wd = None
if tl["current"] and tl["patched"]:
    wa, wb = tl["current"]["weights"], tl["patched"]["weights"]; ks = set(wa) | set(wb)
    nd = [k for k in ks if wa.get(k) != wb.get(k)]
    wd = {"n_names": len(ks), "n_differ": len(nd), "max_abs": max([abs((wa.get(k) or 0.0) - (wb.get(k) or 0.0)) for k in nd] or [0.0]),
          "key_sets_equal": set(wa) == set(wb)}
chk = {
    "i_current_vs_archived_bitwise": bool(re.fullmatch(r"\d+ weights bit-equal", str(C0.get("current_vs_archived")))),
    "iii_a_holes_before_A_equal_literal": holes == lit,
    # an empty literal (a gap-free anchor) means NO recompute line at all (control on run 4's 09-26 08Z found rev 0 demanded a line there)
    "iii_a_patched_MH_RECOMPUTED_equals_literal_no_errors": (bool(mh) and int(mh.group(1)) == len(lit) and json.loads(mh.group(2)) == lit and mh.group(3) == "{}")
                                                            if lit else (mh is None and "MH_RECOMPUTED" not in log["patched"]),
    "iii_a_patched_missing_0": "(missing 0)" in log["patched"],
    "iii_a_current_missing_equals_len_literal": f"(missing {len(lit)})" in log["current"],
    "iii_b_patched_sources_own": tc.get("kc_state_source") == "own" and tc.get("fc_state_source") == "own" and tb.get("h_source") == "own",
    "iii_b_no_state_lookup_no_cold_no_page": "state_lookup" not in tc and not tc.get("cold_start_refused") and "GAP_PAGE" not in log["patched"],
    "iii_b_members_recomputed_keys_equal_literal": sorted(int(k) for k in (tc.get("members_recomputed") or {})) == lit and not tc.get("members_recompute_errors"),
    "iii_b_rc_both_0": rc == {"current": "0", "patched": "0"},
    "iii_c_kc_state_bitwise": st_diff("kc").get("bitwise") is True,
}
named = {"f10_state": st_diff("f10"), "fc_state": st_diff("fc"), "kc_state": st_diff("kc"), "weights": wd,
         "target_combo_bytes_equal": C0.get("target_combo_bytes_equal"), "target_blend_bytes_equal": C0.get("target_blend_bytes_equal"),
         "weights_combo_arrays_equal": C0.get("weights_combo_arrays_equal")}
ok = all(chk.values())
for k, v in chk.items(): print(f"  {'OK ' if v else 'BAD'} {k}")
print(f"  VAL (i) {C0.get('current_vs_archived')} | holes {holes} | MH line {mh.group(0) if mh else None}")
print(f"  VAL named differences: {json.dumps(named, default=str)}")
rec = {"device": "c0_round5_attrib.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "A": A, "expect_mh": lit,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": chk, "named_differences": named, "c0_section": C0,
       "ii_cited": "receipts/GAPFIX_JUDGE_run4_arm64.json: C0 current==patched bitwise on 1790380800/1790395200/1790409600 (arm64)",
       "VERDICT": "PASS" if ok else "FAIL"}
json.dump(rec, open(out, "w"), indent=1, default=str)
print(f"C0_ROUND5 {'PASS' if ok else 'FAIL'} A={A}")
sys.exit(0 if ok else 1)
