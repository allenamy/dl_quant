> **创建:** 2026-09-27 02:4xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (integ) | **状态:** 出处说明

三个文件由 integ 写入,但落在了另一个代理的提交 **6213fe12c** 里(提交信息是 King IC 装置),不在 integ 自己的提交中:
- `docs/DEPLOY_m3_on_2026-09-27.md` §1 的电池行(166/166);
- `m3_on_2026-09-27/receipts/BATTERY_m3on_a6f8c21_20260927T0102Z.log`;
- `fixpkg_e_2026-09-27/receipts/BATTERY_fixpkg_e_2c19df9_20260927T0105Z.log`。

经过:integ 执行 `git add -f <这三个路径>` 时,另一个 git 进程正持有 index.lock,那次提交报错失败。随后这三个路径以已暂存的状态,被那个并发提交一并带走。
内容已核对:两份电池日志的末行分别是 `ACCEPTANCE: ALL GREEN (166/166 suites exit 0)` 和 `(167/167 suites exit 0)`,与 scratch 里的原始日志逐字节相同(sha 见下)。

sha256 (repo vs scratch source):
ecf6795962cd174e
e3b0c44298fc1c14
