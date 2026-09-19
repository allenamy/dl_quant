#!/usr/bin/env python3
"""Object B · S3 (PREREG §3 S3; comparison type (3) — no returns; NOT used by object B, ruling 1): rebuild mu/sd for the 20 monthly mE1cX7 RAW s42
checkpoints (bare state_dicts) and test them (B-REPRO). If the gate fails the path is reported UNAVAILABLE; stats recomputed on new data are NOT
substituted. Rule = trainer /workspace/review_scratch/pod_f10_train_monthly_v4.py (2147a7dd…) L42–51 (data, XL 171 cols; L282 asserts 171), L310–328 (fold rows,
EMBARGO=1, 85% split, rowsel = rows of tr1[::7], XS = rowsel[::3], mu = mean, sd = std + 1e-6 on the device) — RNG-free.
Reference = the trainer's own per-fold raw scores preds_fold/mE1cX7_<YM>.npz (P = mdl.f(nan_to_num(clamp((X − mu)/sd, −5, 5))) for every anchor
>= first test anchor; test-month rows == the merged OOF f10_v4RAW_s42.npy 58d64a6f). Gate per fold: identical finite support and max|d| <= 1e-6 on
the test-month cells. Runs on the GPU only if nvidia-smi shows no compute process (else CPU); records which."""
import os, sys, json, time, glob, hashlib, subprocess
import numpy as np
import torch, torch.nn as nn

R = "/workspace/object_b_2026-09-19"; MWF = "/workspace/f8_v4/mwf_v4b/RAW_s42"
SRC = {"trainer": ("/workspace/review_scratch/pod_f10_train_monthly_v4.py", "2147a7dd128be180ac6c5b01cde6d066413ac0333700deb887cef542cc8d50bb"),
       "targets": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
       "fea82": ("/workspace/dlw_v4raw/data/dlw_fea82.npz", "40608701cad1aea1d72936eb91e31cee4f10cd37fccf48d6b6f4a4b1c7d9389d"),
       "fea89": ("/workspace/f8_v4/data/f8_fea89.npz", "f7363889fa823a97d96374b6f504db5a2cb7491296e819bcce3899e8d1a021b4"),
       "oof": ("/workspace/f8_v4/mwf_v4b/RAW_s42/preds/f10_V2MAIN_RAW_mE1cX7_s42.npy", "c534316e522caba0489f4bc73c62528143b766c42fa45bd6f0a9bd138d155329"),
       "merge": ("/workspace/f8_v4/mwf_v4b/RAW_s42/results/merge.json", None)}
