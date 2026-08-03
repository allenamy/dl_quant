# STATE — 当前状态唯一真相源

> **本文件是【可变的当前快照】, 被【重写】而不是追加。** 历史记录在 `multi_asset/exports/live/pilot_journal/JOURNAL_<date>_*.md`(只追加)。
> **任何会话(含 team-lead 自己)在做任何判断之前, 先读本文件。**
> **最后核实:** 2026-08-03 15:45 UTC | **核实者:** team-lead (session 6737834a)

---

## 1. 我们在哪 (一句话)

**实盘试点 P0 第 3 天** —— 真钱 ~2,193 USDT, 107 个仓位, 4 小时锚点, 市场中性横截面书, Binance USDT 永续。**机器已证明能跑; alpha 尚未被证明存在**(13 个锚, t=0.92, 统计上与零不可区分)。

## 2. 线上配置 (改动它 = 改动真钱)

| 项 | 值 |
|---|---|
| 权益 / 敞口 | ~2,193 USDT / 2× 杠杆(gross ≈ 4,390) |
| 腿与权重 | king .5952 / s2 .2024 / funding .2024 / size **0.0**(已摘除, 键保留) |
| 部署模型 | `king_fold4.pt` `5a7b27d9…` ← `wideA_lamorth0_xattn_**5yr**/fold_4`; `s2_fold4.pt` `8b1bc1ab…` ← `wideA_s2_y24_5yr/fold_4` |
| sizing | **等金额**(波动缩放待部署) |
| 执行 | maker 阶梯 900s → k_cancel → taker 补单; 中性优先(C 政策) |
| 运行方式 | launchd `com.dlquant.live.anchor`, **工作树即运行目录 ⇒ 落盘即上线** |
| 锚点 | 00:00 / 04:00 / 08:00 / 12:00 / 16:00 / 20:00 UTC |

**实测基线(近 11 锚):** 成本名义加权 **+3.79 bps**(红线 6.93; 平静锚 +0.84 / 奔跑锚 +4.48) · 中性度 <1% · maker 成交率 63–93% · 守卫近 6 锚零触发。

## 3. 在飞任务 —— **每项必须有具名 owner**

| 任务 | owner | 状态 | 阻塞于 |
|---|---|---|---|
| 停机门接线(§4-5e/§4-6 拆分) | B3-wire | **已完成并入库 `d997767`**, 电池 108 全绿, team-lead 已逐行审 | — (16:00Z 锚生效) |
| 波动缩放 λ=1.0 | team-lead | **收益侧否决**(G2 在实盘口径失败); 实现完成待重批 | 只含风险判据的新预注册 |
| ΔNet 三口径污染检验 | C3-volcheck | **已全部交付**(主表/归因/红测/成本敏感性, SHA 5dddd205) | — |
| champion vs **lamorth0_5yr**(真对手, 受控A/B 唯一变量=attention) SERVE 对照 | C3-volcheck | 在跑, ETA 16:42Z | — |
| S1 干净面板 | B4-retrain | **已建成+161断言绿**(SHA e947df63) | — |
| S1 两架构重训 | B4-retrain | **训练中** PID 1121881, ETA run1≈18:50Z run2≈20:40Z | — |
| **0.079′(G1 及格线重测)** | B4-retrain | SERVE 面板 CPU 构建中; 推理排 S1 后(GPU 串行) | S1 完成 |
| 重训预注册 v5 收口 | C2-prereg | 押住待 C3 SHA | C3 对照落盘 |
| 追价实验(no_chase 臂) | 系统自跑 | 第 6 锚 | N\* ≈ 129 锚 ≈ 22 天 |
| 加金 10,000 | 用户 | **建议暂缓** | 干净口径盈亏平衡 2.504bps vs 实测成本区间跨它两侧 |

## 4. 已冻结 / 不得改动

- **`signal/panel_build.py:187` 的 `np.convolve(..., "same")`** —— 含 11h 未来但**实盘因末行截断收不到**; 改成因果版会使冻结模型 IC **0.079 → 0.041**(实测)。**唯一安全修复是重训。** 详见记忆 [[panel-lookahead-betaadj-ret24]]。
- 单资产代码 `src/` `configs/` —— 只 import 不改。
- share data 与 `/mnt/storage/btcusdt_copy_*` —— 一律只读。

## 5. 已知缺陷(登记在案, 未修)

| 缺陷 | 严重度 | 备注 |
|---|---|---|
| 面板前视 `betaadj_ret24` | **高** | 回测高估 ~1.7×; 实盘不受影响; 污染面判据见 journal §10 |
| `MANIFEST.json` 无 provenance 字段 | **中, 且随时间恶化** | 两个训练 run 目录一旦清理, 部署模型永久失去可追溯来源 |
| 名义额缓存无标记价 | 低 | 高波动名每锚一条 reconcile 误告警; 改存数量即可 |
| champion 选型可能被前视污染 | **待测** | 部署模型利用度 +0.25; SERVE 对照在跑(C3) |
| **5yr 训练配置无记录** | 中 | 架构可由 state_dict 形状精确复原, 折结构可由 te_rows 复原, 过程参数只能取默认+UNRECORDED 声明 |

## 6. 数字的口径纪律(引用时必须带)

| 数 | 口径 |
|---|---|
| 模型 IC **0.079** | **实盘实际拿到的** —— 对外只引这一档 |
| 模型 IC 0.135 | 回测展示, **含前视, 高估** |
| 实盘 rank-IC **+0.111** (t 2.54, n=10) | **Spearman**; 同批 **Pearson 仅 +0.003** —— P/S 分歧由尾部收益驱动, 必须并报 |
| vol-scaling ΔNet +1.814 | **已证伪**: 99.8% 是前视经 beta 择时兑现; 实盘口径 −0.083 |
| 基线书干净回测 | 净额缩水 94%; **盈亏平衡成本 2.504bps**; 书级 rank-IC 0.044(t 27, alpha 未归零) |
| 影子期盈亏 | **41–44% 来自前视** ⇒ 不得用于预期实盘 |

## 7. 关键文档

| 用途 | 路径 |
|---|---|
| **协作规则** | `docs/TEAM_PROTOCOL.md` |
| 项目宪法 | `CLAUDE.md` |
| 每日历史(只追加) | `multi_asset/exports/live/pilot_journal/JOURNAL_<date>_*.md` |
| 前视审计交接 | `multi_asset/exports/eda/HANDOFF_lookahead_audit_2026-08-03.md` (`95f804b1…`) |
| 追价实验预注册 | `multi_asset/exports/eda/PREREG_chase_opportunity_cost_2026-08-03.md` (`3a0f3d4f…`) |
