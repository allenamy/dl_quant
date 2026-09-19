#!/usr/bin/env python3
"""PREREG AMENDMENT 5 A5.2 post-processing (comparison type (3), no returns):
  M-REPRO  the derived trainer's re-run of fold 202501 (work/mwf_ext/repro) vs the stored v4b checkpoint (merge receipt pt a6dd82e4…, preds_fold e44d7a51…):
           every state_dict tensor bitwise and the preds_fold P array bitwise => PASS, else NEW_DRAW (new folds still usable, labelled).
  new folds 202301..202412 (work/mwf_ext/shard*): mu/sd rebuilt by the B-REPRO rule (trainer L310–328, RNG-free, on the device), predictions recomputed
           on the test months must equal the fold's own preds_fold P (support equal, max|d| <= 1e-6) else that fold is UNAVAILABLE; serving-format np export
           (w0,b0,w1,b1,w2,b2, mu, sd_) with trained_through / label_end (= config max_train_label_end anchor + 4h).
GPU only if nvidia-smi shows no compute process (else CPU); records which. Writes models/monthly_mE1cX7_RAW_s42_ext/ and receipts/M_REPRO_V4.json."""
import os, sys, json, time, glob, hashlib, subprocess, calendar
import numpy as np
import torch, torch.nn as nn

R = "/workspace/object_b_2026-09-19"; W = f"{R}/work/mwf_ext"; OUTM = f"{R}/models/monthly_mE1cX7_RAW_s42_ext"
SRC = {"targets": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
       "fea82": ("/workspace/dlw_v4raw/data/dlw_fea82.npz", "40608701cad1aea1d72936eb91e31cee4f10cd37fccf48d6b6f4a4b1c7d9389d"),
       "fea89": ("/workspace/f8_v4/data/f8_fea89.npz", "f7363889fa823a97d96374b6f504db5a2cb7491296e819bcce3899e8d1a021b4"),
       "merge": ("/workspace/f8_v4/mwf_v4b/RAW_s42/results/merge.json", None), "derived_trainer": (f"{R}/devices/pod_f10_train_monthly_ext.py", "0e405b9715133c2df1260ca7403a40f22438259db88335b51046170cdf20a517")}
EMBM = 1


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()


