"""FIX7 monthly-fold (202608) pure inference on the CORRECTED holefix chain (dlw_hf2 / f8_hf2, PANEL=v3splice).
Contract copied from the independent reviewer's inference_contract (parity.py sha 64e2a045…, hf_infer.py sha 05d2395e…):
  Net 171->256->256->1 GELU/Dropout(.1); eval/no_grad; per-anchor batch; clamp((X-mu)/sd,-5,5) then nan_to_num;
  mu/sd = the reviewer's sealed calibration.npz (6853b250…) which equals the ORIGINAL-input recomputation bitwise.
GATES (all before any post-change forward): (G0) frozen file identities; (G1) mu/sd recomputed from THESE inputs by the
original recipe must equal calibration.npz uint32-bitwise; (G2) 66 pre-hole anchors (E < 2026-08-12 00:00Z) must
reproduce OLD_s{seed}.npz uint32-bitwise. Zero optimizer steps. No book evaluation."""
import os, sys, json, time, hashlib, datetime
import numpy as np, torch
from torch import nn
OUT = "/workspace/review_scratch/hf2_infer"; os.makedirs(OUT, exist_ok=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
class Net(nn.Module):
    def __init__(s, d=171, h=256, p=.1):
        super().__init__(); s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1)); s.a = nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(s.f[-1].weight, 0., 1e-3); nn.init.zeros_(s.f[-1].bias)
FROZEN = {
  "/workspace/dlw_hf2/data/dlw_targets.npz": None, "/workspace/dlw_hf2/data/dlw_fea82.npz": None, "/workspace/f8_hf2/data/f8_fea89.npz": None,
  "/workspace/review_scratch/allweather_trackB/earlystop/FIX7/shard3/models/mE1cX7_202608.pt": "a5fc46b49d9f756c",
  "/workspace/review_scratch/allweather_trackB/earlystop/FIX7_s2027/shard3/models/mE1cX7s27_202608.pt": "3795e117b744a38b",
  "/workspace/codex_research/QNT-2026-0907/breakthrough_batch_20260908/native_target_repair/attempts/OLD_202608_s42/audit/calibration.npz": "6853b250111627f0",
  "/workspace/codex_research/QNT-2026-0907/holefix_review_2026-09-08/inference_contract/parity_attempt/OLD_s42.npz": "2f5f69762c08e8e1",
  "/workspace/codex_research/QNT-2026-0907/holefix_review_2026-09-08/inference_contract/parity_attempt/OLD_s2027.npz": "13598402f131c839",
}
MODEL = {42: "/workspace/review_scratch/allweather_trackB/earlystop/FIX7/shard3/models/mE1cX7_202608.pt",
         2027: "/workspace/review_scratch/allweather_trackB/earlystop/FIX7_s2027/shard3/models/mE1cX7s27_202608.pt"}
