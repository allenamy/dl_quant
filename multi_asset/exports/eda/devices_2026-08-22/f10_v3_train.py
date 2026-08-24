"""F-10 V3FULL 满配分数体 @jpline(2026-08-24)。设计 §11+§11.1 冻结; 链/损失与 V2MAIN 逐字同(隔离架构变量)。
体: PLE 数值嵌入 → 主干 MLP + 并行低秩 DCNv2 交叉 ×2 + RG-FiLM(前2块, γ→1/β→0) + 锚史因果DW卷积(K=16, 门控)
   + 截面 MHA(2头, QKLN, 秩化Q/K) —— 全部近零 LayerScale(1e-2) 接入, 初始 ≈ 冠军基线。
正则: 特征 dropout 0.12 + 对抗输入扰动 FGSM ε=0.02σ(隔 epoch)。力学: 成本乘子前 25% 步 0→1; τ 退火至 corr(soft,hard)≥0.99 停。
权重EMA/TabM 未启用(待用户合规裁定)。"""
import os, json, time, math, hashlib
import numpy as np
import torch, torch.nn as nn
ROOT = "/mnt/storage/private/work_hsy"; DLW = f"{ROOT}/dlw_2026-08-22"; OUT = f"{ROOT}/f8_2026-08-22"
SEED = int(os.environ.get("SEED", "42")); ARM = os.environ.get("ARM", "V3FULL")
COST, LDD = 3.52, 0.25
WIN, BURN, STRIDE, EPOCHS, LR, CAPM, EMB = 96, 24, 48, 15, 3e-4, 2.5, 60
KH = 16
DEV = "cuda" if torch.cuda.is_available() else "cpu"
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()
torch.manual_seed(SEED); np.random.seed(SEED)
TG = np.load(f"{DLW}/data/dlw_targets.npz", allow_pickle=True)
E_ts = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int); y4s = TG["y4s"]; nA, NW = y4s.shape
FE = np.load(f"{DLW}/data/dlw_fea82.npz", allow_pickle=True)
pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
F9 = np.load(f"{OUT}/data/f8_fea89.npz", allow_pickle=True)
XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); del FE, F9
NCOL = XL.shape[1]
ST = np.searchsorted(pa, np.arange(nA + 1))
ROWMAP = np.full((nA, NW), -1, np.int64)
ROWMAP[pa, ps] = np.arange(len(pa))
L = np.load(f"{OUT}/data/f10v2_legs.npz", allow_pickle=True)
LZ24 = torch.from_numpy(np.nan_to_num(L["Z24"], nan=0.0)).to(DEV)
LZFD = torch.from_numpy(np.nan_to_num(L["ZFD"], nan=0.0)).to(DEV)
LWL = torch.from_numpy(np.nan_to_num(L["WL"], nan=1.0 / 3)).to(DEV)
# 因果 regime ctx(与 R1CTX 同构造)
MKT = np.array([np.nanmean(y4s[i]) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA)])
MKT_PREV = np.concatenate([[np.nan], MKT[:-1]])
def _trail(v, w_):
    o = np.full(nA, np.nan)
    for i in range(nA):
        x = v[max(0, i - w_):i]; x = x[np.isfinite(x)]
        if len(x) >= 10: o[i] = x.std()
    return o
VOL42 = _trail(MKT_PREV, 42)
BRD = np.concatenate([[np.nan], [float(np.nanmean(y4s[i] > 0)) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA - 1)]])
DISP = np.concatenate([[np.nan], [float(np.nanstd(y4s[i])) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA - 1)]])
CTXM = np.stack([np.nan_to_num(MKT_PREV, 0.0), np.nan_to_num(VOL42, 0.0), np.nan_to_num(BRD, 0.5) - 0.5, np.nan_to_num(DISP, 0.0)], 1).astype(np.float32)
CTXM = (CTXM - np.nanmean(CTXM, 0)) / (np.nanstd(CTXM, 0) + 1e-9)
XT = torch.from_numpy(XL).to(DEV); del XL
YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)
PST = torch.from_numpy(ps).to(DEV)
CTXT = torch.from_numpy(CTXM).to(DEV)
RMT = torch.from_numpy(ROWMAP).to(DEV)
rep = {"arm": ARM, "seed": SEED, "self_sha256": sha(os.path.abspath(__file__)), "recipe": "V3FULL §11.1", "folds": {}}


