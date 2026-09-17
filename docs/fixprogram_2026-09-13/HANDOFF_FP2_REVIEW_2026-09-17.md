> **创建:** 2026-09-17 06:0xZ | **Session:** 0134cBjSFjjurUhAz95RNuWk(主研究员) | **状态:** 交独立研究员复审(用户常设规则: 每批修复 → 完整提交链 + 报告 → 独立复审) | **作废条件:** 本批任一提交被改写、或 FP2-8 运行出最终判官/逐年表后升 v2

# FP2 批次交接(执行器部署后的全链修复与 FP2-8 重训试跑)

## 0. 请先看什么
1. `docs/fixprogram_2026-09-13/ACCEPTANCE_LEDGER_full_chain_2026-09-17.md`(v1.2; §8 FP2-1..5, §9 FP2-7 实测)
2. `docs/fixprogram_2026-09-13/DESIGN_FP2-8_fullchain_retrain_2026-09-17.md`(预注册 + AMENDMENT 1–4, 全在数字之前)
3. `docs/fixprogram_2026-09-13/PROPOSAL_FP2-6_booster_pin_2026-09-17.md`(待用户字, 零部署)
4. 受据目录 `docs/fixprogram_2026-09-13/FP2_receipts/`

## 1. 提交链(研究仓 research/book-uplift-2026-09-11)
| commit | 内容 | 测试 |
|---|---|---|
| 26982400 → ac8131cb | FP2-1..5(面板验证器 v2 / 后视构建器退役 / 月度启动重核 / 三态 / CLOSE 归属)+ 验收表 v1.1 | 478/478, 15/15, 8/8, 10/10, 12/12 |
| dcf0e006 | FP2-7 实测(C1/C3/C6 不在我方数据)+ FP2-6 提案 + FP2-8 预注册 + 验收表 v1.2 §9 | 探针 .py/.out 受据 |
| 0b5df2f6 | v2 构建器(派生脚本恰一次 hunk)+ 成员掩码装置 + 合成套件 | tests_fp2_builders_v2 18/18; pod2 P2 逐位 = 3badc4b6 |
| 73f40056 | fp2_controls + fp2_gate_step1/2 + fp2_gate_lib | tests_fp2_gates 8/8(G3–G7 红能力) |
| 19a246b8 | 驱动可选键/掩码; 合同 PROPOSED3; build_dev_v4 掩码感知; run_arm.sh 缺陷; 运行器; 首锚验收 | tests_pipeline_gates 482/482; tests_build_dev_v4_mask 5/5 |
| 7ca64ab9 | fp2_per_year_table + 测试; AMENDMENT 4 | 5/5(精确值) |

## 2. 请重点复审的判断(按我认为最可能出错的顺序)
1. **ELIGIBILITY_CONTRACT PROPOSED3**(1188267a → 69edc437): 我在没有你复审的情况下为 STEP1/STEP2 追加了 FP2 门变体的批准 sha(依用户常设规则「不等裁定」), 前身保留于 `.r1_1188267a.json`, 套件自洽格改为「归档 sha + 已声明变体」。请判: 变体门的语义(以 controls 收据替代上月增量比较)是否成立; 是否应限定只对 `V4_MONTH=2026-09` 且 `R≠review_scratch` 的合同有效(现在没有这一限制)。
2. **成员掩码语义**(AMENDMENT 1.2): A1 训练成员 = TRADABLE(W24H)@锚(不含 umask); 评估两臂同 umask∧tradable(3badc4b6)。这是「数据修正」还是「书性质改动」? 我按前者处理(无用户字)。
3. **king v2 builder 的机制选择**(AMENDMENT 1.1): 全窗 clamp + 实际窗长归一, 使 30 个 E<2016 锚以 2–7 天窗进入训练。另一选择是显式 `grid>=2016` 丢弃。我选前者是为与 DL 轴(P.1)同构; 请判是否引入首 5 天的弱统计噪音。
4. **AMENDMENT 4**: 逐年表主仪器从 lifecycle 引擎改为臂记录(与判官同源)。我在数字之前改的; lifecycle 引擎降为交叉核对且可能 PENDING。请判这是否削弱了「最可信回测」的声明。
5. **C1/C3/C6 不在我方数据**的三条探针(FP2_receipts): 是否遗漏了别的表现形式(例如 4h 面板 v3splice 的资金费列、或 fea82 的窗口特征在代际边界的泄漏)。我只查了 5m 缓存 ch0/ch4 与 RAW 目标 y4s。
6. **run_arm.sh 硬编码根**: 我只改了 FP2 副本(f30b2c7c)并登记十月 runbook 修订 8; 是否应立即把它收进装置目录(我列为 FP2-9 采纳项)。
7. **build_dev_v4 掩码感知自检**: 「掩码成员 ⊆ 参照 ∧ 被减者掩码为 False」是否足够, 或应同时要求「参照中掩码为 True 的成员必须都在」(即相等而非子集; 我没这样要求, 因为 MIN_MEM/NTOP 截断也可能去掉成员)。

## 3. 运行状态(pod2 `/workspace/fp2_2026-09`, 2026-09-17 06:0xZ)
preflight PASS(23 装置 / 31 输入 / 3/3 批准)· cache coverage v2 PASS · RAW_PATCH_COVERAGE PASS(952/952, 0 unaccounted)· controls 在跑 · data 在跑 · 运行器 `chain_fp2_run.sh` 等待后依次 gates → king → legs → mwf(GPU)→ refit → np_export → arms → a0rerun → judge → export。所有收据在 `$R/v4_gates/`、`$R/controls/CONTROLS.json`、`$R/v4_gates/A0_RERUN_TRADABLE.json`。判据 G1/G2/G3 见 DESIGN §5。

## 4. 我知道的局限(不是问题清单的全部)
- legs 按 AMENDMENT 5 复制在役旧行(未掩码成员)—— A1 的 legs 与其成员集不一致(设计 AMENDMENT 1.4)。
- F10/DL 腿身份在 target_live 无字段, FP2-6 钉不到它。
- 生命周期日历 candidate2 非全 829 PIT 认证; 若做 lifecycle 交叉核对会继承这一限制。
- 首锚验收(§8)只证明新树正常成交与新码零触发, 不证明六项修复在真实事件下的行为(那在电池里)。
