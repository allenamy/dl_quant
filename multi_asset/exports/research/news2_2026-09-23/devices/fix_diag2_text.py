"""Correct a claim I wrote into the diagnostic-2 output that the measurement does not support.

I wrote: "D4 stores X82 as float32, so nearly every X82 cell moves by about 1e-7 -- counting cells alone
reads a pure storage-precision change as the biggest fix." The count part is right. The SIZE is wrong:
measured median |delta| is 3.70e-05 absolute and 1.66e-04 RELATIVE to the base value, while float32 eps is
about 1.2e-07. So D4's effect is ~1000x larger than float32 rounding and "pure storage precision" does not
explain it. Numbers are untouched; only my explanatory sentence is replaced, and the replacement asserts
no mechanism I have not measured.
"""
import json, re

MD = "/dev/shm/news2_2026-09-23/receipts/DIAG2_PASS2_REACH.md"
t = open(MD).read()
old = ("> **动格数不是效应量。** D4 把 X82 存成 float32, 于是 X82 几乎每一格都动约 1e-7 —— "
       "只看格数会把一个纯存储精度改动读成作用最大的修复。所以每个格数都配 max|Δ| 与中位 |Δ|。")
new = (
    "> **动格数不是效应量, 而且我先前对 D4 的解释是错的(已更正)。**\n"
    ">\n"
    "> ~~D4 把 X82 存成 float32, 于是 X82 几乎每一格都动约 1e-7 —— 只看格数会把一个纯存储精度改动"
    "读成作用最大的修复。~~\n"
    ">\n"
    "> **格数那半对, 量级那半错。** 实测 D4 在 X82 上的中位 |Δ| 是 **3.70e-05**(相对基值 **1.66e-04**), "
    "而 float32 的机器精度约 1.2e-07 —— **比纯 float32 取整大约三个数量级**。所以「纯存储精度」解释不了它, "
    "这个解释我撤回。D4 到底改变了什么, 要由补丁文本本身回答, 我不在收据里猜。\n"
    ">\n"
    "> 保留的结论仍然成立: **动格数与幅度给出不同的排序**, 所以每个格数都必须配 max|Δ| 与中位 |Δ|。\n"
    "> 逐项相对幅度(中位 |Δ|/|base|): D4 X82 1.66e-04 · D4 X89 3.29e-04 · **D5 king_X78 2.59e-07**"
    "(这一项确实是精度量级) · D6 2.48e-02 · D7 6.70e-03 · D8 2.66e-02 · D9 1.16e-02。\n"
    "> **NaN↔有限翻转: 全部为 0** —— 所有差异都是有限对有限。")
assert t.count(old) == 1, f"anchor occurs {t.count(old)} times"
open(MD, "w").write(t.replace(old, new))
print("markdown caveat corrected (numbers untouched)")

J = "/dev/shm/news2_2026-09-23/receipts/DIAG2_PASS2_REACH.json"
r = json.load(open(J))
r["CORRECTION_05_5xZ"] = (
    "An earlier version of the markdown said D4's X82 change is 'about 1e-7, a pure storage-precision "
    "change'. Measured: median |delta| 3.70e-05 absolute, 1.66e-04 relative to base, versus float32 eps "
    "~1.2e-07 -- about three orders larger, so that explanation is withdrawn. The counts and magnitudes in "
    "this receipt are unchanged; only my explanatory sentence was wrong. Of the seven fixes, only D5's "
    "king_X78 median relative change (2.59e-07) is actually at precision scale.")
r["nan_flips"] = {"all_matrices_all_arms": 0,
                  "how_known": "cells_different equals n_finite_deltas for every (arm, matrix, anchor)"}
json.dump(r, open(J, "w"), indent=1)
print("json CORRECTION section added")
