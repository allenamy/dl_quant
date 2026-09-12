"""F-10 部署重训 @jpline: V2MAIN 冻结配方全史(→2026-08-10), 保存权重+标定+α(REVIEW §6.2)。

★ 2026-09-12 (RUNBOOK_monthly_retrain_2026-10 §0★ 修订 2 ①; independent review 0dfc0d87 R1): NO SILENT DEFAULTS. The September copy defaulted to
  F10_DLW=/workspace/dlw_ext, F10_OUT=/workspace/f8_ext and BEST_EP_FIX=-1 (argmax), so a bare call read the PREVIOUS generation's inputs, kept the argmax
  epoch and overwrote f8_ext/models/f10_live_s42.pt; the launcher's sub-shell `BEST_EP_FIX=7` never reached a bare parent-shell call. Now the four
  locators/knobs F10_DLW F10_OUT SEED BEST_EP_FIX must ALL be in the environment or the program refuses (rc 2) BEFORE importing torch.
  The training recipe below the env block is byte-identical to the September copy (COST/LDD/WIN/BURN/STRIDE/EPOCHS/LR/CAPM, split, optimiser, FIX rule).
  The report gains the TRUE label cutoff (review R1 ¶2): `trained_through` (kept, = pool end tr_idx[-1]) is NOT the last label the optimiser saw;
  `trained_through_label_utc` = the last anchor whose net entered a TBPTT loss window (starts[-1] + WIN - 1), `trained_through_tr1_end_utc` = the tr1
  split end, `validation_span_utc` = va1. A JSON sidecar beside the .pt carries the same metadata for readers without torch (the chain checks best_ep_rule)."""
import os, sys, json, time, math, hashlib
_REQ = ("F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX")
_missing = [k for k in _REQ if not os.environ.get(k)]
if _missing:
    print(f"REFIT_REFUSED: env {_missing} not set — pod_f10_refit_v4.py has NO defaults (the legacy dlw_ext / f8_ext / argmax defaults were removed 2026-09-12); "
          f"pass F10_DLW F10_OUT SEED BEST_EP_FIX explicitly (chain_v4_monthly.sh does)", flush=True)
    sys.exit(2)
import numpy as np
import torch, torch.nn as nn
DLW = os.environ["F10_DLW"]
OUT = os.environ["F10_OUT"]
SEED = int(os.environ["SEED"]); BEST_EP_FIX = int(os.environ["BEST_EP_FIX"])   # v4: -1 = verbatim argmax; k = keep exactly epoch k (FIX rule) — explicit, never defaulted
COST, LDD = 3.52, 0.25
WIN, BURN, STRIDE, EPOCHS, LR, CAPM = 96, 24, 48, 15, 3e-4, 2.5
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); y4s = TG["y4s"]; nA, NW = y4s.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); del FE, F9
ST = np.searchsorted(pa, np.arange(nA + 1))
L = np.load(f"{OUT}/data/f10v2_legs.npz", allow_pickle=True)
LZ24 = torch.from_numpy(np.nan_to_num(L["Z24"], nan=0.0)).to(DEV)
LZFD = torch.from_numpy(np.nan_to_num(L["ZFD"], nan=0.0)).to(DEV)
LWL = torch.from_numpy(np.nan_to_num(L["WL"], nan=1.0 / 3)).to(DEV)
XT = torch.from_numpy(XL).to(DEV); del XL
YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)
PST = torch.from_numpy(ps).to(DEV)


class Net(nn.Module):
    def __init__(s, d, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)

    def alpha(s):
        return 0.02 + 0.88 * torch.sigmoid(s.a)


def softrank(z, tau):
    n = z.shape[0]
    return (torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1) - 0.5) / max(n - 1, 1) - 0.5


def hardrank(z):
    n = z.shape[0]
    return torch.argsort(torch.argsort(z)).float() / max(n - 1, 1) - 0.5


def u_of(mdl, i, mu, sd, tau, hard):
    a, b = int(ST[i]), int(ST[i + 1])
    if b - a < 50:
        return None, None
    cols_t = PST[a:b].long()
    x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
    s = mdl.f(torch.nan_to_num(x)).squeeze(-1)
    z = (s - s.mean()) / (s.std() + 1e-8)
    r = hardrank(z) if hard else softrank(z, tau)
    wl = LWL[i]
    r = wl[0] * r + wl[1] * LZ24[i].index_select(0, cols_t) + wl[2] * LZFD[i].index_select(0, cols_t)
    r = r - r.mean()
    u = r / (r.abs().sum() + 1e-8)
    c = CAPM / (b - a)
    u = c * torch.tanh(u / c); u = u - u.mean()
    return u, cols_t


def run_span(mdl, idx, mu, sd, tau, hard, loss_span=None):
    w = torch.zeros(NW, device=DEV); al = mdl.alpha(); nets = []
    for k, i in enumerate(idx):
        u, midx = u_of(mdl, i, mu, sd, tau, hard)
        wn = (1 - al) * w + al * torch.zeros(NW, device=DEV).scatter(0, midx, u) if u is not None else w
        dn = torch.sqrt((wn - w) ** 2 + 1e-12).sum()
        net = 1e4 * (wn * YT[i]).sum() - COST * dn
        if loss_span is None or k >= loss_span:
            nets.append(net)
        w = wn
    return torch.stack(nets)


