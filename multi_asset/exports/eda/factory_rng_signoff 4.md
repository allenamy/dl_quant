> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 预注册管辖) | **状态:** final (协议修订 — bootstrap rng 方案) | **作废条件:** rng 方案再变 / 幸存门统计口径变
> factory_prereg.md §2.3/§2.5 的 rng 方案修订签字。适用 batch_002+; batch_001 台账 (M=140) 不改写。

# bootstrap rng 并行化 — 0C 签字

## 签字: **APPROVED (条件版)** —— per-formula 确定性 rng 合法且**更**正确, 附 4 条硬约束 (2 条防后门 + 1 条 scope + 1 条验证)。

## Q1 — 是否合法统计改动? **合法, 且更正确。**
- 串行穿线 (单 rng 顺序过所有公式): 公式 k 的 bootstrap 抽样依赖前 k−1 个公式消耗了多少抽样 → **公式 k 的 CI 依赖批内顺序与其他公式** = 顺序相关污染, 且不可并行/不可复现。这本身是隐患 (你的直觉对)。
- per-formula 独立 rng: 公式 k 的 CI 只依赖 (base_seed, 公式自身) → **CI 是公式自身数据的干净函数, 独立于评估顺序**。统计上**更正确** —— bootstrap CI 本就该估计该公式自身统计量的抽样分布, 不该被批内顺序/其他公式沾染。**签。**

## ★ Q1-scope 硬约束 (关键, 别漏): 只改 STAGE-0, STAGE-1 max-null 必须保留共享 rng
- **Stage-0 (并行, per-formula CI/z bootstrap): 用 per-formula rng —— 对, 这是要并行的部分。**
- **★ Stage-1 Reality-Check / Romano-Wolf max-null: 必须保留单一共享 rng。** 其正确性是**联合的**: 每个 null repeat 用**同一个 day-block 置换应用到所有 survivor 因子**, 再取 max-over-factors (这才是吃多重性+因子相关的 max-null)。若给每个因子独立 rng → 各因子置换不同 → **破坏 max-over-共享置换 结构 → 多重性核算错 (幸存门失效)**。Stage-1 只跑少数 survivors (串行, 便宜), 无需并行。**实现必须确保 per-formula rng 只入 stage0, 不碰 stage1 的 max-null 置换 rng。** (stage1 的 per-survivor CI 可选用 per-formula rng, 但 max-null 置换必须共享。)

## Q2 — 防后门: **两个条件, 都要锁**
1. **base_seed = 冻结预注册常量, 非 run 参数。** 现 `run_batch(seed=0)` 是**可调参数** = 后门 (选 seed 让边界公式 CI 排 0 = seed-hacking)。**必须**: base_seed 写死进 `ledger.py`/`factory_prereg` 常量 (同 M_MAX/BONFERRONI_Z), 移出 run_batch 签名 (或忽略调用方传值)。
2. **★ per-formula key 必须是公式内容 (ast_md5), 非批内位置 (formula_idx)。** 你转述的 "f(base_seed, formula_idx)" 里的 idx **若是批内位置** → 重排批次即改每个公式的 rng → **顺序相关 + 可 game (重排以给目标公式取有利 seed)**。**必须 key 在公式内容**: `rng = default_rng(hash(base_seed, ast_md5))` —— rng 是公式**自身**的确定函数, 换 rng 必换公式, 不可 game。**这条比"base_seed 固定"更要紧, 别只锁 base_seed 漏了 key。**

## Q3 — 验证标准: **0B 的两条必要, 加两条**
- 0B (a) n_jobs 1 vs 24 逐值 byte-identical ✓ (证并行确定性, 必要)。
- 0B (b) batch_001 6 survivors 新 rng 下仍 6 ✓ (但**弱**: 6 个都 ARCHIVE, 远离边界, ~1% 噪声不翻 archive 是低门槛)。
- **加 (c) ★ 批次重排 byte-identical**: 打乱公式输入顺序后, 每公式的 CI/z/verdict **逐值不变** —— 直接证 key 在内容非位置 (Q2.2 的机器验证)。**这条必跑。**
- **加 (d) 位移是噪声级非系统**: 报 serial vs per-formula 的 CI/z delta 分布, 确认在 bootstrap SE (~1%) 内且**随机非系统偏** (系统偏 = 红旗)。

