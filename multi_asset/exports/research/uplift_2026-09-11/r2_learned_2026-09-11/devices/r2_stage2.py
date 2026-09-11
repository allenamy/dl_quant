"""Round-2 sleeve family: A DIFFERENT LEARNED OBJECTIVE (v4 caliber, GPU).
Chain copied verbatim from the in-service F10 (pod_f10_train_ext.py): score -> z -> softrank(tau anneal)
-> demean -> L1 -> softcap 2.5/n -> demean -> EMA(alpha learned) -> net = 1e4*w.y - COST*|dw|.
WHAT CHANGES IS THE OBJECTIVE ONLY (PREREG_r2_learned_objective_2026-09-11 S2).
Walk-forward identical to in-service: folds 2023..2026, train = yrs<YV and i < first_te-60 (embargo 60).
Features: v4-native dlw_fea82 ONLY (f8_fea89 is _ext lineage, FORBIDDEN).
Output: preds/<ARM>_s<SEED>.npy  (nA=10212 x 829 raw scores, NaN before the first fold).
"""
import os, json, time, math, hashlib
import numpy as np
import torch, torch.nn as nn

R2 = "/workspace/uplift_2026-09-11/r2_learned"
ARM = os.environ["ARM"]
SEED = int(os.environ.get("SEED", "42"))
PERM = int(os.environ.get("PERM", "0"))        # placebo A: per-anchor permutation of the FEATURE rows
SHUFY = int(os.environ.get("SHUFY", "0"))      # leakage probe: shuffle y4 across anchors
COST, LDD = 3.52, 0.25
WIN, BURN, STRIDE, EPOCHS, LR, EMB, CAPM = 96, 24, 48, 15, 3e-4, 60, 2.5
LAM = float(os.environ.get("LAM", "0.21"))     # sleeve L1 gross = 0.30 * mean |W_A0|_1 (=0.6995)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)

torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int); y4s = TG["y4s"]
nA, NW = y4s.shape
FE = np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz", allow_pickle=True)
XL = np.asarray(FE["X"]).astype(np.float32); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
assert np.all(np.diff(pa) >= 0), "pairs must be anchor-sorted"
ST = np.searchsorted(pa, np.arange(nA + 1))
A0 = np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s%d.npz" % SEED, allow_pickle=True)
lts = A0["legs_ts"].astype(np.int64); OFF = int(np.searchsorted(E_ts, lts[0]))
assert np.array_equal(E_ts[OFF:OFF + len(lts)], lts), "book axis"
WA = np.zeros((nA, NW), np.float32); WA[OFF:OFF + len(lts)] = A0["d30_n2_c42_W"]

if PERM:   # placebo A: within each anchor, permute which SYMBOL each feature row belongs to
    rng = np.random.default_rng([777, SEED])
    for i in range(nA):
        a, b = int(ST[i]), int(ST[i + 1])
        if b - a > 1: XL[a:b] = XL[a + rng.permutation(b - a)]
Y = np.nan_to_num(y4s, nan=0.0).astype(np.float32)
if SHUFY:  # leakage probe: destroy the anchor<->target pairing
    rng = np.random.default_rng([888, SEED]); Y = Y[rng.permutation(nA)]

XT = torch.from_numpy(XL).to(DEV); del XL
YT = torch.from_numpy(Y).to(DEV)
WAT = torch.from_numpy(WA).to(DEV)
PST = torch.from_numpy(ps).to(DEV)

# deployed fund-leg score rank, per anchor, for the differentiable orthogonalisation layer
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
assert np.array_equal(PW["symbols"], TG["symbols"]) and np.array_equal(PW["ts"].astype(np.int64), lts)
FE1 = np.asarray(PW["f_fund_ema_v1"], float)
FR = np.zeros((nA, NW), np.float32)
for i in range(OFF, OFF + len(lts)):
    v = FE1[i - OFF]; ok = np.isfinite(v); n = int(ok.sum())
    if n >= 10:
        r = np.argsort(np.argsort(v[ok])).astype(np.float64) / max(n - 1, 1) - 0.5
        FR[i, np.nonzero(ok)[0]] = r
