#!/usr/bin/env python3
"""fm_o6_export_gate_recheck.py -- FACT_TABLE_MODEL open row O6, READ-ONLY.

Question: the in-service deployable model `/workspace/f8_ext/models/f10_live_s42_np.npz` exists, but TRN-28 established
that `pod_f10_np_export.py` writes that file at L56-57 **before** its own V1 parity gate verdict is known (`ok` is
computed at L55, PASS/FAIL printed at L58, exit 0/3 at L59). So the file's existence is not evidence that its gate
passed -- and a search of pod2 found **no surviving log of the 2026-09-01 export's verdict**.

This device does NOT re-run the exporter. Running `pod_f10_np_export.py` would WRITE to `{F10_OUT}/models/`, whose
default is the in-service artifact path, i.e. it would overwrite the live file. Instead this reproduces the gate's
comparison read-only, on the artifacts as they stand:

  G0  IDENTITY   does the deployed npz actually correspond to the checkpoint beside it? Compare w0/b0/w1/b1/w2/b2
                 against `f10_live_s42.pt`'s state_dict (f.0/f.3/f.6) and mu/sd_ against the checkpoint's mu/sd,
                 bitwise via integer views. If this fails, the npz was produced from a DIFFERENT .pt and nothing else
                 in the file can be trusted.
  G1  V1 GATE    the exporter's own check, same construction: 30,000 real feature rows drawn with
                 `np.random.default_rng(0)` exactly as the exporter draws them, scored through (a) torch eval on the
                 checkpoint and (b) the numpy path the producer uses (GELU via erf, float64). Thresholds are the
                 exporter's own: spearman >= 0.99999 and maxabs <= 1e-5.
  G2  PRODUCER   the same numpy path but using the DEPLOYED npz's own w/mu/sd_ rather than the checkpoint's, because
                 that is what `combo_stage.py:165-166` actually executes in production.

Nothing is written except the receipt. No GPU. No network. No venue. Nothing under ~/wide_shadow or ~/dl_quant_live.

Usage: FM_O6_OUT=<receipt.json> python3 fm_o6_export_gate_recheck.py
"""
import os, sys, json, time, hashlib
import numpy as np
import torch, torch.nn as nn
from scipy.stats import spearmanr
from scipy.special import erf

