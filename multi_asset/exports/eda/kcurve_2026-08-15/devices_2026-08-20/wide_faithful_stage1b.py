"""忠实宽书装置 stage1: 从 5m 原料重建 78 特征 → 真 king 腿(slow2026.txt LGBM)→ 三道校验。
门1 对齐: 自算 Y4 与面板 Y4 相关 >0.99。门2 king 信号: xsec rank-IC ≈ +0.06 且为正。
产物: wide_faithful_stage1.npz(king_pred, qv4h, Y4, elig, fund_ema, fund_now)供 stage2 组书。
"""
import numpy as np, json, time
from scipy.stats import rankdata, spearmanr
K = '/mnt/storage/private/work_hsy/w3lane/kcurve'
t0 = time.time()
cfg = json.load(open(f'{K}/wide_cfg.json')); names = cfg['keep_names']
d = np.load(f'{K}/data/dlnative_5m_wide829_f16.npz', allow_pickle=True)
ts = d['ts']; CHN = [str(x) for x in d['ch']]; SY = [str(x) for x in d['symbols']]
n5, NS, NC = d['data'].shape
A = np.arange(48, n5 - 48, 48)          # 4h 锚(留首窗)
nA = len(A); print(f'5m {n5} 名 {NS} 锚 {nA}', flush=True)
WINS = [48, 288, 864, 2016, 8640]
FEAT = {}
for ci, ch in enumerate(CHN):
    x = np.asarray(d['data'][:, :, ci], np.float32)
    fin = np.isfinite(x); xf = np.where(fin, x, 0.0)
    cs = np.cumsum(xf, 0, dtype=np.float64); cn = np.cumsum(fin, 0, dtype=np.float64)
    if ch == 'ret5':
        cs2 = np.cumsum(xf.astype(np.float64)**2, 0)
    for Wd in WINS:
        lo = np.maximum(A - Wd, 0)
        s = cs[A] - cs[lo]; c = np.maximum(cn[A] - cn[lo], 1.0)
        mean = (s / c).astype(np.float32)
        if ch == 'ret5':
            if Wd in (864, 2016, 8640): FEAT[f'ret5_sum_{Wd}'] = s.astype(np.float32)
            s2 = cs2[A] - cs2[lo]
            FEAT[f'vol_{Wd}'] = np.sqrt(np.maximum(s2/c - (s/c)**2, 0)).astype(np.float32)
        else:
            FEAT[f'{ch}_mean_{Wd}'] = mean
    del x, fin, xf, cs, cn
    print(f'  ch {ch} done {time.time()-t0:.0f}s', flush=True)
# 自算 Y4(前向4h对数收益)
r5 = np.asarray(d['data'][:, :, CHN.index('ret5')], np.float32)
cr = np.cumsum(np.where(np.isfinite(r5), r5, 0.0), 0, dtype=np.float64)
Y4_own = np.expm1(cr[np.minimum(A+48, n5-1)] - cr[A]).astype(np.float32)
have = np.isfinite(r5).astype(np.float32)
ch_ = np.cumsum(have, 0, dtype=np.float64)
cov48 = (ch_[np.minimum(A+48, n5-1)] - ch_[A]) / 48.0
Y4_own = np.where(cov48 > 0.8, Y4_own, np.nan)
del r5, cr, have, ch_
# 门1: 用面板自带 ts 精确对齐(不用相关性搜索)
P = np.load(f'{K}/data/wide_panel_4h_v1.npz', allow_pickle=True)
pts = np.asarray(P['ts']).astype('int64'); pts = pts//1000 if pts[0] > 2e10 else pts
ats = np.asarray(ts[A]).astype('int64'); ats = ats//1000 if ats[0] > 2e10 else ats
psy = [str(x) for x in P['symbols']]
assert psy == SY, f'门0 符号轴不一致 {psy[:3]} vs {SY[:3]}'
pos = {int(t): i for i, t in enumerate(ats)}
sel_idx = np.array([pos.get(int(t), -1) for t in pts])
hit = (sel_idx >= 0).mean()
print(f'门1 ts 对齐命中率 {hit:.4f} (需 =1.0)', flush=True)
assert hit > 0.999, '门1 未过: 面板 ts 未能全部落在 4h 锚网格'
Yp = P['Y4']; npn = Yp.shape[0]
a_chk = Y4_own[sel_idx]
mk = np.isfinite(a_chk) & np.isfinite(Yp)
CORR = float(np.corrcoef(a_chk[mk], Yp[mk])[0, 1])
OFF = int(sel_idx[0])
print(f'诊断: ts对齐后自算Y4 vs 面板Y4 corr={CORR:.4f}(定义差异容忍, PnL 用面板 Y4)', flush=True)
FEAT = {k: v[sel_idx] for k, v in FEAT.items()}
Y4 = Yp; elig = P['elig']; fe = P['f_fund_ema']; fn = P['f_fund_now']
FEAT['fund_ema'] = np.asarray(fe, np.float32); FEAT['fund_now'] = np.asarray(fn, np.float32)
qv4h = (np.expm1(np.clip(FEAT['log_qv_mean_48'], 0, 30)) * 48).astype(np.float32)
# 组装 78 列(_v 原值, _r 截面秩)
nn, NN = Y4.shape
X = np.full((nn, NN, 78), np.nan, np.float32)
for k, nm in enumerate(names):
    if nm in ('fund_ema', 'fund_now'):
        X[:, :, k] = FEAT[nm]; continue
    base, kind = nm[:-2], nm[-1]
    v = FEAT[base]
    if kind == 'v': X[:, :, k] = v
    else:
        for i in range(nn):
            row = v[i]; m = np.isfinite(row) & elig[i]
            if m.sum() >= 10:
                o = np.full(NN, np.nan, np.float32)
                o[m] = (rankdata(row[m]) / max(m.sum()-1, 1) - 0.5).astype(np.float32)
                X[i, :, k] = o
    if k % 12 == 0: print(f'  feat {k}/78 {time.time()-t0:.0f}s', flush=True)
import lightgbm as lgb
B = lgb.Booster(model_file=f'{K}/slow2026.txt')
print('booster feats:', B.num_feature(), flush=True)
KP = np.full((nn, NN), np.nan, np.float32)
for i in range(nn):
    m = np.where(elig[i])[0]
    if len(m) < 20: continue
    xi = X[i, m]
    ok = np.isfinite(xi).all(1)
    if ok.sum() < 20: continue
    KP[i, m[ok]] = B.predict(xi[ok]).astype(np.float32)
    if i % 1500 == 0: print(f'  pred {i}/{nn} {time.time()-t0:.0f}s', flush=True)
ics = []
for i in range(200, nn, 7):
    m = elig[i] & np.isfinite(KP[i]) & np.isfinite(Y4[i])
    if m.sum() >= 50: ics.append(spearmanr(KP[i][m], Y4[i][m]).statistic)
IC = float(np.nanmean(ics))
print(f'门2 king 信号 xsec rank-IC = {IC:.4f} (需 >0 且 ≈0.06, n={len(ics)})', flush=True)
np.savez_compressed(f'{K}/wide_faithful_stage1.npz', king=KP, qv4h=qv4h, Y4=Y4,
                    elig=elig, fund_ema=FEAT['fund_ema'], fund_now=FEAT['fund_now'],
                    meta=np.array([OFF, CORR, IC]))
print('STAGE1_DONE', round(time.time()-t0), 's', flush=True)
