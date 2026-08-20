"""自适应 regime 跟踪判官: 符号若是"年块"结构, 拖尾估计能否跟上?
政策: 每个事件用【过去12个月、含30天禁运】已实现的 hold−cut 差决定本次该扛还是该砍。
对照: always-hold / always-cut / 自适应 / 完美后见(上界)。事件=空头深度首穿 -25%, 结局=后续7d。
"""
import numpy as np, json, datetime
closes = {k: {int(a): b for a, b in v.items()} for k, v in json.load(open('daily_closes_2020.json')).items()}
d0 = datetime.date(2020, 1, 5).toordinal(); d1 = datetime.date(2026, 8, 19).toordinal()
D = d1 - d0 + 1
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
COST = 0.0002   # 砍仓退出成本(maker, 保守)
years = np.array([datetime.date.fromordinal(d0 + int(t)).year for t in E])
adapt = np.zeros(len(E)); decis = np.zeros(len(E))
for i, t in enumerate(E):
    m = (E >= t - 395) & (E <= t - 30)      # 12个月拖尾, 30天禁运
    if m.sum() < 200:
        adapt[i] = H[i]; decis[i] = 1        # 冷启动=维持现状(扛)
    else:
        cut_better = H[m].mean() < -COST
        decis[i] = 0.0 if cut_better else 1.0
        adapt[i] = -COST if cut_better else H[i]
out = {'n_events': int(len(E))}
for y in sorted(set(years)):
    m = years == y
    out[int(y)] = {'n': int(m.sum()),
                   'hold': round(float(H[m].mean())*1e4, 0),
                   'cut': round(-COST*1e4, 0),
                   'adaptive': round(float(adapt[m].mean())*1e4, 0),
                   'pct_decision_cut': round(float(1 - decis[m].mean()), 2)}
tot = {'hold_all': round(float(H.mean())*1e4, 0), 'cut_all': round(-COST*1e4, 0),
       'adaptive_all': round(float(adapt.mean())*1e4, 0),
       'oracle_all': round(float(np.maximum(H, -COST).mean())*1e4, 0)}
# 仅 2021 起(冷启动后)
m2 = E >= (datetime.date(2021, 3, 1).toordinal() - d0)
tot['since2021'] = {'hold': round(float(H[m2].mean())*1e4, 0), 'adaptive': round(float(adapt[m2].mean())*1e4, 0), 'cut': round(-COST*1e4, 0)}
out['TOTAL'] = tot
print(json.dumps(out, ensure_ascii=False))
