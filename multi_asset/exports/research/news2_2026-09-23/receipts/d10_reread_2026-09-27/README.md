> **创建:** 2026-09-27 11:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 描述性重读的逐步收据(计划 docs/PLAN_d10_reread_past_cut_2026-09-27.md);冻结判词 UNDECIDED(6838a219a)不改 | **作废条件:** 计划被改写

# D10 描述性重读:收据(逐步追加)

## R1 九月 API 毫秒源
- COMPLETE:829 个名,92,040 行,153 个名为空,失败 0。输出 sha 08fdd1c2178881a4423b3803d08f30363011339cba7df9f981726971e42e6f33。
- 空名普查(`r1/EMPTY_SYMBOLS_VS_UNIVERSE.json`):与切点之后 108 个锚上的书成员(469 个名)交集为 0;与十月 legs 切点之后 KZ 有限的名交集也为 0 ⇒ 不影响重读。

## R2 账本延长(d10_build_ledger_ms rev 2.2 → 2.3)
- **第一轮**(`r2_first/`,11:30:05Z):NOT_RECONCILED,原因只是计数缺陷:fold_removed 把窗口之后的 87,962 行算成了折叠删掉的行。
  - 数据本身没问题:五列逐位相同,PREFIX_BITWISE,升级 0,overlap 0。
  - 修复为 rev 2.3(bd6d2bdd7),属于**读数后修订(解释性)**。
- **rev 2.3 重跑**(`r2b/`):
  - **V1**:npz 数组与 e179071d 逐位 IDENTICAL。收据比较的字面判词如下(lead 原文):
    「V1 比较器字面判词为 DIFFERS:新增单向键 positive_control_reconciliation.rows_in_old_window。lead 解读:行为不变。依据是 npz 数组逐位相同、139 个旧键全同;唯一的差异是 rev 2.3 修复本身新增的诊断计数,值自洽(2,633,090 + 18 = 2,633,108)。预声明写 IDENTICAL 是预声明时的疏漏,具名记录。」
  - **R2**:RECONCILED;fold_removed 18,等于派生集合 18;ALL_BITWISE;不允许的差异 0;api_overlap_unequal 0;PREFIX_BITWISE,升级 0;切点之后 87,962 行;最后一行 09-27T07:00Z。账本 sha 76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db,与第一轮相同。
  - **same_second_extra 变异**:RECONCILED,fold_removed 19 等于派生集合 19,与预声明一致。前缀判 DIFFERS 是这个变异按构造必然出现的。
