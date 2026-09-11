"""BOOKERR arm: same net/walk-forward, but the OBJECTIVE is a plain xsec rank loss on the book's own
realised error  ytil = y4 - beta_i * W_A0[i]  (no differentiable book). Kept separate for clarity."""
import os, json, time, math, hashlib
import numpy as np, torch, torch.nn as nn
R2 = "/workspace/uplift_2026-09-11/r2_learned"
SEED = int(os.environ.get("SEED", "42")); TGT = os.environ.get("TGT", "til")   # til | raw
PERM = int(os.environ.get("PERM", "0"))
EPOCHS, LR, EMB = 15, 3e-4, 60
DEV = "cuda"; T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
yrs = TG["yrs"].astype(int); nA, NW = TG["y4s"].shape
FE = np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz", allow_pickle=True)
XL = np.asarray(FE["X"]).astype(np.float32); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
ST = np.searchsorted(pa, np.arange(nA + 1))
T = np.load(R2 + "/targets_resid.npz")
R = T["Rraw"] if TGT == "raw" else T["Rtil"]
if PERM:
    rng = np.random.default_rng([777, SEED])
    for i in range(nA):
        a, b = int(ST[i]), int(ST[i + 1])
        if b - a > 1: XL[a:b] = XL[a + rng.permutation(b - a)]
XT = torch.from_numpy(XL).to(DEV); del XL
RT = torch.from_numpy(np.nan_to_num(R, nan=0.0)).to(DEV)
MT = torch.from_numpy(np.isfinite(R).astype(np.float32)).to(DEV)
class Net(nn.Module):
    def __init__(s, d, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)
rep = {"arm": "BOOKERR_" + TGT, "seed": SEED, "perm": PERM, "target": TGT, "folds": {},
       "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
PRED = np.full((nA, NW), np.nan, np.float32)
BS = 65536
for YV in (2023, 2024, 2025, 2026):
    te = np.where(yrs == YV)[0]; first_te = int(te[0])
    tr = np.array([i for i in range(first_te - EMB) if yrs[i] < YV and ST[i + 1] - ST[i] >= 50])
    cut = int(len(tr) * 0.85); tr1, va1 = tr[:cut], tr[cut:]
    rtr = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1])
    rva = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in va1])
    rte = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in te if ST[i + 1] - ST[i] >= 50])
    idx = torch.from_numpy(rtr[::3]).to(DEV)
    XS = XT[idx]; mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
    torch.manual_seed(SEED + YV); mdl = Net(XT.shape[1]).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    trt = torch.from_numpy(rtr).to(DEV); vat = torch.from_numpy(rva).to(DEV)
    best, bstate, curve = -1e9, None, []
    for ep in range(EPOCHS):
        mdl.train(); perm = torch.randperm(len(trt), device=DEV)
        for k in range(0, len(trt), BS):
            b = trt[perm[k:k + BS]]
            x = torch.clamp((XT[b] - mu) / sd, -5, 5)
            p = mdl.f(torch.nan_to_num(x)).squeeze(-1)
            m = MT[b]; t = RT[b]
            loss = (((p - t) ** 2) * m).sum() / m.sum().clamp(min=1)
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step(); mdl.eval()
        with torch.no_grad():
            ps_, ts_, ms_ = [], [], []
            for k in range(0, len(vat), BS):
                b = vat[k:k + BS]
                x = torch.clamp((XT[b] - mu) / sd, -5, 5)
                ps_.append(mdl.f(torch.nan_to_num(x)).squeeze(-1)); ts_.append(RT[b]); ms_.append(MT[b])
            p = torch.cat(ps_); t = torch.cat(ts_); m = torch.cat(ms_) > 0
            p = p[m]; t = t[m]
            va = float(((p - p.mean()) * (t - t.mean())).mean() / (p.std() * t.std() + 1e-12))
        curve.append(round(va, 5))
        if va > best: best, bstate = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log("[%d] ep%d va_corr %+.5f" % (YV, ep, va))
    mdl.load_state_dict(bstate); mdl.eval()
    with torch.no_grad():
        tt = torch.from_numpy(rte).to(DEV); out = []
        for k in range(0, len(tt), BS):
            b = tt[k:k + BS]
            x = torch.clamp((XT[b] - mu) / sd, -5, 5)
            out.append(mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy())
        o = np.concatenate(out)
    PRED[pa[rte], ps[rte]] = o
    rep["folds"][str(YV)] = {"best_va_corr": best, "curve": curve}
    tag = "BOOKERR%s%s_s%d" % (TGT, "_PERM" if PERM else "", SEED)
    np.save(R2 + "/preds/%s.npy" % tag, PRED); json.dump(rep, open(R2 + "/results/%s.json" % tag, "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
log("BOOKERR_DONE")
