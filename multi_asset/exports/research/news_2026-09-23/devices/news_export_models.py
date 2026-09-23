"""NEWS P5 model export (pod2, /workspace/venv torch) — deploy files in the PRODUCTION formats, bound into ONE manifest with the exact
artifacts the evaluation used (R10 export item): any link that does not match ⇒ refuse (exit 3), nothing half-written counts.
Chain bound (each arrow = a sha equality asserted from the receipts, not from file names):
  NEWS_FEATURES (P2B_FEATURES.sha256) → King TRAIN_RECEIPT.inputs → fold 2026 model sha → KING_OOF (predictions_sha256) → legs.npz inputs
  → F10 s42 fold receipts (inputs: features + legs) → fold 202609 model.pt / scores.npz → F10_OOF (pred_sha256) → combo_s42 TARGET_RECEIPT
  (inputs: F10_OOF, legs, features) → scaled_diagnostic.npz → adapter TARGETS_NEWS_s42.json (sources.scaled sha, targets_npz_sha256)
  → RUN_CONFIG_NEWS_s42 (targets.sources) → engine run dir → NEWS_STATS.json (runs root, verdict).
  deploy slow2026.txt == fold 2026 model (sha); deploy f10_live_s42_np.npz exported from fold 202609 model.pt (V1 gate numpy ≡ torch).
F10 202609 training span is reported as it is: the trainer uses only the first 85 % of the admissible training anchors (train_f10.py L102-103),
so ADMISSION.max_train_label_end (≈ 2026-01) — not the 2026-08-22 cutoff — is the last label the gradient saw.
usage: /workspace/venv/bin/python news_export_models.py"""
import os, sys, json, time, hashlib, shutil
import numpy as np
import torch
from scipy.stats import spearmanr
from scipy.special import erf
W = "/dev/shm/news_2026-09-23"


class ExportError(Exception):
    pass


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def need(cond, why):
    if not cond: raise ExportError(why)


def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))


