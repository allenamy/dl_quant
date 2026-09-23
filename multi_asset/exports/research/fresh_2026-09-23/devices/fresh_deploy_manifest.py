"""fresh_deploy_manifest.py — build P5_DEPLOY_MANIFEST.json for the FRESH candidate package, in the structure the deployment
manual docs/DEPLOY_new_servable_models_2026-09-23.md §0.1 requires (NEW_S's manifest 3a648aa6… is the shape being matched).
Everything here is read from a receipt that already exists; nothing is recomputed except one check, named below.

TWO STRUCTURAL DIFFERENCES FROM NEW_S'S MANIFEST, both required by the FRESH pre-registration and both stated in the product:
  1. NEW_S deploys its LAST WALK-FORWARD FOLD (King fold 2026, F10 fold 202609). FRESH deploys a FINAL REFIT AT THE DATA END
     (training-label cutoff = last available label − 6 anchors), so the manifest carries fold "FINAL", not a fold name.
  2. NEW_S's manifest carries `numpy_serving_vs_gpu_oof_202609`: the deployed npz re-checked against the GPU scores that same
     fold produced out-of-fold. FRESH's deployed model is a final refit that never scored an OOF fold, so that comparison HAS NO
     COUNTERPART and is NOT reported as a number. It is replaced by a same-shaped check on the object actually being deployed —
     numpy serving vs torch eval of the FINAL model over the real member rows of the nine acceptance anchors, reporting the same
     three statistics (anchors / max_abs / within-anchor rank mismatch cells). The substitution is named in the product.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fresh_deploy_manifest.py PATH,HOME,LC_CTYPE <FRESH_STATS.json> <out.json>
"""
import os, sys, json, time, hashlib
import numpy as np
WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
STATS, OUT = sys.argv[2:4]
W = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def gelu(x):
    from scipy.special import erf
    return 0.5 * x * (1 + erf(x / np.sqrt(2)))


def np_infer(M, X171):
    xz = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    return (h @ M["w2"].T + M["b2"]).squeeze(-1)


def serving_check(npz_path, pt_path, rows_path):
    """numpy serving vs torch eval of the SAME (FINAL) model, on the real member rows of the acceptance anchors."""
    import torch
    M = np.load(npz_path); ck = torch.load(pt_path, map_location="cpu", weights_only=False); sd = ck["state_dict"]
    net = torch.nn.Sequential(torch.nn.Linear(171, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 1))
    net.load_state_dict({k[2:]: v for k, v in sd.items() if k.startswith("f.")}); net.eval()
    R = np.load(rows_path, allow_pickle=True); anch = [int(x) for x in R["anchors"]]
    mx = 0.0; mism = 0; cells = 0
    for A in anch:
        X = np.concatenate([R[f"X82_{A}"].astype(np.float32), R[f"X89_{A}"]], 1)
        s_np = np_infer(M, X)
        with torch.no_grad():
            s_t = net(torch.clamp((torch.from_numpy(X) - ck["mu"].cpu()) / ck["sd"].cpu(), -5, 5)).squeeze(-1).numpy()
        mx = max(mx, float(np.abs(s_np.astype(np.float64) - s_t).max()))
        mism += int((np.argsort(np.argsort(s_np)) != np.argsort(np.argsort(s_t))).sum()); cells += len(s_np)
    return {"anchors": len(anch), "max_abs": mx, "within_anchor_rank_mismatch_cells": mism, "cells": cells,
            "what": "numpy serving vs torch eval of the DEPLOYED FINAL model over the real member rows of the nine acceptance anchors",
            "replaces": "NEW_S's numpy_serving_vs_gpu_oof_202609, which has no counterpart for a final refit that never scored an OOF fold"}