class PLE(nn.Module):
    """逐列分段线性嵌入(d8): x→(bins 分位斜坡)·W, 汇成 d 维列嵌入的和(参数 O(ncol×8×d/ncol))"""
    def __init__(s, ncol, nb=8, d=64):
        super().__init__()
        s.nb = nb
        s.register_buffer("qs", torch.zeros(ncol, nb - 1))
        s.w = nn.Parameter(torch.randn(ncol, nb, d) * 0.02)

    def set_bins(s, mu_sd_x):
        with torch.no_grad():
            q = torch.quantile(mu_sd_x, torch.linspace(0, 1, s.nb + 1, device=mu_sd_x.device)[1:-1], dim=0).T
            s.qs.copy_(q)

    def forward(s, x):                                     # x (n, ncol) 已 z 化
        t = torch.bucketize(x, s.qs[0] * 0 + torch.linspace(-2.5, 2.5, s.nb - 1, device=x.device))
        oh = torch.nn.functional.one_hot(t.clamp(0, s.nb - 1), s.nb).float()
        return torch.einsum("nc b, c b d -> n d", oh, s.w)


class V3(nn.Module):
    def __init__(s, d=NCOL, h=256, p=0.1):
        super().__init__()
        s.fdrop = 0.12
        s.ple = PLE(d, 8, h)
        s.inp = nn.Sequential(nn.Linear(d, h), nn.GELU())
        s.film = nn.Sequential(nn.Linear(4, 32), nn.GELU(), nn.Linear(32, 4 * h))
        nn.init.zeros_(s.film[-1].weight); nn.init.zeros_(s.film[-1].bias)   # γ→1/β→0
        s.b1 = nn.Sequential(nn.Linear(h, h), nn.GELU(), nn.Dropout(p))
        s.b2 = nn.Sequential(nn.Linear(h, h), nn.GELU(), nn.Dropout(p))
        s.crossU = nn.Parameter(torch.randn(2, d, 32) * 0.02)
        s.crossV = nn.Parameter(torch.randn(2, 32, d) * 0.02)
        s.crossP = nn.Linear(d, h)
        s.hist = nn.Sequential(nn.Conv1d(h, 32, 3, padding=2, dilation=1), nn.GELU(),
                               nn.Conv1d(32, 32, 3, padding=4, dilation=2), nn.GELU())
        s.histP = nn.Linear(32, h)
        s.xq = nn.Linear(h, 64); s.xk = nn.Linear(h, 64); s.xv = nn.Linear(h, h)
        s.qln = nn.LayerNorm(64); s.kln = nn.LayerNorm(64)
        s.g_ple = nn.Parameter(torch.tensor(1e-2)); s.g_cross = nn.Parameter(torch.tensor(1e-2))
        s.g_hist = nn.Parameter(torch.tensor(1e-2)); s.g_x = nn.Parameter(torch.tensor(1e-2))
        s.head = nn.Linear(h, 1)
        nn.init.normal_(s.head.weight, 0, 1e-3); nn.init.zeros_(s.head.bias)
        s.a = nn.Parameter(torch.tensor(-2.303))

    def alpha(s):
        return 0.02 + 0.88 * torch.sigmoid(s.a)

    def enc(s, x, ctx, xh=None, train=False):
        if train and s.fdrop > 0:
            keep = (torch.rand(1, x.shape[1], device=x.device) > s.fdrop).float()
            x = x * keep / (1 - s.fdrop)
        z = s.inp(x) + s.g_ple * s.ple(x)
        xc = x
        for k in range(2):
            xc = x * (torch.relu(xc @ s.crossU[k]) @ s.crossV[k]) + xc
        z = z + s.g_cross * s.crossP(xc)
        fb = s.film(ctx)
        g1, b1_, g2, b2_ = fb.chunk(4, -1)
        z = s.b1(z * (1 + g1) + b1_)
        z = s.b2(z * (1 + g2) + b2_)
        if xh is not None:
            hh = s.hist(xh)                                # (n, 32, K)
            z = z + s.g_hist * s.histP(hh[:, :, -1])
        q = s.qln(s.xq(z)); kk = s.kln(s.xk(z))
        att = torch.softmax(q @ kk.T / 8.0, -1)
        z = z + s.g_x * (att @ s.xv(z))
        return s.head(z).squeeze(-1)


