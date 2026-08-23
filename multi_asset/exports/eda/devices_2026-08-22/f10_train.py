"""F-10 · 可微书损失 v1 @jpline(2026-08-23, Session 6737834a 主线)。
设计+判据: docs/DESIGN_differentiable_book_loss_2026-08-22.md §2-§6(实现冻结 commit 07cf9aa, 先于任何数字)。
链(全可微): score → 锚内z → 软秩(τ退火) → 去均值 → L1 → softcap 2.5/n → 再去均值 → EMA(α可学) → 净额 = 1e4·w·r − COST·|Δw|。
损失/窗 = −mean(net) + LDD·ES5(net)。TBPTT: 窗96+燃烧24, 训练窗打乱; 验证/测试=时序整段+硬秩。
臂: ARM=MAIN|C0|NOCVAR|AFIX (环境变量 COST/LDD/AFIX 由 queue 设定)。
产物: preds/f10_{ARM}_s{SEED}.npy (锚×829 原始分数, 供 f3 书链终审) + results/f10_{ARM}_s{SEED}.json。
"""
import os, json, time, hashlib, math
import numpy as np
import torch, torch.nn as nn

ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
SEED = int(os.environ.get("SEED", "42")); ARM = os.environ.get("ARM", "MAIN")
COST = float(os.environ.get("COST", "3.52")); LDD = float(os.environ.get("LDD", "0.25"))
AFIX = int(os.environ.get("AFIX", "0"))
EPOCHS = int(os.environ.get("EPOCHS", "15")); LR = float(os.environ.get("LR", "3e-4"))
WIN, BURN, STRIDE, EMB = 96, 24, 48, 60
CAPM = 2.5
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int); y4s = TG["y4s"]
nA, NW = y4s.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
X82 = FE["X"]; pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
assert np.array_equal(F9["pair_a"].astype(np.int64), pa)
assert np.all(np.diff(pa) >= 0), "pairs must be anchor-sorted"
XL = np.concatenate([X82, F9["X"]], 1).astype(np.float32)   # (nrows, 167)
del X82, FE, F9
ST = np.searchsorted(pa, np.arange(nA + 1))
medy = float(np.nanmedian(np.abs(y4s[np.isfinite(y4s)])))
assert 1e-4 <= medy <= 0.05, f"y4s 疑似非小数收益 med|y|={medy}"    # 小数收益口径守卫
log(f"rows {len(pa)} cols {XL.shape[1]} anchors {nA} med|y| {medy:.5f}")

XT = torch.from_numpy(XL).to(DEV); del XL
YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)
PST = torch.from_numpy(ps).to(DEV)
rep = {"arm": ARM, "seed": SEED, "cost": COST, "ldd": LDD, "afix": AFIX, "epochs": EPOCHS,
       "lr": LR, "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB,
       "self_sha256": sha(os.path.abspath(__file__)),
       "targets_sha256": sha(f"{DLW}/data/dlw_targets.npz"),
       "fea82_sha256": sha(f"{DLW}/data/dlw_fea82.npz"), "fea89_sha256": sha(f"{OUT}/data/f8_fea89.npz"),
       "folds": {}}


class Net(nn.Module):
    def __init__(s, d=167, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))          # sigmoid→0.0909 ⇒ α≈0.10
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)

    def alpha(s):
        if AFIX:
            return torch.tensor(0.10, device=s.a.device)
        return 0.02 + 0.88 * torch.sigmoid(s.a)


def softrank(z, tau):
    n = z.shape[0]
    r = torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1)
    return (r - 0.5) / max(n - 1, 1) - 0.5


def hardrank(z):
    n = z.shape[0]
    r = torch.argsort(torch.argsort(z)).float()
    return r / max(n - 1, 1) - 0.5


def u_of(mdl, i, mu, sd, tau, hard):
    a, b = int(ST[i]), int(ST[i + 1])
    if b - a < 50:
        return None, None
    x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
    s = mdl.f(torch.nan_to_num(x)).squeeze(-1)
    z = (s - s.mean()) / (s.std() + 1e-8)
    r = hardrank(z) if hard else softrank(z, tau)
    r = r - r.mean()
    u = r / (r.abs().sum() + 1e-8)
    c = CAPM / (b - a)
    u = c * torch.tanh(u / c)
    u = u - u.mean()
    return u, PST[a:b]


def run_span(mdl, idx, mu, sd, tau, hard, w0=None, loss_span=None):
    """按时序推进 idx 内的链; 返回 (net序列(loss_span部分), w_end)。"""
    w = torch.zeros(NW, device=DEV) if w0 is None else w0
    al = mdl.alpha()
    nets = []
    for k, i in enumerate(idx):
        u, midx = u_of(mdl, i, mu, sd, tau, hard)
        if u is not None:
            uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u)
            wn = (1 - al) * w + al * uf
        else:
            wn = w
        dn = torch.sqrt((wn - w) ** 2 + 1e-12).sum()
        net = 1e4 * (wn * YT[i]).sum() - COST * dn
        if loss_span is None or k >= loss_span:
            nets.append(net)
        w = wn
    return torch.stack(nets), w