T0 = time.time()
OUT = os.environ["FM_O6_OUT"]
F8 = "/workspace/f8_ext"
DLW = "/workspace/dlw_ext"
CK = f"{F8}/models/f10_live_s42.pt"
NP = f"{F8}/models/f10_live_s42_np.npz"
LIVE_NP_SHA = "351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4"   # == ~/wide_shadow/fea171 copy


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def biteq(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape:
        return False, {"shape_a": list(a.shape), "shape_b": list(b.shape)}
    ai, bi = a.astype(np.float64), b.astype(np.float64)
    iv = ai.view(np.uint64) != bi.view(np.uint64)
    return int(iv.sum()) == 0, {"differing": int(iv.sum()), "total": int(a.size),
                                "maxabs": float(np.max(np.abs(ai - bi))) if a.size else 0.0}


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__, "torch": torch.__version__,
          "question": "O6: did the in-service f10_live_s42_np.npz pass its own V1 parity gate? The exporter writes the "
                      "file before the verdict (TRN-28) and no log of the 2026-09-01 verdict survives on pod2.",
          "writes_nothing_but_the_receipt": True,
          "inputs": {CK: sha(CK), NP: sha(NP)}}
    rc["deployed_npz_is_the_live_one"] = (rc["inputs"][NP] == LIVE_NP_SHA)
    log("input shas read; deployed==live:", rc["deployed_npz_is_the_live_one"])

    ck = torch.load(CK, map_location="cpu", weights_only=False)
    sd = ck["state_dict"]
    M = np.load(NP, allow_pickle=True)
    mu_ck = ck["mu"].numpy().astype(np.float64)
    sd_ck = ck["sd"].numpy().astype(np.float64)

    # ---- G0 identity: is the deployed npz this checkpoint? ----
    pairs = [("w0", "f.0.weight"), ("b0", "f.0.bias"), ("w1", "f.3.weight"), ("b1", "f.3.bias"),
             ("w2", "f.6.weight"), ("b2", "f.6.bias")]
    g0 = {}
    ok0 = True
    for nk, tk in pairs:
        eq, det = biteq(M[nk], sd[tk].numpy())
        g0[nk] = {"bitwise_equal": eq, **det}
        ok0 = ok0 and eq
    for nk, arr in (("mu", mu_ck), ("sd_", sd_ck)):
        eq, det = biteq(M[nk], arr)
        g0[nk] = {"bitwise_equal": eq, **det}
        ok0 = ok0 and eq
    rc["G0_identity_npz_matches_checkpoint"] = {"PASS": bool(ok0), "per_array": g0,
                                                "meaning": "if FAIL, the deployed npz came from a different .pt and "
                                                           "nothing else here is interpretable"}
    log("G0 identity:", "PASS" if ok0 else "FAIL")

    # ---- reproduce the exporter's row draw exactly ----
    FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
    F9 = np.load(f"{F8}/data/f8_fea89.npz", allow_pickle=True)
    rc["inputs"][f"{DLW}/data/dlw_fea82.npz"] = "not hashed (466MB; identity by path+shape)"
    rng = np.random.default_rng(0)                       # exporter's own seed
    n_rows = FE["X"].shape[0]
    sel = rng.choice(n_rows, 30000, replace=False)       # exporter's own draw
    XL = np.concatenate([FE["X"][sel].astype(np.float32), F9["X"][sel].astype(np.float32)], 1)
    rc["gate_rows"] = {"n_rows_in_fea82": int(n_rows), "n_drawn": 30000, "n_cols": int(XL.shape[1]),
                       "draw": "np.random.default_rng(0).choice(n, 30000, replace=False), identical to the exporter"}
    log("rows drawn", XL.shape)

    def np_score(W, mu, sdv):
        xz = np.nan_to_num(np.clip((XL - mu) / sdv, -5, 5)).astype(np.float64)
        def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
        h = gelu(xz @ W["w0"].T.astype(np.float64) + W["b0"].astype(np.float64))
        h = gelu(h @ W["w1"].T.astype(np.float64) + W["b1"].astype(np.float64))
        return (h @ W["w2"].T.astype(np.float64) + W["b2"].astype(np.float64)).squeeze(-1)

    class Net(nn.Module):
        def __init__(s, d=171, h=256, p=0.1):
            super().__init__()
            s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                                nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        def forward(s, x): return s.f(x).squeeze(-1)

    net = Net()
    net.load_state_dict({k: v for k, v in sd.items() if k.startswith("f.")}, strict=False)
    net.eval()
    xz_t = np.nan_to_num(np.clip((XL - mu_ck) / sd_ck, -5, 5))
    with torch.no_grad():
        s_t = net(torch.from_numpy(xz_t.astype(np.float32))).numpy().astype(np.float64)

    Wck = {"w0": sd["f.0.weight"].numpy(), "b0": sd["f.0.bias"].numpy(),
           "w1": sd["f.3.weight"].numpy(), "b1": sd["f.3.bias"].numpy(),
           "w2": sd["f.6.weight"].numpy(), "b2": sd["f.6.bias"].numpy()}
    s_np_ck = np_score(Wck, mu_ck, sd_ck)
    rho = float(spearmanr(s_np_ck, s_t).correlation)
    mx = float(np.abs(s_np_ck - s_t).max())
    passed = bool(rho >= 0.99999 and mx <= 1e-5)
    rc["G1_V1_gate_reproduced"] = {"spearman": rho, "maxabs": mx, "thresholds": {"spearman_min": 0.99999, "maxabs_max": 1e-5},
                                   "PASS": passed, "note": "the exporter's own check, reproduced without writing anything"}
    log("G1 V1 gate:", "PASS" if passed else "FAIL", rho, mx)

    Wnp = {k: M[k] for k in ("w0", "b0", "w1", "b1", "w2", "b2")}
    s_np_dep = np_score(Wnp, M["mu"].astype(np.float64), M["sd_"].astype(np.float64))
    rho2 = float(spearmanr(s_np_dep, s_t).correlation)
    mx2 = float(np.abs(s_np_dep - s_t).max())
    rc["G2_deployed_weights_vs_checkpoint"] = {"spearman": rho2, "maxabs": mx2,
                                               "PASS": bool(rho2 >= 0.99999 and mx2 <= 1e-5),
                                               "note": "scores the DEPLOYED npz's own w/mu/sd_ through the production "
                                                       "numpy path (combo_stage.py L165-166) against torch on the "
                                                       "checkpoint -- this is the contrast production actually depends on"}
    log("G2 deployed:", rc["G2_deployed_weights_vs_checkpoint"]["PASS"], rho2, mx2)

    rc["verdict"] = {
        "gate_verdict_recoverable_from_logs": False,
        "gate_verdict_reproduced_now": rc["G1_V1_gate_reproduced"]["PASS"],
        "reading": ("The 2026-09-01 verdict itself is unrecoverable -- no log survives and the artifact would exist "
                    "either way (TRN-28). What CAN be established is whether the artifacts as they stand satisfy the "
                    "gate today, which is what G0/G1/G2 report. A PASS today does not prove the original run passed; "
                    "it proves the deployed file is consistent with its checkpoint now.")}
    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("SUMMARY G0=%s G1=%s G2=%s rho=%.9f maxabs=%.3e wall=%.1fs"
          % (rc["G0_identity_npz_matches_checkpoint"]["PASS"], rc["G1_V1_gate_reproduced"]["PASS"],
             rc["G2_deployed_weights_vs_checkpoint"]["PASS"], rho, mx, rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
