import sys, time; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import spearmanr, rankdata
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
ts_ms = P['ts'].astype(np.int64); Y4 = P['Y4'].astype(np.float32); MEM = P['MEMBER110']
K = zload('/workspace/harness_y4_pred_panel.npz', allow_pickle=True)
KP = K[list(K.keys())[0]].astype(np.float32) if len(K.files) == 1 else K['king_pred'].astype(np.float32)
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
SOLO = {}
for yv in (2023, 2024, 2025, 2026):
    SOLO[yv] = np.load(f'/workspace/exports_train/arm5_xfd_s42_pred_{yv}.npy')
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return spearmanr(a[ok], b[ok]).correlation if ok.sum() >= 10 else np.nan
rhos, kic, sic, bic = [], [], [], []
for w in (0.3, 0.4, 0.5):
    bics = []
    for yv in (2023, 2024, 2025, 2026):
        te = np.where(yrs == yv)[0]
        for i in te:
            r = anchors[i]
            s_ = SOLO[yv][i]; k_ = KP[r]
            ok = np.isfinite(s_) & np.isfinite(k_) & np.isfinite(Y4[r]) & MEM[r]
            if ok.sum() < 30: continue
            sr = rankdata(s_[ok]); kr = rankdata(k_[ok])
            sr = (sr-sr.mean())/ (sr.std()+1e-9); kr = (kr-kr.mean())/(kr.std()+1e-9)
            b_ = (1-w)*kr + w*sr
            if w == 0.3:
                rhos.append(np.corrcoef(sr, kr)[0, 1])
                kic.append(sp(k_[ok], Y4[r][ok])); sic.append(sp(s_[ok], Y4[r][ok]))
            bics.append(spearmanr(b_, Y4[r][ok]).correlation)
    print(f'w={w}: blend IC {np.nanmean(bics):+.4f}', flush=True)
print(f'rho(solo,king) 逐锚均值 {np.nanmean(rhos):+.4f}', flush=True)
print(f'king IC {np.nanmean(kic):+.4f}  solo IC {np.nanmean(sic):+.4f}', flush=True)
