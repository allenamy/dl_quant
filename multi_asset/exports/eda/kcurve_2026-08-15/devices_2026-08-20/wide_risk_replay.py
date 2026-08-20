"""宽书(影子)风控四臂回放 —— 缺口A。组装逐字复刻 shadow_loop.py §7-8。
自校验门: 必须复现影子实测 gross_pos≈1.378 / turnover≈0.0075 / sel≈216, 否则不看风控数字。
臂: S0 无止损 / S1 在役等价(-25%×2锚→平+42锚冷却) / S2 激进(1锚) / S1L 仅低流动名止损
口径: gross-cost(bps/锚) + carry(iv=8h 近似, 声明); 深度=成本均价 unrealized/|notional|
"""
import numpy as np, json
from scipy.stats import rankdata
K = '/mnt/storage/private/work_hsy/w3lane/kcurve'
P = np.load(f'{K}/data/wide_panel_4h_v1.npz', allow_pickle=True)
print('PANEL KEYS:', list(P.keys()))
M = np.load(f'{K}/exports_train/kcurve_meta_K400_s2027.npz', allow_pickle=True)
E_ts, yrs, qvk = M['E_ts'], M['yrs'], M['qvk']
pred = np.full(qvk.shape, np.nan, np.float32)
for y in (2023, 2024, 2025, 2026):
    a = np.load(f'{K}/exports_train/kcurve_pred_K400_s2027_{y}.npy')
    m = (yrs == y)
    pred[m] = a[m] if a.shape == pred.shape else a[:m.sum()]
    print('pred', y, 'rows', int(m.sum()), 'finite', int(np.isfinite(pred[m]).sum()))
# 对齐: 面板 9913 vs meta 10086 —— 用尾部对齐(两者同为4h网格)
n_p = P['Y4'].shape[0]; n_m = qvk.shape[0]
off = n_m - n_p
print('对齐偏移(meta−panel):', off)
Y4 = P['Y4']; elig = P['elig']; rev24 = P['f_rev_24h']; fe = P['f_fund_ema']; fn = P['f_fund_now']
qv = qvk[off:] if off > 0 else qvk
pr = pred[off:] if off > 0 else pred
YR = yrs[off:] if off > 0 else yrs
n, N = Y4.shape
QMIN, CAP, ALPHA, BAND, LOOK, SELMIN = 250000.0, 2.5, 0.1, 0.00025, 900, 80
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
DEPTH, COOL = -0.25, 42
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum()-1, 1) - 0.5
    return out
