# MANIFEST · allweather_2026-09-05/t3c_revalidation(T3c DL 乘性调节复验 + T3/T3b/T2, 无偏口径)
> **创建:** 2026-09-05 16:5xZ | **Session:** b9646a9e / Track C agent | **预注册:** docs/PREREG_deploy_modulation_2026-09-04.md §2/§3(674ade3f… @c763361)+ docs/PREREG_fusion_2026-09-04.md 判据; 组长 09-06 重述冻结 | **结果文档:** docs/RESULT_t3c_revalidation_2026-09-05.md | **pod 源目录:** pod2 /workspace/review_scratch/allweather_trackC/t3c/(dev/ dev_alt/ 的 24 个 npz 留 pod, sha 见 logs/chain_t3c.log)

| 文件 | 内容 |
|---|---|
| w10_health.py | health_check 装置逐字节副本(8684d9a9…); 无补丁, 旋钮 KTAIL/KMOD/KMOD_L/KMOD_AGREE/KMOD_F10 为既有 |
| setup_t3c.sh / run_arm.sh / chain_t3c.sh | 布局(14 SAME)/ 单跑包装 / 恒等 4 格 + 4 臂 × 2 口径 × 2 种子 + V4 固定席位 4 跑 |
| check_equiv_t3c.py | 恒等收据脚本(四数组 array_equal + max|Δ| + config 相等) |
| judge_t3c.py / results/judge.json / results/tables.md | 冻结判官(CI 下界/逐年 −0.017/换手 +5%/V1/V2/V7; 次判 PREREG_fusion 判据)与全部数字(水平/配对 Δ 含装置书刻度/V1/V2/V4/V7/ES5) |
| logs/setup_t3c.log / check_equiv.log / chain_t3c.log / commands.txt | 布局与输入 sha / 恒等 4/4 PASS max|Δ| 0 / 产物 sha / 24 条逐字命令 rc=0 |
| logs/*_s*.out | 每跑 CONFIG·RECEIPT_EX |
| logs/judge_t3c.log | 判官 stdout(首行单位链) |
| data/ | 空(未建新数据; regime 序列直接读 health_check/masks/regime_series.npz 只读) |
| SHA256SUMS | 本目录全文件 sha(不含本文件与自身) |
