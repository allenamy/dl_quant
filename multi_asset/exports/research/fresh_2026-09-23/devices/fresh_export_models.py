"""FRESH deployment-candidate export (pod2, /workspace/venv torch) — news_export_models.py with the sources replaced by the
FRESH FINAL fits (fresh_final_fit.py), in the PRODUCTION file formats. NOT deployed.
  King   : work/final/king_final.txt → deploy/slow2026.txt (LightGBM text model; production shadow_loop_v3 load_bundle reads
           shadow_bundle/slow2026.txt with lightgbm.Booster(model_file=...)).
  F10 s42: work/final/f10_final_s42.pt → deploy/f10_live_s42_np.npz with the keys production combo_stage L186-196 reads
           (w0,b0,w1,b1,w2,b2,mu,sd_) plus alpha / n_cols / trained_through (layout of pod_f10_np_export.py).
Gate V1 (same as pod_f10_np_export.py / news_export_models.py): 30,000 real feature rows, production numpy inference
(erf GELU, float32 arrays as in combo_stage) vs torch eval: median Spearman >= 0.99999 and max|Δ| <= 1e-5, else exit 3.
The receipt states the ACTUAL gradient cutoff of each leg.
"""
import os, sys, json, time, hashlib, shutil
import numpy as np
import torch
from scipy.stats import spearmanr
from scipy.special import erf
W = "/dev/shm/fresh_2026-09-23"
N = "/dev/shm/news_2026-09-23"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))


def np_infer(M, X171):
    """verbatim combo_stage.py L194-196 arithmetic"""
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    return (h @ M["w2"].T + M["b2"]).squeeze(-1)


def main():
    out = f"{W}/deploy"; os.makedirs(out, exist_ok=True)
    cutrec = json.load(open(f"{W}/work/final/CUTOFF.json"))
    kr = json.load(open(f"{W}/work/final/KING_FINAL_RECEIPT.json"))
    assert sha(kr["model_path"]) == kr["model_sha256"]
    shutil.copy2(kr["model_path"], f"{out}/slow2026.txt"); assert sha(f"{out}/slow2026.txt") == kr["model_sha256"]
    fr = json.load(open(f"{W}/work/final/F10_FINAL_RECEIPT_s42.json")); mp = fr["model_path"]
    assert sha(mp) == fr["model_sha256"] and fr["seed"] == 42
    ck = torch.load(mp, map_location="cpu", weights_only=False); sd = ck["state_dict"]
    a = sd["a"]; alpha = float((.02 + .88 * torch.sigmoid(a)).item())
    Wt = {"w0": sd["f.0.weight"].numpy(), "b0": sd["f.0.bias"].numpy(), "w1": sd["f.3.weight"].numpy(), "b1": sd["f.3.bias"].numpy(),
          "w2": sd["f.6.weight"].numpy(), "b2": sd["f.6.bias"].numpy()}
    assert Wt["w0"].shape == (256, 171) and Wt["w2"].shape == (1, 256)
    mu = ck["mu"].cpu().numpy().astype(np.float32); sdv = ck["sd"].cpu().numpy().astype(np.float32)
    tt = int(fr["admission"]["max_train_label_end"])
    npz = f"{out}/f10_live_s42_np.npz"
    np.savez(npz, **{k: v.astype(np.float32) for k, v in Wt.items()}, mu=mu, sd_=sdv, alpha=np.float32(alpha), n_cols=np.int64(171), trained_through=np.int64(tt))
    M = np.load(npz)
    F = np.load(f"{N}/work/NEWS_FEATURES.npz"); X = np.concatenate([F["X82"].astype(np.float32), F["X89"]], 1)
    rng = np.random.default_rng(0); sel = rng.choice(len(X), 30000, replace=False); XL = X[sel]
    s_np = np_infer(M, XL)
    net = torch.nn.Sequential(torch.nn.Linear(171, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 1))
    net.load_state_dict({k[2:]: v for k, v in sd.items() if k.startswith("f.")}); net.eval()
    with torch.no_grad():
        s_t = net(torch.clamp((torch.from_numpy(XL) - ck["mu"].cpu()) / ck["sd"].cpu(), -5, 5)).squeeze(-1).numpy()
    rho = float(spearmanr(s_np, s_t).correlation); mx = float(np.abs(s_np.astype(np.float64) - s_t).max())
    ok = rho >= 0.99999 and mx <= 1e-5
    rec = {"status": "DEPLOYMENT_CANDIDATE_NOT_DEPLOYED", "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
           "cutoff_rule": cutrec,
           "king": {"source": kr["model_path"], "sha256": kr["model_sha256"], "deploy_file": f"{out}/slow2026.txt", "fold": "FINAL",
                    "actual_gradient_cutoff": {"max_train_label_end": kr["max_train_label_end"], "iso": kr["max_train_label_end_iso"]},
                    "train_pairs": kr["train_pairs"], "train_anchors": kr["train_anchors"], "receipt_sha256": sha(f"{W}/work/final/KING_FINAL_RECEIPT.json")},
           "f10_s42": {"source": mp, "model_pt_sha256": fr["model_sha256"], "deploy_file": npz, "deploy_sha256": sha(npz), "fold": "FINAL", "alpha": alpha,
                       "actual_gradient_cutoff": {"max_train_label_end": tt, "iso": iso(tt)}, "admission": fr["admission"],
                       "receipt_sha256": sha(f"{W}/work/final/F10_FINAL_RECEIPT_s42.json")},
           "V1_gate": {"spearman": rho, "maxabs": mx, "rows": 30000, "PASS": bool(ok), "rule": "spearman >= 0.99999 and maxabs <= 1e-5 (pod_f10_np_export.py)"},
           "torch": torch.__version__, "numpy": np.__version__, "device_sha256": sha(os.path.abspath(__file__))}
    json.dump(rec, open(f"{W}/receipts/P5_EXPORT.json", "w"), indent=1)
    print("FRESH_EXPORT", json.dumps({"king_sha": kr["model_sha256"], "king_cutoff": kr["max_train_label_end_iso"], "f10_np_sha": rec["f10_s42"]["deploy_sha256"],
                                      "f10_cutoff": iso(tt), "V1": rec["V1_gate"]}), flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
