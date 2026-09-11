"""Round-3: RESID_SHARPE made DEPLOYABLE (checkpoints) and EXTENDED to 2022.
Derived from /workspace/uplift_2026-09-11/r2_learned/r2_stage2.py sha256 fe5e759a2cb49df9...
CHANGES, and ONLY these:
 (1) torch.save() of the selected state per fold per seed  -> ckpt/<TAG>_f<YV>.pt  (+ mu/sd/names/config/sha256)
 (2) a second checkpoint at the FIX7 epoch (ep index 7)    -> ckpt/<TAG>_f<YV>_ep7.pt, and a second pred matrix
 (3) YVLIST env selects which folds to run (so the 2023-2026 run stays BITWISE identical to r2:
     the numpy global RNG stream is consumed by np.random.permutation(starts) inside the fold loop,
     so adding a 2022 fold in front of 2023 would shift every later fold. Folds are therefore run in
     SEPARATE PROCESSES and the prediction matrices merged afterwards.)
 (4) fold YV=2022 = a within-2022 causal split (declared in PREREG_r3, FIRST_TE_2022=1044):
     test  = DL anchors [1044, last 2022 anchor] = panel rows [876, 2009]
             (panel row 900 = 2022-06-30 00Z = the first post-warm anchor; 1044 = 1068-BURN so the
              sleeve book carries 24 anchors of state into the first anchor that enters any reading)
     train = DL anchors [LO, 1044-60) , i.e. strictly before the test window, embargo 60 anchors.
 (5) the redundant clause `yrs[i] < YV` in the train filter is dropped: for YV>=2023 every i < first_te
     already has yrs[i] < YV (anchors are time-sorted), so 2023-2026 is unchanged; for YV=2022 the
     clause would have emptied the training set.
Everything else - features, architecture, loss, LAM/COST/LDD, epochs, lr, schedule, early-stop rule,
seeds, the book chain, the test-time inference - is byte-for-byte the r2 recipe.
"""
import os, json, time, math, hashlib, datetime as dt
import numpy as np
import torch, torch.nn as nn

R2 = "/workspace/uplift_2026-09-11/r2_learned"
R3 = "/workspace/uplift_2026-09-11/r3_resid"
ARM = os.environ["ARM"]
SEED = int(os.environ.get("SEED", "42"))
PERM = int(os.environ.get("PERM", "0"))        # placebo A: per-anchor permutation of the FEATURE rows
SHUFY = int(os.environ.get("SHUFY", "0"))      # leakage probe: shuffle y4 across anchors
COST, LDD = 3.52, 0.25
WIN, BURN, STRIDE, EPOCHS, LR, EMB, CAPM = 96, 24, 48, 15, 3e-4, 60, 2.5
LAM = float(os.environ.get("LAM", "0.21"))
YVLIST = [int(x) for x in os.environ.get("YVLIST", "2023,2024,2025,2026").split(",")]
FIRST_TE_2022 = int(os.environ.get("FIRST_TE_2022", "1044"))   # declared in PREREG_r3 before any number
FIX_EP = int(os.environ.get("FIX_EP", "7"))
TAG = os.environ["TAG"]
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
def uts(t): return dt.datetime.utcfromtimestamp(int(t)).strftime("%Y-%m-%d %HZ")

torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int); y4s = TG["y4s"]
nA, NW = y4s.shape
FE = np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz", allow_pickle=True)
FNAMES = [str(x) for x in FE["names"]]
XL = np.asarray(FE["X"]).astype(np.float32); pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
assert np.all(np.diff(pa) >= 0), "pairs must be anchor-sorted"
ST = np.searchsorted(pa, np.arange(nA + 1))
A0 = np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s%d.npz" % SEED, allow_pickle=True)
lts = A0["legs_ts"].astype(np.int64); OFF = int(np.searchsorted(E_ts, lts[0]))
assert np.array_equal(E_ts[OFF:OFF + len(lts)], lts), "book axis"
WA = np.zeros((nA, NW), np.float32); WA[OFF:OFF + len(lts)] = A0["d30_n2_c42_W"]

if PERM:
    rng = np.random.default_rng([777, SEED])
    for i in range(nA):
        a, b = int(ST[i]), int(ST[i + 1])
        if b - a > 1: XL[a:b] = XL[a + rng.permutation(b - a)]
