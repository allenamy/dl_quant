"""king_oct_manifest.py -- release manifest of the October candidate King (fresh2 2026-09-27; lead: user chose October plan (ii),
runbook 1fa4e3be5). Reads the finished release root and writes MANIFEST_RELEASE.json through durable_write:
  served   : m0 (rs=0) fold "2026" model file = THE file to pin (booster_sha_pin); its sha as the trainer's verified write returned it
             (TRAIN_RECEIPT folds[2026].model_sha256), plus whether the file on disk still has it now (a boolean, not a second sha source)
  members  : m0..m7 (rs 0..7; m0 = the served run) KING_OOF path, predictions_sha256 (from each receipt), P array sha, receipt sha;
             m1..m7 are descriptive only (lead ruling: King member spread is a description column, not a gate)
  gates    : the three KOC_CHECK receipts the driver ran (dup / cross-run vs the controls' C2a / served) must all be PASS
  inputs   : features / labels / fold source / trainer / durable_write shas, all from the m0 receipt, asserted equal across members
usage: python king_oct_manifest.py <release root> <features sha expected>
"""
import os, sys, json, hashlib
import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    root, fsha_want = sys.argv[1], sys.argv[2]
    members, inputs0 = {}, None
    for m in range(8):
        w = os.path.join(root, "m%d" % m); rp = os.path.join(w, "TRAIN_RECEIPT.json"); rec = json.load(open(rp))
        assert rec["random_state"] == m and rec["arm"] == "A0" and rec["label_switch"] == "y4s"
        assert fsha_want in rec["inputs"].values(), "m%d not trained on the expected features" % m
        if inputs0 is None: inputs0 = (rec["inputs"], rec["source_sha"])
        assert (rec["inputs"], rec["source_sha"]) == inputs0, "m%d inputs / devices differ from m0" % m
        oof = os.path.join(w, "KING_OOF.npz")
        members["m%d" % m] = {"random_state": m, "role": "served" if m == 0 else "descriptive", "oof": oof,
                              "predictions_sha256": rec["predictions_sha256"], "oof_file_matches_receipt_now": sha(oof) == rec["predictions_sha256"],
                              "P_array_sha256": hashlib.sha256(np.ascontiguousarray(np.load(oof)["P"]).tobytes()).hexdigest(),
                              "receipt": rp, "receipt_sha256": sha(rp), "models_kept": rec["models_kept"]}
    r0 = json.load(open(os.path.join(root, "m0", "TRAIN_RECEIPT.json")))
    assert r0["models_kept"], "the served run must keep its models"
    f26 = [f for f in r0["folds"] if f["fold"] == "2026"]; assert len(f26) == 1; f26 = f26[0]
    served = {"path": f26["model_path"], "sha256": f26["model_sha256"], "sha_source": "m0 TRAIN_RECEIPT folds[2026].model_sha256 (verified write)",
              "file_matches_now": sha(f26["model_path"]) == f26["model_sha256"], "train_pairs": f26["train_pairs"],
              "max_train_label_end": f26["max_train_label_end"], "score_start": f26["score_start"], "embargo_anchors": f26["embargo_anchors"]}
    all_folds = [{"fold": f["fold"], "path": f["model_path"], "sha256": f["model_sha256"]} for f in r0["folds"]]
    gates = {}
    for n in ("G1_dup", "G2_cross_run_vs_C2a", "G3_served"):
        g = json.load(open(os.path.join(root, "checks", n + ".json"))); gates[n] = {"PASS": g["PASS"], "receipt_sha256": sha(os.path.join(root, "checks", n + ".json"))}
    ok = all(g["PASS"] for g in gates.values()) and served["file_matches_now"] and all(v["oof_file_matches_receipt_now"] for v in members.values())
    man = {"device": "king_oct_manifest.py", "self_sha256": sha(os.path.realpath(__file__)), "RELEASE_OK": bool(ok),
           "recipe": "in-service A0 (annual folds, fold 2026 served), features swapped to D10 only (lead ruling 06:4xZ)",
           "served_model_TO_PIN": served, "m0_all_fold_models": all_folds, "members": members, "gates": gates,
           "inputs": inputs0[0], "source_sha": inputs0[1]}
    s = DW.write_json(os.path.join(root, "MANIFEST_RELEASE.json"), man, indent=1)
    print("KOR_MANIFEST RELEASE_OK=%s served=%s sha=%s" % (bool(ok), served["sha256"], s), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