# NOTE (2026-09-19): the health-check copy f10_v4RAW_s42.npy pinned by S2 (58d64a6f) was rewritten on disk on 2026-09-18 13:4xZ (sha now 31581097);
# the reference used here is the monthly run's own stitched file, pinned in its merge receipt (stitched_sha256 c534316e), plus per-fold shas.
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
    MERGE = json.load(open(SRC["merge"][0]))["merged"]; assert MERGE["stitched_sha256"] == SRC["oof"][1] and MERGE["trainer_sha256"] == SRC["trainer"][1]
    assert MERGE["gate"]["targets_sha256"] == SRC["targets"][1] and MERGE["gate"]["fea82_sha256"] == SRC["fea82"][1] and MERGE["gate"]["fea89_sha256"] == SRC["fea89"][1]
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    DEV = "cuda" if (torch.cuda.is_available() and not apps) else "cpu"
    TG = np.load(SRC["targets"][0], allow_pickle=True); E_ts = TG["E_ts"].astype(np.int64); nA, NW = TG["y4s"].shape
    FE = np.load(SRC["fea82"][0], allow_pickle=True); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(SRC["fea89"][0], allow_pickle=True); assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.all(np.diff(pa) >= 0)
    XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); assert XL.shape[1] == 171, XL.shape   # trainer L282 asserts XT.shape[1] == 171 (its L50 comment "167" is stale)
    ST = np.searchsorted(pa, np.arange(nA + 1))
    XT = torch.from_numpy(XL).to(DEV); del XL, FE, F9
    OOF = np.load(SRC["oof"][0])
    ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])
    months = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]

    class Net(nn.Module):
        def __init__(s, d=171, h=256, p=0.1):
            super().__init__()
            s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
            s.a = nn.Parameter(torch.tensor(-2.303))
    folds = {}; t0 = time.time()
    for YM in months:
        pt = glob.glob(f"{MWF}/shard*/models/mE1cX7_{YM}.pt"); pf = glob.glob(f"{MWF}/shard*/preds_fold/mE1cX7_{YM}.npz"); cf = glob.glob(f"{MWF}/shard*/models/mE1cX7_{YM}_config.json")
        assert len(pt) == len(pf) == len(cf) == 1, (YM, pt, pf)
        conf = json.load(open(cf[0])); mf = MERGE["folds"][str(YM)]
        assert sha(pt[0]) == mf["pt_sha256"] and sha(pf[0]) == mf["preds_fold_sha256"], ("fold artefact sha != merge receipt", YM)
        te = np.where(ym == YM)[0]; first_te, last_te = int(te[0]), int(te[-1])
        tr_idx = np.array([i for i in range(first_te - EMBM) if ST[i + 1] - ST[i] >= 50])
        assert len(tr_idx) == conf["n_train"] and int(tr_idx[-1]) == conf["max_train_idx"], (YM, len(tr_idx), conf["n_train"])
        cut = int(len(tr_idx) * 0.85); tr1 = tr_idx[:cut]
        assert len(tr_idx) - cut == conf["n_val"], (YM, len(tr_idx) - cut, conf["n_val"])
        rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
        XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
        mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
        sdict = torch.load(pt[0], map_location=DEV, weights_only=False)
        mdl = Net().to(DEV); mdl.load_state_dict(sdict); mdl.eval()
        Z = np.load(pf[0]); P = Z["P"]; assert int(Z["first_te"]) == first_te
        mx = 0.0; supp_ok = True; n = 0
        with torch.no_grad():
            for i in range(first_te, last_te + 1):
                a0, b0 = int(ST[i]), int(ST[i + 1])
                if b0 - a0 < 50: continue
                x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                s = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy().astype(np.float32)
                ref = P[i - first_te, ps[a0:b0]]; oof = OOF[i, ps[a0:b0]]
                if not (np.array_equal(np.isfinite(ref), np.isfinite(s)) and np.array_equal(ref[np.isfinite(ref)], oof[np.isfinite(oof)])): supp_ok = False
                d = np.abs(s.astype(np.float64) - ref.astype(np.float64)); mx = max(mx, float(np.nanmax(d))); n += int(np.isfinite(d).sum())
        # save the rebuilt stats + a serving-format np export (combo_stage L160–168 form: w0,b0,w1,b1,w2,b2, mu, sd_) — usable only if this fold PASSes
        os.makedirs(f"{R}/models/monthly_mE1cX7_RAW_s42", exist_ok=True)
        SDn = {k: v.detach().cpu().numpy() for k, v in sdict.items()}
        npz = f"{R}/models/monthly_mE1cX7_RAW_s42/mE1cX7_{YM}_np.npz"
        np.savez(npz, w0=SDn["f.0.weight"], b0=SDn["f.0.bias"], w1=SDn["f.3.weight"], b1=SDn["f.3.bias"], w2=SDn["f.6.weight"], b2=SDn["f.6.bias"],
                 mu=mu.cpu().numpy().astype(np.float32), sd_=sd.cpu().numpy().astype(np.float32), alpha=np.float32(conf.get("alpha_final", np.nan)),
                 n_cols=np.int64(171), trained_through=np.int64(int(E_ts[int(tr_idx[-1])])), label_end=np.int64(int(E_ts[int(tr_idx[-1])]) + 14400))
        folds[str(YM)] = {"n_test_cells": n, "max_abs": mx, "support_and_oof_consistent": supp_ok, "PASS": bool(supp_ok and mx <= 1e-6), "np_export": npz, "np_export_sha256": sha(npz),
                          "pt_sha256": sha(pt[0]), "preds_fold_sha256": sha(pf[0]), "mu_sd_rows": int(len(rowsel[::3]))}
        print(YM, folds[str(YM)], flush=True)
    verdict = "PASS" if all(f["PASS"] for f in folds.values()) else "UNAVAILABLE"
    doc = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "comparison_type": "(3) packaging/prediction parity — not a return",
           "inputs_sha256": shas, "device_used": DEV, "torch": torch.__version__, "folds": folds, "B_REPRO_VERDICT": verdict,
           "rule": "UNAVAILABLE => stats recomputed on new data are NOT substituted (PREREG §3 S3)", "runtime_s": round(time.time() - t0, 1),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(doc, open(f"{R}/receipts/B_REPRO.json", "w"), indent=1)
    print("B_REPRO_VERDICT", verdict, "device", DEV, flush=True)


if __name__ == "__main__":
    main()
