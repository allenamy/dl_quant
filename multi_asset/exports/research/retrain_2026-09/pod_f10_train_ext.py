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

ROOT = "/workspace"
DLW = os.environ.get("F10_DLW", f"{ROOT}/dlw_ext")
OUT = os.environ.get("F10_OUT", f"{ROOT}/f8_ext")
SEED = int(os.environ.get("SEED", "42")); ARM = os.environ.get("ARM", "MAIN")
COST = float(os.environ.get("COST", "3.52")); LDD = float(os.environ.get("LDD", "0.25"))
AFIX = int(os.environ.get("AFIX", "0"))
LDC = float(os.environ.get("LDC", "0.0"))     # R1: 条件尾部权重(因果代理最低五分位)
CTXA = int(os.environ.get("CTXA", "0"))       # 架构A: 因果 regime 上下文 4 维
REC = int(os.environ.get("REC", "0"))
PLEON = int(os.environ.get("PLE", "0"))       # PLE 提取臂: V3 认证的逐列 8 桶固定网格嵌入(恰一个变量)         # 架构B: 逐名递归分数态(HRT 学习衰减门)
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
NCOL = int(os.environ.get("NCOL", "167"))
EXTRA = os.environ.get("EXTRA", "")            # ""|"e4"(L3四头+旗标5列)|"lob38"|"cc3"(在役三腿z)
LPP = float(os.environ.get("LPP", "0.0"))      # L2 持久罚: 惩罚 |u_t − u_{t−1}|
if NCOL == 78:
    # 归因臂: 去掉 89 新列 + 4 根 king 剔除的快列 = 忠实 king 弹药(唯一变量 vs MAIN = 弹药)
    KEEP = [i for i in range(82) if i not in (0, 1, 2, 3)]
    XL = XL[:, KEEP]
del X82, FE, F9
if EXTRA == "e4":
    _AP = np.load(f"{OUT}/preds/f12_heads_s42.npz", allow_pickle=True)
    _sc = _AP["scol60"].astype(np.int64); _m = {int(c): j for j, c in enumerate(_sc)}
    _A4 = _AP["AP"].astype(np.float32)
    E4 = np.zeros((len(pa), 5), np.float32)
    for r in range(len(pa)):
        j = _m.get(int(ps[r]))
        if j is not None:
            v = _A4[pa[r], j]
            if np.isfinite(v).all():
                E4[r, :4] = v; E4[r, 4] = 1.0
    XL = np.concatenate([XL, E4], 1); del _AP, _A4, E4
elif EXTRA == "lob38":
    import glob as _g
    _parts = sorted(_g.glob(f"{OUT}/data/f11_parts/*.npz"))
    _z0 = np.load(_parts[0], allow_pickle=True); _K = _z0["fe"].shape[1]
    _L38 = np.full((nA, NW, _K), np.nan, np.float32)
    for _pp in _parts:
        _z = np.load(_pp, allow_pickle=True)
        _L38[:, int(_z["scol"]), :] = _z["fe"][:, :_K]
    R38 = np.nan_to_num(_L38[pa, ps], nan=0.0).astype(np.float32)
    XL = np.concatenate([XL, R38], 1); del _L38, R38
elif EXTRA == "tree1":
    # V2TREE(PREREG_v2tree_2026-08-26): f4 树的 walk-forward OOS 分数作第 172 列。
    # 因果: 逐年折+embargo60 的折外分数, 锚 t 处为已知量; NaN(折前/缺名)→0(mu/sd 标准化后近似均值填充)。
    _TP = np.load(f"{OUT}/preds/f4_lgbm_K171raw.npy")
    T1 = np.nan_to_num(_TP[pa, ps], nan=0.0).astype(np.float32)[:, None]
    XL = np.concatenate([XL, T1], 1); del _TP, T1
elif EXTRA == "cc3":
    _LG = np.load(f"{OUT}/data/f10v2_legs2.npz", allow_pickle=True)
    C3 = np.stack([np.nan_to_num(_LG[k], nan=0.0)[pa, ps] for k in ("KZ", "Z24", "ZFD")], 1).astype(np.float32)
    XL = np.concatenate([XL, C3], 1); del _LG, C3
ST = np.searchsorted(pa, np.arange(nA + 1))
V2 = int(os.environ.get("V2", "0"))
if V2:
    _L = np.load(f"{OUT}/data/f10v2_legs.npz", allow_pickle=True)
    LZ24 = torch.from_numpy(np.nan_to_num(_L["Z24"], nan=0.0)).to("cuda" if torch.cuda.is_available() else "cpu")
    LZFD = torch.from_numpy(np.nan_to_num(_L["ZFD"], nan=0.0)).to(LZ24.device)
    LWL = torch.from_numpy(np.nan_to_num(_L["WL"], nan=1.0 / 3)).to(LZ24.device)
    HASL = torch.from_numpy(np.isfinite(_L["WL"][:, 0])).to(LZ24.device)
