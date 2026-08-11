"""W5/#47 SSL 预训练器 — 下 bar 预测(因果), 逐折, 严格与监督折同数据同 embargo。
PREREG_ssl_pretrain_2026-08-10(冻结)。产出: exports_train/ssl_enc32/fold_{i}_encoder.pt
用法: python3 pretrain_ssl.py <panel.npz> <out_dir> [epochs] [seed]"""
import sys, os, time
import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, "/workspace/code")
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.train.train_wide_harness import year_folds, build_encoder, KERNEL, DROPOUT

PANEL = sys.argv[1]
OUT = sys.argv[2]
EPOCHS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 42
DEV = "cuda"
os.makedirs(OUT, exist_ok=True)

data = WidePanelData(path=PANEL, target_horizon=4, aux_horizons=(1, 24))
folds = year_folds(data, embargo_days=10, val_days=30, year_from=2022)
print(f"[ssl] panel={PANEL} T={data.T} N={data.N} C={data.C} W={data.W} folds={len(folds)}", flush=True)

HORIZONS = (1, 4, 8)          # 下 bar 主 + 两辅(削平凡持续性解)
HW = {1: 1.0, 4: 0.5, 8: 0.25}
# 每窗口取的预测位置数(从窗尾往前, 留出最大视界)
NPOS = 48

for fi, fold in enumerate(folds):
    torch.manual_seed(SEED + fi); np.random.seed(SEED + fi)
    tr, va = fold["tr"], fold["va"]
    data.set_fold(tr)                       # 训练统计量 = 该折监督训练同口径
    enc = build_encoder("conformer", data.C, 64, 2, KERNEL, DROPOUT).to(DEV)
    core = enc.enc                          # SharedTemporalEncoder
    core.backbone.return_sequence = True
    heads = nn.ModuleDict({str(h): nn.Linear(64, data.C) for h in HORIZONS}).to(DEV)
    opt = torch.optim.AdamW(list(enc.parameters()) + list(heads.parameters()), lr=1e-3,
                            weight_decay=1e-4)
    hub = nn.HuberLoss(delta=1.0, reduction="none")
    rng = np.random.default_rng(SEED + fi)
    best_va, best_state, bad = 1e9, None, 0
    t00 = time.time()
    for ep in range(EPOCHS):
        enc.train(); heads.train()
        tot, nb = 0.0, 0
        for b in data.iter_batches(tr, batch_hours=48, rng=rng, shuffle=True, train=True):
            X = torch.from_numpy(b["Xseq"]).to(DEV)          # (B,N,W,C) 标准化后
            m = torch.from_numpy(b["mask"]).to(DEV)          # (B,N) 名内过滤
            B, N, Wn, C = X.shape
            x = X.reshape(B * N, Wn, C)
            h = core.in_norm(core.input_proj(x))
            H = core.backbone(h)                             # (B*N, W, d) 因果逐时刻
            maxh = max(HORIZONS)
            pos = np.arange(Wn - maxh - NPOS, Wn - maxh)     # 窗尾前 NPOS 个位置
            Hp = H[:, pos, :]                                # (B*N, P, d)
            loss = 0.0
            for hz in HORIZONS:
                pred = heads[str(hz)](Hp)                    # (B*N, P, C)
                tgt = x[:, pos + hz, :]
                l = hub(pred, tgt).mean(dim=(1, 2))          # (B*N,)
                l = (l.reshape(B, N) * m).sum() / m.sum().clamp(min=1)
                loss = loss + HW[hz] * l
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(list(enc.parameters()) + list(heads.parameters()), 1.0)
            opt.step()
            tot += float(loss); nb += 1
        # 验证(va 日, 无梯度)
        enc.eval(); heads.eval(); vtot, vnb = 0.0, 0
        with torch.no_grad():
            for b in data.iter_batches(va, batch_hours=48, rng=rng, shuffle=False, train=True):
                X = torch.from_numpy(b["Xseq"]).to(DEV); m = torch.from_numpy(b["mask"]).to(DEV)
                B, N, Wn, C = X.shape
                x = X.reshape(B * N, Wn, C)
                H = core.backbone(core.in_norm(core.input_proj(x)))
                maxh = max(HORIZONS)
                pos = np.arange(Wn - maxh - NPOS, Wn - maxh)
                Hp = H[:, pos, :]
                vloss = 0.0
                for hz in HORIZONS:
                    pred = heads[str(hz)](Hp); tgt = x[:, pos + hz, :]
                    l = hub(pred, tgt).mean(dim=(1, 2))
                    vloss = vloss + HW[hz] * float((l.reshape(B, N) * m).sum() / m.sum().clamp(min=1))
                vtot += vloss; vnb += 1
        vavg = vtot / max(vnb, 1)
        print(f"[fold {fi}] ep{ep} train {tot/max(nb,1):.4f} va {vavg:.4f} "
              f"({time.time()-t00:.0f}s)", flush=True)
        if vavg < best_va - 1e-4:
            best_va, bad = vavg, 0
            best_state = {k: v.detach().cpu().clone() for k, v in enc.state_dict().items()}
        else:
            bad += 1
            if bad >= 2:
                print(f"[fold {fi}] early stop ep{ep}", flush=True)
                break
    torch.save(best_state if best_state is not None else enc.state_dict(),
               os.path.join(OUT, f"fold_{fi}_encoder.pt"))
    print(f"[fold {fi}] saved (best va {best_va:.4f})", flush=True)
print("SSL_PRETRAIN_DONE", flush=True)