FRT = torch.from_numpy(FR).to(DEV)
log("data on device", tuple(XT.shape), "arm", ARM, "seed", SEED, "PERM", PERM, "SHUFY", SHUFY)


class Net(nn.Module):
    def __init__(s, d, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)
    def alpha(s): return 0.02 + 0.88 * torch.sigmoid(s.a)


def softrank(z, tau):
    n = z.shape[0]
    return (torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1) - 0.5) / max(n - 1, 1) - 0.5
def hardrank(z):
    n = z.shape[0]
    return torch.argsort(torch.argsort(z)).float() / max(n - 1, 1) - 0.5

ORTH = ARM.endswith("_ORTH")

def u_of(mdl, i, mu, sd, tau, hard):
    a, b = int(ST[i]), int(ST[i + 1])
    if b - a < 50: return None, None
    cols_t = PST[a:b].long()
    x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
    s = mdl.f(torch.nan_to_num(x)).squeeze(-1)
    z = (s - s.mean()) / (s.std() + 1e-8)
    if ORTH:                                    # differentiable per-anchor xsec orthogonalisation
        fr = FRT[i].index_select(0, cols_t)     # deployed fund-leg rank on this anchor's members
        fr = fr - fr.mean()
        d = (fr * fr).sum()
        if float(d) > 1e-8:
            z = z - (z * fr).sum() / d * fr
        z = (z - z.mean()) / (z.std() + 1e-8)
    r = hardrank(z) if hard else softrank(z, tau)
    r = r - r.mean()
    u = r / (r.abs().sum() + 1e-8)
    c = CAPM / (b - a)
    u = c * torch.tanh(u / c); u = u - u.mean()
    return u, cols_t


def run_span(mdl, idx, mu, sd, tau, hard, loss_span=None, resid=False):
    w = torch.zeros(NW, device=DEV); wc = torch.zeros(NW, device=DEV); al = mdl.alpha(); nets = []
    for k, i in enumerate(idx):
        u, midx = u_of(mdl, i, mu, sd, tau, hard)
        wn = (1 - al) * w + al * torch.zeros(NW, device=DEV).scatter(0, midx, u) if u is not None else w
        cn = WAT[i] + LAM * wn if resid else wn
        dn = torch.sqrt((cn - wc) ** 2 + 1e-12).sum()
        net = 1e4 * (cn * YT[i]).sum() - COST * dn
        if loss_span is None or k >= loss_span: nets.append(net)
        w = wn; wc = cn
    return torch.stack(nets)


def es5(nets):
    k = max(1, int(math.ceil(0.05 * nets.shape[0])))
    return torch.topk(-nets, k).values.mean()

RESID = ARM.startswith("RESID")
def objective(nets):
    if ARM in ("RESID", "RESID_ORTH"):  return -nets.mean() + LDD * es5(nets)
    if ARM in ("SHARPE",):              return -nets.mean() / (nets.std() + 1e-6)
    if ARM in ("RESID_SHARPE",):        return -nets.mean() / (nets.std() + 1e-6)
    if ARM in ("CVAR",):                return -0.1 * nets.mean() + 1.0 * es5(nets)
    if ARM in ("BASE",):                return -nets.mean() + LDD * es5(nets)
    raise SystemExit("bad ARM " + ARM)
def va_score(nets):
    if ARM in ("RESID", "RESID_ORTH"):  return float(nets.mean() - LDD * es5(nets))
    if ARM in ("SHARPE", "RESID_SHARPE"): return float(nets.mean() / (nets.std() + 1e-6))
    if ARM in ("CVAR",):                return float(0.1 * nets.mean() - 1.0 * es5(nets))
    if ARM in ("BASE",):                return float(nets.mean() - LDD * es5(nets))

