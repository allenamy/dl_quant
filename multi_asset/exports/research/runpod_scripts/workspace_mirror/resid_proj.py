'''决定性测量: film2 预测在 raw vs 残差(YR4) 两口径下的 IC — 5m alpha 有多少被 zoo 吸收'''
import sys, time, glob; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import spearmanr
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
ts_ms = P['ts'].astype(np.int64); Y4 = P['Y4'].astype(np.float32); YR4 = P['YR4'].astype(np.float32)
MEM = P['MEMBER110']; CL4 = P['CL4']
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
def icser(files, Ytgt, useCL=False):
    ics = []
    for f in files:
        PR = np.load(f)
        for i in range(len(anchors)):
            r_ = anchors[i]
            base = MEM[r_] & np.isfinite(PR[i]) & np.isfinite(Ytgt[r_])
            if useCL: base = base & CL4[r_]
            if base.sum() >= 10:
                ics.append(spearmanr(PR[i][base], Ytgt[r_][base]).correlation)
    return float(np.nanmean(ics)), len(ics)
fs = sorted(glob.glob('/workspace/exports_train/fast_film2_s42_pred_*.npy'))
raw_ic, n1 = icser(fs, Y4)
res_ic, n2 = icser(fs, YR4)
res_cl, n3 = icser(fs, YR4, useCL=True)
print(f'film2(s42) raw口径 IC: {raw_ic:+.4f} (n={n1})')
print(f'film2(s42) 残差口径 IC: {res_ic:+.4f} (n={n2})')
print(f'film2(s42) 残差+CL干净行: {res_cl:+.4f} (n={n3})')
print(f'⇒ 残差保留率 {100*res_ic/max(raw_ic,1e-9):.0f}%')