def es5(nets):
    """Expected shortfall: 最差 5% 锚净额均值的相反数 ⇒ 尾部越坏值越大(正), 进损失作惩罚。
    ★ 2026-08-23 符号修正: 首版多了一道取负 ⇒ 损失在奖励坏尾部(验证分虚高 +16, 2023 折 ES 实测 65.7 bps
    被当成负值). topk(-nets).values = 最坏锚的 |净额|(正), 其均值即 ES, 不再取负。"""
    k = max(1, int(math.ceil(0.05 * nets.shape[0])))
    return torch.topk(-nets, k).values.mean()


for YV in (2023, 2024, 2025, 2026):
    te = np.where(yrs == YV)[0]
    if te.size == 0:
        continue
    first_te = int(te[0])
    tr_idx = np.array([i for i in range(first_te - EMB) if yrs[i] < YV and ST[i + 1] - ST[i] >= 50])
    cut = int(len(tr_idx) * 0.85)
    tr1, va1 = tr_idx[:cut], tr_idx[cut:]
    # 标定: 训练行抽样 med/std
    rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
    XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
    mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6
    del XS
    torch.manual_seed(SEED + YV)
    mdl = Net(XT.shape[1]).to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
    best_va, best_state, va_curve, alist = -1e9, None, [], []
    for ep in range(EPOCHS):
        tau = 0.5 - (0.5 - 0.1) * ep / max(EPOCHS - 1, 1)
        mdl.train(); order = np.random.permutation(starts); t0 = time.time()
        for s0 in order:
            span = [i for i in range(s0 - BURN, s0 + WIN) if i < first_te - EMB and yrs[i] < YV]
            if len(span) < BURN + 32:
                continue
            nets, _ = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN)
            loss = -nets.mean() + LDD * es5(nets)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step()
        mdl.eval()
        with torch.no_grad():
            span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
            nets, _ = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN)
            va = float(nets.mean() - LDD * es5(nets))
        al = float(mdl.alpha()); va_curve.append(round(va, 4)); alist.append(round(al, 4))
        if va > best_va:
            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log(f"[{YV}] ep{ep} va {va:+.3f} α {al:.3f} τ {tau:.2f} ({time.time()-t0:.0f}s)")
    mdl.load_state_dict(best_state); mdl.eval()
    # 测试: 时序整段(燃烧段用 te 前 BURN 锚), 硬秩; 同时导出原始分数
    with torch.no_grad():
        span = [int(i) for i in range(max(0, first_te - BURN), int(te[-1]) + 1)]
        nets, _ = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=first_te - span[0])
        trn_series = []
        w = torch.zeros(NW, device=DEV); al = mdl.alpha()
        PRED_f = np.full((len(te), NW), np.nan, np.float32)
        for k, i in enumerate(span):
            u, midx = u_of(mdl, i, mu, sd, 0.1, hard=True)
            if u is not None:
                uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u)
                wn = (1 - al) * w + al * uf
                if i >= first_te:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                    PRED_f[i - first_te, midx.cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()
            else:
                wn = w
            if i >= first_te:
                trn_series.append(float((wn - w).abs().sum()))
            w = wn
    nets_np = nets.cpu().numpy()
    yr_net = float(np.mean(nets_np)); es_np = float(es5(nets).item())
    if "PRED" not in dir():
        PRED = np.full((nA, NW), np.nan, np.float32)
    PRED[first_te:int(te[-1]) + 1] = PRED_f
    rep["folds"][str(YV)] = {"n_test": int(te.size), "best_va": round(best_va, 4), "va_curve": va_curve,
                             "alpha_curve": alist, "alpha_final": alist[int(np.argmax(va_curve))],
                             "net_mean_bps": round(yr_net, 4), "es5_bps": round(es_np, 3),
                             "turnover_mean": round(float(np.mean(trn_series)), 5)}
    log(f"== {YV}: net {yr_net:+.3f} bps/锚 ES5 {es_np:.2f} 换手 {np.mean(trn_series):.4f} α* {rep['folds'][str(YV)]['alpha_final']}")
    np.save(f"{OUT}/preds/f10_{ARM}_s{SEED}.npy", PRED)
    json.dump(rep, open(f"{OUT}/results/f10_{ARM}_s{SEED}.json", "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
rep["net_mean_all"] = round(float(np.mean([f["net_mean_bps"] for f in rep["folds"].values()])), 4)
json.dump(rep, open(f"{OUT}/results/f10_{ARM}_s{SEED}.json", "w"), indent=1, default=float)
log(f"F10_TRAIN_DONE {ARM} s{SEED} 年均净 {rep['net_mean_all']:+.3f} bps/锚(训练帧, 非终审)")
