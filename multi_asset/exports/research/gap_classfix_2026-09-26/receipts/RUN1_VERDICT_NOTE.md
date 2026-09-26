> **创建:** 2026-09-26 17:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** run 1 判词记录(不改) | **作废条件:** 无(历史记录)

# run 1(tree GAP1, combo_stage cffd41d3)判词: FAIL n_bad=4 —— 按冻结判据原文如实记
- 通过 16/20: C0×3 字节同一 + T×3 耗时; G1/G2/G6 现码 RED 且补丁码 PASS(来源 own_gap<k>, 权重与桥接参照臂逐位相等); gap7 / X1–X3 现码 RED。
- 未过 4: gap7_patched / x1_patched / x2_patched / x3_patched。**唯一未过项是页报判据**: 判据要求 run.log 的 `GAP_PAGE` **那一行**含
  文件名与 `rejected` / `beyond_bound`; 补丁码把页报正文用 `\n` 拼接后整段写进日志, 于是 `GAP_PAGE` 行只有标题, 名字与原因在下一行
  (见 run1_x1_gap_page_block.txt)。其余条件在这 4 臂全过: rc 0 已发布、来源 == 判据值、权重与参照臂逐位相等(gap7 315 名, X 臂 318 名)。
- 处置(不改判据、不改判官): 这是被测代码的缺陷 —— 日志是一行一事件的文件, 多行日志会让按行 grep 的监控读不到内容。修法 = 日志行里把
  换行换成 ` | `(发往 Telegram 的正文保持多行)。新树 GAP3 = GAP2(含成员历史组件)+ 这一行; 全部补丁码臂在 GAP3 上重跑, 判官不变。
