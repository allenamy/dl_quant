#!/usr/bin/env python3
"""ARM-N1a Phase-1: future-comovement soft-contrastive pretraining of the king encoder (per fold).

Target = future realized co-movement (high-SNR). For anchor t, future window = 64 4h-bars (256h);
C_fut[i,j] = Pearson corr of the two assets' 64 future 4h-returns. Encoder embeddings z_i (L2-norm)
-> S[i,j]=z_i.z_j; loss = masked MSE(S, C_fut) over member pairs. LEAKAGE: per-fold, future window
fully inside the train window (t+256 <= train_end -> boundary drop). Saves pretrained encoder + loss
curve; inference is <=t causal (future used only as a training-phase self-supervised target).
"""
import sys, json, argparse, numpy as np, torch, torch.nn as nn, pandas as pd
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import ConformerPanelEncoder
MA = REPO + "/multi_asset"
DEV = "cuda"; C = 32; D = 64; NBLK = 2; KER = 15; DROP = 0.2
HF_H = 256           # future window hours; 64 4h-bars
STRIDE_4H = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--te_year", type=int, default=2023)     # fold0
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch_hours", type=int, default=24)
    ap.add_argument("--anchor_stride", type=int, default=4)  # pretrain anchors every 4h
    ap.add_argument("--out", default=MA + "/exports/train/n1a_pretrain_fold0")
    a = ap.parse_args()
    import os; os.makedirs(a.out, exist_ok=True)

    NPZ = MA + "/exports/wide_dl_full_12h.npz"
    data = WidePanelData(path=NPZ, target_horizon=12)
    T, N, W = data.T, data.N, data.W
    ts = data.ts.astype(np.int64)
    yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    # future 4h-return series per asset from wide_panel_full CLOSE
    z = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    logc = np.log(np.where(z["CLOSE"].astype(np.float64) > 0, z["CLOSE"].astype(np.float64), np.nan)).astype(np.float32)
    logc_t = torch.from_numpy(logc).to(DEV)                  # (T,N)
    member = data.member

    # fold0 train window (year_folds expanding): all days < te_year, minus embargo(10)+val(30) tail
    day_year = np.array([int(yr[data.day == d][0]) for d in data.uniq_days])
    tr_days = data.uniq_days[day_year < a.te_year]
    tr_days = tr_days[:-(10 + 30)] if len(tr_days) > 40 else tr_days
    data.set_fold(tr_days)
    trm = np.isin(data.day, tr_days)
    train_hours = np.where(trm)[0]
    train_end = int(train_hours.max())
    # pretrain anchors: in train window, full lookback + future window inside train, enough members
    ok = (np.arange(T) >= (W - 1)) & (np.arange(T) + HF_H <= train_end) & trm
    ok &= (member.sum(1) >= 20)
    anchors = np.where(ok)[0][::a.anchor_stride]
    print("[n1a-pre] te=%d train_days=%d train_hours=[%d,%d] anchors=%d (stride %dh, future %dh dropped-tail)" % (
        a.te_year, len(tr_days), train_hours.min(), train_end, len(anchors), a.anchor_stride, HF_H), flush=True)

    enc = ConformerPanelEncoder(C, d=D, n_blocks=NBLK, kernel_size=KER, dropout=DROP).to(DEV)
    proj = nn.Sequential(nn.Linear(D, D), nn.GELU(), nn.Linear(D, D)).to(DEV)
    opt = torch.optim.AdamW(list(enc.parameters()) + list(proj.parameters()), lr=6e-4, weight_decay=0.01)
    mu = torch.from_numpy(data.mu).to(DEV); sd = torch.from_numpy(data.sd).to(DEV)
    offs = np.arange(-W + 1, 1)
    fut_idx = torch.arange(0, HF_H + 1, STRIDE_4H, device=DEV)   # 0..256 step4 -> 65 pts -> 64 rets

    def cfut(bh):
        # bh: (B,) anchor hours -> future 64 4h-ret corr (B,N,N), member-masked
        idx = torch.as_tensor(bh, device=DEV)[:, None] + fut_idx[None, :]   # (B,65)
        lc = logc_t[idx]                                          # (B,65,N)
        r = lc[:, 1:, :] - lc[:, :-1, :]                          # (B,64,N) future 4h logret
        r = torch.nan_to_num(r, nan=0.0)
        rc = r - r.mean(1, keepdim=True)
        rn = rc / rc.norm(dim=1, keepdim=True).clamp_min(1e-6)
        Cf = torch.einsum("bti,btj->bij", rn, rn)                # (B,N,N)
        return Cf

    curve = []
    rng = np.random.default_rng(42)
    for ep in range(a.epochs):
        enc.train(); proj.train()
        perm = anchors.copy(); rng.shuffle(perm)
        tot = 0.0; nb = 0
        for b0 in range(0, len(perm), a.batch_hours):
            bh = perm[b0:b0 + a.batch_hours]
            widx = bh[:, None] + offs[None, :]                   # (B,W)
            x = torch.from_numpy(np.nan_to_num(data.CH[widx].transpose(0, 2, 1, 3))).to(DEV)  # (B,N,W,C)
            x = ((x - mu) / sd).clamp(-10, 10)
            m = torch.from_numpy(member[bh]).to(DEV)             # (B,N) bool
            h = enc(x, m.float())                                # (B,N,d)
            zt = torch.nn.functional.normalize(proj(h), dim=-1)  # (B,N,d)
            S = torch.bmm(zt, zt.transpose(1, 2))                # (B,N,N)
            Cf = cfut(bh)
            pair = (m[:, :, None] & m[:, None, :]).float()
            eye = torch.eye(N, device=DEV)[None]
            pair = pair * (1 - eye)                              # drop diagonal
            loss = ((S - Cf) ** 2 * pair).sum() / pair.sum().clamp_min(1.0)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(list(enc.parameters()) + list(proj.parameters()), 1.0)
            opt.step()
            tot += float(loss.detach()); nb += 1
        curve.append(round(tot / max(nb, 1), 5))
        print("  ep %2d comovement-MSE = %.5f" % (ep, curve[-1]), flush=True)

    torch.save(enc.state_dict(), a.out + "/pretrained_encoder.pt")
    json.dump({"te_year": a.te_year, "anchors": int(len(anchors)), "HF_hours": HF_H,
               "loss_curve": curve, "final": curve[-1], "drop_ratio": round(curve[-1] / curve[0], 3)},
              open(a.out + "/pretrain_report.json", "w"), indent=1)
    print("[n1a-pre] saved encoder + curve. first=%.5f last=%.5f drop=%.2fx" % (
        curve[0], curve[-1], curve[0] / max(curve[-1], 1e-9)), flush=True)


if __name__ == "__main__":
    main()
