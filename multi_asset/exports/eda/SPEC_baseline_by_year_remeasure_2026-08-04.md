> **创建:** 2026-08-04 09:0x UTC | **Session:** 0C (C2-prereg) | **状态:** final — **规格**, 非测量(本文不含任何新数字) | **派工:** team-lead 队列第 2 件("现在就能做, 不阻塞于干净 s2") | **对象:** `engine/live/monitor.py` 的 `BASELINE_BY_YEAR` + `DECAY_FRAC`, 部署批第一批第 ④ 件 | **作废条件:** (a) 部署模型改判(如 plain 取代 xattn)⇒ 基线重测的对象变, 全文重述; (b) 实盘滚动 IC 的计算口径被改动 ⇒ §2 的"同口径"要求需重新表述。

# 规格 — `BASELINE_BY_YEAR` 重测 与 `_baseline_provenance()` 的第三问

## 0. 一句话

**不要给自检加第三个具名检查项。** 本项目**已经有**一个为这一族设计好的机制(`panel_caliber_manifest.json` 的 **generation 哈希 + flip_rule**), 而 `BASELINE_BY_YEAR` **是这一族的第三个成员, 也是唯一没被纳入的那个。** ⇒ **把它纳入既有机制, 比新增一问更耐用。**

---

## 1. ★★ 为什么"补第三问"是错的解法 —— team-lead 的顾虑成立, 而答案已经在盘上

**team-lead 的顾虑, 照录:**
> *"一个自检检查了三件里的两件, 补的时候要把第三件也补上, 否则**下次换的是别的东西, 它又检查不到**。"*

**这个顾虑是对的, 而"再加一问查面板"恰恰不解决它** —— 下次变的可能是宇宙(top-110 刷新)、目标定义、打分口径、折结构。**具名检查项的数量永远追不上可变维度的数量。**

### 1-1 盘上已有的正解: `panel_caliber_manifest.json` 的 `flip_rule`

该 manifest 为**同一族的另一个成员**(面板 funding 口径)设计, 其 `generation` 字段:
```json
"generation": {
  "id": "e46d5768f3baa7e9",
  "members": {"king": {"sha256": "5a7b27d9…"}, "s2": {"sha256": "8b1bc1ab…"}},
  "flip_rule": "this manifest is keyed to the generation hash ON PURPOSE. A retrain changes the
                hash, which fails the assertion, which forces a deliberate re-bless —
                the caliber expectation and the model version flip together or not at all."
}
```
**⇒ 它不枚举"哪些维度要一致", 而是把口径期望【绑在模型代次哈希上】: 任何一次换模型都会让哈希失配 ⇒ 断言红 ⇒ 强制一次【有意识的重新赐福】。** 变的是什么无所谓 —— **变了就红。**

### 1-2 ★★★ 而该 manifest 自己的 `why` 已经点名了这一族, 只是漏了第三个成员

> *"the funding caliber of a model-input panel is the same class of object as the frozen normalisation statistics: changing it feeds the frozen weights something they were not fitted on. **norm_stats got a hash; this is the panel's.**"*

**这一族有三个成员, 判据是同一条 —— "换了它, 就等于喂给冻结权重一个它没被拟合过的东西":**

| 成员 | 有没有被绑到代次 |
|---|---|
| `norm_stats`(冻结归一化统计) | **有**(该 `why` 明说 "norm_stats got a hash") |
| 面板 funding 口径 | **有**(本 manifest 就是为它建的) |
| **`BASELINE_BY_YEAR`(衰减告警基线)** | **★ 没有 —— 它是这一族里唯一裸着的** |

> **⇒ 换模型会让前两者红, 让第三者【静默地继续用旧数】。**
> **而第三者恰恰是【判决新模型死活】的那个门限。**

**⇒ 规格第一条: 把 `BASELINE_BY_YEAR` 纳入 `panel_caliber_manifest` 的 generation 绑定, 而不是给 `_baseline_provenance()` 加第三个 if。**

---

## 2. 重测规格(逐项写死, 免得届时凭手边有什么就用什么)

### 2-1 测什么

**`BASELINE_BY_YEAR[y]` 的定义必须是: 【部署模型】在【实盘滚动 IC 所用的同一口径】下, 在第 y 年的横截面 rank-IC。**

**⇒ 三个"同"必须逐条对齐, 因为不对齐正是现在的病:**

| 维度 | 实盘滚动 IC 那一侧(被判方) | 基线那一侧(判据) | 现状 |
|---|---|---|---|
| **打分对象** | 实盘**持仓** × **实际收益** | 回放的**模型分数** × 面板收益 | **不同** —— 这一条无法完全消除(见 §4-1) |
| **成员集** | 实盘当日 top-110 | 回放的 `MEMBER110` | 须核 |
| **面板** | 实盘线上口径 | **`wide_dl_full.npz`(脏)** | **★ 错的就是这条** |
| **模型代次** | 新模型 | **旧脏模型** | **★ 换装后必错** |

### 2-2 用哪张面板

**用【部署后实盘实际收到的那一张】。**

**★ 注意部署批已被 C3 砍小(2026-08-04 04:3xZ 修订): `panel_build.py:187` 不改了 ⇒ 面板仍是 SERVE 口径(尾部-13)。** ⇒ **基线必须测在 SERVE 口径面板上, 不是训练用的 causal 面板。**
> **这一条极易搞反, 因为新模型是在 causal 面板上【训】的。但基线要回答的是"它上线后能拿到多少", 不是"它训得多好"。** ⇒ **训练口径与基线口径本来就应该不同; 用训练口径会把基线定得过高, 于是告警永不触发 —— 那是把守卫调成了永远绿。**

