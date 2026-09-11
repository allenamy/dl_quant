# SHIP-2 · 四项待裁定事项 · 单一决策文档(登记册)

> **创建:** 2026-09-11 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 待用户裁定; 本文=登记册与收据索引, 完整论证(正反同页)在 Artifact | **作废条件:** 四项全部裁定并写入 STATE.md 后, 本文转为历史记录
> **全文(正反论证、后果、建议与置信度):** https://claude.ai/code/artifact/bca49b72-e06a-4f8d-8b62-e30b206fb401
> **口径 PIN:** v4 chain 2026-09-09; 成本 `costb_PWR_G230k.json`(K=0.17); 主窗 post-warm n=9018, SE(Sharpe)=0.4928; 装置 `w10_sleeve.py` sha `b88e35a46b93d712`。
> **GATE P:** bitwise PASS(`r3_receipts/GATE_P.json`: 四格 rec/W 全 `array_equal=true`, maxabs 0.0, device sha 同 PIN)。**本文未跑新测量**, 全部数字为对既有收据的复核与再验证。
> **ENV:** 本文背后每一条命令均未设置任何环境变量(全为 git / python / ssh 只读), 按 E-0826-D 断言。

## 登记册

| # | 裁定项 | 问的是什么 | 建议 | 置信度 |
|---|---|---|---|---|
| 1 | 逆向 IC / 偏移谱门 | 退役 S7(按字面), 以 S7-R 取代 | 采纳, 带两条修正 | MEDIUM(退役 S7: MEDIUM-HIGH) |
| 2 | 主判决窗 | 冻结窗降级为诊断, 判决移到全周期 n=9018 | 采纳, **但与 XIB 解耦** | MEDIUM(冻结窗不适用: HIGH) |
| 3 | 资格合同 | 批准门源 sha, 使任何臂可被晋级 | 批准 — **但先补一张缺失收据** | MEDIUM(门本身可靠: HIGH) |
| 4 | 部署执行器 b681ca5 | 运行树 d040c74 → b681ca5 | 部署, 非锚窗内 | HIGH |

**建议裁定顺序:** 4 → 3(仅门 sha)→ 2 → 1 → 然后才重判 XIB 与 sleeve、并决定是否签 `arms.XIBLAG50`。前三项互相咬合, 第 4 项独立。

## 必须先看的三个背景数(不裁定)

| 量 | 值 | 收据 |
|---|---|---|
| A0 跨 regime 诚实规划数 | **1.4150** [0.449, 2.381], n=9018(s2027 1.4370) | `r3k_impact/analyze3.out:25` / `:24` |
| 冻结窗同一本书 | **2.9357** ⇒ **2.07× 为 regime rent** | 同上; 2.9357/1.4150 |
| 唯一已验证提升(受阻于 SHIP-1 工程) | a=0.20 orth-Amihud sleeve **+0.2458 / +0.2407**, 4/4 下界 >0 | `PREREG_p6_amihud_sleeve_2026-09-11.md` §4/§5 |

**sleeve 的真实性质**: 每个配额的 **Δg 都是负的**(a=0.20: −0.00252 / −0.00581 bps/锚/单位 gross, P(Δg>0)≈0.48)。它不赚钱, 它降波动; gross 钉死 2.0× 时约 −11 bps/年 NAV(INFERRED)换夏普。

## 逐项收据索引

**1. 偏移谱门** — `PREREG_gateA_offset_spectrum_2026-09-11.md`(装置 `r3_gates/devices/offspec.py` 64d4c346, `echo2.py` 62f6186e)
- S7 按字面的实测算子特性: 13 条因果臂**拒 10**(含在役 3 腿中的 2 腿: DL 6.35×/7.07×, king 2.48×), 2 条合成泄漏**拒 0**。
- 机理: a₁ = ic_oracle(−1) = **−0.04424**; CTRL_REV4 预测回声 +0.04261 vs 实测 +0.03946(吻合 7%)。
- S7-R 校准: NULL xic −0.00037 [−0.00177,+0.00097](size 0); REV4 −0.00336(纯回声剥净); ORACLE +0.96054(满功率)。
- **★ 与唯一提升相撞**: S7-R 的 R2 判 **AMI_SLEEVE_ORTHLAG FAIL**(pre-2025 +0.0184 / 2025-on +0.0039 [+0.0008,+0.0074], 比 0.21 < 0.25)。注意其 2025-on CI **仍排除零** —— 败在自选的 0.25 门槛, 不是败在零。gate-A 的 `AMI_SLEEVE_ORTHLAG` 与 p6 的 `ORTHLAGA` 同构 = **INFERRED**(读两处构造, 未做逐位比对)。
- R2 的 0.25 是提议者自选, 在役 DL 腿余量仅 0.32; **门槛若定 0.35, 在役 DL 腿 FAIL**(提议者自陈的敏感点)。
- R3 声明的永久盲区: 合成泄漏 `CTRL_LEAK_XIB_FWD50` 读 ic(0) +0.0213 / xic +0.0235(诚实臂 +0.0142 / +0.0151), **过所有谱检**。

