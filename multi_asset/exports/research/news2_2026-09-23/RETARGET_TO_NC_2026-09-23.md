> **创建:** 2026-09-23 18:5xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(news2 代理) | **状态:** 评估 + 一条对集成者的请求, 待 lead 裁定; **未产生任何 NEW_S2 模型或书层数字** | **作废条件:** `nc_derive_producer.py` 的 `NEWS2_FAMILIES` / `load_news2` 接口改变, 或 `nc_hist_features.py` 的 pass1 / pass2 接口改变

# 把 news2 的 B 部分检查改指向 nc 树:能做什么、卡在哪、要集成者改一行

lead 指令(b)-2:「你的 26 格单测、射程门、D7 准入门、B8 逐位对照,改为指向 nc 生成的树」。实测下来这不是改一个路径,分四种情况。

## 0. 先说结论

| 我的检查 | 能否指向 nc 树 | 说明 |
|---|---|---|
| **B8 逐位对照** | **不用做了** | 集成者的 `nc_gate_g1.py` 的 **G1-3** 已经覆盖同一件事(补丁内核的 c7/v7/qvm vs 研究员 `window_stats`,f32 逐位为门,成员逐名),而且是在**真实 nc 输入**上跑的。我的 B8 是它的前身,留作收据。 |
| **26 格单测 · dlw / f8 那 21 格** | **能, 要补夹具** | nc 对这两个文件只多 2+2 条 A3 编辑(新收益通道的读取),其余就是我的 19+2 条 B 编辑。夹具要改成提供 A3 的收益通道输入。 |
| **26 格单测 · King 块那 5 格** | **要重写夹具** | nc 的 King 块多 15 条 A 编辑,已经要 `NC` / `TR` 两个模块、rr 通道、legal ∧ crypto、成员历史。我的合成夹具喂不了。 |
| **射程门 · D7 准入门** | **卡住, 要集成者改一行** | 见 §2 |

## 1. 我的重放核不能直接跑 nc 树(实测)

`news2_hist_features.set_tree()` 在 nc 树上**能**工作(收据格式兼容):King 块定位到 L538–L626,`_btcv_series` 抽得出,`F8_TREND_ROWS` 读到 `last`,资金费面板块定位到 L191–L197。

但实跑单锚重放 **`NameError: name 'NC' is not defined`** —— nc 的 King 块引用了 `nc_contract` 模块,生产者在模块级 import 它,我的 exec 命名空间里没有。

**这不该由我补。** 集成者的 `nc_hist_features.py` 才是 nc 树的重放核(DESIGN §C-4 把重放装置给了它):它注入 `NC` / `TR`(L41、L56),拆成 `pass1_anchor` / `pass2_anchor`,处理 rr 通道、成员历史、资金费 as-of。**两个重放核就是这轮 D11 的形状**,所以我不在自己的核里补 `NC`,而是把我的门改成驱动它的核。

⇒ 我这边要做的是**门驱动层的改写**(我的门 → `nc_hist_features.pass1/pass2`),不是路径替换。`pass1_anchor(I, A, P, cfg, king_block)` 需要 `nc_prep.py` 产出的 `I` 与成员历史,接口和我的 `replay_anchor(A, cd, ts, syms, ...)` 不同。

## 2. 卡点:per-fix 臂在 nc 里造不出来 —— 请集成者改一行

射程门与 D7 准入门的做法是**每条修复单开一臂**(只施加该条,别的不施加),然后判「射程外逐位不变」。

`nc_derive_producer.py` L29 把家族写死:
```python
NEWS2_FAMILIES = {"D4", "D5", "D6", "D7", "D8", "D9", "D14"}
```
以及 L464 `N2.Patcher(k, ..., NEWS2_FAMILIES)`。所以 nc 只能生成「全部 B 都施加」这一棵树,**造不出单条臂**,射程门无从跑起。

**请求(集成者的文件,我不动)**:把它改成可覆盖,例如
```python
NEWS2_FAMILIES = set((os.environ.get("NC_NEWS2_FAMILIES") or "D4,D5,D6,D7,D8,D9,D14").split(","))
```
缺省值不变 ⇒ 生产路径零影响;我就能用 `NC_NEWS2_FAMILIES=D8` 之类造臂。

D7 准入门另需 `--trend-rows all|last` 那个维度:nc 固定调 `N2.patch_combo(P[...], "last")`(L466)。同样一行,让它读环境变量即可。

## 3. 钉的问题(另报,已发 lead)

`nc` 钉的是我 `3dd4d6f50` 的版本 `9c475421…`,我现在是 `dbb10e00…`(摘除 D11/D13 之后),**nc 当前跑不起来**。实测换钉**输出中性**(五个生产者源文件逐位相同),但会让 nc 的排除守卫 `set(skipped) <= {"D11","D13"}` 变成空转。收据 `receipts/NEWS2_PIN_COMPARE.json`。

## 4. 我不执行「把 news2_derive_producer.py 标作废」

lead 指令(b)写「你的 `news2_derive_producer.py` 标作废,用横幅 + 原文保留」。**前提不成立**:nc 不是复制它,而是 `import` 它。
1. 它是 B 部分的**唯一在产实现**;
2. **加横幅就改 sha,nc 的第一条断言当场红**。
已停下报 lead,等裁定。

## 5. 顺序建议

1. 集成者改那一行(§2)+ 挪钉(§3),并把排除守卫换成正面检查;
2. 我改门驱动层到 `nc_hist_features`,重跑射程门与 D7 准入门;
3. 新收益通道接上后,按 FREEZE §3-1 在 nc 树上重跑全部(这也是 26 格夹具补 A3 输入的时机,一次做完)。
