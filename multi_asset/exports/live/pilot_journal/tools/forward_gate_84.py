"""combo 84 锚前向门二读(CANDIDATE_wide_v2main_norev24_2026-08-26 §6 冻结判据). 方法逐字沿用首读 gate42_fill.py(2026-09-02):
影子记分 = target_live(候选 combo) vs target_live_king(在役 king 形态) 各自 w(gross 归一=1)× 下一锚 venue mid 简单收益; carry = w × 实收 funding_rate(结算锚);
换手成本 1.9bps × Σ|Δw|; 相邻锚无 anchors 行时用生产者 rolling 缓存 (a, a+4h] 5m 复利收益补 mid; 不可配对锚显式列出。只读; 实盘书零接触。
新增(本读): 按窗内单变量事件分段报数; live 实跑锚子集; kc/fc 状态链; sidecar 独立复算计数; 账本权益路径(扣 TRANSFER); 首读 42 锚复现(#20)。"""
import json, glob, re, os, collections, time
import numpy as np
H = os.path.expanduser('~/wide_shadow/state'); P = os.path.expanduser('~/dl_quant_live/state/live/pilot_log')
syms = json.load(open(os.path.expanduser('~/wide_shadow/shadow_bundle/config.json')))['symbols_panel']; sidx = {s: i for i, s in enumerate(syms)}
z = np.load(f'{H}/rolling.npz', allow_pickle=True); rts = z['ts'].astype(np.int64); R5 = z['data'][:, :, 0].astype(np.float32)
def ret4h_cache(a):
    i0 = np.searchsorted(rts, a, side='right'); i1 = np.searchsorted(rts, a + 14400, side='right')
    if i1 <= i0 or rts[i1 - 1] < a + 14400: return None   # 需要覆盖到 a+4h 的整段 bar
    r = R5[i0:i1]; r = np.where(np.isfinite(r), r, 0.0); return np.prod(1 + r, axis=0) - 1
def anum(v):
    m = re.search(r'(\d{10})', str(v)) if v is not None else None
    return int(m.group(1)) if m else None
