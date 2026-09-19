# -*- coding: utf-8 -*-
"""融合逐层 IC 拆解(独立研究员第三轮 §8-2: 「逐层导出 King 侧组合、F10、融合前后… 核对身份」)。

## ★ 2026-09-19 人口修正版(独立复审第四轮 R4-B1 / R4-B2; 上一版存档 archive/blend_layers_ic_22d2c826.py)

1. **R4-B2**: 上一版第二部分 `neutral_ret` 为每层【各自】重筛非零名, 122 锚中多数锚六层比的是不同人口,
   而报告写「六层同一批名」。本版第二部分与第一部分用【同一个】逐锚共同人口
   (六层皆非零 ∩ A、B 两端有价); 旧口径(逐层各自人口)仍复算并打印, **只作对账, 已作废**。
2. **R4-B1**: FC − KC 比的是两条【生产状态链】(各自 EMA/免交易带历史、各自初始化, 2026-08-30 04Z 热启动来源不同),
   不是原始模型分数。上一版命名「F10 模型 vs king 模型」过度认领 ⇒ 改名「生产 KC/FC 状态链比较」。
   原始分数对照**本版不做**(FTRIM 前 / chain 前的 z 未归档), 需要的装置见输出末尾。
3. 价格量只覆盖相邻锚都有价的共同持有人口, 逐层去均值、除 gross; 不含资金费、不扣费;
   读价在名义锚之后(中位数本装置打印); 平仓区间被排除。⇒ 它不能说「执行层不贡献」,
   也不能登记已证明的「排序≠净额」新案例(那要完整净额)。正确说法: 「排序与价格收益证据不同」。

## 生产 combo 的构造(`~/wide_shadow/fea171/combo_stage.py`, 在役 3520d363, L229–272 —— 读的是【生产】文件,
## 因为这里拆的是生产写出的归档, 不是回放)

    w3m   = [w3[king], 0, w3[fund]] 归一              # rev24 席位去掉
    z_kc  = w3m[0]·z_king + w3m[2]·z_fund           # king 复合腿
    z_fc  = w3m[0]·z_F10  + w3m[2]·z_fund           # F10 复合腿(同一资金费腿、同一席位)
    FTRIM: 两腿各自把「负费率空头」z 置 0
    sm_kc = chain(z_kc | H_kc_prev) ; sm_fc = chain(z_fc | H_fc_prev)     # 去均值/L1/cap/EMA α/免交易带/出场
    combo = exec_reshape(0.55·sm_kc + 0.45·sm_fc)  → target_combo

**L268–270 把 sm_kc / sm_fc 本身存成 `fea171/state_H_{kc,fc}_{A}.npz`** ⇒ 两条链逐锚都有归档, 本装置**不做任何重建**。
**但归档的是链的【状态】, 不是链的【输入】**: sm_t = f(z_t, sm_{t−1}) 且免交易带(combo_stage.py L92)使 f 非线性、路径依赖;
两链各有初始化(combo_stage.py L262–263: kc 以实盘 H 热启动、fc 以侧车 f10 态热启动), 故 FC − KC ≠ z_F10 − z_king 的效应。

## 层

| 层 | 来源 | 是什么 |
|---|---|---|
| KING_FORM | `state/target_live_king/{A}.json` | 生产者 king 三腿形态书(含 rev24, 不含 F10)—— **不是 combo 的一个分量** |
| KC | `fea171/state_H_kc_{A}.npz` | combo 内 king 复合链的状态(去 rev24, 过 FTRIM 与 chain) |
| FC | `fea171/state_H_fc_{A}.npz` | combo 内 F10 复合链的状态(同上) |
| COMBO | `state/target_combo/{A}.json` | 0.55·KC + 0.45·FC 经 reshape |
| FINAL | `state/target_live/{A}.json` | 执行器读的目标 |
| HELD | `pilot_log/*/position_readback.jsonl` | 场所回读持仓(读价时钟见输出) |

收益 = 场所隐含价 `|notional|/|qty|` 相邻 4h 网格锚之比 −1(与生产 `ic_monitor` 同源, 其 261 锚已逐值复现)。
**第一、第二部分的所有层都限制在同一批名上**(逐锚: 六层皆非零 ∩ A、B 两端有价), 否则比的是人口不是书。

## 配对差(每条都是一个可解释的变动; 都不是单变量因果)

- KC − KING_FORM : 去掉 rev24 + 换到 combo 的状态链(两件事叠在一起, 本装置分不开)
- FC − KC        : 生产 KC/FC 状态链比较(当期输入只在模型项不同, 但比的是带历史/初始化的状态, 不是原始分数)
- COMBO − KC     : combo 书 vs KC 状态链(混入 45% FC 链的净效果)
- FINAL − COMBO  : combo → 执行目标(只差 reshape)
- HELD − FINAL   : 持仓回读 vs 目标(共同持有人口 + 回读时钟上; 不是执行因果损益)

## 边界(先写)

IC 是**排序**量不是**净额**量; 第二部分是去均值的**价格分量**, 也不是净额。
本装置**不主张**移除 F10、改 55/45、换任何形态会更赚钱, 也**不主张**任何执行层归因。
FTRIM 前 / chain 前的 z 未归档, 本装置**测不到**那两层, 也做不了原始分数对照; 那需要已认证的 as-of 回放装置加导出。

窗口冻结: 起点锚 A ∈ [COMBO_START, A_END] = [2026-08-26 04Z, 2026-09-18 20Z] —— 与上一版收据(22d2c826)及复审 R4 探针同窗,
使本版数字可与二者逐值对账。延长窗口 = 改 A_END 另跑、另存收据, 不覆盖本收据。

用法: /usr/bin/python3 blend_layers_ic.py
"""
import calendar
import glob
import hashlib
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
A_END = T("2026-09-18T20:00Z")    # 冻结窗口终点(起点锚上限), 见 docstring
SEED = 20260919
# 复审第四轮探针结果(只读, 用于逐值对账; 不存在时只打印「缺」, 不影响本装置数字)
REVIEW_R4 = ("/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/"
             "research/codex_causal_fullchain_2026-09-14/integration/round4_cash_blend_20260919/agents/blend/probe_result.json")

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