### 2-3 窗口

**沿用现有的 disjoint 要求**(`_baseline_window_disjoint` 已实现): 基线窗口必须与被判窗口不相交。现状是**靠"冻结面板止于 2026-06-30、影子打分始于 07-01"这个巧合成立的**(该函数的 docstring 自己写了 "**that holds by accident of**")。
**⇒ 规格: 重测后必须显式声明基线窗口的起止, 并让 disjoint 检查读【声明值】而不是继续依赖巧合。**

### 2-4 `DECAY_FRAC` 不动

**保持 0.5, 且【禁止】在这次重测里调它。** 理由: 若基线与阈值同时变, 告警行为的变化无法归因; 且"调 `DECAY_FRAC` 让它别响"与"修基线"在结果上不可区分, 而动机完全不同。**一锚一变更(TEAM_PROTOCOL §6)。**

### 2-5 验收判据(写在测之前)

```
通过 iff  (1) 新基线的每一年都来自【同一次】重测, 且面板/成员集/模型代次三项在产物里被记录;
         (2) generation 哈希绑定已落地 —— 拿旧模型的哈希去跑, 断言必须【红】;
         (3) disjoint 检查读声明值, 且对一个人为构造的相交窗口必须【红】;
         (4) DECAY_FRAC 逐位未变。
```
**★ (2)(3) 都要求【红测】而不只是绿跑 —— 一个只验过绿的守卫, 与一个瞎掉的守卫输出相同**(今晚静态门那次的教训: 红/绿必须成对)。

---

## 3. `_baseline_provenance()` 的第三问 —— 写成什么形状

**现有两问(照代码):**
- **(a) 它是不是一次真实测量?** —— 不信注释, 去核 `engine_fullhist_replay.json`。**这一问的写法是模范, 保留。**
- **(b) 基线窗口是否与被判窗口不相交?**

**第三问【不是】"用的哪张面板", 而是:**

> **(c) 产生这个基线的那次测量, 其 generation 哈希是否等于当前部署模型的 generation 哈希?**

**为什么这个形状比"查面板"强:**
| 将来变的东西 | "查面板"能抓到吗 | "查 generation" 能抓到吗 |
|---|---|---|
| 换面板 | ✔ | ✔ |
| 换模型(面板不变) | **✘** ← **正是这次部署的情形** | ✔ |
| 刷新币集 / 改目标 / 改折结构 | ✘ | ✔(只要它进 generation) |

**⇒ 一句话: (a) 问"这是不是测量", (b) 问"它有没有偷看", (c) 问"它测的还是不是【现在这个东西】"。三问覆盖三类失效, 而 (c) 用哈希而非枚举, 所以它不随可变维度增长。**

---

## 4. 未解决 / 明标(本节是本文最该被读的一节)

1. **★ §2-1 第一行那个"不同"消不掉, 而它是这个守卫的固有限制。** 实盘滚动 IC 打的是**持仓×实际收益**(经过整形、cap、成本、成交), 基线打的是**模型分数×面板收益**。**二者永远不是同一个量** —— 换基线只能消掉面板与代次的不一致, **消不掉"信号层 vs 执行后"的层级差**。
   **⇒ 这意味着: 即使本规格全部落地, 该告警仍然是【近似】的。** 它能抓"信号塌了", 抓不到"信号没塌但执行把它吃光了"。**这一句必须随告警一起被引用, 否则下一个人会把它当成一个精确门限。**
2. **我没有重测任何东西**, 本文零新数字。新基线的**数值**必须由跑重测的人给, 并按 §2-5 验收。
3. **`DECAY_FRAC = 0.5` 本身的出处我没追。** 它是不是也来自某次测量, 我不知道 —— **按 §2-4 这次不动它, 但它应进下一轮 SEQ 1-b 式的枚举。**
4. **generation 哈希当前只含 king 与 s2 两个成员。** 若将来腿集变化(如 size 腿回归), **它是否该进 generation, 本文不裁**。
5. ~~我没有读 `engine_fullhist_replay.py` 是否能切换口径~~ **⇒ 已查, 转为事实, 且它是一个【小】前置:**
   ```
   engine/panel_source.py:17   def __init__(self, panel=PANEL, king=KING, s2=S2, ...)   ← 类【可参数化】
   engine/replay_fullhist.py:36    _SRC = PanelSource()                                  ← 但调用时不传
   engine/replay_fullhist.py:153-156  argparse 只有 --funding_mode / --no_c5 / --shaping / --out
                                                          ← 【没有 --panel / --king / --s2】
   ```
   **⇒ 底层类已经是对的, 缺的只是脚本的 CLI 透传。** 与 `factory/pipeline.py`(四个 `np.load` 全硬编码, 连类都不可参数化)**不同族、小一档**: 这里是"加三个 argparse 参数并透传", 那里是"改载入结构"。
   **⇒ 规格补一条前置: 重测前先给 `replay_fullhist.py` 加 `--panel/--king/--s2` 透传。这是纯参数化改动, 零行为变化, 应能独立验证(不传参时输出必须与现状逐位相同)。**
