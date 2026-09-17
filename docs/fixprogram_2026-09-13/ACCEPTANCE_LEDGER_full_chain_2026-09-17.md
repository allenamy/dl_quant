# 全链逐环节验收表(v1, 2026-09-17 03:1xZ)—— 源码版本 · 实际输入 · 模型/产物 · 测试证据 · 是否部署 · 判定 · 缺口

> **创建:** 2026-09-17 | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** v1.3(FP2-1..5 §8 ✅; FP2-7 §9; FP2-6 提案待裁定; FP2-8 在跑 §10; FP2-9 开放)(每格标 VERIFIED=本会话读到原件 / INFERRED=由原件推出 / UNVERIFIED=未核) | **作废条件:** 任一格的版本或收据变化; FP2 各项完成后升 v2
> **读法:** 本表只回答「现在能证明什么」。「有中间版本」≠「正式流程已修好」; 「训练跑完」≠「流程认证」。缺口一律映射到 §8 的 FP2 编号, 不在表内宣布关闭。

## 0. 两个总判(先说结论)
- **执行侧(交易执行 / 记账对账 / 异常处置)**: 已修复、已复审收口、**已部署**(运行树 = origin/main = 6661ea3, 02:06Z; 生产电池 160/1/0, 唯一余红 NOSLEEP-1 属机器证据层)。**首锚 04:00Z 真实运行证据待采**(等待器 04:58Z)。
- **非执行侧(数据 / 特征 / 模型 / 组合 / 回放 / 重训)**: **未全部证明**。在役模型是 **v3 口径世代**(king bundle `v3_2026-09` 09-01 构建; F10 v3 09-01 换装), 而 09-09 定为唯一正确口径的 **v4 链的产物与门收据全在 pod2、从未换装**; 其唯一一次配对评估(JUDGE_v4e, 09-09, 3168 锚)**全格 UNDECIDED**(A1−A0 dyn s42 +0.061 bps/锚, CI [−0.168, +0.287]), 且早于其后的数据修复(C1/C3/C5, holefix2, king 轴缺 5 天, A0 死合约偏高)。

