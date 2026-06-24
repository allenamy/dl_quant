# Multi-Asset y180 — CONCLUDED Milestone

> **创建:** 2026-06-15 07:30 UTC | **Session:** multi-asset autonomous push | **状态:** final | **作废条件:** 若引入新信息源(funding/OI)或新执行环境(rebate-maker <0.2bp)并重新打开 IC/经济结论。

## 一句话结论

多资产横截面 y180 研究+产品线 **以诚实负结果收口**:cross-sectional rank-IC 稳定在 **0.0744(信息天花板,非建模问题)**,且该信号 **net-of-cost 不可交易**(单笔毛边际 ~0.5 bps < 成本地板 ~3 bps;有统计显著性的净 Sharpe ≈ 0)。**成本主导,与单资产同结论。**

## 目标与方法论支点

- 目标:14 USDT-perp 同步 1s bar,预测每 symbol 未来收益,avg per-asset Pearson 0.10 / cross-sectional rank-IC。
- 核心 reframing:同期 BTC→alt beta 巨大(ETH 0.84,avg ~0.70);lagged 弱(~0.02)。⇒ beta-projection 白送 ~0.045/alt,模型真正要做的是 **residual alpha**(预测横截面残差 r_i = y_i − mean_j y_j)。
- 关键数学约束(整条线的支点):demean 把横截面**共同分量**切除,rank-IC 只看**跨资产差异**;任何 BTC→alt 的**共同**传导 = 被 demean 抹零,只有**差异化**信号能活。

## IC 轴结果(信息天花板 0.0744)

| 杠杆 | 实测 | 判决 |
|---|---|---|
| **RevIN**(per-asset 逐窗实例归一) | **+0.0040** | **唯一 PASS** → 0.0744 |
| 横截面 BTC 融合 — broadcast(DMF/DMF2 塔) | +0.002 | FAIL |
| 横截面 BTC 融合 — differential(regbias,attention-logit 重连) | −0.001 | FAIL |
| MTL 跨-horizon(借 y60 SNR) | +0.0001 | FAIL |
| 派生微结构特征扩容(microprice/Kyle/Roll/Stoikov…) | +0.0001(Ridge) | FAIL(与 44 维冗余) |
| SSL 预训练 / target 重设计 / 横截面新架构 / regime-MoE | — | workflow 逐条否决(见下) |

- **GBDT ≈ DL ≈ Ridge** 都收在 0.0744 → 信息天花板,非建模失败。
- 横截面差异化部分实测**死**:lead-lag null,残差 AC(1)≈−0.02,~1min 后均值回归。
- **过程中抓出并修复一个真 bug**:zero-init 标量门(`dmf_alpha`)乘整个融合子网 → 子网梯度饥饿、early-stop 前学不动;改非零初始化后梯度恢复,但塔仍 FAIL → 证实是信号缺失而非 bug。

### 19-agent breakthrough workflow 否决的大杠杆
- **SSL**:根因是 inference-time map-drift(在线问题),离线目标(含 P1raw,已 FAIL)治不了。
- **y60 frontier**:成本不变幻象 —— IC·σ 跨 horizon 持平(0.51/0.54/0.66 bps @y60/180/600),y60 IC 高 63% 被 σ 缩小精确抵消,零净边际。
- **横截面新架构**:最被证伪的轴(bilinear/regbias/EPNet/multipool/market_token 全 NEG);N=14 时 14×14 attn 已覆盖 pairwise。
- **regime-MoE**:Phase B 三次证伪;calm-tape edge 只 conditional on 未来 |y|,因果门看不到。
- **target 重设计**:LambdaRankIC 已是部署的主 loss。

## 经济轴结果(不可交易,3 个独立角度)

1. **通用 sweep**(`_hfecon_prod.py`):全 rebal 灾难(−408..−2650 bps/天);最佳节流配置(滞回 λ0.97/band0.10 @VIP-maker ≤0.5bp)= +4.1 bps/天、Sharpe 2.51,**但 CI 含 0、2/3 折、0.6 笔/天** → 非可部署 edge。
2. **用户点名策略**(`_hfecon_tail.py`,240 配置:L/S+尾部幅度带+min-hold+反转平仓+单边):**480 cell 无一个 95% Sharpe CI 排除 0**;唯一净正角落 = 单边做空的市场 drift(beta,非 alpha)。**有显著性的净 alpha-Sharpe ≈ 0。**
3. **y60 frontier**:用 IC·σ 算术正式关闭(成本不变)。

## 唯一未测的 IC 杠杆(deferred)
**funding / OI / liquidation 的 per-asset 差异化数据** —— 唯一 LOB 之外的新信息源,~12% 突破胜率,需多 symbol Tardis 拉数;风险 = 去杠杆 regime 下是共同因子(被 demean 切掉),且 F2 已挖 liquidation toxicity。若试:先 60-90 天便宜 Ridge probe 把门。

## 关键产出 / 工具
- 模型:`multi_asset/model/temporal_spatial_panel.py`(per-asset Conformer+RevIN + cross-asset attn + DAQH;含 dmf/dmf2/regbias/MTL flags,均已 FAIL-park)。
- 经济:`multi_asset/eda/_hfecon_prod.py` / `_hfecon_tail.py`(+ JSON 全 sweep,最佳配置已存,留给未来 sub-0.2bp / rebate-maker venue)。
- 数据:`btc25_raw_perp`(25 档 perp ladder)、`btc_feat64_perp`(REG_arch 64 特征在修正 perp 上,leak-free,487 天)、`btc_trade_perp`(12 trade feat)。
- 滚动日志:`multi_asset/exports/OVERNIGHT_PROGRESS_2026_05_20.md`(全部实验逐条 verdict)。
- memory:`multi_asset_y180_concluded`、`multi_asset_btc_hardest_residual`、`multi_asset_temporal_spatial_pivot_2026_06_09`。

## 要让它净正且显著,只有两条超-setup 的路
1. **更低费率**:rebate-maker / 做市返佣,把成本地板压到 <0.2 bp/side。
2. **新信息源**:funding/OI/liquidation 差异化数据(抬 IC / 单笔边际)。
