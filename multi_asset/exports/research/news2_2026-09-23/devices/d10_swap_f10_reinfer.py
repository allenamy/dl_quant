#!/usr/bin/env python3
"""d10_swap_f10_reinfer.py -- line D stage 3: SAME F10 weights (every fold's model.pt of the delivered seed), funding inputs swapped.
PLAN_funding_only_control_cell rev 1 R1.2 stage 3; lead: identity must reproduce F10_OOF bitwise or no number is produced.

Inference path = news2_train_f10.py L127-L131 verbatim in structure (Net IMPORTED from that file; per anchor with >= 50 members:
clamp((X - mu) / sd, -5, 5) -> model.f -> squeeze), on the same device class it was trained on (cuda), X = [X82, X89] float32.
  C2  identity : ORIGINAL NEWS_FEATURES X -> every fold's scores == its scores.npz P, bitwise, and the merged P == F10_OOF.npz P.
  C2b red      : one input cell of X82 col 80 moved by +1 on a scored row -> that row's score must change.
  SWAP         : X82 cols 80/81 from NEWS_FEATURES_D10 (stage 2c) -> F10_OOF_SWAP.npz; nothing else of X differs (asserted).
usage (GPU, behind the run gate): d10_swap_f10_reinfer.py --features NF --features-sha S --swapped NFD10 --swapped-sha S2
                                   --f10-dir DIR --oof-sha S3 --cut EPOCH --out-dir OUT
"""
import argparse, hashlib, json, os, sys, time
import numpy as np

sys.path.insert(0, "/dev/shm/news2_2026-09-23/devices")
import torch
import news2_train_f10 as T


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def stop(msg):
    print("STOP", msg, flush=True); raise SystemExit(3)


def infer(XT, st, ps, a, fold_dir, tag, start, end, w, dev):
    ck = torch.load(os.path.join(fold_dir, tag, "model.pt"), map_location=dev)
    model = T.Net().to(dev); model.load_state_dict(ck["state_dict"]); model.eval()
    mu, sd = ck["mu"].to(dev), ck["sd"].to(dev)
    te = np.flatnonzero((a >= start) & (a < end)); pred = np.full((len(te), w), np.nan, np.float32)
    with torch.no_grad():
        for k, i in enumerate(te):
            if st[i + 1] - st[i] < 50: continue
            xx = torch.clamp((XT[st[i]:st[i + 1]] - mu) / sd, -5, 5)
            pred[k, ps[st[i]:st[i + 1]]] = model.f(xx).squeeze(-1).cpu().numpy()
    return te, pred, model, mu, sd


def bits_differ(x, y):
    same = (x.view(np.uint32) == y.view(np.uint32)) | (np.isnan(x) & np.isnan(y))
    return int((~same).sum())


