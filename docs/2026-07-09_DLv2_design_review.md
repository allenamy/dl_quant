# DL v2 设计评审 — 6 轴调研 × 工程实证 × 验收协议 → 分批测试计划

> **创建:** 2026-07-09 | **状态:** final (评审结论, 批次待执行) | **输入:** 6 轴 web 调研(每轴带来源+置信标签) + 0B 工程 memo(on-disk 实证) + 0C 验收协议(9328d3f 预注册)
> **作废条件:** 批次结果落地后由结果文档取代

## 0. 统领性结论 — "horizon 法则"决定一切

**瞬时盘口信号活在秒级（~2 个价格变动），只有 持久化/聚合/滞后 变换存活到 1-2h。**（axis-1/5 文献一致 + 我们自己 OBI-snapshot/快微结构历史）DL v2 的每个设计都以此过滤。

## 1. 六轴判决汇总

| 轴 | 采纳（过滤后） | 拒绝（带理由存档） |
|---|---|---|
| **1 raw book** | 平稳流变换: 多档 OFI 梯子 / PCA 积分 OFI(唯一有 5-10min 证据) / volume-at-distance(9桶深度重塑) → 先 Ridge 门, 过了才建 <10K 参数小 stem | DeepLOB/TransLOB/HLOB/消息级模型全家(事件级 horizon 错配 100-1000×; 加密复现: 简单模型+对输入 ≥ 深网) |
| **2 特征交叉** | **SE-gate 一项**(44 通道逐窗重加权, ~600 参数, REPLACE 式避 #29; 状态条件化=GBDT 静态交叉做不到的唯一机制; 低先验快证伪) | DCN/FiBiNET/FinalMLP 全家(CTR-表格, GBDT 已挖尽该机制); 通道混合注意力(小变量低SNR 反适配, PatchTST 后共识) |
| **3 regime** | (a) **在线统计/检查点混合适应**(OneNet-lite: 冠军+近期重训副本, 输出 value-blend 按滚动实盘 rank-IC 加权 —— 唯一有复现 OOS-drift 证据的杠杆, 且=我们生产计划的形式化) (b) 线性慢上下文分支(先 Ridge 门, 非 Mamba) (c) 保持 MAD/RevIN 不动(自适应归一在重尾上输给固定稳健法, avg rank 2.08 vs 4.17) | MoE 路由(router collapse+专家海市蜃楼=我们 causal-router 失败的泛化)/离散 regime-FiLM/MAML(全部=我们的负结果被文献重述) |
| **4 跨资产 N=14** | (a) **市场-token 状态门控**(MASTER 的门控子模块, O(d) 与 N 无关; g_t=[BTC 状态,截面 dispersion,市场 vol] FiLM 每资产 stem —— ★与 axis-3 张力的和解: 失败的是单资产 level-调制, 未测的是截面状态调制相对排序, 一次预注册测试+G4 强月 kill) (b) 条件时变 β(GKX/IPCA 子机制: β_i,t=f(资产状态), 偷机制不搬全套) (c) seesaw 负 lead-lag(大币负向预测小币, **加密+我们尺度验证**但日/周频 — 便宜 Ridge 证伪 1-2h) | HIST/ADGAT/深图栈(要几百资产); FactorVAE 全套(N=14 塌缩成 beta-projection 重推导; VAE+低SNR=不稳定磁铁) |
| **5 对抗/博弈** | (a) **分解 OFI**(主动 taker vs 被动 add/del —— ICAIF 2023 证据, 用上我们从未用的 add/del 数据) (b) **滞后跨资产 OFI**(Cont: 同期无增量但滞后版预测未来 —— 唯一 horizon-耐受跨截面流杠杆) (c) VPIN/passive-fill markout 只作 regime/风险门(Andersen-Bondarenko 混淆批判) (d) 潜空间 FGSM 正则器(便宜低期望旋钮) | 对抗双塔(零预测证据); GAN/扩散增广(零 OOS 收益证据); **LOB SSL 预训练降级**(零收益预测 OOS 证据+我们 params:sample 已健康) |
| **6 损失** | (a) **LambdaRankIC 成对代理**(w 0.1-0.3, 多时刻 batch —— 最强 OOS 证据: +30% IC vs RankNet, train-test gap 稳定=反 #15 drift; ⚠先验代码核对: 我们的 rank 项已名为 lambda_rank_ic, 若已实现则测试塌缩为权重/batching 调整) (b) 3-分位非交叉头(DAQH 已有, 校验配置) (c) Kendall-Gal 不确定度自动加权(带 clamp 防 rank 升主) | 可微 Sharpe(小 universe seed-不稳定, t≈2 过不了 Bonferroni); 换手-入-损失(后处理成本完胜=Path-C 先验确认); batch-IC 主损失(Numerai 实盘塌缩); DPO 排序(纯炒作); 纯 listwise(N=14 无优势) |

## 2. 与 0B 工程 memo 的交汇（on-disk 现实）
- **最大数据缺口 = add/del 博弈**: 4 原始通道被压成 1 个双重净额标量(高churn幌骗盘 vs 安静盘不可分) —— 恰与 axis-5 分解-OFI 会师 = Batch-0 核心;
- **18 个 gated 臂已在代码里**(bilinear/EPNet/raw-path/BTC25/DMF/coarse/multipool/MTL, 全零初始化 off=bit-identical) —— v2 = 激活+审计+过门, 非写新架构;
- RevIN 在 panel 模型里其实从未构建(只是 LayerNorm) — axis-3 说保持现状恰好成立;
- 487 天生产窗口 Xraw 完好 → raw 实验零磁盘代价; 历史扩展(+70GB)仅在臂过门后。

## 3. 批次计划（0C 协议锁定: 五关 vs 现 book + G1σ/G2 seed-median/G3 每面泄漏审计/G4 强月 kill）

**BATCH-0 — CPU Ridge 前置门（无 GPU, panel 重建后即跑）:**
- B0a 流家族通道: 多档 OFI 梯 + 积分 OFI + volume-at-distance + **分解主动/被动 OFI** + **add/del churn 统计**(强度/撤挂比/边不对称/扫后补充) + 多半衰期 EMA 持久化;
- B0b 滞后跨资产流 + seesaw 滞后大币收益(多 lag);
- B0c 线性慢上下文特征(4-8h 描述子);
- B0d 市场状态向量 g_t 交互项。
门: ΔP≥+0.005, per-fold 符号一致, shuffle-future null。**过门者才挣 GPU 臂。**

**BATCH-1 — GPU 最便宜臂（M0 回放释放 GPU 后）:**
L1 LambdaRankIC 核对/升级 + w{0.1→0.3} + 多时刻 batch; L2 分位头配置 + Kendall-Gal(clamp); A1 SE-gate(600 参数); (选)潜空间 FGSM。

**BATCH-2 — GPU 条件臂（依 Batch-0 过门情况）:**
平稳-book 小 stem(<10K, 只吃过门通道); 截面状态门控(市场-token FiLM, **G4 强月 kill 预注册**); 条件 β 头。

**BATCH-3 — 生产侧（非架构）:**
OneNet-lite 冠军/挑战者输出混合(滚动实盘 rank-IC 加权, value-blend 非 rank-blend #16)。

## 4. 纪律
每批预注册读数; 单臂可归因; gated off=bit-identical 验证; 双人(0B 建/0C 判); GPU 串行(回放优先); 所有 reject 存档防重测。

## 4b. Batch-0 结果(滚动)
**B0b(滞后跨资产流)/B0c(慢上下文) = FAIL (2026-07-10):** ΔP +0.0015/−0.0017, 符号不一致 —— Cont 滞后杠杆在我们数据死, horizon 法则再胜。
**★ B0d(市场状态交互) = 审计后大幅降级 (2026-07-10):** headline ΔP +0.036(7×门)过了 shuffle-z 13/α-稳健/因果检查(无泄漏), **但 ~86% 是市场择时**: 主导项 = 市值加权市场收益×资产收益(市场自身反转预测, per-asset Pearson 奖励 beta 择时)。**部署指标(截面 rank-IC, 美元中性)下 Δ 塌到 +0.0049** —— 真实但温和, 勉强过 +0.003 门。Batch-2 FiLM 臂仅边际正当(追 +0.005 非 +0.036), G4 kill 预注册不变。**方法论修复: Ridge 门指标 per-asset Pearson → 截面 rank-IC(奖励市场择时=错误指标, 已换 75d4fd4); B0a/b/c FAIL 依旧成立(错误指标上都没过, 正确指标只会更差)。**
**L1(w_rank 0.3) = 趋向 REJECT (2026-07-10):** 3 fold IC-IR 2.5-3.4(M0 是 7+), fold0 单调转负 —— #15 应验, 加重 rank 权重伤质量。0C 正式判决中。
**B0a(own-book 流家族) = FAIL (2026-07-09):** baseline 44-feat cleanP +0.0235; ladder ΔP +0.0001/decomposed +0.0005/depth +0.0001/churn +0.0002/all_new +0.0008 « +0.005 门, shuffle-z 0.31, fold 符号不一致。**own-book 平稳变换(多档 OFI/分解/深度形态/add-del churn)在 1h 无增量 —— horizon 法则的预期结果, Ridge 门以 ~零成本关闭 own-book 轴, raw-book 小 stem 不获 GPU 槽。** B0b(滞后跨资产 OFI+seesaw, Cont 唯一 horizon-耐受杠杆)/B0c/B0d 待测。

## 5. 证据置信 caveat
部分承重主张为单源(Kolm 数值幅度 SSRN 403/Cont 跨影响 abstract-vs-PDF 分歧/seesaw 频率未核/2026 新 paper abstract 级)。**Batch-0 的 Ridge 前置门中和了这一风险: 我们不按引文行动, 按自己数据的门行动 —— 文献只决定"试哪些通道", 门决定"哪些是真的"。**
