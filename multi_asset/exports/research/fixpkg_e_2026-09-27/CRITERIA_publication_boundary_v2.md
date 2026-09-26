> **创建:** 2026-09-26 21:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** FROZEN 判据(写于 v2 测试任何代码之前) | **作废条件:** lead 裁定;只追加

# fix-pkg-e 第 2 项:发布边界测试 v2(E-0926-H)
缺陷(47c8bdfe3 已查清):20260922 的 tests_combo_publication_boundary.py 用手写 env 执行 combo_stage 的发布 Try 节点;C 发布(12a76de8)把 `DIO`/`io` 放进了 Try ⇒ NameError 被 except 吞成 _bail ⇒ 4/6 红(3 条是 env 漂移,1 条 late_status_error 编码的是被 C 发布有意推翻的旧合同)。
修法规格:
1. env 补 `io` 与生产者自己的 `durable_io`(读 ~/wide_shadow/fea171/durable_io.py,只读)。
2. **新测试 `test_env_covers_every_free_name`**:发布 Try 节点里「被读取且在节点内从未被赋值」的名字(去掉 builtins)必须全部在 env 里,**唯一例外**是一个具名的 ALLOWED_ABSENT 表(每个名字带理由);并且断言 ALLOWED_ABSENT 里的每个名字的**每一次读取**都位于一个带 `except Exception` 的内层 try 里(由 AST 推出,不手写)。⇒ 被测代码明天多出一个名字,这条测试直接红并点名,而不是在 except 里静默变成 _bail。
3. `late_status_error` 改为 C 发布的合同:发布之后状态文件写失败(注入 `DIO.write_json_durable` 在 step=="done" 时抛 DurableWriteError)⇒ **不判失败**、目标已发布且通过真实读者校验、恰好两次 replace、从不回写 King。
判据:
- B 基线:v2 在生产 12a76de8 上 **7/7 OK**(6 条原测试 + 新测试);在 NC 363dd8c8 上新测试可以红(那一版没有 DIO,环境里多给名字不影响),其余 6 条 OK。
- C 候选:v2 在 GAP4 5eaabcdb 上 7/7 OK。
- R 红控:(a) 从 env 拿掉 DIO ⇒ 新测试红并点名 DIO;(b) 在被测源里多引入一个新全局名(变异:在 Try 内加一行 `_zz = SOME_NEW_GLOBAL`)⇒ 新测试红并点名;(c) 把 ALLOWED_ABSENT 的某个名字挪到非 try 位置(变异)⇒ 新测试红。
