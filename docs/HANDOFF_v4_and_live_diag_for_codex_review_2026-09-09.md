> **创建:** 2026-09-09 10:4xZ | **Session:** 续 b9646a9e | **状态:** 交独立研究员复审 | **范围:** ① 口径 v4 链全量重训与量化(含三处我方错误的定因与修正); ② 实盘回吐根因拆解 | **实盘:** 零接触; 换装等复审后由用户决定

# HANDOFF · v4 链 + 实盘根因拆解 · 给独立研究员复审

## A. 提交清单(研究仓 multi-asset-v2, 时间序)
| 提交 | 内容 |
|---|---|
| 493e9ef4 | CALIBER_STATUS 账本(缺陷三栏) |
| 61af466b | PREREG v4 链(判据冻结先于数字; §3 换装规则) |
| ac2d8e6a | AMD1: 轴+6 锚 / 噪声带 / 成员 NaN 规则 / 20 折 / 原始记账免校正 |
| f99ca64e | AMD2: 守卫红 = 导出漏 EXPORT_PANEL/EMA_STATE_JSON; v3 复现 2.284/1.024 逐腿逐位 |
| 59a4860d | AMD3: fea89 门字面 FAIL → trend_288 全局累积和残差受据 → 修订读法 |
| 5749a821 | 装置+收据入库(门 1/2/守卫/对账/判官/队列) |
| 7421ea29 · a28a9e10 | RESULT 进行中: 链定义/门读数/A0 逐年表/refit V1 |
| 05dd5464 | AMD4: 扩展窗次级读数 |
| 32060a3f · a7d497d3 · e586cbed | 首轮 A1/A2 s42(后作废); V3′ 谱塌缩发现 |
| 3f058a7c | **AMD5: legs 文件缺陷(全行重算 WL ⇒ 2023 king 席位≈0)定因(D2/D3 单折)与修正, 首轮四链+refit 作废重跑** |
| 9da34ebf · 92c1a9dd · f281a44f · 662b2b90 | legs v4b 重跑: 主判双种子 (C); 十格全 (C); RESULT final |
| 47ffc514 | combo 84 锚前向门二读(① 不过 ② 未否决) |
| a8b1ef4c | RUNBOOK_2026-10 §v4 正典配方 + 根因装置 |
| (本提交) | DIAG 实盘根因 + 本 HANDOFF |
装置与收据: `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`(脚本 + receipts/*.json + v4_commands.txt 逐字命令); 实盘装置 `multi_asset/exports/live/pilot_journal/tools/`。

## B. 请重点复审的点
1. **legs 策略**(AMD5): 「在役 legs 行逐位原样 + 新锚同公式」是否是正确的正典? 替代 = 用有 2022+ 覆盖的 king 史重算 WL(需 hist king)。D2/D3 单折受据在 `receipts/diag_202507.json`。
2. **V3′ 条款② 参照代改为同配方月折**(AMD6, 明写事后): 是否接受; 对年折的 k−2/k−3 差 0.06–0.10 是否有别的解释。
3. **fea89 trend_288 残差读法**(AMD3): 全局累积和特征对数据编辑的永久记忆, 是否应改造 f8 构建器(局部窗口重算)而不是放宽门。
4. **十格全 (C) 的解读**: 「正确口径全量重训与在役形态不可区分」是否成立; 是否需要第三种子或更长窗。
5. **实盘根因**(DIAG 文档): 多空两半各 ≈ ±1× 山寨指数、书净 β≈0、亏损 = 急涨里多头半区跑输 + 单名崩 + FTRIM 残留暴露 — 请复算 §1 分解(装置只读, positions×mid)与 §2 回放桶; 候选 C1(regime 门提速)/C3(FTRIM 硬出场)是否值得预注册。
6. 未做: V4 跨机门(jpline 不可达); bundle `generation` 标签; 十月 RUNBOOK §v4 尚未实跑。
