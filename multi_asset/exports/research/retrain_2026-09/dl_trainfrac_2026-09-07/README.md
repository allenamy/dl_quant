# dl_trainfrac_2026-09-07 — 满窗梯度臂(TRAIN_FRAC)装置归档

**预注册**: `docs/PREREG_dl_full_gradient_window_2026-09-07.md` sha256 `d5f078a0910e826e6435787d736a11fcc7a264f4b4ca5c464c34b4d5d4599d73`(**写于任何本臂数字之前**)。
**状态(2026-09-07 15:2xZ)**: 补丁与发起脚本已就绪并通过 `py_compile`; **尚未跑任何臂** —— GPU 被独立研究员 CONST2027 占用(pid 10611), 按「不抢 GPU」顺延。

| 文件 | 作用 |
|---|---|
| `scripts/make_patch_trainfrac.py` | 补丁生成器(精确串替换, 7 个锚点各断言恰一次) |
| `trainfrac_patch.diff` | 生成的 diff(35 行) |
| `scripts/launch_mwf_trainfrac.sh` | 单臂单分片发起(X7FULL / X6FULL / SELFCHK) |
| `scripts/selfcheck_trainfrac.py` | **PREREG §6 自检**: `TRAIN_FRAC=0.85` 默认路径必须与归档 FIX7 **逐位相等**, 否则退出 1 并禁止发起 |
| `scripts/trainfrac_calc.py` | 立项依据的逐折算术(梯度赤字天数、步数比) |
| `scripts/judge_trainfrac.py` | **判官, sha256 `2191186853531b6d`** — 读法逐字取自预注册 §4.1/§4.2/§4.3 |

**sha**: 基底 `pod_f10_train_monthly_earlystop.py` `55ee8382deecebce` → 产物 `pod_f10_train_monthly_trainfrac.py` **`20b531ba0e65a899`**。

**逐折立项数字**(`trainfrac_calc.py`, 20 折 202501–202608): 梯度赤字均值 **207 天**(164–251); 满窗/85% 步数比 **1.1802**(1.1733–1.1880)⇒ 满窗 ep6 ≈ 85% ep7 步数(残差 **+1.2%**), ep7 会是 +18.0%。

## 判官先于数字的收据(2026-09-07 15:4xZ)
`judge_trainfrac.py` 写于**任何本臂数字存在之前**(彼时 GPU 仍由 CONST2027 占用, 两臂一格未跑)。当日在 pod 上执行, 它**按设计拒绝运行**:
```
AssertionError: MISSING ARM ARTIFACT X7FULL: .../w10_ablation_series_G_mE1x7full_R0_spl42.npz
                — judge refuses to run on a partial arm set
```
**这条报错即是收据。** 判官内含:
- §4.1 主门三条件逐字转录, 结论由代码计算并打印 `(A)/(B)/(C)`, 无人工判读余地;
- §4.2 **预先承诺的条件动作**由代码判定并打印 `PRE-COMMITTED CONDITIONAL ACTION triggered: True/False`;
- §4.3 非劣腿按 **E-0907-F 正确形式**判 `CI 下界 > −δ`, 并**并列打印**旧决策规则的结论以示区别, 附措辞纪律行;
- 每个对照**两侧臂名同行打印**(E-0907-E);
- 缺任何一臂即 `AssertionError` 退出, 不在部分臂集上出结论(判官 CI 随臂集变, 见 `judge_ci_depends_on_arm_set`)。