## 1. 数据准备与特征生成
| 子项 | 源码版本 | 实际输入 | 产物 | 测试证据 | 部署 | 判定 | 缺口 |
|---|---|---|---|---|---|---|---|
| 5m 缓存(holefix2 正典) | `chain_v4_data.sh`(研究仓 v4_chain 目录, sha 清单 `v4_scripts_sha_full.json` 09-16) | `/workspace/data/dlnative_5m_wide829_f16_holefix2.npz`(pod2, 月合同 CACHE) | 同左 | `cache_coverage_gate_v2.py`(洞 0/宽缺口 0 门) | pod2 | **INFERRED**(合同与脚本读到, 门收据未在本会话打开) | FP2-8 重跑时出收据 |
| 原始行情回填 C1(三月 raw)、标签重算 C3(BOB/BMT/MTL) | 独立研究员代码(分支 `codex/fullchain-continuation-20260914`, C1/C3 于 `CODEREVIEW_codex_fixes` 判「采纳」, 量级 3/3 复算) | 其分支产物 | 519 有效标签格恢复(≠519 训练样本) | 我方逐位复算 + 其 §3 双方判决一致 | **未接入正式 v4 链** | VERIFIED(判决) / **UNVERIFIED(接入)** | **FP2-7** |
| AERGO 四估值点 C5 | 同上, 判「采纳但需改」 | — | — | 两组数字我方独立证实 | 未接入 | 同上 | FP2-7 |
| 合约生命周期 / 未知期屏蔽 C6 | `6ef59338`(51 文件 +3825 行, 不在任何分支, 对象可恢复) | — | `build_targets.py` / `build_funding.py` | **内容未审**(仅 sha 相符) | 未接入 | **UNVERIFIED** | FP2-7(内容审) · **复审 F08 (2026-09-17 10:4xZ)**: 「C1/C3/C6 不在我方数据」降级为「首根不跳价已证(13/13 ret5=NaN); OPEN 后窗口暴露已量化: 48h 0 / 7d 40 / 30d 1,771 成员锚(0.064%), 首次入成员 ≈161h; 经济影响 UNAVAILABLE」收据 `FP2_receipts/OPEN_WINDOW_EXPOSURE_2026-09-17.json`; 计划 = 十月链 OPEN 后 30 天成员屏蔽(预注册) |
| 资金费特征(在役 king: fund_ema v1 normfix HL3d + fund_now) | `shadow_loop_v3.py`(82 列 = 40 值+40 秩+fund_ema+fund_now), 状态 `shadow_bundle/fund_ema_v1_state.json`; 构建器 `build_fund_ema_fullhist.py`(median 0 处) | 结算账本 + REST fundingInfo | 面板列 | x0910: 09 月延展行 `f_fund_iv` 用拉取时刻间隔(547 格/23 名错, 修正面板在 pod2, 在役行未换) | 在役 | VERIFIED(路径) / 缺陷已知未修 | **FP2-2b**(ivfix 面板接入) |
| 资金费 v2 全段后视中位数(R16-D1) | `multi_asset/data/build_funding_hist.py` L31(M0 2026-07-09, 全段 `median(funding_interval_h)`); `apply_funding_fix.py` L80(span 用全段 median(iv)); `megacap_funding_replay.py` L41 | — | — | **消费者普查: v4 数据链 / 月驱动 / runbook 均不引用**(grep 0 命中) | 不在役 | VERIFIED(遗留、未接) | **FP2-2**: 退役+守卫测试, 不建后继(无消费者) |
| 增量面板验证器三缺口(R16-D2) | `FX_DATA/devices/fx_fnd_hol_rebuild.py`: C1 L137 相对 1e-6 阈值、finite→+Inf 时 `Inf>Inf` 为 False、无全特征有限性门; C2 五列先拷 INC 再只重算三列 EMA, `f_fund_now`/`f_fund_iv` 自比; 写后 roundtrip 只核 keys/ts(X[0,0]→999 仍 PASS) | — | — | 复审 R16 §D2 + PENDING_DECISIONS 行 2 | 研究门 | **UNVERIFIED(未修)** | **FP2-1** |
| 宇宙(450, sha 93ad1d25…) | `shadow_loop_v3.universe_sha()`; 读者 `external_book.universe_sha` 重算拒绝 | `config.json symbols_live` | target_live `universe` 列表 | 配对测试(pair test)钉住配方 | 在役 | VERIFIED | UNI-01 3× 反向永续/商品/pre-IPO 名在训练宇宙(记忆 09-16), 待 T7 |
| 死合约 / 冻结行 | 记忆 09-13: 研究数据层无「按成交」可交易定义; A0 参照因死合约偏高 ≈0.06 bps/锚/gross | — | — | SPEC §7 A0 臂 09-16 INCONCLUSIVE | — | VERIFIED(问题) | **FP2-7c**(A0 重基) |
| king 训练轴缺首 5 天(30 锚) | 记忆 09-16(covr 除常数 2016 未 clamp) | — | — | 三仪器同得 30 | — | VERIFIED(问题) | **FP2-8**(修后重训) |

