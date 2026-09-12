#!/usr/bin/env python3
"""r21_judge.py -- Part A judge (PREREG_r21 SS A4): rematched-null table, rank/z of the true arm, the frozen verdict rule for
CEM_99_neutral, and the R12-wide (29 arms) audit of the 'turnover-matched' claim. Local; ENV whitelist = EMPTY SET (asserted)."""
import os, json, time, hashlib
_F = ["LEGS", "PHI", "CAL", "CEM_Q", "CEM_MODE", "R12_NULL", "R21_DOSE", "FSEED", "FPRED", "COSTB_JSON", "UMASK_SCOPE", "FTRIM"]
assert sorted(k for k in _F if k in os.environ) == [], "env not empty"
import numpy as np
ROOT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"; R21 = f"{ROOT}/r21_nulls_costbridge"
PREREG_SHA = "c4de6df3a37483462d4e10373c30ea4137c02c78f9a23e06148007c5ce246232"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""): h.update(c)
    return h.hexdigest()
assert sha(f"{R21}/PREREG_r21_2026-09-12.md") == PREREG_SHA
B = json.load(open(f"{R21}/receipts/BISECT_r21.json")); REP = json.load(open(f"{R21}/receipts/REPRO_A1.json"))
NJ = json.load(open(f"{ROOT}/r12_intervene/receipts/NULLJUDGE.json")); BAT = json.load(open(f"{ROOT}/r12_intervene/receipts/BATTERY_r12.json"))
assert sha(f"{ROOT}/r12_intervene/receipts/NULLJUDGE.json") == "e39323b0e11d0994bd51b7450efeaf710f3da4b080202d7192e5c47b5b081997"
assert sha(f"{ROOT}/r12_intervene/receipts/BATTERY_r12.json") == "546192fe13459bd5fffd30ea5d9b70427b8eaeef1a848d3240cc3a9eee75c11d"
assert REP["G_A1_PASS"] and all(v["rec_bitwise"] and v["W_bitwise"] for v in B["gates"].values())
OUT = {"prereg_sha256": PREREG_SHA, "env_whitelist": [], "utc": time.strftime("%FT%TZ", time.gmtime()), "inputs": {"BISECT_r21": sha(f"{R21}/receipts/BISECT_r21.json"), "REPRO_A1": sha(f"{R21}/receipts/REPRO_A1.json")},
       "device_sha256": B["device_sha256"], "gates": {"G_A1": REP["G_A1_PASS"], "G_A2": B["gates"]}, "arms": {}}
def zrank(true_dg, null_dgs):
    a = np.array(null_dgs, float)
    return {"n_nulls": len(a), "null_mean": float(a.mean()), "null_sd_ddof1": float(a.std(ddof=1)), "null_max": float(a.max()),
            "n_nulls_beating_true": int((a >= true_dg).sum()), "beats_all": bool((a < true_dg).all()), "z": float((true_dg - a.mean()) / a.std(ddof=1))}
for arm, v in B["arms"].items():
    t = v["true"]; rows = {}
    for nm, n in v["nulls"].items():
        e0 = [e for e in n["evals"] if e["dose"] == 0.0][0]; m = n["matched"]
        rows[nm] = {"construction": n["construction"], "fires": n["fires"],
                    "archived_or_D0": {"dturn_frac_pct": e0["dturn_frac_pct"], "rel_mismatch": abs(e0["dturn_frac_pct"] - t["dturn_frac_pct"]) / abs(t["dturn_frac_pct"]), "fire_n": e0["fire_n"], "dg": e0["dg"], "cem_n_mean": e0["cem_n_mean"], "source": e0["source"]},
                    "rematched": {"dose": m["dose"], "dturn_frac_pct": m["dturn_frac_pct"], "rel_mismatch": n["rel_mismatch_after"], "within_1pct": n["matched_within_1pct"], "fire_n": m["fire_n"], "fire_diff_vs_true": m["fire_n"] - t["fire_n"],
                                  "dg": m["dg"], "cem_n_mean": m["cem_n_mean"], "dturn_file_caliber_pct": m["dturn_file_pct"], "n_evals": n["n_evals"]}}
    z0 = zrank(t["dg"], [r["archived_or_D0"]["dg"] for r in rows.values()]); z1 = zrank(t["dg"], [r["rematched"]["dg"] for r in rows.values()])
    # receipt's own six (for CEM_99/95 these are the same archived series; for derisk there is no receipt entry)
    key = arm; rec = NJ["nulls"].get(key)
    zrec = zrank(rec["true_dg"], [x["dg"] for x in rec["nulls"].values()]) if rec else None
    verdict = None
    if arm == "R12_CEM_99_neutral_s42":
        if not z1["beats_all"]: verdict = "DOES_NOT_SURVIVE (a rematched null reaches the true dg)"
        elif z1["z"] >= (2.0 / 3.0) * z0["z"]: verdict = "SURVIVES (6/6 and z >= 2/3 of archived z)"
        else: verdict = "WEAKENED (6/6 holds but z fell by more than 1/3)"
    OUT["arms"][arm] = {"true": t, "nulls": rows, "z_archived_or_D0": z0, "z_rematched": z1, "z_from_receipt": zrec,
                        "all_rematched_within_1pct": bool(all(r["rematched"]["within_1pct"] for r in rows.values())),
                        "all_fires_within_pm1": bool(all(abs(r["rematched"]["fire_diff_vs_true"]) <= 1 for r in rows.values())),
                        "max_rel_mismatch_before": max(r["archived_or_D0"]["rel_mismatch"] for r in rows.values()),
                        "max_rel_mismatch_after": max(r["rematched"]["rel_mismatch"] for r in rows.values()),
                        "mean_dose": float(np.mean([r["rematched"]["dose"] for r in rows.values()])), "verdict_rule_A4_3": verdict}
