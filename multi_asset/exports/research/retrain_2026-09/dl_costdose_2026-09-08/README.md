# dl_costdose_2026-09-08 — 路径罚剂量臂(训练期 COST)装置归档

**预注册**: `docs/PREREG_dl_path_cost_dose_2026-09-08.md` sha256 `ce7a6be927a4c31284e58b3db1d682eb89a59903f7b3a2cc16ce0d1c23728d96`(**写于任何数字之前**)
**判官**: `scripts/judge_costdose.py` sha256 `3fe15c72f8c9abff` —— **写于任何书层数字之前**, 当日执行按设计拒绝运行(`AssertionError: MISSING ARM ARTIFACT C2_85 — judge refuses to run on a partial arm set`), 该报错即收据。
**补丁**: 基底 `pod_f10_train_monthly_trainfrac.py` `20b531ba0e65a899` → `pod_f10_train_monthly_costdose.py` **`5c58093e3b1bbd0b`**, 唯一改动 = L281 的 `COST == 3.52` 断言改白名单 `(3.52, 7.04, 14.08)`, 缺省逐字等价(9 行 diff)。
**自检门**: `COST=3.52` 缺省路径 2 折与归档 FIX7 **逐位相等**(`SELFCHK_PASS`, wall 678s)。
**训练**: 4 臂 × 4 分片 × 5 月 = **80/80 折全部 rc=0**, 异常扫描零命中, 各 wall 4,141–5,244 s。

| 臂 | COST | TRAIN_FRAC | tag |
|---|---|---|---|
| C2_85 | 7.04 | 0.85 | mE1c2f85 |
| C4_85 | 14.08 | 0.85 | mE1c4f85 |
| C2_FULL | 7.04 | 1.0 | mE1c2full |
| C4_FULL | 14.08 | 1.0 | mE1c4full |

**门 0 前瞻(训练帧, 非终审口径)**: 85% 0.05028 → 0.04830 → 0.04454; FULL 0.05174 → 0.04990 → 0.04596 —— 两族内均单调下降。**正式门 0 用回放口径的 `turnover/gross` 判**(预注册 §3.0)。
