"""书级决定性实验: 自适应止损 vs 在役止损 vs 无止损, 在 9,821 锚真书回放上。
四臂: S0 无止损 / S1 在役(-25%×2锚→平+42锚冷却) / S2 激进(-25%×1锚) / S3 自适应(C期用S2, H期用S0)
regime 信号: 因果拖尾12月(禁运30d)"深水空头后续7d"均值符号, 脚本内重算, 非硬编码。
口径: 输出 book bps/锚(gross≈1)。判据(冻结, 先于看数): S3 需 ①逐年不劣于 S1 ≥4/5年 ②全期净额 > S1 ③尾部(年最差5%锚)不劣。
"""
import sys, json, datetime
import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live"); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import legs as LG
import engine.replay_fullhist as RF

W = {"king": .5952380952380952, "s2": .20238095238095238, "funding": .20238095238095238, "size": 0.}
RB = {"alpha": .5, "lambda": 1.}; C1 = 4.137; BW = 0.002; ANN = np.sqrt(6*365)
DEPTH = -0.25; COOL = 42
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
FI, RVI = src.fund_idx, src.ch.index("rvol_24h")
SYMS = [str(s) for s in src.symbols]
# 锚→近似日期(年内序号/6)
dates = []
cnt = {}
for i in range(n):
    y = int(yr[i]); cnt[y] = cnt.get(y, 0) + 1
    doy = min(365, cnt[y] // 6)
    dates.append(datetime.date(y, 1, 1).toordinal() + doy)
dates = np.array(dates)
# regime 信号(因果拖尾, 从日线缓存重算)
closes = {k: {int(x): v2 for x, v2 in v.items()} for k, v in json.load(open('/mnt/storage/private/work_hsy/w3lane/s30/daily_closes_2020.json')).items()}
D0 = datetime.date(2020, 1, 5).toordinal(); D1 = datetime.date(2026, 8, 19).toordinal(); DD = D1 - D0 + 1
def px(s):
    p = np.full(DD, np.nan)
    for dd, c in closes.get(s, {}).items():
        if D0 <= dd <= D1: p[dd - D0] = c
    return p
lb = np.log(px('BTCUSDT')); E = []; Hh = []
for s in closes:
    if s == 'BTCUSDT': continue
    lp = np.log(px(s)); r = np.diff(lp) - np.diff(lb)
    for t0_ in range(0, DD - 10, 5):
        lpc = 0.0; hit = -1
        for k in range(t0_, min(t0_ + 60, DD - 9)):
            if k >= len(r) or not np.isfinite(r[k]): break
            lpc += r[k]
            if np.expm1(-lpc) <= DEPTH: hit = k; break
        if hit < 0: continue
        w = r[hit+1:hit+8]
        if len(w) < 7 or not np.isfinite(w).all(): continue
        E.append(D0 + hit); Hh.append(-float(np.expm1(w.sum())))
E = np.array(E); Hh = np.array(Hh)
def regime_at(dord):
    m = (E >= dord - 395) & (E <= dord - 30)
    if m.sum() < 200: return 'H'
    return 'C' if Hh[m].mean() < -0.0002 else 'H'
reg_cache = {}
REG = np.array([reg_cache.setdefault(d, regime_at(d)) for d in dates])
print('regime 分布:', {k: int((REG == k).sum()) for k in ('C', 'H')})
# 目标权重预计算(与 healthcheck 同)
TGT, MSK, RET = [], [], []
held = {"k": np.full(N, np.nan), "s": np.full(N, np.nan), "f": np.full(N, np.nan)}
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held["k"] = v
    if i == 0 or ti % 24 == 0:
        v = np.full(N, np.nan); v[m] = src.s2[ti, m]; held["s"] = v
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.CH[ti, m, FI]; held["f"] = v
    r = LG.compose_book(held["k"][m], held["s"][m], held["f"][m], np.ones(len(m)),
                        weights=W, rvol=src.CH[ti, m, RVI].astype(float), risk_budget=RB)
    w = np.full(N, 0.0); w[m] = np.asarray(r["target_w"], float)
    TGT.append(w); MSK.append(m); RET.append(src.Y4[ti, m].astype(float))

def run(mode):
    state = None; prev = np.zeros(N)
    cum = np.zeros(N); cnt2 = np.zeros(N, int); stop_until = np.full(N, -1)
    pnl = np.zeros(n); trn = np.zeros(n)
    for i in range(n):
        m = MSK[i]; syms = [SYMS[j] for j in m]
        out = LG.apply_harvest_ema(TGT[i][m], syms, state, 0.05)
        state = out["state"]
        tgt = np.asarray(out["target_w"], float)
        active = mode in ('S1', 'S2') or (mode == 'S3' and REG[i] == 'C')
        if mode != 'S0':
            blocked = np.where(stop_until > i)[0]
            if len(blocked):
                bs = set(blocked.tolist())
                for k2, j in enumerate(m):
                    if j in bs: tgt[k2] = 0.0
        w = prev.copy(); w[[j for j in range(N) if j not in set(m)]] = 0.0
        delta = tgt - w[m]; T = np.abs(delta) > BW
        wm = w[m].copy(); wm[T] = tgt[T]
        if T.any(): wm[T] -= wm.sum()/T.sum()
        w[m] = wm
        y = RET[i]; ok = np.isfinite(y)
        contrib = np.zeros(N); idx = m[ok]
        contrib[idx] = w[m][ok]*y[ok]*1e4
        pnl[i] = contrib.sum(); trn[i] = float(np.abs(w-prev).sum())
        # 深度记账(基于本臂自身路径)
        newpos = (np.abs(w) > 1e-9)
        cum = np.where(newpos, cum + contrib, 0.0)
        with np.errstate(all='ignore'):
            depth = np.where(newpos & (np.abs(w) > 1e-6), cum / (np.abs(w)*1e4), 0.0)
        if mode != 'S0':
            need = 1 if (mode == 'S2' or (mode == 'S3' and REG[i] == 'C')) else 2
            hitd = newpos & (depth <= DEPTH) & (stop_until <= i)
            if mode == 'S3' and REG[i] == 'H': hitd = np.zeros(N, bool)
            cnt2 = np.where(hitd, cnt2 + 1, 0)
            fire = cnt2 >= need
            if fire.any():
                stop_until[fire] = i + COOL; cnt2[fire] = 0
        prev = w
    return pnl, trn

res = {}
for mode in ('S0', 'S1', 'S2', 'S3'):
    g, t = run(mode)
    net = g - t*C1
    df = pd.DataFrame({'y': yr, 'net': net})
    by = {int(y): round(float(gg.net.mean()), 3) for y, gg in df.groupby('y')}
    q5 = float(np.percentile(net, 5))
    res[mode] = {'net_all': round(float(net.mean()), 3), 'sharpe': round(float(net.mean()/net.std(ddof=1)*ANN), 2),
                 'by_year': by, 'p5_anchor': round(q5, 1), 'turnover': round(float(t.mean()), 4)}
    print(mode, json.dumps(res[mode], ensure_ascii=False))
json.dump(res, open(f'{PD}/book_adaptive_stop.json', 'w'))