## 2. 模型预测(线上)
| 子项 | 源码版本 | 输入 | 模型文件 | 证据 | 部署 | 判定 | 缺口 |
|---|---|---|---|---|---|---|---|
| king LGBM | `shadow_loop_v3.py`(`lgb.Booster(model_file=BUNDLE/slow2026.txt)`) | bundle 内 cache_tail_40d / leg_returns / parity_signals_aug | `~/wide_shadow/shadow_bundle/slow2026.txt` sha256 **8d79186b…** = target_live `booster_sha` ✓; MANIFEST 8 文件 sha; `config.provenance`: built 2026-09-01T06:00:37Z, **generation v3_2026-09**, fold_ic 2024 .0548 / 2025 .063, pinned_ic2026 .0584, pinned_sharpe_full_b 2.28 | king 书自平价 max\|Δw\|=4e-10 每锚 | **在役** | VERIFIED | **v3 口径**; v4 bundle(pod2 `shadow_bundle_v4` f2365771 / `_v4e` 722c83b8, 09-09)从未换装 → FP2-8/9 |
| F10(V2MAIN DL) | `combo_stage.py` / `sidecar_blend.py`(`np.load(f10_live_s42_np.npz)`) | fea82 面板 | `fea171/f10_live_s42_np.npz` sha 351ae26b(**v3 2026-09-01 换装**, V2 配方全史重训至 08-30, np≡torch 1e-7; 备份 f4abac43); `.pt` 08-24 | SIDECAR_DRYRUN PASS 每锚 | 在役 | VERIFIED | 记忆: 两腿梯度止于 2025 底; DL fea82 资金费列只覆盖 2026-08 在役名单 → FP2-8 |
| 执行器对模型身份的钉 | `config/book.json external_book`: `booster_sha_pin: null`, `universe_sha_pin: null` | — | — | 读者只校验文件自洽(universe 配方重算), **不钉具体 sha** | 在役 | VERIFIED(缺口) | **FP2-6**(治理: 钉 sha, 需裁定) |

## 3. 策略组合与权重(生产者)
| 子项 | 源码版本 | 证据 | 判定 | 缺口 |
|---|---|---|---|---|
| combo_stage(king 0.55 + V2MAIN 0.45 + funding; 去 rev24; FTRIM; w3_masked 席位) | `fea171/combo_stage.py`(09-02 16:59), `sidecar_blend.py`(08-26); 每锚 log: kc/fc=own, net=0, 读者验收 ok | 09-16 rev24 单变量实验(独立研究员): 归零 rev24 combo 目标不变 ≤8.67e−19 | VERIFIED(在役行为) | **未整套重新认证**(连续组合/状态恢复的严格因果认证有边界; 反事实改写比例 27%→33%→31.5% 机制=席位滚动) → FP2-8 配对 |
| 席位(msharpe 900 锚, 逐锚滚动) | 同上 | regime_dash 逐锚 | VERIFIED | 席位对资金费燃料表盲(记忆 09-12) |

## 4. 交易执行 / 5. 记账对账异常处置(执行器)
| 子项 | 版本 | 证据 | 部署 | 判定 |
|---|---|---|---|---|
| 执行器全部(截量/下单/撤单/补单/止损/比例响应/未知仓位/减仓恢复/公证/日报/修订) | **6661ea3** = origin/main(链 ef60f85 → … → 183915f → cdfc06b → d580eb5 → 6661ea3) | 五轮独立复审收口; 生产电池 160/1/0(`receipts/PROD_BATTERY_20260917T022536Z_6661ea3_post_revendor.log`); 回滚已排演 | **已部署 02:06Z**; 首锚 04:00Z 待采 | VERIFIED |
| 余项 | NOSLEEP-1(证据层)· B14 已合同化 · 部署后首锚 | — | — | 开放(机器/验收) |

