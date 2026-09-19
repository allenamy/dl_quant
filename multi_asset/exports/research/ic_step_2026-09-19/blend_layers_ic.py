# -*- coding: utf-8 -*-
"""融合逐层 IC 拆解(独立研究员第三轮 §8-2: 「逐层导出 King 侧组合、F10、融合前后… 核对身份」)。

## 生产 combo 的构造(`~/wide_shadow/fea171/combo_stage.py`, 在役 3520d363, L229–272 —— 读的是【生产】文件,
## 因为这里拆的是生产写出的归档, 不是回放)

    w3m   = [w3[king], 0, w3[fund]] 归一              # rev24 席位去掉
    z_kc  = w3m[0]·z_king + w3m[2]·z_fund           # king 复合腿
    z_fc  = w3m[0]·z_F10  + w3m[2]·z_fund           # F10 复合腿(同一资金费腿、同一席位)
    FTRIM: 两腿各自把「负费率空头」z 置 0
    sm_kc = chain(z_kc | H_kc_prev) ; sm_fc = chain(z_fc | H_fc_prev)     # EMA / 带
    combo = exec_reshape(0.55·sm_kc + 0.45·sm_fc)  → target_combo

**L268 把 sm_kc / sm_fc 本身存成 `fea171/state_H_{kc,fc}_{A}.npz`** ⇒ 两条腿逐锚都有归档, 本装置**不做任何重建**。

## 层

| 层 | 来源 | 是什么 |
|---|---|---|
| KING_FORM | `state/target_live_king/{A}.json` | 生产者 king 三腿形态书(含 rev24, 不含 F10)—— **不是 combo 的一个分量** |
| KC | `fea171/state_H_kc_{A}.npz` | combo 内的 king 复合腿(去 rev24, 过 FTRIM 与 chain) |
| FC | `fea171/state_H_fc_{A}.npz` | combo 内的 F10 复合腿(同上) |
| COMBO | `state/target_combo/{A}.json` | 0.55·KC + 0.45·FC 经 reshape |
| FINAL | `state/target_live/{A}.json` | 执行器读的目标 |
| HELD | `pilot_log/*/position_readback.jsonl` | 场所回读实际持仓 |

收益 = 场所隐含价 `|notional|/|qty|` 相邻 4h 网格锚之比 −1(与生产 `ic_monitor` 同源, 其 261 锚已逐值复现)。
**所有层限制在同一批名上**(六层皆非零 ∩ 两端有价), 否则比的是人口不是书。

## 配对差(每条都是一个可解释的变动)

- KC − KING_FORM : 去掉 rev24 + combo 自己的平滑链(两件事叠在一起, 本装置分不开)
- FC − KC        : F10 复合 vs king 复合(**同一资金费腿、同一席位权重** ⇒ 差别只在 king 模型 vs F10 模型那一项)
- COMBO − KC     : 混入 45% F10 的净效果
- FINAL − COMBO  : combo → 执行目标
- HELD − FINAL   : 执行

## 边界(先写)

IC 是**排序**量不是**净额**量; 本装置**不主张**移除 F10、改 55/45 或换任何形态会更赚钱。
FTRIM 前 / chain 前的 z 未归档, 本装置**测不到**那两层; 那需要已认证的回放装置加导出。

用法: python3 blend_layers_ic.py
"""
import calendar
import glob
import json
import os
import time

import numpy as np

WS = "/Users/haosiyu/wide_shadow"
PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
GRID = 14400
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))
T = lambda s: calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%MZ"))
COMBO_START = 1787716800          # 2026-08-26 04Z, 第一个 producer=combo_stage_v1 的锚
SEED = 20260919

syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]


def rankdata(x):
    x = np.asarray(x, float); o = np.argsort(x, kind="mergesort"); r = np.empty(len(x), float)
    r[o] = np.arange(1, len(x) + 1)
    i, xs = 0, x[o]
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    return r