**2. 主判决窗** — `PREREG_gateB_primary_window_2026-09-11.md`(`r3_gates/regime_composition.json`, `rejudge_windows.json`)
- 冻结窗 n=3168, HH 0.9426, L1(A) 0.672 / L1(B) 0.968; FULLCYCLE n=9018, HH(已标注) 0.6005, L1(A) 0.0118 / L1(B) 0.046 —— **同时是 n 的 argmax 与 L1 的 argmin**。
- **★ 提议者书面声明: 动手前就被任务书告知 XIB 在全周期强、冻结窗 (C), 故「无盲性可主张」。这是本项的首要风险, 必须由用户直接裁。**
- 翻转的判决: XIB_LAG50 (C)→(A), 四格全过含 Bonferroni K=4(下界 +0.1004/+0.0980/+0.0422/+0.0492)。冻结窗判官原件读数(`infra2/receipts/JUDGE_v4_PROPOSED.json`)为 **(C) UNDECIDED 双席位**(dyn s42 +0.4698 [+0.0586,+0.8467] / fix s42 +0.1612 [−0.3408,+0.6290])。
- 对称代价: RESID_SHARPE 因跨度缺陷最高只能 PROVISIONAL。
- **洞**: 四条已判 (B) 的轨道未在新窗重判(INFERRED)。

**3. 资格合同** — 要批的就是两行
- `gates.BUNDLE_export.approved_source_sha256`: `[]` → `["f814c728938482b876cbcaa31f200832d207a0f89387d58ed3e2d0d45448e214"]`, `source: null` → `"v4e_gate_export.py"`。**本地复算 sha 一致(VERIFIED)**。
- 另一行独立: `arms.XIBLAG50` 注册(= 声明该书形态是本台愿意拿真钱跑的形态, 预注册行为)。
- 批准 sha = 把门内阈值批准为出口标准并冻结: fold IC 2024/2025 |Δ|≤0.004, pinned 2026 |Δ|≤0.006, baseline Sharpe 带 [2.27,2.57], MANIFEST 完整性, config/live_pins 平价, 严格 book contract。
- XIBLAG50 收据 PASS(`infra2/receipts/BUNDLE_export_XIBLAG50.json`): 11 输入全哈希, E1–E7 全 ok; E3 重算 IC 0.05444/0.06092/0.05732(Δ −0.00036/−0.00208/+0.00022); E4 重算 Sharpe 2024-on **2.3044** 在带内(n=10177)。
- **judge_v4 回归我方独立复核(VERIFIED)**: 基线 36 对照 / 18 判决, 提议 40 / 20; **共有 36 对照 0 变, 共有 18 判决 0 变**, 新增 4 对照 + 2 判决(皆 XIBLAG50-A0)。
- 声明盲区: 门验的是**已发运的** `slow_pred_pinned.npy`, 不是产它的 LightGBM 运行(2024/2025 折在 n_jobs=100 下不可复现)。
- **★ UNRESOLVED**: 可证伪性演示(用 exporter 默认面板应 FAIL, 复现归档 E-0826-D 假红 1.9622/0.8998 vs 日志 1.96/0.900)**未找到收据** —— 查过 `infra2/receipts/`、`infra2/runner.log`、pod2 `/workspace/uplift_2026-09-11/infra2/`。**建议补出这张收据再签**: 一个只被见过说 PASS 的门, 还不算已知是门。

**4. 部署 b681ca5** — `docs/RUNBOOK_deploy_executor_b681ca5_2026-09-11.md`
- 树状态复核(VERIFIED, 只读): 运行树 `d040c74`, `origin/main` = `b681ca5285e9620cb6d9158d72dc2d50b2d21109`, 落后 **19** 提交。
- **今日 08Z 实盘证据(我方直接读账本, 非引用 journal)**: rebalance `A1789115039`, **73** 行补单全部 `order_type=topup_taker` / `terminal_reason=abandoned_max_attempts` / `attempt_idx=2`, 73 个不同标的, Σ|意图| **4,014.2 USDT**, **成交 0.0** ⇒ **73×2 = 146 次请求**打在场所违规计数器上。b681ca5 的 `skipped_venue_lock` 熔断在第一次就会停。
- 当日四锚(补单成交 / −4400 / abandoned): 00Z 53/0/0 · 04Z 42/0/0 · **08Z 0/73/73** · 12Z **43/0/0** ⇒ **锁于 12Z 自行解除**(VERIFIED)。
- 前提五条 / 一条命令(`git -C ~/dl_quant_live pull --ff-only origin main`, 无需重启)/ 验收(27 files +5098/−280; drift rc=0; 三套烟测 378; **建议把 132/132 全电池作为部署步骤而非可选**, 它正是独立复审点名的缺口)/ 已排演回滚(revert 19 提交 ⇒ 对 d040c74 零文件差)。
- **延后不是免费的**: `ops/safe_commit.sh` L23-28 在运行目录会 fetch+rebase origin/main ⇒ 下次在运行树跑 safe_commit = 无人裁定的部署。延后需要一条常设禁令。
- **不可搭车**: §4 的 52 行 `reconstructed` 回写, 其回滚兼容性 **UNRESOLVED**, 必须另裁、另锚。

## 洞(签字前必读)

1. **门的可证伪性收据缺失**(上述 3)。**UNRESOLVED**
2. 四条已判 (B) 的轨道未在提议主窗重判。**INFERRED**
3. gate-A 的 Amihud 臂与 SHIP-1 的 sleeve 同构为**读码所得**, 未逐位比对 —— 而裁定 1 与提升的相撞依赖此同一性。**INFERRED**
4. 「旧码读者忽略新键」为读码所得, 未逐读者实跑。**INFERRED**
5. **旧文档的数已过期**: 凡引 A0 Sharpe `1.32` / `n=9918` 者早于 E-0911-A 预热丢弃, 现行为 `1.4150` / `n=9018`(`RESULT_uplift_program_2026-09-11.md` §2/§3 仍带旧对)。
6. 本文**未测量任何新候选**; 它只做合并与复核。标 VERIFIED 者为我方亲自复跑/复读者(judge 回归、今日账本、门 sha、全周期 Sharpe 表、GATE P 收据)。
