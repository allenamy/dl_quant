> **创建:** 2026-07-12 | **Session:** 0C Track-1 deepdive (tick validation) | **状态:** final | **作废条件:** live pilot 落地(实测 alt-leg markout),或 Tardis 口径重建

# Track-1 maker-fill 深化 — tick 级验证 + regime 压力 (0C)

**一句话: 1s-bar 近似在两个轴上都乐观、两偏差不抵消(用户直觉对) —— 但书级修正温和,pilot 判词经得起 tick 修正。残余集中风险 = 崩盘日逆选择(mean −5.3,尾 −20 bps)→ 加 vol-gate。**

## Part 1 — tick 级验证(Tardis µs 真 FIFO 队列 vs 1s-bar,BTC-perp 12 天)

| | 1s-bar | tick(真) | 方向 |
|--|--|--|--|
| fill(f=1%,k300) | 0.75-0.96 | 0.45-0.66 | **1s 高估 ~1.5×**(T/B=0.63)|
| adverse markout | ~0(+0.2)| −0.3~−5.3 mean | **1s 基本漏掉逆选择** |
| cancel-clear | — | 0-9% | 排除 cancel 的保守可忽略 |

- **fill 高估机理:** 1s-bar 把**所有**对手侧成交量都算作消耗我们的队列,但 tick 精确只有**价格 ≤p0** 的成交才消耗(价格漂走时那些量打不到我们)。
- **markout 漏掉机理:** 1s 的成交时刻 + 1s mid 把 µs 级逆向移动抹平了;真实 tick 逆选择 = 你**正好在激进流打到你时成交** = 价格即将逆你而动。
- **★两偏差不抵消 —— 都乐观,复合不抵消。** join-at-back + 排除 cancel 的保守(可忽略)远不足以补偿 1s 聚合的乐观。**用户要求 tick 验证是对的。**

## Part 2 — regime 分层(bar_1s 14 币 22 天 + tick 12 天)

- **fill 流动性无关性在崩盘日成立:** 跨币 fill std 在压力期反而**收紧**(calm 0.084 → stress 0.031);bar fill regime-稳(calm 0.87/normal 0.88/stress 0.95)。
- **spread 压力期 ~2× 加宽**(calm 0.69 / normal 0.85 / stress 1.50 bps 中位)。
- **★tick adverse markout 强 regime 依赖(BTC):**

| regime(BTC rvol) | markout mean | p25 尾 | fill |
|--|--|--|--|
| calm (<7) | −0.97 | −3.8 | 0.56 |
| normal (7-18) | −1.71 | −9.5 | 0.52 |
| stress (≥18) | −3.24 | −12.1 | 0.50 |
| **最坏崩盘 2024-08-05** | **−5.30** | **−20.4** | 0.53 |

**压力降级系数: adverse markout ×3-5(calm −1 → 崩盘 −5.3);p25 尾 −3.8 → −20。fill 基本稳。崩盘日 = 最大换手 = 集中风险。**

## Part 4 — tick 修正后书净 Sharpe 下界($5M)

| 场景 | 2022 | 2023 | 2024 | 2025 | 2026 | 有效成本 |
|--|--|--|--|--|--|--|
| normal 全书 | 10.3 | 16.3 | 19.3 | 20.4 | 10.9 | 1.87 |
| normal calib | 8.8 | 15.5 | 17.3 | 18.4 | 13.8 | 1.89 |
| **stress 全书** | 9.2 | 14.8 | 18.1 | 18.9 | **9.5** | 2.68 |
| **stress calib** | 7.9 | 14.4 | 16.3 | 17.0 | 12.5 | 2.90 |

**全场景逐年净正**(含弱年+stress-adverse)。tick 修正把有效成本从 Track-1 的 ~1.5 抬到 **~1.9(normal)/ ~2.7-2.9(stress)bps** —— 温和 +0.4-1.4。**书 gross 边际大,pilot 判词经得起修正。** k=900 工作把 maker fill 翻倍(0.27→0.51)降成本。

## 判词

**PILOT 仍值得(经得起 tick 修正),但+一条 vol-gate。**

**修订 pilot 建议书(存档):** $2-5M,calib-grounded/mega+mid 核心,**k=900 被动**(fill 翻倍)+残余 taker。**★新增 vol-gate: 高波动/崩盘日(BTC rvol >~18 bps/min 或实时触发)减参与/加宽工作窗/趋 taker-中性** —— 逆选择那时飙到 −5 bps mean、尾 −20,这是集中风险(崩盘=最大换手)。**成功判据:** 实测 markout ≤ tick(−1 calm/−3 stress)、fill ≥0.5@k900、成本 ≤2.5(normal)/3.5(stress)bps。**止损:** 成本>4bps 持续 / 崩盘日 markout 尾差于 −25 / fill≪tick。

## ★诚实 caveats(量化残余不确定)

1. **tick markout 只测了 BTC;alt-leg 逆选择未测,大概率更差**(越不流动越 toxic)。我把 BTC markout 统一套用 → **对 alt 腿可能低估 = 最大残余不确定**。pilot 须实测 alt-leg markout。
2. static-at-p0 tick sim(不追价)→ fill 是**下界**(追价 maker fill 更多);真相在 tick(懒)与 bar(追)之间,我取 tick(保守)。
3. fill 流动性无关性 BTC 跨 regime + bar 跨币验证过,alt tick-fill 沿用此假设。
4. 净 Sharpe 量级(8-20)仍带频率×breadth caveat;可部署结论是**有效成本(~1.9-2.9 tick 修正)仍 ≪ gross 边际**。

## 方法论教训(存档)

**1s-bar 聚合不是 maker-fill 经济的保守代理 —— 它是乐观的(高估 fill,漏掉逆选择)。未来执行建模的 markout 必须用 tick 数据;1s bar 只够 spread/notl 的量级估计。**

---
**产物:** `makerfill_deepdive.json` · `tick_vs_1s_raw.json`(tick校准)· `bar_regime_raw.json`(regime)· `tickcorrected_apply_raw.json`(修正下界)· `tick_vs_1s.py`/`bar_regime_sweep.py`/`apply_tickcorrected.py`(可复算)
