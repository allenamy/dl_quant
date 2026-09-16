#!/usr/bin/env python3
"""fm_gate_b_repro.py -- GATE B-REPRO, the precondition for arm B. pod2, READ-ONLY, CPU only.

PREREG (FROZEN 2026-09-16, sha256 d17ea08949e8d2c731327b75d14dc3c4cf5bc75ec5584b5a63ddfc84fe73f671) section 2.1:

  > For each fold, recompute the training-time mapping on the OLD input by re-running the trainer's own calibration
  > lines, then score the OLD input through the saved checkpoint. The result must reproduce that fold's stored OOF
  > predictions -- DL to the trainer's own asserted tolerance (test_vs_all_maxdiff <= 1e-5).
  > If GATE B-REPRO fails for a family, arm B is NOT AVAILABLE for that family and will be reported as unavailable.
  > It will not be substituted, approximated, or replaced by the refit checkpoint.

Why this gate exists: the DL monthly fold checkpoints store a BARE state_dict -- no mu/sd, and none in their config
(FACT_TABLE_MODEL section 1.3(d)). The only checkpoints carrying their own mapping are the refits, trained through
2026-08-30, which cannot be the out-of-sample forward model. So arm B needs the training-time mu/sd RECONSTRUCTED, and
a reconstruction is inadmissible until it is shown to reproduce what the fold actually produced.

The reconstruction is exact in principle because the calibration block is RNG-free and precedes seeding
(pod_f10_train_monthly.py L323-328, seeding at L330+). This device tests that in practice.

Reproduced verbatim from pod_f10_train_monthly.py (sha 7bb39f8d93f2daf749535f8a6d91aecd15e8e3361de80138a29c6fbb6270b51e):
  L42-50  XL = concat([dlw_fea82 X (82), f8_fea89 X (89)], 1).astype(float32)   -> 171 columns
  L91     ST = np.searchsorted(pa, np.arange(nA + 1))
  L323-328 tr_idx / cut 0.85 / rowsel = tr1[::7] anchors then [::3] rows / mu,sd = nan_to_num(XS).mean,std + 1e-6
  L154-158 Net(d=171, h=256, p=0.1): Linear-GELU-Dropout-Linear-GELU-Dropout-Linear, scored via mdl.f
  L378    mdl.eval()   (dropout off, deterministic)
  L412-419 PA[i-first_te, ps[a0:b0]] = mdl.f(nan_to_num(clamp((XT[a0:b0]-mu)/sd, -5, 5))).squeeze(-1)

DECLARED IN ADVANCE: the fold was trained on GPU (DEV = cuda if available); this runs on CPU. Small float differences
between CPU and GPU GEMM are expected. The gate's tolerance is the trainer's own 1e-5, and the observed maxabs is
reported whatever it is. If the gate fails ONLY because of a CPU/GPU arithmetic gap, that is reported as such and NOT
waved through -- a retry on GPU would then be announced first, per the GPU rule.

Writes nothing but its receipt. No network, no venue, nothing under ~/wide_shadow or ~/dl_quant_live.

Usage: FM_GB_OUT=<receipt.json> [FM_GB_TAG=mE1] [FM_GB_FOLDS=all|202608,...] python3 fm_gate_b_repro.py
"""
import os, sys, json, time, hashlib
import numpy as np
import torch, torch.nn as nn

T0 = time.time()
OUT = os.environ["FM_GB_OUT"]
TAG = os.environ.get("FM_GB_TAG", "mE1")
WANT = os.environ.get("FM_GB_FOLDS", "all")
D = "/workspace/review_scratch/dl_monthly_wf"
DLW = "/workspace/dlw_ext"
F8 = "/workspace/f8_ext"
TRAINER = f"{D}/pod_f10_train_monthly.py"
TRAINER_SHA = "7bb39f8d93f2daf749535f8a6d91aecd15e8e3361de80138a29c6fbb6270b51e"
TOL = 1e-5                      # the trainer's own asserted tolerance (L422)
torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "4")))


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


