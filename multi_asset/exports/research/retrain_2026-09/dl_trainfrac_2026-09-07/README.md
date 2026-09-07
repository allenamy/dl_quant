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

**sha**: 基底 `pod_f10_train_monthly_earlystop.py` `55ee8382deecebce` → 产物 `pod_f10_train_monthly_trainfrac.py` **`20b531ba0e65a899`**。

**逐折立项数字**(`trainfrac_calc.py`, 20 折 202501–202608): 梯度赤字均值 **207 天**(164–251); 满窗/85% 步数比 **1.1802**(1.1733–1.1880)⇒ 满窗 ep6 ≈ 85% ep7 步数(残差 **+1.2%**), ep7 会是 +18.0%。
