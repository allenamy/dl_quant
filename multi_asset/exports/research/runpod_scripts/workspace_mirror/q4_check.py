'''军规: 判据必须带最坏五分位 — film2 双种子的 Q4 与 BTC波动分档 IC'''
import sys, time; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import spearmanr
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
ts_ms = P['ts'].astype(np.int64); Y4 = P['Y4'].astype(np.float32); MEM = P['MEMBER110']
Z = zload('/workspace/data/dlnative_5m_k7_f16.npz', allow_pickle=True)
CTS = Z['ts'].astype(np.int64); CD = Z['data']; csyms = list(Z['symbols'])
BTC = csyms.index('BTCUSDT'); t0c = int(CTS[0])
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
wall = ts_ms[np.array(anchors)]//1000 + 3600
row_end = (wall - t0c) // 300
btcvol = np.full(len(anchors), np.nan)
for i in range(len(anchors)):
    e = int(row_end[i]); s0 = e - 288
    if s0 >= 0 and e <= CD.shape[0]:
        btcvol[i] = np.nanstd(CD[s0:e, BTC, 0].astype(np.float32))
ics = {}
for sd in ('s42', 's2027'):
    pref = 'fast_film2_s42_pred' if sd == 's42' else 'fast2_film2_s2027_pred'
    import glob
    fs = sorted(glob.glob(f'/workspace/exports_train/*film2*{sd}*pred_*.npy'))
    if not fs: fs = sorted(glob.glob(f'/workspace/exports_train/fast_film2_{sd}_pred_*.npy'))
    print(sd, 'files', [f.split("/")[-1] for f in fs])
    ic = np.full(len(anchors), np.nan)
    for f in fs:
        PR = np.load(f)
        for i in range(len(anchors)):
            if np.isfinite(PR[i]).sum() >= 10:
                r_ = anchors[i]
                ok = np.isfinite(PR[i]) & np.isfinite(Y4[r_])
                if ok.sum() >= 10:
                    ic[i] = spearmanr(PR[i][ok], Y4[r_][ok]).correlation
    ics[sd] = ic
for sd, ic in ics.items():
    okm = np.isfinite(ic)
    seq = ic[okm]
    roll = np.convolve(seq, np.ones(20)/20, mode='valid')
    qs = np.quantile(roll, [0, .2, .4, .6, .8, 1])
    srt = np.sort(roll)
    q4 = srt[:max(1, len(srt)//5)].mean()
    print(f'[{sd}] n_anchor {okm.sum()} 全期IC {np.nanmean(ic):+.4f} | 滚动20锚 Q4(最坏五分位均值) {q4:+.4f} | 滚动分位 {np.round(qs, 4)}')
    bv = btcvol[okm]
    qb = np.nanquantile(bv, [.2, .4, .6, .8])
    lab = np.digitize(bv, qb)
    for g in range(5):
        print(f'   BTC波动档{g+1}: IC {np.nanmean(seq[lab==g]):+.4f} (n={int((lab==g).sum())})')