# ── R1/A: 因果代理与上下文(全部只用 ≤ t−1 信息)──
MKT = np.array([np.nanmean(y4s[i]) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA)])
MKT_PREV = np.concatenate([[np.nan], MKT[:-1]])
FLAG = np.zeros(nA, bool)
for i in range(nA):
    lo = max(0, i - 500)
    w = MKT_PREV[lo:i + 1]
    w = w[np.isfinite(w)]
    if len(w) >= 100 and np.isfinite(MKT_PREV[i]):
        FLAG[i] = MKT_PREV[i] <= np.quantile(w, 0.2)
def _trail(v, w_):
    o = np.full(nA, np.nan)
    for i in range(nA):
        x = v[max(0, i - w_):i]
        x = x[np.isfinite(x)]
        if len(x) >= 10:
            o[i] = x.std() if w_ > 1 else x[-1]
    return o
VOL42 = _trail(MKT_PREV, 42)
BRD = np.concatenate([[np.nan], [float(np.nanmean(y4s[i] > 0)) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA - 1)]])
DISP = np.concatenate([[np.nan], [float(np.nanstd(y4s[i])) if np.isfinite(y4s[i]).sum() >= 30 else np.nan for i in range(nA - 1)]])
CTXM = np.stack([np.nan_to_num(MKT_PREV, nan=0.0), np.nan_to_num(VOL42, nan=0.0),
                 np.nan_to_num(BRD, nan=0.5) - 0.5, np.nan_to_num(DISP, nan=0.0)], 1).astype(np.float32)
CTXM = (CTXM - np.nanmean(CTXM, 0)) / (np.nanstd(CTXM, 0) + 1e-9)
FLAGT = torch.from_numpy(FLAG)
CTXT = torch.from_numpy(CTXM)
medy = float(np.nanmedian(np.abs(y4s[np.isfinite(y4s)])))
assert 1e-4 <= medy <= 0.05, f"y4s 疑似非小数收益 med|y|={medy}"    # 小数收益口径守卫
log(f"rows {len(pa)} cols {XL.shape[1]} anchors {nA} med|y| {medy:.5f}")

XT = torch.from_numpy(XL).to(DEV); del XL
CTXT = CTXT.to(DEV); FLAGT = FLAGT.to(DEV)
YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)
PST = torch.from_numpy(ps).to(DEV)
rep = {"arm": ARM, "seed": SEED, "cost": COST, "ldd": LDD, "afix": AFIX, "epochs": EPOCHS,
       "lr": LR, "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB,
       "self_sha256": sha(os.path.abspath(__file__)),
       "targets_sha256": sha(f"{DLW}/data/dlw_targets.npz"),
       "fea82_sha256": sha(f"{DLW}/data/dlw_fea82.npz"), "fea89_sha256": sha(f"{OUT}/data/f8_fea89.npz"),
       "folds": {}}


class PLEmb(nn.Module):
    """V3 认证机制原样搬运: 固定网格(±2.5σ, nb 桶)硬 one-hot × 可学 (col,bin,d) 嵌入, 列上求和"""
    def __init__(s, ncol, nb=8, d=256):
        super().__init__()
        s.nb = nb
        s.w = nn.Parameter(torch.randn(ncol, nb, d) * 0.02)

    def forward(s, x):
        t = torch.bucketize(x, torch.linspace(-2.5, 2.5, s.nb - 1, device=x.device))
        oh = torch.nn.functional.one_hot(t.clamp(0, s.nb - 1), s.nb).float()
        return torch.einsum("ncb,cbd->nd", oh, s.w)


class Net(nn.Module):
    def __init__(s, d=167, h=256, p=0.1, hs=32):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))          # sigmoid→0.0909 ⇒ α≈0.10
        if PLEON:
            s.ple = PLEmb(d, 8, h); s.g_ple = nn.Parameter(torch.tensor(1e-2))
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)
        if REC:
            s.emb = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU())
            s.push = nn.Linear(h, hs); s.gate = nn.Linear(h, hs)
            nn.init.constant_(s.gate.bias, -1.5)          # HRT: 慢记忆先验
            s.head2 = nn.Linear(h + hs, 1)
            nn.init.normal_(s.head2.weight, 0.0, 1e-3); nn.init.zeros_(s.head2.bias)

    def score_rec(s, x, hp):
        e = s.emb(x)
        g = torch.sigmoid(s.gate(e)) ** 3                 # cubic-sigmoid 衰减门(HRT)
        hn = hp * (1 - g) + s.push(e) * g
        return s.head2(torch.cat([e, hn], -1)).squeeze(-1), hn

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


