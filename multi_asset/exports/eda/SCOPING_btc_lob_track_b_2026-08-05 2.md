> **创建:** 2026-08-05 14:1x UTC | **Session:** team-lead (6737834a) | **状态:** draft(圈定, 非预注册 —— 每条路各自出 prereg 才可跑判决) | **作废条件:** 数据核实(§2)推翻输入可得性 ⇒ 对应路线删除

# SCOPING — Track B: BTC 25 档 LOB, 从单资产最佳版本(REG_arch)出发 benefit 多资产书

**用户指令(2026-08-05): "btc lob 有之前实现的最佳版本单资产模型, 参考看如何 benefit 这个任务"。**
本文把"benefit"拆成三条机制不同的通路, 各配各的门; 复用优先于新造。

## 1. 可复用资产清单(全部已定位)

| 资产 | 位置 | 状态 |
|---|---|---|
| REG_arch 架构 preset | `DualPathLOBModelV3(conformer, FiLM-multistage, DAQH, mono-quantile, 2blk k15 d32)` | 冻结, NAMING.md 钉死 |
| 赢家配置 | `configs/v5push/singh_alpha0_huber_track_reg_arch.json` | 15/15 live gates 的那份 |
| 训好的权重 | `experiments/v5push/singh_daqh_lambda0/fold_*/best_model.pt`(单资产仓, server) | y_600, P≈0.0646(clip+demean 口径)/0.037 honest |
| 25 档双源数据 | `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/`, 现货+永续, 1247d, µs | 干净(修了现货-永续口径 bug) |
| 永续缓存 | server `exports/btc25_raw / btc25_state / btc_feat64_perp / btc_trade_perp` | 已建 |
| 双源 v2 幸存件 | branch `dual-source-perp`: 双书 REG_arch, **always-Run1**(router 已证伪) | 可 warm-start |
| DO-NOT-RETRY | perp-concat ✗ / tail-loss ✗ / regime router ✗ / 盲 backbone 搜索 ✗ | 记忆+STATE 在案 |

## 2. 三条通路(按性价比排序, 机制先行)

### B-1 ★ 执行 overlay: ŷ_BTC(600s) × β_i → 锚点窗口内的成交调度(最高性价比)

**机制**: REG_arch 的原生 horizon 是 **600s = 书的 maker 执行窗的尺度**。单资产结论"alpha 真实
但 taker 成本吃光" —— 但书**本来就要在锚点成交 ~5k USDT**: 用 ŷ_BTC×因果β 给每个名字一个未来
10 分钟漂移预报(同期 β 白送 ~0.045/alt), 只用来决定**已计划成交**的时机与激进度(预报有利⇒更
被动等更好价; 不利⇒尽早成交/提前 topup)。**成本预算 = 0(不新增任何交易) ⇒ 历史否决被结构性
翻转: 不可交易的 alpha 变成不用付成本的 alpha。**
**门**: 影子 A/B(与 chase 随机实验正交性先查, 不得抢它的结论) —— fill 侧 |slip|/markout 改善,
n≥20 锚。**先决核实**: ①旧 checkpoint 的输入管线(通道/norm)实盘能否逐位复现 ②25 档 snapshot
实时可得性(现在只拉 bookTicker; 需 ws depth 或 REST depth, weight 成本入账)。
**与 #33 同框**: ĉ 预测(P(fill) ρ=0.338)和 ŷ 漂移是同一个调度器的两个输入。

### B-2 4h 重定标 leader 因子(书的同 horizon, GPU 排 #46 之后)

**机制**: 25 档双源 REG_arch 重训到 y=4h BTC → (a) β 投影作全书 prior 腿 (b) BTC 名字自身因子。
**风险**: LOB 微结构信号随 horizon 衰减(y600 天花板 ~0.08, 4h 未测可能薄); BTC 无 idio(实测
最难名字) ⇒ 贡献主要走 β 投影而非 BTC 自身。
**门(纪律)**: 先 Ridge/浅层 walk-forward pre-gate(ΔP≥+0.005 才准上 DL); DL 后书级净
ΔrankIC ≥ +0.003 + 与 king/s2 的独立性筛(s2≡vol 的教训: 相关 >0.6 即回声, 杀)。
**warm-start**: dual-source-perp 分支 Run1 权重, 不从零。

### B-3 leader 特征通道广播进 king(最弱先验, 排最后)

channel-addition penalty 实测每通道 −0.013 P —— 只有 B-2 证明 BTC-LOB 在 4h 有信息后才考虑,
且必须过 ≥+0.003 通道门。

## 3. 时序与资源

今晚 GPU = #46 逐头(已冻结 prereg)。B-1 先决核实 = CPU(本周内, 两个核实点见上)。
B-2 pre-gate = CPU Ridge; 重训排 GPU 队列第二位。每条路各自 prereg 后才跑判决 —— 本文不判任何门。

## 4. ★ 判决性更新(2026-08-05 14:2x, 用户两问深想后) — 全轨降级为"记录先行、建模推迟"

**用户问题①: 600 step × 1s 输入直接重训 4h, 序列输入是否要调?** 深想结论: **直接重训否决**, 三重:
(i) 10min 感受野 vs 4h 靶结构失配 —— 窗里只有微结构状态, 无趋势/波动上下文;
(ii) #25 实测 4h 预测的上下文需求在 **126h 量级已饱和** —— 那是 panel 模型已有的东西, 微结构模型补不了;
(iii) 单资产 multiscale 输入 DO-NOT-RETRY(`phase_d_stage1_failed`: 多尺度伤所有 horizon)。
⇒ B-2 重塑为**特征级桥接**: 粗粒度深档状态特征(书斜率/多深度失衡/补单率, 1min 采样, 故意小 parity 面)
进 panel 走 Ridge pre-gate; ŷ600 时序聚合("微结构压力指数")同理 —— 但后者仍需完整 serving 栈, 见下。

**用户问题②: 深档 LOB 推理环节能否免费录到? 不行就别花时间。** 核实结论:
- **原始数据: 能, 免费** —— ws diff-depth 全书维护 + aggTrade, 零 request weight(partial @depth20 只有
  20 档不够 25, 必须走全书)。
- **但真正的成本不是数据, 是 parity 面积**: 赢家 config 实测输入栈 = 25 档 npz_v4 + **ridge_features
  overlay + regime_prior + quantize** 三层离线工件 + norm。逐位复现到实盘 = 数周工程, 且 Tardis 史与
  live ws **无重叠期**(史至 2026-05-31) ⇒ 没有现成 ground truth 做 parity, 只能靠跨源容差实验。
  这正是本项目被反复咬的 train/serve skew 缺陷族。
- **EV 对照(诚实)**: B-1 上界 ≈ 当前换手 16k U/天 × 0.5-1bps 时机改善 ≈ **1-2 U/天**; 全轨只覆盖
  BTC(13 alt 无深档) ⇒ 只能经 β 投影 ⇒ 有界。**排不过 #46/#35/#33/#34 的任何一条。**

**处置**: ① 模型/serving 侧**全部推迟** —— 重启条件 = NAV 放大(上界∝换手) 或 #33 需要深档特征(共享
先决)。② 唯一现在做的 = **零风险隔离记录器**(独立进程/独立目录/与交易零交互, ~90MB/天压缩): 它是
将来任何微结构工作的数据期权, 且从第一天起定义"我们自己的流格式", 把跨源 parity 从"必须"变"可选"。
③ 全轨 kill-switch = 跨源 parity 小实验(故意简单的特征, Tardis 重建 vs ws 重建, 容差预写) —— 若连
简单特征都过不了, track B 整体死, 按用户判据不再花时间。
