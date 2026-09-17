> **创建:** 2026-09-17 08:5xZ | **Session:** 0134cBjSFjjurUhAz95RNuWk(主研究员) | **状态:** 复审指令(用户转述给独立研究员) | **作废条件:** FP2-8 出最终判官/逐年表后升 v2

# 独立研究员复审指令 · FP2 批次(2026-09-17)

你好。请对主研究员 2026-09-17 的 FP2 批次做独立复审。原则不变:**只读**(研究仓 `research/book-uplift-2026-09-11` 分支;不 checkout 改写、不动 pod2 `/workspace/fp2_2026-09` 以外任何目录、不碰实盘);**每条结论带受据**(文件路径 + commit/sha);**不接受"解释了失败原因"当作通过**;发现问题只报不修。

## A. 先读(按序)
1. `docs/fixprogram_2026-09-13/HANDOFF_FP2_REVIEW_2026-09-17.md` —— 交接件:提交链、七个待判问题、已知局限。
2. `docs/fixprogram_2026-09-13/DESIGN_FP2-8_fullchain_retrain_2026-09-17.md` —— 预注册 + AMENDMENT 1–7(全部写在任何书层数字之前)。
3. `docs/fixprogram_2026-09-13/ACCEPTANCE_LEDGER_full_chain_2026-09-17.md`(v1.3)—— 逐环节验收表(§8 FP2-1..5、§9 FP2-7 实测、§10 运行状态)。
4. `docs/fixprogram_2026-09-13/PROPOSAL_FP2-6_booster_pin_2026-09-17.md` —— 用户已裁定:钉 king(执行中)、DL 另立 FP2-6b、universe 不钉。
5. 受据:`docs/fixprogram_2026-09-13/FP2_receipts/`;pod2 收据 `/workspace/fp2_2026-09/v4_gates/*.json`、`/workspace/fp2_2026-09/controls/CONTROLS.json`。

## B. 提交链(研究仓;每条请 `git show --stat` 核对)
26982400 → ac8131cb(FP2-1..5)· dcf0e006(FP2-7 实测 + FP2-6 提案 + FP2-8 预注册)· 0b5df2f6(v2 构建器 + 掩码装置)· 73f40056(controls + FP2 门)· 19a246b8(驱动可选键 / 合同 PROPOSED3 / dev 树两缺陷 / 运行器 / 首锚验收)· 7ca64ab9(逐年表装置 + AMENDMENT 4)· d96c4cdc(交接件 + 验收表 v1.3)· e37ef281(AMENDMENT 5 OOM)· 6c18d1d2(4.3 补记)· e0476901(controls K3 判据修 + AMENDMENT 6)。

## C. 请逐条判定并给出「成立 / 不成立 / 无法判定(缺什么)」
1. **合同 PROPOSED3**(`ELIGIBILITY_CONTRACT.json` 1188267a → 69edc437):STEP1/STEP2 追加了 FP2 门变体批准 sha(`fp2_gate_step1.py` ae21f86f / `fp2_gate_step2.py` db5b44d1),前身 `.r1_1188267a.json` 保留。判:以 controls 收据(v2 无掩码 vs 九月 v1 逐位)替代"上月增量比较"的门语义是否成立;是否应把变体限定到 `V4_MONTH=2026-09 ∧ R≠review_scratch`。
2. **成员掩码语义**(AMENDMENT 1.2):A1 训练成员 = TRADABLE(W24H)@锚(不含 U-PIT/CRYPTO umask);评估两臂同 umask∧tradable(3badc4b6)。这是数据修正还是书性质改动?
3. **king v2 构建器**(AMENDMENT 1.1,`pod_fea_ext_clamp_v2.py` 7b8b843d,派生脚本 `derive_fp2_builders_v2.py`):全窗 clamp + 实际窗长归一 vs 显式 `grid>=2016` 丢弃;真实数据 controls 已证共同 10,182 锚逐位相等、额外恰 30 锚(AMENDMENT 6)。判:首 5 天以 2–7 天窗进入训练是否引入不可接受的弱统计噪音。
4. **AMENDMENT 4**:逐年表主仪器 = 臂记录(与 `judge_v4.py` 同源,`d30_n2_c42`),lifecycle 引擎降为交叉核对且 PENDING(4.3 补记:价格源不在盘上、登记表绑定 expanded3)。判:这是否削弱"最可信回测"的声明;若削弱,最小补救是什么。
5. **C1/C3/C6 不在我方数据**(FP2_receipts 三探针):是否遗漏了其它表现形式(v3splice 面板资金费列、fea82 窗口特征在代际边界的泄漏等)。
6. **`run_arm.sh` 硬编码九月根**(dev 树内,FP2 副本已改 f30b2c7c;十月 runbook §0★ 修订 8):是否应立即收进装置目录由 D 分发。
7. **`build_dev_v4.py` 掩码感知自检**(env `DEV_MEMBER_MASK_NPZ`):「掩码成员 ⊆ 参照 ∧ 被减者掩码为 False」是否足够,还是应要求相等。
8. **controls K3 判据修正**(AMENDMENT 6):把"成员特征全部有限"改为"非资金费列有限"并用 `VERIFY_ONLY=1` 在既有 rc-0 产物上重判(不重建)。判:这是否属于"看到数字后改判据"(不应),还是"判据本身错(king 面板首行前 fund 列 NaN、九月 v1 同)"(应)。请独立核 `controls/CONTROLS_fail_K3criterion_20260917T0819Z.json` 与新收据。
9. **FP2-9 判据 AMENDMENT 7**(用户字:有帮助或不损害即换装):G1 改为非劣性判据「A1−A0 在 W_ALPHA 与 KING_LIVE、s42 与 s2027、dyn 下 CI95 **下界 > −δ**(δ=0.05 bps/锚/gross)」,BETTER 为下界 > 0;UNDECIDED 保留给下界 ≤ −δ 但上界 ≥ 0 的情形。判:δ 与两窗两种子"全满足"的合取是否恰当;是否需要 KING_LIVE 单独更严。
10. **FP2-6 实施**(执行器 `config/book.json booster_sha_pin` 填 8d79186b…;runbook 步 8 加"同窗改钉";DL 钉 FP2-6b 待生产者扩 schema):请在部署提交后核对提交链与电池计数(与 6661ea3 同一部署协议)。

## D. 报告格式
每条:判定 + 一句话理由 + 受据路径;发现的新问题按 P1/P2 分级,只报不修;若任一 UNAVAILABLE,写明缺什么。回件请落在 `docs/fixprogram_2026-09-13/REVIEW_FP2_<你的 session>_2026-09-17.md`。