## 6. 回放 / 收益评估
| 子项 | 引擎 | 输入 | 读数 | 判定 | 缺口 |
|---|---|---|---|---|---|
| 608 日连续回放(2025-01..2026-08) | 独立研究员 `book_engine_lifecycle.replay_book_lifecycle`(ORDER funding→close→open→rebalance; 结算登记簿; 精确张数; 官方资金费审计) | 修复重训模型 + 给定成本 + **停机政策关闭** | Sharpe **2.523** [0.858, 4.185], vol 29.80%, 含 reshape; 126 格预注册网格中唯一交付格 | VERIFIED(条件读数) | 通用 CLOSE 终止瞬间归属(113 CLOSE/67 端点未发现漏算) → **FP2-5**; 未完成网格; 无选择校正 |
| 长窗读数 | 我方 W_ALPHA 9,138 锚 1.291; 对方 2025 全年 1.324; 停机臂 0.782 | — | 「0.8–1.3」= **人工保守情景锚点**(HONEST_EXPECTATION v4) | VERIFIED(定性) | 非验证出的线上区间 |
| 实盘 20 日 | 账本 | 总 +37.9%/yr(资金费 −48.9%, 价格 +86.8%); 09-16 +2.05%, 09-17 至 00Z −0.83% | VERIFIED | CI [−5.23, +7.23] 不排除任何值 |

## 7. 离线重训 / 评估 / 导出
| 子项 | 版本 | 产物/收据 | 判定 | 缺口 |
|---|---|---|---|---|
| v4 链(数据→legs→F10 20 折→king 导出→书层量化→出口门→换装) | `RUNBOOK_monthly_retrain_2026-10.md §0★`(修订 1–6), `chain_v4_monthly.sh`, 门 `v4_gate_*`(roll_paths 已三态+空值; `v4_gate_common` 24e813f1 冻结二态) | pod2 `/workspace/review_scratch/v4_gates/`: G1 parity PASS, G2 stable_hardened PASS(global FAIL), G4 report-only, JUDGE_v4e(09-09), STEP1, F10_GATE_RAW/CLIP, V3P_*; bundle v4/v4e | VERIFIED(存在) | **月驱动启动不重核上月合同/记录/工件**(FP2-3); **finalize 三态**(FP2-4); 修订 6 的 TRN-15/16 待裁定 |
| 配对评估 A1(新) vs A0(在役) | `JUDGE_v4e_hardened.json` 09-09T16:50Z, 3168 锚, s42/s2027, dyn/fix | 全 18 对比 **UNDECIDED**; A1−A0 dyn s42 +0.0605 bps/锚 CI [−0.168, +0.287] p>0 0.70; fix s42 +0.005 | VERIFIED | 早于 C1/C3/C5/holefix/king 轴/A0 重基 → **FP2-8 重跑** |
| 换装 | runbook §0★ 步 8(用户对具体 bundle sha 给字) | — | 未换 | FP2-9 |