rep = {"arm": ARM, "seed": SEED, "lam": LAM, "cost": COST, "ldd": LDD, "epochs": EPOCHS, "lr": LR,
       "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB, "perm": PERM, "shufy": SHUFY,
       "resid": bool(RESID), "orth": bool(ORTH), "features": "dlw_fea82 (82, v4 native)",
       "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "folds": {}}
PRED = np.full((nA, NW), np.nan, np.float32)
LO = OFF if RESID else 0        # RESID arms need a real W_A0 row

for YV in (2023, 2024, 2025, 2026):
    te = np.where(yrs == YV)[0]
    if te.size == 0: continue
    first_te = int(te[0])
    tr_idx = np.array([i for i in range(LO, first_te - EMB) if yrs[i] < YV and ST[i + 1] - ST[i] >= 50])
    cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
    rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
    XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
    mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
    torch.manual_seed(SEED + YV)
    mdl = Net(XT.shape[1]).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
    best_va, best_state, va_curve, alist = -1e9, None, [], []
    for ep in range(EPOCHS):
        tau = 0.5 - 0.4 * ep / max(EPOCHS - 1, 1)
        mdl.train(); t1 = time.time()
        for s0 in np.random.permutation(starts):
            span = [i for i in range(s0 - BURN, s0 + WIN) if LO <= i < first_te - EMB and yrs[i] < YV]
            if len(span) < BURN + 32: continue
            nets = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN, resid=RESID)
            loss = objective(nets)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step(); mdl.eval()
        with torch.no_grad():
            span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
            nets = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN, resid=RESID)
            va = va_score(nets)
        va_curve.append(round(va, 4)); alist.append(round(float(mdl.alpha()), 4))
        if va > best_va: best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log("[%d] ep%d va %+.4f a %.3f tau %.2f (%.0fs)" % (YV, ep, va, float(mdl.alpha()), tau, time.time() - t1))
    mdl.load_state_dict(best_state); mdl.eval()
    with torch.no_grad():
        span = [int(i) for i in range(max(LO, first_te - BURN), int(te[-1]) + 1)]
        nets = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=first_te - span[0], resid=RESID)
        for i in span:
            if i < first_te: continue
            a, b = int(ST[i]), int(ST[i + 1])
            if b - a < 50: continue
            x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
            sc = mdl.f(torch.nan_to_num(x)).squeeze(-1)
            if ORTH:
                fr = FRT[i].index_select(0, PST[a:b].long()); fr = fr - fr.mean()
                d = (fr * fr).sum()
                zz = (sc - sc.mean()) / (sc.std() + 1e-8)
                if float(d) > 1e-8: zz = zz - (zz * fr).sum() / d * fr
                sc = zz
            PRED[i, ps[a:b]] = sc.cpu().numpy()
    nn_ = nets.cpu().numpy()
    rep["folds"][str(YV)] = {"n_test": int(te.size), "best_va": round(best_va, 4), "va_curve": va_curve,
                             "alpha_curve": alist, "alpha_final": alist[int(np.argmax(va_curve))],
                             "net_mean_bps": round(float(nn_.mean()), 4), "net_sharpe_trainframe": round(float(nn_.mean() / (nn_.std() + 1e-9) * math.sqrt(2190)), 3),
                             "es5_bps": round(float(es5(torch.tensor(nn_)).item()), 3)}
    log("== %d net %+.3f bps/anchor" % (YV, nn_.mean()))
    os.makedirs(R2 + "/preds", exist_ok=True); os.makedirs(R2 + "/results", exist_ok=True)
    tag = ARM + ("_PERM" if PERM else "") + ("_SHUFY" if SHUFY else "") + ("" if abs(LAM-0.21)<1e-9 else "_LAM%g"%LAM) + "_s%d" % SEED
    np.save(R2 + "/preds/%s.npy" % tag, PRED)
    json.dump(rep, open(R2 + "/results/%s.json" % tag, "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
log("STAGE2_DONE %s" % ARM)