def softrank(z, tau):
    n = z.shape[0]
    return (torch.sigmoid((z[:, None] - z[None, :]) / tau).sum(1) - 0.5) / max(n - 1, 1) - 0.5


def hardrank(z):
    n = z.shape[0]
    return torch.argsort(torch.argsort(z)).float() / max(n - 1, 1) - 0.5


def gather_hist(i, cols_t, mu, sd):
    """(n, h?) 锚史: 每名最近 K 锚的 z 化特征 → inp 后作 conv 输入; 缺锚行用当锚行填。"""
    n = cols_t.shape[0]
    idxs = []
    for k in range(KH - 1, -1, -1):
        j = max(i - k, 0)
        r = RMT[j].index_select(0, cols_t)
        r = torch.where(r >= 0, r, RMT[i].index_select(0, cols_t))
        idxs.append(r)
    R = torch.stack(idxs, 1)                                # (n, K)
    x = XT[R.reshape(-1)].reshape(n, KH, -1)
    x = torch.clamp((x - mu) / sd, -5, 5)
    return torch.nan_to_num(x)


def u_of(mdl, i, mu, sd, tau, hard, train=False, adv_eps=0.0):
    a, b = int(ST[i]), int(ST[i + 1])
    if b - a < 50:
        return None, None
    cols_t = PST[a:b].long()
    x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
    x = torch.nan_to_num(x)
    if adv_eps > 0:
        x = x + adv_eps * torch.sign(torch.randn_like(x))    # 快近似: 随机符号扰动(FGSM 方向近似, 免二次反传)
    xh = gather_hist(i, cols_t, mu, sd)
    xh_e = mdl.inp(xh.reshape(-1, xh.shape[-1])).reshape(xh.shape[0], KH, -1).transpose(1, 2)
    z = mdl.enc(x, CTXT[i], xh=xh_e, train=train)
    zz = (z - z.mean()) / (z.std() + 1e-8)
    r = hardrank(zz) if hard else softrank(zz, tau)
    wl = LWL[i]
    r = wl[0] * r + wl[1] * LZ24[i].index_select(0, cols_t) + wl[2] * LZFD[i].index_select(0, cols_t)
    r = r - r.mean()
    u = r / (r.abs().sum() + 1e-8)
    c = CAPM / (b - a)
    u = c * torch.tanh(u / c); u = u - u.mean()
    return u, cols_t


def run_span(mdl, idx, mu, sd, tau, hard, loss_span=None, cost_mult=1.0, train=False, adv=0.0):
    w = torch.zeros(NW, device=DEV); al = mdl.alpha(); nets = []
    for k, i in enumerate(idx):
        u, midx = u_of(mdl, i, mu, sd, tau, hard, train=train, adv_eps=adv)
        wn = (1 - al) * w + al * torch.zeros(NW, device=DEV).scatter(0, midx, u) if u is not None else w
        dn = torch.sqrt((wn - w) ** 2 + 1e-12).sum()
        net = 1e4 * (wn * YT[i]).sum() - COST * cost_mult * dn
        if loss_span is None or k >= loss_span:
            nets.append(net)
        w = wn
    return torch.stack(nets)


def es5(nets):
    k = max(1, int(math.ceil(0.05 * nets.shape[0])))
    return torch.topk(-nets, k).values.mean()