## 8. FP2 修复清单(按依赖序; 每项 = 修复 + 测试 + 提交 + 复审交接)
| # | 项 | 环节 | 依赖 | 需裁定? |
|---|---|---|---|---|
| FP2-1 ✅(装置 v2 + 15 格负控; pod2 真实面板运行随 FP2-8) | 增量面板验证器三缺口: C1 分别核轴/有限支持/NaN-Inf/值; C2 从原始来源独立重建 now/iv/EMA(禁复制自比); 写出后重开核 payload; 负控 finite→Inf / 同值不同 mask / 误写一列 | 数据 | — | 否 |
| FP2-2 ✅(退役+守卫+链普查 8/8) | 资金费 v2 后视路径: 退役 `build_funding_hist.py` / `megacap_funding_replay.py` 的全段 median, `apply_funding_fix.py` span 改因果; **守卫测试 = v4 链构建器清单不含它们**(消费者普查入测试) | 数据 | — | 否 |
| FP2-2b | x0910 ivfix 面板接入 09 月延展行 | 数据 | — | 否(数据修正) |
| FP2-3 ✅(可选键 + 启动现场重跑 roll gate + 十月模板 + mk_prev_sha_record; 478/478, dryrun 双负控) | 月驱动 preflight 重核: 上月合同 + `ROLL_PREV_SHA_JSON` + 上月工件当前 sha, 三态 PASS 才起跑; 旧 PASS 票不再被接受 | 重训 | FP2-4 | 否 |
| FP2-4 ✅(finalize3 + 读者普查 10/10; roll gate 已切) | `v4_gate_common_v2.finalize3`(PASS 0 / FAIL 3 / UNAVAILABLE 3, 各自留因); 读者普查(哪些读 printed 标签); 冻结 24e813f1 不动 | 重训 | — | **是**(冻结装置的后继需你一句) |
| FP2-5 ✅(规则 R1–R7 成文 + 冻结他方引擎性质测试 12/12; 引擎无需改) | CLOSE 终止瞬间归属: 在 lifecycle 引擎登记后继 —— 规则「旧代非零持仓 + 同 ms 结算 + CLOSE/OPEN 任意合法顺序只计一次; 未知拒绝认证该现金路径; 不越世代末端」+ 顺序枚举性质测试; 复跑 608 日核不变 | 回放 | — | 否 |
| FP2-6 | 执行器钉模型身份: `booster_sha_pin`/`universe_sha_pin` 填在役值 + 换装流程随之更新; 测试: 错 sha ⇒ hold | 执行/模型 | — | **是**(线上行为门) |
| FP2-7 | 采纳 C1/C3/C5/C7 进正式 v4 数据链(逐文件、带其测试); C6 内容审(6ef59338 51 文件); A0 参照重基(死合约) | 数据/评估 | FP2-1/2 | 否 |
| FP2-8 | 修复版全链重训(pod2): 数据门 → legs → F10 20 折 s42/s2027 → king 导出(轴修) → JUDGE A1 vs A0(同窗同政策) → 出口门; 再经 lifecycle 回放(含停机政策臂)出**逐年 v4 RAW 口径表** = 最可信回测 | 重训/评估 | FP2-1..7 | 否(跑) |
| FP2-9 | 换装决策(bundle sha + F10 np sha) | 上线 | FP2-8 | **是** |

## §9 FP2-7 实测收口(2026-09-17 04:3x-04:5xZ, 只读探针, 受据 `FP2_receipts/`)
| 项 | 原登记 | 实测 | 判定 | 受据 |
|---|---|---|---|---|
| C1 三月 raw 回填 | 「未接入正式 v4 链」 | 我方 holefix2 缓存 BOB/BMT [2026-01-30, 03-03) 各 9216 行: ch0 NaN 0、冻结 0、log_cnt 无 0; MTL [03-30, 05-03) 9792 行同 | **不适用于我方数据**(缺陷在独立研究员的 canonical 档案, 其 `canonical_data.py:20,23` 前推) | `probe_c1c3_ours.out` |
| C3 519 标签重算 | 同上 | RAW 目标 y4s: BOB/BMT 2026-02 168/168 有限、MTL 2026-04 180/180 有限, qvk>0 全部 | **不适用**(我方这些锚从未被 mask) | `probe_c1c3_targets.out` |
| C6 内容审(6ef59338) | 「内容未审(仅 sha 相符)」 | 对象 = `fullaxis_continuous_scalar_20260915` 冻结(51 文件): 溯源绑定门(`repair_completion.py` 硬编码 3 档案/24,768 行)+ `funding_support.py` 诊断掩码(`exchange_pit_certified: False`); 主源 `build_funding.py`(53 行 dcc9fe92)/`build_targets.py`(18 行 938b4488)在 pod2 未入库: 逐名逐位复现原公式 + 代际外资金费 null 测 + 知识 HOLD; 日历 candidate2 166 名/168 CLOSE/13 OPEN, 非全 829 PIT | **已审**; 对我方数据: 13/13 OPEN 首根新代 bar ret5=NaN、prev NaN ⇒ 无跨代假收益 ⇒ **无需进链** | `probe_c6_open_bars.out` |
| C5 AERGO 估值点 | 「未接入」 | 属回放估值层 | → FP2-8 §2 估值覆盖门 | DESIGN_FP2-8 |
| C7 E60 顺序 | 「采纳但需改」 | 只在 RiskEngine 路径 | → FP2-8 停机政策臂 v2 引擎副本 | DESIGN_FP2-8 |
| A0 重基(死合约) | 「FP2-7c」 | FX_DATA TRD-D3 N1-N9 已测(TF Δg −0.0603/−0.0519, INCONCLUSIVE@δ0.05, 几乎全在 2026); 掩码工件 3badc4b6 在 pod2 | → FP2-8 两臂同掩码评估 | FACT_TABLE_DATA §TRD-D3 |
| king 轴首 5 天 | 「FP2-8(修后重训)」 | 机制核实: `pod_fea_ext_clamp.py` L26-32 `grid>=576` 但窗 2016, 负索引绕回 ⇒ v7=0 ⇒ 30 锚静默删除(非污染) | → FP2-8 v2 builder 显式 `grid>=2016` + 逐位正控 | DESIGN_FP2-8 §2 |
| FP2-6 钉 | 「需裁定」 | 读者 R2/H6/源码钉三格已认证; 生产 `on_unavailable=hold`; target_live 无 F10 身份字段 | **提案 + 补丁已备, 待用户字** | `PROPOSAL_FP2-6_booster_pin_2026-09-17.md`, `fp2-6_booster_pin_book_json.patch` |