## ★ 定心原则 (为何本改动 by-design 安全)
**幸存门是 z ≥ z\*(M_max)=4.42, 真信号大幅跨过 (batch_001 z 全 10-17)。** ~1% rng 位移对 z=10 的判决无关。**任何会因 ~1% rng 噪声翻转的 verdict = z≈4.42±噪声 的边界公式 = 本就不是稳健发现, 正确地不该是 survivor。** ⇒ rng 方案对**稳健** survivor 判决不可能 decision-relevant。**建议**: nboot 取足够大 (如 2000→3000+) 使 bootstrap SE « 决策余量; 且预注册"z 在 [4.42, 4.42×1.1] 的公式标 rng-sensitive, 需更高 nboot 复核"防未来边界个案。

## 一句
**签 (条件): per-formula 确定性 rng 更正确, 但 (i) 只改 stage0 别碰 stage1 max-null 的共享置换 rng, (ii) base_seed 冻结常量, (iii) ★ key 在 ast_md5 非批位置, (iv) 验证加"批重排 byte-identical" + "位移噪声级"。** 收到 0B 实现我核这 4 条 (尤其 iii key 与 stage1 scope) 再终签。台账 M=140 不改写正确。

---

## ★ 终签 (2026-07-20, 读码复核后) — **APPROVED, 全 4 约束达成。**

0B 修复后 0C 逐条核 (读实现, 非信报告):
- **Q1-scope 联合结构 CONFIRMED (核心, 我读了 `_maxnull_fast`):** 每个 repeat 从**单一共享** `null_rng=default_rng([RNG_BASE_SEED, STAGE1_NULL_TAG])` 抽**一个** day-block 置换 `pm`, 应用到**所有** survivor (`tp=tr[perm_i]` 一份共享置换目标), `best=max over fr_list` —— **共享置换 + max-over-survivor 的联合多重性结构正确恢复**, 串行非 per-formula。✓ 这正是 White Reality-Check / Romano-Wolf max-null。
- **stage0 key=内容 CONFIRMED:** `default_rng([RNG_BASE_SEED, int(root.value["md5"],16)])` = ast_md5 内容哈希 (非批位置) → 顺序无关+不可 game。✓
- **base_seed 冻结 CONFIRMED:** `RNG_BASE_SEED=20260720` 常量在 ledger.py (同 M_MAX/BONFERRONI_Z), run_batch/stage0/stage1 签名无 `seed=` 参数。✓
- **nboot=3000 ✓**（我建议的 SE«余量）。
- **四验证达标:** (a) n_jobs 1v24 byte-identical / (b) batch_001→6 / (c) **批重排 byte-identical (我 Q2.2 的机器证, key=内容非位置)** / (d) 位移 signed-mean −0.004 无偏、中位 1.16%≈MC 1.29%、z=4.42 附近零 flip。全 ✓。

**两处待定裁定:**
- (i) **RNG_BASE_SEED=20260720 — APPROVE + 锁死。** 值本身与正确性无关, 只要 (a) mining 前固定 (是, batch_001 前已定且 batch_001 已收官 0 进书, 未对任何结果调) (b) 内容-keyed (是)。20260720=日期, 非 cherry-pick, 已 commit。**★ 现为冻结 campaign 常量: 此后不得改 —— 见结果后改 seed = 后门。锁。**
- (ii) **预注册补 rng-sensitive 带 —— 我已自补** factory_prereg §2.3 (下)。

**终签: 签。batch_002 可用新 rng (M 从 140 续)。** 联合结构、内容-keying、seed-冻结 三个我关心的都读码确认真实。

---
**产物:** `exports/eda/factory_rng_signoff.md`。
