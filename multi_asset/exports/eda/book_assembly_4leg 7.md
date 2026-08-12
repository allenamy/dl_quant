> **创建:** 2026-07-14 | **Session:** 0C 四腿装配 | **状态:** final | **作废条件:** 部署实现变更或腿收益口径重建

# 四腿书装配 — S2 正式进书 (0C)

**判词: S2 正式进书(四腿)。加 S2 在所有指标上改善三腿书 —— Sharpe↑、最差月↑、最差年(2026H1)保护兑现。** 前置 G2 PASS(seed-robust)+ 5yr(regime-robust)全过。

腿 = funding(mega-cap raw crowding-reversion,net@2bps)/ **DL-king**(xattn 王 4h,net@5bps,替换旧 QIM)/ SIZE(宽 size sleeve,tiered)/ **S2-24h**(5yr fold 预测,24h rank-L/S net@5bps)。全对齐日净收益(book_assembly v2 口径),风险归一化。联合窗 2022-01→2026-06(1641d)。

## 腿间相关(重点 S2)

- **S2↔king = 0.224**(24h vs 4h,低)。
- **S2↔SIZE = 0.002**(近零)。
- ⇒ S2 是真·第四分散腿;**全书中对所有腿低相关使其无歧义加项**(不同于成对 king-blend 的方向-不显著 —— 多腿语境才兑现分散价值)。

## 三腿 vs 四腿(风险归一化,等风险基)

| 组合 | Sharpe | 最差月 | 2026H1 Sh |
|--|--|--|--|
| 三腿等风险 | 6.60 | −2.84 | 5.91 |
| 四腿 S2 w0.05 | 6.87 | −2.63 | 6.30 |
| **四腿 S2 w0.10** | **7.10** | **−2.42** | **6.61** |
| 四腿 S2 w0.15 | 7.27 | −2.20 | 6.83 |
| 四腿 inverse-vol | 5.89 | −2.30 | 6.55 |

**Sharpe 随 S2 权重单调升(6.60→7.27),最差月单调改善(−2.84→−2.20),最差年 2026H1 逐步抬(5.91→6.83)。** ★**最差年保护兑现: S2 抬王座弱书年 2026H1。** inverse-vol(5.89)欠配 king → 不推荐。

## 终版四腿权重建议

- **S2 风险预算 ~0.10**(平衡默认;单 24h DL 因子独立 Sharpe 4.16 中等,勿过度 tilt)。
- 三核心腿保 book_assembly v2 比例(**DL-king 0.35-0.40 / funding ~0.28 / SIZE ~0.28**)缩放到 0.90。
- **敏感性 w0.05-0.15 全改善**;0.10 基准,0.15 激进上界。用风险预算+king-tilt,非 inverse-vol。

## caveat

腿 Sharpe 信号级(无摩擦膨胀,尤其快 king);**决策靠 corr 结构 + 最差年保护 + 单调书改善(口径-稳健),非 Sharpe 量级**。S2 是**分散 sleeve**(真 regime+seed-robust 增量,护 2022/2026),非 Sharpe headline。

---
**产物:** `book_assembly_4leg.json` · `book_assembly_4leg_raw.json` · `build_4leg.py`(可复算)
