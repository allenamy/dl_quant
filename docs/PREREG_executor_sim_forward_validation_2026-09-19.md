> **创建:** 2026-09-19 09:5xZ(冻结提交之后、前瞻期任何实盘锚运行之前) | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(流 E 执行器层子代理) | **状态:** 预注册 —— 无数据; 首次也是唯一一次读数在第 42 个前瞻窗存在之后 | **作废条件:** 批准表中任一文件改变(见 §2); 或在停止点之前算出任何前瞻期模拟数字; 或读数多于一次; 或读数所用门、模拟器、标定与本文所钉 sha 不同

# 预注册: 执行器模拟器 v3.1 的真前瞻验证(V1b 门 v2, 冻结后前 42 个完整实盘窗)

**为什么需要:** 复审 5b R5B-03 —— 09-11 → 09-18 那一周在 v1/v2 标定与诊断中已被看过, 按时间截断重拟合之后它只能叫"历史诊断", 不是独立验证。真正的前瞻验证只能用冻结之后才发生的实盘锚。

## 1. 冻结

- **冻结提交:** `ca86f383a`(committer 时间 2026-09-19T17:50:24+08:00 = **2026-09-19 09:50:24Z**)。
- 该提交钉住的装置(全部由门 v2 的 APPROVED 表逐文件复核, 任何一个不符即 UNAVAILABLE):
  - 模拟器 `exec_sim.py` v3.1 sha256 `29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24`
  - 判官 `v1b_gate.py` v2 sha256 `4a725921a470f4c11f47cda5a8e210979215079cea16b496c709c7cc62fb5410`
  - 标定器 `calib_v3.py` `14357bbadd6076fed5f31b9d9fe5095c41c5f3b37a40c7624501f88102d05e96`; 合池标定 `CALIBRATION_v3_POOLED_20260826_20260910.json` `fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6`(锚 08-26 00Z → 09-10 20Z)
  - 依赖 `simlib.py` `55246fe9…`、`v1_gate.py` `c97d9b3d…`、`fills_reader.py` `4a906fba…`、场所只读输入(MISSING_TRADES、BNB 指数、5 份平仓原始成交)—— 见门内 APPROVED 表
  - 电池 `tests_exec_sim.py` v3.1 `9458558e1bccfbb3fc44e5eb9e45b230ccb52ae90ae5446b9dcf905706270bf9`: `BATTERY VERDICT: ALL PASS 77/77 checks …`, exit code 0

## 2. 人口(写死, 不再改)

- **重启状态:** 执行器自己在 **09-19 12Z** 窗口 t0 的锚后回读(约 12:40Z, 晚于冻结时刻)—— 仓位、止损状态、NAV 按门 v2 规则从新镜像独立复算。该窗为热身窗, 不判。
- **判窗人口:** LIVE_G 顺序中, 起点锚 ≥ **2026-09-19 16Z**(epoch `1789833600`)的**前 42 个完整实盘窗**(门常量 `FORWARD_N_WINDOWS = 42`; 两锚合并的 8 小时窗算一个窗; 停机、整书平仓、入金、实验参数变化都**照样在内**, 不剔除)。若无合并窗, 第 42 个窗起点锚为 09-26 12Z。
- 选 16Z 而不是 12Z 的理由: 规则是"重启所用回读本身也必须晚于冻结"。冻结 09:50:24Z 之后的第一个锚是 12Z(其回读 ~12:40Z), 它做重启状态; 第一个被判的窗从 16Z 开始。
- **实盘侧须是闭合现金恒等式:** 每个判窗 `cash_ok` 为真, 否则 UNAVAILABLE(门 v2 `live_side_violations`)。

## 3. 读数规则