def run(mode, diag=False):
    H = np.zeros(N); LR = {'king': [], 'rev24': [], 'fund': []}
    Pi = np.ones(N); sh = np.zeros(N); cost_b = np.zeros(N)
    cnt = np.zeros(N, int); su = np.full(N, -1); fires = []
    g_bps = np.zeros(n); c_bps = np.zeros(n); car = np.zeros(n); trn = np.zeros(n); sels = []; gps = []
    liq_lo = np.zeros(N, bool)
    for i in range(n):
        m = np.where(elig[i])[0]
        if len(m) < SELMIN: continue
        qv4h = np.expm1(np.clip(qv[i, m], 0, 30)) * 48
        sel = qv4h >= QMIN
        if sel.sum() < SELMIN: continue
        if len(LR['king']) >= LOOK:
            r = np.stack([np.array(LR[l][-LOOK:]) for l in ('king', 'rev24', 'fund')])
            s = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
            w3 = s / s.sum() if s.sum() > 0 else np.array([1/3]*3)
        else: w3 = np.array([1/3]*3)
        lz = {'king': xz(pr[i, m]), 'rev24': xz(-rev24[i, m]), 'fund': xz(fe[i, m])}
        z = w3[0]*np.nan_to_num(lz['king']) + w3[1]*np.nan_to_num(lz['rev24']) + w3[2]*np.nan_to_num(lz['fund'])
        w = np.where(sel, z, 0.0); w = w - w[sel].mean()
        gg = np.abs(w).sum()
        if gg < 1e-9: continue
        w /= gg
        cw = CAP / max(int(sel.sum()), 1); w = np.clip(w, -cw, cw)
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        tgt = np.zeros(N); tgt[m] = w
        if mode != 'S0':
            blk = su > i
            if mode == 'S1L': blk = blk & liq_lo
            tgt[blk] = 0.0
        sm = H + ALPHA * (tgt - H)
        tr = sm - H
        sm = np.where(np.abs(tr) < BAND, H, sm); tr = sm - H
        # 成本
        tiers = np.full(len(m), 2, np.int8); tiers[qv4h >= 1e6] = 1; tiers[qv4h >= 5e6] = 0
        ta = np.abs(tr[m])
        cst = float(sum(ta[tiers == t].sum() * (fr*mk + (1-fr)*tk) for t, (mk, tk, fr) in enumerate(COST_B)))
        yv = np.nan_to_num(Y4[i], nan=0.0)
        gr = float((sm * yv).sum() * 1e4)
        cr = float((sm[m] * np.nan_to_num(fn[i, m], nan=0.0) * 0.5).sum() * 1e4)
        g_bps[i] = gr; c_bps[i] = cst; car[i] = cr; trn[i] = float(np.abs(tr).sum())
        sels.append(int(sel.sum())); gps.append(float(np.abs(sm).sum()))
        # 腿收益(供 msharpe)
        gz = np.abs(z).sum()
        for l in ('king', 'rev24', 'fund'):
            zz = np.nan_to_num(lz[l]); gl = np.abs(zz).sum()
            LR[l].append(float((zz/gl * yv[m]).sum()*1e4) if gl > 1e-9 else 0.0)
        # 深度记账
        nsh = np.where(Pi > 1e-12, sm/Pi, 0.0)
        same = np.sign(nsh) == np.sign(sh)
        add = same & (np.abs(nsh) > np.abs(sh)); red = same & (~add) & (np.abs(nsh) > 1e-12)
        new = (~same) | (np.abs(sh) < 1e-12)
        cost_b = np.where(add, cost_b + (nsh-sh)*Pi, cost_b)
        with np.errstate(all='ignore'):
            ratio = np.where(np.abs(sh) > 1e-12, nsh/np.where(np.abs(sh) > 1e-12, sh, 1.0), 0.0)
        cost_b = np.where(red, cost_b*ratio, cost_b)
        cost_b = np.where(new, nsh*Pi, cost_b); cost_b = np.where(np.abs(nsh) < 1e-12, 0.0, cost_b)
        sh = nsh
        with np.errstate(all='ignore'):
            avg = np.where(np.abs(sh) > 1e-12, cost_b/sh, np.nan)
            dep = np.where(np.isfinite(avg) & (Pi > 0), np.sign(sh)*(1.0-avg/Pi), 0.0)
        liq_lo[:] = False; liq_lo[m[qv4h < 1e6]] = True
        if mode != 'S0':
            need = 2 if mode in ('S1', 'S1L') else 1
            cand = (np.abs(sh) > 1e-12) & (dep <= DEPTH) & (su <= i)
            if mode == 'S1L': cand = cand & liq_lo
            cnt = np.where(cand, cnt+1, 0)
            fr2 = cnt >= need
            if fr2.any():
                su[fr2] = i + COOL; cnt[fr2] = 0; fires.append((int(YR[i]), int(fr2.sum())))
        H = sm; Pi = Pi * (1.0 + yv)
    ok = g_bps != 0
    net = (g_bps - c_bps + car)[ok]; yy = YR[ok]
    fy = {}
    for y_, k in fires: fy[y_] = fy.get(y_, 0) + k
    out = {'n_anchor': int(ok.sum()), 'net_all': round(float(net.mean()), 3),
           'sharpe': round(float(net.mean()/net.std(ddof=1)*np.sqrt(6*365)), 2),
           'by_year': {int(y_): round(float(net[yy == y_].mean()), 3) for y_ in sorted(set(yy.tolist()))},
           'p5': round(float(np.percentile(net, 5)), 1), 'turnover': round(float(trn[ok].mean()), 5),
           'fires': int(sum(v for _, v in fires)), 'fires_year': fy}
    if diag: out['selftest'] = {'sel_mean': round(float(np.mean(sels[-500:])), 0), 'gross_pos': round(float(np.mean(gps[-500:])), 4)}
    return out
res = {}
r0 = run('S0', diag=True); res['S0'] = r0
print('S0', json.dumps(r0, ensure_ascii=False))
st = r0['selftest']
print(f"自校验: sel {st['sel_mean']}(影子实测≈216) gross_pos {st['gross_pos']}(≈1.378) turnover {r0['turnover']}(≈0.0075)")
for mode in ('S1', 'S2', 'S1L'):
    res[mode] = run(mode); print(mode, json.dumps(res[mode], ensure_ascii=False))
json.dump(res, open('/mnt/storage/private/work_hsy/probe_artifacts/wide_risk_replay.json', 'w'))