def main():
    kr = json.load(open(f"{W}/work/final/KING_FINAL_RECEIPT.json")); fr = json.load(open(f"{W}/work/final/F10_FINAL_RECEIPT_s42.json"))
    ex = json.load(open(f"{W}/receipts/P5_EXPORT.json")); kt = json.load(open(f"{W}/work/king/TRAIN_RECEIPT.json")); ft = json.load(open(f"{W}/work/f10_s42/TRAIN_RECEIPT.json"))
    ar = json.load(open(f"{W}/receipts/P5_ACCEPT_ROWS.json")); st = json.load(open(STATS))
    deploy_king = f"{W}/deploy/slow2026.txt"; deploy_f10 = f"{W}/deploy/f10_live_s42_np.npz"
    ks, fs = sha(deploy_king), sha(deploy_f10)
    assert ks == kr["model_sha256"], "deployed King is not the FINAL fit"
    assert fs == ex["f10_s42"]["deploy_sha256"], "deployed F10 npz is not the exported one"
    chk = serving_check(deploy_f10, fr["model_path"], ar["output"])
    rec = {
        "device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
        "candidate": "FRESH", "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
        "deployed_object": "FINAL REFIT AT THE DATA END (NOT the last walk-forward fold, which is what NEW_S deploys): "
                           "training-label cutoff = last available label on the axis − 6 anchors",
        "links": {
            "features": {"path": f"{N}/work/NEWS_FEATURES.npz", "sha256": kr["inputs"][f"{N}/work/NEWS_FEATURES.npz"],
                         "note": "NEW_S's producer-replayed panel, read-only; FRESH changes the folds, not the features"},
            "king": {"receipt": f"{W}/work/king/TRAIN_RECEIPT.json", "receipt_sha256": sha(f"{W}/work/king/TRAIN_RECEIPT.json"),
                     "oof_sha256": kt["predictions_sha256"], "n_folds": len(kt["folds"]),
                     "fold_FINAL": {"fold": "FINAL", "max_train_label_end": kr["max_train_label_end"], "max_train_label_end_utc": kr["max_train_label_end_iso"],
                                    "cutoff": kr["cutoff"], "cutoff_utc": iso(kr["cutoff"]), "embargo_anchors": kr["embargo_anchors"],
                                    "train_pairs": kr["train_pairs"], "train_anchors": kr["train_anchors"], "model_path": kr["model_path"], "model_sha256": kr["model_sha256"],
                                    "seconds": kr["seconds"]}},
            "legs": {"sha256": sha(f"{W}/work/legs.npz")},
            "f10_s42": {"receipt": f"{W}/work/f10_s42/TRAIN_RECEIPT.json", "receipt_sha256": sha(f"{W}/work/f10_s42/TRAIN_RECEIPT.json"),
                        "oof_sha256": ft["pred_sha256"], "n_folds": len(ft["folds"]),
                        "fold_FINAL": {"model_pt_sha256": fr["model_sha256"], "admission": fr["admission"],
                                       "max_train_label_end_utc": iso(fr["admission"]["max_train_label_end"]), "cutoff_utc": iso(fr["admission"]["cutoff"]),
                                       "note": "TRAIN_FRAC = 1.0 (PREREG §1 F): the whole admissible training window enters the gradient, so "
                                               "max_train_label_end EQUALS the cutoff. NEW_S's note about the first 85% does not apply."}},
            "combo_s42": {"receipt_sha256": sha(f"{W}/work/combo_s42/TARGET_RECEIPT.json"), "scaled_sha256": sha(f"{W}/work/combo_s42/scaled_diagnostic.npz")},
            "adapter_s42": {"spec": f"{W}/configs/ADAPTER_SPEC_FRESH_s42.json", "spec_sha256": sha(f"{W}/configs/ADAPTER_SPEC_FRESH_s42.json")},
            "run_config_s42": {"path": f"{W}/configs/RUN_CONFIG_FRESH_s42_2026-09-23.json", "sha256": sha(f"{W}/configs/RUN_CONFIG_FRESH_s42_2026-09-23.json"), "pod_root": W},
            "accept_rows": {"path": ar["output"], "sha256": ar["sha256"], "receipt_sha256": sha(f"{W}/receipts/P5_ACCEPT_ROWS.json")},
            "stats": {"path": STATS, "sha256": sha(STATS), "VERDICT": st.get("VERDICT"), "failing_by_seed": st.get("failing_by_seed")}},
        "deploy": {
            "slow2026.txt": {"path": deploy_king, "sha256": ks, "= King FINAL refit": True},
            "f10_live_s42_np.npz": {"path": deploy_f10, "sha256": fs, "from_model_pt_sha256": fr["model_sha256"], "alpha": ex["f10_s42"]["alpha"],
                                    "trained_through(max_train_label_end)": fr["admission"]["max_train_label_end"],
                                    "trained_through_utc": iso(fr["admission"]["max_train_label_end"])},
            "V1_gate": ex["V1_gate"],
            "numpy_serving_vs_gpu_oof": {"AVAILABLE": False,
                                         "why": "the deployed object is a final refit at the data end; it never scored an out-of-fold window, so there are no GPU OOF "
                                                "scores for it to be compared against. Not reported as a number, and NOT substituted by the same check run on a "
                                                "different (fold) model, which would certify an object that is not being deployed.",
                                         "substitute": chk},
            "executor_pins": {"booster_sha_pin": ks, "f10_sha_pin": fs}},
        "torch": ex["torch"], "numpy": ex["numpy"],
        "VERDICT": "BOUND" if (ex["V1_gate"]["PASS"] and ks == kr["model_sha256"] and fs == ex["f10_s42"]["deploy_sha256"]) else "NOT_BOUND",
        "verdict_meaning": "BOUND = the two deployed files are byte-identical to the receipted final fits and the V1 inference-consistency gate passed. "
                           "It says nothing about whether the candidate should be deployed; that is links.stats.VERDICT."}
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print(f"FRESH_DEPLOY_MANIFEST VERDICT={rec['VERDICT']} stats_verdict={rec['links']['stats']['VERDICT']} "
          f"booster_sha_pin={ks[:16]} f10_sha_pin={fs[:16]} V1_PASS={ex['V1_gate']['PASS']} "
          f"substitute_check(anchors={chk['anchors']}, max_abs={chk['max_abs']:.3e}, rank_mismatch_cells={chk['within_anchor_rank_mismatch_cells']}/{chk['cells']}) "
          f"manifest_sha256={sha(OUT)}", flush=True)
    sys.exit(0 if rec["VERDICT"] == "BOUND" else 3)


if __name__ == "__main__":
    main()
