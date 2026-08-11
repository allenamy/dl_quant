p = '/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/PREREG_retrain_causal_panel_2026-08-03.md'
s = open(p, encoding='utf-8').read()
subs = []

subs.append((
 '''**`margin_dirty` 已落定(v5):**
```
出处   C3 `RESULT_champion_serve_caliber_2026-08-03.md`  SHA ac5b5101…
       (其自带 PREREG 冻结于 15:43Z)
TRAIN 口径 champion − lamorth0 边际:   Y4 +0.01470   YR4 +0.01895
margin_dirty := +29.2%(YR4 相对值, 主判)          Y4 并报
★ 与 B4 独立 harness 实测 +29.3% 吻合 —— 两台仪器, 两条独立路径, 同一个数
margin_clean := 干净面板重训后的同口径边际
```''',
 '''**`margin_dirty` 已落定(v6 更新引用形式与阈值):**
```
出处   C3 `RESULT_champion_serve_caliber_2026-08-03.md` 【链式侧车】
       本文所据链顶 = 3d0bc6f5…(链 v2)      注: ac5b5101… 是链 v1
       (按 §4-b 引【文件名 + 链】而非单一 SHA —— 该文档已是判据的一部分, 会继续演进)
TRAIN 口径 champion − lamorth0 边际:   Y4 +0.01470   YR4 +0.01895
margin_dirty := +29.2%(YR4 相对值, 主判)          Y4 并报
★ 与 B4 独立 harness 实测 +29.3% 吻合 —— 两台仪器, 两条独立路径, 同一个数
margin_clean := 干净面板重训后的同口径边际
```

**★ 三分阈值已代入绝对值(链 v2 提供, 免得判定时再算一次):**

| 目标 | H-ATT 成立(< 0.5×) | H-ATT 证伪(≥ 0.8×) |
|---|---|---|
| **YR4(主判)** | `margin_clean < +0.009475` | `margin_clean ≥ +0.015160` |
| Y4(并报) | `< +0.007350` | `≥ +0.011760` |

**⇒ 两阈值之间 = 不决定性。且 §4-2 的量尺条款仍先行: 若 margin 变化落在 run-to-run 量尺的 2 倍内, 直接判不决定性, 不进这张表。**

**★ C3 原话级的限定必须随 margin_dirty 一起走:** `margin_dirty` 用**当年的 checkpoint**, `margin_clean` 来自**重训** ⇒ **两者之差中仍含 run 世代变异。** 这正是 §4-2 选方案 A 的已知代价, **量尺条款就是为它而存在的**。'''))

subs.append((
 '''| 模型 | TRAIN 口径前视利用度 |
|---|---|
| champion(`lamorth0_xattn_5yr`) | **+0.2495** |
| **`lamorth0_5yr`(无 attention, 本条要测的那个)** | **+0.2035**(t 显著) |
| qim | +0.2311 |
| 三者在 **SERVE** 口径下 | **全部塌向 0** |

**登记: 已于 S1 开跑前看过; 看过时刻 = 该文档落盘时刻。**''',
 '''| 模型 | TRAIN 口径前视利用度 |
|---|---|
| champion(`lamorth0_xattn_5yr`) | **+0.2514**(head_scores)/ +0.2495 |
| **`lamorth0_5yr`(无 attention, 本条要测的那个)** | **+0.2040**(head_scores)/ **+0.2035**(重推理), 差 **0.0005** |
| qim | +0.2311 |
| 三者在 **SERVE** 口径下 | **全部塌向 0** |

**★ 两条交叉核对, 都指向"尺子是同一把":**
1. lam0 用**两台装置**(已记录 head_scores vs 重新推理)测出 +0.2040 / +0.2035, **差 0.0005**;
2. champion 的 head_scores 值 **+0.2514 复现了我审计里的 +0.2518**(差 0.0004)—— **我那个数被一条独立路径独立重现了。**

**登记: 已于 S1 开跑前看过; 看过时刻 = 16:48–16:49Z, 早于 S1 任何重训 ⇒ 披露条件满足。**'''))

subs.append((
 '''**⇒ 这【不改变】§4 已冻结的三分阈值**(看到数据后调阈值正是预注册要防的), **但它意味着 H-ATT 在开跑前就已有可见的反向证据 —— 而让这件事可见, 正是披露条款存在的全部意义。**''',
 '''**⇒ 这【不改变】§4 已冻结的三分阈值**(看到数据后调阈值正是预注册要防的), **但它意味着 H-ATT 在开跑前就已有可见的反向证据 —— 而让这件事可见, 正是披露条款存在的全部意义。**

#### 3-3bis ★ 逐年切: 两个弱年给出【相反】的答案 —— 引用时不得合并成一句

链 v2 的逐年切显示: **弱年 2022 的 margin 翻负; 而 2026 仍为正。**

**⇒ 三条后果, 必须一起读:**
1. **`margin_dirty = +29.2%` 是一个【池化】数, 而它池化掉的东西不是同号的。** 把两个弱年合并成"弱年表现如何"这一句话, 会造出一个数据里不存在的一致性。
2. **判别的稳健性因此存疑**: 若 `margin_dirty` 本身逐年不稳(一年翻负), 那么拿单一池化 `margin_dirty` 去比 `margin_clean`, **其差可能主要反映年份构成而非泄漏移除**。
3. **⇒ 落地要求: S1 报告在给出 margin_clean 时, 必须【同时给逐年切】**, 且**逐年结论不得被合并表述**。若逐年方向不一致, 三分判定须带该限定词。

**★ 这与今天的"池化 vs 横截面"是同一族的又一次: 一个池化量掩盖了成分间的反号, 而池化本身没有算错。**'''))

for a, b in subs:
    n = s.count(a)
    print(('OK   %d x  ' % n) + repr(a[:40]) if n == 1 else ('*** MISS/DUP n=%d ***  ' % n) + repr(a[:40]))
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('written')