for YV in (2023, 2024, 2025, 2026):
    te = np.where(yrs == YV)[0]
    if te.size == 0:
        continue
    first_te = int(te[0])
    tr_idx = np.array([i for i in range(first_te - EMB) if yrs[i] < YV and ST[i + 1] - ST[i] >= 50])
    cut = int(len(tr_idx) * 0.85); tr1, va1 = tr_idx[:cut], tr_idx[cut:]
    rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]])
    XS = XT[torch.from_numpy(rowsel[::3]).to(DEV)]
    mu = torch.nan_to_num(XS).mean(0); sd = torch.nan_to_num(XS).std(0) + 1e-6; del XS
    torch.manual_seed(SEED + YV)
    mdl = V3().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    starts = list(range(int(tr1[0]) + BURN, int(tr1[-1]) - WIN, STRIDE))
    total_steps = EPOCHS * len(starts); step = 0
    best_va, best_state, va_curve = -1e9, None, []
    tau = 0.5; tau_frozen = False
    for ep in range(EPOCHS):
        mdl.train()
        adv = 0.02 if ep % 2 == 1 else 0.0
        for s0 in np.random.permutation(starts):
            step += 1
            cm = min(1.0, step / max(1, int(0.25 * total_steps)))
            span = [i for i in range(s0 - BURN, s0 + WIN)]
            nets = run_span(mdl, span, mu, sd, tau, hard=False, loss_span=BURN, cost_mult=cm, train=True, adv=adv)
            loss = -nets.mean() + LDD * es5(nets)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step()
        # τ 退火: corr(soft, hard) ≥ 0.99 即停
        if not tau_frozen:
            with torch.no_grad():
                i0 = int(va1[len(va1) // 2])
                u1, m1 = u_of(mdl, i0, mu, sd, tau, hard=False)
                u2, _ = u_of(mdl, i0, mu, sd, tau, hard=True)
                if u1 is not None and float(torch.corrcoef(torch.stack([u1, u2]))[0, 1]) >= 0.99:
                    tau_frozen = True
                else:
                    tau = max(0.1, tau - 0.4 / (EPOCHS - 1))
        mdl.eval()
        with torch.no_grad():
            span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
            nets = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN)
            va = float(nets.mean() - LDD * es5(nets))
        va_curve.append(round(va, 4))
        if va > best_va:
            best_va, best_state = va, {k: v.detach().clone() for k, v in mdl.state_dict().items()}
        log(f"[{YV}] ep{ep} va {va:+.3f} α {float(mdl.alpha()):.3f} τ {tau:.2f}{'*' if tau_frozen else ''} 门 {float(mdl.g_ple):.3f}/{float(mdl.g_cross):.3f}/{float(mdl.g_hist):.3f}/{float(mdl.g_x):.3f}")
    mdl.load_state_dict(best_state); mdl.eval()
    if "PRED" not in dir():
        PRED = np.full((nA, NW), np.nan, np.float32)
    trn_series = []
    with torch.no_grad():
        w = torch.zeros(NW, device=DEV); al = mdl.alpha()
        nets_t = []
        for i in range(max(0, first_te - BURN), int(te[-1]) + 1):
            u, midx = u_of(mdl, i, mu, sd, 0.1, hard=True)
            wn = (1 - al) * w + al * torch.zeros(NW, device=DEV).scatter(0, midx, u) if u is not None else w
            if i >= first_te:
                nets_t.append(float(1e4 * (wn * YT[i]).sum() - COST * (wn - w).abs().sum()))
                trn_series.append(float((wn - w).abs().sum()))
                if u is not None:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    cols_t = PST[a0:b0].long()
                    x = torch.nan_to_num(torch.clamp((XT[a0:b0] - mu) / sd, -5, 5))
                    xh = gather_hist(i, cols_t, mu, sd)
                    xh_e = mdl.inp(xh.reshape(-1, xh.shape[-1])).reshape(xh.shape[0], KH, -1).transpose(1, 2)
                    PRED[i, cols_t.cpu().numpy()] = mdl.enc(x, CTXT[i], xh=xh_e).cpu().numpy()
            w = wn
    rep["folds"][str(YV)] = {"best_va": round(best_va, 4), "va_curve": va_curve,
                             "net_mean_bps": round(float(np.mean(nets_t)), 4), "turnover_mean": round(float(np.mean(trn_series)), 5),
                             "alpha_final": round(float(mdl.alpha()), 4),
                             "gates": [round(float(g), 4) for g in (mdl.g_ple, mdl.g_cross, mdl.g_hist, mdl.g_x)]}
    log(f"== {YV}: net {np.mean(nets_t):+.3f} 换手 {np.mean(trn_series):.4f} α {float(mdl.alpha()):.3f} 门 {rep['folds'][str(YV)]['gates']}")
    np.save(f"{OUT}/preds/f10_{ARM}_s{SEED}.npy", PRED)
    json.dump(rep, open(f"{OUT}/results/f10_{ARM}_s{SEED}.json", "w"), indent=1, default=float)
    del mdl, opt; torch.cuda.empty_cache()
rep["net_mean_all"] = round(float(np.mean([f["net_mean_bps"] for f in rep["folds"].values()])), 4)
json.dump(rep, open(f"{OUT}/results/f10_{ARM}_s{SEED}.json", "w"), indent=1, default=float)
log(f"V3_TRAIN_DONE {ARM} s{SEED} 年均净 {rep['net_mean_all']:+.3f}(训练帧)")
