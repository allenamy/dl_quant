> **创建:** 2026-09-16 03:4xZ | **Session:** FX-PROD (session b9646a9e) | **状态:** 更正记录, 只追加 | **作废条件:** 无

# 更正: 提交 `71c80e1d` 携带的 17 个文件属 FX-PROD, 不属 FX-EXEC

**事实.** `71c80e1d`("FX-EXEC 更正: 电池窗口外误跑的迟到量按秒重算 = 85 s")的 18 个文件里, 只有第 1 个
`docs/fixprogram_2026-09-13/FX_EXEC/receipts/GATECOV/INCIDENT_battery_outside_window_20260916T0316Z.log`
是 FX-EXEC 的。其余 **17 个全部是 FX-PROD 的 FXR-PROD-1 / PROD-28 / 换装 dry run 收据**:

```
docs/fixprogram_2026-09-13/FX_PROD/FACT_TABLE_PROD.md
docs/fixprogram_2026-09-13/FX_PROD/SWAP_PLAN_FX_PROD.md
docs/fixprogram_2026-09-13/FX_PROD/receipts/fx_prod_commit_chain.txt
docs/fixprogram_2026-09-13/FX_PROD/receipts/fxr1/GREEN_FXR1_at_fix.log
docs/fixprogram_2026-09-13/FX_PROD/receipts/fxr1/GREEN_firstrun_RECEIPT_fixed.json
docs/fixprogram_2026-09-13/FX_PROD/receipts/fxr1/GREEN_rerun_REFUSED_RECEIPT_fixed.json
docs/fixprogram_2026-09-13/FX_PROD/receipts/fxr1/RED_PREFIX_rerun_RECEIPT_1cbeca90.json
docs/fixprogram_2026-09-13/FX_PROD/receipts/fxr1/SHA256SUMS_fxr1_prod28_swapdry.txt
docs/fixprogram_2026-09-13/FX_PROD/receipts/p9/P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz
docs/fixprogram_2026-09-13/FX_PROD/receipts/prod28/PROD28_RUNTIME.json
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/FOOTPRINT_swapdry_20260916.txt
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/RECEIPT_p5_rescore_seat_king.json
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/guard.log
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/live_ro_after.txt
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/live_ro_before.txt
docs/fixprogram_2026-09-13/FX_PROD/receipts/swapdry/run_dry.log
docs/receipts/fx_prod_stack.diff
```

**机理: 共享索引竞态.** 研究仓是一个工作树, 多个工作者共用**同一个 git index**。FX-PROD 在 03:40:0xZ 左右
`git add` 了这 17 个文件, 还没 `git commit`; FX-EXEC 在 03:40:51Z 用**不带显式 pathspec** 的 `git commit`
提交, 于是把索引里已暂存的全部内容(含 FX-PROD 的)一并写进了它的提交。FX-PROD 随后的 `git commit` 因索引已空
报 `no changes added to commit`, rc=1。

**这正是 FIXPROGRAM §0.7 已有的规矩在防的事**:「提交显式 pathspec 并核 `git show --name-only`」。
两侧都有责任 —— 提交方未用显式 pathspec; 暂存方(本人)在共享索引上让文件停留在已暂存状态。

**不做什么.** 不改写历史。`71c80e1d` 已是共享分支上的祖先, 其他工作者在其之上工作, rebase/amend 会破坏他们的树。
文件内容本身正确且完整(逐条 `git ls-files --error-unmatch` 核过 17/17 在库)。

**做什么.** (1) 本记录入库, 复审读提交链时以此为准; (2) FX-PROD 今后一律
`git commit -- <显式路径>`(绕开索引状态), 并在提交后逐条按**缺席**核对而非只看在场;
(3) 建议 lead 把「`git commit` 必带显式 pathspec」作为全体硬规矩重申 —— 这次没丢数据, 但同样的竞态
如果发生在**部分暂存**的时刻, 会把半成品写进别人的提交, 且两边的报告都会引到错误的提交号。