def spear(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else np.nan


def js_weights(d, A):
    p = f"{WS}/state/{d}/{A}.json"
    if not os.path.exists(p):
        return None
    w = json.load(open(p)).get("weights")
    return {k: float(v) for k, v in w.items()} if w else None


def npz_weights(tag, A):
    p = f"{WS}/fea171/state_H_{tag}_{A}.npz"
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return {syms[int(i)]: float(v) for i, v in zip(z["idx"], z["val"]) if abs(float(v)) > 0}


px, held = {}, {}
for p in sorted(glob.glob(f"{PL}/*/position_readback.jsonl")):
    for l in open(p, errors="ignore"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        q, nt = r.get("venue_position_qty"), r.get("venue_position_notional")
        if q in (None, 0) or nt is None:
            continue
        g = int(float(r.get("anchor_ts") or 0) // GRID * GRID)
        px.setdefault(g, {})[r["symbol"]] = abs(float(nt)) / abs(float(q))
        held.setdefault(g, {})[r["symbol"]] = float(nt)

LAYERS = ("KING_FORM", "KC", "FC", "COMBO", "FINAL", "HELD")
rows, skipped = [], {"missing_layer": 0, "no_next": 0, "small_common": 0}
for A in sorted(a for a in px if a >= COMBO_START):
    nxt = [g for g in px if A < g <= A + 6 * 3600]
    if not nxt:
        skipped["no_next"] += 1
        continue
    B = min(nxt)
    L = {"KING_FORM": js_weights("target_live_king", A), "KC": npz_weights("kc", A), "FC": npz_weights("fc", A),
         "COMBO": js_weights("target_combo", A), "FINAL": js_weights("target_live", A), "HELD": held.get(A)}
    if any(v is None for v in L.values()):
        skipped["missing_layer"] += 1
        continue
    common = set(px[A]) & set(px[B])
    for v in L.values():
        common &= {k for k, x in v.items() if abs(x) > 0}
    common = sorted(common)
    if len(common) < 30:
        skipped["small_common"] += 1
        continue
    ret = np.array([px[B][s] / px[A][s] - 1.0 for s in common])
    rows.append({"A": A, "n": len(common), **{k: spear(np.array([L[k][s] for s in common]), ret) for k in LAYERS}})

print(f"可评分锚 {len(rows)}  ({U(rows[0]['A'])} .. {U(rows[-1]['A'])});  逐锚六层共同名 中位 {int(np.median([r['n'] for r in rows]))}")
print(f"跳过: {skipped}")
print("★ 六层限制在【同一批名】上\n")

WINS = (("整个 combo 期", lambda r: True), ("九月", lambda r: r["A"] >= T("2026-09-01T00:00Z")), ("最近 24 锚", None))
print(f"{'窗口':<14}{'n':>4}" + "".join(f"{k:>11}" for k in LAYERS))
for lab, f in WINS:
    sub = rows[-24:] if f is None else [r for r in rows if f(r)]
    print(f"{lab:<14}{len(sub):>4}" + "".join(f"{np.nanmean([r[k] for r in sub]):>+11.5f}" for k in LAYERS))

print("\n=== 配对差, 整个 combo 期; 块长敏感性 1/2/3/5 日(各 8000 次, seed %d) ===" % SEED)
print("  ★ 「含0」用闭区间 lo <= 0 <= hi —— 上一版写成开区间, 退化区间 [0,0] 被误判为「不含 0」")
day = np.array([time.strftime("%Y-%m-%d", time.gmtime(r["A"])) for r in rows])
days = sorted(set(day))
PAIRS = (("KC − KING_FORM", "KC", "KING_FORM", "去 rev24 + combo 平滑链"),
         ("FC − KC", "FC", "KC", "F10 模型 vs king 模型(同资金费腿同席位)"),
         ("COMBO − KC", "COMBO", "KC", "混入 45% F10 的净效果"),
         ("FINAL − COMBO", "FINAL", "COMBO", "combo → 执行目标"),
         ("HELD − FINAL", "HELD", "FINAL", "执行"))
print(f"  {'配对':<16}{'点估计':>10}" + "".join(f"{f'{L}日块 CI':>26}" for L in (1, 2, 3, 5)) + "   含义")
for lab, a, b, what in PAIRS:
    d = np.array([r[a] - r[b] for r in rows])
    cells = []
    for L in (1, 2, 3, 5):
        blocks = [days[i:i + L] for i in range(0, len(days), L)]
        idx_sets = [np.isin(day, bb) for bb in blocks]
        rng = np.random.default_rng(SEED + L)
        bs = np.array([np.nanmean(np.concatenate([d[idx_sets[i]] for i in rng.integers(0, len(blocks), len(blocks))]))
                       for _ in range(8000)])
        lo, hi = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
        mark = "·含0" if lo <= 0 <= hi else "  ★"
        cells.append(f"[{lo:+.5f},{hi:+.5f}]{mark}")
    print(f"  {lab:<16}{np.nanmean(d):>+10.5f}" + "".join(f"{c:>26}" for c in cells) + f"   {what}")
print(f"\n  日数 {len(days)} ⇒ 块数 1日 {len(days)} / 2日 {-(-len(days)//2)} / 3日 {-(-len(days)//3)} / 5日 {-(-len(days)//5)}")
print("\n★ 边界: IC 是排序量不是净额量; 本装置不主张移除 F10 / 改 55/45 / 换形态会更赚钱。")
print("  FTRIM 前与 chain 前的 z 未归档, 这两层本装置测不到。")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 第二部分(2026-09-19 追加): 用【书层单位】对账 —— rank-IC 与书的价格收益会不会给出同一个结论?
#
# 为什么必须做: rank-IC 对「全书统一平移」不变(平移是单调变换), 且把每个名【等权】看待;
#   书的价格收益 Σw·r 按【权重】加权, 且对净敞口敏感。两者可以在符号上相反(CLAUDE.md「排序≠净额」)。
# 公平性: 各层原始净敞口不同(KING_FORM −0.069 / FINAL −0.060 / COMBO −0.010 / HELD −0.002),
#   直接比 Σw·r 会吃进「净敞口 × 市场涨跌」。所以每层先【去均值】—— 与执行器 reshape(legs.py 去均值+缩放)同构 ——
#   再除以 gross。target_live 写的是 combo_raw(未 reshape, combo_stage.py L68), 执行器自己再 reshape, 这是设计。
# 2026-09-19 实测: 所有融合层配对差(KC−KING_FORM / FC−KC / COMBO−KC / COMBO−KING_FORM)在 1/3/5 日块下 CI 全含 0;
#   FC−KC +0.012, COMBO−KC +0.074 bps/锚/gross。⇒ IC 的融合层信号【不转化为】可检测的书层价格效应。
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("\n\n=== 第二部分: 书层单位对账(每层去均值, bps/锚/gross, 价格分量, 不含资金费 carry, 不扣费) ===")


def neutral_ret(w, A, B):
    names = [s for s in w if s in px[A] and s in px[B] and abs(w[s]) > 0]
    v = np.array([w[s] for s in names]); r = np.array([px[B][s] / px[A][s] - 1 for s in names])
    raw_net = float(v.sum() / max(np.abs(v).sum(), 1e-12))
    v = v - v.mean()
    gv = np.abs(v).sum()
    return ((v @ r) / gv * 1e4 if gv > 0 else np.nan), raw_net


brows = []
for A in sorted(a for a in px if a >= COMBO_START):
    nxt = [x for x in px if A < x <= A + 6 * 3600]
    if not nxt:
        continue
    B = min(nxt)
    L = {"KING_FORM": js_weights("target_live_king", A), "KC": npz_weights("kc", A), "FC": npz_weights("fc", A),
         "COMBO": js_weights("target_combo", A), "FINAL": js_weights("target_live", A), "HELD": held.get(A)}
    if any(v is None for v in L.values()):
        continue
    r = {"A": A}
    for k, w in L.items():
        r[k], r[k + "_net"] = neutral_ret(w, A, B)
    brows.append(r)
print("原始净敞口(净/gross)均值: " + "  ".join(f"{k} {np.mean([x[k + '_net'] for x in brows]):+.3f}" for k in LAYERS))
print(f"{'窗口':<14}{'n':>4}" + "".join(f"{k:>11}" for k in LAYERS))
for lab, f in WINS:
    sub = brows[-24:] if f is None else [r for r in brows if f(r)]
    print(f"{lab:<14}{len(sub):>4}" + "".join(f"{np.nanmean([r[k] for r in sub]):>+11.3f}" for k in LAYERS))
bday = np.array([time.strftime("%Y-%m-%d", time.gmtime(r["A"])) for r in brows]); bdays = sorted(set(bday))
print(f"  {'配对':<18}{'点估计':>9}" + "".join(f"{f'{Lb}日块 CI':>22}" for Lb in (1, 3, 5)))
for lab, a, b, _ in PAIRS:
    d = np.array([r[a] - r[b] for r in brows]); cells = []
    for Lb in (1, 3, 5):
        blocks = [bdays[i:i + Lb] for i in range(0, len(bdays), Lb)]; idx_sets = [np.isin(bday, bb) for bb in blocks]
        rng = np.random.default_rng(SEED + 100 + Lb)
        bs = np.array([np.nanmean(np.concatenate([d[idx_sets[i]] for i in rng.integers(0, len(blocks), len(blocks))]))
                       for _ in range(6000)])
        lo, hi = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
        cells.append(f"[{lo:+.2f},{hi:+.2f}]{'·含0' if lo <= 0 <= hi else '  ★'}")
    print(f"  {lab:<18}{np.nanmean(d):>+9.3f}" + "".join(f"{c:>22}" for c in cells))
print("\n★ 读法: 上半部分(rank-IC)融合层配对差显著为负; 下半部分(书层价格, 去均值)全含 0 ⇒ 两台仪器不同向。")
print("  书层单位才对应盈亏。本窗 24 天内【没有】证据表明去 rev24 / 混 F10 改变了书的价格收益。")