mid = {}
for f in sorted(glob.glob(f'{P}/2026*/anchors.jsonl')):
    for ln in open(f):
        d = json.loads(ln); a = anum(d.get('anchor_ts'))
        if not a: continue
        mv = d.get('mid_at_anchor_vector'); mv = json.loads(mv) if isinstance(mv, str) else (mv or {})
        mid[a // 14400 * 14400] = {s: float(p) for s, p in mv.items() if p}
fr = collections.defaultdict(dict)
for f in sorted(glob.glob(f'{P}/2026*/funding.jsonl')):
    for ln in open(f):
        d = json.loads(ln); t = int(float(d.get('settlement_ts', 0))) // 14400 * 14400
        if d.get('funding_rate') is not None: fr[t][d['symbol']] = float(d['funding_rate'])
T0 = 1787716800; N = 84; COST = 1.9e-4
def load_w(dirn, a):
    p = f'{H}/{dirn}/{a}.json'
    if not os.path.exists(p): return None
    d = json.load(open(p)); w = {k: float(v) for k, v in d.get('weights', d).items()}; g = sum(abs(v) for v in w.values()) or 1.0
    return {k: v / g for k, v in w.items()}
def ts(a): return time.strftime('%m-%d %HZ', time.gmtime(a))
rows = []; prevc = prevk = None; src = collections.Counter(); unpair = []
for a in [T0 + 14400 * i for i in range(N)]:
    wc = load_w('target_live', a); wk = load_w('target_live_king', a)
    if wc is None or wk is None: src['unpairable_no_target'] += 1; unpair.append((a, f"无目标文件(combo {wc is not None}/king {wk is not None})")); continue
    nxt = a + 14400
    if a in mid and nxt in mid:
        ret = {s: (mid[nxt][s] / mid[a][s] - 1) for s in set(mid[a]) & set(mid[nxt])}; s_ = 'venue_mid'
    else:
        rc = ret4h_cache(a)
        if rc is None: src['unpairable_no_return'] += 1; unpair.append((a, "相邻锚无 anchors 行且缓存未覆盖 a+4h")); continue
        ret = {s: float(rc[sidx[s]]) for s in syms if s in sidx}; s_ = 'cache_fill'
    src[s_] += 1
    def score(w, prev):
        g = sum(x * ret.get(s, 0.0) for s, x in w.items()); car = sum(x * fr.get(a, {}).get(s, 0.0) for s, x in w.items())
        to = sum(abs(w.get(s, 0) - (prev or {}).get(s, 0)) for s in set(w) | set(prev or {})) if prev is not None else 0.0
        return g * 1e4 - car * 1e4 - to * COST * 1e4, g * 1e4, car * 1e4, to * COST * 1e4
    c = score(wc, prevc); k = score(wk, prevk); rows.append(dict(a=a, src=s_, c=c[0], k=k[0], cg=c[1], kg=k[1], cc=c[2], kc=k[2], ct=c[3], kt=k[3])); prevc, prevk = wc, wk
A = np.array([r['a'] for r in rows]); nc = np.array([r['c'] for r in rows]); nk = np.array([r['k'] for r in rows]); d = nc - nk; n = len(rows)
def stat(m, lab):
    x = nc[m]; y = nk[m]; dd = x - y
    if m.sum() == 0: return f'{lab}: 0 锚'
    se = dd.std(ddof=1) / np.sqrt(m.sum()) if m.sum() > 1 else float('nan')
    return f'{lab:42s} n={m.sum():2d} combo {x.sum():+7.1f}(均 {x.mean():+6.2f}) king {y.sum():+7.1f}(均 {y.mean():+6.2f}) 差 {dd.sum():+7.1f}(均 {dd.mean():+6.3f} ±{1.96*se:5.3f}) 正锚 {(dd>0).mean():.2f}'
out = {}
print(f'== §6 二读(84 锚窗 {ts(T0)}..{ts(T0+14400*(N-1))}; 可配对 {n} 锚; 来源 {dict(src)})')
for a, why in unpair: print(f'   不可配对: {ts(a)} — {why}')
print(f'① 候选(combo)前向净累计 {nc.sum():+.1f}bps(gross=1) 均 {nc.mean():+.3f}/锚 ⇒ ≥0 {"过(未否决)" if nc.sum() >= 0 else "不过"}')
se = d.std(ddof=1) / np.sqrt(n)
print(f'② 差值(combo−在役king形态) 均 {d.mean():+.3f}bps/锚 ±{1.96*se:.3f}(95%) 正锚 {(d>0).mean():.2f} | 回放 +0.29~+0.43 同向 ⇒ {"过(未否决)" if d.mean() > 0 else "不过"}(判据不要求显著)')
print(f'   在役形态净累计 {nk.sum():+.1f}bps | NAV口径(×2.0)候选累计 ≈ {nc.sum()*2/100:+.2f}%, 在役形态 ≈ {nk.sum()*2/100:+.2f}%')
print(f'   分解(均/锚): combo 毛 {np.mean([r["cg"] for r in rows]):+.3f} carry {np.mean([r["cc"] for r in rows]):+.3f} 成本 {np.mean([r["ct"] for r in rows]):+.3f} | king 毛 {np.mean([r["kg"] for r in rows]):+.3f} carry {np.mean([r["kc"] for r in rows]):+.3f} 成本 {np.mean([r["kt"] for r in rows]):+.3f}')
# 首读复现(#20): 首 42 锚, 与 journal_2026-09-02 发表值 +51.5 / +0.654 ±1.224 比
m42 = A < T0 + 14400 * 42; print(f'#20 首读复现(首 42 锚窗, 可配对 {m42.sum()}): combo {nc[m42].sum():+.1f} (发表 +51.5) | 差均 {d[m42].mean():+.3f} (发表 +0.654) | king {nk[m42].sum():+.1f} (发表 +25.3)')
def T(*x): import calendar; return calendar.timegm(x + (0,) * (6 - len(x)))
SEG = [('S0 08-26 04Z–16Z E-0826-F 平仓期(live 未交易)', T(2026, 8, 26, 4), T(2026, 8, 26, 16)), ('S1 08-26 20Z→09-02 08Z combo 1.5×→2.0×(FTRIM 前)', T(2026, 8, 26, 20), T(2026, 9, 2, 8)),
       ('S2 09-02 12Z→09-03 12Z +FTRIM', T(2026, 9, 2, 12), T(2026, 9, 3, 12)), ('S3 09-03 16Z→09-04 00Z +入金×4(2.0× 恒定)', T(2026, 9, 3, 16), T(2026, 9, 4, 0)),
       ('S4 09-04 04Z→09-06 04Z +M1(席位种子 08:53→11:46Z 回滚, 0 锚受影响)', T(2026, 9, 4, 4), T(2026, 9, 6, 4)), ('S5a 09-06 08Z 止损锚(08:46Z 平仓, 部分成交)', T(2026, 9, 6, 8), T(2026, 9, 6, 8)),
       ('S5 09-06 12Z→09-07 00Z 平仓期(影子照记, live 未交易)', T(2026, 9, 6, 12), T(2026, 9, 7, 0)), ('S6 09-07 04Z→09-08 08Z 重建后', T(2026, 9, 7, 4), T(2026, 9, 8, 8)), ('S7 09-08 12Z→09-09 04Z +入金 35k', T(2026, 9, 8, 12), T(2026, 9, 9, 4))]
print('分段(单变量事件, 数字先于结论):')
for lab, lo, hi in SEG: print('  ' + stat((A >= lo) & (A <= hi), lab))
live = ~(((A >= T(2026, 8, 26, 4)) & (A <= T(2026, 8, 26, 16))) | ((A >= T(2026, 9, 6, 12)) & (A <= T(2026, 9, 7, 0))))
print('  ' + stat(live, '★ live 实跑锚子集(剔 S0/S5)')); print('  ' + stat(live & (A >= T(2026, 9, 2, 12)), '   其中 FTRIM 后(09-02 12Z 起)')); print('  ' + stat(live & (A >= T(2026, 9, 4, 4)), '   其中 M1 后(09-04 04Z 起)'))
print('  ' + stat(A >= T0 + 14400 * 42, '   后 42 锚(二读新增窗 09-02 04Z 起)'))
# kc/fc 状态链 + sidecar
L = open(os.path.expanduser('~/wide_shadow/fea171/combo_live.log')).read().splitlines(); own = collections.Counter(); nonown = []
for ln in L:
    if 'COMBO 落盘' in ln:
        k = 'own/own' if 'kc_src=own fc_src=own' in ln else 'other'; own[k] += 1
        if k == 'other': nonown.append(ln.strip()[:160])
sc = collections.Counter(('SIDECAR_DRYRUN PASS' if 'SIDECAR_DRYRUN PASS' in ln else 'SIDECAR_DRYRUN FAIL') for ln in L if 'SIDECAR_DRYRUN' in ln)
print(f'kc/fc 状态链(combo_live.log 全部 COMBO 落盘行): {dict(own)}; 非 own 行: {nonown}'); print(f'sidecar 独立复算(SIDECAR_DRYRUN): {dict(sc)}')
SD = open(os.path.expanduser('~/wide_shadow/fea171/sidecar_daemon.log')).read().splitlines() if os.path.exists(os.path.expanduser('~/wide_shadow/fea171/sidecar_daemon.log')) else []
mx = [float(m.group(1)) for ln in SD for m in [re.search(r'max\|Δw\|=([0-9.e+-]+)', ln)] if m]
print(f'sidecar king 书自平价 max|Δw|: n={len(mx)} 最大 {max(mx) if mx else float("nan"):.2e}(<1e-6 {"全过" if mx and max(mx) < 1e-6 else "见上"})')
# 账本权益路径(扣 TRANSFER)
print('账本权益路径(daily_nav 每日末行; ΔNAV 扣当日 TRANSFER):'); prev = None; cum = 0.0
for dday in sorted(os.listdir(P)):
    p = f'{P}/{dday}/daily_nav.jsonl'
    if not os.path.exists(p) or dday < '20260826': continue
    rws = [json.loads(l) for l in open(p) if l.strip()]
    if not rws: continue
    nav = float(rws[-1].get('nav') or 0); tr = float((rws[-1].get('realised_by_type') or {}).get('TRANSFER') or 0)
    dn = (nav - prev - tr) if prev is not None else 0.0; cum += dn
    print(f'  {dday} nav末 {nav:10.2f} transfer {tr:9.2f} ΔNAV净 {dn:+9.2f} 累计 {cum:+9.2f}'); prev = nav
json.dump({'rows': rows, 'unpairable': unpair, 'src': dict(src), 'own': dict(own), 'sidecar': dict(sc), 'sidecar_maxdw': mx, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forward_gate_84_receipt.json'), 'w'), indent=0)
print('FORWARD_GATE_84_DONE')