def main():
    shas = {}
    for k, (p, s) in SRC.items():
        got = sha(p); shas[k] = got
        if s is not None: assert got == s, (k, got)
    MERGE = json.load(open(SRC["merge"][0]))["merged"]
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    DEV = "cuda" if (torch.cuda.is_available() and not apps) else "cpu"
    # ── M-REPRO ──
    st_pt = glob.glob("/workspace/f8_v4/mwf_v4b/RAW_s42/shard*/models/mE1cX7_202501.pt")[0]; st_pf = glob.glob("/workspace/f8_v4/mwf_v4b/RAW_s42/shard*/preds_fold/mE1cX7_202501.npz")[0]
    assert sha(st_pt) == MERGE["folds"]["202501"]["pt_sha256"] and sha(st_pf) == MERGE["folds"]["202501"]["preds_fold_sha256"]
    a = torch.load(st_pt, map_location="cpu", weights_only=False); b = torch.load(f"{W}/repro/models/mE1cX7_202501.pt", map_location="cpu", weights_only=False)
    tens = {k: bool(torch.equal(a[k], b[k])) for k in sorted(set(a) | set(b)) if k in a and k in b}
    Pa = np.load(st_pf)["P"]; Pb = np.load(f"{W}/repro/preds_fold/mE1cX7_202501.npz")["P"]
    p_eq = bool(np.array_equal(Pa, Pb, equal_nan=True))
    mrep = {"stored_pt_sha256": sha(st_pt), "repro_pt_sha256": sha(f"{W}/repro/models/mE1cX7_202501.pt"), "tensors_bitwise": tens, "preds_fold_P_bitwise": p_eq,
            "VERDICT": "PASS" if (all(tens.values()) and len(tens) == len(a) and p_eq) else "NEW_DRAW"}
    if mrep["VERDICT"] != "PASS":
        mrep["P_max_abs"] = float(np.nanmax(np.abs(Pa.astype(np.float64) - Pb.astype(np.float64))))
    print("M_REPRO", mrep["VERDICT"], flush=True)
    # ── new folds: rebuild mu/sd, check against own preds_fold, export ──
    TG = np.load(SRC["targets"][0], allow_pickle=True); E_ts = TG["E_ts"].astype(np.int64); nA, NW = TG["y4s"].shape
    FE = np.load(SRC["fea82"][0], allow_pickle=True); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(SRC["fea89"][0], allow_pickle=True); assert np.array_equal(F9["pair_a"].astype(np.int64), pa)
    XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); assert XL.shape[1] == 171
    ST = np.searchsorted(pa, np.arange(nA + 1)); XT = torch.from_numpy(XL).to(DEV); del XL, FE, F9
    ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])

    class Net(nn.Module):
        def __init__(s, d=171, h=256, p=0.1):
            super().__init__()
            s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
            s.a = nn.Parameter(torch.tensor(-2.303))
    os.makedirs(OUTM, exist_ok=True); folds = {}
    months = [202301 + k for k in range(12)] + [202401 + k for k in range(12)]
    for YM in months:
        pt = glob.glob(f"{W}/shard*/models/mE1cX7_{YM}.pt"); pf = glob.glob(f"{W}/shard*/preds_fold/mE1cX7_{YM}.npz"); cf = glob.glob(f"{W}/shard*/models/mE1cX7_{YM}_config.json")
        if not (len(pt) == len(pf) == len(cf) == 1): folds[str(YM)] = {"PASS": False, "why": "fold artefacts missing"}; continue
        conf = json.load(open(cf[0]))
        te = np.where(ym == YM)[0]; first_te, last_te = int(te[0]), int(te[-1])
        tr_idx = np.array([i for i in range(first_te - EMBM) if ST[i + 1] - ST[i] >= 50])
        assert len(tr_idx) == conf["n_train"] and int(tr_idx[-1]) == conf["max_train_idx"], (YM,)
        cut = int(len(tr_idx) * 0.85); tr1 = tr_idx[:cut]; assert len(tr_idx) - cut == conf["n_val"]
        rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
        XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]; mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
        sdict = torch.load(pt[0], map_location=DEV, weights_only=False); mdl = Net().to(DEV); mdl.load_state_dict(sdict); mdl.eval()
        P = np.load(pf[0])["P"]; mx = 0.0; supp = True; n = 0
        with torch.no_grad():
            for i in range(first_te, last_te + 1):
                a0, b0 = int(ST[i]), int(ST[i + 1])
                if b0 - a0 < 50: continue
                s_ = mdl.f(torch.nan_to_num(torch.clamp((XT[a0:b0] - mu) / sd, -5, 5))).squeeze(-1).cpu().numpy().astype(np.float32)
                ref = P[i - first_te, ps[a0:b0]]
                if not np.array_equal(np.isfinite(ref), np.isfinite(s_)): supp = False
                d = np.abs(s_.astype(np.float64) - ref.astype(np.float64)); mx = max(mx, float(np.nanmax(d))); n += int(np.isfinite(d).sum())
        tt = int(E_ts[int(tr_idx[-1])]); SDn = {k: v.detach().cpu().numpy() for k, v in sdict.items()}
        npz = f"{OUTM}/mE1cX7_{YM}_np.npz"
        np.savez(npz, w0=SDn["f.0.weight"], b0=SDn["f.0.bias"], w1=SDn["f.3.weight"], b1=SDn["f.3.bias"], w2=SDn["f.6.weight"], b2=SDn["f.6.bias"],
                 mu=mu.cpu().numpy().astype(np.float32), sd_=sd.cpu().numpy().astype(np.float32), alpha=np.float32(conf.get("alpha_final", np.nan)),
                 n_cols=np.int64(171), trained_through=np.int64(tt), label_end=np.int64(tt + 14400))
        folds[str(YM)] = {"n_test_cells": n, "max_abs": mx, "support_equal": supp, "PASS": bool(supp and mx <= 1e-6), "max_train_label_end": conf["max_train_label_end"],
                          "label_end_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(tt + 14400)), "best_epoch": conf.get("best_epoch"), "pt_sha256": sha(pt[0]),
                          "preds_fold_sha256": sha(pf[0]), "np_export": npz, "np_export_sha256": sha(npz)}
        print(YM, {k: folds[str(YM)][k] for k in ("n_test_cells", "max_abs", "PASS", "label_end_utc")}, flush=True)
    doc = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "comparison_type": "(3) packaging/prediction parity — not a return",
           "inputs_sha256": shas, "device_used": DEV, "torch": torch.__version__, "M_REPRO": mrep, "new_folds": folds,
           "n_new_folds_pass": sum(1 for f in folds.values() if f.get("PASS")), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(doc, open(f"{R}/receipts/M_REPRO_V4.json", "w"), indent=1)
    print("M_REPRO_V4", mrep["VERDICT"], "new folds PASS", doc["n_new_folds_pass"], "/", len(months), "device", DEV, flush=True)


if __name__ == "__main__":
    main()
