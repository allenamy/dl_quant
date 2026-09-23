"""NEWS P5 model export (pod2, /workspace/venv torch): deploy files in the PRODUCTION formats.
  King: work/king/king_2026.txt (latest annual fold, the one that scores 2026) copied as slow2026.txt (LightGBM text model; production
        shadow_loop_v3 load_bundle reads shadow_bundle/slow2026.txt with lightgbm.Booster(model_file=...)).
  F10 s42: work/f10_s42/202609/model.pt (latest monthly fold) → f10_live_s42_np.npz with the keys production combo_stage L186-196 reads
        (w0,b0,w1,b1,w2,b2,mu,sd_) plus alpha / n_cols / trained_through (same layout as the in-service file, pod_f10_np_export.py).
Gate V1 (same as pod_f10_np_export.py): 30,000 real NEWS feature rows, production numpy inference (erf GELU, float32 arrays as in
combo_stage) vs torch eval: median Spearman >= 0.99999 and max|Δ| <= 1e-5, else exit 3. Also reports numpy-vs-GPU-OOF on the
202609 test anchors (the scores the evaluation used)."""
import os, sys, json, time, hashlib, shutil
import numpy as np
import torch
from scipy.stats import spearmanr
from scipy.special import erf
W = "/dev/shm/news_2026-09-23"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))


def np_infer(M, X171):
    """verbatim combo_stage.py L194-196 arithmetic"""
    xz_in = np.nan_to_num(np.clip((X171 - M["mu"]) / M["sd_"], -5, 5))
    h = gelu(xz_in @ M["w0"].T + M["b0"]); h = gelu(h @ M["w1"].T + M["b1"])
    return (h @ M["w2"].T + M["b2"]).squeeze(-1)


def main():
    out = f"{W}/deploy"; os.makedirs(out, exist_ok=True)
    kr = json.load(open(f"{W}/work/king/TRAIN_RECEIPT.json")); k26 = [f for f in kr["folds"] if f["fold"] == "2026"][0]
    assert sha(k26["model_path"]) == k26["model_sha256"]
    shutil.copy2(k26["model_path"], f"{out}/slow2026.txt"); assert sha(f"{out}/slow2026.txt") == k26["model_sha256"]
    fr = json.load(open(f"{W}/work/f10_s42/202609/FOLD_RECEIPT.json")); mp = f"{W}/work/f10_s42/202609/model.pt"
    assert sha(mp) == fr["model_sha256"] and fr["fold"] == "202609" and fr["seed"] == 42
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
    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); X = np.concatenate([F["X82"].astype(np.float32), F["X89"]], 1)
    rng = np.random.default_rng(0); sel = rng.choice(len(X), 30000, replace=False); XL = X[sel]
    s_np = np_infer(M, XL)
    net = torch.nn.Sequential(torch.nn.Linear(171, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 256), torch.nn.GELU(), torch.nn.Dropout(.1), torch.nn.Linear(256, 1))
    net.load_state_dict({k[2:]: v for k, v in sd.items() if k.startswith("f.")}); net.eval()
    with torch.no_grad():
        s_t = net(torch.clamp((torch.from_numpy(XL) - ck["mu"].cpu()) / ck["sd"].cpu(), -5, 5)).squeeze(-1).numpy()
    rho = float(spearmanr(s_np, s_t).correlation); mx = float(np.abs(s_np.astype(np.float64) - s_t).max())
    ok = rho >= 0.99999 and mx <= 1e-5
    # numpy (serving) vs the GPU OOF the evaluation used, on the 202609 test anchors
    sc = np.load(f"{W}/work/f10_s42/202609/scores.npz"); rows = sc["rows"]; P = sc["P"]; off = F["off"]
    dmax = 0.0; rk_mis = 0; n_an = 0
    for k, i in enumerate(rows):
        if off[i + 1] - off[i] < 50: continue
        m = F["m"][off[i]:off[i + 1]].astype(int); x = X[off[i]:off[i + 1]]; s1 = np_infer(M, x); s0 = P[k, m]
        dmax = max(dmax, float(np.abs(s1.astype(np.float64) - s0).max())); n_an += 1
        rk_mis += int((np.argsort(np.argsort(s1)) != np.argsort(np.argsort(s0))).sum())
    rec = {"king": {"source": k26["model_path"], "sha256": k26["model_sha256"], "deploy_file": f"{out}/slow2026.txt", "fold": "2026",
                    "max_train_label_end": k26["max_train_label_end"], "score_start": k26["score_start"]},
           "f10_s42": {"source": mp, "model_pt_sha256": fr["model_sha256"], "deploy_file": npz, "deploy_sha256": sha(npz), "fold": "202609",
                       "alpha": alpha, "trained_through(max_train_label_end)": tt, "admission": fr["admission"]},
           "V1_gate": {"spearman": rho, "maxabs": mx, "rows": 30000, "PASS": bool(ok), "rule": "spearman >= 0.99999 and maxabs <= 1e-5 (pod_f10_np_export.py)"},
           "numpy_vs_gpu_oof_202609": {"anchors": n_an, "max_abs": dmax, "within_anchor_rank_mismatch_cells": rk_mis},
           "torch": torch.__version__, "numpy": np.__version__, "device_sha256": sha(os.path.abspath(__file__))}
    json.dump(rec, open(f"{W}/receipts/P5_EXPORT.json", "w"), indent=1)
    print("EXPORT", json.dumps({"king_sha": k26["model_sha256"], "f10_np_sha": rec["f10_s42"]["deploy_sha256"], "V1": rec["V1_gate"], "gpu_vs_np": rec["numpy_vs_gpu_oof_202609"]}), flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
