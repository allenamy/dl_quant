"""D4, third pass: lead was right, my first explanation was right in MECHANISM, and my withdrawal of it was
an over-correction. All three states are recorded; the measurement decides.

Measured (base arm vs D4 arm, anchor 1789660800):
  base X82 dtype = float16   ->  D4 X82 dtype = float32     (dtype DOES change)
  base X89 dtype = float32   ->  D4 X89 dtype = float32     (dtype does NOT change)
  f16 rounding of real X89-scale values: median relative 1.661e-04, p99 4.273e-04, max 1.312e-02
  D4 measured median relative change: X82 1.66e-04, X89 3.29e-04
"""
import json

MD = "/dev/shm/news2_2026-09-23/receipts/DIAG2_PASS2_REACH.md"
t = open(MD).read()
start = t.index("> **动格数不是效应量")
end = t.index("\n\n", t.index("NaN↔有限翻转: 全部为 0"))
new = """> **动格数不是效应量。D4 的解释经过三次修正, 三个状态都留在这里, 由实测定案。**
>
> 1. ~~D4 把 X82 存成 float32, 几乎每格动约 **1e-7**, 是纯存储精度改动。~~ — 机制对, **常数错**: 1e-7 是 float32 的机器精度, 而基线是 **float16**。
> 2. ~~「纯存储精度」解释不了它, 撤回该解释。~~ — **这是过度更正**。我拿错的参照否掉了一个本来正确的机制(lead 2026-09-24 指出)。
> 3. **实测定案**(基线臂 vs D4 臂, 锚 1789660800):
>
> | 量 | 实测 |
> |---|---|
> | base `X82` dtype | **float16** → D4 `X82` **float32**(dtype 确实变了) |
> | base `X89` dtype | **float32** → D4 `X89` **float32**(dtype **没**变) |
> | f16 舍入在真实 X89 量级值上的相对误差 | 中位 **1.661e-04**, p99 4.273e-04, max 1.312e-02 |
> | D4 实测中位相对变化 | `X82` **1.66e-04**, `X89` **3.29e-04** |
>
> ⇒ **`X82`: 解释成立。** D4 去掉 float16 存储舍入, 而其量级(中位相对 1.66e-04)与 f16 舍入的中位相对误差
> (1.661e-04)**吻合到三位有效数字**。f16 单位舍入是 4.883e-04, 与 1e-4 量级一致。
>
> ⇒ **`X89`: 解释不成立, 且这一半仍未解释。** X89 在两边**都是 float32**, 所以它那 23,511 格 / 22 列、
> 中位相对 3.29e-04 的变化**不是 dtype 造成的**。D4 在 X89 上还做了别的事, 本测量没有确定是什么,
> 我不在收据里猜。
>
> 保留的方法论结论不变: 计数与幅度给出**不同的排序**, 所以每个格数都必须配 max|Δ| 与中位 |Δ|。
> 逐项中位相对: D4 X82 1.66e-04 · D4 X89 3.29e-04 · **D5 king_X78 2.59e-07**(唯一真在 f32 精度量级) ·
> D6 2.48e-02 · D7 6.70e-03 · D8 2.66e-02 · D9 1.16e-02。**NaN↔有限翻转全部为 0。**"""
open(MD, "w").write(t[:start] + new + t[end:])
print("markdown D4 section rewritten from the measurement")

J = "/dev/shm/news2_2026-09-23/receipts/DIAG2_PASS2_REACH.json"
r = json.load(open(J))
r["D4_RESOLVED_06_0xZ"] = {
    "history": ["(1) I wrote: float32 storage, ~1e-7, pure precision -- mechanism right, CONSTANT WRONG "
                "(1e-7 is float32 eps; the baseline is float16).",
                "(2) I then withdrew the mechanism entirely -- an OVER-CORRECTION, caused by comparing "
                "against the wrong precision constant (lead caught this).",
                "(3) Measured, below."],
    "measured": {"base_X82_dtype": "float16", "D4_X82_dtype": "float32",
                 "base_X89_dtype": "float32", "D4_X89_dtype": "float32",
                 "f16_rounding_on_real_values_median_rel": 1.661e-04,
                 "f16_rounding_p99_rel": 4.273e-04, "f16_rounding_max_rel": 1.312e-02,
                 "f16_unit_roundoff": 4.883e-04,
                 "D4_measured_median_rel_X82": 1.66e-04, "D4_measured_median_rel_X89": 3.29e-04},
    "conclusion_X82": "EXPLAINED: removing float16 storage rounding; magnitude agrees with the f16 rounding "
                      "median to three significant figures.",
    "conclusion_X89": "NOT EXPLAINED BY DTYPE: X89 is float32 on BOTH sides, so its 23,511 cells / 22 columns "
                      "at 3.29e-04 median relative are something else D4 does. This measurement does not "
                      "establish what, and no guess is recorded here.",
    "anchor": 1789660800}
json.dump(r, open(J, "w"), indent=1)
print("json D4_RESOLVED section added")
