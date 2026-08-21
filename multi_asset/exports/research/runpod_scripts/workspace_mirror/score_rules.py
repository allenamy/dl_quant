'''打分规则对照: 同一 qh 模型的 25 维输出, 四种打分各算 IC(免训练)'''
import sys, pickle; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import spearmanr
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
Y4 = P['Y4'].astype(np.float32)
QD = pickle.load(open('/workspace/exports_train/fast_base_qdump.pkl', 'rb'))
ts_ms = P['ts'].astype(np.int64); MEM = P['MEMBER110']
import time
rows4 = np.arange(0, Y4.shape[0], 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return spearmanr(a[ok], b[ok]).correlation if ok.sum() >= 10 else np.nan
rules = {'mean25': lambda q: q.mean(-1), 'q50': lambda q: q[:, 12],
         'trim  ': lambda q: q[:, 2:23].mean(-1), 'tails ': lambda q: 0.5*(q[:, :5].mean(-1)+q[:, 20:].mean(-1)),
         'skewtilt': lambda q: q.mean(-1) + 0.5*((q[:, 20:].mean(-1)-q[:, 12]) - (q[:, 12]-q[:, :5].mean(-1)))}
out = {k: [] for k in rules}
for i, m, oq in QD:
    r = anchors[i]; y = Y4[r, m]
    for k, f in rules.items(): out[k].append(sp(f(oq), y))
for k in rules: print(f'{k}: IC {np.nanmean(out[k]):+.4f} (n={len(out[k])})')
