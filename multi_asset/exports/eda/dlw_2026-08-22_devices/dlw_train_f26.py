"""DLW · film2 K400 协议训练臂 D0 / D1(h) @jpline 3090(2026-08-22, Session 6737834a-DLW)。
预注册 §P.1–P.3(冻结段 SHA256 33f066c9…64577, commit 7acda02)。
训练体逐字沿袭 multi_asset/exports/eda/kcurve_2026-08-15/pod_kcurve.py(film2: 8 层膨胀卷积 CHW=128 + GroupNorm + FiLM(8 维 regime ctx)
+ 末 288 行注意力池化 ∥ 末行 → z(256) → [顶部横截面 MHA(256, h) + LayerNorm + 残差] → QIM 25 分位 pinball 头; EPOCHS 8 / LR 1e-3 / AdamW wd 1e-4 /
余弦 / 梯度裁剪 1.0 / BATCH 4 锚 / 验证集 = 训练锚末 15%, 检查点 = 验证 IC 最高 epoch), 改动只有三处且全部冻结于预注册:
  ① 锚/成员/标签/目标来自 dlw_targets.npz(唯一真相源; 标签 YRZ = 成员内残差简单收益秩; 验证/测试 IC 对 YR4s 与 y4s 双报);
  ② 输入行窗对齐为 [E−575, E](含收盘于 N 的 bar; regime ctx 同), 目标行 ≥ E+1(装置断言);
  ③ XA=0 ⇒ 移除顶部横截面 MHA 与其 LayerNorm(D0); XA=1 ⇒ 保留, 头数 HEADS ∈ {8(原样), 4, 1}(D1(h))。
产物: preds/dlw_{ARM}_s{SEED}.npy(锚 × 829, 逐折追加保存), results/dlw_{ARM}_s{SEED}.json(逐年 IC 双口径 / 验证曲线 / 用时 / cuDNN / 显存峰值 / n_params)。
用法 @jpline: XA=0|1 HEADS=8|4|1 SEED=42 python -u dlw_train.py   (单卡单任务; 由 dlw_queue.sh 串行调度)
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
import torch, torch.nn as nn

ROOT = "/mnt/storage/private/work_hsy"; OUT = f"{ROOT}/dlw_2026-08-22"
CACHE = f"{ROOT}/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz"
XA = int(os.environ.get("XA", "1")); HEADS = int(os.environ.get("HEADS", "8")); SEED = int(os.environ.get("SEED", "42"))
EPOCHS = int(os.environ.get("EPOCHS", "8")); LR = float(os.environ.get("LR", "1e-3")); DROP = float(os.environ.get("DROP", "0"))
BATCH = int(os.environ.get("BATCH", "4")); CHW = int(os.environ.get("CHW", "128")); RESD = 0; MIDX = 0
ARM = os.environ.get("ARM") or ("D0" if XA == 0 else f"D1h{HEADS}")
W = 576; FWD = 48; TRAIL = 2016; EMBARGO = 60; DEV = "cuda"; QN = 25
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan


assert torch.cuda.is_available(), "GPU required"
CUDNN = torch.backends.cudnn.version()
assert CUDNN is not None, "cuDNN missing (memory feedback_verify_cudnn_not_just_cuda)"
log(f"ARM {ARM} SEED {SEED} XA {XA} HEADS {HEADS} | torch {torch.__version__} cuDNN {CUDNN} GPU {torch.cuda.get_device_name(0)}")
TG = np.load(f"{OUT}/data/dlw_targets.npz", allow_pickle=True)
E = TG["E_row"].astype(np.int64); E_ts = TG["E_ts"].astype(np.int64); MS = list(TG["members"]); yrs = TG["yrs"]
YRZ = TG["YRZ"]; YR4s = TG["YR4s"]; y4s = TG["y4s"]; csyms = [str(s) for s in TG["symbols"]]
nA = len(E); NW = len(csyms)
Z = np.load(CACHE, allow_pickle=True)
CD = Z["data"]; CTS = Z["ts"].astype(np.int64)
assert [str(s) for s in Z["symbols"]] == csyms and np.array_equal(CTS[E], E_ts)
TT = CD.shape[0]; BTC_T = csyms.index("BTCUSDT")
assert E.min() - W + 1 >= 0 and E.max() + FWD <= TT - 1
MS_T = [torch.from_numpy(np.asarray(m, dtype=np.int64)).to(DEV) for m in MS]
CDT = torch.from_numpy(np.ascontiguousarray(CD)).to(DEV)
del CD, Z
log(f"anchors {nA} 平均成员 {np.mean([len(m) for m in MS]):.0f} | CDT {tuple(CDT.shape)} {CDT.dtype} on GPU")


def regime_ctx(i, cols_t):
    e = int(E[i]); s0 = max(e - TRAIL + 1, 0)           # rows [e−2015, e] (≤ E)
    blk = CDT[s0:e + 1].index_select(1, cols_t).float()
    r = torch.nan_to_num(blk[:, :, 0])
    vol7 = r.std(0)
    btcv = torch.nan_to_num(CDT[s0:e + 1, BTC_T, 0].float()).std()
    disp = torch.nan_to_num(blk[-576:, :, 0]).sum(0).std()
    breadth = (torch.nan_to_num(blk[-288:, :, 0]).sum(0) > 0).float().mean()
    absr = r.abs().mean()
    volpct = vol7.argsort().argsort().float() / max(len(vol7) - 1, 1) - 0.5
    qz = torch.nan_to_num(blk[-288:, :, 3]).mean(0)
    qz = (qz - qz.mean()) / (qz.std() + 1e-6)
    tbf = torch.nan_to_num(blk[-288:, :, 6]).mean(0) - 0.5
    n = blk.shape[1]
    mkt = torch.stack([btcv.expand(n), disp.expand(n), breadth.expand(n), absr.expand(n)], -1)
    own = torch.stack([torch.log1p(100 * vol7), volpct, qz, tbf], -1)
    return torch.cat([mkt * 100, own], -1)


def gather_t(i, cols_t):
    e = int(E[i]); s0 = e - W + 1                         # rows [e−575, e] (max_feature_row == E)
    if s0 < 0 or e + 1 > CDT.shape[0]:
        return None
    blk = CDT[s0:e + 1].index_select(1, cols_t).float()
    mk = torch.isfinite(blk)
    xp = torch.where(mk, blk, torch.zeros((), device=DEV))
    return torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)


class Model(nn.Module):
    def __init__(s, ch=CHW, xa=XA, heads=HEADS):
        super().__init__()
        L = []; c = 8
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            if DROP > 0:
                L += [nn.Dropout(DROP)]
            c = ch
        s.net = nn.ModuleList(L)
        s.apq = nn.Linear(ch, 1)
        zd = ch * 2
        s.films = nn.ModuleList([nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2 * ch)) for _ in range(8)])
        s.use_xa = bool(xa)
        s.xa = nn.MultiheadAttention(zd, heads, batch_first=True) if s.use_xa else None
        s.xln = nn.LayerNorm(zd) if s.use_xa else None
        s.head = nn.Linear(zd, QN)

    def enc(s, x, net, ctx=None):
        h = x.transpose(1, 2); nb = 0
        for l in net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0] * 2, 0)); h = l(h)
            else:
                h = l(h)
                if isinstance(l, nn.GroupNorm) and ctx is not None:
                    fb = s.films[nb](ctx); nb += 1
                    h = h * (1 + 0.1 * fb[:, :h.shape[1]].unsqueeze(-1)) + 0.1 * fb[:, h.shape[1]:].unsqueeze(-1)
        return h

    def forward(s, x, sizes, ctx=None):
        h = s.enc(x, s.net, ctx)
        hs = h[:, :, -288:]
        w_ = torch.softmax(s.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        if s.use_xa:                                      # D1: 顶部横截面注意力(同锚成员间), D0 跳过
            parts = torch.split(z, sizes)
            zp = nn.utils.rnn.pad_sequence(parts, batch_first=True)
            mask = torch.ones(zp.shape[:2], dtype=torch.bool, device=z.device)
            for gi, n_ in enumerate(sizes):
                mask[gi, :n_] = False
            q = s.xln(zp)
            a, _ = s.xa(q, q, q, key_padding_mask=mask)
            zp = zp + a
            z = torch.cat([zp[gi, :n_] for gi, n_ in enumerate(sizes)], 0)
        return s.head(z)


QS = torch.tensor([(i + 0.5) / QN for i in range(QN)], device=DEV)
n_params = sum(p.numel() for p in Model().parameters())
log(f"n_params {n_params} (xa={XA}, heads={HEADS})")
res = {"arm": ARM, "seed": SEED, "xa": XA, "heads": HEADS, "n_params": int(n_params), "epochs": EPOCHS, "lr": LR, "batch": BATCH, "chw": CHW,
       "cudnn": int(CUDNN), "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0), "self_sha256": sha(os.path.abspath(__file__)),
       "targets_sha256": sha(f"{OUT}/data/dlw_targets.npz"), "feature_row_window": "[E-575, E]", "target_row_window": "[E+1, E+48]",
       "embargo_anchors": EMBARGO, "folds": {}}
PRED = np.full((nA, NW), np.nan, np.float32)
FOLD_MIN = int(os.environ.get("FOLD_MIN", "0"))  # 2026-08-22: rerun a late fold alone (2026 OOM at BATCH=4)
for YV in (2023, 2024, 2025, 2026):
    if YV < FOLD_MIN:
        continue
    if (yrs == YV).sum() == 0:
        log(f"[{YV}] 无测试锚, 跳过"); continue
    torch.manual_seed(SEED); np.random.seed(SEED); torch.cuda.reset_peak_memory_stats()
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = np.array([i for i in range(nA) if yrs[i] < YV and i < first_te - EMBARGO and np.isfinite(YRZ[i, MS[i]]).sum() >= 30])
    cut = int(len(tr_all) * 0.85); tr1, va1 = tr_all[:cut], tr_all[cut:]
    te = np.where(yrs == YV)[0]
    assert tr_all.max() < first_te - EMBARGO
    sidx = [i for i in tr1[::25]]
    SS = torch.cat([gather_t(i, MS_T[i])[:, ::8, :7].reshape(-1, 7) for i in sidx])
    mu = SS.mean(0); sd = SS.std(0) + 1e-6
    del SS

    def norm(x):
        x = x.clone(); x[:, :, :7] = torch.clamp((x[:, :, :7] - mu) / sd, -5, 5)
        return x
    mdl = Model().to(DEV)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    best_va, best_state, va_curve, ep_sec = -9, None, [], []
    for ep in range(EPOCHS):
        mdl.train(); order = np.random.permutation(tr1); t00 = time.time()
        for bi in range(0, len(order), BATCH):
            xs, ys, sz, cxs = [], [], [], []
            for i in order[bi:bi + BATCH]:
                m = MS[i]; okf = np.isfinite(YRZ[i, m])
                if okf.sum() < 30:
                    continue
                x = gather_t(i, MS_T[i])
                if x is None:
                    continue
                okt = torch.from_numpy(okf).to(DEV)
                x = norm(x)
                xs.append(x[okt]); ys.append(YRZ[i, m[okf]]); sz.append(int(okf.sum()))
                cxs.append(regime_ctx(i, MS_T[i])[okt])
            if not xs:
                continue
            xb = torch.cat(xs); yb = torch.from_numpy(np.concatenate(ys)).to(DEV); cb = torch.cat(cxs)
            o = mdl(xb, sz, ctx=cb)
            d_ = yb.unsqueeze(-1) - o
            loss = torch.maximum(QS * d_, (QS - 1) * d_).mean()
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(mdl.parameters(), 1.0); opt.step()
        sched.step()
        mdl.eval(); v = []
        with torch.no_grad():
            for i in va1:
                m = MS[i]
                x = gather_t(i, MS_T[i])
                if x is None:
                    continue
                x = norm(x)
                p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i])).mean(-1)
                v.append(spear(p.cpu().numpy(), YR4s[i, m]))
        va = float(np.nanmean(v)); va_curve.append(va); ep_sec.append(round(time.time() - t00, 1))
        log(f"[{YV}] ep{ep} va(resid) {va:+.4f} ({time.time() - t00:.0f}s) peakmem {torch.cuda.max_memory_allocated()/2**30:.1f}G")
        if va > best_va:
            best_va, best_state = va, {k: t.cpu().clone() for k, t in mdl.state_dict().items()}
    mdl.load_state_dict(best_state); mdl.eval(); tics_r, tics_y, sig = [], [], []
    with torch.no_grad():
        for i in te:
            m = MS[i]
            x = gather_t(i, MS_T[i])
            if x is None:
                continue
            x = norm(x)
            p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i])).cpu().numpy().mean(-1)
            PRED[i, m] = p
            tics_r.append(spear(p, YR4s[i, m])); tics_y.append(spear(p, y4s[i, m]))
            okz = np.isfinite(YRZ[i, m])
            if okz.sum() >= 30:
                sig.append(float(np.std(p[okz]) / (np.std(YRZ[i, m][okz]) + 1e-12)))
    res["folds"][str(YV)] = {"n_train": int(len(tr1)), "n_val": int(len(va1)), "n_test": int(len(te)), "best_va": best_va, "best_epoch": int(np.argmax(va_curve)),
                             "va_curve": va_curve, "epoch_sec": ep_sec, "ic_resid": float(np.nanmean(tics_r)), "ic_raw": float(np.nanmean(tics_y)),
                             "sigma_ratio_median": float(np.nanmedian(sig)), "peak_mem_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)}
    np.save(f"{OUT}/preds/dlw_{ARM}_s{SEED}.npy", PRED)
    json.dump(res, open(f"{OUT}/results/dlw_{ARM}_s{SEED}.json", "w"), indent=1)
    log(f"== {YV}: IC resid {np.nanmean(tics_r):+.4f} raw {np.nanmean(tics_y):+.4f} σŷ/σy {np.nanmedian(sig):.3f} best_ep {int(np.argmax(va_curve))}")
    del mdl, opt, best_state; torch.cuda.empty_cache()
res["ic_resid_mean"] = float(np.mean([f["ic_resid"] for f in res["folds"].values()]))
res["ic_raw_mean"] = float(np.mean([f["ic_raw"] for f in res["folds"].values()]))
res["total_sec"] = round(time.time() - T0, 1)
json.dump(res, open(f"{OUT}/results/dlw_{ARM}_s{SEED}.json", "w"), indent=1)
log(f"TRAIN_DONE {ARM} s{SEED}: 年均 IC resid {res['ic_resid_mean']:+.4f} raw {res['ic_raw_mean']:+.4f} | {res['total_sec']/3600:.2f}h")