## §10 FP2-8 运行与仪器(2026-09-17 06:0xZ; 状态随 pod2 收据更新)
| 项 | 位置 | 状态 |
|---|---|---|
| 合同 / 装置目录 / 根 | `v4_month_2026-09_fp2.env`(b7d0afa7)/ `$R/devices_v4chain` / `/workspace/fp2_2026-09` | preflight PASS 05:27:58Z(重跑 05:42Z 钉最终装置 sha) |
| cache 门 | `$R/v4_gates/cache_coverage.json`, `RAW_PATCH_COVERAGE.json` | PASS / PASS(952/952, unaccounted 0) |
| controls(v2 无掩码 vs 九月 v1 逐位) | `$R/controls/CONTROLS.json` | **PASS**(verify_only 08:59Z; K2 共同 10,182 锚逐位; 30 额外锚) |
| data / gates / king / legs / mwf / refit / np_export / arms / a0rerun / judge / export | `$R/chain_fp2_stage_*.log`, `$R/v4_gates/*.json`, `$R/chain_fp2_run.log` | data DONE 06:56Z; **gates PASS 09:38Z**(STEP1/STEP2 变体 9410a403/a4cda6db; AMENDMENT 8 截断感知); king 起 09:38Z; 运行器在跑 |
| 逐年表 | `fp2_per_year_table.py` → `$R/v4_gates/PER_YEAR_TABLE.{json,md}`(判官同源臂记录, AMENDMENT 4) | 装置就绪; 干跑(九月 A0 副本, 原 umask)仅验 schema, **非结果** |
| lifecycle 交叉核对 | AMENDMENT 4.3 | PENDING |
| 独立复审 | `HANDOFF_FP2_REVIEW_2026-09-17.md` + `REVIEW_REQUEST_FP2_2026-09-17.md` | 已交 |
| FP2-6 钉 king(用户字 09:0xZ) | 执行器 **6e177c4**(config/book.json booster_sha_pin=8d79186b…; universe 不钉) | 生产电池 160/1/0(唯一红 NOSLEEP-1) | 已部署 09:16Z; 首锚 12:24Z 验 | DL 钉 = FP2-6b(生产者写 f10_sha 后) |

> ⚠ **复审 F05 降级(2026-09-17 10:5xZ)**: FP2-1 资金费/假日面板重建的 `C2 … REPRODUCED` 判词在用新装置(`c2_compare_columns_sourced`, 提交 a1444008)重跑前**降级为「有源名部分未知」**: 旧装置把无源流的名(照抄旧面板)也计入 REPRODUCED。重跑后按 `C2_no_source` 的 n_with_source/n_no_source 重写本行。
