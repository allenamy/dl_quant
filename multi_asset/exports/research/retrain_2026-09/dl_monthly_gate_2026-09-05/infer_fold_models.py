"""infer_fold_models.py — dl_monthly_gate step 1 (PREREG_dl_monthly_gate_and_phi_grid §A1; GPU INFERENCE ONLY, no training).
Re-derive each fold model's raw scores from its saved state_dict (dl_monthly_wf/models/{TAG}_{YM}.pt) with the fold's standardisation recomputed exactly as the
trainer did (training anchors tr1[::7], rows [::3], GPU float32 mean/std + 1e-6), score every anchor >= first_te on the ext grid, verify against the trainer's own
diagnostic output (dl_monthly_wf/preds_fold/{TAG}_{YM}.npz: max|Δ|, bitwise share), assert causality per model, and package per-model per-month npz (ages 1..6,
months <= 2026-08) with sha256 into preds_model/ + preds_model_manifest.json. Read-only on dl_monthly_wf; writes only under dl_monthly_gate/.
usage: TAGS=mE1,mE60 /workspace/venv/bin/python infer_fold_models.py"""
import os, json, time, hashlib, calendar
import numpy as np, torch, torch.nn as nn
W = "/workspace/review_scratch/dl_monthly_wf"; G = "/workspace/review_scratch/dl_monthly_gate"; DLW = "/workspace/dlw_ext"; OUT = "/workspace/f8_ext"
DEV = "cuda" if torch.cuda.is_available() else "cpu"; T0 = time.time()
TAGS = [t for t in os.environ.get("TAGS", "mE1,mE60").split(",") if t]
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
os.makedirs(f"{G}/preds_model", exist_ok=True); os.makedirs(f"{G}/logs", exist_ok=True)
# ── data exactly as the trainer head (pod_f10_train_ext.py lines 33-45; NCOL=167 default => no column drop) ──
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True); E_ts = TG["E_ts"].astype(np.int64); nA = len(E_ts); NW = TG["y4s"].shape[1]
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True); X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True); assert np.array_equal(F9["pair_a"].astype(np.int64), pa) and np.all(np.diff(pa) >= 0)
XL = np.concatenate([X82, F9["X"]], 1).astype(np.float32); del X82, FE, F9
ST = np.searchsorted(pa, np.arange(nA + 1)); XT = torch.from_numpy(XL).to(DEV); del XL; PST = torch.from_numpy(ps).to(DEV)
assert XT.shape[1] == 171 and np.all(np.diff(E_ts) == 14400)
INPUT_SHA = {"targets": sha(f"{DLW}/data/dlw_targets.npz"), "fea82": sha(f"{DLW}/data/dlw_fea82.npz"), "fea89": sha(f"{OUT}/data/f8_fea89.npz")}
log(f"rows {XT.shape[0]} cols {XT.shape[1]} anchors {nA} dev {DEV} inputs {INPUT_SHA}")
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E_ts])
MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
class Net(nn.Module):   # verbatim architecture of pod_f10_train_ext.py Net (PLE/REC off): only .f and .a are used
    def __init__(s, d=171, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))