# ---------------- R12-wide audit of the claim ----------------
audit = {}
for arm in sorted(BAT["arms"]):
    a = BAT["arms"][arm]; key = arm if arm in NJ["nulls"] else None
    row = {"kind": a["kind"], "dg": a["dg"], "dturn_frac_pct": a["dturn_frac_pct"], "fire_n": a.get("fire_n"), "nulls_exist_in_receipt": key is not None}
    if key:
        rec = NJ["nulls"][key]; rels = {nm: abs(x["dturn_frac_pct"] - rec["true_dturn_frac_pct"]) / abs(rec["true_dturn_frac_pct"]) for nm, x in rec["nulls"].items()}
        fd = {nm: x["fire_n"] - a["fire_n"] for nm, x in rec["nulls"].items()}
        row.update({"receipt_flag_turnover_matched": rec["turnover_matched"], "receipt_rule": "max|d_null - d_true| < max(2.0 pp, 0.5*|d_true|)",
                    "max_rel_turnover_mismatch": max(rels.values()), "argmax": max(rels, key=rels.get), "rule_lt1pct_relative_held": bool(max(rels.values()) <= 0.01),
                    "fire_diffs": fd, "fire_within_pm1_held": bool(all(abs(x) <= 1 for x in fd.values())), "receipt_beats_all_nulls": rec["beats_all_nulls"]})
        if arm in OUT["arms"]:
            row["r21_rematched"] = {"max_rel_after": OUT["arms"][arm]["max_rel_mismatch_after"], "beats_all_after": OUT["arms"][arm]["z_rematched"]["beats_all"], "z_after": OUT["arms"][arm]["z_rematched"]["z"]}
    else:
        row["note"] = ("overlay arm (no device run, no nulls were constructed)" if a["kind"] == "overlay" else "device arm; r12 built no nulls for it")
        if arm in OUT["arms"]: row["r21_new_nulls"] = {"max_rel_after": OUT["arms"][arm]["max_rel_mismatch_after"], "beats_all_after": OUT["arms"][arm]["z_rematched"]["beats_all"], "z_after": OUT["arms"][arm]["z_rematched"]["z"]}
    audit[arm] = row
OUT["R12_wide_audit"] = {"n_arms": len(audit), "n_with_nulls": sum(1 for r in audit.values() if r["nulls_exist_in_receipt"]),
                         "n_flag_true": sum(1 for r in audit.values() if r.get("receipt_flag_turnover_matched")),
                         "n_lt1pct_held": sum(1 for r in audit.values() if r.get("rule_lt1pct_relative_held")), "arms": audit}
json.dump(OUT, open(f"{R21}/receipts/JUDGE_r21_partA.json", "w"), indent=1)
for arm, v in OUT["arms"].items():
    print("\n==", arm, "true dg %+.6f dturn %.6f fires %d" % (v["true"]["dg"], v["true"]["dturn_frac_pct"], v["true"]["fire_n"]))
    print("   z archived/D0: mean %+.6f sd %.6f z %+.3f beats %d/6 | rematched: mean %+.6f sd %.6f z %+.3f beats %d/6 | max rel before %.4f after %.4f | mean dose %+.4f | verdict %s" % (
        v["z_archived_or_D0"]["null_mean"], v["z_archived_or_D0"]["null_sd_ddof1"], v["z_archived_or_D0"]["z"], 6 - v["z_archived_or_D0"]["n_nulls_beating_true"],
        v["z_rematched"]["null_mean"], v["z_rematched"]["null_sd_ddof1"], v["z_rematched"]["z"], 6 - v["z_rematched"]["n_nulls_beating_true"], v["max_rel_mismatch_before"], v["max_rel_mismatch_after"], v["mean_dose"], v["verdict_rule_A4_3"]))
    for nm, r in v["nulls"].items():
        print("   %-10s before: dturn %.6f rel %.4f fires %d dg %+.6f | after: dose %+.5f dturn %.6f rel %.4f fires %d dg %+.6f cem_n %.3f" % (nm, r["archived_or_D0"]["dturn_frac_pct"], r["archived_or_D0"]["rel_mismatch"], r["archived_or_D0"]["fire_n"], r["archived_or_D0"]["dg"],
              r["rematched"]["dose"], r["rematched"]["dturn_frac_pct"], r["rematched"]["rel_mismatch"], r["rematched"]["fire_n"], r["rematched"]["dg"], r["rematched"]["cem_n_mean"]))
A = OUT["R12_wide_audit"]; print("\nR12-wide: arms %d, with nulls %d, flag True %d, <1%% held %d" % (A["n_arms"], A["n_with_nulls"], A["n_flag_true"], A["n_lt1pct_held"]))
for arm, r in A["arms"].items():
    if r["nulls_exist_in_receipt"]: print("   %-32s max rel %.4f (%s) flag %s <1%% %s fires+-1 %s beats_all %s" % (arm, r["max_rel_turnover_mismatch"], r["argmax"], r["receipt_flag_turnover_matched"], r["rule_lt1pct_relative_held"], r["fire_within_pm1_held"], r["receipt_beats_all_nulls"]))
print("WROTE", f"{R21}/receipts/JUDGE_r21_partA.json")
