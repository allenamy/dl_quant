> **创建:** 2026-09-12 08:0xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 用户三问的状态书(结论/生效/差因); 每个数字带收据路径与提交; 供独立研究员 double check | **作废条件:** 08Z 首锚验收结果、研究员复核、任一裁定落地后按行更新

# 三问状态书 —— 结论与行动 · 版本生效核对 · 实盘差因与正确口径水平

**读法**: 所有回放数字 = v4 口径钉(`uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`, 8608cd4d): holefix2 5m 缓存 / 记账 y4 = Π(1+r)−1 原始收益(meta_newprod_v4)/ 拟合成本 `costb_PWR_G230k.json` 295b4e7b / g = net_ex/gross_total bps/锚/单位 gross / UTC 日块自举 CI95 / 主窗 W_ALPHA n=9138(丢暖机 900 锚, ≤2026-08-30 20Z)。**禁用**: dlw_ext/_ext 谱系、pod_fea_ext.py(未 clamp)、裁剪复利(E-0908-B)、shadow_bundle_v3 研究副本、W_TAIL 阶梯(r18 作废)、从缓存 ret5 重算收益(r18 规则)。

---

## Q1 · 十四轮 + 复测(r17–r21)+ 研究员复审与建议 —— 结论与行动

### 1.1 重大问题 · 已修并已在实盘生效(今天之前是"修了没上", 今天全部上线)
| # | 问题 | 修复 | 实盘提交 | 生效 |
|---|---|---|---|---|
| 1 | 场所不应答杀锚 → 孤儿单(E-0909-D) | 请求相/应答相分相有界重发, 幂等 = 动词×相位 | `d040c74`(09-09) | 09-09 14:07Z 起 |
| 2 | 执行器 15 轮复审(b0a573a1 → b681ca5): 逐请求账本 / 身份门 / UNKNOWN 语义 / 金额三态 / 撤单合并 / 熔断先记账 | 27 文件 +5098/−280 | `b681ca5`(09-11) | **09-12 06:05:30Z**(ff-merge 钉 sha; 收据 `docs/ACCEPTANCE_b681ca5_2026-09-12.md`) |
| 3 | 收入账本孪生行去重键过粗(E-0909-H): 手续费少记一半 | 键 = (tranId, incomeType, symbol, asset) | `e1c4c87` ∈ b681ca5 | 同上 |
| 4 | −2027 场所仓位上限每锚重发同一被拒增量(PIEVERSEUSDT ≈2.1–2.2kU/锚, 09-08 起)(E-0909-E) | 规划期按 maxNotionalValue 有限上限截断 | `961a858` ∈ b681ca5 | 同上; **08Z 首锚验收看残差是否归零** |
| 5 | 场所账户级量化规则锁 −4400 后仍狂发(E-0910-A, 09-10 00Z / 09-11 08Z) | 同循环首拒后不发, 记 `skipped_venue_lock`; 按相位分页 | `3ff5e00` ∈ b681ca5 | 同上 |
| 6 | 账本字段被变量名碰撞静默清空三天(E-0908-A) | anchor_loop 修 | `64c4a16`(09-08) | 09-08 起 |
| 7 | 电池红在账本事实上挡住 safe_commit | 尺子按事实重标(VENUE-LOCKED 类 / −2027 分母 target / 自愿从行求和; 不放宽) | `77d9baf`(09-12, 仅测试) | 07:49Z; 电池 132/132 |

