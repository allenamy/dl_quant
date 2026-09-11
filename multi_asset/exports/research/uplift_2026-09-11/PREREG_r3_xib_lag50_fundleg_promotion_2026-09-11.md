> **创建:** 2026-09-11 | **Session:** round-3 integration (uplift_2026-09-11) | **状态:** CONDITIONAL / 未裁定 — 两项阻断测试未跑, GATE B 未裁定 | **作废条件:** (a) 用户裁定 GATE B 维持冻结窗为 PRIMARY; 或 (b) §3 任一阻断测试不过; 或 (c) XIB_LAG50 定义改变

# PREREG — XIB_LAG50 作为在役 fund 腿评分的替换 (书行为改动)

本文件是**裁定用文件, 不是执行许可**。作者未改动 `~/wide_shadow` 或 `~/dl_quant_live` 任何字节。
§3 的两项阻断测试**未跑**; 在它们通过且用户对 GATE B (PREREG_gateB_primary_window_2026-09-11.md) 做出裁定之前, 本 PREREG 处于 **BLOCKED**, 不可提交裁定。

## 1. 改什么 — 确切文件与行

在役生产者 `~/wide_shadow/shadow_loop_v3.py` (当前 sha256 `e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e`, mtime 2026-09-04 08:53)

- **第 471 行**, `legz` 字典的 `"fund"` 项:
  现行 `"fund": xz_in_base(fe_v[m], [st.syms[int(j)] for j in m], base_vals)`   (M1 秩基口径)
  改为   `"fund": 0.5*xz_in_base(fe_v[m], ...) + 0.5*xz_in_base(ami_v[m], ...)`
  其中 `ami_v` = f_amihud_24h, 其 24h 窗**结束于 E 之前一个锚** (LAG50 的 LAG 部分)。
- 新增 `ami_v` 的构造: 生产者第 357 行 `wstat(ch,w,kind)` 已有全部原料 — 通道 0 = `ret5`, 通道 3 = `log_qv`。Amihud 须与面板 `f_amihud_24h` **逐位同义**, 不是"同名"。
- 第 472 行 `z = w3[0]*king + w3[1]*rev24 + w3[2]*fund` 不变; 席位规则 (WRULE=msharpe, `P["msharpe_look"]=900`, 第 456 行) 不变。

**这不是新增一条腿**: XIB_LAG50 与 A0 的相关系数 +0.8891 — 它是 A0 的重新加权。因此爆炸半径是整本书, 不是一个 sleeve。

## 2. 冻结的接受门 (在看任何新数字之前冻结)

统计量 `g = net_ex/gross_total` (bps/anchor/unit gross), UTC 日块 bootstrap 2000 抽样, rng `default_rng([20260905,k])`。
成对: 同一 seed 的 XIB 减 A0。口径针 = v4 chain (见 CALIBER_PIN_v4_2026-09-11.md), 成本模型 = `costb_PWR_G230k.json` (拟合 K=0.17), **不是** deployed `costb_fee_steady`, **不是** K=1。

PRIMARY 窗 = GATE B 裁定的窗。两种裁定各自的门:

| 裁定 | PRIMARY | 门 (四格 dyn/fix × s42/s2027 全部满足) | 现测结果 |
|---|---|---|---|
| RULE W 通过 | FULLCYCLE post-warm n=9018 | Bonferroni K=4 下界 > 0 | dyn +0.1004 / +0.0980, fix +0.0422 / +0.0492 — **四格全过** |
| RULE W 不通过 | FROZEN n=3168 | Bonferroni K=4 下界 > 0 | fix 席 0/6 seeds 过 (INSTRUMENT-3) — **不过, 判 REJECT** |

冻结的副条件 (无论 GATE B 怎么裁, 全部必须满足):
- (S1) 成本敏感性: 在 `costb_honest_X1` (K=1) 下 PRIMARY 四格点估计仍 > 0。已测: 是。
  **声明的脆弱点**: XIB 抬换手 +12.8%; 在 K=2 下冻结窗 s42 已翻负 (INSTRUMENT-3 §4d)。拟合 K=0.17 远低于 2, 但 CRITICAL-1 自陈 metaorder 冲击只会比 book-walk 更大且未定界。
- (S2) 修复后的安慰剂 (INSTRUMENT-1 `null_families.py` sha256 `2ce8b88b49ae5462...`): RO/T 两族均 SURVIVES 且 cost ratio ∈ [0.8,1.3]。已测: c_rat 1.13–1.24, 三窗两 seed 全 SURVIVES。
- (S3) 修复后的 GATE A (S7-R, PREREG_gateA sha256 `e2e7273d58a86185...`): R1 回声调整前向 IC 下界 > 0 且 R2 年代稳定。**未跑**。
- (S4) §3 的两项阻断测试通过。**未跑**。

## 3. 阻断测试 (必须先跑, 因为它们正是杀死 RESID_SHARPE 的两把尺)