MAN = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inputs": INPUT_SHA, "torch": torch.__version__, "device": DEV, "models": {}}
for TAG in TAGS:
    EMBM = 60 if TAG == "mE60" else 1
    for YM in MONTHS:
        cfg = json.load(open(f"{W}/models/{TAG}_{YM}_config.json")); ptp = f"{W}/models/{TAG}_{YM}.pt"; pfp = f"{W}/preds_fold/{TAG}_{YM}.npz"
        te = np.where(ym == YM)[0]; first_te, last_te = int(te[0]), int(te[-1])
        tr_idx = np.array([i for i in range(first_te - EMBM) if ST[i + 1] - ST[i] >= 50]); cut = int(len(tr_idx) * 0.85); tr1 = tr_idx[:cut]
        max_tr = int(tr_idx[-1]); cutoff = int(E_ts[first_te]) - EMBM * 14400; label_end = int(E_ts[max_tr]) + 48 * 300
        assert cfg["max_train_idx"] == max_tr and cfg["n_train"] == len(tr_idx) and cfg["cutoff"] == iso(cutoff), (TAG, YM, cfg["max_train_idx"], max_tr)
        assert max_tr < first_te - EMBM and label_end <= cutoff
        rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
        XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]; mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
        mdl = Net(XT.shape[1]).to(DEV); sdict = torch.load(ptp, map_location=DEV); mdl.load_state_dict(sdict); mdl.eval()
        PA = np.full((nA - first_te, NW), np.nan, np.float32)
        with torch.no_grad():
            for i in range(first_te, nA):
                a0, b0 = int(ST[i]), int(ST[i + 1])
                if b0 - a0 < 50: continue
                x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                PA[i - first_te, PST[a0:b0].cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
        z = np.load(pfp); P0 = z["P"]; assert int(z["first_te"]) == first_te and P0.shape == PA.shape
        ok = np.isfinite(P0) & np.isfinite(PA); assert np.array_equal(np.isfinite(P0), np.isfinite(PA))
        dmax = float(np.max(np.abs(P0[ok] - PA[ok]))); bit = float((P0[ok] == PA[ok]).mean()); exact = bool(np.array_equal(P0, PA, equal_nan=True))
        rec = {"pt_sha256": sha(ptp), "preds_fold_sha256": sha(pfp), "first_te": first_te, "first_test": iso(E_ts[first_te]), "n_train": int(len(tr_idx)), "max_train_idx": max_tr,
               "train_cutoff": iso(cutoff), "max_train_label_end": iso(label_end), "embargo": EMBM, "causality_ok": True, "reinfer_vs_preds_fold": {"bitwise_equal": exact, "max_abs_diff": dmax, "share_exact": bit, "n_cells": int(ok.sum())}, "months": {}}
        for a in range(1, 7):
            yy, mm = divmod(YM, 100); mm2 = mm + a - 1; yy2 = yy + (mm2 - 1) // 12; mm2 = (mm2 - 1) % 12 + 1; M2 = yy2 * 100 + mm2
            if M2 > 202608: break
            tm = np.where(ym == M2)[0]; f2, l2 = int(tm[0]), int(tm[-1]); assert int(E_ts[f2]) > cutoff, ("scored month starts before the cutoff", TAG, YM, M2)
            blk = PA[f2 - first_te:l2 - first_te + 1]; p = f"{G}/preds_model/{TAG}_{YM}_age{a}_{M2}.npz"
            np.savez_compressed(p, P=blk, model_month=YM, scored_month=M2, age=a, first_idx=f2, last_idx=l2, E_first=int(E_ts[f2]), E_last=int(E_ts[l2]), train_cutoff_ts=cutoff)
            rec["months"][str(M2)] = {"age": a, "file": os.path.basename(p), "sha256": sha(p), "n_anchors": int(l2 - f2 + 1), "finite_rows": int(np.isfinite(blk).any(1).sum()), "first_anchor": iso(E_ts[f2]), "cutoff_before_first_anchor": True}
        MAN["models"][f"{TAG}_{YM}"] = rec
        log(f"{TAG} {YM}: cutoff {iso(cutoff)} < first scored {iso(E_ts[first_te])} OK | re-infer vs preds_fold bitwise {exact} max|Δ| {dmax:.2e} | months packaged {len(rec['months'])}")
        del mdl, sdict; torch.cuda.empty_cache()
json.dump(MAN, open(f"{G}/preds_model_manifest.json", "w"), indent=1)
allexact = all(v["reinfer_vs_preds_fold"]["bitwise_equal"] for v in MAN["models"].values()); worst = max(v["reinfer_vs_preds_fold"]["max_abs_diff"] for v in MAN["models"].values())
log(f"INFER_DONE models {len(MAN['models'])} all_bitwise {allexact} worst max|Δ| {worst:.2e} files {sum(len(v['months']) for v in MAN['models'].values())}")