Y = np.nan_to_num(y4s, nan=0.0).astype(np.float32)
if SHUFY:
    rng = np.random.default_rng([888, SEED]); Y = Y[rng.permutation(nA)]

XT = torch.from_numpy(XL).to(DEV); del XL
YT = torch.from_numpy(Y).to(DEV)
WAT = torch.from_numpy(WA).to(DEV)
PST = torch.from_numpy(ps).to(DEV)

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
log("data on device", tuple(XT.shape), "arm", ARM, "seed", SEED, "PERM", PERM, "SHUFY", SHUFY, "folds", YVLIST)


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
    if ORTH:
        fr = FRT[i].index_select(0, cols_t)
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

SELF_SHA = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rep = {"arm": ARM, "seed": SEED, "lam": LAM, "cost": COST, "ldd": LDD, "epochs": EPOCHS, "lr": LR,
       "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB, "perm": PERM, "shufy": SHUFY,
       "resid": bool(RESID), "orth": bool(ORTH), "features": "dlw_fea82 (82, v4 native)",
       "yvlist": YVLIST, "first_te_2022": FIRST_TE_2022, "fix_ep": FIX_EP, "tag": TAG,
       "derived_from": "r2_stage2.py sha256 fe5e759a2cb49df92b6a9763d7e98747321778edb995ba8734e6ee5ddb8ad055",
       "self_sha256": SELF_SHA, "folds": {}}
PRED = np.full((nA, NW), np.nan, np.float32)
PRED7 = np.full((nA, NW), np.nan, np.float32)
LO = OFF if RESID else 0
os.makedirs(R3 + "/preds", exist_ok=True); os.makedirs(R3 + "/results", exist_ok=True); os.makedirs(R3 + "/ckpt", exist_ok=True)

def score_into(P, mdl, span, first_te, mu, sd):
    with torch.no_grad():
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
            P[i, ps[a:b]] = sc.cpu().numpy()

