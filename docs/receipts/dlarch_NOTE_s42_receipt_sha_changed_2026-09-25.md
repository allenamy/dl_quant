> **写于:** 2026-09-25 09:2xZ | **作者:** dlarch | **状态:** 具名注记, 交付件**未**回改(lead 裁定: 恢复也是再改一次交付件)

# 注记: seed 42 的 TRAIN_RECEIPT sha 变过一次, 内容未变

## 发生了什么

lead 要求评估 GPU 并行, 其中一项是"重跑一个已完成的折, `scores.npz` 必须与已存逐位相同"。我在
**本交付树上**的 `(T0, s42, 202506)` 做了这个跨负载检查(先备份、末尾验证 OOF sha、带失败自动恢复)。

| 键 | 旧 | 新 |
|---|---|---|
| `TRAIN_RECEIPT.json` 文件 sha | `21f94f907f8a1eb67da4ff9f72e3e65b1d20f6ad4258f6a42aeeb3fc62efc9fc` | **`178f2cbe8d61e174951a39720562529b441e3ae1a60a5da0390b8d31e31a0804`** |
| `F10_OOF.npz` sha | `de3f12028cd9c7c4238dab91d3172717566fa49996ce58a39feb54db91953dc3` | **未变** |

## 原因: 只有计时字段

逐项对比备份(`determinism_probe/ref_parent/202506/FOLD_RECEIPT.json`)与重跑结果:

- **相同**: `scores.npz` sha (`2d1d30ffc502…`)、`model.pt` sha (`2fa9e06c…`)、`train_loss`、`alpha`、
  `a_final` (`-2.3568949699401855`)、`scored_pairs` (72000)、`test_anchors` (180)
- **不同**: `elapsed_seconds` 135.33 → 133.93,以及 `curve[*].seconds`

⇒ `FOLD_RECEIPT.json` 文件 sha 变 (`2a47f56d` → `524eafd0`) ⇒ 记录它的 `TRAIN_RECEIPT.json` 文件 sha 变。
**没有任何预测改变。**

## 独立佐证

重跑后对整棵树跑回读门: `READBACK_VERDICT=GREEN folds=23 all_ok=True control_fired=True`, 且该收据的
sha 与重跑**之前完全相同**: `651e0eff7965bbe8b88fcb0de791274da22f1d570531776d448ad081ab2b21bd`
—— 因为回读收据只记**内容统计量**, 不记计时。这本身就是"内容未变"的一个独立读数。

## 引用键该用什么

用**内容 sha**, 不用收据文件 sha:

- 整个种子: `CONTENT_RECEIPT.json` 的 `content_sha256` = `002869ef10d8f94593e345e3ae386252b50c29c2632f4aed9b4a125c078a28ab`
- 只要预测: `oof_sha256` = `de3f1202…`(跨重跑稳定)

两者都由 `dlarch_content_receipt.py` 产出, 它把计时/GPU 名/绝对路径放进**不参与哈希**的 `env` 段。

## 我漏在哪(记在这里, 不只记在消息里)

跨负载检查前我做了安全检查, **但只验了 OOF sha**, 没想到收据 sha 也会因计时字段而变。
安全检查覆盖了"数据有没有变", 漏了"**引用键**有没有变"。
自此: 已交付的树**只读**; 任何重跑/探针都在副本目录做(lead 裁定)。
