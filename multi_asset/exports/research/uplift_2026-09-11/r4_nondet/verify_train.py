"""P4 -- training-layer receipts. For every DL run available, report:
  - sha256 of the prediction array it wrote (the only identity that is exact)
  - the four fold best_va / net / turnover / alpha it stamped
  - the input shas it stamped (targets / fea82 / fea89) and the trainer's own self_sha256
  - whether its preds are BITWISE equal to the archived in-service s42 preds
Groups: V2ZERO = runs launched WITHOUT V2=1 (round 3's replication recipe, and my D1..D8 copies of it)
        V2ONE  = runs launched WITH V2=1 (the in-service recipe)
"""
import numpy as np, json, os, hashlib, sys

R = "/workspace/uplift_2026-09-11/r4_nondet"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


RUNS = {}
RUNS["ARCHIVED_s42"] = ("/workspace/f8_ext/preds/f10_V2MAIN_s42.npy",
                        "/workspace/f8_ext/results/f10_V2MAIN_s42.json", "?")
RUNS["ARCHIVED_s2027"] = ("/workspace/f8_ext/preds/f10_V2MAIN_s2027.npy",
                          "/workspace/f8_ext/results/f10_V2MAIN_s2027.json", "?")
for s in ("42", "7", "101", "1234", "31337"):
    p = "/workspace/uplift_2026-09-11/r3_xib/f8/preds/f10_V2MAIN_s%s.npy" % s
    if os.path.exists(p):
        RUNS["R3_s%s" % s] = (p, "/workspace/uplift_2026-09-11/r3_xib/f8/results/f10_V2MAIN_s%s.json" % s, "V2ZERO")
for L in sys.argv[1].split(","):
    p = "%s/f8_%s/preds/f10_V2MAIN_s42.npy" % (R, L)
    if os.path.exists(p):
        RUNS[L] = (p, "%s/f8_%s/results/f10_V2MAIN_s42.json" % (R, L), "V2ZERO" if L.startswith("D") else "V2ONE")

REF = np.load(RUNS["ARCHIVED_s42"][0])
OUT = {}
print("%-16s %-6s %-16s %-42s %-10s %s" % ("run", "V2", "preds_sha16", "best_va 2023/24/25/26", "net_all", "bitwise==ARCH_s42"))
for k, (p, j, v2) in RUNS.items():
    s = sha(p)
    d = json.load(open(j)) if os.path.exists(j) else {}
    bv = "/".join("%.4f" % d["folds"][y]["best_va"] for y in ("2023", "2024", "2025", "2026")) if d.get("folds") else "?"
    Y = np.load(p)
    bw = bool(np.array_equal(np.isnan(Y), np.isnan(REF)) and np.array_equal(Y[~np.isnan(Y)], REF[~np.isnan(REF)]))
    OUT[k] = {"preds": p, "preds_sha256": s, "V2_group": v2, "best_va": bv,
              "net_mean_all": d.get("net_mean_all"), "bitwise_eq_archived_s42": bw,
              "self_sha256": d.get("self_sha256"), "targets_sha256": d.get("targets_sha256"),
              "fea82_sha256": d.get("fea82_sha256"), "fea89_sha256": d.get("fea89_sha256"),
              "alpha_final": [d["folds"][y]["alpha_final"] for y in ("2023", "2024", "2025", "2026")] if d.get("folds") else None,
              "net_by_fold": [d["folds"][y]["net_mean_bps"] for y in ("2023", "2024", "2025", "2026")] if d.get("folds") else None}
    print("%-16s %-6s %-16s %-42s %-10s %s" % (k, v2, s[:16], bv, OUT[k]["net_mean_all"], bw))

# input-sha agreement with the archive
a = OUT["ARCHIVED_s42"]
AGREE = {k: {f: (OUT[k][f] == a[f]) for f in ("self_sha256", "targets_sha256", "fea82_sha256", "fea89_sha256")}
         for k in OUT if OUT[k]["self_sha256"]}
OUT["_input_sha_agreement_with_archived_s42"] = AGREE
# within-group identity
for g in ("V2ZERO", "V2ONE"):
    ks = [k for k in RUNS if RUNS[k][2] == g]
    if len(ks) >= 2:
        s0 = OUT[ks[0]]["preds_sha256"]
        OUT["_within_%s_all_identical" % g] = {"runs": ks, "all_same_sha": all(OUT[k]["preds_sha256"] == s0 for k in ks),
                                               "shas": {k: OUT[k]["preds_sha256"][:16] for k in ks}}
        print("within %s: all identical sha = %s" % (g, OUT["_within_%s_all_identical" % g]["all_same_sha"]))
json.dump(OUT, open(R + "/receipts/RESULT_P4_train.json", "w"), indent=1)
print("VERIFY_TRAIN_DONE")