def np_infer(M, X171):
    """verbatim combo_stage.py L194-196 arithmetic"""
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    return (h @ M["w2"].T + M["b2"]).squeeze(-1)


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def main():
    man = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "links": {}}
    L = man["links"]
    feat = f"{W}/work/NEWS_FEATURES.npz"; p2b = json.load(open(f"{W}/receipts/P2B_FEATURES.json"))
    need(sha(feat) == p2b["sha256"], "features sha != P2B receipt"); L["features"] = {"path": feat, "sha256": p2b["sha256"]}
    kr_p = f"{W}/work/king/TRAIN_RECEIPT.json"; kr = json.load(open(kr_p))
    need(kr["inputs"].get(feat) == p2b["sha256"], "King trained on other features")
    need(sha(f"{W}/work/king/KING_OOF.npz") == kr["predictions_sha256"], "KING_OOF sha != King receipt")
    k26 = [f for f in kr["folds"] if f["fold"] == "2026"]; need(len(k26) == 1 and sha(k26[0]["model_path"]) == k26[0]["model_sha256"], "King fold 2026 model sha")
    L["king"] = {"receipt": kr_p, "receipt_sha256": sha(kr_p), "oof_sha256": kr["predictions_sha256"], "fold_2026": k26[0]}
    lg = json.load(open(f"{W}/receipts/P3_LEGS.json"))
    need(sha(f"{W}/work/legs.npz") == lg["sha256"] and lg["inputs"]["features"] == p2b["sha256"] and lg["inputs"]["king_oof"] == kr["predictions_sha256"], "legs lineage")
    L["legs"] = {"sha256": lg["sha256"]}
    fr_p = f"{W}/work/f10_s42/TRAIN_RECEIPT.json"; fr = json.load(open(fr_p))
    need(fr["status"] == "ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED" and set(fr["folds"]) == set(fr["expected_folds"]), "F10 s42 folds incomplete")
    need(fr["inputs"].get(feat) == p2b["sha256"] and fr["inputs"].get(f"{W}/work/legs.npz") == lg["sha256"], "F10 trained on other features/legs")
    need(sha(f"{W}/work/f10_s42/F10_OOF.npz") == fr["pred_sha256"], "F10_OOF sha")
    for p, h in fr["fold_artifacts"].items(): need(sha(p) == h, f"F10 fold artifact drift {p}")
    fold = json.load(open(f"{W}/work/f10_s42/202609/FOLD_RECEIPT.json")); mp = f"{W}/work/f10_s42/202609/model.pt"
    need(fold["fold"] == "202609" and fold["seed"] == 42 and sha(mp) == fold["model_sha256"], "F10 202609 fold identity")
    L["f10_s42"] = {"receipt_sha256": sha(fr_p), "oof_sha256": fr["pred_sha256"], "fold_202609": {"model_pt_sha256": fold["model_sha256"], "score_sha256": fold["score_sha256"],
                    "admission": fold["admission"], "max_train_label_end_utc": iso(fold["admission"]["max_train_label_end"]), "cutoff_utc": iso(fold["admission"]["cutoff"]),
                    "note": "only the first 85% of admissible training anchors enter the gradient (train_f10.py L102-103): the last label the model saw is max_train_label_end, not the cutoff"}}
    cr_p = f"{W}/work/combo_s42/TARGET_RECEIPT.json"; cr = json.load(open(cr_p))
    need(cr["inputs"].get(f"{W}/work/f10_s42/F10_OOF.npz") == fr["pred_sha256"] and cr["inputs"].get(f"{W}/work/legs.npz") == lg["sha256"] and cr["inputs"].get(feat) == p2b["sha256"], "combo lineage")
    sc = cr["policies"]["scaled_diagnostic"]; need(sha(sc["path"]) == sc["sha"], "combo scaled npz sha")
    L["combo_s42"] = {"receipt_sha256": sha(cr_p), "scaled_sha256": sc["sha"]}
    ar_p = f"{W}/targets/TARGETS_NEWS_s42.json"; ar = json.load(open(ar_p))
    need(ar["adapter"]["sources"]["scaled"]["sha256"] == sc["sha"] and ar["roundtrip"]["scaled"]["bitwise_equal"] and sha(f"{W}/targets/TARGETS_NEWS_s42.npz") == ar["targets_npz_sha256"], "adapter lineage")
    L["adapter_s42"] = {"receipt_sha256": sha(ar_p), "targets_npz_sha256": ar["targets_npz_sha256"]}
    cfg_p = f"{W}/configs/RUN_CONFIG_NEWS_s42_2026-09-23.json"; cfg = json.load(open(cfg_p))
    need(all(r["targets"]["sources"][0]["npz_sha256"] == ar["targets_npz_sha256"] and r["targets"]["sources"][0]["receipt_sha256"] == sha(ar_p) for r in cfg["runs"]), "run config targets")
    L["run_config_s42"] = {"path": cfg_p, "sha256": sha(cfg_p), "pod_root": cfg["paths"]["pod_root"]}
    st_p = f"{W}/receipts/engine/NEWS_STATS.json"; st = json.load(open(st_p))
    need(st["runs_roots"]["news"] == f"{cfg['paths']['pod_root']}/runs", "stats read another runs root")
    L["stats"] = {"path": st_p, "sha256": sha(st_p), "VERDICT": st["VERDICT"], "failing_by_seed": st["failing_by_seed"]}
    # ---- deploy files ----
    out = f"{W}/deploy"; os.makedirs(out, exist_ok=True)
    shutil.copy2(k26[0]["model_path"], f"{out}/slow2026.txt"); need(sha(f"{out}/slow2026.txt") == k26[0]["model_sha256"], "deploy King copy")
    ck = torch.load(mp, map_location="cpu", weights_only=False); sdict = ck["state_dict"]
    alpha = float((.02 + .88 * torch.sigmoid(sdict["a"])).item())
    Wt = {"w0": sdict["f.0.weight"].numpy(), "b0": sdict["f.0.bias"].numpy(), "w1": sdict["f.3.weight"].numpy(), "b1": sdict["f.3.bias"].numpy(),
          "w2": sdict["f.6.weight"].numpy(), "b2": sdict["f.6.bias"].numpy()}
    need(Wt["w0"].shape == (256, 171) and Wt["w2"].shape == (1, 256), "F10 layer shapes")
    mu = ck["mu"].cpu().numpy().astype(np.float32); sdv = ck["sd"].cpu().numpy().astype(np.float32); tt = int(fold["admission"]["max_train_label_end"])
    npz = f"{out}/f10_live_s42_np.npz"
    np.savez(npz, **{k: v.astype(np.float32) for k, v in Wt.items()}, mu=mu, sd_=sdv, alpha=np.float32(alpha), n_cols=np.int64(171), trained_through=np.int64(tt))
    M = np.load(npz)
    F = np.load(feat); X = np.concatenate([F["X82"].astype(np.float32), F["X89"]], 1)
    rng = np.random.default_rng(0); sel = rng.choice(len(X), 30000, replace=False); XL = X[sel]
    s_np = np_infer(M, XL)
    net = torch.nn.Sequential(torch.nn.Linear(171, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 1))
    net.load_state_dict({k[2:]: v for k, v in sdict.items() if k.startswith("f.")}); net.eval()
    with torch.no_grad():
        s_t = net(torch.clamp((torch.from_numpy(XL) - ck["mu"].cpu()) / ck["sd"].cpu(), -5, 5)).squeeze(-1).numpy()
    rho = float(spearmanr(s_np, s_t).correlation); mx = float(np.abs(s_np.astype(np.float64) - s_t).max()); v1 = rho >= 0.99999 and mx <= 1e-5
    scz = np.load(f"{W}/work/f10_s42/202609/scores.npz"); rows = scz["rows"]; Pg = scz["P"]; off = F["off"]; dmax = 0.0; rk = 0; n_an = 0
    for k, i in enumerate(rows):
        if off[i + 1] - off[i] < 50: continue
        m = F["m"][off[i]:off[i + 1]].astype(int); s1 = np_infer(M, X[off[i]:off[i + 1]]); s0 = Pg[k, m]
        dmax = max(dmax, float(np.abs(s1.astype(np.float64) - s0).max())); n_an += 1; rk += int((np.argsort(np.argsort(s1)) != np.argsort(np.argsort(s0))).sum())
    man["deploy"] = {"slow2026.txt": {"path": f"{out}/slow2026.txt", "sha256": sha(f"{out}/slow2026.txt"), "= King fold 2026 model": True},
                     "f10_live_s42_np.npz": {"path": npz, "sha256": sha(npz), "from_model_pt_sha256": fold["model_sha256"], "alpha": alpha, "trained_through(max_train_label_end)": tt,
                                             "trained_through_utc": iso(tt)},
                     "V1_gate": {"spearman": rho, "maxabs": mx, "rows": 30000, "PASS": bool(v1), "rule": "spearman >= 0.99999 and maxabs <= 1e-5 (pod_f10_np_export.py)"},
                     "numpy_serving_vs_gpu_oof_202609": {"anchors": n_an, "max_abs": dmax, "within_anchor_rank_mismatch_cells": rk},
                     "executor_pins": {"booster_sha_pin": sha(f"{out}/slow2026.txt"), "f10_sha_pin": sha(npz)}}
    need(v1, f"V1 gate failed rho={rho} maxabs={mx}")
    man["torch"] = torch.__version__; man["numpy"] = np.__version__; man["VERDICT"] = "BOUND"
    json.dump(man, open(f"{W}/receipts/P5_DEPLOY_MANIFEST.json", "w"), indent=1)
    print("EXPORT BOUND", json.dumps(man["deploy"]["executor_pins"]), "V1", man["deploy"]["V1_gate"], "gpu_vs_np", man["deploy"]["numpy_serving_vs_gpu_oof_202609"], flush=True)


if __name__ == "__main__":
    try:
        main()
    except ExportError as e:
        print(f"EXPORT REFUSED: {e}", flush=True); sys.exit(3)