CAL = "/workspace/codex_research/QNT-2026-0907/breakthrough_batch_20260908/native_target_repair/attempts/OLD_202608_s42/audit/calibration.npz"
OLDP = "/workspace/codex_research/QNT-2026-0907/holefix_review_2026-09-08/inference_contract/parity_attempt/OLD_s%d.npz"
PRECUT = 1786492800   # 2026-08-12 00:00Z (reviewer's prespecified pre-change cut)
def main():
    t0 = time.perf_counter(); torch.set_num_threads(4); assert torch.cuda.is_available()
    before = {p: sha(p) for p in FROZEN}
    for p, want in FROZEN.items():
        if want: assert before[p].startswith(want), ("G0 identity mismatch", p, before[p][:16], want)
    print("G0 frozen identities OK (%d files)" % len(before), flush=True)
    tg = np.load("/workspace/dlw_hf2/data/dlw_targets.npz", allow_pickle=True); ts = tg["E_ts"].astype(np.int64); symbols = tg["symbols"]
    fe = np.load("/workspace/dlw_hf2/data/dlw_fea82.npz", allow_pickle=True); f9 = np.load("/workspace/f8_hf2/data/f8_fea89.npz", allow_pickle=True)
    pa = fe["pair_a"].astype(np.int64); ps = fe["pair_s"].astype(np.int64)
    assert np.array_equal(f9["pair_a"].astype(np.int64), pa) and np.array_equal(f9["pair_s"].astype(np.int64), ps)
    names = fe["names"].astype(str).tolist() + f9["names"].astype(str).tolist(); assert len(names) == 171
    x = np.concatenate([fe["X"], f9["X"]], 1).astype(np.float32); assert x.shape[1] == 171 and np.all(np.diff(pa) >= 0)
    st = np.searchsorted(pa, np.arange(len(ts) + 1)); xt = torch.from_numpy(x).cuda(); del x
    te = np.flatnonzero((ts >= 1785542400) & (ts < 1788220800)); print("august anchors in hf2: %d (first %d last %d)" % (len(te), ts[te[0]], ts[te[-1]]), flush=True)
    assert len(te) == 186 and ts[te[-1]] == 1788206400
    # ---- G1: recompute mu/sd by the ORIGINAL monthly-fold recipe on THESE inputs ----
    first = int(te[0]); tr = np.array([i for i in range(first - 1) if st[i + 1] - st[i] >= 50]); tr1 = tr[:int(len(tr) * .85)]
    rowsel = np.concatenate([np.arange(st[i], st[i + 1]) for i in tr1[::7]]); xs = xt[torch.from_numpy(rowsel[::3]).cuda()]
    mu = torch.nan_to_num(xs).mean(0); sd = torch.nan_to_num(xs).std(0) + 1e-6; del xs
    c = np.load(CAL)
    g1 = bool(np.array_equal(mu.cpu().numpy().view(np.uint32), c["mu"].view(np.uint32))) and bool(np.array_equal(sd.cpu().numpy().view(np.uint32), c["sd"].view(np.uint32)))
    print("G1 calibration recomputed on hf2 inputs == sealed original calibration (uint32): %s  (sample rows %d, tr %d, tr1 %d)" % (g1, len(rowsel[::3]), len(tr), len(tr1)), flush=True)
    assert g1, "G1 FAIL: training rows differ from the original — stop"
    mu = torch.from_numpy(c["mu"]).cuda(); sd = torch.from_numpy(c["sd"]).cuda()      # use the sealed values verbatim from here on
    npre = int((ts[te] < PRECUT).sum()); assert npre == 66
    res = {"utc": utc(), "self_sha256": sha(__file__), "inputs": before, "torch": torch.__version__, "G1_calibration_bitwise": g1, "seeds": {}}
    preds = {}; models = {}
    for seed in (42, 2027):
        torch.manual_seed(seed); m = Net().cuda(); state = torch.load(MODEL[seed], map_location="cuda", weights_only=True)
        assert "state_dict" not in state and "mu" not in state; m.load_state_dict(state, strict=True); m.eval(); models[seed] = m
        pred = np.full((186, 829), np.nan, np.float32)
        with torch.no_grad():
            for j in range(npre):
                a, b = int(st[te[j]]), int(st[te[j] + 1])
                if b - a < 50: continue
                inp = torch.clamp((xt[a:b] - mu) / sd, -5, 5); pred[j, ps[a:b]] = m.f(torch.nan_to_num(inp)).squeeze(-1).cpu().numpy()
        old = np.load(OLDP % seed); assert np.array_equal(old["ts"][:npre], ts[te[:npre]]) and np.array_equal(old["symbols"].astype(str), symbols.astype(str))
        q = old["P"][:npre]; r = pred[:npre]
        diff = r.view(np.uint32) != q.view(np.uint32); common = np.isfinite(r) & np.isfinite(q)
        rec = {"pre_anchors": npre, "cells": int(r.size), "finite_mask_equal": bool(np.array_equal(np.isfinite(r), np.isfinite(q))),
               "different_uint32_cells": int(diff.sum()), "max_common_finite_abs_diff": float(np.max(np.abs(r[common] - q[common]))) if common.any() else 0.0,
               "first_changed_E": int(ts[te[np.argwhere(diff)[0, 0]]]) if diff.any() else None, "G2_pass": bool(not diff.any())}
        print("G2 seed %d: pre-hole %d anchors, different uint32 cells %d, maxabs %.3e -> %s" % (seed, npre, rec["different_uint32_cells"], rec["max_common_finite_abs_diff"], "PASS" if rec["G2_pass"] else "FAIL"), flush=True)
        res["seeds"][str(seed)] = rec; preds[seed] = pred
    if not all(v["G2_pass"] for v in res["seeds"].values()):
        res["status"] = "STOP_PRECHANGE_BITWISE_GATE_FAILED"; res["post_change_forward_calls"] = 0
        json.dump(res, open(OUT + "/RESULT.json", "w"), indent=1); print("STOP", flush=True); return 3
    # ---- post-change segment (descriptive only) ----
    for seed in (42, 2027):
        m = models[seed]; pred = preds[seed]
        with torch.no_grad():
            for j in range(npre, 186):
                a, b = int(st[te[j]]), int(st[te[j] + 1])
                if b - a < 50: continue
                inp = torch.clamp((xt[a:b] - mu) / sd, -5, 5); pred[j, ps[a:b]] = m.f(torch.nan_to_num(inp)).squeeze(-1).cpu().numpy()
        pp = OUT + "/HF2_s%d.npz" % seed; np.savez_compressed(pp, ts=ts[te], symbols=symbols, P=pred)
        old = np.load(OLDP % seed); q = old["P"]; n_old = q.shape[0]           # 180 anchors (08-01..08-30 20Z)
        r = pred[:n_old]; common = np.isfinite(r) & np.isfinite(q); d = np.abs(r - q); ch = common & (d > 0)
        rows = np.where(ch.any(1))[0]
        desc = {"path": pp, "sha256": sha(pp), "common_anchors": int(n_old), "changed_finite_cells": int(ch.sum()), "common_finite_cells": int(common.sum()),
                "max_abs_diff": float(d[common].max()) if common.any() else 0.0, "first_changed_E": int(ts[te[rows[0]]]) if len(rows) else None,
                "changed_anchors": int(len(rows)), "newly_finite": int((np.isfinite(r) & ~np.isfinite(q)).sum()), "lost_finite": int((~np.isfinite(r) & np.isfinite(q)).sum()),
                "new_anchors_08-31": {"count": 6, "finite_scores": [int(np.isfinite(pred[k]).sum()) for k in range(n_old, 186)]}}
        # per-anchor Spearman old vs new on the post-change common anchors (descriptive)
        from scipy.stats import spearmanr
        sp = []
        for k in rows:
            ok = common[k]
            if ok.sum() > 30: sp.append(float(spearmanr(r[k, ok], q[k, ok]).correlation))
        desc["spearman_old_new_changed_anchors"] = {"n": len(sp), "min": min(sp) if sp else None, "median": float(np.median(sp)) if sp else None}
        res["seeds"][str(seed)]["post"] = desc
        print("seed %d post-change: changed finite cells %d / %d common, first changed %s, changed anchors %d, maxabs %.4f, spearman(old,new) median %s min %s, 08-31 finite per anchor %s"
              % (seed, desc["changed_finite_cells"], desc["common_finite_cells"], desc["first_changed_E"], desc["changed_anchors"], desc["max_abs_diff"],
                 desc["spearman_old_new_changed_anchors"]["median"], desc["spearman_old_new_changed_anchors"]["min"], desc["new_anchors_08-31"]["finite_scores"]), flush=True)
    after = {p: sha(p) for p in FROZEN}; assert after == before
    res["status"] = "COMPLETE"; res["forward_calls"] = 2 * 186; res["optimizer_steps"] = 0; res["wall_seconds"] = time.perf_counter() - t0
    json.dump(res, open(OUT + "/RESULT.json", "w"), indent=1); print("HF2_INFER_DONE", flush=True); return 0
if __name__ == "__main__":
    sys.exit(main())
