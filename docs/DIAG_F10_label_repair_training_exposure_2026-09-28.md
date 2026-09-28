> **创建:** 2026-09-28 16:58 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final-diagnostic | **作废条件:** 被引用的模型收据、准入清点或抽样实现改变；不代替完整组合判词

# 补齐标签后，优化器实际看到了什么

这是训练完成后、完整组合数字读取前的机制诊断，不是事先登记的效果检验。原预注册及20条经济门不变：`PREREG_F10_label_evidence_repair_2026-09-28.md`。本件只读四份新折与四份U折收据、原准入清点，不读分数、损失曲线或收益。

| 种子/折 | 原→新可抽窗口 | 新准入窗口被抽次数 | 与U相同窗口的更新 | 改抽另一个既有窗口的更新 |
|---|---:|---:|---:|---:|
| 42 / 202608 | 175→177 | 1 | 27 | 68 |
| 42 / 202609 | 178→181 | 1 | 15 | 80 |
| 2027 / 202608 | 175→177 | 2 | 25 | 69 |
| 2027 / 202609 | 178→181 | 1 | 18 | 77 |

每行共96次更新；总384次里，新窗口5次（1.30%）、同一旧窗口85次、不同旧窗口294次（76.56%）。每折只有一个新窗口实际被抽到。这里按收据里的窗口标签终点识别窗口；先验唯一性、原集合为新集合子集、新增集合与准入清点相等、索引合法、三类计数闭合。

机制来自现有均匀分位抽样：两边使用相同随机数，但抽样集合从175变177、178变181，同一个分位对应的旧窗口大多也变了。源码 `devices/f10_label_repair_20260928/train_adapt.py` 的 `fit` 与 `admission` 记录可复核；原输入GPU对照已精确复现U的模型状态、窗口与分数，不能把这里的变化说成运行环境不稳定。

因此这轮**可以**评价“补齐已确认标签，再执行原训练算法”的整体结果；**不能**将经济差异单独归因为新标签的信息增益，也不能因结果无改善就判定真实标签修复没有价值。两种模型种子及成交路径不足以剥离大量旧样本替换。若未来要专门识别信息效应，应事先固定共同窗口的抽样日程，并单列新窗口替换的对照；本轮不改抽样或追试参数。

复跑（Pod，只读旧收据，输出必须不存在）：

```sh
python3 /dev/shm/training_exposure_label_repair_20260928.py --root /dev/shm/f10_label_repair_20260928_attempt2 --inventory /dev/shm/f10_label_repair_20260928_attempt2_sources/ADMISSION_INVENTORY.json --old /dev/shm/f10_recent_adapt_20260928_attempt2 --output /tmp/TRAINING_EXPOSURE_independent.json
```

源码入库：`multi_asset/exports/research/acting_lead_2026-09-27/devices/training_exposure_label_repair_20260928.py`，SHA256 `a53b3596ad380a4c668b9446189709153a313c294f31c040b7b1c8b054309072`。

收据：同根 `receipts/F10_LABEL_REPAIR_20260928/TRAINING_EXPOSURE_REPRO.json`，SHA256 `3b0f14ef2f583b100f80e1631752171d50aec46a24a27380dbeab7e1e16dfddf`，含九个输入SHA。第一次内联只读清点与此入库装置的四行结果逐项相同。没有模型、组合或生产动作改变。