1. **只读一次,** 在第 42 个判窗已结束并完成下面 §4 的数据准备之后。在此之前任何人不计算前瞻期的模拟数字、不看前瞻期 V1b 读数(实盘本身的每锚监控照常)。
2. 门不满 42 窗 ⇒ `V1b[FORWARD] VERDICT: UNAVAILABLE`(门强制)。
3. 判词 = 门 v2 的输出逐字: PASS / FAIL / INVALID_INPUT / UNAVAILABLE, 不重调参数、不换窗口、不换种子(R = 32, 种子 0..31, 模拟器强制)、不重跑挑结果。
4. **V1b 只验条件均值**(每 4h 窗的价格与成交 / 资金费 / 手续费 / 换手的 32 路径均值 vs 唯一实盘路径); 路径风险(方差、停机/止损发生、尾部、maxDD)只作诊断报告, 不在判词里。界是预声明的工程容差, 不是统计等价检验。
5. 读数命令(逐字; `<…>` 是 §4 准备的新输入; 工作目录 = `multi_asset/exports/research/replay_exec_2026-09-19`):
```
/usr/bin/python3 exec_sim.py --events live --period FORWARD --forward-first-anchor 1789833600 --paths 32 \
    --mirror <NEW_MIRROR> --manifest <NEW_MANIFEST.json> --live-g <LIVE_G_FORWARD.json> --transfers <INCOME_TRANSFER_FORWARD.json> \
    --out SIM_v31_live_FORWARD_20260919T16Z_n42.json
/usr/bin/python3 v1b_gate.py SIM_v31_live_FORWARD_20260919T16Z_n42.json FORWARD V1B2_GATE_v31_FORWARD_20260919T16Z_n42.json \
    --mirror <NEW_MIRROR> --manifest <NEW_MANIFEST.json> --live-g <LIVE_G_FORWARD.json> --transfers <INCOME_TRANSFER_FORWARD.json> \
    --forward-first-anchor 1789833600 --calib-mirror <ORIGINAL_MIRROR (manifest 59875e5a)>
```

## 4. 读数前必须备好的数据(只动数据管道, 不动冻结装置)

1. **前瞻快照:** 现有 `snapshot_inputs.py` 把日期写死到 09-19、并会覆盖被钉住的 `INPUT_MANIFEST.json`, **不能原样用**。需要一个只读快照变体: 写入新镜像目录与**新文件名**的清单, 日期覆盖到第 42 个窗结束, 文件族与现有快照相同, 执行器导出树仍为 409ea16(模拟器从 `exec_tree_409ea16` 导入书层函数; 若前瞻期内实盘执行器换版, 前瞻验证衡量的是冻结模拟器 + 409ea16 书层逻辑对实际实盘, 换版提交须在读数件里逐条列出, 不改判词规则)。该变体须在读数前入库。
2. **实盘窗文件:** 用 `live_g_decomposition.py`(读数时的 sha 记入收据)从覆盖前瞻期的现金恒等式收据生成 LIVE_G 前瞻文件; 每个判窗须 `cash_ok`。
3. **划转:** 场所收入 TRANSFER 文件刷新到覆盖前瞻期; 本机任何 fapi 调用必须经 `multi_asset/exports/research/common/venue_quiet_window.py`(E-0919-V)。
4. **原镜像保留:** 清单 `59875e5a…` 对应的原镜像(本会话 scratchpad `replay_exec_mirror/`)须在读数时仍可读 —— 门 v2 用它重跑标定器复核标定人口与截止边界。若已丢失, 读数为 UNAVAILABLE, 不以别的方式替代。

## 5. 范围与局限(预先写明)

- 一周、单条实盘路径; PASS 是"在预声明的工程容差下这 42 个窗与实盘条件均值等价", 不是其它 regime 的保证, 也不验证路径风险。
- 合池参数跨越两个仍在盲态的实验(CFG-04、CFG-06)的全部臂; 读数只报合池量, 不出现任何逐臂结果。
- 生产者面板 `rolling.npz` 的 ±0.30 裁剪 bar 若出现在前瞻期, 会进入价格误差(已知噪声底, 见结果件 §7)。