def u_of(mdl, i, mu, sd, tau, hard, H=None):
    # V2: cols_t = 本锚成员在 829 维中的列号(用于取固定腿)
    a, b = int(ST[i]), int(ST[i + 1])
    if b - a < 50:
        return None, None
    cols_t = PST[a:b].long()
    x = torch.clamp((XT[a:b] - mu) / sd, -5, 5)
    if CTXA:
        x = torch.cat([x, CTXT[i].expand(b - a, 4)], 1)
    if REC and H is not None:
        s, hn = mdl.score_rec(torch.nan_to_num(x), H[cols_t])
    else:
        xin = torch.nan_to_num(x)
        if PLEON:
            s = mdl.f[1:](mdl.f[0](xin) + mdl.g_ple * mdl.ple(xin)).squeeze(-1); hn = None
        else:
            s = mdl.f(xin).squeeze(-1); hn = None
    z = (s - s.mean()) / (s.std() + 1e-8)
    r = hardrank(z) if hard else softrank(z, tau)
    if V2 and bool(HASL[i]):
        # 合成链: msharpe 腿权 × [model, rev24, fund] 的 rank-z, 与 f3 同序(先合成后 去均值/L1/cap)
        wl = LWL[i]
        r = wl[0] * r + wl[1] * LZ24[i].index_select(0, cols_t) + wl[2] * LZFD[i].index_select(0, cols_t)
    r = r - r.mean()
    u = r / (r.abs().sum() + 1e-8)
    c = CAPM / (b - a)
    u = c * torch.tanh(u / c)
    u = u - u.mean()
    return u, PST[a:b], (cols_t, hn)


def run_span(mdl, idx, mu, sd, tau, hard, w0=None, loss_span=None):
    """按时序推进 idx 内的链; 返回 (net序列(loss_span部分), w_end)。"""
    w = torch.zeros(NW, device=DEV) if w0 is None else w0
    H = torch.zeros(NW, 32, device=DEV) if REC else None
    al = mdl.alpha()
    nets = []
    for k, i in enumerate(idx):
        u, midx, hst = u_of(mdl, i, mu, sd, tau, hard, H)
        if u is not None:
            if REC and hst[1] is not None:
                H = H.index_put((hst[0],), hst[1])
            uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u)
            wn = (1 - al) * w + al * uf
        else:
            wn = w
        dn = torch.sqrt((wn - w) ** 2 + 1e-12).sum()
        net = 1e4 * (wn * YT[i]).sum() - COST * dn
        if LPP > 0 and u is not None:
            uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u) if not REC else torch.zeros(NW, device=DEV).scatter(0, hst[0].long(), u)
            if "up" in locals() and up is not None:
                net = net - LPP * 1e4 * torch.sqrt((uf - up) ** 2 + 1e-12).sum() * 0.0  # 罚进 loss 不进 net
            up = uf
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
    mdl = Net(XT.shape[1] + (4 if CTXA else 0)).to(DEV)
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
            if LPP > 0:
                us = []
                for i2 in span[BURN::4]:
                    u2, m2, _h = u_of(mdl, i2, mu, sd, tau, False)
                    if u2 is not None:
                        us.append(torch.zeros(NW, device=DEV).scatter(0, m2.long(), u2))
                if len(us) > 1:
                    loss = loss + LPP * torch.stack([torch.abs(us[k + 1] - us[k]).sum() for k in range(len(us) - 1)]).mean() * 1e2
            if LDC > 0:
                fl = FLAGT[torch.tensor(span[BURN:], device=DEV)]
                if int(fl.sum()) >= 3:
                    nf = nets[fl]
                    k = max(1, min(int(fl.sum()), int(math.ceil(0.05 * nets.shape[0]))))
                    loss = loss + LDC * torch.topk(-nf, k).values.mean()
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sch.step()
        mdl.eval()
        with torch.no_grad():
            span = [int(i) for i in np.concatenate([tr1[-BURN:], va1])]
            nets, _ = run_span(mdl, span, mu, sd, 0.1, hard=True, loss_span=BURN)
            va = float(nets.mean() - LDD * es5(nets))
            if LDC > 0:
                flv = FLAGT[torch.tensor(span[BURN:], device=DEV)]
                if int(flv.sum()) >= 3:
                    kv = max(1, min(int(flv.sum()), int(math.ceil(0.05 * nets.shape[0]))))
                    va -= float(LDC * torch.topk(-nets[flv], kv).values.mean())
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
        HT = torch.zeros(NW, 32, device=DEV) if REC else None
        PRED_f = np.full((len(te), NW), np.nan, np.float32)
        for k, i in enumerate(span):
            u, midx, hst = u_of(mdl, i, mu, sd, 0.1, hard=True, H=HT)
            if REC and hst[1] is not None:
                HT = HT.index_put((hst[0],), hst[1].detach())
            if u is not None:
                uf = torch.zeros(NW, device=DEV).scatter(0, midx.long(), u)
                wn = (1 - al) * w + al * uf
                if i >= first_te:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                    if CTXA:
                        x = torch.cat([x, CTXT[i].expand(b0 - a0, 4)], 1)
                    if REC:
                        sc, _ = mdl.score_rec(torch.nan_to_num(x), HT[PST[a0:b0].long()])
                        PRED_f[i - first_te, midx.cpu().numpy()] = sc.cpu().numpy()
                    else:
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