class Net(nn.Module):
    """pod_f10_train_monthly.py L154-158, with PLEON=0 and REC=0 as the env whitelist asserts."""
    def __init__(s, d, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__, "torch": torch.__version__,
          "prereg_sha256": "d17ea08949e8d2c731327b75d14dc3c4cf5bc75ec5584b5a63ddfc84fe73f671",
          "gate": "B-REPRO", "tag": TAG, "tolerance": TOL, "device_used": "cpu",
          "cpu_gpu_caveat": "the fold was trained on GPU; this runs on CPU. A failure caused only by CPU/GPU GEMM "
                            "differences is reported as such and is NOT waved through.",
          "writes_nothing_but_the_receipt": True, "inputs": {}}
    got = sha(TRAINER)
    rc["inputs"][TRAINER] = got
    assert got == TRAINER_SHA, ("TRAINER SHA MISMATCH", got)

    TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
    y4s = TG["y4s"]
    nA, NW = y4s.shape
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
    X82 = FE["X"]
    pa = FE["pair_a"].astype(np.int64)
    ps = FE["pair_s"].astype(np.int64)
    F9 = np.load(f"{F8}/data/f8_fea89.npz", allow_pickle=True)
    assert np.array_equal(F9["pair_a"].astype(np.int64), pa), "pair_a mismatch fea82 vs fea89"
    assert np.all(np.diff(pa) >= 0), "pairs must be anchor-sorted"
    XL = np.concatenate([X82, F9["X"]], 1).astype(np.float32)
    del X82
    ST = np.searchsorted(pa, np.arange(nA + 1))
    XT = torch.from_numpy(XL)
    rc["shapes"] = {"nA": int(nA), "NW": int(NW), "rows": int(XL.shape[0]), "cols": int(XL.shape[1])}
    assert XL.shape[1] == 171, XL.shape
    log("XT built", XL.shape, "nA", nA)

    cfgs = sorted(f for f in os.listdir(f"{D}/models") if f.startswith(TAG + "_") and f.endswith("_config.json"))
    folds = [int(f.split("_")[1]) for f in cfgs]
    if WANT != "all":
        keep = set(int(x) for x in WANT.split(","))
        folds = [y for y in folds if y in keep]
    rc["folds_requested"] = folds
    log("folds", len(folds))

    results = []
    for ym in folds:
        t1 = time.time()
        cfg = json.load(open(f"{D}/models/{TAG}_{ym}_config.json"))
        embm = int(cfg["embargo_anchors"])
        pf = np.load(f"{D}/preds_fold/{TAG}_{ym}.npz")
        first_te, last_te = int(pf["first_te"]), int(pf["last_te"])
        P_stored = pf["P"]

        # --- the trainer's calibration block, verbatim (L323-328) ---
        tr_idx = np.array([i for i in range(first_te - embm) if ST[i + 1] - ST[i] >= 50])
        cut = int(len(tr_idx) * 0.85)
        tr1 = tr_idx[:cut]
        rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
        XS = XT[torch.from_numpy(rowsel[::3])]
        mu = torch.nan_to_num(XS).mean(0)
        sd = torch.nan_to_num(XS).std(0) + 1e-6
        del XS

        mdl = Net(XT.shape[1])
        state = torch.load(f"{D}/models/{TAG}_{ym}.pt", map_location="cpu", weights_only=False)
        missing = mdl.load_state_dict(state, strict=False)
        mdl.eval()

        PA = np.full((nA - first_te, NW), np.nan, np.float32)
        with torch.no_grad():
            for i in range(first_te, nA):
                a0, b0 = int(ST[i]), int(ST[i + 1])
                if b0 - a0 < 50:
                    continue
                x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                PA[i - first_te, ps[a0:b0]] = mdl.f(torch.nan_to_num(x)).squeeze(-1).numpy()

        fin_s, fin_r = np.isfinite(P_stored), np.isfinite(PA)
        pat = bool(np.array_equal(fin_s, fin_r))
        both = fin_s & fin_r
        mx = float(np.max(np.abs(P_stored[both] - PA[both]))) if both.any() else float("nan")
        nt = last_te - first_te + 1
        both_t = both[:nt]
        mx_t = float(np.max(np.abs(P_stored[:nt][both_t] - PA[:nt][both_t]))) if both_t.any() else float("nan")
        r = {"fold": ym, "n_train_anchors": int(len(tr_idx)), "calib_rows": int(len(rowsel[::3])),
             "first_te": first_te, "last_te": last_te,
             "nan_pattern_equal": pat, "cells_compared": int(both.sum()),
             "maxabs_full_P": mx, "maxabs_test_span_only": mx_t,
             "PASS_full": bool(pat and mx <= TOL), "PASS_test_span": bool(mx_t <= TOL),
             "missing_keys": list(missing.missing_keys), "unexpected_keys": list(missing.unexpected_keys),
             "wall_s": round(time.time() - t1, 1)}
        results.append(r)
        print("fold %d  pattern=%s  maxabs_full=%.3e  maxabs_test=%.3e  PASS_full=%s  (%.0fs)"
              % (ym, pat, mx, mx_t, r["PASS_full"], r["wall_s"]), flush=True)

    rc["per_fold"] = results
    n_pass = sum(1 for r in results if r["PASS_full"])
    worst = max((r["maxabs_full_P"] for r in results if np.isfinite(r["maxabs_full_P"])), default=float("nan"))
    rc["summary"] = {"folds": len(results), "PASS_full": n_pass, "FAIL_full": len(results) - n_pass,
                     "worst_maxabs": worst, "tolerance": TOL,
                     "all_nan_patterns_equal": all(r["nan_pattern_equal"] for r in results)}
    rc["GATE_B_REPRO"] = "PASS" if (n_pass == len(results) and results) else "FAIL"
    rc["consequence"] = ("arm B is AVAILABLE for the DL family: the training-time mu/sd is exactly reconstructible and "
                         "the reconstruction reproduces what the fold actually produced."
                         if rc["GATE_B_REPRO"] == "PASS" else
                         "arm B is NOT AVAILABLE for the DL family on these folds. Per the frozen prereg it will be "
                         "reported as unavailable and NOT substituted, approximated or replaced by the refit checkpoint.")
    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("GATE_B_REPRO=%s  %d/%d folds pass  worst_maxabs=%.3e  tol=%.0e  wall=%.0fs"
          % (rc["GATE_B_REPRO"], n_pass, len(results), worst, TOL, rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