def main():
    ap = argparse.ArgumentParser()
    for k in ("--features", "--features-sha", "--swapped", "--swapped-sha", "--f10-dir", "--oof-sha", "--out-dir"): ap.add_argument(k, required=True)
    ap.add_argument("--cut", type=int, required=True)
    a_ = ap.parse_args()
    dev = "cuda"
    for p, s in ((a_.features, a_.features_sha), (a_.swapped, a_.swapped_sha), (os.path.join(a_.f10_dir, "F10_OOF.npz"), a_.oof_sha)):
        if sha(p) != s: stop(f"sha {p}")
    op = os.path.join(a_.out_dir, "F10_OOF_SWAP.npz")
    if os.path.exists(op): stop("refusing to overwrite")
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "trainer_sha256": sha(T.__file__), "torch": torch.__version__,
           "gpu": torch.cuda.get_device_name(0), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "argv": sys.argv[1:]}
    F = np.load(a_.features); G = np.load(a_.swapped)
    a = F["anchors"].astype(np.int64); cnt = F["count"]; off = F["off"]; w = len(F["symbols"])
    pa = np.repeat(np.arange(len(a)), cnt).astype(int); ps = F["m"].astype(int); st = np.searchsorted(pa, np.arange(len(a) + 1))
    x0 = np.concatenate([F["X82"].astype(np.float32), F["X89"]], 1).astype(np.float32)
    x1 = np.concatenate([G["X82"].astype(np.float32), G["X89"]], 1).astype(np.float32)
    other = [c for c in range(171) if c not in (80, 81)]
    if bits_differ(x0[:, other], x1[:, other]): stop("swapped features differ outside X82 cols 80/81")
    rec["input_rows_differ"] = {"col80_fund_ema": bits_differ(x0[:, 80], x1[:, 80]), "col81_fund_now": bits_differ(x0[:, 81], x1[:, 81])}
    OOF = np.load(os.path.join(a_.f10_dir, "F10_OOF.npz"))["P"]
    specs = T.fold_specs(a)
    XT0 = torch.from_numpy(x0).to(dev)
    P_id = np.full((len(a), w), np.nan, np.float32); c2 = {}
    for tag, start, end in specs:
        te, pred, model, mu, sd = infer(XT0, st, ps, a, a_.f10_dir, tag, start, end, w, dev)
        z = np.load(os.path.join(a_.f10_dir, tag, "scores.npz"))
        if not np.array_equal(z["rows"], te): stop(f"fold {tag} rows")
        c2[tag] = bits_differ(pred, z["P"]); P_id[te] = pred
    c2["merged_vs_F10_OOF"] = bits_differ(P_id, OOF)
    rec["C2_identity_cells_not_bitwise"] = c2
    print("C2", json.dumps(c2), flush=True)
    if any(c2.values()): stop(f"C2 identity failed: {c2}")
    # C2b red control on the last fold
    tag, start, end = specs[-1]
    te = np.flatnonzero((a >= start) & (a < end)); i = next(int(i) for i in te if st[i + 1] - st[i] >= 50)
    xx = XT0[st[i]:st[i + 1]].clone(); base = model.f(torch.clamp((xx - mu) / sd, -5, 5)).squeeze(-1)
    xx[0, 80] += 1.0; moved = model.f(torch.clamp((xx - mu) / sd, -5, 5)).squeeze(-1)
    rec["C2b_red_control"] = {"anchor_row": i, "score_changed": bool((moved[0] != base[0]).item())}
    if not rec["C2b_red_control"]["score_changed"]: stop("C2b: score does not respond to col 80")
    del XT0; torch.cuda.empty_cache()
    XT1 = torch.from_numpy(x1).to(dev); P_sw = np.full((len(a), w), np.nan, np.float32)
    for tag, start, end in specs:
        te, pred, _, _, _ = infer(XT1, st, ps, a, a_.f10_dir, tag, start, end, w, dev); P_sw[te] = pred
    pre = a < a_.cut; fin = np.isfinite(OOF)
    d = (P_sw.view(np.uint32) != OOF.view(np.uint32)) & fin
    rec["swap_profile"] = {"scored_cells_pre_cut": int((fin & pre[:, None]).sum()), "differ_pre_cut": int((d & pre[:, None]).sum()),
                           "differ_after_cut_NO_REBUILT_EVENTS": int((d & ~pre[:, None]).sum()),
                           "abs_d_median_pre_cut": float(np.median(np.abs(P_sw - OOF)[d & pre[:, None]])) if (d & pre[:, None]).any() else 0.0}
    print("SWAP", json.dumps(rec["swap_profile"]), flush=True)
    os.makedirs(a_.out_dir, exist_ok=True)
    np.savez_compressed(op, P=P_sw, E_ts=a, symbols=F["symbols"])
    rec["output"] = {"path": op, "sha256": sha(op)}
    with open(os.path.join(a_.out_dir, "F10_SWAP_RECEIPT.json"), "w") as fh:
        fh.write(json.dumps(rec, indent=1)); fh.flush(); os.fsync(fh.fileno())
    print("F10_SWAP_DONE", rec["output"]["sha256"], flush=True)


if __name__ == "__main__":
    main()
