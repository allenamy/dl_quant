'''femb 前置: 51 特征数组 [n_anchors, 140, 51] 预计算(与树v2同定义)'''
import sys, time; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import rankdata
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
ts_ms = P['ts'].astype(np.int64); Y4 = P['Y4'].astype(np.float32); MEM = P['MEMBER110']
SY = [str(s) for s in P['symbols']]
Z = zload('/workspace/data/dlnative_5m_k7_f16.npz', allow_pickle=True)
CTS = Z['ts'].astype(np.int64); CD = Z['data'][:, :, :7].astype(np.float32)
t0c = int(CTS[0]); csyms = list(Z['symbols']); col_of = np.array([csyms.index(s) for s in SY])
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
W = 576
OUT = np.full((len(anchors), N, 51), np.nan, np.float32)
for i in range(len(anchors)):
    e = int(row_end[i]); s0 = e - W
    if s0 < 0 or e > CD.shape[0]: continue
    b = CD[s0:e][:, col_of, :]
    r = np.nan_to_num(b[:, :, 0]); q = np.nan_to_num(b[:, :, 3]); tb = np.nan_to_num(b[:, :, 6])
    rg = np.nan_to_num(b[:, :, 1]); cp = np.nan_to_num(b[:, :, 2]); sf = (2*tb-1)*q
    F = []
    for L in (12, 48, 144, 288, 576):
        F.append(r[-L:].sum(0)); F.append(r[-L:].std(0))
    for L in (48, 288):
        F.append(q[-L:].mean(0)); F.append(tb[-L:].mean(0)); F.append(sf[-L:].mean(0))
    F.append(rg[-288:].mean(0)); F.append(cp[-48:].mean(0))
    c = np.cumsum(r[-288:], 0); F.append(c.max(0)); F.append(c.min(0))
    F.append(r[-288:].std(0)/(r[-576:].std(0)+1e-9)); F.append(np.abs(r[-48:]).max(0))
    X = np.stack(F, -1)
    XR = np.stack([rankdata(np.nan_to_num(X[:, j]))/max(len(X)-1, 1) - 0.5 for j in range(X.shape[1])], -1)
    vol7 = r.std(0); vp = rankdata(vol7)/max(len(vol7)-1, 1) - 0.5
    inter = np.stack([XR[:, 3]*vp, XR[:, 0]*vp, XR[:, 12]*vp], -1)
    OUT[i] = np.concatenate([X, XR, inter, np.zeros((X.shape[0], 4), np.float32)], -1)
    if i % 2000 == 0: print(i, flush=True)
np.savez_compressed('/workspace/data/.tmp_feat51.npz', feat=OUT.astype(np.float16))
import os
os.replace('/workspace/data/.tmp_feat51.npz', '/workspace/data/feat51.npz')
print('FEAT51_DONE', OUT.shape, flush=True)