def es5(nets):
    k = max(1, int(math.ceil(0.05 * nets.shape[0])))
    return torch.topk(-nets, k).values.mean()


tr_idx = np.array([i for i in range(nA) if ST[i + 1] - ST[i] >= 50])
cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
mdl = Net(XT.shape[1]).to(DEV)
opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
best_va, best_state, curve = -1e9, None, []
for ep in range(EPOCHS):
    tau = 0.5 - 0.4 * ep / max(EPOCHS - 1, 1)
    mdl.train()
    for s0 in np.random.permutation(starts):
        span = [i for i in range(s0 - BURN, s0 + WIN) if ST[i + 1] - ST[i] >= 0]
        nets = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN)
        loss = -nets.mean() + LDD * es5(nets)
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
    sch.step()
    mdl.eval()
    with torch.no_grad():
        span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
        nets = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN)
        va = float(nets.mean() - LDD * es5(nets))
    curve.append(round(va, 4))
    if (BEST_EP_FIX < 0 and va > best_va) or (BEST_EP_FIX >= 0 and ep == BEST_EP_FIX):   # v4: FIX rule keeps exactly epoch BEST_EP_FIX
        best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
    log(f"ep{ep} va {va:+.3f} α {float(mdl.alpha()):.3f}")
mdl.load_state_dict(best_state)
os.makedirs(f"{OUT}/models", exist_ok=True)
def _iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
_last_loss_idx = int(starts[-1] + WIN - 1)   # the last anchor whose net entered a loss window (span k >= BURN of the last TBPTT start); its label = 5m rows [E+1, E+48]
_best_ep = int(BEST_EP_FIX) if BEST_EP_FIX >= 0 else int(np.argmax(curve))
meta = {"seed": SEED, "n_cols": int(XT.shape[1]), "va_curve": curve, "best_va": best_va, "best_ep_rule": ("fix%d" % BEST_EP_FIX if BEST_EP_FIX >= 0 else "argmax"), "best_ep_kept": _best_ep,
        "trained_through": int(E_ts[tr_idx[-1]]),   # KEPT for readers of the old key: the POOL END (tr_idx[-1]); the optimiser never saw labels past trained_through_label_utc (review R1)
        "trained_through_meaning": "pool end = last anchor of tr_idx (its first 85% is tr1 = optimised, last 15% va1 = validation only); NOT the last loss label",
        "trained_through_pool_end_utc": _iso(E_ts[tr_idx[-1]]), "trained_through_tr1_end_utc": _iso(E_ts[tr1[-1]]),
        "trained_through_label_utc": _iso(E_ts[_last_loss_idx]), "trained_through_label_end_utc": _iso(int(E_ts[_last_loss_idx]) + 48 * 300), "trained_through_label_idx": _last_loss_idx,
        "validation_span_utc": [_iso(E_ts[va1[0]]), _iso(E_ts[va1[-1]])], "n_train_anchors_tr1": int(len(tr1)), "n_val_anchors_va1": int(len(va1)), "n_tbptt_windows": int(len(starts)),
        "data_axis_end_utc": _iso(E_ts[-1]), "epochs_computed": EPOCHS, "recipe": "V2MAIN frozen (REVIEW §6.2)",
        "env_given": {k: os.environ.get(k) for k in ("F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX", "EMBARGO", "V4_MONTH", "V4_MONTH_ENV")},
        "inputs": {"targets": f"{DLW}/data/dlw_targets.npz", "fea82": f"{DLW}/data/dlw_fea82.npz", "fea89": f"{OUT}/data/f8_fea89.npz", "legs": f"{OUT}/data/f10v2_legs.npz"},
        "self_sha256": _sha(os.path.abspath(__file__)), "torch": torch.__version__, "device": DEV, "finished_utc": _iso(time.time())}
meta["inputs_sha256"] = {k: _sha(v) for k, v in meta["inputs"].items()}
torch.save(dict({"state_dict": best_state, "mu": mu.cpu(), "sd": sd.cpu(), "alpha": float(mdl.alpha())}, **meta), f"{OUT}/models/f10_live_s{SEED}.pt")
meta["pt"] = f"{OUT}/models/f10_live_s{SEED}.pt"; meta["pt_sha256"] = _sha(meta["pt"]); meta["alpha"] = float(mdl.alpha())
json.dump(meta, open(f"{OUT}/models/f10_live_s{SEED}.json", "w"), indent=1)   # sidecar: the same metadata readable without torch
log(f"REFIT_DONE s{SEED} best_va {best_va:+.3f} α {float(mdl.alpha()):.3f} rule {meta['best_ep_rule']} label cutoff {meta['trained_through_label_utc']} (pool end {meta['trained_through_pool_end_utc']}) -> models/f10_live_s{SEED}.pt")
