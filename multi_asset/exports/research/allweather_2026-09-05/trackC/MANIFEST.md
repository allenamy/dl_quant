# MANIFEST · allweather_2026-09-05/trackC(Track C: 上市年龄倾斜 C1 / 只降波动目标 C2 / B1 maximin 重读 C3 / 全天候前沿表 C4)
> **创建:** 2026-09-05 14:4xZ | **Session:** b9646a9e / Track C agent | **预注册:** docs/PREREG_allweather_programme_2026-09-05.md §3 Track C(sha256 8a02895c…, commit 5075b36) | **结果文档:** docs/RESULT_trackC_book_construction_2026-09-05.md | **pod 源目录:** pod2 /workspace/review_scratch/allweather_trackC/(dev/ dev_alt/ 的 16 个 npz 产物留在 pod, sha 见 SHA256SUMS_pod 与 logs/chain_c1.log)

| 文件 | 内容 |
|---|---|
| w10_health_orig.py | health_check 装置逐字节副本, sha256 8684d9a9f43a8d15… |
| w10_agew.py | 补丁装置(+AGEW 上市年龄倾斜, m1 FZB 路径; AGEW=0 逐位同原件), sha256 55ba5028c06e15e7… |
| device.diff | 原件 vs 补丁 diff(41 行) |
| setup_trackC.sh / run_arm.sh / chain_c1.sh | 布局(符号链接与 health_check 逐一 SAME)/ 单跑包装(逐字命令入 logs/commands.txt)/ C1 链(4 恒等 + 12 剂量跑) |
| check_equiv_c.py | 恒等收据脚本(四数组 array_equal + max|Δ| + config 去自报键相等) |
| judge_c1.py / results/c1_judge.json / results/c1_tables.md | C1 判官(冻结判据)与全部数字 |
| c2_voltarget.py / c2/c2_voltarget.json / c2/c2_tables.md | C2 纸面叠加(保险 gate + 对称控制)与全部数字 |
| c4_frontier.py / c4/c4_frontier.{json,md} / c4/c3_seat_round2_B1.{json,md} | C4 前沿表(175 行, 每行 artifact 路径 + sha16 + 自报形态)与 C3 B1 重读 |
| logs/setup_trackC.log | 14/14 SAME + 输入 sha |
| logs/check_equiv.log / logs/chain_c1.log | 恒等 4/4 PASS(max|Δ| 0)/ 产物 sha + IDENTITY_PASS_COUNT |
| logs/commands.txt / logs/A*_*.out | 16 条逐字命令(全部 rc=0)/ 每跑 CONFIG·AGEW_DEF·RECEIPT_EX |
| logs/judge_c1.log / logs/c2_voltarget.log / logs/c4_frontier.log | 三个脚本的 stdout(单位链首行; c4 含 CROSSCHECK 行) |
| SHA256SUMS_pod / SHA256SUMS | pod 侧(含 16 npz)/ 本地归档全文件 sha |