for YV in YVLIST:
    if YV == 2022:
        te_all = np.where(yrs == 2022)[0]
        first_te = FIRST_TE_2022
        te = te_all[te_all >= first_te]
    else:
        te = np.where(yrs == YV)[0]
        if te.size == 0: continue
        first_te = int(te[0])
    tr_idx = np.array([i for i in range(LO, first_te - EMB) if ST[i + 1] - ST[i] >= 50])
    cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
    rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
    XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
    mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
    torch.manual_seed(SEED + YV)
    mdl = Net(XT.shape[1]).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
    log("fold %d train[%d,%d) %s..%s n_tr %d wins %d | test[%d,%d] %s..%s n_te %d"
        % (YV, LO, first_te - EMB, uts(E_ts[LO]), uts(E_ts[first_te - EMB - 1]), len(tr_idx), len(starts),
           first_te, int(te[-1]), uts(E_ts[first_te]), uts(E_ts[int(te[-1])]), len(te)))
    best_va, best_state, va_curve, alist = -1e9, None, [], []
    ep7_state = None
    for ep in range(EPOCHS):
        tau = 0.5 - 0.4 * ep / max(EPOCHS - 1, 1)
        mdl.train(); t1 = time.time()
        for s0 in np.random.permutation(starts):
            span = [i for i in range(s0 - BURN, s0 + WIN) if LO <= i < first_te - EMB]
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
        if ep == FIX_EP: ep7_state = {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log("[%d] ep%d va %+.4f a %.3f tau %.2f (%.0fs)" % (YV, ep, va, float(mdl.alpha()), tau, time.time() - t1))
    best_ep = int(np.argmax(va_curve))
    mdl.load_state_dict(best_state); mdl.eval()
    with torch.no_grad():
        span = [int(i) for i in range(max(LO, first_te - BURN), int(te[-1]) + 1)]
        nets = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=first_te - span[0], resid=RESID)
    score_into(PRED, mdl, span, first_te, mu, sd)
    # ---- (1)(2) CHECKPOINTS: the whole live inference path, nothing external needed ----
    muc = mu.detach().cpu().numpy(); sdc = sd.detach().cpu().numpy()
    ck_meta = {"arm": ARM, "seed": SEED, "fold": YV, "tag": TAG, "lam": LAM, "cost": COST, "ldd": LDD,
               "capm": CAPM, "win": WIN, "burn": BURN, "stride": STRIDE, "epochs": EPOCHS, "lr": LR,
               "embargo": EMB, "perm": PERM, "shufy": SHUFY, "resid": bool(RESID), "orth": bool(ORTH),
               "arch": "Linear(82,256)-GELU-Drop0.1-Linear(256,256)-GELU-Drop0.1-Linear(256,1); alpha=0.02+0.88*sigmoid(a)",
               "feature_npz": "/workspace/dlw_v4raw/data/dlw_fea82.npz", "feature_names": FNAMES,
               "inference": "x=clamp((X-mu)/sd,-5,5); s=f(nan_to_num(x)); publish s as the raw per-anchor score matrix; the book device ranks it",
               "train_idx_range": [int(LO), int(first_te - EMB)],
               "train_ts": [uts(E_ts[LO]), uts(E_ts[first_te - EMB - 1])],
               "test_idx_range": [int(first_te), int(te[-1])],
               "test_ts": [uts(E_ts[first_te]), uts(E_ts[int(te[-1])])],
               "n_train_anchors": int(len(tr_idx)), "n_windows_per_epoch": int(len(starts)),
               "best_epoch": best_ep, "best_va": round(best_va, 4), "va_curve": va_curve,
               "alpha_curve": alist, "alpha_best": alist[best_ep], "fix_ep": FIX_EP,
               "alpha_fix_ep": alist[FIX_EP] if FIX_EP < len(alist) else None,
               "epoch_rule": "unconstrained argmax over 15 epochs on the 85/15 time-split validation (the in-service F10 YEARLY recipe). NOT FIX7 - FIX7 (BEST_EP_FIX=7) is the MONTHLY F10 chain rule; the ep%d checkpoint is written beside it as the robustness arm." % FIX_EP,
               "script_sha256": SELF_SHA}
    for suff, st in (("", best_state), ("_ep%d" % FIX_EP, ep7_state)):
        if st is None: continue
        p = R3 + "/ckpt/%s_f%d%s.pt" % (TAG, YV, suff)
        torch.save({"state_dict": {k: v.cpu() for k, v in st.items()}, "mu": muc, "sd": sdc,
                    "feature_names": FNAMES, "meta": ck_meta, "which": "best" if suff == "" else "fix_ep"}, p)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        m = dict(ck_meta); m["which"] = "best" if suff == "" else "fix_ep"; m["ckpt_path"] = p; m["ckpt_sha256"] = h
        json.dump(m, open(p[:-3] + ".json", "w"), indent=1, default=float)
        log("CKPT %s sha256 %s" % (p, h[:16]))
    if ep7_state is not None:
        mdl.load_state_dict(ep7_state); mdl.eval()
        score_into(PRED7, mdl, span, first_te, mu, sd)
        mdl.load_state_dict(best_state); mdl.eval()
    nn_ = nets.cpu().numpy()
    rep["folds"][str(YV)] = {"n_test": int(te.size), "best_va": round(best_va, 4), "best_epoch": best_ep,
                             "va_curve": va_curve, "alpha_curve": alist, "alpha_final": alist[best_ep],
                             "n_train_anchors": int(len(tr_idx)), "n_windows_per_epoch": int(len(starts)),
                             "train_ts": [uts(E_ts[LO]), uts(E_ts[first_te - EMB - 1])],
                             "test_ts": [uts(E_ts[first_te]), uts(E_ts[int(te[-1])])],
                             "net_mean_bps": round(float(nn_.mean()), 4),
                             "net_sharpe_trainframe": round(float(nn_.mean() / (nn_.std() + 1e-9) * math.sqrt(2190)), 3),
                             "es5_bps": round(float(es5(torch.tensor(nn_)).item()), 3)}
    log("== %d net %+.3f bps/anchor" % (YV, nn_.mean()))
    np.save(R3 + "/preds/%s.npy" % TAG, PRED)
    np.save(R3 + "/preds/%s_ep%d.npy" % (TAG, FIX_EP), PRED7)
    json.dump(rep, open(R3 + "/results/%s.json" % TAG, "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
log("STAGE2_DONE %s %s" % (ARM, TAG))