- **B1 换手匹配时移零假设**: CRITICAL-3 的 SHIFT101 / SHIFT503 / SHIFT1009 / RELAB 电池 (`r3_attack_RESID_SHARPE/null.py`), 原样指向 XIB_LAG50, 同一 span (FULL post-warm 与 2024-on 各一遍)。
  判据: XIB 的 net_ex 必须**严格高于**全部时移拷贝。RESID_SHARPE 在 2024-on 上排第 3/3 而死。
  这是 CRITICAL-3 自报的头号 hole: "在任何人断言 XIB 是幸存对象之前, 必须对 XIB 跑同一电池"。
- **B2 尾部集中度尺**: INSTRUMENT-2 的 `rs_conc.py`, 原样指向 XIB_LAG50 的 fund 腿, 2025-on 子窗。
  判据: 剔除每锚 top-20 |z*y| 名之后 Sharpe 仍 > 0。RESID_SHARPE 在此读 −2.399 / −5.596; 对照在役 fund 腿读 +6.709。

B1 或 B2 任一不过 ⇒ 本 PREREG 作废, 且轮次 1–2 的整个评估路径需重审 (不是这一条臂的问题)。

## 4. 爆炸半径

- **整本书**。fund 腿在 msharpe 席位下占 w3[2], 近年常在 0.3–0.5; 改它改变每个锚的全部 400 名目标权重。
- 下游: combo_stage 重写 target_live (五层安全) → 执行器 N+23 读取。目标层数值变化会经 α=0.1 EMA 与 band=0.00025 中性带传导, **首锚换手是一次性重定位**, 量级 ≈ 一次完整 rebalance, 远大于常态 0.03 gross/anchor。必须预估并在首锚前告知。
- 不触及: 杠杆 (constant_leverage_2.00)、宇宙门 (qv4h_min 250k / NTOP 400 / sel_min 80)、cap_mult 2.5、止损层、FTRIM。
- 生产者由 launchd 管理 (`com.hsy.c2shadow`); 重启动词 = `kickstart`, 不是 `restart`。
- bundle 由 `shadow_bundle/MANIFEST.json` 做 sha 校验; Amihud 若引入任何新状态文件, 必须进该 manifest (对照缺陷: combo_stage.py:160 读模型 npz 无 sha 校验)。

## 5. 首锚检查 (上线后第一个锚, 逐项必须有收据)

1. 生产者进程实际在跑新代码: `pgrep -f '[s]hadow_loop_v3'` + 进程启动时间晚于改动 mtime + 运行中文件 sha 复核 (E-0825-F / "补丁在盘≠在跑")。
2. `shadow_log.jsonl` 新锚有 `legz` 三腿齐全、无 `anchor_skip`、成员数 ≥ 300。
3. fund 腿分数与离线 replay 同锚逐位比对 (双实现相等断言); 不等即回滚, 不做解释。
4. 首锚换手: |Δw| 之和与预估值比对, 超预估 1.5× 即回滚。
5. 订单账本: 该锚 `orders` 行数 > 0 (E-0909-G 看门狗缺口形态)。
6. net/gross 与 regime 仪表盘 + FTRIM 按既定纪律读一次, 只读一次 (每锚深查只做一次)。
7. 场所状态: 复场/拒单前读 `apiTradingStatus` (E-0910-A)。

## 6. 回滚

- 触发条件 (任一): §5 任一项不过; 连续两锚 net/gross 低于回测同窗 5% 分位; 看门狗触发; 用户口头。
- 动作: `shadow_loop_v3.py` 还原至 sha256 `e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e` → `launchctl kickstart -k gui/$UID/com.hsy.c2shadow` → 下一锚验证 §5.1/§5.3 回到旧值。
- 书形态: combo_stage 五层安全在失败时自动回滚为 king 形态; 本改动不改变该路径。
- 回滚是**代码还原**, 不是"关开关" — 不得留下默认关闭的旗标 (E-0826-C: 口径旗标凭记忆)。
- 存量仓位: α=0.1 EMA + 中性带意味着回滚后仍需 ~数锚收敛; 期间账面归因须按"过渡期"单独标注, 不得混入任一臂的业绩。

## 7. 本 PREREG 自陈的弱点

1. GATE B 的 RULE W 是在**已知它会把 XIB 从 (C) 提到 (A)** 的情况下选的 — INSTRUMENT-2 自己写明了这点。窗规则的两条依据 (L1 regime cell 距离、n) 是与臂无关的, 但先后顺序无法洗白, 裁定者必须把这当作已知偏好来读。
2. 冻结窗与全周期给出相反判决 (REJECT vs (A) PASS)。机制上的解释是: 冻结窗 94.3% 是单一 regime cell, 且 XIB 在该窗的收益 63% 来自 msharpe 席位再加权 (fix/dyn = 0.37), 而在全周期该比例是 0.95。该解释支持全周期读数, 但它是**事后**的机制解释。
3. XIB 与 A0 相关 0.8891 — 它不增加一个赌注, 只是把现有赌注调得更好。它对"跨 regime Sharpe 显著高于 3.0"这个目标**没有**贡献路径。
