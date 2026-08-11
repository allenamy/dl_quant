# DESIGN — metrics 特征族 v2(深设计, 法证驱动)

> **创建:** 2026-08-07 15:4x UTC | **Session:** multi-asset-v2 主线 | **状态:** in-progress
> **作废条件:** v2 特征集过门并入面板后, 本文转 final; 若 v2 整族被拒, 标 superseded
> 依据: 用户刚性要求(动手前深设计) + `forensics.log` 八项实测(RunPod, 2026-08-07)。
> v1(21 特征快版)已产出侦察读数(Ridge 0.0321 / DL 0.017), **v1 不作废但不再演进**;
> 采纳决定只看 v2。

## 1. 六个原始量的语义(法证核实, 非文档转述)

| 列 | 语义 | 法证 |
|---|---|---|
| sum_open_interest | 全市场未平仓量, **币本位** | F4: oi_value/oi 隐含价逐年吻合 BTC 价 ✓ |
| sum_open_interest_value | 同, **USDT 本位** | 同上 |
| count_toptrader_long_short_ratio | 头部账户(前20%保证金)多空比, **按账户数** | 15% 历史缺失(晚上线), F2 需 dropna 重测 |
| sum_toptrader_long_short_ratio | 头部账户多空比, **按持仓量** | 同上; 与 count 的分歧 sd≈0.4, AR1≈0.997 |
| count_long_short_ratio | 全市场多空比, 按账户数(散户情绪 proxy) | 缺失 ~1% |
| sum_taker_long_short_vol_ratio | 窗口内主动买/卖量比 | ★F5: 与 klines 推导 corr 仅 0.757 ⇒ 非重复列 |

## 2. 法证结论 → 设计决定(逐条挂钩)

| 法证 | 数字 | 设计决定 |
|---|---|---|
| F1 帧规整 | 300s 占 >99.9%, 重复戳 2/90d | 小时聚合安全; 重复戳 keep-last |
| F2 count vs sum | corr=nan(脚本 bug) | **待重测**; 分歧轴(集中度)仅在 corr<0.9 时进 v2 |
| F3 分布 | taker raw skew +4.93 → log 0.00 | **四个 ratio 全走 log 域**再算描述子 |
| F4 单位 | 隐含价吻合 | oi(币本位)不可跨币比; **强度化后才进横截面** |
| F5 与 klines 重叠 | corr 0.757 | taker 族保留 mean(24% 新息) + std/slope(全新) |
| F6 覆盖 | 44 起 >3 天成块缺口 | 端点缺失自然 NaN; 不 ffill 跨缺口 |
| F7 OI 跳变 | BTC 532 起, 最大 3246% | **跳变守卫: \|Δlog\|>0.5/5min 判伪迹 → NaN** |
| F8 四象限 | 续/续/衰/弹 = +0.83/−1.12/−1.00/+0.42 bps | **交互项进 v2**(拆开动量/回归两机制) |

## 3. v2 特征规格(~26 列, 全部滞后 1h, 构造期断言)

**基变换**: ratio→log; OI→两个口径: `oi_lvl` = log(oi_value / roll30d_mean(oi_value))(自身水平),
`oi_int` = log(oi_value / roll24h(quote_vol))(持仓强度 —— 高 OI/低流量 = 拥挤且难解).

**每小时描述子**(在已 log/强度化的序列上):
1. 六量 × {mean, std, slope} 中保留有法证支撑的 14 列:
   oi_lvl_{m,s}, oi_int_{m,s}, tt_cnt_{m,s}, tt_sum_{m,s}, glb_cnt_{m,s}, taker_{m,s,slope}, oi_slope
2. **变化率(跳变守卫后)**: doi_1h, doi_24h (log, \|Δ\|>0.5 → NaN)
3. **★ 交互(F8 机制)**: `doi_x_ret1` = doi_1h × sign(ret_1h_kline), `doi_x_ret24` = doi_24h × sign(ret_24h)
   —— 正值=主动建仓(动量), 负值=被动平仓(回归); 连续积保留幅度信息
4. **分歧轴(条件进入, 等 F2 重测)**: `tt_div` = log(sum_ratio) − log(count_ratio)(头部集中度),
   `elite_div` = log(tt_cnt) − log(glb_cnt)(精英 vs 散户)
5. 价格条件字段用 **klines close**(独立源), 不用 metrics 内字段 —— 避免同源伪相关

**归一化**: 面板装配时逐时刻 xsec rank-z(与 v1 同, 天然因果)。
**弃选与理由**: 末值(v1 前实测 IC 反号); 六量全量 mean/std/slope 18 列全保(v1 做法 —— slope 除 taker 外
IC≤0.004, F 检验不支持占列); 高阶交互(先过一阶的门)。

## 4. 预写判据(v2 采纳门, 与 T0 对标)

- G1 \|IC vs 未来24h\| < 0.15 全列; G1b 时移不对称无一例
- Ridge 逐年走前: 均值 ≥ v1 的 0.0321(v2 若不如快版 v1, 深设计就是负价值 —— 这条会红)
- PR: 加入后必须上升; 与 32ch 最大 \|corr\| < 0.8
- DL 增量(接 T0): 在 32+book+basis 的最终面板上, v2 替换 v1 的 Δresid ≥ 0 且不伤坏锚地板

## 5. 开放项

- F2 重测(dropna 后 corr) → 决定分歧轴去留
- F7 跳变的**根因抽检**(3 起最大跳变的原始帧人工看) —— 区分归档伪迹 vs 交易所重置
- rb32 vs jpline −18% 差距: baseline8 到齐后逐列 corr 判别(种子噪声 vs 构造残差)

---

# 附: DESIGN — 门控双塔融合 (E10 治疗①, 2026-08-07 16:4x Z)

**机制**: metrics(持仓状态, 5min 源, AR1 0.94-1.0 慢量)与价量(1h 快量)动力学不同源。
扁平拼接把 21 条慢通道塞进同一 input_proj, 稀释共享编码器几何(E11 三种子实测 −0.0135)。
族塔给每族独立表示空间; 门控让模型**学**何时采信 metrics —— 塔 B 输入全零(缺失纪元)时
gate 可学会关闭, 与存在掩码臂互补(两治疗可叠加)。

**数据法证**: 尺度冲突实测(rank-z 有界 sd0.66 vs raw 1e-4~15, 千倍差 = E7 嫌疑②);
AR1≈1 ⇒ 塔 B 不需深时序容量, 因果 depthwise conv(k=24) 足够。

**备选弃选**: cross-attn 融合(参数×4, 单族时≈门控加法软版, 不值);
每族独立 xattn(破坏 harness xattn 槽, 大改); FiLM(语义是"调制"而 metrics 是"加信息",
FiLM 留给 E 阶段 regime 门控)。

**构造**: `FusionTwoTowerEncoder(n_feat=53, split=32)`:
xA=x[...,:32]→SharedTemporalEncoder(d=64, 与 rb32 同容量); xB=x[...,32:]→Linear(21→32)
→causal depthwise Conv1d(k=24)→GELU→last-token→Linear(32→64);
gate=sigmoid(MLP([hA;hB]→32→1)) 逐币标量; **h = hA + α·gate·hB, α 零初始化**
⇒ init 时函数≡纯塔A(结构等价 rb32 = 内置消融)。增参 ~25k。

**判据(预写)**: vs rb32_s42(0.0387): Δresid ≥ +0.003 逐折不反号; 且 ≥ ch53+0.010
(塔式必须显著优于拼接); σŷ/σy≥0.02; seed 2027 同向复现。
不过门 ⇒ 融合假说降级, 主攻转 v2 特征质量。