def js_doc(d, A):
    p = f"{WS}/state/{d}/{A}.json"
    return json.load(open(p)) if os.path.exists(p) else None


def js_weights(d, A):
    j = js_doc(d, A)
    w = j.get("weights") if j else None
    return {k: float(v) for k, v in w.items()} if w else None


def npz_weights(tag, A):
    p = f"{WS}/fea171/state_H_{tag}_{A}.npz"
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return {syms[int(i)]: float(v) for i, v in zip(z["idx"], z["val"]) if abs(float(v)) > 0}


# ── 读回读: px/held 与上一版逐字同(只收非零行, 同格点后写覆盖先写); 另记读价时刻与「被零仓更新取代」的行 ──
px, held, rts = {}, {}, {}
latest = {}                        # (grid, sym) → 该格点最后一条记录(含零仓), 只用于识别平仓格点
n_no_read_ts = 0
for p in sorted(glob.glob(f"{PL}/*/position_readback.jsonl")):
    for l in open(p, errors="ignore"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        g = int(float(r.get("anchor_ts") or 0) // GRID * GRID)
        latest[(g, r.get("symbol"))] = r
        q, nt = r.get("venue_position_qty"), r.get("venue_position_notional")
        if q in (None, 0) or nt is None:
            continue
        px.setdefault(g, {})[r["symbol"]] = abs(float(nt)) / abs(float(q))
        held.setdefault(g, {})[r["symbol"]] = float(nt)
        if r.get("read_ts") is None:
            n_no_read_ts += 1
        rts.setdefault(g, {})[r["symbol"]] = float(r.get("read_ts") or r.get("anchor_ts"))


def neutral_bps(v, r):
    """去均值 → 除 gross → Σw·r, bps/锚/gross。v, r 同序数组。"""
    v = np.asarray(v, float); v = v - v.mean(); gv = np.abs(v).sum()
    return float((v @ r) / gv * 1e4) if gv > 0 else np.nan


def neutral_ret_own_pop(w, A, B):
    """★ 旧口径(22d2c826 第二部分, 已作废, 只作对账): 每层【各自】重筛自己的非零名 ⇒ 六层人口不同。逐字保留。"""
    names = [s for s in w if s in px[A] and s in px[B] and abs(w[s]) > 0]
    v = np.array([w[s] for s in names]); r = np.array([px[B][s] / px[A][s] - 1 for s in names])
    raw_net = float(v.sum() / max(np.abs(v).sum(), 1e-12))
    v = v - v.mean()
    gv = np.abs(v).sum()
    return ((v @ r) / gv * 1e4 if gv > 0 else np.nan), raw_net


LAYERS = ("KING_FORM", "KC", "FC", "COMBO", "FINAL", "HELD")
rows, skipped = [], {"missing_layer": 0, "no_next": 0, "small_common": 0}
skipped_list = []
for A in sorted(a for a in px if COMBO_START <= a <= A_END):
    nxt = [g for g in px if A < g <= A + 6 * 3600]
    if not nxt:
        skipped["no_next"] += 1; skipped_list.append((A, "no_next"))
        continue
    B = min(nxt)
    L = {"KING_FORM": js_weights("target_live_king", A), "KC": npz_weights("kc", A), "FC": npz_weights("fc", A),
         "COMBO": js_weights("target_combo", A), "FINAL": js_weights("target_live", A), "HELD": held.get(A)}
    if any(v is None for v in L.values()):
        skipped["missing_layer"] += 1; skipped_list.append((A, "missing_layer"))
        continue
    priced = set(px[A]) & set(px[B])
    own = {k: {s for s, x in v.items() if abs(x) > 0} & priced for k, v in L.items()}
    common = set(priced)
    for v in L.values():
        common &= {k for k, x in v.items() if abs(x) > 0}
    common = sorted(common)
    if len(common) < 30:
        skipped["small_common"] += 1; skipped_list.append((A, "small_common"))
        continue
    ret = np.array([px[B][s] / px[A][s] - 1.0 for s in common])
    row = {"A": A, "B": B, "n": len(common), **{k: spear(np.array([L[k][s] for s in common]), ret) for k in LAYERS}}
    # 第二部分 · 修正口径: 与 IC 同一批 common 名
    for k in LAYERS:
        row["bk_" + k] = neutral_bps([L[k][s] for s in common], ret)
        v = np.array([L[k][s] for s in common]); row["net_" + k] = float(v.sum() / max(np.abs(v).sum(), 1e-12))
        gall = sum(abs(x) for x in L[k].values())
        row["cov_" + k] = float(np.abs(v).sum() / gall) if gall > 0 else np.nan        # 该层 gross 落在共同人口里的份额
        row["own_n_" + k] = len(own[k])
        row["bo_" + k], row["neto_" + k] = neutral_ret_own_pop(L[k], A, B)       # 旧口径, 只作对账
    row["pop_set_differs"] = any(own[k] != set(common) for k in LAYERS)
    row["pop_count_differs"] = len({len(own[k]) for k in LAYERS}) > 1
    row["lagA"] = [rts[A][s] - A for s in common]
    row["lagB"] = [rts[B][s] - B for s in common]
    row["span"] = [rts[B][s] - rts[A][s] for s in common]
    row["lag_allA"] = [rts[A][s] - A for s in px[A]]
    jc = js_doc("target_combo", A) or {}
    row["kc_src"], row["fc_src"] = jc.get("kc_state_source"), jc.get("fc_state_source")
    ft = jc.get("ftrim")
    row["ftrim"] = None if not ft else (len(set(ft.get("names_kc") or {}) ^ set(ft.get("names_fc") or {})), ft.get("n_kc"), ft.get("n_fc"))
    rows.append(row)

print(f"可评分锚 {len(rows)}  ({U(rows[0]['A'])} .. {U(rows[-1]['A'])});  逐锚六层共同名 中位 {int(np.median([r['n'] for r in rows]))}")
print(f"窗口冻结: 起点锚 {U(COMBO_START)} .. {U(A_END)}(与 22d2c826 收据、复审 R4 探针同窗)")
print(f"跳过: {skipped}  明细: " + ", ".join(f"{U(a)}={w}" for a, w in skipped_list))
print("★ 六层限制在【同一批名】上(第一、第二部分同一人口)\n")

WINS = (("整个 combo 期", lambda r: True), ("九月", lambda r: r["A"] >= T("2026-09-01T00:00Z")), ("最近 24 锚", None))
print(f"{'窗口':<14}{'n':>4}" + "".join(f"{k:>11}" for k in LAYERS))
for lab, f in WINS:
    sub = rows[-24:] if f is None else [r for r in rows if f(r)]
    print(f"{lab:<14}{len(sub):>4}" + "".join(f"{np.nanmean([r[k] for r in sub]):>+11.5f}" for k in LAYERS))

day = np.array([time.strftime("%Y-%m-%d", time.gmtime(r["A"])) for r in rows])
days = sorted(set(day))


def block_ci(d, L, seed, nboot):
    """按 UTC 日分块自举(与 22d2c826 逐字同算法, 以便旧数逐值复现)。返回 (lo, hi)。"""
    blocks = [days[i:i + L] for i in range(0, len(days), L)]
    idx_sets = [np.isin(day, bb) for bb in blocks]
    rng = np.random.default_rng(seed)
    bs = np.array([np.nanmean(np.concatenate([d[idx_sets[i]] for i in rng.integers(0, len(blocks), len(blocks))]))
                   for _ in range(nboot)])
    return np.percentile(bs, 2.5), np.percentile(bs, 97.5)


print("\n=== 配对差, 整个 combo 期; 块长敏感性 1/2/3/5 日(各 8000 次, seed %d) ===" % SEED)
print("  ★ 「含0」用闭区间 lo <= 0 <= hi —— 更早一版写成开区间, 退化区间 [0,0] 被误判为「不含 0」")
PAIRS = (("KC − KING_FORM", "KC", "KING_FORM", "去 rev24 + 换到 combo 状态链(两件事叠加)"),
         ("FC − KC", "FC", "KC", "生产 KC/FC 状态链比较(非原始模型分数比较)"),
         ("COMBO − KC", "COMBO", "KC", "combo 书 vs KC 状态链(混入 45% FC 链)"),
         ("FINAL − COMBO", "FINAL", "COMBO", "combo → 执行目标(只差 reshape)"),
         ("HELD − FINAL", "HELD", "FINAL", "持仓回读 vs 目标(共同持有人口·回读时钟; 非执行因果)"))
print(f"  {'配对':<16}{'点估计':>10}" + "".join(f"{f'{L}日块 CI':>26}" for L in (1, 2, 3, 5)) + "   含义")
for lab, a, b, what in PAIRS:
    d = np.array([r[a] - r[b] for r in rows])
    cells = []
    for L in (1, 2, 3, 5):
        lo, hi = block_ci(d, L, SEED + L, 8000)
        mark = "·含0" if lo <= 0 <= hi else "  ★"
        cells.append(f"[{lo:+.5f},{hi:+.5f}]{mark}")
    print(f"  {lab:<16}{np.nanmean(d):>+10.5f}" + "".join(f"{c:>26}" for c in cells) + f"   {what}")
print(f"\n  日数 {len(days)} ⇒ 块数 1日 {len(days)} / 2日 {-(-len(days)//2)} / 3日 {-(-len(days)//3)} / 5日 {-(-len(days)//5)}")
print("\n★ 边界: IC 是排序量不是净额量; 本装置不主张移除 F10 / 改 55/45 / 换形态会更赚钱。")
print("  FC − KC 是两条生产状态链之差(各自历史/初始化/免交易带), 不是「F10 分数代替 king 分数」的单变量效应。")
print("  FTRIM 前与 chain 前的 z 未归档, 这两层本装置测不到。")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 第二部分: 书层价格分量 —— rank-IC 与去均值价格收益给不给同一个方向?
#
# 为什么做: rank-IC 对「全书统一平移」不变且把每个名【等权】看待; Σw·r 按【权重】加权。两者可以不同向。
# 公平性: 各层原始净敞口不同, 直接比 Σw·r 会吃进「净敞口 × 市场涨跌」⇒ 每层先【去均值】(与执行器 reshape 同构)再除 gross。
# ★ 人口(2026-09-19 修正, R4-B2): 每层都在第一部分的同一个逐锚 common 人口上算。
#   上一版(22d2c826)第二部分每层各自重筛非零名, 六层人口不同; 其数字在下方以「旧口径」打印, 只作对账, 已作废。
# ★ 这个量【不是】净额: 只覆盖相邻锚都有价的共同持有人口; 去均值 + 除 gross; 不含资金费; 不扣费;
#   价格在名义锚之后读(下方打印中位分钟数); 平仓区间被排除(下方列出)。
#   ⇒ 不能据此说「执行层不贡献」, 也不能登记已证明的「排序≠净额」新案例; 只能说「排序与价格收益证据不同」。
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("\n\n=== 第二部分: 书层价格分量(每层去均值, bps/锚/gross; 不含资金费 carry, 不扣费; 【与第一部分同一逐锚人口】) ===")

nd = sum(r["pop_set_differs"] for r in rows); ndc = sum(r["pop_count_differs"] for r in rows)
print(f"人口对账: 旧口径下「六层各自人口」与共同人口【集合】不同的锚 {nd}/{len(rows)}"
      f"(只看计数不同的锚 {ndc}/{len(rows)}, 计数相同但集合不同的锚 {nd - ndc})")
print("  逐层各自人口大小(中位/最小/最大) vs 共同人口 中位 %d / 最小 %d / 最大 %d:" %
      (int(np.median([r['n'] for r in rows])), min(r['n'] for r in rows), max(r['n'] for r in rows)))
print("   " + "  ".join(f"{k} {np.median([r['own_n_' + k] for r in rows]):.1f}/{min(r['own_n_' + k] for r in rows)}/{max(r['own_n_' + k] for r in rows)}"
                        for k in LAYERS))
print("  各层 gross 落在共同人口外的份额(均值/中位/最大): " + "  ".join(
    f"{k} {np.mean([1 - r['cov_' + k] for r in rows]):.2%}/{np.median([1 - r['cov_' + k] for r in rows]):.2%}/{max(1 - r['cov_' + k] for r in rows):.2%}"
    for k in LAYERS))


def mins(x):
    x = np.asarray(x, float) / 60.0
    return f"中位 {np.median(x):.2f} / p10 {np.percentile(x, 10):.2f} / p90 {np.percentile(x, 90):.2f} / 最小 {x.min():.2f} / 最大 {x.max():.2f} 分钟"


print("读价时钟(read_ts − 名义格点锚):")
print("  起点 A, 所有非零回读行: " + mins([x for r in rows for x in r["lag_allA"]]) + f"  (行数 {sum(len(r['lag_allA']) for r in rows)})")
print("  起点 A, 共同人口:       " + mins([x for r in rows for x in r["lagA"]]))
print("  终点 B, 共同人口:       " + mins([x for r in rows for x in r["lagB"]]))
sp = np.array([x for r in rows for x in r["span"]]) / 3600.0
print(f"  实际读价间隔 read_ts(B) − read_ts(A): 中位 {np.median(sp):.3f} h / 最小 {sp.min():.3f} / 最大 {sp.max():.3f}   (缺 read_ts 退回 anchor_ts 的回读行: {n_no_read_ts})")
print("  ⇒ 目标写出到第一次读价之间的价格变化、成交与未成交, 不在这个量里。")

# 平仓格点: 同一格点内先有非零回读、后被零仓回读取代的行(加载器只收非零行 ⇒ 这些格点的 px 是平仓前读价)
flat = {}
for (g, s), r in latest.items():
    if COMBO_START <= g <= A_END + 6 * 3600 and r.get("venue_position_qty") == 0 and g in px and s in px[g]:
        flat.setdefault(g, {"n": 0, "src": set()}); flat[g]["n"] += 1; flat[g]["src"].add(str(r.get("source")))
startA = {r["A"] for r in rows}; endB = {r["B"]: r["A"] for r in rows}
print("平仓区间(同格点内非零回读后被零仓回读取代; 读者只收非零行):")
for g in sorted(flat):
    tag = ("作为起点入选" if g in startA else "不作为起点(无 6h 内下一有价格点)") + \
          (f"; 作为终点: {U(endB[g])}→{U(g)} 用的是平仓前读价" if g in endB else "")
    print(f"  {U(g)}  被取代 {flat[g]['n']} 名  来源 {sorted(flat[g]['src'])}  {tag}")
print(f"  共 {len(flat)} 个平仓格点, {sum(v['n'] for v in flat.values())} 条被取代的非零行; 入选起点的平仓格点 {len(set(flat) & startA)} 个")
print("  ⇒ 平仓本身、平仓后 halt 的区间都不在本量里; 以平仓格点为终点的区间只算到平仓前读价。")

print(f"\n原始净敞口(净/gross, 共同人口)均值: " + "  ".join(f"{k} {np.mean([x['net_' + k] for x in rows]):+.3f}" for k in LAYERS))
print(f"{'窗口':<14}{'n':>4}" + "".join(f"{k:>11}" for k in LAYERS))
for lab, f in WINS:
    sub = rows[-24:] if f is None else [r for r in rows if f(r)]
    print(f"{lab:<14}{len(sub):>4}" + "".join(f"{np.nanmean([r['bk_' + k] for r in sub]):>+11.3f}" for k in LAYERS))

print(f"\n  配对差(同一人口), 块自举各 6000 次, seed {SEED}+100+块长; 「含0」= 闭区间 lo <= 0 <= hi")
print(f"  {'配对':<16}{'旧口径点估计':>14}{'修正点估计':>12}" + "".join(f"{f'{Lb}日块 CI':>26}" for Lb in (1, 3, 5)) + "   含义")
PAIRS2 = PAIRS + (("COMBO − KING_FORM", "COMBO", "KING_FORM", "换装净形态差(去 rev24 + 混 FC 链 + 换链; 上一版报告「另算」项)"),)
fixed = {}
for lab, a, b, what in PAIRS2:
    d = np.array([r["bk_" + a] - r["bk_" + b] for r in rows]); do = np.array([r["bo_" + a] - r["bo_" + b] for r in rows])
    cells = []; fixed[lab] = {"mean": float(np.nanmean(d)), "old": float(np.nanmean(do)), "ci": {}}
    for Lb in (1, 3, 5):
        lo, hi = block_ci(d, Lb, SEED + 100 + Lb, 6000)
        fixed[lab]["ci"][Lb] = (lo, hi)
        cells.append(f"[{lo:+.4f},{hi:+.4f}]{'·含0' if lo <= 0 <= hi else '  ★'}")
    print(f"  {lab:<16}{np.nanmean(do):>+14.6f}{np.nanmean(d):>+12.6f}" + "".join(f"{c:>26}" for c in cells) + f"   {what}")

print("\n  —— 旧口径(22d2c826 第二部分: 逐层各自人口, 已作废; 只为证明本装置逐值复现上一版收据) ——")
print(f"  原始净敞口(净/gross, 各自人口)均值: " + "  ".join(f"{k} {np.mean([x['neto_' + k] for x in rows]):+.3f}" for k in LAYERS))
print(f"  {'窗口':<14}{'n':>4}" + "".join(f"{k:>11}" for k in LAYERS))
for lab, f in WINS:
    sub = rows[-24:] if f is None else [r for r in rows if f(r)]
    print(f"  {lab:<14}{len(sub):>4}" + "".join(f"{np.nanmean([r['bo_' + k] for r in sub]):>+11.3f}" for k in LAYERS))
print(f"  {'配对':<18}{'点估计':>9}" + "".join(f"{f'{Lb}日块 CI':>22}" for Lb in (1, 3, 5)))
for lab, a, b, _ in PAIRS2:
    d = np.array([r["bo_" + a] - r["bo_" + b] for r in rows]); cells = []
    for Lb in (1, 3, 5):
        lo, hi = block_ci(d, Lb, SEED + 100 + Lb, 6000)
        cells.append(f"[{lo:+.2f},{hi:+.2f}]{'·含0' if lo <= 0 <= hi else '  ★'}")
    print(f"  {lab:<18}{np.nanmean(d):>+9.3f}" + "".join(f"{c:>22}" for c in cells))

# ── 与复审第四轮探针逐值对账(共同人口) ──
print("\n=== 与复审 R4 探针(agents/blend/probe_result.json, book_common)逐值对账 ===")
if os.path.exists(REVIEW_R4):
    raw = open(REVIEW_R4, "rb").read(); rv = json.loads(raw)
    print(f"  文件 sha256 {hashlib.sha256(raw).hexdigest()}  复审 n={rv.get('n')} 日={rv.get('days')}  复审「逐层人口不同的锚」={rv.get('layer_support_diff_anchors')}(按计数)")
    for lab, a, b, _ in PAIRS:
        pr = rv["stats"]["book_common"]["pairs"].get(f"{a}-{b}")
        if pr is None:
            print(f"  {lab:<16} 复审缺此配对"); continue
        c3 = pr["fixed"]["3"]; m3 = fixed[lab]["ci"][3]
        print(f"  {lab:<16} 本装置 {fixed[lab]['mean']:+.8f}  复审 {pr['mean']:+.8f}  |Δ| {abs(fixed[lab]['mean'] - pr['mean']):.2e}"
              f"   3日块 本 [{m3[0]:+.4f},{m3[1]:+.4f}] 复审 [{c3[0]:+.4f},{c3[1]:+.4f}]")
else:
    print(f"  缺: {REVIEW_R4}")

# ── 状态链事实(支撑 R4-B1 改名) ──
nonown = [(r["A"], r["kc_src"], r["fc_src"]) for r in rows if (r["kc_src"], r["fc_src"]) != ("own", "own")]
fts = [r["ftrim"] for r in rows if r["ftrim"] is not None]
print("\n=== 状态链事实(FC − KC 为什么不是原始分数比较) ===")
print(f"  入选锚中链状态非 own(热启动)的锚: " + (", ".join(f"{U(a)} kc={k} fc={f}" for a, k, f in nonown) or "无"))
print(f"  有 FTRIM 字段的入选锚 {len(fts)}, 其中 kc/fc FTRIM 名单不同的锚 {sum(x[0] > 0 for x in fts)}")
print("  ⇒ 当期输入的差只在模型项(同资金费腿、同席位、FTRIM 名单相同), 但比较对象是带历史与初始化的状态;")
print("    免交易带使 chain 非线性、路径依赖 ⇒ FC − KC 的秩差不能归给「F10 分数 vs king 分数」。")
print("  原始分数对照: 【未做】。需要已认证的 as-of 回放装置(p2_attr_chain_asof.py 一族, 先对生产 3520d363 重生成并过平价)")
print("    导出 chain 前、FTRIM 前的 z_king / z_F10, 并在【同一固定前态】H 下各走一次 chain, 单独替换原始分数;")
print("    与「完整历史路径效应」分开报告, 不混用两个估计对象。")

print("\n=== 逐锚人口(A→B, 共同人口 n, 旧口径各层各自人口 n: KING_FORM/KC/FC/COMBO/FINAL/HELD, 集合是否不同) ===")
for r in rows:
    print(f"  {U(r['A'])}→{U(r['B'])}  n={r['n']:>3}  own=" + "/".join(f"{r['own_n_' + k]}" for k in LAYERS)
          + ("  集合不同" if r["pop_set_differs"] else "  集合相同"))

print("\n★ 读法: 第一部分(rank-IC)融合层配对差(KC−KING_FORM / FC−KC / COMBO−KC)各块长 CI 全在 0 下方;")
print("  第二部分(同一人口上的去均值价格分量)这三对在 1/3/5 日块下 CI 全含 0 ⇒ 排序与价格收益证据不同。")
print("  HELD−FINAL 价格分量只在 5 日块(仅 5 块)不含 0, 1/3 日块含 0 ⇒ 不稳, 不作结论; 且它不是执行因果损益。")
print("  第二部分不是净额(无资金费、无费、读价滞后、平仓区间排除、只覆盖共同持有人口) ⇒ 不登记「排序≠净额」新案例, 不作执行归因。")
print("  本窗 24 天内【没有】证据表明去 rev24 / 混 F10 改变了书的价格分量, 也没有证据表明没改变(低功效)。")
