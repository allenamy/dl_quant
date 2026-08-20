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
years = np.array([datetime.date.fromordinal(d0 + i).year for i in range(D)])
evs = []
for s in closes:
    if s == 'BTCUSDT': continue
    lp = np.log(px(s))
    r = np.diff(lp) - np.diff(lbtc)
    for t0_ in range(0, D - 10, 5):
        lpc = 0.0; hit = -1
        for k in range(t0_, min(t0_ + 60, D - 9)):
            if k >= len(r) or not np.isfinite(r[k]): break
            lpc += r[k]
            if np.expm1(-lpc) <= -0.25: hit = k; break
        if hit < 0: continue
        w = r[hit+1:hit+8]
        if len(w) < 7 or not np.isfinite(w).all(): continue
        evs.append((int(years[hit]), -float(np.expm1(w.sum()))))
out = {}
for y in sorted(set(e[0] for e in evs)):
    a = np.array([e[1] for e in evs if e[0] == y])
    if len(a) >= 30: out[y] = {'n': int(len(a)), 'hold7_bps': round(float(a.mean())*1e4, 0), 'med7_bps': round(float(np.median(a))*1e4, 0)}
print(json.dumps(out))