### 1.2 需要你动作的"立即"项(运维裁定域, 不是研究)
1. **BNB 手续费抵扣断了 6 天(09-07 起)**: 每锚 maker 恰 2.0000 / taker 恰 5.0000 bps, commission 全 USDT, 账户在 VIP0 底档。r11 定价 ≈ **+1.5% NAV/年**, 零研究风险, 是全部研究里唯一"可直接入账"的项(POSITIVE_FINDINGS 一句话总账已把 +5.29% 撤回到只剩这一项)。动作: 恢复 BNB 抵扣(充 BNB / 开抵扣开关)。
2. **杠杆 2.0× 与停机门**: 修后全史真 maxDD 阶梯(r18 NW, 原始回放波动)2.0×: maxDD −44%, 停机 **1.09–1.31 次/年**, 最差日 −6.4%; ≤10%·≤1 停机门下可行 L = **1.50**(原始波动)/ **0.88**(×1.4042 敏感性, 非事实)。你说的"两周多次停机": 42 天里**真实**击穿 −4% 线 1 次(08-21 是口径缺陷, 09-09 是账本缺口 E-0909-G 触发看门狗)。降不降杠杆是裁定(DOCKET #2 risk_scale 暂不部署)。
3. **生产者 paper 计分器**自 08-26 起在给已退役的 3 腿 king 书计分(combo_stage 从不写 aux.json)⇒ 监控"IC 转负"告警有一部分在读错书。修复 = 改生产者(非 git, 需换装事件), 登记待办。

### 1.3 研究结论(白话)
- **目标"跨 regime 夏普显著 > 3.0"未达成, 且从未被任何测量支持**: 冻结窗(2025-03..2026-08-10, n=3168)Sharpe 2.9357 自身 CI95 **[1.31, 4.57]**; 2026 年内(n=1452)4.52(SE 1.23); 全周期 1.29。要"CI 下界过 3.0"需点估计 3.97, 距现书 5.2 SE; Sharpe 预算(8ba85e15): 完美择时上限 2.21, 到 3.0 要再加 ~2 本不相关、各 Sharpe 1.5 的书。
- **~300 条候选 + r8–r21 零录取**(判据 (A) 双种子 CI 下界 > 0)。有正效但不显著的: CEM_99 carry 紧急处置 +0.038 [−0.005, +0.085](零假设重匹配后仍胜 6/6); 更慢的平滑角落(0.05, 2.5e-4)在共同可行 L=0.88 上中位 1 年 +8.2% vs 在役 +0.3%(点估计, Δg CI 含零); Amihud sleeve 是方差削减不是 alpha(亏损格 ρ +0.374/+0.369, 一起亏); 仓位级 FTRIM +0.018(CI 含零)。
- **被正确口径关掉的**: 腿层净额席位(REJECT, 过罚 2.6×); 非对称带(带在进场侧净赚); FTRIM 泄漏修复零和; 加速平滑有害(对称); 成本模型"偏便宜 3.2×"(同事件同价格钟无分量支持); "退出腿只成交 65%"(撤回, 意图组 0.91); "真因是波动率"(同期配对比 0.656); "数学上关不上"(撤回)。
- **研究员并行建议的处置**: GRU/MLP 相对排序 —— 46 配置零费用亦负、输给 ZERO ⇒ 不推进; OI 776 币采集 —— 唯一在建新信息源, 按来源时间规则, OI 轴弱关闭待其对齐检查; 4h 目标 t+5→t+245 —— 请先与钉住 y4s=[E+1,E+48] 比对(可能同一对象); FIRST30 真实库存现金回放 —— 请固化为常备仪器; 资金费方向/席位只看价格 —— 已测(v4 上 REJECT; 席位对燃料表盲 = 风险登记); 半衰期 26.3h 停滞 —— 与"更慢更好"点估计一致, 不支持加速。

### 1.4 能"尽快准备换装"的东西 —— 没有一条过录取线; 可准备的按顺序
1. BNB 抵扣(运维, 上面 1.2-1)。
2. **CEM_99**(carry 紧急处置)作预注册影子臂: 需先裁定出口门(PROPOSED2 v2 门 d63f4ec3, r20)与 NW 基线, 再走影子 + 首锚验收 + 用户字。
3. **Amihud 第四腿整书回放**(统一仓位 + 联合成本), 作分散化候选(不是 alpha)。
4. **exec 口径回放**(`build_y4_alt.py` meta_exec25: 按 E+24m 价格执行 Δw), 把 24 分钟执行钟装进回放 —— 这是缩小"回放 vs 实盘书构造 +2.70"的正确实验。
5. 裁定: N2/暖机修法是否换钉 `w10_sleeve.py`; NW 取代 A0 为基线; 缓存 ret5 裁剪规则进 CALIBER_PIN。

---

## Q2 · 09-08 以来的修复是否都生效 —— 逐层核对(给研究员 double check)

### 2.1 执行器 `~/dl_quant_live`(git; 远端 github.com/allenamy/dl_quant_live main)
| 提交 | 内容 | 部署时刻(reflog) |
|---|---|---|
| `64c4a16` 09-08 | E-0908-A 变量名碰撞 | 09-08 06:42Z |
| `d040c74` 09-09 | E-0909-D 传输韧性 | 09-09 14:07Z |
| `961a858`→`b681ca5` 09-09..09-11(19 提交) | 复审 15 轮: E-0909-E 截断 / E-0909-H 去重 / E-0910-A 熔断 / 逐请求账本 / 身份门 / UNKNOWN / 金额三态 / 撤单合并 / 读者(neutrality 已测口径, chase_readout 已测桶) | **09-12 06:05:30Z**(ff-merge) |
| `77d9baf` 09-12 | tests_disposition_matrix 重标定(仅测试) | 09-12 07:49Z(safe_commit) |
**验证**: `git -C ~/dl_quant_live rev-parse HEAD origin/main`(两行 = 77d9baf…); `git -C ~/dl_quant_live reflog --date=iso | head -3`; `git -C ~/dl_quant_live diff --stat d040c74 b681ca5 | tail -1`(27 files, +5098 −280); 电池 `~/dl_quant_live/state/acceptance/20260912T073458Z_*.log` 132 套全 exit 0; 部署验收 `docs/ACCEPTANCE_b681ca5_2026-09-12.{md,json}`。**首锚验收 = 08Z 锚**(RUNBOOK §3 六条 + −2027 残差归零), 写当日 journal。

### 2.2 生产者 `~/wide_shadow`(非 git; 在役书的信号/权重/平滑/FTRIM 全在这里)
| 件 | 值 | 最后改动 | 依据 |
|---|---|---|---|
| bundle | `shadow_bundle/` **generation v3_2026-09**, built 2026-09-01T06:00:37Z; MANIFEST: slow2026.txt `8d79186b…`(= 每锚 anchors 行 `booster_sha`), slow_pred_pinned.npy `158cd4ac…`, config.json `3a8422f3…` | 09-01 | 09-01 月度重训首跑(RUNBOOK_monthly_retrain_2026-09) |
| 代码 | shadow_loop_v3.py `e9c98374…`(09-04 00:53Z, E-0904-F 席位历史口径 = Σ5m 简单收益; 席位种子 v3 09-05 经 state 文件); fea171/combo_stage.py `b5c698f9…`(09-02, FTRIM `pre_zero_rn8_le_-10bp_8h`) | 09-04 / 09-02 | 文件 sha/mtime |
| 参数 | NTOP 400 / alpha **0.1** / band **0.00025** / msharpe_look 900 / cap_mult 2.5 / qv4h_min 250k / cost_scen b / fund_caliber v1 normfix HL3d | 09-01 config | `shadow_bundle/config.json params` |
| 书形态 | combo_v2main_norev24, phi 0.45(king 0.55 / V2MAIN 0.45), rev24 去除; 席位 msharpe(900 锚, 纯价格毛额腿)⇒ 掩码 king 0.3557–0.3611(09-11/12); 宇宙 Phase A M1(universe_sha 93ad1d25…, 09-04) | 08-26 / 09-04 / 09-05 | target_combo/*.json, anchors 行 factor_version |
**结论**: 在役权重与参数 = 截至 09-05 的全部裁定(换装 08-26, FTRIM 09-02, 宇宙 09-04, 席位种子 09-05, 口径 E-0904-F 09-04)。**09-05 之后没有任何研究结果够格改生产者**(全部 (C)/(B)), 所以生产者未动是对的, 不是漏了。

### 2.3 模型: "重训了模型"到底生效了什么
- v4 链全量重训(09-09; PREREG `61af466b`, 装置/收据 `5749a821` → `multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/`, RESULT `7421ea29`, 研究员审计 `c8e2fc13`): holefix2 缓存 + clamp 特征 + RAW/CLIP 双臂目标 + FIX7 epoch + 原始记账 + 轴 +6 锚。**主判**: A1(v4 重训)− A0(在役形态)双种子动态 **+0.061 [−0.168, +0.287] / +0.048 [−0.171, +0.270]**, 固定 ±0.01 ⇒ **(C) 不可区分**。
- **裁定(CALIBER_STATUS_2026-09-09 L40)**: 线上模型腿在正确口径下**不需要**为口径原因换装 ⇒ **v4 bundle 没有上线, 在役仍是 king v3 + F10 v3(09-01 代)**。它们训练在有洞 / 未 clamp / 裁剪标签 / argmax 选 epoch 的旧链上, 每处缺陷对书层的影响都在 ±0.1–0.3 bps/锚内且全 (C)。**换装还有两道硬闸没开**: `ELIGIBILITY_CONTRACT.gates.BUNDLE_export.source = null`(什么臂都不能经 judge_v4 晋级; r20 的 v2 门 d63f4ec3 是 PROPOSED 未应用), 且 v4 bundle 的 `provenance.generation` 仍写 "v3_2026-09" 字面(成候选前须改标签重导)。
- **未来重训是否按最新方式**: `docs/RUNBOOK_monthly_retrain_2026-10.md` **§v4**(a8b1ef4c, 09-09)明写"下一次重训按本节而不是上文旧步骤", 八项: holefix2 + 覆盖门 v2 / `pod_fea_ext_clamp.py` / `pod_dlw_targets_raw.py` + raw_patch / legs 在役行逐位 + 新锚同公式(禁全行重算) / `pod_export_bundle_v4.py` env 逐字 + provenance 标签改本代 / F10 月折 FIX7 + `pod_f10_refit_v4.py` / 书层 meta y4 原始记账 + 判官先复现已发表数 / 易错项。**但有两处必须在十月前收口**: (a) 同一文件 §2–§4 仍是 09-01 的 v3 步骤原文(`pod_export_bundle_v3.py`, `pod_fea_ext`), 执行者若按 §2–§4 走会回到旧链 —— 应把 §v4 展开成唯一的步骤单并把 §2–§4 标作废; (b) 出口门空(上一条), 十月即使重训出候选也无门可过。

### 2.4 回测口径与装置
- 研究回放全部钉 v4(`CALIBER_PIN_v4_2026-09-11.md`, 8608cd4d); 更正表 `handoff_audit/caliber/CANONICAL_NUMBERS_2026-09-12.md`(修订 ①–⑬)。
- 三个基线的谱系要分清: **A0** = 在役形态的模型(v3 谱系 king/F10 预测)放在 v4 数据轴上(`build_dev_v4.py`); **A1x** = v4 原生模型(唯一谱系干净的规划数); **NW** = A0 装置修掉 N2 前视成员资格 + 暖机掩码后的书(r18)。钉住装置 `w10_sleeve.py` b88e35a4 **仍含 N2/暖机两处缺陷**, 修法在 `r18_foundation/devices/w10_sleeve_r18.py` 9b8a6323 —— 是否换钉是裁定。
- 实盘账本读者(研究侧): anchor_ts 墙钟连接 / fills 后写胜出 / income 四元键 / BNB 换算(E-0911-C)—— 已进 r14/r17/r21 装置。

### 2.5 研究员 double check 清单(命令逐字)
```
git -C ~/dl_quant_live rev-parse HEAD origin/main; git -C ~/dl_quant_live reflog --date=iso | head -3
git -C ~/dl_quant_live log --oneline d040c74..b681ca5 | wc -l        # 19
shasum -a 256 ~/wide_shadow/shadow_bundle/slow2026.txt ~/wide_shadow/shadow_bundle/slow_pred_pinned.npy ~/wide_shadow/shadow_loop_v3.py ~/wide_shadow/fea171/combo_stage.py
python3 -c "import json;c=json.load(open('/Users/haosiyu/wide_shadow/shadow_bundle/config.json'));print(c['provenance'],c['params'])"
python3 -c "import json;c=json.load(open('multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09/ELIGIBILITY_CONTRACT.json'));print({k:(v.get('source'),len(v.get('approved_source_sha256') or [])) for k,v in c['gates'].items()})"
sed -n '99,110p' docs/RUNBOOK_monthly_retrain_2026-10.md
```

---

## Q3 · 实盘为什么差于回放 —— 全部正确口径下的数与因

### 3.1 账本分解(combo 期, bps/锚/单位 gross; 收据 `PREREG_r6_coverage_extension_and_live_reconciliation_2026-09-11.md` L187)
| 分量 | 值 | SE | t | 读法 |
|---|---|---|---|---|
| 价格 alpha | −0.022 | 4.018 | −0.01 | 统计上是零 |
| 资金费 | **−1.371** | 0.113 | **−12.09** | 唯一显著项, 为负 |
摩擦/成本**没有**比回放差(用户观察成立, 且是关键): 费 实付 2.388 vs 模型 2.383(差 0.005); 成本模型本身 +2.96 [−0.64, +5.88] 含零(r21); 漏单定价 |Δ| ≤ 0.03(r17); E→E+24m 价格钟对成交子集 +7.3 但对全部意图 −2.28 ≈ 0(r21)。

### 3.2 回放 vs 实现(部署权重 × 回放收益, r6 D2, K=4)
ρ **+0.83** [0.71, 0.90](方向对); 斜率 **0.835** [0.707, 0.963](回放两个方向都把幅度放大 15–27%); 资金费分量 ρ 0.85, 斜率 0.73; 均值: 价格 回放 −0.74 vs 实现 −0.11(W5 n=78), 资金费 −1.56 vs −1.39。**回放与实盘最大的差项 = 书的构造本身 +2.70 bps/锚(CI 不含零)**: 回放里的书(A0/A1x)不是部署的那本(席位路径、FTRIM/EMA/带的状态、宇宙), 而不是成交(r17)或成本(r21)。**这就是 "exec 口径回放" 与 "NW 基线" 两项要做的原因。**

### 3.3 regime 与燃料
实盘窗 99.2%(r19 修掩码后)落在 HH 格(与冻结窗同格, 不是新格); 变的是格内强度: 成员横截面费率 sd 12.91 → 8.70, 平均费率 −2.4 → −0.16 bps/锚。冻结窗高夏普里 **2.27×** 是 regime 租金(2.9357 / 1.2912)。唯一真正样本外的 61 锚(08-30 之后)A0 读 **−3.87 [−12.19, +3.53]**。波动率不是原因: 跨年代比 1.404 可复现, 但同期 20Z 对齐配对比 **0.656 [0.467, 1.008]**。

### 3.4 正确口径的水平(v4 钉, 拟合成本, g bps/锚/单位 gross)
| 对象 | 窗 | g | CI95 / SE | Sharpe |
|---|---|---|---|---|
| A0(在役形态) | W_ALPHA n=9138 | **+0.6342** | [+0.165, +1.107] | 1.2912(SE 0.49) |
| A1x(v4 原生, 规划数, 历史读数非期望) | n=9199 | **+0.6602** | [+0.167, +1.147] | 1.2857 |
| NW(N2+暖机修后, s42 / s2027) | W_ALPHA | +0.6313 / +0.6640 | 配对 Δ vs A0 −0.003 / +0.006 | 1.2846 / 1.3411 |
| 逐年 A0 | 2022 / 2023 / 2024 / 2025 / 2026→08-30 | +0.16 / **−0.65** / +0.49 / +0.68 / **+3.09** | 2026 SE(Sharpe) 1.23 | 0.48 / −1.94 / 1.09 / 1.19 / **4.52** |
| 冻结窗 A0 | 2025-03..2026-08-10 n=3168 | +1.8267 | Sharpe CI **[1.31, 4.57]** | 2.9357 |
| 实盘实现(SEP 46 锚净额) | 09-01..09-10 | **−2.78** | 回放同权重 −4.94 | — |
| 2.0× 尾部(NW 全史, 真 maxDD) | 2022-01..2026-08 | maxDD −44%, 最差日 −6.4%, 停机 1.09–1.31/年 | P(1y maxDD ≥25%) 27–33% | 1.00× 无停机 |

### 3.5 高潜力改动在正确口径下的严格因果回测(全部 CI 含零; 判据 (A) 无一过)
| 改动 | Δ(bps/锚/gross)或读数 | CI95 | 换算 | 状态 |
|---|---|---|---|---|
| CEM_99 carry 紧急处置(r12; 零假设 r21 重匹配后仍胜 6/6) | **+0.0380** | [−0.0045, +0.0851]; Bonf-29 含零 | ≈ +1.7% NAV/年 @2× | (C) UNDECIDED |
| 更慢平滑 (α 0.05, band 2.5e-4)(r12/r18) | Δg +0.0725 (s42) / +0.0430 (s2027) | [−0.093, +0.244] / [−0.094, +0.178] | 共同可行 L=0.88: 中位 1 年 +8.2% vs 在役 +0.3%(点估计) | 方向存活, 无 CI 支持 |
| Amihud sleeve(r4/r14/r19) | 独立 Sharpe 1.4721 vs A0 1.4150(n=9018); 合入 +0.2458 = 方差削减 | 干净样本 +0.2181 含零; 亏损格 ρ +0.374/+0.369 | 分散化候选, 非 alpha | 待第四腿整书回放 |
| 仓位级 FTRIM(r15) | +0.018 | 含零; 2026 −0.20; 换手 +24% | — | UNDECIDED |
| XIB_LAG50(r5–r7) | 冻结窗 ΔSharpe +0.82 | ρ-to-A0 0.911; 回吐窗更差; gross 剖面 2.1× | 再加权非分散 | 不晋级 |
| r13 FORM B(半区 beta 再配置) | +0.0077 | [−0.164, +0.179] | 机制成立 alpha 否 | REJECT as alpha |
| BNB 抵扣恢复(运维) | ≈ +1.5% NAV/年 | 近确定 | — | 待用户动作 |

**一句话**: 实盘差不是执行、不是成本、不是延迟、不是模型陈旧、不是波动率; 是这本书本质上只有一个下注(资金费动量), 它在当前 regime 里的燃料掉了(横截面费率 sd 12.9 → 8.7), 而回放里的书与部署的书构造差 +2.70 bps/锚。要显著过 3.0, 需要**第二本不相关的书**, 不是同席位再加权 —— 已测的全部候选都是后者。
