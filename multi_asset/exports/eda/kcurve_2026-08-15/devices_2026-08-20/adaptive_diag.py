"""自适应结论的仪器诊断: ①窗长敏感性(6/12/18/24m) ②切换次数与鞭打 ③决策序列 ④净额敏感于成本?"""
import numpy as np, json, datetime
closes = {k: {int(a): b for a, b in v.items()} for k, v in json.load(open('daily_closes_2020.json')).items()}
d0 = datetime.date(2020, 1, 5).toordinal(); d1 = datetime.date(2026, 8, 19).toordinal(); D = d1 - d0 + 1
def px(s):
    p = np.full(D, np.nan)
    for dd, c in closes.get(s, {}).items():
        if d0 <= dd <= d1: p[dd - d0] = c
    return p
lbtc = np.log(px('BTCUSDT'))
evs = []
for s in closes:
    if s == 'BTCUSDT': continue
    lp = np.log(px(s)); r = np.diff(lp) - np.diff(lbtc)
    for t0_ in range(0, D - 10, 5):
        lpc = 0.0; hit = -1
        for k in range(t0_, min(t0_ + 60, D - 9)):
            if k >= len(r) or not np.isfinite(r[k]): break
            lpc += r[k]
            if np.expm1(-lpc) <= -0.25: hit = k; break
        if hit < 0: continue
        w = r[hit+1:hit+8]
        if len(w) < 7 or not np.isfinite(w).all(): continue
        evs.append((hit, -float(np.expm1(w.sum()))))
evs.sort()
E = np.array([e[0] for e in evs]); H = np.array([e[1] for e in evs])
COST = 0.0002
res = {}
for WIN in (180, 395, 550, 730):
    ad = np.zeros(len(E)); dec = np.zeros(len(E))
    for i, t in enumerate(E):
        m = (E >= t - WIN) & (E <= t - 30)
        if m.sum() < 200: ad[i] = H[i]; dec[i] = 1
        else:
            cut = H[m].mean() < -COST
            dec[i] = 0.0 if cut else 1.0
            ad[i] = -COST if cut else H[i]
    m2 = E >= (datetime.date(2021, 3, 1).toordinal() - d0)
    # 月度决策序列 + 切换次数
    mon = {}
    for i, t in enumerate(E):
        dt = datetime.date.fromordinal(d0 + int(t))
        mon.setdefault(f'{dt.year}-{dt.month:02d}', []).append(dec[i])
    seq = [(k, round(float(np.mean(v)), 2)) for k, v in sorted(mon.items())]
    binseq = [1 if v >= 0.5 else 0 for _, v in seq]
    switches = sum(1 for a, b in zip(binseq, binseq[1:]) if a != b)
    res[f'win{WIN}d'] = {'adaptive_all': round(float(ad.mean())*1e4, 0),
                         'adaptive_since2021': round(float(ad[m2].mean())*1e4, 0),
                         'switches': switches,
                         'pct_cut_overall': round(float(1 - dec.mean()), 2)}
    if WIN == 395:
        res['decision_monthly_win395'] = [f'{k}:{"H" if v>=0.5 else "C"}' for k, v in seq]
res['static'] = {'hold_all': round(float(H.mean())*1e4, 0), 'cut_all': round(-COST*1e4, 0),
                 'hold_since2021': round(float(H[E >= (datetime.date(2021,3,1).toordinal()-d0)].mean())*1e4, 0)}
print(json.dumps(res, ensure_ascii=False))
